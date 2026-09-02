"""Saqlash rejimini tanlaydi.

STORAGE=json   -> data/state.json   (GitHub Pages / Actions uchun, standart)
STORAGE=sqlite -> data/kurs.db      (o'z serveringizda ishlatsangiz)

Ikkalasining interfeysi bir xil, collector farqni sezmaydi.
"""
from . import config

if config.STORAGE == "sqlite":
    from .db import (init, save_rates, log_fetch, get_rates, get_history,
                     last_fetch_status, is_stale, utcnow)
else:
    from .jsonstore import (init, save_rates, log_fetch, get_rates, get_history,
                            last_fetch_status, is_stale, utcnow)

__all__ = ["init", "save_rates", "log_fetch", "get_rates", "get_history",
           "last_fetch_status", "is_stale", "utcnow"]
