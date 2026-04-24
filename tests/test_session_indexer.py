import json
import pytest
from pathlib import Path
from unittest.mock import patch


def _write_jsonl(path: Path, lines: list[dict]):
    path.write_text('\n'.join(json.dumps(l) for l in lines) + '\n', encoding='utf-8')


def test_encode_path():
    from vibe.session_indexer import _encode_path
    assert _encode_path('/Users/chao/projects/mira') == '-Users-chao-projects-mira'
    assert _encode_path('/Users/chao') == '-Users-chao'


def test_parse_line_user_string():
    from vibe.session_indexer import _parse_line
    line = json.dumps({
        "type": "user",
        "message": {"role": "user", "content": "你好"},
        "timestamp": "2026-04-24T10:00:00.000Z"
    })
    result = _parse_line(line)
    assert result is not None
    role, text, ts = result
    assert role == 'user'
    assert text == '你好'
    assert ts > 0


def test_parse_line_assistant_content_list():
    from vibe.session_indexer import _parse_line
    line = json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": [
            {"type": "text", "text": "好的，我来帮你"},
            {"type": "tool_use", "name": "Bash"}
        ]},
        "timestamp": "2026-04-24T10:00:01.000Z"
    })
    result = _parse_line(line)
    assert result is not None
    role, text, ts = result
    assert role == 'assistant'
    assert text == '好的，我来帮你'


def test_parse_line_skips_system():
    from vibe.session_indexer import _parse_line
    line = json.dumps({"type": "system", "message": {"role": "system", "content": "init"}})
    assert _parse_line(line) is None


def test_parse_line_skips_empty_content():
    from vibe.session_indexer import _parse_line
    line = json.dumps({
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "tool_use", "name": "Bash"}]},
        "timestamp": "2026-04-24T10:00:01.000Z"
    })
    assert _parse_line(line) is None


def test_parse_line_skips_malformed():
    from vibe.session_indexer import _parse_line
    assert _parse_line("not json") is None
    assert _parse_line("") is None


def test_index_file_incremental(tmp_path):
    """index_file should only process new lines after last_line."""
    db_file = tmp_path / 'history.db'
    jsonl = tmp_path / 'sess1.jsonl'

    lines = [
        {"type": "user", "message": {"role": "user", "content": "第一条消息"},
         "timestamp": "2026-04-24T10:00:00.000Z"},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "回复一"}]},
         "timestamp": "2026-04-24T10:00:01.000Z"},
    ]
    _write_jsonl(jsonl, lines)

    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db, search, get_last_line
        from vibe.session_indexer import index_file
        init_db()
        index_file(jsonl, 'sess1', 'proj1', 'My Project')
        assert get_last_line('sess1') == 2
        results = search('第一条消息')
        assert len(results) == 1

        # Append a new line and re-index — should only process the new line
        new_line = {"type": "user", "message": {"role": "user", "content": "第二条消息"},
                    "timestamp": "2026-04-24T10:00:02.000Z"}
        with open(jsonl, 'a', encoding='utf-8') as f:
            f.write(json.dumps(new_line) + '\n')

        index_file(jsonl, 'sess1', 'proj1', 'My Project')
        assert get_last_line('sess1') == 3
        results2 = search('第二条消息')
        assert len(results2) == 1


def test_find_jsonl_for_project(tmp_path):
    """_find_jsonl_for_project yields .jsonl files for known project, not other files."""
    from unittest.mock import patch
    from vibe.session_indexer import _find_jsonl_for_project, _encode_path

    # Create fake Claude projects dir
    fake_claude_dir = tmp_path / '.claude' / 'projects'
    project_path = '/Users/chao/projects/testproject'
    encoded = _encode_path(project_path)
    session_dir = fake_claude_dir / encoded
    session_dir.mkdir(parents=True)

    # Create one .jsonl and one .txt file
    (session_dir / 'abc123.jsonl').write_text('{}')
    (session_dir / 'notes.txt').write_text('notes')

    with patch('vibe.session_indexer.CLAUDE_PROJECTS_DIR', fake_claude_dir):
        results = list(_find_jsonl_for_project(project_path))

    assert len(results) == 1
    assert results[0].name == 'abc123.jsonl'


def test_find_jsonl_for_project_missing_dir(tmp_path):
    """_find_jsonl_for_project yields nothing when Claude session dir does not exist."""
    from unittest.mock import patch
    from vibe.session_indexer import _find_jsonl_for_project

    fake_claude_dir = tmp_path / '.claude' / 'projects'
    fake_claude_dir.mkdir(parents=True)

    with patch('vibe.session_indexer.CLAUDE_PROJECTS_DIR', fake_claude_dir):
        results = list(_find_jsonl_for_project('/Users/chao/projects/nonexistent'))

    assert results == []


def test_index_file_set_last_line_failure_is_logged(tmp_path, caplog):
    """If set_last_line raises ValueError, index_file logs error and doesn't raise."""
    import json
    import logging
    from unittest.mock import patch

    db_file = tmp_path / 'history.db'
    jsonl = tmp_path / 'sess2.jsonl'
    jsonl.write_text(json.dumps({
        "type": "user",
        "message": {"role": "user", "content": "测试消息"},
        "timestamp": "2026-04-24T10:00:00.000Z"
    }) + '\n', encoding='utf-8')

    with patch('vibe.history_db.DB_PATH', db_file):
        from vibe.history_db import init_db
        from vibe.session_indexer import index_file
        init_db()

        with patch('vibe.history_db.set_last_line', side_effect=ValueError('session not found')):
            with caplog.at_level(logging.ERROR, logger='vibe.session_indexer'):
                # Should not raise
                index_file(jsonl, 'sess2', 'proj2', 'My Project')

        assert any('Failed to advance last_line' in r.message for r in caplog.records)
