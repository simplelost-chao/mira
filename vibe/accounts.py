"""子账号(多用户)模型、会话与输入消毒。

存储:账号列表存在 vibe.yaml 的 `accounts`(飞书 open_id 为主键),由 main 负责读写。
登录会话内存缓存 + history.db sub_sessions 表持久化(抗 mira 重启)。

账号结构:
    {feishu_open_id, name, avatar, status: pending|active|disabled,
     projects: [project_id...], created_at, granted_by}
"""
import re
import secrets
import time

# 会话:token -> {"open_id": str, "expires": float}。
# 内存是缓存层,同时落到 history.db 的 sub_sessions 表 —— mira 重启(部署新代码、
# launchd 自愈)不再把子账号踢下线。DB 不可用时优雅退化为仅内存。
_sessions: dict[str, dict] = {}
SESSION_TTL = 7 * 24 * 3600  # 7 天


def _sess_db():
    """history.db 连接(线程本地、WAL),顺手建表。调用方负责捕获异常。"""
    from vibe.history_db import _conn
    conn = _conn()
    conn.execute("CREATE TABLE IF NOT EXISTS sub_sessions ("
                 "token TEXT PRIMARY KEY, open_id TEXT NOT NULL, expires REAL NOT NULL)")
    return conn

# 子账号发给 claude 的输入:只允许可打印文本 + 空格,删掉所有控制字符
# (含 \r \n \t、Ctrl-C(\x03)/Ctrl-D(\x04)/Ctrl-Z(\x1a)/Esc(\x1b) 等),
# 防止把 claude 打断、掉回 shell 或做转义逃逸。提交由调用方单独补一个回车。
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """消毒子账号输入:剥掉所有控制字符,只留可打印内容。"""
    return _CTRL_RE.sub("", text or "")


def new_session(open_id: str) -> str:
    token = secrets.token_urlsafe(24)
    expires = time.time() + SESSION_TTL
    _sessions[token] = {"open_id": open_id, "expires": expires}
    try:
        with _sess_db() as conn:
            conn.execute("INSERT OR REPLACE INTO sub_sessions VALUES (?, ?, ?)",
                         (token, open_id, expires))
            conn.execute("DELETE FROM sub_sessions WHERE expires < ?", (time.time(),))
    except Exception:
        pass   # 落库失败退化为仅内存(重启丢会话),不影响本次登录
    return token


def session_open_id(token: str) -> str | None:
    """返回会话对应的 open_id;不存在或已过期返回 None(并清理)。
    内存没有时回源 DB(mira 重启后内存是空的,老 token 从 DB 恢复)。"""
    if not token:
        return None
    s = _sessions.get(token)
    if not s:
        try:
            with _sess_db() as conn:
                row = conn.execute("SELECT open_id, expires FROM sub_sessions WHERE token = ?",
                                   (token,)).fetchone()
        except Exception:
            row = None
        if not row:
            return None
        s = {"open_id": row["open_id"], "expires": row["expires"]}
        _sessions[token] = s
    if s["expires"] < time.time():
        drop_session(token)
        return None
    return s["open_id"]


def drop_session(token: str) -> None:
    _sessions.pop(token, None)
    try:
        with _sess_db() as conn:
            conn.execute("DELETE FROM sub_sessions WHERE token = ?", (token,))
    except Exception:
        pass


def find_account(accounts: list[dict], open_id: str) -> dict | None:
    return next((a for a in (accounts or []) if a.get("feishu_open_id") == open_id), None)


def account_can_access_project(account: dict | None, project_id: str) -> bool:
    """active 账号、且 project_id 在其授权列表里,才算有权访问。"""
    if not account or account.get("status") != "active":
        return False
    return project_id in (account.get("projects") or [])
