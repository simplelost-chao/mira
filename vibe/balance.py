"""API provider balance fetcher.

Each provider is defined in PROVIDERS. A provider is shown in the dashboard
only when its API key is present in the config. Results are cached for 1 hour.
"""

import time
import threading
import urllib.request
import urllib.error
import json
import hmac
import hashlib
import datetime
import urllib.parse
from typing import Optional

# ── Provider registry ──────────────────────────────────────────────────────────
# To add a new provider: append an entry here and add its config_key to
# load_global_config() in config.py.

PROVIDERS = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "config_key": "openrouter_api_key",
        "url": "https://openrouter.ai/api/v1/credits",
        "parse": "_parse_openrouter",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "config_key": "deepseek_api_key",
        "url": "https://api.deepseek.com/user/balance",
        "parse": "_parse_deepseek",
    },
    {
        "id": "kimi",
        "name": "Kimi",
        "config_key": "kimi_api_key",
        "url": "https://api.moonshot.cn/v1/users/me/balance",
        "parse": "_parse_kimi",
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "config_key": "gemini_api_key",
        "url": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth_type": "query_key",
        "parse": "_parse_gemini",
        "optional_balance": True,
    },
    {
        "id": "doubao",
        "name": "豆包",
        "config_key": "doubao_access_key",   # 火山引擎 AK（余额查询）
        "config_key_alt": "doubao_api_key",  # ARK API key（兜底，只显示已配置）
        "secret_key": "doubao_secret_key",
        "parse": "_parse_doubao",
        "optional_balance": True,
    },
]


# ── Parsers ────────────────────────────────────────────────────────────────────

def _parse_openrouter(data: dict) -> dict:
    d = data.get("data", {})
    total = d.get("total_credits", 0)
    used  = d.get("total_usage", 0)
    remaining = round(total - used, 4)
    return {
        "balance": remaining,
        "used": round(used, 4),
        "limit": round(total, 4),
        "currency": "USD",
        "unit": "$",
    }


def _parse_deepseek(data: dict) -> dict:
    # {"is_available": true, "balance_infos": [{"currency": "CNY", "total_balance": "...", ...}]}
    infos = data.get("balance_infos", [])
    if not infos:
        return {"balance": None, "used": None, "currency": "CNY", "unit": "¥"}
    info = infos[0]
    currency = info.get("currency", "CNY")
    unit = "¥" if currency == "CNY" else "$"
    total = info.get("total_balance")
    granted = info.get("granted_balance")      # free credits
    topped = info.get("topped_up_balance")     # paid credits
    return {
        "balance": float(total) if total else None,
        "granted": float(granted) if granted else None,
        "topped": float(topped) if topped else None,
        "used": None,
        "currency": currency,
        "unit": unit,
    }


def _parse_kimi(data: dict) -> dict:
    # {"code": 0, "data": {"available_balance": "...", "cash_balance": "...", "voucher_balance": "..."}}
    d = data.get("data", data)
    avail = d.get("available_balance") or d.get("balance")
    return {
        "balance": float(avail) if avail else None,
        "used": None,
        "currency": "CNY",
        "unit": "¥",
    }


def _parse_gemini(data: dict) -> dict:
    # Response is a model list — just confirms key is valid; no balance concept
    return {
        "balance": None,
        "used": None,
        "currency": "USD",
        "unit": "$",
        "label": "免费",
    }


def _parse_doubao(data: dict) -> dict:
    # QueryBalanceAcct response: {"Result": {"AvailableBalance": "77.01", "CashBalance": "83.01", ...}}
    result = data.get("Result", {})
    available = result.get("AvailableBalance")
    cash = result.get("CashBalance")
    freeze = result.get("FreezeAmount")
    return {
        "balance": float(available) if available else None,
        "topped": float(cash) if cash else None,
        "granted": float(freeze) if freeze else None,
        "used": None,
        "currency": "CNY",
        "unit": "¥",
    }


_PARSERS = {
    "_parse_openrouter": _parse_openrouter,
    "_parse_deepseek": _parse_deepseek,
    "_parse_kimi": _parse_kimi,
    "_parse_gemini": _parse_gemini,
    "_parse_doubao": _parse_doubao,
}


# ── HTTP fetch ─────────────────────────────────────────────────────────────────

def _volcengine_balance(access_key: str, secret_key: str, timeout: float = 8.0) -> Optional[dict]:
    """Query 火山引擎 account balance via QueryBalanceAcct (HMAC-SHA256 signed)."""
    host = "open.volcengineapi.com"
    service = "billing"
    region = "cn-north-1"
    method = "GET"
    path = "/"
    query_params = {"Action": "QueryBalanceAcct", "Version": "2022-01-01"}

    now = datetime.datetime.utcnow()
    date_str = now.strftime("%Y%m%d")
    datetime_str = now.strftime("%Y%m%dT%H%M%SZ")

    canonical_query = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
        for k, v in sorted(query_params.items())
    )
    canonical_headers = f"host:{host}\nx-date:{datetime_str}\n"
    signed_headers = "host;x-date"
    payload_hash = hashlib.sha256(b"").hexdigest()
    canonical_request = "\n".join([method, path, canonical_query,
                                    canonical_headers, signed_headers, payload_hash])

    credential_scope = f"{date_str}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256", datetime_str, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    def _hmac(key: bytes, data: str) -> bytes:
        return hmac.new(key, data.encode(), hashlib.sha256).digest()

    signing_key = _hmac(_hmac(_hmac(_hmac(secret_key.encode(), date_str), region), service), "request")
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    url = f"https://{host}/?{canonical_query}"
    req = urllib.request.Request(url, headers={
        "Authorization": authorization,
        "X-Date": datetime_str,
        "Host": host,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _fetch(url: str, api_key: str, timeout: float = 8.0, auth_type: str = "bearer") -> Optional[dict]:
    if auth_type == "query_key":
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}key={api_key}"
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# ── OpenRouter activity (management key) ──────────────────────────────────────

_activity_cache: list[dict] = []
_activity_cache_ts: float = 0.0
_activity_lock = threading.Lock()
_ACTIVITY_TTL = 3600  # 1 hour


def fetch_openrouter_activity(config: dict, force: bool = False) -> list[dict]:
    """Return daily cost breakdown for OpenRouter (last 30 days).

    Requires a management key. Returns list of {date, cost_usd} sorted ascending.
    Returns [] if key missing or API fails.
    """
    global _activity_cache, _activity_cache_ts

    with _activity_lock:
        if not force and _activity_cache and (time.time() - _activity_cache_ts) < _ACTIVITY_TTL:
            return _activity_cache

    key = config.get("openrouter_api_key")
    if not key:
        return []

    raw = _fetch("https://openrouter.ai/api/v1/activity?limit=500", key)
    if not raw or "data" not in raw:
        return []

    # Aggregate by day
    by_day: dict[str, float] = {}
    for row in raw["data"]:
        day = str(row.get("date", ""))[:10]
        if not day:
            continue
        by_day[day] = round(by_day.get(day, 0.0) + float(row.get("usage", 0)), 6)

    result = [{"date": d, "cost_usd": round(v, 4)} for d, v in sorted(by_day.items())]

    with _activity_lock:
        _activity_cache = result
        _activity_cache_ts = time.time()

    return result


# ── Cache ──────────────────────────────────────────────────────────────────────

_cache: list[dict] = []
_cache_ts: float = 0.0
_cache_lock = threading.Lock()
_CACHE_TTL = 3600  # 1 hour


def fetch_all_balances(config: dict, force: bool = False) -> list[dict]:
    """Return balance info for all configured providers. Cached for 1 hour."""
    global _cache, _cache_ts

    with _cache_lock:
        if not force and _cache and (time.time() - _cache_ts) < _CACHE_TTL:
            return _cache

    results = []
    for p in PROVIDERS:
        pid = p["id"]

        # ── 豆包：优先用 AK+SK 查真实余额，兜底用 api_key 显示已配置 ──
        if pid == "doubao":
            ak = config.get("doubao_access_key", "").strip()
            sk = config.get("doubao_secret_key", "").strip()
            api_key = config.get("doubao_api_key", "").strip()
            if not ak and not api_key:
                continue  # 什么都没配置，跳过
            if ak and sk:
                raw = _volcengine_balance(ak, sk)
                if raw is not None:
                    parsed = _parse_doubao(raw)
                    results.append({"id": pid, "name": p["name"], "error": False, **parsed})
                else:
                    results.append({"id": pid, "name": p["name"], "error": True})
            else:
                # 只有 ARK api key，无法查余额，显示已配置
                results.append({
                    "id": pid, "name": p["name"], "error": False,
                    "balance": None, "label": "已配置", "currency": "CNY", "unit": "¥",
                })
            continue

        # ── 普通 provider ──
        key = config.get(p["config_key"])
        if not key:
            continue

        raw = _fetch(p["url"], key, auth_type=p.get("auth_type", "bearer"))
        if raw is None:
            if p.get("optional_balance"):
                results.append({
                    "id": pid, "name": p["name"], "error": False,
                    "balance": None, "label": "已配置", "currency": "CNY", "unit": "¥",
                })
            else:
                results.append({"id": pid, "name": p["name"], "error": True})
            continue

        parsed = _PARSERS[p["parse"]](raw)
        results.append({"id": pid, "name": p["name"], "error": False, **parsed})

    with _cache_lock:
        _cache = results
        _cache_ts = time.time()

    return results
