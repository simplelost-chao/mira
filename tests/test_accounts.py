"""子账号模块:消毒、会话、权限判定。"""
import time

from vibe import accounts


def test_sanitize_strips_control_chars_keeps_text():
    # Ctrl-C(\x03)、Esc(\x1b)、换行回车制表都该被剥掉,可打印保留
    raw = "hello\x03 world\n\r\t\x1b[31mred\x1b 你好"
    out = accounts.sanitize_text(raw)
    assert "\x03" not in out and "\x1b" not in out
    assert "\n" not in out and "\r" not in out and "\t" not in out
    assert "hello" in out and "world" in out and "你好" in out


def test_sanitize_empty_and_none():
    assert accounts.sanitize_text("") == ""
    assert accounts.sanitize_text(None) == ""


def test_session_roundtrip_and_drop():
    tok = accounts.new_session("ou_abc")
    assert accounts.session_open_id(tok) == "ou_abc"
    accounts.drop_session(tok)
    assert accounts.session_open_id(tok) is None


def test_session_expired_returns_none(monkeypatch):
    tok = accounts.new_session("ou_x")
    # 把会话过期时间改到过去
    accounts._sessions[tok]["expires"] = time.time() - 1
    assert accounts.session_open_id(tok) is None
    assert tok not in accounts._sessions   # 过期即清理


def test_session_unknown_token():
    assert accounts.session_open_id("nope") is None
    assert accounts.session_open_id("") is None


def test_find_account():
    accs = [{"feishu_open_id": "ou_1"}, {"feishu_open_id": "ou_2"}]
    assert accounts.find_account(accs, "ou_2")["feishu_open_id"] == "ou_2"
    assert accounts.find_account(accs, "ou_x") is None
    assert accounts.find_account([], "ou_1") is None


def test_account_can_access_project():
    active = {"status": "active", "projects": ["a", "b"]}
    assert accounts.account_can_access_project(active, "a") is True
    assert accounts.account_can_access_project(active, "z") is False
    # pending / disabled 一律无权
    assert accounts.account_can_access_project({"status": "pending", "projects": ["a"]}, "a") is False
    assert accounts.account_can_access_project({"status": "disabled", "projects": ["a"]}, "a") is False
    assert accounts.account_can_access_project(None, "a") is False
