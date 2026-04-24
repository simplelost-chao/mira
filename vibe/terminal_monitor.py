import logging
import re
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_monitored: dict[str, dict] = {}
_terminal_alerts: list[dict] = []
_monitor_lock = threading.Lock()

_AUTO_COMMANDS = {"claude", "ccc"}

WAIT_PATTERNS = [
    r"do you want to",
    r"\(y/n\)",
    r"\[y/n\]",
    r"\ballow\b",
    r"\bdeny\b",
    r"continue\?",
    r"proceed\?",
    r"press enter",
    r"are you sure",
]
_WAIT_RE = re.compile("|".join(WAIT_PATTERNS), re.IGNORECASE)


def register_pane(target: str, label: str) -> None:
    with _monitor_lock:
        if target not in _monitored:
            _monitored[target] = {
                "target": target,
                "label": label,
                "command": "",
                "cwd": "",
                "auto": False,
                "project_id": None,
                "last_output": "",
                "waiting": False,
                "registered_at": time.time(),
            }


def unregister_pane(target: str) -> None:
    with _monitor_lock:
        _monitored.pop(target, None)


def get_panes() -> list[dict]:
    with _monitor_lock:
        return [dict(v) for v in _monitored.values()]


def get_terminal_alerts() -> list[dict]:
    with _monitor_lock:
        alerts = list(_terminal_alerts)
        _terminal_alerts.clear()
    return alerts


def _match_project(cwd: str) -> str | None:
    """Match a cwd to a known Mira project path."""
    try:
        from vibe.config import load_global_config
        from vibe.scanner import discover_projects
        cfg = load_global_config()
        projects = discover_projects(
            cfg["scan_dirs"], cfg["exclude"],
            cfg.get("extra_projects"), cfg.get("excluded_paths"),
        )
        for p in projects:
            if cwd.startswith(p["path"]):
                return Path(p["path"]).name
    except Exception:
        pass
    return None


def _poll_once() -> None:
    from vibe.tmux_bridge import list_panes, capture_pane

    # Auto-discover Claude panes
    try:
        all_panes = list_panes()
    except Exception as e:
        logger.warning("list_panes failed: %s", e)
        all_panes = []

    # Auto-discover Claude panes — compute project_id OUTSIDE the lock (I/O)
    new_entries = {}
    for pane in all_panes:
        if pane["command"] in _AUTO_COMMANDS:
            new_entries[pane["target"]] = (pane, _match_project(pane["cwd"]))

    with _monitor_lock:
        for target, (pane, project_id) in new_entries.items():
            if target not in _monitored:
                _monitored[target] = {
                    "target": pane["target"],
                    "label": f"{pane['command']}/{Path(pane['cwd']).name}",
                    "command": pane["command"],
                    "cwd": pane["cwd"],
                    "auto": True,
                    "project_id": project_id,
                    "last_output": "",
                    "waiting": False,
                    "registered_at": time.time(),
                }
        # Evict auto-discovered panes that are no longer in list_panes
        current_targets = set(p["target"] for p in all_panes)
        stale = [t for t, v in _monitored.items() if v["auto"] and t not in current_targets]
        for t in stale:
            del _monitored[t]
        targets = list(_monitored.keys())

    for target in targets:
        try:
            output = capture_pane(target, lines=20)
        except RuntimeError:
            with _monitor_lock:
                if target in _monitored and _monitored[target].get("auto"):
                    del _monitored[target]
            continue

        last_10_lines = "\n".join(output.splitlines()[-10:])
        is_waiting = bool(_WAIT_RE.search(last_10_lines))

        with _monitor_lock:
            if target not in _monitored:
                continue
            entry = _monitored[target]
            was_waiting = entry["waiting"]
            entry["last_output"] = output
            entry["waiting"] = is_waiting

            if is_waiting and not was_waiting:
                snippet = last_10_lines.strip()[-200:]
                _terminal_alerts.append({
                    "target": target,
                    "label": entry["label"],
                    "snippet": snippet,
                    "ts": int(time.time() * 1000),
                })


def run_monitor() -> None:
    """Infinite poll loop. Runs as a daemon thread."""
    logger.info("Terminal monitor started")
    while True:
        try:
            _poll_once()
        except Exception as e:
            logger.warning("Terminal monitor poll error: %s", e)
        time.sleep(2)
