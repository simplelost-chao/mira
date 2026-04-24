"""API provider balance fetcher.

Each provider is defined in PROVIDERS. A provider is shown in the dashboard
only when its API key is present in the config. Results are cached for 1 hour.
"""

import time
import threading
import urllib.request
import urllib.error
import json
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


_PARSERS = {
    "_parse_openrouter": _parse_openrouter,
    "_parse_deepseek": _parse_deepseek,
    "_parse_kimi": _parse_kimi,
}


# ── HTTP fetch ─────────────────────────────────────────────────────────────────

def _fetch(url: str, api_key: str, timeout: float = 8.0) -> Optional[dict]:
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
        key = config.get(p["config_key"])
        if not key:
            continue  # not configured → skip

        raw = _fetch(p["url"], key)
        if raw is None:
            results.append({
                "id": p["id"],
                "name": p["name"],
                "error": True,
            })
            continue

        parsed = _PARSERS[p["parse"]](raw)
        results.append({
            "id": p["id"],
            "name": p["name"],
            "error": False,
            **parsed,
        })

    with _cache_lock:
        _cache = results
        _cache_ts = time.time()

    return results
