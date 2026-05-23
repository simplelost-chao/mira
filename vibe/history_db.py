import sqlite3
import threading
import time
from pathlib import Path

DB_PATH = Path.home() / '.vibe-manager' / 'history.db'

_PRICE_INPUT       = 3.00  / 1_000_000
_PRICE_OUTPUT      = 15.00 / 1_000_000
_PRICE_CACHE_WRITE = 3.75  / 1_000_000
_PRICE_CACHE_READ  = 0.30  / 1_000_000


_local = threading.local()

def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = getattr(_local, 'conn', None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                project_id  TEXT,
                project_name TEXT,
                file_path   TEXT,
                last_line   INTEGER DEFAULT 0,
                first_ts    INTEGER,
                last_ts     INTEGER,
                created_at  INTEGER
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                role        TEXT,
                content     TEXT,
                ts          INTEGER
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                session_id  UNINDEXED,
                message_id  UNINDEXED,
                tokenize='trigram'
            );
            CREATE TABLE IF NOT EXISTS daily_stats (
                session_id              TEXT PRIMARY KEY,
                project_id              TEXT NOT NULL,
                date                    TEXT NOT NULL,
                messages                INTEGER DEFAULT 0,
                input_tokens            INTEGER DEFAULT 0,
                output_tokens           INTEGER DEFAULT 0,
                cache_creation_tokens   INTEGER DEFAULT 0,
                cache_read_tokens       INTEGER DEFAULT 0,
                active_hours            REAL    DEFAULT 0.0
            );
            CREATE INDEX IF NOT EXISTS daily_stats_project_date
                ON daily_stats(project_id, date);
        """)
        # Migrate existing installations: add cache token columns if missing
        for col, defn in [
            ('cache_creation_tokens', 'INTEGER DEFAULT 0'),
            ('cache_read_tokens',     'INTEGER DEFAULT 0'),
        ]:
            try:
                conn.execute(f'ALTER TABLE daily_stats ADD COLUMN {col} {defn}')
            except sqlite3.OperationalError:
                pass
        # Migrate: change PK from session_id to (session_id, date)
        try:
            cur = conn.execute("SELECT sql FROM sqlite_master WHERE name='daily_stats' AND type='table'")
            schema = cur.fetchone()[0]
            if 'session_id              TEXT PRIMARY KEY' in schema:
                conn.executescript("""
                    ALTER TABLE daily_stats RENAME TO _daily_stats_old;
                    CREATE TABLE daily_stats (
                        session_id              TEXT NOT NULL,
                        project_id              TEXT NOT NULL,
                        date                    TEXT NOT NULL,
                        messages                INTEGER DEFAULT 0,
                        input_tokens            INTEGER DEFAULT 0,
                        output_tokens           INTEGER DEFAULT 0,
                        cache_creation_tokens   INTEGER DEFAULT 0,
                        cache_read_tokens       INTEGER DEFAULT 0,
                        active_hours            REAL    DEFAULT 0.0,
                        PRIMARY KEY (session_id, date)
                    );
                    INSERT INTO daily_stats SELECT * FROM _daily_stats_old;
                    DROP TABLE _daily_stats_old;
                    CREATE INDEX IF NOT EXISTS daily_stats_project_date
                        ON daily_stats(project_id, date);
                """)
        except Exception:
            pass  # Column already exists


def upsert_session(session_id: str, project_id: str, project_name: str, file_path: str) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, project_id, project_name, file_path, last_line, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_id   = excluded.project_id,
                project_name = excluded.project_name,
                file_path    = excluded.file_path
            """,
            (session_id, project_id, project_name, str(file_path), int(time.time() * 1000)),
        )


def get_last_line(session_id: str) -> int:
    with _conn() as conn:
        row = conn.execute(
            "SELECT last_line FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return row["last_line"] if row else 0


def set_last_line(session_id: str, n: int) -> None:
    with _conn() as conn:
        cur = conn.execute("UPDATE sessions SET last_line = ? WHERE id = ?", (n, session_id))
        if cur.rowcount == 0:
            raise ValueError(f"session not found: {session_id}")


def insert_message(session_id: str, role: str, content: str, ts: int) -> None:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (session_id, role, content, ts),
        )
        msg_id = cur.lastrowid
        conn.execute(
            "INSERT INTO messages_fts (content, session_id, message_id) VALUES (?, ?, ?)",
            (content, session_id, msg_id),
        )
        conn.execute(
            """
            UPDATE sessions SET
                first_ts = CASE WHEN first_ts IS NULL THEN ? ELSE MIN(first_ts, ?) END,
                last_ts  = CASE WHEN last_ts  IS NULL THEN ? ELSE MAX(last_ts,  ?) END
            WHERE id = ?
            """,
            (ts, ts, ts, ts, session_id),
        )


def get_sessions(project_id: str = "", limit: int = 100) -> list[dict]:
    """Return sessions from DB, optionally filtered by project_id."""
    try:
        with _conn() as conn:
            if project_id:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE project_id = ? ORDER BY last_ts DESC LIMIT ?",
                    (project_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sessions ORDER BY last_ts DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def get_all_session_ids() -> set[str]:
    """Return all session IDs already in the DB."""
    try:
        with _conn() as conn:
            rows = conn.execute("SELECT id FROM sessions").fetchall()
        return {r["id"] for r in rows}
    except sqlite3.OperationalError:
        return set()


def search(query: str, limit: int = 20) -> list[dict]:
    if not query.strip():
        return []
    with _conn() as conn:
        # trigram FTS requires ≥3 characters; fall back to LIKE for shorter queries
        if len(query.strip()) >= 3:
            try:
                rows = conn.execute(
                    """
                    SELECT s.id          AS session_id,
                           s.project_id,
                           s.project_name,
                           s.last_ts,
                           snippet(messages_fts, 0, '<mark>', '</mark>', '…', 20) AS snippet
                    FROM   messages_fts
                    JOIN   sessions s ON messages_fts.session_id = s.id
                    WHERE  messages_fts MATCH ?
                    ORDER  BY rank
                    LIMIT  ?
                    """,
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        else:
            try:
                rows = conn.execute(
                    """
                    SELECT s.id          AS session_id,
                           s.project_id,
                           s.project_name,
                           s.last_ts,
                           m.content    AS snippet
                    FROM   messages m
                    JOIN   sessions s ON m.session_id = s.id
                    WHERE  m.content LIKE ?
                    ORDER  BY m.ts DESC
                    LIMIT  ?
                    """,
                    (f"%{query}%", limit),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        return [dict(r) for r in rows]


def upsert_daily_stats(
    session_id: str,
    project_id: str,
    date: str,
    messages: int,
    input_tokens: int,
    output_tokens: int,
    active_hours: float,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> None:
    """Insert or replace stats for one session + date (per-day granularity)."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_stats
                (session_id, project_id, date, messages, input_tokens, output_tokens,
                 active_hours, cache_creation_tokens, cache_read_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, date) DO UPDATE SET
                project_id              = excluded.project_id,
                messages                = excluded.messages,
                input_tokens            = excluded.input_tokens,
                output_tokens           = excluded.output_tokens,
                active_hours            = excluded.active_hours,
                cache_creation_tokens   = excluded.cache_creation_tokens,
                cache_read_tokens       = excluded.cache_read_tokens
            """,
            (session_id, project_id, date, messages, input_tokens, output_tokens,
             active_hours, cache_creation_tokens, cache_read_tokens),
        )


def get_project_activity(
    project_id: str,
    folder_prefix: str,
    extra_ids: list[str] | None = None,
) -> dict:
    """Query DB for project card stats. Returns {} if no sessions found.

    Matches sessions by:
    1. project_id (or extra_ids aliases) — covers content-scan classified sessions
    2. file_path prefix — covers sessions physically in the project's Claude folder
       (handles renamed/moved projects whose sessions are in the right folder)
    """
    from datetime import date as _date, timedelta

    today = _date.today()
    d_7d  = (today - timedelta(days=7)).isoformat()
    d_30d = (today - timedelta(days=30)).isoformat()
    d_15d = (today - timedelta(days=14)).isoformat()

    all_ids = [project_id] + list(extra_ids or [])
    id_placeholders = ','.join('?' * len(all_ids))
    # folder_prefix e.g. /Users/chao/.claude/projects/-Users-chao-Documents-Projects-argus
    folder_like = folder_prefix + '/%'

    try:
        with _conn() as conn:
            # Single query: all matching sessions (deduped by session_id PK)
            rows = conn.execute(
                f"""
                SELECT ds.session_id,
                       ds.date,
                       ds.input_tokens,
                       ds.output_tokens,
                       COALESCE(ds.cache_creation_tokens, 0) AS cache_creation_tokens,
                       COALESCE(ds.cache_read_tokens, 0)     AS cache_read_tokens,
                       ds.active_hours,
                       s.last_ts,
                       s.file_path
                FROM   daily_stats ds
                JOIN   sessions s ON s.id = ds.session_id
                WHERE  ds.project_id IN ({id_placeholders})
                    OR s.file_path LIKE ?
                """,
                all_ids + [folder_like],
            ).fetchall()

            if not rows:
                return {}

            # Aggregate
            count_7d = count_30d = 0
            inp = out = cc = cr = 0
            active_hours = 0.0
            last_ts = None
            day_hours: dict[str, float] = {}

            for r in rows:
                d = r['date']
                if d >= d_7d:
                    count_7d += 1
                if d >= d_30d:
                    count_30d += 1
                inp += r['input_tokens'] or 0
                out += r['output_tokens'] or 0
                cc  += r['cache_creation_tokens'] or 0
                cr  += r['cache_read_tokens'] or 0
                active_hours += r['active_hours'] or 0.0
                lt = r['last_ts']
                if lt and (last_ts is None or lt > last_ts):
                    last_ts = lt
                if d >= d_15d:
                    day_hours[d] = day_hours.get(d, 0.0) + (r['active_hours'] or 0.0)

            cost = (inp * _PRICE_INPUT + out * _PRICE_OUTPUT
                    + cc * _PRICE_CACHE_WRITE + cr * _PRICE_CACHE_READ)

            spark = [
                round(day_hours.get(
                    (today - timedelta(days=14 - i)).isoformat(), 0.0), 2)
                for i in range(15)
            ]

            last_session = None
            if last_ts:
                from datetime import datetime
                last_session = datetime.fromtimestamp(last_ts / 1000).isoformat()

            return {
                'last_session':           last_session,
                'session_count_7d':       count_7d,
                'session_count_30d':      count_30d,
                'input_tokens':           inp,
                'output_tokens':          out,
                'cache_creation_tokens':  cc,
                'cache_read_tokens':      cr,
                'estimated_cost_usd':     round(cost, 4),
                'active_hours':           round(active_hours, 1),
                'session_spark_15d':      spark,
            }
    except sqlite3.OperationalError:
        return {}


def get_latest_session_stats(folder_prefix: str) -> dict | None:
    """Return token stats for the most recent session in a Claude project folder."""
    folder_like = folder_prefix + '/%'
    try:
        with _conn() as conn:
            row = conn.execute(
                """
                SELECT ds.session_id,
                       ds.date,
                       ds.messages,
                       ds.input_tokens,
                       ds.output_tokens,
                       COALESCE(ds.cache_creation_tokens, 0) AS cache_creation_tokens,
                       COALESCE(ds.cache_read_tokens, 0)     AS cache_read_tokens,
                       ds.active_hours,
                       s.last_ts
                FROM   daily_stats ds
                JOIN   sessions s ON s.id = ds.session_id
                WHERE  s.file_path LIKE ?
                ORDER  BY s.last_ts DESC
                LIMIT  1
                """,
                (folder_like,),
            ).fetchone()
            if not row:
                return None
            inp = row['input_tokens'] or 0
            out = row['output_tokens'] or 0
            cc  = row['cache_creation_tokens'] or 0
            cr  = row['cache_read_tokens'] or 0
            cost = (inp * _PRICE_INPUT + out * _PRICE_OUTPUT
                    + cc * _PRICE_CACHE_WRITE + cr * _PRICE_CACHE_READ)
            return {
                'session_id':             row['session_id'],
                'date':                   row['date'],
                'messages':               row['messages'] or 0,
                'input_tokens':           inp,
                'output_tokens':          out,
                'cache_creation_tokens':  cc,
                'cache_read_tokens':      cr,
                'active_hours':           round(row['active_hours'] or 0, 2),
                'estimated_cost_usd':     round(cost, 4),
            }
    except sqlite3.OperationalError:
        return None


def get_session_details(
    project_id: str,
    folder_prefix: str,
    extra_ids: list[str] | None = None,
) -> list[dict]:
    """Return per-session token stats for a project, newest first."""
    all_ids = [project_id] + list(extra_ids or [])
    id_placeholders = ','.join('?' * len(all_ids))
    folder_like = folder_prefix + '/%'

    try:
        with _conn() as conn:
            rows = conn.execute(
                f"""
                SELECT ds.session_id,
                       ds.date,
                       ds.messages,
                       ds.input_tokens,
                       ds.output_tokens,
                       COALESCE(ds.cache_creation_tokens, 0) AS cache_creation_tokens,
                       COALESCE(ds.cache_read_tokens, 0)     AS cache_read_tokens,
                       ds.active_hours,
                       s.last_ts
                FROM   daily_stats ds
                JOIN   sessions s ON s.id = ds.session_id
                WHERE  ds.project_id IN ({id_placeholders})
                    OR s.file_path LIKE ?
                ORDER  BY s.last_ts DESC
                """,
                all_ids + [folder_like],
            ).fetchall()

            result = []
            for r in rows:
                inp = r['input_tokens'] or 0
                out = r['output_tokens'] or 0
                cc  = r['cache_creation_tokens'] or 0
                cr  = r['cache_read_tokens'] or 0
                cost = (inp * _PRICE_INPUT + out * _PRICE_OUTPUT
                        + cc * _PRICE_CACHE_WRITE + cr * _PRICE_CACHE_READ)
                result.append({
                    'session_id':             r['session_id'],
                    'date':                   r['date'],
                    'messages':               r['messages'] or 0,
                    'input_tokens':           inp,
                    'output_tokens':          out,
                    'cache_creation_tokens':  cc,
                    'cache_read_tokens':      cr,
                    'active_hours':           round(r['active_hours'] or 0, 2),
                    'estimated_cost_usd':     round(cost, 4),
                })
            return result
    except sqlite3.OperationalError:
        return []


def rename_project_id(old_id: str, new_id: str) -> int:
    """Update sessions and daily_stats from old_id to new_id. Returns rows updated."""
    with _conn() as conn:
        conn.execute(
            "UPDATE sessions SET project_id = ? WHERE project_id = ?", (new_id, old_id))
        cur = conn.execute(
            "UPDATE daily_stats SET project_id = ? WHERE project_id = ?", (new_id, old_id))
        return cur.rowcount


def reclassify_by_folder(folder_prefix: str, new_project_id: str) -> int:
    """Reassign sessions whose file_path starts with folder_prefix to new_project_id.

    Useful for:
    - Sub-directory sessions: folder '-Users-chao-Projects-argus-backend' → 'argus'
    - Old project folders that were renamed
    """
    with _conn() as conn:
        # Find matching session ids
        rows = conn.execute(
            "SELECT id FROM sessions WHERE file_path LIKE ?",
            (folder_prefix + "%",),
        ).fetchall()
        if not rows:
            return 0
        session_ids = [r[0] for r in rows]
        placeholders = ",".join("?" * len(session_ids))
        conn.execute(
            f"UPDATE sessions SET project_id = ? WHERE id IN ({placeholders})",
            [new_project_id] + session_ids,
        )
        cur = conn.execute(
            f"UPDATE daily_stats SET project_id = ? WHERE session_id IN ({placeholders})",
            [new_project_id] + session_ids,
        )
        return cur.rowcount


def get_prompts(project_id: str, limit: int = 200) -> list[dict]:
    """Return user prompts for a project, most recent first."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                """
                SELECT m.content AS text, m.ts
                FROM   messages m
                JOIN   sessions s ON m.session_id = s.id
                WHERE  s.project_id = ? AND m.role = 'user'
                ORDER  BY m.ts DESC
                LIMIT  ?
                """,
                (project_id, limit),
            ).fetchall()
        return [
            {"text": r["text"], "date": str(r["ts"] // 1000)}
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []


def get_all_project_prompts(limit_per_project: int = 50) -> list[dict]:
    """Return user prompts grouped by project, limited per project at SQL level."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                """
                SELECT project_id, project_name, text, ts
                FROM (
                    SELECT s.project_id,
                           s.project_name,
                           m.content AS text,
                           m.ts,
                           ROW_NUMBER() OVER (
                               PARTITION BY s.project_id
                               ORDER BY m.ts DESC
                           ) AS rn
                    FROM   messages m
                    JOIN   sessions s ON m.session_id = s.id
                    WHERE  m.role = 'user'
                )
                WHERE rn <= ?
                ORDER BY project_id, ts DESC
                """,
                (limit_per_project,),
            ).fetchall()
    except sqlite3.OperationalError:
        return []

    from collections import defaultdict
    grouped: dict[str, dict] = defaultdict(lambda: {"id": "", "name": "", "prompts": []})
    for r in rows:
        pid = r["project_id"]
        entry = grouped[pid]
        entry["id"] = pid
        entry["name"] = r["project_name"] or pid
        entry["prompts"].append({"text": r["text"], "date": str(r["ts"] // 1000)})

    return [v for v in grouped.values() if v["prompts"]]


def get_stats(range_days: int = 30) -> dict:
    """Return aggregated daily stats and project rankings for the last range_days days."""
    from datetime import date as _date, timedelta

    cutoff = (_date.today() - timedelta(days=range_days - 1)).isoformat()

    try:
        with _conn() as conn:
            day_rows = conn.execute(
                """
                SELECT date,
                       COUNT(DISTINCT session_id)             AS sessions,
                       SUM(messages)                          AS messages,
                       SUM(input_tokens)                      AS input_tokens,
                       SUM(output_tokens)                     AS output_tokens,
                       SUM(COALESCE(cache_creation_tokens,0)) AS cache_creation_tokens,
                       SUM(COALESCE(cache_read_tokens,0))     AS cache_read_tokens,
                       SUM(active_hours)                      AS active_hours
                FROM   daily_stats
                WHERE  date >= ?
                GROUP  BY date
                ORDER  BY date
                """,
                (cutoff,),
            ).fetchall()

            proj_rows = conn.execute(
                """
                SELECT ds.project_id,
                       CASE WHEN MAX(s.project_name) IN ('未分类', 'unclassified', '')
                            THEN ds.project_id
                            ELSE COALESCE(MAX(s.project_name), ds.project_id)
                       END  AS project_name,
                       COUNT(DISTINCT ds.session_id)                  AS sessions,
                       SUM(ds.messages)                               AS total_messages,
                       SUM(ds.input_tokens)                           AS total_input_tokens,
                       SUM(ds.output_tokens)                          AS total_output_tokens,
                       SUM(COALESCE(ds.cache_creation_tokens,0))      AS total_cache_creation_tokens,
                       SUM(COALESCE(ds.cache_read_tokens,0))          AS total_cache_read_tokens,
                       SUM(ds.active_hours)                           AS total_hours
                FROM   daily_stats ds
                LEFT   JOIN sessions s ON ds.session_id = s.id
                WHERE  ds.date >= ?
                GROUP  BY ds.project_id
                ORDER  BY total_hours DESC
                LIMIT  20
                """,
                (cutoff,),
            ).fetchall()

            total_sessions_row = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM daily_stats WHERE date >= ?",
                (cutoff,),
            ).fetchone()
            total_sessions = total_sessions_row[0] if total_sessions_row else 0
    except sqlite3.OperationalError:
        day_rows, proj_rows, total_sessions = [], [], 0

    # Build zero-padded days list
    day_map = {r["date"]: dict(r) for r in day_rows}
    days = []
    for i in range(range_days):
        d = (_date.today() - timedelta(days=range_days - 1 - i)).isoformat()
        row = day_map.get(d, {})
        days.append({
            "date":                  d,
            "sessions":              row.get("sessions", 0),
            "messages":              row.get("messages", 0),
            "input_tokens":          row.get("input_tokens", 0),
            "output_tokens":         row.get("output_tokens", 0),
            "cache_creation_tokens": row.get("cache_creation_tokens", 0),
            "cache_read_tokens":     row.get("cache_read_tokens", 0),
            "active_hours":          round(row.get("active_hours") or 0.0, 2),
        })

    projects = []
    for r in proj_rows:
        r = dict(r)
        r["total_cost_usd"] = round(
            (r["total_input_tokens"] or 0)            * _PRICE_INPUT
            + (r["total_output_tokens"] or 0)         * _PRICE_OUTPUT
            + (r["total_cache_creation_tokens"] or 0) * _PRICE_CACHE_WRITE
            + (r["total_cache_read_tokens"] or 0)     * _PRICE_CACHE_READ,
            2,
        )
        r["total_hours"] = round(r.get("total_hours") or 0.0, 2)
        projects.append(r)

    total_input  = sum(d["input_tokens"]  for d in days)
    total_output = sum(d["output_tokens"] for d in days)
    total_cc     = sum(d["cache_creation_tokens"] for d in days)
    total_cr     = sum(d["cache_read_tokens"]     for d in days)

    # ── Heatmap: last 365 days, one value per day ──────────────────────────────
    from datetime import date as _date2, timedelta as _td
    heatmap_cutoff = (_date2.today() - _td(days=364)).isoformat()
    try:
        with _conn() as conn:
            hm_rows = conn.execute(
                """
                SELECT date, SUM(active_hours) AS hours,
                       COUNT(DISTINCT session_id) AS sessions
                FROM   daily_stats
                WHERE  date >= ?
                GROUP  BY date
                """,
                (heatmap_cutoff,),
            ).fetchall()
    except sqlite3.OperationalError:
        hm_rows = []
    heatmap = {r["date"]: {"hours": round(r["hours"] or 0, 2),
                            "sessions": r["sessions"] or 0}
               for r in hm_rows}

    # ── Per-project daily breakdown: all projects ────────────────────────────
    all_proj_ids = [p["project_id"] for p in projects]
    project_days: dict[str, list] = {}
    if all_proj_ids:
        placeholders = ",".join("?" * len(all_proj_ids))
        try:
            with _conn() as conn:
                pd_rows = conn.execute(
                    f"""
                    SELECT project_id, date,
                           SUM(input_tokens)                      AS input_tokens,
                           SUM(output_tokens)                     AS output_tokens,
                           SUM(COALESCE(cache_creation_tokens,0)) AS cache_creation_tokens,
                           SUM(COALESCE(cache_read_tokens,0))     AS cache_read_tokens
                    FROM   daily_stats
                    WHERE  project_id IN ({placeholders}) AND date >= ?
                    GROUP  BY project_id, date
                    """,
                    all_proj_ids + [cutoff],
                ).fetchall()
        except sqlite3.OperationalError:
            pd_rows = []
        # Index by project_id → date → {cost, tokens}
        for r in pd_rows:
            pid = r["project_id"]
            inp = r["input_tokens"] or 0
            out = r["output_tokens"] or 0
            cw  = r["cache_creation_tokens"] or 0
            cr  = r["cache_read_tokens"] or 0
            cost = round(
                inp * _PRICE_INPUT + out * _PRICE_OUTPUT
                + cw * _PRICE_CACHE_WRITE + cr * _PRICE_CACHE_READ, 4,
            )
            project_days.setdefault(pid, {})[r["date"]] = {
                "cost": cost,
                "input_tokens": inp,
                "output_tokens": out,
                "cache_creation_tokens": cw,
                "cache_read_tokens": cr,
            }

    return {
        "days": days,
        "projects": projects,
        "totals": {
            "active_hours":            round(sum(d["active_hours"] for d in days), 1),
            "input_tokens":            total_input,
            "output_tokens":           total_output,
            "cache_creation_tokens":   total_cc,
            "cache_read_tokens":       total_cr,
            "estimated_cost_usd":      round(
                total_input  * _PRICE_INPUT  + total_output * _PRICE_OUTPUT
                + total_cc   * _PRICE_CACHE_WRITE + total_cr * _PRICE_CACHE_READ, 2),
            "sessions":                total_sessions,
        },
        "heatmap": heatmap,
        "project_days": project_days,
    }


def get_top_sessions(sort_by: str = "cost", limit: int = 50) -> list[dict]:
    """Return top sessions ranked by cost or active_hours, with first user message as task summary."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                """
                SELECT ds.session_id,
                       ds.project_id,
                       COALESCE(s.project_name, ds.project_id) AS project_name,
                       ds.date,
                       ds.messages,
                       ds.input_tokens,
                       ds.output_tokens,
                       COALESCE(ds.cache_creation_tokens, 0) AS cache_creation_tokens,
                       COALESCE(ds.cache_read_tokens, 0)     AS cache_read_tokens,
                       ds.active_hours,
                       s.first_ts,
                       s.last_ts
                FROM   daily_stats ds
                JOIN   sessions s ON s.id = ds.session_id
                ORDER  BY ds.session_id
                """,
            ).fetchall()

            if not rows:
                return []

            # Compute cost for each row and collect session ids
            enriched = []
            session_ids = []
            for r in rows:
                inp = r['input_tokens'] or 0
                out = r['output_tokens'] or 0
                cc  = r['cache_creation_tokens'] or 0
                cr  = r['cache_read_tokens'] or 0
                cost = (inp * _PRICE_INPUT + out * _PRICE_OUTPUT
                        + cc * _PRICE_CACHE_WRITE + cr * _PRICE_CACHE_READ)
                enriched.append({
                    'session_id':             r['session_id'],
                    'project_id':             r['project_id'],
                    'project_name':           r['project_name'],
                    'date':                   r['date'],
                    'messages':               r['messages'] or 0,
                    'input_tokens':           inp,
                    'output_tokens':          out,
                    'cache_creation_tokens':  cc,
                    'cache_read_tokens':      cr,
                    'active_hours':           round(r['active_hours'] or 0, 2),
                    'estimated_cost_usd':     round(cost, 4),
                    'first_ts':               r['first_ts'],
                    'last_ts':                r['last_ts'],
                })
                session_ids.append(r['session_id'])

            # Sort
            if sort_by == "hours":
                enriched.sort(key=lambda x: x['active_hours'], reverse=True)
            else:
                enriched.sort(key=lambda x: x['estimated_cost_usd'], reverse=True)

            enriched = enriched[:limit]

            # Fetch first user message for each top session
            top_ids = [s['session_id'] for s in enriched]
            placeholders = ','.join('?' * len(top_ids))
            msg_rows = conn.execute(
                f"""
                SELECT session_id, content
                FROM (
                    SELECT session_id, content,
                           ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY id ASC) AS rn
                    FROM   messages
                    WHERE  role = 'user' AND session_id IN ({placeholders})
                )
                WHERE rn = 1
                """,
                top_ids,
            ).fetchall()
            first_msg = {r['session_id']: r['content'] for r in msg_rows}

            for s in enriched:
                msg = first_msg.get(s['session_id'], '')
                # Truncate to first 120 chars, strip system prompts
                if msg:
                    msg = msg.strip().split('\n')[0][:120]
                s['task_summary'] = msg

            return enriched
    except sqlite3.OperationalError:
        return []


# Trivial confirmation patterns — these inherit the label from the previous real task
_TRIVIAL_RE = None
def _is_trivial(text: str) -> bool:
    import re
    global _TRIVIAL_RE
    if _TRIVIAL_RE is None:
        pats = (r'^(yes|no|ok|okay|好|嗯|行|对|是|不|继续|continue|go\s+ahead|done|确认|知道了|好的|明白|继续做|'
                r'proceed|sure|yep|nope|正确|没错|来吧|加油|试试|搞|干|做|再|然后|那|就这样|好吧|可以|帮我做|帮我|'
                r'[\.,\?!！？。，、…]+)$')
        _TRIVIAL_RE = re.compile(pats, re.IGNORECASE)
    stripped = text.strip()
    return len(stripped) < 20 and bool(_TRIVIAL_RE.match(stripped))


def analyze_session_turns(session_id: str) -> list[dict]:
    """Parse a session JSONL and return cost per task turn.

    A turn starts at each real user text message (not tool_result).
    Consecutive duplicate assistant usages are deduplicated.
    Trivial confirmations inherit the label from the previous real task.
    Returns top 30 turns by cost.
    """
    import json as _json

    try:
        with _conn() as conn:
            row = conn.execute(
                "SELECT file_path FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
    except sqlite3.OperationalError:
        return []
    if not row or not row['file_path']:
        return []

    try:
        with open(row['file_path'], encoding='utf-8') as f:
            lines = f.readlines()
    except OSError:
        return []

    turns: list[dict] = []
    current_label: str = ""
    current_task_label: str = ""
    cur_inp = cur_out = cur_cw = cur_cr = 0
    seen_usage_hashes: set = set()
    turn_seq = 0

    def _flush():
        nonlocal cur_inp, cur_out, cur_cw, cur_cr
        if cur_out == 0 and cur_cw == 0 and cur_cr == 0:
            cur_inp = cur_out = cur_cw = cur_cr = 0
            seen_usage_hashes.clear()
            return
        cost = cur_inp * _PRICE_INPUT + cur_out * _PRICE_OUTPUT + cur_cw * _PRICE_CACHE_WRITE + cur_cr * _PRICE_CACHE_READ
        turns.append({
            'seq':                   turn_seq,
            'label':                 current_task_label or current_label or '(无标题)',
            'raw_label':             current_label,
            'input_tokens':          cur_inp,
            'output_tokens':         cur_out,
            'cache_creation_tokens': cur_cw,
            'cache_read_tokens':     cur_cr,
            'estimated_cost_usd':    round(cost, 4),
        })
        cur_inp = cur_out = cur_cw = cur_cr = 0
        seen_usage_hashes.clear()

    for raw in lines:
        try:
            d = _json.loads(raw)
        except Exception:
            continue

        msg_type = d.get('type', '')

        if msg_type == 'user':
            msg = d.get('message', d)
            content = msg.get('content', '')
            text = ''
            if isinstance(content, list):
                if any(isinstance(c, dict) and c.get('type') == 'tool_result' for c in content):
                    continue  # tool result, not a real user turn
                text = ' '.join(
                    c.get('text', '') for c in content
                    if isinstance(c, dict) and c.get('type') == 'text'
                ).strip()
            elif isinstance(content, str):
                text = content.strip()
            if not text:
                continue

            _flush()
            turn_seq += 1
            current_label = text
            if not _is_trivial(text):
                current_task_label = text
            # else: inherit current_task_label from before

        elif msg_type == 'assistant':
            usage = d.get('message', {}).get('usage') or d.get('usage') or {}
            inp = usage.get('input_tokens', 0) or 0
            out = usage.get('output_tokens', 0) or 0
            cw  = usage.get('cache_creation_input_tokens', 0) or 0
            cr  = usage.get('cache_read_input_tokens', 0) or 0
            if inp == 0 and out == 0 and cw == 0 and cr == 0:
                continue
            h = f"{inp}:{out}:{cw}:{cr}"
            if h in seen_usage_hashes:
                continue
            seen_usage_hashes.add(h)
            cur_inp += inp
            cur_out += out
            cur_cw  += cw
            cur_cr  += cr

    _flush()

    turns.sort(key=lambda t: t['estimated_cost_usd'], reverse=True)
    return turns[:30]
