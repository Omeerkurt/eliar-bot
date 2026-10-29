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
        logging.info("✅ Google GenAI istemcisi başarıyla bağlandı.")
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

# ----------------- GERÇEK ELİPS DEPO ENVANTERİ -----------------
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

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class CustomReportState(StatesGroup):
    waiting_date_range = State()

class QuoteBuilderState(StatesGroup):
    waiting_firm = State()
    waiting_item_query = State()
    waiting_custom_tr = State()
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
load_sales = lambda: load_data(SALES_FILE, INITIAL_REAL_SALES)
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

def extract_part_image_from_pdf(code: str, name: str = "") -> bytes:
    pdf_path = get_catalog_pdf_file()
    if not pdf_path: return None
    code_str = str(code).strip()

    try:
        import fitz
        doc = fitz.open(pdf_path)

        for p_idx, page in enumerate(doc):
            pw, ph = page.rect.width, page.rect.height
            rects = page.search_for(code_str) or page.search_for(f"({code_str})")
            if not rects: continue

            first_match = rects[0]
            col = 0 if first_match.x0 < (pw / 2) else 1

            col_rects = [r for r in rects if (r.x0 < pw/2 if col == 0 else r.x0 >= pw/2)]
            if not col_rects: col_rects = rects
            min_code_y = min(r.y0 for r in col_rects)

            y0 = max(10, min_code_y - 28)
            x0 = 8 if col == 0 else (pw / 2 + 3)
            x1 = (pw / 2 - 3) if col == 0 else (pw - 8)

            all_other = page.search_for("Order Code")
            next_y1 = ph - 15

            for oc in all_other:
                is_same_col = (oc.x0 < pw/2) if col == 0 else (oc.x0 >= pw/2)
                if is_same_col and oc.y0 > (min_code_y + 45):
                    cand_y1 = oc.y0 - 28
                    if cand_y1 < next_y1:
                        next_y1 = cand_y1

            y1 = next_y1
            if (y1 - y0) < 90:
                y1 = min(ph - 15, y0 + 260)

            clip_rect = fitz.Rect(max(0, x0), max(0, y0), min(pw, x1), min(ph, y1))
            pix = page.get_pixmap(clip=clip_rect, dpi=200)
            img_bytes = pix.tobytes("png")
            if img_bytes and len(img_bytes) > 2500:
                return img_bytes

        return None
    except Exception as e:
        logging.error(f"Kırpma motoru hatası: {e}")
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

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e: logging.warning(f"Bildirim iletilemedi ({cid}): {e}")

async def parse_quote_pdf_with_gemini(pdf_path: str) -> dict:
    pdf_bytes = b""
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        logging.error(f"PDF dosya okuma hatası: {e}")

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
                    logging.info(f"✅ Gemini ({model_name}) ile PDF başarıyla okundu: {parsed.get('firm')}")
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

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Başlat / Ana Menü"),
        BotCommand(command="teklif", description="Nilay Hanım'a Teklif Hazırla"),
        BotCommand(command="stok", description="Parça Listesi"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
        BotCommand(command="tamamlananlar", description="Tamamlanmış Teklifler"),
        BotCommand(command="verilenler", description="Verilen Teklifler"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu"),
        BotCommand(command="gecmis", description="Tesis Geçmişi"),
        BotCommand(command="katalog", description="Katalog PDF İndir")
    ]
    await bot.set_my_commands(commands)

# ----------------- ANA MENÜ / START -----------------
@dp.message(CommandStart())
@dp.message(F.text.lower().in_(["/start", "start", "başlat", "baslat"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.chat.id
    sender_name = html.escape(message.from_user.first_name if message.from_user else "Kullanıcı")
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else sender_name)
    pdf_info = "✓ Bulundu" if get_catalog_pdf_file() else "✗ Bulunamadı (Katalog.pdf)"
    stocks = load_stocks()

    msg_text = (
        f"👋 Selam {name}! <b>Elips Depo</b> Robotu Aktif.\n\n"
        f"• Katalog PDF: {pdf_info}\n"
        f"• Güncel Depo Kalem: {len(stocks)} Çeşit\n"
        f"• <b>İpucu:</b> Fiyat teklifi PDF'ini direkt buraya gönderebilirsiniz, yapay zeka ile otomatik taranacaktır."
    )
    await message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@dp.message(Command("katalog"))
@dp.message(F.text == "📖 Kataloğu Gönder")
async def send_catalog_pdf(message: types.Message):
    cat_path = get_catalog_pdf_file()
    if cat_path and os.path.exists(cat_path):
        await message.answer_document(FSInputFile(cat_path), caption="📖 <b>Elips Depo - Yedek Parça Kataloğu</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Sunucuda <code>Katalog.pdf</code> bulunamadı.", parse_mode="HTML")

# ----------------- NİLAY HANIM'A TEKLİF SİHİRBAZI -----------------
@dp.message(Command("teklif", ignore_mention=True))
@dp.message(F.text == "📝 Nilay Hanım'a Teklif Hazırla")
async def start_quote_wizard(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteBuilderState.waiting_firm)
    await message.answer("🏢 <b>Teklif hangi müşteri / fabrika için hazırlanacak?</b>\n(Örnek: <code>MARK FORMELLE</code>, <code>TERRY JAR</code>)", parse_mode="HTML")

@dp.message(QuoteBuilderState.waiting_firm)
async def process_quote_firm(message: types.Message, state: FSMContext):
    firm = message.text.strip().upper()
    await state.update_data(firm_name=firm)
    await state.set_state(QuoteBuilderState.waiting_item_query)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇹🇷 Eliar TR'den İstenecek (Manuel Parça)", callback_data="qb_custom_tr")],
        [InlineKeyboardButton(text="📖 Parça Kataloğunu İncele (PDF)", callback_data="qb_get_catalog")]
    ])
    await message.answer(
        f"🔍 <b>Hangi parça için teklif istenecek?</b>\n"
        f"• Varsa <b>Sipariş Kodunu</b> yazın (Örn: <code>91463</code>, <code>90880</code>)\n"
        f"• Veya <b>Ürün İsmini</b> yazın (Örn: <code>adaptör</code>, <code>diyafram</code>)\n"
        f"• Katalogda/stokta yoksa aşağıdaki <b>Eliar TR</b> butonuna tıklayın:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "qb_custom_tr")
async def on_quote_custom_tr_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_custom_tr)
    await callback.message.edit_text(
        "🇹🇷 <b>Eliar TR (Türkiye Deposu) İçin Parça Ekleme</b>\n\n"
        "Lütfen parçanın <b>ismini</b> ve biliyorsanız <b>kodunu</b> yazın:\n\n"
        "<i>Örnek:</i> <code>91999 - Dozaj Pompası Diyaframı</code>\n"
        "<i>Veya:</i> <code>Sıcaklık Transmiteri 4-20mA</code>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_custom_tr)
async def process_quote_custom_tr(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Lütfen geçerli bir parça bilgisi yazın.")
        return

    parts = re.split(r"[-–—:]", text, maxsplit=1)
    if len(parts) == 2 and (parts[0].strip().isalnum() or len(parts[0].strip()) <= 10):
        code = parts[0].strip().upper()
        name = f"{parts[1].strip()} (Eliar TR)"
    else:
        if text.replace(" ", "").isalnum() and len(text) <= 8 and any(c.isdigit() for c in text):
            code = text.upper()
            name = f"Yedek Parça [{code}] (Eliar TR)"
        else:
            code = "TR-STOK"
            name = f"{text} (Eliar TR)"

    selected_part = {"code": code, "name": name, "qty": 0, "is_tr": True}
    await state.update_data(selected_part=selected_part)
    await state.set_state(QuoteBuilderState.waiting_qty)

    await message.answer(
        f"🎯 <b>Eliar TR Parçası Eklendi:</b>\n"
        f"• Kod: <code>[{code}]</code>\n"
        f"• Tanım: <b>{html.escape(name)}</b>\n\n"
        f"🔢 Kaç <b>adet</b> teklif istenecek?",
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

    buttons = [[InlineKeyboardButton(text=f"👉 [{p['code']}] {p['name'][:30]} ({p.get('qty',0)} ADT)", callback_data=f"qbsel:{p['code']}")] for p, _ in current_items]
    nav_row = []
    if page_idx > 0: nav_row.append(InlineKeyboardButton(text="⬅️ Önceki", callback_data=f"qbpage:{page_idx-1}"))
    if page_idx < total_pages - 1: nav_row.append(InlineKeyboardButton(text="Sonraki ➡️", callback_data=f"qbpage:{page_idx+1}"))
    if nav_row: buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🇹🇷 Eliar TR'den İstenecek (Listede Yok)", callback_data="qb_custom_tr")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔍 Farklı Kelime Ara", callback_data="qb_retry_search"),
        InlineKeyboardButton(text="📖 Katalog Aç", callback_data="qb_get_catalog")
    ])

    text = f"🔍 <b>Arama:</b> <code>{html.escape(query)}</code> (Bulunan: {len(matches)} | Sayfa: {page_idx + 1}/{total_pages})\nSeçmek istediğiniz parçaya tıklayın:"
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(QuoteBuilderState.waiting_item_query)
async def process_quote_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    matches = find_best_matches(query)

    if not matches:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇹🇷 Eliar TR'den İstenecek (Manuel Ekle)", callback_data="qb_custom_tr")],
            [InlineKeyboardButton(text="📖 Kataloğu Gönder", callback_data="qb_get_catalog")]
        ])
        await message.answer(
            f"⚠️ <code>{html.escape(query)}</code> yerel depoda veya katalogda bulunamadı.\n\n"
            f"Bu parçayı doğrudan <b>Eliar Türkiye (TR)</b> deposundan istemek için aşağıdaki butona tıklayın:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    top_part, score = matches[0]
    if normalize_tr(query) == normalize_tr(top_part['code']) or score >= 0.95:
        await state.update_data(selected_part=top_part)
        await state.set_state(QuoteBuilderState.waiting_qty)

        img_bytes = extract_part_image_from_pdf(top_part["code"], top_part.get("name", ""))
        if img_bytes:
            photo = BufferedInputFile(img_bytes, filename=f"{top_part['code']}.png")
            await message.answer_photo(photo, caption=f"📸 <b>Katalog Görseli:</b> <code>[{top_part['code']}]</code> — {html.escape(top_part['name'])}", parse_mode="HTML")

        stock_text = f"Depo: {top_part.get('qty', 0)} ADT" if top_part.get('qty', 0) > 0 else "Stokta Yok (0 ADT)"
        await message.answer(f"🎯 <b>Seçilen:</b> <code>[{top_part['code']}]</code> {html.escape(top_part['name'])}\n📊 Durum: <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")
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
    part = next((p for p in stocks if p["code"].lower() == code.lower()), None)
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
    await callback.message.answer(f"🎯 <b>Seçilen:</b> <code>[{part['code']}]</code> {html.escape(part['name'])}\n📊 Durum: <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_qty)
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
        [InlineKeyboardButton(text="➕ Yerel Depodan Ekle", callback_data="qb_more_local"),
         InlineKeyboardButton(text="🇹🇷 Eliar TR'den Ekle", callback_data="qb_custom_tr")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir", callback_data="qb_done")]
    ])
    await state.set_state(QuoteBuilderState.confirm_more)
    await message.answer(f"✅ <b>{qty} Adet</b> <code>[{part['code']}]</code> eklendi!\nNe yapmak istersiniz?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "qb_more_local")
async def on_quote_add_another_local(callback: types.CallbackQuery, state: FSMContext):
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

    sender_name = "Ömer" if callback.from_user.id == OMER_CHAT_ID else "Kamil"
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
        "id": quote_id, "firm": firm, "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING", "items": items, "pdf_file": None, "creator": sender_name
    })
    save_quotes(quotes)

    text = (
        f"📋 <b>KOPYALAMAYA HAZIR TEKLİF METNİ:</b>\n"
        f"═══════════════════════════════\n\n"
        f"{formatted_quote}\n\n"
        f"═══════════════════════════════\n"
        f"💡 <i>Metne basılı tutarak kopyalayabilirsiniz.</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")

    notify_text = (
        f"📥 <b>YENİ TEKLİF HAZIRLANDI!</b>\n"
        f"👤 <b>Hazırlayan:</b> {sender_name}\n"
        f"🏢 <b>Firma:</b> {firm}\n"
        f"📦 <b>Ürünler:</b>\n" +
        "\n".join([f"• [{i['code']}] {i['name']} ({i['qty']} Adet)" for i in items])
    )
    await notify_both(notify_text)
    await state.clear()
    await callback.answer("Teklif kaydedildi!")

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

# ----------------- TEKLİF SİLME (TESTLER İÇİN) -----------------
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

# ----------------- TEKLİF ONAY & STOK DÜŞÜŞÜ -----------------
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
            [InlineKeyboardButton(text="⚠️ Evet, Depo Stoğundan Düş", callback_data=f"qdeduct:{quote_id}:yes")],
            [InlineKeyboardButton(text="❌ Hayır, Sadece Durumu Onayla", callback_data=f"qdeduct:{quote_id}:no")]
        ])
        await callback.message.answer(
            f"⚠️ <b>{html.escape(q['firm'])}</b> teklifini onaylıyorsunuz.\n\n"
            f"Bu parçalar <b>Elips Depo</b> stoğundan düşülsün mü?",
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
            code = item.get("code", "")
            try: qty = int(item.get("qty", 1))
            except Exception: qty = 1
            p = next((s for s in stocks if s["code"].lower() == code.lower()), None)
            if not p: p = next((s for s in stocks if normalize_tr(s["name"]) in normalize_tr(item.get("name", ""))), None)
            if p:
                p["qty"] = max(0, p.get("qty", 0) - qty)
                deducted_info.append(f"• <code>[{p['code']}]</code> {p['name']}: <b>-{qty} Adet</b> (Depoda Kalan: {p['qty']})")

        save_stocks(stocks)
        sales.append({
            "id": f"SLS-{int(time.time())}", "firm": q["firm"], "ref_no": "TEKLIF-ONAY",
            "items": q["items"], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        msg = (
            f"📦 <b>ELİPS DEPO - STOKTAN DÜŞÜM YAPILDI!</b>\n"
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
        lines.append(f"{idx}. <code>[{itm.get('code')}]</code> {itm.get('name')} — {itm.get('qty')} Adet")

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

# ----------------- ZAMANLAYICI & SERVER (RENDER İÇİN PORT BINDING) -----------------
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
        init_flag = ".init_done_v9"
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
