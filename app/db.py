"""SQLite qatlami. Tashqi ORM ishlatilmagan — sxema kichik va tushunarli."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS rates (
    bank        TEXT NOT NULL,
    currency    TEXT NOT NULL,
    buy         REAL,
    sell        REAL,
    fetched_at  TEXT NOT NULL,
    source_url  TEXT,
    origin      TEXT NOT NULL DEFAULT 'auto',  -- auto | manual
    PRIMARY KEY (bank, currency)
);

CREATE TABLE IF NOT EXISTS rate_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bank        TEXT NOT NULL,
    currency    TEXT NOT NULL,
    buy         REAL,
    sell        REAL,
    seen_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_history ON rate_history (bank, currency, seen_at);

CREATE TABLE IF NOT EXISTS fetch_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bank        TEXT NOT NULL,
    status      TEXT NOT NULL,          -- ok | error
    message     TEXT,
    rows        INTEGER DEFAULT 0,
    took_ms     INTEGER,
    at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fetchlog ON fetch_log (bank, at);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def cursor():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with cursor() as conn:
        conn.executescript(SCHEMA)


def save_rates(bank: str, rows, origin: str = "auto"):
    """rows: Rate obyektlari ro'yxati. Qiymat o'zgargan bo'lsagina tarixga yoziladi."""
    now = utcnow()
    with cursor() as conn:
        for r in rows:
            prev = conn.execute(
                "SELECT buy, sell FROM rates WHERE bank=? AND currency=?",
                (bank, r.currency),
            ).fetchone()
            changed = prev is None or prev["buy"] != r.buy or prev["sell"] != r.sell
            conn.execute(
                """INSERT INTO rates (bank, currency, buy, sell, fetched_at, source_url, origin)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(bank, currency) DO UPDATE SET
                     buy=excluded.buy, sell=excluded.sell,
                     fetched_at=excluded.fetched_at,
                     source_url=excluded.source_url,
                     origin=excluded.origin""",
                (bank, r.currency, r.buy, r.sell, now, r.source_url, origin),
            )
            if changed:
                conn.execute(
                    "INSERT INTO rate_history (bank, currency, buy, sell, seen_at) VALUES (?,?,?,?,?)",
                    (bank, r.currency, r.buy, r.sell, now),
                )


def log_fetch(bank: str, status: str, message: str = "", rows: int = 0, took_ms: int = 0):
    with cursor() as conn:
        conn.execute(
            "INSERT INTO fetch_log (bank, status, message, rows, took_ms, at) VALUES (?,?,?,?,?,?)",
            (bank, status, message[:500], rows, took_ms, utcnow()),
        )


def get_rates(currency: str = None):
    q = "SELECT * FROM rates"
    args = []
    if currency:
        q += " WHERE currency=?"
        args.append(currency.upper())
    with cursor() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


def get_history(bank: str, currency: str, days: int = 30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with cursor() as conn:
        rows = conn.execute(
            """SELECT buy, sell, seen_at FROM rate_history
               WHERE bank=? AND currency=? AND seen_at >= ?
               ORDER BY seen_at""",
            (bank, currency.upper(), since),
        ).fetchall()
    return [dict(r) for r in rows]


def last_fetch_status():
    """Har bir bank uchun oxirgi urinish natijasi."""
    with cursor() as conn:
        rows = conn.execute(
            """SELECT f.* FROM fetch_log f
               JOIN (SELECT bank, MAX(at) AS mx FROM fetch_log GROUP BY bank) m
                 ON f.bank = m.bank AND f.at = m.mx"""
        ).fetchall()
    return {r["bank"]: dict(r) for r in rows}


def is_stale(fetched_at: str) -> bool:
    try:
        ts = datetime.fromisoformat(fetched_at)
    except ValueError:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts > timedelta(hours=config.STALE_HOURS)
