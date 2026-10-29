import json
import logging
import asyncio
import os
import re
import time
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"

# RD96 KATALOĞUNUN TAM VE EKSİKSİZ LİSTESİ
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

class QuoteBuilderState(StatesGroup):
    waiting_firm = State()
    waiting_contact = State()
    waiting_item_query = State()
    waiting_qty = State()
    confirm_more = State()

def get_catalog_pdf_file():
    """Büyük-küçük harf fark etmeksizin katalog dosyasını bulur."""
    for fn in os.listdir("."):
        if fn.lower() in ["katalog.pdf", "catalog.pdf", "rd96.pdf", "rd96_katalog.pdf"]:
            return fn
        if fn.lower().endswith(".pdf") and "katalog" in fn.lower():
            return fn
    return None

def extract_part_image_from_pdf(code: str) -> bytes:
    """PDF kataloğundaki metin aramasıyla parça kutusunu tespit eder ve kırpar."""
    pdf_path = get_catalog_pdf_file()
    if not pdf_path:
        logging.warning("Katalog PDF dosyası bulunamadı.")
        return None
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()

        for page in doc:
            instances = page.search_for(code_str)
            if instances:
                rect = instances[0]
                pw = page.rect.width
                ph = page.rect.height

                # Ürün hücresini (Sol veya Sağ sütun) belirle
                is_left = rect.x0 < (pw / 2)
                x0 = 15 if is_left else (pw / 2 + 5)
                x1 = (pw / 2 - 5) if is_left else (pw - 15)

                # Fotoğraf üstte mi altta mı kontrol edip tüm kutuyu kırp
                y0 = max(30, rect.y0 - 200)
                y1 = min(ph - 30, rect.y1 + 220)

                crop_rect = fitz.Rect(x0, y0, x1, y1)
                pix = page.get_pixmap(clip=crop_rect, dpi=200)
                return pix.tobytes("png")

        return None
    except Exception as e:
        logging.error(f"Görsel çıkarma hatası: {e}")
        return None

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

def init_stocks_from_catalog():
    items = []
    for c in RD96_CATALOG:
        items.append({
            "code": c["code"],
            "name": c["name"],
            "cat": c["cat"],
            "qty": 0,
            "loc": "MERKEZ-DEPO"
        })
    save_data(STOCKS_FILE, items)
    logging.info("Stoklar sıfırlandı ve tüm RD96 parçaları yüklendi.")

load_stocks = lambda: load_data(STOCKS_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, [])
save_sales = lambda d: save_data(SALES_FILE, d)

def find_catalog_matches(query: str):
    q = query.strip().lower()
    exact = [p for p in RD96_CATALOG if q == p["code"].lower()]
    if exact: return exact
    return [p for p in RD96_CATALOG if q in p["code"].lower() or q in p["name"].lower()][:6]

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📝 Nilay Hanım'a Teklif Hazırla"), KeyboardButton(text="📦 Parça Listesi")],
            [KeyboardButton(text="📊 Z-Raporu Al"), KeyboardButton(text="⏳ Bekleyen Teklifler")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.chat.id
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else message.from_user.first_name)
    pdf_found = "✓ Bulundu" if get_catalog_pdf_file() else "✗ Bulunamadı (Katalog.pdf)"
    await message.answer(
        f"👋 **Selam {name}! Eliar Depo & Teklif İstasyonu Aktif.**\n\n"
        f"• Katalog PDF Durumu: `{pdf_found}`\n"
        f"• Toplam Parça Sayısı: **{len(RD96_CATALOG)} Kalem**\n"
        f"• Kodsuz arama & teklif için **Nilay Hanım'a Teklif Hazırla** butonuna basabilirsiniz.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

# ----------------- NİLAY HANIM'A TEKLİF SİHİRBAZI -----------------
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
    matches = find_catalog_matches(query)

    if not matches:
        await message.answer(f"⚠️ `{query}` ile eşleşen katalog parçası bulunamadı. Lütfen başka bir anahtar kelime veya sipariş kodu yazın:", parse_mode="Markdown")
        return

    if len(matches) == 1:
        part = matches[0]
        await state.update_data(selected_part=part)
        await state.set_state(QuoteBuilderState.waiting_qty)
        await message.answer(f"✅ Seçilen Parça:\n📦 `{part['code']}` — **{part['name']}**\n\nKaç **adet** teklif edilecek?", parse_mode="Markdown")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{p['code']} - {p['name'][:30]}...", callback_data=f"qbsel:{p['code']}")]
        for p in matches
    ])
    await message.answer("🔍 Birden fazla parça eşleşti. İstediğinizi seçin:", reply_markup=kb)

@dp.callback_query(F.data.startswith("qbsel:"))
async def on_quote_part_picked(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data.split(":")[1]
    part = next((p for p in RD96_CATALOG if p["code"] == code), None)
    if not part:
        await callback.answer("Parça bulunamadı.", show_alert=True)
        return
    await state.update_data(selected_part=part)
    await state.set_state(QuoteBuilderState.waiting_qty)
    await callback.message.edit_text(f"✅ Seçilen Parça:\n📦 `{part['code']}` — **{part['name']}**\n\nKaç **adet** teklif edilecek?", parse_mode="Markdown")
    await callback.answer()

@dp.message(QuoteBuilderState.waiting_qty)
async def process_quote_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0: raise ValueError
    except Exception:
        await message.answer("⚠️ Lütfen sayı girin (Örn: `1`, `2`, `5`):", parse_mode="Markdown")
        return

    data = await state.get_data()
    part = data.get("selected_part")
    items = data.get("quote_items", [])
    items.append({"code": part["code"], "name": part["name"], "qty": qty})
    await state.update_data(quote_items=items)

    # KATALOGDAN GÖRSELİ ÇIKARIP GÖNDERME
    img_bytes = extract_part_image_from_pdf(part["code"])
    if img_bytes:
        try:
            photo = BufferedInputFile(img_bytes, filename=f"{part['code']}.png")
            await message.answer_photo(photo, caption=f"📸 **Katalog Görseli:** `{part['code']}` — {part['name']}", parse_mode="Markdown")
        except Exception as e:
            logging.warning(f"Resim iletilemedi: {e}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="qb_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir & Formatı Al", callback_data="qb_done")]
    ])
    await state.set_state(QuoteBuilderState.confirm_more)
    await message.answer(f"✅ **{qty} Adet** `{part['code']}` teklife eklendi!\nNe yapmak istersiniz?", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "qb_more")
async def on_quote_add_another(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(QuoteBuilderState.waiting_item_query)
    await callback.message.edit_text("🔍 Yeni parçanın **kodunu** veya **ismini** yazın:", parse_mode="Markdown")
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
        f"💡 _Metne basılı tutarak kopyalayabilir, WhatsApp ya da E-Posta ile Nilay Hanım'a gönderebilirsiniz._"
    )

    await callback.message.edit_text(text, parse_mode="Markdown")
    await state.clear()
    await callback.answer("Teklif tamamlandı!")

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
        text += f"• `{s['code']}` — {s['name'][:35]}\n  └ Stok: **{s.get('qty', 0)} ADT** | Konum: `{s.get('loc', 'MERKEZ-DEPO')}`\n"
    if len(stocks) > 20:
        text += f"\n_...ve {len(stocks)-20} kalem parça daha. Tamamı Mini App'te listelenmektedir._"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("sifirla"))
async def cmd_reset_all(message: types.Message):
    init_stocks_from_catalog()
    await message.answer(f"✅ **Stoklar sıfırlandı ve {len(RD96_CATALOG)} kalem RD96 parçası başarıyla yüklendi!**", parse_mode="Markdown")

@dp.message(F.web_app_data)
async def handle_webapp_payload(message: types.Message):
    try:
        p = json.loads(message.web_app_data.data)
    except Exception:
        return

    op = "Ömer" if message.chat.id == OMER_CHAT_ID else "Kamil"
    dir_type = p.get("direction")

    if dir_type == "STOCK_CHANGE" and p.get("action") == "DECREASE":
        dest = p.get("destination", "Bilinmeyen")
        contact = p.get("contact", "-")
        code, name, qty = p.get("code"), p.get("name"), p.get("delta", 1)
        
        sales = load_sales()
        sales.append({
            "id": f"REF-{int(time.time())}",
            "firm": dest,
            "contact": contact,
            "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}],
            "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        msg = (
            f"📤 **PARÇA SATILDI / DEPO ÇIKIŞI!**\n"
            f"🏢 Firma: `{dest}`\n"
            f"👤 İlgili Kişi: `{contact}`\n"
            f"⚙️ `[{code}]` {name}\n"
            f"📉 Adet: **-{qty}** | Kalan: `{p.get('current_qty', 0)} ADT`\n"
            f"👷‍♂️ Çıkış Yapan: {op}"
        )
        for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
            try: await bot.send_message(cid, msg, parse_mode="Markdown")
            except Exception: pass

    elif dir_type == "OMER_TO_KAMIL":
        msg = (
            f"🔔 **ÖMER'DEN YENİ TALEP!**\n"
            f"🏢 Firma: `{p.get('firm')}`\n"
            f"👤 İlgili: `{p.get('contact')}`\n"
            f"⚙️ `[{p.get('part_code')}]` {p.get('part_name')}\n"
            f"📦 Adet: **{p.get('quantity')}** | Öncelik: `{p.get('priority')}`\n"
            f"📝 Not: _{p.get('notes') or 'Yok'}_"
        )
        await bot.send_message(KAMIL_CHAT_ID, msg, parse_mode="Markdown")
        await message.answer("✅ Talep Kamil'e iletildi.")

    elif dir_type == "KAMIL_TO_OMER":
        msg = (
            f"📋 **KAMİL'DEN YENİ SAHA İŞ EMRİ!**\n"
            f"🏢 Gidilecek Firma: `{p.get('firm')}`\n"
            f"👤 İlgili Kişi: `{p.get('contact')}`\n"
            f"🔧 Görev: **{p.get('task_type')}**\n"
            f"📝 Talimat: _{p.get('instructions') or 'Yok'}_"
        )
        await bot.send_message(OMER_CHAT_ID, msg, parse_mode="Markdown")
        await message.answer("✅ Görev Ömer'e iletildi.")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text="Eliar Aktif"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    if not os.path.exists(STOCKS_FILE):
        init_stocks_from_catalog()
    await start_dummy_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
