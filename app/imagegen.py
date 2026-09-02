"""Tayyor rasm shabloni ustiga kurslarni yozib beradi.

Shablon = JSON config + fon rasmi. Dizayner yangi PNG bersa, faqat
JSONdagi koordinatalarni to'g'rilaysiz, kodga tegmaysiz.
"""
import hashlib
import json
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from . import config

FALLBACK_FONTS = {
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}
_font_cache = {}


def load_font(path, size):
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except OSError:
            _font_cache[key] = ImageFont.load_default(size)
    return _font_cache[key]


def money(v):
    if v is None:
        return "—"
    return f"{v:,.0f}".replace(",", " ")


def load_template(name):
    path = config.TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"shablon topilmadi: {name}")
    with open(path, encoding="utf-8") as f:
        tpl = json.load(f)
    tpl["_dir"] = str(config.TEMPLATES_DIR)
    return tpl


def _draw_text(draw, text, spec, fonts, tokens):
    for k, v in tokens.items():
        text = text.replace("{" + k + "}", str(v))
    font = load_font(fonts.get(spec.get("font", "regular")), spec.get("size", 32))
    x, y = spec["x"], spec["y"]
    anchor = {"left": "la", "center": "ma", "right": "ra"}[spec.get("align", "left")]
    draw.text((x, y), text, font=font, fill=spec.get("color", "#111111"), anchor=anchor)


def render(view, template="daily"):
    """view = collector.build_view() natijasi. PNG baytlarini qaytaradi."""
    tpl = load_template(template)
    fonts = {
        "regular": tpl.get("font_regular") or FALLBACK_FONTS["regular"],
        "bold": tpl.get("font_bold") or FALLBACK_FONTS["bold"],
    }
    for k in fonts:
        if not os.path.isabs(fonts[k]):
            fonts[k] = os.path.join(tpl["_dir"], fonts[k])
        if not os.path.exists(fonts[k]):
            fonts[k] = FALLBACK_FONTS[k]

    bg_path = os.path.join(tpl["_dir"], tpl["background"]) if tpl.get("background") else None
    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).convert("RGB")
    else:
        img = Image.new("RGB", tuple(tpl.get("size", [1080, 1080])), tpl.get("bg_color", "#101820"))
    draw = ImageDraw.Draw(img)

    bb, bs = view.get("best_buy"), view.get("best_sell")
    tokens = {
        "currency": view["currency"],
        "date": datetime.now().strftime("%d.%m.%Y"),
        "official": money(view.get("official")),
        "best_buy_bank": bb["name"] if bb else "—",
        "best_buy": money(bb["buy"]) if bb else "—",
        "best_sell_bank": bs["name"] if bs else "—",
        "best_sell": money(bs["sell"]) if bs else "—",
        "site": config.SITE_NAME,
        "note": config.DISCLAIMER_SHORT,
    }

    for spec in tpl.get("text", []):
        _draw_text(draw, spec["text"], spec, fonts, tokens)

    lst = tpl.get("list")
    if lst:
        rows = [r for r in view["banks"] if r["kind"] == "commercial" and not r["stale"]]
        rows = sorted(rows, key=lambda r: -(r["buy"] or 0))[: lst.get("max_rows", 6)]
        labels = lst.get("labels", {"name": "Bank", "buy": "Oladi", "sell": "Sotadi"})
        y = lst["y"]
        if lst.get("header"):
            for col in ("name", "buy", "sell"):
                spec = dict(lst[col])
                spec.update(x=lst["x"] + spec["dx"], y=y,
                            size=lst.get("header_size", 24),
                            color=lst.get("header_color", "#8a94a6"), font="regular")
                _draw_text(draw, labels[col], spec, fonts, {})
            y += lst.get("header_height", 44)
        for r in rows:
            # faqat aynan eng yaxshi bo'lgan katak ajratiladi, butun qator emas
            hl = {
                "name": r["best_buy"] or r["best_sell"],
                "buy": r["best_buy"],
                "sell": r["best_sell"],
            }
            for col, val in (("name", r["name"]),
                             ("buy", money(r["buy"])),
                             ("sell", money(r["sell"]))):
                spec = dict(lst[col])
                spec.update(x=lst["x"] + spec["dx"], y=y)
                if hl[col]:
                    spec["color"] = lst.get("highlight_color", spec.get("color", "#ffffff"))
                    spec["font"] = "bold"
                _draw_text(draw, str(val), spec, fonts, {})
            y += lst.get("row_height", 70)

    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_cached(view, template="daily"):
    """Bir xil ma'lumot uchun rasm qayta chizilmaydi."""
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    sig = json.dumps(
        [view["currency"], view.get("official"),
         [(b["bank"], b["buy"], b["sell"]) for b in view["banks"]],
         template, datetime.now().strftime("%Y-%m-%d")],
        sort_keys=True, default=str,
    )
    key = hashlib.sha1(sig.encode()).hexdigest()[:16]
    path = os.path.join(config.CACHE_DIR, f"{template}_{view['currency']}_{key}.png")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    data = render(view, template)
    with open(path, "wb") as f:
        f.write(data)
    return data
