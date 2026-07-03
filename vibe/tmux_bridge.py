import os
import re
import shutil
import subprocess

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


def scroll_pane(target: str, direction: str, lines: int = 5) -> None:
    """Scroll a tmux pane using copy-mode.

    direction: 'up', 'down', 'top', 'bottom', 'page-up', 'page-down', 'exit'
    """
    if not _TARGET_RE.match(target):
        raise RuntimeError(f"Invalid tmux target format: {target!r}")

    def _run(cmd: list[str]) -> None:
        subprocess.run(cmd, capture_output=True, text=True, env=_TMUX_ENV)

    if direction == "exit":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "cancel"])
        return

    # Enter copy-mode if not already in it (idempotent)
    _run([_TMUX_BIN, "copy-mode", "-t", target])

    if direction == "up":
        for _ in range(lines):
            _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "cursor-up"])
    elif direction == "down":
        for _ in range(lines):
            _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "cursor-down"])
    elif direction == "page-up":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "page-up"])
    elif direction == "page-down":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "page-down"])
    elif direction == "top":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "history-top"])
    elif direction == "bottom":
        _run([_TMUX_BIN, "send-keys", "-t", target, "-X", "history-bottom"])
