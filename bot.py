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

BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            u_name = event.from_user.first_name if event.from_user else "Bilinmeyen"
            logging.info(f"--- YENİ MESAJ --- Gönderen: {u_name} (ID: {event.chat.id}) | Metin: '{event.text}'")
        return await handler(event, data)

dp.message.outer_middleware(LoggingMiddleware())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"
QUOTES_FILE = "submitted_quotes.json"
PDF_STORAGE_DIR = "stored_quotes_pdf"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# GERÇEK DEPO ENVANTERİ
REAL_WAREHOUSE_STOCKS = [
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
    {"code": "Umf-ILETISIM20", "name": "Umf-ILETISIM20 İletişim Kablosu", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
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
    {"code": "T7PAC-AIO88SV1", "name": "T7PAC-AIO88SV1 Giriş/Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-AI8SV1", "name": "T7PAC-AI8SV1 Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-AO8SV1", "name": "T7PAC-AO8SV1 Analog Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "PANELSET-T7701 ex", "name": "PANELSET-T7701 ex Ön Panel Seti", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "PANELSET-T7700", "name": "PANELSET-T7700 Ön Panel Seti", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-T7CPURIO", "name": "T7PAC-T7CPURIO İşlemci Modülü", "cat": "KONTROL", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "T7PAC-DOM16V5", "name": "T7PAC-DOM16V5 Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91661", "name": "Sürücü VZAB2P2BAA V1000 3/2,2 kW", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "40642", "name": "PLC CPU: CJ1M-CPU21", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "1013", "name": "Vana TORK 3/4\" 3 yollu + aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "1015", "name": "SLD Kanal Vanası Full 3/4\" TORK", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "5022", "name": "Salmastra", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "30010", "name": "EBARA 15MM SIL/SIL/VITON SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "30076", "name": "SANTOPRENE DIAPHRAGM POMKAR PK10", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "40597", "name": "BES005M BALLUFF Sensör", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "40634", "name": "BES0057: Balluff M12MI-NSC40B-BV03", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "40647", "name": "Smc CJPB15-10H6 Tek Etkili Silindir", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "41300", "name": "RD96 - MU CAMBAZ PISTONU POLIETILEN TAKOZ", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "41316", "name": "Lab120 encoder", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "41396", "name": "12'li Hareketli Kablo (X3-X4)", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "42184", "name": "PIPETLEME SIRINGA UCU", "cat": "MEKATRONIK", "qty": 200, "loc": "ELIPS-DEPO"},
    {"code": "50014", "name": "SUSTURUCU: AN15-02: 1/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "50018", "name": "VALF: SY5140-5YO-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "50090", "name": "Tork çift etkili aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "50138", "name": "PNOMATIK RAKOR: KQ2L04-M5A", "cat": "MEKATRONIK", "qty": 11, "loc": "ELIPS-DEPO"},
    {"code": "50156", "name": "T RAKOR: KQ2T06-22A: 6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "50227", "name": "KISICILI RAKOR: AS2201F-01-04SA", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "50238", "name": "SUSTURUCU: AN 120-M5 (SMC)", "cat": "MEKATRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "50242", "name": "KISICILI RAKOR: AS2002F-06: 6MM", "cat": "MEKATRONIK", "qty": 7, "loc": "ELIPS-DEPO"},
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
    {"code": "52156", "name": "PNOMATIK T RAKOR: KQ2T06-00A", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "54626", "name": "Valf Bobini: A03/0-24VDC 5W", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "54654", "name": "LOP POMPA FILTRE ORINGI 30*3 MM", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "90416", "name": "SOLENOID VALF: 00125317 24VDC", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90501", "name": "SMC C76-32PS PISTON KECESI", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90715", "name": "REGULATOR: AR10-M5H: 0-8 BAR", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90726", "name": "HIZ AYAR VALFI: ASN2-02 1/4\"", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
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
    {"code": "91035", "name": "OMAL TAMIR TAKIMI 3/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "91036", "name": "1\" OMAL VANA TAMIR TAKIMI", "cat": "MEKATRONIK", "qty": 4, "loc": "ELIPS-DEPO"},
    {"code": "91037", "name": "Omal küresel vana conta tamir takımı", "cat": "MEKATRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "91043", "name": "VALF KABLOSU", "cat": "ELEKTRONIK", "qty": 5, "loc": "ELIPS-DEPO"},
    {"code": "91045", "name": "SMC KURESEL MAFSAL KJ6D", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91064", "name": "PNOMATIK RAKOR KQ2H04", "cat": "MEKATRONIK", "qty": 13, "loc": "ELIPS-DEPO"},
    {"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR KQ2L04", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91074", "name": "PNOMATIK RAKOR KQ2L6M5N", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "91086", "name": "PNOMATIK T RAKOR KQ2T04", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "91088", "name": "T RAKOR KQ2T08-06", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91238", "name": "FIP25 POMPA KAPAK O-RINGI", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91277", "name": "RD96-Mu Polietilen Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91284", "name": "BONESSI VALF: P00112200", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91303", "name": "PASLANMAZ ARABA 4 DELIKLI REXROTH", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91332", "name": "FESTO BASINC ANAHTARI", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91406", "name": "FIP25 SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "ELIPS-DEPO"},
    {"code": "91448", "name": "PNOMATIK RAKOR 57116 1/8\"-6MM", "cat": "MEKATRONIK", "qty": 8, "loc": "ELIPS-DEPO"},
    {"code": "91463", "name": "EUROTEC REDUCER-KAFA ADAPTORU", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91502", "name": "LAB120 mikser kayışı", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91590", "name": "U4 CEKVALF", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "91594", "name": "VALF: SY5240-5YO-Q", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "91603", "name": "Omal Vana V451H405 3 Yollu L Port", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91604", "name": "1\" 3 YOLLU L PORT VANA", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "91633", "name": "OMAL VIP VANA VNC10004", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96185", "name": "PISTON: CD76E32-50-B", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96412", "name": "1\" > 3/4\" POLIETILEN DST ADAPTOR", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96467", "name": "Omal Aktüatör: DAN0030411S", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96496", "name": "Omal Çift Etkili Aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96515", "name": "DST Polietilen Z Eksen takozu", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "96516", "name": "DST Z Ekseni Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "96517", "name": "Rd96_MU Z Piston Dayama Takozu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "96570", "name": "Ø19mm Şeffaf Telli Hortum", "cat": "MEKATRONIK", "qty": 10, "loc": "ELIPS-DEPO"},
    {"code": "C-137161", "name": "Tuz rofinadsiyon filtr kapagi", "cat": "MEKATRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "TEST", "name": "Güç Kaynağı: DRL-24V75W1AZ", "cat": "ELEKTRONIK", "qty": 2, "loc": "ELIPS-DEPO"},
    {"code": "90880", "name": "DST Çekvalf Teflonu", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "cat": "MEKATRONIK", "qty": 9, "loc": "ELIPS-DEPO"},
    {"code": "90620", "name": "PH Sensörü SPH-1-DJ-6M", "cat": "ELEKTRONIK", "qty": 0, "loc": "ELIPS-DEPO"},
    {"code": "40025", "name": "PLC CPU: DVP12SA211R", "cat": "KONTROL", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "SP-01", "name": "Saha panosu", "cat": "ELEKTRONIK", "qty": 1, "loc": "ELIPS-DEPO"},
    {"code": "RA032DA", "name": "RA032DA aktuator", "cat": "MEKATRONIK", "qty": 1, "loc": "ELIPS-DEPO"}
]

INITIAL_REAL_SALES = [
    {"firm": "INDIGO", "ref_no": "SATIS", "date": "17.03.2025", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 5}], "status": "APPROVED"},
    {"firm": "WBM ANDIJON", "ref_no": "GARANTI", "date": "02.06.2025", "items": [{"code": "90840", "name": "PISTON SENSORU:DC73L", "qty": 1}], "status": "APPROVED"},
    {"firm": "SAFF TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "items": [{"code": "90484", "name": "3/4\" KIMYASAL VANA", "qty": 3}], "status": "APPROVED"},
    {"firm": "BEST COLOR", "ref_no": "SATIS", "date": "11.06.2025", "items": [{"code": "50289", "name": "VALF:SY3220-5LOU-M5-Q", "qty": 1}], "status": "APPROVED"},
    {"firm": "CHUST TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "items": [{"code": "90620", "name": "PH SENSORU", "qty": 2}], "status": "APPROVED"},
    {"firm": "PARVOZ HUMO", "ref_no": "SATIS", "date": "11.06.2025", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 6}], "status": "APPROVED"},
    {"firm": "SOF MEGA TEKSTIL", "ref_no": "SATIS", "date": "11.06.2025", "items": [{"code": "91332", "name": "FESTO BASINC ANAHTARI", "qty": 1}], "status": "APPROVED"},
    {"firm": "TERRY JAR", "ref_no": "SATIS", "date": "07.07.2025", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 2}], "status": "APPROVED"},
    {"firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "15.07.2025", "items": [{"code": "50257", "name": "TEK ETLKILI PNOMATIK SILINDIR", "qty": 1}, {"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR", "qty": 2}], "status": "APPROVED"},
    {"firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "05.10.2025", "items": [{"code": "91071", "name": "1/8\"-4MM DIRSEK RAKOR", "qty": 10}], "status": "APPROVED"},
    {"firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "07.10.2025", "items": [{"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "qty": 1}], "status": "APPROVED"},
    {"firm": "TERRY JAR", "ref_no": "SATIS", "date": "09.10.2025", "items": [{"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "qty": 5}], "status": "APPROVED"},
    {"firm": "BEST COLOR", "ref_no": "SATIS", "date": "18.10.2025", "items": [{"code": "50260", "name": "PISTON CD85N16-50-B", "qty": 2}], "status": "APPROVED"},
    {"firm": "TERRY JAR", "ref_no": "SATIS", "date": "25.10.2025", "items": [{"code": "90620", "name": "PH Sensörü SPH-1-DJ-6M", "qty": 2}], "status": "APPROVED"},
    {"firm": "JIZZAX TEKSTIL", "ref_no": "SATIS", "date": "04.12.2025", "items": [{"code": "90567", "name": "66MM TEFLON TAKVIYELI DIYAFRAM", "qty": 4}], "status": "APPROVED"},
    {"firm": "TERRY JAR", "ref_no": "SATIS", "date": "20.12.2025", "items": [{"code": "91332", "name": "FESTO BASINC ANAHTARI", "qty": 1}], "status": "APPROVED"},
    {"firm": "BIRYUZA TEKSTIL", "ref_no": "SATIS", "date": "09.02.2026", "items": [{"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "qty": 1}], "status": "APPROVED"},
    {"firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "21.02.2026", "items": [{"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "qty": 1}], "status": "APPROVED"},
    {"firm": "AKPAMUK TEKSTIL", "ref_no": "SATIS", "date": "26.03.2026", "items": [{"code": "5022", "name": "Salmastra", "qty": 1}], "status": "APPROVED"},
    {"firm": "ZELAL TEKSTIL", "ref_no": "SATIS", "date": "01.04.2026", "items": [{"code": "50293", "name": "VALF:SYJ3243-5LOU-Q", "qty": 1}], "status": "APPROVED"},
    {"firm": "BIRYUZA TEKSTIL", "ref_no": "SATIS", "date": "16.04.2026", "items": [{"code": "50260", "name": "PISTON CD85N16-50-B", "qty": 2}, {"code": "91086", "name": "PNOMATIK T RAKOR 4MM", "qty": 2}, {"code": "90765", "name": "RD96 CAMBAZ KOLU", "qty": 1}], "status": "APPROVED"},
    {"firm": "TERRY JAR", "ref_no": "SATIS", "date": "23.04.2026", "items": [{"code": "90881", "name": "DST CEKVALF YAYI", "qty": 2}, {"code": "90879", "name": "DST CEKVALF O-RINGI", "qty": 2}], "status": "APPROVED"},
    {"firm": "ASAKA TEKSTIL", "ref_no": "SATIS", "date": "07.05.2026", "items": [{"code": "91277", "name": "RD96-Mu Ağızlık", "qty": 1}, {"code": "50291", "name": "VALF:SYJ3240", "qty": 1}, {"code": "50289", "name": "VALF:SY3220", "qty": 1}, {"code": "50287", "name": "VALF:SY114", "qty": 2}], "status": "APPROVED"}
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

class UploadQuoteState(StatesGroup):
    waiting_firm_name = State()

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
load_tasks = lambda: load_data(TASKS_FILE, {})
save_tasks = lambda d: save_data(TASKS_FILE, d)
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_quotes = lambda d: save_data(QUOTES_FILE, d)

def get_catalog_pdf_file():
    for root, dirs, files in os.walk("."):
        for fn in files:
            if fn.lower() in ["katalog.pdf", "catalog.pdf", "rd96.pdf", "rd96_katalog.pdf"]:
                return os.path.join(root, fn)
            if fn.lower().endswith(".pdf") and "katalog" in fn.lower():
                return os.path.join(root, fn)
    return None

def extract_part_image_from_pdf(code: str, name: str = "") -> bytes:
    """PDF kataloğundan (2x3 ızgara formatı) ilgili parçanın kutucuğunu kırpar."""
    pdf_path = get_catalog_pdf_file()
    if not pdf_path:
        logging.warning("⚠️ Katalog PDF dosyası bulunamadı!")
        return None
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logging.error("❌ 'pymupdf' kurulu değil! 'pip install pymupdf' çalıştırın.")
        return None

    try:
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()

        for page_num, page in enumerate(doc):
            rects = page.search_for(code_str)
            if not rects and name:
                name_words = [w for w in name.split() if len(w) > 4]
                for w in name_words[:2]:
                    r_tmp = page.search_for(w)
                    if r_tmp:
                        rects = r_tmp
                        break

            if rects:
                r = rects[0]
                pw, ph = page.rect.width, page.rect.height
                
                # Sayfa 2 Sütun ve 3 Satıra bölünmüştür (6 kutucuk)
                col = 0 if r.x0 < (pw / 2) else 1
                row = 0 if r.y0 < (ph / 3) else (1 if r.y0 < (2 * ph / 3) else 2)

                x0 = 8 if col == 0 else (pw / 2 + 2)
                x1 = (pw / 2 - 2) if col == 0 else (pw - 8)
                y0 = 20 + row * (ph / 3.05)
                y1 = y0 + (ph / 3.1)

                clip_rect = fitz.Rect(max(0, x0), max(0, y0), min(pw, x1), min(ph, y1))
                pix = page.get_pixmap(clip=clip_rect, dpi=200)
                logging.info(f"✅ Görsel başarıyla kırpıldı: {code_str} (Sayfa {page_num + 1}, Satır {row + 1}, Sütun {col + 1})")
                return pix.tobytes("png")

        return None
    except Exception as e:
        logging.error(f"❌ Görsel kırpma hatası ({code}): {e}")
        return None

def calculate_similarity(query: str, part: dict) -> float:
    q_norm = normalize_tr(query.strip())
    name_norm = normalize_tr(part["name"])
    code_norm = normalize_tr(part["code"])
    if q_norm == code_norm: return 1.0
    if q_norm in code_norm: return 0.95
    if q_norm in name_norm: return 0.88
    q_words = q_norm.split()
    name_words = name_norm.split()
    word_scores = []
    for qw in q_words:
        best_w = 0.0
        for nw in name_words:
            sim = difflib.SequenceMatcher(None, qw, nw).ratio()
            if sim > best_w: best_w = sim
        word_scores.append(best_w)
    avg_word = sum(word_scores) / len(word_scores) if word_scores else 0.0
    full_ratio = difflib.SequenceMatcher(None, q_norm, name_norm).ratio()
    return max(avg_word, full_ratio)

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = []
    for p in stocks:
        score = calculate_similarity(query, p)
        if score > 0.30: scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e: logging.warning(f"İletilemedi ({cid}): {e}")

# ----------------- RAPOR MOTORU -----------------
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
            Paragraph("ELIPS DEPO PARCA SATIS RAPORU", t_style),
            Paragraph(f"DOKUM TARIHI: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_style)
        ]
        data = [["Sira", "Tarih", "Ref No", "Musteri / Tesis", "Urun Kodu", "Urun Adi", "Adet"]]
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

# ----------------- TESİS GEÇMİŞİ (ESNEK / YAKIN ARAMA) -----------------
def get_client_history_text(firm_query: str):
    sales = load_sales()
    q_norm = normalize_tr(firm_query.strip())
    
    scored_sales = []
    for s in sales:
        if s.get("status") != "APPROVED": continue
        f_norm = normalize_tr(s.get("firm", ""))
        ratio = difflib.SequenceMatcher(None, q_norm, f_norm).ratio()
        if q_norm in f_norm or ratio > 0.45:
            scored_sales.append((s, ratio))

    if not scored_sales:
        return f"🔍 <code>{html.escape(firm_query)}</code> için geçmiş onaylı kayıt bulunamadı."

    scored_sales.sort(key=lambda x: x[1], reverse=True)
    best_firm = scored_sales[0][0].get("firm")
    firm_records = [s for s, _ in scored_sales if s.get("firm") == best_firm]

    text = f"🏢 <b>{html.escape(best_firm)} — PARÇA GEÇMİŞİ</b>\n═══════════════════════════════\n\n"
    for item in firm_records:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for itm in item.get("items", []):
            text += f"• 📅 <code>{item.get('date', '')}</code> ➔ <b>{itm.get('qty')}x</b> <code>[{itm.get('code')}]</code> ({html.escape(itm.get('name', ''))}){ref_str}\n"
    text += f"\n═══════════════════════════════\n✅ Toplam: <b>{len(firm_records)} Sevkiyat / Hareket</b>"
    return text

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla"), KeyboardButton(text="📦 Parça Listesi")],
            [KeyboardButton(text="📊 Z-Raporu Al"), KeyboardButton(text="📅 Tarihli Rapor Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="📂 Verilen Teklifler")],
            [KeyboardButton(text="🏢 Tesis Geçmişi"), KeyboardButton(text="📖 Kataloğu Gönder")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Başlat / Ana Menü"),
        BotCommand(command="teklif", description="Nilay Hanım'a Teklif Hazırla"),
        BotCommand(command="stok", description="Parça Listesi"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
        BotCommand(command="verilenler", description="Verilen Teklifler"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu"),
        BotCommand(command="gecmis", description="Tesis Geçmişi"),
        BotCommand(command="katalog", description="Katalog PDF İndir")
    ]
    await bot.set_my_commands(commands)

# ----------------- ANA MENÜ / START KOMUTU -----------------
@dp.message(CommandStart())
@dp.message(F.text.lower().in_(["/start", "start", "başlat", "baslat"]))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.chat.id
    sender_name = html.escape(message.from_user.first_name if message.from_user and message.from_user.first_name else "Kullanıcı")
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else sender_name)
    pdf_info = "✓ Bulundu" if get_catalog_pdf_file() else "✗ Bulunamadı (Katalog.pdf)"
    stocks = load_stocks()

    msg_text = (
        f"👋 Selam {name}! <b>Elips Depo</b> & Teklif Robotu Aktif.\n\n"
        f"• Katalog PDF: {pdf_info}\n"
        f"• Güncel Depo Kalem: {len(stocks)} Çeşit\n"
        f"• Menü butonlarını kullanarak teklif oluşturabilir veya teklif PDF'i yükleyebilirsiniz."
    )
    await message.answer(msg_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ----------------- KATALOG PDF GÖNDERME -----------------
@dp.message(Command("katalog"))
@dp.message(F.text == "📖 Kataloğu Gönder")
async def send_catalog_pdf(message: types.Message):
    cat_path = get_catalog_pdf_file()
    if cat_path and os.path.exists(cat_path):
        await message.answer_document(FSInputFile(cat_path), caption="📖 <b>Elips Depo - Yedek Parça Kataloğu</b>", parse_mode="HTML")
    else:
        await message.answer("⚠️ Sunucuda <code>Katalog.pdf</code> dosyası bulunamadı.", parse_mode="HTML")

# ---------------- NİLAY HANIM'A TEKLİF SİHİRBAZI ----------------
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
        [InlineKeyboardButton(text="📖 Parça Kataloğunu İncele (PDF)", callback_data="qb_get_catalog")]
    ])
    await message.answer(
        f"🔍 <b>Hangi parça için teklif istenecek?</b>\n"
        f"• Varsa <b>Sipariş Kodunu</b> yazın (Örn: <code>90880</code>, <code>91661</code>)\n"
        f"• Veya <b>Ürün İsmini</b> yazın (Örn: <code>sürücü</code>, <code>diyafram</code>, <code>rakor</code>):",
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
    
    start_i = page_idx * page_size
    end_i = start_i + page_size
    current_items = matches[start_i:end_i]

    buttons = []
    for p, _ in current_items:
        buttons.append([InlineKeyboardButton(text=f"👉 {p['code']} - {p['name'][:28]}", callback_data=f"qbsel:{p['code']}")])

    nav_row = []
    if page_idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Önceki", callback_data=f"qbpage:{page_idx-1}"))
    if page_idx < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Sonraki ➡️", callback_data=f"qbpage:{page_idx+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔍 Farklı Kelime Ara", callback_data="qb_retry_search"),
        InlineKeyboardButton(text="📖 Katalog Aç", callback_data="qb_get_catalog")
    ])

    text = (
        f"🔍 <b>Arama Sonuçları:</b> <code>{html.escape(query)}</code>\n"
        f"Sayfa: <b>{page_idx + 1} / {total_pages}</b>\n\n"
        f"Lütfen teklif etmek istediğiniz parçayı seçin:"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(QuoteBuilderState.waiting_item_query)
async def process_quote_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    matches = find_best_matches(query)

    if not matches:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Parça Kataloğunu Gönder", callback_data="qb_get_catalog")]
        ])
        await message.answer(f"⚠️ <code>{html.escape(query)}</code> ile eşleşen parça bulunamadı.\nParça adını tam bilmiyorsanız kataloğu inceleyebilirsiniz:", reply_markup=kb, parse_mode="HTML")
        return

    top_part, top_score = matches[0]
    if query.strip().lower() == top_part['code'].lower():
        await state.update_data(selected_part=top_part)
        await state.set_state(QuoteBuilderState.waiting_qty)
        stock_text = f"Mevcut Depo: {top_part.get('qty', 0)} ADT" if top_part.get('qty', 0) > 0 else "Stokta Yok (0 ADT)"
        await message.answer(f"🎯 <b>Seçilen Parça:</b>\n📦 <code>[{top_part['code']}]</code> <b>{html.escape(top_part['name'])}</b> ({stock_text})\n\n🔢 Kaç <b>adet</b> teklif edilecek?", parse_mode="HTML")
        return

    await state.update_data(search_matches=matches, search_query=query)
    text, kb = render_search_results_page(matches, 0, query)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("qbpage:"))
async def on_quote_page_navigate(callback: types.CallbackQuery, state: FSMContext):
    page_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    matches = data.get("search_matches", [])
    query = data.get("search_query", "")
    if not matches:
        await callback.answer("Arama oturumu sonlandı.")
        return
    text, kb = render_search_results_page(matches, page_idx, query)
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
    stock_text = f"Mevcut Depo: {part.get('qty', 0)} ADT" if part.get('qty', 0) > 0 else "Stokta Yok (0 ADT)"
    await callback.message.edit_text(
        f"🎯 <b>Seçilen Parça:</b>\n📦 <code>[{part['code']}]</code> <b>{html.escape(part['name'])}</b> ({stock_text})\n\n"
        f"🔢 Kaç <b>adet</b> teklif edilecek? (Örn: <code>1</code>, <code>2</code>)", 
        parse_mode="HTML"
    )
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

    # KATALOGDAN EKRAN GÖRÜNTÜSÜ KESİP GÖNDERME
    img_bytes = extract_part_image_from_pdf(part["code"], part.get("name", ""))
    if img_bytes:
        try:
            photo = BufferedInputFile(img_bytes, filename=f"{part['code']}.png")
            await message.answer_photo(photo, caption=f"📸 <b>Katalog Görseli:</b> <code>[{part['code']}]</code> — {html.escape(part['name'])}", parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Resim iletilemedi: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="qb_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir & Formatı Al", callback_data="qb_done")]
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

    # İlgili kişi kısmı istenmediği için kaldırıldı
    formatted_quote = (
        f"Merhaba Nilay hanim\n\n"
        f"{firm} için aşağıdaki listedeki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    )
    for itm in items:
        formatted_quote += f"• {itm['code']} - {itm['name']} - {itm['qty']} Adet\n"

    formatted_quote += "\nİyi çalışmalar."

    # Yeni teklif olarak kaydet
    quotes = load_quotes()
    quote_id = f"TK-{int(time.time())}"
    quotes.append({
        "id": quote_id,
        "firm": firm,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING",
        "items": items,
        "text": formatted_quote,
        "pdf_file": None
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

    # Genel bildirim (İsimsiz, kurumsal)
    notify_text = (
        f"📥 <b>YENİ TEKLİF ALINDI!</b>\n\n"
        f"🏢 <b>Firma:</b> {firm}\n"
        f"📦 <b>Ürünler:</b>\n" +
        "\n".join([f"• [{i['code']}] {i['name']} ({i['qty']} Adet)" for i in items])
    )
    await notify_both(notify_text)

    await state.clear()
    await callback.answer("Teklif kaydedildi!")

# ----------------- PDF YÜKLEME VE TEKLİF YÖNETİMİ -----------------
@dp.message(F.document)
async def handle_document_upload(message: types.Message, state: FSMContext):
    doc = message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await message.answer("⚠️ Lütfen PDF formatında bir teklif dosyası yükleyin.")
        return

    file_id = doc.file_id
    saved_filename = f"{int(time.time())}_{doc.file_name}"
    save_path = os.path.join(PDF_STORAGE_DIR, saved_filename)
    
    await bot.download(doc, destination=save_path)
    await state.update_data(uploaded_pdf_path=save_path, uploaded_doc_name=doc.file_name)
    await state.set_state(UploadQuoteState.waiting_firm_name)

    await message.answer(
        f"📄 <b>Teklif PDF'i Alındı:</b> <code>{html.escape(doc.file_name)}</code>\n\n"
        f"Lütfen bu teklifin ait olduğu <b>Firma / Müşteri Adını</b> yazın:",
        parse_mode="HTML"
    )

@dp.message(UploadQuoteState.waiting_firm_name)
async def process_upload_firm_name(message: types.Message, state: FSMContext):
    firm = message.text.strip().upper()
    data = await state.get_data()
    pdf_path = data.get("uploaded_pdf_path")
    doc_name = data.get("uploaded_doc_name")

    quote_id = f"PDF-{int(time.time())}"
    quotes = load_quotes()
    new_quote = {
        "id": quote_id,
        "firm": firm,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING",
        "items": [],
        "text": f"{firm} teklif belgesi ({doc_name})",
        "pdf_file": pdf_path
    }
    quotes.append(new_quote)
    save_quotes(quotes)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Beklemede Bırak", callback_data=f"qstat:{quote_id}:PENDING")],
        [InlineKeyboardButton(text="✅ Onaylandı", callback_data=f"qstat:{quote_id}:APPROVED")],
        [InlineKeyboardButton(text="❌ Reddedildi", callback_data=f"qstat:{quote_id}:REJECTED")]
    ])

    await message.answer(
        f"✅ <b>{html.escape(firm)}</b> için teklif PDF'i kaydedildi!\n"
        f"Lütfen teklifin güncel durumunu seçin:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.clear()

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
        buttons.append([InlineKeyboardButton(text=f"⏳ {q['firm']} ({q['date'][:10]})", callback_data=f"qview:{q['id']}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("⏳ <b>BEKLEYEN TEKLİFLER:</b>\nİncelemek istediğinize tıklayın:", reply_markup=kb, parse_mode="HTML")

@dp.message(Command("verilenler"))
@dp.message(F.text == "📂 Verilen Teklifler")
async def show_submitted_quotes(message: types.Message):
    quotes = load_quotes()
    if not quotes:
        await message.answer("ℹ️ Kayıtlı teklif bulunmamaktadır.", parse_mode="HTML")
        return

    buttons = []
    for q in reversed(quotes[-12:]):
        st_icon = "🟢" if q.get("status") == "APPROVED" else ("🔴" if q.get("status") == "REJECTED" else "⏳")
        buttons.append([InlineKeyboardButton(text=f"{st_icon} {q['firm']} ({q['date'][:10]})", callback_data=f"qview:{q['id']}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📂 <b>VERİLEN TEKLİFLER LİSTESİ:</b>\nDetayı ve PDF'i görmek için seçin:", reply_markup=kb, parse_mode="HTML")

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

    text = (
        f"📄 <b>Teklif Detayı</b>\n"
        f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n"
        f"📅 Tarih: <code>{q['date']}</code>\n"
        f"📊 Durum: <b>{cur_st}</b>\n\n"
        f"📝 <b>Açıklama / Kalemler:</b>\n{html.escape(q.get('text', ''))}"
    )

    buttons = [
        [InlineKeyboardButton(text="✅ Onayla", callback_data=f"qstat:{quote_id}:APPROVED"),
         InlineKeyboardButton(text="❌ Reddet", callback_data=f"qstat:{quote_id}:REJECTED")],
        [InlineKeyboardButton(text="⏳ Beklemeye Al", callback_data=f"qstat:{quote_id}:PENDING")]
    ]

    # Eğer PDF'i varsa dosyayı gönder
    if q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        await callback.message.answer_document(FSInputFile(q["pdf_file"]), caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()

# Durum Değiştirme ve Stok Düşüm Onayı
@dp.callback_query(F.data.startswith("qstat:"))
async def on_quote_status_change(callback: types.CallbackQuery):
    _, quote_id, new_status = callback.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q:
        await callback.answer("Teklif bulunamadı.", show_alert=True)
        return

    if new_status == "APPROVED":
        # Stok Düşümü Sorusu
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Evet, Stoktan Düş", callback_data=f"qdeduct:{quote_id}:yes")],
            [InlineKeyboardButton(text="❌ Hayır, Sadece Durumu Onayla", callback_data=f"qdeduct:{quote_id}:no")]
        ])
        await callback.message.answer(
            f"⚠️ <b>{html.escape(q['firm'])}</b> teklifi ONAYLANDI olarak işaretleniyor.\n\n"
            f"Bu teklifteki parçalar <b>Elips Depo</b> stoğundan düşülsün mü? Emin misiniz?",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    q["status"] = new_status
    save_quotes(quotes)
    await callback.message.edit_text(callback.message.text + f"\n\n⚙️ <b>Durum Güncellendi:</b> {new_status}", parse_mode="HTML")
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

    if choice == "yes" and q.get("items"):
        stocks = load_stocks()
        sales = load_sales()
        deducted_info = []

        for item in q["items"]:
            code, qty = item["code"], item.get("qty", 1)
            p = next((s for s in stocks if s["code"] == code), None)
            if p:
                p["qty"] = max(0, p.get("qty", 0) - qty)
                deducted_info.append(f"• [{code}] {p['name']}: -{qty} (Kalan: {p['qty']})")
        
        save_stocks(stocks)

        # Satış geçmişine ekle
        sales.append({
            "id": f"SLS-{int(time.time())}",
            "firm": q["firm"],
            "ref_no": "TEKLIF-ONAY",
            "items": q["items"],
            "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        msg = (
            f"📦 <b>ELİPS DEPO STOK DÜŞÜMÜ GERÇEKLEŞTİ!</b>\n"
            f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n\n" +
            "\n".join(deducted_info)
        )
        await notify_both(msg)
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>Onaylandı ve Stoklardan Düşüldü!</b>", parse_mode="HTML")
    else:
        await callback.message.edit_text(callback.message.text + "\n\n✅ <b>Teklif Onaylandı (Stoklar değiştirilmedi).</b>", parse_mode="HTML")
    await callback.answer()

# ----------------- PARÇA LİSTESİ -----------------
@dp.message(Command("stok", ignore_mention=True))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stocks(message: types.Message):
    stocks = load_stocks()
    available = [s for s in stocks if s.get("qty", 0) > 0]
    out_of_stock = [s for s in stocks if s.get("qty", 0) == 0]

    text = f"📦 <b>GÜNCEL ELİPS DEPO STOKLARI</b>\n"
    text += f"📊 Toplam Kalem: <b>{len(stocks)}</b> | Stokta Olan: <b>{len(available)}</b> | Tükendi: <b>{len(out_of_stock)}</b>\n"
    text += "═══════════════════════════════\n\n"

    for s in available[:15]:
        text += f"• <code>[{s['code']}]</code> {html.escape(s['name'][:35])}\n  └ Stok: <b>{s['qty']} ADT</b> | {s['loc']}\n"
    
    if len(available) > 15:
        text += f"\n<i>...ve {len(available)-15} kalem ürün daha (Mini App'ten görebilirsiniz).</i>"

    await message.answer(text, parse_mode="HTML")

# ----------------- RAPOR İŞLEMLERİ -----------------
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
        await callback.message.answer("✍️ Format: <code>GG.AA.YYYY - GG.AA.YYYY</code> (Örn: <code>01.10.2026 - 29.10.2026</code>)", parse_mode="HTML")
        await callback.answer(); return

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
        await message.answer("⚠️ Format hatalı! Örnek: <code>01.10.2026 - 29.10.2026</code>", parse_mode="HTML")

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
        await callback.answer("Onaylı satış kaydı yok.", show_alert=True); return
    await callback.answer("Hazırlanıyor...")
    if fmt in ["excel", "both"]:
        f = generate_excel_z_report(sales, title)
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📊 <b>Elips Depo {title} (Excel)</b>", parse_mode="HTML")
    if fmt in ["pdf", "both"]:
        f = generate_pdf_z_report(sales, title)
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📑 <b>Elips Depo {title} (PDF)</b>", parse_mode="HTML")

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

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="HTML")

# ----------------- WEBAPP VERİ ALIŞVERİŞİ -----------------
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
            "id": ref_id, "firm": dest, "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y"), "timestamp": datetime.now().isoformat()
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
        logging.warning(f"Server baslatilamadi: {e}")

async def main():
    try:
        save_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
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
