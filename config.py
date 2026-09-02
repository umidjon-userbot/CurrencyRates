"""Loyiha sozlamalari. Hammasi .env orqali o'zgartiriladi."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Saqlash rejimi: json (GitHub Pages/Actions) yoki sqlite (o'z serveringiz)
STORAGE = os.getenv("STORAGE", "json")
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "kurs.db"))
STATE_PATH = os.getenv("STATE_PATH", str(BASE_DIR / "data" / "state.json"))
# Statik sayt shu papkaga yig'iladi (GitHub Pages "docs/" ni tarqata oladi)
BUILD_DIR = os.getenv("BUILD_DIR", str(BASE_DIR / "docs"))
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
CACHE_DIR = BASE_DIR / "data" / "cache"

SITE_NAME = os.getenv("SITE_NAME", "Kurs.uz")
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# Saytda ko'rsatiladigan valyutalar (tartib ham shu)
CURRENCIES = os.getenv("CURRENCIES", "USD,EUR,RUB").split(",")

# Nechchi soatdan keyin ma'lumot "eskirgan" deb hisoblanadi.
# Eskirgan kurs saytda ko'rsatiladi, lekin "eskirgan" belgisi bilan va
# eng yaxshi kurs hisobida qatnashmaydi.
STALE_HOURS = int(os.getenv("STALE_HOURS", "12"))

# Har bir manbaga so'rov yuborishda kutish vaqti (soniya)
FETCH_TIMEOUT = int(os.getenv("FETCH_TIMEOUT", "20"))

# Bir vaqtda nechta bankka so'rov yuborilsin
FETCH_CONCURRENCY = int(os.getenv("FETCH_CONCURRENCY", "5"))

# Avtomatik yangilash oralig'i (daqiqa). 0 bo'lsa ichki scheduler o'chadi
# va faqat cron orqali `python -m app.cli update` ishlatiladi.
UPDATE_INTERVAL_MINUTES = int(os.getenv("UPDATE_INTERVAL_MINUTES", "60"))

# Admin panel uchun token (qo'lda kurs kiritish va manbani o'chirish uchun)
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

USER_AGENT = os.getenv(
    "USER_AGENT",
    "KursBot/1.0 (+{}; kurs solishtirish xizmati)".format(SITE_URL),
)

DISCLAIMER = (
    "Ma'lumotlar banklarning ochiq manbalaridan avtomatik olinadi va faqat "
    "tanishtiruv uchun. Aniq kursni bankning o'zidan tasdiqlang."
)
DISCLAIMER_SHORT = "Kurs o'zgarishi mumkin — bankdan aniqlang."
