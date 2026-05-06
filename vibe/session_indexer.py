import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_RESCAN_INTERVAL = 600  # seconds between periodic full rescans

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
    cache_creation_tokens = 0
    cache_read_tokens = 0
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
            cache_creation_tokens += usage.get('cache_creation_input_tokens', 0)
            cache_read_tokens     += usage.get('cache_read_input_tokens', 0)

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
        'date':                   date_str,
        'messages':               message_count,
        'input_tokens':           input_tokens,
        'output_tokens':          output_tokens,
        'cache_creation_tokens':  cache_creation_tokens,
        'cache_read_tokens':      cache_read_tokens,
        'active_hours':           round(active_secs / 3600, 4),
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
                cache_creation_tokens=stats["cache_creation_tokens"],
                cache_read_tokens=stats["cache_read_tokens"],
            )
            _stats_last_updated[session_id] = now
    except Exception as e:
        logger.warning("upsert_daily_stats failed for %s: %s", path, e)


def backfill_cache_tokens() -> None:
    """One-time background job: recompute daily_stats for sessions missing cache token data.

    Runs at startup, processes sessions in small batches to avoid I/O spikes.
    Only processes sessions where cache_creation_tokens = 0 AND output_tokens > 0
    (i.e., the session was indexed before cache token tracking was added).
    """
    from vibe.history_db import _conn, upsert_daily_stats

    try:
        with _conn() as conn:
            rows = conn.execute(
                """
                SELECT s.id, s.project_id, s.file_path
                FROM   sessions s
                JOIN   daily_stats ds ON ds.session_id = s.id
                WHERE  ds.output_tokens > 0
                  AND  COALESCE(ds.cache_creation_tokens, 0) = 0
                  AND  COALESCE(ds.cache_read_tokens, 0) = 0
                ORDER  BY ds.date DESC
                """
            ).fetchall()
    except Exception as e:
        logger.warning('backfill_cache_tokens: failed to query sessions: %s', e)
        return

    if not rows:
        return

    logger.info('backfill_cache_tokens: %d sessions to recompute', len(rows))
    processed = 0
    for row in rows:
        path = Path(row['file_path'])
        if not path.exists():
            continue
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            stats = _compute_session_stats(lines)
            if stats and (stats['cache_creation_tokens'] or stats['cache_read_tokens']):
                upsert_daily_stats(
                    session_id=row['id'],
                    project_id=row['project_id'],
                    date=stats['date'],
                    messages=stats['messages'],
                    input_tokens=stats['input_tokens'],
                    output_tokens=stats['output_tokens'],
                    active_hours=stats['active_hours'],
                    cache_creation_tokens=stats['cache_creation_tokens'],
                    cache_read_tokens=stats['cache_read_tokens'],
                )
                processed += 1
        except Exception as e:
            logger.debug('backfill skip %s: %s', path.stem[:8], e)
        time.sleep(0.005)  # gentle pace: ~200 files/sec max

    logger.info('backfill_cache_tokens: updated %d/%d sessions', processed, len(rows))


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
    return 'unclassified', '未分类'


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

    # Pass 3: reclassify unclassified / sub-directory sessions
    reclassify_sessions(discovered)

    # Thread 1: watchfiles for real-time detection (non-blocking in background)
    threading.Thread(
        target=_watchfiles_loop,
        args=(dir_to_project, discovered),
        daemon=True,
        name='mira-watchfiles',
    ).start()

    # Thread 2: periodic rescan (runs in this thread, blocks forever)
    _periodic_rescan_loop(discovered)


def _watchfiles_loop(dir_to_project: dict, discovered: list[dict]) -> None:
    """Real-time detection of JSONL file changes via watchfiles."""
    import watchfiles
    watch_dirs = [str(d) for d in CLAUDE_PROJECTS_DIR.iterdir() if d.is_dir()]
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
                if parent_enc in dir_to_project:
                    project_id, project_name = dir_to_project[parent_enc]
                else:
                    project_id, project_name = _match_to_project(p, discovered)
                try:
                    index_file(p, p.stem, project_id, project_name)
                except Exception as e:
                    logger.warning('Watch index failed for %s: %s', p, e)
    except Exception as e:
        logger.error('watchfiles loop exited: %s', e)


def _periodic_rescan_loop(discovered: list[dict]) -> None:
    """Every 10 minutes: find new JSONL files and propagate project renames."""
    while True:
        time.sleep(_RESCAN_INTERVAL)
        try:
            _run_incremental_rescan(discovered)
        except Exception as e:
            logger.warning('Periodic rescan error: %s', e)


def _run_incremental_rescan(discovered: list[dict]) -> None:
    """Index JSONL files not yet in DB; propagate project renames detected via folder paths."""
    from vibe.config import load_global_config
    from vibe.scanner import discover_projects
    from vibe.history_db import get_all_session_ids

    # Re-discover projects to pick up newly added/renamed dirs
    try:
        cfg = load_global_config()
        current_discovered = discover_projects(
            cfg['scan_dirs'], cfg['exclude'],
            cfg.get('extra_projects'), cfg.get('excluded_paths'),
        )
    except Exception:
        current_discovered = discovered

    # Build current folder → project_id map
    current_folder_map: dict[str, str] = {}
    for item in current_discovered:
        encoded = _encode_path(item['path'])
        current_folder_map[encoded] = Path(item['path']).name

    # Propagate renames: if a session's Claude folder now belongs to a different project_id, update
    _check_and_apply_renames(current_folder_map)
    reclassify_sessions(current_discovered)

    # Index new JSONL files not yet in DB
    already_indexed = get_all_session_ids()
    new_files = [f for f in _all_jsonl_files_global() if f.stem not in already_indexed]
    if new_files:
        logger.info('Periodic rescan: indexing %d new JSONL files', len(new_files))
    for jsonl_path in new_files:
        try:
            project_id, project_name = _match_to_project(jsonl_path, current_discovered)
            index_file(jsonl_path, jsonl_path.stem, project_id, project_name)
        except Exception as e:
            logger.warning('Rescan index failed for %s: %s', jsonl_path, e)


def _check_and_apply_renames(current_folder_map: dict[str, str]) -> None:
    """Detect sessions whose Claude folder now maps to a different project_id and update DB."""
    from vibe.history_db import _conn, rename_project_id

    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT project_id, file_path FROM sessions"
            ).fetchall()
    except Exception:
        return

    # Group by (claude_folder_name, db_project_id) to batch renames
    rename_map: dict[tuple[str, str], str] = {}  # (old_id, new_id) → new_id
    for row in rows:
        db_pid = row['project_id']
        if not db_pid or db_pid == 'unclassified':
            continue
        fp = Path(row['file_path'])
        try:
            rel = fp.relative_to(CLAUDE_PROJECTS_DIR)
            claude_folder = rel.parts[0]
        except (ValueError, IndexError):
            continue
        current_pid = current_folder_map.get(claude_folder)
        if current_pid and current_pid != db_pid:
            rename_map[(db_pid, current_pid)] = current_pid

    for (old_id, new_id), _ in rename_map.items():
        try:
            n = rename_project_id(old_id, new_id)
            if n:
                logger.info('Renamed project_id %s → %s (%d sessions)', old_id, new_id, n)
        except Exception as e:
            logger.warning('rename_project_id(%s→%s) failed: %s', old_id, new_id, e)


def reclassify_sessions(discovered: list[dict]) -> None:
    """Reassign unclassified / mismatched sessions to projects. Three rules:

    1. Aliases: rename old project_ids declared in vibe.yaml aliases → current id.
    2. Folder-prefix: sessions from sub-directories (e.g. argus-backend) → parent project.
    3. Content-match: scan first ~3KB of unclassified sessions for project name keywords.
    """
    from vibe.history_db import rename_project_id, reclassify_by_folder, _conn

    # Build keyword → project_id map from discovered projects
    keyword_map: dict[str, str] = {}
    for item in discovered:
        project_id = Path(item['path']).name
        vibe_cfg = item.get('vibe_config') or {}

        # Rule 1: explicit aliases
        for alias in (vibe_cfg.get('aliases') or []):
            try:
                n = rename_project_id(alias, project_id)
                if n:
                    logger.info('Alias reclassify: %s → %s (%d sessions)', alias, project_id, n)
            except Exception as e:
                logger.warning('alias rename(%s→%s): %s', alias, project_id, e)

        # Rule 2: folder-prefix match
        encoded_prefix = str(CLAUDE_PROJECTS_DIR / _encode_path(item['path']))
        try:
            n = reclassify_by_folder(encoded_prefix, project_id)
            if n:
                logger.info('Folder-prefix reclassify: %s → %s (%d rows)', item['path'], project_id, n)
        except Exception as e:
            logger.warning('folder reclassify(%s): %s', item['path'], e)

        # Collect keywords for Rule 3 (project name + aliases as keywords)
        for kw in [project_id] + list(vibe_cfg.get('aliases') or []):
            keyword_map[kw.lower()] = project_id

    # Rule 3: content-scan unclassified sessions for project keywords
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT s.id, s.file_path FROM sessions s "
                "WHERE s.project_id = 'unclassified' AND s.file_path != ''"
            ).fetchall()
    except Exception:
        return

    updated = 0
    for row in rows:
        sid, fp = row['id'], row['file_path']
        if not fp:
            continue
        try:
            with open(fp, encoding='utf-8', errors='replace') as fh:
                text = fh.read(3000).lower()
        except OSError:
            continue
        matched = next((pid for kw, pid in keyword_map.items() if kw in text), None)
        if not matched:
            continue
        try:
            with _conn() as conn:
                conn.execute("UPDATE sessions SET project_id=? WHERE id=?", (matched, sid))
                conn.execute("UPDATE daily_stats SET project_id=? WHERE session_id=?", (matched, sid))
            updated += 1
        except Exception:
            pass
    if updated:
        logger.info('Content-match reclassify: %d unclassified sessions reassigned', updated)
