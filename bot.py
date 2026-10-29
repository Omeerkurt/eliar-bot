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
from aiogram.filters import Command, CommandStart
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

ai_client = None
if HAS_GENAI and GEMINI_API_KEY:
    try:
        ai_client = genai.Client(api_key=GEMINI_API_KEY)
        logging.info("✅ Google GenAI istemcisi bağlandı.")
    except Exception as e:
        logging.warning(f"⚠️ Gemini uyarısı: {e}")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            u_name = event.from_user.first_name if event.from_user else "Bilinmeyen"
            logging.info(f"--- MESAJ: {u_name} (ID: {event.chat.id}) | {event.text or event.document.file_name if event.document else ''}")
        return await handler(event, data)

dp.message.outer_middleware(LoggingMiddleware())

# ----------------- 1. TÜM FSM DURUMLARI (EN BAŞTA) -----------------
class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class CustomReportState(StatesGroup):
    waiting_date_range = State()

class QuoteBuilderState(StatesGroup):
    waiting_firm = State()
    waiting_item_query = State()
    waiting_custom_manual = State()
    waiting_ask_technic_input = State()
    waiting_supply_source = State()
    waiting_qty = State()
    confirm_more = State()

# ----------------- 2. DOSYA VE VERİ YARDIMCILARI -----------------
STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"
QUOTES_FILE = "submitted_quotes.json"
PDF_STORAGE_DIR = "stored_quotes_pdf"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_data(file_path, default):
    if not os.path.exists(file_path):
        save_data(file_path, default)
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def normalize_tr(text: str) -> str:
    if not text: return ""
    m = {'ı':'i','İ':'i','I':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = text.lower()
    for k, v in m.items(): res = res.replace(k, v)
    return res

# ----------------- 3. 64 SAYFALIK KATALOG IZGARA HARİTASI -----------------
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

# ----------------- 4. GERÇEK ELİPS DEPO ENVANTERİ -----------------
REAL_WAREHOUSE_STOCKS = [
    {"code": "Pd320", "name": "Pd320 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "PD330", "name": "PD330 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Aim8-A", "name": "Aim8-A Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "Aim8-B", "name": "Aim8-B Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "Dim32", "name": "Dim32 Dijital Giriş Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Dom16-PLC", "name": "Dom16-PLC Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 6, "loc": "ELIPS-DEPO"},
    {"code": "P44", "name": "P44 Panel Kartı", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "Pd300", "name": "Pd300 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "Pd340", "name": "Pd340 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "Pd350", "name": "Pd350 Kontrol Cihazı", "cat": "KONTROL", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "S400", "name": "S400 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "S42", "name": "S42 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Umf-ILETISIM20", "name": "Umf-ILETISIM20 kablosu", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "TBBPLC-F", "name": "TBBPLC-F Modülü", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "Edc T7000", "name": "Edc T7000 Kontrolör", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "Edc M7700", "name": "Edc M7700 Kontrolör", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "Edc T710", "name": "Edc T710 Kontrolör", "cat": "KONTROL", "qty": 9, "loc": "ELIPS-DEPO"},
    {"code": "Edc T712", "name": "Edc T712 Kontrolör", "cat": "KONTROL", "qty": 8, "loc": "ELIPS-DEPO"},
    {"code": "Powerfail", "name": "Powerfail Güç Koruma Kartı", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "P42", "name": "P42 Panel Kartı", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "P300", "name": "P300 Panel Kartı", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "P40", "name": "P40 Panel Kartı", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "Edc T7701EX", "name": "Edc T7701EX Kontrolör", "cat": "KONTROL", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "Edc T7700", "name": "Edc T7700 Kontrolör", "cat": "KONTROL", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "T7700", "name": "T7700 Cihazı", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "P43", "name": "P43 Panel Kartı", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "AOM8", "name": "AOM8 Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 7, "loc": "ELIPS-DEPO"},
    {"code": "T7701 EX G", "name": "T7701 EX G Cihazı", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "T7RACK 6 PLC", "name": "T7RACK 6 PLC Ünitesi", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "T7RACK 10 PLC", "name": "T7RACK 10 PLC Ünitesi", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-POWER 30", "name": "T7PAC-POWER 30 Güç Kaynağı", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-POWER 20", "name": "T7PAC-POWER 20 Güç Kaynağı", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-DIM32V5", "name": "T7PAC-DIM32V5 Giriş Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-DOM32V5", "name": "T7PAC-DOM32V5 Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-DIM16V5", "name": "T7PAC-DIM16V5 Giriş Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-AIO88SV1", "name": "T7PAC-AIO88SV1 Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-AI8SV1", "name": "T7PAC-AI8SV1 Analog Giriş", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-AO8SV1", "name": "T7PAC-AO8SV1 Analog Çıkış", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "PANELSET-T7701 ex", "name": "PANELSET-T7701 ex Ön Panel Seti", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "PANELSET-T7700", "name": "PANELSET-T7700 Ön Panel Seti", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-T7CPURIO", "name": "T7PAC-T7CPURIO İşlemci", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-DOM16V5", "name": "T7PAC-DOM16V5 Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "40025", "name": "PLC CPU: DVP12SA211R: 8DI 4DO", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "SP-01", "name": "Saha panosu (SPU su yok)", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "RA032DA", "name": "RA032DA09036000 aktuator", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "1013", "name": "Vana TORK (ko'k) 3/4\" 3 yollu + aktuator", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "1015", "name": "SLD Kanal Vanası Full 3/4\" TORK 2 yollu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "5022", "name": "Salmastra (Geylani ile geldi)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "30010", "name": "EBARA 15MM SIL/SIL/VITON SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "30076", "name": "SANTOPRENE DIAPHRAGM POMKAR PK10", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "40597", "name": "BES005M BALLUFF Sensör", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "40634", "name": "BES0057: Balluff M12MI-NSC40B-BV03", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "40647", "name": "Smc CJPB15-10H6 Tek Etkili Silindir", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "41300", "name": "RD96 - MU CAMBAZ PISTONU POLIETILEN (YESIL) TAKOZ", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "41316", "name": "Lab120 encoder", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41396", "name": "12'li Hareketli Kablo (X3-X4 Pistonu)", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "42184", "name": "PIPETLEME SIRINGA UCU", "cat": "MEKATRONIK", "qty": 200, "loc": "ELIPS-DEPO"},
    {"code": "50014", "name": "SUSTURUCU: AN15-02: 1/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "50018", "name": "VALF: SY5140-5YO-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50090", "name": "Tork çift etkili aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50138", "name": "PNOMATIK RAKOR: KQ2L04-M5A 4MM DIRSEK", "cat": "MEKATRONIK", "qty": 11, "loc": "ELIPS-DEPO"},
    {"code": "50156", "name": "T RAKOR: KQ2T06-22A 6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50227", "name": "KISICILI RAKOR: AS2201F-01-04SA 1/8\"-4MM", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "50238", "name": "SUSTURUCU: AN 120-M5 (SMC)", "cat": "MEKATRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "50242", "name": "KISICILI RAKOR: AS2002F-06 6MM HAT TIPI", "cat": "MEKATRONIK", "qty": 7, "loc": "ELIPS-DEPO"},
    {"code": "50257", "name": "TEK ETLKILI PNOMATIK SILINDIR CD75E32", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50258", "name": "SILINDIR CD85N16-100-B (SMC)", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50259", "name": "SILINDIR CD85N16-200-B (SMC)", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50260", "name": "PISTON CD85N16-50-B", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50261", "name": "PISTON CD85N16-80-B", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50269", "name": "Manifold: SS3Y1-S41-02-M5-Q 2'li", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50270", "name": "Manifold: SS3Y1-S41-04-M5-Q 4'lü", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50287", "name": "VALF: SY114-5LOU-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50289", "name": "VALF: SY3220-5LOU-M5-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50291", "name": "VALF: SYJ3143-5LOU-Q", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50292", "name": "VALF: SYJ3240-5LOU-Q", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50293", "name": "VALF: SYJ3243-5LOU-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50294", "name": "VALF: SYJ7120-5DZ-01F-Q", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "50295", "name": "VALF: SYJ7220-5DZ-01F-Q", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "52156", "name": "PNOMATIK T RAKOR: KQ2T06-00A 6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "54626", "name": "A03/0-24VDC B00123525: 5W 22mm", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "54654", "name": "LOP POMPA FILTRE ORINGI 30*3 MM", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "90416", "name": "SOLENOID VALF: 00125317 24VDC", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90501", "name": "SMC C76-32PS PISTON KECESI", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90715", "name": "REGULATOR: AR10-M5H: 0-8 BAR", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90726", "name": "HIZ AYAR VALFI: ASN2-02 1/4\" SUSTURUCULU", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90759", "name": "SENSOR TUTUCU: BJ2-016", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "90761", "name": "SENSOR TUTUCU: BM2-025", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "90765", "name": "RD96 CAMBAZ KOLU", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90766", "name": "RD96 ALIMINYUM LAMA MONTAJ PARCASI", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90769", "name": "RD96 BOS CAMBAZ KUTUSU", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90771", "name": "RD96 CAMBAZ MEKANIZMASI", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90781", "name": "SMC C85-25PS PISTON KECESI", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90782", "name": "C85C16 EKLEM BAGLANTI PARCASI", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "90840", "name": "PISTON SENSORU: DC73L", "cat": "ELEKTRONIK", "qty": 6, "loc": "ELIPS-DEPO"},
    {"code": "90879", "name": "DST CEKVALF O-RINGI", "cat": "MEKATRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "90881", "name": "DST CEKVALF YAYI", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90946", "name": "SLR1-40 FILTRE", "cat": "MEKATRONIK", "qty": 12, "loc": "ELIPS-DEPO"},
    {"code": "90948", "name": "FIP25 BAKALIT FLANŞ", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91035", "name": "OMAL (TAMIR) TAKIMI: KGBV4505 3/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "91036", "name": "1\" OMAL VANA TAMIR TAKIMI", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "91037", "name": "Omal küresel vana conta tamir takımı", "cat": "MEKATRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "91043", "name": "VALF KABLOSU", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "91045", "name": "SMC KURESEL MAFSAL: KJ6D M6*1", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91064", "name": "PNOMATIK RAKOR: KQ2H04-M5A 4MM DUZ", "cat": "MEKATRONIK", "qty": 13, "loc": "ELIPS-DEPO"},
    {"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR KQ2L04-01NS", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91074", "name": "PNOMATIK RAKOR: KQ2L6M5N 6MM DIRSEK", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "91086", "name": "PNOMATIK T RAKOR: KQ2T04-M5A 4MM", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "91088", "name": "T RAKOR: KQ2T08-06 8-6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91238", "name": "FIP25 POMPA KAPAK O-RINGI", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91277", "name": "RD96-Mu Polietilen Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91284", "name": "BONESSI VALF: P00112200 E1A/4", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91303", "name": "PASLANMAZ ARABA 4 DELIKLI REXROTH", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91332", "name": "FESTO BASINC ANAHTARI", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91406", "name": "FIP25 SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91448", "name": "PNOMATIK RAKOR: 57116 1/8\"-6MM DIRSEK", "cat": "MEKATRONIK", "qty": 8, "loc": "ELIPS-DEPO"},
    {"code": "91463", "name": "EUROTEC REDUCER-KAFA ADAPTORU", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91502", "name": "LAB120 mikser kayışı", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91590", "name": "U4 CEKVALF", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91594", "name": "VALF: SY5240-5YO-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91603", "name": "Omal Vana: V451H405 3 Yollu L Port 3/4\"", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91604", "name": "1\" 3 YOLLU L PORT VANA", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91633", "name": "OMAL VIP VANA VNC10004", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96185", "name": "PISTON: CD76E32-50-B", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96412", "name": "1\" > 3/4\" POLIETILEN DST CEK VALF ADAPTORU", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96467", "name": "Omal Aktüatör: DAN0030411S F03-F05", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96496", "name": "Omal Çift Etkili Aktüatör: DAN0015411S", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96515", "name": "DST Polietilen Z Eksen dayama takozu", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "96517", "name": "Rd96_MU Z Polietilen Z eksen Piston Dayama Takozu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96570", "name": "Ø19mm Şeffaf Telli Hortum (Mavi)", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "C-137161", "name": "Tuz rofinadsiyon filtr kapagi", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "TEST", "name": "Güç Kaynağı: DRL-24V75W1AZ", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90880", "name": "DST Çekvalf Teflonu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "cat": "MEKATRONIK", "qty": 9, "loc": "ELIPS-DEPO"},
    {"code": "90620", "name": "PH Sensörü: SPH-1-DJ-6M Ph Sensör - 6mt Kablosu", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91410", "name": "Wat 3 faz Motor (Q2E112M6C) 2,2 kW 3 HP", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91411", "name": "WAT Motor Ayağı (Q2E112M6C)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41436", "name": "Rd96 SLR1-40 Pompa Çıkış Bağlantı Rakor ve Dirsekleri", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41435", "name": "Rd96 SLR1-40 Pompa Giriş Bağlantı Rakor ve Dirsekleri", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "96469", "name": "Rakor Contası - Gasket - Nw 40 Dın - EPDM", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "60002", "name": "Klemp Contası: EPDM (DN25) 1''- Ø33.7mm", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91661", "name": "Sürücü VZAB2P2BAA V1000 3/2,2 kW", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "40642", "name": "PLC CPU: CJ1M-CPU21", "cat": "KONTROL", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "40645", "name": "Güç kaynağı: CJ1W-PA202", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "40643", "name": "Dijital giriş modülü: CJ1W-ID211", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "40644", "name": "Dijital çıkış modülü: CJ1W-OC211", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90802", "name": "Güç Kaynağı: CQM1-PA203 (omron)", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91514", "name": "Rd96 SLR1-40 AISI 316L Loblu Pompa", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41381", "name": "Rd96 22 Li Pompa Altı Paslanmaz Tava", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90338", "name": "SLR1-40 ASI 316L Salmastra Bileziği", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91128", "name": "SLR 1-40 Mec. Seal Si.Carbon/Si.Carbide", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91516", "name": "SLR1-40 NBR O-Ring (Part No 80D)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41538", "name": "SLR1-40 Cover Seal (Part No: 09)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41407", "name": "SLR1-40 Pump Housing (CF-8M)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90484", "name": "3/4\" Kimyasal Vana (Kür. Vana + Elcik + Adaptör)", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91490", "name": "3/4 RD Vana Adaptör Bağlantı O-ringi", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91489", "name": "3/4' RD Vana Conta Takımı", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91488", "name": "3/4 RD Vana Küre", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "90930", "name": "EPDM Lastik Conta 25*40 Kare Oring", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91495", "name": "3/4\" Şeffaf Kimyasal Hortum", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "96404", "name": "RD96-MU22 Paslanmaz Çelik Tabla", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41406", "name": "RD96_MU33 PVC Tabla", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41405", "name": "RD96-MU33 Paslanmaz Çelik Tabla", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"}
]

INITIAL_REAL_SALES = [
    {"id": "SL-1", "firm": "INDIGO", "ref_no": "SATIS", "date": "17.03.2025", "timestamp": "2025-03-17", "status": "APPROVED", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 5}]},
    {"id": "SL-2", "firm": "WBM ANDIJON", "ref_no": "GARANTI", "date": "02.06.2025", "timestamp": "2025-06-02", "status": "APPROVED", "items": [{"code": "90840", "name": "PISTON SENSORU:DC73L", "qty": 1}]},
    {"id": "SL-3", "firm": "SAFF TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "timestamp": "2025-06-11", "status": "APPROVED", "items": [{"code": "90484", "name": "3/4\" KIMYASAL VANA", "qty": 3}]},
    {"id": "SL-4", "firm": "BEST COLOR", "ref_no": "SATIS", "date": "11.06.2025", "timestamp": "2025-06-11", "status": "APPROVED", "items": [{"code": "50289", "name": "VALF:SY3220-5LOU-M5-Q", "qty": 1}]},
    {"id": "SL-5", "firm": "CHUST TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "timestamp": "2025-06-11", "status": "APPROVED", "items": [{"code": "90620", "name": "PH SENSORU", "qty": 2}]},
    {"id": "SL-6", "firm": "PARVOZ HUMO (HAJJ TEKSTIL)", "ref_no": "SATIS", "date": "11.06.2025", "timestamp": "2025-06-11", "status": "APPROVED", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 6}]},
    {"id": "SL-7", "firm": "SOF MEGA TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "timestamp": "2025-06-11", "status": "APPROVED", "items": [{"code": "91332", "name": "FESTO BASINC ANAHTARI", "qty": 1}]},
    {"id": "SL-8", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "07.07.2025", "timestamp": "2025-07-07", "status": "APPROVED", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 2}]},
    {"id": "SL-9", "firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "15.07.2025", "timestamp": "2025-07-15", "status": "APPROVED", "items": [{"code": "50257", "name": "TEK ETLKILI PNOMATIK SILINDIR", "qty": 1}, {"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR", "qty": 2}]},
    {"id": "SL-10", "firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "05.10.2025", "timestamp": "2025-10-05", "status": "APPROVED", "items": [{"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR", "qty": 10}]},
    {"id": "SL-11", "firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "07.10.2025", "timestamp": "2025-10-07", "status": "APPROVED", "items": [{"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "qty": 1}]},
    {"id": "SL-12", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "09.10.2025", "timestamp": "2025-10-09", "status": "APPROVED", "items": [{"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "qty": 5}]},
    {"id": "SL-13", "firm": "BEST COLOR", "ref_no": "SATIS", "date": "18.10.2025", "timestamp": "2025-10-18", "status": "APPROVED", "items": [{"code": "50260", "name": "PISTON CD85N16-50-B", "qty": 2}]},
    {"id": "SL-14", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "25.10.2025", "timestamp": "2025-10-25", "status": "APPROVED", "items": [{"code": "90620", "name": "PH Sensörü: SPH-1-DJ-6M Ph Sensör", "qty": 2}]},
    {"id": "SL-15", "firm": "JIZZAX TEKSTIL", "ref_no": "SATIS", "date": "04.12.2025", "timestamp": "2025-12-04", "status": "APPROVED", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 4}]},
    {"id": "SL-16", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "20.12.2025", "timestamp": "2025-12-20", "status": "APPROVED", "items": [{"code": "91332", "name": "FESTO BASINC ANAHTARI", "qty": 1}]},
    {"id": "SL-17", "firm": "BIRYUZA TEKSTIL", "ref_no": "SATIS", "date": "09.02.2026", "timestamp": "2026-02-09", "status": "APPROVED", "items": [{"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "qty": 1}]},
    {"id": "SL-18", "firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "21.02.2026", "timestamp": "2026-02-21", "status": "APPROVED", "items": [{"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "qty": 1}]},
    {"id": "SL-19", "firm": "AKPAMUK TEKSTIL", "ref_no": "SATIS", "date": "26.03.2026", "timestamp": "2026-03-26", "status": "APPROVED", "items": [{"code": "5022", "name": "Salmastra", "qty": 1}]},
    {"id": "SL-20", "firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "01.04.2026", "timestamp": "2026-04-01", "status": "APPROVED", "items": [{"code": "50293", "name": "VALF:SYJ3243-5LOU-Q", "qty": 1}]},
    {"id": "SL-21", "firm": "BIRYUZA TEKSTIL", "ref_no": "SATIS", "date": "16.04.2026", "timestamp": "2026-04-16", "status": "APPROVED", "items": [{"code": "50260", "name": "PISTON CD85N16-50-B", "qty": 2}, {"code": "91086", "name": "PNOMATIK T RAKOR", "qty": 2}, {"code": "90765", "name": "RD96 CAMBAZ KOLU", "qty": 1}]},
    {"id": "SL-22", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "23.04.2026", "timestamp": "2026-04-23", "status": "APPROVED", "items": [{"code": "90881", "name": "DST CEKVALF YAYI", "qty": 2}, {"code": "90879", "name": "DST CEKVALF O-RINGI", "qty": 2}]},
    {"id": "SL-23", "firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "07.05.2026", "timestamp": "2026-05-07", "status": "APPROVED", "items": [{"code": "91277", "name": "RD96-Mu Polietilen Ağızlık", "qty": 1}, {"code": "50291", "name": "VALF:SYJ3240-5LOU-Q", "qty": 1}, {"code": "50289", "name": "VALF:SY3220-5LOU-M5-Q", "qty": 1}, {"code": "50287", "name": "VALF:SY114-5LOU-Q", "qty": 2}]},
    {"id": "SL-24", "firm": "AKPAMUK TEKSTIL", "ref_no": "SATIS", "date": "20.05.2026", "timestamp": "2026-05-20", "status": "APPROVED", "items": [{"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "qty": 1}]},
    {"id": "SL-25", "firm": "DAKA TEKSTIL", "ref_no": "SATIS", "date": "04.07.2026", "timestamp": "2026-07-04", "status": "APPROVED", "items": [{"code": "41316", "name": "Lab120 encoder", "qty": 1}]},
    {"id": "SL-26", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "06.07.2026", "timestamp": "2026-07-06", "status": "APPROVED", "items": [{"code": "90840", "name": "PISTON SENSORU:DC73L", "qty": 2}]},
    {"id": "SL-27", "firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "30.09.2026", "timestamp": "2026-09-30", "status": "APPROVED", "items": [{"code": "50018", "name": "VALF:SY5140-5YO-Q", "qty": 3}]},
    {"id": "SL-28", "firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "21.10.2026", "timestamp": "2026-10-21", "status": "APPROVED", "items": [{"code": "91594", "name": "VALF:SY5240-5YO-Q", "qty": 3}]},
    {"id": "SL-29", "firm": "TERRY JAR", "ref_no": "SATIS", "date": "21.10.2026", "timestamp": "2026-10-21", "status": "APPROVED", "items": [{"code": "90879", "name": "DST CEKVALF O-RINGI", "qty": 2}, {"code": "90881", "name": "DST CEKVALF YAYI", "qty": 2}, {"code": "91284", "name": "BONESSI VALF:P00112200", "qty": 2}]}
]

load_stocks = lambda: load_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, INITIAL_REAL_SALES)
save_sales = lambda d: save_data(SALES_FILE, d)
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_quotes = lambda d: save_data(QUOTES_FILE, d)

# ----------------- 5. GÖRSEL VE ARAMA MOTORU -----------------
def get_catalog_pdf_file():
    for name in ["Katalog.pdf", "katalog.pdf", "CATALOG.PDF", "catalog.pdf", "rd96.pdf", "RD96.pdf"]:
        if os.path.exists(name): return name
    for root, dirs, files in os.walk("."):
        for fn in files:
            lower = fn.lower()
            if lower.endswith(".pdf") and ("katalog" in lower or "catalog" in lower or "rd96" in lower):
                return os.path.join(root, fn)
    return None

def crop_slot_from_page(page, slot: int) -> bytes:
    pw, ph = page.rect.width, page.rect.height
    col = 0 if slot in [1, 3, 5] else 1
    row = 0 if slot in [1, 2] else (1 if slot in [3, 4] else 2)

    x0 = 8 if col == 0 else (pw / 2 + 1)
    x1 = (pw / 2 - 1) if col == 0 else (pw - 8)
    top_offset = 12
    bottom_offset = 24
    avail_h = ph - top_offset - bottom_offset
    row_h = avail_h / 3.0

    y0 = max(0, top_offset + row * row_h - 4)
    y1 = min(ph, y0 + row_h + 8)

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
    code_str = str(code).strip()

    try:
        import fitz
        doc = fitz.open(pdf_path)

        if code_str in CATALOG_GRID_MAP:
            page_no, slot = CATALOG_GRID_MAP[code_str]
            p_idx = page_no - 1
            if 0 <= p_idx < len(doc):
                img = crop_slot_from_page(doc[p_idx], slot)
                if img: return img

        for p_idx, page in enumerate(doc):
            rects = page.search_for(code_str) or page.search_for(f"({code_str})")
            if rects:
                r = rects[0]
                pw, ph = page.rect.width, page.rect.height
                col = 0 if r.x0 < (pw / 2) else 1
                row = 0 if r.y0 < (ph / 3) else (1 if r.y0 < (2 * ph / 3) else 2)
                return crop_slot_from_page(page, (row * 2) + col + 1)

        return None
    except Exception as e:
        logging.error(f"Görsel çıkarma hatası: {e}")
        return None

def calculate_similarity(query: str, part: dict) -> float:
    q_norm = normalize_tr(query.strip())
    name_norm = normalize_tr(part["name"])
    code_norm = normalize_tr(part["code"])

    if q_norm == code_norm: return 1.0
    if q_norm in code_norm: return 0.96
    if q_norm in name_norm: return 0.90

    q_words, name_words = q_norm.split(), name_norm.split()
    matched_words = sum(1 for qw in q_words if any(qw in nw for nw in name_words))
    word_ratio = matched_words / len(q_words) if q_words else 0.0
    seq_ratio = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
    return max(word_ratio * 0.85, seq_ratio)

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = []
    for p in stocks:
        score = calculate_similarity(query, p)
        if score > 0.25: scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

async def notify_both(text: str, reply_markup=None, photo_file=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try:
            if photo_file:
                await bot.send_photo(chat_id=cid, photo=photo_file, caption=text, parse_mode="HTML", reply_markup=reply_markup)
            else:
                await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Bildirim iletilemedi ({cid}): {e}")

async def parse_quote_pdf_with_gemini(pdf_path: str) -> dict:
    pdf_bytes = b""
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        logging.error(f"PDF okuma hatası: {e}")

    extracted_text = ""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for p in doc: extracted_text += p.get_text() + "\n"
    except Exception: pass

    prompt = (
        "Sen profesyonel bir depo ve muhasebe asistanısın. Ekteki fiyat teklifi belgesini analiz et.\n"
        "Aşağıdaki bilgileri eksiksiz tespit edip YALNIZCA SAF JSON formatında döndür (Markdown ```json etiketi KULLANMA):\n"
        "{\n"
        '  "firm": "Müşteri / Fabrika Adı",\n'
        '  "date": "GG.AA.YYYY",\n'
        '  "currency": "EUR veya USD veya TL",\n'
        '  "grand_total": "1250.00",\n'
        '  "items": [\n'
        '    {"code": "90880", "name": "Ürün Adı", "qty": 2, "unit_price": "50", "total_price": "100"}\n'
        '  ]\n'
        "}\n\n"
        "Kurallar:\n"
        "- Müşteri firma adını bul (Örn: ZELAL TEKSTIL, TERRY JAR, ASAKA TEKSTIL vb.). Eğer satıcı Eliar ise teklif verilen muhatap firmayı al.\n"
        "- Her bir ürün kaleminin kodunu (varsa), adını, adedini (tam sayı) ve fiyatını çıkar.\n"
        "- Para birimini ve genel toplamı bul."
    )

    if ai_client and pdf_bytes and HAS_GENAI:
        try:
            pdf_part = genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            contents_payload = [pdf_part, prompt]
        except Exception:
            contents_payload = [f"{prompt}\n\nTeklif Metni:\n{extracted_text[:5000]}"]

        for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(
                    None,
                    lambda m=model_name: ai_client.models.generate_content(
                        model=m,
                        contents=contents_payload
                    )
                )
                raw = res.text.strip()
                raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
                raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
                parsed = json.loads(raw)
                if parsed.get("firm") and parsed.get("items"):
                    logging.info(f"✅ Gemini ({model_name}) ile PDF okundu: {parsed.get('firm')}")
                    return parsed
            except Exception as e:
                logging.warning(f"Gemini {model_name} denemesi: {e}")

    firm_match = re.search(r"(?:Sayın|Müşteri|Firma|Tesis|Sayin|Company)[\s:]+([^\n\r]+)", extracted_text, re.IGNORECASE)
    detected_firm = firm_match.group(1).strip() if firm_match else "BİLİNMEYEN FİRMA"

    cur = "EUR"
    if "USD" in extracted_text or "$" in extracted_text: cur = "USD"
    elif "TL" in extracted_text or "TRY" in extracted_text: cur = "TL"

    tot_match = re.search(r"(?:Genel Toplam|Grand Total|Toplam|Total)[\s:]*([0-9.,]+)", extracted_text, re.IGNORECASE)
    grand_total = tot_match.group(1).strip() if tot_match else "-"

    detected_items = []
    lines = [l.strip() for l in extracted_text.split("\n") if l.strip()]
    for line in lines:
        code_match = re.search(r"\b(\d{4,6})\b", line)
        if code_match:
            c = code_match.group(1)
            detected_items.append({"code": c, "name": line[:40], "qty": 1, "unit_price": "-", "total_price": "-"})

    if not detected_items:
        detected_items = [{"code": "GENEL", "name": "PDF Teklif Kalemleri", "qty": 1, "unit_price": "-", "total_price": "-"}]

    return {
        "firm": detected_firm[:30].upper(),
        "date": datetime.now().strftime("%d.%m.%Y"),
        "currency": cur,
        "grand_total": grand_total,
        "items": detected_items[:15]
    }

def generate_excel_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_{title}_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satislar"
        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet"]
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
            for item in sale.get("items", []):
                ws.append([cnt, str(sale.get("date", "")), str(sale.get("ref_no", "YOK")), str(sale.get("firm", "")),
                           item.get("code", ""), item.get("name", ""), item.get("qty", 1)])
                for c in range(1, len(headers) + 1): ws.cell(row=row, column=c).border = border
                row += 1; cnt += 1
        for idx, w in enumerate([8, 18, 14, 25, 16, 40, 10], 1):
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
            Paragraph("ELİPS DEPO PARÇA SATIŞ RAPORU", t_style),
            Paragraph(f"DÖKÜM TARİHİ: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_style)
        ]
        data = [["Sıra", "Tarih", "Ref No", "Müşteri / Tesis", "Ürün Kodu", "Ürün Adı", "Adet"]]
        cnt, total = 1, 0
        for sale in sales_data:
            ref = str(sale.get("ref_no", "YOK"))
            firm = str(sale.get("firm", ""))[:22]
            date = str(sale.get("date", "")).split()[0]
            for itm in sale.get("items", []):
                q = int(itm.get("qty", 1))
                total += q
                data.append([str(cnt), date, ref, firm, str(itm.get("code", "")), str(itm.get("name", ""))[:28], str(q)])
                cnt += 1
        data.append(["TOPLAM", "", "", "", "", "Toplam Adet:", str(total)])
        table = Table(data, colWidths=[30, 65, 60, 130, 80, 150, 50], repeatRows=1)
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

def filter_sales_by_range(start_dt: datetime, end_dt: datetime):
    sales = load_sales()
    res = []
    for s in sales:
        if s.get("status") != "APPROVED": continue
        try:
            ts = s.get("timestamp")
            d = datetime.fromisoformat(ts) if ts else datetime.strptime(s.get("date", "").split()[0], "%d.%m.%Y")
            if start_dt <= d <= end_dt: res.append(s)
        except Exception: res.append(s)
    return res

def build_report_text(sales_data, report_name="SATIŞ Z-RAPORU"):
    now = datetime.now()
    if not sales_data:
        return f"📊 <b>ELİPS DEPO {report_name}</b>\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\nℹ️ Kayıt bulunamadı."
    text = f"📊 <b>ELİPS DEPO {report_name}</b>\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\n\n"
    total_qty, plants, cnt = 0, set(), 1
    for sale in sales_data:
        plants.add(sale.get("firm", ""))
        for itm in sale.get("items", []):
            q = int(itm.get("qty", 1))
            total_qty += q
            text += f"<b>{cnt}.</b> <code>[{itm.get('code')}]</code> {html.escape(itm.get('name', ''))}\n   └ Miktar: <b>{q} Adet</b> | Tesis: <b>{html.escape(sale.get('firm', ''))}</b>\n\n"
            cnt += 1
    text += f"───────────────────────────────\n📦 Toplam Satış: <b>{total_qty} Adet</b> | Tesis: <b>{len(plants)}</b>\n📂 Format seçin:"
    return text

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

    if not scored: return f"🔍 <code>{html.escape(firm_query)}</code> için onaylı geçmiş hareket bulunamadı."
    scored.sort(key=lambda x: x[1], reverse=True)
    best_firm = scored[0][0].get("firm")
    firm_records = [s for s, _ in scored if s.get("firm") == best_firm]

    text = f"🏢 <b>{html.escape(best_firm)} — PARÇA GEÇMİŞİ</b>\n═══════════════════════════════\n\n"
    for item in firm_records:
        for itm in item.get("items", []):
            text += f"• 📅 <code>{item.get('date', '')}</code> ➔ <b>{itm.get('qty')}x</b> <code>[{itm.get('code')}]</code> ({html.escape(itm.get('name', ''))})\n"
    text += f"\n═══════════════════════════════\n✅ Toplam: <b>{len(firm_records)} Sevkiyat / Hareket</b>"
    return text

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Elips Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla"), KeyboardButton(text="📦 Parça Listesi")],
            [KeyboardButton(text="📊 Z-Raporu Al"), KeyboardButton(text="📅 Tarihli Rapor Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="✅ Tamamlanmış Teklifler")],
            [KeyboardButton(text="📂 Verilen Teklifler"), KeyboardButton(text="🏢 Tesis Geçmişi")],
            [KeyboardButton(text="📖 Kataloğu Gönder")]
        ],
        resize_keyboard=True
    )

# ----------------- 6. NİLAY HANIM'A TEKLİF SİHİRBAZI -----------------
@dp.message(Command("teklif", ignore_mention=True))
@dp.message(F.text == "📝 Nilay Hanım'a Teklif Hazırla")
async def start_quote_wizard(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteBuilderState.waiting_firm)
    await message.answer("🏢 <b>Teklif hangi müşteri / fabrika için hazırlanacak?</b>\n(Örnek: <code>MARK FORMELLE</code>, <code>TERRY JAR</code>)", parse_mode="HTML")

# ADIM 1: FİRMA ALINDI, SADECE PARÇA SORULUR (BUTON KALABALIĞI YOK)
@dp.message(QuoteBuilderState.waiting_firm)
async def process_quote_firm(message: types.Message, state: FSMContext):
    firm = message.text.strip().upper()
    await state.update_data(firm_name=firm)
    await state.set_state(QuoteBuilderState.waiting_item_query)

    await message.answer(
        f"🔍 <b>Hangi parça için teklif istenecek?</b>\n\n"
        f"Lütfen parçanın <b>kodunu</b> veya <b>ismini</b> yazın:\n"
        f"<i>(Örn: 90880, diyafram, motor, teflon...)</i>",
        parse_mode="HTML"
    )

# ADIM 2: KULLANICI YAZINCA DEPO & KATALOGDA ARAMA
@dp.message(QuoteBuilderState.waiting_item_query)
async def process_quote_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    matches = find_best_matches(query)

    # PARÇA BULUNAMADIYSA: İŞTE O ZAMAN SEÇENEKLER ÇIKAR!
    if not matches:
        await state.update_data(pending_query=query)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Kodu ve İsmi Biliyorum (Kendim Yazacağım)", callback_data="qb_manual")],
            [InlineKeyboardButton(text="❓ Bilmiyorum (Tekniğe Sor & Fotoğraf Gönder)", callback_data="qb_ask_tech")],
            [InlineKeyboardButton(text="🔍 Tekrar Ara", callback_data="qb_retry_search")]
        ])
        await message.answer(
            f"⚠️ <code>{html.escape(query)}</code> yerel depomuzda veya katalogda bulunamadı.\n\n"
            f"Lütfen seçiminizi yapın:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    top_part, score = matches[0]
    # Tam kod eşleşmesi varsa direkt görselle kaynağı sor
    if normalize_tr(query) == normalize_tr(top_part['code']) or score >= 0.94:
        await prompt_part_selection(message, top_part, state)
        return

    # Eşleşenleri listele
    await state.update_data(search_matches=matches, search_query=query)
    text, kb = render_search_results_page(matches, 0, query)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

def render_search_results_page(matches, page_idx, query):
    page_size = 5
    total_pages = (len(matches) + page_size - 1) // page_size
    page_idx = max(0, min(page_idx, total_pages - 1))
    current_items = matches[page_idx * page_size : (page_idx + 1) * page_size]

    buttons = []
    for p, _ in current_items:
        st_text = f"🟢 {p.get('qty',0)} ADT" if p.get('qty',0) > 0 else "🔴 0 ADT"
        buttons.append([InlineKeyboardButton(text=f"👉 [{p['code']}] {p['name'][:24]} ({st_text})", callback_data=f"qbsel:{p['code']}")])

    nav_row = []
    if page_idx > 0: nav_row.append(InlineKeyboardButton(text="⬅️ Önceki", callback_data=f"qbpage:{page_idx-1}"))
    if page_idx < total_pages - 1: nav_row.append(InlineKeyboardButton(text="Sonraki ➡️", callback_data=f"qbpage:{page_idx+1}"))
    if nav_row: buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="✍️ Aradığım Yok (Manuel Yaz)", callback_data="qb_manual"),
        InlineKeyboardButton(text="❓ Bilmiyorum (Tekniğe Sor)", callback_data="qb_ask_tech")
    ])

    text = f"🔍 <b>Arama Sonuçları:</b> <code>{html.escape(query)}</code>\nSeçmek istediğiniz parçaya tıklayın:"
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

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

# ADIM 3: PARÇA SEÇİLDİĞİNDE GÖRSELİ AT VE TEDARİK KAYNAĞI SOR
async def prompt_part_selection(target, part: dict, state: FSMContext):
    await state.update_data(selected_part=part)
    await state.set_state(QuoteBuilderState.waiting_supply_source)

    img_bytes = extract_part_image_from_pdf(part["code"], part.get("name", ""))
    if img_bytes:
        photo = BufferedInputFile(img_bytes, filename=f"{part['code']}.png")
        cap = f"📸 <b>Katalog Görseli:</b> <code>[{part['code']}]</code> — {html.escape(part['name'])}"
        if isinstance(target, types.CallbackQuery):
            await target.message.answer_photo(photo, caption=cap, parse_mode="HTML")
        else:
            await target.answer_photo(photo, caption=cap, parse_mode="HTML")

    has_stock = part.get("qty", 0) > 0
    stock_badge = f"🟢 <b>Depoda Var: {part.get('qty', 0)} ADT</b>" if has_stock else "🔴 <b>Depoda Yok: 0 ADT</b>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Elips Depodan Gidecek", callback_data="qbsource:ELIPS")],
        [InlineKeyboardButton(text="🇹🇷 TR'den Gelecek", callback_data="qbsource:TR")]
    ])

    msg_text = (
        f"🎯 <b>Seçilen Parça:</b> <code>[{part['code']}]</code> {html.escape(part['name'])}\n"
        f"📊 {stock_badge}\n\n"
        f"❓ <b>Bu parça nereden tedarik edilecek?</b>\n"
        f"<i>(Elips Depodan derseniz onaylanınca depodan düşer; TR derseniz depo stoğuna dokunulmaz)</i>"
    )
    if isinstance(target, types.CallbackQuery):
        await target.message.answer(msg_text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.answer(msg_text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("qbsel:"))
async def on_quote_part_selected(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]
    stocks = load_stocks()
    part = next((p for p in stocks if p["code"].lower() == code.lower()), None)
    if not part:
        await callback.answer("Parça bulunamadı.", show_alert=True)
        return
    await prompt_part_selection(callback, part, state)
    await callback.answer()

# MANUEL YAZMA
@dp.callback_query(F.data == "qb_manual")
async def on_quote_manual_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_custom_manual)
    await callback.message.edit_text(
        "✍️ <b>Parçanın Kodunu ve İsmini Yazın:</b>\n\n"
        "<i>Örnek:</i> <code>91999 - Dozaj Pompası Diyaframı</code>\n"
        "<i>Veya:</i> <code>Sıcaklık Sensörü 0-100C</code>\n\n"
        "<i>(Katalogda olmadığı için resmi olmayacaktır)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_custom_manual)
async def process_quote_manual_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Lütfen geçerli bir parça bilgisi yazın.")
        return

    parts = re.split(r"[-–—:]", text, maxsplit=1)
    if len(parts) == 2 and (parts[0].strip().isalnum() or len(parts[0].strip()) <= 10):
        code = parts[0].strip().upper()
        name = parts[1].strip()
    else:
        if text.replace(" ", "").isalnum() and len(text) <= 8 and any(c.isdigit() for c in text):
            code = text.upper()
            name = f"Özel Parça [{code}]"
        else:
            code = "ÖZEL"
            name = text

    selected_part = {"code": code, "name": name, "qty": 0, "is_manual": True}
    await state.update_data(selected_part=selected_part)
    await state.set_state(QuoteBuilderState.waiting_supply_source)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 TR'den Gelecek", callback_data="qbsource:TR")],
        [InlineKeyboardButton(text="🇺🇿 Elips Depodan Gidecek", callback_data="qbsource:ELIPS")]
    ])
    await message.answer(
        f"🎯 <b>Parça:</b> <code>[{code}]</code> {html.escape(name)}\n\n"
        f"❓ <b>Bu parça nereden tedarik edilecek?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

# TEKNİĞE SOR & FOTOĞRAF GÖNDER
@dp.callback_query(F.data == "qb_ask_tech")
async def on_quote_ask_tech_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_ask_technic_input)
    await callback.message.edit_text(
        "❓ <b>Tekniğe Sor & Fotoğraf Gönder</b>\n\n"
        "📸 Parçanın <b>fotoğrafını çekip gönderin</b> veya parça/makine açıklamasını yazın:",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_ask_technic_input, F.photo)
async def process_quote_tech_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    caption = message.caption or "Fotoğraflı Parça (Teknik İnceleme)"
    selected_part = {
        "code": "TEKNIK",
        "name": caption,
        "qty": 0,
        "photo_id": photo_id,
        "is_tech": True
    }
    await state.update_data(selected_part=selected_part)
    await state.set_state(QuoteBuilderState.waiting_supply_source)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 TR'den Gelecek", callback_data="qbsource:TR")],
        [InlineKeyboardButton(text="🇺🇿 Elips Depodan Gidecek", callback_data="qbsource:ELIPS")]
    ])
    await message.answer(
        f"📸 <b>Fotoğraf Alındı!</b>\nAçıklama: <i>{html.escape(caption)}</i>\n\n"
        f"❓ <b>Bu parça nereden tedarik edilecek?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.message(QuoteBuilderState.waiting_ask_technic_input, F.text)
async def process_quote_tech_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    selected_part = {
        "code": "TEKNIK",
        "name": f"{text} (Teknik İnceleme)",
        "qty": 0,
        "is_tech": True
    }
    await state.update_data(selected_part=selected_part)
    await state.set_state(QuoteBuilderState.waiting_supply_source)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 TR'den Gelecek", callback_data="qbsource:TR")],
        [InlineKeyboardButton(text="🇺🇿 Elips Depodan Gidecek", callback_data="qbsource:ELIPS")]
    ])
    await message.answer(
        f"❓ <b>Teknik Tarif:</b> <i>{html.escape(text)}</i>\n\n"
        f"❓ <b>Bu parça nereden tedarik edilecek?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

# TEDARİK KAYNAĞI SEÇİMİ
@dp.callback_query(F.data.startswith("qbsource:"))
async def on_supply_source_selected(callback: types.CallbackQuery, state: FSMContext):
    source = callback.data.split(":")[1]
    data = await state.get_data()
    part = data.get("selected_part", {})

    source_label = "Elips Depodan" if source == "ELIPS" else "TR'den"
    part["supply_source"] = source
    part["source_label"] = source_label
    await state.update_data(selected_part=part)
    await state.set_state(QuoteBuilderState.waiting_qty)

    await callback.message.edit_text(
        f"📍 <b>Tedarik:</b> <b>{source_label}</b>\n"
        f"⚙️ <code>[{part.get('code')}]</code> {html.escape(part.get('name'))}\n\n"
        f"🔢 Kaç <b>adet</b> teklif istenecek?",
        parse_mode="HTML"
    )
    await callback.answer()

# ADET GİRİŞİ
@dp.message(QuoteBuilderState.waiting_qty)
async def process_quote_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("⚠️ Lütfen geçerli bir sayı girin (Örn: 1, 2):", parse_mode="HTML")
        return

    data = await state.get_data()
    part = data.get("selected_part", {})
    items = data.get("quote_items", [])

    items.append({
        "code": part.get("code", "KODSUZ"),
        "name": part.get("name", "Ürün"),
        "supply_source": part.get("supply_source", "ELIPS"),
        "source_label": part.get("source_label", "Elips Depodan"),
        "photo_id": part.get("photo_id"),
        "qty": qty
    })
    await state.update_data(quote_items=items)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="qb_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir", callback_data="qb_done")]
    ])
    await state.set_state(QuoteBuilderState.confirm_more)
    await message.answer(
        f"✅ <b>{qty} Adet</b> <code>[{part.get('code')}]</code> ({part.get('source_label')}) eklendi!\nNe yapmak istersiniz?",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "qb_more")
async def on_quote_add_more(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Yeni parçanın <b>kodunu</b> veya <b>ismini</b> yazın:")
    await callback.answer()

# TEKLİF BİTİRME VE NİLAY HANIM'A METİN HAZIRLAMA
@dp.callback_query(F.data == "qb_done")
async def on_quote_completed(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    firm = html.escape(data.get("firm_name", "MÜŞTERİ"))
    items = data.get("quote_items", [])
    if not items:
        await callback.message.edit_text("⚠️ Teklifte ürün yok.")
        await state.clear()
        return

    sender_name = "Ömer" if callback.from_user.id == OMER_CHAT_ID else "Kamil"

    formatted_quote = (
        f"Merhaba Nilay Hanım,\n\n"
        f"{firm} için aşağıdaki listedeki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    )
    for itm in items:
        source_str = "Elips Depodan" if itm.get('supply_source') == "ELIPS" else "TR'den"
        formatted_quote += f"• [{itm['code']}] {itm['name']} - {itm['qty']} Adet (Tedarik: {source_str})\n"
    formatted_quote += "\nİyi çalışmalar."

    quotes = load_quotes()
    quote_id = f"TK-{int(time.time())}"
    quotes.append({
        "id": quote_id,
        "firm": firm,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING",
        "items": items,
        "pdf_file": None,
        "creator": sender_name
    })
    save_quotes(quotes)

    text = (
        f"📋 <b>KOPYALAMAYA HAZIR TEKLİF METNİ:</b>\n"
        f"═══════════════════════════════\n\n"
        f"{formatted_quote}\n\n"
        f"═══════════════════════════════\n"
        f"💡 <i>Metne basılı tutarak doğrudan Nilay Hanım'a iletebilirsiniz.</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")

    notify_text = (
        f"📥 <b>YENİ TEKLİF TALEBİ HAZIRLANDI!</b>\n"
        f"👤 <b>Hazırlayan:</b> {sender_name}\n"
        f"🏢 <b>Firma:</b> {firm}\n"
        f"📦 <b>Parçalar:</b>\n" +
        "\n".join([f"• [{i['code']}] {i['name']} ({i['qty']} Adet - {i.get('source_label')})" for i in items])
    )
    await notify_both(notify_text)

    for itm in items:
        if itm.get("photo_id"):
            for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
                try:
                    await bot.send_photo(chat_id=cid, photo=itm["photo_id"], caption=f"📸 <b>Teknik Parça Fotoğrafı ({firm}):</b>\n<code>[{itm['code']}]</code> {itm['name']}", parse_mode="HTML")
                except Exception: pass

    await state.clear()
    await callback.answer("Teklif kaydedildi!")

# ----------------- 7. SERVER VE MAIN ÇALIŞTIRICISI -----------------
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
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logging.info(f"✅ Render web server {port} portunda baslatildi.")
    except Exception as e:
        logging.warning(f"Server baslatilamadi: {e}")

async def main():
    try:
        init_flag = ".init_done_v16"
        if not os.path.exists(init_flag):
            save_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
            save_data(SALES_FILE, INITIAL_REAL_SALES)
            try:
                with open(init_flag, "w") as f: f.write("ok")
            except Exception: pass

        await bot.delete_webhook(drop_pending_updates=True)

        # Doğrudan main içinde kuruluyor, NameError olması imkansız
        await bot.set_my_commands([
            BotCommand(command="start", description="Başlat / Ana Menü"),
            BotCommand(command="teklif", description="Nilay Hanım'a Teklif Hazırla"),
            BotCommand(command="stok", description="Parça Listesi"),
            BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
            BotCommand(command="tamamlananlar", description="Tamamlanmış Teklifler"),
            BotCommand(command="verilenler", description="Tüm Verilen Teklifler"),
            BotCommand(command="zraporu", description="Haftalık Z-Raporu"),
            BotCommand(command="gecmis", description="Tesis Geçmişi"),
            BotCommand(command="katalog", description="Katalog PDF İndir")
        ])

        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        logging.info(">>> ELIPS DEPO BOTU AKTIF VE CALISIYOR <<<")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Kritik hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
