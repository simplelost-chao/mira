import asyncio
import hashlib
import shutil
import subprocess
import typer
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

cli = typer.Typer()

from contextlib import asynccontextmanager

# ── ttyd subprocess management ─────────────────────────────────────────────────
_TTYD_PORT = 7681
_ttyd_proc: subprocess.Popen | None = None

def _ttyd_bin() -> str:
    return shutil.which("ttyd") or "/opt/homebrew/bin/ttyd"

def _tmux_bin() -> str:
    return shutil.which("tmux") or "/opt/homebrew/bin/tmux"

def _start_ttyd() -> None:
    """Start ttyd subprocess. Uses admin_password as HTTP basic auth (admin:<pwd>).

    Without admin_password set, ttyd is wide open — only safe on localhost/tailnet.
    With it set, every request to /terminal/ requires Authorization header.
    """
    global _ttyd_proc
    ttyd = _ttyd_bin()
    tmux = _tmux_bin()
    if not Path(ttyd).exists():
        return

    from vibe.config import load_global_config
    pwd = (load_global_config().get("admin_password") or "").strip()

    cmd = [
        ttyd, "-p", str(_TTYD_PORT),
        "--writable",
        "--base-path", "/terminal",
    ]
    if pwd:
        cmd += ["--credential", f"admin:{pwd}"]
    cmd += [tmux, "new-session", "-A", "-s", "mira", "-c", str(Path.home())]

    _ttyd_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _watch_ttyd() -> None:
    """Restart ttyd if it dies."""
    while True:
        time.sleep(5)
        if _ttyd_proc and _ttyd_proc.poll() is not None:
            _start_ttyd()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _cache, _cache_ts
    from vibe.cache_db import init_db, load_projects
    init_db()
    cached, ts = load_projects()
    if cached:
        _cache, _cache_ts = cached, ts
    threading.Thread(target=_background_refresh, daemon=True).start()
    from vibe.history_db import init_db as history_init_db
    from vibe.session_indexer import run_indexer
    history_init_db()
    threading.Thread(target=run_indexer, daemon=True).start()
    from vibe.terminal_monitor import run_monitor
    threading.Thread(target=run_monitor, daemon=True).start()
    _start_ttyd()
    threading.Thread(target=_watch_ttyd, daemon=True).start()
    yield
    if _ttyd_proc:
        _ttyd_proc.terminate()

api = FastAPI(title="Vibe Manager", lifespan=_lifespan)

STATIC_DIR = Path(__file__).parent.parent / "static"

if STATIC_DIR.exists():
    api.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @api.get("/", response_class=FileResponse)
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"),
                            headers={"Cache-Control": "no-cache"})

# ── In-memory cache ────────────────────────────────────────────────────────────
_cache: list[dict] = []
_cache_ts: float = 0.0
_cache_lock = threading.Lock()
_refresh_lock = threading.Lock()   # prevents concurrent rebuilds
_CACHE_TTL = 120  # seconds
_refreshing = False

# ── Agent ──────────────────────────────────────────────────────────────────────
_alerts: list[str] = []
_alerts_lock = threading.Lock()

_AGENT_MODEL = "qwen2.5:7b"

# ── Admin Auth ─────────────────────────────────────────────────────────────────

def _admin_token() -> str | None:
    """Return expected admin token derived from password, or None if auth is disabled."""
    from vibe.config import load_global_config
    password = (load_global_config().get("admin_password") or "").strip()
    if not password:
        return None
    return hashlib.sha256(password.encode()).hexdigest()


def _is_admin(request: Request) -> bool:
    token = _admin_token()
    if token is None:
        return True  # No password configured → open access
    return request.headers.get("X-Admin-Token") == token


_DANGEROUS_PATTERNS = [
    "rm -rf /", "rm -rf ~", ":(){ :|:& };:", "mkfs", "dd if=/dev/zero",
    "> /dev/sd", "curl | bash", "wget | sh", "curl|bash", "wget|sh",
    "chmod 777 /",
]

_SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "在本机执行 shell 命令，返回 stdout/stderr。用于查看日志、检查进程、重启服务等。",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 shell 命令"},
                "working_dir": {"type": "string", "description": "工作目录，默认 ~"},
            },
            "required": ["command"],
        },
    },
}

_READ_TERMINAL_TOOL = {
    "type": "function",
    "function": {
        "name": "read_terminal",
        "description": "读取一个 tmux pane 的最新输出，用于了解任务进度或判断是否在等待确认。",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "tmux pane target，如 work:0.1"},
                "lines":  {"type": "integer", "description": "读取行数，默认 50"},
            },
            "required": ["target"],
        },
    },
}

_SEND_TERMINAL_TOOL = {
    "type": "function",
    "function": {
        "name": "send_to_terminal",
        "description": "向 tmux pane 发送按键或文字，用于确认操作或输入指令。",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "tmux pane target，如 work:0.1"},
                "keys":   {"type": "string", "description": "要发送的按键，如 'y\\n'、'no\\n'、'exit\\n'"},
            },
            "required": ["target", "keys"],
        },
    },
}


def _build_system_prompt(projects: list[dict]) -> str:
    from datetime import datetime
    lines = []
    for p in projects:
        svc = p.get("service") or {}
        git = p.get("git") or {}
        status = "运行中" if svc.get("is_running") else "未运行"
        port = f":{svc['port']}" if svc.get("port") else ""
        domain = svc.get("public_domain", "")
        commits = git.get("monthly_commits", 0)
        branch = git.get("branch", "?")
        lines.append(
            f"- {p['name']}（{p.get('status', 'active')}）："
            f"{status}{port}，{domain}，{commits}次提交/月，branch={branch}"
        )
    summary = "\n".join(lines) if lines else "（暂无数据）"
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Terminal panes summary
    try:
        from vibe.terminal_monitor import get_panes
        panes = get_panes()
        if panes:
            pane_lines = []
            for pn in panes:
                status_str = "⚠ 等待确认" if pn.get("waiting") else "运行中"
                pane_lines.append(f"  - {pn['target']} [{pn['label']}] {status_str}")
            terminal_section = "\n已监控的 terminal panes：\n" + "\n".join(pane_lines)
        else:
            terminal_section = ""
    except Exception:
        terminal_section = ""

    return (
        f"你是 Mira，一个本地项目管理 agent。今天是 {date}。\n"
        f"运行在 macOS。\n"
        f"用中文回答。需要查看实际情况时使用 run_shell 工具。\n"
        f"需要读取 terminal 输出时使用 read_terminal，需要发送指令时使用 send_to_terminal。\n"
        f"如果工具执行后仍然找不到所需信息，或问题超出你的能力范围，直接告诉用户你不知道，不要反复重试。\n\n"
        f"当前项目状态（共 {len(projects)} 个项目）：\n{summary}"
        f"{terminal_section}"
    )


def _run_shell(command: str, working_dir: str = "~") -> str:
    import subprocess, os
    normalized = " ".join(command.split()).lower()
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.lower() in normalized:
            return f"[拒绝执行] 包含危险操作：{pattern}"
    cwd = os.path.expanduser(working_dir)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            cwd=cwd, timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        if len(output) > 3000:
            output = output[:3000] + "\n...[输出已截断]"
        return output or "(无输出)"
    except subprocess.TimeoutExpired:
        return "[超时] 命令执行超过 30 秒"
    except Exception as e:
        return f"[错误] {e}"


def _check_anomalies(projects: list[dict]) -> None:
    from datetime import datetime
    global _alerts
    new_alerts = []
    for p in projects:
        if p.get("status") != "active":
            continue
        svc = p.get("service") or {}
        if svc.get("port") and not svc.get("is_running"):
            new_alerts.append(f"{p['name']} 服务应运行在 :{svc['port']} 但当前未运行")
        git = p.get("git") or {}
        monthly = git.get("monthly_commits")
        if monthly is not None and monthly == 0:
            new_alerts.append(f"{p['name']} 本月没有新提交")
    ts = datetime.now().strftime("%H:%M")
    with _alerts_lock:
        _alerts.clear()
        _alerts.extend(f"[{ts}] {a}" for a in new_alerts)
        if len(_alerts) > 50:
            del _alerts[:-50]


def _collect_one(item: dict) -> dict:
    from vibe.aggregator import collect_project
    from vibe.models import ProjectInfo
    path = Path(item["path"])
    try:
        info = collect_project(path, name=item["name"], vibe_cfg=item["vibe_config"])
        return info.model_dump()
    except Exception as e:
        return ProjectInfo(
            id=path.name, name=item["name"], path=str(path),
            status="active", error=str(e),
        ).model_dump()


def _resolve_ip(hostname: str) -> str:
    """Resolve hostname to IP, return empty string on failure."""
    import socket
    try:
        return socket.gethostbyname(hostname)
    except Exception:
        return ""


def _http_check(hostname: str, timeout: float = 1.5) -> bool:
    """Return True if https://hostname returns any HTTP response (even 4xx/5xx)."""
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen(f"https://{hostname}", timeout=timeout, context=ctx)
        return True
    except urllib.error.HTTPError:
        return True   # got a response → server is up
    except Exception:
        return False


def _enrich_domains(projects: list[dict]) -> list[dict]:
    """Attach public_domain, public_ip to each project's service.
    is_running is already set correctly by collect_service (with health token check).
    Priority: vibe.yaml `domain` field > cloudflared port mapping."""
    port_to_host = _parse_cloudflared_tunnels()  # {port: hostname}

    # First pass: fill in cloudflared domain for projects without one
    for p in projects:
        svc = p.get("service") or {}
        if svc.get("public_domain"):
            continue  # vibe.yaml takes priority
        port = svc.get("port")
        if port and port in port_to_host:
            p["service"] = {**svc, "public_domain": port_to_host[port]}

    # Collect all unique hostnames
    hostnames = {
        p["service"]["public_domain"]
        for p in projects
        if p.get("service", {}).get("public_domain")
    }
    if not hostnames:
        return projects

    # Resolve IPs in parallel (is_running already correct from collect_service)
    ip_map: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(hostnames)) as pool:
        ip_futs = {pool.submit(_resolve_ip, h): h for h in hostnames}
        for f in as_completed(ip_futs):
            ip_map[ip_futs[f]] = f.result()

    for p in projects:
        svc = p.get("service") or {}
        domain = svc.get("public_domain")
        if domain:
            p["service"] = {**svc, "public_ip": ip_map.get(domain, "")}
    return projects


def _build_projects() -> list[dict]:
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    # Collect all projects in parallel (8 workers)
    projects: list[dict] = [None] * len(discovered)  # type: ignore
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_collect_one, item): i for i, item in enumerate(discovered)}
        for fut in as_completed(futures):
            projects[futures[fut]] = fut.result()
    projects = [p for p in projects if p is not None]
    return _enrich_domains(projects)


def _rebuild_and_persist() -> list[dict]:
    from vibe.cache_db import save_projects
    global _cache, _cache_ts, _refreshing
    with _refresh_lock:
        _refreshing = True
        try:
            projects = _build_projects()
            save_projects(projects)
            _check_anomalies(projects)
            with _cache_lock:
                _cache = projects
                _cache_ts = time.time()
            return projects
        finally:
            _refreshing = False


def get_all_projects(force: bool = False) -> list[dict]:
    global _cache, _cache_ts
    with _cache_lock:
        if not force and _cache and (time.time() - _cache_ts) < _CACHE_TTL:
            return _cache
        if not force and _cache:
            # Stale cache: trigger background refresh if not already running,
            # always return immediately (never block on a running refresh)
            if not _refreshing:
                threading.Thread(target=_rebuild_and_persist, daemon=True).start()
            return _cache
        if not force and _refreshing:
            # No cache yet but a build is in progress — wait for it instead
            # of starting a second rebuild. Release cache lock first to avoid
            # deadlock, then wait for the refresh lock.
            pass
    if not force and _refreshing:
        with _refresh_lock:
            pass  # Wait for the in-progress build to finish
        with _cache_lock:
            if _cache:
                return _cache
    return _rebuild_and_persist()


def _background_refresh():
    """Refresh cache every TTL seconds."""
    while True:
        time.sleep(_CACHE_TTL)
        try:
            _rebuild_and_persist()
        except Exception:
            pass


def _mask_projects(projects: list[dict]) -> list[dict]:
    """Remove sensitive cost/token fields and add _masked flag for non-admin responses."""
    import copy
    result = copy.deepcopy(projects)
    _COST_KEYS = {"estimated_cost_usd", "input_tokens", "output_tokens",
                  "cache_read_tokens", "cache_write_tokens"}
    for p in result:
        act = p.get("claude_activity") or {}
        if any(k in act for k in _COST_KEYS):
            for k in _COST_KEYS:
                act.pop(k, None)
            act["_masked"] = True
            p["claude_activity"] = act
    return result


@api.get("/api/projects")
def list_projects(request: Request):
    projects = get_all_projects()
    return projects if _is_admin(request) else _mask_projects(projects)

@api.get("/api/projects/{project_id}")
def get_project(request: Request, project_id: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p if _is_admin(request) else _mask_projects([p])[0]
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/refresh")
def refresh_project(project_id: str):
    return get_project(project_id)

_NC = {"Cache-Control": "no-store, no-cache, must-revalidate"}

@api.get("/stats", response_class=HTMLResponse)
def stats_page_route():
    from vibe.stats_page import render_stats_page
    return HTMLResponse(render_stats_page(), headers=_NC)


@api.get("/dev", response_class=HTMLResponse)
def dev_page_route():
    from vibe.dev_page import render_dev_page
    return HTMLResponse(render_dev_page(), headers=_NC)


@api.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(request: Request, project_id: str):
    import json as _json
    from vibe.detail_page import render_detail_page
    projects = get_all_projects()
    item = next((p for p in projects if p["id"] == project_id), None)
    name = item["name"] if item else project_id
    # Embed project data to avoid a second round-trip for /api/projects/{id}.
    # Strip large lazy-loaded fields (design_docs, plans) — only needed on the design tab.
    _LAZY_FIELDS = {"design_docs", "plans"}
    if item:
        masked = _mask_projects([item])[0] if not _is_admin(request) else item
        slim = {k: v for k, v in masked.items() if k not in _LAZY_FIELDS}
        inline_data = _json.dumps(slim, default=str)
    else:
        inline_data = "null"
    return HTMLResponse(render_detail_page(project_id, name, inline_data), headers=_NC)

@api.get("/projects/{project_id}/overview", response_class=HTMLResponse)
def project_overview_page(project_id: str, embed: bool = False):
    from vibe.overview_page import render_overview_page
    from vibe.models import ProjectInfo

    # Check for hand-crafted page first (no cache needed)
    projects = get_all_projects()
    item = next((p for p in projects if p.get("id") == project_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    path = Path(item["path"])
    hand_crafted = path / "design-preview" / "system-overview.html"
    if hand_crafted.exists():
        return HTMLResponse(hand_crafted.read_text(encoding="utf-8"))

    # Reuse cached collect_project data — no re-collection needed
    info = ProjectInfo(**item)
    return HTMLResponse(render_overview_page(info, embed=embed), headers=_NC)

@api.post("/api/refresh")
def refresh_all(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return get_all_projects(force=True)

@api.get("/api/projects/{project_id}/design-docs")
def list_design_docs(request: Request, project_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p.get("design_docs", [])
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/design-docs/{filename}")
def get_design_doc(request: Request, project_id: str, filename: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            for doc in p.get("design_docs", []):
                if doc["filename"] == filename:
                    return doc
            raise HTTPException(status_code=404, detail="Design doc not found")
    raise HTTPException(status_code=404, detail="Project not found")


@api.get("/api/projects/{project_id}/prompts")
def get_project_prompts(request: Request, project_id: str):
    """Return user prompts for a project from the session index DB."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.history_db import get_prompts
    return get_prompts(project_id)


@api.get("/api/prompts")
def get_all_prompts(request: Request):
    """Return user prompts grouped by project from the session index DB."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.history_db import get_all_project_prompts
    return {"projects": get_all_project_prompts()}


@api.get("/api/trending")
def github_trending(period: str = "weekly"):
    """Proxy GitHub search API to avoid browser CORS issues."""
    import urllib.request, json as _json, urllib.error
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 7)
    from datetime import datetime, timedelta
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"https://api.github.com/search/repositories?q=created:>{since}&sort=stars&order=desc&per_page=12"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "vibe-manager"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = _json.loads(r.read())
        return data.get("items", [])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@api.delete("/api/projects/{project_id}")
def delete_project(request: Request, project_id: str):
    """Hide a project from discovery by adding it to excluded_paths."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.config import exclude_project
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            exclude_project(p["path"])
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Project not found")


def _write_project_status(path: str, status: str):
    """Write status field to project's vibe.yaml (creates if missing)."""
    import yaml as _yaml
    vibe_path = Path(path) / "vibe.yaml"
    if vibe_path.exists():
        data = _yaml.safe_load(vibe_path.read_text()) or {}
    else:
        data = {}
    data["status"] = status
    vibe_path.write_text(
        _yaml.dump(data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


@api.patch("/api/projects/{project_id}/status")
def set_project_status(request: Request, project_id: str, body: dict):
    """Change project status and persist to vibe.yaml."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    status = body.get("status")
    if status not in ("active", "paused", "done", "trash"):
        raise HTTPException(status_code=400, detail="invalid status")
    with _cache_lock:
        for p in _cache:
            if p["id"] == project_id:
                _write_project_status(p["path"], status)
                p["status"] = status  # update in-memory cache
                return {"status": "ok", "new_status": status}
    raise HTTPException(status_code=404, detail="Project not found")


@api.post("/api/projects/{project_id}/summarize")
def summarize_project_endpoint(request: Request, project_id: str, force: bool = False):
    """Generate and write AI summary for a single project."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.summarizer import summarize_project
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            ok, msg = summarize_project(p, force=force)
            if ok:
                # Re-collect to include fresh summary
                from vibe.aggregator import collect_project
                from pathlib import Path as _Path
                refreshed = collect_project(_Path(p["path"]), p["name"], None)
                return {"status": "ok", "project": refreshed.model_dump()}
            raise HTTPException(status_code=500, detail=msg)
    raise HTTPException(status_code=404, detail="Project not found")


def _check_port(port: int, host: str = "127.0.0.1") -> bool:
    import socket
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _check_process(name: str) -> bool:
    """Return True if any running process matches the given name."""
    import psutil
    name_lower = name.lower()
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if name_lower in (proc.info.get('name') or '').lower():
                return True
            cmdline = proc.info.get('cmdline') or []
            if any(name_lower in (arg or '').lower() for arg in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def _parse_ngrok_tunnels() -> dict[int, str]:
    """Returns {local_port: public_url} from ngrok local API."""
    import re, urllib.request, json as _json
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1) as r:
            data = _json.loads(r.read())
        result = {}
        for t in data.get("tunnels", []):
            public = t.get("public_url", "")
            addr = t.get("config", {}).get("addr", "")
            m = re.search(r":(\d+)$", addr)
            if public and m:
                result[int(m.group(1))] = public.removeprefix("https://").removeprefix("http://")
        return result
    except Exception:
        return {}


def _parse_cloudflared_tunnels() -> dict[int, str]:
    """Returns {local_port: public_hostname} from ~/.cloudflared/config.yml."""
    import yaml as _yaml
    import re
    cfg_path = Path.home() / ".cloudflared" / "config.yml"
    if not cfg_path.exists():
        return {}
    try:
        data = _yaml.safe_load(cfg_path.read_text()) or {}
        result = {}
        for rule in data.get("ingress", []):
            hostname = rule.get("hostname", "")
            service = rule.get("service", "")
            if hostname and service:
                m = re.search(r":(\d+)$", service)
                if m:
                    result[int(m.group(1))] = hostname
        return result
    except Exception:
        return {}


def _detect_used_by(port: int, projects: list[dict]) -> list[str]:
    """Scan project files to find which projects reference this port."""
    import re
    port_str = str(port)
    found = []
    scan_patterns = ["**/.env", "**/vibe.yaml", "**/.env.example",
                     "**/config.py", "**/settings.py", "**/docker-compose.yml"]
    for p in projects:
        proj_path = Path(p.get("path", ""))
        if not proj_path.exists():
            continue
        matched = False
        for pattern in scan_patterns:
            if matched:
                break
            for f in proj_path.glob(pattern):
                if matched:
                    break
                # skip .venv and node_modules
                if any(part in f.parts for part in (".venv", "node_modules", "__pycache__")):
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    if re.search(rf'\b{port_str}\b', text):
                        matched = True
                except OSError:
                    pass
        if matched:
            found.append(p["id"])
    return found


@api.get("/api/base-services")
def list_base_services():
    """Check status of host-level infrastructure services defined in vibe.yaml."""
    from vibe.config import load_global_config
    cfg = load_global_config()
    services = cfg.get("base_services") or []
    tunnels = {**_parse_ngrok_tunnels(), **_parse_cloudflared_tunnels()}  # ngrok + cloudflared, cloudflared wins
    projects = get_all_projects()                   # for used_by detection

    result = []
    for svc in services:
        port = svc.get("port")
        process = svc.get("process")
        is_running = (_check_port(port) if port else False) or (_check_process(process) if process else False)
        # used_by: config takes priority, fallback to auto-scan
        used_by = svc.get("used_by") or []
        if not used_by and port:
            used_by = _detect_used_by(port, projects)
        # For ngrok (management port 4040), show all active tunnel URLs
        public_url = tunnels.get(port)
        extra_tunnels: list[str] = []
        if port == 4040 and is_running:
            ngrok_map = _parse_ngrok_tunnels()  # {local_port: public_host}
            extra_tunnels = [f":{k} → {v}" for k, v in ngrok_map.items()]
            if not public_url and ngrok_map:
                public_url = next(iter(ngrok_map.values()))

        result.append({
            "name": svc.get("name", ""),
            "port": port,
            "type": svc.get("type", "other"),
            "desc": svc.get("desc", ""),
            "is_running": is_running,
            "used_by": used_by,
            "public_url": public_url,
            "extra_tunnels": extra_tunnels,
        })
    return result


def _check_service_statuses() -> dict:
    """Lightweight port check for all discovered projects. Returns {project_id: {is_running, port}}."""
    import psutil
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.collectors.service import collect_service

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    result = {}
    for item in discovered:
        p = Path(item["path"])
        try:
            svc = collect_service(p, item["vibe_config"])
            result[p.name] = {"is_running": svc.is_running, "port": svc.port,
                               "process_name": svc.process_name, "domain_ok": svc.domain_ok}
        except Exception:
            result[p.name] = {"is_running": False, "port": None, "process_name": None}
    return result


@api.get("/healthz")
def healthz():
    return {"status": "ok", "token": "mira-ok"}


@api.get("/api/balance")
def get_balance(request: Request, force: bool = False):
    from .balance import fetch_all_balances
    from .config import load_global_config
    providers = fetch_all_balances(load_global_config(), force=force)
    if _is_admin(request):
        return {"providers": providers}
    # Non-admin: keep structure, null out money fields
    _MONEY_FIELDS = {"balance", "used", "topped", "granted", "limit", "total"}
    masked = [{**p, **{f: None for f in _MONEY_FIELDS if f in p}, "_masked": True} for p in providers]
    return {"providers": masked}


@api.get("/api/balance/activity")
def get_balance_activity(request: Request, force: bool = False):
    from .balance import fetch_openrouter_activity
    from .config import load_global_config
    data = fetch_openrouter_activity(load_global_config(), force=force)
    if _is_admin(request):
        return {"openrouter": data}
    # Non-admin: keep dates, zero amounts
    masked = [{"date": r["date"], "cost_usd": 0} for r in (data or [])]
    return {"openrouter": masked or None, "_masked": True}


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@api.post("/api/auth/login")
def auth_login(body: dict):
    from vibe.config import load_global_config
    password = (load_global_config().get("admin_password") or "").strip()
    if not password:
        return {"ok": True, "token": "no-auth"}
    if (body.get("password") or "").strip() != password:
        raise HTTPException(status_code=401, detail="密码错误")
    return {"ok": True, "token": hashlib.sha256(password.encode()).hexdigest()}


@api.get("/api/auth/check")
def auth_check(request: Request):
    token = _admin_token()
    return {"admin": _is_admin(request), "auth_required": token is not None}


# ── Settings (API keys stored in vibe.yaml) ────────────────────────────────────
_SETTINGS_KEYS = ["openrouter_api_key", "deepseek_api_key", "kimi_api_key"]

@api.get("/api/settings")
def get_settings(request: Request):
    from .config import load_global_config
    cfg = load_global_config()
    result = {}
    for k in _SETTINGS_KEYS:
        v = cfg.get(k) or ""
        if _is_admin(request):
            result[k] = (v[:8] + "****") if len(v) > 8 else ("****" if v else "")
        else:
            result[k] = "****" if v else ""
    # admin_password: always fully masked regardless of admin status
    result["admin_password"] = "****" if cfg.get("admin_password") else ""
    result["notification_sound"] = cfg.get("notification_sound", "Pop")
    return result

@api.post("/api/settings")
def save_settings(request: Request, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).parent.parent / "vibe.yaml"
    data = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
    for k in _SETTINGS_KEYS:
        if k in body:
            v = (body[k] or "").strip()
            if v and not v.endswith("****"):   # real value → save
                data[k] = v
            elif v == "":   # empty → delete key
                data.pop(k, None)
    # admin_password: save if provided and not placeholder
    if "admin_password" in body:
        v = (body["admin_password"] or "").strip()
        if v and v != "****":
            data["admin_password"] = v
    # notification_sound
    if "notification_sound" in body:
        v = (body["notification_sound"] or "").strip()
        if v:
            data["notification_sound"] = v
    cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    # invalidate balance cache with fresh config
    from .balance import fetch_all_balances
    from .config import load_global_config
    fetch_all_balances(load_global_config(), force=True)
    return {"ok": True}

@api.get("/api/sounds")
def list_sounds():
    """返回可用的系统提示音列表。"""
    sounds_dir = Path("/System/Library/Sounds")
    names = sorted(f.stem for f in sounds_dir.glob("*.aiff")) if sounds_dir.exists() else []
    if not names:
        names = ["Pop", "Glass", "Ping", "Purr", "Tink", "Hero", "Submarine"]
    return {"sounds": names}

@api.get("/api/sounds/{name}")
def get_sound(name: str):
    """提供系统音效文件。"""
    sound_file = Path(f"/System/Library/Sounds/{name}.aiff")
    if not sound_file.exists():
        raise HTTPException(status_code=404, detail="Sound not found")
    return FileResponse(sound_file, media_type="audio/aiff")

@api.get("/api/llm-providers")
def get_llm_providers():
    """聚合所有项目检测到的 LLM provider 列表（去重）。"""
    projects = get_all_projects()
    providers: set[str] = set()
    for p in projects:
        for api_name in p.get("llm_apis", []):
            providers.add(api_name)
    return {"providers": sorted(providers)}


# ── History / Session Warehouse ────────────────────────────────────────────────

@api.get("/api/history/search")
def history_search(request: Request, q: str = "", limit: int = 20):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    if not q.strip():
        return []
    from vibe.history_db import search
    return search(q.strip(), limit=limit)


@api.get("/api/history/sessions")
def history_sessions(request: Request, project_id: str = ""):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.history_db import get_sessions
    return get_sessions(project_id)


@api.get("/api/stats")
def stats_view(request: Request, range: str = "30d"):  # noqa: A002
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")

    # Parse range param: "30d" → 30 days, "2w" → 14 days
    range_str = range
    _is_weekly = range_str.endswith("w")
    try:
        n = int(range_str.rstrip("dw"))
        if n <= 0:
            raise ValueError("non-positive")
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 range 格式，请使用如 '30d' 或 '4w'")
    if _is_weekly:
        n = max(1, min(n, 52))   # 52 weeks = 364 days, always full 7-day buckets
        range_days = n * 7
    else:
        range_days = max(7, min(n, 365))

    from vibe.history_db import get_stats
    data = get_stats(range_days=range_days)

    if _is_weekly:
        # Collapse daily → weekly buckets (7 days each)
        weeks = []
        chunk_days = data["days"]
        i = 0
        while i < len(chunk_days):
            chunk = chunk_days[i:i + 7]
            i += 7
            if not chunk:
                break
            weeks.append({
                "date":          chunk[-1]["date"],
                "sessions":      sum(d["sessions"]      for d in chunk),
                "messages":      sum(d["messages"]      for d in chunk),
                "input_tokens":  sum(d["input_tokens"]  for d in chunk),
                "output_tokens": sum(d["output_tokens"] for d in chunk),
                "active_hours":  round(sum(d["active_hours"] for d in chunk), 2),
            })
        data["days"] = weeks

    return data


# ── Terminal Bridge ────────────────────────────────────────────────────────────

@api.get("/api/terminals")
def terminals_list(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.terminal_monitor import get_panes
    return get_panes()


@api.get("/api/dev/panes")
def dev_panes_list(request: Request):
    """Return ALL tmux panes for the Dev mode panel (not filtered by command)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import list_panes
    from vibe.terminal_monitor import get_panes
    monitored = {p["target"]: p for p in get_panes()}
    # Build a lookup so we can return each project's display name (vibe.yaml `name`)
    projects = get_all_projects()
    proj_by_path = {pr["path"]: pr for pr in projects}
    all_panes = list_panes()
    result = []
    for p in all_panes:
        target = p["target"]
        mon = monitored.get(target, {})
        label = mon.get("label") or f"{p['command']}/{Path(p['cwd']).name}"
        # Match cwd to a project by longest-path-prefix
        match = None
        cwd = p["cwd"]
        for path, proj in proj_by_path.items():
            if cwd == path or cwd.startswith(path + "/"):
                if match is None or len(path) > len(match["path"]):
                    match = proj
        project_id = mon.get("project_id") or (Path(match["path"]).name if match else Path(cwd).name)
        project_name = (match["name"] if match else None) or project_id
        result.append({
            "target": target,
            "label": label,
            "command": p["command"],
            "cwd": p["cwd"],
            "waiting": mon.get("waiting", False),
            "project_id": project_id,
            "project_name": project_name,
        })
    return result


@api.delete("/api/dev/panes/{target:path}")
def dev_kill_pane(request: Request, target: str):
    """Kill a tmux pane (target = session:window.pane). Removes it from
    the live tmux server, which propagates to /dev sidebar (auto-refresh)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    import subprocess
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    from vibe.terminal_monitor import unregister_pane
    proc = subprocess.run(
        [_TMUX_BIN, "kill-pane", "-t", target],
        capture_output=True, text=True, env=_TMUX_ENV,
    )
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"tmux kill-pane failed: {proc.stderr.strip()}")
    unregister_pane(target)
    return {"ok": True, "target": target}


@api.post("/api/projects/{project_id}/name")
def update_project_name(project_id: str, request: Request, body: dict):
    """Rename a project — writes `name:` into project's vibe.yaml.

    Creates vibe.yaml if it doesn't exist. Invalidates project cache so
    the new name is picked up on next /api/projects request.
    """
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    new_name = (body.get("name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="name required")
    projects = get_all_projects()
    proj = next((p for p in projects if p.get("id") == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="project not found")
    import yaml
    yaml_path = Path(proj["path"]) / "vibe.yaml"
    cfg = {}
    if yaml_path.exists():
        try:
            with open(yaml_path) as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            cfg = {}
    cfg["name"] = new_name
    with open(yaml_path, "w") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    # In-place patch the cache so the next request sees the new name
    # immediately (rebuild would take 10-30s and block the API). Kick off
    # a background full rebuild for any other fields that might depend
    # on vibe.yaml.
    with _cache_lock:
        if _cache:
            for cp in _cache:
                if cp.get("id") == project_id:
                    cp["name"] = new_name
                    break
    threading.Thread(target=_rebuild_and_persist, daemon=True).start()
    return {"ok": True, "name": new_name}


@api.get("/api/terminals/alerts")
def terminals_alerts(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.terminal_monitor import get_terminal_alerts
    return get_terminal_alerts()


@api.post("/api/terminals/register")
def terminals_register(request: Request, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    target = (body.get("target") or "").strip()
    label = (body.get("label") or target).strip()
    project_id = (body.get("project_id") or "").strip() or None
    if not target:
        raise HTTPException(status_code=400, detail="target required")
    from vibe.terminal_monitor import register_pane
    register_pane(target, label, project_id=project_id)
    return {"ok": True}


@api.delete("/api/terminals/{target:path}")
def terminals_unregister(request: Request, target: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.terminal_monitor import unregister_pane
    unregister_pane(target)
    return {"ok": True}


@api.get("/api/terminals/{target:path}/output")
def terminals_output(request: Request, target: str, lines: int = 200):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import capture_pane
    try:
        text = capture_pane(target, lines=lines)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"target": target, "output": text}


_UPLOAD_DIR = Path("/tmp/mira-uploads")

@api.post("/api/upload/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    ct = file.content_type or ""
    if not ct.startswith("image/"):
        raise HTTPException(status_code=400, detail="只接受图片文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="图片太大（最大 20MB）")
    import uuid, mimetypes
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "img").suffix or (mimetypes.guess_extension(ct) or ".png")
    dest = _UPLOAD_DIR / f"{uuid.uuid4().hex[:10]}{ext}"
    dest.write_bytes(content)
    return {"path": str(dest)}


@api.post("/api/terminals/{target:path}/send")
def terminals_send(request: Request, target: str, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    keys = body.get("keys", "")
    if not keys:
        raise HTTPException(status_code=400, detail="keys required")
    if len(keys) > 4096:
        raise HTTPException(status_code=400, detail="keys too long (max 4096 chars)")
    from vibe.tmux_bridge import send_keys
    try:
        send_keys(target, keys)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@api.get("/api/alerts")
def get_alerts():
    with _alerts_lock:
        current = list(_alerts)
        _alerts.clear()
    return {"alerts": current}


@api.post("/api/chat")
async def chat_endpoint(request: Request, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    import json as _json
    import urllib.request as _ureq
    import asyncio as _asyncio

    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    async def generate():
        projects = await _asyncio.to_thread(get_all_projects)
        system_prompt = _build_system_prompt(projects)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        # Tool calling loop (non-streaming, max 5 rounds)
        for _ in range(5):
            payload = _json.dumps({
                "model": _AGENT_MODEL,
                "messages": messages,
                "tools": [_SHELL_TOOL, _READ_TERMINAL_TOOL, _SEND_TERMINAL_TOOL],
                "stream": False,
            }).encode()
            try:
                req = _ureq.Request(
                    "http://localhost:11434/api/chat",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                result = await _asyncio.to_thread(
                    lambda: _json.loads(_ureq.urlopen(req, timeout=120).read())
                )
            except Exception as e:
                yield f"data: {_json.dumps({'type': 'error', 'content': f'无法连接到本地模型：{e}'})}\n\n"
                return

            msg = result.get("message", {})
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                # Stream final response word by word
                text = msg.get("content", "（无回复）")
                words = text.split(" ")
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {_json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    await _asyncio.sleep(0.015)
                yield f"data: {_json.dumps({'type': 'done'})}\n\n"
                return

            # Execute tools
            messages.append({
                "role": "assistant",
                "content": msg.get("content", ""),
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:
                fn = tc.get("function", {})
                if fn.get("name") == "run_shell":
                    args = fn.get("arguments", {})
                    cmd = args.get("command", "")
                    cwd = args.get("working_dir", "~")
                    output = await _asyncio.to_thread(_run_shell, cmd, cwd)
                    yield f"data: {_json.dumps({'type': 'tool_exec', 'command': cmd, 'output': output})}\n\n"
                    messages.append({"role": "tool", "content": output, "tool_call_id": tc.get("id", "")})
                elif fn.get("name") == "read_terminal":
                    args = fn.get("arguments", {})
                    t_target = args.get("target", "")
                    try:
                        t_lines = max(1, int(args.get("lines", 50)))
                    except (ValueError, TypeError):
                        t_lines = 50
                    try:
                        from vibe.tmux_bridge import capture_pane
                        output = await _asyncio.to_thread(capture_pane, t_target, t_lines)
                    except RuntimeError as e:
                        output = f"[错误] {e}"
                    yield f"data: {_json.dumps({'type': 'tool_exec', 'command': f'read_terminal {t_target}', 'output': output})}\n\n"
                    messages.append({"role": "tool", "content": output, "tool_call_id": tc.get("id", "")})
                elif fn.get("name") == "send_to_terminal":
                    args = fn.get("arguments", {})
                    t_target = args.get("target", "")
                    t_keys = args.get("keys", "")
                    if len(t_keys) > 4096:
                        t_keys = t_keys[:4096]  # silently truncate for agent calls
                    if not t_target or not t_keys:
                        output = "[错误] target 和 keys 均为必填项"
                        yield f"data: {_json.dumps({'type': 'tool_exec', 'command': 'send_to_terminal', 'output': output})}\n\n"
                        messages.append({"role": "tool", "content": output, "tool_call_id": tc.get("id", "")})
                    else:
                        try:
                            from vibe.tmux_bridge import send_keys
                            await _asyncio.to_thread(send_keys, t_target, t_keys)
                            output = f"[已发送] {repr(t_keys)} → {t_target}"
                        except RuntimeError as e:
                            output = f"[错误] {e}"
                        yield f"data: {_json.dumps({'type': 'tool_exec', 'command': f'send_to_terminal {t_target}', 'output': output})}\n\n"
                        messages.append({"role": "tool", "content": output, "tool_call_id": tc.get("id", "")})
                else:
                    messages.append({"role": "tool", "content": f"[未知工具：{fn.get('name')}]", "tool_call_id": tc.get("id", "")})

        yield f"data: {_json.dumps({'type': 'error', 'content': '工具调用轮次超限'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api.websocket("/ws/status")
async def ws_service_status(websocket: WebSocket):
    """Push service status every 30s. Sends full snapshot on connect, then diffs."""
    await websocket.accept()
    prev: dict = {}
    try:
        while True:
            current = await asyncio.get_event_loop().run_in_executor(None, _check_service_statuses)
            # Compute changes
            changes = {k: v for k, v in current.items()
                       if k not in prev or prev[k]["is_running"] != v["is_running"]}
            payload = {"snapshot": current, "changes": changes}
            await websocket.send_json(payload)
            prev = current
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── ttyd HTTP proxy ─────────────────────────────────────────────────────────────

@api.api_route("/terminal/{path:path}", methods=["GET", "POST", "HEAD"])
async def ttyd_http_proxy(path: str, request: Request):
    """Proxy HTTP requests (HTML/JS/CSS assets) to the ttyd process.

    No admin check here — ttyd is bound to 127.0.0.1 and unreachable
    from outside. The security boundary is Mira's login page.
    """
    import httpx
    url = f"http://127.0.0.1:{_TTYD_PORT}/terminal/{path}"
    params = str(request.url.query)
    if params:
        url += "?" + params
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "connection")},
                content=await request.body(),
                timeout=10,
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="ttyd 未运行")
    # Strip hop-by-hop and encoding headers (httpx decompresses; don't re-claim gzip)
    skip = {"transfer-encoding", "connection", "keep-alive", "content-encoding", "content-length"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
    return Response(content=resp.content, status_code=resp.status_code, headers=headers)


@api.websocket("/terminal/ws")
async def ttyd_ws_proxy(websocket: WebSocket):
    """Proxy WebSocket connection to ttyd.

    Forwards admin:<admin_password> as basic auth to ttyd (which requires it
    when --credential is set). Security boundary remains Mira login + ttyd auth.
    """
    import websockets as _ws
    import base64
    from vibe.config import load_global_config

    # 鉴权：WebSocket 无法用自定义 header，通过 query param 传 token
    token = _admin_token()
    if token is not None:
        client_token = websocket.query_params.get("token", "")
        if client_token != token:
            await websocket.close(code=4001, reason="Unauthorized")
            return

    await websocket.accept(subprotocol="tty")
    ttyd_url = f"ws://127.0.0.1:{_TTYD_PORT}/terminal/ws"

    pwd = (load_global_config().get("admin_password") or "").strip()
    extra_headers = []
    if pwd:
        token = base64.b64encode(f"admin:{pwd}".encode()).decode()
        extra_headers = [("Authorization", f"Basic {token}")]

    try:
        async with _ws.connect(
            ttyd_url, subprotocols=["tty"],
            additional_headers=extra_headers,
        ) as ttyd_ws:
            async def browser_to_ttyd():
                try:
                    async for msg in websocket.iter_bytes():
                        await ttyd_ws.send(msg)
                except Exception:
                    pass

            async def ttyd_to_browser():
                try:
                    async for msg in ttyd_ws:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                except Exception:
                    pass

            await asyncio.gather(browser_to_ttyd(), ttyd_to_browser())
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── Terminal focus / new-window API ────────────────────────────────────────────

@api.post("/api/terminal/focus")
async def terminal_focus(request: Request, body: dict):
    """Switch tmux client view to a specific pane (used by sidebar click)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    target = (body.get("target") or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="target required")
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    import re
    # target format: session:window.pane  e.g. "mira:0.1"
    m = re.match(r'^(.+):(\d+)\.(\d+)$', target)
    if not m:
        raise HTTPException(status_code=400, detail="invalid target format")
    session, window, _pane = m.group(1), m.group(2), m.group(3)
    # Switch the tmux session's active window, then select the pane
    subprocess.run([_TMUX_BIN, "switch-client", "-t", f"{session}:{window}"],
                   env=_TMUX_ENV, capture_output=True)
    subprocess.run([_TMUX_BIN, "select-pane", "-t", target],
                   env=_TMUX_ENV, capture_output=True)
    return {"ok": True}


@api.post("/api/terminal/new-window")
async def terminal_new_window(request: Request, body: dict):
    """Create a new tmux window, optionally in a project directory."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    cwd = (body.get("cwd") or "").strip() or None
    cmd = [_TMUX_BIN, "new-window", "-t", "mira"]
    if cwd:
        cmd += ["-c", cwd]
    result = subprocess.run(cmd, env=_TMUX_ENV, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip())
    return {"ok": True}


@api.get("/api/terminal/buffer")
async def terminal_buffer(request: Request):
    """Return tmux paste buffer (last copied text from copy-mode)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    result = subprocess.run(
        [_TMUX_BIN, "show-buffer"],
        env=_TMUX_ENV, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return {"text": ""}
    return {"text": result.stdout}


@cli.callback()
def main():
    """Vibe Manager — project dashboard CLI."""

@cli.command("summarize")
def summarize_cmd(
    force: bool = typer.Option(False, "--force", help="Re-generate even if summary exists"),
):
    """Generate AI summaries for all discovered projects and write docs/vibe-summary.md."""
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.aggregator import collect_project
    from vibe.summarizer import summarize_project

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    typer.echo(f"Found {len(discovered)} projects. Generating summaries...\n")

    for item in discovered:
        path = Path(item["path"])
        name = item["name"]
        try:
            info = collect_project(path, name=name, vibe_cfg=item["vibe_config"])
            ok, msg = summarize_project(info.model_dump(), force=force)
            icon = "✓" if ok else ("⟳" if "skipped" in msg else "✗")
            typer.echo(f"  {icon}  {name}: {msg}")
        except Exception as e:
            typer.echo(f"  ✗  {name}: error — {e}")

    typer.echo("\nDone.")


@cli.command("term")
def term_cmd(
    project: str = typer.Argument(..., help="项目名（目录名），如 kohl"),
    cmd: str = typer.Option("ccc", "--cmd", "-c", help="在终端里运行的命令，默认 ccc"),
    host: str = typer.Option("http://127.0.0.1:8888", "--host", help="mira 地址"),
    password: str = typer.Option("", "--password", "-p", help="mira admin 密码（可省略，从 vibe.yaml 读取）"),
):
    """在 tmux 里为指定项目启动终端会话，并注册到 mira。

    示例：vibe term kohl
          vibe term kohl --cmd "npm run dev"
    """
    import hashlib, os, subprocess, time, urllib.request, urllib.error, json as _json

    from vibe.config import load_global_config
    from vibe.scanner import discover_projects

    cfg = load_global_config()
    pw = password or (cfg.get("admin_password") or "")
    if not pw:
        typer.echo("错误：需要 admin 密码（--password 或 vibe.yaml admin_password）", err=True)
        raise typer.Exit(1)
    token = hashlib.sha256(pw.encode()).hexdigest()

    # Resolve project path
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    item = next((i for i in discovered if Path(i["path"]).name == project), None)
    if not item:
        typer.echo(f"错误：找不到项目 '{project}'", err=True)
        raise typer.Exit(1)
    project_path = item["path"]

    # Create or reuse tmux session
    session = project
    existing = subprocess.run(["tmux", "has-session", "-t", session],
                               capture_output=True).returncode == 0
    if existing:
        typer.echo(f"tmux session '{session}' 已存在，复用")
    else:
        # Create detached, send command, then we'll attach below
        subprocess.run(["tmux", "new-session", "-d", "-s", session, "-c", project_path], check=True)
        subprocess.run(["tmux", "send-keys", "-t", f"{session}:0.0", cmd, "Enter"])
        time.sleep(0.5)

    # Detect pane target
    target = f"{session}:0.0"

    # Register with mira
    payload = _json.dumps({"target": target, "label": f"{project} · {cmd}", "project_id": project}).encode()
    req = urllib.request.Request(
        f"{host}/api/terminals/register",
        data=payload,
        headers={"Content-Type": "application/json", "X-Admin-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = _json.loads(resp.read())
        if result.get("ok"):
            typer.echo(f"已注册到 mira：{target} → 项目 {project}")
        else:
            typer.echo(f"注册失败：{result}", err=True)
    except urllib.error.URLError as e:
        typer.echo(f"无法连接到 mira ({host})：{e}", err=True)
        raise typer.Exit(1)

    # Attach to the session — replaces current process so Termius shows the terminal
    os.execvp("tmux", ["tmux", "attach", "-t", session])


@cli.command("serve")
def serve(
    port: int = typer.Option(None, help="Port to listen on (default: from vibe.yaml or 8888)"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on file changes"),
):
    """Start the Vibe Manager web server."""
    from vibe.config import load_global_config
    cfg = load_global_config()
    actual_port = port if port is not None else cfg.get("port", 8888)
    typer.echo(f"Vibe Manager running at http://{host}:{actual_port}" + (" (reload)" if reload else ""))
    uvicorn.run("vibe.main:api", host=host, port=actual_port, reload=reload)

app = cli

if __name__ == "__main__":
    cli()
