"""子账号模块:消毒、会话、权限判定。"""
import threading
import time

import pytest

from vibe import accounts


@pytest.fixture(autouse=True)
def _isolated_session_db(tmp_path, monkeypatch):
    """会话现在落 history.db:测试重定向到临时库,并清空内存缓存。"""
    from vibe import history_db
    monkeypatch.setattr(history_db, "DB_PATH", tmp_path / "history.db")
    monkeypatch.setattr(history_db, "_local", threading.local())
    accounts._sessions.clear()
    yield
    accounts._sessions.clear()


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


def test_session_survives_restart():
    """mira 重启(内存清空)后,老 token 应能从 DB 恢复;drop 后彻底失效。"""
    tok = accounts.new_session("ou_persist")
    accounts._sessions.clear()                              # 模拟进程重启
    assert accounts.session_open_id(tok) == "ou_persist"    # 从 DB 回源
    assert tok in accounts._sessions                        # 回源后写回缓存
    accounts.drop_session(tok)
    accounts._sessions.clear()
    assert accounts.session_open_id(tok) is None            # DB 里也删干净了


def test_expired_session_not_restored_from_db(monkeypatch):
    """DB 里的过期会话不能复活。"""
    tok = accounts.new_session("ou_old")
    with accounts._sess_db() as conn:
        conn.execute("UPDATE sub_sessions SET expires = ? WHERE token = ?",
                     (time.time() - 1, tok))
    accounts._sessions.clear()
    assert accounts.session_open_id(tok) is None


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
