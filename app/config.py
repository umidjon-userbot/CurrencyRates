"""Loyiha sozlamalari.

Hamma qiymat muhit o'zgaruvchisi (.env yoki GitHub Actions variables) orqali
almashtirilishi mumkin. Sozlanmagan bo'lsa — shu fayldagi standart qiymat.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key: str, default):
    """Muhit o'zgaruvchisi. Bo'sh yoki faqat probel bo'lsa — standart qiymat.

    Bu muhim: GitHub Actions sozlanmagan `vars.SITE_URL` ni bo'sh satr qilib
    yuboradi, oddiy os.getenv esa uni haqiqiy qiymat deb qabul qilib,
    standartni bekor qilib yuboradi.
    """
    v = os.getenv(key)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


# --- sayt ------------------------------------------------------------------
SITE_NAME = env("SITE_NAME", "Valyuta kurslari")
SITE_URL = env("SITE_URL", "https://umidjon-userbot.github.io/CurrencyRates")

# --- saqlash ---------------------------------------------------------------
# json   -> data/state.json  (GitHub Pages / Actions uchun, standart)
# sqlite -> data/kurs.db     (o'z serveringizda ishlatsangiz)
STORAGE = env("STORAGE", "json")
DB_PATH = env("DB_PATH", str(BASE_DIR / "data" / "kurs.db"))
STATE_PATH = env("STATE_PATH", str(BASE_DIR / "data" / "state.json"))

# Statik sayt shu papkaga yig'iladi (GitHub Pages "docs/" ni tarqata oladi)
BUILD_DIR = env("BUILD_DIR", str(BASE_DIR / "docs"))

WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
CACHE_DIR = BASE_DIR / "data" / "cache"

# --- ma'lumot --------------------------------------------------------------
# Saytda ko'rsatiladigan valyutalar (tartib ham shu)
CURRENCIES = [c.strip().upper() for c in env("CURRENCIES", "USD,EUR,RUB").split(",") if c.strip()]

# Nechchi soatdan keyin ma'lumot "eskirgan" deb hisoblanadi.
# Eskirgan kurs saytda ko'rsatiladi, lekin "eskirgan" belgisi bilan va
# eng yaxshi kurs hisobida qatnashmaydi.
STALE_HOURS = int(env("STALE_HOURS", 12))

# --- yig'ish ---------------------------------------------------------------
# Har bir manbaga so'rov yuborishda kutish vaqti (soniya)
FETCH_TIMEOUT = int(env("FETCH_TIMEOUT", 20))

# Bir vaqtda nechta bankka so'rov yuborilsin
FETCH_CONCURRENCY = int(env("FETCH_CONCURRENCY", 5))

# Server rejimidagi avtomatik yangilash oralig'i (daqiqa).
# 0 bo'lsa ichki scheduler o'chadi va faqat cron / GitHub Actions ishlatiladi.
UPDATE_INTERVAL_MINUTES = int(env("UPDATE_INTERVAL_MINUTES", 60))

USER_AGENT = env(
    "USER_AGENT",
    f"KursBot/1.0 (+{SITE_URL}; valyuta kurslarini solishtirish xizmati)",
)

# --- admin (faqat server rejimida) -----------------------------------------
# Qo'lda kurs kiritish uchun. Bo'sh bo'lsa endpoint yopiq turadi.
ADMIN_TOKEN = env("ADMIN_TOKEN", "")

# --- izohlar ---------------------------------------------------------------
DISCLAIMER = (
    "Ma'lumotlar banklarning ochiq manbalaridan avtomatik olinadi va faqat "
    "tanishtiruv uchun. Aniq kursni bankning o'zidan tasdiqlang."
)
DISCLAIMER_SHORT = "Kurs o'zgarishi mumkin — bankdan aniqlang."
