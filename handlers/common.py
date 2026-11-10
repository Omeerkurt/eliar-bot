import html
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from config import (
    OMER_CHAT_ID, KAMIL_CHAT_ID, WEBAPP_URL, TEST_MODE, bot,
    QuoteState, StockAddState
)
from database import load_stocks, safe_stock_qty

router = Router()

def get_user_keyboard(user_id: int):
    # Teklif yönetim butonları menüye eklendi
    base_rows = [
        [KeyboardButton(text="⚡ Eliar Mini App", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="📦 Parça Listesi"), KeyboardButton(text="📥 Depoya Stok Ekle")],
        [KeyboardButton(text="⏳ Bekleyen Teklifler"), KeyboardButton(text="✅ Tamamlanan Teklifler")],
        [KeyboardButton(text="📂 Tüm Teklifler"), KeyboardButton(text="📝 Eliar'dan Teklif Al")],
        [KeyboardButton(text="📊 Z-Raporu Al")]
    ]
    if user_id == OMER_CHAT_ID:
        base_rows.insert(2, [KeyboardButton(text="🗑️ Parça Sil")])
    return ReplyKeyboardMarkup(keyboard=base_rows, resize_keyboard=True, is_persistent=False)

@router.message(Command("iptal", "vazgec"), StateFilter("*"))
@router.message(F.text.casefold().in_(["iptal", "vazgeç", "vazgec"]), StateFilter("*"))
async def cmd_cancel(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ <b>İşlem iptal edildi.</b>", reply_markup=get_user_keyboard(msg.chat.id), parse_mode="HTML")

@router.message(CommandStart(), StateFilter("*"))
@router.message(Command("start"), StateFilter("*"))
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
        f"• PDF Teklif & Servis Takibi: <b>Aktif</b>\n\n"
        f"💡 <i>Nilay Hanım'dan gelen PDF teklifleri doğrudan bu sohbete iletebilirsin; bot otomatik tanıyacaktır.</i>"
    )
    await msg.answer(welcome_text, reply_markup=get_user_keyboard(user_id), parse_mode="HTML")

# ✅ DÜZELTİLDİ: Sadece gerçek metin mesajlarını yakalar, PDF ve dosyaları engellemez!
@router.message(F.text & ~F.text.startswith("/"))
async def chat_bridge(msg: types.Message):
    if TEST_MODE or msg.text in [
        "📦 Parça Listesi", "📥 Depoya Stok Ekle", "🗑️ Parça Sil", "📝 Eliar'dan Teklif Al",
        "📊 Z-Raporu Al", "⏳ Bekleyen Teklifler", "✅ Tamamlanan Teklifler", "📂 Tüm Teklifler"
    ]: return
    tid = KAMIL_CHAT_ID if msg.chat.id == OMER_CHAT_ID else (OMER_CHAT_ID if msg.chat.id == KAMIL_CHAT_ID else None)
    sender = "Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil"
    if tid and msg.text:
        await bot.send_message(tid, f"💬 <b>{sender}:</b> {html.escape(msg.text)}", parse_mode="HTML")
        await msg.reply("✓ <i>İletildi.</i>", parse_mode="HTML")
