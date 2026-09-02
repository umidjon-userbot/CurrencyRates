"""Statik saytni yig'adi: docs/ papkasiga JSON, CSV, RSS, PNG va index.html.

GitHub Pages shu papkani tarqatadi. Server kerak emas — hamma narsa
oldindan tayyorlangan fayl.
"""
import csv
import io
import json
import os
import shutil
from pathlib import Path

from . import config, imagegen
from .banks import BY_CODE
from .collector import build_view
from .feed import build_feed
from . import storage as db


def _write(path: Path, data, binary=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(data)
    else:
        path.write_text(data, encoding="utf-8")


def _json(path: Path, obj):
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1))


def build(out_dir=None):
    out = Path(out_dir or config.BUILD_DIR)
    out.mkdir(parents=True, exist_ok=True)

    # Jekyll bu papkani qayta ishlamasin
    _write(out / ".nojekyll", "")

    # sahifa
    shutil.copyfile(config.WEB_DIR / "index.html", out / "index.html")

    made = []
    _json(out / "api" / "currencies.json", {"currencies": config.CURRENCIES})
    _json(out / "api" / "banks.json", [
        {"code": a.code, "name": a.name, "kind": getattr(a, "kind", "commercial"),
         "site": a.site, "verified": getattr(a, "verified", False)}
        for a in BY_CODE.values()
    ])

    st = db.last_fetch_status()
    sources = []
    for a in BY_CODE.values():
        s = st.get(a.code, {})
        sources.append({"code": a.code, "name": a.name,
                        "status": s.get("status", "never"),
                        "message": s.get("message"), "rows": s.get("rows", 0),
                        "at": s.get("at")})
    _json(out / "api" / "status.json", {
        "healthy": sum(1 for s in sources if s["status"] == "ok"),
        "total": len(sources), "sources": sources,
    })

    for cur in config.CURRENCIES:
        view = build_view(cur)
        _json(out / "api" / "rates" / f"{cur}.json", view)
        _json(out / "api" / "best" / f"{cur}.json", {
            "currency": view["currency"], "official": view["official"],
            "best_buy": view["best_buy"], "best_sell": view["best_sell"],
            "disclaimer": view["disclaimer"],
        })
        _json(out / "api" / "history" / f"{cur}.json", {
            "currency": cur,
            "banks": {code: db.get_history(code, cur, 90) for code in BY_CODE},
        })

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["bank", "nomi", "oladi", "sotadi", "farq", "yangilangan", "eskirgan"])
        for b in view["banks"]:
            w.writerow([b["bank"], b["name"], b["buy"], b["sell"], b["spread"],
                        b["fetched_at"], "ha" if b["stale"] else "yo'q"])
        _write(out / "api" / "rates" / f"{cur}.csv", buf.getvalue())

        try:
            _write(out / "img" / f"{cur}.png", imagegen.render(view), binary=True)
            made.append(f"img/{cur}.png")
        except Exception as e:
            print(f"  rasm chizilmadi ({cur}): {e}")

        made.append(f"api/rates/{cur}.json")

    _write(out / "feed.xml", build_feed())
    print(f"{out} ga yig'ildi: {len(made)} ta asosiy fayl + RSS, CSV, status")
    return out
