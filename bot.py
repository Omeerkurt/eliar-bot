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

load_stocks = lambda: load_data(STOCKS_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d)
load_sales = lambda: load_data(SALES_FILE, [])
save_sales = lambda d: save_data(SALES_FILE, d)
load_tasks = lambda: load_data(TASKS_FILE, {})
save_tasks = lambda d: save_data(TASKS_FILE, d)

async def notify_both(text: str, reply_markup=None):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try:
            await bot.send_message(chat_id=cid, text=text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception as e:
            logging.warning(f"Mesaj iletilemedi ({cid}): {e}")

async def send_file_to_both(file_path: str, caption: str):
    for cid in {OMER_CHAT_ID, KAMIL_CHAT_ID}:
        try:
            await bot.send_document(chat_id=cid, document=FSInputFile(file_path), caption=caption)
        except Exception as e:
            logging.warning(f"Dosya iletilemedi ({cid}): {e}")

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
        BotCommand(command="stok", description="Parça Listesi"),
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
        f"👋 **Selam {name}! Eliar Elips Depo & İş Santrali Aktif.**\n\n"
        f"• Parça listesi Mekatronik ➔ Elektronik ➔ Kontrolör sırasında listelenir.\n"
        f"• Z-Raporu ve Tarihli Raporları Excel ve PDF formatında indirebilirsiniz.\n"
        f"• Aşağıdaki menüden veya butonlardan işlem yapabilirsiniz.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(Command("yardim"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🛠 **Komutlar:**\n"
        "• `/stok` : Parça listesi\n"
        "• `/zraporu` : Haftalık Z-raporu\n"
        "• `/aylikrapor` : Aylık satış raporu\n"
        "• `/tarihraporu` : Belirtilen tarihler arası rapor\n"
        "• `/ref [kod]` : Teklif arama\n"
        "• `/gecmis [firma]` : Tesis parça geçmişi",
        parse_mode="Markdown"
    )

@dp.message(Command("stok"))
@dp.message(F.text == "📦 Parça Listesi")
async def show_stock_list(message: types.Message):
    stocks = load_stocks()
    if not stocks:
        await message.answer("📦 **Depoda henüz kayıtlı parça bulunmuyor.**", parse_mode="Markdown")
        return

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
        f"🕒 Tarih: {quote.get('date')}\n"
        f"👤 Ekleyen: {quote.get('uploaded_by', 'Ömer')}\n\n"
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

    matched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    text = f"🏢 **{matched[0].get('firm')} — PARÇA GEÇMİŞİ**\n═══════════════════════════════\n\n"
    for item in matched:
        ref_str = f" [Ref: {item.get('ref_no')}]" if item.get('ref_no') and item.get('ref_no') != 'YOK' else ""
        for itm in item.get("items", []):
            text += f"• 📅 `{item.get('date', '')}` ➔ **{itm.get('qty')}x** `{itm.get('code')}` ({itm.get('name')}){ref_str}\n"

    text += f"\n═══════════════════════════════\n✅ Toplam: **{len(matched)} Sevkiyat / Hareket**"
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
    await message.answer("🔍 Geçmişini aradığınız **Fabrika Adını** yazın:", parse_mode="Markdown")

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

        row = 2
        cnt = 1
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
            d = datetime.fromisoformat(ts) if ts else datetime.strptime(s.get("date", "").split()[0], "%d.%m.%Y")
            if start_dt <= d <= end_dt:
                res.append(s)
        except Exception:
            res.append(s)
    return res

def build_report_text(sales_data, report_name="SATIŞ Z-RAPORU"):
    now = datetime.now()
    if not sales_data:
        return f"📊 **ELİPS TEKSTİL ELİAR {report_name}**\n📅 Tarih: {now.strftime('%d.%m.%Y %H:%M')}\n═══════════════════════════════\nℹ️ Onaylanan satış kaydı bulunmamaktadır."

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
        await callback.message.answer("✍️ Format: `GG.AA.YYYY - GG.AA.YYYY` (Örn: `01.10.2026 - 29.10.2026`)", parse_mode="Markdown")
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
        await message.answer("⚠️ Format hatalı! Örnek: `01.10.2026 - 29.10.2026`", parse_mode="Markdown")

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
        await callback.answer("Onaylı satış kaydı yok.", show_alert=True)
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
    await notify_both(f"🟢 **SATIŞ ONAYLANDI!**\n🏭 `{sale.get('firm')}` — Ref: `{sale.get('ref_no')}`\nStoktan düşüldü ve Z-Raporuna işlendi.")
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
