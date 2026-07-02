import asyncio
import base64
import hashlib
import hmac
import ipaddress
import re
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
import typer
import uvicorn
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response, RedirectResponse
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
_TTYD_CLIENT_OPTIONS = ("rendererType=canvas",)
_ttyd_proc: subprocess.Popen | None = None

# 子账号只读 ttyd:每子账号一个,端口由 open_id 哈希决定,挂在他自己的 tmux session(只读)。
_SUB_TTYD_BASE = 7700
_SUB_TTYD_RANGE = 250
_sub_ttyd_procs: dict = {}   # open_id -> Popen
_sub_ttyd_ports: dict = {}   # open_id -> 已分配端口(本进程内稳定、互不碰撞)
_sub_ttyd_port_lock = threading.Lock()


def _sub_ttyd_port(open_id: str) -> int:
    """给每个子账号分配一个【互不碰撞】的 ttyd 端口。
    旧实现用 hash%250,两个子账号可能撞同一端口 → 互相杀 ttyd、串到对方终端。
    改为按 open_id 在范围内分配第一个未占用端口,进程内稳定。"""
    with _sub_ttyd_port_lock:
        if open_id in _sub_ttyd_ports:
            return _sub_ttyd_ports[open_id]
        used = set(_sub_ttyd_ports.values())
        for off in range(_SUB_TTYD_RANGE):
            p = _SUB_TTYD_BASE + off
            if p not in used:
                _sub_ttyd_ports[open_id] = p
                return p
        # 兜底:子账号超过 250 个(几乎不可能)→ 回退 hash
        return _SUB_TTYD_BASE + (int(hashlib.sha256(open_id.encode()).hexdigest(), 16) % _SUB_TTYD_RANGE)


def _kill_port_listeners(port: int) -> None:
    """杀掉监听该端口的进程(用于回收残留 ttyd,保证新实例能 bind)。"""
    try:
        r = subprocess.run(["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
                           capture_output=True, text=True)
        for pid in r.stdout.split():
            subprocess.run(["kill", pid])
    except Exception:
        pass


def _ensure_sub_ttyd(open_id: str) -> int | None:
    """确保该子账号有一个【可写】ttyd,挂在他自己的 session sub-<openid>。
    可写但安全:会话已禁用 tmux prefix + claude 跑在外壳脚本里,逃不到裸 shell。
    返回端口。base-path = /subterm/<port>,供 mira 反代时路径对齐。"""
    sess = _sub_session_name(open_id)
    if _tmux_run("has-session", "-t", sess).returncode != 0:
        return None   # 还没有会话,先 _ensure_sub_session
    port = _sub_ttyd_port(open_id)
    proc = _sub_ttyd_procs.get(open_id)
    if proc is not None and proc.poll() is None:
        return port   # 已在跑
    ttyd = _ttyd_bin()
    if not Path(ttyd).exists():
        return None
    # 清掉可能残留在该端口的旧 ttyd(如服务重启后遗留的实例),否则新的 --writable 实例 bind 失败,
    # 反代会连回那个旧的只读实例 → 子账号能看不能输入。
    _kill_port_listeners(port)
    base = f"/subterm/{port}"
    cmd = [ttyd, "-p", str(port), "--base-path", base, "--writable"]
    for opt in _TTYD_CLIENT_OPTIONS:
        cmd += ["--client-option", opt]
    cmd += [_tmux_bin(), "attach", "-t", sess]
    _sub_ttyd_procs[open_id] = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return port

def _ttyd_bin() -> str:
    return shutil.which("ttyd") or "/opt/homebrew/bin/ttyd"

def _tmux_bin() -> str:
    return shutil.which("tmux") or "/opt/homebrew/bin/tmux"

def _ttyd_auth_header() -> dict[str, str]:
    from vibe.config import load_global_config
    pwd = (load_global_config().get("admin_password") or "").strip()
    if not pwd:
        return {}
    token = base64.b64encode(f"admin:{pwd}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def _ttyd_healthy(timeout: float = 1.0) -> bool:
    """Return True when ttyd is reachable with Mira's configured auth."""
    req = urllib.request.Request(
        f"http://127.0.0.1:{_TTYD_PORT}/terminal/",
        headers=_ttyd_auth_header(),
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except urllib.error.HTTPError as e:
        # 401 means the port is occupied by ttyd, but not usable by Mira.
        return 200 <= e.code < 400
    except Exception:
        return False

def _ttyd_listener_pids() -> list[str]:
    proc = subprocess.run(
        ["lsof", f"-tiTCP:{_TTYD_PORT}", "-sTCP:LISTEN"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return []
    return [pid.strip() for pid in proc.stdout.splitlines() if pid.strip()]

def _ttyd_command(pid: str) -> str:
    proc = subprocess.run(
        ["ps", "-p", pid, "-o", "command="],
        capture_output=True, text=True,
    )
    return proc.stdout.strip()

def _ttyd_command_has_expected_options(cmd: str) -> bool:
    return all(opt in cmd or opt.replace("=", " ") in cmd for opt in _TTYD_CLIENT_OPTIONS)

def _ttyd_listener_has_expected_options() -> bool:
    for pid in _ttyd_listener_pids():
        cmd = _ttyd_command(pid)
        if "ttyd" in cmd and _ttyd_command_has_expected_options(cmd):
            return True
    return False

def _stop_stale_ttyd_listeners() -> None:
    """Stop Mira's ttyd listener when it lacks required client options.

    The tmux session is not killed; only the browser bridge is restarted.
    """
    for pid in _ttyd_listener_pids():
        cmd = _ttyd_command(pid)
        if "ttyd" not in cmd or _ttyd_command_has_expected_options(cmd):
            continue
        try:
            subprocess.run(["kill", pid], capture_output=True)
        except Exception:
            pass

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
    if _ttyd_healthy():
        if _ttyd_listener_has_expected_options():
            return
        _stop_stale_ttyd_listeners()
        time.sleep(0.3)

    from vibe.config import load_global_config
    pwd = (load_global_config().get("admin_password") or "").strip()

    cmd = [
        ttyd, "-p", str(_TTYD_PORT),
        "--writable",
        "--base-path", "/terminal",
    ]
    for opt in _TTYD_CLIENT_OPTIONS:
        cmd += ["--client-option", opt]
    if pwd:
        cmd += ["--credential", f"admin:{pwd}"]
    # Ensure mira tmux session exists before ttyd starts (ttyd only creates it on client connect)
    subprocess.run([tmux, "new-session", "-d", "-s", "mira", "-c", str(Path.home())],
                   capture_output=True)  # ignore error if already exists

    cmd += [tmux, "new-session", "-A", "-s", "mira", "-c", str(Path.home())]

    _ttyd_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _ensure_ttyd_running() -> None:
    """Start ttyd when Mira has no live child process to serve terminals."""
    if _ttyd_proc is None or _ttyd_proc.poll() is not None:
        _start_ttyd()


def _watch_ttyd() -> None:
    """Restart ttyd only after its process exits.

    HTTP health probes can fail independently of the already established
    terminal WebSocket. Restarting a live ttyd on such a failure disconnects
    every browser session and leaves ttyd's reconnect prompt in a loop.
    """
    while True:
        time.sleep(5)
        _ensure_ttyd_running()


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
# gzip 压缩:页面 HTML(dev 页 ~180KB)、stats/prompts 等大 JSON 响应都能省 ~5-8 倍带宽
from starlette.middleware.gzip import GZipMiddleware
api.add_middleware(GZipMiddleware, minimum_size=600)

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
    from vibe.dev_page import _build_id
    return {"version": _read_version(), "build": _build_id()}

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
_alerts: list[str] = []        # 看门狗运行时事件（append-only，读取时消费）
_anomalies: list[str] = []     # 异常扫描快照（每次重建整体替换，读取时消费）
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


def _get_principal(request: Request):
    """鉴权主体:('owner', None) / ('sub', account) / None。
    owner = 密码 token;sub = 飞书会话 token(X-Sub-Token)对应的 active 子账号。"""
    if _is_admin(request):
        return ("owner", None)
    from vibe.accounts import session_open_id, find_account
    open_id = session_open_id(request.headers.get("X-Sub-Token") or "")
    if open_id:
        _, data = _read_vibe_yaml()
        acc = find_account(data.get("accounts", []), open_id)
        if acc and acc.get("status") == "active":
            return ("sub", acc)
    return None




_BLOCKED_PATTERNS = [
    "rm ", "rmdir", "mv ", "cp ", "> /", ">> /",
    "mkfs", "dd if=", ":(){ ", "sudo ", "chmod ", "chown ",
    "eval ", "exec ", "shutdown", "reboot", "halt", "kill -9",
    "DROP TABLE", "DELETE FROM",
]

# 管道到解释器（含任意空白：`| sh`、`|sh`、`|\tpython3`）——比写死字符串更难绕过
_PIPE_TO_INTERPRETER = re.compile(r"\|\s*(sh|bash|zsh|ksh|python3?|node|perl|ruby|php|lua)\b")


def _command_is_blocked(command: str):
    """Return the matched danger marker if command is blocked, else None.
    归一化空白后匹配，防止用 Tab/多空格绕过带空格的模式。"""
    norm = re.sub(r"\s+", " ", command.strip().lower())
    for pattern in _BLOCKED_PATTERNS:
        if pattern.lower() in norm:
            return pattern
    if _PIPE_TO_INTERPRETER.search(norm):
        return "| <解释器>"
    return None

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
    blocked = _command_is_blocked(command)
    if blocked:
        return f"[拒绝执行] 包含危险操作：{blocked}"
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
    global _anomalies
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
        # 只替换异常快照，绝不触碰看门狗线程写入的运行时事件（_alerts）
        _anomalies.clear()
        _anomalies.extend(f"[{ts}] {a}" for a in new_alerts)
        if len(_anomalies) > 50:
            del _anomalies[:-50]




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
                _base_svc_state[name] = True
                return
        ts = datetime.now().strftime("%H:%M")
        with _alerts_lock:
            _alerts.append(f"[{ts}] {name} 自动重启后端口仍无响应")
    except Exception as e:
        ts = datetime.now().strftime("%H:%M")
        with _alerts_lock:
            _alerts.append(f"[{ts}] {name} 自动重启失败：{e}")


def _establish_baseline(cfg: dict) -> None:
    """Startup baseline pass. A service already down at this point (e.g. after
    a machine reboot) never produces an up→down transition for the monitor
    loop, so restart it here directly when it has a restart_cmd."""
    from datetime import datetime
    sound = cfg.get("notification_sound", "Pop")
    for svc in cfg.get("base_services") or []:
        name = svc.get("name", "")
        port, process = svc.get("port"), svc.get("process")
        up = (_check_port(port) if port else False) or \
             (_check_process(process) if process else False)
        _base_svc_state[name] = up
        restart_cmd = svc.get("restart_cmd", "").strip()
        if not up and restart_cmd:
            ts = datetime.now().strftime("%H:%M")
            with _alerts_lock:
                _alerts.append(f"[{ts}] {name} 启动检查发现服务未运行，正在自动重启…")
            threading.Thread(
                target=_auto_restart,
                args=(name, restart_cmd, port, sound),
                daemon=True,
            ).start()


def _monitor_base_services_loop() -> None:
    """Background thread: check base services every 60s, notify on state change."""
    _MONITOR_INTERVAL = 60
    from datetime import datetime
    from vibe.config import load_global_config
    global _base_svc_state

    # ── Establish baseline (restarts services already down, e.g. after reboot) ─
    try:
        _establish_baseline(load_global_config())
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
                else:         # down → up
                    msg = f"{name} 服务已恢复"
                    with _alerts_lock:
                        _alerts.append(f"[{ts}] {msg}")
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


def _insert_project_into_cache(path: str) -> None:
    """Collect a single (newly created) project and splice it into the cache,
    so it is visible immediately without waiting for the full rebuild."""
    from vibe.config import load_project_config
    global _cache
    p = Path(path)
    try:
        vibe_cfg = load_project_config(p)
    except RuntimeError:
        vibe_cfg = None
    name = vibe_cfg.get("name", p.name) if vibe_cfg else p.name
    info = _collect_one({"path": str(p), "name": name, "vibe_config": vibe_cfg})
    with _cache_lock:
        _cache = [c for c in _cache if c.get("path") != str(p)] + [info]


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

@api.get("/api/projects/{project_id}")
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


@api.get("/sessions")
def session_dashboard_route():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/stats", status_code=302)


@api.get("/dev", response_class=HTMLResponse)
def dev_page_route():
    from vibe.dev_page import render_dev_page
    return HTMLResponse(render_dev_page(), headers=_NC)


@api.get("/deploy", response_class=HTMLResponse)
def deploy_page_route():
    from vibe.deploy_page import render_deploy_page
    return HTMLResponse(render_deploy_page(), headers=_NC)


@api.get("/new", response_class=HTMLResponse)
def new_project_page(request: Request):
    from vibe.new_project_page import render_new_project_page
    return HTMLResponse(render_new_project_page(), headers=_NC)


@api.get("/accounts")
def accounts_page_route():
    """子账号管理已并入「设置 → 子账户」tab;旧链接重定向到 dev 页(可从齿轮进入设置)。"""
    return RedirectResponse(url="/dev", status_code=302)


@api.get("/sub")
def sub_page_redirect():
    """旧 /sub 链接 → 统一到 dev 页(子账号现在直接用 dev 页面)。"""
    return RedirectResponse(url="/dev", status_code=302)


@api.get("/settings", response_class=HTMLResponse)
def settings_console_page(request: Request):
    from vibe.settings_page import render_settings_page
    return render_settings_page()


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
    ref_image = body.get("ref_image")  # base64 string or None
    ref_image_mime = body.get("ref_image_mime") or "image/png"
    try:
        candidates = call_brainstorm(description, model_id, cfg,
                                     ref_image=ref_image, ref_image_mime=ref_image_mime)
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
    if domain and "." not in domain:
        raise HTTPException(status_code=400, detail=f"域名格式不对：{domain}（应形如 myapp.zhuchao.life，留空表示无域名）")

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

    # 新项目先单独采集并插入缓存，跳回首页立即可见；全量重建仍走后台
    try:
        _insert_project_into_cache(result["path"])
        log_lines.append("✓ 已加入项目列表")
    except Exception as e:
        log_lines.append(f"⚠ 项目列表缓存更新失败（稍后会自动刷新）: {e}")

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


# ── 设计文档公开分享(免登录只读链接)──────────────────────────────────────────

_SHARE_404_HTML = (
    "<!DOCTYPE html><html lang=zh><head><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>链接失效 · Mira</title>"
    "<style>body{background:#080c14;color:#7a8499;font-family:monospace;"
    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
    "div{text-align:center}h1{color:#eef1f7;font-size:18px;margin:0 0 8px}</style></head>"
    "<body><div><h1>链接已失效</h1><p>该分享不存在或已被取消。</p></div></body></html>"
)


def _read_doc_shares() -> list[dict]:
    _, data = _read_vibe_yaml()
    return data.get("doc_shares", [])


@api.post("/api/projects/{project_id}/design-docs/{filename}/share")
def share_design_doc(request: Request, project_id: str, filename: str):
    """为某个设计文档生成公开分享 token(幂等)。公开页免登录、内容实时。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    proj = next((p for p in get_all_projects() if p["id"] == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    if not any(d.get("filename") == filename for d in proj.get("design_docs", [])):
        raise HTTPException(status_code=404, detail="Design doc not found")
    cfg_path, data = _read_vibe_yaml()
    shares = data.get("doc_shares", [])
    existing = next((s for s in shares
                     if s.get("project") == project_id and s.get("filename") == filename), None)
    if existing:
        return {"token": existing["token"]}
    token = secrets.token_urlsafe(16)
    shares.append({"token": token, "project": project_id,
                   "filename": filename, "created_at": int(time.time())})
    data["doc_shares"] = shares
    _write_vibe_yaml(cfg_path, data)
    return {"token": token}


@api.delete("/api/projects/{project_id}/design-docs/{filename}/share")
def unshare_design_doc(request: Request, project_id: str, filename: str):
    """撤销某个设计文档的分享;公开链接立即失效。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    shares = data.get("doc_shares", [])
    new_list = [s for s in shares
                if not (s.get("project") == project_id and s.get("filename") == filename)]
    if len(new_list) == len(shares):
        raise HTTPException(status_code=404, detail="该文档未分享")
    data["doc_shares"] = new_list
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


@api.get("/api/projects/{project_id}/shares")
def list_project_shares(request: Request, project_id: str):
    """返回本项目已分享文档的 {filename: token} 映射,供设计文档页显示分享状态。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return {s["filename"]: s["token"] for s in _read_doc_shares()
            if s.get("project") == project_id}


@api.get("/share/{token}", response_class=HTMLResponse)
def public_shared_doc(token: str):
    """公开的设计文档只读页 —— 免登录,任何人可访问。内容实时读取当前文档。"""
    share = next((s for s in _read_doc_shares() if s.get("token") == token), None)
    doc = None
    proj_name = ""
    if share:
        proj = next((p for p in get_all_projects() if p["id"] == share.get("project")), None)
        if proj:
            proj_name = proj.get("name", share["project"])
            doc = next((d for d in proj.get("design_docs", [])
                        if d.get("filename") == share.get("filename")), None)
    if not doc:
        return HTMLResponse(_SHARE_404_HTML, status_code=404)
    from vibe.share_page import render_share_page
    return HTMLResponse(render_share_page(doc, proj_name))


@api.get("/api/projects/{project_id}/prompts")
def get_project_prompts(request: Request, project_id: str):
    """项目的用户 prompts + 每条的账号归属(时间推断:落在某子账号活跃区间→该子账号,否则 owner)。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.history_db import get_prompts
    prompts = get_prompts(project_id)
    by_oid = {}
    if any(p.get("sub_open_id") for p in prompts):
        _, vy = _read_vibe_yaml()
        by_oid = {a.get("feishu_open_id"): a for a in (vy.get("accounts") or [])}
    for p in prompts:
        oid = p.pop("sub_open_id", None)
        exact = p.pop("attr_exact", False)
        if oid:
            acc = by_oid.get(oid) or {}
            p["account"] = {"name": acc.get("name") or oid, "avatar": acc.get("avatar") or "",
                            "sub": True, "exact": exact}
        else:
            p["account"] = None   # owner / 终端直接敲(未落入任何子账号)
    return prompts


@api.get("/api/projects/{project_id}/sessions")
def get_project_sessions(request: Request, project_id: str):
    """Return per-session token stats for a project."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects_with_remote()
    proj = next((p for p in projects if p["id"] == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    from pathlib import Path as _P
    project_path = proj.get("path", "")
    encoded = '-' + project_path.replace('/', '-').lstrip('-')
    folder_prefix = str(_P.home() / '.claude' / 'projects' / encoded)
    aliases = (proj.get("_vibe_config") or {}).get("aliases", [])
    from vibe.history_db import get_session_details
    return get_session_details(project_id, folder_prefix, aliases)


@api.get("/api/projects/{project_id}/insights")
def get_project_insights(request: Request, project_id: str):
    """详情页:全历史按天(会话/token/开销,可往前翻) + 该项目的子账号协同统计。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects_with_remote()
    proj = next((p for p in projects if p["id"] == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    from pathlib import Path as _P
    project_path = proj.get("path", "")
    encoded = '-' + project_path.replace('/', '-').lstrip('-')
    folder_prefix = str(_P.home() / '.claude' / 'projects' / encoded)
    aliases = (proj.get("_vibe_config") or {}).get("aliases", [])
    from vibe.history_db import get_project_daily, get_project_sub_collab
    daily = get_project_daily(project_id, folder_prefix, aliases)
    collab = get_project_sub_collab(project_id)
    if collab:
        _, vy = _read_vibe_yaml()
        by_oid = {a.get("feishu_open_id"): a for a in (vy.get("accounts") or [])}
        for c in collab:
            acc = by_oid.get(c["open_id"]) or {}
            c["name"] = acc.get("name") or c["open_id"]
            c["avatar"] = acc.get("avatar") or ""
    return {"days": daily["days"], "totals": daily["totals"], "sub_collab": collab}


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


def _remove_deployment_entry(project: str) -> None:
    """从 vibe.yaml 删掉指定项目(按 project 名/folder 名)的部署条目;没有则无操作。"""
    cfg_path, data = _read_vibe_yaml()
    deployments = data.get("deployments", [])
    new_list = [d for d in deployments if d.get("project") != project]
    if len(new_list) != len(deployments):
        data["deployments"] = new_list
        _write_vibe_yaml(cfg_path, data)


def _remove_project_from_cache(path: str) -> None:
    """从内存缓存即时剔除一个项目,避免删后最长等一个 TTL 才从首页消失。"""
    global _cache
    with _cache_lock:
        _cache = [c for c in _cache if c.get("path") != str(path)]


@api.delete("/api/projects/{project_id}")
def delete_project(request: Request, project_id: str):
    """彻底移除项目:加入 excluded_paths 永久排除发现、清掉它的部署条目、
    即时从缓存剔除。不删除磁盘文件(可从 vibe.yaml 删掉那行恢复显示)。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.config import exclude_project
    projects = get_all_projects()
    for p in projects:
        if p["id"] == project_id:
            exclude_project(p["path"])
            _remove_deployment_entry(project_id)
            _remove_project_from_cache(p["path"])
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


_TUNNEL_SERVICES_FILE = Path.home() / ".cloudflared" / "services.yml"
_TUNNEL_SCRIPT = Path.home() / ".cloudflared" / "tunnel"


def _load_tunnel_services() -> list[dict]:
    """Read services.yml and return list of tunnel service dicts."""
    import yaml as _yaml
    if not _TUNNEL_SERVICES_FILE.exists():
        return []
    try:
        data = _yaml.safe_load(_TUNNEL_SERVICES_FILE.read_text()) or {}
        services = data.get("services", {})
        result = []
        for name, svc in services.items():
            result.append({
                "name": name,
                "hostname": svc.get("hostname", ""),
                "port": svc.get("port", 0),
                "enabled": bool(svc.get("enabled", False)),
            })
        return result
    except Exception:
        return []


@api.get("/api/tunnels")
def list_tunnels(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    services = _load_tunnel_services()
    # check which ports are actually listening
    for svc in services:
        svc["is_running"] = _check_port(svc["port"]) if svc["port"] else False
    return services


@api.post("/api/tunnels/{name}/toggle")
def toggle_tunnel(name: str, request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    import yaml as _yaml
    if not _TUNNEL_SERVICES_FILE.exists():
        raise HTTPException(status_code=404, detail="services.yml not found")
    data = _yaml.safe_load(_TUNNEL_SERVICES_FILE.read_text()) or {}
    services = data.get("services", {})
    if name not in services:
        raise HTTPException(status_code=404, detail=f"未找到 tunnel: {name}")
    services[name]["enabled"] = not services[name].get("enabled", False)
    _TUNNEL_SERVICES_FILE.write_text(
        _yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))
    # regenerate config.yml
    subprocess.run([str(_TUNNEL_SCRIPT), "generate"], capture_output=True)
    return {"name": name, "enabled": services[name]["enabled"]}


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


_oauth_cache: dict = {}  # {"token": str, "expires_at": float}

def _get_claude_oauth_token() -> tuple[str, str] | None:
    """Return (access_token, subscription_type) or None.

    Tries in order:
    1. ~/.claude/.credentials.json  (old CLI auth)
    2. macOS Claude desktop app config.json (encrypted with Keychain key)
    Auto-refreshes expired tokens using the stored refresh_token.
    """
    import json as _json, hashlib, ctypes, base64, subprocess as _sp, sys

    # Return cached token if still valid (with 60s margin)
    if _oauth_cache.get("token") and _oauth_cache.get("expires_at", 0) > time.time() + 60:
        return _oauth_cache["token"], _oauth_cache.get("sub", "unknown")

    # ── 方式1: macOS Keychain "Claude Code-credentials" (current Claude Code) ─
    if sys.platform == "darwin":
        try:
            raw = _sp.check_output(
                ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                stderr=_sp.DEVNULL,
            ).strip().decode()
            creds = _json.loads(raw)
            oauth = creds.get("claudeAiOauth", {})
            if oauth.get("accessToken"):
                token = oauth["accessToken"]
                sub = oauth.get("subscriptionType", "unknown")
                expires_at = oauth.get("expiresAt", 0) / 1000
                # Auto-refresh if expired
                if expires_at < time.time() and oauth.get("refreshToken"):
                    try:
                        import httpx
                        resp = httpx.post(
                            "https://console.anthropic.com/v1/oauth/token",
                            json={
                                "grant_type": "refresh_token",
                                "refresh_token": oauth["refreshToken"],
                            },
                            timeout=15,
                        )
                        if resp.status_code == 200:
                            rd = resp.json()
                            token = rd["access_token"]
                            expires_at = time.time() + rd.get("expires_in", 28800)
                    except Exception:
                        pass
                _oauth_cache["token"] = token
                _oauth_cache["expires_at"] = expires_at
                _oauth_cache["sub"] = sub
                return token, sub
        except Exception:
            pass

    # ── 方式2: 旧版 CLI 凭证文件 ──────────────────────────────────────────
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = _json.loads(creds_path.read_text())
            token = creds["claudeAiOauth"]["accessToken"]
            sub = creds["claudeAiOauth"].get("subscriptionType", "unknown")
            return token, sub
        except (KeyError, _json.JSONDecodeError):
            pass

    # ── 方式3: macOS 桌面 App config.json (Electron safeStorage + Keychain) ─
    if sys.platform != "darwin":
        return None
    try:
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "config.json"
        if not config_path.exists():
            return None
        cfg = _json.loads(config_path.read_text())
        enc_b64 = cfg.get("oauth:tokenCache")
        if not enc_b64:
            return None

        # 从 Keychain 读取加密密钥字符串
        key_b64 = _sp.check_output(
            ["security", "find-generic-password", "-s", "Claude Safe Storage",
             "-a", "Claude Key", "-w"],
            stderr=_sp.DEVNULL,
        ).strip().decode()

        # 派生 AES-128 密钥: PBKDF2(key_str, "saltysalt", 1003, SHA1) → 16字节
        aes_key = hashlib.pbkdf2_hmac("sha1", key_b64.encode(), b"saltysalt", 1003, 16)

        # AES-128-CBC 解密: 跳过 "v10" 前缀, IV = 16个空格
        enc_bytes = base64.b64decode(enc_b64)
        ct = enc_bytes[3:]  # skip "v10"
        iv = b" " * 16
        libcc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        out = ctypes.create_string_buffer(len(ct))
        out_len = ctypes.c_size_t(0)
        err = libcc.CCCrypt(1, 0, 1, aes_key, len(aes_key), iv,
                            ct, len(ct), out, len(ct), ctypes.byref(out_len))
        if err != 0:
            return None

        token_cache = _json.loads(bytes(out[:out_len.value]).decode("utf-8"))

        # 找到含 claude_code scope 的 entry（含 token + refreshToken + expiresAt）
        entry = None
        entry_key = None
        for k, v in token_cache.items():
            if isinstance(v, dict) and v.get("token"):
                if "claude_code" in k:
                    entry = v
                    entry_key = k
                    break
        if not entry:
            for k, v in token_cache.items():
                if isinstance(v, dict) and v.get("token"):
                    entry = v
                    entry_key = k
                    break
        if not entry:
            return None

        token = entry["token"]
        expires_at = entry.get("expiresAt", 0) / 1000  # ms → seconds

        # Token 过期且有 refreshToken → 自动刷新
        if expires_at < time.time() and entry.get("refreshToken") and entry_key:
            client_id = entry_key.split(":")[0]
            try:
                import httpx
                resp = httpx.post(
                    "https://console.anthropic.com/v1/oauth/token",
                    json={
                        "grant_type": "refresh_token",
                        "refresh_token": entry["refreshToken"],
                        "client_id": client_id,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    rd = resp.json()
                    token = rd["access_token"]
                    expires_at = time.time() + rd.get("expires_in", 28800)
            except Exception:
                pass  # fall through with expired token

        _oauth_cache["token"] = token
        _oauth_cache["expires_at"] = expires_at
        _oauth_cache["sub"] = "unknown"
        return token, "unknown"
    except Exception:
        return None


# Account-global Claude usage 变化很慢(5h/7d 才 reset),而 Anthropic 的 OAuth
# usage 接口有限流(429)。用 TTL 缓存把对上游的请求压到最多每 5 分钟一次,
# 并在上游抖动时返回上次成功值(stale),避免前端拿到 error。
_claude_usage_cache = {"ts": 0.0, "data": None}
_CLAUDE_USAGE_TTL = 300  # seconds


_WEEKLY_USAGE_FILE = Path.home() / ".vibe-manager" / "weekly_usage.json"


def _record_weekly_usage(utilization, resets_at) -> None:
    """记录某一周的真实占用率。key=该周起始日(=重置日次日,因重置在重置日晚上;
    resets_at 是本周末重置时间,起始日=resets_at-6天)。存所见最大值(周内
    utilization 单调递增,max=临近重置的最终值)。供趋势图显示真实 %。"""
    if utilization is None or not resets_at:
        return
    try:
        import json as _json
        from datetime import datetime as _dtm, timedelta as _td
        key = (_dtm.fromtimestamp(resets_at) - _td(days=6)).strftime("%Y-%m-%d")
        _WEEKLY_USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if _WEEKLY_USAGE_FILE.exists():
            try:
                data = _json.loads(_WEEKLY_USAGE_FILE.read_text()) or {}
            except Exception:
                data = {}
        prev = (data.get(key) or {}).get("util", 0)
        data[key] = {"util": max(prev, float(utilization)), "updated": int(time.time())}
        _WEEKLY_USAGE_FILE.write_text(_json.dumps(data))
    except Exception:
        pass


@api.get("/api/weekly-usage-history")
def weekly_usage_history(request: Request):
    """已记录的每周真实占用率 { 周起始日: 0~1 }。从开始记录起才有数据。"""
    if not _get_principal(request):
        raise HTTPException(status_code=401, detail="需要登录")
    import json as _json
    try:
        data = _json.loads(_WEEKLY_USAGE_FILE.read_text()) if _WEEKLY_USAGE_FILE.exists() else {}
    except Exception:
        data = {}
    return {k: (v or {}).get("util", 0) for k, v in (data or {}).items()}


@api.get("/api/claude-usage")
def claude_usage(request: Request):
    """Get Claude Code usage via Anthropic OAuth usage API (TTL-cached, stale-on-error)."""
    # 账号级用量是共享账号的(子账号也用这个账号),owner / sub 都可读
    if not _get_principal(request):
        raise HTTPException(status_code=401, detail="需要登录")

    import time as _time
    now = _time.time()
    cached = _claude_usage_cache["data"]
    # 缓存未过期:直接返回,不打上游
    if cached is not None and (now - _claude_usage_cache["ts"]) < _CLAUDE_USAGE_TTL:
        return cached

    def _stale_or_error(err_code, err_msg):
        # 上游失败时:有旧值就返回旧值(标记 stale),否则才返回错误
        if cached is not None:
            return {**cached, "_stale": True}
        return {"error": err_code, "message": err_msg}

    creds = _get_claude_oauth_token()
    if not creds:
        return _stale_or_error("no_credentials", "无法获取 Claude OAuth token")
    token, sub_type = creds
    import httpx
    from datetime import datetime as _dt
    try:
        resp = httpx.get(
            "https://api.anthropic.com/api/oauth/usage",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code != 200:
            return _stale_or_error("api_error", f"OAuth usage API returned {resp.status_code}")
        data = resp.json()
    except Exception:
        return _stale_or_error("api_error", "Failed to reach Anthropic OAuth usage API")

    def _parse_window(win):
        if not win:
            return None
        resets_at = win.get("resets_at")
        ts = None
        if resets_at:
            try:
                ts = int(_dt.fromisoformat(resets_at.replace("Z", "+00:00")).timestamp())
            except Exception:
                pass
        return {
            "utilization": (win.get("utilization") or 0) / 100.0,
            "resets_at": ts,
        }

    result = {
        "subscription": sub_type,
        "session": _parse_window(data.get("five_hour")),
        "weekly": _parse_window(data.get("seven_day")),
    }
    # Per-model 7d breakdown
    for key in ("seven_day_opus", "seven_day_sonnet"):
        win = _parse_window(data.get(key))
        if win:
            result[key] = win
    _claude_usage_cache["ts"] = now
    _claude_usage_cache["data"] = result
    _wk = result.get("weekly") or {}
    _record_weekly_usage(_wk.get("utilization"), _wk.get("resets_at"))
    return result


def _calc_local_7d_usage() -> dict:
    """Aggregate token usage from Claude Code session JSONL files for the past 7 days."""
    import json as _json
    sessions_root = Path.home() / ".claude" / "projects"
    if not sessions_root.exists():
        return {}
    cutoff = time.time() - 7 * 86400
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "messages": 0}
    model_totals: dict[str, dict] = {}
    try:
        for jsonl in sessions_root.rglob("*.jsonl"):
            try:
                if jsonl.stat().st_mtime < cutoff:
                    continue
            except OSError:
                continue
            try:
                with open(jsonl, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if '"usage"' not in line:
                            continue
                        try:
                            entry = _json.loads(line)
                        except _json.JSONDecodeError:
                            continue
                        msg = entry.get("message") or {}
                        usage = msg.get("usage")
                        if not usage or msg.get("role") != "assistant":
                            continue
                        inp = usage.get("input_tokens", 0)
                        out = usage.get("output_tokens", 0)
                        cr = usage.get("cache_read_input_tokens", 0)
                        cc = usage.get("cache_creation_input_tokens", 0)
                        totals["input"] += inp
                        totals["output"] += out
                        totals["cache_read"] += cr
                        totals["cache_create"] += cc
                        totals["messages"] += 1
                        # per-model breakdown
                        model = msg.get("model", "unknown")
                        if model not in model_totals:
                            model_totals[model] = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "msgs": 0}
                        mt = model_totals[model]
                        mt["input"] += inp
                        mt["output"] += out
                        mt["cache_read"] += cr
                        mt["cache_create"] += cc
                        mt["msgs"] += 1
            except OSError:
                continue
    except Exception:
        return {}
    # Estimate cost (USD) per model
    _PRICING = {
        "claude-opus-4-6":   {"input": 15, "output": 75, "cache_read": 1.5, "cache_create": 18.75},
        "claude-sonnet-4-6": {"input": 3, "output": 15, "cache_read": 0.30, "cache_create": 3.75},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4, "cache_read": 0.08, "cache_create": 1},
    }
    total_cost = 0.0
    for model, mt in model_totals.items():
        p = _PRICING.get(model, _PRICING.get("claude-sonnet-4-6", {}))
        cost = (mt["input"] * p["input"] + mt["output"] * p["output"]
                + mt["cache_read"] * p["cache_read"] + mt["cache_create"] * p["cache_create"]) / 1_000_000
        mt["cost_usd"] = round(cost, 2)
        total_cost += cost
    totals["cost_usd"] = round(total_cost, 2)
    totals["models"] = model_totals
    return totals


# Cache local 7d calculation (expensive to scan)
_local_7d_cache: dict = {}
_local_7d_cache_ts: float = 0.0

def _calc_local_7d_usage_cached() -> dict:
    global _local_7d_cache, _local_7d_cache_ts
    if time.time() - _local_7d_cache_ts < 300:  # 5 min cache
        return _local_7d_cache
    _local_7d_cache = _calc_local_7d_usage()
    _local_7d_cache_ts = time.time()
    return _local_7d_cache


@api.get("/api/codex-usage")
def codex_usage(request: Request):
    """Get Codex rate limit info from its local SQLite logs."""
    if not _get_principal(request):
        raise HTTPException(status_code=401, detail="需要登录")
    import sqlite3, re, json as _json
    db_path = Path.home() / ".codex" / "logs_2.sqlite"
    if not db_path.exists():
        return {"error": "no_db", "message": "Codex logs DB not found"}
    try:
        # 注意：with sqlite3.connect() 只管理事务、不关闭连接，必须显式 close
        conn = sqlite3.connect(str(db_path), timeout=3)
        try:
            row = conn.execute(
                "SELECT feedback_log_body FROM logs "
                "WHERE feedback_log_body LIKE '%rate_limits%' AND feedback_log_body LIKE '%used_percent%' "
                "ORDER BY ts DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return {"error": "no_data"}
        def _parse_window(text, name):
            m = re.search(
                rf'"{name}":\{{"used_percent":(\d+),"window_minutes":(\d+),'
                rf'"reset_after_seconds":(\d+),"reset_at":(\d+)\}}',
                text,
            )
            if not m:
                return None
            return {
                "used_percent": int(m.group(1)),
                "window_minutes": int(m.group(2)),
                "reset_at": int(m.group(4)),
            }
        primary = _parse_window(row[0], "primary")
        secondary = _parse_window(row[0], "secondary")
        if not primary:
            return {"error": "parse_error"}
        m_top = re.search(r'"limit_reached":(true|false)', row[0])
        return {
            "limit_reached": m_top.group(1) == "true" if m_top else False,
            "session": primary,
            "weekly": secondary,
        }
    except Exception as e:
        return {"error": str(e)}


@api.get("/api/codex-stats")
def codex_stats(request: Request):
    """Return global Codex usage + per-project breakdown (mapped to Mira project names)."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.collectors.codex_sessions import (
        collect_codex_activity,
        _all_jsonl_files,
        _get_session_workdir,
        _parse_session,
    )
    from pathlib import Path as _Path

    data = collect_codex_activity(str(Path.home()))

    # Build workdir → project name mapping from discovered projects
    proj_path_map: dict[str, str] = {}  # lowercased project path → display name
    for p in get_all_projects():
        p_path = (p.get("path") or "").rstrip("/").lower()
        if p_path:
            proj_path_map[p_path] = p.get("name") or p.get("id", p_path.rsplit("/", 1)[-1])
        # Also index by parent-less basename (for Codex workdirs like /Users/chao/projects/echo-chao)
        p_base = p_path.rsplit("/", 1)[-1] if "/" in p_path else ""
        if p_base and p_base not in proj_path_map:
            proj_path_map[p_base] = p.get("name") or p.get("id", p_base)

    # Manual fallback for Codex workdirs not in Mira's scan scope
    # Maps: Codex workdir basename → Mira project name
    _MANUAL_ALIAS: dict[str, str] = {
        "echo-chao": "minion-agent",
        "simulacra": "minion-agent",
        "feishu-coo": "minion-agent",
        "feishu-ai-assistant": "minion-agent",
        "vibe-cli": "Mira",
        "ai-investment-dashboard": "Argus",
    }
    proj_path_map.update({k: v for k, v in _MANUAL_ALIAS.items() if k not in proj_path_map})
    _KNOWN_WORKDIR_PATHS = {
        "/users/chao/ai-investment-dashboard": "Argus",
    }
    proj_path_map.update(_KNOWN_WORKDIR_PATHS)

    def _match_workdir_to_project(wd: str) -> str | None:
        """Find the Mira project that this workdir belongs to."""
        wd_lower = wd.rstrip("/").lower()
        # Exact path match
        for p_path, p_name in proj_path_map.items():
            if wd_lower == p_path or wd_lower.startswith(p_path + "/"):
                return p_name
            if p_path.startswith(wd_lower + "/"):
                return p_name
        # Basename match
        base = wd_lower.rsplit("/", 1)[-1]
        return proj_path_map.get(base)

    # Per-project breakdown: group sessions by Mira project name
    proj_stats: dict[str, dict] = {}
    unclassified = {"sessions": 0, "input": 0, "output": 0, "cached": 0}

    for f in _all_jsonl_files():
        wd = _get_session_workdir(f)
        parsed = _parse_session(f)
        tok = parsed.get("tokens", {})
        inp = tok.get("input", 0)
        out = tok.get("output", 0)
        cached = tok.get("cached_input", 0)

        if wd:
            proj_name = _match_workdir_to_project(wd)
            if proj_name is None:
                proj_name = wd.rsplit("/", 1)[-1]  # fallback to raw basename
            if proj_name not in proj_stats:
                proj_stats[proj_name] = {"sessions": 0, "input": 0, "output": 0, "cached": 0}
            proj_stats[proj_name]["sessions"] += 1
            proj_stats[proj_name]["input"] += inp
            proj_stats[proj_name]["output"] += out
            proj_stats[proj_name]["cached"] += cached
        else:
            unclassified["sessions"] += 1
            unclassified["input"] += inp
            unclassified["output"] += out
            unclassified["cached"] += cached

    # Build heatmap: daily session count for last 365 days
    from datetime import date as _date, timedelta
    day_counts: dict[str, int] = {}
    for f in _all_jsonl_files():
        try:
            mtime = f.stat().st_mtime
            from datetime import datetime as _dt
            d = _dt.fromtimestamp(mtime).strftime("%Y-%m-%d")
            day_counts[d] = day_counts.get(d, 0) + 1
        except OSError:
            pass

    heatmap: dict[str, dict] = {}
    for i in range(365):
        d = (_date.today() - timedelta(days=364 - i)).isoformat()
        cnt = day_counts.get(d, 0)
        if cnt > 0:
            heatmap[d] = {"hours": float(cnt), "sessions": cnt}

    # Per-project cost for top-5 trend
    cx_price_in = 15.0 / 1e6
    cx_price_cached = 7.5 / 1e6
    cx_price_out = 75.0 / 1e6
    proj_trend = []
    for pname, ps in proj_stats.items():
        non_cached = max(ps["input"] - ps["cached"], 0)
        cost = non_cached * cx_price_in + ps["cached"] * cx_price_cached + ps["output"] * cx_price_out
        proj_trend.append({
            "project_name": pname,
            "total_cost_usd": round(cost, 2),
            "sessions": ps["sessions"],
        })
    proj_trend.sort(key=lambda x: -x["total_cost_usd"])

    if isinstance(data, dict):
        data["projects"] = proj_stats
        data["unclassified"] = unclassified
        data["heatmap"] = heatmap
        data["project_trend"] = proj_trend[:10]
    return data if data else {}


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
    """Lightweight 30s liveness check for /ws/status. Returns {project_id: {is_running, port, ...}}.

    复用 _cache 拿项目列表与已解析端口，只做一次 TCP 探活；不再每30s扫盘
    (discover_projects) 也不跑完整 collect_service(全进程遍历 + 串行域名HTTPS探测)。
    端口/进程名/domain_ok 取自 120s 全量重建的快照即可——前端这个推送只用 is_running 和 port。"""
    result = {}
    for p in get_all_projects():
        svc = p.get("service") or {}
        port = svc.get("port")
        pid = p.get("id") or Path(p["path"]).name
        # 有端口就实时 TCP 探活；无端口的服务回落到缓存里的 is_running
        is_running = _check_port(port) if port else bool(svc.get("is_running"))
        result[pid] = {
            "is_running": is_running,
            "port": port,
            "process_name": svc.get("process_name"),
            "domain_ok": svc.get("domain_ok"),
        }
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
    from .balance import fetch_openrouter_activity, get_balance_activity_all
    from .config import load_global_config
    # OpenRouter has its own precise activity API
    or_data = fetch_openrouter_activity(load_global_config(), force=force)
    # Other providers: computed from balance snapshots
    snap_data = get_balance_activity_all()
    # Merge: OpenRouter API data takes precedence over snapshot-based
    result = dict(snap_data)
    if or_data:
        result["openrouter"] = or_data
    if _is_admin(request):
        return result
    # Non-admin: mask amounts
    masked = {}
    for pid, rows in result.items():
        masked[pid] = [{"date": r["date"], "cost_usd": 0} for r in (rows or [])]
    masked["_masked"] = True
    return masked


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
    out = {"admin": _is_admin(request), "auth_required": token is not None}
    if not out["admin"]:
        principal = _get_principal(request)
        if principal and principal[0] == "sub":
            acc = principal[1]
            out["sub"] = {
                "name": acc.get("name") or "",
                "avatar": acc.get("avatar") or "",
                "projects": acc.get("projects") or [],
            }
    return out


@api.get("/api/hosts")
def list_hosts(request: Request):
    """返回远程主机连接状态列表。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return [h.status_dict() for h in _remote_hosts]


# ── Settings (API keys stored in vibe.yaml) ────────────────────────────────────
_SETTINGS_KEYS = ["openrouter_api_key", "deepseek_api_key", "kimi_api_key", "gemini_api_key", "doubao_api_key", "doubao_access_key", "doubao_secret_key"]


def _mask_key(val: str) -> str:
    if not val:
        return ""
    if len(val) <= 6:
        return "****"
    return val[:6] + "****"


_vibe_yaml_cache: dict = {"mtime": None, "data": None}
# 保护 _vibe_yaml_cache + 提供原子 read-modify-write(见 _mutate_vibe_yaml)。
# 用 RLock:_mutate 持锁时内部还会调 _read/_write(各自再取锁),需可重入。
_vibe_yaml_lock = threading.RLock()


def _read_vibe_yaml() -> tuple[Path, dict]:
    import yaml
    import copy
    cfg_path = Path(__file__).parent.parent / "vibe.yaml"
    if not cfg_path.exists():
        return cfg_path, {}
    # 按 mtime 缓存已解析结果，避免每次(含 5~8s 轮询)重读+解析 6.7KB yaml。
    # 返回 deepcopy：调用方常做 read→mutate→write，独立副本可防止改动污染缓存。
    mt = cfg_path.stat().st_mtime
    with _vibe_yaml_lock:
        if _vibe_yaml_cache["mtime"] == mt:
            return cfg_path, copy.deepcopy(_vibe_yaml_cache["data"])
        data = yaml.safe_load(cfg_path.read_text()) or {}
        _vibe_yaml_cache["mtime"] = mt
        _vibe_yaml_cache["data"] = data
        return cfg_path, copy.deepcopy(data)


def _write_vibe_yaml(cfg_path: Path, data: dict) -> None:
    import yaml
    import copy
    with _vibe_yaml_lock:
        cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
        # mtime 已变，下次 _read_vibe_yaml 会重新解析；这里顺手刷新缓存避免一次多余解析
        try:
            _vibe_yaml_cache["mtime"] = cfg_path.stat().st_mtime
            _vibe_yaml_cache["data"] = copy.deepcopy(data)
        except Exception:
            _vibe_yaml_cache["mtime"] = None
    from .config import invalidate_config_cache
    invalidate_config_cache()


def _mutate_vibe_yaml(mutate):
    """原子 read-modify-write vibe.yaml:在锁内读→改→写,防并发 lost update。
    mutate(data) 就地修改 data,其返回值原样返回。所有需要改 vibe.yaml 的写路径
    都应走这里(而不是各自散开的 _read_vibe_yaml + _write_vibe_yaml)。"""
    with _vibe_yaml_lock:
        cfg_path, data = _read_vibe_yaml()
        result = mutate(data)
        _write_vibe_yaml(cfg_path, data)
        return result


# ── Keys Vault CRUD ──────────────────────────────────────────────────────────

@api.get("/api/settings/keys")
def list_keys(request: Request):
    """列出所有密钥（值脱敏）。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from .config import load_global_config
    cfg = load_global_config()
    keys = cfg.get("keys", [])
    return {"keys": [{
        "id": k.get("id", ""),
        "name": k.get("name", ""),
        "category": k.get("category", "other"),
        "key": _mask_key(k.get("key", "")),
        "note": k.get("note", ""),
        "env_name": k.get("env_name", ""),
    } for k in keys]}


@api.post("/api/settings/keys")
def add_key(request: Request, body: dict):
    """添加新密钥。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    name = (body.get("name") or "").strip()
    key_val = (body.get("key") or "").strip()
    if not name or not key_val:
        raise HTTPException(status_code=400, detail="name 和 key 为必填项")
    category = (body.get("category") or "other").strip()
    note = (body.get("note") or "").strip()
    key_id = uuid.uuid4().hex[:8]
    cfg_path, data = _read_vibe_yaml()
    keys = data.get("keys", [])
    env_name = (body.get("env_name") or "").strip()
    keys.append({"id": key_id, "name": name, "category": category, "key": key_val, "note": note, "env_name": env_name})
    data["keys"] = keys
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True, "id": key_id}


@api.put("/api/settings/keys/{key_id}")
def update_key(request: Request, key_id: str, body: dict):
    """更新密钥。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    keys = data.get("keys", [])
    target = None
    for k in keys:
        if k.get("id") == key_id:
            target = k
            break
    if not target:
        raise HTTPException(status_code=404, detail="未找到该密钥")
    if "name" in body:
        target["name"] = (body["name"] or "").strip()
    if "category" in body:
        target["category"] = (body["category"] or "other").strip()
    if "key" in body:
        v = (body["key"] or "").strip()
        if v and not v.endswith("****"):
            target["key"] = v
    if "note" in body:
        target["note"] = (body["note"] or "").strip()
    if "env_name" in body:
        target["env_name"] = (body["env_name"] or "").strip()
    data["keys"] = keys
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


@api.delete("/api/settings/keys/{key_id}")
def delete_key(request: Request, key_id: str):
    """删除密钥。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    keys = data.get("keys", [])
    new_keys = [k for k in keys if k.get("id") != key_id]
    if len(new_keys) == len(keys):
        raise HTTPException(status_code=404, detail="未找到该密钥")
    data["keys"] = new_keys
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


# ── Deployments CRUD (集中部署文档) ──────────────────────────────────────────

@api.get("/api/deployments")
def list_deployments(request: Request):
    """列出所有部署条目 + 静态检测结果。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from .config import load_global_config
    from .deploy_check import find_port_conflicts, find_missing_dependencies, reverse_impact
    cfg = load_global_config()
    deployments = cfg.get("deployments", [])
    base_services = cfg.get("base_services", [])
    return {
        "deployments": deployments,
        "base_services": base_services,
        "port_conflicts": find_port_conflicts(deployments, base_services),
        "missing_deps": find_missing_dependencies(deployments, base_services),
        "reverse_impact": reverse_impact(deployments, base_services),
    }


@api.post("/api/deployments")
def add_deployment(request: Request, body: dict):
    """新增部署条目;project 必填且唯一。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    project = (body.get("project") or "").strip()
    if not project:
        raise HTTPException(status_code=400, detail="project 为必填项")
    cfg_path, data = _read_vibe_yaml()
    deployments = data.get("deployments", [])
    if any(d.get("project") == project for d in deployments):
        raise HTTPException(status_code=400, detail="该项目已存在部署条目")
    from .models import Deployment
    from pydantic import ValidationError
    try:
        model = Deployment(
            project=project,
            ports=body.get("ports") or [],
            depends_on=body.get("depends_on") or [],
            domain=(body.get("domain") or "").strip() or None,
            deploy=body.get("deploy") or None,
            notes=body.get("notes") or "",
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    entry = model.model_dump()
    deployments.append(entry)
    data["deployments"] = deployments
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True, "project": project}


@api.put("/api/deployments/{project}")
def update_deployment(request: Request, project: str, body: dict):
    """更新指定项目的部署条目。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    deployments = data.get("deployments", [])
    target = next((d for d in deployments if d.get("project") == project), None)
    if not target:
        raise HTTPException(status_code=404, detail="未找到该部署条目")
    if "ports" in body:
        try:
            target["ports"] = [int(p) for p in (body["ports"] or [])]
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="ports 必须是整数列表")
    if "depends_on" in body:
        target["depends_on"] = body["depends_on"]
    if "deploy" in body:
        target["deploy"] = body["deploy"]
    if "domain" in body:
        target["domain"] = (body["domain"] or "").strip() or None
    if "notes" in body:
        target["notes"] = body["notes"] or ""
    data["deployments"] = deployments
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


@api.delete("/api/deployments/{project}")
def delete_deployment(request: Request, project: str):
    """删除指定项目的部署条目。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    deployments = data.get("deployments", [])
    new_list = [d for d in deployments if d.get("project") != project]
    if len(new_list) == len(deployments):
        raise HTTPException(status_code=404, detail="未找到该部署条目")
    data["deployments"] = new_list
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


# ── Key Distribution API ─────────────────────────────────────────────────────

@api.get("/v1/keys/{project_id}")
def distribute_keys(request: Request, project_id: str):
    """Return bound keys for a project as env_name→value map."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    # Find project and its bound_keys
    projects = get_all_projects()
    proj = next((p for p in projects if p.get("id") == project_id or p.get("name") == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="未找到该项目")
    import yaml as _yaml
    proj_path = Path(proj["path"])
    vibe_yaml = proj_path / "vibe.yaml"
    proj_cfg = _yaml.safe_load(vibe_yaml.read_text()) if vibe_yaml.exists() else {}
    bound_ids = proj_cfg.get("bound_keys", [])
    if not bound_ids:
        return {}
    # Look up keys from vault
    from .config import load_global_config
    all_keys = load_global_config().get("keys", [])
    result = {}
    for k in all_keys:
        if k.get("id") in bound_ids and k.get("env_name"):
            result[k["env_name"]] = k["key"]
    return result


@api.post("/api/settings/projects/{project_id}/sync-keys")
def sync_keys_to_env(request: Request, project_id: str):
    """Write bound keys into project's .env file."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    proj_path = _resolve_project_path(request, project_id)
    import yaml as _yaml
    vibe_yaml = proj_path / "vibe.yaml"
    proj_cfg = _yaml.safe_load(vibe_yaml.read_text()) if vibe_yaml.exists() else {}
    bound_ids = proj_cfg.get("bound_keys", [])
    if not bound_ids:
        return {"ok": True, "synced": 0, "message": "无绑定密钥"}
    from .config import load_global_config
    all_keys = load_global_config().get("keys", [])
    key_map = {}
    for k in all_keys:
        if k.get("id") in bound_ids and k.get("env_name"):
            key_map[k["env_name"]] = k["key"]
    if not key_map:
        return {"ok": True, "synced": 0, "message": "绑定的密钥未设置变量名"}
    # Read existing .env, update/append
    env_file = proj_path / ".env"
    lines = []
    existing_keys = set()
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0]
                if k in key_map:
                    lines.append(f"{k}={key_map[k]}")
                    existing_keys.add(k)
                    continue
            lines.append(line)
    # Append new keys
    for k, v in key_map.items():
        if k not in existing_keys:
            lines.append(f"{k}={v}")
    env_file.write_text("\n".join(lines) + "\n")
    return {"ok": True, "synced": len(key_map), "keys": list(key_map.keys())}


# ── Project Config API ───────────────────────────────────────────────────────

@api.get("/api/settings/projects/{project_id}/config")
def get_project_config(request: Request, project_id: str):
    """读取项目 vibe.yaml 配置。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects()
    proj = None
    for p in projects:
        if p.get("id") == project_id or p.get("name") == project_id:
            proj = p
            break
    if not proj:
        raise HTTPException(status_code=404, detail="未找到该项目")
    import yaml
    proj_path = Path(proj["path"])
    vibe_yaml = proj_path / "vibe.yaml"
    data = {}
    if vibe_yaml.exists():
        data = yaml.safe_load(vibe_yaml.read_text()) or {}
    return {
        "name": data.get("name", proj.get("name", "")),
        "description": data.get("description", ""),
        "domain": data.get("domain", ""),
        "status": data.get("status", ""),
        "service": data.get("service", ""),
        "deploy": data.get("deploy", ""),
        "bound_keys": data.get("bound_keys", []),
        "raw_yaml": vibe_yaml.read_text() if vibe_yaml.exists() else "",
    }


@api.put("/api/settings/projects/{project_id}/config")
def save_project_config(request: Request, project_id: str, body: dict):
    """保存项目 vibe.yaml 配置。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects()
    proj = None
    for p in projects:
        if p.get("id") == project_id or p.get("name") == project_id:
            proj = p
            break
    if not proj:
        raise HTTPException(status_code=404, detail="未找到该项目")
    import yaml
    proj_path = Path(proj["path"])
    vibe_yaml = proj_path / "vibe.yaml"
    if "raw_yaml" in body and body["raw_yaml"].strip():
        # Raw YAML mode: write directly
        vibe_yaml.write_text(body["raw_yaml"])
    else:
        data = {}
        if vibe_yaml.exists():
            data = yaml.safe_load(vibe_yaml.read_text()) or {}
        for field in ("name", "description", "domain", "status", "service", "deploy", "bound_keys"):
            if field in body:
                data[field] = body[field]
        vibe_yaml.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    return {"ok": True}


# ── Project Env Files API ────────────────────────────────────────────────────

def _resolve_project_path(request: Request, project_id: str) -> Path:
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = get_all_projects()
    proj = next((p for p in projects if p.get("id") == project_id or p.get("name") == project_id), None)
    if not proj:
        raise HTTPException(status_code=404, detail="未找到该项目")
    return Path(proj["path"])

_ENV_PATTERNS = {".env", ".env.local", ".env.production", ".env.development", ".env.staging", ".env.test"}
_ENV_EXCLUDE = {".env.example", ".env.sample", ".env.template"}


def _is_valid_env_filename(name: str) -> bool:
    """与 get_env_files 的列举判定保持一致：只接受 .env 系列文件，
    防止 save 接口被用来覆写 vibe.yaml / main.py 等任意文件。"""
    if not name or ".." in name or "/" in name:
        return False
    return name in _ENV_PATTERNS or (name.startswith(".env.") and name not in _ENV_EXCLUDE)

@api.get("/api/settings/projects/{project_id}/env-files")
def get_env_files(request: Request, project_id: str, reveal: bool = False):
    """List .env files with key-value pairs."""
    proj_path = _resolve_project_path(request, project_id)
    result = []
    for f in sorted(proj_path.iterdir()):
        if not f.is_file():
            continue
        if f.name not in _ENV_PATTERNS and not (f.name.startswith(".env.") and f.name not in _ENV_EXCLUDE):
            continue
        if f.name in _ENV_EXCLUDE:
            continue
        entries = []
        for line in f.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                entries.append({"type": "comment", "text": line})
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                entries.append({"type": "kv", "key": k, "value": v if reveal else "••••••"})
            else:
                entries.append({"type": "comment", "text": line})
        result.append({"filename": f.name, "entries": entries})
    return result


@api.put("/api/settings/projects/{project_id}/env-files")
def save_env_file(request: Request, project_id: str, body: dict):
    """Save a single .env file."""
    proj_path = _resolve_project_path(request, project_id)
    filename = body.get("filename", "")
    if not _is_valid_env_filename(filename):
        raise HTTPException(status_code=400, detail="只允许写入 .env 系列文件")
    entries = body.get("entries", [])
    lines = []
    for e in entries:
        if e.get("type") == "comment":
            lines.append(e.get("text", ""))
        else:
            lines.append(f"{e['key']}={e['value']}")
    (proj_path / filename).write_text("\n".join(lines) + "\n")
    return {"ok": True}


# ── Project Config Files API ─────────────────────────────────────────────────

_CONFIG_PATTERNS = {"config.json", "config.yaml", "config.yml", "config.toml",
                    "settings.json", "settings.yaml", "settings.yml"}
_CONFIG_EXCLUDE_DIRS = {"node_modules", ".venv", "__pycache__", ".git", "dist", "build", ".next"}
_CONFIG_EXCLUDE_FILES = {"package.json", "tsconfig.json", "pyproject.toml", "Cargo.toml",
                         "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}

@api.get("/api/settings/projects/{project_id}/config-files")
def get_config_files(request: Request, project_id: str):
    """List config files with content."""
    proj_path = _resolve_project_path(request, project_id)
    result = []
    def _scan(directory: Path, depth: int = 0):
        if depth > 1:
            return
        try:
            items = sorted(directory.iterdir())
        except PermissionError:
            return
        for f in items:
            if f.is_dir() and depth == 0 and f.name not in _CONFIG_EXCLUDE_DIRS:
                _scan(f, depth + 1)
                continue
            if not f.is_file() or f.name in _CONFIG_EXCLUDE_FILES:
                continue
            if f.name in _CONFIG_PATTERNS:
                rel = str(f.relative_to(proj_path))
                try:
                    content = f.read_text(errors="replace")
                except Exception:
                    continue
                result.append({
                    "filename": rel,
                    "size": f.stat().st_size,
                    "content": content,
                })
    _scan(proj_path)
    return result


@api.put("/api/settings/projects/{project_id}/config-files")
def save_config_file(request: Request, project_id: str, body: dict):
    """Save a config file."""
    proj_path = _resolve_project_path(request, project_id)
    filename = body.get("filename", "")
    content = body.get("content", "")
    if not filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    target = (proj_path / filename).resolve()
    if not str(target).startswith(str(proj_path.resolve())):
        raise HTTPException(status_code=400, detail="Path traversal blocked")
    target.write_text(content)
    return {"ok": True}


# ── System Lists API ─────────────────────────────────────────────────────────

@api.get("/api/settings/system-lists")
def get_system_lists(request: Request):
    """返回扫描目录和排除列表。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from .config import load_global_config
    cfg = load_global_config()
    return {
        "scan_dirs": cfg.get("scan_dirs", []),
        "exclude": cfg.get("exclude", []),
    }


@api.post("/api/settings/system-lists")
def save_system_lists(request: Request, body: dict):
    """保存扫描目录和排除列表到 vibe.yaml。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    cfg_path, data = _read_vibe_yaml()
    if "scan_dirs" in body:
        data["scan_dirs"] = body["scan_dirs"]
    if "exclude" in body:
        data["exclude"] = body["exclude"]
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


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
    _write_vibe_yaml(cfg_path, data)   # 统一写:刷新缓存 + 持写锁 + invalidate_config_cache
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
    _write_vibe_yaml(cfg_path, data)
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
    _write_vibe_yaml(cfg_path, data)
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


@api.get("/api/session/{session_id}/turns")
def session_turns_view(request: Request, session_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.history_db import analyze_session_turns
    return analyze_session_turns(session_id)


@api.get("/api/top-sessions")
def top_sessions_view(request: Request, sort: str = "cost", limit: int = 100):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    limit = max(1, min(limit, 500))
    sort_by = "hours" if sort == "hours" else "cost"
    from vibe.history_db import get_top_sessions
    return get_top_sessions(sort_by=sort_by, limit=limit)


@api.get("/api/top-codex-sessions")
def top_codex_sessions_view(request: Request, sort: str = "cost", limit: int = 100):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    limit = max(1, min(limit, 500))
    sort_by = "active_hours" if sort == "hours" else "estimated_cost_usd"
    from vibe.collectors.codex_sessions import get_top_codex_sessions
    return get_top_codex_sessions(sort_by=sort_by, limit=limit)


@api.get("/api/codex-session/turns")
def codex_session_turns_view(request: Request, path: str = ""):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    # Security: ensure the path doesn't escape CODEX_DIR
    from vibe.collectors.codex_sessions import CODEX_DIR, analyze_codex_session_turns
    try:
        resolved = (CODEX_DIR / path).resolve()
        if not str(resolved).startswith(str(CODEX_DIR.resolve())):
            raise HTTPException(status_code=403, detail="禁止访问")
    except Exception:
        raise HTTPException(status_code=400, detail="无效路径")
    return analyze_codex_session_turns(path)


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
    # 子账号会话标记:tmux session 名是 sub-<openid>,映射回子账号显示名
    _, _vy = _read_vibe_yaml()
    sub_sessions = {}
    for acc in (_vy.get("accounts") or []):
        oid = acc.get("feishu_open_id")
        if oid:
            sub_sessions[_sub_session_name(oid)] = acc
    all_panes = list_panes()
    result = []
    for p in all_panes:
        target = p["target"]
        sess = p.get("session", "")
        is_sub = sess.startswith("sub-")
        sub_acc = sub_sessions.get(sess)
        sub_name = (sub_acc.get("name") or sub_acc.get("feishu_open_id")) if sub_acc else None
        sub_avatar = sub_acc.get("avatar") if sub_acc else None
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
        # 子账号 badge 只在该 pane 的项目仍授权给该子账号时显示。取消授权后,进程仍在
        # sub session 里跑着(不杀),但不再标记归属——撤销后不该再把项目和该子账号关联。
        if is_sub and sub_acc and project_id not in (sub_acc.get("projects") or []):
            is_sub = False
            sub_name = None
            sub_avatar = None
        # Detect tool type from terminal_monitor's resolved command
        mon_cmd = mon.get("command", "")
        if mon_cmd == "codex":
            tool = "codex"
        elif mon_cmd == "claude":
            tool = "claude"
        else:
            tool = None
        result.append({
            "target": target,
            "label": label,
            "command": p["command"],
            "cwd": p["cwd"],
            "waiting": mon.get("waiting", False),
            "project_id": project_id,
            "project_name": project_name,
            "tool": tool,
            "sub": is_sub,
            "sub_name": sub_name,
            "sub_avatar": sub_avatar,
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


# ── Dev 侧栏:项目合并分组 + 自定义命名(纯展示,存 vibe.yaml)──────────────────

@api.get("/api/dev/groups")
def get_dev_groups(request: Request):
    """返回 dev 侧栏分组/命名/排序。{groups, names, order:[顶层key,...]}"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    _, data = _read_vibe_yaml()
    return {"groups": data.get("dev_groups", []),
            "names": data.get("dev_project_names", {}),
            "order": data.get("dev_order", [])}


@api.post("/api/dev/order")
def set_dev_order(request: Request, body: dict):
    """保存 dev 侧栏顶层项排序。order 是 key 列表(项目=project_id,文件夹='folder:'+id)。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    order = body.get("order")
    if not isinstance(order, list):
        raise HTTPException(status_code=400, detail="order 必须是列表")
    cfg_path, data = _read_vibe_yaml()
    data["dev_order"] = [str(x) for x in order]
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


@api.post("/api/dev/groups/merge")
def merge_dev_groups(request: Request, body: dict):
    """把 source 项目并入 target 所在文件夹(没有则新建)。纯展示分组,不动项目本身。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    source = (body.get("source") or "").strip()
    target = (body.get("target") or "").strip()
    if not source or not target or source == target:
        raise HTTPException(status_code=400, detail="source/target 无效")
    cfg_path, data = _read_vibe_yaml()
    groups = data.get("dev_groups", [])
    # 先把 source 从它当前所在文件夹移除(支持跨文件夹拖拽)
    for g in groups:
        if source in g.get("projects", []):
            g["projects"].remove(source)
    tgt = next((g for g in groups if target in g.get("projects", [])), None)
    if tgt:
        if source not in tgt["projects"]:
            tgt["projects"].append(source)
    else:
        groups.append({"id": secrets.token_urlsafe(8),
                       "name": (body.get("name") or "新分组").strip(),
                       "projects": [target, source]})
    # 解散只剩 ≤1 个项目的空壳文件夹
    groups = [g for g in groups if len(g.get("projects", [])) >= 2]
    data["dev_groups"] = groups
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True, "groups": groups}


@api.post("/api/dev/groups/unmerge")
def unmerge_dev_group(request: Request, body: dict):
    """把一个项目从所在文件夹移出;文件夹剩 ≤1 个项目时解散。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    project = (body.get("project") or "").strip()
    cfg_path, data = _read_vibe_yaml()
    groups = data.get("dev_groups", [])
    for g in groups:
        if project in g.get("projects", []):
            g["projects"].remove(project)
    groups = [g for g in groups if len(g.get("projects", [])) >= 2]
    data["dev_groups"] = groups
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True, "groups": groups}


@api.post("/api/dev/groups/rename")
def rename_dev_group(request: Request, body: dict):
    """重命名合并文件夹。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    gid = (body.get("id") or "").strip()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name 必填")
    cfg_path, data = _read_vibe_yaml()
    groups = data.get("dev_groups", [])
    g = next((g for g in groups if g.get("id") == gid), None)
    if not g:
        raise HTTPException(status_code=404, detail="分组不存在")
    g["name"] = name
    data["dev_groups"] = groups
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


@api.post("/api/dev/project-name")
def set_dev_project_name(request: Request, body: dict):
    """给项目设/清 dev 侧栏自定义显示名。name 为空则清除。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    pid = (body.get("project_id") or "").strip()
    name = (body.get("name") or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="project_id 必填")
    cfg_path, data = _read_vibe_yaml()
    names = data.get("dev_project_names", {})
    if name:
        names[pid] = name
    else:
        names.pop(pid, None)
    data["dev_project_names"] = names
    _write_vibe_yaml(cfg_path, data)
    return {"ok": True}


# ── 子账号(多用户):owner 管理 + 子账号作用域受限访问 ──────────────────────────

@api.get("/api/accounts")
def list_accounts(request: Request):
    """owner 列出所有子账号(含 pending,用于审批)。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    _, data = _read_vibe_yaml()
    return data.get("accounts", [])


def _update_account(open_id: str, mutate):
    """原子 read-modify-write:对匹配 open_id 的账号执行 mutate,写回。找不到则 404。"""
    def _do(data):
        accounts_list = data.get("accounts", [])
        acc = next((a for a in accounts_list if a.get("feishu_open_id") == open_id), None)
        if not acc:
            raise HTTPException(status_code=404, detail="账号不存在")
        mutate(acc)
        data["accounts"] = accounts_list
    _mutate_vibe_yaml(_do)
    return {"ok": True}


@api.post("/api/accounts/{open_id}/approve")
def approve_account(request: Request, open_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return _update_account(open_id, lambda a: a.update(status="active"))


@api.post("/api/accounts/{open_id}/disable")
def disable_account(request: Request, open_id: str):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    return _update_account(open_id, lambda a: a.update(status="disabled"))


@api.put("/api/accounts/{open_id}/projects")
def set_account_projects(request: Request, open_id: str, body: dict):
    """设置某子账号被授权的项目列表。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    projects = body.get("projects")
    if not isinstance(projects, list):
        raise HTTPException(status_code=400, detail="projects 必须是列表")
    return _update_account(open_id, lambda a: a.update(projects=[str(p) for p in projects]))


@api.get("/api/sub/me")
def sub_me(request: Request):
    """子账号:返回自己的信息 + 被授权项目。"""
    principal = _get_principal(request)
    if not principal or principal[0] != "sub":
        raise HTTPException(status_code=401, detail="需要子账号登录")
    acc = principal[1]
    return {"name": acc.get("name"), "avatar": acc.get("avatar"),
            "projects": acc.get("projects") or []}


# ── 子账号专属沙箱会话(每子账号一个 tmux session,进项目起加固 claude)──────────

_HARDENED_SETTINGS = str(Path(__file__).parent / "sub_claude_settings.json")
_SUB_LOOP = str(Path(__file__).parent / "sub_claude_loop.sh")


def _sub_session_name(open_id: str) -> str:
    """每个子账号一个独立 tmux session,天然隔离(他只能碰自己 session 的窗口)。"""
    return "sub-" + re.sub(r"[^A-Za-z0-9_]", "", open_id)[:16]


def _project_path(project_id: str):
    for p in get_all_projects():
        if p.get("id") == project_id:
            return p.get("path")
    return None


def _tmux_run(*args):
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    return subprocess.run([_TMUX_BIN, *args], env=_TMUX_ENV, capture_output=True, text=True)


def _sub_claude_cmd(path: str) -> str:
    """子账号窗口的 pane 命令:外壳脚本(claude 退出即重开,背后无裸 shell)。"""
    import shlex
    return f"{shlex.quote(_SUB_LOOP)} {shlex.quote(path)} {shlex.quote(_HARDENED_SETTINGS)}"


def _harden_sub_session(sess: str) -> None:
    """让可写 tmux attach 也逃不出去:禁用 prefix —— Ctrl-B 不再能开 shell 窗口或跑 tmux 命令。"""
    _tmux_run("set-option", "-t", sess, "prefix", "None")
    _tmux_run("set-option", "-t", sess, "prefix2", "None")
    _tmux_run("set-option", "-t", sess, "status", "off")


def _ensure_sub_session(open_id: str, project_id: str):
    """确保 (子账号, 项目) 有一个加固 claude 窗口,返回 pane target;失败 None。

    窗口的 pane 命令直接是外壳脚本(无交互 shell);session 级禁用 tmux prefix。
    两层加固保证:子账号即便拿到可写终端,也退不出 claude、开不了裸 shell。"""
    path = _project_path(project_id)
    if not path or not Path(path).is_dir():
        return None
    # 时间推断归属:记录该子账号此刻在此项目活跃(见 history_db.get_sub_account_audit)
    try:
        from vibe.history_db import record_sub_activity
        record_sub_activity(open_id, project_id)
    except Exception:
        pass
    sess = _sub_session_name(open_id)
    win = re.sub(r"[^A-Za-z0-9_-]", "", project_id)[:24] or "proj"
    lw = _tmux_run("list-windows", "-t", sess, "-F", "#{window_name}\t#{window_index}")
    if lw.returncode == 0:
        for line in lw.stdout.splitlines():
            nm, _, idx = line.partition("\t")
            if nm == win:
                return f"{sess}:{idx}.0"   # 已有,复用
    cmd = _sub_claude_cmd(path)
    if _tmux_run("has-session", "-t", sess).returncode != 0:
        r = _tmux_run("new-session", "-d", "-s", sess, "-n", win, "-c", path,
                      "-P", "-F", "#{window_index}", cmd)
        _harden_sub_session(sess)
    else:
        r = _tmux_run("new-window", "-t", sess, "-n", win, "-c", path,
                      "-P", "-F", "#{window_index}", cmd)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return f"{sess}:{r.stdout.strip()}.0"


def _sub_target_project(open_id: str, target: str):
    """target 必须属于该子账号自己的 session;返回其 cwd 对应的 project_id,否则 None。
    双重保险:既校验 session 归属(隔离),又把 pane 当前目录映射回项目(配合授权校验)。"""
    if target.split(":")[0] != _sub_session_name(open_id):
        return None
    r = _tmux_run("display-message", "-t", target, "-p", "#{pane_current_path}")
    if r.returncode != 0:
        return None
    cwd = r.stdout.strip()
    best = None
    for p in get_all_projects():
        pp = p.get("path") or ""
        if pp and (cwd == pp or cwd.startswith(pp + "/")):
            if best is None or len(pp) > len(best[1]):
                best = (p["id"], pp)
    return best[0] if best else None


@api.get("/api/sub/projects")
def sub_projects(request: Request):
    """子账号:被授权且当前存在的项目列表。"""
    principal = _get_principal(request)
    if not principal or principal[0] != "sub":
        raise HTTPException(status_code=401, detail="需要子账号登录")
    granted = principal[1].get("projects") or []
    by_id = {p["id"]: p for p in get_all_projects()}
    return [{"id": pid, "name": by_id[pid].get("name", pid)} for pid in granted if pid in by_id]


@api.post("/api/sub/project/{project_id}/session")
def sub_open_session(request: Request, project_id: str, response: Response):
    """子账号:进入某授权项目 → 起/复用加固 claude 会话 + 只读 ttyd,返回 target 与终端端口。"""
    principal = _get_principal(request)
    if not principal or principal[0] != "sub":
        raise HTTPException(status_code=401, detail="需要子账号登录")
    from vibe.accounts import account_can_access_project
    if not account_can_access_project(principal[1], project_id):
        raise HTTPException(status_code=403, detail="无权访问该项目")
    open_id = principal[1]["feishu_open_id"]
    target = _ensure_sub_session(open_id, project_id)
    if not target:
        raise HTTPException(status_code=400, detail="项目不存在或无法创建会话")
    # 让只读 ttyd 显示这个项目的窗口
    _tmux_run("select-window", "-t", target.rsplit(".", 1)[0])
    port = _ensure_sub_ttyd(open_id)
    # 给只读终端代理发一个 cookie(= 子账号会话 token),供 /subterm 反代鉴权
    sub_tok = request.headers.get("X-Sub-Token") or ""
    if sub_tok:
        response.set_cookie("sub_term", sub_tok, path="/subterm", httponly=True,
                            samesite="lax", secure=True, max_age=7 * 24 * 3600)
    return {"target": target, "term_port": port,
            "term_base": (f"/subterm/{port}/" if port else None)}


@api.get("/api/sub/pane/{target:path}/output")
def sub_pane_output(request: Request, target: str, lines: int = 200):
    """子账号:读自己会话里某 pane 的输出(只读)。"""
    principal = _get_principal(request)
    if not principal or principal[0] != "sub":
        raise HTTPException(status_code=401, detail="需要子账号登录")
    from vibe.accounts import account_can_access_project
    pid = _sub_target_project(principal[1]["feishu_open_id"], target)
    if not pid or not account_can_access_project(principal[1], pid):
        raise HTTPException(status_code=403, detail="无权访问该终端")
    from vibe.tmux_bridge import capture_pane
    try:
        text = capture_pane(target, lines=lines)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"target": target, "output": text}


# ── claude 完整会话历史(读 ~/.claude 的 jsonl,终端画面之外的治本方案)──────────

def _claude_session_file(cwd: str):
    """pane cwd → ~/.claude/projects/<编码路径>/ 下最新修改的会话 jsonl;找不到返回 None。
    claude 的目录名编码 = 路径中非 [A-Za-z0-9-] 字符全部替换成 '-'。
    cwd 可能是项目子目录(用户 cd 过),逐级向上找存在的会话目录。"""
    base = Path.home() / ".claude" / "projects"
    p = Path(cwd)
    for cand in [p, *p.parents]:
        enc = re.sub(r"[^A-Za-z0-9-]", "-", str(cand))
        d = base / enc
        if d.is_dir():
            files = sorted(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                return files[0]
        if str(cand) == str(Path.home()):
            break
    return None


_UPLOAD_PATH_RE = re.compile(r"^/tmp/mira-uploads/[\w.\-]+$")
_UPLOAD_TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".log", ".py", ".js", ".ts", ".html", ".css"}


def _inline_upload(text: str, cap: int) -> str:
    """prompt 是 mira 上传文件的纯路径时,把文件内容内联进历史(真正的 prompt 在文件里)。
    只认 /tmp/mira-uploads/ 前缀,文本类内联,其余(图片等)只标注文件名。"""
    if not _UPLOAD_PATH_RE.match(text):
        return text
    p = Path(text)
    try:
        if not p.is_file():
            return text + "(上传文件已清理)"
        if p.suffix.lower() in _UPLOAD_TEXT_EXT and p.stat().st_size < 200_000:
            return "📎 " + p.name + "\n" + p.read_text(errors="replace")[: cap - 100]
        return "📎 上传文件: " + p.name
    except Exception:
        return text


def _parse_claude_turns(path: Path, agent: str | None = None) -> list[dict]:
    """把会话 jsonl 解析成轮次列表:user prompt 一轮,assistant 每个文字段落一轮。
    跳过 meta、tool_result 载体行。agent=None 时解析主时间线(跳过 sidechain 行);
    传 agent 标签时解析子代理文件(行都是 sidechain),轮次带 agent 字段。
    截断:user prompt(可能内联整份上传文档)60k;子代理的派发任务书 1500(模板化长文);
    assistant 单个文字段落 8k。"""
    import json
    turns: list[dict] = []
    cap = 8000
    user_cap = 60000 if not agent else 1500
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("isSidechain") and not agent:
                continue
            t = d.get("type")
            if t == "user":
                if d.get("isMeta"):
                    continue
                mc = (d.get("message") or {}).get("content")
                if isinstance(mc, str):
                    text = mc
                elif isinstance(mc, list):
                    if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in mc):
                        continue
                    text = "\n".join(x.get("text", "") for x in mc
                                     if isinstance(x, dict) and x.get("type") == "text")
                else:
                    continue
                text = (text or "").strip()
                # 斜杠命令/本地命令的 XML 包装行不算真实 prompt
                if not text or text.startswith("<"):
                    continue
                text = _inline_upload(text, user_cap)
                turn = {"role": "user", "text": text[:user_cap], "ts": d.get("timestamp", "")}
                if agent:
                    turn["agent"] = agent
                turns.append(turn)
            elif t == "assistant":
                blocks = ((d.get("message") or {}).get("content")) or []
                cur = turns[-1] if turns and turns[-1]["role"] == "assistant" else None
                for blk in blocks:
                    if not isinstance(blk, dict):
                        continue
                    if blk.get("type") == "text" and (blk.get("text") or "").strip():
                        # 每个文字段落独立成轮(不与之前的合并)——两条 prompt 之间可能有
                        # 几百条 assistant 输出(长时间自主干活),全并成一轮会截断成一团。
                        if cur is None or cur["text"]:
                            cur = {"role": "assistant", "text": "", "tools": {}, "ts": d.get("timestamp", "")}
                            if agent:
                                cur["agent"] = agent
                            turns.append(cur)
                        cur["text"] = blk["text"].strip()[:cap]
                    elif blk.get("type") == "tool_use":
                        if cur is None:
                            cur = {"role": "assistant", "text": "", "tools": {}, "ts": d.get("timestamp", "")}
                            if agent:
                                cur["agent"] = agent
                            turns.append(cur)
                        name = blk.get("name") or "?"
                        cur["tools"][name] = cur["tools"].get(name, 0) + 1
    return turns


_turns_cache: dict[str, tuple[float, float, list]] = {}   # sess_file -> (mtime戳, 缓存时刻, 轮次)


def _session_turns(sess_file: Path) -> list[dict]:
    """主时间线 + 子代理过程按时间戳合并成一条时间线。
    自主开发型会话的内容大头在子代理里(实测主文件 2MB vs subagents 5MB),
    只看主链会"只有一屏"。缓存避免重复解析几 MB:mtime 没变直接命中;
    活跃会话 mtime 一直在变,再给 30s 新鲜度窗口(历史晚 30s 无感,切换不卡)。"""
    import json
    sub_dir = sess_file.parent / sess_file.stem / "subagents"
    stamp = sess_file.stat().st_mtime
    if sub_dir.is_dir():
        stamp += sum(f.stat().st_mtime for f in sub_dir.glob("agent-*.jsonl"))
    key = str(sess_file)
    cached = _turns_cache.get(key)
    if cached and (cached[0] == stamp or time.time() - cached[1] < 30):
        return cached[2]
    turns = _parse_claude_turns(sess_file)
    if sub_dir.is_dir():
        for f in sorted(sub_dir.glob("agent-*.jsonl")):
            label = f.stem.removeprefix("agent-")[:8]
            try:
                meta = json.loads(f.with_name(f.stem + ".meta.json").read_text())
                label = meta.get("description") or meta.get("agentType") or label
            except Exception:
                pass
            turns.extend(_parse_claude_turns(f, agent=label))
        turns.sort(key=lambda t: t.get("ts") or "")
    if len(_turns_cache) > 8:                      # 只留最近几个会话的解析结果
        _turns_cache.pop(next(iter(_turns_cache)))
    _turns_cache[key] = (stamp, time.time(), turns)
    return turns


@api.get("/api/dev/pane-history")
def dev_pane_history(request: Request, target: str, before: int = 0, limit: int = 20):
    """claude pane 的完整会话历史(来自 ~/.claude jsonl,不受终端擦屏影响)。
    admin 看任意 pane;子账号只能看自己 session 里且被授权项目的 pane。
    分页:before=已取轮数(从最新往前翻),limit=本次轮数。"""
    principal = _get_principal(request)
    if not principal:
        raise HTTPException(status_code=401, detail="需要登录")
    if principal[0] == "sub":
        from vibe.accounts import account_can_access_project
        pid = _sub_target_project(principal[1]["feishu_open_id"], target)
        if not pid or not account_can_access_project(principal[1], pid):
            raise HTTPException(status_code=403, detail="无权访问该终端")
    r = _tmux_run("display-message", "-t", target, "-p", "#{pane_current_path}")
    if r.returncode != 0:
        raise HTTPException(status_code=404, detail="终端不存在")
    sess_file = _claude_session_file(r.stdout.strip())
    if not sess_file:
        raise HTTPException(status_code=404, detail="没有找到该项目的 claude 会话记录")
    turns = _session_turns(sess_file)
    total = len(turns)
    end = max(0, total - max(0, before))
    # 按"用户回合"分页:一页 = 最近 limit 条【主链】user prompt 及其间的全部内容
    # (含子代理过程)。若按轮数分页,一页 20 个小段落只剩几分钟的内容,观感像被截断。
    # 客户端游标(before)仍是"已消费的轮数",与本切片方式天然兼容。
    rounds = max(1, min(limit, 100))
    max_turns = 800   # 极端会话(自主长跑几乎没有 user 轮)的硬上限
    start, seen = end, 0
    while start > 0 and (end - start) < max_turns:
        start -= 1
        if turns[start]["role"] == "user" and not turns[start].get("agent"):
            seen += 1
            if seen >= rounds:
                break
    return {"turns": turns[start:end], "total": total, "has_more": start > 0,
            "session": sess_file.stem[:8]}


def _stream_backlog(target: str) -> str | None:
    """终端流的历史回放垫底:从会话 jsonl 组装终端风格文本(prompt 高亮/子代理
    缩进降级/工具摘要)。去掉最后一个回合——那部分正在实时屏上,避免和实时区重复。"""
    r = _tmux_run("display-message", "-t", target, "-p", "#{pane_current_path}")
    if r.returncode != 0:
        return None
    sess_file = _claude_session_file(r.stdout.strip())
    if not sess_file:
        return None
    turns = _session_turns(sess_file)
    last_user = None
    for i in range(len(turns) - 1, -1, -1):
        if turns[i]["role"] == "user" and not turns[i].get("agent"):
            last_user = i
            break
    if last_user is not None:
        turns = turns[:last_user]
    turns = turns[-150:]
    if not turns:
        return None
    out = []
    for t in turns:
        txt = (t.get("text") or "").strip()
        if t.get("agent"):
            if txt:
                out.append("\x1b[2m  ↳ [" + t["agent"][:40] + "] " + txt[:600] + "\x1b[0m")
        elif t["role"] == "user":
            out.append("")
            out.append("\x1b[1;36m❯ " + txt[:3000] + "\x1b[0m")
        elif txt:
            out.append(txt)
        tools = t.get("tools") or {}
        if tools:
            summ = " · ".join(k.split("__")[-1] + (f"×{v}" if v > 1 else "") for k, v in tools.items())
            out.append("\x1b[2m  ⚙ " + summ[:200] + "\x1b[0m")
    return ("\x1b[2m════ 历史回放(来自会话记录)════\x1b[0m\n"
            + "\n".join(out)
            + "\n\x1b[2m════ 以上历史 · 以下实时 ════\x1b[0m\n")


@api.post("/api/sub/pane/{target:path}/send")
def sub_pane_send(request: Request, target: str, body: dict):
    """子账号:向自己会话里的 claude 发一句话(消毒后补回车提交)。无裸 shell。"""
    principal = _get_principal(request)
    if not principal or principal[0] != "sub":
        raise HTTPException(status_code=401, detail="需要子账号登录")
    from vibe.accounts import account_can_access_project, sanitize_text
    pid = _sub_target_project(principal[1]["feishu_open_id"], target)
    if not pid or not account_can_access_project(principal[1], pid):
        raise HTTPException(status_code=403, detail="无权操作该终端")
    text = sanitize_text(body.get("text", ""))
    if not text:
        raise HTTPException(status_code=400, detail="内容为空")
    if len(text) > 4096:
        raise HTTPException(status_code=400, detail="内容过长")
    from vibe.tmux_bridge import send_keys
    try:
        send_keys(target, text + "\n")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        from vibe.history_db import record_sub_activity, record_sub_prompt
        oid = principal[1]["feishu_open_id"]
        record_sub_activity(oid, pid)         # 活跃区间(终端直接敲的走时间兜底)
        record_sub_prompt(oid, pid, text)     # 精确:这条 prompt 就是该子账号发的
    except Exception:
        pass
    return {"ok": True}


def _sync_sub_activity_from_tmux() -> None:
    """把当前 tmux 里 sub-<openid> session 回填进 sub_activity(时间推断归属用):
    每个 (子账号,项目) 用 session 创建时刻作为 first_ts、now 作为 last_ts,这样审计能把
    这些 session 期间该项目的会话算给子账号(近似,可能把 owner 在同项目的活动也算进去)。"""
    try:
        from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
        from vibe.history_db import record_sub_activity
        _, d = _read_vibe_yaml()
        name2oid = {}
        for a in (d.get("accounts") or []):
            oid = a.get("feishu_open_id")
            if oid:
                name2oid[_sub_session_name(oid)] = oid
        r = subprocess.run([_TMUX_BIN, "list-windows", "-a", "-F",
                            "#{session_name}\t#{window_name}\t#{session_created}"],
                           capture_output=True, text=True, env=_TMUX_ENV)
        now = int(time.time() * 1000)
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            sess, win, created = parts
            oid = name2oid.get(sess)
            if not oid or not win:
                continue
            try:
                created_ms = int(created) * 1000
            except ValueError:
                created_ms = now
            record_sub_activity(oid, win, created_ms)
            record_sub_activity(oid, win, now)
    except Exception:
        pass


@api.get("/api/sub-audit")
def sub_audit_data(request: Request):
    """owner:每个子账号的 prompts + token/开销(时间推断归属,见 history_db)。"""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    _sync_sub_activity_from_tmux()   # 先按当前子账号 session 回填,确保有数据
    from vibe.history_db import get_sub_account_audit
    _, data = _read_vibe_yaml()
    result = []
    for acc in (data.get("accounts") or []):
        oid = acc.get("feishu_open_id")
        if not oid:
            continue
        audit = get_sub_account_audit(oid)
        result.append({
            "open_id": oid,
            "name": acc.get("name") or oid,
            "avatar": acc.get("avatar") or "",
            "status": acc.get("status") or "",
            "granted_projects": acc.get("projects") or [],
            "projects": audit["projects"],
            "totals": audit["totals"],
            "prompts": audit["prompts"],
        })
    return result


@api.get("/sub-audit", response_class=HTMLResponse)
def sub_audit_page_route(embed: int = 0):
    """owner:子账号审计页壳(数据走 _is_admin 守卫的 /api/sub-audit)。embed=1 用于嵌进统计页 iframe。"""
    from vibe.sub_audit_page import render_sub_audit_page
    return HTMLResponse(render_sub_audit_page(embed=bool(embed)), headers=_NC)


# ── 飞书 OAuth 登录(复用 feishu-coo 应用)────────────────────────────────────

_feishu_states: dict[str, tuple] = {}   # state -> (过期时间, 组织 key)(CSRF 校验 + 多组织路由)


def _feishu_coo_env() -> dict:
    """回落读 feishu-coo 的 .env 复用其自建应用(用户明确要求复用)。只取需要的几项。"""
    env = {}
    try:
        p = Path.home() / "feishu-coo-run" / ".env"
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env


def _feishu_oauth_cfg() -> dict:
    from .config import load_global_config
    fo = (load_global_config().get("feishu_oauth") or {})
    coo = _feishu_coo_env() if not fo.get("app_id") else {}
    pub = (fo.get("public_base_url") or "https://mira.zhuchao.life").rstrip("/")
    return {
        "app_id": fo.get("app_id") or coo.get("FEISHU_COO_APP_ID", ""),
        "app_secret": fo.get("app_secret") or coo.get("FEISHU_COO_APP_SECRET", ""),
        "open_base_url": (fo.get("open_base_url") or coo.get("FEISHU_COO_OPEN_BASE_URL")
                          or "https://open.feishu.cn/open-apis"),
        "scopes": fo.get("scopes") or coo.get("FEISHU_COO_USER_OAUTH_SCOPES", ""),
        "redirect_uri": pub + "/auth/feishu/callback",
    }


def _feishu_oauth_apps() -> list[dict]:
    """所有可登录的飞书应用(多组织/多租户)。第一个是默认(feishu_oauth 或回落 feishu-coo),
    其余来自 config 的 feishu_oauth.orgs 列表。callback 用 state 里记的 key 选回对应应用。"""
    from .config import load_global_config
    fo = load_global_config().get("feishu_oauth") or {}
    pub = (fo.get("public_base_url") or "https://mira.zhuchao.life").rstrip("/")
    redirect = pub + "/auth/feishu/callback"
    apps: list[dict] = []
    coo = _feishu_coo_env() if not fo.get("app_id") else {}
    aid = fo.get("app_id") or coo.get("FEISHU_COO_APP_ID", "")
    if aid:
        apps.append({
            "key": "default",
            "label": fo.get("label") or "默认组织",
            "app_id": aid,
            "app_secret": fo.get("app_secret") or coo.get("FEISHU_COO_APP_SECRET", ""),
            "open_base_url": (fo.get("open_base_url") or coo.get("FEISHU_COO_OPEN_BASE_URL")
                              or "https://open.feishu.cn/open-apis"),
            "scopes": fo.get("scopes") or coo.get("FEISHU_COO_USER_OAUTH_SCOPES", ""),
            "redirect_uri": redirect,
        })
    for org in (fo.get("orgs") or []):
        if not org.get("app_id"):
            continue
        apps.append({
            "key": org.get("key") or org["app_id"][-8:],
            "label": org.get("label") or "组织",
            "app_id": org["app_id"],
            "app_secret": org.get("app_secret", ""),
            "open_base_url": org.get("open_base_url") or "https://open.feishu.cn/open-apis",
            "scopes": org.get("scopes", ""),
            "redirect_uri": redirect,
        })
    return apps


def _feishu_app_by_key(key: str):
    apps = _feishu_oauth_apps()
    for a in apps:
        if a["key"] == key:
            return a
    return apps[0] if apps else None


def _feishu_org_picker_html(apps: list[dict]) -> str:
    import html as _h
    from vibe.topbar import theme_vars_css
    btns = "".join(
        '<a href="/auth/feishu/login?org=' + _h.escape(a["key"], quote=True) + '" '
        'style="display:block;font-size:15px;font-weight:600;background:var(--accent);color:#fff;'
        'border-radius:10px;padding:14px 26px;text-decoration:none;margin:10px 0;min-width:240px">'
        + _h.escape(a["label"]) + ' 飞书登录</a>'
        for a in apps
    )
    return (
        '<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>选择组织 · Mira</title>'
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>"
        '<style>*{box-sizing:border-box;margin:0;padding:0}' + theme_vars_css() + '</style></head>'
        '<body style="display:flex;flex-direction:column;align-items:center;justify-content:center;'
        'min-height:100vh;gap:2px;text-align:center;padding:24px;font-family:var(--mono);background:var(--bg);color:var(--text)">'
        '<div style="font-size:20px;font-weight:700;margin-bottom:14px">'
        '<span style="color:var(--accent)">M</span>ira 协作 · 选择你的组织</div>'
        + btns +
        '</body></html>'
    )


@api.get("/auth/feishu/login")
def feishu_login(org: str = ""):
    """跳转飞书授权页;配置了多个组织且未指定 org 时,先返回组织选择页。"""
    from vibe.feishu_oauth import build_authorize_url
    apps = _feishu_oauth_apps()
    if not apps:
        raise HTTPException(status_code=503, detail="未配置飞书应用(feishu_oauth)")
    if not org and len(apps) > 1:
        return HTMLResponse(_feishu_org_picker_html(apps), headers=_NC)
    app = _feishu_app_by_key(org) if org else apps[0]
    state = secrets.token_urlsafe(16)
    _feishu_states[state] = (time.time() + 600, app["key"])
    return RedirectResponse(build_authorize_url(app, state))


@api.get("/auth/feishu/callback")
def feishu_callback(code: str = "", state: str = ""):
    """飞书授权回调:换码拿用户 → 找/建账号 → active 发会话,否则进待批准。"""
    st = _feishu_states.pop(state, None)
    if not st or st[0] < time.time():
        return RedirectResponse("/dev?sub_error=state")
    from vibe.feishu_oauth import exchange_code
    from vibe.accounts import new_session
    app = _feishu_app_by_key(st[1])   # 用发起登录时记下的组织 key 选回对应应用
    if not app:
        return RedirectResponse("/dev?sub_error=noapp")
    try:
        user = exchange_code(app, code)
    except Exception:
        return RedirectResponse("/dev?sub_error=exchange")
    open_id = user.get("open_id")
    if not open_id:
        return RedirectResponse("/dev?sub_error=nouser")
    cfg_path, data = _read_vibe_yaml()
    accounts_list = data.get("accounts", [])
    acc = next((a for a in accounts_list if a.get("feishu_open_id") == open_id), None)
    if acc is None:
        # 陌生人:建为 pending、零权限,等 owner 后台批准
        accounts_list.append({
            "feishu_open_id": open_id, "name": user.get("name", ""),
            "avatar": user.get("avatar_url", ""), "status": "pending",
            "projects": [], "created_at": int(time.time()),
        })
        data["accounts"] = accounts_list
        _write_vibe_yaml(cfg_path, data)
        return RedirectResponse("/dev?sub_status=pending")
    # 已有账号:刷新姓名/头像
    acc["name"] = user.get("name", acc.get("name", ""))
    acc["avatar"] = user.get("avatar_url", acc.get("avatar", ""))
    data["accounts"] = accounts_list
    _write_vibe_yaml(cfg_path, data)
    if acc.get("status") != "active":
        return RedirectResponse("/dev?sub_status=" + (acc.get("status") or "pending"))
    token = new_session(open_id)
    return RedirectResponse(f"/dev?sub_token={token}")


@api.get("/api/dev/project-options")
def dev_project_options(request: Request):
    """Return a non-blocking cache snapshot for the new-terminal dialog."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")

    with _cache_lock:
        projects = list(_cache)

    result = []
    for project in projects:
        path = project.get("path")
        if not path:
            continue
        claude_last = str((project.get("claude_activity") or {}).get("last_session") or "")
        codex_last = str((project.get("codex_activity") or {}).get("last_session") or "")
        result.append({
            "id": project.get("id") or Path(path).name,
            "name": project.get("name") or project.get("id") or Path(path).name,
            "path": path,
            "last_activity": max(claude_last, codex_last),
        })
    result.sort(key=lambda project: project["last_activity"], reverse=True)
    return result


@api.get("/api/dev/pane-tokens")
def dev_pane_tokens(request: Request, target: str = "", tool: str = ""):
    """Return token stats for the latest session in this pane's CWD."""
    principal = _get_principal(request)
    if not principal:
        raise HTTPException(status_code=401, detail="需要登录")
    if not target:
        raise HTTPException(status_code=400, detail="target required")
    # 子账号只能查自己 session 里的 pane,否则会泄漏 owner 其他项目的用量
    if principal[0] == "sub" and not _sub_target_project(principal[1]["feishu_open_id"], target):
        raise HTTPException(status_code=403, detail="无权访问该会话")
    from vibe.tmux_bridge import list_panes
    pane = next((p for p in list_panes() if p["target"] == target), None)
    if not pane:
        raise HTTPException(status_code=404, detail="Pane not found")
    cwd = pane["cwd"]

    if tool == "codex":
        from vibe.collectors.codex_sessions import get_latest_codex_session_stats
        stats = get_latest_codex_session_stats(cwd)
        return stats or {}

    # Default: Claude
    encoded = '-' + cwd.replace('/', '-').lstrip('-')
    folder_prefix = str(Path.home() / '.claude' / 'projects' / encoded)
    from vibe.history_db import get_latest_session_stats
    stats = get_latest_session_stats(folder_prefix)
    if stats:
        stats["tool"] = "claude"
        try:
            from vibe.collectors.claude_sessions import get_latest_session_context
            ctx = get_latest_session_context(folder_prefix)
            if ctx:
                stats["context_tokens"] = ctx   # 当前 context 占用(最后一次请求送入的总量)
        except Exception:
            pass
    return stats or {}


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
    def _do_kill():
        proc = subprocess.run(
            [_TMUX_BIN, "kill-pane", "-t", target],
            capture_output=True, text=True, env=_TMUX_ENV,
        )
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"tmux kill-pane failed: {proc.stderr.strip()}")
        unregister_pane(target)
    await asyncio.to_thread(_do_kill)
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
    def _do_capture():
        try:
            return capture_pane(target, lines=lines)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
    text = await asyncio.to_thread(_do_capture)
    return {"target": target, "output": text}


@api.websocket("/ws/terminal/{target:path}/stream")
async def terminal_stream_ws(ws: WebSocket, target: str):
    """Stream terminal output via WebSocket for mobile clients.

    Uses adaptive capture-pane polling and only sends when content changes.
    Active terminals refresh at 25 FPS for smooth typing, then back off when
    idle so mobile and desktop remain independent without constant high CPU.
    """
    # WS 认证：优先检查 header，兼容 query param（浏览器 WS 无法设 header）
    ws_token = ws.headers.get("x-admin-token") or ws.query_params.get("token", "")
    expected = _admin_token()
    authed = (expected is None) or (bool(ws_token) and hmac.compare_digest(ws_token, expected))
    if not authed:
        # 子账号:token 对应有效会话,且 target 属于他自己的 session 才放行(只读输出)
        from vibe.accounts import session_open_id
        oid = session_open_id(ws_token)
        if not (oid and _sub_target_project(oid, target)):
            await ws.close(code=1008, reason="Unauthorized")
            return
    await ws.accept()

    # 远程 WebSocket 代理：连接远程 Mira 的同名 WS 端点，双向转发
    remote_host, real_target = _parse_target(target)
    if remote_host is not None:
        import websockets as _ws
        import logging
        logger = logging.getLogger(__name__)
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
        except Exception as e:
            logger.warning("remote terminal stream closed for %s via %s: %s", real_target, remote_host.alias, e)
            try:
                await ws.close(code=1011, reason="Remote terminal stream failed")
            except Exception:
                pass
        return

    from vibe.tmux_bridge import capture_pane
    prev_hash = ""
    last_change_at = time.monotonic()
    import logging
    logger = logging.getLogger(__name__)
    # 先推第一帧实时画面(切换即见),再补历史回放 —— 回放要解析几 MB 会话文件,
    # 冷缓存时耗时秒级,不能挡在首帧前面。客户端会把回放插到 scrollback 最前。
    try:
        _first = await asyncio.to_thread(capture_pane, target, 300, ansi=True)
        prev_hash = hashlib.md5(_first.encode()).hexdigest()
        await ws.send_text(_first)
        _bl = await asyncio.to_thread(_stream_backlog, target)
        if _bl:
            await ws.send_text("\x00BL\x00" + _bl)
    except WebSocketDisconnect:
        return
    except Exception:
        pass
    try:
        while True:
            text = await asyncio.to_thread(capture_pane, target, 300, ansi=True)
            h = hashlib.md5(text.encode()).hexdigest()
            if h != prev_hash:
                prev_hash = h
                last_change_at = time.monotonic()
                await ws.send_text(text)
            active = (time.monotonic() - last_change_at) < 1.5
            # 8 FPS(活跃)/3 FPS(空闲)对终端阅读已足够。每帧是一次 capture-pane subprocess
            # fork(拉 300 行带 ANSI),原来的 25 FPS 在多客户端时会把 threadpool 线程吃满、
            # 拖慢其他同步端点(panes 轮询/focus/写操作)。
            await asyncio.sleep(0.12 if active else 0.3)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("terminal stream closed for %s: %s", target, e)
        try:
            await ws.close(code=1011, reason="Terminal stream failed")
        except Exception:
            pass


_UPLOAD_DIR = Path("/tmp/mira-uploads")

_ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml", "image/bmp"}
_UPLOAD_DENY_TYPES = {"application/x-executable", "application/x-msdos-program"}
_UPLOAD_MAX = 50 * 1024 * 1024

@api.post("/api/upload/image")
async def upload_image(request: Request, file: UploadFile = File(...), host: str = ""):
    principal = _get_principal(request)
    if not principal:
        raise HTTPException(status_code=401, detail="需要登录")
    if principal[0] == "sub" and host:
        raise HTTPException(status_code=403, detail="子账号不能访问远程主机")
    # 先验证类型，再读取完整内容
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct in _UPLOAD_DENY_TYPES:
        raise HTTPException(status_code=415, detail=f"不允许上传此类型文件: {ct}")
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
    principal = _get_principal(request)
    if not principal:
        raise HTTPException(status_code=401, detail="需要登录")
    # 子账号只能往自己 session 的 pane 发键(写键不净化:终端本就可写,会话已 shell-proof)
    if principal[0] == "sub" and not _sub_target_project(principal[1]["feishu_open_id"], target):
        raise HTTPException(status_code=403, detail="无权操作该会话")
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
    def _do_send():
        try:
            send_keys(target, keys)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
    await asyncio.to_thread(_do_send)
    # 子账号通过输入框发的一句话(body.prompt=原文) → 精确记录归属,不靠时间
    if principal[0] == "sub" and body.get("prompt"):
        try:
            from vibe.history_db import record_sub_prompt
            pid = _sub_target_project(principal[1]["feishu_open_id"], target)
            if pid:
                record_sub_prompt(principal[1]["feishu_open_id"], pid, body["prompt"])
        except Exception:
            pass
    return {"ok": True}


@api.get("/api/alerts")
def get_alerts(request: Request):
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    with _alerts_lock:
        current = list(_alerts) + list(_anomalies)
        _alerts.clear()
        _anomalies.clear()
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

# Injected before ttyd's application script. It reports connection state to the
# parent dev page, keeps ttyd's automatic reconnect enabled after socket errors,
# and hides ttyd's text overlays (Connection Closed / Press Enter to Reconnect).
_TTYD_CONNECTION_INJECT = """<script id="mira-ttyd-connection">
(function(){
var NativeWebSocket=window.WebSocket;
function notify(connected){
  try{window.parent.postMessage({type:'mira-ttyd-connection',connected:connected},'*');}catch(_){}
}
function MiraWebSocket(url,protocols){
  var ws=protocols===undefined?new NativeWebSocket(url):new NativeWebSocket(url,protocols);
  if(String(url).indexOf('/terminal/ws')!==-1){
    var nativeAdd=ws.addEventListener.bind(ws);
    nativeAdd('open',function(){notify(true);});
    nativeAdd('close',function(){notify(false);});
    nativeAdd('error',function(){notify(false);});
    // ttyd disables automatic reconnect when its error listener runs. The
    // close event still follows and will use ttyd's normal reconnect path.
    ws.addEventListener=function(type,listener,options){
      if(type==='error')return;
      return nativeAdd(type,listener,options);
    };
  }
  return ws;
}
MiraWebSocket.prototype=NativeWebSocket.prototype;
Object.setPrototypeOf(MiraWebSocket,NativeWebSocket);
window.WebSocket=MiraWebSocket;
var style=document.createElement('style');
style.textContent='.xterm>div[style*="font-size: xx-large"]{display:none!important}';
document.head.appendChild(style);
notify(false);
})();
</script>"""


# Injected into ttyd's HTML so the terminal follows Mira's active skin.
# Runs inside the iframe: reads localStorage, polls for the xterm Terminal
# instance (React mounts it async), and listens for postMessage updates.
_TTYD_THEME_INJECT = """<script id="mira-ttyd-theme">
(function(){
/* Per-skin config: colors + terminal options */
var T={
  'default':{
    bg:'#080c14',fg:'#eef1f7',cu:'#4f46e5',ca:'#080c14',sel:'rgba(79,70,229,.3)',
    k:'#0e1420',r:'#e06c75',g:'#3fb950',y:'#d29922',b:'#4e9eff',m:'#c792ea',c:'#56b6c2',w:'#eef1f7',
    bk:'#2a3040',br:'#e06c75',bg2:'#3fb950',by:'#e5a650',bb:'#82aaff',bm:'#d9a0f5',bc:'#89ddff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:false,fontSize:14},
  'claude-light':{
    bg:'#f5f3ef',fg:'#1a1a1a',cu:'#da7756',ca:'#ffffff',sel:'rgba(218,119,86,.25)',
    k:'#383a42',r:'#dc2626',g:'#16a34a',y:'#ca8a04',b:'#4078f2',m:'#a626a4',c:'#0184bc',w:'#1a1a1a',
    bk:'#b0b0b0',br:'#dc2626',bg2:'#16a34a',by:'#d97706',bb:'#4078f2',bm:'#a626a4',bc:'#0184bc',bw:'#383a42',
    cursorStyle:'bar',cursorBlink:true,fontSize:14},
  'claude-dark':{
    bg:'#131313',fg:'#ededed',cu:'#09B83E',ca:'#131313',sel:'rgba(9,184,62,.25)',
    k:'#1a1a1a',r:'#ef4444',g:'#4caf50',y:'#d4a84b',b:'#4e9eff',m:'#c792ea',c:'#56b6c2',w:'#ededed',
    bk:'#3a3a3a',br:'#ef4444',bg2:'#4caf50',by:'#e5a84b',bb:'#82aaff',bm:'#d9a0f5',bc:'#89ddff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:false,fontSize:14},
  'neon-pixel':{
    bg:'#0a0a0a',fg:'#e0e0ff',cu:'#ff00ff',ca:'#0a0a0a',sel:'rgba(0,255,0,.2)',
    k:'#0e0e1a',r:'#ff0040',g:'#00ff00',y:'#ffff00',b:'#00ccff',m:'#ff00ff',c:'#00ffff',w:'#e0e0ff',
    bk:'#2a2a40',br:'#ff0040',bg2:'#00ff00',by:'#ff8800',bb:'#00ccff',bm:'#ff00ff',bc:'#00ffff',bw:'#ffffff',
    cursorStyle:'block',cursorBlink:true,fontSize:14},
  'pixel-cyber':{
    bg:'#020c1a',fg:'#eef8ff',cu:'#ff0055',ca:'#020c1a',sel:'rgba(0,212,255,.2)',
    k:'#04111f',r:'#ff3355',g:'#00ff88',y:'#ffaa00',b:'#00d4ff',m:'#a855f7',c:'#00d4ff',w:'#eef8ff',
    bk:'#1a3a50',br:'#ff3355',bg2:'#00ff88',by:'#ffaa00',bb:'#00d4ff',bm:'#a855f7',bc:'#00d4ff',bw:'#ffffff',
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
function fitTerm(){
  var term=_term||(window.term&&window.term.element?window.term:null);
  if(term)_term=term;
  try{if(window.fitAddon&&window.fitAddon.fit)window.fitAddon.fit();}catch(e){}
  try{if(term&&term.fit)term.fit();}catch(e){}
  try{window.dispatchEvent(new Event('resize'));}catch(e){}
}
function apply(){
  var sk=skin();var t=T[sk]||T['default'];
  applyCSS(t,sk);
  if(_term){setTheme(_term,t);setTimeout(fitTerm,0);return;}
  if(window.term&&window.term.element){_term=window.term;setTheme(_term,t);setTimeout(fitTerm,0);return;}
  var n=0,id=setInterval(function(){
    if(window.term&&window.term.element){
      clearInterval(id);_term=window.term;setTheme(_term,T[skin()]||T['default']);setTimeout(fitTerm,0);
    } else if(++n>100){clearInterval(id);}
  },150);
}
window.addEventListener('message',function(e){
  if(!e.data)return;
  if(e.data.type==='mira-theme')apply();
  if(e.data.type==='mira-resize'){fitTerm();setTimeout(fitTerm,80);setTimeout(fitTerm,250);}
});
// Notify parent on mouseup so it can grab tmux buffer immediately
document.addEventListener('mouseup',function(e){
  if(e.button===0)try{window.parent.postMessage({type:'mira-mouseup'},'*');}catch(_){}
},true);
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',apply);
else apply();
})();
</script>"""  # end _TTYD_THEME_INJECT

# Reusable httpx client for ttyd proxy (avoids per-request connection pool churn)
import httpx as _httpx
_ttyd_http_client: _httpx.AsyncClient | None = None

def _get_ttyd_http_client() -> _httpx.AsyncClient:
    global _ttyd_http_client
    if _ttyd_http_client is None or _ttyd_http_client.is_closed:
        _ttyd_http_client = _httpx.AsyncClient(trust_env=False, timeout=10)
    return _ttyd_http_client

@api.api_route("/terminal/{path:path}", methods=["GET", "POST", "HEAD"])
async def ttyd_http_proxy(path: str, request: Request):
    """Proxy HTTP requests (HTML/JS/CSS assets) to the ttyd process.

    No admin check here — ttyd is bound to 127.0.0.1 and unreachable
    from outside. The security boundary is Mira's login page.
    """
    import base64
    from vibe.config import load_global_config

    url = f"http://127.0.0.1:{_TTYD_PORT}/terminal/{path}"
    params = str(request.url.query)
    if params:
        url += "?" + params
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "connection", "authorization")}
    pwd = (load_global_config().get("admin_password") or "").strip()
    if pwd:
        token = base64.b64encode(f"admin:{pwd}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    try:
        resp = await _get_ttyd_http_client().request(
            method=request.method,
            url=url,
            headers=headers,
            content=await request.body(),
        )
    except _httpx.ConnectError:
        raise HTTPException(status_code=502, detail="ttyd 未运行")
    # Strip hop-by-hop and encoding headers (httpx decompresses; don't re-claim gzip)
    skip = {"transfer-encoding", "connection", "keep-alive", "content-encoding", "content-length", "www-authenticate"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
    content = resp.content
    # Connection interception must run before ttyd creates its WebSocket. Theme
    # sync can run after the application has mounted the xterm instance.
    if "text/html" in resp.headers.get("content-type", ""):
        if b"</head>" in content:
            content = content.replace(b"</head>", _TTYD_CONNECTION_INJECT.encode() + b"</head>", 1)
        if b"</body>" in content:
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
    import logging
    from vibe.config import load_global_config
    logger = logging.getLogger(__name__)

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
            proxy=None,
            compression=None,
        ) as ttyd_ws:
            async def browser_to_ttyd():
                try:
                    while True:
                        msg = await websocket.receive()
                        msg_type = msg.get("type")
                        if msg_type == "websocket.disconnect":
                            break
                        if msg_type != "websocket.receive":
                            continue
                        if msg.get("bytes") is not None:
                            await ttyd_ws.send(msg["bytes"])
                        elif msg.get("text") is not None:
                            await ttyd_ws.send(msg["text"])
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.warning("browser->ttyd relay failed: %s", e)
                    raise

            async def ttyd_to_browser():
                try:
                    async for msg in ttyd_ws:
                        if isinstance(msg, bytes):
                            await websocket.send_bytes(msg)
                        else:
                            await websocket.send_text(msg)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.warning("ttyd->browser relay failed: %s", e)
                    raise

            t1 = asyncio.create_task(browser_to_ttyd())
            t2 = asyncio.create_task(ttyd_to_browser())
            done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
    except Exception as e:
        logger.warning("ttyd ws proxy closed: %s", e)
    finally:
        try:
            # ttyd automatically reconnects abnormal closures. A normal 1000
            # close makes its UI wait for Enter instead.
            await websocket.close(code=1012, reason="Terminal bridge reconnect")
        except Exception:
            pass


# ── 子账号只读终端作用域代理(/subterm/<port>/…)────────────────────────────────
# 每个子账号一个只读 ttyd(无 --writable),端口由 open_id 决定。代理用 cookie
# (= 子账号会话 token)鉴权,只放行"端口 == 自己端口"的请求,杜绝偷看别人终端。

def _subterm_open_id(cookie_token: str, port: int):
    """校验 cookie 会话,且其端口 == 请求端口。通过返回 open_id,否则 None。"""
    from vibe.accounts import session_open_id
    oid = session_open_id(cookie_token or "")
    if not oid or _sub_ttyd_port(oid) != port:
        return None
    return oid


@api.api_route("/subterm/{port:int}/{path:path}", methods=["GET", "POST", "HEAD"])
async def sub_ttyd_http_proxy(port: int, path: str, request: Request):
    if not _subterm_open_id(request.cookies.get("sub_term"), port):
        raise HTTPException(status_code=403, detail="无权访问该终端")
    url = f"http://127.0.0.1:{port}/subterm/{port}/{path}"
    params = str(request.url.query)
    if params:
        url += "?" + params
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "connection")}
    try:
        resp = await _get_ttyd_http_client().request(
            method=request.method, url=url, headers=headers, content=await request.body(),
        )
    except _httpx.ConnectError:
        raise HTTPException(status_code=502, detail="终端未运行")
    skip = {"transfer-encoding", "connection", "keep-alive", "content-encoding", "content-length"}
    out = {k: v for k, v in resp.headers.items() if k.lower() not in skip}
    content = resp.content
    # 让子账号的终端也跟随 Mira 皮肤(注入主题同步脚本,与 owner 终端一致)
    if "text/html" in resp.headers.get("content-type", ""):
        if b"</head>" in content:
            content = content.replace(b"</head>", _TTYD_CONNECTION_INJECT.encode() + b"</head>", 1)
        if b"</body>" in content:
            content = content.replace(b"</body>", _TTYD_THEME_INJECT.encode() + b"</body>", 1)
    return Response(content=content, status_code=resp.status_code, headers=out)


@api.websocket("/subterm/{port}/ws")
async def sub_ttyd_ws_proxy(websocket: WebSocket, port: int):
    import websockets as _ws
    import logging
    logger = logging.getLogger(__name__)
    if not _subterm_open_id(websocket.cookies.get("sub_term"), int(port)):
        await websocket.close(code=1008)
        return
    await websocket.accept(subprotocol="tty")
    ttyd_url = f"ws://127.0.0.1:{int(port)}/subterm/{int(port)}/ws"
    try:
        async with _ws.connect(ttyd_url, subprotocols=["tty"], proxy=None, compression=None) as ttyd_ws:
            async def browser_to_ttyd():
                while True:
                    msg = await websocket.receive()
                    if msg.get("type") == "websocket.disconnect":
                        break
                    if msg.get("type") != "websocket.receive":
                        continue
                    if msg.get("bytes") is not None:
                        await ttyd_ws.send(msg["bytes"])
                    elif msg.get("text") is not None:
                        await ttyd_ws.send(msg["text"])

            async def ttyd_to_browser():
                async for msg in ttyd_ws:
                    if isinstance(msg, bytes):
                        await websocket.send_bytes(msg)
                    else:
                        await websocket.send_text(msg)

            t1 = asyncio.create_task(browser_to_ttyd())
            t2 = asyncio.create_task(ttyd_to_browser())
            done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
    except Exception as e:
        logger.warning("sub ttyd ws proxy closed: %s", e)
    finally:
        try:
            await websocket.close(code=1012, reason="Terminal bridge reconnect")
        except Exception:
            pass


# ── Terminal focus / new-window API ────────────────────────────────────────────

_ttyd_focus_cache: dict = {"sig": None, "ttys": set()}


@api.post("/api/terminal/focus")
def terminal_focus(request: Request, body: dict):
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

    # 只切 owner 的【全局 ttyd】(监听 7681)派生的 tmux 客户端,按【进程身份】识别,
    # 不按"当前在哪个会话"判断——因为 admin 点开子账号面板时,自己的 ttyd 会临时
    # 连到 sub-* 会话;若按会话过滤会把 admin 自己也跳过 → 切不回来(乱了)。
    # 子账号 ttyd 监听 7700+,永远不在这里,自然不会被切。
    # 枚举 owner ttyd(7681)派生的 tmux 客户端子进程 pid。lsof+pgrep 较轻;真正贵的是
    # 逐个子进程 ps 查 TTY。用【子进程集签名】缓存解析结果:集合不变→直接复用(跳过 ps);
    # 集合一变(新开标签页多了 client、或 ttyd 重启 pid 变)→重算,从而既不漏新客户端、
    # 也不会踩 pid 复用拿到旧 TTY。冷路径把 N 次 ps 合并成 1 次。
    lsof = subprocess.run(["lsof", f"-tiTCP:{_TTYD_PORT}", "-sTCP:LISTEN"],
                          capture_output=True, text=True)
    child_pids: list[str] = []
    for pid in lsof.stdout.split():
        ch = subprocess.run(["pgrep", "-P", pid.strip()], capture_output=True, text=True)
        child_pids.extend(c.strip() for c in ch.stdout.split() if c.strip())
    sig = tuple(sorted(child_pids))
    if sig and sig == _ttyd_focus_cache.get("sig"):
        owner_ttys: set[str] = _ttyd_focus_cache["ttys"]
    else:
        owner_ttys = set()
        if child_pids:
            ps = subprocess.run(["ps", "-p", ",".join(child_pids), "-o", "tty="],
                                capture_output=True, text=True)
            for t in ps.stdout.split():
                t = t.strip()
                if t and t != "??":
                    owner_ttys.add(f"/dev/{t}")
        _ttyd_focus_cache["sig"] = sig
        _ttyd_focus_cache["ttys"] = owner_ttys
    switched = 0
    for tty in owner_ttys:
        subprocess.run(
            [_TMUX_BIN, "switch-client", "-c", tty, "-t", f"{session}:{window}"],
            env=_TMUX_ENV, capture_output=True,
        )
        switched += 1
    return {"ok": True, "switched": switched}


@api.post("/api/terminals/{target:path}/scroll")
def terminal_scroll(request: Request, target: str, body: dict):
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
def terminal_new_window(request: Request, body: dict):
    """Create a new tmux window, optionally in a project directory."""
    if not _is_admin(request):
        raise HTTPException(status_code=401, detail="需要管理员权限")
    from vibe.tmux_bridge import _TMUX_BIN, _TMUX_ENV
    # Ensure mira session exists (may not if no ttyd client has connected yet)
    subprocess.run([_TMUX_BIN, "new-session", "-d", "-s", "mira", "-c", str(Path.home())],
                   env=_TMUX_ENV, capture_output=True)
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
    # Immediately poll terminal monitor so the new pane appears in /api/dev/panes
    # without waiting for the 2-second monitor cycle.
    try:
        from vibe.terminal_monitor import _poll_once as _tm_poll
        _tm_poll()
    except Exception:
        pass
    return {"ok": True}


@api.get("/api/terminal/buffer")
def terminal_buffer(request: Request):
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
