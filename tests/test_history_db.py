import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True)
def tmp_db(tmp_path):
    """Redirect DB_PATH to a temp file for each test."""
    db_file = tmp_path / 'test_history.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        yield db_file


def test_init_db_creates_tables(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db
        init_db()
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert 'sessions' in tables
    assert 'messages' in tables
    assert 'messages_fts' in tables


def test_upsert_and_last_line(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_session, get_last_line, set_last_line
        init_db()
        upsert_session('sess1', 'proj1', 'My Project', '/path/to/sess1.jsonl')
        assert get_last_line('sess1') == 0
        set_last_line('sess1', 42)
        assert get_last_line('sess1') == 42


def test_insert_message_and_search(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_session, insert_message, search
        init_db()
        upsert_session('sess1', 'proj1', 'My Project', '/path/to/sess1.jsonl')
        insert_message('sess1', 'user', '你好 Claude 今天天气怎么样', 1700000000000)
        insert_message('sess1', 'assistant', '今天天气不错，阳光明媚', 1700000001000)
        results = search('天气')
        assert len(results) > 0
        assert results[0]['session_id'] == 'sess1'
        assert results[0]['project_name'] == 'My Project'
        assert 'snippet' in results[0]


def test_upsert_session_idempotent(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_session, set_last_line, get_last_line
        init_db()
        upsert_session('sess1', 'proj1', 'Old Name', '/old/path.jsonl')
        set_last_line('sess1', 10)
        # Re-upsert with new name — last_line must NOT reset
        upsert_session('sess1', 'proj1', 'New Name', '/new/path.jsonl')
        assert get_last_line('sess1') == 10


def test_search_empty_query_returns_empty(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, search
        init_db()
        assert search('') == []


def test_search_bad_fts_syntax_returns_empty(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, search
        init_db()
        assert search('hello)') == []
