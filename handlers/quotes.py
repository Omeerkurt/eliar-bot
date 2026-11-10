import html, time, os
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
# ✅ DÜZELTİLDİ: QuoteState doğrudan config'den çekiliyor
from config import (
    PDF_STORAGE_DIR, KAMIL_CHAT_ID, TEST_MODE, get_now_uz, notify_both, bot, QuoteState
)
from database import (
    load_stocks, save_stocks, load_quotes, save_quotes, load_sales, save_sales,
    safe_stock_qty, parse_qty_safe, find_best_matches
)
from pdf_tools import extract_part_image_from_pdf, parse_eliar_pdf_locally

router = Router()

# ==============================================================================
#      NİLAY HANIM'DAN GELEN PDF TEKLİFİ OKUYUCU MOTORU
# ==============================================================================
@router.message(F.document)
async def handle_pdf_upload(msg: types.Message):
    doc = msg.document
    if not (doc.file_name or "").lower().endswith(".pdf"):
        await msg.answer("⚠️ Lütfen PDF formatında teklif belgesi yükleyin.")
        return

    save_path = os.path.join(PDF_STORAGE_DIR, f"{int(time.time())}_{doc.file_name}")
    await bot.download(doc, destination=save_path)

    wait = await msg.answer("⏳ <i>PDF taranıyor, parçalar Elips deposuyla eşleştiriliyor...</i>", parse_mode="HTML")
    parsed = parse_eliar_pdf_locally(save_path, doc.file_name)
    await wait.delete()

    quote_id = f"TK-{int(time.time())}"
    quote_data = {
        "id": quote_id, "firm": parsed["firm"], "ref_no": parsed["ref_no"],
        "date": parsed["date"], "currency": parsed["currency"], "grand_total": parsed["grand_total"],
        "status": "PENDING", "items": parsed["items"], "pdf_file": save_path
    }
    quotes = load_quotes()
    quotes.append(quote_data)
    save_quotes(quotes)

    stocks = load_stocks()
    analysis_lines = []
    for idx, itm in enumerate(parsed["items"], 1):
        p = next((s for s in stocks if str(s.get("code", "")).lower() == str(itm["code"]).lower()), None)
        avail = safe_stock_qty(p.get("qty", 0)) if p else 0
        req = itm["qty"]
        stat = f"🟢 Depoda Var ({avail} ADT)" if avail >= req else (f"🟡 Kısmi ({avail} ADT)" if avail > 0 else "🔴 Depoda YOK (TR'den İstenmeli)")
        analysis_lines.append(f"<b>{idx}.</b> <code>[{itm['code']}]</code> {html.escape(itm['name'])} ➔ {req} Adet ({stat})")

    text = (
        f"📄 <b>NİLAY HANIM'DAN GELEN TEKLİF DOĞRULANDI!</b>\n"
        f"═══════════════════════════════\n"
        f"🏢 <b>Firma:</b> <b>{html.escape(parsed['firm'])}</b>\n"
        f"🔖 <b>Ref No:</b> <code>{parsed['ref_no']}</code> | 💰 <b>Tutar:</b> {parsed['grand_total']} {parsed['currency']}\n\n"
        f"<b>📦 ÖZBEKİSTAN (ELİPS) DEPO ANALİZİ:</b>\n" +
        ("\n".join(analysis_lines) if analysis_lines else "⚠️ <i>Kalemler ayrıştırılamadı.</i>") +
        f"\n\n❓ <b>Bu teklif nereden karşılanacak?</b>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Özbek (Elips) Depodan Karşıla", callback_data=f"qroute:{quote_id}:ELIPS")],
        [InlineKeyboardButton(text="🇹🇷 Eliar TR'den Gelecek (Kamil'e Bildir)", callback_data=f"qroute:{quote_id}:TR")],
        [InlineKeyboardButton(text="🔕 Bildirimsiz Sil", callback_data=f"qdel:{quote_id}")]
    ])
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("qroute:"))
async def on_quote_route(cb: types.CallbackQuery):
    await cb.answer()
    _, qid, route = cb.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == qid), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return

    if route == "TR":
        q["status"], q["source"] = "APPROVED", "TR_DEPO"
        save_quotes(quotes)
        sales = load_sales()
        sales.append({"id": f"SLS-{int(time.time())}", "firm": q["firm"], "source": "TR_DEPO", "items": q["items"], "status": "APPROVED", "date": get_now_uz().strftime("%d.%m.%Y %H:%M")})
        save_sales(sales)

        tr_msg = (
            f"📦 <b>KAMİL - YENİ TR SEVKİYAT / KARGO EMRİ</b>\n"
            f"═══════════════════════════════\n"
            f"🏭 <b>Müşteri:</b> <b>{html.escape(q['firm'])}</b>\n"
            f"🔖 <b>Ref No:</b> <code>{q.get('ref_no','YOK')}</code>\n\n"
            f"<b>Paketlenecek Parçalar:</b>\n" +
            "\n".join([f"• [{i.get('code')}] {i.get('name')} ➔ <b>{i.get('qty')} Adet</b>" for i in q["items"]]) +
            "\n\n✈️ <i>Lütfen Özbekistan sevkiyat kolisine ekle.</i>"
        )
        if not TEST_MODE:
            try: await bot.send_message(KAMIL_CHAT_ID, tr_msg, parse_mode="HTML")
            except Exception: pass

        await cb.message.edit_text(f"🇹🇷 <b>TEKLİF ONAYLANDI (TÜRKİYE'DEN GELECEK)</b>\nKamil'e kargo ve paketleme talimatı iletildi. Elips depo stoğuna dokunulmadı.", parse_mode="HTML")
        return

    # ELIPS DEPO ÇIKIŞI
    q["status"], q["source"] = "APPROVED", "ELIPS_DEPO"
    save_quotes(quotes)
    stocks = load_stocks()
    sales = load_sales()
    deducted = []

    for itm in q["items"]:
        code, req_q = str(itm.get("code")).lower(), itm.get("qty", 1)
        p = next((s for s in stocks if str(s.get("code")).lower() == code), None)
        if p and p.get("qty", 0) > 0:
            act = min(p["qty"], req_q)
            p["qty"] -= act
            deducted.append(f"• <code>[{p['code']}]</code> {p['name']}: <b>-{act} Adet</b> (Kalan: {p['qty']})")

    save_stocks(stocks)
    sales.append({"id": f"SLS-{int(time.time())}", "firm": q["firm"], "source": "ELIPS_DEPO", "items": q["items"], "status": "APPROVED", "date": get_now_uz().strftime("%d.%m.%Y %H:%M")})
    save_sales(sales)

    await notify_both(f"📦 <b>ELİPS DEPO STOK ÇIKIŞI!</b>\n🏢 {html.escape(q['firm'])}\n" + "\n".join(deducted))
    await cb.message.edit_text("✅ <b>Teklif onaylandı ve Özbekistan Elips stoğundan düşüldü.</b>", parse_mode="HTML")

@router.callback_query(F.data.startswith("qdel:"))
async def on_quote_del(cb: types.CallbackQuery):
    await cb.answer()
    qid = cb.data.split(":")[1]
    quotes = [x for x in load_quotes() if x["id"] != qid]
    save_quotes(quotes)
    await cb.message.edit_text("🔕 Teklif kaydı sessizce silindi.")

# ==============================================================================
#      TEKLİF HAZIRLAMA SİHİRBAZI
# ==============================================================================
@router.message(Command("teklif", ignore_mention=True))
@router.message(F.text == "📝 Eliar'dan Teklif Al")
async def start_quote(msg: types.Message, state: FSMContext):
    await state.clear()
    await state.update_data(quote_items=[])
    await state.set_state(QuoteState.waiting_firm)
    await msg.answer("🏢 <b>Müşteri / Fabrika Adı:</b> (Örn: TERRY JAR)", parse_mode="HTML")

@router.message(QuoteState.waiting_firm, ~F.text.startswith("/"))
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

@router.message(QuoteState.waiting_item_query, ~F.text.startswith("/"))
async def quote_item_search(msg: types.Message, state: FSMContext):
    query = msg.text.strip()
    await state.update_data(search_query=query, custom_query=query)
    matches = find_best_matches(query)

    if not matches:
        kb_custom = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Bu İsimle Teklife Ekle", callback_data="qb_add_custom")],
            [InlineKeyboardButton(text="🔍 Tekrar Ara", callback_data="qb_retry")]
        ])
        await msg.answer(f"⚠️ <code>{html.escape(query)}</code> stokta veya katalogda bulunamadı.\nSerbest kalem olarak eklensin mi?", reply_markup=kb_custom, parse_mode="HTML")
        return

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

    await state.update_data(search_matches=matches)
    text, kb = render_search_page(matches, 0, query)
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("qbpage:"))
async def on_qb_page(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    page_idx = int(cb.data.split(":")[1])
    data = await state.get_data()
    text, kb = render_search_page(data.get("search_matches", []), page_idx, data.get("search_query", ""))
    await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "qb_retry")
async def on_qb_retry(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(QuoteState.waiting_item_query)
    await cb.message.edit_text("🔍 Lütfen parça kodunu veya adını tekrar yazın:")

@router.callback_query(F.data.startswith("qbsel:"))
async def on_qb_part_select(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    code = cb.data.split(":")[1]
    part = next((p for p in load_stocks() if str(p.get("code", "")).lower() == code.lower()), None)
    if not part: await cb.answer("Parça bulunamadı.", show_alert=True); return

    await state.update_data(sel_part=part)
    await state.set_state(QuoteState.waiting_qty)

    img_bytes = extract_part_image_from_pdf(part.get("code", ""), part.get("name", ""))
    if img_bytes:
        photo = BufferedInputFile(img_bytes, filename=f"{part.get('code')}.png")
        await cb.message.answer_photo(photo, caption=f"📸 <b>Katalog Çizimi:</b> <code>[{part.get('code')}]</code> — {html.escape(part.get('name', ''))}", parse_mode="HTML")

    p_qty = safe_stock_qty(part.get('qty', 0))
    stock_text = f"Depo: {p_qty} ADT" if p_qty > 0 else "Stokta Yok (0 ADT)"
    await cb.message.answer(f"🎯 <b>Seçilen:</b> <code>[{part.get('code')}]</code> {html.escape(part.get('name', ''))}\n📦 <b>{stock_text}</b>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")

@router.callback_query(F.data == "qb_add_custom")
async def on_qb_custom(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    q = (await state.get_data()).get("custom_query", "Özel Parça")
    await state.update_data(sel_part={"code": "KODSUZ", "name": q, "qty": 0})
    await state.set_state(QuoteState.waiting_qty)
    await cb.message.answer(f"🎯 <b>Seçilen:</b> {html.escape(q)} <i>(Katalog Dışı)</i>\n\n🔢 Kaç <b>adet</b> teklif istenecek?", parse_mode="HTML")

# --- ADET ALICI: 0 / İPTAL MANTIĞI ---
@router.message(QuoteState.waiting_qty, ~F.text.startswith("/"))
async def quote_process_qty(msg: types.Message, state: FSMContext):
    text
