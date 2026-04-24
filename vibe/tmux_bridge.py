import re
import subprocess

_TARGET_RE = re.compile(r'^[\w.-]+:\d+\.\d+$')


def list_panes() -> list[dict]:
    """Return all tmux panes across all sessions."""
    fmt = "#{session_name}\t#{window_index}\t#{pane_index}\t#{pane_current_command}\t#{pane_current_path}"
    try:
        proc = subprocess.run(
            ["tmux", "list-panes", "-a", "-F", fmt],
            capture_output=True, text=True,
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
        target = f"{session}:{window}.{pane}"
        panes.append({
            "target": target,
            "session": session,
            "window": int(window),
            "pane": int(pane),
            "command": command,
            "cwd": cwd,
        })
    return panes


def capture_pane(target: str, lines: int = 200) -> str:
    """Return recent output from a tmux pane."""
    proc = subprocess.run(
        ["tmux", "capture-pane", "-t", target, "-p", "-J"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"capture-pane failed for target '{target}': {proc.stderr.strip()}")
    text = proc.stdout
    tail = text.splitlines()[-lines:]
    return "\n".join(tail)


def send_keys(target: str, keys: str) -> None:
    """Send keystrokes to a tmux pane."""
    if not _TARGET_RE.match(target):
        raise RuntimeError(f"Invalid tmux target format: {target!r}")
    proc = subprocess.run(
        ["tmux", "send-keys", "-t", target, keys],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"send-keys failed for target '{target}': {proc.stderr.strip()}")
