"""JSON faylga saqlash.

GitHub Actions runneri har safar tozadan ishga tushadi, shuning uchun holat
repoda saqlanishi kerak. SQLite binar fayli git uchun noqulay — bu yerda
oddiy JSON ishlatiladi, o'zgarishlar commitda ko'rinib turadi.

Interfeysi db.py bilan bir xil, shuning uchun collector ikkalasi bilan ham
ishlayveradi.
"""
import json
import os
from datetime import datetime, timedelta, timezone

from . import config

MAX_HISTORY = 4000  # har bir bank+valyuta uchun saqlanadigan nuqtalar soni


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path():
    return config.STATE_PATH


def _load():
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("rates", {})     # "bank|CUR" -> {...}
    data.setdefault("history", {})   # "bank|CUR" -> [[seen_at, buy, sell], ...]
    data.setdefault("fetch_log", {})  # bank -> {...}
    return data


def _save(data):
    os.makedirs(os.path.dirname(_path()) or ".", exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, _path())


def init():
    if not os.path.exists(_path()):
        _save(_load())


def save_rates(bank, rows, origin="auto"):
    data = _load()
    now = utcnow()
    for r in rows:
        key = f"{bank}|{r.currency}"
        prev = data["rates"].get(key)
        changed = (not prev) or prev.get("buy") != r.buy or prev.get("sell") != r.sell
        data["rates"][key] = {
            "bank": bank, "currency": r.currency,
            "buy": r.buy, "sell": r.sell,
            "fetched_at": now, "source_url": r.source_url, "origin": origin,
        }
        if changed:
            h = data["history"].setdefault(key, [])
            h.append([now, r.buy, r.sell])
            if len(h) > MAX_HISTORY:
                del h[: len(h) - MAX_HISTORY]
    _save(data)


def log_fetch(bank, status, message="", rows=0, took_ms=0):
    data = _load()
    data["fetch_log"][bank] = {
        "bank": bank, "status": status, "message": message[:500],
        "rows": rows, "took_ms": took_ms, "at": utcnow(),
    }
    _save(data)


def get_rates(currency=None):
    data = _load()
    out = list(data["rates"].values())
    if currency:
        cur = currency.upper()
        out = [r for r in out if r["currency"] == cur]
    return out


def get_history(bank, currency, days=30):
    data = _load()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    rows = data["history"].get(f"{bank}|{currency.upper()}", [])
    return [{"seen_at": t, "buy": b, "sell": s} for t, b, s in rows if t >= since]


def last_fetch_status():
    return _load()["fetch_log"]


def is_stale(fetched_at):
    try:
        ts = datetime.fromisoformat(fetched_at)
    except (ValueError, TypeError):
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts > timedelta(hours=config.STALE_HOURS)
