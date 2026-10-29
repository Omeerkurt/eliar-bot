import json
import logging
import asyncio
import os
import re
import time
import difflib
from datetime import datetime, timedelta
from io import BytesIO
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
GEMINI_API_KEY = "AIzaSyAuUg0a1ew5V4aF1E-FTsdVinsMpXckOgQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"

# RD96 KATALOĞU (Tüm Parçalar Eksiksiz)
RD96_CATALOG = [
    {"code": "91661", "name": "Sürücü: VZAB2P2BAA V1000 3/2,2 kW", "cat": "ELEKTRONIK"},
    {"code": "40642", "name": "PLC CPU: CJ1M-CPU21", "cat": "KONTROL"},
    {"code": "40645", "name": "Güç kaynağı: CJ1W-PA202", "cat": "ELEKTRONIK"},
    {"code": "40643", "name": "Dijital giriş modülü: CJ1W-ID211", "cat": "ELEKTRONIK"},
    {"code": "40644", "name": "Dijital çıkış modülü: CJ1W-OC211", "cat": "ELEKTRONIK"},
    {"code": "90802", "name": "Güç Kaynağı: CQM1-PA203 (omron)", "cat": "ELEKTRONIK"},
    {"code": "41370", "name": "Plc Çıkış Modülü: CQM1-OC222 (Omron)", "cat": "ELEKTRONIK"},
    {"code": "41381", "name": "Rd96 22 Li Pompa Altı Paslanmaz Tava", "cat": "MEKATRONIK"},
    {"code": "91514", "name": "Rd96 SLR1-40 AISI 316L Loblu Pompa", "cat": "MEKATRONIK"},
    {"code": "91410", "name": "Wat 3 faz Motor 2,2 kW 3 HP 1000 d/d", "cat": "MEKATRONIK"},
    {"code": "91411", "name": "WAT Motor Ayağı (Q2E112M6C)", "cat": "MEKATRONIK"},
    {"code": "41436", "name": "Rd96 SLR1-40 Pompa Çıkış Bağlantı Rakor ve Dirsekleri", "cat": "MEKATRONIK"},
    {"code": "41435", "name": "Rd96 SLR1-40 Pompa Giriş Bağlantı Rakor ve Dirsekleri", "cat": "MEKATRONIK"},
    {"code": "96469", "name": "Rakor Contası - Gasket - Nw 40 Dın - EPDM", "cat": "MEKATRONIK"},
    {"code": "60002", "name": "Klemp Contası: EPDM (DN25) 1''- Ø33.7mm", "cat": "MEKATRONIK"},
    {"code": "90338", "name": "SLR1-40 ASI 316L Salmastra Bileziği (Part No 13)", "cat": "MEKATRONIK"},
    {"code": "91128", "name": "SLR 1-40 Mec. Seal Si.Carbon/Si.Carbide (Part 8-8A)", "cat": "MEKATRONIK"},
    {"code": "91516", "name": "SLR1-40 NBR O-Ring (Part No 80D)", "cat": "MEKATRONIK"},
    {"code": "41538", "name": "SLR1-40 Cover Seal (Part No: 09) (AISI-304)", "cat": "MEKATRONIK"},
    {"code": "41407", "name": "SLR1-40 Pump Housing (Part No: 01) (CF-8M)", "cat": "MEKATRONIK"},
    {"code": "41420", "name": "SLR1-40 Allen Screw (Part No: 51B) (A2)", "cat": "MEKATRONIK"},
    {"code": "93041", "name": "SLR1-40 Brass Flanş Burcu (Part No 35)", "cat": "MEKATRONIK"},
    {"code": "93035", "name": "SLR1-40 AISI 431 Wedge Lobe (Part No 2)", "cat": "MEKATRONIK"},
    {"code": "60020", "name": "SLR1-40 AISI 316 Lobe Screw (Part No 25)", "cat": "MEKATRONIK"},
    {"code": "91517", "name": "SLR1-40 NBR O-Ring (Part No 80)", "cat": "MEKATRONIK"},
    {"code": "41430", "name": "SLR1-40 O-ring (Part No: 80A) (EPDM)", "cat": "MEKATRONIK"},
    {"code": "41408", "name": "SLR1-40 Pump Cover (Part No: 03) (AISI-316)", "cat": "MEKATRONIK"},
    {"code": "41415", "name": "SLR1-40 Wing Nut (Part No: 45) (AISI 316)", "cat": "MEKATRONIK"},
    {"code": "41419", "name": "SLR1-40 Allen Screw (Part No: 51A) (8.8)", "cat": "MEKATRONIK"},
    {"code": "41414", "name": "SLR1-40 Dragging Bushing (Part No: 17B)", "cat": "MEKATRONIK"},
    {"code": "41425", "name": "SLR1-40 Safety Nut (Part No: 62) (Steel)", "cat": "MEKATRONIK"},
    {"code": "41427", "name": "SLR1-40 Conical Tightening Ring (Part No: 65A)", "cat": "MEKATRONIK"},
    {"code": "41426", "name": "SLR1-40 Safety Washer (Part No: 63) (Steel)", "cat": "MEKATRONIK"},
    {"code": "93039", "name": "SLR1-40 F 154 Motor Shaft Dişlisi (Part No 19)", "cat": "MEKATRONIK"},
    {"code": "93040", "name": "SLR1-40 F-154 Tahrik Shaft Dişlisi (Part No 19A)", "cat": "MEKATRONIK"},
    {"code": "41413", "name": "SLR1-40 Drive Shaft Bushing (Part No:17)", "cat": "MEKATRONIK"},
    {"code": "41418", "name": "SLR1-40 Allen Screw (Part No: 51) (8.8)", "cat": "MEKATRONIK"},
    {"code": "41411", "name": "SLR1-40 Bearing Stop Flange (Part No: 12A)", "cat": "MEKATRONIK"},
    {"code": "41428", "name": "SLR1-40 Ball Bearing (Part No: 70) (Steel)", "cat": "MEKATRONIK"},
    {"code": "41429", "name": "SLR1-40 Needle Bearing (Part No: 70A) (Steel)", "cat": "MEKATRONIK"},
    {"code": "93043", "name": "SLR1-40 Steel Tahrik Shaft Mili Kaması (Part 61A)", "cat": "MEKATRONIK"},
    {"code": "93042", "name": "SLR1-40 Steel Motor Shaft Mili Kaması (Part 61)", "cat": "MEKATRONIK"},
    {"code": "93037", "name": "SLR1-40 AISI 329 Tahrik Shaft (Part No 05A)", "cat": "MEKATRONIK"},
    {"code": "93036", "name": "SLR1-40 AISI 329 Motor Shaft (Part No 5)", "cat": "MEKATRONIK"},
    {"code": "60044", "name": "SLR1-40 NBR Keçe (Part No 88)", "cat": "MEKATRONIK"},
    {"code": "41434", "name": "SLR1-40 Bleeder (Part No: 87) (Plastic)", "cat": "MEKATRONIK"},
    {"code": "90946", "name": "SLR1-40 Filtre", "cat": "MEKATRONIK"},
    {"code": "41432", "name": "SLR1-40 Oil Plug (Part No: 85) (Plastic)", "cat": "MEKATRONIK"},
    {"code": "41409", "name": "SLR1-40 Support (Part No: 06) (GG-15)", "cat": "MEKATRONIK"},
    {"code": "41424", "name": "SLR1-40 Pin (Part No: 56) (F-522)", "cat": "MEKATRONIK"},
    {"code": "41433", "name": "SLR1-40 Peephole (Part No: 86) (Plastic)", "cat": "MEKATRONIK"},
    {"code": "41416", "name": "SLR1-40 Protector (Part No: 47A) (Plastic)", "cat": "MEKATRONIK"},
    {"code": "41417", "name": "SLR1-40 Screw (Part No: 50) (A2)", "cat": "MEKATRONIK"},
    {"code": "41533", "name": "SLR1-40 Part 18A (Gasket)", "cat": "MEKATRONIK"},
    {"code": "96541", "name": "23-35 Paslanmaz Hortum Kelepçesi", "cat": "MEKATRONIK"},
    {"code": "EE-ERBI-1", "name": "13-19 mm Paslanmaz Hortum Kelepçesi", "cat": "MEKATRONIK"},
    {"code": "90951", "name": "Rd96 Fip25 Pompa + Motor+ Flanş (Takım)", "cat": "MEKATRONIK"},
    {"code": "41384", "name": "R96 Fip 25 Pompa Bağlantı Çıkış Rakoru ve Dirseği", "cat": "MEKATRONIK"},
    {"code": "41383", "name": "R96 Fip 25 Pompa Bağlantı Giriş Rakoru ve Dirseği", "cat": "MEKATRONIK"},
    {"code": "90310", "name": "Fip25 1\"/1\" Esnek Çarklı Pompa (Motorsuz)", "cat": "MEKATRONIK"},
    {"code": "90952", "name": "Fip25 Pompa Gövde+Kapak+Oring", "cat": "MEKATRONIK"},
    {"code": "90332", "name": "Fip25 Pompa Mili (01-46634) (Part of 7)", "cat": "MEKATRONIK"},
    {"code": "90328", "name": "Fip25 Maşon (Sleeve 01-45214) (Part of 15)", "cat": "MEKATRONIK"},
    {"code": "90949", "name": "Fip25 Maşon Alyan Vida (0.0300.943)", "cat": "MEKATRONIK"},
    {"code": "90947", "name": "Fip25 Salmastra Sacı (Washer 01-45782)", "cat": "MEKATRONIK"},
    {"code": "90321", "name": "Fip25 Saç Vidası (0.0150.001) (Part No 12)", "cat": "MEKATRONIK"},
    {"code": "16073", "name": "Fip25 M8 Pul (Washer 0.0350.11) (Part No 11)", "cat": "MEKATRONIK"},
    {"code": "90490", "name": "Fip25 Kapak Civatası Screw 4-20x8", "cat": "MEKATRONIK"},
    {"code": "91238", "name": "Fip25 O-ring (0-2173.523) FDA", "cat": "MEKATRONIK"},
    {"code": "90333", "name": "Fip25 Kapak Pimi (Screw Stud 01-46638)", "cat": "MEKATRONIK"},
    {"code": "90948", "name": "Fip25 Bakalit Flanş (Motor Flange 01-24252)", "cat": "MEKATRONIK"},
    {"code": "91407", "name": "Fip25 Salmastra (09-46686-04) Si&Si", "cat": "MEKATRONIK"},
    {"code": "93008", "name": "Fip25 Pompa Gövdesi 09-46687-07 SH-DIN", "cat": "MEKATRONIK"},
    {"code": "90345", "name": "Fip25 FDA,EPDM (Impeller)", "cat": "MEKATRONIK"},
    {"code": "90325", "name": "Fip25 Pompa Kapağı (01-35850) Cover SH", "cat": "MEKATRONIK"},
    {"code": "90320", "name": "Fip25 Kapak Somunu (Cap screw 01-46505)", "cat": "MEKATRONIK"},
    {"code": "90950", "name": "Fip25 Motor Flanşı (Paslanmaz+Demir)", "cat": "MEKATRONIK"},
    {"code": "60003", "name": "Rakor Contası - Gasket - Nw 25 Dın - EPDM", "cat": "MEKATRONIK"},
    {"code": "96112", "name": "3/4\" Siyah Madde Verici Kimyasal Hortum (MT)", "cat": "MEKATRONIK"},
    {"code": "90827", "name": "Omal DG451H005 3 Yollu L Port 3/4\" (DN20)", "cat": "MEKATRONIK"},
    {"code": "50155", "name": "Omal Aktüatör: DA030401S DA30 30Nm", "cat": "MEKATRONIK"},
    {"code": "96467", "name": "Omal Aktüatör: DAN0030411S DA30 30Nm", "cat": "MEKATRONIK"},
    {"code": "91603", "name": "Omal Vana: V451H405 3Yollu L Port 3/4\"", "cat": "MEKATRONIK"},
    {"code": "91035", "name": "Omal (Tamir) Takımı: KGBV4505 3/4\" (DN20)", "cat": "MEKATRONIK"},
    {"code": "90547", "name": "3 Yollu \"L\" Port 3/4\" Vana Küresi", "cat": "MEKATRONIK"},
    {"code": "20031", "name": "Tork LS102M Switch Box", "cat": "ELEKTRONIK"},
    {"code": "90475", "name": "Autonics Kapasitif Sensör: CR18-8DN", "cat": "ELEKTRONIK"},
    {"code": "50160", "name": "Pnömatik rakor: 57116 1/2\"-10mm dirsek", "cat": "MEKATRONIK"},
    {"code": "91285", "name": "P00142140 U2 Çek Valf", "cat": "MEKATRONIK"},
    {"code": "50606", "name": "Nipel 2010 - 1/2\"", "cat": "MEKATRONIK"},
    {"code": "91472", "name": "Solenoid Valf: L03Eb13 1/2\" S00100400", "cat": "ELEKTRONIK"},
    {"code": "50247", "name": "Valf bobini: B00126625 FGC1 24VDC 6W", "cat": "ELEKTRONIK"},
    {"code": "50249", "name": "Valf soketi: M1TS2L01 24V ledli 11mm", "cat": "ELEKTRONIK"},
    {"code": "15401", "name": "Tee rakor: 4000 1/4\" D-D-D", "cat": "MEKATRONIK"},
    {"code": "41439", "name": "1/4\" Paslanmaz Tek Taraflı Nipel", "cat": "MEKATRONIK"},
    {"code": "91633", "name": "Omal VIP Vana: VNC10004 NBR 1/2\" PN10", "cat": "MEKATRONIK"},
    {"code": "91448", "name": "Pnömatik rakor: 57116 1/8\"-6mm dirsek", "cat": "MEKATRONIK"},
    {"code": "42595", "name": "1/2\"x Ø16mm Pirinç Altıköşe Hortum Ağzı", "cat": "MEKATRONIK"},
    {"code": "90861", "name": "Siyah Kauçuk Su Hortumu 16mm", "cat": "MEKATRONIK"},
    {"code": "90817", "name": "Omal Vana: DG424H405 3/4\" (DN20) PN65", "cat": "MEKATRONIK"},
    {"code": "96683", "name": "Omal Aktüatör: SRN0015401S SR15 15Nm", "cat": "MEKATRONIK"},
    {"code": "96097", "name": "DG424H405 Omal Aktüatör", "cat": "MEKATRONIK"},
    {"code": "91598", "name": "Omal Küresel Vana: V424H405 3/4\" Paslanmaz", "cat": "MEKATRONIK"},
    {"code": "91037", "name": "Omal (Tamir) Takımı: KGBV6005 3/4\" (DN20)", "cat": "MEKATRONIK"},
    {"code": "40082", "name": "Krohne Optiflux 5300 Magnetik Flowmeter", "cat": "ELEKTRONIK"},
    {"code": "91386", "name": "E/H DN25 (1/2\") Promass40E15 Flowmetre", "cat": "ELEKTRONIK"},
    {"code": "91488", "name": "V424H405 Vana Küresi 3/4\" RD", "cat": "MEKATRONIK"},
    {"code": "90567", "name": "Diyafram 66 Mm Teflon Takviyeli", "cat": "MEKATRONIK"},
    {"code": "90965", "name": "Manometre: G27-10-R1: AW10/AR10 için", "cat": "MEKATRONIK"},
    {"code": "40647", "name": "SMC CJPB15-10H6 Pin Silindir", "cat": "MEKATRONIK"},
    {"code": "90715", "name": "Regülatör: AR10-M5H: 0-8 Bar", "cat": "MEKATRONIK"},
    {"code": "90828", "name": "Omal Vana: DG451H006 3Yollu L Port 1\"", "cat": "MEKATRONIK"},
    {"code": "90834", "name": "Omal Aktüatör: DA045402S Flanş F03-F05", "cat": "MEKATRONIK"},
    {"code": "96468", "name": "Omal Çift Etkili Aktüatör: DAN0045412S DA45", "cat": "MEKATRONIK"},
    {"code": "91463", "name": "Eurotec Reducer Kafa Adaptörü 11mm-9mm", "cat": "MEKATRONIK"},
    {"code": "91604", "name": "V451H406 1\" Omal L Port Vana", "cat": "MEKATRONIK"},
    {"code": "90548", "name": "3 Yollu \"L\" Port 1\" Vana Küresi 545-II-F06", "cat": "MEKATRONIK"},
    {"code": "91036", "name": "Kgbv4506 V451H006 Omal Vana Conta Takımı", "cat": "MEKATRONIK"},
    {"code": "90832", "name": "Omal Aktüatör: DA0015411S DA15 15Nm", "cat": "MEKATRONIK"},
    {"code": "40634", "name": "BES0057: Balluff M12MI-NSC40B-BV03", "cat": "ELEKTRONIK"},
    {"code": "96412", "name": "1\" > 3/4\" Polietilen Dst Çek Valf Adaptörü", "cat": "MEKATRONIK"},
    {"code": "90878", "name": "Dst16-23 Çekvalf Paslanmaz 3/4\"", "cat": "MEKATRONIK"},
    {"code": "90881", "name": "Dst Çek Valf Yayı", "cat": "MEKATRONIK"},
    {"code": "90880", "name": "DST Çekvalf Teflonu", "cat": "MEKATRONIK"},
    {"code": "90879", "name": "Dst Çek Valf Oring 007.59*2.62 EPDM", "cat": "MEKATRONIK"},
    {"code": "91284", "name": "Valf: P00112200 E1A/4: 3/2 i", "cat": "ELEKTRONIK"},
    {"code": "14574", "name": "Nipel 2010 - 1/4\"", "cat": "MEKATRONIK"},
    {"code": "14541", "name": "Orantılı Nipel 2030 1/4\"-1/8\"", "cat": "MEKATRONIK"},
    {"code": "91332", "name": "Basınç Anahtarı: PE-1/8-1N 0-8 bar", "cat": "ELEKTRONIK"},
    {"code": "50219", "name": "Pnömatik rakor: 57116 1/4\"-10mm dirsek", "cat": "MEKATRONIK"},
    {"code": "54626", "name": "Valf Bobini: A03/0-24VDC B00123525 5W", "cat": "ELEKTRONIK"},
    {"code": "41441", "name": "57226 1/4\"x10 Döner Tee", "cat": "MEKATRONIK"},
    {"code": "91447", "name": "Pnömatik rakor: 57020 1/4\"-10mm düz erkek", "cat": "MEKATRONIK"},
    {"code": "50057", "name": "Pnömatik rakor: 57020 1/4\"-8mm düz erkek", "cat": "MEKATRONIK"},
    {"code": "54612", "name": "Yıldız Başlı Cıvata: M4x30mm", "cat": "MEKATRONIK"},
    {"code": "50098", "name": "Manifold: SS5Y5-41-04-01F-Q 4'lü", "cat": "MEKATRONIK"},
    {"code": "50018", "name": "Valf: SY5140-5YO-Q 5/2 tek bobin 24VDC", "cat": "ELEKTRONIK"},
    {"code": "91594", "name": "Valf: SY5240-5YO-Q-5/2 Çift Bobin 24VDC", "cat": "ELEKTRONIK"},
    {"code": "91590", "name": "Çek valf: U4: 1/4\"", "cat": "MEKATRONIK"},
    {"code": "15005", "name": "Kuyruklu dirsek: 5020 1/4\" erkek-dişi", "cat": "MEKATRONIK"},
    {"code": "50549", "name": "Redüksiyon 2090 1/4\"<1/8\"", "cat": "MEKATRONIK"},
    {"code": "40085", "name": "Basınç anahtarı: PMN10A 2-10 bar NO", "cat": "ELEKTRONIK"},
    {"code": "91451", "name": "57116 RDD 1/4-8 DİRSEK AIGNEP", "cat": "MEKATRONIK"},
    {"code": "50023", "name": "KQ2S06-01AS: 1/8\"-6mm düz içten sıkmalı", "cat": "MEKATRONIK"},
    {"code": "50273", "name": "SS5Y5-41-05-01F-Q 5'li Altlık", "cat": "MEKATRONIK"},
    {"code": "50021", "name": "Valf soketi: DIN 43650C-C/Led 24V", "cat": "ELEKTRONIK"},
    {"code": "41442", "name": "RD96 MU_22 Krom Kaplı Ray: Ø25 / 180 mm", "cat": "MEKATRONIK"},
    {"code": "41404", "name": "RD96 MU_33 Krom Kaplı Ray: Ø25 / 267 mm", "cat": "MEKATRONIK"},
    {"code": "96517", "name": "Rd96 MU Z Polietilen Piston Dayama Takozu", "cat": "MEKATRONIK"},
    {"code": "50257", "name": "SMC Tek Etkili Silindir CD75E32-80-B", "cat": "MEKATRONIK"},
    {"code": "96501", "name": "SMC C76-32PS Sızdırmazlık Kiti", "cat": "MEKATRONIK"},
    {"code": "90766", "name": "RD96 Alüminyum Lama Montaj Parçası", "cat": "MEKATRONIK"},
    {"code": "16016", "name": "Paslanmaz Altı köşe Civata M5 x10 mm", "cat": "MEKATRONIK"},
    {"code": "16039", "name": "Paslanmaz M5 Yaylı Rondela", "cat": "MEKATRONIK"},
    {"code": "16034", "name": "Paslanmaz M5 Pul", "cat": "MEKATRONIK"},
    {"code": "41403", "name": "Havşa Başlı İmbus Civata M8 x 10", "cat": "MEKATRONIK"},
    {"code": "90767", "name": "RD96 Cambaz Kolu Sacı", "cat": "MEKATRONIK"},
    {"code": "91071", "name": "KQ2L04-01Ns Dirsek Rakor 1/8\" 4mm", "cat": "MEKATRONIK"},
    {"code": "90762", "name": "Sensör tutucu: BM2-032: bant tipi 32mm", "cat": "MEKATRONIK"},
    {"code": "90840", "name": "Piston sensörü: DC73L: reed 3m kablolu", "cat": "ELEKTRONIK"},
    {"code": "41400", "name": "Rd96 MU Z ekseni Yataklama Pim leri", "cat": "MEKATRONIK"},
    {"code": "41401", "name": "Rd96 MU Z eksen Gijonları 292mm*M6", "cat": "MEKATRONIK"},
    {"code": "41300", "name": "RD96-Mu Cambaz Pistonu Yeşil Takoz", "cat": "MEKATRONIK"},
    {"code": "41402", "name": "Rd96 MU Z ekseni Paslanmaz Yataklama Plakası", "cat": "MEKATRONIK"},
    {"code": "91277", "name": "RD96-Mu Polietilen Ağızlık", "cat": "MEKATRONIK"},
    {"code": "54516", "name": "Rd96 Full Z Axis Equipment", "cat": "MEKATRONIK"},
    {"code": "90768", "name": "Cambaz Kutusu Dolu", "cat": "MEKATRONIK"},
    {"code": "90769", "name": "RD96 Boş Cambaz Kutusu", "cat": "MEKATRONIK"},
    {"code": "90782", "name": "C85 Serisi Silindir Eklem Yer Bağlantı", "cat": "MEKATRONIK"},
    {"code": "16032", "name": "Paslanmaz Altı köşe Civata M6 x10 mm", "cat": "MEKATRONIK"},
    {"code": "16041", "name": "Paslanmaz M6 Yaylı Rondela", "cat": "MEKATRONIK"},
    {"code": "16035", "name": "Paslanmaz M6 Pul", "cat": "MEKATRONIK"},
    {"code": "50260", "name": "Pnömatik Silindir CD85N16-50-B (SMC)", "cat": "MEKATRONIK"},
    {"code": "90759", "name": "Sensör tutucu: BJ2-016", "cat": "MEKATRONIK"},
    {"code": "50138", "name": "Pnömatik rakor: KQ2L04-M5A 4mm dirsek", "cat": "MEKATRONIK"},
    {"code": "91086", "name": "Pnömatik T rakor: KQ2T04-M5A", "cat": "MEKATRONIK"},
    {"code": "91045", "name": "SMC Küresel Mafsal: KJ6D M6*1", "cat": "MEKATRONIK"},
    {"code": "90770", "name": "RD96 Cambaz Mekanizması", "cat": "MEKATRONIK"},
    {"code": "16043", "name": "Paslanmaz İmbus M5 Civata M5x20 mm", "cat": "MEKATRONIK"},
    {"code": "16030", "name": "Paslanmaz Altı köşe Civata M5 x20 mm", "cat": "MEKATRONIK"},
    {"code": "90765", "name": "RD96 Cambaz Kolu", "cat": "MEKATRONIK"},
    {"code": "11906", "name": "Altı Köşe Somun M6", "cat": "MEKATRONIK"},
    {"code": "12302", "name": "Fiberli Kör Somun M6", "cat": "MEKATRONIK"},
    {"code": "41444", "name": "Krom Ray: Ø25 / 1350 mm x ekseni", "cat": "MEKATRONIK"},
    {"code": "91303", "name": "Paslanmaz Araba 4 Delikli Rexroth", "cat": "MEKATRONIK"},
    {"code": "50263", "name": "Silindir: CD85N25-400C-B SMC", "cat": "MEKATRONIK"},
    {"code": "91044", "name": "SMC Küresel Mafsal: KJ10D M10*1,25", "cat": "MEKATRONIK"},
    {"code": "54510", "name": "Pnömatik rakor: KQ2VS04-01AS 1/8-4mm", "cat": "MEKATRONIK"},
    {"code": "90761", "name": "Sensör tutucu: BM2-025: bant tipi", "cat": "MEKATRONIK"},
    {"code": "50262", "name": "Silindir: CD85N25-300C-B (SMC)", "cat": "MEKATRONIK"},
    {"code": "41399", "name": "Pnömatik rakor: KQ2U04-00 4mm Y", "cat": "MEKATRONIK"},
    {"code": "50259", "name": "Silindir CD85N16-200-B (SMC)", "cat": "MEKATRONIK"},
    {"code": "50258", "name": "Silindir CD85N16-100-B (SMC)", "cat": "MEKATRONIK"},
    {"code": "50261", "name": "Silindir 80 mm Strok CD85N16-80-B", "cat": "MEKATRONIK"},
    {"code": "91269", "name": "RD96 X Ekseni mekanik yatak Kilidi", "cat": "MEKATRONIK"},
    {"code": "91270", "name": "RD96 Y Ekseni mekanik yatak Kilidi", "cat": "MEKATRONIK"},
    {"code": "50278", "name": "Manifold: SS5YJ3-S41-02-M5F-Q 2'li", "cat": "MEKATRONIK"},
    {"code": "50293", "name": "Valf: SYJ3243-5LOU-Q 5/2 çift bobin", "cat": "ELEKTRONIK"},
    {"code": "90725", "name": "Hız ayar valfi: ASN2-02 1/8 susturuculu", "cat": "MEKATRONIK"},
    {"code": "50040", "name": "Dirsek Rakor 1/8x6mm / KQ2L06-01AS", "cat": "MEKATRONIK"},
    {"code": "41396", "name": "12'li Hareketli Kablo X3-X4 Valf", "cat": "ELEKTRONIK"},
    {"code": "41398", "name": "Soket ucu SY100-30-A SMC", "cat": "ELEKTRONIK"},
    {"code": "54630", "name": "SYJ3243 2'li full valf grubu", "cat": "MEKATRONIK"},
    {"code": "50270", "name": "Manifold: SS3Y1-S41-04-M5-Q 4'lü", "cat": "MEKATRONIK"},
    {"code": "50287", "name": "Valf: SY114-5LOU-Q SMC", "cat": "ELEKTRONIK"},
    {"code": "91066", "name": "Pnömatik rakor: KQ2H06-M5A M5-6mm", "cat": "MEKATRONIK"},
    {"code": "91064", "name": "Pnömatik rakor: KQ2H04-M5A M5-4mm düz", "cat": "MEKATRONIK"},
    {"code": "41457", "name": "Kör Tapa: M-5P: M5x0,8 (SMC)", "cat": "MEKATRONIK"},
    {"code": "50238", "name": "Susturucu: AN120-M5 (SMC)", "cat": "MEKATRONIK"},
    {"code": "50156", "name": "Pnömatik T rakor: KQ2T06-00A 6mm", "cat": "MEKATRONIK"},
    {"code": "91043", "name": "Valf Kablosu: SY114 için (EM)", "cat": "ELEKTRONIK"},
    {"code": "50269", "name": "Manifold: SS3Y1-S41-02-M5-Q 2'li", "cat": "MEKATRONIK"},
    {"code": "50289", "name": "Valf: SY3220-5LOU-M5-Q çift bobin", "cat": "ELEKTRONIK"},
    {"code": "50291", "name": "Valf: SYJ3143-5LOU-Q SMC", "cat": "ELEKTRONIK"},
    {"code": "90781", "name": "SMC C85-25Ps Piston Keçesi X3-X4", "cat": "MEKATRONIK"},
    {"code": "96404", "name": "RD96-MU22 Paslanmaz Çelik Tabla", "cat": "MEKATRONIK"},
    {"code": "41406", "name": "RD96_MU33 PVC Tabla", "cat": "MEKATRONIK"},
    {"code": "41405", "name": "RD96-MU33 Paslanmaz Çelik Tabla 304", "cat": "MEKATRONIK"},
    {"code": "90484", "name": "3/4\" Kimyasal Vana Kür.Vana+Elcik+Adaptör", "cat": "MEKATRONIK"},
    {"code": "91490", "name": "3/4 RD Vana Adaptör Bağlantı O-ringi", "cat": "MEKATRONIK"},
    {"code": "91489", "name": "3/4' RD Vana Conta Takımı", "cat": "MEKATRONIK"},
    {"code": "90930", "name": "EPDM Lastik Conta 25*40 Kare Oring", "cat": "MEKATRONIK"},
    {"code": "91495", "name": "3/4\" Şeffaf Kimyasal Hortum (MT)", "cat": "MEKATRONIK"},
    {"code": "54661", "name": "Rd96 Mu 22 Y eksen Kolu", "cat": "MEKATRONIK"},
    {"code": "54662", "name": "Rd96 Mu 33 Y eksen Kolu", "cat": "MEKATRONIK"},
    {"code": "41437", "name": "Flowmetre Dönüşüm Flanşı (Micromotion>E/H)", "cat": "MEKATRONIK"},
    {"code": "90568", "name": "66 Mm Teflon Takviyeli Diyafram Pulu", "cat": "MEKATRONIK"},
    {"code": "50014", "name": "Susturucu: AN15-02: 1/4\"", "cat": "MEKATRONIK"},
    {"code": "91782", "name": "Rd96-33 Hareketli Kablo (EM)", "cat": "ELEKTRONIK"},
    {"code": "91271", "name": "RD96-22 Hareketli Kablo (EM)", "cat": "ELEKTRONIK"},
    {"code": "91268", "name": "Rd96 Mu Fırça", "cat": "MEKATRONIK"},
    {"code": "90793", "name": "Loblu Pompa Conta (Teflon Giydirme)", "cat": "MEKATRONIK"},
    {"code": "90324", "name": "SLR1-40 Lob Anahtarı", "cat": "MEKATRONIK"},
    {"code": "16044", "name": "Yıldız Tornavida başlı M4 x 5 mm vida", "cat": "MEKATRONIK"},
    {"code": "14847", "name": "Klemp Kelepçesi: 1\" - Ø33.7mm Paslanmaz", "cat": "MEKATRONIK"},
    {"code": "41290", "name": "Soket muhafazası: HAN24 B-AGG-QB", "cat": "ELEKTRONIK"},
    {"code": "41287", "name": "Socket Cover HDC HB 24TSVU 1/21 P", "cat": "ELEKTRONIK"},
    {"code": "41288", "name": "Soket: HDC-HE-24BS: 24 pin dişi", "cat": "ELEKTRONIK"},
    {"code": "41289", "name": "Soket: HDC-HE-24SS: 24 pin erkek", "cat": "ELEKTRONIK"},
    {"code": "54629", "name": "SY114 4'lü Full Valf Grubu", "cat": "MEKATRONIK"},
    {"code": "54628", "name": "SY114 2'li Full Valf Grubu", "cat": "MEKATRONIK"},
    {"code": "50024", "name": "Hava hortumu: TU0604BU: 6mm mavi", "cat": "MEKATRONIK"},
    {"code": "50025", "name": "Hava hortumu: TU0806BU: 8mm mavi", "cat": "MEKATRONIK"},
    {"code": "91586", "name": "Hava hortumu: TU1065BU: 10mm mavi", "cat": "MEKATRONIK"},
    {"code": "50027", "name": "Hava hortumu: TU0425BU: 4mm mavi", "cat": "MEKATRONIK"},
    {"code": "92038", "name": "Regülatör: AW30-F03DE-B 3/8 NO tahliyeli", "cat": "MEKATRONIK"},
    {"code": "54620", "name": "G36-P10-01-X30 Manometre", "cat": "MEKATRONIK"},
    {"code": "14577", "name": "Nipel: 2010 3/8\"", "cat": "MEKATRONIK"},
    {"code": "14317", "name": "Pnömatik Tee rakor: 4000 3/8\" D-D-D", "cat": "MEKATRONIK"},
    {"code": "96449", "name": "Orantılı nipel: 2030 1/4\"-3/8\"", "cat": "MEKATRONIK"},
    {"code": "91950", "name": "Çek valf: U4: 1/4\"", "cat": "MEKATRONIK"},
    {"code": "96219", "name": "Küresel vana: 6310 3/8\" erkek dişi", "cat": "MEKATRONIK"},
    {"code": "91453", "name": "Pnömatik rakor: 57116 3/8\"-10mm dirsek", "cat": "MEKATRONIK"},
    {"code": "50008", "name": "Tespit Elemanı AR30 / AW30", "cat": "MEKATRONIK"},
    {"code": "50010", "name": "Tespit Elemanı : AW23P-270AS", "cat": "MEKATRONIK"},
    {"code": "50046", "name": "Regülatör: AW20-F02C-B SMC", "cat": "MEKATRONIK"},
    {"code": "50054", "name": "Küresel vana: 6310 1/4\" erkek dişi", "cat": "MEKATRONIK"}
]

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class CustomReportState(StatesGroup):
    waiting_date_range = State()

class QuoteBuilderState(StatesGroup):
    waiting_firm = State()
    waiting_contact = State()
    waiting_item_query = State()
    waiting_qty = State()
    confirm_more = State()

def normalize_tr(text: str) -> str:
    m = {'ı':'i','İ':'i','I':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = text.lower()
    for k, v in m.items(): res = res.replace(k, v)
    return res

def get_catalog_pdf_file():
    for fn in os.listdir("."):
        if fn.lower() in ["katalog.pdf", "catalog.pdf", "rd96.pdf", "rd96_katalog.pdf"]:
            return fn
        if fn.lower().endswith(".pdf") and "katalog" in fn.lower():
            return fn
    return None

def extract_part_image_from_pdf(code: str) -> bytes:
    pdf_path = get_catalog_pdf_file()
    if not pdf_path: return None
    try:
        import fitz
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()
        for page in doc:
            instances = page.search_for(code_str)
            if instances:
                rect = instances[0]
                pw, ph = page.rect.width, page.rect.height
                is_left = rect.x0 < (pw / 2)
                x0 = 15 if is_left else (pw / 2 + 5)
                x1 = (pw / 2 - 5) if is_left else (pw - 15)
                y0 = max(25, rect.y0 - 200)
                y1 = min(ph - 25, rect.y1 + 220)
                pix = page.get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), dpi=200)
                return pix.tobytes("png")
        return None
    except Exception as e:
        logging.error(f"Görsel kırpma hatası: {e}")
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
    scored = []
    for p in RD96_CATALOG:
        score = calculate_similarity(query, p)
        if score > 0.30: scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:5]

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

def init_stocks_from_catalog():
    items = [{"code": c["code"], "name": c["name"], "cat": c["cat"], "qty": 0, "loc": "MERKEZ-DEPO"} for c in RD96_CATALOG]
    save_data(STOCKS_FILE, items)

load_stocks = lambda: load_data(STOCKS_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, [])
save_sales = lambda d: save_data(SALES_FILE, d)
load_tasks = lambda: load_data(TASKS_FILE, {})
save_tasks = lambda d: save_data(TASKS_FILE, d)

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e: logging.warning(f"İletilemedi ({cid}): {e}")

async def send_file_to_both(file_path: str, caption: str):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try: await bot.send_document(chat_id=cid, document=FSInputFile(file_path), caption=caption)
        except Exception as e: logging.warning(f"Dosya iletilemedi ({cid}): {e}")

# ---------------- EXCEL & PDF Z-RAPORU MOTORU ----------------
def generate_excel_z_report(sales_data, title="Z_Raporu"):
    fn = f"Elips_Eliar_{title}_{datetime.now().strftime('%d_%m_%Y')}.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satislar"
        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "İlgili Kişi", "Ürün Kodu", "Ürün Adı", "Adet"]
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
                           str(sale.get("contact", "-")), item.get("code", ""), item.get("name", ""), item.get("qty", 1)])
                for c in range(1, len(headers) + 1): ws.cell(row=row, column=c).border = border
                row += 1; cnt += 1
        for idx, w in enumerate([8, 18, 14, 25, 20, 16, 40, 10], 1):
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
            ref = str(sale.get("ref_no", "YOK"))
            firm = str(sale.get("firm", ""))[:20]
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
        return f"📊 **ELİPS TEKSTİL ELİAR {report_name}**\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\nℹ️ Kayıt bulunamadı."
    text = f"📊 **ELİPS TEKSTİL ELİAR {report_name}**\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\n\n"
    total_qty, plants, cnt = 0, set(), 1
    for sale in sales_data:
        plants.add(sale.get("firm", ""))
        for itm in sale.get("items", []):
            q = int(itm.get("qty", 1))
            total_qty += q
            text += f"**{cnt}.** `[{itm.get('code')}]` {itm.get('name')}\n   └ Miktar: **{q} Adet** | Tesis: **{sale.get('firm')}**\n\n"
            cnt += 1
    text += f"───────────────────────────────\n📦 Toplam Satış: **{total_qty} Adet** | Tesis: **{len(plants)}**\n📂 Format seçin:"
    return text

def get_client_history_text(firm_query: str):
    sales = load_sales()
    query = firm_query.strip().lower()
    matched = [s for s in sales if query in s.get("firm", "").lower() and s.get("status") == "APPROVED"]
    if not matched: return f"🔍 `{firm_query}` için geçmiş onaylı kayıt bulunamadı."
    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    text = f"🏢 **{matched[0].get('firm')} — PARÇA GEÇMİŞİ**\n═══════════════════════════════\n\n"
    for item in matched:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for itm in item.get("items", []):
            text += f"• 📅 `{item.get('date', '')}` ➔ **{itm.get('qty')}x** `{itm.get('code')}` ({itm.get('name')}){ref_str}\n"
    text += f"\n═══════════════════════════════\n✅ Toplam: **{len(matched)} Sevkiyat / Hareket**"
    return text

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla"), KeyboardButton(text="📦 Parça Listesi")],
            [KeyboardButton(text="📊 Z-Raporu Al"), KeyboardButton(text="📅 Tarihli Rapor Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="🏢 Tesis Geçmişi")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Başlat / Ana Menü"),
        BotCommand(command="teklif", description="Nilay Hanım'a Teklif Hazırla"),
        BotCommand(command="stok", description="Parça Listesi"),
        BotCommand(command="sifirla", description="Stokları Sıfırla & Kataloğu Yükle"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu"),
        BotCommand(command="tarihraporu", description="Tarih Aralıklı Rapor"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifler"),
        BotCommand(command="ref", description="Ref No ile Sorgula"),
        BotCommand(command="gecmis", description="Tesis Geçmişi (/gecmis Müşteri)")
    ]
    await bot.set_my_commands(commands)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.chat.id
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else message.from_user.first_name)
    pdf_info = "✓ Bulundu" if get_catalog_pdf_file() else "✗ Bulunamadı (Katalog.pdf)"
    await message.answer(
        f"👋 **Selam {name}! Eliar Depo & Teklif Robotu Aktif.**\n\n"
        f"• Katalog PDF: `{pdf_info}`\n"
        f"• Toplam Parça: **{len(RD96_CATALOG)} Kalem**\n"
        f"• Nilay Hanım'a teklif hazırlamak için aşağıdaki menüden işlem yapabilirsiniz.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# ---------------- NİLAY HANIM'A TEKLİF SİHİRBAZI ----------------
@dp.message(Command("teklif"))
@dp.message(F.text == "📝 Nilay Hanım'a Teklif Hazırla")
async def start_quote_wizard(message: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteBuilderState.waiting_firm)
    await message.answer("🏢 **Teklif hangi müşteri / fabrika için hazırlanacak?**\n(Örnek: `TERRY JAR`, `MICBRO`, `OSB TEKSTİL`)", parse_mode="Markdown")

@dp.message(QuoteBuilderState.waiting_firm)
async def process_quote_firm(message: types.Message, state: FSMContext):
    firm = message.text.strip().upper()
    await state.update_data(firm_name=firm)
    await state.set_state(QuoteBuilderState.waiting_contact)
    await message.answer(f"👤 **{firm}** için **İlgili Kişi & Telefon** bilgisi nedir?\n(Örnek: `Ahmet Bey 0532...` veya yoksa `-` yazın):", parse_mode="Markdown")

@dp.message(QuoteBuilderState.waiting_contact)
async def process_quote_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip()
    await state.update_data(contact=contact)
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await message.answer(
        f"🔍 **Hangi parça için teklif istenecek?**\n"
        f"• Varsa **Sipariş Kodunu** yazın (Örn: `91514`)\n"
        f"• Bilmiyorsanız **Ürün İsmini** yazın (Örn: `loblu pompa`, `rakor`, `vana`, `aktüatör`, `keçe`):",
        parse_mode="Markdown"
    )

@dp.message(QuoteBuilderState.waiting_item_query)
async def process_quote_search(message: types.Message, state: FSMContext):
    query = message.text.strip()
    matches = find_best_matches(query)

    if not matches:
        await message.answer(f"⚠️ `{query}` ile eşleşen katalog parçası bulunamadı.\nLütfen başka bir kelime veya kod deneyin:", parse_mode="Markdown")
        return

    top_part, top_score = matches[0]
    alternatives = matches[1:4]

    buttons = [[InlineKeyboardButton(text=f"✅ Evet, Bu Parça ({top_part['code']})", callback_data=f"qbsel:{top_part['code']}")]]
    for alt_p, _ in alternatives:
        buttons.append([InlineKeyboardButton(text=f"👉 {alt_p['code']} - {alt_p['name'][:30]}...", callback_data=f"qbsel:{alt_p['code']}")])
    buttons.append([InlineKeyboardButton(text="🔄 Hayır, Yeniden Ara", callback_data="qb_retry_search")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if query.strip().lower() == top_part['code'].lower():
        await state.update_data(selected_part=top_part)
        await state.set_state(QuoteBuilderState.waiting_qty)
        await message.answer(f"🎯 **Seçilen Parça:**\n📦 `[{top_part['code']}]` **{top_part['name']}**\n\n🔢 Kaç **adet** teklif edilecek?", parse_mode="Markdown")
        return

    await message.answer(
        f"🔍 **Bunu mu demek istediniz?**\n\n"
        f"📦 Kod: `{top_part['code']}`\n"
        f"⚙️ Parça: **{top_part['name']}**\n"
        f"📂 Kategori: `{top_part.get('cat', 'MEKATRONIK')}`\n\n"
        f"Aradığınız parça bu mu?",
        reply_markup=kb,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "qb_retry_search")
async def on_quote_retry(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Lütfen parça ismini veya kodunu tekrar yazın:")
    await callback.answer()

@dp.callback_query(F.data.startswith("qbsel:"))
async def on_quote_part_confirmed(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]
    part = next((p for p in RD96_CATALOG if p["code"] == code), None)
    if not part:
        await callback.answer("Parça bulunamadı.", show_alert=True)
        return
    await state.update_data(selected_part=part)
    await state.set_state(QuoteBuilderState.waiting_qty)
    await callback.message.edit_text(
        f"🎯 **Seçilen Parça:**\n📦 `[{part['code']}]` **{part['name']}**\n\n"
        f"🔢 Kaç **adet** teklif edilecek? (Örn: `1`, `2`, `5`)", 
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_qty)
async def process_quote_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("⚠️ Lütfen sayı girin (Örn: `1`, `2`):", parse_mode="Markdown")
        return

    data = await state.get_data()
    part = data.get("selected_part")
    items = data.get("quote_items", [])
    items.append({"code": part["code"], "name": part["name"], "qty": qty})
    await state.update_data(quote_items=items)

    img_bytes = extract_part_image_from_pdf(part["code"])
    if img_bytes:
        try:
            photo = BufferedInputFile(img_bytes, filename=f"{part['code']}.png")
            await message.answer_photo(photo, caption=f"📸 **Katalog Görseli:** `[{part['code']}]` — {part['name']}", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Resim iletilemedi: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="qb_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir & Formatı Al", callback_data="qb_done")]
    ])
    await state.set_state(QuoteBuilderState.confirm_more)
    await message.answer(f"✅ **{qty} Adet** `[{part['code']}]` eklendi!\nNe yapmak istersiniz?", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "qb_more")
async def on_quote_add_another(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Yeni parçanın **kodunu** veya **ismini** yazın:")
    await callback.answer()

@dp.callback_query(F.data == "qb_done")
async def on_quote_completed(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    firm = data.get("firm_name", "MÜŞTERİ")
    contact = data.get("contact", "")
    items = data.get("quote_items", [])
    if not items:
        await callback.message.edit_text("⚠️ Teklifte ürün yok.")
        await state.clear()
        return

    contact_str = f" (İlgili: {contact})" if contact and contact != "-" else ""
    text = (
        f"📋 **KOPYALAMAYA HAZIR TEKLİF METNİ:**\n"
        f"═══════════════════════════════\n\n"
        f"Merhaba Nilay hanim\n\n"
        f"{firm}{contact_str} için aşağıdaki listedeki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    )
    for itm in items:
        text += f"• `{itm['code']}` - {itm['name']} - **{itm['qty']} Adet**\n"

    text += (
        f"\nİyi çalışmalar.\n"
        f"═══════════════════════════════\n"
        f"💡 _Metne basılı tutarak doğrudan WhatsApp veya E-Posta ile Nilay Hanım'a gönderebilirsiniz._"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.clear()
    await callback.answer("Teklif tamamlandı!")

# ----------------- RAPOR İŞLEMLERİ -----------------
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
        await callback.message.answer("✍️ Format: `GG.AA.YYYY - GG.AA.YYYY` (Örn: `01.10.2026 - 29.10.2026`)", parse_mode="Markdown")
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
        await message.answer("⚠️ Format hatalı! Örnek: `01.10.2026 - 29.10.2026`", parse_mode="Markdown")

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
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📊 **Elips Eliar {title} (Excel)**")
    if fmt in ["pdf", "both"]:
        f = generate_pdf_z_report(sales, title)
        if f and os.path.exists(f): await callback.message.answer_document(FSInputFile(f), caption=f"📑 **Elips Eliar {title} (PDF)**")

# ---------------- SORGULAR, TESİS GEÇMİŞİ & REF ----------------
@dp.message(Command("ref"))
async def cmd_ref_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Referans Numarası yazın. (Örn: `/ref 46189ND`)", parse_mode="Markdown")
        return
    query = parts[1].strip().upper()
    sales = load_sales()
    quote = next((s for s in sales if query in str(s.get("ref_no", "")).strip().upper()), None)
    if not quote:
        await message.answer(f"🔍 `{query}` referansına ait kayıt bulunamadı.", parse_mode="Markdown")
        return
    status_str = {"APPROVED": "🟢 ONAYLANDI", "WAITING": "🟡 BEKLİYOR", "REJECTED": "🔴 İPTAL"}.get(quote.get("status"), "Bilinmiyor")
    text = (f"🔖 **TEKLİF [Ref: {quote.get('ref_no')}]**\n═══════════════════════════════\n"
            f"🏭 Müşteri: `{quote.get('firm')}`\n👤 İlgili: {quote.get('contact', '-')}\n📌 Durum: {status_str}\n🕒 Tarih: {quote.get('date')}\n\n📦 **Parçalar:**\n")
    for idx, item in enumerate(quote.get("items", []), 1):
        text += f"{idx}. `[{item.get('code')}]` — {item.get('name')} ({item.get('qty')} Adet)\n"
    await message.answer(text, parse_mode="Markdown")

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
    await message.answer("🔍 Geçmişini aradığınız **Fabrika Adını** yazın:", parse_mode="Markdown")

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="Markdown")

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
            txt += f"• `[{itm.get('code')}]` {itm.get('name')} ({itm.get('qty')} Adet)\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Onayla", callback_data=f"q_appr:{s.get('id')}"),
             InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{s.get('id')}")]
        ])
        await message.answer(txt, reply_markup=kb, parse_mode="Markdown")

# ----------------- PARÇA LİSTESİ VE SIFIRLAMA -----------------
@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stocks(message: types.Message):
    stocks = load_stocks()
    if not stocks:
        await message.answer("📦 Kayıtlı parça bulunamadı. `/sifirla` komutu ile kataloğu yükleyebilirsiniz.")
        return
    text = f"📦 **GÜNCEL ELİAR DEPO & RD96 LİSTESİ** (Toplam: {len(stocks)} Kalem)\n═══════════════════════════════\n\n"
    for s in stocks[:20]:
        text += f"• `[{s['code']}]` {s['name'][:35]}\n  └ Stok: **{s.get('qty', 0)} ADT** | Konum: `{s.get('loc', 'MERKEZ-DEPO')}`\n"
    if len(stocks) > 20:
        text += f"\n_...ve {len(stocks)-20} kalem parça daha. Tamamı Mini App'te listelenmektedir._"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("sifirla"))
async def cmd_reset_all(message: types.Message):
    init_stocks_from_catalog()
    await message.answer(f"✅ **Stoklar sıfırlandı ve {len(RD96_CATALOG)} kalem RD96 parçası başarıyla yüklendi!**", parse_mode="Markdown")

# ----------------- MEDYA / TEKLİF FORMU OKUMA (GEMINI) -----------------
def parse_quote_media(file_path: str, is_pdf: bool = False, original_filename: str = ""):
    clean_fn = re.sub(r"(fiyat|teklif|\.pdf|\.jpg|\.png|temp_doc_\w+)", "", original_filename, flags=re.IGNORECASE).strip()
    firm = clean_fn if len(clean_fn) >= 3 else "Bilinmeyen Müşteri"
    items, ref_no = [], "BELİRTİLMEDİ"
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            mime = "application/pdf" if is_pdf else "image/jpeg"
            with open(file_path, "rb") as f: b = f.read()
            prompt = "Teklifi analiz et. Saf JSON dön: {\"firm\":\"...\",\"ref_no\":\"...\",\"items\":[{\"code\":\"...\",\"name\":\"...\",\"qty\":1}]}"
            res = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, genai.types.Part.from_bytes(data=b, mime_type=mime)])
            parsed = json.loads(res.text.replace("```json", "").replace("```", "").strip())
            if parsed.get("items"): return parsed
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
        if is_pdf: await bot.send_document(target_id, doc_id, caption=f"📑 **{op_name} teklif PDF'i paylaştı!**")
        else: await bot.send_photo(target_id, doc_id, caption=f"📷 **{op_name} teklif görseli paylaştı!**")
    except Exception: pass

    file_obj = await bot.get_file(doc_id)
    tmp_path = f"tmp_{int(time.time())}.{'pdf' if is_pdf else 'jpg'}"
    await bot.download_file(file_obj.file_path, tmp_path)
    data = parse_quote_media(tmp_path, is_pdf=is_pdf, original_filename=doc_name)
    if os.path.exists(tmp_path): os.remove(tmp_path)

    s_id = f"Q-{int(time.time()*1000)}"
    sales = load_sales()
    sales.append({
        "id": s_id, "firm": data.get("firm", "Bilinmeyen"), "ref_no": data.get("ref_no", "YOK"),
        "items": data.get("items", []), "status": "WAITING", "uploaded_by": op_name,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
    })
    save_sales(sales)

    txt = f"📄 **ELİAR TEKLİF FORMU ALGILANDI!**\n👤 Paylaşan: {op_name}\n🏭 Müşteri: `{data.get('firm')}`\n🔖 Ref No: `{data.get('ref_no')}`\n\n📦 **Parçalar:**\n"
    for idx, itm in enumerate(data.get("items", []), 1):
        txt += f"{idx}. `[{itm.get('code')}]` — {itm.get('name')} ({itm.get('qty')} Adet)\n"

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
    if sale: sale["status"] = "WAITING"; save_sales(sales)
    await callback.message.edit_text(callback.message.text + "\n\n🟡 **BEKLEMEYE ALINDI**", reply_markup=None)
    await callback.answer("Beklemede")

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    s_id = callback.data.split(":")[1]
    sales, stocks = load_sales(), load_stocks()
    sale = next((s for s in sales if s.get("id") == s_id), None)
    if not sale or sale.get("status") == "APPROVED":
        await callback.answer("Zaten onaylanmış.", show_alert=True); return
    sale["status"] = "APPROVED"
    sale["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_sales(sales)
    for itm in sale.get("items", []):
        for st in stocks:
            if st.get("code") == itm.get("code"):
                st["qty"] = max(0, st["qty"] - int(itm.get("qty", 1))); break
    save_stocks(stocks)
    await callback.message.edit_text(callback.message.text + "\n\n🟢 **ONAYLANDI (SATIŞ)**", reply_markup=None)
    await notify_both(f"🟢 **SATIŞ ONAYLANDI!**\n🏭 `{sale.get('firm')}` — Ref: `{sale.get('ref_no')}`\nStoktan düşüldü ve Z-Raporuna işlendi.")
    await callback.answer("Onaylandı.")

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    s_id = callback.data.split(":")[1]
    sales = load_sales()
    sale = next((s for s in sales if s.get("id") == s_id), None)
    if sale: sale["status"] = "REJECTED"; save_sales(sales)
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **KABUL EDİLMEDİ (İPTAL)**", reply_markup=None)
    await callback.answer("İptal edildi.")

# ----------------- WEBAPP & SAHA İŞ EMİRLERİ -----------------
@dp.message(F.web_app_data)
async def handle_webapp_payload(message: types.Message):
    try: p = json.loads(message.web_app_data.data)
    except Exception: return
    op = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    ref_id = f"REF-{message.message_id}"
    dir_type = p.get("direction")

    if dir_type == "STOCK_CHANGE" and p.get("action") == "DECREASE":
        dest, contact = p.get("destination", "Bilinmeyen"), p.get("contact", "-")
        code, name, qty = p.get("code"), p.get("name"), p.get("delta", 1)
        sales = load_sales()
        sales.append({
            "id": ref_id, "firm": dest, "contact": contact, "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}], "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        msg = f"📤 **PARÇA SATILDI / DEPO ÇIKIŞI!**\n🏢 Firma: `{dest}`\n👤 İlgili Kişi: `{contact}`\n⚙️ `[{code}]` {name}\n📉 Adet: **-{qty}** | Kalan: `{p.get('current_qty', 0)} ADT`\n👷‍♂️ Çıkış Yapan: {op}"
        await notify_both(msg)

    elif dir_type == "OMER_TO_KAMIL":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Onayla", callback_data=f"otk_ok:{ref_id}"),
             InlineKeyboardButton(text="❌ Reddet", callback_data=f"otk_no:{ref_id}")]
        ])
        msg = f"🔔 **ÖMER'DEN YENİ TALEP!**\n🏢 Firma: `{p.get('firm')}`\n👤 İlgili: `{p.get('contact')}`\n⚙️ `[{p.get('part_code')}]` {p.get('part_name')}\n📦 Adet: **{p.get('quantity')}** | Öncelik: `{p.get('priority')}`\n📝 Not: _{p.get('notes') or 'Yok'}_"
        await bot.send_message(KAMIL_CHAT_ID, msg, reply_markup=kb, parse_mode="Markdown")
        await message.answer("✅ Talep Kamil'e iletildi.")

    elif dir_type == "KAMIL_TO_OMER":
        tasks = load_tasks()
        tasks[ref_id] = {"created_at": time.time(), "firm": p.get('firm'), "task_type": p.get('task_type')}
        save_tasks(tasks)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👍 Aldım", callback_data=f"o_ack:{ref_id}"),
             InlineKeyboardButton(text="🔍 İlgileniyorum", callback_data=f"o_busy:{ref_id}")],
            [InlineKeyboardButton(text="✅ Bitirdim", callback_data=f"o_done:{ref_id}")]
        ])
        msg = f"📋 **KAMİL'DEN YENİ SAHA İŞ EMRİ!**\n🏢 Gidilecek Firma: `{p.get('firm')}`\n👤 İlgili Kişi: `{p.get('contact')}`\n🔧 Görev: **{p.get('task_type')}**\n📝 Talimat: _{p.get('instructions') or 'Yok'}_"
        await bot.send_message(OMER_CHAT_ID, msg, reply_markup=kb, parse_mode="Markdown")
        await message.answer("✅ Görev Ömer'e iletildi.")

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

# ----------------- ÖMER VE KAMİL ARASI MESAJLAŞMA KÖPRÜSÜ -----------------
@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    menu_buttons = ["📦 Parça Listesi", "📊 Z-Raporu Al", "📅 Tarihli Rapor Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi", "📝 Nilay Hanım'a Teklif Hazırla"]
    if message.text in menu_buttons: return
    tid = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if message.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and message.text:
        await bot.send_message(tid, f"💬 **{sender}:** {message.text}")
        await message.reply("✓ _İletildi._", parse_mode="Markdown")

# ----------------- OTOMATİK ZAMANLAYICI (HAFTALIK / AYLIK) -----------------
async def automated_scheduler():
    last_week, last_month = "", ""
    while True:
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        # Cumartesi 12:30 Haftalık Z-Raporu
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = filter_sales_by_range(now - timedelta(days=7), now)
            await notify_both("📢 **HAFTALIK OTOMATİK Z-RAPORU**\n\n" + build_report_text(sales, "HAFTALIK"))
            if sales:
                f_xls = generate_excel_z_report(sales, "Haftalik")
                f_pdf = generate_pdf_z_report(sales, "Haftalik")
                if f_xls: await send_file_to_both(f_xls, "📊 Excel Raporu")
                if f_pdf: await send_file_to_both(f_pdf, "📑 PDF Raporu")
        # Ayın 1'i 18:00 Aylık Satış Raporu
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
    app.router.add_get('/', lambda r: web.Response(text="Eliar Robot Aktif"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    if not os.path.exists(STOCKS_FILE):
        init_stocks_from_catalog()
    await setup_bot_commands()
    await start_dummy_server()
    asyncio.create_task(automated_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
