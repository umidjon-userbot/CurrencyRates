"""RSS 2.0 feed — har bir valyuta uchun bugungi holat bitta item."""
import hashlib
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from . import config
from .collector import build_view


def _money(v):
    return "—" if v is None else f"{v:,.0f}".replace(",", " ")


def build_feed():
    now = datetime.now(timezone.utc)
    items = []
    for cur in config.CURRENCIES:
        view = build_view(cur)
        bb, bs = view["best_buy"], view["best_sell"]
        if not (bb or bs or view["official"]):
            continue
        parts = []
        if view["official"]:
            parts.append(f"Markaziy bank: {_money(view['official'])} so'm.")
        if bb:
            parts.append(f"Eng qimmatga oladi — {bb['name']}, {_money(bb['buy'])} so'm.")
        if bs:
            parts.append(f"Eng arzonga sotadi — {bs['name']}, {_money(bs['sell'])} so'm.")
        parts.append(config.DISCLAIMER)
        desc = " ".join(parts)

        sig = f"{cur}|{view['official']}|{bb and bb['buy']}|{bs and bs['sell']}|{now:%Y-%m-%d}"
        guid = hashlib.sha1(sig.encode()).hexdigest()
        items.append({
            "title": f"{cur}: {_money(bb['buy']) if bb else _money(view['official'])} so'm — {now:%d.%m.%Y}",
            "link": f"{config.SITE_URL}/?currency={cur}",
            "guid": guid,
            "desc": desc,
            "date": format_datetime(now),
        })

    body = "".join(
        f"""    <item>
      <title>{escape(i['title'])}</title>
      <link>{escape(i['link'])}</link>
      <guid isPermaLink="false">{i['guid']}</guid>
      <pubDate>{i['date']}</pubDate>
      <description>{escape(i['desc'])}</description>
    </item>
"""
        for i in items
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(config.SITE_NAME)} — valyuta kurslari</title>
    <link>{escape(config.SITE_URL)}</link>
    <description>O'zbekiston banklaridagi valyuta oldi-sotdi kurslari</description>
    <language>uz</language>
    <lastBuildDate>{format_datetime(now)}</lastBuildDate>
{body}  </channel>
</rss>
"""
