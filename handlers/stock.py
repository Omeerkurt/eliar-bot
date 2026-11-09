import html
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from config import OMER_CHAT_ID, notify_both, bot
from database import (
    load_stocks, save_stocks, safe_stock_qty, parse_qty_safe,
    find_best_matches
)
from pdf_tools import extract_part_image_from_pdf
from handlers.common import StockAddState

router = Router()

@router.message(Command("stok", ignore_mention=True))
@router.message(F.text == "📦 Parça Listesi")
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
        [InlineKeyboardButton(text="📦 Tümü", callback_data="stk_all"), InlineKeyboardButton(text="✨ Sadece Yeniler", callback_data="stk_new")]
    ])
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.in_(["stk_all", "stk_new"]))
async def cb_stk_filter(cb: types.CallbackQuery):
    await cb.answer()
    only_new = cb.data == "stk_new"
    stocks = load_stocks()
    if only_new: stocks = [s for s in stocks if isinstance(s, dict) and s.get("is_new")]
    available = [s for s in stocks if isinstance(s, dict) and safe_stock_qty(s.get("qty", 0)) > 0]
    text = f"📦 <b>{'✨ YENİ PARÇALAR' if only_new else 'ELİAR DEPO ENVANTERİ'}</b>\nToplam: <b>{len(stocks)} Kalem</b> | Stokta: <b>{len(available)}</b>\n═══════════════════════════════\n\n"
    for s in available[:15]:
        tag = " 🆕 [YENİ]" if s.get("is_new") else ""
        text += f"• <code>[{s.get('code', 'KODSUZ')}]</code> {html.escape(str(s.get('name', ''))[:28])}{tag} ➔ <b>{safe_stock_qty(s.get('qty', 0))} ADT</b>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Tümü", callback_data="stk_all"), InlineKeyboardButton(text="✨ Sadece Yeniler", callback_data="stk_new")]
    ])
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# STOK EKLEME
@router.message(Command("stokekle", ignore_mention=True))
@router.message(F.text == "📥 Depoya Stok Ekle")
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
            await notify_both(bot, f"📥 <b>STOK EKLENDİ!</b>\n⚙️ <code>[{code_in}]</code> {html.escape(p_name)}{tag}\n📈 <b>+{qty_in}</b> | Stok: <b>{new_q} ADT</b>\n👷‍♂️ Ekleyen: <b>{op}</b>")
            return
        except Exception: pass

    await state.clear()
    await state.set_state(StockAddState.waiting_query)
    await msg.answer("📥 <b>STOK EKLE:</b> Parça kodu veya adını yazın:\n(Örn: <code>90567</code>, <code>diyafram</code>)", parse_mode="HTML")

@router.message(StockAddState.waiting_query, ~F.text.startswith("/"))
async def stock_add_q(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    await state.update_data(raw_query=query)
    matches = find_best_matches(query)

    if not matches:
        new_p = {"code": query.upper() if len(query) <= 12 and " " not in query else "KODSUZ", "name": query, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
        await state.update_data(target_part=new_p)
        await state.set_state(StockAddState.waiting_qty)
        await msg.answer(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> <code>{html.escape(query)}</code>\n➕ Depoya kaç adet eklenecek?", parse_mode="HTML")
        return

    top_part, _ = matches[0]
    if query.lower() == str(top_part.get('code', '')).lower():
        await state.update_data(target_part=top_part)
        await state.set_state(StockAddState.waiting_qty)
        img_bytes = extract_part_image_from_pdf(top_part.get("code", ""), top_part.get("name", ""))
        if img_bytes:
            photo = BufferedInputFile(img_bytes, filename=f"{top_part.get('code')}.png")
            await msg.answer_photo(photo, caption=f"📸 <code>[{top_part.get('code')}]</code> {html.escape(top_part.get('name', ''))}", parse_mode="HTML")
        cur_q = safe_stock_qty(top_part.get('qty', 0))
        tag = " 🆕 [YENİ]" if top_part.get("is_new") else ""
        await msg.answer(f"🎯 <b>Seçilen:</b> <code>[{top_part.get('code')}]</code> {html.escape(top_part.get('name', ''))}{tag}\n📦 Mevcut: <b>{cur_q} ADT</b>\n\n➕ Kaç adet eklenecek?", parse_mode="HTML")
        return

    btns = []
    for p, _ in matches[:5]:
        p_code = p.get('code', 'KODSUZ')
        p_name = p.get('name', '')[:25]
        p_qty = safe_stock_qty(p.get('qty', 0))
        tag = "🆕 " if p.get("is_new") else ""
        btns.append([InlineKeyboardButton(text=f"👉 {tag}[{p_code}] {p_name} ({p_qty} Adt)", callback_data=f"sel_s:{p_code}")])
    btns.append([InlineKeyboardButton(text=f"➕ Listede Yok, Yeni Tanımla: '{query[:15]}'", callback_data="add_unlisted_part")])
    await msg.answer("🔍 Eşleşen parçalar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data == "add_unlisted_part")
async def on_add_unlisted_part(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    q = (await state.get_data()).get("raw_query", "Özel Parça").strip()
    new_p = {"code": q.upper() if len(q) <= 12 and " " not in q else "KODSUZ", "name": q, "cat": "MEKATRONIK", "qty": 0, "loc": "ELIPS-DEPO", "is_new": True}
    await state.update_data(target_part=new_p)
    await state.set_state(StockAddState.waiting_qty)
    await callback.message.edit_text(f"🆕 <b>Yeni Parça Tanımlanıyor:</b> {html.escape(q)}\n➕ Depoya kaç adet eklenecek?")

@router.callback_query(F.data.startswith("sel_s:"))
async def on_sel_s(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if part:
        await state.update_data(target_part=part)
        await state.set_state(StockAddState.waiting_qty)
        img_bytes = extract_part_image_from_pdf(part.get("code", ""), part.get("name", ""))
        if img_bytes:
            photo = BufferedInputFile(img_bytes, filename=f"{part.get('code')}.png")
            await cb.message.answer_photo(photo, caption=f"📸 <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}", parse_mode="HTML")
        await cb.message.answer(f"🎯 <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}\n➕ Kaç adet eklenecek?", parse_mode="HTML")

@router.message(StockAddState.waiting_qty, ~F.text.startswith("/"))
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
    await notify_both(bot, f"📥 <b>STOK EKLENDİ!</b>\n⚙️ <code>[{p.get('code')}]</code> {html.escape(p.get('name', ''))}{tag}\n📈 <b>+{qty}</b> | Yeni Stok: <b>{new_q} ADT</b>\n👷‍♂️ Ekleyen: <b>{op}</b>")

# SADECE ÖMER'E ÖZEL SİLME MOTORU
@router.message(Command("stoksil", ignore_mention=True))
@router.message(F.text == "🗑️ Parça Sil")
async def cmd_stock_delete(msg: types.Message):
    if msg.chat.id != OMER_CHAT_ID:
        await msg.answer("🔒 <b>Yetkisiz İşlem:</b> Bu işlem için yönetici yetkisi gerekmektedir.", parse_mode="HTML")
        return

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() == "Sil":
        await msg.answer("⚠️ Silmek istediğin parça kodunu belirt.\nÖrnek: <code>/stoksil 90567</code>", parse_mode="HTML")
        return

    code = parts[1].strip()
    target = next((s for s in load_stocks() if str(s.get("code", "")).lower() == code.lower()), None)
    if not target: await msg.answer(f"⚠️ <code>{html.escape(code)}</code> bulunamadı."); return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔕 Bildirimsiz Sil (Sessiz)", callback_data=f"del_p:{code}:silent"),
         InlineKeyboardButton(text="📢 Bildirerek Sil", callback_data=f"del_p:{code}:notify")],
        [InlineKeyboardButton(text="❌ Vazgeç", callback_data="cb_close")]
    ])
    await msg.answer(f"⚠️ <code>[{target.get('code')}]</code> {html.escape(target.get('name', ''))}\nNasıl silmek istersin?", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("del_p:"))
async def on_del_p(cb: types.CallbackQuery):
    await cb.answer()
    if cb.message.chat.id != OMER_CHAT_ID:
        await cb.message.edit_text("🔒 Bu işlem için yönetici yetkisi gerekmektedir.")
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
        await notify_both(bot, f"🗑️ <b>DEPO PARÇASI SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(target.get('name', ''))}\n👷‍♂️ Silen: <b>Ömer</b>")
        await cb.message.edit_text(f"🗑️ <code>[{code}]</code> silindi ve herkese bildirildi.", parse_mode="HTML")

@router.callback_query(F.data == "cb_close")
async def cb_close(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.delete()