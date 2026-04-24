"""SQLite-backed persistent cache for project data."""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".vibe-manager" / "cache.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id      TEXT PRIMARY KEY,
                data    TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)


def save_projects(projects: list[dict]) -> None:
    now = time.time()
    with sqlite3.connect(DB_PATH) as conn:
        # Remove stale entries not in current set
        current_ids = [p["id"] for p in projects]
        if current_ids:
            placeholders = ",".join("?" * len(current_ids))
            conn.execute(f"DELETE FROM projects WHERE id NOT IN ({placeholders})", current_ids)
        for p in projects:
            conn.execute(
                "INSERT OR REPLACE INTO projects (id, data, updated_at) VALUES (?, ?, ?)",
                (p["id"], json.dumps(p, default=str), now),
            )


def load_projects() -> tuple[list[dict], float]:
    """Returns (projects, cache_timestamp). Empty list if DB has no data."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute("SELECT data, updated_at FROM projects").fetchall()
        if not rows:
            return [], 0.0
        projects = [json.loads(row[0]) for row in rows]
        ts = max(row[1] for row in rows)
        return projects, ts
    except Exception:
        return [], 0.0
