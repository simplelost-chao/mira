import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from vibe.main import api

client = TestClient(api)

def make_mock_project(id="test-proj"):
    return {
        "id": id, "name": "Test Project", "path": "/tmp/test",
        "status": "active", "tech_stack": [], "features": [],
        "design_docs": [], "git": None, "plans": None,
        "service": None, "loc": None, "fs": None,
        "deploy": None, "arch_summary": None, "description": None,
    }

def test_get_projects():
    with patch("vibe.main.get_all_projects", return_value=[make_mock_project()]):
        resp = client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-proj"

def test_get_project_by_id():
    with patch("vibe.main.get_all_projects", return_value=[make_mock_project("proj-abc")]):
        resp = client.get("/api/projects/proj-abc")
    assert resp.status_code == 200
    assert resp.json()["id"] == "proj-abc"

def test_get_project_not_found():
    with patch("vibe.main.get_all_projects", return_value=[]):
        resp = client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


def test_history_search_no_auth():
    """Search endpoint returns 401 without admin token."""
    resp = client.get('/api/history/search?q=test')
    assert resp.status_code == 401


def test_history_search_admin():
    """Search endpoint returns results when called with mock admin."""
    from unittest.mock import patch
    mock_results = [{'session_id': 's1', 'project_id': 'p1', 'project_name': 'P', 'last_ts': 0, 'snippet': 'hi'}]
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.history_db.search', return_value=mock_results):
        resp = client.get('/api/history/search?q=hi', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]['session_id'] == 's1'


def test_history_search_empty_query():
    """Empty q returns empty list immediately."""
    with patch('vibe.main._is_admin', return_value=True):
        resp = client.get('/api/history/search?q=', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 200
    assert resp.json() == []


def test_history_sessions_no_auth():
    """Sessions endpoint returns 401 without admin token."""
    resp = client.get('/api/history/sessions')
    assert resp.status_code == 401


def test_history_sessions_admin_empty():
    """Sessions endpoint returns empty list when DB has no data."""
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.history_db.get_sessions', return_value=[]):
        resp = client.get('/api/history/sessions', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 200
    assert resp.json() == []


# ── Terminal endpoints ────────────────────────────────────────────────────────

def test_terminals_no_auth():
    resp = client.get('/api/terminals')
    assert resp.status_code == 401


def test_terminals_list_empty():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.get_panes', return_value=[]):
        resp = client.get('/api/terminals', headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    assert resp.json() == []


def test_terminals_register_and_list():
    fake_pane = {'target': 'work:0.0', 'label': 'test', 'waiting': False}
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.register_pane') as mock_reg, \
         patch('vibe.terminal_monitor.get_panes', return_value=[fake_pane]):
        resp = client.post('/api/terminals/register',
                           json={'target': 'work:0.0', 'label': 'test'},
                           headers={'X-Admin-Token': 'x'})
        assert resp.status_code == 200
        mock_reg.assert_called_once_with('work:0.0', 'test')


def test_terminals_output_success():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.tmux_bridge.capture_pane', return_value='line1\nline2'):
        resp = client.get('/api/terminals/work%3A0.0/output',
                          headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['target'] == 'work:0.0'
    assert 'line1' in data['output']


def test_terminals_output_error():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.tmux_bridge.capture_pane', side_effect=RuntimeError('bad target')):
        resp = client.get('/api/terminals/bad%3A9.9/output',
                          headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 400


def test_terminals_send_keys():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.tmux_bridge.send_keys') as mock_send:
        resp = client.post('/api/terminals/work%3A0.0/send',
                           json={'keys': 'y\n'},
                           headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    mock_send.assert_called_once_with('work:0.0', 'y\n')


def test_terminals_send_keys_tmux_error():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.tmux_bridge.send_keys', side_effect=RuntimeError('bad target')):
        resp = client.post('/api/terminals/bad%3A9.9/send',
                           json={'keys': 'y\n'},
                           headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 400


def test_terminals_alerts():
    fake = [{'target': 'work:0.0', 'label': 'claude/mira', 'snippet': 'proceed?', 'ts': 0}]
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.get_terminal_alerts', return_value=fake):
        resp = client.get('/api/terminals/alerts', headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    assert resp.json()[0]['target'] == 'work:0.0'


def test_terminals_send_empty_keys():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.get_panes', return_value=[{'target': 'work:0.0', 'label': 'test', 'command': 'ccc', 'cwd': '/tmp', 'auto': True, 'waiting': False}]):
        resp = client.post(
            '/api/terminals/work%3A0.0/send',
            json={'keys': ''},
            headers={'X-Admin-Token': 'x'},
        )
    assert resp.status_code == 400
