import json
import logging
import asyncio
import os
import re
import time
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    BotCommand,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
GEMINI_API_KEY = "AIzaSyAuUg0a1ew5V4aF1E-FTsdVinsMpXckOgQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"

DEFAULT_STOCKS = [
    # KONTROLÖRLER
    {"code": "PD320", "name": "Pd320 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "PD330", "name": "PD330 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "PD300", "name": "Pd300 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "PD340", "name": "Pd340 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "PD350", "name": "Pd350 Kontrol Cihazı", "cat": "KONTROL", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "P44", "name": "P44 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "P42", "name": "P42 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "P300", "name": "P300 Kontrol Cihazı", "cat": "KONTROL", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "P40", "name": "P40 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "P43", "name": "P43 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "S400", "name": "S400 Kontrol Cihazı", "cat": "KONTROL", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "S42", "name": "S42 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-T7000", "name": "Edc T7000 Kontrol Cihazı", "cat": "KONTROL", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-M7700", "name": "Edc M7700 Kontrol Cihazı", "cat": "KONTROL", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-T710", "name": "Edc T710 Kontrol Cihazı", "cat": "KONTROL", "qty": 9, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-T712", "name": "Edc T712 Kontrol Cihazı", "cat": "KONTROL", "qty": 8, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-T7701EX", "name": "Edc T7701EX Kontrol Cihazı", "cat": "KONTROL", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "EDC-T7700", "name": "Edc T7700 Kontrol Cihazı", "cat": "KONTROL", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "T7700", "name": "T7700 Cihazı", "cat": "KONTROL", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "T7701-EX-G", "name": "T7701 EX G Kontrol Cihazı", "cat": "KONTROL", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "PANELSET-T7701EX", "name": "PANELSET-T7701 ex", "cat": "KONTROL", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "PANELSET-T7700", "name": "PANELSET-T7700", "cat": "KONTROL", "qty": 1, "loc": "MERKEZ-DEPO"},

    # ELEKTRONİK
    {"code": "AIM8-A", "name": "Aim8-A Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "AIM8-B", "name": "Aim8-B Analog Giriş Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "DIM32", "name": "Dim32 Dijital Giriş Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "DOM16-PLC", "name": "Dom16-PLC Dijital Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 6, "loc": "MERKEZ-DEPO"},
    {"code": "AOM8", "name": "AOM8 Analog Çıkış Modülü", "cat": "ELEKTRONIK", "qty": 7, "loc": "MERKEZ-DEPO"},
    {"code": "UMF-ILETISIM20", "name": "Umf-ILETISIM20 kablosu", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "TBBPLC-F", "name": "TBBPLC-F Modülü", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "POWERFAIL", "name": "Powerfail Modülü", "cat": "ELEKTRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "T7RACK-6-PLC", "name": "T7RACK 6 PLC", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "T7RACK-10-PLC", "name": "T7RACK 10 PLC", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-POWER-30", "name": "T7PAC-POWER 30 Güç Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-POWER-20", "name": "T7PAC-POWER 20 Güç Modülü", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-DIM32V5", "name": "T7PAC-DIM32V5 Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-DOM32V5", "name": "T7PAC-DOM32V5 Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-DIM16V5", "name": "T7PAC-DIM16V5 Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-DOM16V5", "name": "T7PAC-DOM16V5 Modülü", "cat": "ELEKTRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-AIO88SV1", "name": "T7PAC-AIO88SV1 Modülü", "cat": "ELEKTRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-AI8SV1", "name": "T7PAC-AI8SV1 Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-AO8SV1", "name": "T7PAC-AO8SV1 Modülü", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "T7PAC-T7CPURIO", "name": "T7PAC-T7CPURIO CPU", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "40597", "name": "BES005M BALLUFF Sensör", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "40634", "name": "BES0057 Balluff M12MI-NSC40B-BV03", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "41316", "name": "Lab120 encoder", "cat": "ELEKTRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "41396", "name": "12'li Hareketli Kablo (X3-X4)", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "54626", "name": "A03/0-24VDC B00123525 Bobin 5W", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90759", "name": "SENSOR TUTUCU: BJ2-016", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "90761", "name": "SENSOR TUTUCU: BM2-025", "cat": "ELEKTRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "90840", "name": "PISTON SENSORU: DC73L", "cat": "ELEKTRONIK", "qty": 6, "loc": "MERKEZ-DEPO"},
    {"code": "91043", "name": "VALF KABLOSU", "cat": "ELEKTRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "91332", "name": "FESTO BASINC ANAHTARI", "cat": "ELEKTRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "TEST", "name": "Güç Kaynağı: DRL-24V75W1AZ", "cat": "ELEKTRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90620", "name": "PH Sensörü: SPH-1-DJ-6M (Seko: 9900105096)", "cat": "ELEKTRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "40025", "name": "PLC CPU: DVP12SA211R: 8DI 4DO", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "SPU-PANO", "name": "Saha panosu (SPU su yok)", "cat": "ELEKTRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},

    # MEKATRONİK
    {"code": "1013", "name": "Vana TORK (ko'k) 3/4\" 3 yollu + aktuator", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "1015", "name": "SLD Kanal Vanası Full 3/4\" TORK 2 yollu + aktuator", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "5022", "name": "Salmastra (Geylani ile geldi)", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "30010", "name": "EBARA 15MM SIL/SIL/VITON SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "30076", "name": "SANTOPRENE DIAPHRAGM FOR POMKAR PK10", "cat": "MEKATRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "40647", "name": "Smc CJPB15-10H6 Tek Etkili Silindir", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "41300", "name": "RD96 MU Cambaz Pistonu Polietilen Takoz", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "42184", "name": "PIPETLEME SIRINGA UCU", "cat": "MEKATRONIK", "qty": 200, "loc": "MERKEZ-DEPO"},
    {"code": "50014", "name": "SUSTURUCU: AN15-02: 1/4\"", "cat": "MEKATRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "50018", "name": "VALF: SY5140-5YO-Q", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "50090", "name": "Tork Çift Etkili Aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "50138", "name": "PNOMATIK RAKOR: KQ2L04-M5A Dirsek", "cat": "MEKATRONIK", "qty": 11, "loc": "MERKEZ-DEPO"},
    {"code": "50156", "name": "T RAKOR: KQ2T06-22A: 6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50227", "name": "KISICILI RAKOR: AS2201F-01-04SA 1/8\"-4MM", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "50238", "name": "SUSTURUCU: AN 120-M5 (SMC)", "cat": "MEKATRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "50242", "name": "KISICILI RAKOR: AS2002F-06 6MM HAT TIPI", "cat": "MEKATRONIK", "qty": 7, "loc": "MERKEZ-DEPO"},
    {"code": "50257", "name": "PNOMATIK SILINDIR CD75E32-80-B-XC6B", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "50258", "name": "SILINDIR CD85N16-100-B (SMC)", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50259", "name": "SILINDIR CD85N16-200-B (SMC)", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50260", "name": "PISTON CD85N16-50-B", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "50261", "name": "PISTON CD85N16-80-B", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50269", "name": "Manifold: SS3Y1-S41-02-M5-Q 2'li Altlık", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "50270", "name": "Manifold: SS3Y1-S41-04-M5-Q 4'lü Altlık", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "50287", "name": "VALF: SY114-5LOU-Q", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "50289", "name": "VALF: SY3220-5LOU-M5-Q", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "50291", "name": "VALF: SYJ3143-5LOU-Q", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50292", "name": "VALF: SYJ3240-5LOU-Q", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "50293", "name": "VALF: SYJ3243-5LOU-Q", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "50294", "name": "VALF: SYJ7120-5DZ-01F-Q", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "50295", "name": "VALF: SYJ7220-5DZ-01F-Q", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "52156", "name": "PNOMATIK T RAKOR: KQ2T06-00A: 6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "54654", "name": "LOP POMPA FILTRE ORINGI 30*3 MM EPDM", "cat": "MEKATRONIK", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "90416", "name": "SOLENOID VALF: 00125317 6013-A02", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90501", "name": "SMC C76-32PS PISTON KECESI", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90715", "name": "REGULATOR: AR10-M5H: 0-8 BAR", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90726", "name": "HIZ AYAR VALFI: ASN2-02 1/4\" Susturuculu", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90765", "name": "RD96 CAMBAZ KOLU", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "90766", "name": "RD96 ALIMINYUM LAMA MONTAJ PARCASI", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90769", "name": "RD96 BOS CAMBAZ KUTUSU", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90771", "name": "RD96 CAMBAZ MEKANIZMASI", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90781", "name": "SMC C85-25PS PISTON KECESI", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90782", "name": "C85C16 EKLEM BAGLANTI PARCASI", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "90879", "name": "DST CEKVALF O-RINGI", "cat": "MEKATRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "90881", "name": "DST CEKVALF YAYI", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "90946", "name": "SLR1-40 FILTRE", "cat": "MEKATRONIK", "qty": 12, "loc": "MERKEZ-DEPO"},
    {"code": "90948", "name": "FIP25 BAKALIT FLANŞ", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "91035", "name": "OMAL (TAMIR) TAKIMI: KGBV4505 3/4\" (DN20)", "cat": "MEKATRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "91036", "name": "1\" OMAL VANA TAMIR TAKIMI", "cat": "MEKATRONIK", "qty": 4, "loc": "MERKEZ-DEPO"},
    {"code": "91037", "name": "Omal Küresel Vana Conta Tamir Takımı", "cat": "MEKATRONIK", "qty": 5, "loc": "MERKEZ-DEPO"},
    {"code": "91045", "name": "SMC KURESEL MAFSAL: KJ6D M6*1", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "91064", "name": "PNOMATIK RAKOR: KQ2H04-M5A Düz", "cat": "MEKATRONIK", "qty": 13, "loc": "MERKEZ-DEPO"},
    {"code": "91071", "name": "1/8\"-4MM Nikel Kaplı Dirsek Rakor / KQ2L04-01NS", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "91074", "name": "PNOMATIK RAKOR: KQ2L6M5N Dirsek", "cat": "MEKATRONIK", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "91086", "name": "PNOMATIK T RAKOR: KQ2T04-M5A: Orta", "cat": "MEKATRONIK", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "91088", "name": "T RAKOR: KQ2T08-06 8-6MM", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "91238", "name": "FIP25 POMPA KAPAK O-RINGI", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "91277", "name": "RD96-Mu Polietilen Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "91284", "name": "BONESSI VALF: P00112200 E1A/4", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "91303", "name": "Paslanmaz Araba 4 Delikli Krom Bilyalı Rexroth", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "91406", "name": "FIP25 SALMASTRA", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO"},
    {"code": "91448", "name": "PNOMATIK RAKOR: 57116 1/8\"-6MM Pirinç", "cat": "MEKATRONIK", "qty": 8, "loc": "MERKEZ-DEPO"},
    {"code": "91463", "name": "EUROTEC REDUCER-KAFA ADAPTORU", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "91502", "name": "LAB120 mikser kayışı", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "91590", "name": "U4 CEKVALF", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "91594", "name": "VALF: SY5240-5YO-Q", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "91603", "name": "Omal Vana: V451H405 3 Yollu L Port 3/4\"", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "91604", "name": "1\" 3 Yollu L Port Vana", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "91633", "name": "OMAL VIP VANA VNC10004", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "96185", "name": "PISTON: CD76E32-50-B", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "96412", "name": "1\" > 3/4\" Polietilen DST Çekvalf Adaptörü", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "96467", "name": "Omal Aktüatör: DAN0030411S F03-F05", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "96496", "name": "Omal Çift Etkili Aktüatör: DAN0015411S DA15", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "96515", "name": "DST Polietilen Z Eksen dayama takozu", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "96516", "name": "DST Z Ekseni Polietilen Ağızlık", "cat": "MEKATRONIK", "qty": 0, "loc": "MERKEZ-DEPO"},
    {"code": "96517", "name": "Rd96_MU Z Polietilen Z Eksen Dayama", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "96570", "name": "Ø19mm Şeffaf Telli Hortum (Mavi)", "cat": "MEKATRONIK", "qty": 10, "loc": "MERKEZ-DEPO"},
    {"code": "C-137161", "name": "Tuz rafinasyon filtre kapağı", "cat": "MEKATRONIK", "qty": 2, "loc": "MERKEZ-DEPO"},
    {"code": "90880", "name": "DST Çekvalf Teflonu", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"},
    {"code": "90567", "name": "66 Mm Teflon Takviyeli Diyafram", "cat": "MEKATRONIK", "qty": 9, "loc": "MERKEZ-DEPO"},
    {"code": "RA032DA", "name": "RA032DA09036000 Aktüatör", "cat": "MEKATRONIK", "qty": 1, "loc": "MERKEZ-DEPO"}
]

DEFAULT_SALES = [
    {"id":"S-1","date":"17.03.2025","firm":"INDIGO","ref_no":"SATIS","items":[{"code":"90567","name":"66MM TEFLON TAKVIYELI DIYAFRAM","qty":5}],"status":"APPROVED","timestamp":"2025-03-17T00:00:00"},
    {"id":"S-2","date":"02.06.2025","firm":"WBM ANDIJON","ref_no":"GARANTI","items":[{"code":"90840","name":"PISTON SENSORU:DC73L","qty":1}],"status":"APPROVED","timestamp":"2025-06-02T00:00:00"},
    {"id":"S-3","date":"11.06.2025","firm":"SAFF TEKSTIL","ref_no":"SATIS","items":[{"code":"90484","name":"3/4\" KIMYASAL VANA","qty":3}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-4","date":"11.06.2025","firm":"BEST COLOR","ref_no":"SATIS","items":[{"code":"50289","name":"VALF:SY3220-5LOU-M5-Q","qty":1}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-5","date":"11.06.2025","firm":"CHUST TEKSTIL","ref_no":"SATIS","items":[{"code":"90620","name":"PH SENSORU: SPH-1-S-6","qty":2}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-6","date":"11.06.2025","firm":"PARVOZ HUMO (HAJJ TEKSTIL)","ref_no":"SATIS","items":[{"code":"90567","name":"66MM TEFLON TAKVIYELI DIYAFRAM","qty":6}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-7","date":"11.06.2025","firm":"SOF MEGA TEKSTIL","ref_no":"SATIS","items":[{"code":"91332","name":"FESTO BASINC ANAHTARI","qty":1}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-8","date":"07.07.2025","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90567","name":"66MM TEFLON TAKVIYELI DIYAFRAM","qty":2}],"status":"APPROVED","timestamp":"2025-07-07T00:00:00"},
    {"id":"S-9","date":"15.07.2025","firm":"ASAKA TEKSTIL","ref_no":"SATIS","items":[{"code":"50257","name":"TEK ETKILI SILINDIR CD75E32-80-B","qty":1},{"code":"91071","name":"1/8\" -4MM NIKEL DIRSEK RAKOR","qty":2}],"status":"APPROVED","timestamp":"2025-07-15T00:00:00"},
    {"id":"S-10","date":"05.10.2025","firm":"ASAKA TEKSTIL","ref_no":"SATIS","items":[{"code":"91071","name":"1/8\" -4MM NIKEL DIRSEK RAKOR","qty":10}],"status":"APPROVED","timestamp":"2025-10-05T00:00:00"},
    {"id":"S-11","date":"07.10.2025","firm":"ZELAL TEKSTIL","ref_no":"SATIS","items":[{"code":"96516","name":"DST Z Ekseni Polietilen Ağızlık","qty":1}],"status":"APPROVED","timestamp":"2025-10-07T00:00:00"},
    {"id":"S-12","date":"09.10.2025","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90567","name":"66 Mm Teflon Takviyeli Diyafram","qty":5}],"status":"APPROVED","timestamp":"2025-10-09T00:00:00"},
    {"id":"S-13","date":"18.10.2025","firm":"BEST COLOR","ref_no":"SATIS","items":[{"code":"50260","name":"PISTON CD85N16-50-B","qty":2}],"status":"APPROVED","timestamp":"2025-10-18T00:00:00"},
    {"id":"S-14","date":"25.10.2025","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90620","name":"PH Sensörü: SPH-1-DJ-6M","qty":2}],"status":"APPROVED","timestamp":"2025-10-25T00:00:00"},
    {"id":"S-15","date":"04.12.2025","firm":"JIZZAX TEKSTIL","ref_no":"SATIS","items":[{"code":"90567","name":"66MM TEFLON TAKVIYELI DIYAFRAM","qty":4}],"status":"APPROVED","timestamp":"2025-12-04T00:00:00"},
    {"id":"S-16","date":"20.12.2025","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"91332","name":"FESTO BASINC ANAHTARI","qty":1}],"status":"APPROVED","timestamp":"2025-12-20T00:00:00"},
    {"id":"S-17","date":"09.02.2026","firm":"BIRYUZA TEKSTIL","ref_no":"SATIS","items":[{"code":"90567","name":"66 Mm Teflon Takviyeli Diyafram","qty":1}],"status":"APPROVED","timestamp":"2026-02-09T00:00:00"},
    {"id":"S-18","date":"21.02.2026","firm":"ZELAL TEKSTIL","ref_no":"SATIS","items":[{"code":"96516","name":"DST Z Ekseni Polietilen Ağızlık","qty":1}],"status":"APPROVED","timestamp":"2026-02-21T00:00:00"},
    {"id":"S-19","date":"26.03.2026","firm":"AKPAMUK TEKSTIL","ref_no":"SATIS","items":[{"code":"5022","name":"Salmastra","qty":1}],"status":"APPROVED","timestamp":"2026-03-26T00:00:00"},
    {"id":"S-20","date":"01.04.2026","firm":"ZELAL TEKSTIL","ref_no":"SATIS","items":[{"code":"50293","name":"VALF:SYJ3243-5LOU-Q","qty":1}],"status":"APPROVED","timestamp":"2026-04-01T00:00:00"},
    {"id":"S-21","date":"16.04.2026","firm":"BIRYUZA TEKSTIL","ref_no":"SATIS","items":[{"code":"50260","name":"PISTON CD85N16-50-B","qty":2},{"code":"91086","name":"PNOMATIK T RAKOR","qty":2},{"code":"90765","name":"RD96 CAMBAZ KOLU","qty":1}],"status":"APPROVED","timestamp":"2026-04-16T00:00:00"},
    {"id":"S-22","date":"23.04.2026","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90881","name":"DST CEKVALF YAYI","qty":2},{"code":"90879","name":"DST CEKVALF O-RINGI","qty":2}],"status":"APPROVED","timestamp":"2026-04-23T00:00:00"},
    {"id":"S-23","date":"07.05.2026","firm":"ASAKA TEKSTIL","ref_no":"SATIS","items":[{"code":"91277","name":"RD96-Mu Polietilen Ağızlık","qty":1},{"code":"50291","name":"VALF:SYJ3240-5LOU-Q","qty":1},{"code":"50289","name":"VALF:SY3220-5LOU-M5-Q","qty":1},{"code":"50287","name":"VALF:SY114-5LOU-Q","qty":2}],"status":"APPROVED","timestamp":"2026-05-07T00:00:00"},
    {"id":"S-24","date":"20.05.2026","firm":"AKPAMUK TEKSTIL","ref_no":"SATIS","items":[{"code":"90567","name":"66 Mm Teflon Takviyeli Diyafram","qty":1}],"status":"APPROVED","timestamp":"2026-05-20T00:00:00"},
    {"id":"S-25","date":"04.07.2026","firm":"DAKA TEKSTIL","ref_no":"SATIS","items":[{"code":"41316","name":"Lab120 encoder","qty":1}],"status":"APPROVED","timestamp":"2026-07-04T00:00:00"},
    {"id":"S-26","date":"06.07.2026","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90840","name":"PISTON SENSORU:DC73L","qty":2}],"status":"APPROVED","timestamp":"2026-07-06T00:00:00"},
    {"id":"S-27","date":"30.09.2026","firm":"ZELAL TEKSTIL","ref_no":"SATIS","items":[{"code":"50018","name":"VALF:SY5140-5YO-Q","qty":3}],"status":"APPROVED","timestamp":"2026-09-30T00:00:00"},
    {"id":"S-28","date":"21.10.2026","firm":"ZELAL TEKSTIL","ref_no":"SATIS","items":[{"code":"91594","name":"VALF:SY5240-5YO-Q","qty":3}],"status":"APPROVED","timestamp":"2026-10-21T00:00:00"},
    {"id":"S-29","date":"21.10.2026","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"90879","name":"DST CEKVALF O-RINGI","qty":2},{"code":"90881","name":"DST CEKVALF YAYI","qty":2},{"code":"91284","name":"BONESSI VALF:P00112200","qty":2}],"status":"APPROVED","timestamp":"2026-10-21T00:00:00"},
    # ELEKTRONİK & KONTROL SATIŞLARI
    {"id":"S-30","date":"18.04.2025","firm":"TASHTIP","ref_no":"SATIS","items":[{"code":"EDC-T7000","name":"Edc T7000","qty":1}],"status":"APPROVED","timestamp":"2025-04-18T00:00:00"},
    {"id":"S-31","date":"11.06.2025","firm":"GLOBAL","ref_no":"SATIS","items":[{"code":"AIM8-B","name":"Aim8-B","qty":1}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-32","date":"11.06.2025","firm":"ELEGANT GARANTI","ref_no":"SATIS","items":[{"code":"PD300","name":"Pd300","qty":1}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-33","date":"11.06.2025","firm":"AL HAKIM","ref_no":"SATIS","items":[{"code":"AOM8","name":"AOM8","qty":1}],"status":"APPROVED","timestamp":"2025-06-11T00:00:00"},
    {"id":"S-34","date":"12.06.2025","firm":"EZOZNUR","ref_no":"SATIS","items":[{"code":"S400","name":"S400","qty":1}],"status":"APPROVED","timestamp":"2025-06-12T00:00:00"},
    {"id":"S-35","date":"18.06.2025","firm":"UNITEX","ref_no":"SATIS","items":[{"code":"EDC-T710","name":"Edc T710","qty":1}],"status":"APPROVED","timestamp":"2025-06-18T00:00:00"},
    {"id":"S-36","date":"30.06.2025","firm":"CHUST TEKSTIL","ref_no":"SATIS","items":[{"code":"PD330","name":"Pd330","qty":5}],"status":"APPROVED","timestamp":"2025-06-30T00:00:00"},
    {"id":"S-37","date":"02.07.2025","firm":"CHUST TEKSTIL","ref_no":"SATIS","items":[{"code":"PD330","name":"Pd330","qty":5}],"status":"APPROVED","timestamp":"2025-07-02T00:00:00"},
    {"id":"S-38","date":"18.07.2025","firm":"AYA GLOBAL TEKSTIL","ref_no":"SATIS","items":[{"code":"PD330","name":"PD330","qty":1}],"status":"APPROVED","timestamp":"2025-07-18T00:00:00"},
    {"id":"S-39","date":"23.07.2025","firm":"BARKAS TEKSTIL","ref_no":"SATIS","items":[{"code":"EDC-T7700","name":"EDC T7700","qty":1}],"status":"APPROVED","timestamp":"2025-07-23T00:00:00"},
    {"id":"S-40","date":"25.07.2025","firm":"SAM RAFOAT","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":1}],"status":"APPROVED","timestamp":"2025-07-25T00:00:00"},
    {"id":"S-41","date":"23.10.2025","firm":"EZOZNUR","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":1}],"status":"APPROVED","timestamp":"2025-10-23T00:00:00"},
    {"id":"S-42","date":"06.11.2025","firm":"AYA GLOBAL TEKSTIL","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":1}],"status":"APPROVED","timestamp":"2025-11-06T00:00:00"},
    {"id":"S-43","date":"04.12.2025","firm":"SAMRAFOAT TEKSTIL","ref_no":"SATIS","items":[{"code":"PD300","name":"Pd300","qty":2}],"status":"APPROVED","timestamp":"2025-12-04T00:00:00"},
    {"id":"S-44","date":"17.12.2025","firm":"INDIGO TEKSTIL","ref_no":"SATIS","items":[{"code":"EDC-T712","name":"EDC T712","qty":1}],"status":"APPROVED","timestamp":"2025-12-17T00:00:00"},
    {"id":"S-45","date":"09.01.2026","firm":"EZOZNUR","ref_no":"SATIS","items":[{"code":"S400","name":"S400","qty":1}],"status":"APPROVED","timestamp":"2026-01-09T00:00:00"},
    {"id":"S-46","date":"13.01.2026","firm":"TERRY JAR","ref_no":"SATIS","items":[{"code":"EDC-T7701EX","name":"T7701","qty":1}],"status":"APPROVED","timestamp":"2026-01-13T00:00:00"},
    {"id":"S-47","date":"11.02.2026","firm":"BIRYUZA TEKSTIL","ref_no":"SATIS","items":[{"code":"PD350","name":"PD350","qty":1}],"status":"APPROVED","timestamp":"2026-02-11T00:00:00"},
    {"id":"S-48","date":"16.02.2026","firm":"EZOZNUR TEKSTIL","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":1}],"status":"APPROVED","timestamp":"2026-02-16T00:00:00"},
    {"id":"S-49","date":"16.03.2026","firm":"EZOZNUR TEKSTIL","ref_no":"SATIS","items":[{"code":"DOM16-PLC","name":"DOM16 PLC","qty":1}],"status":"APPROVED","timestamp":"2026-03-16T00:00:00"},
    {"id":"S-50","date":"17.03.2026","firm":"SOF MEGA TEKSTIL","ref_no":"SATIS","items":[{"code":"PD340","name":"PD340","qty":2}],"status":"APPROVED","timestamp":"2026-03-17T00:00:00"},
    {"id":"S-51","date":"24.03.2026","firm":"ELEGANT TEKSTIL","ref_no":"SATIS","items":[{"code":"S42","name":"S42","qty":1}],"status":"APPROVED","timestamp":"2026-03-24T00:00:00"},
    {"id":"S-52","date":"07.05.2026","firm":"BO'STON OPTIMAL","ref_no":"SATIS","items":[{"code":"T7PAC-DOM16V5","name":"T7PAC-DOM16V5","qty":1}],"status":"APPROVED","timestamp":"2026-05-07T00:00:00"},
    {"id":"S-53","date":"05.06.2026","firm":"AYA GLOBAL TEKSTIL","ref_no":"SATIS","items":[{"code":"PD350","name":"PD350","qty":2}],"status":"APPROVED","timestamp":"2026-06-05T00:00:00"},
    {"id":"S-54","date":"24.06.2026","firm":"CHUST TEKSTIL","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":2}],"status":"APPROVED","timestamp":"2026-06-24T00:00:00"},
    {"id":"S-55","date":"07.07.2026","firm":"AYA GLOBAL TEKSTIL","ref_no":"SATIS","items":[{"code":"PD300","name":"PD300","qty":1}],"status":"APPROVED","timestamp":"2026-07-07T00:00:00"},
    {"id":"S-56","date":"18.09.2026","firm":"MIC BRO TEKSTIL","ref_no":"SATIS","items":[{"code":"UMF-ILETISIM20","name":"Umf-ILETISIM20 kablosu","qty":1}],"status":"APPROVED","timestamp":"2026-09-18T00:00:00"},
    {"id":"S-57","date":"29.09.2026","firm":"GLOBAL ELEKTRONIK","ref_no":"SATIS","items":[{"code":"PD340","name":"PD340","qty":1}],"status":"APPROVED","timestamp":"2026-09-29T00:00:00"}
]

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class CustomReportState(StatesGroup):
    waiting_date_range = State()

def load_data(file_path, default):
    if not os.path.exists(file_path):
        save_data(file_path, default)
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_data(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

load_stocks = lambda: load_data(STOCKS_FILE, DEFAULT_STOCKS)
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, DEFAULT_SALES)
save_sales = lambda d: save_data(SALES_FILE, d)
load_tasks = lambda: load_data(TASKS_FILE, {})
save_tasks = lambda d: save_data(TASKS_FILE, d)

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try:
            await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Bildirim iletilemedi: {e}")

async def send_file_to_both(file_path: str, caption: str):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try:
            await bot.send_document(chat_id=cid, document=FSInputFile(file_path), caption=caption)
        except Exception as e:
            logging.warning(f"Dosya iletilemedi: {e}")

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📦 Parça Listesi"), KeyboardButton(text="📊 Z-Raporu Al")],
            [KeyboardButton(text="📅 Tarihli Rapor Al"), KeyboardButton(text="⏳ Bekleyen Teklifler")],
            [KeyboardButton(text="🏢 Tesis Geçmişi")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Başlat / Ana Menü"),
        BotCommand(command="stok", description="Tüm Parçalar"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu"),
        BotCommand(command="tarihraporu", description="Tarih Aralıklı Rapor"),
        BotCommand(command="ref", description="Ref No ile Sorgula (/ref 46189ND)"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
        BotCommand(command="gecmis", description="Tesis Geçmişi (/gecmis Müşteri)"),
        BotCommand(command="yardim", description="Yardım Rehberi")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.chat.id
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else message.from_user.first_name)
    await message.answer(
        f"👋 **Selam {name}! Eliar Depo & İş Santrali Devrede.**\n\n"
        f"• Tüm güncel parçalar ve geçmiş müşteri satışları sisteme yüklendi.\n"
        f"• Sıralama: Mekatronik ➔ Elektronik ➔ Kontrolörler şeklinde dökülür.\n"
        f"• Raporları Excel (.xlsx) ve PDF formatında indirebilirsiniz.\n"
        f"• `⚡ Eliar Mini App` butonundan doğrudan canlı stoğa ulaşabilirsiniz.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Komut Rehberi:**\n"
        "• `/stok` : Tüm depo parçaları\n"
        "• `/zraporu` : Haftalık Z-raporu\n"
        "• `/aylikrapor` : Aylık satış dökümü\n"
        "• `/tarihraporu` : Belirtilen tarihler arası satışlar\n"
        "• `/ref [No]` : Teklif arama\n"
        "• `/gecmis [Müşteri]` : Tesis parça geçmişi",
        parse_mode="Markdown"
    )

@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stock_list(message: types.Message):
    stocks = load_stocks()
    order = [("MEKATRONIK", "⚙️ 1. MEKATRONİK"), ("ELEKTRONIK", "⚡ 2. ELEKTRONİK"), ("KONTROL", "🎛️ 3. KONTROLÖRLER")]
    
    text = "📦 **GÜNCEL ELİAR DEPO STOKLARI**\n═══════════════════════════════\n\n"
    for cat_code, cat_title in order:
        group = [s for s in stocks if s.get("cat") == cat_code]
        text += f"**{cat_title}:**\n"
        if group:
            for s in group:
                text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
        else:
            text += "  _Kayıtlı ürün yok_\n"
        text += "\n"

    total_qty = sum(s.get("qty", 0) for s in stocks)
    text += f"═══════════════════════════════\n📊 Toplam Kalem: **{len(stocks)}** | Toplam Parça: **{total_qty} ADT**"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("ref"))
async def cmd_ref_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Lütfen Referans Numarasını yazın. (Örn: `/ref 46189ND`)", parse_mode="Markdown")
        return

    query = parts[1].strip().upper()
    sales = load_sales()
    quote = next((s for s in sales if query in str(s.get("ref_no", "")).strip().upper()), None)

    if not quote:
        await message.answer(f"🔍 `{query}` referansına ait kayıt bulunamadı.", parse_mode="Markdown")
        return

    status_str = {"APPROVED": "🟢 ONAYLANDI", "WAITING": "🟡 BEKLİYOR", "REJECTED": "🔴 İPTAL"}.get(quote.get("status"), "Bilinmiyor")
    text = (
        f"🔖 **TEKLİF [Ref: {quote.get('ref_no')}]**\n"
        f"═══════════════════════════════\n"
        f"🏭 Müşteri: `{quote.get('firm')}`\n"
        f"📌 Durum: {status_str}\n"
        f"🕒 Tarih: {quote.get('date')}\n\n"
        f"📦 **Parçalar:**\n"
    )
    for idx, item in enumerate(quote.get("items", []), 1):
        text += f"{idx}. `{item.get('code')}` — {item.get('name')} ({item.get('qty')} Adet)\n"

    if quote.get("status") == "WAITING":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Onayla", callback_data=f"q_appr:{quote.get('id')}")],
            [InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{quote.get('id')}")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")

def get_client_history_text(firm_query: str):
    sales = load_sales()
    query = firm_query.strip().lower()
    matched = [s for s in sales if query in s.get("firm", "").lower() and s.get("status") == "APPROVED"]

    if not matched:
        return f"🔍 `{firm_query}` için geçmiş onaylı kayıt bulunamadı."

    matched.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    text = f"🏢 **{matched[0].get('firm')} — PARÇA GEÇMİŞİ**\n═══════════════════════════════\n\n"
    for item in matched:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for itm in item.get("items", []):
            text += f"• 📅 `{item.get('date', '')}` ➔ **{itm.get('qty')}x** `{itm.get('code')}` ({itm.get('name')}){ref_str}\n"

    text += f"\n═══════════════════════════════\n✅ Toplam Kayıt: **{len(matched)} Sevkiyat / Hareket**"
    return text

@dp.message(Command("gecmis"))
async def cmd_history_query(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Tesis adı belirtin. (Örn: `/gecmis TERRY JAR`)", parse_mode="Markdown")
        return
    await message.answer(get_client_history_text(parts[1]), parse_mode="Markdown")

@dp.message(F.text == "🏢 Tesis Geçmişi")
async def btn_client_history(message: types.Message, state: FSMContext):
    await state.set_state(ClientHistoryState.waiting_client_name)
    await message.answer("🔍 Geçmişini aradığınız **Fabrika / Müşteri Adını** yazın:\n(Örn: `TERRY JAR`, `ZELAL`, `ASAKA`, `EZOZNUR`)", parse_mode="Markdown")

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="Markdown")

def sanitize_tr(text: str) -> str:
    m = {'ı':'i','İ':'I','ş':'s','Ş':'S','ğ':'g','Ğ':'G','ü':'u','Ü':'U','ö':'o','Ö':'O','ç':'c','Ç':'C'}
    for tr, en in m.items():
        text = text.replace(tr, en)
    return text

def generate_excel_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_Eliar_{title}_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satislar"
        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet", "Durum"]
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
                           item.get("code", ""), item.get("name", ""), item.get("qty", 1), "ONAYLANDI"])
                for c in range(1, len(headers) + 1):
                    ws.cell(row=row, column=c).border = border
                row += 1
                cnt += 1

        for idx, w in enumerate([8, 18, 14, 28, 16, 40, 10, 14], 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = w

        wb.save(fn)
        return fn
    except Exception as e:
        logging.error(f"Excel hatası: {e}")
        return None

def generate_pdf_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_Eliar_{title}_{datetime.now().strftime('%d_%m_%Y')}.pdf"
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
            Paragraph(f"DOKUM TARIHI: {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_style)
        ]

        data = [["Sira", "Tarih", "Ref No", "Musteri / Tesis", "Urun Kodu", "Urun Adi", "Adet"]]
        cnt, total = 1, 0

        for sale in sales_data:
            ref = sanitize_tr(str(sale.get("ref_no", "YOK")))
            firm = sanitize_tr(str(sale.get("firm", "")))[:24]
            date = str(sale.get("date", "")).split()[0]
            for itm in sale.get("items", []):
                q = int(itm.get("qty", 1))
                total += q
                data.append([str(cnt), date, ref, firm, sanitize_tr(str(itm.get("code", ""))), sanitize_tr(str(itm.get("name", "")))[:28], str(q)])
                cnt += 1

        data.append(["TOPLAM", "", "", "", "", "Toplam Adet:", str(total)])
        table = Table(data, colWidths=[30, 65, 60, 130, 80, 150, 50], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#161F30')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -2), 'LEFT'),
            ('ALIGN', (5, 1), (5, -2), 'LEFT'),
            ('ALIGN', (5, -1), (5, -1), 'RIGHT'),
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
        if s.get("status") != "APPROVED":
            continue
        try:
            ts = s.get("timestamp")
            if ts:
                d = datetime.fromisoformat(ts)
            else:
                d = datetime.strptime(s.get("date", "").split()[0], "%d.%m.%Y")
            if start_dt <= d <= end_dt:
                res.append(s)
        except Exception:
            res.append(s)
    return res

def build_report_text(sales_data, report_name="SATIŞ Z-RAPORU"):
    now = datetime.now()
    if not sales_data:
        return f"📊 **ELİPS TEKSTİL ELİAR {report_name}**\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\nℹ️ Bu dönem için onaylı satış kaydı bulunmamaktadır."

    text = f"📊 **ELİPS TEKSTİL ELİAR {report_name}**\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\n\n"
    total_qty, plants, cnt = 0, set(), 1

    for sale in sales_data:
        plants.add(sale.get("firm", ""))
        ref_text = f" `[Ref: {sale.get('ref_no')}]`" if sale.get('ref_no') and sale.get('ref_no') != 'YOK' else ""
        for itm in sale.get("items", []):
            q = int(itm.get("qty", 1))
            total_qty += q
            text += f"**{cnt}.** `{itm.get('code')}` — {itm.get('name')}\n   └ Miktar: **{q} Adet** | Tesis: **{sale.get('firm')}**{ref_text}\n\n"
            cnt += 1

    text += f"───────────────────────────────\n📦 Toplam Satış: **{total_qty} Adet** | Tesis Sayısı: **{len(plants)}**\n📂 Format seçin:"
    return text

@dp.message(Command("zraporu"))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    sales = filter_sales_by_range(datetime.now() - timedelta(days=7), datetime.now())
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:weekly"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:weekly")],
        [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:weekly")]
    ])
    await message.answer(build_report_text(sales, "HAFTALIK Z-RAPORU"), reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("aylikrapor"))
async def trigger_monthly_report_manual(message: types.Message):
    now = datetime.now()
    sales = filter_sales_by_range(datetime(now.year, now.month, 1), now)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:monthly"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:monthly")],
        [InlineKeyboardButton(text="📦 İkisi Birden", callback_data="dl_rep:both:monthly")]
    ])
    await message.answer(build_report_text(sales, "AYLIK SATIŞ RAPORU"), reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("tarihraporu"))
@dp.message(F.text == "📅 Tarihli Rapor Al")
async def trigger_custom_date_report(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Bugün", callback_data="date_filter:today"),
         InlineKeyboardButton(text="📅 Son 7 Gün", callback_data="date_filter:7days"),
         InlineKeyboardButton(text="🗓️ Bu Ay", callback_data="date_filter:this_month")],
        [InlineKeyboardButton(text="✍️ Özel Tarih Aralığı", callback_data="date_filter:custom")]
    ])
    await message.answer("📅 **Hangi aralığın raporunu almak istersiniz?**", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("date_filter:"))
async def process_date_filter_btn(callback: types.CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    now = datetime.now()

    if mode == "custom":
        await state.set_state(CustomReportState.waiting_date_range)
        await callback.message.answer("✍️ Format: `GG.AA.YYYY - GG.AA.YYYY` (Örn: `01.01.2025 - 29.10.2026`)", parse_mode="Markdown")
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
    await callback.message.edit_text(build_report_text(sales, title_label), reply_markup=kb, parse_mode="Markdown")
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
        await message.answer(build_report_text(sales, f"ÖZEL RAPOR ({s_str} - {e_str})"), reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await message.answer("⚠️ Hatalı format. Örnek: `01.01.2025 - 29.10.2026`", parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_rep:"))
async def handle_download_report_choice(callback: types.CallbackQuery, state: FSMContext):
    _, fmt, scope = callback.data.split(":")
    now = datetime.now()

    if scope == "weekly":
        sales, title = filter_sales_by_range(now - timedelta(days=7), now), "Haftalik_Z_Raporu"
    elif scope == "monthly":
        sales, title = filter_sales_by_range(datetime(now.year, now.month, 1), now), "Aylik_Satis_Raporu"
    else:
        st_data = await state.get_data()
        sales, title = st_data.get("last_filtered_sales", []), st_data.get("report_title", "Ozel_Rapor")

    if not sales:
        await callback.answer("Onaylı satış kaydı bulunmuyor.", show_alert=True)
        return

    await callback.answer("Hazırlanıyor...")

    if fmt in ["excel", "both"]:
        f = generate_excel_z_report(sales, title)
        if f and os.path.exists(f):
            await callback.message.answer_document(FSInputFile(f), caption=f"📊 **Elips Eliar {title} (Excel)**")

    if fmt in ["pdf", "both"]:
        f = generate_pdf_z_report(sales, title)
        if f and os.path.exists(f):
            await callback.message.answer_document(FSInputFile(f), caption=f"📑 **Elips Eliar {title} (PDF)**")

def parse_quote_media(file_path: str, is_pdf: bool = False, original_filename: str = ""):
    clean_fn = re.sub(r"(fiyat|teklif|\.pdf|\.jpg|\.png|temp_doc_\w+)", "", original_filename, flags=re.IGNORECASE).strip()
    firm = clean_fn if len(clean_fn) >= 3 else "Bilinmeyen Müşteri"
    items, ref_no = [], "BELİRTİLMEDİ"

    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            mime = "application/pdf" if is_pdf else "image/jpeg"
            with open(file_path, "rb") as f:
                b = f.read()
            prompt = "Teklifi analiz et. Saf JSON dön: {\"firm\":\"...\",\"ref_no\":\"...\",\"items\":[{\"code\":\"...\",\"name\":\"...\",\"qty\":1}]}"
            res = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, genai.types.Part.from_bytes(data=b, mime_type=mime)])
            parsed = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            if parsed.get("items"):
                return parsed
        except Exception as e:
            logging.error(f"Gemini hatası: {e}")

    return {"firm": firm, "ref_no": ref_no, "items": items}

@dp.message(F.photo | F.document)
async def handle_quote_media(message: types.Message):
    is_pdf = bool(message.document and message.document.file_name.lower().endswith(".pdf"))
    if not is_pdf and not message.photo and not (message.document and message.document.file_name.lower().endswith((".jpg", ".png", ".jpeg"))):
        return

    op_name = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    target_id = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else OMER_CHAT_ID

    doc_id = message.document.file_id if message.document else message.photo[-1].file_id
    doc_name = message.document.file_name if message.document else ""

    try:
        if is_pdf:
            await bot.send_document(target_id, doc_id, caption=f"📑 **{op_name} teklif PDF'i paylaştı!**")
        else:
            await bot.send_photo(target_id, doc_id, caption=f"📷 **{op_name} teklif görseli paylaştı!**")
    except Exception:
        pass

    file_obj = await bot.get_file(doc_id)
    tmp_path = f"tmp_{int(time.time())}.{'pdf' if is_pdf else 'jpg'}"
    await bot.download_file(file_obj.file_path, tmp_path)

    data = parse_quote_media(tmp_path, is_pdf=is_pdf, original_filename=doc_name)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    s_id = f"Q-{int(time.time()*1000)}"
    sales = load_sales()
    sales.append({
        "id": s_id, "firm": data.get("firm", "Bilinmeyen"), "ref_no": data.get("ref_no", "YOK"),
        "items": data.get("items", []), "status": "WAITING", "uploaded_by": op_name,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
    })
    save_sales(sales)

    txt = (
        f"📄 **ELİAR TEKLİF FORMU ALGILANDI!**\n"
        f"👤 Paylaşan: {op_name}\n"
        f"🏭 Müşteri: `{data.get('firm')}`\n"
        f"🔖 Ref No: `{data.get('ref_no')}`\n\n📦 **Parçalar:**\n"
    )
    for idx, itm in enumerate(data.get("items", []), 1):
        txt += f"{idx}. `{itm.get('code')}` — {itm.get('name')} ({itm.get('qty')} Adet)\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Onayla (Satış)", callback_data=f"q_appr:{s_id}")],
        [InlineKeyboardButton(text="🟡 Bekliyor", callback_data=f"q_wait:{s_id}")],
        [InlineKeyboardButton(text="🔴 Kabul Edilmedi", callback_data=f"q_rej:{s_id}")]
    ])
    await notify_both(txt, reply_markup=kb)

@dp.callback_query(F.data.startswith("q_wait:"))
async def quote_waiting(callback: types.CallbackQuery):
    s_id = callback.data.split(":")[1]
    sales = load_sales()
    sale = next((s for s in sales if s.get("id") == s_id), None)
    if sale:
        sale["status"] = "WAITING"
        save_sales(sales)
    await callback.message.edit_text(callback.message.text + "\n\n🟡 **BEKLEMEYE ALINDI**", reply_markup=None)
    await callback.answer("Beklemede")

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    s_id = callback.data.split(":")[1]
    sales, stocks = load_sales(), load_stocks()
    sale = next((s for s in sales if s.get("id") == s_id), None)

    if not sale or sale.get("status") == "APPROVED":
        await callback.answer("Zaten onaylanmış veya geçersiz.", show_alert=True)
        return

    sale["status"] = "APPROVED"
    sale["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_sales(sales)

    for itm in sale.get("items", []):
        for st in stocks:
            if st.get("code") == itm.get("code"):
                st["qty"] = max(0, st["qty"] - int(itm.get("qty", 1)))
                break
    save_stocks(stocks)

    await callback.message.edit_text(callback.message.text + "\n\n🟢 **ONAYLANDI (SATIŞ)**", reply_markup=None)
    await notify_both(f"🟢 **SATIŞ ONAYLANDI!**\n🏭 `{sale.get('firm')}` — Ref: `{sale.get('ref_no')}`\nParçalar stoktan düşüldü.")
    await callback.answer("Onaylandı.")

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    s_id = callback.data.split(":")[1]
    sales = load_sales()
    sale = next((s for s in sales if s.get("id") == s_id), None)
    if sale:
        sale["status"] = "REJECTED"
        save_sales(sales)
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **KABUL EDİLMEDİ (İPTAL)**", reply_markup=None)
    await callback.answer("İptal edildi.")

@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    waiting = [s for s in load_sales() if s.get("status") == "WAITING"]
    if not waiting:
        await message.answer("⏳ Bekleyen teklif bulunmuyor.", parse_mode="Markdown")
        return

    for s in waiting:
        txt = f"🏭 `{s.get('firm')}` | Ref: `{s.get('ref_no')}`\n"
        for itm in s.get("items", []):
            txt += f"• `{itm.get('code')}` ({itm.get('qty')} Adet)\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Onayla", callback_data=f"q_appr:{s.get('id')}"),
             InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{s.get('id')}")]
        ])
        await message.answer(txt, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try:
        p = json.loads(message.web_app_data.data)
    except Exception:
        return

    direction = p.get("direction")
    op = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    ref_id = f"REF-{message.message_id}"

    if direction == "STOCK_CHANGE" and p.get("action") == "DECREASE":
        dest, qty, code, name = p.get("destination", "Belirtilmedi"), p.get("delta", 1), p.get("code"), p.get("name")
        sales = load_sales()
        sales.append({
            "id": ref_id, "firm": dest, "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        await notify_both(f"📤 **PARÇA SATILDI / ÇIKIŞ YAPILDI!**\n📍 Tesis: `{dest}`\n⚙️ `{code}` — {name}\n📉 Adet: -{qty} | Kalan: `{p.get('current_qty')} ADT`\n👷‍♂️ Çıkış: {op}")

    elif direction == "OMER_TO_KAMIL":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Onayla", callback_data=f"otk_ok:{ref_id}"),
             InlineKeyboardButton(text="❌ Reddet", callback_data=f"otk_no:{ref_id}")]
        ])
        txt = f"🔔 **ÖMER'DEN TALEP!**\n🏭 `{p.get('firm')}` | Kişi: {p.get('contact')}\n⚙️ `{p.get('part_code')}` ({p.get('quantity')} Adet)\n📝 Not: _{p.get('notes') or 'Yok'}_"
        await bot.send_message(KAMIL_CHAT_ID, txt, reply_markup=kb, parse_mode="Markdown")
        await message.answer("✅ Talep Kamil'e iletildi.")

    elif direction == "KAMIL_TO_OMER":
        tasks = load_tasks()
        tasks[ref_id] = {"created_at": time.time(), "firm": p.get('firm'), "task_type": p.get('task_type')}
        save_tasks(tasks)

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👍 Aldım", callback_data=f"o_ack:{ref_id}"),
             InlineKeyboardButton(text="🔍 İlgileniyorum", callback_data=f"o_busy:{ref_id}")],
            [InlineKeyboardButton(text="✅ Bitirdim", callback_data=f"o_done:{ref_id}")]
        ])
        txt = f"📋 **KAMİL'DEN YENİ GÖREV!**\n🏭 `{p.get('firm')}`\n🔧 `{p.get('task_type')}`\n📝 _{p.get('instructions') or 'Yok'}_"
        await bot.send_message(OMER_CHAT_ID, txt, reply_markup=kb, parse_mode="Markdown")
        await message.answer("✅ İş emri Ömer'e iletildi.")

@dp.callback_query(F.data.startswith("otk_ok:"))
async def otk_approved(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🟢 **KAMİL ONAYLADI.**")
    await bot.send_message(OMER_CHAT_ID, "🎉 **Kamil talebini onayladı.**")
    await callback.answer()

@dp.callback_query(F.data.startswith("otk_no:"))
async def otk_rejected(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **KAMİL REDDETTİ.**")
    await bot.send_message(OMER_CHAT_ID, "❌ **Kamil talebini reddetti.**")
    await callback.answer()

@dp.callback_query(F.data.startswith("o_done:"))
async def omer_done(callback: types.CallbackQuery):
    ref_id = callback.data.split(":")[1]
    tasks = load_tasks()
    t = tasks.get(ref_id, {})
    sec = int(time.time() - (t.get("created_at") or time.time()))
    dur = f"{sec//60} dk {sec%60} sn" if sec >= 60 else f"{sec} sn"

    await callback.message.edit_text(callback.message.text + f"\n\n✅ **TAMAMLANDI** (Süre: {dur})")
    await bot.send_message(KAMIL_CHAT_ID, f"🏁 **ÖMER GÖREVİ BİTİRDİ!**\n🏭 `{t.get('firm')}` | ⏱️ {dur}")
    await callback.answer("İş tamamlandı.")

@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "📅 Tarihli Rapor Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi"]:
        return
    tid = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if message.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and message.text:
        await bot.send_message(tid, f"💬 **{sender}:** {message.text}")
        await message.reply("✓ _İletildi._", parse_mode="Markdown")

async def automated_scheduler():
    last_week, last_month = "", ""
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = filter_sales_by_range(now - timedelta(days=7), now)
            await notify_both("📢 **HAFTALIK OTOMATİK Z-RAPORU**\n\n" + build_report_text(sales, "HAFTALIK"))
            if sales:
                f_xls = generate_excel_z_report(sales, "Haftalik")
                f_pdf = generate_pdf_z_report(sales, "Haftalik")
                if f_xls: await send_file_to_both(f_xls, "📊 Excel Raporu")
                if f_pdf: await send_file_to_both(f_pdf, "📑 PDF Raporu")

        if (now + timedelta(days=1)).day == 1 and now.hour == 18 and now.minute == 0 and last_month != today:
            last_month = today
            sales = filter_sales_by_range(datetime(now.year, now.month, 1), now)
            await notify_both("📢 **AYLIK OTOMATİK Z-RAPORU**\n\n" + build_report_text(sales, "AYLIK"))
            if sales:
                f_xls = generate_excel_z_report(sales, "Aylik")
                f_pdf = generate_pdf_z_report(sales, "Aylik")
                if f_xls: await send_file_to_both(f_xls, "📊 Excel Raporu")
                if f_pdf: await send_file_to_both(f_pdf, "📑 PDF Raporu")

        await asyncio.sleep(25)

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Eliar Aktif"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    await setup_bot_commands()
    await start_dummy_server()
    asyncio.create_task(automated_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

2. index.html

<!DOCTYPE html>
<html lang="tr" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Eliar Depo</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 500: '#22c55e', 600: '#16a34a', 700: '#15803d' },
            darkbg: '#0B0F19', cardbg: '#161F30', bordercol: '#233047'
          }
        }
      }
    }
  </script>
  <style>
    body { -webkit-tap-highlight-color: transparent; }
    input, textarea, select { user-select: auto !important; pointer-events: auto !important; }
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
  </style>
</head>
<body class="bg-darkbg text-slate-100 font-sans antialiased min-h-screen pb-16">

  <!-- HEADER -->
  <header class="sticky top-0 z-40 bg-cardbg/95 backdrop-blur border-b border-bordercol px-4 py-3 flex items-center justify-between shadow-lg">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center shadow-md shadow-amber-500/20">
        <i class="fa-solid fa-bolt text-white text-lg"></i>
      </div>
      <div>
        <h1 class="text-base font-bold tracking-wide text-white leading-tight">ELIAR DEPO</h1>
        <p class="text-[10px] text-amber-400 font-mono tracking-wider font-semibold">Eliar Elips İş Paylaşımı</p>
      </div>
    </div>
    <div class="flex items-center bg-darkbg border border-bordercol rounded-xl p-1 shadow-inner">
      <button id="lang-tr" onclick="setLanguage('tr')" class="px-2.5 py-1 text-xs font-bold rounded-lg transition-all">TR</button>
      <button id="lang-uz" onclick="setLanguage('uz')" class="px-2.5 py-1 text-xs font-bold rounded-lg transition-all">UZ</button>
    </div>
  </header>

  <!-- ANA ALAN -->
  <main class="p-3.5 max-w-2xl mx-auto space-y-4">
    <div class="grid grid-cols-3 gap-1.5 p-1 bg-cardbg border border-bordercol rounded-2xl text-xs font-semibold">
      <button onclick="switchTab('stock')" id="tab-btn-stock" class="tab-btn py-3 rounded-xl transition-all flex flex-col items-center justify-center space-y-1 bg-brand-600 text-white shadow-md">
        <i class="fa-solid fa-boxes-stacked text-sm"></i><span data-i18n="nav_stock">Stok</span>
      </button>
      <button onclick="switchTab('workflow')" id="tab-btn-workflow" class="tab-btn py-3 rounded-xl transition-all flex flex-col items-center justify-center space-y-1 text-slate-400">
        <i class="fa-solid fa-share-nodes text-sm"></i><span data-i18n="nav_workflow">İş Akışı</span>
      </button>
      <button onclick="switchTab('reports')" id="tab-btn-reports" class="tab-btn py-3 rounded-xl transition-all flex flex-col items-center justify-center space-y-1 text-slate-400">
        <i class="fa-solid fa-chart-line text-sm"></i><span data-i18n="nav_reports">Rapor / Tesis</span>
      </button>
    </div>

    <!-- TAB 1: STOK -->
    <section id="tab-stock" class="tab-content space-y-3">
      <div class="flex space-x-2">
        <div class="relative flex-1">
          <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-400 text-xs"></i>
          <input type="text" id="stock-search" oninput="renderStockTable()" placeholder="Ürün kodu veya isimle ara..." 
            class="w-full bg-cardbg border border-bordercol rounded-xl pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-brand-500">
        </div>
        <button onclick="openStockModal()" class="px-3.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-bold flex items-center space-x-1 text-xs shadow-md">
          <i class="fa-solid fa-plus"></i><span data-i18n="btn_add_part">Yeni</span>
        </button>
      </div>

      <div class="flex space-x-1.5 overflow-x-auto no-scrollbar py-0.5 text-xs">
        <button onclick="filterCategory('ALL')" id="pill-ALL" class="cat-pill px-3 py-1.5 rounded-xl font-bold bg-brand-600 text-white shadow-sm whitespace-nowrap" data-i18n="cat_all">Tümü</button>
        <button onclick="filterCategory('MEKATRONIK')" id="pill-MEKATRONIK" class="cat-pill px-3 py-1.5 rounded-xl font-semibold bg-cardbg border border-bordercol text-slate-300 whitespace-nowrap" data-i18n="cat_mechatronic">1. Mekatronik</button>
        <button onclick="filterCategory('ELEKTRONIK')" id="pill-ELEKTRONIK" class="cat-pill px-3 py-1.5 rounded-xl font-semibold bg-cardbg border border-bordercol text-slate-300 whitespace-nowrap" data-i18n="cat_electronic">2. Elektronik</button>
        <button onclick="filterCategory('KONTROL')" id="pill-KONTROL" class="cat-pill px-3 py-1.5 rounded-xl font-semibold bg-cardbg border border-bordercol text-slate-300 whitespace-nowrap" data-i18n="cat_control">3. Kontrolörler</button>
      </div>
      <div id="stock-list" class="space-y-2"></div>
    </section>

    <!-- TAB 2: İŞ AKIŞI -->
    <section id="tab-workflow" class="tab-content hidden space-y-3">
      <div class="grid grid-cols-2 p-1 bg-darkbg border border-bordercol rounded-2xl gap-1">
        <button onclick="setWorkflowDirection('OMER_TO_KAMIL')" id="btn-flow-otk" class="py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 bg-brand-600 text-white shadow-md">
          <i class="fa-solid fa-user-gear"></i><span data-i18n="btn_tab_request">Sahadan Talep</span>
        </button>
        <button onclick="setWorkflowDirection('KAMIL_TO_OMER')" id="btn-flow-kto" class="py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 text-slate-400 hover:text-white">
          <i class="fa-solid fa-paper-plane"></i><span data-i18n="btn_tab_dispatch">Sahaya İş Gönder</span>
        </button>
      </div>

      <!-- FORM ÖMER -> KAMİL -->
      <div id="form-omer-to-kamil" class="bg-cardbg border border-bordercol rounded-2xl p-4 shadow-xl space-y-3">
        <div class="border-b border-bordercol pb-2">
          <h2 class="text-sm font-bold text-white flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span><span data-i18n="title_otk">Sahadan Talep (Ömer ➔ Kamil)</span>
          </h2>
        </div>
        <div>
          <label class="text-xs text-slate-400 font-semibold flex items-center"><span data-i18n="lbl_request_type">Talep Türü</span> *</label>
          <select id="otk-req-type" class="w-full mt-1 bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white focus:outline-none">
            <option value="PARCA">📦 Parça Talebi</option>
            <option value="SERVIS">🛠️ Servis Talebi</option>
            <option value="SERVIS_PARCA">⚡ Servis + Parça Talebi</option>
          </select>
        </div>
        <div class="space-y-2">
          <input type="text" id="otk-firm-name" placeholder="Fabrika / Müşteri Adı *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
          <input type="text" id="otk-firm-contact" placeholder="Yetkili Kişi & Telefon" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
        </div>
        <div class="relative">
          <div class="relative mt-1">
            <i class="fa-solid fa-magnifying-glass absolute left-3 top-2.5 text-slate-500 text-xs"></i>
            <input type="text" id="otk-part-search" oninput="searchPartsLive(this.value)" placeholder="Ürün adı veya kodu yazın... *" class="w-full bg-darkbg border border-bordercol rounded-xl pl-8 pr-8 py-2 text-xs text-white focus:outline-none">
            <button type="button" onclick="clearPartSelection()" id="otk-clear-btn" class="hidden absolute right-2.5 top-2.5 text-slate-400 hover:text-white text-xs">✕</button>
          </div>
          <div id="otk-part-dropdown" class="absolute z-30 left-0 right-0 mt-1 bg-cardbg border border-bordercol rounded-xl shadow-2xl max-h-52 overflow-y-auto hidden divide-y divide-bordercol/50"></div>
          <input type="hidden" id="otk-selected-code" value="">
        </div>
        <div class="grid grid-cols-2 gap-2">
          <input type="number" id="otk-qty" value="1" min="1" placeholder="Adet" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
          <select id="otk-priority" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
            <option value="NORMAL">Normal Servis</option>
            <option value="KRITIK" class="text-rose-400">Acil (Hat Duruşu!)</option>
          </select>
        </div>
        <textarea id="otk-notes" rows="2" placeholder="Ömer'in Notu..." class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white"></textarea>
        <button onclick="dispatchOmerToKamil()" class="w-full bg-emerald-600 hover:bg-emerald-500 py-3 rounded-xl font-bold flex items-center justify-center space-x-2 text-xs shadow-lg">
          <i class="fa-brands fa-telegram text-sm"></i><span data-i18n="btn_send_kamil">Kamil'e Gönder & Onay İste</span>
        </button>
      </div>

      <!-- FORM KAMİL -> ÖMER -->
      <div id="form-kamil-to-omer" class="bg-cardbg border border-bordercol rounded-2xl p-4 shadow-xl space-y-3 hidden">
        <div class="border-b border-bordercol pb-2">
          <h2 class="text-sm font-bold text-white flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-cyan-400"></span><span data-i18n="title_kto">Sahaya İş Gönder (Kamil ➔ Ömer)</span>
          </h2>
        </div>
        <div class="space-y-2">
          <input type="text" id="kto-firm-name" placeholder="Gidilecek Müşteri / Tesis *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
          <input type="text" id="kto-firm-contact" placeholder="Tesis Sorumlusu & Telefon" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
        </div>
        <input type="text" id="kto-task-type" placeholder="Görev Tipi / Başlığı *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
        <textarea id="kto-instructions" rows="2" placeholder="Kamil'in Talimatları..." class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white"></textarea>
        <button onclick="dispatchKamilToOmer()" class="w-full bg-cyan-600 hover:bg-cyan-500 py-3 rounded-xl font-bold flex items-center justify-center space-x-2 text-xs shadow-lg">
          <i class="fa-solid fa-paper-plane text-sm"></i><span data-i18n="btn_send_omer">Sahaya İş Gönder (Ömer'e)</span>
        </button>
      </div>
    </section>

    <!-- TAB 3: RAPORLAR -->
    <section id="tab-reports" class="tab-content hidden space-y-3">
      <div class="bg-cardbg border border-bordercol rounded-2xl p-4 space-y-3 shadow-xl">
        <div class="flex justify-between items-center border-b border-bordercol pb-2">
          <div>
            <h3 class="text-sm font-bold text-white flex items-center space-x-1.5"><i class="fa-solid fa-chart-pie text-emerald-400"></i><span>Satış Z-Raporu</span></h3>
            <p class="text-[10px] text-slate-400">ELİPS TEKSTİL ELİAR SATIŞ DÖKÜMÜ</p>
          </div>
          <div class="flex items-center space-x-1.5">
            <button onclick="exportZReportCSV()" class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-[11px] font-bold flex items-center space-x-1"><i class="fa-solid fa-file-excel"></i><span>Excel</span></button>
            <button onclick="exportZReportPDF()" class="px-2.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-[11px] font-bold flex items-center space-x-1"><i class="fa-solid fa-file-pdf"></i><span>PDF</span></button>
            <button onclick="exportZReportBoth()" class="px-2.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-[11px] font-bold flex items-center space-x-1"><i class="fa-solid fa-download"></i><span>İkisi</span></button>
          </div>
        </div>

        <div class="space-y-2 bg-darkbg p-2.5 rounded-xl border border-bordercol">
          <div class="grid grid-cols-2 gap-2 text-xs">
            <input type="date" id="z-start-date" onchange="renderZReport()" class="w-full bg-cardbg border border-bordercol rounded-lg px-2 py-1 text-white text-xs">
            <input type="date" id="z-end-date" onchange="renderZReport()" class="w-full bg-cardbg border border-bordercol rounded-lg px-2 py-1 text-white text-xs">
          </div>
          <div class="flex space-x-1.5 text-[10px]">
            <button onclick="setDatePreset('week')" class="px-2.5 py-1 bg-cardbg border border-bordercol rounded-md text-slate-300">Bu Hafta</button>
            <button onclick="setDatePreset('month')" class="px-2.5 py-1 bg-cardbg border border-bordercol rounded-md text-slate-300">Bu Ay</button>
            <button onclick="setDatePreset('all')" class="px-2.5 py-1 bg-cardbg border border-bordercol rounded-md text-slate-300">Tümü</button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 text-center">
          <div class="p-2.5 bg-darkbg border border-bordercol rounded-xl">
            <span class="text-[10px] text-slate-400 block">Toplam Parça</span>
            <span id="z-total-qty" class="text-base font-black text-emerald-400">0 ADT</span>
          </div>
          <div class="p-2.5 bg-darkbg border border-bordercol rounded-xl">
            <span class="text-[10px] text-slate-400 block">Tesis Sayısı</span>
            <span id="z-total-plants" class="text-base font-black text-cyan-400">0 Tesis</span>
          </div>
        </div>
        <div class="space-y-1.5 max-h-56 overflow-y-auto no-scrollbar" id="z-sales-list"></div>
      </div>

      <div class="bg-cardbg border border-bordercol rounded-2xl p-4 space-y-3 shadow-xl">
        <h3 class="text-xs font-bold text-white flex items-center space-x-1.5"><i class="fa-solid fa-industry text-cyan-400"></i><span>Tesis Parça Geçmişi</span></h3>
        <input type="text" id="facility-search-input" oninput="queryFacilityHistoryLive()" placeholder="Fabrika Adı Yazın..." class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
        <div id="facility-history-results" class="space-y-1.5 max-h-60 overflow-y-auto text-xs">
          <p class="text-slate-500 text-center py-2 text-[11px]">Geçmişini aradığınız fabrikayı yazın.</p>
        </div>
      </div>
    </section>
  </main>

  <!-- MODAL: STOK DÜŞ / SATIŞ -->
  <div id="modal-deduct" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm hidden items-end sm:items-center justify-center p-0 sm:p-4">
    <div class="bg-cardbg border border-bordercol w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-5 space-y-4 shadow-2xl relative z-[10000]">
      <div class="flex justify-between items-center border-b border-bordercol pb-2">
        <div>
          <h3 class="font-bold text-white text-sm">Stok Çıkışı / Satış</h3>
          <p id="deduct-part-header" class="text-[11px] text-emerald-400 font-mono mt-0.5"></p>
        </div>
        <button type="button" onclick="closeDeductModal()" class="w-8 h-8 text-slate-400 hover:text-white rounded-lg bg-darkbg">✕</button>
      </div>
      <div>
        <div class="flex justify-between text-xs text-slate-400"><span>Adet *</span><span id="deduct-current-stock"></span></div>
        <div class="flex items-center space-x-2 mt-1.5">
          <input type="number" id="deduct-qty" value="1" min="1" class="flex-1 bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-white font-bold text-center">
          <button type="button" onclick="setDeductQty(1)" class="px-2.5 py-2 bg-darkbg border border-bordercol text-xs rounded-xl">+1</button>
          <button type="button" onclick="setDeductQty(2)" class="px-2.5 py-2 bg-darkbg border border-bordercol text-xs rounded-xl">+2</button>
          <button type="button" onclick="setDeductQty(5)" class="px-2.5 py-2 bg-darkbg border border-bordercol text-xs rounded-xl">+5</button>
        </div>
      </div>
      <div>
        <label class="text-xs text-slate-400">Satılan Müşteri / Tesis *</label>
        <input type="text" id="deduct-destination" placeholder="Örn: TERRY JAR" class="w-full mt-1.5 bg-darkbg border border-bordercol rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500">
      </div>
      <input type="hidden" id="deduct-part-id" value="">
      <button type="button" onclick="confirmStockDeduction()" class="w-full bg-rose-600 hover:bg-rose-500 py-3 rounded-xl font-bold text-white text-xs">Stoktan Düş & Bildir</button>
    </div>
  </div>

  <!-- MODAL: YENİ PARÇA -->
  <div id="modal-stock" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm hidden items-end sm:items-center justify-center p-0 sm:p-4">
    <div class="bg-cardbg border border-bordercol w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl p-5 space-y-3 relative z-[10000]">
      <div class="flex justify-between items-center border-b border-bordercol pb-2">
        <h3 class="font-bold text-white text-sm">Yeni Parça Ekle</h3>
        <button type="button" onclick="closeStockModal()" class="w-8 h-8 text-slate-400 hover:text-white rounded-lg bg-darkbg">✕</button>
      </div>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <input type="text" id="m-code" placeholder="Ürün Kodu *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-white font-mono">
        <select id="m-cat" class="w-full bg-darkbg border border-bordercol rounded-xl px-2 py-2 text-white">
          <option value="MEKATRONIK">1. Mekatronik</option>
          <option value="ELEKTRONIK">2. Elektronik</option>
          <option value="KONTROL">3. Kontrolörler</option>
        </select>
      </div>
      <input type="text" id="m-name" placeholder="Parça Tanımı *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-xs text-white">
      <div class="grid grid-cols-2 gap-2 text-xs">
        <input type="number" id="m-qty" value="1" min="0" placeholder="Miktar *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-white">
        <input type="text" id="m-loc" placeholder="Konum / Raf *" class="w-full bg-darkbg border border-bordercol rounded-xl px-3 py-2 text-white">
      </div>
      <button type="button" onclick="saveStockItem()" class="w-full bg-brand-600 hover:bg-brand-500 py-2.5 rounded-xl font-bold text-white text-xs">Stoka Kaydet</button>
    </div>
  </div>

  <script>
    const tg = window.Telegram?.WebApp;
    if (tg) { tg.expand(); tg.ready(); tg.setHeaderColor('#161F30'); tg.setBackgroundColor('#0B0F19'); }

    const I18N = {
      tr: { nav_stock: "Stok", nav_workflow: "İş Akışı", nav_reports: "Rapor/Tesis", cat_all: "Tümü", cat_control: "3. Kontrolörler", cat_electronic: "2. Elektronik", cat_mechatronic: "1. Mekatronik", btn_tab_request: "Sahadan Talep", btn_tab_dispatch: "Sahaya İş Gönder", title_otk: "Sahadan Talep (Ömer ➔ Kamil)", title_kto: "Sahaya İş Gönder (Kamil ➔ Ömer)", lbl_request_type: "Talep Türü", btn_send_kamil: "Kamil'e Gönder", btn_send_omer: "Sahaya İş Gönder", btn_add_part: "Yeni", shelf: "Konum" },
      uz: { nav_stock: "Ombor", nav_workflow: "Ish Oqimi", nav_reports: "Hisobot/Tesis", cat_all: "Hammasi", cat_control: "3. Kontrollerlar", cat_electronic: "2. Elektronika", cat_mechatronic: "1. Mexatronika", btn_tab_request: "Maydondan So'rov", btn_tab_dispatch: "Maydonga Ish", title_otk: "Maydondan So'rov (O'mar ➔ Komil)", title_kto: "Maydonga Ish (Komil ➔ O'mar)", lbl_request_type: "So'rov Turi", btn_send_kamil: "Komilga Yuborish", btn_send_omer: "Maydonga Yuborish", btn_add_part: "Yangi", shelf: "Joy" }
    };

    let currentLang = localStorage.getItem('eliar_lang') || 'tr';
    let currentFlow = 'OMER_TO_KAMIL';
    let selectedCat = 'ALL';

    const INITIAL_STOCKS = [
      {"code":"PD320","name":"Pd320 Kontrol Cihazı","cat":"KONTROL","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"PD330","name":"PD330 Kontrol Cihazı","cat":"KONTROL","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"PD300","name":"Pd300 Kontrol Cihazı","cat":"KONTROL","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"PD340","name":"Pd340 Kontrol Cihazı","cat":"KONTROL","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"PD350","name":"Pd350 Kontrol Cihazı","cat":"KONTROL","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"P44","name":"P44 Kontrol Cihazı","cat":"KONTROL","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"P42","name":"P42 Kontrol Cihazı","cat":"KONTROL","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"P300","name":"P300 Kontrol Cihazı","cat":"KONTROL","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"P40","name":"P40 Kontrol Cihazı","cat":"KONTROL","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"P43","name":"P43 Kontrol Cihazı","cat":"KONTROL","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"S400","name":"S400 Kontrol Cihazı","cat":"KONTROL","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"S42","name":"S42 Kontrol Cihazı","cat":"KONTROL","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-T7000","name":"Edc T7000 Kontrol Cihazı","cat":"KONTROL","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-M7700","name":"Edc M7700 Kontrol Cihazı","cat":"KONTROL","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-T710","name":"Edc T710 Kontrol Cihazı","cat":"KONTROL","qty":9,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-T712","name":"Edc T712 Kontrol Cihazı","cat":"KONTROL","qty":8,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-T7701EX","name":"Edc T7701EX Kontrol Cihazı","cat":"KONTROL","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"EDC-T7700","name":"Edc T7700 Kontrol Cihazı","cat":"KONTROL","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"T7700","name":"T7700 Cihazı","cat":"KONTROL","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"T7701-EX-G","name":"T7701 EX G Kontrol Cihazı","cat":"KONTROL","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"PANELSET-T7701EX","name":"PANELSET-T7701 ex","cat":"KONTROL","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"PANELSET-T7700","name":"PANELSET-T7700","cat":"KONTROL","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"AIM8-A","name":"Aim8-A Analog Giriş Modülü","cat":"ELEKTRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"AIM8-B","name":"Aim8-B Analog Giriş Modülü","cat":"ELEKTRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"DIM32","name":"Dim32 Dijital Giriş Modülü","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"DOM16-PLC","name":"Dom16-PLC Dijital Çıkış Modülü","cat":"ELEKTRONIK","qty":6,"loc":"MERKEZ-DEPO"},
      {"code":"AOM8","name":"AOM8 Analog Çıkış Modülü","cat":"ELEKTRONIK","qty":7,"loc":"MERKEZ-DEPO"},
      {"code":"UMF-ILETISIM20","name":"Umf-ILETISIM20 kablosu","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"TBBPLC-F","name":"TBBPLC-F Modülü","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"POWERFAIL","name":"Powerfail Modülü","cat":"ELEKTRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"T7RACK-6-PLC","name":"T7RACK 6 PLC","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"T7RACK-10-PLC","name":"T7RACK 10 PLC","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-POWER-30","name":"T7PAC-POWER 30 Güç Modülü","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-POWER-20","name":"T7PAC-POWER 20 Güç Modülü","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-DIM32V5","name":"T7PAC-DIM32V5 Modülü","cat":"ELEKTRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-DOM32V5","name":"T7PAC-DOM32V5 Modülü","cat":"ELEKTRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-DIM16V5","name":"T7PAC-DIM16V5 Modülü","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-DOM16V5","name":"T7PAC-DOM16V5 Modülü","cat":"ELEKTRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-AIO88SV1","name":"T7PAC-AIO88SV1 Modülü","cat":"ELEKTRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-AI8SV1","name":"T7PAC-AI8SV1 Modülü","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-AO8SV1","name":"T7PAC-AO8SV1 Modülü","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"T7PAC-T7CPURIO","name":"T7PAC-T7CPURIO CPU","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"40597","name":"BES005M BALLUFF Sensör","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"40634","name":"BES0057 Balluff M12MI-NSC40B-BV03","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"41316","name":"Lab120 encoder","cat":"ELEKTRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"41396","name":"12'li Hareketli Kablo (X3-X4)","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"54626","name":"A03/0-24VDC B00123525 Bobin 5W","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90759","name":"SENSOR TUTUCU: BJ2-016","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"90761","name":"SENSOR TUTUCU: BM2-025","cat":"ELEKTRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"90840","name":"PISTON SENSORU: DC73L","cat":"ELEKTRONIK","qty":6,"loc":"MERKEZ-DEPO"},
      {"code":"91043","name":"VALF KABLOSU","cat":"ELEKTRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"91332","name":"FESTO BASINC ANAHTARI","cat":"ELEKTRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"TEST","name":"Güç Kaynağı: DRL-24V75W1AZ","cat":"ELEKTRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90620","name":"PH Sensörü: SPH-1-DJ-6M (Seko)","cat":"ELEKTRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"40025","name":"PLC CPU: DVP12SA211R: 8DI 4DO","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"SPU-PANO","name":"Saha panosu (SPU su yok)","cat":"ELEKTRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"1013","name":"Vana TORK (ko'k) 3/4\" 3 yollu + aktuator","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"1015","name":"SLD Kanal Vanası Full 3/4\" TORK 2 yollu","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"5022","name":"Salmastra (Geylani ile geldi)","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"30010","name":"EBARA 15MM SIL/SIL/VITON SALMASTRA","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"30076","name":"SANTOPRENE DIAPHRAGM FOR POMKAR PK10","cat":"MEKATRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"40647","name":"Smc CJPB15-10H6 Tek Etkili Silindir","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"41300","name":"RD96 MU Cambaz Pistonu Polietilen Takoz","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"42184","name":"PIPETLEME SIRINGA UCU","cat":"MEKATRONIK","qty":200,"loc":"MERKEZ-DEPO"},
      {"code":"50014","name":"SUSTURUCU: AN15-02: 1/4\"","cat":"MEKATRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"50018","name":"VALF: SY5140-5YO-Q","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"50090","name":"Tork Çift Etkili Aktüatör","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"50138","name":"PNOMATIK RAKOR: KQ2L04-M5A Dirsek","cat":"MEKATRONIK","qty":11,"loc":"MERKEZ-DEPO"},
      {"code":"50156","name":"T RAKOR: KQ2T06-22A: 6MM","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50227","name":"KISICILI RAKOR: AS2201F-01-04SA","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"50238","name":"SUSTURUCU: AN 120-M5 (SMC)","cat":"MEKATRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"50242","name":"KISICILI RAKOR: AS2002F-06 6MM","cat":"MEKATRONIK","qty":7,"loc":"MERKEZ-DEPO"},
      {"code":"50257","name":"PNOMATIK SILINDIR CD75E32-80-B","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"50258","name":"SILINDIR CD85N16-100-B (SMC)","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50259","name":"SILINDIR CD85N16-200-B (SMC)","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50260","name":"PISTON CD85N16-50-B","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"50261","name":"PISTON CD85N16-80-B","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50269","name":"Manifold: SS3Y1-S41-02-M5-Q 2'li Altlık","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"50270","name":"Manifold: SS3Y1-S41-04-M5-Q 4'lü Altlık","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"50287","name":"VALF: SY114-5LOU-Q","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"50289","name":"VALF: SY3220-5LOU-M5-Q","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"50291","name":"VALF: SYJ3143-5LOU-Q","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50292","name":"VALF: SYJ3240-5LOU-Q","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"50293","name":"VALF: SYJ3243-5LOU-Q","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"50294","name":"VALF: SYJ7120-5DZ-01F-Q","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"50295","name":"VALF: SYJ7220-5DZ-01F-Q","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"52156","name":"PNOMATIK T RAKOR: KQ2T06-00A: 6MM","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"54654","name":"LOP POMPA FILTRE ORINGI 30*3 MM EPDM","cat":"MEKATRONIK","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"90416","name":"SOLENOID VALF: 00125317 6013-A02","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90501","name":"SMC C76-32PS PISTON KECESI","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90715","name":"REGULATOR: AR10-M5H: 0-8 BAR","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90726","name":"HIZ AYAR VALFI: ASN2-02 1/4\"","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90765","name":"RD96 CAMBAZ KOLU","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"90766","name":"RD96 ALIMINYUM LAMA MONTAJ PARCASI","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90769","name":"RD96 BOS CAMBAZ KUTUSU","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90771","name":"RD96 CAMBAZ MEKANIZMASI","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90781","name":"SMC C85-25PS PISTON KECESI","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90782","name":"C85C16 EKLEM BAGLANTI PARCASI","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"90879","name":"DST CEKVALF O-RINGI","cat":"MEKATRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"90881","name":"DST CEKVALF YAYI","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"90946","name":"SLR1-40 FILTRE","cat":"MEKATRONIK","qty":12,"loc":"MERKEZ-DEPO"},
      {"code":"90948","name":"FIP25 BAKALIT FLANŞ","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"91035","name":"OMAL TAMIR TAKIMI: KGBV4505 3/4\"","cat":"MEKATRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"91036","name":"1\" OMAL VANA TAMIR TAKIMI","cat":"MEKATRONIK","qty":4,"loc":"MERKEZ-DEPO"},
      {"code":"91037","name":"Omal Küresel Vana Conta Tamir Takımı","cat":"MEKATRONIK","qty":5,"loc":"MERKEZ-DEPO"},
      {"code":"91045","name":"SMC KURESEL MAFSAL: KJ6D M6*1","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"91064","name":"PNOMATIK RAKOR: KQ2H04-M5A Düz","cat":"MEKATRONIK","qty":13,"loc":"MERKEZ-DEPO"},
      {"code":"91071","name":"1/8\"-4MM Nikel Dirsek / KQ2L04-01NS","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"91074","name":"PNOMATIK RAKOR: KQ2L6M5N Dirsek","cat":"MEKATRONIK","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"91086","name":"PNOMATIK T RAKOR: KQ2T04-M5A","cat":"MEKATRONIK","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"91088","name":"T RAKOR: KQ2T08-06 8-6MM","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"91238","name":"FIP25 POMPA KAPAK O-RINGI","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"91277","name":"RD96-Mu Polietilen Ağızlık","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"91284","name":"BONESSI VALF: P00112200 E1A/4","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"91303","name":"Paslanmaz Araba 4 Delikli Krom Bilyalı","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"91406","name":"FIP25 SALMASTRA","cat":"MEKATRONIK","qty":3,"loc":"MERKEZ-DEPO"},
      {"code":"91448","name":"PNOMATIK RAKOR: 57116 1/8\"-6MM Pirinç","cat":"MEKATRONIK","qty":8,"loc":"MERKEZ-DEPO"},
      {"code":"91463","name":"EUROTEC REDUCER-KAFA ADAPTORU","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"91502","name":"LAB120 mikser kayışı","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"91590","name":"U4 CEKVALF","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"91594","name":"VALF: SY5240-5YO-Q","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"91603","name":"Omal Vana: V451H405 3 Yollu L Port 3/4\"","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"91604","name":"1\" 3 Yollu L Port Vana","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"91633","name":"OMAL VIP VANA VNC10004","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"96185","name":"PISTON: CD76E32-50-B","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"96412","name":"1\" > 3/4\" Polietilen DST Çekvalf Adaptörü","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"96467","name":"Omal Aktüatör: DAN0030411S","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"96496","name":"Omal Çift Etkili Aktüatör: DAN0015411S","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"96515","name":"DST Polietilen Z Eksen dayama takozu","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"96516","name":"DST Z Ekseni Polietilen Ağızlık","cat":"MEKATRONIK","qty":0,"loc":"MERKEZ-DEPO"},
      {"code":"96517","name":"Rd96_MU Z Polietilen Z Eksen Dayama","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"96570","name":"Ø19mm Şeffaf Telli Hortum (Mavi)","cat":"MEKATRONIK","qty":10,"loc":"MERKEZ-DEPO"},
      {"code":"C-137161","name":"Tuz rafinasyon filtre kapağı","cat":"MEKATRONIK","qty":2,"loc":"MERKEZ-DEPO"},
      {"code":"90880","name":"DST Çekvalf Teflonu","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"},
      {"code":"90567","name":"66 Mm Teflon Takviyeli Diyafram","cat":"MEKATRONIK","qty":9,"loc":"MERKEZ-DEPO"},
      {"code":"RA032DA","name":"RA032DA09036000 Aktüatör","cat":"MEKATRONIK","qty":1,"loc":"MERKEZ-DEPO"}
    ];

    let stocks = JSON.parse(localStorage.getItem('eliar_stocks')) || INITIAL_STOCKS;
    let sales = JSON.parse(localStorage.getItem('eliar_sales')) || [];

    const persist = () => { localStorage.setItem('eliar_stocks', JSON.stringify(stocks)); localStorage.setItem('eliar_sales', JSON.stringify(sales)); };

    function setLanguage(lang) {
      currentLang = lang;
      localStorage.setItem('eliar_lang', lang);
      document.getElementById('lang-tr').className = lang === 'tr' ? "px-2.5 py-1 text-xs font-bold rounded-lg bg-brand-600 text-white" : "px-2.5 py-1 text-xs font-bold rounded-lg text-slate-400";
      document.getElementById('lang-uz').className = lang === 'uz' ? "px-2.5 py-1 text-xs font-bold rounded-lg bg-brand-600 text-white" : "px-2.5 py-1 text-xs font-bold rounded-lg text-slate-400";
      document.querySelectorAll('[data-i18n]').forEach(el => {
        const k = el.getAttribute('data-i18n');
        if (I18N[lang][k]) el.innerText = I18N[lang][k];
      });
      renderStockTable();
      renderZReport();
    }

    function switchTab(t) {
      document.querySelectorAll('.tab-content').forEach(e => e.classList.add('hidden'));
      document.getElementById('tab-' + t).classList.remove('hidden');
      document.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('bg-brand-600', 'text-white', 'shadow-md'); b.classList.add('text-slate-400'); });
      document.getElementById('tab-btn-' + t).classList.add('bg-brand-600', 'text-white', 'shadow-md');
      document.getElementById('tab-btn-' + t).classList.remove('text-slate-400');
      if (t === 'reports') renderZReport();
    }

    function setWorkflowDirection(dir) {
      currentFlow = dir;
      const isOtk = dir === 'OMER_TO_KAMIL';
      document.getElementById('btn-flow-otk').className = isOtk ? "py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 bg-brand-600 text-white shadow-md" : "py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 text-slate-400 hover:text-white";
      document.getElementById('btn-flow-kto').className = !isOtk ? "py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 bg-cyan-600 text-white shadow-md" : "py-2.5 px-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1.5 text-slate-400 hover:text-white";
      document.getElementById('form-omer-to-kamil').classList.toggle('hidden', !isOtk);
      document.getElementById('form-kamil-to-omer').classList.toggle('hidden', isOtk);
    }

    function filterCategory(cat) {
      selectedCat = cat;
      document.querySelectorAll('.cat-pill').forEach(btn => {
        btn.classList.remove('bg-brand-600', 'text-white', 'shadow-sm');
        btn.classList.add('bg-cardbg', 'border', 'border-bordercol', 'text-slate-300');
      });
      const active = document.getElementById('pill-' + cat);
      if (active) {
        active.classList.remove('bg-cardbg', 'border', 'border-bordercol', 'text-slate-300');
        active.classList.add('bg-brand-600', 'text-white', 'shadow-sm');
      }
      renderStockTable();
    }

    function getCategoryBadge(cat) {
      if (cat === 'MEKATRONIK') return `<span class="text-[9px] font-bold px-2 py-0.5 rounded-md bg-purple-950 text-purple-400 border border-purple-800">1. MEKATRONİK</span>`;
      if (cat === 'ELEKTRONIK') return `<span class="text-[9px] font-bold px-2 py-0.5 rounded-md bg-amber-950 text-amber-400 border border-amber-800">2. ELEKTRONİK</span>`;
      return `<span class="text-[9px] font-bold px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-400 border border-emerald-800">3. KONTROLÖR</span>`;
    }

    function renderStockTable() {
      const s = document.getElementById('stock-search')?.value.toLowerCase() || "";
      const order = { "MEKATRONIK": 1, "ELEKTRONIK": 2, "KONTROL": 3 };
      const sorted = [...stocks].sort((a, b) => (order[a.cat] || 99) - (order[b.cat] || 99));
      const filtered = sorted.filter(p => (p.name.toLowerCase().includes(s) || p.code.toLowerCase().includes(s)) && (selectedCat === 'ALL' || p.cat === selectedCat));

      const list = document.getElementById('stock-list');
      if (filtered.length === 0) {
        list.innerHTML = `<div class="p-8 text-center text-xs text-slate-500 bg-cardbg rounded-2xl border border-bordercol">Kayıtlı parça bulunamadı.</div>`;
        return;
      }

      list.innerHTML = filtered.map(i => `
        <div class="bg-cardbg border border-bordercol rounded-2xl p-3 flex justify-between items-center shadow-md">
          <div>
            <div class="flex items-center space-x-1.5">
              <span class="text-[10px] font-mono font-bold text-white bg-darkbg px-2 py-0.5 rounded border border-emerald-500/40">${i.code}</span>
              ${getCategoryBadge(i.cat || 'MEKATRONIK')}
            </div>
            <h4 class="text-xs font-semibold text-white mt-1 leading-tight">${i.name}</h4>
            <p class="text-[11px] text-slate-400 mt-0.5">${I18N[currentLang].shelf}: <span class="text-slate-300 font-mono">${i.loc}</span></p>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs font-black text-emerald-400 whitespace-nowrap">${i.qty} ADT</span>
            <div class="flex flex-col space-y-1">
              <button onclick="increaseStock('${i.code}')" class="w-6 h-6 bg-darkbg border border-bordercol hover:bg-emerald-950 text-emerald-400 rounded-lg text-xs font-bold flex items-center justify-center">+</button>
              <button onclick="openDeductModal('${i.code}')" class="w-6 h-6 bg-darkbg border border-bordercol hover:bg-rose-950 text-rose-400 rounded-lg text-xs font-bold flex items-center justify-center">-</button>
            </div>
          </div>
        </div>
      `).join('');
    }

    function openDeductModal(code) {
      const it = stocks.find(x => x.code === code);
      if (!it || it.qty <= 0) { alert("Stok tükenmiş!"); return; }
      document.getElementById('deduct-part-id').value = code;
      document.getElementById('deduct-part-header').innerText = `[${it.code}] ${it.name}`;
      document.getElementById('deduct-current-stock').innerText = `Mevcut: ${it.qty} ADT`;
      document.getElementById('deduct-qty').value = "1";
      document.getElementById('deduct-qty').max = it.qty;
      const dest = document.getElementById('deduct-destination');
      dest.value = "";
      document.getElementById('modal-deduct').classList.remove('hidden');
      document.getElementById('modal-deduct').classList.add('flex');
      setTimeout(() => dest.focus(), 100);
    }

    function closeDeductModal() {
      document.getElementById('modal-deduct').classList.add('hidden');
      document.getElementById('modal-deduct').classList.remove('flex');
    }

    function setDeductQty(d) {
      const el = document.getElementById('deduct-qty');
      let val = (parseInt(el.value) || 1) + d;
      el.value = Math.min(Math.max(val, 1), parseInt(el.max) || 999);
    }

    function confirmStockDeduction() {
      const code = document.getElementById('deduct-part-id').value;
      const it = stocks.find(x => x.code === code);
      const qty = parseInt(document.getElementById('deduct-qty').value) || 0;
      const dest = document.getElementById('deduct-destination').value.trim();

      if (!it || qty <= 0 || qty > it.qty || !dest) {
        alert("Lütfen tüm alanları doğru doldurun!"); return;
      }

      it.qty -= qty;
      sales.unshift({
        id: "Q-" + Date.now(), firm: dest, ref_no: "MANUEL-ÇIKIŞ",
        items: [{ code: it.code, name: it.name, qty }], status: "APPROVED",
        date: new Date().toLocaleString([], { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }),
        timestamp: new Date().toISOString()
      });

      persist();
      renderStockTable();
      renderZReport();
      closeDeductModal();

      if (tg?.sendData) {
        tg.sendData(JSON.stringify({
          direction: "STOCK_CHANGE", action: "DECREASE", delta: qty,
          code: it.code, name: it.name, current_qty: it.qty, destination: dest, loc: it.loc
        }));
      }
    }

    function increaseStock(code) {
      const it = stocks.find(x => x.code === code);
      if (!it || !confirm(`[${it.code}] stoğu +1 artırılsın mı?`)) return;
      it.qty += 1;
      persist();
      renderStockTable();
      if (tg?.sendData) tg.sendData(JSON.stringify({ direction: "STOCK_CHANGE", action: "INCREASE", delta: 1, code: it.code, name: it.name, current_qty: it.qty, loc: it.loc }));
    }

    function openStockModal() { document.getElementById('modal-stock').classList.remove('hidden'); document.getElementById('modal-stock').classList.add('flex'); }
    function closeStockModal() { document.getElementById('modal-stock').classList.add('hidden'); document.getElementById('modal-stock').classList.remove('flex'); }

    function saveStockItem() {
      const code = document.getElementById('m-code').value.trim();
      const cat = document.getElementById('m-cat').value;
      const name = document.getElementById('m-name').value.trim();
      const qty = parseInt(document.getElementById('m-qty').value) || 0;
      const loc = document.getElementById('m-loc').value.trim();

      if (!code || !name || !loc) { alert("Lütfen zorunlu alanları doldurun!"); return; }
      if (stocks.some(p => p.code.toLowerCase() === code.toLowerCase())) { alert("Bu ürün kodu zaten mevcut!"); return; }

      stocks.unshift({ code, cat, name, qty, loc });
      persist();
      closeStockModal();
      renderStockTable();
      if (tg?.sendData) tg.sendData(JSON.stringify({ direction: "STOCK_CHANGE", action: "NEW_ITEM", category: cat, code, name, qty, loc }));
      document.getElementById('m-code').value = "";
      document.getElementById('m-name').value = "";
      document.getElementById('m-loc').value = "";
    }

    function searchPartsLive(query) {
      const drop = document.getElementById('otk-part-dropdown');
      const q = (query || "").trim().toLowerCase();
      const matches = stocks.filter(p => p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q));
      if (!matches.length) { drop.innerHTML = `<div class="p-2 text-xs text-slate-400 text-center">Eşleşen ürün yok</div>`; drop.classList.remove('hidden'); return; }
      drop.innerHTML = matches.map(p => `
        <div onclick="selectPart('${p.code}', '${p.name.replace(/'/g, "\\'")}')" class="p-2 hover:bg-slate-800 cursor-pointer flex justify-between text-xs">
          <span><b>[${p.code}]</b> ${p.name}</span><span class="text-emerald-400 font-bold">${p.qty} ADT</span>
        </div>
      `).join('');
      drop.classList.remove('hidden');
    }

    function selectPart(code, name) {
      document.getElementById('otk-selected-code').value = code;
      document.getElementById('otk-part-search').value = `${name} [${code}]`;
      document.getElementById('otk-clear-btn').classList.remove('hidden');
      document.getElementById('otk-part-dropdown').classList.add('hidden');
    }

    function clearPartSelection() {
      document.getElementById('otk-selected-code').value = "";
      document.getElementById('otk-part-search').value = "";
      document.getElementById('otk-clear-btn').classList.add('hidden');
      document.getElementById('otk-part-dropdown').classList.add('hidden');
    }

    function dispatchOmerToKamil() {
      const firm = document.getElementById('otk-firm-name').value.trim();
      const partCode = document.getElementById('otk-selected-code').value;
      if (!firm || !partCode) { alert("Fabrika ve ürün seçilmelidir!"); return; }

      const payload = {
        direction: "OMER_TO_KAMIL", request_type: document.getElementById('otk-req-type').value,
        firm, contact: document.getElementById('otk-firm-contact').value.trim(),
        part_code: partCode, quantity: document.getElementById('otk-qty').value,
        priority: document.getElementById('otk-priority').value, notes: document.getElementById('otk-notes').value
      };
      if (tg?.sendData) tg.sendData(JSON.stringify(payload));
      alert("Talep iletildi.");
    }

    function dispatchKamilToOmer() {
      const firm = document.getElementById('kto-firm-name').value.trim();
      const taskType = document.getElementById('kto-task-type').value.trim();
      if (!firm || !taskType) { alert("Tesis ve görev tipi zorunludur!"); return; }

      const payload = {
        direction: "KAMIL_TO_OMER", firm, contact: document.getElementById('kto-firm-contact').value.trim(),
        task_type: taskType, instructions: document.getElementById('kto-instructions').value
      };
      if (tg?.sendData) tg.sendData(JSON.stringify(payload));
      alert("Görev iletildi.");
    }

    function setDatePreset(type) {
      const s = document.getElementById('z-start-date');
      const e = document.getElementById('z-end-date');
      const now = new Date();
      const iso = d => d.toISOString().split('T')[0];

      if (type === 'week') {
        const d = new Date(); d.setDate(now.getDate() - 7);
        s.value = iso(d); e.value = iso(now);
      } else if (type === 'month') {
        s.value = iso(new Date(now.getFullYear(), now.getMonth(), 1)); e.value = iso(now);
      } else {
        s.value = ""; e.value = "";
      }
      renderZReport();
    }

    function getFilteredZSales() {
      const app = sales.filter(s => s.status === 'APPROVED');
      const sVal = document.getElementById('z-start-date').value;
      const eVal = document.getElementById('z-end-date').value;
      if (!sVal && !eVal) return app;
      return app.filter(s => {
        const d = s.timestamp ? s.timestamp.split('T')[0] : "";
        return (!sVal || d >= sVal) && (!eVal || d <= eVal);
      });
    }

    function renderZReport() {
      const list = getFilteredZSales();
      let total = 0;
      const plants = new Set();
      list.forEach(s => {
        plants.add(s.firm);
        s.items.forEach(i => total += parseInt(i.qty || 1));
      });

      document.getElementById('z-total-qty').innerText = `${total} ADT`;
      document.getElementById('z-total-plants').innerText = `${plants.size} Tesis`;

      const box = document.getElementById('z-sales-list');
      if (!list.length) {
        box.innerHTML = `<p class="text-xs text-slate-500 text-center py-4 bg-darkbg rounded-xl">Kayıtlı satış bulunamadı.</p>`;
        return;
      }
      box.innerHTML = list.map(s => `
        <div class="p-2.5 bg-darkbg border border-bordercol rounded-xl text-xs flex justify-between items-center">
          <div>
            <span class="font-bold text-white">${s.firm}</span>
            <span class="text-[10px] text-slate-400 font-mono block">${s.items.map(i => `${i.code} (${i.qty} Adet)`).join(', ')}</span>
          </div>
          <span class="text-[10px] text-slate-500">${s.date.split(' ')[0]}</span>
        </div>
      `).join('');
    }

    function exportZReportCSV() {
      const list = getFilteredZSales();
      if (!list.length) { alert("Kayıt yok."); return; }
      let csv = "\uFEFFSıra;Tarih;Ref No;Müşteri / Fabrika;Ürün Kodu;Ürün Adı;Adet;Durum\n";
      let cnt = 1;
      list.forEach(s => s.items.forEach(i => {
        csv += `${cnt};${s.date};${s.ref_no || 'YOK'};${s.firm};${i.code};${i.name};${i.qty};ONAYLANDI\n`;
        cnt++;
      }));
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
      a.download = `Elips_Eliar_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
    }

    function exportZReportPDF() {
      const list = getFilteredZSales();
      if (!list.length) { alert("Kayıt yok."); return; }
      let total = 0, cnt = 1;
      let html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Rapor</title><style>
        body { font-family: sans-serif; padding: 20px; font-size: 11px; }
        h2 { text-align: center; margin: 0; font-size: 16px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #CBD5E1; padding: 6px; }
        th { background: #161F30; color: white; text-align: center; }
        .center { text-align: center; }
        .total { background: #E2E8F0; font-weight: bold; }
      </style></head><body>
      <h2>ELİPS TEKSTİL ELİAR PARÇA SATIŞ RAPORU</h2>
      <table><thead><tr><th>Sıra</th><th>Tarih</th><th>Ref No</th><th>Müşteri</th><th>Kod</th><th>Ürün Adı</th><th>Adet</th></tr></thead><tbody>`;

      list.forEach(s => s.items.forEach(i => {
        const q = parseInt(i.qty || 1);
        total += q;
        html += `<tr><td class="center">${cnt++}</td><td class="center">${s.date.split(' ')[0]}</td><td class="center">${s.ref_no || 'YOK'}</td><td><b>${s.firm}</b></td><td>${i.code}</td><td>${i.name}</td><td class="center font-bold">${q}</td></tr>`;
      }));

      html += `<tr class="total"><td colspan="6" style="text-align:right;">GENEL TOPLAM:</td><td class="center">${total} ADT</td></tr></tbody></table></body></html>`;

      const w = window.open('', '', 'width=900,height=700');
      w.document.write(html);
      w.document.close();
      w.focus();
      setTimeout(() => { w.print(); w.close(); }, 350);
    }

    function exportZReportBoth() { exportZReportCSV(); setTimeout(exportZReportPDF, 400); }

    function queryFacilityHistoryLive() {
      const q = document.getElementById('facility-search-input').value.trim().toLowerCase();
      const box = document.getElementById('facility-history-results');
      if (!q) { box.innerHTML = `<p class="text-slate-500 text-center py-2 text-[11px]">Fabrika adı giriniz.</p>`; return; }
      const matched = sales.filter(s => s.status === 'APPROVED' && s.firm.toLowerCase().includes(q));
      if (!matched.length) { box.innerHTML = `<p class="text-slate-400 text-center py-2 text-[11px]">Kayıt bulunamadı.</p>`; return; }
      box.innerHTML = matched.map(s => `
        <div class="p-2.5 bg-darkbg border border-bordercol rounded-xl space-y-1">
          <div class="flex justify-between text-[11px]"><span class="font-bold text-white">${s.firm}</span><span class="text-slate-500">${s.date}</span></div>
          <div class="border-t border-bordercol/40 pt-1">${s.items.map(i => `<p class="text-slate-300">• <span class="font-mono text-emerald-400">${i.code}</span> — ${i.name} (<b>${i.qty} Adet</b>)</p>`).join('')}</div>
        </div>
      `).join('');
    }

    window.addEventListener('DOMContentLoaded', () => {
      setLanguage(currentLang);
      setDatePreset('all');
      switchTab('stock');
    });
  </script>
</body>
</html>
