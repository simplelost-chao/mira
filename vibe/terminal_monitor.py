import logging
import re
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_monitored: dict[str, dict] = {}
_terminal_alerts: list[dict] = []
_monitor_lock = threading.Lock()

# 未识别 pane 的 Codex 内容检测负向缓存：target -> 上次扫描的单调时钟。
# 避免每 2s 轮询都对同一个非 Codex pane 反复 capture_pane；间隔到了再重扫，
# 这样后来才在该 pane 启动的 Codex 仍能在一个间隔内被发现。
_codex_scan_cache: dict[str, float] = {}
_CODEX_RESCAN_INTERVAL = 30.0

_AUTO_COMMANDS = {"claude", "ccc"}
_AUTO_TITLE_FRAGMENTS = {"Claude Code"}
_CLAUDE_TITLE_ICONS = {"✳", "⠐", "⠂", "⠈", "⠁", "⠑", "⠃", "⠊", "⠔", "⠤", "⠠"}  # Claude Code spinner chars
_CODEX_COMMANDS = {"codex"}
_CODEX_TITLE_FRAGMENTS = {"Codex"}
# 版本无关的 Codex 终端内容特征(检测标题/命令都认不出的 Codex pane,如标题被设成项目名、命令是 node)
_CODEX_CONTENT_RE = re.compile(
    r"OpenAI Codex|codex app|gpt-[56](?:\.\d+)?\b|Worked for \d+[hms]"
)

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


def register_pane(target: str, label: str, project_id: str | None = None) -> None:
    with _monitor_lock:
        if target not in _monitored:
            _monitored[target] = {
                "target": target,
                "label": label,
                "command": "",
                "cwd": "",
                "auto": False,
                "project_id": project_id,
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


_projects_cache: list[dict] = []
_projects_cache_ts: float = 0.0
_PROJECTS_CACHE_TTL: float = 60.0


def _get_projects() -> list[dict]:
    """Return cached project list, refreshing at most once per 60 seconds."""
    global _projects_cache, _projects_cache_ts
    now = time.time()
    if _projects_cache and now - _projects_cache_ts < _PROJECTS_CACHE_TTL:
        return _projects_cache
    try:
        from vibe.config import load_global_config
        from vibe.scanner import discover_projects
        cfg = load_global_config()
        _projects_cache = discover_projects(
            cfg["scan_dirs"], cfg["exclude"],
            cfg.get("extra_projects"), cfg.get("excluded_paths"),
        )
        _projects_cache_ts = now
    except Exception:
        pass
    return _projects_cache


def _match_project(cwd: str) -> str | None:
    """Match a cwd to a known Mira project path."""
    try:
        for p in _get_projects():
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

    # Snapshot currently tracked targets to avoid calling _match_project for known panes
    with _monitor_lock:
        tracked_targets = set(_monitored.keys())

    # 清理已消失 pane 的负向缓存,防止长跑积累
    _live_targets = {pane["target"] for pane in all_panes}
    for _gone in [t for t in _codex_scan_cache if t not in _live_targets]:
        del _codex_scan_cache[_gone]

    # Auto-discover Claude / Codex panes — compute project_id OUTSIDE the lock (I/O)
    new_entries = {}
    for pane in all_panes:
        title = pane.get("title", "")
        is_claude = pane["command"] in _AUTO_COMMANDS or any(
            frag in title for frag in _AUTO_TITLE_FRAGMENTS
        ) or (title and title[0] in _CLAUDE_TITLE_ICONS)
        is_codex = not is_claude and (
            pane["command"] in _CODEX_COMMANDS or any(
                frag in title for frag in _CODEX_TITLE_FRAGMENTS
            )
        )
        # For unrecognized node panes not yet tracked, check terminal output for Codex
        # Codex uses alternate screen, so check both scrollback and visible pane
        if not is_claude and not is_codex and pane["target"] not in tracked_targets:
            # 负向缓存:间隔内不重扫同一个未识别 pane,避免每 2s 两次 subprocess
            _last = _codex_scan_cache.get(pane["target"], 0.0)
            if time.monotonic() - _last >= _CODEX_RESCAN_INTERVAL:
                _codex_scan_cache[pane["target"]] = time.monotonic()
                # 用版本无关的标记,别再硬编码具体模型号(gpt-5.5/5.6… 会让旧列表失效)。
                # _CODEX_CONTENT_RE 匹配 Codex CLI 的稳定特征:任意 gpt-5.x/gpt-6.x 模型行、
                # "Worked for …" 状态行、以及 "OpenAI Codex" 字样。
                # 用 tmux_bridge.capture_pane(它设了正确的 PATH/TMUX_TMPDIR);裸 subprocess
                # 在 launchd 环境下找不到 tmux socket,会静默失败 —— 这正是之前检测不到的原因。
                for _lines in (0, 50):   # 0=可见(备用屏),50=往上 50 行回滚
                    try:
                        out = capture_pane(pane["target"], _lines)
                        if out and _CODEX_CONTENT_RE.search(out):
                            is_codex = True
                            break
                    except Exception:
                        pass
        if is_claude or is_codex:
            project_id = (
                None if pane["target"] in tracked_targets
                else _match_project(pane["cwd"])
            )
            display_cmd = "codex" if is_codex else "claude"
            new_entries[pane["target"]] = (pane, project_id, display_cmd)

    with _monitor_lock:
        for target, (pane, project_id, display_cmd) in new_entries.items():
            if target not in _monitored:
                _monitored[target] = {
                    "target": pane["target"],
                    "label": f"{display_cmd}/{Path(pane['cwd']).name}",
                    "command": display_cmd,
                    "cwd": pane["cwd"],
                    "auto": True,
                    "project_id": project_id,
                    "last_output": "",
                    "waiting": False,
                    "registered_at": time.time(),
                }
        # Evict any pane whose tmux target no longer exists
        current_targets = set(p["target"] for p in all_panes)
        stale = [t for t in _monitored if t not in current_targets]
        for t in stale:
            del _monitored[t]
        targets = list(_monitored.keys())

    for target in targets:
        try:
            output = capture_pane(target, lines=20)
        except RuntimeError:
            with _monitor_lock:
                _monitored.pop(target, None)
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
