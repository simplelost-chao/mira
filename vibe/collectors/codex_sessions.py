# vibe/collectors/codex_sessions.py
"""Read OpenAI Codex CLI session data from ~/.codex/sessions/."""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

CODEX_DIR = Path.home() / ".codex" / "sessions"

# Per-project cache: project_path → (frozenset of (file, mtime) pairs, result dict)
_cache: dict[str, tuple[frozenset, dict]] = {}
# Per-file cache: (file_path_str, mtime) → Optional[cwd]
_file_cwd_cache: dict[tuple[str, float], Optional[str]] = {}
# Per-file cache: (file_path_str, mtime) → primary workdir (most-used exec_command workdir)
_file_workdir_cache: dict[tuple[str, float], Optional[str]] = {}
_CACHE_MAX = 500
_FILE_CACHE_MAX = 10000

# Pricing per token (GPT-5.3-Codex approximate rates)
_PRICE_INPUT              = 15.00 / 1_000_000  # $15/MTok input
_PRICE_OUTPUT             = 75.00 / 1_000_000  # $75/MTok output
_PRICE_CACHED_INPUT       =  7.50 / 1_000_000  # $7.5/MTok cached input
_PRICE_REASONING_OUTPUT   = 75.00 / 1_000_000  # $75/MTok reasoning output


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


def _get_session_workdir(jsonl_path: Path) -> Optional[str]:
    """从 exec_command 的 workdir 参数中提取最主要的项目目录。

    扫描前 500 行 function_call 的 workdir，返回最常出现的、非 ~ 的目录。
    """
    counts: dict[str, int] = {}
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= 500:
                    break
                try:
                    d = json.loads(line)
                    if d.get("type") != "response_item":
                        continue
                    p = d.get("payload") or {}
                    if p.get("type") != "function_call":
                        continue
                    args = json.loads(p.get("arguments") or "{}")
                    wd = args.get("workdir", "")
                    if wd and wd != "/Users/chao":
                        counts[wd] = counts.get(wd, 0) + 1
                except Exception:
                    continue
    except Exception:
        pass
    if not counts:
        return None
    # Return the most common workdir
    return max(counts, key=counts.get)


def _session_touches_project(cwd: Optional[str], project_path: str, primary_workdir: Optional[str] = None) -> bool:
    """判断 Codex session 是否与项目相关。

    匹配策略（按优先级）：
    1. cwd 精确匹配 project_path
    2. cwd 是 project_path 子目录（项目内启动的 session）
    3. primary_workdir 匹配或包含 project_path
    （Codex session 的 cwd 均为 workspace 根目录 ~，
     依赖 workdir 做精确匹配）
    """
    if not cwd:
        return False
    cwd_norm = cwd.rstrip("/").lower() + "/"
    proj_norm = project_path.rstrip("/").lower() + "/"

    # 精确匹配或子目录
    if cwd_norm == proj_norm or cwd_norm.startswith(proj_norm):
        return True

    # 用 workdir 做精确匹配（cwd 是 ~ 时不走上面那条）
    if primary_workdir:
        wd_norm = primary_workdir.rstrip("/").lower() + "/"
        if wd_norm == proj_norm or wd_norm.startswith(proj_norm):
            return True

    return False


def _all_jsonl_files() -> list[Path]:
    if not CODEX_DIR.exists():
        return []
    return list(CODEX_DIR.rglob("*.jsonl"))


def _parse_session(jsonl_path: Path) -> dict:
    """解析单个 Codex session，提取时间线、任务统计和 token 用量。"""
    timestamps: list[datetime] = []
    task_durations: list[float] = []  # ms
    tokens = {  # accumulate token counts from token_count events
        "input": 0,
        "cached_input": 0,
        "output": 0,
        "reasoning_output": 0,
        "total": 0,
    }

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    ts = d.get("timestamp")
                    if ts:
                        timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))

                    if d.get("type") == "event_msg":
                        payload = d.get("payload") or {}
                        if payload.get("type") == "task_complete":
                            dur = payload.get("duration_ms")
                            if isinstance(dur, (int, float)) and dur > 0:
                                task_durations.append(dur)
                        elif payload.get("type") == "token_count":
                            # Use total_token_usage for per-session total
                            info = payload.get("info") or {}
                            usage = info.get("total_token_usage") or {}
                            tokens["input"] = max(tokens["input"], usage.get("input_tokens") or 0)
                            tokens["cached_input"] = max(tokens["cached_input"], usage.get("cached_input_tokens") or 0)
                            tokens["output"] = max(tokens["output"], usage.get("output_tokens") or 0)
                            tokens["reasoning_output"] = max(tokens["reasoning_output"], usage.get("reasoning_output_tokens") or 0)
                            tokens["total"] = max(tokens["total"], usage.get("total_tokens") or 0)
                except Exception:
                    continue
    except Exception:
        pass

    timestamps.sort()
    return {"timestamps": timestamps, "task_durations": task_durations, "tokens": tokens}


def collect_codex_activity(project_path: str) -> dict:
    """收集与指定项目关联的 Codex session 数据。"""
    global _cache, _file_cwd_cache

    if not CODEX_DIR.exists():
        return {}

    # 收集文件 mtime，避免重复 stat()
    all_files = _all_jsonl_files()
    file_mtimes: dict[Path, float] = {}
    for f in all_files:
        try:
            file_mtimes[f] = f.stat().st_mtime
        except OSError:
            continue

    matching: list[Path] = []
    for f, mtime in file_mtimes.items():
        key = (str(f), mtime)
        if key not in _file_cwd_cache:
            if len(_file_cwd_cache) > _FILE_CACHE_MAX:
                _file_cwd_cache.clear()
            _file_cwd_cache[key] = _get_session_cwd(f)
        cwd = _file_cwd_cache[key]

        # If cwd is workspace root (~), also check workdir for precise matching
        primary_workdir: Optional[str] = None
        if cwd and cwd.rstrip("/").lower() == Path.home().as_posix().lower():
            if key not in _file_workdir_cache:
                if len(_file_workdir_cache) > _FILE_CACHE_MAX:
                    _file_workdir_cache.clear()
                _file_workdir_cache[key] = _get_session_workdir(f)
            primary_workdir = _file_workdir_cache[key]

        if _session_touches_project(cwd, project_path, primary_workdir):
            matching.append(f)

    matching.sort(key=lambda p: file_mtimes[p])

    # 检查缓存
    fingerprint = frozenset((str(f), file_mtimes[f]) for f in matching)
    if project_path in _cache:
        cached_fp, cached_result = _cache[project_path]
        if cached_fp == fingerprint:
            return cached_result

    if not matching:
        # No per-project sessions match — return empty.
        # Global Codex stats are served via /api/codex-stats on the homepage KPI.
        _cache[project_path] = (fingerprint, {})
        return {}

    result = _aggregate_sessions(matching, file_mtimes)
    if len(_cache) > _CACHE_MAX:
        _cache.clear()
    _cache[project_path] = (fingerprint, result)
    return result


def _aggregate_sessions(session_files: list[Path], file_mtimes: dict[Path, float]) -> dict:
    """Aggregate token/task/activity data from a list of session files."""
    now = datetime.now()
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)
    last_mtime: Optional[datetime] = None
    count_7d = count_30d = 0
    active_secs = 0.0
    all_task_durations: list[float] = []
    day_counts: dict[str, float] = {}
    GAP_THRESHOLD = 30 * 60

    total_input = 0
    total_output = 0
    total_cached_input = 0
    total_reasoning_output = 0

    for f in session_files:
        mtime = datetime.fromtimestamp(file_mtimes[f])
        if mtime > cutoff_30d:
            count_30d += 1
        if mtime > cutoff_7d:
            count_7d += 1
        if last_mtime is None or mtime > last_mtime:
            last_mtime = mtime

        parsed = _parse_session(f)
        all_task_durations.extend(parsed["task_durations"])
        timestamps = parsed["timestamps"]
        tokens = parsed["tokens"]

        total_input += tokens["input"]
        total_output += tokens["output"]
        total_cached_input += tokens["cached_input"]
        total_reasoning_output += tokens["reasoning_output"]

        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if gap < GAP_THRESHOLD:
                active_secs += gap
                day_key = timestamps[i - 1].astimezone().strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + gap / 3600

    spark_15d = [
        round(day_counts.get((now - timedelta(days=14 - i)).strftime("%Y-%m-%d"), 0.0), 2)
        for i in range(15)
    ]

    total_tasks = len(all_task_durations)
    avg_task_ms = sum(all_task_durations) / total_tasks if total_tasks else 0

    # input_tokens ALREADY includes cached_input_tokens (OpenAI API convention),
    # so we charge non-cached portion at full price and cached at reduced price.
    non_cached_input = max(total_input - total_cached_input, 0)
    estimated_cost = (
        non_cached_input * _PRICE_INPUT
        + total_cached_input * _PRICE_CACHED_INPUT
        + total_output * _PRICE_OUTPUT
        + total_reasoning_output * _PRICE_REASONING_OUTPUT
    )

    return {
        "last_session": last_mtime.isoformat() if last_mtime else None,
        "session_count_7d": count_7d,
        "session_count_30d": count_30d,
        "active_hours": round(active_secs / 3600, 1),
        "session_spark_15d": spark_15d,
        "total_tasks": total_tasks,
        "avg_task_duration_sec": round(avg_task_ms / 1000, 1) if total_tasks else 0,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cached_input_tokens": total_cached_input,
        "reasoning_output_tokens": total_reasoning_output,
        "estimated_cost_usd": round(estimated_cost, 4),
    }


def get_latest_codex_session_stats(project_path: str) -> dict | None:
    """Return token stats for the most recent Codex session matching a project CWD."""
    if not CODEX_DIR.exists():
        return None

    all_files = _all_jsonl_files()
    if not all_files:
        return None

    # Find matching files, pick the newest by mtime
    best: tuple[float, Path] | None = None
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

        primary_workdir: Optional[str] = None
        if cwd and cwd.rstrip("/").lower() == Path.home().as_posix().lower():
            if key not in _file_workdir_cache:
                if len(_file_workdir_cache) > _FILE_CACHE_MAX:
                    _file_workdir_cache.clear()
                _file_workdir_cache[key] = _get_session_workdir(f)
            primary_workdir = _file_workdir_cache[key]

        if _session_touches_project(cwd, project_path, primary_workdir):
            if best is None or mtime > best[0]:
                best = (mtime, f)

    if not best:
        return None

    mtime, f = best
    parsed = _parse_session(f)
    tokens = parsed["tokens"]
    inp = tokens["input"]
    out = tokens["output"]
    cached = tokens["cached_input"]
    reasoning = tokens["reasoning_output"]

    non_cached = max(inp - cached, 0)
    cost = (non_cached * _PRICE_INPUT + cached * _PRICE_CACHED_INPUT
            + out * _PRICE_OUTPUT + reasoning * _PRICE_REASONING_OUTPUT)

    return {
        "tool": "codex",
        "input_tokens": inp,
        "output_tokens": out,
        "cached_input_tokens": cached,
        "reasoning_output_tokens": reasoning,
        "estimated_cost_usd": round(cost, 4),
    }


def _get_first_user_message(jsonl_path: Path) -> str:
    """Return the first user_message text from a Codex session file."""
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("type") == "event_msg":
                        p = d.get("payload") or {}
                        if p.get("type") == "user_message":
                            msg = p.get("message", "")
                            if msg:
                                return msg[:200]
                except Exception:
                    continue
    except Exception:
        pass
    return ""


def get_top_codex_sessions(sort_by: str = "cost", limit: int = 100) -> list[dict]:
    """Return top Codex sessions ranked by cost or active_hours."""
    if not CODEX_DIR.exists():
        return []

    all_files = _all_jsonl_files()
    sessions = []
    GAP_THRESHOLD = 30 * 60

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
        cwd = _file_cwd_cache[key] or ""

        # Derive project name from cwd path
        project_name = Path(cwd).name if cwd else "unknown"

        parsed = _parse_session(f)
        tokens = parsed["tokens"]
        timestamps = parsed["timestamps"]

        # Compute active hours
        active_secs = 0.0
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if gap < GAP_THRESHOLD:
                active_secs += gap

        inp = tokens["input"]
        out = tokens["output"]
        cached = tokens["cached_input"]
        reasoning = tokens["reasoning_output"]
        non_cached = max(inp - cached, 0)
        cost = (non_cached * _PRICE_INPUT + cached * _PRICE_CACHED_INPUT
                + out * _PRICE_OUTPUT + reasoning * _PRICE_REASONING_OUTPUT)

        if cost == 0 and active_secs == 0:
            continue

        date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        first_msg = _get_first_user_message(f)

        sessions.append({
            "session_id":              str(f.relative_to(CODEX_DIR)),
            "project_id":              cwd,
            "project_name":            project_name,
            "date":                    date_str,
            "input_tokens":            inp,
            "output_tokens":           out,
            "cached_input_tokens":     cached,
            "reasoning_output_tokens": reasoning,
            "active_hours":            round(active_secs / 3600, 2),
            "estimated_cost_usd":      round(cost, 4),
            "first_message":           first_msg,
        })

    sessions.sort(key=lambda s: s[sort_by if sort_by == "active_hours" else "estimated_cost_usd"], reverse=True)
    return sessions[:limit]


_TRIVIAL_CODEX = __import__("re").compile(
    r"^(yes|ok|好|继续|嗯|是|对|行|可以|没问题|好的|确认|continue|sure|go|"
    r"proceed|y|yep|yeah|done|next|1|2|3|4|5|\.+|,+)$",
    __import__("re").IGNORECASE,
)


def analyze_codex_session_turns(rel_path: str) -> list[dict]:
    """Parse a Codex session JSONL and return per-turn cost breakdown."""
    jsonl_path = CODEX_DIR / rel_path
    if not jsonl_path.exists():
        return []

    turns: list[dict] = []
    current_turn_id: Optional[str] = None
    current_label: str = ""
    last_cumulative: dict = {"input": 0, "output": 0, "cached": 0, "reasoning": 0}
    turn_cumulative: dict = {"input": 0, "output": 0, "cached": 0, "reasoning": 0}
    current_task_label: str = ""  # last non-trivial label (for inheritance)

    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "event_msg":
                    continue
                p = d.get("payload") or {}
                pt = p.get("type", "")

                if pt == "task_started":
                    current_turn_id = p.get("turn_id")
                    current_label = ""
                    turn_cumulative = dict(last_cumulative)

                elif pt == "user_message":
                    msg = (p.get("message") or "").strip()
                    if msg:
                        current_label = msg

                elif pt == "token_count":
                    info = p.get("info") or {}
                    usage = info.get("total_token_usage") or {}
                    if usage.get("input_tokens"):
                        turn_cumulative = {
                            "input":     usage.get("input_tokens", 0),
                            "output":    usage.get("output_tokens", 0),
                            "cached":    usage.get("cached_input_tokens", 0),
                            "reasoning": usage.get("reasoning_output_tokens", 0),
                        }

                elif pt == "task_complete" and current_turn_id == p.get("turn_id"):
                    # Delta tokens for this turn
                    d_inp  = max(turn_cumulative["input"]     - last_cumulative["input"],     0)
                    d_out  = max(turn_cumulative["output"]    - last_cumulative["output"],    0)
                    d_cach = max(turn_cumulative["cached"]    - last_cumulative["cached"],    0)
                    d_reas = max(turn_cumulative["reasoning"] - last_cumulative["reasoning"], 0)

                    non_cached = max(d_inp - d_cach, 0)
                    cost = (non_cached * _PRICE_INPUT + d_cach * _PRICE_CACHED_INPUT
                            + d_out * _PRICE_OUTPUT + d_reas * _PRICE_REASONING_OUTPUT)

                    label = current_label or "(无输入)"
                    trivial = bool(_TRIVIAL_CODEX.match(label.strip()))
                    if trivial:
                        display_label = current_task_label or label
                    else:
                        display_label = label
                        if label.strip():
                            current_task_label = label

                    if d_inp > 0 or d_out > 0:
                        turns.append({
                            "label":            display_label[:200],
                            "raw_label":        label[:200],
                            "input_tokens":     d_inp,
                            "output_tokens":    d_out,
                            "cached_input_tokens": d_cach,
                            "reasoning_tokens": d_reas,
                            "estimated_cost_usd": round(cost, 5),
                        })

                    last_cumulative = dict(turn_cumulative)
                    current_turn_id = None

    except Exception:
        pass

    turns.sort(key=lambda t: t["estimated_cost_usd"], reverse=True)
    return turns[:30]
