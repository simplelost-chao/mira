import os
import re
import secrets
import shutil
import subprocess
import time

_TARGET_RE = re.compile(r'^[\w.-]+:\d+\.\d+$')

# macOS launchd services have a minimal PATH that excludes Homebrew (/opt/homebrew/bin)
# and set TMPDIR to a per-user /var/folders/... path instead of /tmp.
# Both break tmux subprocess calls:
#   - tmux binary not found (FileNotFoundError)
#   - tmux can't find its socket (returns no sessions)
# Fix: augment PATH to include common install locations, force TMUX_TMPDIR=/tmp.
_EXTRA_PATHS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"]
_PATH = os.environ.get("PATH", "") + ":" + ":".join(_EXTRA_PATHS)
_TMUX_ENV = {**os.environ, "PATH": _PATH, "TMUX_TMPDIR": "/tmp"}

# Resolve the tmux binary once at import time so we can use the full path.
_TMUX_BIN = shutil.which("tmux", path=_PATH) or "tmux"


def list_panes() -> list[dict]:
    """Return all tmux panes across all sessions."""
    fmt = "#{session_name}\t#{window_index}\t#{pane_index}\t#{pane_current_command}\t#{pane_current_path}\t#{pane_title}"
    try:
        proc = subprocess.run(
            [_TMUX_BIN, "list-panes", "-a", "-F", fmt],
            capture_output=True, text=True, env=_TMUX_ENV,
        )
    except FileNotFoundError:
        return []

    if proc.returncode != 0:
        # tmux server not running or no sessions; treat as no panes
        return []

    panes = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        session, window, pane, command, cwd = parts[:5]
        # viewer 分组会话(v-*)与源会话共享窗口,不滤会在列表里出现重复面板
        if session.startswith("v-"):
            continue
        title = parts[5] if len(parts) > 5 else ""
        target = f"{session}:{window}.{pane}"
        panes.append({
            "target": target,
            "session": session,
            "window": int(window),
            "pane": int(pane),
            "command": command,
            "cwd": cwd,
            "title": title,
        })
    return panes


def capture_pane(target: str, lines: int = 200, ansi: bool = False) -> str:
    """Return recent output from a tmux pane.

    Args:
        target: tmux pane target (e.g. "mira:0.0")
        lines:  how many scrollback lines to capture (0 = visible only)
        ansi:   if True, preserve ANSI escape sequences (-e flag)
    """
    cmd = [_TMUX_BIN, "capture-pane", "-t", target, "-p", "-J"]
    if ansi:
        cmd.append("-e")
    if lines > 0:
        cmd.extend(["-S", str(-lines)])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=_TMUX_ENV)
    if proc.returncode != 0:
        raise RuntimeError(f"capture-pane failed for target '{target}': {proc.stderr.strip()}")
    text = proc.stdout
    if not ansi and lines > 0:
        tail = text.splitlines()[-lines:]
        return "\n".join(tail)
    return text


def send_keys(target: str, keys: str) -> None:
    """Send keystrokes to a tmux pane.

    For multi-line or long text: uses tmux load-buffer + paste-buffer
    for reliable paste without truncation.
    For short single-line: uses send-keys with -l (literal) flag.
    Special control chars (\x03 etc.) use send-keys without -l.
    """
    if not _TARGET_RE.match(target):
        raise RuntimeError(f"Invalid tmux target format: {target!r}")

    def _run(cmd: list[str]) -> None:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=_TMUX_ENV)
        if proc.returncode != 0:
            raise RuntimeError(f"send-keys failed for target '{target}': {proc.stderr.strip()}")

    # copy-mode(滚动模式)会静默吞掉 send-keys -l 的字节(含 \x03),且自己不退出——
    # 客户端的滚动状态标志不跨页面刷新,pane 却可能一直留在 copy-mode,先退出再发
    mode = subprocess.run(
        [_TMUX_BIN, "display", "-p", "-t", target, "#{pane_in_mode}"],
        capture_output=True, text=True, env=_TMUX_ENV,
    )
    if mode.returncode == 0 and mode.stdout.strip() == "1":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "cancel"])

    # Control characters (Ctrl+C, Ctrl+U, Esc, etc.) — send directly
    if len(keys) == 1 and ord(keys) < 32 and keys != '\n':
        _run([_TMUX_BIN, "send-keys", "-t", target, "-l", keys])
        return

    # Multi-line or long text — use buffer paste for reliability
    if '\n' in keys and not keys.endswith('\n'):
        # Text without trailing newline: use load-buffer + paste-buffer
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(keys)
            f.flush()
            _run([_TMUX_BIN, "load-buffer", f.name])
            _run([_TMUX_BIN, "paste-buffer", "-t", target, "-d"])
        import os
        os.unlink(f.name)
        return

    # Split on newlines, send each part literally
    parts = keys.split("\n")
    for i, part in enumerate(parts):
        if part:
            _run([_TMUX_BIN, "send-keys", "-t", target, "-l", part])
        if i < len(parts) - 1:
            _run([_TMUX_BIN, "send-keys", "-t", target, "Enter"])


# ── viewer 会话:真终端直连的隔离层 ──────────────────────────────────────────
# 每条观看 WS 连接一个独立分组会话:共享源 session 的窗口内容,但"当前窗口"指针
# 各自独立 —— 多端同看、随意切换项目,内容归属不可能串台。

def create_viewer_session(target: str) -> str:
    """target 'mira:3.0' → 分组到 'mira' 的临时会话 v-<hex>,当前窗口 3。
    viewer 内禁 tmux 前缀键(子账号切不了窗口)、关状态栏(画面 100% 是 pane 内容)。"""
    if not _TARGET_RE.match(target):
        raise RuntimeError(f"Invalid tmux target format: {target!r}")
    session, rest = target.split(":", 1)
    window = rest.split(".", 1)[0]
    name = "v-" + secrets.token_hex(6)

    def _run(cmd: list[str]) -> None:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=_TMUX_ENV)
        if proc.returncode != 0:
            raise RuntimeError(f"viewer session failed for '{target}': {proc.stderr.strip()}")

    try:
        _run([_TMUX_BIN, "new-session", "-d", "-t", session, "-s", name])
        _run([_TMUX_BIN, "select-window", "-t", f"{name}:{window}"])
        _run([_TMUX_BIN, "set-option", "-t", name, "prefix", "None"])
        _run([_TMUX_BIN, "set-option", "-t", name, "status", "off"])
    except RuntimeError:
        kill_viewer_session(name)   # 半成品不留
        raise
    return name


def kill_viewer_session(name: str) -> None:
    """幂等销毁 viewer 会话。只认 v-* 前缀,防止误杀真实会话。"""
    if not name.startswith("v-"):
        return
    subprocess.run([_TMUX_BIN, "kill-session", "-t", name],
                   capture_output=True, text=True, env=_TMUX_ENV)


def window_size(target: str) -> tuple[int, int]:
    """target 所在窗口的 (cols, rows)。"""
    proc = subprocess.run(
        [_TMUX_BIN, "display-message", "-p", "-t", target, "#{window_width} #{window_height}"],
        capture_output=True, text=True, env=_TMUX_ENV)
    if proc.returncode != 0:
        raise RuntimeError(f"window_size failed for '{target}': {proc.stderr.strip()}")
    w, h = proc.stdout.split()
    return int(w), int(h)


def cleanup_orphan_viewers(max_age_seconds: int = 300) -> int:
    """兜底:清掉无客户端且创建超过 max_age 的 v-* 会话。
    正常路径由 WS 关闭时显式 kill;进程崩溃/断电时关闭事件会丢,靠这里回收。"""
    proc = subprocess.run(
        [_TMUX_BIN, "list-sessions", "-F", "#{session_name}\t#{session_attached}\t#{session_created}"],
        capture_output=True, text=True, env=_TMUX_ENV)
    if proc.returncode != 0:
        return 0
    now = time.time()
    n = 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0].startswith("v-"):
            continue
        try:
            if int(parts[1]) == 0 and now - int(parts[2]) > max_age_seconds:
                subprocess.run([_TMUX_BIN, "kill-session", "-t", parts[0]],
                               capture_output=True, text=True, env=_TMUX_ENV)
                n += 1
        except ValueError:
            continue
    return n
