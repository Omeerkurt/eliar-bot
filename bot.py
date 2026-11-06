import json, logging, asyncio, os, re, time, html, difflib
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup, WebAppInfo, BotCommand, FSInputFile, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 1. ÖZBEKİSTAN SAAT DİLİMİ (Arka planda çalışır, ekrana teknik yazı basmaz)
os.environ['TZ'] = 'Asia/Tashkent'
if hasattr(time, 'tzset'):
    try: time.tzset()
    except Exception: pass

try:
    import zoneinfo
    UZ_TZ = zoneinfo.ZoneInfo('Asia/Tashkent')
except Exception:
    UZ_TZ = None

def get_now_uz() -> datetime:
    if UZ_TZ:
        try: return datetime.now(UZ_TZ).replace(tzinfo=None)
        except Exception: pass
    return datetime.now()

# ==============================================================================
#                     CANLI YAPILANDIRMA
# ==============================================================================
BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
TEST_MODE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
QUOTES_FILE = "submitted_quotes.json"

class QuoteState(StatesGroup):
    waiting_firm = State()
    waiting_item = State()
    waiting_qty = State()
    confirm_more = State()

class StockAddState(StatesGroup):
    waiting_query = State()
    waiting_qty = State()

# ----------------- 174 KALEMLİK FABRİKA KATALOG VERİSİ (ENVANTER SIFIRLANMASINI ENGELLER) -----------------
RAW_CATALOG_DATA = [
    ("Pd320", "Eliar Pd320 Boya Kontrolörü", "KONTROL", 4, "ELIPS-DEPO"),
    ("PD330", "Eliar PD330 Boya Kontrolörü", "KONTROL", 4, "ELIPS-DEPO"),
    ("Pd300", "Eliar Pd300 Boya Kontrol Cihazı", "KONTROL", 2, "ELIPS-DEPO"),
    ("Pd340", "Eliar Pd340 Boya Kontrolörü", "KONTROL", 2, "ELIPS-DEPO"),
    ("Pd350", "Eliar Pd350 Boya Kontrolörü", "KONTROL", 10, "ELIPS-DEPO"),
    ("S400", "Eliar S400 Kontrol Cihazı", "KONTROL", 3, "ELIPS-DEPO"),
    ("S42", "Eliar S42 Kontrol Cihazı", "KONTROL", 4, "ELIPS-DEPO"),
    ("Edc T7000", "Eliar Edc T7000 Kontrolör", "KONTROL", 2, "ELIPS-DEPO"),
    ("Edc M7700", "Eliar Edc M7700 Kontrolör", "KONTROL", 1, "ELIPS-DEPO"),
    ("Edc T710", "Eliar Edc T710 Kontrolör", "KONTROL", 9, "ELIPS-DEPO"),
    ("Edc T712", "Eliar Edc T712 Kontrolör", "KONTROL", 8, "ELIPS-DEPO"),
    ("Edc T7701EX", "Eliar Edc T7701EX Kontrolör", "KONTROL", 10, "ELIPS-DEPO"),
    ("Edc T7700", "Eliar Edc T7700 Kontrolör", "KONTROL", 4, "ELIPS-DEPO"),
    ("T7700", "Eliar T7700 Cihazı", "KONTROL", 1, "ELIPS-DEPO"),
    ("T7701 EX G", "Eliar T7701 EX G Cihazı", "KONTROL", 1, "ELIPS-DEPO"),
    ("PANELSET-T7701 ex", "PANELSET-T7701 ex Ön Panel Seti", "KONTROL", 1, "ELIPS-DEPO"),
    ("PANELSET-T7700", "PANELSET-T7700 Ön Panel Seti", "KONTROL", 1, "ELIPS-DEPO"),
    ("T7PAC-T7CPURIO", "T7PAC-T7CPURIO İşlemci Modülü", "KONTROL", 2, "ELIPS-DEPO"),
    ("40642", "Omron PLC CPU: CJ1M-CPU21", "KONTROL", 1, "ELIPS-DEPO"),
    ("CQM1H-CPU21", "Omron CQM1H-CPU21 Modül", "KONTROL", 1, "ELIPS-DEPO"),
    ("40025", "Delta PLC CPU: DVP12SA211R 8DI 4DO", "KONTROL", 1, "ELIPS-DEPO"),
    ("Aim8-A", "Aim8-A Analog Giriş Modülü", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("Aim8-B", "Aim8-B Analog Giriş Modülü", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("Dim32", "Dim32 Dijital Giriş Modülü", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("Dom16-PLC", "Dom16-PLC Dijital Çıkış Modülü", "ELEKTRONIK", 6, "ELIPS-DEPO"),
    ("AOM8", "AOM8 Analog Çıkış Modülü", "ELEKTRONIK", 7, "ELIPS-DEPO"),
    ("P44", "P44 Panel Elektronik Kartı", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("P42", "P42 Panel Elektronik Kartı", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("P300", "P300 Panel Elektronik Kartı", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("P40", "P40 Panel Elektronik Kartı", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("P43", "P43 Panel Elektronik Kartı", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("Umf-ILETISIM20", "Umf-ILETISIM20 İletişim Kablosu", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("TBBPLC-F", "TBBPLC-F Haberleşme Modülü", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("Powerfail", "Powerfail Güç Koruma Modülü", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("T7RACK 6 PLC", "T7RACK 6 PLC Taşıyıcı Rack", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("T7RACK 10 PLC", "T7RACK 10 PLC Taşıyıcı Rack", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("T7PAC-POWER 30", "T7PAC-POWER 30 Güç Kaynağı", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("T7PAC-POWER 20", "T7PAC-POWER 20 Güç Kaynağı", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("T7PAC-DIM32V5", "T7PAC-DIM32V5 Dijital Giriş Modülü", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("T7PAC-DOM32V5", "T7PAC-DOM32V5 Dijital Çıkış Modülü", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("T7PAC-DIM16V5", "T7PAC-DIM16V5 Dijital Giriş Modülü", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("T7PAC-DOM16V5", "T7PAC-DOM16V5 Dijital Çıkış Modülü", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("T7PAC-AIO88SV1", "T7PAC-AIO88SV1 Analog Giriş/Çıkış", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("T7PAC-AI8SV1", "T7PAC-AI8SV1 Analog Giriş Modülü", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("T7PAC-AO8SV1", "T7PAC-AO8SV1 Analog Çıkış Modülü", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("40645", "Güç kaynağı: CJ1W-PA202", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("40643", "Dijital giriş modülü: CJ1W-ID211", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("40644", "Dijital çıkış modülü: CJ1W-OC211", "ELEKTRONIK", 6, "ELIPS-DEPO"),
    ("90802", "Güç Kaynağı: CQM1-PA203 (omron)", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("CQM1-ID211", "Omron CQM1-ID211 Input Modül", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("41370", "Plc Çıkış Modülü: CQM1-OC222 (Omron)", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("20031", "Tork LS102M Switch Box", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("90475", "Autonics Kapasitif Sensör: CR18-8DN", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("40597", "BES005M BALLUFF Sensör", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("40634", "BES0057: Balluff M12MI-NSC40B-BV03", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("90840", "Piston sensörü: DC73L reed 3m kablolu", "ELEKTRONIK", 6, "ELIPS-DEPO"),
    ("90620", "PH Sensörü: SPH-1-DJ-6M (Seko)", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("41316", "Lab120 encoder", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("40082", "Krohne Optiflux 5300 Debimetre", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91386", "E/H DN25 (1/2\") mass Flowmetre", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("40085", "Basınç anahtarı: PMN10A 2-10 bar NO", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91332", "Basınç Anahtarı: PE-1/8-1N 1/8\" 0-8 bar", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("SPU-PANO", "Saha panosu (SPU su yok)", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91514", "Rd96 SLR1-40 AISI 316L Loblu Pompa", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90951", "Rd96 Fip25 Pompa + Motor+ Flanş", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90310", "Fip25 1\"/1\" Esnek Çarklı Pompa", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90952", "Fip25 Pompa Gövde+Kapak+Oring", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91410", "Wat 3 faz Motor 2,2 kW 3 HP 1000 d/d", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91411", "WAT Motor Ayağı (Q2E112M6C)", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41381", "Rd96 22 Li Pompa Altı Paslanmaz Tava", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90567", "Diyafram 66 Mm Teflon Takviyeli", "MEKATRONIK", 9, "ELIPS-DEPO"),
    ("90568", "66 Mm Teflon Takviyeli Diyafram Pulu", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("30076", "SANTOPRENE DIAPHRAGM PK10", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("41835", "Apexco Salmastra 7003TTG-20", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("30010", "EBARA 15MM SIL/SIL/VITON SALMASTRA", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("91407", "Fip25 Salmastra Si&Si", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("91406", "FIP25 SALMASTRA", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("5022", "Salmastra (Geylani ile geldi)", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("91128", "SLR 1-40 Mec. Seal Si.Carbon/Si.Carbide", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("90338", "SLR1-40 ASI 316L Salmastra Bileziği", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("90416", "SOLENOID VALF: 00125317 24VDC", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91472", "Solenoid Valf: L03Eb13 1/2\"", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50018", "Valf: SY5140-5YO-Q: 5/2 tek bobin 24VDC", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("91594", "Valf: SY5240-5YO-Q-5/2 Çift Bobin 24VDC", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("50287", "Valf: SY114-5LOU-Q", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("50289", "Valf: SY3220-5LOU-M5-Q: çift bobin", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("50291", "Valf: SYJ3143-5LOU-Q", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("50292", "VALF: SYJ3240-5LOU-Q", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("50293", "Valf: SYJ3243-5LOU-Q: 5/2 çift bobin", "ELEKTRONIK", 0, "ELIPS-DEPO"),
    ("50294", "VALF: SYJ7120-5DZ-01F-Q", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("50295", "VALF: SYJ7220-5DZ-01F-Q", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("91284", "Valf: P00112200 E1A/4: 3/2", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("54629", "SY114 4'lü Full Valf Grubu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54628", "SY114 2'li Full Valf Grubu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54630", "SYJ3243 2'li full valf grubu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54627", "Dst komple purge valfi komple", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("1013", "Vana TORK 3/4\" 3 yollu + aktüatör", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("1015", "SLD Kanal Vanası Full 3/4\" TORK 2 yollu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91633", "Omal VIP Vana: VNC10004 1/2\" PN10", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90817", "Omal Vana: DG424H405 3/4\" DN20 PN65", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91598", "Omal Küresel Vana: V424H405 3/4\" Paslanmaz", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90827", "Omal DG451H005 3 Yollu L Port 3/4\" PN40", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90828", "Omal Vana: DG451H006 3Yollu L Port 1\" PN40", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91603", "Omal Vana: V451H405 3 Yollu L Port 3/4\"", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91604", "V451H406 1\" Omal L Port Vana", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90484", "3/4\" Kimyasal Vana / Kür. Vana + Elcik + Adaptör", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("96219", "Küresel vana: 6310 3/8\" erkek dişi", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50054", "Küresel vana: 6310 1/4\" erkek dişi", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91035", "Omal (Tamir) Takımı: KGBV4505 3/4\"", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91036", "Kgbv4506 V451H006 Omal Vana Conta Takımı", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91037", "Omal (Tamir) Takımı: KGBV6005 3/4\"", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("91489", "3/4' RD Vana Conta Takımı", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("90547", "3 Yollu \"L\" Port 3/4\" Vana Küresi", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90548", "3 Yollu \"L\" Port 1\" Vana Kuresi", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91488", "V424H405 Vana Küresi 3/4\" RD", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50090", "Tork Çift Etkili Aktüatör", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50155", "Omal Aktüatör: DA030401S 30Nm", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96467", "Omal Aktüatör: DAN0030411S DA30", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96468", "Omal Çift Etkili Aktüatör: DAN0045412S", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96496", "Omal Çift Etkili Aktüatör: DAN0015411S", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96683", "Omal Aktüatör: SRN0015401S 15Nm", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96097", "DG424H405 Omal Aktüatör", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90832", "Omal Aktüatör: DA0015411S 15Nm", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90834", "Omal Aktüatör: DA045402S", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("RA032DA", "RA032DA09036000 Aktüatör", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("40647", "SMC CJPB15-10H6 Pin Silindir Tek Etkili", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50257", "Tek Etkili Pnömatik Silindir CD75E32-80-B", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50258", "Silindir CD85N16-100-B (SMC)", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("50259", "Silindir CD85N16-200-B (SMC)", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("50260", "Pnömatik Silindir CD85N16-50-B (SMC)", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("50261", "Silindir 80 mm Strok CD85N16-80-B", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("50262", "Silindir: CD85N25-300C-B (SMC)", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50263", "Silindir: CD85N25-400C-B Çelik (SMC)", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96185", "PISTON: CD76E32-50-B", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90501", "SMC C76-32PS PISTON KECESI", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("96501", "SMC C76-32PS Sızdırmazlık Kiti", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90781", "SMC C85-25Ps Piston Keçesi X3-X4", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90782", "C85 Serisi Silindir Eklem Bağlantı", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("91044", "SMC Küresel Mafsal: KJ10D M10*1,25", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91045", "SMC Küresel Mafsal: KJ6D M6*1", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("90715", "Regülatör: AR10-M5H: 0-8 Bar", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("92038", "Regülatör: AW30-F03DE-B: 3/8\"", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50046", "Regülatör: AW20-F02C-B (SMC)", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90725", "Hız ayar valfi: ASN2-02: 1/8\" susturuculu", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90726", "HIZ AYAR VALFI: ASN2-02 1/4\"", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50227", "KISICILI RAKOR: AS2201F-01-04SA 1/8\"-4MM", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50242", "KISICILI RAKOR: AS2002F-06 6MM HAT TIPI", "MEKATRONIK", 7, "ELIPS-DEPO"),
    ("90965", "Manometre: G27-10-R1: 0-10 Bar", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("54620", "G36-P10-01-X30 Manometre", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91285", "P00142140 U2 Çek Valf", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91590", "Çek valf: U4: 1/4\"", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91950", "Çek valf: U4: 1/4\"", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90878", "Dst16-23 Cekvalf Paslanmaz 3/4\"", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90881", "Dst Cek Valf Yayı", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("90880", "DST Çekvalf Teflonu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90879", "Dst Cek Valf Oring EPDM", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("96412", "1\" > 3/4\" Polietilen Dst Çek Valf Adaptörü", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41437", "Flowmetre Dönüşüm Flanşı", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91463", "Eurotec Reducer - Kafa Adaptörü 11-9mm", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41300", "RD96-Mu Cambaz Pistonu Polietilen Takoz", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("96515", "DST Polietilen Z Eksen dayama takozu", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("96516", "DST Z Ekseni Polietilen Ağızlık", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("96517", "Rd96_MU Z Polietilen Dayama Takozu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91277", "RD96-Mu Polietilen Ağızlık", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("90770", "RD96 Cambaz Mekanizması", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90771", "RD96 CAMBAZ MEKANIZMASI", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90765", "RD96 Cambaz Kolu", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("90767", "RD96 Cambaz Kolu Sacı", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90768", "Cambaz Kutusu Dolu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90769", "RD96 Bos Cambaz Kutusu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90766", "RD96 Aliminyum Lama Montaj Parcası", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54516", "Rd96 Full Z Axis Equipment", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54661", "Rd96 Mu 22 Y eksen Kolu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("54662", "Rd96 Mu 33 Y eksen Kolu", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91269", "RD96 X Ekseni mekanik yatak Kilidi", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91270", "RD96 Y Ekseni mekanik yatak Kilidi", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("41400", "Rd96 MU Z ekseni Yataklama Pim leri", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41401", "Rd96 MU Z eksen Gijonları 292mm*M6", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41402", "Rd96 MU Z ekseni Paslanmaz Plaka", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41442", "RD96 MU_22 Krom Kaplı Ray: Ø25 / 180 mm", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41404", "RD96 MU_33 Krom Kaplı Ray: Ø25 / 267 mm", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41444", "Krom Ray: Ø25 / 1350 mm x ekseni", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91303", "Paslanmaz Araba 4 Delikli Rexroth", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("41407P", "RD96_MU22 PVC Tabla", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("96404", "RD96-MU22 Paslanmaz Çelik Tabla", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("41406", "RD96_MU33 PVC Tabla", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("41405", "RD96-MU33 Paslanmaz Çelik Tabla", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("91268", "Rd96 Mu Fırca", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("91502", "LAB120 mikser kayışı", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("42184", "PIPETLEME SIRINGA UCU", "MEKATRONIK", 200, "ELIPS-DEPO"),
    ("C-137161", "Tuz rafinasyon filtre kapağı", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90324", "SLR1-40 Lob Anahtarı", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("90793", "Loblu Pompa Conta Teflon", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91490", "3/4 RD Vana Adaptör Bağlantı O-ringi", "MEKATRONIK", 8, "ELIPS-DEPO"),
    ("90930", "EPDM Lastik Conta 25*40 Kare Oring", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("96469", "Rakor Contası - Gasket - Nw 40 Dın", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("60002", "Klemp Contası: EPDM (DN25) 1''", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("60003", "Rakor Contası - Gasket - Nw 25 Dın", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("54654", "LOP POMPA FILTRE ORINGI 30*3 MM", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("96541", "23-35 Paslanmaz Hortum Kelepçesi", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("96540", "13-19 mm Paslanmaz Hortum Kelepçesi", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("14847", "Klemp Kelepçesi: 1\" Paslanmaz 316", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("90861", "Siyah Kauçuk Su Hortumu 16mm", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("96112", "3/4\" Siyah Kimyasal Hortum", "MEKATRONIK", 15, "ELIPS-DEPO"),
    ("91495", "3/4\" Seffaf Kimyasal Hortum", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("96570", "Ø19mm Şeffaf Telli Hortum (Mavi)", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("50024", "Hava hortumu: TU0604BU: 6mm mavi", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("50025", "Hava hortumu: TU0806BU: 8mm mavi", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("91586", "Hava hortumu: TU1065BU: 10mm mavi", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("50027", "Hava hortumu: TU0425BU: 4mm mavi", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("50138", "Pnömatik rakor: KQ2L04-M5A 4mm", "MEKATRONIK", 11, "ELIPS-DEPO"),
    ("91071", "KQ2L04-01Ns Dirsek Rakor 1/8\" 4 Mm", "MEKATRONIK", 0, "ELIPS-DEPO"),
    ("91074", "PNOMATIK RAKOR: KQ2L6M5N Dirsek", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("50040", "Dirsek Rakor 1/8x6mm / KQ2L06-01AS", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("91451", "57116 RDD 1/4-8 DİRSEK AIGNEP", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91453", "Pnömatik rakor: 57116 3/8\"-10mm dirsek", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("50219", "Pnömatik rakor: 57116 1/4\"-10mm dirsek", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("50160", "Pnömatik rakor: 57116 1/2\"-10mm dirsek", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("91448", "Pnömatik rakor: 57116 1/8\"-6mm dirsek", "MEKATRONIK", 8, "ELIPS-DEPO"),
    ("54510", "Pnömatik rakor: KQ2VS04-01AS 4mm", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91064", "Pnömatik rakor: KQ2H04-M5A 4mm düz", "MEKATRONIK", 13, "ELIPS-DEPO"),
    ("91066", "Pnömatik rakor: KQ2H06-M5A 6mm düz", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("50023", "KQ2S06-01AS: 1/8\"-6mm düz", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("91447", "Pnömatik rakor: 57020 1/4\"-10mm düz", "MEKATRONIK", 8, "ELIPS-DEPO"),
    ("50057", "Pnömatik rakor: 57020 1/4\"-8mm düz", "MEKATRONIK", 8, "ELIPS-DEPO"),
    ("50162", "1021 Düz Erkek 6/4 M5", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("42595", "1/2\"x Ø16mm Pirinç Hortum Ağzı", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("15401", "Tee rakor: 4000 1/4\" D-D-D", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("14317", "Pnömatik Tee rakor: 4000 3/8\"", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("91086", "Pnömatik T rakor: KQ2T04-M5A", "MEKATRONIK", 10, "ELIPS-DEPO"),
    ("50156", "Pnömatik T rakor: KQ2T06-00A 6mm", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("91088", "T RAKOR: KQ2T08-06 8-6MM", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("41441", "57226 1/4\"x10 Döner Tee", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("41399", "Pnömatik rakor: KQ2U04-00 4mm Y", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("15005", "Kuyruklu dirsek: 5020 1/4\" E-D", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("50161", "Nipel 2010 - M5", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("14574", "Nipel 2010 - 1/4\"", "MEKATRONIK", 8, "ELIPS-DEPO"),
    ("14577", "Nipel: 2010 3/8\"", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("50606", "Nipel 2010 - 1/2\"", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("41439", "1/4\" Paslanmaz Tek Taraflı Nipel", "MEKATRONIK", 3, "ELIPS-DEPO"),
    ("14541", "Orantılı Nipel 2030 1/4\"-1/8\"", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("96449", "Orantılı nipel: 2030 1/4\"-3/8\"", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("50549", "Redüksiyon 2090 1/4\"<1/8\"", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("41457", "Kör Tapa: M-5P: M5x0,8 (SMC)", "MEKATRONIK", 6, "ELIPS-DEPO"),
    ("50014", "Susturucu: AN15-02: 1/4\"", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("50238", "Susturucu: AN120-M5 (SMC)", "MEKATRONIK", 5, "ELIPS-DEPO"),
    ("50098", "Manifold: SS5Y5-41-04-01F-Q 4'lü", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50273", "SS5Y5-41-05-01F-Q 5'li Altlık", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50269", "Manifold: SS3Y1-S41-02-M5-Q 2'li", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50270", "Manifold: SS3Y1-S41-04-M5-Q 4'lü", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50278", "Manifold: SS5YJ3-S41-02-M5F-Q 2'li", "MEKATRONIK", 1, "ELIPS-DEPO"),
    ("50239", "3220 İçin Braket", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50008", "Tespit Elemanı AR30 / AW30", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("50010", "Tespit Elemanı : AW23P-270AS", "MEKATRONIK", 2, "ELIPS-DEPO"),
    ("90759", "Sensör tutucu: BJ2-016", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("90761", "Sensör tutucu: BM2-025 bant tipi", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("90762", "Sensör tutucu: BM2-032 32mm çap", "MEKATRONIK", 4, "ELIPS-DEPO"),
    ("41396", "12'li Hareketli Kablo X3-X4 Pistonu", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91782", "Rd96-33 Hareketli Kablo (EM)", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91271", "RD96-22 Hareketli Kablo (EM)", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("91043", "Valf Kablosu: SY114 için (EM)", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("41398", "Soket ucu SY100-30-A", "ELEKTRONIK", 5, "ELIPS-DEPO"),
    ("41290", "Soket muhafazası: HAN24 B-AGG-QB", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("41287", "Socket Cover HDC HB 24TSVU", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("41288", "Soket: HDC-HE-24BS 24 pin dişi", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("41289", "Soket: HDC-HE-24SS 24 pin erkek", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("50247", "Valf bobini: B00126625 24VDC 6W", "ELEKTRONIK", 2, "ELIPS-DEPO"),
    ("54626", "A03/0-24VDC B00123525 5W 22mm", "ELEKTRONIK", 1, "ELIPS-DEPO"),
    ("50249", "Valf soketi: M1TS2L01 24V ledli", "ELEKTRONIK", 4, "ELIPS-DEPO"),
    ("50021", "Valf soketi: DIN 43650C-C/Led 24V", "ELEKTRONIK", 3, "ELIPS-DEPO"),
    ("16016", "Paslanmaz Civata M5 x10 mm", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("16030", "Paslanmaz Civata M5 x20 mm", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("16032", "Paslanmaz Civata M6 x10 mm", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("16043", "Paslanmaz İmbus M5 Civata M5x20 mm", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("41403", "Havşa Başlı İmbus Civata M8 x 10", "MEKATRONIK", 15, "ELIPS-DEPO"),
    ("54612", "Yıldız Başlı Cıvata: M4x30mm", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("16044", "Yıldız Başlı M4 x 5 mm vida", "MEKATRONIK", 15, "ELIPS-DEPO"),
    ("16039", "Paslanmaz M5 Yaylı Rondela", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("16041", "Paslanmaz M6 Yaylı Rondela", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("16034", "Paslanmaz M5 Pul", "MEKATRONIK", 25, "ELIPS-DEPO"),
    ("16035", "Paslanmaz M6 Pul", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("11906", "Altı Köşe Somun M6", "MEKATRONIK", 20, "ELIPS-DEPO"),
    ("12302", "Fiberli Kör Somun M6", "MEKATRONIK", 15, "ELIPS-DEPO")
]

REAL_WAREHOUSE_STOCKS = [
    {"code": c, "name": n, "cat": ct, "qty": q, "loc": l}
    for c, n, ct, q, l in RAW_CATALOG_DATA
]

def sync_all_stocks_to_db():
    existing = load_data(STOCKS_FILE, [])
    existing_map = {str(s.get("code", "")).strip().lower(): s for s in existing}
    for p in REAL_WAREHOUSE_STOCKS:
        code_l = str(p.get("code", "")).strip().lower()
        if code_l not in existing_map:
            existing.append(p)
            existing_map[code_l] = p
    save_data(STOCKS_FILE, existing)
    logging.info(f"✅ Envanter Doğrulandı: {len(existing)} Kalem Parça Aktif!")

def normalize_tr(text: str) -> str:
    if not text: return ""
    m = {'ı':'i','İ':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = str(text).lower()
    for k, v in m.items(): res = res.replace(k, v)
    return res

def parse_qty_safe(text: str) -> int:
    digits = re.findall(r"\d+", str(text))
    if digits and int(digits[0]) > 0: return int(digits[0])
    raise ValueError()

def safe_stock_qty(val, default=0) -> int:
    if val is None: return default
    try: return max(0, int(val))
    except Exception:
        digits = re.findall(r"\d+", str(val))
        return int(digits[0]) if digits else default

def load_data(path, default):
    if not os.path.exists(path): save_data(path, default); return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save_data(path, data):
    tmp = f"{path}.tmp_{int(time.time()*1000)}"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

load_stocks = lambda: load_data(STOCKS_FILE, REAL_WAREHOUSE_STOCKS)
load_sales = lambda: load_data(SALES_FILE, [])
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d) if not TEST_MODE else None
save_sales = lambda d: save_data(SALES_FILE, d) if not TEST_MODE else None
save_quotes = lambda d: save_data(QUOTES_FILE, d)

def get_catalog_pdf_file():
    for name in ["Katalog.pdf", "katalog.pdf", "rd96.pdf", "RD96.pdf"]:
        if os.path.exists(name): return name
    return None

def extract_part_image_from_pdf(code: str) -> bytes:
    pdf_path = get_catalog_pdf_file()
    if not pdf_path: return None
    try:
        import fitz
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()
        for page in doc:
            rects = page.search_for(code_str)
            if rects:
                pw, ph = page.rect.width, page.rect.height
                r = rects[0]
                col = 0 if ((r.x0 + r.x1) / 2.0) < (pw / 2.0) else 1
                x0 = 8 if col == 0 else (pw / 2.0 + 2)
                x1 = (pw / 2.0 - 2) if col == 0 else (pw - 8)
                clip_rect = fitz.Rect(x0, max(10, r.y0 - 30), x1, min(ph - 10, r.y0 + 260))
                return page.get_pixmap(clip=clip_rect, dpi=180).tobytes("png")
        return None
    except Exception:
        return None

def calculate_similarity(query: str, part: dict) -> float:
    q = normalize_tr(query.strip())
    name_n, code_n = normalize_tr(part.get("name", "")), normalize_tr(part.get("code", ""))
    if q == code_n: return 1.0
    if q in code_n: return 0.95
    if q in name_n: return 0.88
    return difflib.SequenceMatcher(None, q, name_n).ratio()

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = [(p, calculate_similarity(query, p)) for p in stocks if calculate_similarity(query, p) > 0.28]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

async def notify_both(text: str, reply_markup=None):
    recipients = {OMER_CHAT_ID} if TEST_MODE else {OMER_CHAT_ID, KAMIL_CHAT_ID}
    for cid in recipients:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception: pass

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📦 Parça Listesi"), KeyboardButton(text="📥 Depoya Stok Ekle")],
            [KeyboardButton(text="📝 Eliar'dan Teklif Al"), KeyboardButton(text="📊 Z-Raporu Al")]
        ],
        resize_keyboard=True, is_persistent=False
    )

async def setup_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Ana Menü / Durum"),
        BotCommand(command="stok", description="Depo Envanteri & Yeniler"),
        BotCommand(command="stokekle", description="Stok Ekle / Yeni Tanımla"),
        BotCommand(command="stoksil", description="Parça Sil (Sessiz/Bildirimli)"),
        BotCommand(command="teklif", description="Teklif Oluştur"),
        BotCommand(command="zraporu", description="Satış Z-Raporu"),
        BotCommand(command="iptal", description="Açık İşlemi İptal Et")
    ])

@dp.message(Command("iptal", "vazgec"), StateFilter("*"))
@dp.message(F.text.casefold().in_(["iptal", "vazgeç", "vazgec"]), StateFilter("*"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ <b>İşlem iptal edildi.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

# ==============================================================================
#            KURUMSAL VE TEMİZ KARŞILAMA EKRANI (/start)
# ==============================================================================
@dp.message(CommandStart(), StateFilter("*"))
@dp.message(Command("start"), StateFilter("*"))
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    user_id = msg.chat.id
    u_name = html.escape(msg.from_user.first_name if msg.from_user else "Yetkili")
    user_title = "Ömer Bey" if user_id == OMER_CHAT_ID else ("Kamil Bey" if user_id == KAMIL_CHAT_ID else u_name)
    
    stocks = load_stocks()
    in_stock = len([s for s in stocks if safe_stock_qty(s.get("qty", 0)) > 0])
    
    welcome_text = (
        f"🏢 <b>ELİPS TEKSTİL OTOMASYON & DEPO YÖNETİMİ</b>\n"
        f"═══════════════════════════════\n"
        f"Sayın <b>{user_title}</b>, sisteme hoş geldiniz.\n\n"
        f"📊 <b>Depo Envanter Durumu:</b>\n"
        f"• Tanımlı Parça Çeşidi: <b>{len(stocks)} Kalem</b>\n"
        f"• Depoda Mevcut Ürün: <b>{in_stock} Çeşit</b>\n"
        f"• Teknik Servis & Ekran Takibi: <b>Aktif</b>\n\n"
        f"💡 <i>Aşağıdaki <b>'Eliar Mini App'</b> butonuna dokunarak canlı stokları görebilir, parça ekleyip düşebilir veya ekran tamir süreçlerini yönetebilirsiniz.</i>"
    )
    await msg.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# --- STOK EKLEME ---
@dp.message(Command("stokekle", ignore_mention=True))
@dp.message(F.text == "📥 Depoya Stok Ekle")
async def start_stock_add(msg: types.Message, state: FSMContext):
    args = msg.text.split() if msg.text else []
    if len(args) >= 3 and args[0].lower().startswith("/stokekle"):
        code_in = args[1].strip()
        try:
            qty_in = parse_qty_safe(args[2])
            stocks = load_stocks()
            target = next((s for s in stocks if str(s.get("code", "")).lower() == code_in.lower()), None)
            if target:
                target["qty"] = safe_stock_qty(target.get("qty", 0)) + qty_in
                new_q, p_name, tag = target["qty"], target.get("name", "Parça"), (" 🆕 [YENİ]" if target.get("is_new") else "")
            else:
                new_q = qty_in
                target = {"code": code_in, "name": f"Yeni Parça ({code_in})", "cat": "MEKATRONIK", "qty": new_q, "loc": "ELIPS-DEPO", "is_new": True}
                stocks.append(target)
                p_name, tag = target["name"], " 🆕 [YENİ TANIMLANDI]"
            save_stocks(stocks)
            op = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
            await notify_both(f"📥 <b>STOK EKLENDİ!</b>\n⚙️ <code>[{code_in}]</code> {html.escape(p_name)}{tag}\n📈 <b>+{qty_in}</b> | Stok: <b>{new_q} ADT</b>\n👷‍♂️ Ekleyen: <b>{op}</b>")
            return
        except Exception: pass

    await state.clear()
    await state.set_state(StockAddState.waiting_query)
    await msg.answer("📥 <b>STOK EKLE:</b> Parça kodu veya adını yazın:\n(Örn: <code>90567</code>, <code>diyafram</code>)", parse_mode="HTML")

@dp.message(StockAddState.waiting_query, ~F.text.startswith("/"))
async def stock_add_q(msg: types.Message, state: FSMContext):
    q = msg.text.strip()
    await state.update_data(raw_q=q)
    matches = find_best_matches(q)
    if not matches:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yeni Parça Olarak Tanımla", callback_data="add_unlisted")],
            [InlineKeyboardButton(text="❌ İptal", callback_data="cb_close")]
        ])
        await msg.answer(f"⚠️ <code>{html.escape(q)}</code> depoda yok. <b>[YENİ]</b> olarak eklensin mi?", reply_markup=kb, parse_mode="HTML")
        return

    top, _ = matches[0]
    if q.lower() == str(top.get('code', '')).lower():
        await state.update_data(target_part=top)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(top.get("code", ""))
        if img:
            await msg.answer_photo(BufferedInputFile(img, filename=f"{top.get('code')}.png"), caption=f"📸 <code>[{top.get('code')}]</code> {html.escape(top.get('name', ''))}")
        await msg.answer(f"🎯 <code>[{top.get('code')}]</code> {html.escape(top.get('name', ''))}\n📦 Mevcut: <b>{safe_stock_qty(top.get('qty', 0))} ADT</b>\n\n➕ Kaç adet eklenecek?", parse_mode="HTML")
        return

    btns = [[InlineKeyboardButton(text=f"👉 [{p.get('code')}] {p.get('name', '')[:25]}", callback_data=f"sel_s:{p.get('code')}")] for p, _ in matches[:5]]
    btns.append([InlineKeyboardButton(text="➕ Yeni Olarak Tanımla", callback_data="add_unlisted")])
    await msg.answer("🔍 Eşleşen parçalar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@dp.callback_query(F.data == "add_unlisted")
async def on_add_unlisted(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    q = (await state.get_data()).get("raw_q", "Özel Parça").strip()
    new_p = {"code": q.upper() if len(q) <= 12 and " " not in q else "KODSUZ", "name": q, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
    await state.update_data(target_part=new_p)
    await state.set_state(StockAddState.waiting_qty)
    await cb.message.edit_text(f"🆕 <b>Yeni Parça:</b> {html.escape(q)}\n➕ Kaç adet eklenecek?", parse_mode="HTML")

@dp.callback_query(F.data.startswith("sel_s:"))
async def on_sel_s(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if part:
        await state.update_data(target_part=part)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(part.get("code", ""))
        if img:
            await cb.message.answer_photo(BufferedInputFile(img, filename=f"{part.get('code')}.png"), caption=f"📸 <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}")
        await cb.message.answer(f"🎯 <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}\n➕ Kaç adet eklenecek?", parse_mode="HTML")

@dp.message(StockAddState.waiting_qty, ~F.text.startswith("/"))
async def stock_add_process_qty(msg: types.Message, state: FSMContext):
    try: qty = parse_qty_safe(msg.text)
    except Exception: await msg.answer("⚠️ Lütfen sayı girin (Örn: 5):"); return

    part = (await state.get_data()).get("target_part", {})
    code = str(part.get("code", "KODSUZ")).strip()
    stocks = load_stocks()
    p = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower() and code != "KODSUZ"), None)

    if p:
        p["qty"] = safe_stock_qty(p.get("qty", 0)) + qty
        new_q, tag = p["qty"], (" 🆕 [YENİ]" if p.get("is_new") else "")
    else:
        new_q = qty
        p = {"code": code, "name": part.get("name", "İsimsiz"), "cat": part.get("cat", "MEKATRONIK"), "qty": new_q, "loc": "ELIPS-DEPO", "is_new": True}
        stocks.append(p)
        tag = " 🆕 [YENİ TANIMLANDI]"

    save_stocks(stocks)
    await state.clear()
    op = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
    await notify_both(f"📥 <b>STOK EKLENDİ!</b>\n⚙️ <code>[{p.get('code')}]</code> {html.escape(p.get('name', ''))}{tag}\n📈 <b>+{qty}</b> | Yeni Stok: <b>{new_q} ADT</b>\n👷‍♂️ Ekleyen: <b>{op}</b>")

# --- SESSİZ VEYA BİLDİRİMLİ PARÇA SİLME ---
@dp.message(Command("stoksil", ignore_mention=True))
async def cmd_stock_delete(msg: types.Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2: await msg.answer("⚠️ Parça kodu girin. Örn: <code>/stoksil 90567</code>", parse_mode="HTML"); return
    code = parts[1].strip()
    target = next((s for s in load_stocks() if str(s.get("code", "")).lower() == code.lower()), None)
    if not target: await msg.answer(f"⚠️ <code>{html.escape(code)}</code> bulunamadı."); return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔕 Bildirimsiz Sil (Sessiz)", callback_data=f"del_p:{code}:silent"),
         InlineKeyboardButton(text="📢 Bildirerek Sil", callback_data=f"del_p:{code}:notify")],
        [InlineKeyboardButton(text="❌ Vazgeç", callback_data="cb_close")]
    ])
    await msg.answer(f"⚠️ <code>[{target.get('code')}]</code> {html.escape(target.get('name', ''))}\nNasıl silmek istersiniz?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("del_p:"))
async def on_del_p(cb: types.CallbackQuery):
    await cb.answer()
    _, code, mode = cb.data.split(":")
    stocks = load_stocks()
    target = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower()), None)
    if not target: await cb.message.edit_text("⚠️ Parça bulunamadı."); return

    stocks = [s for s in stocks if str(s.get("code", "")).lower() != code.lower()]
    save_stocks(stocks)

    if mode == "silent":
        await cb.message.edit_text(f"🔕 <code>[{code}]</code> parçası <b>kimseye bildirim gitmeden</b> sessizce silindi.", parse_mode="HTML")
    else:
        op = "Ömer" if cb.message.chat.id == OMER_CHAT_ID else "Kamil"
        msg = f"🗑️ <b>DEPO PARÇASI SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(target.get('name', ''))}\n👷‍♂️ Silen: <b>{op}</b>"
        await notify_both(msg)
        await cb.message.edit_text(msg, parse_mode="HTML")

# --- PARÇA LİSTESİ ---
@dp.message(Command("stok", ignore_mention=True))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stocks(msg: types.Message):
    args = msg.text.split() if msg.text else []
    only_new = len(args) > 1 and "yeni" in args[1].lower()
    stocks = load_stocks()
    if only_new: stocks = [s for s in stocks if isinstance(s, dict) and s.get("is_new")]

    available = [s for s in stocks if isinstance(s, dict) and safe_stock_qty(s.get("qty", 0)) > 0]
    text = f"📦 <b>{'✨ YENİ PARÇALAR' if only_new else 'ELİAR DEPO ENVANTERİ'}</b>\nToplam: <b>{len(stocks)} Kalem</b> | Stokta: <b>{len(available)}</b>\n═══════════════════════════════\n\n"
    for s in available[:15]:
        tag = " 🆕 [YENİ]" if s.get("is_new") else ""
        text += f"• <code>[{s.get('code', 'KODSUZ')}]</code> {html.escape(str(s.get('name', ''))[:28])}{tag} ➔ <b>{safe_stock_qty(s.get('qty', 0))} ADT</b>\n"
    if len(available) > 15: text += f"\n<i>...ve {len(available)-15} kalem daha var.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Tümü", callback_data="stk_all"), InlineKeyboardButton(text="✨ Sadece Yeniler", callback_data="stk_new")],
        [InlineKeyboardButton(text="📥 Stok Ekle", callback_data="btn_stok_ekle")]
    ])
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.in_(["stk_all", "stk_new", "btn_stok_ekle", "cb_close"]))
async def cb_stk_actions(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    if cb.data == "cb_close": await cb.message.delete(); return
    if cb.data == "btn_stok_ekle": await start_stock_add(cb.message, state); return

    only_new = cb.data == "stk_new"
    stocks = load_stocks()
    if only_new: stocks = [s for s in stocks if isinstance(s, dict) and s.get("is_new")]
    available = [s for s in stocks if isinstance(s, dict) and safe_stock_qty(s.get("qty", 0)) > 0]
    text = f"📦 <b>{'✨ YENİ PARÇALAR' if only_new else 'ELİAR DEPO ENVANTERİ'}</b>\nToplam: <b>{len(stocks)} Kalem</b> | Stokta: <b>{len(available)}</b>\n═══════════════════════════════\n\n"
    for s in available[:15]:
        tag = " 🆕 [YENİ]" if s.get("is_new") else ""
        text += f"• <code>[{s.get('code', 'KODSUZ')}]</code> {html.escape(str(s.get('name', ''))[:28])}{tag} ➔ <b>{safe_stock_qty(s.get('qty', 0))} ADT</b>\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Tümü", callback_data="stk_all"), InlineKeyboardButton(text="✨ Sadece Yeniler", callback_data="stk_new")],
        [InlineKeyboardButton(text="📥 Stok Ekle", callback_data="btn_stok_ekle")]
    ])
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# --- TEKLİF SİHİRBAZI ---
@dp.message(Command("teklif", ignore_mention=True))
@dp.message(F.text == "📝 Eliar'dan Teklif Al")
async def start_quote(msg: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteState.waiting_firm)
    await msg.answer("🏢 <b>Müşteri / Fabrika Adı:</b>", parse_mode="HTML")

@dp.message(QuoteState.waiting_firm, ~F.text.startswith("/"))
async def quote_f(msg: types.Message, state: FSMContext):
    await state.update_data(firm=msg.text.strip().upper())
    await state.set_state(QuoteState.waiting_item)
    await msg.answer("🔍 Parça kodu veya adı yazın:", parse_mode="HTML")

@dp.message(QuoteState.waiting_item, ~F.text.startswith("/"))
async def quote_i(msg: types.Message, state: FSMContext):
    q = msg.text.strip()
    matches = find_best_matches(q)
    part = matches[0][0] if matches else {"code": "KODSUZ", "name": q}
    await state.update_data(sel_part=part)
    await state.set_state(QuoteState.waiting_qty)
    img = extract_part_image_from_pdf(part.get("code", ""))
    if img:
        await msg.answer_photo(BufferedInputFile(img, filename=f"{part.get('code')}.png"), caption=f"📸 <code>[{part.get('code')}]</code>")
    await msg.answer(f"🎯 <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}\n🔢 Kaç adet teklif istenecek?", parse_mode="HTML")

@dp.message(QuoteState.waiting_qty, ~F.text.startswith("/"))
async def quote_q(msg: types.Message, state: FSMContext):
    t = msg.text.strip().lower()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="q_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir", callback_data="q_done")]
    ])
    if t in {"0", "iptal", "vazgeç", "vazgec", "geç", "gec", "atla"}:
        await state.set_state(QuoteState.confirm_more)
        await msg.answer("ℹ️ Bu parça atlandı. Devam etmek için seçim yapın:", reply_markup=kb, parse_mode="HTML")
        return

    try: qty = parse_qty_safe(msg.text)
    except Exception: await msg.answer("⚠️ Lütfen sayı girin (Vazgeçmek için 0 veya iptal):"); return

    data = await state.get_data()
    p = data.get("sel_part", {})
    items = data.get("quote_items", [])
    items.append({"code": p.get("code", "KODSUZ"), "name": p.get("name", "Parça"), "qty": qty})
    await state.update_data(quote_items=items)
    await state.set_state(QuoteState.confirm_more)
    await msg.answer(f"✅ <b>{qty} Adet</b> eklendi!", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "q_more")
async def on_q_more(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(QuoteState.waiting_item)
    await cb.message.edit_text("🔍 Yeni parçanın kodunu veya adını yazın:")

@dp.callback_query(F.data == "q_done")
async def on_q_done(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    firm, items = data.get("firm", "MÜŞTERİ"), data.get("quote_items", [])
    if not items: await cb.message.edit_text("⚠️ Teklifte parça yok."); await state.clear(); return

    fmt = f"Merhaba Nilay Hanım\n\n{firm} için aşağıdaki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    for itm in items: fmt += f"• {itm['code']} - {itm['name']} - {itm['qty']} Adet\n"
    fmt += "\nİyi çalışmalar."

    quotes = load_quotes()
    quotes.append({"id": f"TK-{int(time.time())}", "firm": firm, "date": get_now_uz().strftime("%d.%m.%Y %H:%M"), "status": "PENDING", "items": items})
    save_quotes(quotes)
    await cb.message.edit_text(f"📋 <b>KOPYALAMAYA HAZIR METİN:</b>\n\n<code>{html.escape(fmt)}</code>", parse_mode="HTML")
    await notify_both(f"📥 <b>YENİ TEKLİF:</b> {firm} ({len(items)} kalem)")
    await state.clear()

# --- WEBAPP VERİLERİ (Stok Değişimi, Sessiz Silme ve EKRAN TAMİR BİLDİRİMİ) ---
@dp.message(F.web_app_data)
async def handle_webapp(msg: types.Message):
    try: p = json.loads(msg.web_app_data.data)
    except Exception: return
    op = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
    dir_t = p.get("direction")

    # STOK DEĞİŞİMİ
    if dir_t == "STOCK_CHANGE":
        code, name, delta = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), safe_stock_qty(p.get("delta", 1), 1)
        stocks = load_stocks()
        target = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower()), None)
        if p.get("action") == "INCREASE":
            if target: target["qty"] = safe_stock_qty(target.get("qty", 0)) + delta; new_q = target["qty"]
            else: new_q = delta; stocks.append({"code": code, "name": name, "cat": "MEKATRONIK", "qty": new_q, "loc": "ELIPS-DEPO", "is_new": bool(p.get("is_new", False))})
            save_stocks(stocks)
            await notify_both(f"📥 <b>STOK ARTIRILDI</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n📈 <b>+{delta}</b> | Yeni: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>")
        elif p.get("action") == "DECREASE":
            dest = p.get("destination", "Bilinmeyen")
            if target: target["qty"] = max(0, safe_stock_qty(target.get("qty", 0)) - delta); new_q = target["qty"]
            else: new_q = safe_stock_qty(p.get("current_qty", 0))
            save_stocks(stocks)
            sales = load_sales()
            sales.append({"id": f"SLS-{int(time.time())}", "firm": dest, "source": "ELIPS_DEPO", "items": [{"code": code, "name": name, "qty": delta}], "status": "APPROVED", "date": get_now_uz().strftime("%d.%m.%Y %H:%M"), "timestamp": get_now_uz().isoformat()})
            save_sales(sales)
            await notify_both(f"📤 <b>STOK ÇIKIŞI / SATIŞ</b>\n🏢 {html.escape(dest)}\n⚙️ <code>[{code}]</code> (-{delta} Adet)\n📉 Kalan: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>")

    # BİLDİRİMSİZ / BİLDİRİMLİ SİLME
    elif dir_t == "STOCK_DELETE":
        code, name, silent = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), bool(p.get("silent", False))
        stocks = [s for s in load_stocks() if str(s.get("code", "")).lower() != code.lower()]
        save_stocks(stocks)
        if not silent:
            await notify_both(f"🗑️ <b>PARÇA SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n👷‍♂️ Yapan: <b>{op}</b>")

    # EKRAN TAMİR BİLDİRİMİ (Özellikle Türkiye'ye Gönderildiğinde Kamil'e Ulaşır)
    elif dir_t == "REPAIR_UPDATE":
        f_name, model, sn, st, issue = p.get("firm"), p.get("model"), p.get("sn"), p.get("status_text"), p.get("issue")
        await notify_both(
            f"🖥️ <b>EKRAN TAMİR / SERVİS GÜNCELLEMESİ</b>\n═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(str(f_name))}</b>\n"
            f"📱 Model: <b>{html.escape(str(model))}</b> (SN: <code>{html.escape(str(sn))}</code>)\n"
            f"⚠️ Arıza: <i>{html.escape(str(issue))}</i>\n"
            f"📍 Durum: <b>{html.escape(str(st))}</b>\n"
            f"👷‍♂️ Güncelleyen: <b>{op}</b>"
        )

# --- TELSİZ KÖPRÜSÜ ---
@dp.message(~F.text.startswith("/"))
async def chat_bridge(msg: types.Message):
    if TEST_MODE or msg.text in ["📦 Parça Listesi", "📥 Depoya Stok Ekle", "📝 Eliar'dan Teklif Al", "📊 Z-Raporu Al"]: return
    tid = KAMIL_CHAT_ID if msg.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if msg.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and msg.text:
        await bot.send_message(tid, f"💬 <b>{sender}:</b> {html.escape(msg.text)}", parse_mode="HTML")
        await msg.reply("✓ <i>İletildi.</i>", parse_mode="HTML")

# --- ZAMANLAYICI (CUMARTESİ 12:30 Z-RAPORU ÖZBEKİSTAN SAATİ) ---
async def automated_scheduler():
    last_week = ""
    while True:
        now = get_now_uz()
        today = now.strftime("%Y-%m-%d")
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = [s for s in load_sales() if s.get("status") == "APPROVED"]
            await notify_both("📢 <b>HAFTALIK Z-RAPORU (Cumartesi 12:30)</b>\n\n" + f"Toplam Satış Adedi: {sum([sum([i.get('qty',1) for i in s.get('items',[])]) for s in sales])} ADT")
        await asyncio.sleep(25)

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="Elips Depo Aktif"))
        runner = web.AppRunner(app); await runner.setup()
        await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()
    except Exception: pass

async def main():
    try:
        sync_all_stocks_to_db()
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands()
        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        logging.info(">>> ELIPS DEPO BOTU AKTIF <<<")
        await dp.start_polling(bot)
    except Exception as e: logging.error(f"Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
