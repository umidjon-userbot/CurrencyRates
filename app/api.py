"""HTTP API + sayt.

Barcha /api/* javoblari CORS ochiq — boshqa saytlar ham ishlata oladi.
"""
import asyncio
import csv
import io
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import config, imagegen
from . import storage as db
from .banks import BY_CODE
from .banks.base import Rate
from .collector import build_view, update_all
from .feed import build_feed

log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    task = None
    if config.UPDATE_INTERVAL_MINUTES > 0:
        async def loop():
            while True:
                try:
                    await update_all()
                except Exception as e:
                    log.exception("yangilashda xato: %s", e)
                await asyncio.sleep(config.UPDATE_INTERVAL_MINUTES * 60)
        task = asyncio.create_task(loop())
    yield
    if task:
        task.cancel()


app = FastAPI(title=f"{config.SITE_NAME} API", version="1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)

CACHE_HEADERS = {"Cache-Control": "public, max-age=300"}


@app.get("/")
def index():
    return FileResponse(config.WEB_DIR / "index.html")


@app.get("/api/currencies")
@app.get("/api/currencies.json")
def currencies():
    return {"currencies": config.CURRENCIES}


@app.get("/api/rates/{currency}.json")
def rates_static(currency: str):
    return rates(currency)


@app.get("/api/rates")
def rates(currency: str = Query("USD")):
    """Bitta valyuta bo'yicha barcha banklar + eng yaxshi kurslar."""
    if currency.upper() not in config.CURRENCIES:
        raise HTTPException(404, "bunday valyuta kuzatilmaydi")
    return JSONResponse(build_view(currency), headers=CACHE_HEADERS)


@app.get("/api/best/{currency}.json")
def best_static(currency: str):
    return best(currency)


@app.get("/api/best")
def best(currency: str = Query("USD")):
    v = build_view(currency)
    return JSONResponse(
        {
            "currency": v["currency"],
            "official": v["official"],
            "best_buy": v["best_buy"],
            "best_sell": v["best_sell"],
            "disclaimer": v["disclaimer"],
        },
        headers=CACHE_HEADERS,
    )


@app.get("/api/banks")
@app.get("/api/banks.json")
def banks():
    """Kuzatilayotgan manbalar ro'yxati."""
    return [
        {"code": a.code, "name": a.name, "kind": getattr(a, "kind", "commercial"),
         "site": a.site, "verified": getattr(a, "verified", False)}
        for a in BY_CODE.values()
    ]


@app.get("/api/history")
def history(bank: str, currency: str = "USD", days: int = 30):
    if bank not in BY_CODE:
        raise HTTPException(404, "bunday bank yo'q")
    return {"bank": bank, "currency": currency.upper(),
            "points": db.get_history(bank, currency, days)}


@app.get("/api/status")
@app.get("/api/status.json")
def status():
    """Qaysi manba ishlayapti, qaysi biri sinigan."""
    st = db.last_fetch_status()
    out = []
    for a in BY_CODE.values():
        s = st.get(a.code, {})
        out.append({
            "code": a.code, "name": a.name,
            "status": s.get("status", "never"),
            "message": s.get("message"),
            "rows": s.get("rows", 0),
            "at": s.get("at"),
        })
    healthy = sum(1 for o in out if o["status"] == "ok")
    return {"healthy": healthy, "total": len(out), "sources": out}


@app.get("/api/rates/{currency}.csv")
def rates_csv_static(currency: str):
    return rates_csv(currency)


@app.get("/api/rates.csv")
def rates_csv(currency: str = "USD"):
    v = build_view(currency)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["bank", "nomi", "oladi", "sotadi", "farq", "yangilangan", "eskirgan"])
    for b in v["banks"]:
        w.writerow([b["bank"], b["name"], b["buy"], b["sell"], b["spread"],
                    b["fetched_at"], "ha" if b["stale"] else "yo'q"])
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="kurs_{currency}.csv"'},
    )


@app.get("/feed.xml")
def feed():
    return Response(build_feed(), media_type="application/rss+xml; charset=utf-8",
                    headers=CACHE_HEADERS)


@app.get("/img/{currency}.png")
def image_static(currency: str):
    return image(currency)


@app.get("/api/image")
def image(currency: str = "USD", template: str = "daily"):
    """Kurslar yozilgan PNG. Telegram/Instagram uchun."""
    try:
        png = imagegen.render_cached(build_view(currency), template)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    return Response(png, media_type="image/png", headers=CACHE_HEADERS)


# --- admin: qo'lda kurs kiritish (manba sinib qolgan holat uchun) -----------
@app.post("/api/admin/rate")
def manual_rate(bank: str, currency: str, buy: float = None, sell: float = None,
                x_admin_token: str = Header(None)):
    if not config.ADMIN_TOKEN or x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(401, "token noto'g'ri")
    if bank not in BY_CODE:
        raise HTTPException(404, "bunday bank yo'q")
    db.save_rates(bank, [Rate(currency.upper(), buy, sell, BY_CODE[bank].site)],
                  origin="manual")
    return {"ok": True}
