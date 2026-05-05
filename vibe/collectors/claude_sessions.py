# vibe/collectors/claude_sessions.py
"""Read Claude Code session data from ~/.claude/projects/."""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

CLAUDE_DIR = Path.home() / ".claude" / "projects"

# Per-project cache: project_path → (frozenset of (file, mtime) pairs, result dict)
# Invalidated only when the set of matching files or their mtimes change.
_cache: dict[str, tuple[frozenset, dict]] = {}
# Per-file membership cache: (file_path_str, mtime) → bool (does it touch the project?)
_file_cache: dict[tuple[str, float], bool] = {}
_CACHE_MAX = 500
_FILE_CACHE_MAX = 10000


def _session_touches_project(jsonl_path: Path, project_path: str, scan_lines: int = 300, aliases: list[str] | None = None) -> bool:
    """Return True if any tool_use in the session accesses files under project_path.

    Matches by:
    1. Exact path prefix (case-insensitive)
    2. Project folder name as path segment (handles old/different base dirs)
    3. Any alias name segments (handles renamed projects)
    """
    project_id = project_path.rstrip("/").split("/")[-1]
    segments = {f"/{project_id}/"}
    for a in (aliases or []):
        segments.add(f"/{a}/")
    segment = f"/{project_id}/"          # e.g. "/vibe-manager/"
    prefix_lower = project_path.lower().rstrip("/") + "/"
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= scan_lines:
                    break
                try:
                    d = json.loads(line)
                    content = (d.get("message") or {}).get("content") or []
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        inp = block.get("input") or {}
                        for key in ("file_path", "path", "new_path", "old_path"):
                            val = inp.get(key, "")
                            if not isinstance(val, str):
                                continue
                            if val.lower().startswith(prefix_lower):
                                return True
                            if any(seg in val for seg in segments):
                                return True
                        cmd = inp.get("command", "")
                        if isinstance(cmd, str) and any(seg in cmd for seg in segments):
                            return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _all_jsonl_files() -> list[Path]:
    if not CLAUDE_DIR.exists():
        return []
    files = []
    for proj_dir in CLAUDE_DIR.iterdir():
        if proj_dir.is_dir():
            files.extend(proj_dir.glob("*.jsonl"))
    return files


def _latest_todos(jsonl_path: Path) -> list[dict]:
    last: list[dict] = []
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    content = (d.get("message") or {}).get("content") or []
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if (isinstance(block, dict)
                                and block.get("type") == "tool_use"
                                and block.get("name") == "TodoWrite"):
                            todos = (block.get("input") or {}).get("todos") or []
                            if todos:
                                last = todos
                except Exception:
                    continue
    except Exception:
        pass
    return [{"content": t.get("content", ""), "status": t.get("status", "pending")}
            for t in last]


# Pricing per token (Sonnet 4.x rates; approximation for other models)
_PRICE_INPUT        = 3.00  / 1_000_000   # $3/MTok
_PRICE_OUTPUT       = 15.00 / 1_000_000   # $15/MTok
_PRICE_CACHE_WRITE  = 3.75  / 1_000_000   # $3.75/MTok
_PRICE_CACHE_READ   = 0.30  / 1_000_000   # $0.30/MTok


def _sum_tokens(jsonl_path: Path) -> dict:
    """Return cumulative token counts from all assistant messages in a session."""
    totals = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    usage = (d.get("message") or {}).get("usage") or {}
                    if not usage or not usage.get("output_tokens"):
                        continue
                    totals["input"]          += usage.get("input_tokens", 0)
                    totals["output"]         += usage.get("output_tokens", 0)
                    totals["cache_creation"] += usage.get("cache_creation_input_tokens", 0)
                    totals["cache_read"]     += usage.get("cache_read_input_tokens", 0)
                except Exception:
                    continue
    except Exception:
        pass
    return totals


def collect_claude_activity(project_path: str, aliases: list[str] | None = None) -> dict:
    global _cache, _file_cache

    if not CLAUDE_DIR.exists():
        return {}

    # Build matching list using per-file mtime cache
    all_files = _all_jsonl_files()
    matching = []
    for f in all_files:
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        key = (str(f), mtime, project_path)
        if key not in _file_cache:
            # 防止缓存无限增长
            if len(_file_cache) > _FILE_CACHE_MAX:
                _file_cache.clear()
            _file_cache[key] = _session_touches_project(f, project_path, aliases=aliases)
        if _file_cache[key]:
            matching.append(f)

    matching.sort(key=lambda f: f.stat().st_mtime)

    # Check if cached result is still valid (same files + same mtimes)
    fingerprint = frozenset((str(f), f.stat().st_mtime) for f in matching)
    if project_path in _cache:
        cached_fp, cached_result = _cache[project_path]
        if cached_fp == fingerprint:
            return cached_result

    if not matching:
        _cache[project_path] = (fingerprint, {})
        return {}

    now = datetime.now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    last_mtime: datetime | None = None
    count_7d = count_30d = 0
    tok = {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0}
    active_secs = 0.0
    # per-day session counts for last 15 days (index 0 = 14 days ago, 14 = today)
    day_counts: dict[str, int] = {}

    GAP_THRESHOLD = 30 * 60  # gaps < 30min count as active time

    for f in matching:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime > cutoff_30d:
            count_30d += 1
        if mtime > cutoff_7d:
            count_7d += 1
        if last_mtime is None or mtime > last_mtime:
            last_mtime = mtime

            # active time: sum inter-message gaps < 30min within this session
        timestamps = []
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        ts = d.get("timestamp")
                        if ts:
                            timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                    except Exception:
                        continue
        except Exception:
            pass
        timestamps.sort()
        session_active = 0.0
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if gap < GAP_THRESHOLD:
                active_secs += gap
                session_active += gap
                # attribute this gap to the day of the earlier timestamp (local time)
                day_key = timestamps[i - 1].astimezone().strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + gap / 3600

        t = _sum_tokens(f)
        for k in tok:
            tok[k] += t[k]

    cost = (
        tok["input"]          * _PRICE_INPUT +
        tok["output"]         * _PRICE_OUTPUT +
        tok["cache_creation"] * _PRICE_CACHE_WRITE +
        tok["cache_read"]     * _PRICE_CACHE_READ
    )

    # Build 15-day spark array: active hours per day (float, 12h = full)
    spark_15d = [
        round(day_counts.get((now - timedelta(days=14 - i)).strftime("%Y-%m-%d"), 0.0), 2)
        for i in range(15)
    ]

    todos = _latest_todos(matching[-1])
    summary = {"completed": 0, "in_progress": 0, "pending": 0}
    for t in todos:
        s = t.get("status", "pending")
        if s in summary:
            summary[s] += 1

    result = {
        "last_session": last_mtime.isoformat() if last_mtime else None,
        "session_count_7d": count_7d,
        "session_count_30d": count_30d,
        "todos": todos,
        "todo_summary": summary,
        "input_tokens": tok["input"],
        "output_tokens": tok["output"],
        "cache_creation_tokens": tok["cache_creation"],
        "cache_read_tokens": tok["cache_read"],
        "estimated_cost_usd": round(cost, 4),
        "active_hours": round(active_secs / 3600, 1),
        "session_spark_15d": spark_15d,
    }
    # 防止缓存无限增长
    if len(_cache) > _CACHE_MAX:
        _cache.clear()
    _cache[project_path] = (fingerprint, result)
    return result
