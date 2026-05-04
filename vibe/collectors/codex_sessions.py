# vibe/collectors/codex_sessions.py
"""Read OpenAI Codex CLI session data from ~/.codex/sessions/."""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

CODEX_DIR = Path.home() / ".codex" / "sessions"

# Per-project cache: project_path → (frozenset of (file, mtime), result dict)
_cache: dict[str, tuple[frozenset, dict]] = {}
# Per-file cache: (file_path_str, mtime) → Optional[cwd]
_file_cwd_cache: dict[tuple[str, float], Optional[str]] = {}
_CACHE_MAX = 500
_FILE_CACHE_MAX = 10000


def _get_session_cwd(jsonl_path: Path) -> Optional[str]:
    """从 session_meta 中提取 cwd。"""
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("type") == "session_meta":
                        return (d.get("payload") or {}).get("cwd")
                except Exception:
                    continue
    except Exception:
        pass
    return None


def _session_touches_project(cwd: Optional[str], project_path: str) -> bool:
    """cwd 精确匹配或是 project_path 子目录。"""
    if not cwd:
        return False
    cwd_norm = cwd.rstrip("/") + "/"
    proj_norm = project_path.rstrip("/") + "/"
    return cwd_norm == proj_norm or cwd_norm.startswith(proj_norm)


def _all_jsonl_files() -> list[Path]:
    if not CODEX_DIR.exists():
        return []
    return sorted(CODEX_DIR.rglob("*.jsonl"))


def _parse_session(jsonl_path: Path) -> dict:
    """解析单个 Codex session，提取时间线和任务统计。"""
    timestamps: list[datetime] = []
    task_durations: list[float] = []  # ms
    cli_version: Optional[str] = None
    model_provider: Optional[str] = None

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    ts = d.get("timestamp")
                    if ts:
                        timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))

                    dtype = d.get("type")
                    payload = d.get("payload") or {}

                    if dtype == "session_meta":
                        cli_version = payload.get("cli_version")
                        model_provider = payload.get("model_provider")

                    elif dtype == "event_msg":
                        evt_type = payload.get("type", "")
                        if evt_type == "task_complete":
                            dur = payload.get("duration_ms")
                            if isinstance(dur, (int, float)) and dur > 0:
                                task_durations.append(dur)
                except Exception:
                    continue
    except Exception:
        pass

    timestamps.sort()
    return {
        "timestamps": timestamps,
        "task_durations": task_durations,
        "cli_version": cli_version,
        "model_provider": model_provider,
    }


def collect_codex_activity(project_path: str) -> dict:
    """收集与指定项目关联的 Codex session 数据。"""
    global _cache, _file_cwd_cache

    if not CODEX_DIR.exists():
        return {}

    all_files = _all_jsonl_files()
    matching: list[Path] = []

    for f in all_files:
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        key = (str(f), mtime)
        if key not in _file_cwd_cache:
            if len(_file_cwd_cache) > _FILE_CACHE_MAX:
                _file_cwd_cache.clear()
            _file_cwd_cache[key] = _get_session_cwd(f)
        cwd = _file_cwd_cache[key]
        if _session_touches_project(cwd, project_path):
            matching.append(f)

    matching.sort(key=lambda p: p.stat().st_mtime)

    # 检查缓存
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
    last_mtime: Optional[datetime] = None
    count_7d = count_30d = 0
    active_secs = 0.0
    all_task_durations: list[float] = []
    day_counts: dict[str, float] = {}
    GAP_THRESHOLD = 30 * 60  # 30min

    for f in matching:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime > cutoff_30d:
            count_30d += 1
        if mtime > cutoff_7d:
            count_7d += 1
        if last_mtime is None or mtime > last_mtime:
            last_mtime = mtime

        parsed = _parse_session(f)
        all_task_durations.extend(parsed["task_durations"])
        timestamps = parsed["timestamps"]

        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if gap < GAP_THRESHOLD:
                active_secs += gap
                day_key = timestamps[i - 1].astimezone().strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + gap / 3600

    # 15天 spark 数组
    spark_15d = [
        round(day_counts.get((now - timedelta(days=14 - i)).strftime("%Y-%m-%d"), 0.0), 2)
        for i in range(15)
    ]

    # 任务统计
    total_tasks = len(all_task_durations)
    avg_task_ms = sum(all_task_durations) / total_tasks if total_tasks else 0

    result = {
        "last_session": last_mtime.isoformat() if last_mtime else None,
        "session_count_7d": count_7d,
        "session_count_30d": count_30d,
        "active_hours": round(active_secs / 3600, 1),
        "session_spark_15d": spark_15d,
        "total_tasks": total_tasks,
        "avg_task_duration_sec": round(avg_task_ms / 1000, 1) if total_tasks else 0,
    }

    if len(_cache) > _CACHE_MAX:
        _cache.clear()
    _cache[project_path] = (fingerprint, result)
    return result
