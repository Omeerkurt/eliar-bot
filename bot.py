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
    for cid in set([OMER_CHAT_ID, KAMIL_CHAT_ID]):
        try:
            await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Mesaj iletilemedi: {e}")

async def send_file_to_both(file_path: str, caption: str):
    for cid in set([OMER_CHAT_ID, KAMIL_CHAT_ID]):
        try:
            await bot.send_document(chat_id=cid, document=FSInputFile(file_path), caption=caption)
        except Exception as e:
            logging.warning(f"Dosya iletilemedi: {e}")

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡ Eliar Mini Uygulama", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text="📦 Parça Listesi"), KeyboardButton(text="📊 Z-Raporu Al")],
            [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="🏢 Tesis Geçmişi")]
        ],
        resize_keyboard=True
    )

async def setup_bot_commands():
    commands = [
        BotCommand(command="start", description="Sistemi Başlat / Menü"),
        BotCommand(command="stok", description="Tüm Parça Listesi"),
        BotCommand(command="zraporu", description="Haftalık Z-Raporu (Excel/PDF)"),
        BotCommand(command="aylikrapor", description="Aylık Satış Raporu (Excel/PDF)"),
        BotCommand(command="rapor", description="Tarihli Rapor (/rapor 01.10.2026 28.10.2026)"),
        BotCommand(command="ref", description="Ref No ile Teklif Sorgula (/ref 46189ND)"),
        BotCommand(command="bekleyenler", description="Bekleyen Teklifleri İncele"),
        BotCommand(command="gecmis", description="Fabrika Parça Geçmişi (/gecmis Müşteri)"),
        BotCommand(command="sifirla", description="Tüm Verileri Kesin Olarak Sıfırla"),
        BotCommand(command="yardim", description="Nasıl Kullanılır?")
    ]
    await bot.set_my_commands(commands)

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
        f"└ `/rapor 01.10.2026 28.10.2026` ile iki tarih arası rapor çekin.\n\n"
        f"📄 **Teklif & Evrak İşleme:**\n"
        f"└ PDF veya Fotoğraf attığınızda yapay zeka okuyup karşı tarafa iletir.\n\n"
        f"🔎 **Hızlı Sorgulama:**\n"
        f"└ `/ref [No]` ➔ Teklif detaylarını getirir (Örn: `/ref 46189ND`)\n"
        f"└ `/gecmis [Müşteri]` ➔ Tesise verilen tüm parçaları listeler.\n\n"
        f"⚙️ **Sistem:**\n"
        f"└ `/sifirla` ➔ Tüm stok ve satış verilerini tamamen siler (0'lar).\n\n"
        f"═══════════════════════════════\n"
        f"💡 _Aşağıdaki menüden işlem seçebilirsiniz._"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(Command("sifirla"))
async def cmd_wipe_data(message: types.Message):
    try:
        if os.path.exists(STOCKS_FILE): os.remove(STOCKS_FILE)
        if os.path.exists(SALES_FILE): os.remove(SALES_FILE)
        if os.path.exists(TASKS_FILE): os.remove(TASKS_FILE)
    except Exception as e:
        logging.error(f"Dosya silme hatası: {e}")

    save_stocks([])
    save_sales([])
    save_tasks({})
    await message.answer("🚨 **SİSTEM KÖKTEN SIFIRLANDI!**\nTüm stoklar, satışlar ve geçmiş kayıtlar tamamen silindi. Sistem şu an 0 noktasındadır.", parse_mode="Markdown")

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Eliar Bot Komut Rehberi:**\n"
        "1. `/stok` ➔ Tüm parça listesi.\n"
        "2. `/rapor [Başlangıç] [Bitiş]` ➔ Tarih filtreli rapor.\n"
        "3. `/ref [RefNo]` ➔ Teklifi referans no ile bulur.\n"
        "4. `/gecmis [Müşteri]` ➔ O tesise geçmişte verilen parçalar.\n"
        "5. `/sifirla` ➔ Sistemi tamamen temizler.",
        parse_mode="Markdown"
    )

@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stock_list(message: types.Message):
    stocks = load_stocks()
    if not stocks:
        await message.answer("📦 **Stok listesi şu an tamamen boş (0).**", parse_mode="Markdown")
        return

    mekatronik = [s for s in stocks if s.get("cat") == "MEKATRONIK"]
    elektronik = [s for s in stocks if s.get("cat") == "ELEKTRONIK"]
    kontrol = [s for s in stocks if s.get("cat") == "KONTROL"]
    
    text = "📦 **GÜNCEL ELİAR DEPO STOK LİSTESİ**\n═══════════════════════════════\n\n"
    
    if mekatronik:
        text += "⚙️ **MEKATRONİK:**\n"
        for s in mekatronik:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if elektronik:
        text += "\n⚡ **ELEKTRONİK:**\n"
        for s in elektronik:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
    if kontrol:
        text += "\n🎛️ **KONTROLÖRLER:**\n"
        for s in kontrol:
            text += f"• `{s['code']}` — {s['name']}\n  └ Stok: **{s['qty']} ADT** | Konum: `{s['loc']}`\n"
        
    total_qty = sum(s.get("qty", 0) for s in stocks)
    text += f"\n═══════════════════════════════\n📊 Toplam Kalem: **{len(stocks)}** | Toplam Parça: **{total_qty} ADT**"
    await message.answer(text, parse_mode="Markdown")

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
        await message.answer("⚠️ Referans Numarasını yazın.\nÖrnek: `/ref 46189ND`", parse_mode="Markdown")
        return
    ref_no = parts[1].strip()
    quote = find_quote_by_ref(ref_no)
    if not quote:
        await message.answer(f"🔍 `{ref_no}` teklifi bulunamadı.", parse_mode="Markdown")
        return
    status_str = {"APPROVED": "🟢 ONAYLANDI", "WAITING": "🟡 BEKLİYOR", "REJECTED": "🔴 İPTAL"}.get(quote.get("status"), "Bilinmiyor")
    text = (f"🔖 **TEKLİF [Ref: {quote.get('ref_no')}]**\n🏭 **Müşteri:** `{quote.get('firm')}`\n📌 **Durum:** {status_str}\n🕒 **Tarih:** {quote.get('date')}\n📦 **PARÇALAR:**\n")
    for idx, item in enumerate(quote.get("items", []), 1):
        text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"
    await message.answer(text, parse_mode="Markdown")

def get_client_history_text(firm_query: str):
    sales = load_sales()
    query = firm_query.strip().lower()
    matched = [s for s in sales if query in s.get("firm", "").lower() and s.get("status"] == "APPROVED"]
    if not matched: return f"🔍 `{firm_query}` tesisi için geçmiş kayıt bulunamadı."
    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    text = f"🏢 **{matched[0].get('firm')} — PARÇA GEÇMİŞİ**\n═══════════════════════════════\n\n"
    for item in matched:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for sub_item in item.get("items", []):
            text += f"• 📅 `{item.get('date', '')}` ➔ **{sub_item.get('qty')}x** `{sub_item.get('code')}` ({sub_item.get('name')}){ref_str}\n"
    return text

@dp.message(Command("gecmis"))
async def cmd_history_query(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.answer("⚠️ Tesis adı belirtin. Örnek: `/gecmis TERRY`", parse_mode="Markdown")
    await message.answer(get_client_history_text(parts[1]), parse_mode="Markdown")

@dp.message(F.text == "🏢 Tesis Geçmişi")
async def btn_client_history(message: types.Message, state: FSMContext):
    await state.set_state(ClientHistoryState.waiting_client_name)
    await message.answer("🔍 Müşteri Adını yazın:\n(Örn: `TERRY` veya `MICBRO`)", parse_mode="Markdown")

@dp.message(ClientHistoryState.waiting_client_name)
async def process_client_history_input(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(get_client_history_text(message.text.strip()), parse_mode="Markdown")

def generate_excel_z_report(sales_data, title="Z_Raporu"):
    today_str = datetime.now().strftime("%d_%m_%Y")
    excel_filename = f"Eliar_{title}_{today_str}.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Satışlar"
        header_fill = PatternFill(start_color="161F30", end_color="161F30", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        headers = ["Sıra", "Tarih", "Ref No", "Müşteri / Fabrika", "Ürün Kodu", "Ürün Adı", "Adet", "Durum"]
        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        counter = 1
        for sale in sales_data:
            ref = str(sale.get("ref_no", "YOK"))
            firm = str(sale.get("firm", "Bilinmeyen"))
            date = str(sale.get("date", ""))
            for item in sale.get("items", []):
                ws.append([counter, date, ref, firm, item.get("code", ""), item.get("name", ""), item.get("qty", 1), "ONAYLANDI"])
                counter += 1
        col_widths = [8, 18, 14, 28, 16, 40, 10, 14]
        for idx, width in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width
        wb.save(excel_filename)
        return excel_filename
    except Exception:
        import csv
        csv_filename = f"Eliar_{title}_{today_str}.csv"
        with open(csv_filename, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Sira", "Tarih", "Ref No", "Musteri", "Urun Kodu", "Urun Adi", "Adet", "Durum"])
            cnt = 1
            for s in sales_data:
                for itm in s.get("items", []):
                    writer.writerow([cnt, s.get("date"), s.get("ref_no"), s.get("firm"), itm.get("code"), itm.get("name"), itm.get("qty"), "ONAYLANDI"])
                    cnt += 1
        return csv_filename

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

        doc = SimpleDocTemplate(pdf_filename, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'], fontName="Helvetica-Bold",
            fontSize=14, textColor=colors.HexColor('#161F30'), alignment=1, spaceAfter=4
        )
        sub_style = ParagraphStyle(
            'SubStyle', parent=styles['Normal'], fontName="Helvetica",
            fontSize=8, textColor=colors.HexColor('#64748B'), alignment=1, spaceAfter=12
        )

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
                    str(counter), date, ref, firm[:22],
                    tr_fix(item.get("code", "")), tr_fix(item.get("name", ""))[:28], str(q)
                ])
                counter += 1

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
            ('SPAN', (0, -1), (5, -1)),
            ('ALIGN', (0, -1), (0, -1), 'RIGHT'),
        ]))
        elements.append(table)
        doc.build(elements)
        return pdf_filename
    except Exception as e:
        logging.error(f"PDF oluşturma hatası: {e}")
        return None

def build_weekly_report_data():
    sales = load_sales()
    now = datetime.now()
    one_week_ago = now - timedelta(days=7)
    return [s for s in sales if s.get("status") == "APPROVED" and (datetime.fromisoformat(s.get("timestamp", now.isoformat())) >= one_week_ago)]

def build_monthly_report_data():
    sales = load_sales()
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    return [s for s in sales if s.get("status") == "APPROVED" and (datetime.fromisoformat(s.get("timestamp", now.isoformat())) >= start_of_month)]

def build_report_text(sales_data, report_name):
    if not sales_data: return f"📊 **{report_name}**\nℹ️ _Kayıt bulunamadı._"
    text = f"📊 **{report_name}**\n═══════════════════════════════\n"
    total_items = 0
    for idx, sale in enumerate(sales_data, 1):
        for sub in sale.get("items", []):
            total_items += int(sub.get("qty", 1))
            text += f"**{idx}.** `{sub.get('code')}` — **{sub.get('name')}** ({sub.get('qty')} Adet) | Tesis: {sale.get('firm')}\n"
    text += f"═══════════════════════════════\n📦 **Toplam Parça:** {total_items} Adet"
    return text

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
        return await message.answer("⚠️ Tarih formatı hatalı. (Gün.Ay.Yıl) olmalı.")

    sales = load_sales()
    filtered_sales = []
    for s in sales:
        if s.get("status") == "APPROVED":
            try:
                s_date = datetime.fromisoformat(s.get("timestamp", ""))
                if start_date <= s_date <= end_date:
                    filtered_sales.append(s)
            except: pass

    if not filtered_sales:
        return await message.answer(f"🔍 `{start_str}` ile `{end_str}` arasında onaylı işlem yok.", parse_mode="Markdown")

    await message.answer(f"⏳ `{start_str}` - `{end_str}` arası raporunuz hazırlanıyor...", parse_mode="Markdown")
    
    title = f"Ozel_Rapor_{start_str}_{end_str}"
    excel_file = generate_excel_z_report(filtered_sales, title)
    pdf_file = generate_pdf_z_report(filtered_sales, title)
    
    if os.path.exists(excel_file):
        await message.answer_document(FSInputFile(excel_file))
    if pdf_file and os.path.exists(pdf_file):
        await message.answer_document(FSInputFile(pdf_file))

@dp.message(Command("zraporu"))
@dp.message(F.text == "📊 Z-Raporu Al")
async def trigger_z_report_manual(message: types.Message):
    sales_data = build_weekly_report_data()
    report_text = build_report_text(sales_data, "HAFTALIK SATIŞ Z-RAPORU")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Excel", callback_data="dl_rep:excel:weekly"), InlineKeyboardButton(text="📑 PDF", callback_data="dl_rep:pdf:weekly")],
        [InlineKeyboardButton(text="📦 İkisini de İndir", callback_data="dl_rep:both:weekly")]
    ])
    await message.answer(report_text, reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("dl_rep:"))
async def handle_download_report_choice(callback: types.CallbackQuery):
    _, fmt, scope = callback.data.split(":")
    sales_data = build_weekly_report_data() if scope == "weekly" else build_monthly_report_data()
    title = "Haftalik_Rapor" if scope == "weekly" else "Aylik_Rapor"
    if not sales_data: return await callback.answer("Bu dönem için satış yok.", show_alert=True)
    await callback.answer("Hazırlanıyor...")
    if fmt in ["excel", "both"]:
        await callback.message.answer_document(FSInputFile(generate_excel_z_report(sales_data, title)))
    if fmt in ["pdf", "both"]:
        await callback.message.answer_document(FSInputFile(generate_pdf_z_report(sales_data, title)))

def parse_quote_media(file_path: str, is_pdf: bool = False, original_filename: str = ""):
    firm, ref_no, items = None, None, []
    clean_fn = re.sub(r"(fiyat|teklif|teklifi|\.pdf|\.jpg|\.png|temp_doc_\w+)", "", original_filename, flags=re.IGNORECASE).strip()
    if len(clean_fn) >= 3: firm = clean_fn

    if GEMINI_API_KEY and GEMINI_API_KEY != "AIzaSyAuUg0a1ew5V4aF1E-FTsdVinsMpXckOgQ":
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            mime_type = "application/pdf" if is_pdf else "image/jpeg"
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            prompt = (
                "Sen bir endüstriyel teklif analiz uzmanısın. Ek'teki teklifi incele. Saf JSON formatında dön:\n"
                "{\"firm\": \"Müşteri Adı\", \"ref_no\": \"Ref No\", \"items\": [{\"code\": \"Kod\", \"name\": \"Ad\", \"qty\": 1}]}\n"
            )
            response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt, genai.types.Part.from_bytes(data=file_bytes, mime_type=mime_type)])
            res = json.loads(response.text.replace("```json", "").replace("```", "").strip())
            if res.get("items") and res.get("firm"): return res
        except Exception: pass

    if not firm: firm = clean_fn if len(clean_fn) >= 3 else "BILINMEYEN TESIS"
    if not items: items = [{"code": "BILINMIYOR", "name": "Tespit Edilemedi", "qty": 1}]
    return {"firm": firm, "ref_no": ref_no or "BELİRTİLMEDİ", "items": items}

@dp.message(F.photo | F.document)
async def handle_quote_media(message: types.Message):
    if message.text in ["📦 Parça Listesi", "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "🏢 Tesis Geçmişi"]: return
    is_pdf = False
    doc_name = message.document.file_name if message.document else ""
    if doc_name.lower().endswith(".pdf"): is_pdf = True
    elif not message.photo: return

    uploader_name = "Ömer" if message.chat.id == OMER_CHAT_ID else ("Kamil" if message.chat.id == KAMIL_CHAT_ID else message.from_user.first_name)
    status_msg = await message.reply("🔍 _Taranıyor..._", parse_mode="Markdown")
    
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    file = await bot.get_file(file_id)
    ext = ".pdf" if is_pdf else ".jpg"
    local_filename = f"temp_doc_{message.message_id}{ext}"
    await bot.download_file(file.file_path, local_filename)

    data = parse_quote_media(local_filename, is_pdf, doc_name)
    if os.path.exists(local_filename): os.remove(local_filename)

    session_id = f"Q-{int(time.time()*1000)}"
    sales = load_sales()
    sales.append({
        "id": session_id, "firm": data.get("firm"), "ref_no": data.get("ref_no"),
        "items": data.get("items"), "status": "WAITING", "uploaded_by": uploader_name,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
    })
    save_sales(sales)

    result_text = f"**TEKLİF ALGILANDI!**\n🏭 **Müşteri:** `{data.get('firm')}`\n🔖 **Ref No:** `{data.get('ref_no')}`\n📦 **PARÇALAR:**\n"
    for idx, item in enumerate(data.get("items", []), 1):
        result_text += f"{idx}. `{item.get('code')}` — **{item.get('name')}** ({item.get('qty')} Adet)\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Müşteri Onayladı (Satış)", callback_data=f"q_appr:{session_id}")],
        [InlineKeyboardButton(text="🔴 Müşteri Kabul Etmedi", callback_data=f"q_rej:{session_id}")]
    ])
    await status_msg.delete()
    await notify_both(result_text, reply_markup=kb)

@dp.callback_query(F.data.startswith("q_appr:"))
async def quote_approved(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    sales, stocks = load_sales(), load_stocks()
    for s in sales:
        if s.get("id") == session_id:
            s["status"], s["date"] = "APPROVED", datetime.now().strftime("%d.%m.%Y %H:%M")
            for item in s.get("items", []):
                for st in stocks:
                    if st.get("code") == item.get("code"): st["qty"] = max(0, st["qty"] - int(item.get("qty", 1)))
            break
    save_sales(sales)
    save_stocks(stocks)
    await callback.message.edit_text(callback.message.text + "\n\n🟢 **ONAYLANDI!**", reply_markup=None)

@dp.callback_query(F.data.startswith("q_rej:"))
async def quote_rejected(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    sales = load_sales()
    for s in sales:
        if s.get("id") == session_id: s["status"] = "REJECTED"
    save_sales(sales)
    await callback.message.edit_text(callback.message.text + "\n\n🔴 **İPTAL EDİLDİ.**", reply_markup=None)

@dp.message(Command("bekleyenler"))
@dp.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(message: types.Message):
    waiting_sales = [s for s in load_sales() if s.get("status") == "WAITING"]
    if not waiting_sales: return await message.answer("⏳ Bekleyen teklif yok.")
    for s in waiting_sales:
        text = f"🏭 **Tesis:** `{s.get('firm')}`\n"
        for itm in s.get("items", []): text += f" • `{itm.get('code')}` ({itm.get('qty')} Adet)\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🟢 Onayla", callback_data=f"q_appr:{s['id']}"), InlineKeyboardButton(text="🔴 İptal", callback_data=f"q_rej:{s['id']}")]])
        await message.answer(text, reply_markup=kb)

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    try: payload = json.loads(message.web_app_data.data)
    except: return
    if payload.get("direction") == "STOCK_CHANGE" and payload.get("action") == "DECREASE":
        sales = load_sales()
        sales.append({
            "id": f"REF-{message.message_id}", "firm": payload.get("destination", "Belirtilmedi"),
            "ref_no": "MANUEL-ÇIKIŞ", "items": [{"code": payload.get("code"), "name": payload.get("name"), "qty": payload.get("delta", 1)}],
            "status": "APPROVED", "date": datetime.now().strftime("%d.%m.%Y %H:%M"), "timestamp": datetime.now().isoformat()
        })
        save_sales(sales)
        await notify_both(f"📤 **PARÇA ÇIKIŞI!**\n📍 Yer: `{payload.get('destination')}`\n⚙️ Parça: `{payload.get('code')}` (-{payload.get('delta', 1)} Adet)")

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

async def main():
    await setup_bot_commands()
    await start_dummy_server()
    print("🚀 Eliar Bot Devrede!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
