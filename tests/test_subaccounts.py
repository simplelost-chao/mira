"""子账号端点:owner 账号管理 + 子账号作用域受限访问。"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from vibe.main import api
from vibe import accounts

client = TestClient(api)


def _yaml(tmp_path, accs):
    import yaml
    fake = tmp_path / "vibe.yaml"
    fake.write_text(yaml.safe_dump({"accounts": accs}, allow_unicode=True))

    def r():
        import yaml as _y
        return fake, (_y.safe_load(fake.read_text()) or {})
    return fake, r


# ── owner 账号管理 ────────────────────────────────────────────────────────────

def test_owner_lists_accounts(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_1", "name": "Z", "status": "pending", "projects": []}])
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        resp = client.get("/api/accounts", headers={"X-Admin-Token": "x"})
    assert resp.status_code == 200
    assert resp.json()[0]["feishu_open_id"] == "ou_1"


def test_non_owner_cannot_list_accounts():
    with patch("vibe.main._is_admin", return_value=False):
        resp = client.get("/api/accounts")
    assert resp.status_code == 401


def test_owner_approve_and_grant_projects(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_1", "name": "Z", "status": "pending", "projects": []}])
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        assert client.post("/api/accounts/ou_1/approve", headers={"X-Admin-Token": "x"}).status_code == 200
        assert client.put("/api/accounts/ou_1/projects", json={"projects": ["proj-a"]},
                          headers={"X-Admin-Token": "x"}).status_code == 200
    import yaml
    saved = yaml.safe_load(fake.read_text())["accounts"][0]
    assert saved["status"] == "active"
    assert saved["projects"] == ["proj-a"]


def test_owner_disable_account(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_1", "status": "active", "projects": ["a"]}])
    with patch("vibe.main._is_admin", return_value=True), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        assert client.post("/api/accounts/ou_1/disable", headers={"X-Admin-Token": "x"}).status_code == 200
    import yaml
    assert yaml.safe_load(fake.read_text())["accounts"][0]["status"] == "disabled"


# ── 子账号作用域访问 ──────────────────────────────────────────────────────────

def _sub(tmp_path, projects, status="active"):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_s", "name": "Sub", "status": status, "projects": projects}])
    return fake, r, accounts.new_session("ou_s")


def test_sub_me_returns_granted_projects(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        resp = client.get("/api/sub/me", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Sub" and resp.json()["projects"] == ["proj-a"]


def test_sub_no_token_unauthorized(tmp_path):
    with patch("vibe.main._is_admin", return_value=False):
        assert client.get("/api/sub/me").status_code == 401


def test_disabled_sub_unauthorized(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"], status="disabled")
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        assert client.get("/api/sub/me", headers={"X-Sub-Token": tok}).status_code == 401


def test_sub_can_read_granted_claude_pane(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    panes = [{"target": "s:1.0", "project_id": "proj-a", "command": "claude"}]
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.terminal_monitor.get_panes", return_value=panes), \
         patch("vibe.tmux_bridge.capture_pane", return_value="claude says hi"):
        resp = client.get("/api/sub/pane/s:1.0/output", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert "claude says hi" in resp.json()["output"]


def test_sub_denied_non_granted_project(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    panes = [{"target": "s:2.0", "project_id": "proj-OTHER", "command": "claude"}]
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.terminal_monitor.get_panes", return_value=panes):
        resp = client.get("/api/sub/pane/s:2.0/output", headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


def test_sub_send_sanitizes_and_submits(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    panes = [{"target": "s:1.0", "project_id": "proj-a", "command": "claude"}]
    sent = {}
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.terminal_monitor.get_panes", return_value=panes), \
         patch("vibe.tmux_bridge.send_keys", side_effect=lambda t, k: sent.update(target=t, keys=k)):
        resp = client.post("/api/sub/pane/s:1.0/send", json={"text": "hi\x03 claude"},
                           headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert "\x03" not in sent["keys"]
    assert sent["keys"].endswith("\n")              # 补了回车提交
    assert "hi" in sent["keys"] and "claude" in sent["keys"]


def test_sub_send_to_non_claude_pane_denied(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    panes = [{"target": "s:9.0", "project_id": "proj-a", "command": "bash"}]  # 非 claude/codex
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.terminal_monitor.get_panes", return_value=panes):
        resp = client.post("/api/sub/pane/s:9.0/send", json={"text": "x"}, headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


# ── 飞书 OAuth 回调 ───────────────────────────────────────────────────────────

def _state():
    import time as _t
    from vibe import main as _m
    s = "teststate"
    _m._feishu_states[s] = _t.time() + 600
    return s


def test_feishu_callback_new_user_pending(tmp_path):
    fake, r = _yaml(tmp_path, [])
    s = _state()
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "ou_new", "name": "新人"}):
        resp = client.get(f"/auth/feishu/callback?code=c&state={s}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "status=pending" in resp.headers["location"]
    import yaml
    accs = yaml.safe_load(fake.read_text())["accounts"]
    assert accs[0]["feishu_open_id"] == "ou_new" and accs[0]["status"] == "pending"
    assert accs[0]["projects"] == []


def test_feishu_callback_active_user_gets_session(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_a", "name": "A", "status": "active", "projects": ["p"]}])
    s = _state()
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "ou_a", "name": "A"}):
        resp = client.get(f"/auth/feishu/callback?code=c&state={s}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    loc = resp.headers["location"]
    assert "token=" in loc
    tok = loc.split("token=")[1]
    assert accounts.session_open_id(tok) == "ou_a"   # 会话真发了


def test_feishu_callback_bad_state_rejected(tmp_path):
    fake, r = _yaml(tmp_path, [])
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "x"}):
        resp = client.get("/auth/feishu/callback?code=c&state=bogus", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "error=state" in resp.headers["location"]


def test_feishu_callback_pending_user_no_session(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_p", "status": "pending", "projects": []}])
    s = _state()
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "ou_p", "name": "P"}):
        resp = client.get(f"/auth/feishu/callback?code=c&state={s}", follow_redirects=False)
    assert "status=pending" in resp.headers["location"]
    assert "token=" not in resp.headers["location"]
