import json
import logging
import asyncio
import os
import re
import time
import html
import difflib
from datetime import datetime, timedelta
from io import BytesIO
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    BotCommand,
    FSInputFile,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# GOOGLE GENAI SDK ENTEGRASYONU
try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
GEMINI_API_KEY = "AIzaSyAuUg0a1ew5V4aF1E-FTsdVinsMpXckOgQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Gemini Client Başlatma
ai_client = None
if HAS_GENAI and GEMINI_API_KEY:
    try:
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        logging.info("✅ Google GenAI (Gemini) istemcisi başarıyla bağlandı.")
    except Exception as e:
        logging.warning(f"⚠️ Gemini bağlantı uyarısı: {e}")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            u_name = event.from_user.first_name if event.from_user else "Bilinmeyen"
            logging.info(f"--- MESAJ: {u_name} (ID: {event.chat.id}) | {event.text or event.document.file_name if event.document else ''}")
        return await handler(event, data)

dp.message.outer_middleware(LoggingMiddleware())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"
QUOTES_FILE = "submitted_quotes.json"
PDF_STORAGE_DIR = "stored_quotes_pdf"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# ----------------- KATALOG KOORDİNAT HARİTASI (RD96) -----------------
# Format: "Kod": (Sayfa No, Kutu No [1: Sol Üst, 2: Sağ Üst, 3: Sol Orta, 4: Sağ Orta, 5: Sol Alt, 6: Sağ Alt])
CATALOG_GRID_MAP = {
    "91661": (2, 1), "40642": (2, 2), "40645": (2, 3), "40643": (2, 4), "40644": (2, 5), "90802": (2, 6),
    "41370": (3, 3), "41381": (3, 5), "91514": (3, 6),
    "91410": (4, 1), "91411": (4, 2), "41436": (4, 3), "41435": (4, 4), "96469": (4, 5), "60002": (4, 6),
    "90338": (5, 1), "91128": (5, 2), "91516": (5, 4), "41538": (5, 5), "41407": (5, 6),
    "41420": (6, 1), "93041": (6, 2), "93035": (6, 3), "60020": (6, 4),
    "91517": (7, 1), "41430": (7, 2), "41408": (7, 3), "41415": (7, 4), "41419": (7, 5), "41414": (7, 6),
    "41425": (8, 1), "41427": (8, 2), "41426": (8, 3), "93039": (8, 4), "93040": (8, 5),
    "41413": (9, 2), "41418": (9, 3), "41411": (9, 4), "41428": (9, 5), "41429": (9, 6),
    "93043": (10, 1), "93042": (10, 2), "93037": (10, 3), "93036": (10, 4),
    "60044": (11, 1), "41434": (11, 2), "90946": (11, 3), "41432": (11, 4), "41409": (11, 5), "41424": (11, 6),
    "41433": (12, 1), "41416": (12, 2), "41417": (12, 3), "41533": (12, 4), "96541": (12, 5),
    "90951": (13, 2), "41384": (13, 5), "41383": (13, 6),
    "90310": (14, 1), "90952": (14, 2), "90332": (14, 3), "90328": (14, 4),
    "90949": (15, 1), "90947": (15, 2), "90321": (15, 3), "16073": (15, 4), "90490": (15, 5), "91238": (15, 6),
    "90333": (16, 1), "90948": (16, 2), "91407": (16, 3), "93008": (16, 4), "90345": (16, 5), "90325": (16, 6),
    "90320": (17, 1), "90950": (17, 2), "60003": (17, 3), "96112": (17, 4), "90827": (17, 5), "50155": (17, 6),
    "96467": (18, 1), "91603": (18, 2), "91035": (18, 3), "90547": (18, 4), "20031": (18, 5), "90475": (18, 6),
    "50160": (19, 1), "91285": (19, 2), "50606": (19, 3), "91472": (19, 4),
    "50247": (20, 1), "50249": (20, 2), "15401": (20, 3), "41439": (20, 4), "91633": (20, 5), "91448": (20, 6),
    "42595": (21, 1), "90861": (21, 3), "90817": (21, 6),
    "96683": (22, 1), "96097": (22, 2), "91598": (22, 4), "91037": (22, 5), "40082": (22, 6),
    "91386": (23, 1), "91488": (23, 2), "90567": (23, 3), "90965": (23, 4),
    "40647": (24, 1), "90715": (24, 2), "90828": (24, 5), "90834": (24, 6),
    "96468": (25, 1), "91463": (25, 3), "91604": (25, 4), "90548": (25, 5), "91036": (25, 6),
    "90832": (26, 4), "40634": (26, 6),
    "96412": (27, 1), "90878": (27, 2), "90881": (27, 3), "90880": (27, 4),
    "90879": (28, 1), "91284": (28, 3), "14574": (28, 4), "14541": (28, 6),
    "91332": (29, 1), "50219": (29, 2), "54626": (29, 3), "41441": (29, 5), "91447": (29, 6),
    "50057": (30, 1), "54612": (30, 2), "50098": (30, 3), "50018": (30, 4), "91594": (30, 5),
    "91590": (31, 3), "15005": (31, 4), "50549": (31, 5), "40085": (31, 6),
    "91451": (32, 1), "50023": (32, 2), "50273": (32, 3), "50021": (32, 4),
    "41442": (33, 1), "41404": (33, 2), "96517": (33, 3), "50257": (33, 4), "96501": (33, 5), "90766": (33, 6),
    "16016": (34, 1), "16039": (34, 2), "16034": (34, 3), "41403": (34, 4), "90767": (34, 5), "91071": (34, 6),
    "90762": (35, 1), "90840": (35, 2), "41400": (35, 3), "41401": (35, 4), "41300": (35, 5), "41402": (35, 6),
    "91277": (36, 1), "54516": (36, 2), "90768": (36, 3), "90769": (36, 4),
    "90782": (37, 1), "16032": (37, 2), "16041": (37, 3), "16035": (37, 4), "50260": (37, 5), "90759": (37, 6),
    "50138": (38, 2), "91086": (38, 3), "91045": (38, 4), "90770": (38, 5), "16043": (38, 6),
    "16030": (39, 1), "90765": (39, 4), "11906": (39, 6),
    "12302": (40, 1), "41444": (40, 2), "91303": (40, 3), "50263": (40, 4),
    "91044": (41, 1), "54510": (41, 3), "90761": (41, 4), "50262": (41, 6),
    "41399": (42, 5), "50259": (42, 6), "50258": (43, 6), "50261": (44, 6),
    "91269": (46, 2), "91270": (46, 3), "50278": (46, 4), "50293": (46, 5), "90725": (46, 6),
    "50040": (47, 2), "41396": (47, 3), "41398": (47, 5), "54630": (47, 6),
    "50270": (48, 1), "50287": (48, 2), "91066": (48, 3), "91064": (48, 4), "41457": (48, 5), "50238": (48, 6),
    "50156": (49, 1), "91043": (49, 2), "50269": (49, 3),
    "50289": (50, 6), "50291": (52, 1), "90781": (52, 5),
    "96404": (53, 2), "41406": (53, 3), "41405": (53, 4),
    "90484": (54, 1), "91490": (54, 2), "91489": (54, 3), "90930": (54, 5), "91495": (54, 6),
    "54661": (55, 3), "54662": (55, 4), "41437": (55, 5), "90568": (55, 6),
    "50014": (56, 1), "91782": (56, 2), "91271": (56, 3), "91268": (56, 4), "90793": (56, 5), "90324": (56, 6),
    "16044": (57, 1), "14847": (57, 2), "41290": (57, 3), "41287": (57, 4), "41288": (57, 5), "41289": (57, 6),
    "54629": (58, 1), "54628": (58, 2),
    "50024": (59, 1), "50025": (59, 2), "91586": (59, 3), "50027": (59, 4), "92038": (59, 5), "54620": (59, 6),
    "14577": (60, 1), "14317": (60, 2), "96449": (60, 3), "91950": (60, 4), "96219": (60, 6),
    "91453": (61, 1), "50008": (61, 2), "50010": (61, 3), "50046": (61, 4),
    "50054": (62, 3), "15005": (63, 3)
}

REAL_WAREHOUSE_STOCKS = [
    {"code": "91661", "name": "Sürücü VZAB2P2BAA V1000 3/2,2 kW", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "40642", "name": "PLC CPU: CJ1M-CPU21", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "Pd320", "name": "Pd320 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "PD330", "name": "PD330 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Aim8-A", "name": "Aim8-A Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "Aim8-B", "name": "Aim8-B Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "Dim32", "name": "Dim32 Dijital Giriş Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Dom16-PLC", "name": "Dom16-PLC Dijital Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 6, "loc": "ELIPS-DEPO"},
    {"code": "P44", "name": "P44 Panel Kartı", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "Pd300", "name": "Pd300 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "Pd340", "name": "Pd340 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "Pd350", "name": "Pd350 Kontrol Cihazı", "cat": "KONTROL", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "S400", "name": "S400 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "S42", "name": "S42 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "1013", "name": "Vana TORK 3/4\" 3 yollu + aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "5022", "name": "Salmastra", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "30010", "name": "EBARA 15MM SIL/SIL/VITON SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "40597", "name": "BES005M BALLUFF Sensör", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "40647", "name": "Smc CJPB15-10H6 Tek Etkili Silindir", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "41300", "name": "RD96 - MU CAMBAZ PISTONU POLIETILEN TAKOZ", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "42184", "name": "PIPETLEME SIRINGA UCU", "cat": "MEKATRONIK", "qty": 200, "loc": "ELIPS-DEPO"},
    {"code": "50014", "name": "SUSTURUCU: AN15-02: 1/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "50018", "name": "VALF: SY5140-5YO-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50138", "name": "PNOMATIK RAKOR: KQ2L04-M5A", "cat": "MEKATRONIK", "qty": 11, "loc": "ELIPS-DEPO"},
    {"code": "50257", "name": "TEK ETLKILI PNOMATIK SILINDIR CD75E32", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50258", "name": "SILINDIR CD85N16-100-B (SMC)", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50260", "name": "PISTON CD85N16-50-B", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50289", "name": "VALF: SY3220-5LOU-M5-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50291", "name": "VALF: SYJ3143-5LOU-Q", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "90416", "name": "SOLENOID VALF: 00125317 24VDC", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "cat": "MEKATRONIK", "qty": 9, "loc": "ELIPS-DEPO"},
    {"code": "90715", "name": "REGULATOR: AR10-M5H: 0-8 BAR", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90840", "name": "PISTON SENSORU: DC73L", "cat": "ELEKTRONIK", "qty": 6, "loc": "ELIPS-DEPO"},
    {"code": "90880", "name": "DST Çekvalf Teflonu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90881", "name": "DST CEKVALF YAYI", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90946", "name": "SLR1-40 FILTRE", "cat": "MEKATRONIK", "qty": 12, "loc": "ELIPS-DEPO"},
    {"code": "91035", "name": "OMAL TAMIR TAKIMI 3/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR KQ2L04", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91603", "name": "Omal Vana V451H405 3 Yollu L Port", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96412", "name": "1\" > 3/4\" POLIETILEN DST ADAPTOR", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96467", "name": "Omal Aktüatör: DAN0030411S", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"}
]

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class CustomReportState(StatesGroup):
    waiting_date_range = State()

class QuoteBuilderState(StatesGroup):
    waiting_firm = State()
    waiting_item_query = State()
    waiting_qty = State()
    confirm_more = State()

def normalize_tr(text: str) -> str:
    if not text: return ""
    m = {'ı':'i','İ':'i','I':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = text.lower()
    for k, v in m.items(): res = res.replace(k, v)
    return res

def load_data(file_path, default):
    if not os.path.exists(file_path):
        save_data(file_path, default)
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_stocks = lambda: load_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, [])
save_sales = lambda d: save_data(SALES_FILE, d)
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_quotes = lambda d: save_data(QUOTES_FILE, d)

def get_catalog_pdf_file():
    for name in ["Katalog.pdf", "katalog.pdf", "CATALOG.PDF", "catalog.pdf", "rd96.pdf", "RD96.pdf"]:
        if os.path.exists(name): return name
    for root, dirs, files in os.walk("."):
        for fn in files:
            lower = fn.lower()
            if lower.endswith(".pdf") and ("katalog" in lower or "catalog" in lower or "rd96" in lower):
                return os.path.join(root, fn)
    return None

# ----------------- GELİŞMİŞ VE DOĞRU KATALOG KIRPMA MOTORU -----------------
def crop_slot_from_page(page, slot: int) -> bytes:
    """
    Ürün başlığı, ürün kodu ve altındaki parçayı tam kapsayan, üstteki ürüne taşmayan net kırpıcı.
    """
    pw, ph = page.rect.width, page.rect.height
    col = 0 if slot in [1, 3, 5] else 1
    row = 0 if slot in [1, 2] else (1 if slot in [3, 4] else 2)

    x0 = 12 if col == 0 else (pw / 2.0 + 4)
    x1 = (pw / 2.0 - 4) if col == 0 else (pw - 12)

    # 3'lü dikey ızgara koordinatları (Başlık + altındaki resim kutusu dahil)
    row_bounds = [
        (35, 292),   # Slot 1 & 2
        (298, 552),  # Slot 3 & 4
        (558, 816)   # Slot 5 & 6
    ]
    y0, y1 = row_bounds[row]

    try:
        import fitz
        clip_rect = fitz.Rect(max(0, x0), max(0, y0), min(pw, x1), min(ph, y1))
        pix = page.get_pixmap(clip=clip_rect, dpi=200)
        return pix.tobytes("png")
    except Exception as e:
        logging.error(f"Kırpma hatası: {e}")
        return None

def extract_part_image_from_pdf(code: str, name: str = "") -> bytes:
    pdf_path = get_catalog_pdf_file()
    if not pdf_path: return None
    try:
        import fitz
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()

        # 1. Ön tanımlı koordinat haritasından doğrudan çek
        if code_str in CATALOG_GRID_MAP:
            page_no, slot = CATALOG_GRID_MAP[code_str]
            p_idx = page_no - 1
            if p_idx < len(doc):
                return crop_slot_from_page(doc[p_idx], slot)

        # 2. Dinamik arama: Başlığı ve altındaki resmi tam yakalama
        for p_idx, page in enumerate(doc):
            rects = page.search_for(code_str) or page.search_for(f"({code_str})")
            if rects:
                r = rects[0]
                pw, ph = page.rect.width, page.rect.height
                col = 0 if r.x0 < (pw / 2.0) else 1
                
                # Kod metni ürünün başlığındadır. Başlığın 28pt üstünden başlayıp, altındaki resim dahil ~260pt indiriyoruz.
                y0 = max(20, r.y0 - 32)
                y1 = min(ph - 15, y0 + 265)
                x0 = 12 if col == 0 else (pw / 2.0 + 4)
                x1 = (pw / 2.0 - 4) if col == 0 else (pw - 12)

                clip_rect = fitz.Rect(x0, y0, x1, y1)
                pix = page.get_pixmap(clip=clip_rect, dpi=200)
                return pix.tobytes("png")
        return None
    except Exception as e:
        logging.error(f"Görsel çıkarma hatası: {e}")
        return None

# ----------------- GEMINI 2.5 FLASH İLE PDF ANALİZİ -----------------
async def parse_quote_pdf_with_gemini(pdf_path: str) -> dict:
    extracted_text = ""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for p in doc: extracted_text += p.get_text() + "\n"
    except Exception: pass

    if not extracted_text:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    extracted_text += (page.extract_text() or "") + "\n"
        except Exception: pass

    prompt = (
        "Sen tekstil otomasyonu endüstriyel teklif analiz uzmanısın. Ek'teki fiyat teklifi belgesini tara.\n"
        "YALNIZCA SAF JSON DÖNDÜR, markdown veya ek metin ekleme:\n"
        "{\n"
        '  "firm": "Müşteri / Fabrika Adı",\n'
        '  "ref_no": "Teklif No / Ref Varsa",\n'
        '  "date": "GG.AA.YYYY",\n'
        '  "currency": "EUR veya USD",\n'
        '  "grand_total": "1250.00",\n'
        '  "items": [\n'
        '    {"code": "90880", "name": "Parça Adı", "qty": 2, "unit_price": "10.00", "total_price": "20.00"}\n'
        '  ]\n'
        "}\n\n"
        f"Teklif Metni:\n{extracted_text[:4000]}"
    )

    if ai_client:
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
            )
            raw = response.text.strip()
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
            parsed = json.loads(raw)
            if parsed.get("firm") and parsed.get("items"):
                return parsed
        except Exception as e:
            logging.error(f"Gemini API parse hatası: {e}")

    # Basit Fallback
    firm_match = re.search(r"(?:Sayın|Müşteri|Firma|Firma Adı|Tesis)[\s:]+([^\n\r]+)", extracted_text, re.IGNORECASE)
    detected_firm = firm_match.group(1).strip() if firm_match else "BİLİNMEYEN FİRMA"
    return {
        "firm": detected_firm[:30].upper(),
        "ref_no": "PDF-TEKLIF",
        "date": datetime.now().strftime("%d.%m.%Y"),
        "currency": "EUR",
        "grand_total": "Belirtilmedi",
        "items": []
    }

def calculate_similarity(query: str, part: dict) -> float:
    q_norm = normalize_tr(query.strip())
    name_norm = normalize_tr(part["name"])
    code_norm = normalize_tr(part["code"])
    if q_norm == code_norm: return 1.0
    if q_norm in code_norm: return 0.95
    if q_norm in name_norm: return 0.88
    q_words, name_words = q_norm.split(), name_norm.split()
    word_scores = [max([difflib.SequenceMatcher(None, qw, nw).ratio() for nw in name_words] or [0]) for qw in q_words]
    avg_word = sum(word_scores) / len(word_scores) if word_scores else 0.0
    return max(avg_word, difflib.SequenceMatcher(None, q_norm, name_norm).ratio())

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = [(p, calculate_similarity(query, p)) for p in stocks if calculate_similarity(query, p) > 0.30]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e: logging.warning(f"İletilemedi ({cid}): {e}")

# ----------------- DÜZELTİLMİŞ Z-RAPORU & TARİH FİLTRESİ -----------------
def parse_date_safe(date_str: str) -> datetime:
    if not date_str: return None
    date_str = str(date_str).strip()
    try:
        if "T" in date_str: return datetime.fromisoformat(date_str.split(".")[0])
    except Exception: pass
    for fmt in ["%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try: return datetime.strptime(date_str, fmt)
        except Exception: pass
    return None

def filter_sales_by_range(start_dt: datetime, end_dt: datetime):
    sales = load_sales()
    res = []
    for s in sales:
        if s.get("status") != "APPROVED": continue
        d = parse_date_safe(s.get("timestamp") or s.get("date"))
        if d and (start_dt <= d <= end_dt):
            res.append(s)
    return res

def build_report_text(sales_data, report_name="SATIŞ Z-RAPORU"):
    now = datetime.now()
    if not sales_data:
        return (
            f"📊 <b>ELİPS DEPO {report_name}</b>\n"
            f"📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n"
            "═══════════════════════════════\n"
            "ℹ️ <i>Bu dönem için onaylanmış parça satışı/çıkışı bulunmamaktadır.</i>"
        )

    # Konsolide Ürün Özeti
    item_totals = {}
    plants = set()
    total_qty = 0

    for sale in sales_data:
        plants.add(sale.get("firm", "Bilinmeyen"))
        for itm in sale.get("items", []):
            code = itm.get("code", "KODSUZ")
            name = itm.get("name", "Ürün")
            q = int(itm.get("qty", 1))
            total_qty += q
            if code not in item_totals:
                item_totals[code] = {"name": name, "qty": 0}
            item_totals[code]["qty"] += q

    text = (
        f"📊 <b>ELİPS DEPO {report_name}</b>\n"
        f"📅 Rapor Tarihi: {now.strftime('%d.%m.%Y %H:%M')}\n"
        "═══════════════════════════════\n"
        f"📦 Toplam Satılan Parça: <b>{total_qty} Adet</b>\n"
        f"🏭 Hizmet Verilen Fabrika: <b>{len(plants)} Tesis</b>\n"
        f"📑 Toplam Sevkiyat Hareketi: <b>{len(sales_data)} İşlem</b>\n"
        "═══════════════════════════════\n\n"
        "<b>📦 EN ÇOK SATILAN PARÇALAR (ÖZET):</b>\n"
    )

    for idx, (code, data) in enumerate(item_totals.items(), 1):
        text += f"<b>{idx}.</b> <code>[{code}]</code> {html.escape(data['name'][:30])} ➔ <b>{data['qty']} Adet</b>\n"

    text += "\n═══════════════════════════════\n<b>🏭 TESİS ÇIKIŞLARI:</b>\n"
    for s in sales_data[:12]:
        depo_tag = "🇹🇷 [TR]" if s.get("source") == "TR_DEPO" else "🇺🇿 [ELİPS]"
        item_summary = ", ".join([f"{i.get('code')} ({i.get('qty')} adt)" for i in s.get("items", [])])
        text += f"• <code>{s.get('date', '')[:10]}</code> {depo_tag} <b>{html.escape(s.get('firm', ''))}</b>\n  └ {html.escape(item_summary)}\n"

    if len(sales_data) > 12:
        text += f"\n<i>...ve {len(sales_data) - 12} hareket daha (Excel / PDF ile tam listeyi alabilirsiniz).</i>\n"

    text += "\n📂 <i>İndirmek istediğiniz dosya formatını seçin:</i>"
    return text

def generate_excel_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_{title}_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satislar"
        headers = ["Sıra", "Tarih", "Kaynak Depo", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet"]
        ws.append(headers)
        h_fill = PatternFill(start_color="161F30", end_color="161F30", fill_type="solid")
        h_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border = Border(*(Side(style='thin', color='DDDDDD') for _ in range(4)))
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill, cell.font = h_fill, h_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        row, cnt = 2, 1
        for sale in sales_data:
            depo_str = "TR Depo" if sale.get("source") == "TR_DEPO" else "Özbek (Elips)"
            for item in sale.get("items", []):
                ws.append([cnt, str(sale.get("date", "")), depo_str, str(sale.get("ref_no", "YOK")), str(sale.get("firm", "")),
                           item.get("code", ""), item.get("name", ""), item.get("qty", 1)])
                for c in range(1, len(headers) + 1): ws.cell(row=row, column=c).border = border
                row += 1; cnt += 1
        for idx, w in enumerate([8, 16, 14, 14, 25, 16, 40, 10], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w
        wb.save(fn)
        return fn
    except Exception as e:
        logging.error(f"Excel hatası: {e}")
        return None

def generate_pdf_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_{title}_{datetime.now().strftime('%d_%m_%Y')}.pdf"
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        doc = SimpleDocTemplate(fn, pagesize=A4, rightMargin=15, leftMargin=15, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()
        t_style = ParagraphStyle('T', parent=styles['Heading1'], fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor('#161F30'), alignment=1, spaceAfter=4)
        s_style = ParagraphStyle('S', parent=styles['Normal'], fontName="Helvetica", fontSize=8, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=12)
        elements = [
            Paragraph("ELIPS TEKSTIL ELIAR PARCA SATIS RAPORU", t_style),
            Paragraph(f"RESMI DOKUM TARIHI: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_style)
        ]
        data = [["Sira", "Tarih", "Depo", "Musteri / Tesis", "Urun Kodu", "Urun Adi", "Adet"]]
        cnt, total = 1, 0
        for sale in sales_data:
            depo = "TR" if sale.get("source") == "TR_DEPO" else "Elips"
            firm = str(sale.get("firm", ""))[:22]
            date = str(sale.get("date", "")).split()[0]
            for itm in sale.get("items", []):
                q = int(itm.get("qty", 1))
                total += q
                data.append([str(cnt), date, depo, firm, str(itm.get("code", "")), str(itm.get("name", ""))[:28], str(q)])
                cnt += 1
        data.append(["TOPLAM", "", "", "", "", "Toplam Adet:", str(total)])
        table = Table(data, colWidths=[30, 65, 45, 140, 75, 155, 45], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#161F30')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E2E8F0')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
        ]))
        elements.append(table)
        doc.build(elements)
        return fn
    except Exception as e:
        logging.error(f"PDF hatası: {e}")
        return None

def get_client_history_text(firm_query: str):
    sales = load_sales()
    q_norm = normalize_tr(firm_query.strip())
    scored = []
    for s in sales:
        if s.get("status") != "APPROVED": continue
        f_norm = normalize_tr(s.get("firm", ""))
        ratio = difflib.SequenceMatcher(None, q_norm, f_norm).ratio()
        if q_norm in f_norm or ratio > 0.40:
            scored.append((s, ratio))

    if not scored:
        return f"🔍 <code>{html.escape(firm_query)}</code> için geçmiş onaylı kayıt bulunamadı."

    scored.sort(key=lambda x: x[1], reverse=True)
    best_firm = scored[0][0].get("firm")
    firm_records = [s for s, _ in scored if s.get("firm") == best_firm]

    text = f"🏢 <b>{html.escape(best_firm)} — PARÇA GEÇMİŞİ</b>\n═══════════════════════════════\n\n"
    for item in firm_records:
        depo_lbl = " [TR]" if item.get("source") == "TR_DEPO" else " [Elips]"
        for itm in item.get("items", []):
            text += f"• 📅 <code>{item.get('date', '')[:10]}</code> ➔ <b>{itm.get('qty')}x</b> <code>[{itm.get('code')}]</code> {html.escape(itm.get('name', ''))}{depo_lbl}\n"
    text += f"\n═══════════════════════════════\n✅ Toplam: <b>{len(firm_records)} Sevkiyat / Hareket</b>"
    return text

# ----------------- SAĞLAM KLAVYELER -----------------
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla"), KeyboardButton(text="📦 Parça Listesi")],
            [KeyboardButton(text="📊 Z-Raporu Al"), KeyboardButton(text="📅 Tarihli Rapor Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="📂 Verilen Teklifler")],
            [KeyboardButton(text="🏢 Tesis Geçmişi"), KeyboardButton(text="📖 Kataloğu Gönder")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="İşlem seçin..."
    )

def get_start_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Eliar Mini App'i Aç", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla", callback_data="btn_teklif_hazirla")],
            [InlineKeyboardButton(text="📦 Parça Listesi", callback_data="btn_parca_listesi"), InlineKeyboardButton(text="📊 Z-Raporu Al", callback_data="btn_z_raporu")],
            [InlineKeyboardButton(text="⏳ Bekleyen Teklifler", callback_data="btn_bekleyenler"), InlineKeyboardButton(text="📂 Verilen Teklifler", callback_data="btn_verilenler")],
            [InlineKeyboardButton(text="🏢 Tesis Geçmişi", callback_data="btn_tesis_gecmisi"), InlineKeyboardButton(text="📖 Kataloğu İndir", callback_data="btn_katalog_indir")]
        ]
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Başlat / Ana Menü"),
        BotCommand(command="teklif", description="Nilay Hanım'a Teklif Hazırla"),
        BotCommand(command="stok", description="Parça Listesi"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
        BotCommand(command="verilenler", description="Verilen Teklifler"),
        BotCommand(command="zraporu", description="Satış Z-Raporu"),
        BotCommand(command="tarihraporu", description="Tarihli Rapor Al"),
        BotCommand(command="gecmis", description="Tesis Geçmişi"),
        BotCommand(command="katalog", description="Katalog PDF İndir")
    ]
    await bot.set_my_commands(commands)
    try:
        await bot.set_chat_menu_button(menu_button=types.MenuButtonCommands())
    except Exception as e:
        logging.warning(f"Menu button: {e}")

# ----------------- ANA MENÜ / START -----------------
@dp.message(CommandStart(), StateFilter("*"))
@dp.message(Command("start"), StateFilter("*"))
@dp.message(F.text.casefold().in_(["/start", "start", "başlat", "baslat", "menü", "menu"]), StateFilter("*"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.chat.id
    sender_name = html.escape(message.from_user.first_name if message.from_user else "Kullanıcı")
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else sender_name)
    pdf_info = "✓ Bulundu" if get_catalog_pdf_file() else "✗ Bulunamadı (Katalog.pdf)"
    stocks = load_stocks()

    msg_text = (
        f"👋 Selam {name}! <b>Elips Depo</b> Robotu Aktif.\n\n"
        f"• Katalog PDF: <b>{pdf_info}</b>\n"
        f"• Güncel Depo Kalem: <b>{len(stocks)} Çeşit Parça</b>\n\n"
        f"💡 <i>Aşağıdan Mini App'e girebilir, teklif hazırlayabilir veya gelen teklif PDF'ini direkt buraya yükleyebilirsiniz.</i>"
    )
    await message.answer(msg_text, reply_markup=get_start_inline_keyboard(), parse_mode="HTML")
    await message.answer("👇 <b>Kalıcı Menü:</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ----------------- INLINE BUTON KÖPRÜLERİ -----------------
@dp.callback_query(F.data == "btn_teklif_hazirla")
async def cb_btn_teklif(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_quote_wizard(callback.message, state)

@dp.callback_query(F.data == "btn_parca_listesi")
async def cb_btn_stok(callback: types.CallbackQuery):
    await callback.answer()
    await show_stocks(callback.message)

@dp.callback_query(F.data == "btn_z_raporu")
async def cb_btn_z_raporu(callback: types.CallbackQuery):
    await callback.answer()
    await trigger_z_report_manual(callback.message)

@dp.callback_query(F.data == "btn_bekleyenler")
async def cb_btn_bekleyenler(callback: types.CallbackQuery):
    await callback.answer()
    await show_pending_quotes(callback.message)

@dp.callback_query(F.data == "btn_verilenler")
async def cb_btn_verilenler(callback: types.CallbackQuery):
    await callback.answer()
    await show_submitted_quotes(callback.message)

@dp.callback_query(F.data == "btn_tesis_gecmisi")
async def cb_btn_tesis_gecmisi(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await btn_client_history(callback.message, state)

@dp.callback_query(F.data == "btn_katalog_indir")
async def cb_btn_katalog(callback: types.CallbackQuery):
    await callback.answer()
    await send_catalog_pdf(callback.message)

@dp.message(Command("katalog"))
@dp.message(F.text == "📖 Kataloğu Gönder")
async def send_catalog_pdf(message: types.Message):
    cat_path = get_catalog_pdf_file()
    if cat_path and os.path.exists(cat_path):
        await message.answer_document(FSInputFile(cat_path), caption="📖 <b>Elips Depo - Yedek Parça Kataloğu</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Sunucuda <code>Katalog.pdf</code> bulunamadı.", parse_mode="HTML")

# ----------------- NİLAY HANIM TEKLİFİNİ TANIMA & TR / ÖZBEK DEPO ANALİZİ -----------------
@dp.message(F.document)
async def handle_document_upload(message: types.Message):
    doc = message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await message.answer("⚠️ Lütfen PDF formatında bir teklif dosyası yükleyin.")
        return

    wait_msg = await message.answer("⏳ <i>PDF analiz ediliyor, Nilay Hanım teklif geçmişi ve Elips Depo stokları taranıyor...</i>", parse_mode="HTML")

    saved_filename = f"{int(time.time())}_{doc.file_name}"
    save_path = os.path.join(PDF_STORAGE_DIR, saved_filename)
    await bot.download(doc, destination=save_path)

    parsed_data = await parse_quote_pdf_with_gemini(save_path)
    firm = parsed_data.get("firm", "BİLİNMEYEN FİRMA").upper()
    date = parsed_data.get("date", datetime.now().strftime("%d.%m.%Y"))
    currency = parsed_data.get("currency", "EUR")
    grand_total = parsed_data.get("grand_total", "-")
    items = parsed_data.get("items", [])

    # 1. Nilay Hanım Teklifi İle Eşleşme Kontrolü
    quotes = load_quotes()
    matched_quote = None
    for q in quotes:
        if normalize_tr(q.get("firm", "")) in normalize_tr(firm) or normalize_tr(firm) in normalize_tr(q.get("firm", "")):
            matched_quote = q
            break

    match_header = "🎯 <b>NİLAY HANIM'A HAZIRLANAN TEKLİF İLE EŞLEŞTİ!</b>" if matched_quote else "📄 <b>YENİ FİYAT TEKLİFİ FORMU ALGILANDI</b>"

    # 2. Elips (Özbekistan) Deposu Stok Analizi
    stocks = load_stocks()
    stock_analysis_lines = []
    has_missing_parts = False
    has_any_available = False

    for itm in items:
        code = itm.get("code", "")
        req_qty = int(itm.get("qty", 1))
        # Stokta ara
        p = next((s for s in stocks if s["code"].lower() == code.lower()), None)
        if not p:
            p = next((s for s in stocks if normalize_tr(s["name"]) in normalize_tr(itm.get("name", ""))), None)

        avail_qty = p.get("qty", 0) if p else 0
        itm["depo_available"] = avail_qty

        if avail_qty >= req_qty:
            has_any_available = True
            stock_analysis_lines.append(f"• <code>[{code}]</code> {html.escape(itm.get('name', ''))} ({req_qty} Adet) ➔ 🟢 <b>Depoda Var ({avail_qty} ADT)</b>")
        elif avail_qty > 0:
            has_any_available = True
            has_missing_parts = True
            stock_analysis_lines.append(f"• <code>[{code}]</code> {html.escape(itm.get('name', ''))} ({req_qty} Adet) ➔ 🟡 <b>Kısmi Stok ({avail_qty} ADT Var)</b>")
        else:
            has_missing_parts = True
            stock_analysis_lines.append(f"• <code>[{code}]</code> {html.escape(itm.get('name', ''))} ({req_qty} Adet) ➔ 🔴 <b>Depoda YOK (0 ADT)</b>")

    quote_id = f"TK-{int(time.time())}"
    quotes.append({
        "id": quote_id,
        "firm": firm,
        "date": date,
        "currency": currency,
        "grand_total": grand_total,
        "status": "PENDING",
        "items": items,
        "pdf_file": save_path
    })
    save_quotes(quotes)

    # Yanıt Mesajı Oluşturma
    lines = [
        match_header,
        "═══════════════════════════════",
        f"🏢 <b>Müşteri:</b> {html.escape(firm)}",
        f"📅 <b>Tarih:</b> {date}",
        f"💰 <b>Toplam Tutar:</b> <b>{grand_total} {currency}</b>\n",
        "<b>📦 ÖZBEKİSTAN (ELİPS) DEPO ENVANTER ANALİZİ:</b>"
    ]
    lines.extend(stock_analysis_lines if stock_analysis_lines else ["ℹ️ Kalem tespit edilemedi."])
    lines.append("\n═══════════════════════════════")
    lines.append("❓ <b>Bu parçalar nereden tedarik edilecek / sevk edilecek?</b>")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Özbek (Elips) Depodan Karşıla", callback_data=f"qroute:{quote_id}:ELIPS")],
        [InlineKeyboardButton(text="🇹🇷 Türkiye'den (TR) Gelecek", callback_data=f"qroute:{quote_id}:TR")],
        [InlineKeyboardButton(text="🔄 Kısmi (Elimizdekiler Özbek, Kalan TR)", callback_data=f"qroute:{quote_id}:PARTIAL")],
        [InlineKeyboardButton(text="❌ Teklifi Kabul Etme / İptal", callback_data=f"qstat:{quote_id}:REJECTED")]
    ])

    await wait_msg.delete()
    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")

# ----------------- SEVKİYAT MENŞEİ (ÖZBEK / TR) SEÇİMİ -----------------
@dp.callback_query(F.data.startswith("qroute:"))
async def on_quote_route_selected(callback: types.CallbackQuery):
    _, quote_id, route_choice = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif kaydı bulunamadı.", show_alert=True)
        return

    stocks = load_stocks()
    items = q.get("items", [])

    if route_choice == "TR":
        # Türkiye'den gelecek - Özbek depo stoklarına DOKUNMA
        q["status"] = "APPROVED"
        q["source"] = "TR_DEPO"
        save_quotes(quotes)

        # Satış defterine TR sevkiyatı olarak ekle
        sales = load_sales()
        sales.append({
            "id": f"SLS-{int(time.time())}",
            "firm": q["firm"],
            "source": "TR_DEPO",
            "ref_no": "TR-SEVKIYAT",
            "items": items,
            "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        msg = (
            f"🇹🇷 <b>TEKLİF ONAYLANDI (TÜRKİYE'DEN GELECEK)!</b>\n"
            f"═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n"
            f"📦 Parçalar Türkiye merkez depodan sevk edilecektir.\n"
            f"✅ <i>Özbekistan Elips depo stoklarına dokunulmadı.</i>"
        )
        await notify_both(msg)
        await callback.message.edit_text(msg, parse_mode="HTML")
        await callback.answer("Türkiye sevkiyatı olarak onaylandı.")
        return

    # Özbek veya Kısmi Depo Seçildiğinde Stok Kontrolü
    missing_items = []
    available_items = []

    for itm in items:
        code = itm.get("code", "")
        req_qty = int(itm.get("qty", 1))
        p = next((s for s in stocks if s["code"].lower() == code.lower()), None)
        avail = p.get("qty", 0) if p else 0

        if avail >= req_qty:
            available_items.append((code, itm.get("name", ""), req_qty, avail))
        elif avail > 0:
            available_items.append((code, itm.get("name", ""), avail, avail))
            missing_items.append((code, itm.get("name", ""), req_qty - avail))
        else:
            missing_items.append((code, itm.get("name", ""), req_qty))

    q["route_mode"] = route_choice
    save_quotes(quotes)

    warn_text = ""
    if missing_items:
        warn_text = "\n\n⚠️ <b>DİKKAT: Bazı parçalar Özbekistan Elips depomuzda YOK:</b>\n"
        for c, n, mq in missing_items:
            warn_text += f"• <code>[{c}]</code> {n} (<b>{mq} Adet Eksik</b> ➔ TR'den gelmeli)\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Evet, Elips Stoğundan Düş", callback_data=f"qapplystock:{quote_id}:yes")],
        [InlineKeyboardButton(text="❌ Hayır, Sadece Durumu Onayla", callback_data=f"qapplystock:{quote_id}:no")]
    ])

    await callback.message.edit_text(
        f"🇺🇿 <b>ÖZBEKİSTAN (ELİPS) DEPO ÇIKIŞ ONAYI</b>\n"
        f"🏢 Firma: <b>{html.escape(q['firm'])}</b>"
        f"{warn_text}\n"
        f"Mevcut olan parçalar Elips Depo stoğundan düşülsün mü?",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("qapplystock:"))
async def on_quote_apply_stock(callback: types.CallbackQuery):
    _, quote_id, choice = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif bulunamadı.", show_alert=True)
        return

    q["status"] = "APPROVED"
    q["source"] = "ELIPS_DEPO"
    save_quotes(quotes)

    if choice == "yes" and q.get("items"):
        stocks = load_stocks()
        sales = load_sales()
        deducted_report = []
        not_found_report = []

        for item in q["items"]:
            code = item.get("code", "")
            req_qty = int(item.get("qty", 1))

            p = next((s for s in stocks if s["code"].lower() == code.lower()), None)
            if not p:
                p = next((s for s in stocks if normalize_tr(s["name"]) in normalize_tr(item.get("name", ""))), None)

            if p and p.get("qty", 0) > 0:
                actual_deduct = min(p["qty"], req_qty)
                p["qty"] -= actual_deduct
                deducted_report.append(f"• <code>[{p['code']}]</code> {p['name']}: <b>-{actual_deduct} Adet</b> (Kalan: {p['qty']})")
                if actual_deduct < req_qty:
                    not_found_report.append(f"• <code>[{p['code']}]</code> {p['name']}: {req_qty - actual_deduct} Adet depoda yok (TR'den gelmeli)")
            else:
                not_found_report.append(f"• <code>[{code}]</code> {item.get('name', '')}: Depoda 0 adet var (TR'den gelmeli)")

        save_stocks(stocks)

        sales.append({
            "id": f"SLS-{int(time.time())}",
            "firm": q["firm"],
            "source": "ELIPS_DEPO",
            "ref_no": q.get("ref_no", "TEKLIF-ONAY"),
            "items": q["items"],
            "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        broadcast = (
            f"📦 <b>ELİPS DEPO - STOK ÇIKIŞI GERÇEKLEŞTİ!</b>\n"
            f"═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n\n"
            f"<b>✅ Düşülen Parçalar:</b>\n" + ("\n".join(deducted_report) if deducted_report else "Yok")
        )
        if not_found_report:
            broadcast += "\n\n<b>⚠️ Depoda Olmayan / TR'den İstenecekler:</b>\n" + "\n".join(not_found_report)

        await notify_both(broadcast)
        await callback.message.edit_text(broadcast, parse_mode="HTML")
    else:
        await callback.message.edit_text("✅ <b>Teklif onaylandı (Depo stokları değiştirilmedi).</b>", parse_mode="HTML")
    await callback.answer("İşlem tamamlandı.")

@dp.callback_query(F.data.startswith("qstat:"))
async def on_quote_status_cancel(callback: types.CallbackQuery):
    _, quote_id, new_status = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if q:
        q["status"] = new_status
        save_quotes(quotes)
    await callback.message.edit_text("🔴 <b>Teklif reddedildi / iptal edildi.</b>", parse_mode="HTML")
    await callback.answer("İptal edildi.")

# ----------------- BEKLEYEN VE VERİLEN TEKLİFLER -----------------
@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    quotes = load_quotes()
    pending = [q for q in quotes if q.get("status") == "PENDING"]
    if not pending:
        await message.answer("ℹ️ Şu anda bekleyen bir teklif bulunmamaktadır.", parse_mode="HTML")
        return

    buttons = []
    for q in pending[-10:]:
        buttons.append([InlineKeyboardButton(text=f"⏳ {q['firm']} ({q.get('date', '')[:10]})", callback_data=f"qview:{q['id']}")])
    await message.answer("⏳ <b>BEKLEYEN TEKLİFLER:</b>\nİncelemek istediğinize tıklayın:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.message(Command("verilenler"))
@dp.message(F.text == "📂 Verilen Teklifler")
async def show_submitted_quotes(message: types.Message):
    quotes = load_quotes()
    if not quotes:
        await message.answer("ℹ️ Henüz kayıtlı bir teklif bulunmamaktadır.", parse_mode="HTML")
        return

    buttons = []
    for q in reversed(quotes[-12:]):
        st_icon = "🟢" if q.get("status") == "APPROVED" else ("🔴" if q.get("status") == "REJECTED" else "⏳")
        depo_lbl = " [TR]" if q.get("source") == "TR_DEPO" else (" [Elips]" if q.get("source") == "ELIPS_DEPO" else "")
        buttons.append([InlineKeyboardButton(text=f"{st_icon} {q['firm']}{depo_lbl} ({q.get('date', '')[:10]})", callback_data=f"qview:{q['id']}")])
    await message.answer("📂 <b>VERİLEN TEKLİFLER LİSTESİ:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data.startswith("qview:"))
async def on_quote_view_details(callback: types.CallbackQuery):
    quote_id = callback.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif bulunamadı.", show_alert=True)
        return

    st_map = {"PENDING": "⏳ Beklemede", "APPROVED": "✅ Onaylandı", "REJECTED": "❌ Reddedildi"}
    cur_st = st_map.get(q.get("status"), "Belirsiz")
    cur = q.get("currency", "EUR")

    lines = [
        f"📄 <b>Teklif Detayı</b>",
        f"🏢 Firma: <b>{html.escape(q['firm'])}</b>",
        f"📅 Tarih: <code>{q.get('date')}</code>",
        f"📊 Durum: <b>{cur_st}</b>",
        f"💰 Toplam: <b>{q.get('grand_total', '-')} {cur}</b>\n",
        "📦 <b>Parçalar:</b>"
    ]
    for idx, itm in enumerate(q.get("items", []), 1):
        lines.append(f"{idx}. <code>[{itm.get('code')}]</code> {itm.get('name')} — {itm.get('qty')} Adet")

    if q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        await callback.message.answer_document(FSInputFile(q["pdf_file"]), caption="\n".join(lines), parse_mode="HTML")
    else:
        await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()

# ----------------- NİLAY HANIM'A TEKLİF SİHİRBAZI -----------------
@dp.message(Command("teklif", ignore_mention=True))
@dp.message(F.text == "📝 Nilay Hanım'a Teklif Hazırla")
async def start_quote_wizard(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteBuilderState.waiting_firm)
    await message.answer("🏢 <b>Teklif hangi müşteri / fabrika için hazırlanacak?</b>\n(Örnek: <code>MARK FORMELLE</code>, <code>TERRY JAR</code>)", parse_mode="HTML")

@dp.message(QuoteBuilderState.waiting_firm, ~F.text.startswith("/"))
async def process_quote_firm(message: types.Message, state: FSMContext):
    firm = message.text.strip().upper()
    await state.update_data(firm_name=firm)
    await state.set_state(QuoteBuilderState.waiting_item_query)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Parça Kataloğunu İncele (PDF)", callback_data="qb_get_catalog")]
    ])
    await message.answer(
        f"🔍 <b>Hangi parça için teklif istenecek?</b>\n"
        f"• Varsa <b>Sipariş Kodunu</b> yazın (Örn: <code>91661</code>, <code>90880</code>)\n"
        f"• Veya <b>Ürün İsmini</b> yazın (Örn: <code>sürücü</code>, <code>diyafram</code>):",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "qb_get_catalog")
async def cb_send_catalog_in_quote(callback: types.CallbackQuery):
    cat_path = get_catalog_pdf_file()
    if cat_path and os.path.exists(cat_path):
        await callback.message.answer_document(FSInputFile(cat_path), caption="📖 <b>Yedek Parça Kataloğu</b>", parse_mode="HTML")
    else:
        await callback.answer("Katalog dosyası bulunamadı.", show_alert=True)
    await callback.answer()

def render_search_results_page(matches, page_idx, query):
    page_size = 5
    total_pages = (len(matches) + page_size - 1) // page_size
    page_idx = max(0, min(page_idx, total_pages - 1))
    current_items = matches[page_idx * page_size : (page_idx + 1) * page_size]

    buttons = [[InlineKeyboardButton(text=f"👉 {p['code']} - {p['name'][:30]}", callback_data=f"qbsel:{p['code']}")] for p, _ in current_items]

    nav_row = []
    if page_idx > 0: nav_row.append(InlineKeyboardButton(text="⬅️ Önceki", callback_data=f"qbpage:{page_idx-1}"))
    if page_idx < total_pages - 1: nav_row.append(InlineKeyboardButton(text="Sonraki ➡️", callback_data=f"qbpage:{page_idx+1}"))
    if nav_row: buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔍 Tekrar Ara", callback_data="qb_retry_search"),
        InlineKeyboardButton(text="📖 Kataloğu Aç", callback_data="qb_get_catalog")
    ])

    text = f"🔍 <b>Arama:</b> <code>{html.escape(query)}</code> (Sayfa: {page_idx + 1}/{total_pages})\nLütfen listeden parçayı seçin:"
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(QuoteBuilderState.waiting_item_query, ~F.text.startswith("/"))
async def process_quote_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    matches = find_best_matches(query)

    if not matches:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📖 Kataloğu Gönder", callback_data="qb_get_catalog")]])
        await message.answer(f"⚠️ <code>{html.escape(query)}</code> ile eşleşen parça bulunamadı.\nKataloğu incelemek ister misiniz?", reply_markup=kb, parse_mode="HTML")
        return

    top_part, _ = matches[0]
    if query.lower() == top_part['code'].lower():
        await state.update_data(selected_part=top_part)
        await state.set_state(QuoteBuilderState.waiting_qty)

        img_bytes = extract_part_image_from_pdf(top_part["code"], top_part.get("name", ""))
        if img_bytes:
            photo = BufferedInputFile(img_bytes, filename=f"{top_part['code']}.png")
            await message.answer_photo(photo, caption=f"📸 <b>Katalog Görseli:</b> <code>[{top_part['code']}]</code> — {html.escape(top_part['name'])}", parse_mode="HTML")

        stock_text = f"Depo: {top_part.get('qty', 0)} ADT" if top_part.get('qty', 0) > 0 else "Stokta Yok (0 ADT)"
        await message.answer(f"🎯 <b>Seçilen:</b> <code>[{top_part['code']}]</code> {html.escape(top_part['name'])}\n📦 <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")
        return

    await state.update_data(search_matches=matches, search_query=query)
    text, kb = render_search_results_page(matches, 0, query)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("qbpage:"))
async def on_quote_page_navigate(callback: types.CallbackQuery, state: FSMContext):
    page_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    text, kb = render_search_results_page(data.get("search_matches", []), page_idx, data.get("search_query", ""))
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "qb_retry_search")
async def on_quote_retry(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Lütfen parça ismini veya kodunu tekrar yazın:")
    await callback.answer()

@dp.callback_query(F.data.startswith("qbsel:"))
async def on_quote_part_confirmed(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]
    stocks = load_stocks()
    part = next((p for p in stocks if p["code"] == code), None)
    if not part:
        await callback.answer("Parça bulunamadı.", show_alert=True)
        return

    await state.update_data(selected_part=part)
    await state.set_state(QuoteBuilderState.waiting_qty)

    img_bytes = extract_part_image_from_pdf(part["code"], part.get("name", ""))
    if img_bytes:
        photo = BufferedInputFile(img_bytes, filename=f"{part['code']}.png")
        await callback.message.answer_photo(photo, caption=f"📸 <b>Katalog Görseli:</b> <code>[{part['code']}]</code> — {html.escape(part['name'])}", parse_mode="HTML")

    stock_text = f"Depo: {part.get('qty', 0)} ADT" if part.get('qty', 0) > 0 else "Stokta Yok (0 ADT)"
    await callback.message.answer(f"🎯 <b>Seçilen:</b> <code>[{part['code']}]</code> {html.escape(part['name'])}\n📦 <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_qty, ~F.text.startswith("/"))
async def process_quote_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("⚠️ Lütfen geçerli bir sayı girin (Örn: 1, 2):", parse_mode="HTML")
        return

    data = await state.get_data()
    part = data.get("selected_part")
    items = data.get("quote_items", [])
    items.append({"code": part["code"], "name": part["name"], "qty": qty})
    await state.update_data(quote_items=items)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="qb_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir ve Metni Al", callback_data="qb_done")]
    ])
    await state.set_state(QuoteBuilderState.confirm_more)
    await message.answer(f"✅ <b>{qty} Adet</b> <code>[{part['code']}]</code> eklendi!\nNe yapmak istersiniz?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "qb_more")
async def on_quote_add_another(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Yeni parçanın <b>kodunu</b> veya <b>ismini</b> yazın:", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "qb_done")
async def on_quote_completed(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    firm = html.escape(data.get("firm_name", "MÜŞTERİ"))
    items = data.get("quote_items", [])
    if not items:
        await callback.message.edit_text("⚠️ Teklifte ürün yok.")
        await state.clear()
        return

    formatted_quote = (
        f"Merhaba Nilay hanim\n\n"
        f"{firm} için aşağıdaki listedeki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    )
    for itm in items:
        formatted_quote += f"• {itm['code']} - {itm['name']} - {itm['qty']} Adet\n"
    formatted_quote += "\nİyi çalışmalar."

    quotes = load_quotes()
    quote_id = f"TK-{int(time.time())}"
    quotes.append({
        "id": quote_id,
        "firm": firm,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING",
        "items": items,
        "pdf_file": None
    })
    save_quotes(quotes)

    text = (
        f"📋 <b>KOPYALAMAYA HAZIR NİLAY HANIM TEKLİF METNİ:</b>\n"
        f"═══════════════════════════════\n\n"
        f"<code>{html.escape(formatted_quote)}</code>\n\n"
        f"═══════════════════════════════\n"
        f"💡 <i>Metnin üstüne tek tık yaparak kopyalayabilir, Nilay Hanım'a WhatsApp/Mail ile atabilirsiniz.</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")

    notify_text = (
        f"📥 <b>YENİ TEKLİF TALEBİ OLUŞTURULDU!</b>\n\n"
        f"🏢 <b>Firma:</b> {firm}\n"
        f"📦 <b>Ürünler:</b>\n" +
        "\n".join([f"• [{i['code']}] {i['name']} ({i['qty']} Adet)" for i in items])
    )
    await notify_both(notify_text)
    await state.clear()
    await callback.answer("Teklif kaydedildi!")

# ----------------- PARÇA LİSTESİ -----------------
@dp.message(Command("stok", ignore_mention=True))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stocks(message: types.Message):
    stocks = load_stocks()
    available = [s for s in stocks if s.get("qty", 0) > 0]
    out_of_stock = [s for s in stocks if s.get("qty", 0) == 0]

    text = f"📦 <b>GÜNCEL ELİPS DEPO STOKLARI</b>\n"
    text += f"📊 Toplam Kalem: <b>{len(stocks)}</b> | Stokta: <b>{len(available)}</b> | Tükendi: <b>{len(out_of_stock)}</b>\n"
    text += "═══════════════════════════════\n\n"

    for s in available[:15]:
        text += f"• <code>[{s['code']}]</code> {html.escape(s['name'][:35])}\n  └ Stok: <b>{s['qty']} ADT</b> | {s['loc']}\n"
    if len(available) > 15:
        text += f"\n<i>...ve {len(available)-15} kalem ürün daha (Mini App'ten görebilirsiniz).</i>"

    await message.answer(text, parse_mode="HTML")

# ----------------- RAPOR MOTORU & MENÜSÜ -----------------
@dp.message(Command("zraporu", ignore_mention=True))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Bugünün Z-Raporu", callback_data="date_filter:today"),
            InlineKeyboardButton(text="📅 Bu Hafta (Son 7 Gün)", callback_data="date_filter:7days")
        ],
        [
            InlineKeyboardButton(text="🗓️ Bu Ayın Raporu", callback_data="date_filter:this_month"),
            InlineKeyboardButton(text="📦 Tüm Satışlar & Kapanış", callback_data="date_filter:all")
        ],
        [
            InlineKeyboardButton(text="✍️ Özel Tarih Aralığı Gir", callback_data="date_filter:custom")
        ]
    ])
    await message.answer("📊 <b>Hangi dönemin Z-Raporunu almak istiyorsunuz?</b>", reply_markup=kb, parse_mode="HTML")

@dp.message(Command("tarihraporu", ignore_mention=True))
@dp.message(F.text == "📅 Tarihli Rapor Al")
async def trigger_custom_date_report(message: types.Message):
    await trigger_z_report_manual(message)

@dp.callback_query(F.data.startswith("date_filter:"))
async def process_date_filter_btn(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    now = datetime.now()

    if mode == "custom":
        await state.set_state(CustomReportState.waiting_date_range)
        await callback.message.answer("✍️ Format: <code>GG.AA.YYYY - GG.AA.YYYY</code>\n(Örnek: <code>01.10.2026 - 30.10.2026</code>)", parse_mode="HTML")
        await callback.answer()
        return

    if mode == "today":
        s_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
        e_dt = datetime(now.year, now.month, now.day, 23, 59, 59)
        title_label, file_label = "GÜNLÜK Z-RAPORU", "Gunluk_Z_Raporu"
    elif mode == "7days":
        s_dt = now - timedelta(days=7)
        e_dt = now
        title_label, file_label = "HAFTALIK Z-RAPORU (SON 7 GÜN)", "Haftalik_Z_Raporu"
    elif mode == "this_month":
        s_dt = datetime(now.year, now.month, 1, 0, 0, 0)
        e_dt = now
        title_label, file_label = "BU AYIN Z-RAPORU", "Aylik_Z_Raporu"
    else:  # all
        s_dt = datetime(2020, 1, 1)
        e_dt = datetime(2035, 1, 1)
        title_label, file_label = "GENEL SATIŞ Z-RAPORU (TÜMÜ)", "Genel_Z_Raporu"

    sales = filter_sales_by_range(s_dt, e_dt)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel İndir (.xlsx)", callback_data="dl_rep:excel:custom"),
         InlineKeyboardButton(text="📑 PDF İndir (.pdf)", callback_data="dl_rep:pdf:custom")],
        [InlineKeyboardButton(text="📦 İkisini de İndir (Excel + PDF)", callback_data="dl_rep:both:custom")]
    ])
    await state.update_data(last_filtered_sales=sales, report_title=file_label)
    await callback.message.edit_text(build_report_text(sales, title_label), reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(CustomReportState.waiting_date_range, ~F.text.startswith("/"))
async def process_custom_date_range(message: types.Message, state: FSMContext):
    try:
        s_str, e_str = [p.strip() for p in message.text.split("-")]
        s_dt = datetime.strptime(s_str, "%d.%m.%Y")
        e_dt = datetime.strptime(e_str, "%d.%m.%Y").replace(hour=23, minute=59, second=59)
        sales = filter_sales_by_range(s_dt, e_dt)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Excel İndir", callback_data="dl_rep:excel:custom"),
             InlineKeyboardButton(text="📑 PDF İndir", callback_data="dl_rep:pdf:custom")],
            [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:custom")]
        ])
        await state.update_data(last_filtered_sales=sales, report_title=f"Rapor_{s_str}_{e_str}")
        await message.answer(build_report_text(sales, f"ÖZEL Z-RAPORU ({s_str} - {e_str})"), reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Format hatalı! Örnek format: <code>01.10.2026 - 30.10.2026</code>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("dl_rep:"))
async def handle_download_report_choice(callback: types.CallbackQuery, state: FSMContext):
    _, fmt, scope = callback.data.split(":")
    now = datetime.now()

    if scope == "weekly":
        sales = filter_sales_by_range(now - timedelta(days=7), now)
        title = "Haftalik_Z_Raporu"
    elif scope == "monthly":
        sales = filter_sales_by_range(datetime(now.year, now.month, 1), now)
        title = "Aylik_Z_Raporu"
    else:
        st_data = await state.get_data()
        sales = st_data.get("last_filtered_sales", [])
        title = st_data.get("report_title", "Z_Raporu")

    if not sales:
        await callback.answer("Bu dönem için onaylı satış kaydı bulunmuyor.", show_alert=True)
        return

    await callback.answer("Rapor dökümanı hazırlanıyor...")
    if fmt in ["excel", "both"]:
        f = generate_excel_z_report(sales, title)
        if f and os.path.exists(f):
            await callback.message.answer_document(FSInputFile(f), caption=f"📊 <b>Elips Depo {title} (Excel)</b>", parse_mode="HTML")

    if fmt in ["pdf", "both"]:
        f = generate_pdf_z_report(sales, title)
        if f and os.path.exists(f):
            await callback.message.answer_document(FSInputFile(f), caption=f"📑 <b>Elips Depo {title} (PDF)</b>", parse_mode="HTML")

# ----------------- TESİS GEÇMİŞİ -----------------
@dp.message(Command("gecmis", ignore_mention=True))
async def cmd_history_query(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Tesis adı belirtin. (Örn: <code>/gecmis TERRY JAR</code>)", parse_mode="HTML")
        return
    await message.answer(get_client_history_text(parts[1]), parse_mode="HTML")

@dp.message(F.text == "🏢 Tesis Geçmişi")
async def btn_client_history(message: types.Message, state: FSMContext):
    await state.set_state(ClientHistoryState.waiting_client_name)
    await message.answer("🔍 Geçmişini aradığınız <b>Fabrika Adını</b> yazın (Örn: Terry, Zelal, Asaka):", parse_mode="HTML")

@dp.message(ClientHistoryState.waiting_client_name, ~F.text.startswith("/"))
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="HTML")

# ----------------- WEBAPP -----------------
@dp.message(F.web_app_data)
async def handle_webapp_payload(message: types.Message):
    try: p = json.loads(message.web_app_data.data)
    except Exception: return
    op = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    ref_id = f"REF-{message.message_id}"
    dir_type = p.get("direction")

    if dir_type == "STOCK_CHANGE" and p.get("action") == "DECREASE":
        dest = p.get("destination", "Bilinmeyen")
        code, name, qty = p.get("code"), p.get("name"), p.get("delta", 1)
        sales = load_sales()
        sales.append({
            "id": ref_id, "firm": dest, "source": "ELIPS_DEPO", "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        msg = f"📤 <b>PARÇA SATILDI / DEPO ÇIKIŞI!</b>\n🏢 Firma: <code>{html.escape(dest)}</code>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n📉 Adet: <b>-{qty}</b> | Kalan: <code>{p.get('current_qty', 0)} ADT</code>\n👷‍♂️ Çıkış Yapan: {op}"
        await notify_both(msg)

# ----------------- SOHBET KÖPRÜSÜ -----------------
@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    menu_buttons = ["📦 Parça Listesi", "📊 Z-Raporu Al", "📅 Tarihli Rapor Al", "⏳ Bekleyen Teklifler", "📂 Verilen Teklifler", "🏢 Tesis Geçmişi", "📝 Nilay Hanım'a Teklif Hazırla", "📖 Kataloğu Gönder"]
    if message.text in menu_buttons: return
    tid = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if message.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and message.text:
        await bot.send_message(tid, f"💬 <b>{sender}:</b> {html.escape(message.text)}", parse_mode="HTML")
        await message.reply("✓ <i>İletildi.</i>", parse_mode="HTML")

# ----------------- ZAMANLAYICI & SERVER -----------------
async def automated_scheduler():
    last_week = ""
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = filter_sales_by_range(now - timedelta(days=7), now)
            await notify_both("📢 <b>HAFTALIK OTOMATİK Z-RAPORU</b>\n\n" + build_report_text(sales, "HAFTALIK"))
            if sales:
                f_xls = generate_excel_z_report(sales, "Haftalik")
                f_pdf = generate_pdf_z_report(sales, "Haftalik")
                if f_xls: await bot.send_document(OMER_CHAT_ID, FSInputFile(f_xls))
                if f_pdf: await bot.send_document(OMER_CHAT_ID, FSInputFile(f_pdf))
        await asyncio.sleep(25)

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="Elips Depo Robotu Aktif"))
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        await web.TCPSite(runner, '0.0.0.0', port).start()
    except Exception as e:
        logging.warning(f"Server başlatılamadı: {e}")

async def main():
    try:
        save_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands()
        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        logging.info(">>> ELIPS DEPO BOTU KUSURSUZ DEVREDE <<<")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Kritik hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
