"""Buyruqlar qatori.

  python -m app.cli update              # hamma bankni yangilash (cron uchun)
  python -m app.cli update kapitalbank  # bittasini yangilash
  python -m app.cli check kapitalbank   # o'qilgan qatorlarni ko'rish (bazaga yozmaydi)
  python -m app.cli probe <url>         # sahifadagi jadvallarni ko'rish
  python -m app.cli build               # docs/ ga statik saytni yig'ish
  python -m app.cli status              # qaysi manba ishlayapti
  python -m app.cli image USD out.png   # rasm chizib ko'rish
"""
import asyncio
import sys

import httpx
from selectolax.parser import HTMLParser

from . import config
from . import storage as db
from .banks import BY_CODE
from .collector import build_view, update_all


def _client():
    return httpx.AsyncClient(
        timeout=config.FETCH_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT},
        follow_redirects=True,
    )


async def cmd_check(code):
    """Adapterni sinab ko'radi, natijani chop etadi, bazaga yozmaydi."""
    ad = BY_CODE.get(code)
    if not ad:
        print("Bunday bank yo'q. Mavjudlari:", ", ".join(BY_CODE))
        return
    async with _client() as c:
        try:
            rows = await ad.fetch(c)
        except Exception as e:
            print(f"XATO  {code}: {type(e).__name__}: {e}")
            print(f"      URL: {ad.url}")
            print("      `probe` bilan sahifa tuzilishini ko'ring.")
            return
    print(f"{ad.name} ({code}) — {len(rows)} ta valyuta")
    for r in rows:
        print(f"  {r.currency:<5} oladi={r.buy!s:<12} sotadi={r.sell!s}")


async def cmd_probe(url):
    """Sahifadagi jadvallarni chiqaradi — selektor tanlashga yordam beradi."""
    async with _client() as c:
        r = await c.get(url)
    print(f"HTTP {r.status_code}, {len(r.text)} belgi\n")
    tree = HTMLParser(r.text)
    tables = tree.css("table")
    if not tables:
        print("Sahifada <table> yo'q. Kurslar JavaScript bilan chizilgan bo'lishi mumkin —")
        print("brauzer Network bo'limidan JSON so'rovni qidiring va JsonAdapter ishlating.")
        return
    for i, t in enumerate(tables):
        rows = t.css("tr")
        print(f"--- table[{i}]  ({len(rows)} qator) ---")
        for row in rows[:5]:
            cells = [c.text(strip=True)[:22] for c in row.css("td, th")]
            print("   ", cells)
        print(f"    selektor: table:nth-of-type({i+1}) tr\n")


def cmd_status():
    db.init()
    st = db.last_fetch_status()
    for code, ad in BY_CODE.items():
        s = st.get(code, {})
        mark = {"ok": "  ok  ", "error": " XATO ", }.get(s.get("status"), " ---  ")
        print(f"[{mark}] {ad.name:<22} {s.get('rows', 0):>2} ta  {s.get('message', '') or ''}"[:110])


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "update":
        res = asyncio.run(update_all(args[1] if len(args) > 1 else None))
        ok = sum(1 for _, n, e in res if not e)
        print(f"{ok}/{len(res)} manba yangilandi")
        for code, n, err in res:
            if err:
                print(f"  XATO {code}: {err}")
    elif cmd == "check":
        asyncio.run(cmd_check(args[1]))
    elif cmd == "probe":
        asyncio.run(cmd_probe(args[1]))
    elif cmd == "build":
        from .build import build
        build(args[1] if len(args) > 1 else None)
    elif cmd == "status":
        cmd_status()
    elif cmd == "image":
        from . import imagegen
        cur = args[1] if len(args) > 1 else "USD"
        out = args[2] if len(args) > 2 else "kurs.png"
        with open(out, "wb") as f:
            f.write(imagegen.render(build_view(cur)))
        print("saqlandi:", out)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
