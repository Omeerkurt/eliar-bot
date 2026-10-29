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

# ----------------- 1. FSM DURUMLARI -----------------
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

# ----------------- 2. TEMEL YARDIMCI VE DOSYA İŞLEMLERİ -----------------
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

# ----------------- PDF YÜKLEME VE TEKLİF YÖNETİMİ -----------------
@dp.message(F.document)
async def handle_document_upload(message: types.Message):
    doc = message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await message.answer("⚠️ Lütfen PDF formatında bir teklif dosyası yükleyin.")
        return

    sender_name = "Ömer" if message.from_user.id == OMER_CHAT_ID else "Kamil"
    wait_msg = await message.answer("⏳ <i>PDF belgesi taranıyor ve yapay zeka ile analiz ediliyor...</i>", parse_mode="HTML")
    saved_filename = f"{int(time.time())}_{doc.file_name}"
    save_path = os.path.join(PDF_STORAGE_DIR, saved_filename)
    await bot.download(doc, destination=save_path)

    parsed_data = await parse_quote_pdf_with_gemini(save_path)
    firm = parsed_data.get("firm", "BİLİNMEYEN FİRMA").upper()
    date = parsed_data.get("date", datetime.now().strftime("%d.%m.%Y"))
    currency = parsed_data.get("currency", "EUR")
    grand_total = parsed_data.get("grand_total", "-")
    items = parsed_data.get("items", [])

    quote_id = f"TK-{int(time.time())}"
    quotes = load_quotes()
    new_quote = {
        "id": quote_id, "firm": firm, "date": date, "currency": currency,
        "grand_total": grand_total, "status": "PENDING", "items": items, "pdf_file": save_path, "creator": sender_name
    }
    quotes.append(new_quote)
    save_quotes(quotes)

    lines = [f"🏢 <b>Firma:</b> {html.escape(firm)}", f"📅 <b>Tarih:</b> {date}", f"👤 <b>Yükleyen:</b> {sender_name}"]
    lines.append("\n📦 <b>Algılanan Teklif Kalemleri:</b>")
    for idx, itm in enumerate(items, 1):
        lines.append(f"<b>{idx}.</b> <code>[{itm.get('code','-')}]</code> {html.escape(itm.get('name','Ürün'))} | Adet: <b>{itm.get('qty',1)}</b>")

    lines.append(f"\n💰 <b>Genel Toplam:</b> <b>{grand_total} {currency}</b>\nLütfen teklifin durumunu seçin:")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Onayla", callback_data=f"qstat:{quote_id}:APPROVED"),
         InlineKeyboardButton(text="❌ Reddet", callback_data=f"qstat:{quote_id}:REJECTED")],
        [InlineKeyboardButton(text="🗑️ Teklifi Sil", callback_data=f"qdel:{quote_id}")]
    ])
    await wait_msg.delete()
    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")

    other_notify = f"📄 <b>Yeni Teklif PDF'i Yüklendi!</b>\n👤 Yükleyen: <b>{sender_name}</b>\n🏢 Firma: <b>{firm}</b>\n💰 Tutar: <b>{grand_total} {currency}</b>"
    target_id = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else OMER_CHAT_ID
    try: await bot.send_message(chat_id=target_id, text=other_notify, parse_mode="HTML")
    except Exception: pass

# ----------------- TEKLİF SİLME -----------------
@dp.callback_query(F.data.startswith("qdel:"))
async def on_quote_delete(callback: types.CallbackQuery):
    quote_id = callback.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif zaten silinmiş veya bulunamadı.", show_alert=True)
        return

    if q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        try: os.remove(q["pdf_file"])
        except Exception: pass

    quotes = [x for x in quotes if x["id"] != quote_id]
    save_quotes(quotes)

    del_by = "Ömer" if callback.from_user.id == OMER_CHAT_ID else "Kamil"
    await callback.message.edit_text(f"🗑️ <b>{html.escape(q['firm'])}</b> teklifi başarıyla silindi.", parse_mode="HTML")
    await callback.answer("Teklif silindi.")
    await notify_both(f"🗑️ <b>Bir Teklif Silindi!</b>\n🏢 Firma: <code>{html.escape(q['firm'])}</code>\n👤 Silen: <b>{del_by}</b>")

# ----------------- TEKLİF ONAY & AKILLI STOK DÜŞÜŞÜ (SADECE ELİPS OLANLAR) -----------------
@dp.callback_query(F.data.startswith("qstat:"))
async def on_quote_status_change(callback: types.CallbackQuery):
    _, quote_id, new_status = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif bulunamadı.", show_alert=True)
        return

    if new_status == "APPROVED":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Evet, Elips Depodan Düş", callback_data=f"qdeduct:{quote_id}:yes")],
            [InlineKeyboardButton(text="❌ Hayır, Sadece Durumu Onayla", callback_data=f"qdeduct:{quote_id}:no")]
        ])
        await callback.message.answer(
            f"⚠️ <b>{html.escape(q['firm'])}</b> teklifini onaylıyorsunuz.\n\n"
            f"Bu teklifteki <b>Elips Depo</b> etiketli parçalar depodan düşülsün mü?\n"
            f"<i>(TR'den gelecek parçaların stoğu korunur)</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    q["status"] = new_status
    save_quotes(quotes)
    st_text = "Reddedildi" if new_status == "REJECTED" else "Beklemede"
    await callback.message.answer(f"ℹ️ <b>{html.escape(q['firm'])}</b> teklif durumu: <b>{st_text}</b>", parse_mode="HTML")
    await callback.answer("Durum güncellendi.")

@dp.callback_query(F.data.startswith("qdeduct:"))
async def on_quote_deduct_confirm(callback: types.CallbackQuery):
    _, quote_id, choice = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif bulunamadı.", show_alert=True)
        return

    q["status"] = "APPROVED"
    save_quotes(quotes)
    action_by = "Ömer" if callback.from_user.id == OMER_CHAT_ID else "Kamil"

    if choice == "yes" and q.get("items"):
        stocks = load_stocks()
        sales = load_sales()
        deducted_info = []

        for item in q["items"]:
            source = item.get("supply_source", "ELIPS")
            code = item.get("code", "")
            try: qty = int(item.get("qty", 1))
            except Exception: qty = 1

            if source == "TR":
                deducted_info.append(f"• <code>[{code}]</code> {item.get('name')}: <b>🇹🇷 TR'den sevk edilecek (Depo stoğuna dokunulmadı)</b>")
                continue

            p = next((s for s in stocks if s["code"].lower() == code.lower()), None)
            if not p: p = next((s for s in stocks if normalize_tr(s["name"]) in normalize_tr(item.get("name", ""))), None)
            if p:
                p["qty"] = max(0, p.get("qty", 0) - qty)
                deducted_info.append(f"• <code>[{p['code']}]</code> {p['name']}: <b>-{qty} Adet</b> (Elips Depoda Kalan: {p['qty']})")
            else:
                deducted_info.append(f"• <code>[{code}]</code> {item.get('name')}: <b>Elips Depo kaydı yok (-{qty} Adet)</b>")

        save_stocks(stocks)
        sales.append({
            "id": f"SLS-{int(time.time())}", "firm": q["firm"], "ref_no": "TEKLIF-ONAY",
            "items": q["items"], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        msg = (
            f"📦 <b>ELİPS DEPO - STOKTAN DÜŞÜM TAMAMLANDI!</b>\n"
            f"👤 Onaylayan: <b>{action_by}</b>\n"
            f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n\n" +
            ("\n".join(deducted_info) if deducted_info else "ℹ️ Stok adedi bulunamadı.")
        )
        await notify_both(msg)
        await callback.message.edit_text("✅ <b>Teklif Onaylandı ve Elips Depo Stoğundan Düşüldü!</b>", parse_mode="HTML")
    else:
        await callback.message.edit_text("✅ <b>Teklif Onaylandı (Stoklar değiştirilmedi).</b>", parse_mode="HTML")
        await notify_both(f"✅ <b>Teklif Onaylandı</b>\n🏢 Firma: <b>{html.escape(q['firm'])}</b>\n👤 İşlem Yapan: <b>{action_by}</b>")
    await callback.answer()

# ----------------- BEKLEYEN, TAMAMLANMIŞ VE VERİLEN TEKLİFLER -----------------
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
        buttons.append([
            InlineKeyboardButton(text=f"⏳ {q['firm']} ({q.get('date', '')[:10]})", callback_data=f"qview:{q['id']}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"qdel:{q['id']}")
        ])
    await message.answer("⏳ <b>BEKLEYEN TEKLİFLER:</b>\nİncelemek istediğinize tıklayın:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.message(Command("tamamlananlar"))
@dp.message(F.text == "✅ Tamamlanmış Teklifler")
async def show_approved_quotes(message: types.Message):
    quotes = load_quotes()
    approved = [q for q in quotes if q.get("status") == "APPROVED"]
    if not approved:
        await message.answer("ℹ️ Henüz tamamlanmış (onaylı) bir teklif bulunmamaktadır.", parse_mode="HTML")
        return
    buttons = []
    for q in reversed(approved[-12:]):
        buttons.append([
            InlineKeyboardButton(text=f"✅ {q['firm']} ({q.get('date', '')[:10]})", callback_data=f"qview:{q['id']}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"qdel:{q['id']}")
        ])
    await message.answer("✅ <b>TAMAMLANMIŞ (ONAYLI) TEKLİFLER:</b>\nİncelemek istediğinize tıklayın:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

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
        buttons.append([
            InlineKeyboardButton(text=f"{st_icon} {q['firm']} ({q.get('date', '')[:10]})", callback_data=f"qview:{q['id']}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"qdel:{q['id']}")
        ])
    await message.answer("📂 <b>TÜM VERİLEN TEKLİFLER:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

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
        f"📄 <b>Teklif Kartı</b>",
        f"🏢 Firma: <b>{html.escape(q['firm'])}</b>",
        f"📅 Tarih: <code>{q.get('date')}</code>",
        f"📊 Durum: <b>{cur_st}</b>",
        f"💰 Toplam: <b>{q.get('grand_total', '-')} {cur}</b>\n",
        "📦 <b>Parçalar:</b>"
    ]
    for idx, itm in enumerate(q.get("items", []), 1):
        source_badge = "Elips Depodan" if itm.get('supply_source') == "ELIPS" else "TR'den"
        lines.append(f"{idx}. <code>[{itm.get('code')}]</code> {itm.get('name')} — {itm.get('qty')} Adet (<i>{source_badge}</i>)")

    buttons = [
        [InlineKeyboardButton(text="✅ Onayla", callback_data=f"qstat:{quote_id}:APPROVED"),
         InlineKeyboardButton(text="❌ Reddet", callback_data=f"qstat:{quote_id}:REJECTED")],
        [InlineKeyboardButton(text="🗑️ Bu Teklifi Sil", callback_data=f"qdel:{quote_id}")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        await callback.message.answer_document(FSInputFile(q["pdf_file"]), caption="\n".join(lines), reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")
    await callback.answer()

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
        text += f"\n<i>...ve {len(available)-15} kalem ürün daha (Mini App'ten inceleyebilirsiniz).</i>"
    await message.answer(text, parse_mode="HTML")

# ----------------- RAPORLAR & TESİS GEÇMİŞİ -----------------
@dp.message(Command("zraporu", ignore_mention=True))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    sales = filter_sales_by_range(datetime.now() - timedelta(days=7), datetime.now())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:weekly"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:weekly")],
        [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:weekly")]
    ])
    await message.answer(build_report_text(sales, "HAFTALIK Z-RAPORU"), reply_markup=kb, parse_mode="HTML")

@dp.message(Command("tarihraporu", ignore_mention=True))
@dp.message(F.text == "📅 Tarihli Rapor Al")
async def trigger_custom_date_report(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Bugün", callback_data="date_filter:today"),
         InlineKeyboardButton(text="📅 Son 7 Gün", callback_data="date_filter:7days"),
         InlineKeyboardButton(text="🗓️ Bu Ay", callback_data="date_filter:this_month")],
        [InlineKeyboardButton(text="✍️ Özel Tarih Aralığı", callback_data="date_filter:custom")]
    ])
    await message.answer("📅 <b>Hangi aralığın raporunu almak istersiniz?</b>", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("date_filter:"))
async def process_date_filter_btn(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    now = datetime.now()
    if mode == "custom":
        await state.set_state(CustomReportState.waiting_date_range)
        await callback.message.answer("✍️ Format: <code>GG.AA.YYYY - GG.AA.YYYY</code>", parse_mode="HTML")
        await callback.answer()
        return

    ranges = {
        "today": (datetime(now.year, now.month, now.day), datetime(now.year, now.month, now.day, 23, 59, 59), "GÜNLÜK RAPOR", "Gunluk"),
        "7days": (now - timedelta(days=7), now, "SON 7 GÜN RAPORU", "Son_7_Gun"),
        "this_month": (datetime(now.year, now.month, 1), now, "BU AY RAPORU", "Bu_Ay")
    }
    s_dt, e_dt, title_label, file_label = ranges[mode]
    sales = filter_sales_by_range(s_dt, e_dt)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:custom"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:custom")],
        [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:custom")]
    ])
    await state.update_data(last_filtered_sales=sales, report_title=file_label)
    await callback.message.edit_text(build_report_text(sales, title_label), reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(CustomReportState.waiting_date_range)
async def process_custom_date_range(message: types.Message, state: FSMContext):
    try:
        s_str, e_str = [p.strip() for p in message.text.split("-")]
        s_dt = datetime.strptime(s_str, "%d.%m.%Y")
        e_dt = datetime.strptime(e_str, "%d.%m.%Y").replace(hour=23, minute=59, second=59)
        sales = filter_sales_by_range(s_dt, e_dt)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:custom"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:custom")],
            [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:custom")]
        ])
        await state.update_data(last_filtered_sales=sales, report_title=f"Rapor_{s_str}_{e_str}")
        await message.answer(build_report_text(sales, f"ÖZEL RAPOR ({s_str} - {e_str})"), reply_markup=kb, parse_mode="HTML")
    except Exception:
        await message.answer("⚠️ Format hatalı! Örnek: <code>01.10.2025 - 29.10.2026</code>", parse_mode="HTML")

@dp.callback_query(F.data.startswith("dl_rep:"))
async def handle_download_report_choice(callback: types.CallbackQuery, state: FSMContext):
    _, fmt, scope = callback.data.split(":")
    now = datetime.now()
    if scope == "weekly": sales, title = filter_sales_by_range(now - timedelta(days=7), now), "Haftalik_Z_Raporu"
    elif scope == "monthly": sales, title = filter_sales_by_range(datetime(now.year, now.month, 1), now), "Aylik_Satis_Raporu"
    else:
        st_data = await state.get_data()
        sales, title = st_data.get("last_filtered_sales", []), st_data.get("report_title", "Ozel_Rapor")
    if not sales:
        await callback.answer("Onaylı satış kaydı yok.", show_alert=True)
        return
    await callback.answer("Hazırlanıyor...")
    if fmt in ["excel", "both"]:
        f = generate_excel_z_report(sales, title)
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📊 <b>Elips Depo {title} (Excel)</b>", parse_mode="HTML")
    if fmt in ["pdf", "both"]:
        f = generate_pdf_z_report(sales, title)
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📑 <b>Elips Depo {title} (PDF)</b>", parse_mode="HTML")

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

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="HTML")

# ----------------- WEBAPP VERİ ALICISI & SOHBET KÖPRÜSÜ -----------------
@dp.message(F.web_app_data)
async def handle_webapp_payload(message: types.Message):
    try: p = json.loads(message.web_app_data.data)
    except Exception: return
    op = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    dir_type = p.get("direction")

    if dir_type == "STOCK_CHANGE" and p.get("action") == "DECREASE":
        dest = p.get("destination", "Bilinmeyen")
        code, name, qty = p.get("code"), p.get("name"), p.get("delta", 1)
        sales = load_sales()
        sales.append({
            "id": f"REF-{message.message_id}", "firm": dest, "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        msg = f"📤 <b>PARÇA SATILDI / DEPO ÇIKIŞI!</b>\n🏢 Firma: <code>{html.escape(dest)}</code>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n📉 Düşülen: <b>-{qty} Adet</b> (Depoda Kalan: <code>{p.get('current_qty', 0)} ADT</code>)\n👷‍♂️ Çıkış Yapan: {op}"
        await notify_both(msg)

    elif dir_type == "OMER_TO_KAMIL":
        msg = (
            f"🔔 <b>SAHADAN YENİ TALEP GELDİ! (Ömer ➔ Kamil)</b>\n"
            f"🏢 Firma: <b>{p.get('firm')}</b>\n"
            f"📞 İlgili Kişi: {p.get('contact')}\n"
            f"⚙️ Parça: <code>[{p.get('part_code')}]</code> {p.get('part_name')}\n"
            f"🔢 Adet: <b>{p.get('quantity')}</b> | Öncelik: <b>{p.get('priority')}</b>\n"
            f"📝 Not: {p.get('notes') or '-'}"
        )
        await notify_both(msg)

    elif dir_type == "KAMIL_TO_OMER":
        msg = (
            f"🚀 <b>SAHAYA YENİ GÖREV ATANDI! (Kamil ➔ Ömer)</b>\n"
            f"🏢 Gidilecek Tesis: <b>{p.get('firm')}</b>\n"
            f"📞 İletişim: {p.get('contact')}\n"
            f"📋 Görev Başlığı: <b>{p.get('task_type')}</b>\n"
            f"📌 Talimatlar: {p.get('instructions') or '-'}"
        )
        await notify_both(msg)

@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    menu_buttons = ["📦 Parça Listesi", "📊 Z-Raporu Al", "📅 Tarihli Rapor Al", "⏳ Bekleyen Teklifler", "✅ Tamamlanmış Teklifler", "📂 Verilen Teklifler", "🏢 Tesis Geçmişi", "📝 Nilay Hanım'a Teklif Hazırla", "📖 Kataloğu Gönder"]
    if message.text in menu_buttons: return
    tid = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if message.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and message.text:
        await bot.send_message(tid, f"💬 <b>{sender}:</b> {html.escape(message.text)}", parse_mode="HTML")
        await message.reply("✓ <i>İletildi.</i>", parse_mode="HTML")

# ----------------- 6. SERVER & BAŞLANGIÇ ÇALIŞTIRICISI -----------------
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
        init_flag = ".init_done_v15"
        if not os.path.exists(init_flag):
            save_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
            save_data(SALES_FILE, INITIAL_REAL_SALES)
            try:
                with open(init_flag, "w") as f: f.write("ok")
            except Exception: pass

        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands()
        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        logging.info(">>> ELIPS DEPO BOTU AKTIF VE CALISIYOR <<<")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Kritik hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
