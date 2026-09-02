"""Bank manbalari.

MUHIM: quyidagi tijorat banklari uchun URL va CSS selektorlar TEKSHIRILMAGAN.
Ular ishlab chiqarish serverida bir marta sozlanishi kerak:

    python -m app.cli probe https://bank-sayti.uz/exchange   # jadvallarni ko'rish
    python -m app.cli check kapitalbank                      # bitta bankni sinash

Selektor noto'g'ri bo'lsa — sayt yiqilmaydi, o'sha bank "ma'lumot yo'q"
holatida qoladi va /api/status da xato ko'rinadi.

Yangi bank qo'shish = shu faylga bitta sinf qo'shish.
"""
from .base import HtmlTableAdapter, JsonAdapter, Rate, parse_number


# --- Markaziy bank: rasmiy, hujjatlashtirilgan API -------------------------
class CBU(JsonAdapter):
    """https://cbu.uz/en/arkhiv-kursov-valyut/veb-masteram/ da rasmiy hujjati bor."""
    code = "cbu"
    name = "Markaziy bank"
    kind = "official"          # oldi-sotdi emas, rasmiy (indikativ) kurs
    site = "https://cbu.uz/uz/arkhiv-kursov-valyut/"
    url = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    verified = True

    async def fetch(self, client):
        data = (await self._get(client)).json()
        out = []
        for row in data:
            code = str(row.get("Ccy", "")).strip().upper()
            rate = parse_number(row.get("Rate"))
            nominal = parse_number(row.get("Nominal")) or 1
            if code and rate:
                v = round(rate / nominal, 2)
                # rasmiy kursda oldi-sotdi farqi yo'q — ikkala ustunga ham yoziladi,
                # lekin API bu bankni "official" deb belgilaydi va reytingga qo'shmaydi
                out.append(Rate(code, v, v, self.site))
        return out


# --- Tijorat banklari ------------------------------------------------------
class NBU(HtmlTableAdapter):
    code = "nbu"
    name = "Milliy bank (NBU)"
    kind = "commercial"
    site = "https://nbu.uz/uz/exchange-rates/"
    url = "https://nbu.uz/uz/exchange-rates/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Kapitalbank(HtmlTableAdapter):
    code = "kapitalbank"
    name = "Kapitalbank"
    kind = "commercial"
    site = "https://kapitalbank.uz/uz/services/exchange-rates/"
    url = "https://kapitalbank.uz/uz/services/exchange-rates/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class IpotekaBank(HtmlTableAdapter):
    code = "ipoteka"
    name = "Ipoteka Bank"
    kind = "commercial"
    site = "https://www.ipotekabank.uz/uz/private/exchange-rates/"
    url = "https://www.ipotekabank.uz/uz/private/exchange-rates/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Anorbank(HtmlTableAdapter):
    code = "anorbank"
    name = "Anorbank"
    kind = "commercial"
    site = "https://anorbank.uz/uz/about/exchange-rates/"
    url = "https://anorbank.uz/uz/about/exchange-rates/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class AsakaBank(HtmlTableAdapter):
    code = "asaka"
    name = "Asaka Bank"
    kind = "commercial"
    site = "https://asakabank.uz/uz/exchange/"
    url = "https://asakabank.uz/uz/exchange/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Hamkorbank(HtmlTableAdapter):
    code = "hamkorbank"
    name = "Hamkorbank"
    kind = "commercial"
    site = "https://hamkorbank.uz/uz/exchange/"
    url = "https://hamkorbank.uz/uz/exchange/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class TBCBank(HtmlTableAdapter):
    code = "tbc"
    name = "TBC Bank"
    kind = "commercial"
    site = "https://tbcbank.uz/uz/exchange-rates"
    url = "https://tbcbank.uz/uz/exchange-rates"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Agrobank(HtmlTableAdapter):
    code = "agrobank"
    name = "Agrobank"
    kind = "commercial"
    site = "https://agrobank.uz/uz/exchange-rates"
    url = "https://agrobank.uz/uz/exchange-rates"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Aloqabank(HtmlTableAdapter):
    code = "aloqabank"
    name = "Aloqabank"
    kind = "commercial"
    site = "https://aloqabank.uz/uz/exchange/"
    url = "https://aloqabank.uz/uz/exchange/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class XalqBanki(HtmlTableAdapter):
    code = "xalqbanki"
    name = "Xalq banki"
    kind = "commercial"
    site = "https://xb.uz/uz/exchange-rates"
    url = "https://xb.uz/uz/exchange-rates"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class InFinBank(HtmlTableAdapter):
    code = "infinbank"
    name = "InFinBank"
    kind = "commercial"
    site = "https://infinbank.com/uz/private/exchange-rates/"
    url = "https://infinbank.com/uz/private/exchange-rates/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Trastbank(HtmlTableAdapter):
    code = "trastbank"
    name = "Trastbank"
    kind = "commercial"
    site = "https://trustbank.uz/uz/exchange/"
    url = "https://trustbank.uz/uz/exchange/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class DavrBank(HtmlTableAdapter):
    code = "davrbank"
    name = "Davr Bank"
    kind = "commercial"
    site = "https://davrbank.uz/uz/exchange"
    url = "https://davrbank.uz/uz/exchange"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


class Turonbank(HtmlTableAdapter):
    code = "turonbank"
    name = "Turonbank"
    kind = "commercial"
    site = "https://turonbank.uz/uz/exchange/"
    url = "https://turonbank.uz/uz/exchange/"
    row_selector = "table tr"
    idx = {"currency": 0, "buy": 1, "sell": 2}
    verified = False


ADAPTERS = [
    CBU(), NBU(), Kapitalbank(), IpotekaBank(), Anorbank(), AsakaBank(),
    Hamkorbank(), TBCBank(), Agrobank(), Aloqabank(), XalqBanki(),
    InFinBank(), Trastbank(), DavrBank(), Turonbank(),
]

BY_CODE = {a.code: a for a in ADAPTERS}
