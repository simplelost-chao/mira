import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / '.vibe-manager' / 'history.db'


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
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
        """)


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
