import json, logging, asyncio, os, re, time, html, difflib
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types, BaseMiddleware
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, BotCommand, BufferedInputFile
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

BOT_TOKEN = "9212674639:AAGVES4GiQRUlwrXfFy6iu4IsXKYo-4jzUY"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
TEST_MODE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

STOCKS_FILE, SALES_FILE, QUOTES_FILE = "stocks_db.json", "weekly_sales.json", "submitted_quotes.json"

class QuoteState(StatesGroup):
    waiting_firm = State()
    waiting_item = State()
    waiting_qty = State()
    confirm_more = State()

class StockAddState(StatesGroup):
    waiting_query = State()
    waiting_qty = State()

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

load_stocks = lambda: load_data(STOCKS_FILE, [])
load_sales = lambda: load_data(SALES_FILE, [])
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d) if not TEST_MODE else None
save_sales = lambda d: save_data(SALES_FILE, d) if not TEST_MODE else None
save_quotes = lambda d: save_data(QUOTES_FILE, d)

def extract_part_image_from_pdf(code: str) -> bytes:
    for name in ["Katalog.pdf", "katalog.pdf", "rd96.pdf", "RD96.pdf"]:
        if os.path.exists(name):
            try:
                import fitz
                doc = fitz.open(name)
                for page in doc:
                    if page.search_for(str(code).strip()):
                        return page.get_pixmap(dpi=150).tobytes("png")
            except Exception: pass
    return None

def find_best_matches(query: str):
    q = normalize_tr(query.strip())
    stocks = load_stocks()
    scored = []
    for p in stocks:
        name_n, code_n = normalize_tr(p.get("name", "")), normalize_tr(p.get("code", ""))
        score = 1.0 if q in (code_n, name_n) else max(0.9 if q in code_n else 0.0, difflib.SequenceMatcher(None, q, name_n).ratio())
        if score > 0.3: scored.append((p, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored

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
        BotCommand(command="start", description="Ana Menü / Durum"),
        BotCommand(command="stok", description="Depo Envanteri & Yeniler"),
        BotCommand(command="stokekle", description="Stok Ekle / Yeni Tanımla"),
        BotCommand(command="stoksil", description="Parça Sil (Sadece Admin)"),
        BotCommand(command="teklif", description="Teklif Oluştur"),
        BotCommand(command="zraporu", description="Satış Z-Raporu"),
        BotCommand(command="iptal", description="Açık İşlemi İptal Et")
    ])

@dp.message(Command("iptal", "vazgec"), StateFilter("*"))
@dp.message(F.text.casefold().in_(["iptal", "vazgeç", "vazgec"]), StateFilter("*"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ <b>İşlem iptal edildi.</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")

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
        f" <b>{user_title}</b>, sisteme hoş geldiniz.\n\n"
        f"📊 <b>Depo Envanter Durumu:</b>\n"
        f"• Tanımlı Parça Çeşidi: <b>{len(stocks)} Kalem</b>\n"
        f"• Depoda Mevcut Ürün: <b>{in_stock} Çeşit</b>\n"
        f"• Teknik Servis Takibi: <b>Aktif</b>\n\n"
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
        new_p = {"code": q.upper() if len(q) <= 12 and " " not in q else "KODSUZ", "name": q, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
        await state.update_data(target_part=new_p)
        await state.set_state(StockAddState.waiting_qty)
        await msg.answer(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> <code>{html.escape(q)}</code>\n➕ Kaç adet eklenecek?", parse_mode="HTML")
        return

    top, _ = matches[0]
    if q.lower() == str(top.get('code', '')).lower():
        await state.update_data(target_part=top)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(top.get("code", ""))
        if img: await msg.answer_photo(BufferedInputFile(img, filename=f"{top.get('code')}.png"), caption=f"📸 <code>[{top.get('code')}]</code>")
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
    await cb.message.edit_text(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> {html.escape(q)}\n➕ Kaç adet eklenecek?", parse_mode="HTML")

@dp.callback_query(F.data.startswith("sel_s:"))
async def on_sel_s(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if part:
        await state.update_data(target_part=part)
        await state.set_state(StockAddState.waiting_qty)
        img = extract_part_image_from_pdf(part.get("code", ""))
        if img: await cb.message.answer_photo(BufferedInputFile(img, filename=f"{part.get('code')}.png"), caption=f"📸 <code>[{part.get('code')}]</code>")
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

# --- SADECE ÖMER'E ÖZEL SİLME KOMUTU ---
@dp.message(Command("stoksil", ignore_mention=True))
async def cmd_stock_delete(msg: types.Message):
    # KAMİL ENGELİ: Kamil yazarsa engeller!
    if msg.chat.id != OMER_CHAT_ID:
        await msg.answer("🔒 <b>Yetkisiz İşlem:</b> Depodan parça silme yetkisi yalnızca yöneticiye (Ömer Bey'e) aittir.", parse_mode="HTML")
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
    await msg.answer(f"⚠️ <code>[{target.get('code')}]</code> {html.escape(target.get('name', ''))}\nNasıl silmek istersiniz?", reply_markup=kb, parse_mode="HTML")

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
        await cb.message.edit_text(f"🔕 <code>[{code}]</code> parçası depodan <b>kimseye bildirim gitmeden</b> sessizce silindi.", parse_mode="HTML")
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
    if img: await msg.answer_photo(BufferedInputFile(img, filename=f"{part.get('code')}.png"), caption=f"📸 <code>[{part.get('code')}]</code>")
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

# --- WEBAPP VERİLERİ (TEST MODU VE YETKİ KORUMALI) ---
@dp.message(F.web_app_data)
async def handle_webapp(msg: types.Message):
    try: p = json.loads(msg.web_app_data.data)
    except Exception: return
    op = p.get("sender") or ("Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil")
    is_test = bool(p.get("test_mode", False))
    dir_t = p.get("direction")

    # TEST MODU AÇMA / KAPAMA
    if dir_t == "TEST_MODE_TOGGLE":
        global TEST_MODE
        TEST_MODE = bool(p.get("active", False))
        st_text = "AÇILDI (Kamil'e bildirim gitmez)" if TEST_MODE else "KAPATILDI (Canlı mod aktif)"
        await bot.send_message(OMER_CHAT_ID, f"🧪 <b>TEST MODU BİLGİSİ:</b>\nSimülasyon modu arayüzden <b>{st_text}</b>.", parse_mode="HTML")
        return

    # STOK DEĞİŞİMİ
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

    # PARÇA SİLME (SADECE ÖMER'DEN GELİR)
    elif dir_t == "STOCK_DELETE":
        code, name, silent = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), bool(p.get("silent", False))
        stocks = [s for s in load_stocks() if str(s.get("code", "")).lower() != code.lower()]
        save_stocks(stocks)
        if not silent:
            await notify_both(f"🗑️ <b>PARÇA SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n👷‍♂️ Yapan: <b>Ömer</b>", is_test=is_test)

    # EKRAN TAMİR BİLDİRİMİ
    elif dir_t == "REPAIR_UPDATE":
        f_name, model, sn, st, issue = p.get("firm"), p.get("model"), p.get("sn"), p.get("status_text"), p.get("issue")
        await notify_both(
            f"🖥️ <b>EKRAN TAMİR / SERVİS GÜNCELLEMESİ</b>\n═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(str(f_name))}</b>\n"
            f"📱 Model: <b>{html.escape(str(model))}</b> (SN: <code>{html.escape(str(sn))}</code>)\n"
            f"⚠️ Arıza: <i>{html.escape(str(issue))}</i>\n"
            f"📍 Durum: <b>{html.escape(str(st))}</b>\n"
            f"👷‍♂️ Güncelleyen: <b>{op}</b>",
            is_test=is_test
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
            await notify_both(f"📢 <b>HAFTALIK Z-RAPORU (Cumartesi 12:30)</b>\n\nToplam Satış Hareketi: {len(sales)} adet işlem.")
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
        logging.info(">>> BOT AKTIF <<<")
        await dp.start_polling(bot)
    except Exception as e: logging.error(f"Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
