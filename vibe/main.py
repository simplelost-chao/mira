import asyncio
import typer
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

cli = typer.Typer()
api = FastAPI(title="Vibe Manager")

STATIC_DIR = Path(__file__).parent.parent / "static"

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
    return (
        f"你是 Mira，一个本地项目管理 agent。今天是 {date}。\n"
        f"用中文回答。需要查看实际情况时使用 run_shell 工具。\n\n"
        f"当前项目状态（共 {len(projects)} 个项目）：\n{summary}"
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


def _http_check(hostname: str, timeout: float = 3.0) -> bool:
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
    """Attach public_domain, public_ip, and HTTP-based is_running to each project's service.
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

    # Resolve IPs and HTTP-check in parallel
    ip_map: dict[str, str] = {}
    http_map: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=len(hostnames) * 2) as pool:
        ip_futs = {pool.submit(_resolve_ip, h): h for h in hostnames}
        http_futs = {pool.submit(_http_check, h): h for h in hostnames}
        for f in as_completed(ip_futs):
            ip_map[ip_futs[f]] = f.result()
        for f in as_completed(http_futs):
            http_map[http_futs[f]] = f.result()

    for p in projects:
        svc = p.get("service") or {}
        domain = svc.get("public_domain")
        if domain:
            domain_ok = http_map.get(domain, False)
            port_ok = svc.get("is_running", False)  # local port check from collect_service
            updates: dict = {
                "public_ip": ip_map.get(domain, ""),
                "is_running": domain_ok or port_ok,  # domain reachable OR local port open
            }
            p["service"] = {**svc, **updates}
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
        # Return stale cache while triggering async refresh
        if not force and _cache and not _refreshing:
            threading.Thread(target=_rebuild_and_persist, daemon=True).start()
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

@api.get("/api/projects")
def list_projects():
    return get_all_projects()

@api.get("/api/projects/{project_id}")
def get_project(project_id: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/refresh")
def refresh_project(project_id: str):
    return get_project(project_id)

@api.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(project_id: str):
    from vibe.detail_page import render_detail_page
    projects = get_all_projects()
    item = next((p for p in projects if p["id"] == project_id), None)
    name = item["name"] if item else project_id
    return HTMLResponse(render_detail_page(project_id, name))

@api.get("/projects/{project_id}/overview", response_class=HTMLResponse)
def project_overview_page(project_id: str):
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.aggregator import collect_project
    from vibe.overview_page import render_overview_page

    cfg = load_global_config()
    discovered = discover_projects(cfg["scan_dirs"], cfg["exclude"],
                                   cfg.get("extra_projects"), cfg.get("excluded_paths"))
    item = next((i for i in discovered if Path(i["path"]).name == project_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    path = Path(item["path"])
    # If a hand-crafted overview page exists, serve it directly
    hand_crafted = path / "design-preview" / "system-overview.html"
    if hand_crafted.exists():
        return HTMLResponse(hand_crafted.read_text(encoding="utf-8"))

    info = collect_project(path, name=item["name"], vibe_cfg=item["vibe_config"])
    return HTMLResponse(render_overview_page(info))

@api.post("/api/refresh")
def refresh_all():
    return get_all_projects(force=True)

@api.get("/api/projects/{project_id}/design-docs")
def list_design_docs(project_id: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            return p.get("design_docs", [])
    raise HTTPException(status_code=404, detail="Project not found")

@api.get("/api/projects/{project_id}/design-docs/{filename}")
def get_design_doc(project_id: str, filename: str):
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            for doc in p.get("design_docs", []):
                if doc["filename"] == filename:
                    return doc
            raise HTTPException(status_code=404, detail="Design doc not found")
    raise HTTPException(status_code=404, detail="Project not found")

@api.post("/api/projects/import")
def import_project(body: dict):
    """Add a project path to extra_projects in vibe.yaml."""
    from vibe.config import add_extra_project
    from vibe.aggregator import collect_project
    proj_path = (body.get("path") or "").strip()
    if not proj_path:
        raise HTTPException(status_code=400, detail="path is required")
    p = Path(proj_path).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {p}")
    if not (p / ".git").exists():
        raise HTTPException(status_code=400, detail=f"Not a git repository: {p}")
    add_extra_project(str(p))
    info = collect_project(p, name=p.name, vibe_cfg=None)
    return {"status": "ok", "project": info.model_dump()}


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
def delete_project(project_id: str):
    """Hide a project from discovery by adding it to excluded_paths."""
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
def set_project_status(project_id: str, body: dict):
    """Change project status and persist to vibe.yaml."""
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
def summarize_project_endpoint(project_id: str, force: bool = False):
    """Generate and write AI summary for a single project."""
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
            result[p.name] = {"is_running": svc.is_running, "port": svc.port, "process_name": svc.process_name}
        except Exception:
            result[p.name] = {"is_running": False, "port": None, "process_name": None}
    return result


@api.get("/api/alerts")
def get_alerts():
    with _alerts_lock:
        current = list(_alerts)
        _alerts.clear()
    return {"alerts": current}


@api.post("/api/chat")
async def chat_endpoint(body: dict):
    import json as _json
    import urllib.request as _ureq
    import asyncio as _asyncio

    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    if not message:
        raise HTTPException(status_code=400, detail="message required")

    async def generate():
        global _alerts

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
                "tools": [_SHELL_TOOL],
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
                    messages.append({"role": "tool", "content": output})
                else:
                    messages.append({"role": "tool", "content": f"[未知工具：{fn.get('name')}]"})

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


@cli.command("serve")
def serve(
    port: int = typer.Option(None, help="Port to listen on (default: from vibe.yaml or 8888)"),
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
):
    """Start the Vibe Manager web server."""
    from vibe.config import load_global_config
    cfg = load_global_config()
    actual_port = port if port is not None else cfg.get("port", 8888)
    if STATIC_DIR.exists():
        api.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

        @api.get("/", response_class=FileResponse)
        def index():
            return FileResponse(str(STATIC_DIR / "index.html"))

    # Load persisted cache from DB (instant), then refresh in background
    from vibe.cache_db import init_db, load_projects
    init_db()
    cached, ts = load_projects()
    if cached:
        global _cache, _cache_ts
        _cache, _cache_ts = cached, ts
        typer.echo(f"Loaded {len(cached)} projects from DB cache. Refreshing in background...")
        threading.Thread(target=_rebuild_and_persist, daemon=True).start()
    else:
        typer.echo("No DB cache found, building projects (first run)...")
        threading.Thread(target=_rebuild_and_persist, daemon=True).start()

    threading.Thread(target=_background_refresh, daemon=True).start()
    typer.echo(f"Vibe Manager running at http://{host}:{actual_port}")
    uvicorn.run(api, host=host, port=actual_port)

app = cli

if __name__ == "__main__":
    cli()
