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

    date_str = timestamps[-1].strftime('%Y-%m-%d')
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

    # Update daily stats for this session
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
    except Exception as e:  # DB errors (OperationalError, IntegrityError, etc.) are non-fatal
        logger.warning("upsert_daily_stats failed for %s: %s", path, e)


def _find_jsonl_for_project(project_path: str):
    """Yield all JSONL paths for a given project."""
    session_dir = CLAUDE_PROJECTS_DIR / _encode_path(project_path)
    if not session_dir.exists():
        return
    yield from session_dir.glob('*.jsonl')


def run_indexer() -> None:
    """Initial full scan, then watchfiles loop for incremental updates. Runs forever."""
    import watchfiles
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects

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

    # Initial scan — reuse dir_to_project values
    for item in discovered:
        encoded = _encode_path(item['path'])
        project_id, project_name = dir_to_project[encoded]
        for jsonl_path in _find_jsonl_for_project(item['path']):
            try:
                index_file(jsonl_path, jsonl_path.stem, project_id, project_name)
            except Exception as e:
                logger.warning('Initial index failed for %s: %s', jsonl_path, e)

    # Collect watch dirs that exist
    watch_dirs = [
        str(CLAUDE_PROJECTS_DIR / enc)
        for enc in dir_to_project
        if (CLAUDE_PROJECTS_DIR / enc).exists()
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
                parent_enc = p.parent.name
                if parent_enc not in dir_to_project:
                    continue
                project_id, project_name = dir_to_project[parent_enc]
                try:
                    index_file(p, p.stem, project_id, project_name)
                except Exception as e:
                    logger.warning('Watch index failed for %s: %s', p, e)
    except Exception as e:
        logger.error('watchfiles loop exited unexpectedly: %s', e)
