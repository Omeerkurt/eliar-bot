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

# STOKLAR SIFIRLANDI
DEFAULT_STOCKS = []

class ClientHistoryState(StatesGroup):
    waiting_client_name = State()

class ReportDateState(StatesGroup):
    waiting_for_date = State()

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
    for cid in set([OMER_CHAT_ID, KAMIL_CHAT_ID]):
        try:
            await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Mesaj {cid} adresine iletilemedi: {e}")

async def send_file_to_both(file_path: str, caption: str):
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
            [KeyboardButton(text="📅 Tarihli Rapor"), KeyboardButton(text="⏳ Bekleyen Teklifler")],
            [KeyboardButton(text="🏢 Tesis Geçmişi")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Sistemi Başlat / Menü"),
        BotCommand(command="stok", description="Tüm Parça Listesi"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu (Excel / PDF)"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu (Excel / PDF)"),
        BotCommand(command="tarihrapor", description="Belirli Bir Tarihin Raporu"),
        BotCommand(command="ref", description="Ref No ile Teklif Sorgula"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifleri İncele"),
        BotCommand(command="gecmis", description="Fabrika Parça Geçmişi"),
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
    await message.answer(
        f"👋 **Selam {name}! Eliar Depo & İş Santrali Devrede.**\n\n"
        f"• **Rapor Çıktısı Seçimi:** Z-Raporu alırken ister **Excel**, ister **PDF** indirebilirsiniz.\n"
        f"• **Tarihli Rapor:** İhtiyacınız olan spesifik bir günün dökümünü alabilirsiniz.\n"
        f"• **İş Emri & Kronometre:** Tam süre takibi yapılır.\n"
        f"• **PDF / Fotoğraf At:** Orijinal dosya yapay zeka tarafından okunur.\n"
        f"• `/ref [No]`: Referans numarasıyla arayın.\n"
        f"• `🏢 Tesis Geçmişi`: Müşteriye daha önce hangi parçaları verdik döker.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Eliar Bot Komut Rehberi:**\n\n"
        "1. `/stok` ➔ Fiyatsız tüm parça ve raf listesi.\n"
        "2. `/zraporu` ➔ Haftalık Z-raporu.\n"
        "3. `/aylikrapor` ➔ Aylık satış raporu.\n"
        "4. `/tarihrapor` ➔ Sadece sizin seçeceğiniz tarihin raporunu verir.\n"
        "5. `/ref [RefNo]` ➔ Teklifi referans numarasıyla bulur.\n"
        "6. `/gecmis [Müşteri]` ➔ Tesise verilen tüm parçaları listeler.\n"
        "7. `/bekleyenler` ➔ Onay bekleyen teklifleri gösterir.",
        parse_mode="Markdown"
    )

# ==============================================================================
#                 2. PARÇA LİSTESİ 
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
    diger = [s for s in stocks if s.get("cat") not in ["KONTROL", "ELEKTRONIK", "MEKATRONIK"]]
    
    text = "📦 **GÜNCEL ELİAR DEPO STOK LİSTESİ**\n═══════════════════════════════\n\n"
    if kontrol:
        text += "🎛️ **KONTROLÖRLER:**\n"
        for s in kontrol: text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if elektronik:
        text += "\n⚡ **ELEKTRONİK:**\n"
        for s in elektronik: text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if mekatronik:
        text += "\n⚙️ **MEKATRONİK:**\n"
        for s in mekatronik: text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if diger:
        text += "\n📌 **DİĞER:**\n"
        for s in diger: text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s.get('loc', '')}`\n"
        
    total_qty = sum(s.get("qty", 0) for s in stocks)
    text += f"\n═══════════════════════════════\n📊 Toplam Kalem: **{len(stocks)}** | Toplam Parça: **{total_qty} ADT**"
    await message.answer(text, parse_mode="Markdown")

# ==============================================================================
#        3. REF NO & TESİS GEÇMİŞİ
# ==============================================================================
def find_quote_by_ref(ref_query: str):
    sales = load_sales()
    query = ref_query.strip().upper()
    for s in sales:
        clean_ref = str(s.get("ref_no", "")).strip().upper()
        if clean_ref == query or (len(query) >= 4 and query in clean_ref): return s
    return None

@dp.message(Command("ref"))
async def cmd_ref_search(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Lütfen Referans Numarasını yazın.\nÖrnek: `/ref 46189ND`", parse_mode="Markdown")
        return
    
    quote = find_quote_by_ref(parts[1].strip())
    if not quote:
        await message.answer(f"🔍 Referans numarasına ait teklif bulunamadı.", parse_mode="Markdown")
        return

    status_str = {"APPROVED": "🟢 ONAYLANDI", "WAITING": "🟡 BEKLİYOR", "REJECTED": "🔴 KABUL EDİLMEDİ"}.get(quote.get("status"), "Bilinmiyor")
    text = (
        f"🔖 **TEKLİF DETAYI [Ref: {quote.get('ref_no')}]**\n═══════════════════════════════\n"
        f"🏭 **Müşteri:** `{quote.get('firm')}`\n📌 **Durum:** {status_str}\n🕒 **Tarih:** {quote.get('date')}\n"
        f"👤 **İşleyen:** {quote.get('uploaded_by', 'Ömer')}\n═══════════════════════════════\n📦 **PARÇALAR:**\n"
    )
    for idx, item in enumerate(quote.get("items", []), 1):
        text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"

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
    if not matched: return f"🔍 `{firm_query}` tesisi için geçmişte kayıtlı parça çıkışı bulunamadı."

    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    text = f"🏢 **{matched[0].get('firm')} — PARÇA GEÇMİŞİ**\n═══════════════════════════════\n\n"
    for item in matched:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for sub_item in item.get("items", []):
            text += f"• 📅 `{item.get('date', 'Bilinmiyor')}` ➔ **{sub_item.get('qty')}x** `{sub_item.get('code')}` ({sub_item.get('name')}){ref_str}\n"
            
    text += f"\n═══════════════════════════════\n✅ Toplam Kayıt: **{len(matched)} Sevkiyat / Servis Hareketi**"
    return text

@dp.message(Command("gecmis"))
async def cmd_history_query(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Lütfen tesis adını belirtin.", parse_mode="Markdown")
        return
    await message.answer(get_client_history_text(parts[1]), parse_mode="Markdown")

@dp.message(F.text == "🏢 Tesis Geçmişi")
async def btn_client_history(message: types.Message, state: FSMContext):
    await state.set_state(ClientHistoryState.waiting_client_name)
    await message.answer("🔍 Geçmişini görmek istediğiniz **Fabrika / Müşteri Adını** yazın:", parse_mode="Markdown")

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="Markdown")

# ==============================================================================
#            4. TARİHE GÖRE RAPOR ALMA
# ==============================================================================
@dp.message(Command("tarihrapor"))
@dp.message(F.text == "📅 Tarihli Rapor")
async def ask_for_report_date(message: types.Message, state: FSMContext):
    await state.set_state(ReportDateState.waiting_for_date)
    await message.answer(
        "📅 Hangi tarihin raporunu almak istiyorsunuz?\n"
        "Lütfen **GG.AA.YYYY** formatında yazın:\n\n"
        "👉 Örnek: `29.10.2026`", 
        parse_mode="Markdown"
    )

@dp.message(ReportDateState.waiting_for_date)
async def process_report_date(message: types.Message, state: FSMContext):
    target_date = message.text.strip()
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", target_date):
        await message.answer("⚠️ Hatalı format. Lütfen `GG.AA.YYYY` formatında girin (Örn: 29.10.2026):")
        return
    await state.clear()
    
    sales = load_sales()
    filtered_sales = [s for s in sales if s.get("status") == "APPROVED" and s.get("date", "").startswith(target_date)]
            
    if not filtered_sales:
        await message.answer(f"ℹ️ `{target_date}` tarihinde onaylanmış herhangi bir parça satışı bulunmuyor.", parse_mode="Markdown")
        return

    await message.answer("Raporlarınız hazırlanıyor...")
    title = f"Rapor_{target_date.replace('.','_')}"
    
    excel_file = generate_excel_z_report(filtered_sales, title)
    if os.path.exists(excel_file):
        await message.answer_document(document=FSInputFile(excel_file), caption=f"📊 **{target_date} Excel Raporu**", parse_mode="Markdown")
        
    pdf_file = generate_pdf_z_report(filtered_sales, title)
    if pdf_file and os.path.exists(pdf_file):
        await message.answer_document(document=FSInputFile(pdf_file), caption=f"📑 **{target_date} PDF Raporu**", parse_mode="Markdown")

# ==============================================================================
#            5. EXCEL VE PDF ÜRETİCİLERİ
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
        border_thin = Border(left=Side(style='thin', color='DDDDDD'), right=Side(style='thin', color='DDDDDD'), top=Side(style='thin', color='DDDDDD'), bottom=Side(style='thin', color='DDDDDD'))

        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet", "Durum"]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx, counter = 2, 1
        for sale in sales_data:
            for item in sale.get("items", []):
                ws.append([counter, sale.get("date", ""), str(sale.get("ref_no", "YOK")), str(sale.get("firm", "Bilinmeyen")), item.get("code", ""), item.get("name", ""), item.get("qty", 1), "ONAYLANDI"])
                for col_num in range(1, len(headers) + 1):
                    c = ws.cell(row=row_idx, column=col_num)
                    c.border = border_thin
                    if col_num in [1, 2, 3, 7, 8]: c.alignment = Alignment(horizontal="center")
                row_idx += 1; counter += 1

        for idx, width in enumerate([8, 18, 14, 28, 16, 40, 10, 14], 1): ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width
        wb.save(excel_filename)
        return excel_filename
    except Exception as e:
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

        font_name = "Helvetica" # Varsayılan
        # Bot dosyasıyla aynı klasöre arial.ttf atılırsa otomatik tanır, harfler bozulmaz.
        for fpath in ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(fpath):
                try:
                    pdfmetrics.registerFont(TTFont('TurkishFont', fpath))
                    font_name = 'TurkishFont'
                    break
                except Exception:
                    pass

        doc = SimpleDocTemplate(pdf_filename, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName=font_name, fontSize=14, textColor=colors.HexColor('#161F30'), alignment=1, spaceAfter=4)
        sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName=font_name, fontSize=8, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=12)

        # PDF BAŞLIĞI DEĞİŞTİRİLDİ
        elements.append(Paragraph("ELİPS TEKSTİL ELİAR PARÇA SATIŞ RAPORU", title_style))
        elements.append(Paragraph(f"Oluşturulma Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}", sub_style))

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
                data.append([str(counter), date, ref, firm[:22], str(item.get("code", "")), str(item.get("name", ""))[:28], str(q)])
                counter += 1

        data.append(["TOPLAM", "", "", "", "", "", str(total_qty)])

        table = Table(data, colWidths=[30, 65, 60, 120, 75, 160, 45], repeatRows=1)
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
            # TOPLAM SATIRI İÇİN HÜCRE BİRLEŞTİRME EKLENDİ (Yazı Sığmama Sorunu Çözüldü)
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
#         6. HAFTALIK & AYLIK RAPOR MOTORLARI
# ==============================================================================
def build_weekly_report_data():
    sales = load_sales()
    one_week_ago = datetime.now() - timedelta(days=7)
    return [s for s in sales if s.get("status") == "APPROVED" and (datetime.fromisoformat(s.get("timestamp", datetime.now().isoformat())) >= one_week_ago)]

def build_monthly_report_data():
    sales = load_sales()
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    return [s for s in sales if s.get("status") == "APPROVED" and (datetime.fromisoformat(s.get("timestamp", now.isoformat())) >= start_of_month)]

def build_report_text(sales_data, report_name="HAFTALIK SATIŞ Z-RAPORU"):
    if not sales_data: return f"📊 **ELİAR {report_name}**\n═══════════════════════════════\nℹ️ _Kayıt bulunamadı._"

    text = f"📊 **ELİAR {report_name}**\n📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\n\n"
    total_items, counter = 0, 1

    for sale in sales_data:
        ref_text = f" `[Ref: {sale.get('ref_no')}]`" if sale.get('ref_no') and sale.get('ref_no') != 'YOK' else ""
        for sub_i in sale.get("items", []):
            q = int(sub_i.get("qty", 1))
            total_items += q
            text += f"**{counter}.** `{sub_i.get('code')}` — **{sub_i.get('name')}**\n   └ 📦 {q} Adet | 🏭 {sale.get('firm')}{ref_text} | 🕒 {sale.get('date')}\n\n"
            counter += 1

    text += f"───────────────────────────────\n📦 **Toplam Parça:** {total_items} Adet\n═══════════════════════════════\n📂 _Aşağıdan indirebilirsiniz:_"
    return text

@dp.message(Command("zraporu"))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    sales_data = build_weekly_report_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel İndir", callback_data="dl_rep:excel:weekly"), InlineKeyboardButton(text="📑 PDF İndir", callback_data="dl_rep:pdf:weekly")],
        [InlineKeyboardButton(text="📦 İkisini de İndir", callback_data="dl_rep:both:weekly")]
    ])
    await message.answer(build_report_text(sales_data, "HAFTALIK SATIŞ Z-RAPORU"), reply_markup=kb, parse_mode="Markdown")

@dp.message(Command("aylikrapor"))
async def trigger_monthly_report_manual(message: types.Message):
    sales_data = build_monthly_report_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel İndir", callback_data="dl_rep:excel:monthly"), InlineKeyboardButton(text="📑 PDF İndir", callback_data="dl_rep:pdf:monthly")],
        [InlineKeyboardButton(text="📦 İkisini de İndir", callback_data="dl_rep:both:monthly")]
    ])
    await message.answer(build_report_text(sales_data, f"AYLIK SATIŞ RAPORU"), reply_markup=kb, parse_mode="Markdown")

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
        if os.path.exists(excel_file): await callback.message.answer_document(FSInputFile(excel_file))

    if fmt in ["pdf", "both"]:
        pdf_file = generate_pdf_z_report(sales_data, title)
        if pdf_file and os.path.exists(pdf_file): await callback.message.answer_document(FSInputFile(pdf_file))

# ==============================================================================
#    7. TEKLİF PDF & FOTOĞRAF AYRIŞTIRICI
# ==============================================================================
def parse_quote_media(file_path: str, is_pdf: bool = False, original_filename: str = ""):
    firm, ref_no, items = None, None, []
    clean_fn = re.sub(r"(fiyat|teklif|teklifi|\.pdf|\.jpg|\.png|temp_doc_\w+)", "", original_filename, flags=re.IGNORECASE).strip()
    if len(clean_fn) >= 3: firm = clean_fn

    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            with open(file_path, "rb") as f: file_bytes = f.read()
            prompt = "Sen endüstriyel teklif analiz uzmanısın. Ek'teki formu incele. Kesinlikle saf JSON formatında şu yapıda dön: {\"firm\": \"Müşteri Adı\", \"ref_no\": \"Ref No\", \"items\": [{\"code\": \"Ürün Kodu\", \"name\": \"Ürün Adı\", \"qty\": 1}]}. Fiyat ekleme."
            response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, genai.types.Part.from_bytes(data=file_bytes, mime_type="application/pdf" if is_pdf else "image/jpeg")])
            res = json.loads(response.text.replace("```json", "").replace("```", "").strip())
            if res.get("items") and res.get("firm"): return res
        except Exception:
            pass

    if not firm or "İlgili Kişi" in str(firm): firm = clean_fn if len(clean_fn) >= 3 else "BİLİNMEYEN TESİS"
    if not items: items = [{"code": "BILINMEYEN", "name": "Otomatik Algılanamadı (Manuel Giriniz)", "qty": 1}]
    return {"firm": firm, "ref_no": ref_no or "BELİRTİLMEDİ", "items": items}

@dp.message(F.photo | F.document)
async def handle_quote_media(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi", "📅 Tarihli Rapor"]: return
    is_pdf, doc_name = False, (message.document.file_name or "" if message.document else "")
    if message.document:
        if doc_name.lower().endswith(".pdf"): is_pdf = True
        elif not doc_name.lower().endswith((".jpg", ".jpeg", ".png")): return

    uploader_name = "Ömer" if message.chat.id == OMER_CHAT_ID else ("Kamil" if message.chat.id == KAMIL_CHAT_ID else message.from_user.first_name)
    target_chat_id = KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else OMER_CHAT_ID
    status_msg = await message.reply("🔍 _Eliar dosyası taranıyor ve aktarılıyor..._", parse_mode="Markdown")

    try:
        if is_pdf: await bot.send_document(chat_id=target_chat_id, document=message.document.file_id, caption=f"📑 **{uploader_name} yeni teklif paylaştı!**")
        elif message.photo: await bot.send_photo(chat_id=target_chat_id, photo=message.photo[-1].file_id, caption=f"📷 **{uploader_name} yeni görsel paylaştı!**")
        
        file_id = message.document.file_id if message.document else message.photo[-1].file_id
        file = await bot.get_file(file_id)
        local_filename = f"temp_doc_{message.message_id}_{int(time.time())}{'.pdf' if is_pdf else '.jpg'}"
        await bot.download_file(file.file_path, local_filename)

        data = parse_quote_media(local_filename, is_pdf=is_pdf, original_filename=doc_name)
        if os.path.exists(local_filename): os.remove(local_filename)

        session_id = f"Q-{int(time.time()*1000)}"
        sales = load_sales()
        sales.append({
            "id": session_id, "firm": data.get("firm"), "ref_no": data.get("ref_no"),
            "items": data.get("items"), "status": "WAITING", "uploaded_by": uploader_name,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)

        result_text = (f"**ELİAR TEKLİF FORMU ALGILANDI!**\n👤 _Paylaşan: {uploader_name}_\n═══════════════════════════════\n"
                       f"🏭 **Müşteri:** `{data.get('firm')}`\n🔖 **Ref No:** `{data.get('ref_no')}`\n═══════════════════════════════\n📦 **PARÇALAR:**\n")
        for idx, item in enumerate(data.get("items", []), 1): result_text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Müşteri Onayladı", callback_data=f"q_appr:{session_id}")],
            [InlineKeyboardButton(text="🟡 Müşteri Bekliyor", callback_data=f"q_wait:{session_id}")],
            [InlineKeyboardButton(text="🔴 Kabul Etmedi", callback_data=f"q_rej:{session_id}")]
        ])

        try: await status_msg.delete()
        except: pass
        await notify_both(result_text, reply_markup=kb)
    except Exception as e:
        await message.reply(f"⚠️ Hata: `{e}`", parse_mode="Markdown")

# ==============================================================================
#      8. TEKLİF BUTONLARI & DURUM
# ==============================================================================
@dp.callback_query(F.data.startswith("q_wait:"))
async def quote_waiting(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    for s in sales:
        if s.get("id") == session_id: s["status"], s["decided_by"] = "WAITING", operator
    save_sales(sales)

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Onaylandı", callback_data=f"q_appr:{session_id}")], [InlineKeyboardButton(text="🔴 Red", callback_data=f"q_rej:{session_id}")]])
    await callback.message.edit_text(callback.message.text + f"\n\n🟡 **DURUM: BEKLİYOR**\n_İşlem: {operator}_", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales, stocks = load_sales(), load_stocks()
    
    for s in sales:
        if s.get("id") == session_id:
            if s.get("status") == "APPROVED":
                await callback.answer("Bu teklif zaten onaylı!", show_alert=True)
                return
            s["status"], s["date"], s["decided_by"] = "APPROVED", datetime.now().strftime("%d.%m.%Y %H:%M"), operator
            for item in s.get("items", []):
                for st in stocks:
                    if st.get("code") == item.get("code"): st["qty"] = max(0, st["qty"] - int(item.get("qty", 1)))
            break
            
    save_sales(sales)
    save_stocks(stocks)
    await callback.message.edit_text(callback.message.text + f"\n\n🟢 **ONAYLANDI! ({operator})**", reply_markup=None, parse_mode="Markdown")
    await notify_both(f"🟢 **TEKLİF ONAYLANDI! ({operator})**\n✅ Stoktan düşüldü ve deftere işlendi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    operator = "Ömer" if callback.from_user.id == OMER_CHAT_ID else ("Kamil" if callback.from_user.id == KAMIL_CHAT_ID else callback.from_user.first_name)
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    for s in sales:
        if s.get("id") == session_id: s["status"], s["decided_by"] = "REJECTED", operator
    save_sales(sales)
    await callback.message.edit_text(callback.message.text + f"\n\n🔴 **KABUL EDİLMEDİ ({operator})**", reply_markup=None, parse_mode="Markdown")
    await notify_both(f"🔴 **TEKLİF İPTAL EDİLDİ! ({operator})**")
    await callback.answer()

@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    sales = load_sales()
    waiting_sales = [s for s in sales if s.get("status") == "WAITING"]
    if not waiting_sales:
        await message.answer("⏳ **Bekleyen açık bir teklif bulunmuyor.**", parse_mode="Markdown")
        return
    for s in waiting_sales:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Onaylandı", callback_data=f"q_appr:{s.get('id')}")], [InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{s.get('id')}")]])
        text = f"🏭 **Tesis:** `{s.get('firm')}`\n🕒 **Tarih:** {s.get('date')}\n📦 **Kalemler:**\n"
        for itm in s.get("items", []): text += f" • `{itm.get('code')}` — **{itm.get('name')}**\n"
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# ==============================================================================
#             10. WEBAPP & GÖREV KONTROL
# ==============================================================================
@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try: payload = json.loads(message.web_app_data.data)
    except: return
    direction, req_id = payload.get("direction"), f"REF-{message.message_id}"
    operator = "Ömer" if message.chat.id == OMER_CHAT_ID else ("Kamil" if message.chat.id == KAMIL_CHAT_ID else message.from_user.first_name)

    if direction == "STOCK_CHANGE" and payload.get("action") == "DECREASE":
        sales = load_sales()
        sales.append({"id": req_id, "firm": payload.get("destination") or "Belirtilmedi", "ref_no": "MANUEL-ÇIKIŞ", "items": [{"code": payload.get("code"), "name": payload.get("name"), "qty": payload.get("delta", 1)}], "status": "APPROVED", "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()})
        save_sales(sales)
        await notify_both(f"📤 **PARÇA ÇIKIŞI YAPILDI!**\n📍 `{payload.get('destination')}`\n⚙️ `{payload.get('code')}` ({payload.get('name')})\n📉 Düşülen: -{payload.get('delta', 1)} Adet\n👷‍♂️ Yapan: {operator}")

    elif direction == "OMER_TO_KAMIL":
        await bot.send_message(chat_id=OMER_CHAT_ID, text=f"✅ **Talebin Alındı!**", parse_mode="Markdown")
        kamil_text = f"🔔 **ÖMER'DEN TALEP GELDİ!**\n🏭 {payload.get('firm')}\n⚙️ `{payload.get('part_code')}`\n📝 Not: _{payload.get('notes')}_"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Onayla", callback_data=f"otk_ok:{req_id}")], [InlineKeyboardButton(text="❌ Reddet", callback_data=f"otk_no:{req_id}")]])
        await bot.send_message(chat_id=KAMIL_CHAT_ID, text=kamil_text, reply_markup=kb, parse_mode="Markdown")

    elif direction == "KAMIL_TO_OMER":
        tasks = load_tasks()
        tasks[req_id] = {"created_at": time.time(), "started_at": None, "firm": payload.get('firm'), "task_type": payload.get('task_type')}
        save_tasks(tasks)
        await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"✅ İş emri fırlatıldı.")
        omer_text = f"📋 **KAMİL YENİ İŞ GÖNDERDİ!**\n🏭 Tesis: {payload.get('firm')}\n🔧 Görev: `{payload.get('task_type')}`\n📝 Talimat: _{payload.get('instructions')}_"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👍 Aldım", callback_data=f"o_ack:{req_id}"), InlineKeyboardButton(text="🔍 İlgileniyorum", callback_data=f"o_busy:{req_id}")], [InlineKeyboardButton(text="✅ Tamamladım", callback_data=f"o_done:{req_id}")]])
        await bot.send_message(chat_id=OMER_CHAT_ID, text=omer_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("otk_ok:"))
async def omer_req_approved(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🟢 **ONAYLANDI.**", reply_markup=None)
    await bot.send_message(chat_id=OMER_CHAT_ID, text="🎉 **Kamil talebini onayladı!**")

@dp.callback_query(F.data.startswith("otk_no:"))
async def omer_req_rejected(callback: types.CallbackQuery):
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **REDDEDİLDİ.**", reply_markup=None)
    await bot.send_message(chat_id=OMER_CHAT_ID, text="❌ **Talep reddedildi.**")

@dp.callback_query(F.data.startswith("o_ack:"))
async def omer_ack_task(callback: types.CallbackQuery):
    await callback.answer("Görevi kabul ettin.")
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"👍 **Ömer işi teslim aldı.**")

@dp.callback_query(F.data.startswith("o_busy:"))
async def omer_busy_task(callback: types.CallbackQuery):
    req_id = callback.data.split(":")[1]
    tasks = load_tasks()
    if req_id in tasks and not tasks[req_id].get("started_at"):
        tasks[req_id]["started_at"] = time.time()
        save_tasks(tasks)
    await callback.answer("İlgileniliyor.")
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"🔍 **Ömer iş ile ilgilenmeye başladı.**")

@dp.callback_query(F.data.startswith("o_done:"))
async def omer_done_task(callback: types.CallbackQuery):
    req_id = callback.data.split(":")[1]
    task = load_tasks().get(req_id, {})
    elapsed = int(time.time() - (task.get("started_at") or task.get("created_at") or time.time()))
    duration = f"{elapsed // 3600} saat {(elapsed % 3600) // 60} dakika" if elapsed >= 3600 else f"{elapsed // 60} dakika"
    await callback.message.edit_text(callback.message.text + f"\n\n✅ **TAMAMLANDI.**\n⏱️ Süre: `{duration}`", reply_markup=None)
    await bot.send_message(chat_id=KAMIL_CHAT_ID, text=f"🏁 **ÖMER GÖREVİ BİTİRDİ!**\n🏭 {task.get('firm')}\n⏱️ Süre: `{duration}`")

@dp.message(~F.text.startswith("/"))
async def chat_bridge(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi", "📅 Tarihli Rapor"]: return
    target_id = OMER_CHAT_ID if message.chat.id == KAMIL_CHAT_ID else (KAMIL_CHAT_ID if message.chat.id == OMER_CHAT_ID else None)
    if not target_id: return
    sender = "Kamil" if message.chat.id == KAMIL_CHAT_ID else "Ömer"
    if message.text:
        await bot.send_message(chat_id=target_id, text=f"💬 **{sender}:** {message.text}")
        await message.reply("✓ _İletildi._", parse_mode="Markdown")
    elif message.voice:
        await bot.send_voice(chat_id=target_id, voice=message.voice.file_id, caption=f"🎙️ **{sender}**")
        await message.reply("✓ _İletildi._", parse_mode="Markdown")

async def automated_scheduler():
    last_weekly, last_monthly = "", ""
    while True:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_weekly != today_str:
            last_weekly = today_str
            sales = build_weekly_report_data()
            await notify_both("📢 **HAFTALIK Z-RAPORU**\n\n" + build_report_text(sales, "HAFTALIK SATIŞ"))
            if sales:
                ex = generate_excel_z_report(sales, "Haftalik"); pdf = generate_pdf_z_report(sales, "Haftalik")
                if os.path.exists(ex): await send_file_to_both(ex, "📊 Excel")
                if pdf and os.path.exists(pdf): await send_file_to_both(pdf, "📑 PDF")
        
        if (now + timedelta(days=1)).day == 1 and now.hour == 18 and now.minute == 0 and last_monthly != today_str:
            last_monthly = today_str
            sales = build_monthly_report_data()
            await notify_both(f"📢 **AYLIK Z-RAPORU**\n\n" + build_report_text(sales, "AYLIK SATIŞ"))
            if sales:
                ex = generate_excel_z_report(sales, "Aylik"); pdf = generate_pdf_z_report(sales, "Aylik")
                if os.path.exists(ex): await send_file_to_both(ex, "📊 Excel")
                if pdf and os.path.exists(pdf): await send_file_to_both(pdf, "📑 PDF")
        await asyncio.sleep(25)

async def handle(request): return web.Response(text="Bot Aktif!")
async def start_dummy_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080))).start()

async def main():
    await setup_bot_commands()
    await start_dummy_server()
    asyncio.create_task(automated_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
