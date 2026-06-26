"""飞书 user OAuth —— 复用 feishu-coo 的自建应用。

端点完全对齐 feishu-coo(outbound.py)里已验证可用的实现:
  - app_access_token: POST /auth/v3/app_access_token/internal {app_id, app_secret}
  - 授权页:        GET  /authen/v1/index?app_id=&redirect_uri=&scope=&state=
  - 换码:          POST /authen/v1/access_token  (Bearer app_access_token, {grant_type, code})
                    响应 data 内含 open_id / name / avatar_url / access_token

cfg 形如 {app_id, app_secret, open_base_url, scopes, redirect_uri}。
"""
import json
import urllib.parse
import urllib.request

DEFAULT_OPEN_BASE = "https://open.feishu.cn/open-apis"


def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def build_authorize_url(cfg: dict, state: str) -> str:
    base = (cfg.get("open_base_url") or DEFAULT_OPEN_BASE).rstrip("/")
    params = {
        "app_id": cfg["app_id"],
        "redirect_uri": cfg["redirect_uri"],
        "scope": cfg.get("scopes", ""),
        "state": state,
    }
    return f"{base}/authen/v1/index?{urllib.parse.urlencode(params)}"


def _app_access_token(cfg: dict) -> str:
    base = (cfg.get("open_base_url") or DEFAULT_OPEN_BASE).rstrip("/")
    data = _post_json(f"{base}/auth/v3/app_access_token/internal",
                      {"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]})
    tok = data.get("app_access_token")
    if not tok:
        raise RuntimeError(f"取 app_access_token 失败: {data}")
    return str(tok)


def exchange_code(cfg: dict, code: str) -> dict:
    """用授权码换用户信息。返回响应里的 data:{open_id, name, avatar_url, access_token, ...}"""
    base = (cfg.get("open_base_url") or DEFAULT_OPEN_BASE).rstrip("/")
    resp = _post_json(
        f"{base}/authen/v1/access_token",
        {"grant_type": "authorization_code", "code": code},
        headers={"Authorization": f"Bearer {_app_access_token(cfg)}"},
    )
    return resp.get("data") or {}
