import json, logging, asyncio, os, re, time, html, difflib
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup, WebAppInfo, BotCommand, BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 1. ÖZBEKİSTAN SAAT DİLİMİ
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
#                     CANLI YAPILANDIRMA & TOKEN
# ==============================================================================
# BOTFATHER'DAN REVOKE EDİP ALDIĞIN YENİ TOKEN'I BURAYA YAPIŞTIR:
BOT_TOKEN = "9212674639:AAE3H17yvghBQmbbq86_kLwI-L5787KzwXQ"

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
    waiting_item_query = State()
    waiting_qty = State()
    confirm_more = State()

class StockAddState(StatesGroup):
    waiting_query = State()
    waiting_qty = State()

# ----------------- KATALOG KOORDİNAT HARİTASI (RD96) -----------------
CATALOG_GRID_MAP = {
    "91661": (2, 1), "40642": (2, 2), "40645": (2, 3), "40643": (2, 4), "40644": (2, 5), "90802": (2, 6),
    "41370": (3, 3), "41381": (3, 5), "91514": (3, 6), "91410": (4, 1), "91411": (4, 2), "41436": (4, 3),
    "41435": (4, 4), "96469": (4, 5), "60002": (4, 6), "90338": (5, 1), "91128": (5, 2), "91516": (5, 4),
    "41538": (5, 5), "41407": (5, 6), "41420": (6, 1), "93041": (6, 2), "93035": (6, 3), "60020": (6, 4),
    "91517": (7, 1), "41430": (7, 2), "41408": (7, 3), "41415": (7, 4), "41419": (7, 5), "41414": (7, 6),
    "41425": (8, 1), "41427": (8, 2), "41426": (8, 3), "93039": (8, 4), "93040": (8, 5), "41413": (9, 2),
    "41418": (9, 3), "41411": (9, 4), "41428": (9, 5), "41429": (9, 6), "93043": (10, 1), "93042": (10, 2),
    "93037": (10, 3), "93036": (10, 4), "60044": (11, 1), "41434": (11, 2), "90946": (11, 3), "41432": (11, 4),
    "41409": (11, 5), "41424": (11, 6), "41433": (12, 1), "41416": (12, 2), "41417": (12, 3), "41533": (12, 4),
    "96541": (12, 5), "96540": (12, 6), "90951": (13, 2), "41384": (13, 5), "41383": (13, 6), "90310": (14, 1),
    "90952": (14, 2), "90332": (14, 3), "90328": (14, 4), "90949": (14, 5), "90947": (14, 6), "90321": (15, 3),
    "16073": (15, 4), "90490": (15, 5), "91238": (15, 6), "90333": (16, 1), "90948": (16, 2), "91407": (16, 3),
    "93008": (16, 4), "90345": (16, 5), "90325": (16, 6), "90320": (17, 1), "90950": (17, 2), "60003": (17, 3),
    "96112": (17, 4), "90827": (17, 5), "50155": (17, 6), "96467": (18, 1), "91603": (18, 2), "91035": (18, 3),
    "90547": (18, 4), "20031": (18, 5), "90475": (18, 6), "50160": (19, 1), "91285": (19, 2), "50606": (19, 3),
    "91472": (19, 4), "50247": (19, 5), "50249": (19, 6), "15401": (20, 3), "41439": (20, 4), "91633": (20, 5),
    "91448": (20, 6), "42595": (21, 1), "90861": (21, 3), "90817": (21, 6), "96683": (22, 1), "96097": (22, 2),
    "91598": (22, 4), "91037": (22, 5), "40082": (22, 6), "91386": (23, 3), "91488": (23, 4), "90567": (23, 5),
    "90965": (23, 6), "40647": (24, 1), "90715": (24, 2), "50161": (24, 3), "50162": (24, 4), "90828": (24, 5),
    "90834": (24, 6), "96468": (25, 1), "91463": (25, 3), "91604": (25, 4), "90548": (25, 5), "91036": (25, 6),
    "90832": (26, 4), "40634": (26, 6), "96412": (27, 1), "90878": (27, 2), "90881": (27, 3), "90880": (27, 4),
    "90879": (27, 5), "91284": (28, 3), "14574": (28, 4), "14541": (28, 6), "91332": (29, 1), "50219": (29, 2),
    "54626": (29, 3), "41441": (29, 5), "91447": (29, 6), "50057": (30, 1), "54612": (30, 2), "50098": (30, 3),
    "50018": (30, 4), "91594": (30, 5), "91590": (31, 3), "15005": (31, 4), "50549": (31, 5), "40085": (31, 6),
    "91451": (32, 1), "50023": (32, 2), "50273": (32, 3), "50021": (32, 4), "41442": (32, 5), "41404": (32, 6),
    "96517": (33, 3), "50257": (33, 4), "96501": (33, 5), "90766": (33, 6), "16016": (34, 1), "16039": (34, 2),
    "16034": (34, 3), "41403": (34, 4), "90767": (34, 5), "91071": (34, 6), "90762": (35, 1), "90840": (35, 2),
    "41400": (35, 3), "41401": (35, 4), "41300": (35, 5), "41402": (35, 6), "91277": (36, 1), "54516": (36, 2),
    "90768": (36, 3), "90769": (36, 4), "90782": (36, 5), "16032": (36, 6), "16041": (37, 3), "16035": (37, 4),
    "50260": (37, 5), "90759": (37, 6), "50138": (38, 2), "91086": (38, 3), "91045": (38, 4), "90770": (38, 5),
    "16043": (38, 6), "16030": (39, 1), "90765": (39, 4), "11906": (39, 6), "12302": (40, 1), "41444": (40, 2),
    "91303": (40, 3), "50263": (40, 4), "91044": (40, 5), "54510": (41, 3), "90761": (41, 4), "50262": (41, 6),
    "41399": (42, 5), "50259": (42, 6), "50258": (43, 6), "50261": (44, 6), "91269": (45, 6), "91270": (46, 3),
    "50278": (46, 4), "50293": (46, 5), "90725": (46, 6), "50040": (47, 2), "41396": (47, 3), "41398": (47, 5),
    "54630": (47, 6), "50270": (48, 1), "50287": (48, 2), "91066": (48, 3), "91064": (48, 4), "41457": (48, 5),
    "50238": (48, 6), "50156": (49, 1), "91043": (49, 2), "50269": (49, 3), "50289": (50, 6), "50239": (51, 4),
    "50291": (52, 1), "90781": (52, 5), "41407P": (53, 1), "96404": (53, 2), "41406": (53, 3), "41405": (53, 4),
    "90484": (53, 5), "91490": (53, 6), "91489": (54, 1), "90930": (54, 5), "91495": (54, 6), "54661": (55, 3),
    "54662": (55, 4), "41437": (55, 5), "90568": (55, 6), "50014": (56, 1), "91782": (56, 2), "91271": (56, 3),
    "91268": (56, 4), "90793": (56, 5), "90324": (56, 6), "16044": (57, 1), "14847": (57, 2), "41290": (57, 3),
    "41287": (57, 4), "41288": (57, 5), "41289": (57, 6), "54629": (58, 1), "54628": (58, 2), "54627": (58, 3),
    "50024": (58, 5), "50025": (58, 6), "91586": (59, 3), "50027": (59, 4), "92038": (59, 5), "54620": (59, 6),
    "14577": (60, 1), "14317": (60, 2), "96449": (60, 3), "91950": (60, 4), "96219": (60, 6), "91453": (61, 1),
    "50008": (61, 2), "50010": (61, 3), "50046": (61, 4), "50054": (62, 3), "15005": (63, 3)
}

# ==============================================================================
#      KUSURSUZ MİLİMETRİK GÖRSEL KIRPICI (SAYFAYI BÜTÜN ATMAZ, KUTUYU KESER)
# ==============================================================================
def crop_slot_from_page(page, slot: int) -> bytes:
    pw, ph = page.rect.width, page.rect.height
    col = 0 if slot in [1, 3, 5] else 1
    row = 0 if slot in [1, 2] else (1 if slot in [3, 4] else 2)
    x0 = 8 if col == 0 else (pw / 2.0 + 2)
    x1 = (pw / 2.0 - 2) if col == 0 else (pw - 8)
    row_bounds = [(25, 285), (288, 550), (550, 815)]
    y0, y1 = row_bounds[row]
    try:
        import fitz
        clip_rect = fitz.Rect(max(0, x0), max(0, y0), min(pw, x1), min(ph, y1))
        pix = page.get_pixmap(clip=clip_rect, dpi=200)
        return pix.tobytes("png")
    except Exception as e:
        logging.error(f"Kırpma hatası: {e}")
        return None

def extract_part_image_from_pdf(code: str, name: str = "") -> bytes:
    pdf_path = None
    for fn in ["Katalog.pdf", "katalog.pdf", "rd96.pdf", "RD96.pdf", "CATALOG.PDF"]:
        if os.path.exists(fn): pdf_path = fn; break
    if not pdf_path: return None

    try:
        import fitz
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()

        # 1. Koordinat Haritasından Doğrudan Slot Kırpma (Jilet gibi tek kutuyu keser)
        if code_str in CATALOG_GRID_MAP:
            page_no, slot = CATALOG_GRID_MAP[code_str]
            p_idx = page_no - 1
            if p_idx < len(doc):
                return crop_slot_from_page(doc[p_idx], slot)

        # 2. Koordinatta yoksa metin arayarak koordinat kırpma
        for p_idx, page in enumerate(doc):
            rects = page.search_for(code_str)
            if rects:
                pw, ph = page.rect.width, page.rect.height
                r = rects[0]
                col = 0 if ((r.x0 + r.x1) / 2.0) < (pw / 2.0) else 1
                x0 = 8 if col == 0 else (pw / 2.0 + 2)
                x1 = (pw / 2.0 - 2) if col == 0 else (pw - 8)
                clip_rect = fitz.Rect(x0, max(10, r.y0 - 32), x1, min(ph - 10, r.y0 + 265))
                return page.get_pixmap(clip=clip_rect, dpi=200).tobytes("png")

        return None
    except Exception as e:
        logging.error(f"Görsel çıkarma hatası: {e}")
        return None

# ==============================================================================
#            YAZIM HATASI TOLERANSLI AKILLI PARÇA ARAMA MOTORU
# ==============================================================================
def normalize_tr(text: str) -> str:
    if not text: return ""
    m = {'ı':'i','İ':'i','I':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = str(text).lower()
    for k, v in m.items(): res = res.replace(k, v)
    # Yaygın yazım hatalarını düzelt (diayfram -> diyafram)
    res = res.replace("diayfram", "diyafram").replace("diafram", "diyafram")
    return res

def calculate_similarity(query: str, part: dict) -> float:
    q_norm = normalize_tr(query.strip())
    name_norm = normalize_tr(part.get("name", ""))
    code_norm = normalize_tr(part.get("code", ""))

    if q_norm == code_norm: return 1.0
    if q_norm in code_norm: return 0.95
    if q_norm in name_norm: return 0.88

    q_words = q_norm.split()
    name_words = name_norm.split()
    word_scores = [max([difflib.SequenceMatcher(None, qw, nw).ratio() for nw in name_words] or [0]) for qw in q_words]
    avg_word = sum(word_scores) / len(word_scores) if word_scores else 0.0

    return max(avg_word, difflib.SequenceMatcher(None, q_norm, name_norm).ratio())

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = [(p, calculate_similarity(query, p)) for p in stocks if calculate_similarity(query, p) > 0.30]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

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

load_stocks = lambda: load_data(STOCKS_FILE, [])
load_sales = lambda: load_data(SALES_FILE, [])
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d) if not TEST_MODE else None
save_sales = lambda d: save_data(SALES_FILE, d) if not TEST_MODE else None
save_quotes = lambda d: save_data(QUOTES_FILE, d)

async def notify_both(text: str, reply_markup=None, is_test=False):
    global TEST_MODE
    recipients = {OMER_CHAT_ID} if (TEST_MODE or is_test) else {OMER_CHAT_ID, KAMIL_CHAT_ID}
    if is_test or TEST_MODE:
        text += "\n\n🧪 <i>[TEST MODU: Kamil'e bildirim gitmedi]</i>"
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
        BotCommand(command="start", description="Ana Menü"),
        BotCommand(command="stok", description="Depo Envanteri"),
        BotCommand(command="stokekle", description="Stok Ekle / Yeni Tanımla"),
        BotCommand(command="stoksil", description="Parça Sil (Sadece Ömer)"),
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
#            SADE VE NET KARŞILAMA EKRANI (/start)
# ==============================================================================
@dp.message(CommandStart(), StateFilter("*"))
@dp.message(Command("start"), StateFilter("*"))
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.clear()
    user_id = msg.chat.id
    name = "Ömer" if user_id == OMER_CHAT_ID else ("Kamil" if user_id == KAMIL_CHAT_ID else "Yetkili")
    
    stocks = load_stocks()
    in_stock = len([s for s in stocks if safe_stock_qty(s.get("qty", 0)) > 0])
    
    welcome_text = (
        f"🏢 <b>ELİPS TEKSTİL OTOMASYON</b>\n"
        f"═══════════════════════════════\n"
        f"Selam <b>{name}</b>, sistem aktif.\n\n"
        f"📊 <b>Canlı Depo Durumu:</b>\n"
        f"• Tanımlı Parça: <b>{len(stocks)} Kalem</b>\n"
        f"• Depoda Mevcut: <b>{in_stock} Çeşit</b>\n"
        f"• Ekran Servis Takibi: <b>Aktif</b>\n\n"
        f"💡 <i>Aşağıdaki <b>'Eliar Mini App'</b> butonuna basarak depoyu açabilir veya menüden işlem seçebilirsin.</i>"
    )
    await msg.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

# ==============================================================================
#      TEKLİF SİHİRBAZI (SEÇENEK SUNAN AKILLI MOTOR + RESMİ KIRPAN SİSTEM)
# ==============================================================================
@dp.message(Command("teklif", ignore_mention=True))
@dp.message(F.text == "📝 Eliar'dan Teklif Al")
async def start_quote(msg: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteState.waiting_firm)
    await msg.answer("🏢 <b>Müşteri / Fabrika Adı:</b> (Örn: TERRY JAR)", parse_mode="HTML")

@dp.message(QuoteState.waiting_firm, ~F.text.startswith("/"))
async def quote_firm(msg: types.Message, state: FSMContext):
    await state.update_data(firm=msg.text.strip().upper())
    await state.set_state(QuoteState.waiting_item_query)
    await msg.answer("🔍 <b>Parça kodu veya adını yazın:</b>\n(Örn: <code>90567</code> veya <code>diyafram</code>)", parse_mode="HTML")

def render_search_page(matches, page_idx, query):
    page_size = 5
    total_pages = (len(matches) + page_size - 1) // page_size
    page_idx = max(0, min(page_idx, total_pages - 1))
    current_items = matches[page_idx * page_size : (page_idx + 1) * page_size]

    buttons = []
    for p, _ in current_items:
        buttons.append([InlineKeyboardButton(text=f"👉 [{p.get('code')}] {p.get('name', '')[:25]}", callback_data=f"qbsel:{p.get('code')}")])

    nav_row = []
    if page_idx > 0: nav_row.append(InlineKeyboardButton(text="⬅️ Önceki", callback_data=f"qbpage:{page_idx-1}"))
    if page_idx < total_pages - 1: nav_row.append(InlineKeyboardButton(text="Sonraki ➡️", callback_data=f"qbpage:{page_idx+1}"))
    if nav_row: buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=f"➕ Listede Yok, Bu İsimle Ekle: '{query[:16]}'", callback_data="qb_add_custom")])
    buttons.append([InlineKeyboardButton(text="🔍 Tekrar Ara", callback_data="qb_retry")])

    text = f"🔍 <b>'{html.escape(query)}' Arama Sonuçları:</b> (Sayfa: {page_idx + 1}/{total_pages})\nLütfen teklife eklenecek parçayı seçin:"
    return text, InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(QuoteState.waiting_item_query, ~F.text.startswith("/"))
async def quote_item_search(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    await state.update_data(search_query=query, custom_query=query)
    matches = find_best_matches(query)

    if not matches:
        kb_custom = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"➕ Bu İsimle Teklife Ekle", callback_data="qb_add_custom")],
            [InlineKeyboardButton(text="🔍 Tekrar Ara", callback_data="qb_retry")]
        ])
        await msg.answer(f"⚠️ <code>{html.escape(query)}</code> stokta veya katalogda bulunamadı.\nSerbest kalem olarak eklensin mi?", reply_markup=kb_custom, parse_mode="HTML")
        return

    # SADECE VE SADECE tam kod eşleşirse direkt seç
    top_part, score = matches[0]
    if query.lower() == str(top_part.get('code', '')).lower():
        await state.update_data(sel_part=top_part)
        await state.set_state(QuoteState.waiting_qty)

        img_bytes = extract_part_image_from_pdf(top_part.get("code", ""), top_part.get("name", ""))
        if img_bytes:
            photo = BufferedInputFile(img_bytes, filename=f"{top_part.get('code')}.png")
            await msg.answer_photo(photo, caption=f"📸 <b>Katalog Çizimi:</b> <code>[{top_part.get('code')}]</code> — {html.escape(top_part.get('name', ''))}", parse_mode="HTML")

        t_qty = safe_stock_qty(top_part.get('qty', 0))
        stock_text = f"Depo: {t_qty} ADT" if t_qty > 0 else "Stokta Yok (0 ADT)"
        tag = " 🆕 [YENİ]" if top_part.get("is_new") else ""
        await msg.answer(f"🎯 <b>Seçilen:</b> <code>[{top_part.get('code')}]</code> {html.escape(top_part.get('name', ''))}{tag}\n📦 <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")
        return

    # Kelime aramalarında (örn: "diyafram" / "diayfram") ASLA kafana göre parça seçme, listeyi sun!
    await state.update_data(search_matches=matches)
    text, kb = render_search_page(matches, 0, query)
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("qbpage:"))
async def on_qb_page(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    page_idx = int(cb.data.split(":")[1])
    data = await state.get_data()
    text, kb = render_search_page(data.get("search_matches", []), page_idx, data.get("search_query", ""))
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "qb_retry")
async def on_qb_retry(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(QuoteState.waiting_item_query)
    await cb.message.edit_text("🔍 Lütfen parça kodunu veya adını tekrar yazın:")

@dp.callback_query(F.data.startswith("qbsel:"))
async def on_qb_part_select(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if not part:
        await cb.answer("Parça bulunamadı.", show_alert=True)
        return

    await state.update_data(sel_part=part)
    await state.set_state(QuoteState.waiting_qty)

    img_bytes = extract_part_image_from_pdf(part.get("code", ""), part.get("name", ""))
    if img_bytes:
        photo = BufferedInputFile(img_bytes, filename=f"{part.get('code')}.png")
        await cb.message.answer_photo(photo, caption=f"📸 <b>Katalog Çizimi:</b> <code>[{part.get('code')}]</code> — {html.escape(part.get('name', ''))}", parse_mode="HTML")

    p_qty = safe_stock_qty(part.get('qty', 0))
    stock_text = f"Depo: {p_qty} ADT" if p_qty > 0 else "Stokta Yok (0 ADT)"
    await cb.message.answer(f"🎯 <b>Seçilen:</b> <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}\n📦 <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")

@dp.callback_query(F.data == "qb_add_custom")
async def on_qb_custom(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    q = (await state.get_data()).get("custom_query", "Özel Parça")
    await state.update_data(sel_part={"code": "KODSUZ", "name": q, "qty": 0})
    await state.set_state(QuoteState.waiting_qty)
    await cb.message.answer(f"🎯 <b>Seçilen:</b> {html.escape(q)} <i>(Katalog Dışı)</i>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")

# --- ADET ALICI: 0 / İPTAL MANTIĞI EKSİKSİZ KORUNDU ---
@dp.message(QuoteState.waiting_qty, ~F.text.startswith("/"))
async def quote_process_qty(msg: types.Message, state: FSMContext):
    text = msg.text.strip().lower()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Başka Parça Ekle", callback_data="q_more")],
        [InlineKeyboardButton(text="🏁 Teklifi Bitir ve Metni Al", callback_data="q_done")]
    ])

    if text in {"0", "iptal", "vazgeç", "vazgec", "geç", "gec", "atla"}:
        await state.set_state(QuoteState.confirm_more)
        await msg.answer("ℹ️ Bu parça teklif sepetine eklenmedi (atlandı).\nDevam etmek için seçim yapın:", reply_markup=kb, parse_mode="HTML")
        return

    try:
        qty = parse_qty_safe(msg.text)
    except Exception:
        await msg.answer("⚠️ Lütfen sayı girin (Vazgeçmek için <b>0</b> veya <b>iptal</b> yazabilirsiniz):", parse_mode="HTML")
        return

    data = await state.get_data()
    p = data.get("sel_part", {})
    items = data.get("quote_items", [])
    items.append({"code": p.get("code", "KODSUZ"), "name": p.get("name", "Parça"), "qty": qty})
    await state.update_data(quote_items=items)

    await state.set_state(QuoteState.confirm_more)
    await msg.answer(f"✅ <b>{qty} Adet</b> <code>[{p.get('code', 'KODSUZ')}]</code> eklendi!\nNe yapmak istersin?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "q_more")
async def on_q_more(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(QuoteState.waiting_item_query)
    await cb.message.edit_text("🔍 Yeni parçanın kodunu veya adını yazın:")

@dp.callback_query(F.data == "q_done")
async def on_q_done(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    firm, items = data.get("firm", "MÜŞTERİ"), data.get("quote_items", [])
    if not items:
        await cb.message.edit_text("⚠️ Teklifte hiç parça yok.")
        await state.clear()
        return

    fmt = f"Merhaba Nilay Hanım\n\n{firm} için aşağıdaki listedeki parçalar için fiyat teklifi verebilir misiniz?\n\n"
    for itm in items:
        prefix = f"{itm['code']} - " if itm.get('code') != "KODSUZ" else ""
        fmt += f"• {prefix}{itm['name']} - {itm['qty']} Adet\n"
    fmt += "\nİyi çalışmalar."

    quotes = load_quotes()
    quotes.append({"id": f"TK-{int(time.time())}", "firm": firm, "date": get_now_uz().strftime("%d.%m.%Y %H:%M"), "status": "PENDING", "items": items})
    save_quotes(quotes)

    text = f"📋 <b>KOPYALAMAYA HAZIR ELİAR TEKLİF METNİ:</b>\n═══════════════════════════════\n\n<code>{html.escape(fmt)}</code>\n\n═══════════════════════════════\n💡 <i>Metne tıklayarak tek dokunuşla kopyalayabilirsin.</i>"
    await cb.message.edit_text(text, parse_mode="HTML")
    await notify_both(f"📥 <b>YENİ TEKLİF TALEBİ:</b> {firm} ({len(items)} kalem)")
    await state.clear()

# ==============================================================================
#      STOK EKLEME (/stokekle)
# ==============================================================================
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
        new_p = {"code": q.upper() if len(q) <= 12 and " " not in q else "KODSUZ", "name": q, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
        await state.update_data(target_part=new_p)
        await state.set_state(StockAddState.waiting_qty)
        await msg.answer(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> <code>{html.escape(q)}</code>\n➕ Depoya kaç adet eklenecek?", parse_mode="HTML")
        return

    top, _ = matches[0]
    if q.lower() == str(top.get('code', '')).lower():
        await state.update_data(target_part=top)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(top.get("code", ""))
        if img: await msg.answer_photo(BufferedInputFile(img, filename=f"{top.get('code')}.png"), caption=f"📸 <code>[{top.get('code')}]</code>", parse_mode="HTML")
        await msg.answer(f"🎯 <code>[{top.get('code')}]</code> {html.escape(top.get('name', ''))}\n📦 Mevcut: <b>{safe_stock_qty(top.get('qty', 0))} ADT</b>\n\n➕ Kaç adet eklenecek?", parse_mode="HTML")
        return

    btns = [[InlineKeyboardButton(text=f"👉 [{p.get('code')}] {p.get('name', '')[:25]}", callback_data=f"sel_s:{p.get('code')}")] for p, _ in matches[:5]]
    btns.append([InlineKeyboardButton(text=f"➕ Yeni Olarak Ekle: '{q[:15]}'", callback_data="add_unlisted")])
    await msg.answer("🔍 Eşleşen parçalar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@dp.callback_query(F.data == "add_unlisted")
async def on_add_unlisted(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    q = (await state.get_data()).get("raw_q", "Özel Parça").strip()
    new_p = {"code": q.upper() if len(q) <= 12 and " " not in q else "KODSUZ", "name": q, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
    await state.update_data(target_part=new_p)
    await state.set_state(StockAddState.waiting_qty)
    await cb.message.edit_text(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> {html.escape(q)}\n➕ Kaç adet eklenecek?")

@dp.callback_query(F.data.startswith("sel_s:"))
async def on_sel_s(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if part:
        await state.update_data(target_part=part)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(part.get("code", ""))
        if img: await cb.message.answer_photo(BufferedInputFile(img, filename=f"{part.get('code')}.png"), caption=f"📸 <code>[{part.get('code')}]</code>", parse_mode="HTML")
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

# ==============================================================================
#      SADECE ÖMER'E ÖZEL SİLME MOTORU (/stoksil)
# ==============================================================================
@dp.message(Command("stoksil", ignore_mention=True))
async def cmd_stock_delete(msg: types.Message):
    if msg.chat.id != OMER_CHAT_ID:
        await msg.answer("🔒 <b>Yetkisiz İşlem:</b> Depodan parça silme yetkisi yalnızca Ömer'e aittir.", parse_mode="HTML")
        return

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
    await msg.answer(f"⚠️ <code>[{target.get('code')}]</code> {html.escape(target.get('name', ''))}\nNasıl silmek istersin?", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("del_p:"))
async def on_del_p(cb: types.CallbackQuery):
    await cb.answer()
    if cb.message.chat.id != OMER_CHAT_ID:
        await cb.message.edit_text("🔒 Bu işlem sadece yöneticiye açıktır.")
        return

    _, code, mode = cb.data.split(":")
    stocks = load_stocks()
    target = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower()), None)
    if not target: await cb.message.edit_text("⚠️ Parça bulunamadı."); return

    stocks = [s for s in stocks if str(s.get("code", "")).lower() != code.lower()]
    save_stocks(stocks)

    if mode == "silent":
        await cb.message.edit_text(f"🔕 <code>[{code}]</code> parçası <b>kimseye bildirim gitmeden</b> sessizce silindi.", parse_mode="HTML")
    else:
        await notify_both(f"🗑️ <b>DEPO PARÇASI SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(target.get('name', ''))}\n👷‍♂️ Silen: <b>Ömer</b>")
        await cb.message.edit_text(f"🗑️ <code>[{code}]</code> silindi ve herkese bildirildi.", parse_mode="HTML")

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

# --- WEBAPP VERİLERİ ---
@dp.message(F.web_app_data)
async def handle_webapp(msg: types.Message):
    try: p = json.loads(msg.web_app_data.data)
    except Exception: return
    op = p.get("sender") or ("Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil")
    is_test = bool(p.get("test_mode", False))
    dir_t = p.get("direction")

    if dir_t == "TEST_MODE_TOGGLE":
        global TEST_MODE
        TEST_MODE = bool(p.get("active", False))
        st_text = "AÇILDI" if TEST_MODE else "KAPATILDI"
        await bot.send_message(OMER_CHAT_ID, f"🧪 <b>TEST MODU:</b> {st_text}", parse_mode="HTML")
        return

    if dir_t == "STOCK_CHANGE":
        code, name, delta = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), safe_stock_qty(p.get("delta", 1), 1)
        stocks = load_stocks()
        target = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower()), None)
        if p.get("action") == "INCREASE":
            if target: target["qty"] = safe_stock_qty(target.get("qty", 0)) + delta; new_q = target["qty"]
            else: new_q = delta; stocks.append({"code": code, "name": name, "cat": p.get("category", "MEKATRONIK"), "qty": new_q, "loc": "ELIPS-DEPO", "is_new": bool(p.get("is_new", False))})
            save_stocks(stocks)
            await notify_both(f"📥 <b>STOK ARTIRILDI</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n📈 <b>+{delta}</b> | Yeni: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>", is_test=is_test)
        elif p.get("action") == "DECREASE":
            dest = p.get("destination", "Bilinmeyen")
            if target: target["qty"] = max(0, safe_stock_qty(target.get("qty", 0)) - delta); new_q = target["qty"]
            else: new_q = safe_stock_qty(p.get("current_qty", 0))
            save_stocks(stocks)
            sales = load_sales()
            sales.append({"id": f"SLS-{int(time.time())}", "firm": dest, "source": "ELIPS_DEPO", "items": [{"code": code, "name": name, "qty": delta}], "status": "APPROVED", "date": get_now_uz().strftime("%d.%m.%Y %H:%M"), "timestamp": get_now_uz().isoformat()})
            save_sales(sales)
            await notify_both(f"📤 <b>STOK ÇIKIŞI / SATIŞ</b>\n🏢 {html.escape(dest)}\n⚙️ <code>[{code}]</code> (-{delta} Adet)\n📉 Kalan: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>", is_test=is_test)

    elif dir_t == "STOCK_DELETE":
        code, name, silent = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), bool(p.get("silent", False))
        stocks = [s for s in load_stocks() if str(s.get("code", "")).lower() != code.lower()]
        save_stocks(stocks)
        if not silent:
            await notify_both(f"🗑️ <b>PARÇA SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n👷‍♂️ Yapan: <b>Ömer</b>", is_test=is_test)

    elif dir_t == "REPAIR_UPDATE":
        f_name, model, sn, st, issue = p.get("firm"), p.get("model"), p.get("sn"), p.get("status_text"), p.get("issue")
        await notify_both(
            f"🖥️ <b>EKRAN TAMİR GÜNCELLEMESİ</b>\n═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(str(f_name))}</b>\n"
            f"📱 Model: <b>{html.escape(str(model))}</b> (SN: <code>{html.escape(str(sn))}</code>)\n"
            f"⚠️ Arıza: <i>{html.escape(str(issue))}</i>\n"
            f"📍 Durum: <b>{html.escape(str(st))}</b>\n"
            f"👷‍♂️ Güncelleyen: <b>{op}</b>",
            is_test=is_test
        )

# --- SOHBET / TELSİZ KÖPRÜSÜ ---
@dp.message(~F.text.startswith("/"))
async def chat_bridge(msg: types.Message):
    if TEST_MODE or msg.text in ["📦 Parça Listesi", "📥 Depoya Stok Ekle", "📝 Eliar'dan Teklif Al", "📊 Z-Raporu Al"]: return
    tid = KAMIL_CHAT_ID if msg.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if msg.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and msg.text:
        await bot.send_message(tid, f"💬 <b>{sender}:</b> {html.escape(msg.text)}", parse_mode="HTML")
        await msg.reply("✓ <i>İletildi.</i>", parse_mode="HTML")

# --- CUMARTESİ 12:30 Z-RAPORU ---
async def automated_scheduler():
    last_week = ""
    while True:
        now = get_now_uz()
        today = now.strftime("%Y-%m-%d")
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = [s for s in load_sales() if s.get("status") == "APPROVED"]
            await notify_both(f"📢 <b>HAFTALIK Z-RAPORU (Cumartesi 12:30)</b>\n\nToplam Satış Hareketi: {len(sales)} işlem.")
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
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands()
        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        logging.info(">>> ELIPS DEPO BOTU AKTIF <<<")
        await dp.start_polling(bot)
    except Exception as e: logging.error(f"Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
