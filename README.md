# Valyuta kurslari — banklar bo'yicha solishtirish

O'zbekiston banklaridagi valyuta oldi-sotdi kurslarini yig'adi, solishtiradi,
sayt sifatida ko'rsatadi va API / RSS / CSV / PNG ko'rinishida beradi.

## Nima ishlaydi, nima sozlanadi

| Manba | Holat |
|---|---|
| Markaziy bank (rasmiy kurs) | **Ishlaydi.** Rasmiy hujjatlashtirilgan JSON API |
| 14 ta tijorat banki | **Sozlash kerak.** URL va CSS selektorlar taxminiy |

Tijorat banklarining ochiq API'si yo'q, shuning uchun ularning sahifasi parse
qilinadi. `app/banks/sources.py` dagi selektorlar sinovdan o'tkazilmagan —
serverda bir marta to'g'rilanadi. Bir bank ishlamasa, qolganlari ishlayveradi.

## Ikki xil ishlatish

### 1. GitHub Pages (server kerak emas, bepul)

GitHub Actions soatiga bir marta banklarga kiradi, natijani `docs/` ga
tayyor JSON/PNG/RSS qilib yozadi, Pages shuni tarqatadi. API — statik fayl,
CDN'dan uzatiladi.

1. Reponi yarating va kodni yuklang.
2. **Settings -> Pages -> Source: Deploy from a branch**, branch `main`,
   folder `/docs`.
3. **Settings -> Actions -> General -> Workflow permissions**:
   "Read and write permissions" ni yoqing (bot commit qila olishi uchun).
4. `app/config.py` dagi `SITE_URL` ni o'z manzilingizga o'zgartiring
   (yoki xohlasangiz Settings -> Secrets and variables -> Actions ->
   Variables da `SITE_NAME` / `SITE_URL` qo'shing — ikkalasi ham ishlaydi).
5. Actions bo'limidan workflow'ni bir marta qo'lda ishga tushiring.

Bilib qo'yish kerak bo'lgan cheklovlar:

- Actions cron kafolatlanmagan, **5-20 daqiqa kechikish odatiy hol**.
- Public repo **60 kun tegilmasa scheduled workflow o'chib qoladi** —
  GitHub xat yuboradi, Actions'dan qayta yoqasiz.
- Ba'zi banklar Cloudflare orqasida va GitHub serverlarining IP'sini
  bloklashi mumkin. Bunday bank `status.json` da `error` bo'lib turadi;
  o'z serveringizdan esa o'tishi mumkin.
- Qo'lda kurs kiritish endpointi yo'q — `data/state.json` ni tahrirlab
  commit qilasiz.
- Har yangilanish commit qiladi. Repo tarixi o'sib boradi; xohlasangiz
  vaqti-vaqti bilan `git gc` yoki tarixni siqib tashlaysiz.

Mahalliy sinash:

```bash
pip install -r requirements.txt
python -m app.cli update
python -m app.cli build
cd docs && python -m http.server 8000
```

### 2. O'z serveringizda (to'liq API)

```bash
pip install -r requirements.txt
cp .env.example .env
echo "STORAGE=sqlite" >> .env
python -m app.cli update
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

Bu rejimda qo'shimcha: `?currency=` bilan so'rov, qo'lda kurs kiritish
endpointi, ichki scheduler, SQLite tarixi. Sahifaning o'zi ikkala rejimda
ham bir xil ishlaydi.

## Bankni sozlash

Yangi bank qo'shish yoki sinib qolganini tuzatish uchun uchta buyruq:

```bash
python -m app.cli status              # qaysi manba ishlayapti
python -m app.cli check kapitalbank   # bitta bankni sinash (bazaga yozmaydi)
python -m app.cli probe https://bank.uz/exchange   # sahifadagi jadvallarni ko'rish
```

`probe` sahifadagi har bir `<table>` ni raqamlab, birinchi qatorlarini
ko'rsatadi va tayyor selektor taklif qiladi. Shundan keyin `sources.py` da
o'sha bankning `row_selector` va `idx` qiymatlarini to'g'rilaysiz:

```python
class Kapitalbank(HtmlTableAdapter):
    row_selector = "table:nth-of-type(2) tbody tr"
    idx = {"currency": 0, "buy": 2, "sell": 3}   # katak tartib raqamlari
```

Agar `probe` "sahifada `<table>` yo'q" desa — kurslar JavaScript bilan
chizilgan. Brauzerning Network bo'limidan JSON so'rovni topib, `JsonAdapter`
ishlating:

```python
class Kapitalbank(JsonAdapter):
    url = "https://kapitalbank.uz/api/rates"
    rows_path = "data.rates"
    field_map = {"currency": "code", "buy": "buy", "sell": "sell"}
```

Bu eng barqaror variant — sayt dizayni o'zgarsa ham ishlayveradi.

## API

Barchasi CORS ochiq, kalit talab qilinmaydi.

Statik manzillar ikkala rejimda ham ishlaydi:

| Manzil | Nima qaytaradi |
|---|---|
| `api/rates/USD.json` | Barcha banklar + eng yaxshi kurslar |
| `api/best/USD.json` | Faqat eng yaxshi olish/sotish |
| `api/banks.json` | Kuzatilayotgan manbalar ro'yxati |
| `api/history/USD.json` | 90 kunlik tarix, banklar bo'yicha |
| `api/status.json` | Qaysi manba ishlayapti, qaysi biri sinigan |
| `api/rates/USD.csv` | Excel uchun |
| `feed.xml` | RSS |
| `img/USD.png` | Tayyor rasm |

Faqat server rejimida qo'shimcha: `GET /api/rates?currency=USD`,
`GET /api/image?currency=USD&template=daily`, `POST /api/admin/rate`.

Javob namunasi:

```json
{
  "currency": "USD",
  "official": 12312.5,
  "best_buy":  { "bank": "kapitalbank", "name": "Kapitalbank", "buy": 12480 },
  "best_sell": { "bank": "anorbank",    "name": "Anorbank",    "sell": 12495 },
  "banks": [ { "bank": "nbu", "buy": 12400, "sell": 12520, "spread": 120,
               "stale": false, "fetched_at": "..." } ],
  "disclaimer": "..."
}
```

`buy` — bank **sizdan** shu narxga oladi. `sell` — bank **sizga** shu narxga
sotadi. Ya'ni valyuta sotmoqchi bo'lsangiz eng katta `buy`, olmoqchi
bo'lsangiz eng kichik `sell` foydali.

`stale: true` — ma'lumot `STALE_HOURS` dan eski. Bunday kurs saytda
ko'rsatiladi, lekin eng yaxshi kurs hisobiga kirmaydi.

## Rasm shabloni

`assets/templates/daily.json` — koordinatalar va ranglar shu yerda.
`daily_bg.png` — fon rasmi, dizayner bergan PNG bilan almashtiriladi.
Koddan hech narsa o'zgartirilmaydi.

Matn ichida ishlatiladigan o'rin egallovchilar:
`{currency}` `{date}` `{official}` `{best_buy}` `{best_buy_bank}`
`{best_sell}` `{best_sell_bank}` `{site}` `{note}`

Sinab ko'rish:

```bash
python -m app.cli image USD /tmp/kurs.png
```

Shrift: `assets/templates/` ichiga `.ttf` tashlab, JSON da nomini yozasiz.
Topilmasa DejaVu ishlatiladi. O'zbek lotin, kirill va rus harflarini
qamraydigan shrift tanlang.

## Yangilash

Pages rejimida — `.github/workflows/update.yml`. Server rejimida ichki
scheduler (`UPDATE_INTERVAL_MINUTES=60`) yoki cron:

```
0 * * * * cd /srv/kurs && /srv/kurs/venv/bin/python -m app.cli update >> /var/log/kurs.log 2>&1
```

Cron ishlatsangiz `.env` da `UPDATE_INTERVAL_MINUTES=0` qo'ying.

## Telegram kanalga post qilish

```bash
curl -s "http://localhost:8000/api/image?currency=USD" -o /tmp/kurs.png
curl -F chat_id=@kanal -F photo=@/tmp/kurs.png \
     -F caption="$(curl -s localhost:8000/api/best?currency=USD | jq -r .disclaimer)" \
     "https://api.telegram.org/bot$TOKEN/sendPhoto"
```

## Manba sinib qolsa

Server rejimida kurs qo'lda kiritiladi (`.env` da `ADMIN_TOKEN` bo'lishi kerak):

```bash
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" \
  "http://localhost:8000/api/admin/rate?bank=nbu&currency=USD&buy=12400&sell=12520"
```

Pages rejimida `data/state.json` dagi tegishli yozuvni tahrirlab,
`origin` ni `manual` qilib commit qilasiz.

Bunday yozuv saytda "qoʻlda" belgisi bilan ko'rinadi.

## Huquqiy tomoni

Sayt banklarning ochiq sahifalaridan ma'lumot oladi. Har bir sahifada va
rasmda ma'lumot tanishtiruv uchun ekani va aniq kursni bankdan tasdiqlash
kerakligi yozilgan. So'rovlar soatiga bir marta yuboriladi va `User-Agent`
da xizmat nomi ko'rsatiladi. Bank e'tiroz bildirsa, o'sha adapterni
`enabled = False` qilib o'chirasiz.
