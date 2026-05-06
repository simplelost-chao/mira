import asyncio
import hashlib
import hmac
import ipaddress
import re
import shutil
import subprocess
import typer
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from urllib.parse import urlparse

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


def _migrate_remote_passwords() -> None:
    """自动将 remote_hosts 中的明文密码迁移为 hash 存储。"""
    import yaml
    cfg_path = Path(__file__).parent.parent / "vibe.yaml"
    if not cfg_path.exists():
        return
    data = yaml.safe_load(cfg_path.read_text()) or {}
    hosts = data.get("remote_hosts", [])
    migrated = False
    for entry in hosts:
        pw = (entry.get("admin_password") or "").strip()
        if pw and not entry.get("admin_password_hash"):
            entry["admin_password_hash"] = hashlib.sha256(pw.encode()).hexdigest()
            del entry["admin_password"]
            migrated = True
    if migrated:
        data["remote_hosts"] = hosts
        cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))

def _init_remote_hosts() -> None:
    """从配置中初始化远程主机列表。"""
    _migrate_remote_passwords()
    from vibe.config import load_global_config
    cfg = load_global_config()
    for entry in cfg.get("remote_hosts", []):
        host = _RemoteHost.from_config(entry)
        if host:
            _remote_hosts.append(host)


def _remote_refresh_loop() -> None:
    """定期拉取远程主机项目和 pane 列表（300s 间隔）。"""
    _INTERVAL = 300

    async def _poll_once():
        for host in _remote_hosts:
            try:
                projects = await host.fetch_projects()
                _remote_cache[host.alias] = projects
                panes = await host.fetch_panes()
                _remote_panes_cache[host.alias] = panes
            except Exception as e:
                import logging as _rlog
                _rlog.getLogger(__name__).warning("remote poll failed for %s: %s", host.alias, e)

    import asyncio as _aio
    import logging as _rlog
    _logger = _rlog.getLogger(__name__)
    loop = _aio.new_event_loop()
    _aio.set_event_loop(loop)
    try:
        loop.run_until_complete(_poll_once())
    except Exception as e:
        _logger.warning("remote refresh initial poll failed: %s", e)

    while True:
        time.sleep(_INTERVAL)
        try:
            loop.run_until_complete(_poll_once())
        except Exception as e:
            _logger.warning("remote refresh poll failed: %s", e)


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
    from vibe.session_indexer import run_indexer, backfill_cache_tokens
    history_init_db()
    threading.Thread(target=backfill_cache_tokens, daemon=True, name='mira-backfill').start()
    threading.Thread(target=run_indexer, daemon=True).start()
    from vibe.terminal_monitor import run_monitor
    threading.Thread(target=run_monitor, daemon=True).start()
    threading.Thread(target=_monitor_base_services_loop, daemon=True, name='mira-svc-monitor').start()
    _start_ttyd()
    threading.Thread(target=_watch_ttyd, daemon=True).start()
    # 远程主机
    _init_remote_hosts()
    if _remote_hosts:
        threading.Thread(target=_remote_refresh_loop, daemon=True).start()
    yield
    if _ttyd_proc:
        _ttyd_proc.terminate()

api = FastAPI(title="Vibe Manager", lifespan=_lifespan)

STATIC_DIR = Path(__file__).parent.parent / "static"
VERSION_FILE = Path(__file__).parent.parent / "version.json"

import json as _json

def _read_version() -> str:
    try:
        return _json.loads(VERSION_FILE.read_text()).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


@api.get("/api/version")
def get_version():
    return {"version": _read_version()}

if STATIC_DIR.exists():
    api.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @api.get("/", response_class=FileResponse)
    def index():
        return FileResponse(str(STATIC_DIR / "index.html"),
                            headers={"Cache-Control": "no-cache"})

    @api.get("/favicon.ico", response_class=FileResponse)
    def favicon():
        return FileResponse(str(STATIC_DIR / "favicon.svg"),
                            media_type="image/svg+xml",
                            headers={"Cache-Control": "public, max-age=86400"})

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

# ── Base-service monitor ───────────────────────────────────────────────────────
_base_svc_state: dict[str, bool] = {}   # name → last known is_running

# ── Remote hosts ──────────────────────────────────────────────────────────────
from vibe.remote_client import RemoteHost as _RemoteHost

_remote_hosts: list[_RemoteHost] = []
_remote_cache: dict[str, list[dict]] = {}  # alias -> projects
_remote_panes_cache: dict[str, list[dict]] = {}  # alias -> panes

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
    req_token = request.headers.get("X-Admin-Token") or ""
    return hmac.compare_digest(req_token, token)


_BLOCKED_PATTERNS = [
    "rm ", "rmdir", "mv ", "cp ", "> /", ">> /",
    "mkfs", "dd if=", ":(){ ", "sudo ", "chmod ", "chown ",
    "curl | ", "wget | ", "curl|", "wget|", "|bash", "|sh",
    "eval ", "exec ", "shutdown", "reboot", "halt", "kill -9",
    "DROP TABLE", "DELETE FROM",
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
    stripped = command.strip().lower()
    # Block dangerous patterns
    for pattern in _BLOCKED_PATTERNS:
        if pattern.lower() in stripped:
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


def _escape_applescript(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _send_os_notification(title: str, body: str, sound: str = "Pop") -> None:
    import subprocess
    try:
        safe_title = _escape_applescript(title)
        safe_body  = _escape_applescript(body)
        safe_sound = _escape_applescript(sound)
        script = (
            f'display notification "{safe_body}" '
            f'with title "{safe_title}" '
            f'sound name "{safe_sound}"'
        )
        subprocess.run(["osascript", "-e", script], timeout=5, capture_output=True)
    except Exception:
        pass


def _auto_restart(name: str, cmd: str, port: int | None, sound: str) -> None:
    """Execute restart_cmd and notify on result."""
    import subprocess
    from datetime import datetime
    try:
        subprocess.run(cmd, shell=True, timeout=30)
        # Wait up to 15s for the port to come up
        for _ in range(15):
            time.sleep(1)
            if port and _check_port(port):
                ts = datetime.now().strftime("%H:%M")
                with _alerts_lock:
                    _alerts.append(f"[{ts}] {name} 自动重启成功")
                _send_os_notification("Mira 监控 ✅", f"{name} 自动重启成功", sound)
                _base_svc_state[name] = True
                return
        ts = datetime.now().strftime("%H:%M")
        with _alerts_lock:
            _alerts.append(f"[{ts}] {name} 自动重启后端口仍无响应")
        _send_os_notification("Mira 监控 ❌", f"{name} 重启失败，请手动检查", sound)
    except Exception as e:
        _send_os_notification("Mira 监控 ❌", f"{name} 重启出错: {e}", sound)


def _monitor_base_services_loop() -> None:
    """Background thread: check base services every 60s, notify on state change."""
    _MONITOR_INTERVAL = 60
    from datetime import datetime
    from vibe.config import load_global_config
    global _base_svc_state

    # ── Establish baseline (no notifications on first pass) ───────────────────
    try:
        cfg = load_global_config()
        for svc in cfg.get("base_services") or []:
            name = svc.get("name", "")
            port, process = svc.get("port"), svc.get("process")
            up = (_check_port(port) if port else False) or \
                 (_check_process(process) if process else False)
            _base_svc_state[name] = up
    except Exception:
        pass

    while True:
        time.sleep(_MONITOR_INTERVAL)
        try:
            cfg = load_global_config()
            sound = cfg.get("notification_sound", "Pop")
            for svc in cfg.get("base_services") or []:
                name = svc.get("name", "")
                port, process = svc.get("port"), svc.get("process")
                up = (_check_port(port) if port else False) or \
                     (_check_process(process) if process else False)
                prev = _base_svc_state.get(name)
                _base_svc_state[name] = up

                if prev is None or prev == up:
                    continue   # no change

                ts = datetime.now().strftime("%H:%M")
                if not up:   # up → down
                    detail = f"端口 {port} 无响应" if port else "进程已退出"
                    restart_cmd = svc.get("restart_cmd", "").strip()
                    if restart_cmd:
                        msg = f"{name} 服务已停止，正在自动重启…"
                        threading.Thread(
                            target=_auto_restart,
                            args=(name, restart_cmd, port, sound),
                            daemon=True,
                        ).start()
                    else:
                        msg = f"{name} 服务已停止 – {detail}"
                    with _alerts_lock:
                        _alerts.append(f"[{ts}] {msg}")
                    _send_os_notification("Mira 监控 ⚠️", msg, sound)
                else:         # down → up
                    msg = f"{name} 服务已恢复"
                    with _alerts_lock:
                        _alerts.append(f"[{ts}] {msg}")
                    _send_os_notification("Mira 监控 ✅", msg, sound)
        except Exception:
            pass


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
    with ThreadPoolExecutor(max_workers=min(10, len(hostnames))) as pool:
        ip_futs = {pool.submit(_resolve_ip, h): h for h in hostnames}
        for f in as_completed(ip_futs, timeout=8.0):
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
    import logging as _log
    while True:
        time.sleep(_CACHE_TTL)
        try:
            _rebuild_and_persist()
        except Exception as e:
            _log.getLogger(__name__).warning("background refresh failed: %s", e)


def _get_remote_host(alias: str) -> _RemoteHost | None:
    """按 alias 查找远程主机。"""
    for h in _remote_hosts:
        if h.alias == alias:
            return h
    return None


def _tagged_remote_projects() -> list[dict]:
    """返回所有远程项目，ID 加前缀、注入 _host 字段。"""
    result: list[dict] = []
    for host in _remote_hosts:
        projects = _remote_cache.get(host.alias, host.last_projects)
        for p in projects:
            tagged = {**p}
            tagged["id"] = f"{host.alias}:{p['id']}"
            tagged["_host"] = host.alias
            tagged["_host_url"] = host.url
            tagged["_host_online"] = host.online
            result.append(tagged)
    return result


def get_all_projects_with_remote(force: bool = False) -> list[dict]:
    """本地项目 + 远程项目合并。"""
    local = get_all_projects(force=force)
    remote = _tagged_remote_projects()
    return local + remote


def _mask_projects(projects: list[dict]) -> list[dict]:
    """Remove sensitive cost/token fields and add _masked flag for non-admin responses."""
    import copy
    result = copy.deepcopy(projects)
    _COST_KEYS = {"estimated_cost_usd", "input_tokens", "output_tokens",
                  "cache_read_tokens", "cache_write_tokens", "cache_creation_tokens"}
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
    projects = get_all_projects_with_remote()
    return projects if _is_admin(request) else _mask_projects(projects)

@api.get("/api/projects/{project_id}/refresh")
def refresh_project(request: Request, project_id: str):
    """Force refresh a single project and return updated data."""
    projects = get_all_projects(force=True)
    for p in projects:
        if p["id"] == project_id:
            return p if _is_admin(request) else _mask_projects([p])[0]
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id:path}")
def get_project(request: Request, project_id: str):
    projects = get_all_projects_with_remote()
    for p in projects:
        if p["id"] == project_id:
            return p if _is_admin(request) else _mask_projects([p])[0]
    raise HTTPException(status_code=404, detail="Project not found")

_NC = {"Cache-Control": "no-store, no-cache, must-revalidate"}

@api.get("/stats", response_class=HTMLResponse)
def stats_page_route():
    from vibe.stats_page import render_stats_page
    return HTMLResponse(render_stats_page(), headers=_NC)


@api.get("/dev", response_class=HTMLResponse)
def dev_page_route():
    from vibe.dev_page import render_dev_page
    return HTMLResponse(render_dev_page(), headers=_NC)


@api.get("/new", response_class=HTMLResponse)
def new_project_page(request: Request):
    from vibe.new_project_page import render_new_project_page
    return HTMLResponse(render_new_project_page(), headers=_NC)


@api.post("/api/projects/brainstorm")
def brainstorm_project(request: Request, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    description = (body.get("description") or "").strip()
    model_id = (body.get("model") or "").strip()
    if not description:
        raise HTTPException(status_code=400, detail="description 不能为空")
    if not model_id:
        raise HTTPException(status_code=400, detail="model 不能为空")
    from vibe.ai_brainstorm import call_brainstorm
    from vibe.config import load_global_config
    cfg = load_global_config()
    try:
        candidates = call_brainstorm(description, model_id, cfg)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"candidates": candidates}


@api.post("/api/projects/create")
def create_project_endpoint(request: Request, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    name     = (body.get("name") or "").strip()
    desc     = (body.get("description") or "").strip()
    logo_svg = (body.get("logo_svg") or "").strip()
    port     = body.get("port") or None
    domain   = (body.get("domain") or "").strip() or None
    if not name:
        raise HTTPException(status_code=400, detail="name 不能为空")
    if not desc:
        raise HTTPException(status_code=400, detail="description 不能为空")

    from vibe.ai_brainstorm import create_project
    from vibe.config import load_global_config
    from pathlib import Path
    cfg = load_global_config()
    scan_dirs = [Path(d).expanduser() for d in (cfg.get("scan_dirs") or [])]
    base_dir = next((d for d in scan_dirs if d.is_dir()), None)
    if base_dir is None:
        raise HTTPException(status_code=500, detail="未找到有效的 scan_dirs 目录")

    log_lines = []
    try:
        log_lines.append(f"✓ 创建目录 {base_dir / name.lower()}")
        result = create_project(base_dir, name, desc, logo_svg, port, domain)
        log_lines.append("✓ 写入 vibe.yaml")
        log_lines.append("✓ 写入 logo.svg")
        log_lines.append("✓ 生成 favicon.svg")
        log_lines.append("✓ git init & 初始提交")
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建失败: {e}")

    import threading
    threading.Thread(target=_rebuild_and_persist, daemon=True).start()

    return {"project_id": result["project_id"], "path": result["path"], "log": log_lines}


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
        # 防止 </script> 注入：转义斜杠
        inline_data = _json.dumps(slim, default=str).replace("</", r"<\/")
    else:
        inline_data = "null"
    return HTMLResponse(render_detail_page(project_id, name, inline_data), headers=_NC)

@api.get("/projects/{project_id}/overview", response_class=HTMLResponse)
def project_overview_page(request: Request, project_id: str, embed: bool = False):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
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
def list_base_services(request: Request):
    """Check status of host-level infrastructure services defined in vibe.yaml."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
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
            "has_restart": bool(svc.get("restart_cmd", "").strip()),
        })
    return result


@api.post("/api/base-services/{name}/restart")
async def restart_base_service(name: str, request: Request):
    """Manually trigger restart_cmd for a base service."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.config import load_global_config
    cfg = load_global_config()
    svc = next((s for s in (cfg.get("base_services") or [])
                if s.get("name") == name), None)
    if not svc:
        raise HTTPException(status_code=404, detail=f"未找到服务: {name}")
    cmd = svc.get("restart_cmd", "").strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="该服务未配置 restart_cmd")
    sound = cfg.get("notification_sound", "Pop")
    port = svc.get("port")
    threading.Thread(
        target=_auto_restart, args=(name, cmd, port, sound), daemon=True
    ).start()
    return {"status": "restarting", "name": name}


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


# ── Rate limiter ──────────────────────────────────────────────────────────────
_auth_attempts: dict[str, list[float]] = {}
_auth_lock = threading.Lock()
_AUTH_WINDOW = 60.0  # 秒
_AUTH_MAX = 5  # 每窗口最大尝试次数

def _rate_limit_ok(ip: str) -> bool:
    now = time.time()
    with _auth_lock:
        # 防止 dict 无限增长：超过 1000 个 IP 时清理过期条目
        if len(_auth_attempts) > 1000:
            expired = [k for k, v in _auth_attempts.items() if not v or now - v[-1] > _AUTH_WINDOW]
            for k in expired:
                del _auth_attempts[k]
        attempts = _auth_attempts.get(ip, [])
        attempts = [t for t in attempts if now - t < _AUTH_WINDOW]
        if len(attempts) >= _AUTH_MAX:
            _auth_attempts[ip] = attempts
            return False
        attempts.append(now)
        _auth_attempts[ip] = attempts
        return True

# ── Auth endpoints ─────────────────────────────────────────────────────────────

@api.post("/api/auth/login")
def auth_login(request: Request, body: dict):
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(client_ip):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    from vibe.config import load_global_config
    password = (load_global_config().get("admin_password") or "").strip()
    if not password:
        return {"ok": True, "token": "no-auth"}
    if not hmac.compare_digest((body.get("password") or "").strip(), password):
        raise HTTPException(status_code=401, detail="密码错误")
    return {"ok": True, "token": hashlib.sha256(password.encode()).hexdigest()}


@api.get("/api/auth/check")
def auth_check(request: Request):
    token = _admin_token()
    return {"admin": _is_admin(request), "auth_required": token is not None}


@api.get("/api/hosts")
def list_hosts(request: Request):
    """返回远程主机连接状态列表。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return [h.status_dict() for h in _remote_hosts]


# ── Settings (API keys stored in vibe.yaml) ────────────────────────────────────
_SETTINGS_KEYS = ["openrouter_api_key", "deepseek_api_key", "kimi_api_key", "gemini_api_key", "doubao_api_key", "doubao_access_key", "doubao_secret_key"]

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
    # invalidate config cache so next call re-reads from disk
    from .config import invalidate_config_cache
    invalidate_config_cache()
    # invalidate balance cache with fresh config
    from .balance import fetch_all_balances
    from .config import load_global_config
    fetch_all_balances(load_global_config(), force=True)
    return {"ok": True}

# ── Remote Hosts CRUD ─────────────────────────────────────────────────────────

@api.get("/api/settings/remote-hosts")
def get_remote_hosts(request: Request):
    """列出已配置的远程主机（密码脱敏）。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.config import load_global_config
    cfg = load_global_config()
    hosts = cfg.get("remote_hosts", [])
    result = []
    for entry in hosts:
        alias = entry.get("alias", "")
        url = entry.get("url", "")
        has_pw = bool(entry.get("admin_password_hash") or entry.get("admin_password", "").strip())
        # 找运行时状态
        runtime = _get_remote_host(alias)
        result.append({
            "alias": alias,
            "url": url,
            "has_password": has_pw,
            "online": runtime.online if runtime else None,
        })
    return {"hosts": result}


def _is_allowed_remote_url(url: str) -> bool:
    """只允许私有网络 / Tailscale CGNAT 地址，防止 SSRF。"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback:
            return True
        # Tailscale CGNAT 范围: 100.64.0.0/10
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        return False
    except (ValueError, TypeError):
        # 非 IP 地址（域名）— 拒绝以防 DNS 重绑定攻击
        return False

@api.post("/api/settings/remote-hosts")
def add_remote_host_endpoint(request: Request, body: dict):
    """添加远程主机到 vibe.yaml 并热加载。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    alias = (body.get("alias") or "").strip()
    url = (body.get("url") or "").strip().rstrip("/")
    password = (body.get("admin_password") or "").strip()
    if not alias or not url:
        raise HTTPException(status_code=400, detail="alias 和 url 为必填项")
    if ":" in alias:
        raise HTTPException(status_code=400, detail="alias 不能包含冒号")
    if not _is_allowed_remote_url(url):
        raise HTTPException(status_code=400, detail="URL 必须指向私有网络或 Tailscale 地址")
    # 密码只存哈希，不存明文
    token_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
    # 写入 vibe.yaml
    import yaml
    cfg_path = Path(__file__).parent.parent / "vibe.yaml"
    data = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
    remote_hosts = data.get("remote_hosts", [])
    # 去重：同 alias 则覆盖
    remote_hosts = [h for h in remote_hosts if h.get("alias") != alias]
    entry = {"alias": alias, "url": url}
    if token_hash:
        entry["admin_password_hash"] = token_hash
    # 清理旧的明文密码字段（如果存在）
    entry.pop("admin_password", None)
    remote_hosts.append(entry)
    data["remote_hosts"] = remote_hosts
    cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    # 热加载到运行时
    existing = _get_remote_host(alias)
    if existing:
        existing.url = url
        existing.token = token_hash
    else:
        host = _RemoteHost.from_config(entry)
        if host:
            _remote_hosts.append(host)
    return {"ok": True}


@api.delete("/api/settings/remote-hosts/{alias}")
def remove_remote_host_endpoint(request: Request, alias: str):
    """删除远程主机��置。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    import yaml
    cfg_path = Path(__file__).parent.parent / "vibe.yaml"
    data = {}
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
    remote_hosts = data.get("remote_hosts", [])
    new_hosts = [h for h in remote_hosts if h.get("alias") != alias]
    if len(new_hosts) == len(remote_hosts):
        raise HTTPException(status_code=404, detail="未找到该主机")
    data["remote_hosts"] = new_hosts
    cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    # 从���行时移��
    for i, h in enumerate(_remote_hosts):
        if h.alias == alias:
            _remote_hosts.pop(i)
            _remote_cache.pop(alias, None)
            _remote_panes_cache.pop(alias, None)
            break
    return {"ok": True}


@api.post("/api/settings/remote-hosts/{alias}/test")
async def test_remote_host_endpoint(request: Request, alias: str):
    """测试远程主机连接。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limit_ok(f"test:{client_ip}"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    host = _get_remote_host(alias)
    if not host:
        raise HTTPException(status_code=404, detail="未找到该主机")
    projects = await host.fetch_projects()
    return {
        "ok": host.online,
        "project_count": len(projects),
        "online": host.online,
    }


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
    if not re.match(r'^[\w\s-]+$', name):
        raise HTTPException(status_code=400, detail="Invalid sound name")
    sound_file = Path("/System/Library/Sounds") / f"{name}.aiff"
    if not sound_file.resolve().parent == Path("/System/Library/Sounds").resolve():
        raise HTTPException(status_code=400, detail="Invalid sound name")
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


# ── Remote target parsing ─────────────────────────────────────────────────────

def _parse_target(target: str) -> tuple[_RemoteHost | None, str]:
    """解析终端 target 字符串。

    远程格式: "alias:session:window.pane" → (host, "session:window.pane")
    本地格式: "session:window.pane" → (None, "session:window.pane")

    判断依据：远程 target 至少有 3 段（alias + session + window.pane），
    且第一段匹配已知的远程主机 alias。
    """
    parts = target.split(":", 1)
    if len(parts) == 2:
        maybe_alias, rest = parts
        host = _get_remote_host(maybe_alias)
        if host is not None:
            return host, rest
    return None, target


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
    # 合并远程 pane（加 alias 前缀）
    for host in _remote_hosts:
        remote_panes = _remote_panes_cache.get(host.alias, host.last_panes)
        for rp in remote_panes:
            result.append({
                **rp,
                "target": f"{host.alias}:{rp['target']}",
                "_host": host.alias,
                "_host_online": host.online,
            })
    return result


@api.delete("/api/dev/panes/{target:path}")
async def dev_kill_pane(request: Request, target: str):
    """Kill a tmux pane (target = session:window.pane). Removes it from
    the live tmux server, which propagates to /dev sidebar (auto-refresh)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    # 远程代理
    remote_host, real_target = _parse_target(target)
    if remote_host is not None:
        result = await remote_host.proxy_kill_pane(real_target)
        if result is None:
            raise HTTPException(status_code=502, detail=f"远程主机 {remote_host.alias} 不可达")
        return result
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


@api.post("/api/projects/{project_id}/description")
def update_project_description(project_id: str, request: Request, body: dict):
    """Update project description — writes `description:` into project's vibe.yaml."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    new_desc = (body.get("description") or "").strip()
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
    cfg["description"] = new_desc
    with open(yaml_path, "w") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    with _cache_lock:
        if _cache:
            for cp in _cache:
                if cp.get("id") == project_id:
                    cp["description"] = new_desc
                    break
    threading.Thread(target=_rebuild_and_persist, daemon=True).start()
    return {"ok": True, "description": new_desc}


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
async def terminals_output(request: Request, target: str, lines: int = 200):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    # 远程代理
    remote_host, real_target = _parse_target(target)
    if remote_host is not None:
        result = await remote_host.proxy_terminal_output(real_target, lines)
        if result is None:
            raise HTTPException(status_code=502, detail=f"远程主机 {remote_host.alias} 不可达")
        return result
    from vibe.tmux_bridge import capture_pane
    try:
        text = capture_pane(target, lines=lines)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"target": target, "output": text}


@api.websocket("/ws/terminal/{target:path}/stream")
async def terminal_stream_ws(ws: WebSocket, target: str):
    """Stream terminal output via WebSocket for mobile clients.

    Uses capture-pane with ANSI codes every 200ms and only sends when
    content changes. This gives <200ms latency real-time streaming without
    sharing the ttyd PTY (so mobile and desktop are fully independent).
    """
    # WS 认证：优先检查 header，兼容 query param（浏览器 WS 无法设 header）
    ws_token = ws.headers.get("x-admin-token") or ws.query_params.get("token", "")
    expected = _admin_token()
    if expected and not hmac.compare_digest(ws_token, expected):
        await ws.close(code=1008, reason="Unauthorized")
        return
    await ws.accept()

    # 远程 WebSocket 代理：连接远程 Mira 的同名 WS 端点，双向转发
    remote_host, real_target = _parse_target(target)
    if remote_host is not None:
        import websockets as _ws
        remote_ws_url = remote_host.url.replace("http://", "ws://").replace("https://", "wss://")
        remote_ws_url += f"/ws/terminal/{real_target}/stream"
        # token 通过 header 传输，不放在 URL 中（避免日志泄露）
        extra_headers = {}
        if remote_host.token:
            extra_headers["X-Admin-Token"] = remote_host.token
        try:
            async with _ws.connect(remote_ws_url, additional_headers=extra_headers) as remote_ws:
                async def _remote_to_client():
                    try:
                        async for msg in remote_ws:
                            if isinstance(msg, bytes):
                                await ws.send_bytes(msg)
                            else:
                                await ws.send_text(msg)
                    except Exception:
                        pass

                async def _client_to_remote():
                    try:
                        async for msg in ws.iter_text():
                            await remote_ws.send(msg)
                    except Exception:
                        pass

                await asyncio.gather(_remote_to_client(), _client_to_remote())
        except Exception:
            pass
        return

    from vibe.tmux_bridge import capture_pane
    prev_hash = ""
    try:
        while True:
            text = await asyncio.to_thread(capture_pane, target, 300, ansi=True)
            h = hashlib.md5(text.encode()).hexdigest()
            if h != prev_hash:
                prev_hash = h
                await ws.send_text(text)
            await asyncio.sleep(0.2)
    except (WebSocketDisconnect, Exception):
        pass


_UPLOAD_DIR = Path("/tmp/mira-uploads")

_ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml", "image/bmp"}
_UPLOAD_MAX = 50 * 1024 * 1024

@api.post("/api/upload/image")
async def upload_image(request: Request, file: UploadFile = File(...), host: str = ""):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    # 先验证类型，再读取完整内容
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in _ALLOWED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail=f"只允许上传图片文件，不支持 {ct}")
    # 分块读取，避免一次性加载超大文件到内存
    chunks = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        total += len(chunk)
        if total > _UPLOAD_MAX:
            raise HTTPException(status_code=413, detail="文件太大（最大 50MB）")
        chunks.append(chunk)
    content = b"".join(chunks)
    # 远程代理：带 host 参数时转发到远程主机
    if host:
        remote_host = _get_remote_host(host)
        if remote_host is None:
            raise HTTPException(status_code=404, detail=f"未知远程主机: {host}")
        result = await remote_host.proxy_upload(content, file.filename or "file", ct)
        if result is None:
            raise HTTPException(status_code=502, detail=f"远程主机 {host} 不可达")
        return result
    import uuid, mimetypes
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix or (mimetypes.guess_extension(ct) or "")
    dest = _UPLOAD_DIR / f"{uuid.uuid4().hex[:10]}{ext}"
    dest.write_bytes(content)
    return {"path": str(dest)}


@api.post("/api/terminals/{target:path}/send")
async def terminals_send(request: Request, target: str, body: dict):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    keys = body.get("keys", "")
    if not keys:
        raise HTTPException(status_code=400, detail="keys required")
    if len(keys) > 4096:
        raise HTTPException(status_code=400, detail="keys too long (max 4096 chars)")
    # 远程代理
    remote_host, real_target = _parse_target(target)
    if remote_host is not None:
        result = await remote_host.proxy_send_keys(real_target, keys)
        if result is None:
            raise HTTPException(status_code=502, detail=f"远程主机 {remote_host.alias} 不可达")
        return result
    from vibe.tmux_bridge import send_keys
    try:
        send_keys(target, keys)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@api.get("/api/alerts")
def get_alerts(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
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
    ws_token = websocket.query_params.get("token", "")
    expected = _admin_token()
    if expected and not hmac.compare_digest(ws_token, expected):
        await websocket.close(code=4401)
        return
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

# Injected into ttyd's HTML so the terminal follows Mira's active skin.
# Runs inside the iframe: reads localStorage, polls for the xterm Terminal
# instance (React mounts it async), and listens for postMessage updates.
_TTYD_THEME_INJECT = """<script id="mira-ttyd-theme">
(function(){
/* Per-skin config: colors + terminal options */
var T={
  'default':{
    bg:'#080c14',fg:'#eef1f7',cu:'#4f46e5',ca:'#080c14',sel:'rgba(79,70,229,.3)',
    k:'#3a3f4b',r:'#e06c75',g:'#3fb950',y:'#d29922',b:'#4e9eff',m:'#c792ea',c:'#56b6c2',w:'#eef1f7',
    bk:'#4a5060',br:'#e06c75',bg2:'#3fb950',by:'#e5a650',bb:'#82aaff',bm:'#d9a0f5',bc:'#89ddff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:false,fontSize:14},
  'claude-light':{
    bg:'#f5f3ef',fg:'#1a1a1a',cu:'#da7756',ca:'#ffffff',sel:'rgba(218,119,86,.25)',
    k:'#383a42',r:'#dc2626',g:'#16a34a',y:'#ca8a04',b:'#4078f2',m:'#a626a4',c:'#0184bc',w:'#1a1a1a',
    bk:'#b0b0b0',br:'#dc2626',bg2:'#16a34a',by:'#d97706',bb:'#4078f2',bm:'#a626a4',bc:'#0184bc',bw:'#383a42',
    cursorStyle:'bar',cursorBlink:true,fontSize:14},
  'claude-dark':{
    bg:'#131313',fg:'#ededed',cu:'#09B83E',ca:'#131313',sel:'rgba(9,184,62,.25)',
    k:'#3a3f4b',r:'#ef4444',g:'#4caf50',y:'#d4a84b',b:'#4e9eff',m:'#c792ea',c:'#56b6c2',w:'#ededed',
    bk:'#5d5d5d',br:'#ef4444',bg2:'#4caf50',by:'#e5a84b',bb:'#82aaff',bm:'#d9a0f5',bc:'#89ddff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:false,fontSize:14},
  'neon-pixel':{
    bg:'#0a0a0a',fg:'#e0e0ff',cu:'#ff00ff',ca:'#0a0a0a',sel:'rgba(0,255,0,.2)',
    k:'#282840',r:'#ff0040',g:'#00ff00',y:'#ffff00',b:'#00ccff',m:'#ff00ff',c:'#00ffff',w:'#e0e0ff',
    bk:'#505070',br:'#ff0040',bg2:'#00ff00',by:'#ff8800',bb:'#00ccff',bm:'#ff00ff',bc:'#00ffff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:true,fontSize:14},
  'pixel-cyber':{
    bg:'#020c1a',fg:'#eef8ff',cu:'#ff0055',ca:'#020c1a',sel:'rgba(0,212,255,.2)',
    k:'#2a5570',r:'#ff3355',g:'#00ff88',y:'#ffaa00',b:'#00d4ff',m:'#a855f7',c:'#00d4ff',w:'#eef8ff',
    bk:'#6bbad8',br:'#ff3355',bg2:'#00ff88',by:'#ffaa00',bb:'#00d4ff',bm:'#a855f7',bc:'#00d4ff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:true,fontSize:14}
};
/* Per-skin CSS injected into the iframe body */
var CSS_EXTRA={
  'neon-pixel':[
    /* CRT vignette: brighter center, dim corners */
    '.xterm{position:relative}',
    '.xterm::after{content:"";position:absolute;inset:0;pointer-events:none;z-index:10;',
    'background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,.55) 100%)}',
    /* Faint green phosphor scanlines */
    '.xterm::before{content:"";position:absolute;inset:0;pointer-events:none;z-index:11;',
    'background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,255,0,.028) 3px,rgba(0,255,0,.028) 4px)}',
    /* Accent scrollbar */
    '.xterm-viewport::-webkit-scrollbar{width:6px}',
    '.xterm-viewport::-webkit-scrollbar-thumb{background:#ff00ff;border-radius:0}',
    '.xterm-viewport::-webkit-scrollbar-track{background:#0a0a0a}',
    /* Green border around terminal */
    '.xterm-screen{outline:1px solid rgba(0,255,0,.2)}'
  ].join(''),
  'pixel-cyber':[
    /* CRT vignette: cyan-tinted */
    '.xterm{position:relative}',
    '.xterm::after{content:"";position:absolute;inset:0;pointer-events:none;z-index:10;',
    'background:radial-gradient(ellipse at center,transparent 55%,rgba(0,8,20,.65) 100%)}',
    /* Cyan scanlines */
    '.xterm::before{content:"";position:absolute;inset:0;pointer-events:none;z-index:11;',
    'background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,212,255,.022) 3px,rgba(0,212,255,.022) 4px)}',
    /* Cyan scrollbar */
    '.xterm-viewport::-webkit-scrollbar{width:6px}',
    '.xterm-viewport::-webkit-scrollbar-thumb{background:#00d4ff;border-radius:0}',
    '.xterm-viewport::-webkit-scrollbar-track{background:#020c1a}',
    /* Cyan border frame */
    '.xterm-screen{outline:1px solid rgba(0,212,255,.3);box-shadow:0 0 20px rgba(0,212,255,.08) inset}'
  ].join(''),
  'claude-light':[
    '.xterm-viewport::-webkit-scrollbar{width:6px}',
    '.xterm-viewport::-webkit-scrollbar-thumb{background:#da7756;border-radius:3px}',
    '.xterm-viewport::-webkit-scrollbar-track{background:#e8e4de}'
  ].join(''),
  'claude-dark':[
    '.xterm-viewport::-webkit-scrollbar{width:6px}',
    '.xterm-viewport::-webkit-scrollbar-thumb{background:#09B83E;border-radius:3px}',
    '.xterm-viewport::-webkit-scrollbar-track{background:#131313}'
  ].join(''),
  'default':[
    '.xterm-viewport::-webkit-scrollbar{width:6px}',
    '.xterm-viewport::-webkit-scrollbar-thumb{background:#4f46e5;border-radius:3px}',
    '.xterm-viewport::-webkit-scrollbar-track{background:#080c14}'
  ].join('')
};
var _term=null;
function skin(){return localStorage.getItem('mira-skin')||'default';}
function applyCSS(t,sk){
  var s=document.getElementById('mira-s');
  if(!s){s=document.createElement('style');s.id='mira-s';document.head.appendChild(s);}
  s.textContent='html,body,.xterm,.xterm-viewport{background:'+t.bg+'!important}'
    +(CSS_EXTRA[sk]||'');
}
function mkTheme(t){
  return {background:t.bg,foreground:t.fg,cursor:t.cu,cursorAccent:t.ca,
    selectionBackground:t.sel,
    black:t.k,red:t.r,green:t.g,yellow:t.y,blue:t.b,magenta:t.m,cyan:t.c,white:t.w,
    brightBlack:t.bk,brightRed:t.br,brightGreen:t.bg2,brightYellow:t.by,
    brightBlue:t.bb,brightMagenta:t.bm,brightCyan:t.bc,brightWhite:t.bw};
}
function setTheme(term,t){
  var th=mkTheme(t);
  try{term.options.theme=th;}catch(e){try{term.setOption('theme',th);}catch(e2){}}
  try{term.options.cursorStyle=t.cursorStyle||'block';}catch(e){try{term.setOption('cursorStyle',t.cursorStyle||'block');}catch(e2){}}
  try{term.options.cursorBlink=!!t.cursorBlink;}catch(e){try{term.setOption('cursorBlink',!!t.cursorBlink);}catch(e2){}}
}
function apply(){
  var sk=skin();var t=T[sk]||T['default'];
  applyCSS(t,sk);
  if(_term){setTheme(_term,t);return;}
  if(window.term&&window.term.element){_term=window.term;setTheme(_term,t);return;}
  var n=0,id=setInterval(function(){
    if(window.term&&window.term.element){
      clearInterval(id);_term=window.term;setTheme(_term,T[skin()]||T['default']);
    } else if(++n>100){clearInterval(id);}
  },150);
}
window.addEventListener('message',function(e){if(e.data&&e.data.type==='mira-theme')apply();});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);
else apply();
})();
</script>"""  # end _TTYD_THEME_INJECT

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
    content = resp.content
    # Inject theme script into the ttyd HTML page
    if "text/html" in resp.headers.get("content-type", "") and b"</body>" in content:
        content = content.replace(b"</body>", _TTYD_THEME_INJECT.encode() + b"</body>", 1)
    return Response(content=content, status_code=resp.status_code, headers=headers)


@api.websocket("/terminal/ws")
async def ttyd_ws_proxy(websocket: WebSocket):
    """Proxy WebSocket connection to ttyd.

    Forwards admin:<admin_password> as basic auth to ttyd (which requires it
    when --credential is set). Security boundary remains Mira login + ttyd auth.
    """
    import websockets as _ws
    import base64
    from vibe.config import load_global_config

    # ttyd 自身的 basic auth (--credential) 已经是安全边界，
    # 这里不再做 Mira token 验证——ttyd 前端 JS 无法注入 query param。
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
    # Select the window and pane in the target session.
    subprocess.run([_TMUX_BIN, "select-window", "-t", f"{session}:{window}"],
                   env=_TMUX_ENV, capture_output=True)
    subprocess.run([_TMUX_BIN, "select-pane", "-t", target],
                   env=_TMUX_ENV, capture_output=True)

    # Collect TTYs of all ttyd-spawned tmux clients.
    # Strategy: find child processes of any running ttyd process (not just the
    # one Mira started — it may have been orphaned after a restart).
    ttyd_ttys: set[str] = set()

    def _collect_ttyd_ttys(parent_pid: str) -> None:
        child_res = subprocess.run(
            ["pgrep", "-P", parent_pid],
            capture_output=True, text=True,
        )
        for child_pid in child_res.stdout.strip().splitlines():
            tty_res = subprocess.run(
                ["ps", "-p", child_pid.strip(), "-o", "tty="],
                capture_output=True, text=True,
            )
            tty = tty_res.stdout.strip()
            if tty and tty != "??":
                ttyd_ttys.add(f"/dev/{tty}")

    # Primary: use tracked _ttyd_proc if still alive
    if _ttyd_proc and _ttyd_proc.poll() is None:
        _collect_ttyd_ttys(str(_ttyd_proc.pid))

    # Fallback: scan for any running ttyd (handles orphaned ttyd after Mira restarts)
    if not ttyd_ttys:
        ttyd_scan = subprocess.run(
            ["pgrep", "-f", "ttyd"],
            capture_output=True, text=True,
        )
        for pid in ttyd_scan.stdout.strip().splitlines():
            _collect_ttyd_ttys(pid.strip())

    for tty in ttyd_ttys:
        subprocess.run(
            [_TMUX_BIN, "switch-client", "-c", tty, "-t", f"{session}:{window}"],
            env=_TMUX_ENV, capture_output=True,
        )
    return {"ok": True, "switched": len(ttyd_ttys)}


@api.post("/api/terminals/{target:path}/scroll")
async def terminal_scroll(request: Request, target: str, body: dict):
    """Scroll a tmux pane using copy-mode (for mobile touch scroll)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import scroll_pane
    direction = (body.get("direction") or "").strip()
    if direction not in ("up", "down", "page-up", "page-down", "top", "bottom", "exit"):
        raise HTTPException(status_code=400, detail="invalid direction")
    lines = min(int(body.get("lines", 5)), 50)
    scroll_pane(target, direction, lines)
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
        cwd_path = Path(cwd).expanduser().resolve()
        if not cwd_path.is_dir():
            raise HTTPException(status_code=400, detail="cwd 目录不存在")
        cmd += ["-c", str(cwd_path)]
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
