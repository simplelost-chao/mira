import json
import logging
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_PROJECTS_DIR = Path.home() / '.claude' / 'projects'


def _encode_path(path: str) -> str:
    """'/Users/chao/projects/foo' → '-Users-chao-projects-foo'"""
    if not path.startswith('/'):
        raise ValueError(f'Expected absolute path, got: {path!r}')
    return path.replace('/', '-')


def _parse_line(line: str):
    """Parse one JSONL line. Returns (role, text, ts_ms) or None."""
    if not line.strip():
        return None
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None

    if obj.get('type') not in ('user', 'assistant'):
        return None

    msg = obj.get('message', {})
    role = msg.get('role')
    if role not in ('user', 'assistant'):
        return None

    content = msg.get('content', '')
    if isinstance(content, str):
        text = content.strip()
    elif isinstance(content, list):
        text = ''
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                text = block.get('text', '').strip()
                break
    else:
        return None

    if not text:
        return None

    ts_str = obj.get('timestamp', '')
    if ts_str:
        try:
            ts_ms = int(
                datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp() * 1000
            )
        except Exception:
            ts_ms = int(time.time() * 1000)
    else:
        ts_ms = int(time.time() * 1000)

    return role, text, ts_ms


def _compute_session_stats(lines: list[str]) -> 'dict | None':
    """Full-file scan to compute token usage, active hours, and date.

    Returns None if lines has no timestamps.
    """
    GAP_THRESHOLD = 30 * 60  # seconds
    timestamps: list[datetime] = []
    input_tokens = 0
    output_tokens = 0
    message_count = 0

    for line in lines:
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Collect timestamps for active-hours calculation
        ts_str = obj.get('timestamp', '')
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                timestamps.append(ts)
            except (ValueError, AttributeError):
                pass

        # Count text-bearing messages
        if obj.get('type') in ('user', 'assistant'):
            msg = obj.get('message', {})
            content = msg.get('content', '')
            has_text = False
            if isinstance(content, str) and content.strip():
                has_text = True
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text' and block.get('text', '').strip():
                        has_text = True
                        break
            if has_text:
                message_count += 1

        # Token usage from assistant messages
        usage = (obj.get('message') or {}).get('usage') or {}
        if usage.get('output_tokens'):
            input_tokens += usage.get('input_tokens', 0)
            output_tokens += usage.get('output_tokens', 0)

    if not timestamps:
        return None

    timestamps.sort()
    active_secs = 0.0
    for i in range(1, len(timestamps)):
        gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
        if gap < GAP_THRESHOLD:
            active_secs += gap

    date_str = timestamps[-1].astimezone().strftime('%Y-%m-%d')
    return {
        'date':          date_str,
        'messages':      message_count,
        'input_tokens':  input_tokens,
        'output_tokens': output_tokens,
        'active_hours':  round(active_secs / 3600, 4),
    }


def index_file(path: Path, session_id: str, project_id: str, project_name: str) -> None:
    """Incrementally index a JSONL file from its last_line pointer."""
    from vibe.history_db import upsert_session, get_last_line, insert_message, set_last_line

    upsert_session(session_id, project_id, project_name, str(path))
    last = get_last_line(session_id)

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except OSError as e:
        logger.warning('Cannot read %s: %s', path, e)
        return

    new_lines = lines[last:]
    if not new_lines:
        return

    processed = 0
    for line in new_lines:
        parsed = _parse_line(line)
        if parsed:
            role, text, ts_ms = parsed
            try:
                insert_message(session_id, role, text, ts_ms)
            except Exception as e:
                logger.error('insert_message failed for %s: %s', path, e)
                break
        processed += 1

    try:
        set_last_line(session_id, last + processed)
    except ValueError as e:
        logger.error('Failed to advance last_line for %s: %s', session_id, e)

    # Update daily stats — only recompute if we actually processed new lines,
    # and at most once every 5 minutes per session to avoid full-file rescans
    # on every incremental write (e.g. active Claude Code conversations).
    _stats_update_if_due(session_id, project_id, lines, path)


_stats_last_updated: dict[str, float] = {}
_STATS_UPDATE_INTERVAL = 300.0  # 最多每 5 分钟重算一次 stats


def _stats_update_if_due(session_id: str, project_id: str, lines: list[str], path: Path) -> None:
    """Recompute and persist daily stats, but at most once per 5 minutes per session."""
    now = time.time()
    if now - _stats_last_updated.get(session_id, 0) < _STATS_UPDATE_INTERVAL:
        return
    try:
        stats = _compute_session_stats(lines)
        if stats:
            from vibe.history_db import upsert_daily_stats
            upsert_daily_stats(
                session_id=session_id,
                project_id=project_id,
                date=stats["date"],
                messages=stats["messages"],
                input_tokens=stats["input_tokens"],
                output_tokens=stats["output_tokens"],
                active_hours=stats["active_hours"],
            )
            _stats_last_updated[session_id] = now
    except Exception as e:
        logger.warning("upsert_daily_stats failed for %s: %s", path, e)


def _find_jsonl_for_project(project_path: str):
    """Yield all JSONL paths for a given project, including subagent files."""
    session_dir = CLAUDE_PROJECTS_DIR / _encode_path(project_path)
    if not session_dir.exists():
        return
    yield from session_dir.glob('*.jsonl')
    yield from session_dir.glob('*/subagents/*.jsonl')


def _all_jsonl_files_global() -> list[Path]:
    """Return every JSONL file under ~/.claude/projects/, including subagents."""
    if not CLAUDE_PROJECTS_DIR.exists():
        return []
    files = []
    for proj_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue
        files.extend(proj_dir.glob('*.jsonl'))
        files.extend(proj_dir.glob('*/subagents/*.jsonl'))
    return files


def _match_to_project(jsonl_path: Path, discovered: list[dict]) -> tuple[str, str]:
    """Return (project_id, project_name) for a JSONL file, or ('unclassified', 'Other')."""
    from vibe.collectors.claude_sessions import _session_touches_project
    for item in discovered:
        aliases = item.get('aliases') or []
        if _session_touches_project(jsonl_path, item['path'], aliases=aliases):
            return Path(item['path']).name, item['name']
    return 'unclassified', 'Other'


def run_indexer() -> None:
    """Initial full scan, then watchfiles loop for incremental updates. Runs forever."""
    import watchfiles
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.history_db import get_all_session_ids

    cfg = load_global_config()
    discovered = discover_projects(
        cfg['scan_dirs'], cfg['exclude'],
        cfg.get('extra_projects'), cfg.get('excluded_paths'),
    )

    # Build reverse map: encoded_dir_name → (project_id, project_name)
    dir_to_project: dict[str, tuple[str, str]] = {}
    for item in discovered:
        encoded = _encode_path(item['path'])
        project_id = Path(item['path']).name
        dir_to_project[encoded] = (project_id, item['name'])

    # Pass 1: index project-specific dirs (fast path via known mapping)
    for item in discovered:
        project_id, project_name = Path(item['path']).name, item['name']
        for jsonl_path in _find_jsonl_for_project(item['path']):
            try:
                index_file(jsonl_path, jsonl_path.stem, project_id, project_name)
            except Exception as e:
                logger.warning('Initial index failed for %s: %s', jsonl_path, e)

    # Pass 2: sweep ALL jsonl files, index anything not yet in DB
    already_indexed = get_all_session_ids()
    all_files = _all_jsonl_files_global()
    unmatched = [f for f in all_files if f.stem not in already_indexed]
    logger.info('Pass 2: %d unindexed JSONL files to process', len(unmatched))
    for jsonl_path in unmatched:
        try:
            project_id, project_name = _match_to_project(jsonl_path, discovered)
            index_file(jsonl_path, jsonl_path.stem, project_id, project_name)
        except Exception as e:
            logger.warning('Pass 2 index failed for %s: %s', jsonl_path, e)

    # Collect ALL claude project dirs to watch (not just known projects)
    watch_dirs = [
        str(d) for d in CLAUDE_PROJECTS_DIR.iterdir()
        if d.is_dir()
    ]

    if not watch_dirs:
        logger.info('No Claude session dirs found to watch')
        return

    logger.info('Watching %d Claude session dirs', len(watch_dirs))

    try:
        for changes in watchfiles.watch(*watch_dirs):
            for _change_type, changed_path in changes:
                p = Path(changed_path)
                if p.suffix != '.jsonl':
                    continue
                # Try fast path first (known project dir)
                parent_enc = p.parent.name
                if parent_enc in dir_to_project:
                    project_id, project_name = dir_to_project[parent_enc]
                else:
                    project_id, project_name = _match_to_project(p, discovered)
                try:
                    index_file(p, p.stem, project_id, project_name)
                except Exception as e:
                    logger.warning('Watch index failed for %s: %s', p, e)
    except Exception as e:
        logger.error('watchfiles loop exited unexpectedly: %s', e)
