"""子账号(多用户)模型、会话与输入消毒。

存储:账号列表存在 vibe.yaml 的 `accounts`(飞书 open_id 为主键),由 main 负责读写。
本模块只放纯逻辑 + 内存会话,方便单测、也不让 main.py 继续膨胀。

账号结构:
    {feishu_open_id, name, avatar, status: pending|active|disabled,
     projects: [project_id...], created_at, granted_by}
"""
import re
import secrets
import time

# 会话:token -> {"open_id": str, "expires": float}。仅内存(重启需重新登录)。
_sessions: dict[str, dict] = {}
SESSION_TTL = 7 * 24 * 3600  # 7 天

# 子账号发给 claude 的输入:只允许可打印文本 + 空格,删掉所有控制字符
# (含 \r \n \t、Ctrl-C(\x03)/Ctrl-D(\x04)/Ctrl-Z(\x1a)/Esc(\x1b) 等),
# 防止把 claude 打断、掉回 shell 或做转义逃逸。提交由调用方单独补一个回车。
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """消毒子账号输入:剥掉所有控制字符,只留可打印内容。"""
    return _CTRL_RE.sub("", text or "")


def new_session(open_id: str) -> str:
    token = secrets.token_urlsafe(24)
    _sessions[token] = {"open_id": open_id, "expires": time.time() + SESSION_TTL}
    return token


def session_open_id(token: str) -> str | None:
    """返回会话对应的 open_id;不存在或已过期返回 None(并清理)。"""
    if not token:
        return None
    s = _sessions.get(token)
    if not s:
        return None
    if s["expires"] < time.time():
        _sessions.pop(token, None)
        return None
    return s["open_id"]


def drop_session(token: str) -> None:
    _sessions.pop(token, None)


def find_account(accounts: list[dict], open_id: str) -> dict | None:
    return next((a for a in (accounts or []) if a.get("feishu_open_id") == open_id), None)


def account_can_access_project(account: dict | None, project_id: str) -> bool:
    """active 账号、且 project_id 在其授权列表里,才算有权访问。"""
    if not account or account.get("status") != "active":
        return False
    return project_id in (account.get("projects") or [])
