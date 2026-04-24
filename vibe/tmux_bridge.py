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


def capture_pane(target: str, lines: int = 200) -> str:
    """Return recent output from a tmux pane."""
    proc = subprocess.run(
        [_TMUX_BIN, "capture-pane", "-t", target, "-p", "-J"],
        capture_output=True, text=True, env=_TMUX_ENV,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"capture-pane failed for target '{target}': {proc.stderr.strip()}")
    text = proc.stdout
    tail = text.splitlines()[-lines:]
    return "\n".join(tail)


def send_keys(target: str, keys: str) -> None:
    """Send keystrokes to a tmux pane.

    Splits on \\n so newlines are sent as the tmux 'Enter' key name,
    which tmux recognises correctly unlike a literal newline character.
    """
    if not _TARGET_RE.match(target):
        raise RuntimeError(f"Invalid tmux target format: {target!r}")

    def _run(cmd: list[str]) -> None:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=_TMUX_ENV)
        if proc.returncode != 0:
            raise RuntimeError(f"send-keys failed for target '{target}': {proc.stderr.strip()}")

    parts = keys.split("\n")
    for i, part in enumerate(parts):
        if part:
            _run([_TMUX_BIN, "send-keys", "-t", target, part])
        if i < len(parts) - 1:
            _run([_TMUX_BIN, "send-keys", "-t", target, "Enter"])
