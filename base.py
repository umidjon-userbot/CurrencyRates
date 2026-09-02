"""Bank adapterlari uchun asos.

Har bir bank uchun alohida sinf yozish shart emas — ko'p holatda
`sources.py` dagi deklarativ config yetadi. Sayt tuzilishi o'zgarsa,
faqat o'sha configdagi selektorni tuzatasiz.
"""
import re
from dataclasses import dataclass
from typing import Optional

from selectolax.parser import HTMLParser


@dataclass
class Rate:
    currency: str
    buy: Optional[float] = None      # bank sizdan shu narxga OLADI
    sell: Optional[float] = None     # bank sizga shu narxga SOTADI
    source_url: Optional[str] = None


class FetchError(Exception):
    pass


# --- raqamni tozalash -------------------------------------------------------
# Banklar turli formatda yozadi: "12 350,00" / "12,350.00" / "12350.5" / "12 350"
_NUM_RE = re.compile(r"-?\d[\d\s\u00a0.,]*")


def parse_number(text) -> Optional[float]:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text) or None
    m = _NUM_RE.search(str(text))
    if not m:
        return None
    s = m.group(0)
    s = s.replace("\u00a0", "").replace(" ", "")
    if "," in s and "." in s:
        # oxirgi belgisi kasr ajratuvchi deb olinadi
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        # "12,5" -> kasr,  "12,350" -> mingliklar
        tail = s.split(",")[-1]
        s = s.replace(",", "." if len(tail) <= 2 else "")
    else:
        # "12.350" ko'rinishi ham mingliklar bo'lishi mumkin
        tail = s.split(".")[-1] if "." in s else ""
        if len(tail) == 3 and s.count(".") == 1 and len(s.replace(".", "")) > 4:
            s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def dig(obj, path: str):
    """'data.rates.0.buy' ko'rinishidagi yo'l bo'yicha JSON ichidan qiymat olish."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if part.isdigit() and isinstance(cur, list):
            idx = int(part)
            cur = cur[idx] if idx < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


# --- adapterlar -------------------------------------------------------------
class BaseAdapter:
    code: str = ""
    name: str = ""
    site: str = ""
    url: str = ""
    enabled: bool = True

    async def fetch(self, client) -> list:
        raise NotImplementedError

    async def _get(self, client, url=None, **kw):
        r = await client.get(url or self.url, **kw)
        if r.status_code != 200:
            raise FetchError(f"HTTP {r.status_code}")
        return r


class JsonAdapter(BaseAdapter):
    """Sayt ichidagi JSON endpointdan o'qiydi — eng barqaror variant.

    rows_path : JSON ichida ro'yxat qayerdaligi ('' = ildizning o'zi)
    field_map : {'currency': 'Ccy', 'buy': 'buy', 'sell': 'sell'}
    """
    rows_path: str = ""
    field_map: dict = {}
    currency_alias: dict = {}

    async def fetch(self, client):
        data = (await self._get(client)).json()
        rows = dig(data, self.rows_path) if self.rows_path else data
        if not isinstance(rows, list):
            raise FetchError("kutilgan ro'yxat topilmadi: " + self.rows_path)
        out = []
        for row in rows:
            code = str(dig(row, self.field_map["currency"]) or "").strip().upper()
            code = self.currency_alias.get(code, code)
            if not code:
                continue
            buy = parse_number(dig(row, self.field_map.get("buy", "")))
            sell = parse_number(dig(row, self.field_map.get("sell", "")))
            if buy or sell:
                out.append(Rate(code, buy, sell, self.site or self.url))
        return out


class HtmlTableAdapter(BaseAdapter):
    """HTML jadvaldan o'qiydi.

    row_selector  : har bir valyuta qatorini tanlaydigan CSS selektor
    cell_selector : qator ichidagi kataklar
    idx           : {'currency': 0, 'buy': 1, 'sell': 2} — katak tartib raqamlari
    """
    row_selector: str = "table tbody tr"
    cell_selector: str = "td, th"
    idx: dict = {"currency": 0, "buy": 1, "sell": 2}
    currency_alias: dict = {}
    wanted = ("USD", "EUR", "RUB", "GBP", "KZT", "JPY", "CHF", "CNY", "TRY")

    def normalize_currency(self, text: str):
        t = (text or "").strip().upper()
        if t in self.currency_alias:
            return self.currency_alias[t]
        for code in self.wanted:
            if re.search(rf"\b{code}\b", t):
                return code
        # "Доллар США", "AQSH dollari" kabi nomlar
        for needle, code in (
            ("ДОЛЛАР", "USD"), ("DOLLAR", "USD"),
            ("ЕВРО", "EUR"), ("YEVRO", "EUR"), ("EURO", "EUR"),
            ("РУБЛ", "RUB"), ("RUBL", "RUB"),
            ("ФУНТ", "GBP"), ("FUNT", "GBP"),
            ("ТЕНГЕ", "KZT"), ("TENGE", "KZT"),
        ):
            if needle in t:
                return code
        return None

    async def fetch(self, client):
        html = (await self._get(client)).text
        tree = HTMLParser(html)
        rows = tree.css(self.row_selector)
        if not rows:
            raise FetchError(f"selektor bo'sh natija berdi: {self.row_selector}")
        out, seen = [], set()
        for row in rows:
            cells = [c.text(strip=True) for c in row.css(self.cell_selector)]
            if len(cells) <= max(self.idx.values()):
                continue
            code = self.normalize_currency(cells[self.idx["currency"]])
            if not code or code in seen:
                continue
            buy = parse_number(cells[self.idx["buy"]]) if "buy" in self.idx else None
            sell = parse_number(cells[self.idx["sell"]]) if "sell" in self.idx else None
            if buy or sell:
                seen.add(code)
                out.append(Rate(code, buy, sell, self.site or self.url))
        if not out:
            raise FetchError("jadval topildi, lekin valyuta o'qilmadi")
        return out
