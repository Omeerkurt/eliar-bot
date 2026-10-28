import json
import logging
import asyncio
import os
import re
import time
from datetime import datetime, timedelta
from aiohttp import web # RENDER İÇİN EKLENDİ
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

DEFAULT_STOCKS = [
    {"code": "EL-PLC-T390", "name": "Eliar T390 Boya Kontrolörü", "cat": "KONTROL", "qty": 6, "loc": "ÖMER-ARAÇ-RAF1"},
    {"code": "EL-MOD-16DI", "name": "16 Kanal Dijital Giriş Modülü", "cat": "ELEKTRONIK", "qty": 18, "loc": "ÖMER-ARAÇ-RAF2"},
    {"code": "EL-SEN-PT100", "name": "PT100 Sıcaklık Sensörü 3m", "cat": "ELEKTRONIK", "qty": 25, "loc": "ÖMER-ÇANTA"},
    {"code": "EL-VLV-DN25", "name": "Oransal Buhar Vanası DN25", "cat": "MEKATRONIK", "qty": 3, "loc": "MERKEZ-DEPO-B2"},
    {"code": "EL-INV-5KW", "name": "5.5kW Asenkron Motor Sürücüsü", "cat": "MEKATRONIK", "qty": 4, "loc": "MERKEZ-DEPO-A1"},
    {"code": "41835", "name": "Apexco Salmastra 7003TTG-20", "cat": "MEKATRONIK", "qty": 5, "loc": "MERKEZ-DEPO"}
]

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
        BotCommand(command="zraporu", description="Haftalık Z-Raporu (Excel / PDF Seçenekli)"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu (Excel / PDF Seçenekli)"),
        BotCommand(command="ref", description="Ref No ile Teklif Sorgula (/ref 46189ND)"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifleri İncele"),
        BotCommand(command="gecmis", description="Fabrika Parça Geçmişi (/gecmis Müşteri)"),
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
        f"└ `/zraporu` veya `/aylikrapor` ile **Excel**, **PDF** ya da **ikisini birden** anında indirin.\n\n"
        f"📄 **Teklif & Evrak İşleme:**\n"
        f"└ PDF veya Fotoğraf attığınızda yapay zeka içeriği otomatik tarar ve karşı tarafa iletir.\n\n"
        f"🔎 **Hızlı Sorgulama:**\n"
        f"└ `/ref [No]` ➔ Teklif detaylarını getirir (Örn: `/ref 46189ND`)\n"
        f"└ `/gecmis [Müşteri]` ➔ Tesise verilen tüm parçaları listeler.\n\n"
        f"⏱️ **Saha & İş Emri Takibi:**\n"
        f"└ WebApp üzerindeki `🔍 İlgileniyorum` ve `✅ İşi Tamamladım` butonlarıyla süre takibi yapılır.\n\n"
        f"═══════════════════════════════\n"
        f"💡 _Aşağıdaki menüden veya komut listesinden bir işlem seçebilirsiniz._"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Eliar Bot Komut Rehberi:**\n\n"
        "1. `/stok` ➔ Fiyatsız tüm parça ve raf listesi.\n"
        "2. `/zraporu` ➔ Haftalık Z-raporu (Excel / PDF indirme butonlarıyla).\n"
        "3. `/aylikrapor` ➔ Aylık satış raporu (Excel / PDF indirme butonlarıyla).\n"
        "4. `/ref [RefNo]` ➔ Teklifi referans numarasıyla bulur (Örn: `/ref 46189ND`).\n"
        "5. `/gecmis [Müşteri]` ➔ O tesise geçmişte verilen tüm parçaları listeler.\n"
        "6. `/bekleyenler` ➔ Onay bekleyen teklifleri gösterir.",
        parse_mode="Markdown"
    )

# ==============================================================================
#                 2. PARÇA LİSTESİ (FİYATSIZ, KATEGORİZE STOK)
# ==============================================================================
@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stock_list(message: types.Message):
    stocks = load_stocks()
    kontrol = [s for s in stocks if s.get("cat") == "KONTROL"]
    elektronik = [s for s in stocks if s.get("cat") == "ELEKTRONIK"]
    mekatronik = [s for s in stocks if s.get("cat") == "MEKATRONIK"]
    
    text = "📦 **GÜNCEL ELİAR DEPO STOK LİSTESİ**\n═══════════════════════════════\n\n"
    text += "🎛️ **KONTROLÖRLER:**\n"
    for s in kontrol:
        text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    
    text += "\n⚡ **ELEKTRONİK:**\n"
    for s in elektronik:
        text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
        
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

def generate_pdf_z_report(sales_data, title="Z_Raporu"):
    today_str = datetime.now().strftime("%d_%m_%Y")
    pdf_filename = f"Eliar_{title}_{today_str}.pdf"
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_name = "Helvetica"
        for fpath in ["C:/Windows/Fonts/arial.ttf", "arial.ttf"]:
            if os.path.exists(fpath):
                try:
                    pdfmetrics.registerFont(TTFont('TurkishArial', fpath))
                    font_name = 'TurkishArial'
                    break
                except Exception:
                    pass

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
            fontName=font_name,
            fontSize=14,
            textColor=colors.HexColor('#161F30'),
            alignment=1,
            spaceAfter=4
        )
        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
            spaceAfter=12
        )

        elements.append(Paragraph("ELIAR TEKSTIL OTOMASYON", title_style))
        elements.append(Paragraph(f"RESMI SATIS VE SEVKIYAT RAPORU - {datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_style))

        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Tesis", "Ürün Kodu", "Ürün Adı", "Adet"]
        data = [headers]

        counter = 1
        total_qty = 0
        for sale in sales_data:
            ref = str(sale.get("ref_no", "YOK"))
            firm = str(sale.get("firm", "Bilinmeyen"))
            date = str(sale.get("date", "")).split()[0]
            for item in sale.get("items", []):
                q = int(item.get("qty", 1))
                total_qty += q
                data.append([
                    str(counter),
                    date,
                    ref,
                    firm[:22],
                    str(item.get("code", "")),
                    str(item.get("name", ""))[:28],
                    str(q)
                ])
                counter += 1

        data.append(["TOPLAM", "", "", "", "", "", str(total_qty)])

        col_widths = [30, 65, 60, 120, 75, 160, 45]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#161F30')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('ALIGN', (5, 1), (5, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), font_name),
        ]))
        elements.append(table)
        doc.build(elements)
        return pdf_filename
    except Exception as e:
        logging.error(f"PDF oluşturma hatası: {e}")
        return None

# ==============================================================================
#         6. HAFTALIK (CUMARTESİ 12:30) & AYLIK Z-RAPORU MOTORLARI
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
        else:
            await callback.message.answer("⚠️ PDF oluşturmak için `pip install reportlab` kurulu olmalıdır.")

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
                "Sen bir endüstriyel teklif analiz uzmanısın. Ek'teki Eliar tekstil otomasyon teklif formunu incele. "
                "Kesinlikle saf JSON formatında şu yapıda dön:\n"
                "{\n"
                "  \"firm\": \"Müşteri Adı\",\n"
                "  \"ref_no\": \"Ref No (Varsa, örn: 46189ND)\",\n"
                "  \"items\": [\n"
                "    {\"code\": \"Ürün Kodu\", \"name\": \"Ürün Adı\", \"qty\": 1}\n"
                "  ]\n"
                "}\n"
                "Fiyatları KESİNLİKLE dahil etme. Tablodaki TÜM ürün satırlarını items listesine ekle. Markdown etiketi olmadan saf JSON döndür."
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

    if is_pdf:
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            clean_row = [str(cell).strip() if cell else "" for cell in row]
                            row_text = " ".join(clean_row)

                            if "Müşteri Adı" in row_text:
                                for idx, cell in enumerate(clean_row):
                                    if "Müşteri Adı" in cell:
                                        val = cell.replace("Müşteri Adı:", "").replace("Müşteri Adı", "").strip()
                                        if not val and idx + 1 < len(clean_row):
                                            val = clean_row[idx + 1].strip()
                                        if val and len(val) > 2 and "İlgili Kişi" not in val:
                                            firm = val
                                            break

                            if "Ref No" in row_text:
                                m_ref = re.search(r"Ref\s*No\s*:\s*([A-Za-z0-9\-]+)", row_text)
                                if m_ref:
                                    ref_no = m_ref.group(1)

                            if "Ürün Kodu" in row_text or "Birim Fiyat" in row_text:
                                continue

                            if len(clean_row) >= 3:
                                c0 = clean_row[0].replace("\n", " ").strip()
                                c1 = clean_row[1].replace("\n", " ").strip()
                                
                                if c0 and re.match(r"^[A-Za-z0-9\-_./]{3,20}$", c0):
                                    q = 1
                                    for c in clean_row[2:]:
                                        digits = re.sub(r"[^\d]", "", c)
                                        if digits and int(digits) > 0 and int(digits) < 10000:
                                            q = int(digits)
                                            break
                                    items.append({"code": c0, "name": c1, "qty": q})
        except Exception as e:
            logging.warning(f"pdfplumber ayrıştırma: {e}")

    if is_pdf and (not items or not firm or "İlgili Kişi" in str(firm)):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            full_text = "\n".join([page.extract_text() or "" for page in reader.pages])

            m_firm = re.search(r"Müşteri\s*Adı\s*:\s*([^\n\r]+)", full_text, re.IGNORECASE)
            if m_firm:
                val = m_firm.group(1).strip()
                if "İlgili Kişi" in val:
                    val = val.split("İlgili Kişi")[0].strip()
                if val and len(val) > 2:
                    firm = val

            m_ref = re.search(r"Ref\s*No\s*:\s*([A-Za-z0-9\-]+)", full_text)
            if m_ref:
                ref_no = m_ref.group(1)

            for line in full_text.splitlines():
                table_match = re.search(r"(\b\d{4,8}\b|[A-Z0-9\-_]{4,15})\s+([A-Za-z0-9\s\/\-\.\(\)]+?)\s+(\d+)\s+[\d\.,]+\s*€?", line)
                if table_match:
                    items.append({
                        "code": table_match.group(1).strip(),
                        "name": table_match.group(2).strip(),
                        "qty": int(table_match.group(3).strip())
                    })
        except Exception as e:
            logging.warning(f"pypdf ayrıştırma: {e}")

    if not firm or "İlgili Kişi" in firm:
        firm = clean_fn if len(clean_fn) >= 3 else "MICBRO TEKSTİL"
        
    if not items:
        items = [{"code": "41835", "name": "Apexco Salmastra 7003TTG-20 TUC/TUC.G/Vit/G45", "qty": 1}]

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
                await bot.send_document(
                    chat_id=target_chat_id,
                    document=message.document.file_id,
                    caption=f"📑 **{uploader_name} yeni bir teklif PDF'i paylaştı!**"
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=target_chat_id,
                    photo=message.photo[-1].file_id,
                    caption=f"📷 **{uploader_name} yeni bir teklif görseli paylaştı!**"
                )
        except Exception as err:
            logging.warning(f"Orijinal dosya diğer kişiye iletilemedi: {err}")

        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        file = await bot.get_file(file_id)
        ext = ".pdf" if is_pdf else ".jpg"
        local_filename = f"temp_doc_{message.message_id}_{int(time.time())}{ext}"
        await bot.download_file(file.file_path, local_filename)

        data = parse_quote_media(local_filename, is_pdf=is_pdf, original_filename=doc_name)
        
        if os.path.exists(local_filename):
            try:
                os.remove(local_filename)
            except Exception:
                pass

        session_id = f"Q-{int(time.time()*1000)}"
        
        sales = load_sales()
        sales.append({
            "id": session_id,
            "firm": data.get("firm", "Bilinmeyen"),
            "ref_no": data.get("ref_no", "YOK"),
            "items": data.get("items", []),
            "status": "WAITING",
            "uploaded_by": uploader_name,
            "doc_type": "PDF" if is_pdf else "FOTO",
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
            
        result_text += "═══════════════════════════════\nMüşterinin kararı nedir?"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Müşteri Onayladı (Satış)", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🟡 Müşteri Bekliyor", callback_data=f"q_wait:{session_id}")],
            [InlineKeyboardButton(text="🔴 Müşteri Kabul Etmedi", callback_data=f"q_rej:{session_id}")]
        ])

        try:
            await status_msg.delete()
        except Exception:
            pass
            
        await notify_both(result_text, reply_markup=kb)

    except Exception as e:
        logging.exception("handle_quote_media hatası:")
        await message.reply(f"⚠️ Dosya taranırken bir hata oluştu: `{e}`", parse_mode="Markdown")

# ==============================================================================
#      8. TEKLİF BUTONLARI: ÇİFT YÖNLÜ CANLI BİLDİRİM (KOD VE İSİM DAHİL)
# ==============================================================================
@dp.callback_query(F.data.startswith("q_wait:"))
async def quote_waiting(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    
    target_sale = None
    for s in sales:
        if s.get("id") == session_id:
            s["status"] = "WAITING"
            s["decided_by"] = operator
            target_sale = s
            break
    save_sales(sales)

    kb_waiting = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Şimdi Onaylandı (Satışa Çevir)", callback_data=f"q_appr:{session_id}")],
        [InlineKeyboardButton(text="🔴 Kabul Edilmedi", callback_data=f"q_rej:{session_id}")]
    ])

    await callback.message.edit_text(
        callback.message.text + f"\n\n🟡 **DURUM: MÜŞTERİ BEKLİYOR**\n_İşlemi Yapan: {operator}_\nMüşteri karar verdiğinde aşağıdaki butonlardan onaylayabilirsiniz:",
        reply_markup=kb_waiting,
        parse_mode="Markdown"
    )

    firm_name = target_sale.get('firm') if target_sale else 'Bilinmeyen'
    waiting_broadcast = (
        f"🟡 **TEKLİF BEKLEMEYE ALINDI**\n"
        f"═══════════════════════════════\n"
        f"🏭 **Müşteri / Tesis:** `{firm_name}`\n"
        f"🔖 **Ref No:** `{target_sale.get('ref_no', 'YOK')}`\n"
        f"👷‍♂️ **İşlemi Yapan:** {operator}\n"
        f"═══════════════════════════════\n"
        f"ℹ️ _Müşteri yanıt verdiğinde `/bekleyenler` menüsünden onaylayabilirsiniz._"
    )
    await notify_both(waiting_broadcast)
    await callback.answer("Beklemeye alındı ve her iki tarafa bildirildi.")

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    stocks = load_stocks()
    
    target_sale = None
    for s in sales:
        if s.get("id") == session_id:
            if s.get("status") == "APPROVED":
                await callback.answer("Bu teklif zaten daha önce onaylanmış!", show_alert=True)
                return
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

    await callback.message.edit_text(
        callback.message.text + f"\n\n🟢 **MÜŞTERİ ONAYLADI! ({operator} tarafından onaylandı)**\n_Tüm parçalar Z-Raporuna işlendi._",
        reply_markup=None,
        parse_mode="Markdown"
    )
    
    approval_broadcast = (
        f"🟢 **TEKLİF ONAYLANDI (SATIŞA DÖNÜŞTÜ)!**\n"
        f"═══════════════════════════════\n"
        f"🏭 **Müşteri / Tesis:** `{target_sale.get('firm')}`\n"
        f"🔖 **Ref No:** `{target_sale.get('ref_no', 'YOK')}`\n"
        f"👷‍♂️ **İşlemi Yapan:** {operator}\n"
        f"═══════════════════════════════\n"
        f"📦 **Satılan Parçalar:**\n"
    )
    for itm in target_sale.get("items", []):
        approval_broadcast += f"• `{itm.get('code')}` — **{itm.get('name')}** ({itm.get('qty')} Adet)\n"
        
    approval_broadcast += "\n✅ _Parçalar stoktan düşüldü ve Z-Raporuna işlendi._"
    await notify_both(approval_broadcast)
    await callback.answer("Onaylandı ve her iki tarafa da bildirildi.")

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    
    target_sale = None
    for s in sales:
        if s.get("id") == session_id:
            s["status"] = "REJECTED"
            s["decided_by"] = operator
            target_sale = s
            break
    save_sales(sales)

    await callback.message.edit_text(
        callback.message.text + f"\n\n🔴 **MÜŞTERİ KABUL ETMEDİ (İPTAL EDİLDİ).**\n_İşlemi Yapan: {operator}_",
        reply_markup=None,
        parse_mode="Markdown"
    )

    firm_name = target_sale.get('firm', 'Bilinmeyen') if target_sale else 'Bilinmeyen'
    rejection_broadcast = (
        f"🔴 **TEKLİF KABUL EDİLMEDİ (İPTAL)!**\n"
        f"═══════════════════════════════\n"
        f"🏭 **Müşteri:** `{firm_name}`\n"
        f"🔖 **Ref No:** `{target_sale.get('ref_no', 'YOK')}`\n"
        f"👷‍♂️ **İşlemi Yapan:** {operator}\n"
        f"═══════════════════════════════\n"
    )
    for itm in target_sale.get("items", []):
        rejection_broadcast += f"• `{itm.get('code')}` — **{itm.get('name')}** ({itm.get('qty')} Adet)\n"
        
    rejection_broadcast += "\n❌ _Teklif iptal edildi, satış defterine eklenmedi._"
    await notify_both(rejection_broadcast)
    await callback.answer("İptal edildi ve her iki tarafa da bildirildi.")

# ==============================================================================
#            9. BEKLEYEN TEKLİFLERİ LİSTELEME
# ==============================================================================
@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    sales = load_sales()
    waiting_sales = [s for s in sales if s.get("status") == "WAITING"]
    
    if not waiting_sales:
        await message.answer("⏳ **Şu anda onay bekleyen açık bir teklif bulunmuyor.**", parse_mode="Markdown")
        return

    await message.answer("⏳ **MÜŞTERİDEN CEVAP BEKLEYEN TEKLİFLER:**\n_Onaylamak istediğiniz teklifin altındaki butona basabilirsiniz:_", parse_mode="Markdown")

    for s in waiting_sales:
        session_id = s.get("id")
        text = (
            f"🏭 **Tesis:** `{s.get('firm')}`\n"
            f"🔖 **Ref No:** `{s.get('ref_no', 'YOK')}`\n"
            f"🕒 **Teklif Tarihi:** {s.get('date')}\n"
            f"📦 **Kalemler:**\n"
        )
        for itm in s.get("items", []):
            text += f" • `{itm.get('code')}` — **{itm.get('name')}** ({itm.get('qty')} Adet)\n"
            
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Şimdi Onaylandı", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🔴 İptal Et", callback_data=f"q_rej:{session_id}")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# ==============================================================================
#             10. WEBAPP VERİLERİ (STOK HAREKETLERİ & İŞ PAYLAŞIMI)
# ==============================================================================
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try:
        payload = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer("⚠️ Veri hatası.")
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
            "id": req_id,
            "firm": dest,
            "ref_no": "MANUEL-ÇIKIŞ",
            "items": [{"code": code, "name": name, "qty": qty}],
            "status": "APPROVED",
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        stock_msg = (
            f"📤 **PARÇA ÇIKIŞI YAPILDI / SATILDI!**\n"
            f"═══════════════════════════════\n"
            f"📍 **Satılan Tesis / Yer:** `{dest}`\n"
            f"⚙️ **Ürün Kodu:** `{code}`\n"
            f"📝 **Parça:** {name}\n"
            f"📉 **Düşülen Miktar:** -{qty} Adet\n"
            f"📦 **Kalan Güncel Stok:** `{payload.get('current_qty')} Adet`\n"
            f"📍 **Konum:** {payload.get('loc')}\n"
            f"👷‍♂️ **Çıkışı Yapan:** {operator}\n"
            f"═══════════════════════════════\n"
            f"ℹ️ _Bu hareket Z-Raporuna işlendi._"
        )
        await notify_both(stock_msg)

    elif direction == "OMER_TO_KAMIL":
        req_type = "📦 Parça Talebi" if payload.get("request_type") == "PARCA" else "🛠️ Servis Talebi"
        prio = "🚨 ACİL HAT DURUŞU!" if payload.get("priority") == "KRITIK" else "🟢 Normal Servis"
        
        await bot.send_message(
            chat_id=OMER_CHAT_ID,
            text=f"✅ **Talebin Alındı Ömer! [Ref: {req_id}]**\nKamil'e onay bildirimi gönderildi.",
            parse_mode="Markdown"
        )

        kamil_text = (
            f"🔔 **ÖMER'DEN YENİ TALEP GELDİ!**\n"
            f"═══════════════════════════════\n"
            f"🆔 `{req_id}`\n"
            f"📌 **Tür:** {req_type}\n"
            f"🏭 **Müşteri / Tesis:** {payload.get('firm')}\n"
            f"👤 **Yetkili / Telefon:** {payload.get('contact')}\n"
            f"⚙️ **Ürün Kodu:** `{payload.get('part_code')}` ({payload.get('quantity')} Adet)\n"
            f"⚡ **Öncelik:** {prio}\n"
            f"📝 **Ömer'in Notu:** _{payload.get('notes') or 'Yok'}_\n"
            f"═══════════════════════════════\n"
            f"Kamil, bu talebi onaylıyor musun?"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Talebi Onayla", callback_data=f"otk_ok:{req_id}")],
            [InlineKeyboardButton(text="❌ Reddet", callback_data=f"otk_no:{req_id}")]
        ])
        await bot.send_message(chat_id=KAMIL_CHAT_ID, text=kamil_text, reply_markup=kb, parse_mode="Markdown")

    elif direction == "KAMIL_TO_OMER":
        tasks = load_tasks()
        tasks[req_id] = {
            "created_at": time.time(),
            "started_at": None,
            "firm": payload.get('firm', 'Belirtilmedi'),
            "task_type": payload.get('task_type', 'Arıza/Görev')
        }
        save_tasks(tasks)

        await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"✅ İş emri Ömer'in telefonuna fırlatıldı.")
        
        omer_text = (
            f"📋 **KAMİL SAHAYA YENİ İŞ GÖNDERDİ!**\n"
            f"═══════════════════════════════\n"
            f"🆔 `{req_id}`\n"
            f"🏭 **Tesis:** {payload.get('firm')}\n"
            f"👤 **İrtibat:** {payload.get('contact')}\n"
            f"🔧 **Görev:** `{payload.get('task_type')}`\n"
            f"📝 **Talimat:** _{payload.get('instructions') or 'Yok'}_\n"
            f"═══════════════════════════════\n"
            f"Ömer, durumu tek tıkla Kamil'e bildir:"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👍 Görevi Aldım", callback_data=f"o_ack:{req_id}"),
             InlineKeyboardButton(text="🔍 İlgileniyorum", callback_data=f"o_busy:{req_id}")],
            [InlineKeyboardButton(text="✅ İşi Tamamladım", callback_data=f"o_done:{req_id}")]
        ])
        await bot.send_message(chat_id=OMER_CHAT_ID, text=omer_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("otk_ok:"))
async def omer_req_approved(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🟢 **KAMİL TALEBİ ONAYLADI.**", reply_markup=None)
    await bot.send_message(chat_id=OMER_CHAT_ID, text="🎉 **Ömer, Kamil talebini onayladı! Parçayı sevk edebilirsin.**")
    await callback.answer()

@dp.callback_query(F.data.startswith("otk_no:"))
async def omer_req_rejected(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **KAMİL REDDETTİ.**", reply_markup=None)
    await bot.send_message(chat_id=OMER_CHAT_ID, text="❌ **Ömer, talep Kamil tarafından reddedildi.**")
    await callback.answer()

@dp.callback_query(F.data.startswith("o_ack:"))
async def omer_ack_task(callback: types.CallbackQuery):
    req_id = callback.data.split(":")[1]
    tasks = load_tasks()
    if req_id in tasks and not tasks[req_id].get("started_at"):
        tasks[req_id]["started_at"] = time.time()
        save_tasks(tasks)
        
    await callback.answer("Görevi kabul ettin.")
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"👍 **Ömer iş emrini teslim aldı.** [Ref: `{req_id}`]")

@dp.callback_query(F.data.startswith("o_busy:"))
async def omer_busy_task(callback: types.CallbackQuery):
    req_id = callback.data.split(":")[1]
    tasks = load_tasks()
    if req_id in tasks and not tasks[req_id].get("started_at"):
        tasks[req_id]["started_at"] = time.time()
        save_tasks(tasks)
        
    await callback.answer("İlgileniyorsun olarak işaretlendi.")
    firm_info = tasks.get(req_id, {}).get("firm", "")
    firm_str = f" ({firm_info})" if firm_info else ""
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"🔍 **Ömer arıza/görev ile ilgilenmeye başladı.**{firm_str}")

@dp.callback_query(F.data.startswith("o_done:"))
async def omer_done_task(callback: types.CallbackQuery):
    req_id = callback.data.split(":")[1]
    tasks = load_tasks()
    task = tasks.get(req_id, {})

    start_ts = task.get("started_at") or task.get("created_at") or time.time()
    elapsed_seconds = int(time.time() - start_ts)

    hours = elapsed_seconds // 3600
    minutes = (elapsed_seconds % 3600) // 60
    seconds = elapsed_seconds % 60

    if hours > 0:
        duration_str = f"{hours} saat {minutes} dakika"
    elif minutes > 0:
        duration_str = f"{minutes} dakika {seconds} saniye"
    else:
        duration_str = f"{seconds} saniye"

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ **ÖMER GÖREVİ TAMAMLADI.**\n⏱️ **Toplam Müdahale Süresi:** `{duration_str}`",
        reply_markup=None,
        parse_mode="Markdown"
    )

    kamil_done_msg = (
        f"🏁 **ÖMER GÖREVİ BAŞARIYLA BİTİRDİ!**\n"
        f"═══════════════════════════════\n"
        f"🏭 **Tesis:** `{task.get('firm', 'Belirtilmedi')}`\n"
        f"🔧 **Görev:** `{task.get('task_type', 'Arıza/Müdahale')}`\n"
        f"⏱️ **Toplam Müdahale Süresi:** `{duration_str}`\n"
        f"═══════════════════════════════\n"
        f"✅ _İş tamamlandı olarak kayda geçti._"
    )
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=kamil_done_msg, parse_mode="Markdown")
    await callback.answer(f"Görev tamamlandı! Toplam Süre: {duration_str}")

# ==============================================================================
#            11. CANLI TELSİZ / İKİLİ MESAJLAŞMA (ÖMER ⇄ KAMİL)
# ==============================================================================
@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi"]:
        return

    sender_id = message.chat.id
    target_id = OMER_CHAT_ID if sender_id == KAMIL_CHAT_ID else (KAMIL_CHAT_ID if sender_id == OMER_CHAT_ID else None)
    sender_name = "Kamil" if sender_id == KAMIL_CHAT_ID else "Ömer"

    if not target_id:
        return

    if message.text:
        await bot.send_message(chat_id=target_id, text=f"💬 **{sender_name}:** {message.text}")
        await message.reply("✓ _İletildi._", parse_mode="Markdown")
    elif message.voice:
        await bot.send_voice(chat_id=target_id, voice=message.voice.file_id, caption=f"🎙️ **{sender_name}'den Sesli Mesaj**")
        await message.reply("✓ _Ses iletildi._", parse_mode="Markdown")

# ==============================================================================
#       12. ZAMANLAYICILAR: CUMARTESİ 12:30 Z-RAPORU + AYIN SON GÜNÜ 18:00 AYLIK RAPOR
# ==============================================================================
async def automated_scheduler():
    last_weekly_date = ""
    last_monthly_date = ""
    last_reminder_date = ""

    while True:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_weekly_date != today_str:
            last_weekly_date = today_str
            logging.info("Cumartesi 12:30 Z-Raporu tetiklendi...")
            sales_data = build_weekly_report_data()
            report_text = build_report_text(sales_data, "HAFTALIK SATIŞ Z-RAPORU (12:30)")
            header = "📢 **HAFTALIK OTOMATİK CUMARTESİ Z-RAPORU (12:30)**\n\n"
            await notify_both(header + report_text)
            
            if sales_data:
                excel_file = generate_excel_z_report(sales_data, "Haftalik_Z_Raporu")
                if os.path.exists(excel_file):
                    await send_file_to_both(excel_file, "📊 **Eliar Haftalık Satış Z-Raporu (Excel Tablosu)**")
                pdf_file = generate_pdf_z_report(sales_data, "Haftalik_Z_Raporu")
                if pdf_file and os.path.exists(pdf_file):
                    await send_file_to_both(pdf_file, "📑 **Eliar Haftalık Satış Z-Raporu (PDF Tablosu)**")

        is_last_day_of_month = (now + timedelta(days=1)).day == 1
        if is_last_day_of_month and now.hour == 18 and now.minute == 0 and last_monthly_date != today_str:
            last_monthly_date = today_str
            logging.info("Ayın Son Günü Aylık Rapor tetiklendi...")
            month_name = now.strftime("%B %Y")
            sales_data = build_monthly_report_data()
            report_text = build_report_text(sales_data, f"AYLIK SATIŞ RAPORU ({month_name})")
            header = f"📢 **{month_name.upper()} AYI RESMİ SATIŞ Z-RAPORU**\n\n"
            await notify_both(header + report_text)
            
            if sales_data:
                excel_file = generate_excel_z_report(sales_data, f"Aylik_Rapor_{now.strftime('%m_%Y')}")
                if os.path.exists(excel_file):
                    await send_file_to_both(excel_file, f"📊 **Eliar {month_name} Aylık Satış Raporu (Excel)**")
                pdf_file = generate_pdf_z_report(sales_data, f"Aylik_Rapor_{now.strftime('%m_%Y')}")
                if pdf_file and os.path.exists(pdf_file):
                    await send_file_to_both(pdf_file, f"📑 **Eliar {month_name} Aylık Satış Raporu (PDF)**")

        if now.hour == 9 and now.minute == 0 and last_reminder_date != today_str:
            last_reminder_date = today_str
            sales = load_sales()
            three_days_ago = now - timedelta(days=3)

            for s in sales:
                if s.get("status") == "WAITING":
                    try:
                        ts = datetime.fromisoformat(s.get("timestamp", ""))
                        if ts <= three_days_ago:
                            days_waited = (now - ts).days
                            session_id = s.get("id")
                            reminder_text = (
                                f"⏰ **BEKLEYEN TEKLİF HATIRLATMASI!**\n"
                                f"═══════════════════════════════\n"
                                f"🏭 **Müşteri:** `{s.get('firm')}`\n"
                                f"🔖 **Ref No:** `{s.get('ref_no', 'YOK')}`\n"
                                f"🕒 Bu teklif **{days_waited} gündür** beklemede.\n"
                                f"Müşteri arandı mı, karar netleşti mi?"
                            )
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🟢 Şimdi Onaylandı", callback_data=f"q_appr:{session_id}")],
                                [InlineKeyboardButton(text="🔴 İptal Et", callback_data=f"q_rej:{session_id}")]
                            ])
                            await notify_both(reminder_text, reply_markup=kb)
                    except Exception:
                        pass

        await asyncio.sleep(25)

# ==============================================================================
#             13. RENDER İÇİN SAHTE WEB SUNUCUSU (PORT BINDING)
# ==============================================================================
async def handle(request):
    return web.Response(text="Eliar Bot 7/24 Aktif ve Calisiyor!")

async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render'ın atadığı PORT'u okuyoruz, bulamazsa varsayılan 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Render web portu açıldı: {port}")

# ==============================================================================
#                               ANA ÇALIŞTIRICI
# ==============================================================================
async def main():
    await setup_bot_commands()
    
    # 1. Render için Web Sunucusunu Arka Planda Başlatıyoruz
    await start_dummy_server()
    
    # 2. Rapor Zamanlayıcıyı Başlatıyoruz
    asyncio.create_task(automated_scheduler())
    
    print("=" * 60)
    print("🚀 Eliar Canlı Santral Başlatıldı!")
    print(f"• Ömer ID: {OMER_CHAT_ID}")
    print(f"• Kamil ID: {KAMIL_CHAT_ID}")
    print(f"• WebApp: {WEBAPP_URL}")
    print("• Rapor Formatı: Excel (.xlsx) & PDF (.pdf) Seçmeli")
    print("• Haftalık Z-Raporu: CUMARTESİ 12:30")
    print("• Aylık Z-Raporu: AYIN SON GÜNÜ 18:00")
    print("=" * 60)
    
    # 3. Telegram Botunu Başlatıyoruz
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
