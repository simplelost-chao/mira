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


def test_sub_projects_returns_granted_existing(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a", "gone"])
    projs = [{"id": "proj-a", "name": "Alpha", "path": "/p/a"}]
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main.get_all_projects", return_value=projs):
        resp = client.get("/api/sub/projects", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert resp.json() == [{"id": "proj-a", "name": "Alpha"}]   # gone 不存在,过滤掉


def test_sub_open_session_granted(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main._ensure_sub_session", return_value="sub-ou_s:0.0"):
        resp = client.post("/api/sub/project/proj-a/session", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert resp.json()["target"] == "sub-ou_s:0.0"


def test_sub_open_session_non_granted_403(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        resp = client.post("/api/sub/project/proj-OTHER/session", headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


def test_sub_output_own_session(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main._sub_target_project", return_value="proj-a"), \
         patch("vibe.tmux_bridge.capture_pane", return_value="claude says hi"):
        resp = client.get("/api/sub/pane/sub-ou_s:0.0/output", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert "claude says hi" in resp.json()["output"]


def test_sub_output_not_own_session_403(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    # _sub_target_project 返回 None = target 不属于他的 session / 无法映射项目
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main._sub_target_project", return_value=None):
        resp = client.get("/api/sub/pane/sub-OTHER:0.0/output", headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


def test_sub_send_sanitizes_and_submits(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    sent = {}
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main._sub_target_project", return_value="proj-a"), \
         patch("vibe.tmux_bridge.send_keys", side_effect=lambda t, k: sent.update(target=t, keys=k)):
        resp = client.post("/api/sub/pane/sub-ou_s:0.0/send", json={"text": "hi\x03 claude"},
                           headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    assert "\x03" not in sent["keys"]
    assert sent["keys"].endswith("\n")
    assert "hi" in sent["keys"] and "claude" in sent["keys"]


def test_sub_send_denied_not_own(tmp_path):
    fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.main._sub_target_project", return_value=None):
        resp = client.post("/api/sub/pane/sub-OTHER:0.0/send", json={"text": "x"}, headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


def test_sub_session_name_isolation():
    from vibe import main as m
    a = m._sub_session_name("ou_aaa")
    b = m._sub_session_name("ou_bbb")
    assert a != b and a.startswith("sub-")


# ── 只读终端作用域代理(/subterm)鉴权 ─────────────────────────────────────────

def test_subterm_no_cookie_forbidden():
    # 没 cookie → 403,代理不向本地 ttyd 转发
    assert client.get("/subterm/7700/").status_code == 403


def test_subterm_wrong_port_forbidden(tmp_path):
    # 持有效会话,但请求的 port 不是该子账号的端口 → 403(防偷看别人终端)
    _fake, _r, tok = _sub(tmp_path, ["proj-a"])
    resp = client.get("/subterm/1/", headers={"Cookie": f"sub_term={tok}"})
    assert resp.status_code == 403


def test_subterm_valid_cookie_passes_auth(tmp_path):
    # 鉴权通过 → 试图连本地 ttyd(未启动)→ 502,而非 403,证明鉴权放行
    from vibe import main as m
    _fake, _r, tok = _sub(tmp_path, ["proj-a"])
    port = m._sub_ttyd_port("ou_s")
    resp = client.get(f"/subterm/{port}/", headers={"Cookie": f"sub_term={tok}"})
    assert resp.status_code == 502


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
    assert "sub_status=pending" in resp.headers["location"]
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
    assert "sub_token=" in loc
    tok = loc.split("sub_token=")[1]
    assert accounts.session_open_id(tok) == "ou_a"   # 会话真发了


def test_feishu_callback_bad_state_rejected(tmp_path):
    fake, r = _yaml(tmp_path, [])
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "x"}):
        resp = client.get("/auth/feishu/callback?code=c&state=bogus", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "sub_error=state" in resp.headers["location"]


def test_accounts_page_renders():
    resp = client.get("/accounts")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert '/api/accounts' in body and 'saveGrant' in body


def test_sub_path_redirects_to_dev():
    # 子账号现在直接用 dev 页面;老 /sub 链接 302 到 /dev
    resp = client.get("/sub", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"] == "/dev"


def test_auth_check_reports_sub(tmp_path):
    # dev 页面靠 /api/auth/check 认出自己是子账号
    _fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        resp = client.get("/api/auth/check", headers={"X-Sub-Token": tok})
    assert resp.status_code == 200
    body = resp.json()
    assert body["admin"] is False
    assert body.get("sub", {}).get("projects") == ["proj-a"]


def test_pane_tokens_sub_foreign_target_403(tmp_path):
    # 子账号查不属于自己 session 的 pane 用量 → 403(防泄漏 owner 其他项目)
    _fake, r, tok = _sub(tmp_path, ["proj-a"])
    with patch("vibe.main._is_admin", return_value=False), \
         patch("vibe.main._read_vibe_yaml", side_effect=r):
        resp = client.get("/api/dev/pane-tokens?target=owner:0.0&tool=claude",
                          headers={"X-Sub-Token": tok})
    assert resp.status_code == 403


def test_feishu_callback_pending_user_no_session(tmp_path):
    fake, r = _yaml(tmp_path, [{"feishu_open_id": "ou_p", "status": "pending", "projects": []}])
    s = _state()
    with patch("vibe.main._read_vibe_yaml", side_effect=r), \
         patch("vibe.feishu_oauth.exchange_code", return_value={"open_id": "ou_p", "name": "P"}):
        resp = client.get(f"/auth/feishu/callback?code=c&state={s}", follow_redirects=False)
    assert "sub_status=pending" in resp.headers["location"]
    assert "token=" not in resp.headers["location"]
