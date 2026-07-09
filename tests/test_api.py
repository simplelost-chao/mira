import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from vibe.main import api
from vibe import main

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


# 401 断言必须显式模拟「已配密码」:没配密码时 _is_admin 开放放行,
# 不 patch 就隐式依赖本机配置(本地有密码能过,CI 干净环境返回 200)
_FAKE_ADMIN_TOKEN = patch('vibe.main._admin_token', return_value='t' * 64)


def test_history_search_no_auth():
    """Search endpoint returns 401 without admin token."""
    with _FAKE_ADMIN_TOKEN:
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
    with _FAKE_ADMIN_TOKEN:
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
    with _FAKE_ADMIN_TOKEN:
        resp = client.get('/api/terminals')
    assert resp.status_code == 401


def test_terminals_list_empty():
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.get_panes', return_value=[]):
        resp = client.get('/api/terminals', headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    assert resp.json() == []


def test_dev_project_options_returns_lightweight_local_projects():
    projects = [{
        'id': 'mira', 'name': 'Mira', 'path': '/projects/mira',
        'description': 'large field that should not be returned',
        'claude_activity': {'last_session': '2026-06-10T10:00:00Z'},
    }]
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.main._cache', projects):
        resp = client.get('/api/dev/project-options', headers={'X-Admin-Token': 'x'})
    assert resp.status_code == 200
    assert resp.json() == [{
        'id': 'mira', 'name': 'Mira', 'path': '/projects/mira',
        'last_activity': '2026-06-10T10:00:00Z',
    }]


def test_terminals_register_and_list():
    fake_pane = {'target': 'work:0.0', 'label': 'test', 'waiting': False}
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.terminal_monitor.register_pane') as mock_reg, \
         patch('vibe.terminal_monitor.get_panes', return_value=[fake_pane]):
        resp = client.post('/api/terminals/register',
                           json={'target': 'work:0.0', 'label': 'test'},
                           headers={'X-Admin-Token': 'x'})
        assert resp.status_code == 200
        mock_reg.assert_called_once_with('work:0.0', 'test', project_id=None)


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


def test_stats_no_auth():
    with _FAKE_ADMIN_TOKEN:
        resp = client.get('/api/stats')
    assert resp.status_code == 401


def test_stats_invalid_range():
    with patch('vibe.main._is_admin', return_value=True):
        resp = client.get('/api/stats?range=abc', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 400


def test_stats_admin_returns_shape():
    from unittest.mock import patch
    mock_data = {
        'days': [{'date': '2026-04-24', 'sessions': 1, 'messages': 10,
                  'input_tokens': 500, 'output_tokens': 200, 'active_hours': 0.5}],
        'projects': [{'project_id': 'mira', 'project_name': 'Mira', 'sessions': 1,
                      'total_messages': 10, 'total_input_tokens': 500,
                      'total_output_tokens': 200, 'total_hours': 0.5, 'total_cost_usd': 0.01}],
        'totals': {'active_hours': 0.5, 'input_tokens': 500, 'output_tokens': 200,
                   'estimated_cost_usd': 0.01, 'sessions': 1},
    }
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.history_db.get_stats', return_value=mock_data):
        resp = client.get('/api/stats?range=30d', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'days' in data
    assert 'projects' in data
    assert 'totals' in data


def test_stats_weekly_aggregation():
    from unittest.mock import patch
    # 14 days of data → 2 weeks expected
    days = [{'date': f'2026-04-{i+1:02d}', 'sessions': 1, 'messages': 5,
             'input_tokens': 100, 'output_tokens': 40, 'active_hours': 0.2}
            for i in range(14)]
    mock_data = {'days': days, 'projects': [], 'totals': {}}
    with patch('vibe.main._is_admin', return_value=True), \
         patch('vibe.history_db.get_stats', return_value=mock_data):
        resp = client.get('/api/stats?range=2w', headers={'X-Admin-Token': 'any'})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['days']) == 2
    assert data['days'][0]['sessions'] == 7   # first week
    assert data['days'][0]['active_hours'] == pytest.approx(1.4, abs=0.01)
    # date = last day of each 7-day bucket
    assert data['days'][0]['date'] == '2026-04-07'
    assert data['days'][1]['date'] == '2026-04-14'


def test_stats_page_returns_html():
    resp = client.get('/stats')
    assert resp.status_code == 200
    assert 'text/html' in resp.headers['content-type']
    assert b'stats' in resp.content.lower()


def test_detail_page_has_dev_link():
    """Terminal tab was migrated to /dev page; detail page now has a Dev link."""
    from unittest.mock import patch
    with patch('vibe.main.get_all_projects', return_value=[{
        'id': 'mira', 'name': 'Mira', 'path': '/mira',
        'description': '', 'tech_stack': [], 'tags': []
    }]):
        resp = client.get('/projects/mira')
    assert resp.status_code == 200
    body = resp.text
    assert '/dev' in body
    assert 'tab-summary' in body   # 概览 tab,改版后 id 从 tab-overview 改名


def test_deployments_list_requires_admin():
    with _FAKE_ADMIN_TOKEN:
        resp = client.get("/api/deployments")
    assert resp.status_code == 401


def test_deployments_crud_roundtrip(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("base_services: []\ndeployments: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        # POST writes through the REAL _write_vibe_yaml to the tmp file
        resp = client.post("/api/deployments",
                           json={"project": "foo", "ports": [8080], "depends_on": ["Ollama"]},
                           headers={"X-Admin-Token": "any"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    # Re-read the file from disk: the entry must have been persisted
    import yaml
    persisted = yaml.safe_load(fake.read_text())
    assert persisted["deployments"][0]["project"] == "foo"
    assert persisted["deployments"][0]["ports"] == [8080]
    assert persisted["deployments"][0]["depends_on"] == ["Ollama"]


def test_deployments_add_duplicate_project():
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml",
               return_value=(__import__("pathlib").Path("/tmp/x"),
                             {"deployments": [{"project": "foo"}]})), \
         patch("vibe.main._write_vibe_yaml"):
        resp = client.post("/api/deployments", json={"project": "foo"},
                           headers={"X-Admin-Token": "any"})
    assert resp.status_code == 400


def test_deploy_page_renders():
    resp = client.get("/deploy")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert 'id="port-table"' in body
    assert 'id="impact-table"' in body
    assert 'id="deploy-cards"' in body


def test_topbar_has_no_deploy_link():
    """部署入口已从 topbar 右上角移除。"""
    from vibe.topbar import topbar_html
    assert '/deploy' not in topbar_html(title="x")


def test_detail_page_has_remove_button():
    """详情页(编辑弹窗)应有'移除项目'入口,走二次确认后调用 DELETE /api/projects。"""
    from vibe.detail_page import render_detail_page
    html = render_detail_page("foo", "Foo")
    assert '移除项目' in html
    assert 'confirmDeleteProject' in html
    assert "/api/projects/" in html and "method: 'DELETE'" in html


def test_delete_project_excludes_removes_deployment_and_busts_cache(tmp_path):
    """彻底移除项目:加入 excluded_paths(隐藏发现)、清掉它的部署条目、
    即时从 _cache 剔除(不删磁盘文件)。"""
    fake = tmp_path / "vibe.yaml"
    fake.write_text(
        "excluded_paths: []\n"
        "deployments:\n"
        "  - project: ghost\n"
        "    ports: [9001]\n"
        "  - project: keep\n"
        "    ports: [9002]\n"
    )

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    excluded = []
    ghost = {"id": "ghost", "path": str(tmp_path / "ghost")}
    keep = {"id": "keep", "path": str(tmp_path / "keep")}

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main.get_all_projects", return_value=[ghost, keep]), \
         patch("vibe.config.exclude_project", side_effect=lambda p: excluded.append(p)), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        main._cache = [dict(ghost), dict(keep)]
        resp = client.delete("/api/projects/ghost", headers={"X-Admin-Token": "any"})
        assert resp.status_code == 200
        # 缓存即时剔除,无需等 120s TTL
        assert all(c["id"] != "ghost" for c in main._cache)
        assert any(c["id"] == "keep" for c in main._cache)

    # 永久排除:确实对该项目路径调用了 exclude_project
    assert excluded == [str(tmp_path / "ghost")]
    # 部署条目:ghost 清掉、keep 保留
    import yaml
    persisted = yaml.safe_load(fake.read_text())
    left = [d["project"] for d in persisted["deployments"]]
    assert "ghost" not in left and "keep" in left


def test_deployments_post_coerces_string_ports_to_int(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("base_services: []\ndeployments: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        resp = client.post("/api/deployments",
                           json={"project": "foo", "ports": ["8080", "9000"]},
                           headers={"X-Admin-Token": "any"})
        assert resp.status_code == 200

    import yaml
    persisted = yaml.safe_load(fake.read_text())["deployments"][0]
    assert persisted["ports"] == [8080, 9000]  # coerced to ints, not strings


def test_deployments_post_rejects_invalid_ports(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("base_services: []\ndeployments: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        resp = client.post("/api/deployments",
                           json={"project": "foo", "ports": ["not-a-port"]},
                           headers={"X-Admin-Token": "any"})
    assert resp.status_code == 400


def test_deployments_put_coerces_string_ports(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("base_services: []\ndeployments:\n- project: foo\n  ports: [1]\n  depends_on: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        resp = client.put("/api/deployments/foo",
                          json={"ports": ["8080"]},
                          headers={"X-Admin-Token": "any"})
        assert resp.status_code == 200

    import yaml
    persisted = yaml.safe_load(fake.read_text())["deployments"][0]
    assert persisted["ports"] == [8080]


# ── Design-doc 公开分享 ────────────────────────────────────────────────────────

def _share_proj():
    return {"id": "demo", "name": "Demo Proj", "design_docs": [
        {"filename": "DESIGN.md", "title": "My Design", "content": "# Hello World", "mtime": 0},
    ]}


def test_share_design_doc_creates_token_and_is_idempotent(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main.get_all_projects", return_value=[_share_proj()]), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r1 = client.post("/api/projects/demo/design-docs/DESIGN.md/share",
                         headers={"X-Admin-Token": "x"})
        assert r1.status_code == 200
        tok = r1.json()["token"]
        assert tok
        r2 = client.post("/api/projects/demo/design-docs/DESIGN.md/share",
                         headers={"X-Admin-Token": "x"})
        assert r2.json()["token"] == tok   # 幂等:同一文档复用同一 token

    import yaml
    shares = yaml.safe_load(fake.read_text())["doc_shares"]
    assert len(shares) == 1
    assert shares[0]["project"] == "demo" and shares[0]["filename"] == "DESIGN.md"


def test_share_design_doc_404_for_missing_doc(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main.get_all_projects", return_value=[_share_proj()]), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/projects/demo/design-docs/NOPE.md/share",
                        headers={"X-Admin-Token": "x"})
    assert r.status_code == 404


def test_unshare_design_doc_removes(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares:\n  - token: tok1\n    project: demo\n    filename: DESIGN.md\n    created_at: 1\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.delete("/api/projects/demo/design-docs/DESIGN.md/share",
                          headers={"X-Admin-Token": "x"})
        assert r.status_code == 200

    import yaml
    assert yaml.safe_load(fake.read_text())["doc_shares"] == []


def test_list_project_shares(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares:\n  - token: tok1\n    project: demo\n    filename: DESIGN.md\n    created_at: 1\n"
                    "  - token: tok2\n    project: other\n    filename: X.md\n    created_at: 1\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.get("/api/projects/demo/shares", headers={"X-Admin-Token": "x"})
    assert r.status_code == 200
    assert r.json() == {"DESIGN.md": "tok1"}   # 只返回本项目的


def test_public_share_route_renders_without_auth(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares:\n  - token: tok1\n    project: demo\n    filename: DESIGN.md\n    created_at: 1\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main.get_all_projects", return_value=[_share_proj()]), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.get("/share/tok1")   # 注意:无 admin token
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "My Design" in r.text                 # 标题渲染
    assert "Hello World" in r.text                # 内容嵌入(供前端 markdown 渲染)


def test_public_share_unknown_token_404(tmp_path):
    fake = tmp_path / "vibe.yaml"
    fake.write_text("doc_shares: []\n")

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})

    with patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.get("/share/nope")
    assert r.status_code == 404


# ── Dev 侧栏:项目合并分组 + 自定义命名 ──────────────────────────────────────────

def _yaml_tmp(tmp_path, text="{}\n"):
    fake = tmp_path / "vibe.yaml"
    fake.write_text(text)

    def fake_read():
        import yaml
        return fake, (yaml.safe_load(fake.read_text()) or {})
    return fake, fake_read


def _load(fake):
    import yaml
    return yaml.safe_load(fake.read_text()) or {}


def test_dev_merge_creates_folder_with_both(tmp_path):
    fake, fake_read = _yaml_tmp(tmp_path, "dev_groups: []\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/groups/merge",
                        json={"source": "a", "target": "b", "name": "登录"},
                        headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
    groups = _load(fake)["dev_groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "登录"
    assert set(groups[0]["projects"]) == {"a", "b"}
    assert groups[0]["id"]


def test_dev_merge_adds_third_into_existing_folder(tmp_path):
    fake, fake_read = _yaml_tmp(
        tmp_path,
        "dev_groups:\n  - id: g1\n    name: F\n    projects: [a, b]\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/groups/merge",
                        json={"source": "c", "target": "a"},
                        headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
    groups = _load(fake)["dev_groups"]
    assert len(groups) == 1
    assert set(groups[0]["projects"]) == {"a", "b", "c"}


def test_dev_merge_moves_project_between_folders(tmp_path):
    fake, fake_read = _yaml_tmp(
        tmp_path,
        "dev_groups:\n"
        "  - id: g1\n    name: F1\n    projects: [a, b]\n"
        "  - id: g2\n    name: F2\n    projects: [c, d]\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        # 把 a 从 F1 拖到 F2(target d):a 离开 F1(只剩 b → 解散),加入 F2
        r = client.post("/api/dev/groups/merge",
                        json={"source": "a", "target": "d"},
                        headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
    groups = {g["id"]: set(g["projects"]) for g in _load(fake)["dev_groups"]}
    assert "g1" not in groups          # F1 只剩 b → 解散
    assert groups["g2"] == {"c", "d", "a"}


def test_dev_unmerge_dissolves_folder_when_one_left(tmp_path):
    fake, fake_read = _yaml_tmp(
        tmp_path,
        "dev_groups:\n  - id: g1\n    name: F\n    projects: [a, b]\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/groups/unmerge",
                        json={"project": "a"}, headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
    assert _load(fake)["dev_groups"] == []   # 只剩 b → 解散


def test_dev_rename_group(tmp_path):
    fake, fake_read = _yaml_tmp(
        tmp_path,
        "dev_groups:\n  - id: g1\n    name: Old\n    projects: [a, b]\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/groups/rename",
                        json={"id": "g1", "name": "New"},
                        headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
    assert _load(fake)["dev_groups"][0]["name"] == "New"


def test_dev_project_name_set_and_clear(tmp_path):
    fake, fake_read = _yaml_tmp(tmp_path, "{}\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        client.post("/api/dev/project-name",
                    json={"project_id": "a", "name": "Plan A"},
                    headers={"X-Admin-Token": "x"})
        assert _load(fake)["dev_project_names"]["a"] == "Plan A"
        client.post("/api/dev/project-name",
                    json={"project_id": "a", "name": ""},
                    headers={"X-Admin-Token": "x"})
        assert "a" not in _load(fake).get("dev_project_names", {})


def test_dev_groups_get_returns_groups_and_names(tmp_path):
    fake, fake_read = _yaml_tmp(
        tmp_path,
        "dev_groups:\n  - id: g1\n    name: F\n    projects: [a, b]\n"
        "dev_project_names:\n  a: Plan A\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.get("/api/dev/groups", headers={"X-Admin-Token": "x"})
    assert r.status_code == 200
    body = r.json()
    assert body["groups"][0]["id"] == "g1"
    assert body["names"]["a"] == "Plan A"


def test_dev_order_roundtrip(tmp_path):
    fake, fake_read = _yaml_tmp(tmp_path, "{}\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/order",
                        json={"order": ["folder:g1", "argus", "mira"]},
                        headers={"X-Admin-Token": "x"})
        assert r.status_code == 200
        g = client.get("/api/dev/groups", headers={"X-Admin-Token": "x"})
    assert _load(fake)["dev_order"] == ["folder:g1", "argus", "mira"]
    assert g.json()["order"] == ["folder:g1", "argus", "mira"]


def test_dev_order_rejects_non_list(tmp_path):
    fake, fake_read = _yaml_tmp(tmp_path, "{}\n")
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=fake_read):
        r = client.post("/api/dev/order", json={"order": "nope"},
                        headers={"X-Admin-Token": "x"})
    assert r.status_code == 400


# ── _claude_session_file:cwd → 会话 jsonl 的向上查找边界 ──────────────────────

def _enc_path(p):
    import re
    return re.sub(r"[^A-Za-z0-9-]", "-", str(p))


def _claude_home(tmp_path, session_dirs):
    """建假 ~/.claude/projects/<enc>/x.jsonl,返回 home 路径。"""
    home = tmp_path / "home"
    for d in session_dirs:
        sd = home / ".claude" / "projects" / _enc_path(d)
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "x.jsonl").write_text("{}\n")
    return home


def test_session_file_does_not_cross_scan_root(tmp_path):
    # 新项目还没有自己的会话目录时,不能向上拿到容器目录(scan_dirs)里
    # 别的项目的会话——否则新开项目的终端会混入上一个项目的历史回放
    scan = tmp_path / "home" / "work"
    home = _claude_home(tmp_path, [scan])          # 容器目录有别的会话
    (scan / "newproj").mkdir(parents=True)
    with patch("vibe.main.Path.home", return_value=home), \
         patch("vibe.config.load_global_config", return_value={"scan_dirs": [str(scan)]}):
        assert main._claude_session_file(str(scan / "newproj")) is None


def test_session_file_walks_up_within_project(tmp_path):
    # 用户在项目里 cd 进子目录:向上找到项目根的会话目录,不受边界影响
    scan = tmp_path / "home" / "work"
    proj = scan / "oldproj"
    home = _claude_home(tmp_path, [proj])
    (proj / "sub").mkdir(parents=True)
    with patch("vibe.main.Path.home", return_value=home), \
         patch("vibe.config.load_global_config", return_value={"scan_dirs": [str(scan)]}):
        f = main._claude_session_file(str(proj / "sub"))
    assert f is not None and _enc_path(proj) in str(f)


def test_session_file_exact_match_at_scan_root(tmp_path):
    # pane 就开在容器目录本身(临时会话):精确匹配仍然可用,只禁向上越界
    scan = tmp_path / "home" / "work"
    home = _claude_home(tmp_path, [scan])
    with patch("vibe.main.Path.home", return_value=home), \
         patch("vibe.config.load_global_config", return_value={"scan_dirs": [str(scan)]}):
        f = main._claude_session_file(str(scan))
    assert f is not None


# ── PTY 终端 WS:鉴权 ─────────────────────────────────────────────────────────

def test_pty_ws_rejects_without_token():
    from starlette.websockets import WebSocketDisconnect
    with patch("vibe.main._admin_token", return_value="tok"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/terminal/mira:0.0/pty"):
                pass


def test_pty_ws_rejects_sub_foreign_target():
    from starlette.websockets import WebSocketDisconnect
    with patch("vibe.main._admin_token", return_value="tok"), \
         patch("vibe.accounts.session_open_id", return_value="ou_x"), \
         patch("vibe.main._sub_target_project", return_value=None):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/terminal/mira:0.0/pty?token=subtok"):
                pass


def test_pty_ws_owner_gets_init_frame():
    # attach 全链路 mock 掉,只验证协议首帧
    with patch("vibe.main._admin_token", return_value="tok"), \
         patch("vibe.tmux_bridge.create_viewer_session", return_value="v-abc123abc123"), \
         patch("vibe.tmux_bridge.window_size", return_value=(120, 40)), \
         patch("vibe.tmux_bridge.kill_viewer_session"), \
         patch("vibe.main._spawn_pty_attach", return_value=(None, None)) as _sp:
        with client.websocket_connect("/ws/terminal/mira:0.0/pty?token=tok") as ws:
            msg = ws.receive_json()
    assert msg == {"type": "init", "cols": 120, "rows": 40}
