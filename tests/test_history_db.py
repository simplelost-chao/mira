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


def test_daily_stats_upsert_and_get(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_daily_stats, get_stats
        init_db()
        upsert_daily_stats('sess1', 'proj1', '2026-04-20', 10, 5000, 2000, 1.5)
        result = get_stats(range_days=30)
        assert result['totals']['sessions'] == 1
        assert result['totals']['active_hours'] == 1.5
        assert result['totals']['input_tokens'] == 5000
        day = next(d for d in result['days'] if d['date'] == '2026-04-20')
        assert day['sessions'] == 1
        assert day['active_hours'] == 1.5
        assert len(result['projects']) == 1
        assert result['projects'][0]['project_id'] == 'proj1'
        assert result['projects'][0]['total_hours'] == 1.5


def test_daily_stats_idempotent(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_daily_stats, get_stats
        init_db()
        upsert_daily_stats('sess1', 'proj1', '2026-04-20', 10, 5000, 2000, 1.5)
        # Same session re-indexed — values should be replaced, not doubled
        upsert_daily_stats('sess1', 'proj1', '2026-04-20', 12, 5500, 2200, 1.6)
        result = get_stats(range_days=30)
        assert result['totals']['sessions'] == 1
        assert result['totals']['active_hours'] == 1.6
        assert result['totals']['input_tokens'] == 5500


def test_daily_stats_multiple_sessions_same_day(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_daily_stats, get_stats
        init_db()
        upsert_daily_stats('sessA', 'proj1', '2026-04-20', 10, 5000, 2000, 1.5)
        upsert_daily_stats('sessB', 'proj1', '2026-04-20', 8, 3000, 1000, 0.8)
        result = get_stats(range_days=30)
        day = next(d for d in result['days'] if d['date'] == '2026-04-20')
        assert day['sessions'] == 2
        assert day['active_hours'] == pytest.approx(2.3, abs=0.01)
        assert result['totals']['input_tokens'] == 8000


def test_get_stats_fills_missing_days(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, upsert_daily_stats, get_stats
        init_db()
        upsert_daily_stats('sess1', 'proj1', '2026-04-20', 5, 1000, 400, 0.5)
        result = get_stats(range_days=7)
        assert len(result['days']) == 7
        empty_days = [d for d in result['days'] if d['date'] != '2026-04-20']
        for d in empty_days:
            assert d['sessions'] == 0
            assert d['active_hours'] == 0.0


def test_get_stats_empty(tmp_path):
    db_file = tmp_path / 'h.db'
    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, get_stats
        init_db()
        result = get_stats(range_days=30)
        assert all(d['sessions'] == 0 for d in result['days'])
        assert result['totals']['sessions'] == 0
        assert result['totals']['estimated_cost_usd'] == 0.0
        assert result['projects'] == []
