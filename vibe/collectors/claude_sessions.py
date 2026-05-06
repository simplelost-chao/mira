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
    1. File lives in the Claude project folder that corresponds to this project path
       (covers renamed/moved projects whose sessions were migrated to the right folder)
    2. Exact path prefix (case-insensitive)
    3. Project folder name as path segment (handles old/different base dirs)
    4. Any alias name segments (handles renamed projects)
    """
    # Fast path: session file is directly in this project's Claude folder
    expected_folder = "-" + project_path.replace("/", "-").lstrip("-")
    if jsonl_path.parent.name == expected_folder:
        return True

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
    """Return Claude session activity for a project, queried from history_db.

    Falls back to empty dict if DB has no data for this project.
    """
    from vibe.history_db import get_project_activity

    # Claude folder for this project path
    encoded = '-' + project_path.replace('/', '-').lstrip('-')
    folder_prefix = str(CLAUDE_DIR / encoded)

    project_id = project_path.rstrip('/').split('/')[-1]
    extra_ids = list(aliases or [])

    result = get_project_activity(project_id, folder_prefix, extra_ids)
    if not result:
        return {}

    # Todos still require reading the most recent JSONL file directly
    session_folder = CLAUDE_DIR / encoded
    todos: list[dict] = []
    if session_folder.exists():
        candidates = sorted(session_folder.glob('*.jsonl'), key=lambda f: f.stat().st_mtime)
        if candidates:
            todos = _latest_todos(candidates[-1])

    summary: dict[str, int] = {"completed": 0, "in_progress": 0, "pending": 0}
    for t in todos:
        s = t.get("status", "pending")
        if s in summary:
            summary[s] += 1

    result['todos'] = todos
    result['todo_summary'] = summary
    return result
