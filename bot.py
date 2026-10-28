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

# ==============================================================================
#                     ÖMER & KAMİL CANLI YAPILANDIRMASI
# ==============================================================================
BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444    # Ömer'in Telegram Chat ID'si
KAMIL_CHAT_ID = 35013468     # Kamil'in Telegram Chat ID'si
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
GEMINI_API_KEY = "AIzaSyAuUg0a1ew5V4aF1E-FTsdVinsMpXckOgQ" 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
TASKS_FILE = "active_tasks.json"

# İSTEĞİNİZ ÜZERİNE STOKLAR SIFIRDAN BAŞLAMASI İÇİN BOŞ BIRAKILDI
DEFAULT_STOCKS = []

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

def load_stocks():
    if not os.path.exists(STOCKS_FILE):
        save_stocks(DEFAULT_STOCKS)
        return DEFAULT_STOCKS
    try:
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_STOCKS

def save_stocks(data):
    with open(STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_sales():
    if not os.path.exists(SALES_FILE):
        return []
    try:
        with open(SALES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_sales(data):
    with open(SALES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {}
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_tasks(data):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def notify_both(text: str, reply_markup=None):
    """Hem Ömer'e hem Kamil'e aynı anda bildirim atar."""
    for cid in set([OMER_CHAT_ID, KAMIL_CHAT_ID]):
        try:
            await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Mesaj {cid} adresine iletilemedi: {e}")

async def send_file_to_both(file_path: str, caption: str):
    """Her iki tarafa da dosya gönderir."""
    for cid in set([OMER_CHAT_ID, KAMIL_CHAT_ID]):
        try:
            await bot.send_document(chat_id=cid, document=FSInputFile(file_path), caption=caption)
        except Exception as e:
            logging.warning(f"Dosya {cid} adresine iletilemedi: {e}")

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar İş Paylaşımı", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📦 Parça Listesi"), KeyboardButton(text="📊 Z-Raporu Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="🏢 Tesis Geçmişi")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Sistemi Başlat / Menü"),
        BotCommand(command="stok", description="Tüm Parça Listesi"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu (Excel / PDF)"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu (Excel / PDF)"),
        BotCommand(command="rapor", description="Tarih Aralığı İle Rapor Çek (/rapor 01.10.2026 28.10.2026)"),
        BotCommand(command="ref", description="Ref No ile Teklif Sorgula (/ref 46189ND)"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifleri İncele"),
        BotCommand(command="gecmis", description="Fabrika Parça Geçmişi (/gecmis Müşteri)"),
        BotCommand(command="sifirla", description="Tüm Verileri Sıfırla (0'la)"),
        BotCommand(command="yardim", description="Nasıl Kullanılır?")
    ]
    await bot.set_my_commands(commands)

# ==============================================================================
#                         1. BAŞLANGIÇ VE YARDIM
# ==============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.chat.id
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else message.from_user.first_name)
    
    welcome_text = (
        f"👋 **Selam {name}! Eliar Depo & İş Santrali Devrede.**\n"
        f"═══════════════════════════════\n\n"
        f"🚀 **SİSTEM KULLANIM REHBERİ**\n\n"
        f"📊 **Raporlama:**\n"
        f"└ `/zraporu` veya `/aylikrapor` ile rapor alın.\n"
        f"└ `/rapor 01.10.2026 28.10.2026` ile iki tarih arası özel rapor çekin.\n\n"
        f"📄 **Teklif & Evrak İşleme:**\n"
        f"└ PDF veya Fotoğraf attığınızda yapay zeka okuyup karşı tarafa iletir.\n\n"
        f"🔎 **Hızlı Sorgulama:**\n"
        f"└ `/ref [No]` ➔ Teklif detaylarını getirir (Örn: `/ref 46189ND`)\n"
        f"└ `/gecmis [Müşteri]` ➔ Tesise verilen tüm parçaları listeler.\n\n"
        f"⚙️ **Sistem:**\n"
        f"└ `/sifirla` ➔ Tüm verileri tamamen sıfırlar (0'lar).\n\n"
        f"═══════════════════════════════\n"
        f"💡 _Aşağıdaki menüden veya komut listesinden işlem seçebilirsiniz._"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(Command("sifirla"))
async def cmd_wipe_data(message: types.Message):
    save_stocks([])
    save_sales([])
    save_tasks({})
    await message.answer("🚨 **SİSTEM BAŞARIYLA SIFIRLANDI!**\nTüm stoklar, satış geçmişi ve görevler temizlendi. Sistem şu an tamamen boş (0).", parse_mode="Markdown")

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Eliar Bot Komut Rehberi:**\n\n"
        "1. `/stok` ➔ Fiyatsız tüm parça ve raf listesi.\n"
        "2. `/rapor [Başlangıç] [Bitiş]` ➔ İki tarih arası Excel/PDF rapor.\n"
        "3. `/ref [RefNo]` ➔ Teklifi referans numarasıyla bulur.\n"
        "4. `/gecmis [Müşteri]` ➔ O tesise geçmişte verilen parçalar.\n"
        "5. `/sifirla` ➔ Tüm verileri sıfırlar.",
        parse_mode="Markdown"
    )

# ==============================================================================
#                 2. PARÇA LİSTESİ (FİYATSIZ, KATEGORİZE STOK)
# ==============================================================================
@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stock_list(message: types.Message):
    stocks = load_stocks()
    if not stocks:
        await message.answer("📦 **Stok listesi şu an tamamen boş.**", parse_mode="Markdown")
        return

    kontrol = [s for s in stocks if s.get("cat") == "KONTROL"]
    elektronik = [s for s in stocks if s.get("cat") == "ELEKTRONIK"]
    mekatronik = [s for s in stocks if s.get("cat") == "MEKATRONIK"]
    
    text = "📦 **GÜNCEL ELİAR DEPO STOK LİSTESİ**\n═══════════════════════════════\n\n"
    if kontrol:
        text += "🎛️ **KONTROLÖRLER:**\n"
        for s in kontrol:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if elektronik:
        text += "\n⚡ **ELEKTRONİK:**\n"
        for s in elektronik:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if mekatronik:
        text += "\n⚙️ **MEKATRONİK:**\n"
        for s in mekatronik:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
        
    total_qty = sum(s.get("qty", 0) for s in stocks)
    text += f"\n═══════════════════════════════\n📊 Toplam Kalem: **{len(stocks)}** | Toplam Parça: **{total_qty} ADT**"
    await message.answer(text, parse_mode="Markdown")

# ==============================================================================
#        3. ELİAR TEKLİF REF NO SORGULAMA MOTORU (/ref 46189ND)
# ==============================================================================
def find_quote_by_ref(ref_query: str):
    sales = load_sales()
    query = ref_query.strip().upper()
    for s in sales:
        clean_ref = str(s.get("ref_no", "")).strip().upper()
        if clean_ref == query or (len(query) >= 4 and query in clean_ref):
            return s
    return None

@dp.message(Command("ref"))
async def cmd_ref_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Lütfen Referans Numarasını yazın.\nÖrnek: `/ref 46189ND`", parse_mode="Markdown")
        return
    
    ref_no = parts[1].strip()
    quote = find_quote_by_ref(ref_no)
    
    if not quote:
        await message.answer(f"🔍 `{ref_no}` referans numarasına ait teklif bulunamadı.", parse_mode="Markdown")
        return

    status_str = {
        "APPROVED": "🟢 ONAYLANDI (Satış)",
        "WAITING": "🟡 MÜŞTERİ BEKLİYOR",
        "REJECTED": "🔴 KABUL EDİLMEDİ (İptal)"
    }.get(quote.get("status"), "Bilinmiyor")

    text = (
        f"🔖 **TEKLİF DETAYI [Ref: {quote.get('ref_no')}]**\n"
        f"═══════════════════════════════\n"
        f"🏭 **Müşteri:** `{quote.get('firm')}`\n"
        f"📌 **Durum:** {status_str}\n"
        f"🕒 **Tarih:** {quote.get('date')}\n"
        f"👤 **Yükleyen / İşleyen:** {quote.get('uploaded_by', 'Ömer')}\n"
        f"═══════════════════════════════\n"
        f"📦 **TEKLİFTEKİ PARÇALAR:**\n"
    )
    for idx, item in enumerate(quote.get("items", []), 1):
        text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"

    if quote.get("status") == "WAITING":
        session_id = quote.get("id")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Şimdi Onaylandı", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🔴 İptal Et", callback_data=f"q_rej:{session_id}")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")

# ==============================================================================
#      4. TESİS PARÇA GEÇMİŞİ (BU MÜŞTERİYE DAHA ÖNCE NE VERDİK?)
# ==============================================================================
def get_client_history_text(firm_query: str):
    sales = load_sales()
    query = firm_query.strip().lower()
    matched = []
    for s in sales:
        if query in s.get("firm", "").lower() and s.get("status") == "APPROVED":
            matched.append(s)
            
    if not matched:
        return f"🔍 `{firm_query}` tesisi için geçmişte kayıtlı onaylı parça çıkışı bulunamadı."

    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    full_firm_name = matched[0].get("firm")
    
    text = f"🏢 **{full_firm_name} — PARÇA GEÇMİŞİ**\n"
    text += "═══════════════════════════════\n\n"
    
    for idx, item in enumerate(matched, 1):
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        if "items" in item and isinstance(item["items"], list):
            for sub_item in item["items"]:
                text += f"• 📅 `{item.get('date', 'Bilinmiyor')}` ➔ **{sub_item.get('qty')}x** `{sub_item.get('code')}` ({sub_item.get('name')}){ref_str}\n"
        else:
            text += f"• 📅 `{item.get('date', 'Bilinmiyor')}` ➔ **{item.get('qty')}x** `{item.get('code')}` ({item.get('name')}){ref_str}\n"
            
    text += "\n═══════════════════════════════\n"
    text += f"✅ Toplam Kayıt: **{len(matched)} Sevkiyat / Servis Hareketi**"
    return text

@dp.message(Command("gecmis"))
async def cmd_history_query(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Lütfen tesis adını belirtin.\nÖrnek: `/gecmis TERRY JAR` veya `/gecmis MICBRO`", parse_mode="Markdown")
        return
    res = get_client_history_text(parts[1])
    await message.answer(res, parse_mode="Markdown")

@dp.message(F.text == "🏢 Tesis Geçmişi")
async def btn_client_history(message: types.Message, state: FSMContext):
    await state.set_state(ClientHistoryState.waiting_client_name)
    await message.answer("🔍 Geçmişini görmek istediğiniz **Fabrika / Müşteri Adını** yazın:\n(Örn: `TERRY JAR` veya `MICBRO`)", parse_mode="Markdown")

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    query = message.text.strip()
    res = get_client_history_text(query)
    await message.answer(res, parse_mode="Markdown")

# ==============================================================================
#            5. EXCEL (.XLSX) VE RESMİ PDF (.PDF) RAPOR ÜRETİCİLERİ
# ==============================================================================
def generate_excel_z_report(sales_data, title="Z_Raporu"):
    today_str = datetime.now().strftime("%d_%m_%Y")
    excel_filename = f"Eliar_{title}_{today_str}.xlsx"
    
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satışlar"

        header_fill = PatternFill(start_color="161F30", end_color="161F30", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border_thin = Border(
            left=Side(style='thin', color='DDDDDD'),
            right=Side(style='thin', color='DDDDDD'),
            top=Side(style='thin', color='DDDDDD'),
            bottom=Side(style='thin', color='DDDDDD')
        )

        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet", "Durum"]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx = 2
        counter = 1
        for sale in sales_data:
            ref = str(sale.get("ref_no", "YOK"))
            firm = str(sale.get("firm", "Bilinmeyen"))
            date = str(sale.get("date", ""))
            
            for item in sale.get("items", []):
                ws.append([
                    counter,
                    date,
                    ref,
                    firm,
                    item.get("code", ""),
                    item.get("name", ""),
                    item.get("qty", 1),
                    "ONAYLANDI"
                ])
                for col_num in range(1, len(headers) + 1):
                    c = ws.cell(row=row_idx, column=col_num)
                    c.border = border_thin
                    if col_num in [1, 2, 3, 7, 8]:
                        c.alignment = Alignment(horizontal="center")
                row_idx += 1
                counter += 1

        col_widths = [8, 18, 14, 28, 16, 40, 10, 14]
        for idx, width in enumerate(col_widths, 1):
            col_letter = openpyxl.utils.get_column_letter(idx)
            ws.column_dimensions[col_letter].width = width

        wb.save(excel_filename)
        return excel_filename
    except Exception as e:
        logging.warning(f"openpyxl hatası, CSV yedeği alınıyor: {e}")
        import csv
        csv_filename = f"Eliar_{title}_{today_str}.csv"
        with open(csv_filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Sıra", "Tarih", "Ref No", "Müşteri", "Ürün Kodu", "Ürün Adı", "Adet", "Durum"])
            cnt = 1
            for s in sales_data:
                for itm in s.get("items", []):
                    writer.writerow([cnt, s.get("date"), s.get("ref_no"), s.get("firm"), itm.get("code"), itm.get("name"), itm.get("qty"), "ONAYLANDI"])
                    cnt += 1
        return csv_filename

# Türkçe karakterlerin PDF içinde kutucuk olmasını önleyen filtre fonksiyonu
def tr_fix(text):
    tr_map = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")
    return str(text).translate(tr_map)

def generate_pdf_z_report(sales_data, title="Z_Raporu"):
    today_str = datetime.now().strftime("%d_%m_%Y")
    pdf_filename = f"Eliar_{title}_{today_str}.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        doc = SimpleDocTemplate(
            pdf_filename,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor('#161F30'),
            alignment=1,
            spaceAfter=4
        )
        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
            spaceAfter=12
        )

        # İstenen kurumsal yeni başlık
        elements.append(Paragraph(tr_fix("ELIPS TEKSTIL ELIAR PARCA SATIS RAPORU"), title_style))
        elements.append(Paragraph(f"RESMI SATIS VE SEVKIYAT RAPORU - {datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_style))

        headers = ["Sira", "Tarih", "Ref No", "Musteri / Tesis", "Urun Kodu", "Urun Adi", "Adet"]
        data = [headers]

        counter = 1
        total_qty = 0
        for sale in sales_data:
            ref = tr_fix(sale.get("ref_no", "YOK"))
            firm = tr_fix(sale.get("firm", "Bilinmeyen"))
            date = tr_fix(sale.get("date", "")).split()[0]
            for item in sale.get("items", []):
                q = int(item.get("qty", 1))
                total_qty += q
                data.append([
                    str(counter),
                    date,
                    ref,
                    firm[:22],
                    tr_fix(str(item.get("code", ""))),
                    tr_fix(str(item.get("name", "")))[:28],
                    str(q)
                ])
                counter += 1

        # TOPLAM satırı ve hücre birleştirme (SPAN) ayarı
        data.append(["TOPLAM", "", "", "", "", "", str(total_qty)])

        col_widths = [30, 65, 60, 120, 75, 160, 45]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#161F30')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), "Helvetica"),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('ALIGN', (5, 1), (5, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), "Helvetica-Bold"),
            # TOPLAM yazısının sığması için 0. sütundan 5. sütuna kadar birleştirme:
            ('SPAN', (0, -1), (5, -1)),
            ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
        ]))
        elements.append(table)
        doc.build(elements)
        return pdf_filename
    except Exception as e:
        logging.error(f"PDF oluşturma hatası: {e}")
        return None

# ==============================================================================
#         6. TARİH SEÇİMLİ, HAFTALIK & AYLIK RAPOR MOTORLARI
# ==============================================================================
def build_weekly_report_data():
    sales = load_sales()
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    recent = []
    for s in sales:
        try:
            s_date = datetime.fromisoformat(s.get("timestamp", ""))
            if s_date >= one_week_ago and s.get("status") == "APPROVED":
                recent.append(s)
        except Exception:
            if s.get("status") == "APPROVED":
                recent.append(s)
    return recent

def build_monthly_report_data():
    sales = load_sales()
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    monthly = []
    for s in sales:
        try:
            s_date = datetime.fromisoformat(s.get("timestamp", ""))
            if s_date >= start_of_month and s.get("status") == "APPROVED":
                monthly.append(s)
        except Exception:
            if s.get("status") == "APPROVED":
                monthly.append(s)
    return monthly

def build_report_text(sales_data, report_name="HAFTALIK SATIŞ Z-RAPORU"):
    now = datetime.now()
    if not sales_data:
        return (
            f"📊 **ELİAR {report_name}**\n"
            f"📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n"
            "═══════════════════════════════\n"
            "ℹ️ _Bu dönem için henüz onaylanan parça satışı bulunmamaktadır._"
        )

    text = f"📊 **ELİAR {report_name}**\n"
    text += f"📅 Rapor Tarihi: {now.strftime('%d.%m.%Y %H:%M')}\n"
    text += "═══════════════════════════════\n\n"
    
    total_items = 0
    unique_clients = set()
    counter = 1

    for sale in sales_data:
        unique_clients.add(sale.get("firm", "Bilinmeyen"))
        ref_text = f" `[Ref: {sale.get('ref_no')}]`" if sale.get('ref_no') and sale.get('ref_no') != 'YOK' else ""
        
        for sub_i in sale.get("items", []):
            q = int(sub_i.get("qty", 1))
            total_items += q
            text += (
                f"**{counter}.** `{sub_i.get('code')}` — **{sub_i.get('name')}**\n"
                f"   └ 📦 Miktar: **{q} Adet**\n"
                f"   └ 🏭 Tesis: **{sale.get('firm')}**{ref_text}\n"
                f"   └ 🕒 Tarih: {sale.get('date')}\n\n"
            )
            counter += 1

    text += "───────────────────────────────\n"
    text += f"📦 **Toplam Satılan Parça:** {total_items} Adet\n"
    text += f"🏭 **Hizmet Verilen Tesis:** {len(unique_clients)} Fabrika\n"
    text += "═══════════════════════════════\n"
    text += "📂 _İndirmek istediğiniz dosya formatını seçin:_"
    return text

# YENİ ÖZELLİK: TARİH ARALIĞI İLE ÖZEL RAPOR ÇEKME (/rapor 01.10.2026 28.10.2026)
@dp.message(Command("rapor"))
async def custom_date_report(message: types.Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("⚠️ Lütfen tarih aralığını şu formatta girin:\n`/rapor 01.10.2026 28.10.2026`", parse_mode="Markdown")
        return
    
    start_str, end_str = parts[1], parts[2]
    try:
        start_date = datetime.strptime(start_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_str, "%d.%m.%Y").replace(hour=23, minute=59, second=59)
    except ValueError:
        await message.answer("⚠️ Tarih formatı hatalى. Örnek: `01.10.2026` şeklinde gün.ay.yıl yazmalısınız.", parse_mode="Markdown")
        return

    sales = load_sales()
    filtered_sales = []
    for s in sales:
        if s.get("status") == "APPROVED":
            try:
                s_date = datetime.fromisoformat(s.get("timestamp", ""))
                if start_date <= s_date <= end_date:
                    filtered_sales.append(s)
            except Exception:
                pass

    if not filtered_sales:
        await message.answer(f"🔍 `{start_str}` ile `{end_str}` tarihleri arasında onaylı satış kaydı bulunamadı.", parse_mode="Markdown")
        return

    await message.answer(f"⏳ `{start_str}` - `{end_str}` arası rapor Excel ve PDF olarak hazırlanıyor...", parse_mode="Markdown")
    
    title = f"Ozel_Rapor_{start_str}_{end_str}"
    excel_file = generate_excel_z_report(filtered_sales, title)
    pdf_file = generate_pdf_z_report(filtered_sales, title)
    
    if os.path.exists(excel_file):
        await message.answer_document(document=FSInputFile(excel_file), caption=f"📊 **{start_str} - {end_str} Excel Raporu**")
    if pdf_file and os.path.exists(pdf_file):
        await message.answer_document(document=FSInputFile(pdf_file), caption=f"📑 **{start_str} - {end_str} PDF Raporu**")

@dp.message(Command("zraporu"))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    sales_data = build_weekly_report_data()
    report_text = build_report_text(sales_data, "HAFTALIK SATIŞ Z-RAPORU")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Excel İndir (.xlsx)", callback_data="dl_rep:excel:weekly"),
            InlineKeyboardButton(text="📑 PDF İndir (.pdf)", callback_data="dl_rep:pdf:weekly")
        ],
        [
            InlineKeyboardButton(text="📦 İkisini de İndir (Excel + PDF)", callback_data="dl_rep:both:weekly")
        ]
    ])
    await message.answer(report_text, reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("aylikrapor"))
async def trigger_monthly_report_manual(message: types.Message):
    month_name = datetime.now().strftime("%B %Y")
    sales_data = build_monthly_report_data()
    report_text = build_report_text(sales_data, f"AYLIK SATIŞ RAPORU ({month_name})")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Excel İndir (.xlsx)", callback_data="dl_rep:excel:monthly"),
            InlineKeyboardButton(text="📑 PDF İndir (.pdf)", callback_data="dl_rep:pdf:monthly")
        ],
        [
            InlineKeyboardButton(text="📦 İkisini de İndir (Excel + PDF)", callback_data="dl_rep:both:monthly")
        ]
    ])
    await message.answer(report_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_rep:"))
async def handle_download_report_choice(callback: types.CallbackQuery):
    _, fmt, scope = callback.data.split(":")
    sales_data = build_weekly_report_data() if scope == "weekly" else build_monthly_report_data()
    title = "Haftalik_Z_Raporu" if scope == "weekly" else "Aylik_Satis_Raporu"
    
    if not sales_data:
        await callback.answer("Bu dönem için onaylı satış kaydı bulunmuyor.", show_alert=True)
        return

    await callback.answer("Döküman hazırlanıyor...")

    if fmt in ["excel", "both"]:
        excel_file = generate_excel_z_report(sales_data, title)
        if os.path.exists(excel_file):
            await callback.message.answer_document(
                document=FSInputFile(excel_file),
                caption=f"📊 **Eliar {title} (Excel)**"
            )

    if fmt in ["pdf", "both"]:
        pdf_file = generate_pdf_z_report(sales_data, title)
        if pdf_file and os.path.exists(pdf_file):
            await callback.message.answer_document(
                document=FSInputFile(pdf_file),
                caption=f"📑 **Eliar {title} (PDF)**"
            )

# ==============================================================================
#    7. ÇOKLU PARÇA OKUYAN TEKLİF AYRIŞTIRICI (PDF & FOTOĞRAF)
# ==============================================================================
def parse_quote_media(file_path: str, is_pdf: bool = False, original_filename: str = ""):
    firm = None
    ref_no = None
    items = []

    clean_fn = re.sub(r"(fiyat|teklif|teklifi|\.pdf|\.jpg|\.png|temp_doc_\w+)", "", original_filename, flags=re.IGNORECASE).strip()
    clean_fn = re.sub(r"^[_\-\s]+|[_\-\s]+$", "", clean_fn)
    if len(clean_fn) >= 3:
        firm = clean_fn

    if GEMINI_API_KEY and GEMINI_API_KEY != "BURAYA_GEMINI_API_KEY_YAZIN":
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            mime_type = "application/pdf" if is_pdf else "image/jpeg"
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            prompt = (
                "Sen bir endüstriyel teklif analiz uzmanısın. Ek'teki Eliar teklif formunu incele. "
                "Saf JSON formatında şu yapıda dön:\n"
                "{\n"
                "  \"firm\": \"Müşteri Adı\",\n"
                "  \"ref_no\": \"Ref No (Varsa)\",\n"
                "  \"items\": [\n"
                "    {\"code\": \"Ürün Kodu\", \"name\": \"Ürün Adı\", \"qty\": 1}\n"
                "  ]\n"
                "}\n"
                "Fiyatları dahil etme. Markdown etiketi olmadan saf JSON döndür."
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, genai.types.Part.from_bytes(data=file_bytes, mime_type=mime_type)]
            )
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            res = json.loads(clean_json)
            if res.get("items") and res.get("firm"):
                return res
        except Exception as e:
            logging.error(f"Gemini API Hatası: {e}")

    if not firm or "İlgili Kişi" in firm:
        firm = clean_fn if len(clean_fn) >= 3 else "MICBRO TEKSTİL"
        
    if not items:
        items = [{"code": "BILINMIYOR", "name": "Teklif Kalemleri Okunamadı", "qty": 1}]

    return {
        "firm": firm,
        "ref_no": ref_no or "BELİRTİLMEDİ",
        "items": items
    }

@dp.message(F.photo | F.document)
async def handle_quote_media(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi"]:
        return

    is_pdf = False
    doc_name = ""

    if message.document:
        doc_name = message.document.file_name or ""
        lower_name = doc_name.lower()
        if lower_name.endswith(".pdf"):
            is_pdf = True
        elif not lower_name.endswith((".jpg", ".jpeg", ".png")):
            return

    try:
        uploader_name = "Ömer" if message.chat.id == OMER_CHAT_ID else ("Kamil" if message.chat.id == KAMIL_CHAT_ID else message.from_user.first_name)
        target_chat_id = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else OMER_CHAT_ID
        doc_type_str = f"PDF Belgesi ({doc_name})" if is_pdf else "Teklif Görseli"
        
        status_msg = await message.reply(f"🔍 _Eliar {doc_type_str} taranıyor ve karşı tarafa aktarılıyor..._", parse_mode="Markdown")

        try:
            if is_pdf:
                await bot.send_document(chat_id=target_chat_id, document=message.document.file_id, caption=f"📑 **{uploader_name} yeni bir teklif PDF'i paylaştı!**")
            elif message.photo:
                await bot.send_photo(chat_id=target_chat_id, photo=message.photo[-1].file_id, caption=f"📷 **{uploader_name} yeni bir teklif görseli paylaştı!**")
        except Exception as err:
            logging.warning(f"Orijinal dosya iletilemedi: {err}")

        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        file = await bot.get_file(file_id)
        ext = ".pdf" if is_pdf else ".jpg"
        local_filename = f"temp_doc_{message.message_id}_{int(time.time())}{ext}"
        await bot.download_file(file.file_path, local_filename)

        data = parse_quote_media(local_filename, is_pdf=is_pdf, original_filename=doc_name)
        
        if os.path.exists(local_filename):
            try: os.remove(local_filename)
            except Exception: pass

        session_id = f"Q-{int(time.time()*1000)}"
        sales = load_sales()
        sales.append({
            "id": session_id,
            "firm": data.get("firm", "Bilinmeyen"),
            "ref_no": data.get("ref_no", "YOK"),
            "items": data.get("items", []),
            "status": "WAITING",
            "uploaded_by": uploader_name,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        icon = "📑" if is_pdf else "📄"
        result_text = (
            f"{icon} **ELİAR TEKLİF FORMU ALGILANDI!**\n"
            f"👤 _Paylaşan: {uploader_name}_\n"
            f"═══════════════════════════════\n"
            f"🏭 **Müşteri:** `{data.get('firm')}`\n"
            f"🔖 **Ref No:** `{data.get('ref_no')}`\n"
            f"═══════════════════════════════\n"
            f"📦 **TALEP EDİLEN PARÇALAR:**\n"
        )
        for idx, item in enumerate(data.get("items", []), 1):
            result_text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Müşteri Onayladı (Satış)", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🟡 Müşteri Bekliyor", callback_data=f"q_wait:{session_id}")],
            [InlineKeyboardButton(text="🔴 Müşteri Kabul Etmedi", callback_data=f"q_rej:{session_id}")]
        ])

        try: await status_msg.delete()
        except Exception: pass
        
        await notify_both(result_text, reply_markup=kb)

    except Exception as e:
        logging.exception("handle_quote_media hatası:")
        await message.reply(f"⚠️ Dosya taranırken hata oluştu: `{e}`", parse_mode="Markdown")

# ==============================================================================
#      8. TEKLİF BUTONLARI VE İŞLEM YÖNETİMİ
# ==============================================================================
@dp.callback_query(F.data.startswith("q_wait:"))
async def quote_waiting(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    for s in sales:
        if s.get("id") == session_id:
            s["status"] = "WAITING"
            s["decided_by"] = operator
            break
    save_sales(sales)
    await callback.message.edit_text(callback.message.text + f"\n\n🟡 **DURUM: MÜŞTERİ BEKLİYOR** ({operator})", reply_markup=None)
    await callback.answer("Beklemeye alındı.")

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    stocks = load_stocks()
    target_sale = None
    
    for s in sales:
        if s.get("id") == session_id:
            s["status"] = "APPROVED"
            s["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            s["decided_by"] = operator
            target_sale = s
            break
    save_sales(sales)

    if target_sale and "items" in target_sale:
        for item in target_sale["items"]:
            code = item.get("code")
            qty = int(item.get("qty", 1))
            for st in stocks:
                if st.get("code") == code:
                    st["qty"] = max(0, st["qty"] - qty)
                    break
        save_stocks(stocks)

    await callback.message.edit_text(callback.message.text + f"\n\n🟢 **ONAYLANDI!** ({operator})", reply_markup=None)
    await notify_both(f"🟢 **TEKLİF ONAYLANDI!**\n🏭 Tesis: `{target_sale.get('firm')}`\n👷‍♂️ İşlemi Yapan: {operator}\n✅ Parçalar stoktan düşüldü.")
    await callback.answer("Onaylandı.")

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    for s in sales:
        if s.get("id") == session_id:
            s["status"] = "REJECTED"
            s["decided_by"] = operator
            break
    save_sales(sales)
    await callback.message.edit_text(callback.message.text + f"\n\n🔴 **İPTAL EDİLDİ.** ({operator})", reply_markup=None)
    await callback.answer("İptal edildi.")

@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    sales = load_sales()
    waiting_sales = [s for s in sales if s.get("status") == "WAITING"]
    if not waiting_sales:
        return await message.answer("⏳ **Onay bekleyen teklif bulunmuyor.**", parse_mode="Markdown")

    for s in waiting_sales:
        session_id = s.get("id")
        text = f"🏭 **Tesis:** `{s.get('firm')}`\n🔖 **Ref:** `{s.get('ref_no')}`\n"
        for itm in s.get("items", []):
            text += f" • `{itm.get('code')}` ({itm.get('qty')} Adet)\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Onayla", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{session_id}")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# ==============================================================================
#             9. WEBAPP VERİLERİ VE TELSİZ / İKİLİ MESAJLAŞMA
# ==============================================================================
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try:
        payload = json.loads(message.web_app_data.data)
    except Exception:
        return

    direction = payload.get("direction")
    operator = "Ömer" if message.chat.id == OMER_CHAT_ID else ("Kamil" if message.chat.id == KAMIL_CHAT_ID else message.from_user.first_name)
    req_id = f"REF-{message.message_id}"

    if direction == "STOCK_CHANGE" and payload.get("action") == "DECREASE":
        dest = payload.get("destination") or "Belirtilmedi"
        qty = payload.get("delta", 1)
        code = payload.get("code")
        name = payload.get("name")
        
        sales = load_sales()
        sales.append({
            "id": req_id, "firm": dest, "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}],
            "status": "APPROVED", "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        await notify_both(f"📤 **PARÇA ÇIKIŞI!**\n📍 Yer: `{dest}`\n⚙️ Parça: `{code}` (-{qty} Adet)\n👷‍♂️ Yapan: {operator}")

    elif direction == "OMER_TO_KAMIL":
        kamil_text = f"🔔 **ÖMER'DEN TALEP:** {payload.get('firm')}\n⚙️ Kod: `{payload.get('part_code')}` ({payload.get('quantity')} Adet)"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Onayla", callback_data=f"otk_ok:{req_id}"), InlineKeyboardButton(text="❌ Reddet", callback_data=f"otk_no:{req_id}")]])
        await bot.send_message(chat_id=KAMIL_CHAT_ID, text=kamil_text, reply_markup=kb)

    elif direction == "KAMIL_TO_OMER":
        omer_text = f"📋 **KAMİL'DEN İŞ EMRİ:** {payload.get('firm')}\n🔧 Görev: `{payload.get('task_type')}`"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👍 Aldım", callback_data=f"o_ack:{req_id}"), InlineKeyboardButton(text="✅ Bitti", callback_data=f"o_done:{req_id}")]])
        await bot.send_message(chat_id=OMER_CHAT_ID, text=omer_text, reply_markup=kb)

@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi"]:
        return
    sender_id = message.chat.id
    target_id = OMER_CHAT_ID if sender_id == KAMIL_CHAT_ID else (KAMIL_CHAT_ID if sender_id == OMER_CHAT_ID else None)
    sender_name = "Kamil" if sender_id == KAMIL_CHAT_ID else "Ömer"
    if target_id and message.text:
        await bot.send_message(chat_id=target_id, text=f"💬 **{sender_name}:** {message.text}")
        await message.reply("✓", parse_mode="Markdown")

# ==============================================================================
#             RENDER İÇİN SAHTE WEB SUNUCUSU (PORT BINDING)
# ==============================================================================
async def handle(request):
    return web.Response(text="Eliar Bot 7/24 Aktif ve Çalışıyor!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Render web portu açıldı: {port}")

async def main():
    await setup_bot_commands()
    await start_dummy_server()
    print("🚀 Eliar Canlı Santral Başlatıldı!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
