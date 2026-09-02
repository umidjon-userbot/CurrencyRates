"""Banklardan kurslarni yig'ish va eng yaxshi kursni hisoblash."""
import asyncio
import logging
import time

import httpx

from . import config
from . import storage as db
from .banks import ADAPTERS, BY_CODE

log = logging.getLogger("collector")


async def fetch_one(adapter, client, sem):
    async with sem:
        t0 = time.monotonic()
        try:
            rows = await adapter.fetch(client)
            rows = [r for r in rows if r.currency in config.CURRENCIES] or rows
            db.save_rates(adapter.code, rows)
            took = int((time.monotonic() - t0) * 1000)
            db.log_fetch(adapter.code, "ok", "", len(rows), took)
            log.info("%s: %d ta valyuta (%d ms)", adapter.code, len(rows), took)
            return adapter.code, len(rows), None
        except Exception as e:  # bitta bank sinsa qolgani ishlayveradi
            took = int((time.monotonic() - t0) * 1000)
            msg = f"{type(e).__name__}: {e}"
            db.log_fetch(adapter.code, "error", msg, 0, took)
            log.warning("%s: XATO %s", adapter.code, msg)
            return adapter.code, 0, msg


async def update_all(only=None):
    db.init()
    adapters = [BY_CODE[only]] if only else [a for a in ADAPTERS if a.enabled]
    sem = asyncio.Semaphore(config.FETCH_CONCURRENCY)
    headers = {"User-Agent": config.USER_AGENT, "Accept-Language": "uz,ru;q=0.8"}
    async with httpx.AsyncClient(
        timeout=config.FETCH_TIMEOUT, headers=headers, follow_redirects=True
    ) as client:
        return await asyncio.gather(*(fetch_one(a, client, sem) for a in adapters))


# --- reyting ---------------------------------------------------------------
def build_view(currency: str):
    """Bitta valyuta bo'yicha to'liq ko'rinish: banklar ro'yxati + eng yaxshilari."""
    currency = currency.upper()
    status = db.last_fetch_status()
    rows = []
    for r in db.get_rates(currency):
        ad = BY_CODE.get(r["bank"])
        if not ad:
            continue
        stale = db.is_stale(r["fetched_at"])
        rows.append({
            "bank": r["bank"],
            "name": ad.name,
            "kind": getattr(ad, "kind", "commercial"),
            "buy": r["buy"],
            "sell": r["sell"],
            "spread": round(r["sell"] - r["buy"], 2)
                      if (r["buy"] and r["sell"] and getattr(ad, "kind", "") != "official") else None,
            "fetched_at": r["fetched_at"],
            "stale": stale,
            "origin": r["origin"],
            "source_url": r["source_url"] or ad.site,
            "last_status": (status.get(r["bank"]) or {}).get("status"),
        })

    # Reytingga faqat yangi ma'lumotli tijorat banklari kiradi
    ranked = [r for r in rows if r["kind"] == "commercial" and not r["stale"]]
    best_buy = max((r for r in ranked if r["buy"]), key=lambda r: r["buy"], default=None)
    best_sell = min((r for r in ranked if r["sell"]), key=lambda r: r["sell"], default=None)

    for r in rows:
        r["best_buy"] = bool(best_buy and r["bank"] == best_buy["bank"])
        r["best_sell"] = bool(best_sell and r["bank"] == best_sell["bank"])

    official = next((r for r in rows if r["kind"] == "official"), None)
    rows.sort(key=lambda r: (r["kind"] != "official", r["stale"], -(r["buy"] or 0)))

    return {
        "currency": currency,
        "official": official["buy"] if official else None,
        "official_at": official["fetched_at"] if official else None,
        "best_buy": best_buy,
        "best_sell": best_sell,
        "banks": rows,
        "disclaimer": config.DISCLAIMER,
    }
