import html, time, os
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile, FSInputFile
from config import (
    PDF_STORAGE_DIR, OMER_CHAT_ID, KAMIL_CHAT_ID, TEST_MODE, get_now_uz, notify_both, bot, QuoteState
)
from database import (
    load_stocks, save_stocks, load_quotes, save_quotes, load_sales, save_sales,
    safe_stock_qty, parse_qty_safe, find_best_matches
)
from pdf_tools import extract_part_image_from_pdf, parse_eliar_pdf_locally

router = Router()

# ==============================================================================
#      1. PDF TEKLİF YÜKLEME (KAMİL YÜKLEYİNCE ÖMER'E ANINDA BİLDİRİM GİDER)
# ==============================================================================
@router.message(F.document)
async def handle_pdf_upload(msg: types.Message):
    doc = msg.document
    doc_name = (doc.file_name or "").lower()

    if not doc_name.endswith(".pdf"):
        await msg.answer("⚠️ Lütfen PDF formatında bir teklif belgesi yükleyin.")
        return

    # Orijinal PDF'i sunucu arşivine kaydet
    save_path = os.path.join(PDF_STORAGE_DIR, f"{int(time.time())}_{doc.file_name}")
    await bot.download(doc, destination=save_path)

    wait = await msg.answer("⏳ <i>PDF taranıyor, parçalar Elips deposuyla eşleştiriliyor...</i>", parse_mode="HTML")
    parsed = parse_eliar_pdf_locally(save_path, doc.file_name)
    await wait.delete()

    quote_id = f"TK-{int(time.time())}"
    quote_data = {
        "id": quote_id,
        "firm": parsed.get("firm", "BİLİNMEYEN FİRMA").upper(),
        "ref_no": parsed.get("ref_no", "BELİRTİLMEDİ"),
        "date": parsed.get("date", get_now_uz().strftime("%d.%m.%Y")),
        "currency": parsed.get("currency", "EUR"),
        "grand_total": parsed.get("grand_total", "-"),
        "status": "PENDING",
        "items": parsed.get("items", []),
        "pdf_file": save_path
    }

    quotes = load_quotes()
    quotes.append(quote_data)
    save_quotes(quotes)

    # Yükleyen kişiye kartı göster
    await render_quote_card(msg, quote_data, is_new=True)

    # ✅ EĞER YÜKLEYEN KAMİL İSE: Ömer'e anında tam teklif kartıyla bildirim gönder!
    if msg.chat.id == KAMIL_CHAT_ID:
        await render_quote_card(
            OMER_CHAT_ID,
            quote_data,
            is_new=True,
            extra_header="📥 <b>KAMİL YENİ BİR TEKLİF PDF'İ YÜKLEDİ!</b>"
        )

# TEKLİF DETAY KARTINI VE İŞLEM BUTONLARINI ÇİZEN MERKEZİ FONKSİYON
async def render_quote_card(target, q, is_new=False, extra_header=""):
    quote_id = q["id"]
    status_map = {
        "PENDING": "⏳ Beklemede (Müşteri Düşünüyor)",
        "APPROVED": "🟢 Kabul Edildi (Onaylandı)",
        "REJECTED": "🔴 Müşteri Reddetti"
    }
    cur_status = status_map.get(q.get("status"), "Belirsiz")
    cur = q.get("currency", "EUR")

    stocks = load_stocks()
    analysis_lines = []
    for idx, itm in enumerate(q.get("items", []), 1):
        code = str(itm.get("code", "")).strip()
        req_q = safe_stock_qty(itm.get("qty", 1), 1)
        p = next((s for s in stocks if str(s.get("code", "")).lower() == code.lower()), None)
        avail = safe_stock_qty(p.get("qty", 0)) if p else 0
        stat = f"🟢 Depoda Var ({avail} ADT)" if avail >= req_q else (f"🟡 Kısmi ({avail} ADT)" if avail > 0 else "🔴 Depoda YOK (TR'den İstenmeli)")
        analysis_lines.append(f"<b>{idx}.</b> <code>[{code}]</code> {html.escape(itm.get('name', ''))} ➔ <b>{req_q} Adet</b> ({stat})")

    default_header = "📄 <b>NİLAY HANIM'DAN YENİ TEKLİF ALINDI!</b>" if is_new else "📄 <b>TEKLİF DOSYA KARTI</b>"
    title_header = extra_header if extra_header else default_header

    text = (
        f"{title_header}\n"
        f"═══════════════════════════════\n"
        f"🏢 <b>Firma:</b> <b>{html.escape(q['firm'])}</b>\n"
        f"🔖 <b>Ref No:</b> <code>{q.get('ref_no', 'YOK')}</code> | 📅 <b>Tarih:</b> {q.get('date')}\n"
        f"💰 <b>Tutar:</b> <b>{q.get('grand_total', '-')} {cur}</b>\n"
        f"📍 <b>Güncel Durum:</b> <b>{cur_status}</b>\n\n"
        f"<b>📦 ÖZBEKİSTAN (ELİPS) DEPO ANALİZİ:</b>\n" +
        ("\n".join(analysis_lines) if analysis_lines else "⚠️ <i>Kalem tablosu tespit edilemedi.</i>") +
        f"\n\n⚙️ <i>Aşağıdaki butonlarla teklif durumunu belirleyebilir veya sonradan değiştirebilirsiniz:</i>"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🟢 Müşteri Kabul Etti (Onayla)", callback_data=f"q_prompt_route:{quote_id}"),
            InlineKeyboardButton(text="🔴 Müşteri Reddetti", callback_data=f"q_set_status:{quote_id}:REJECTED")
        ],
        [
            InlineKeyboardButton(text="⏳ Beklemeye Al (Düşünüyor)", callback_data=f"q_set_status:{quote_id}:PENDING")
        ]
    ]

    # Orijinal PDF dosyası varsa indirme butonu
    if q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        buttons.append([InlineKeyboardButton(text="📄 Orijinal PDF'i Geri İndir", callback_data=f"q_download_pdf:{quote_id}")])

    buttons.append([
        InlineKeyboardButton(text="🗑️ Teklifi Kalıcı Olarak Sil", callback_data=f"q_delete_confirm_prompt:{quote_id}"),
        InlineKeyboardButton(text="❌ Kapat", callback_data="cb_close")
    ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Hedef ister chat_id olsun, ister callback, ister mesaj nesnesi; hatasız gönderir
    if isinstance(target, int):
        await bot.send_message(chat_id=target, text=text, reply_markup=kb, parse_mode="HTML")
    elif hasattr(target, "answer"):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await target.edit_text(text, reply_markup=kb, parse_mode="HTML")

# TEDARİK YERİ SEÇİMİ (Özbek Depo vs. TR Eliar)
@router.callback_query(F.data.startswith("q_prompt_route:"))
async def on_prompt_route(cb: types.CallbackQuery):
    await cb.answer()
    quote_id = cb.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 Özbek (Elips) Depodan Karşıla", callback_data=f"q_apply_route:{quote_id}:ELIPS")],
        [InlineKeyboardButton(text="🇹🇷 Eliar TR'den Gelecek (Kamil'e Görev Aç)", callback_data=f"q_apply_route:{quote_id}:TR")],
        [InlineKeyboardButton(text="🔙 Vazgeç / Geri Dön", callback_data=f"q_view:{quote_id}")]
    ])
    await cb.message.edit_text(
        f"🏢 <b>{html.escape(q['firm'])}</b> teklifi kabul edildi.\n\n"
        f"❓ <b>Bu parçalar nereden sevk edilecek?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )

# KABUL EDİLEN TEKLİFİN SEVKİYAT İŞLEMİ
@router.callback_query(F.data.startswith("q_apply_route:"))
async def on_apply_route(cb: types.CallbackQuery):
    await cb.answer()
    _, quote_id, route = cb.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return

    q["status"] = "APPROVED"
    q["source"] = "TR_DEPO" if route == "TR" else "ELIPS_DEPO"
    save_quotes(quotes)

    # 1. TÜRKİYE'DEN GELECEKSE: Kamil'e kargo emri at, Özbek stoğuna dokunma!
    if route == "TR":
        sales = load_sales()
        sales.append({
            "id": f"SLS-{int(time.time())}", "firm": q["firm"], "source": "TR_DEPO",
            "ref_no": q.get("ref_no", "TR-SEVK"), "items": q.get("items", []), "status": "APPROVED",
            "date": get_now_uz().strftime("%d.%m.%Y %H:%M")
        })
        save_sales(sales)

        tr_msg = (
            f"📦 <b>KAMİL - YENİ TR SEVKİYAT / KARGO EMRİ</b>\n"
            f"═══════════════════════════════\n"
            f"🏭 <b>Müşteri:</b> <b>{html.escape(q['firm'])}</b>\n"
            f"🔖 <b>Ref No:</b> <code>{q.get('ref_no', 'YOK')}</code>\n\n"
            f"<b>Paketlenecek Parçalar:</b>\n" +
            "\n".join([f"• [{i.get('code')}] {i.get('name')} ➔ <b>{i.get('qty')} Adet</b>" for i in q.get("items", [])]) +
            "\n\n✈️ <i>Lütfen Özbekistan sevkiyat kolisine ekle.</i>"
        )
        if not TEST_MODE:
            try: await bot.send_message(KAMIL_CHAT_ID, tr_msg, parse_mode="HTML")
            except Exception: pass

        await cb.message.edit_text(
            f"🇹🇷 <b>TEKLİF KABUL EDİLDİ (TÜRKİYE'DEN GELECEK)</b>\n\n"
            f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n"
            f"📦 Kamil'e paketleme ve kargo emri iletildi.\n"
            f"✅ <i>Özbekistan Elips depo stoklarına dokunulmadı. 'Tamamlanan Teklifler'e işlendi.</i>",
            parse_mode="HTML"
        )
        return

    # 2. ÖZBEKİSTAN DEPOSUNDAN KARŞILANACAKSA: Elips stoğundan düş ve Z-raporuna yaz!
    stocks = load_stocks()
    sales = load_sales()
    deducted = []

    for itm in q.get("items", []):
        code = str(itm.get("code", "")).lower()
        req_q = safe_stock_qty(itm.get("qty", 1), 1)
        p = next((s for s in stocks if str(s.get("code", "")).lower() == code), None)
        if p and p.get("qty", 0) > 0:
            act = min(p["qty"], req_q)
            p["qty"] -= act
            deducted.append(f"• <code>[{p['code']}]</code> {p['name']}: <b>-{act} Adet</b> (Kalan: {p['qty']})")

    save_stocks(stocks)
    sales.append({
        "id": f"SLS-{int(time.time())}", "firm": q["firm"], "source": "ELIPS_DEPO",
        "ref_no": q.get("ref_no", "ELIPS-SEVK"), "items": q.get("items", []), "status": "APPROVED",
        "date": get_now_uz().strftime("%d.%m.%Y %H:%M")
    })
    save_sales(sales)

    await notify_both(
        f"📦 <b>ELİPS DEPO - STOK ÇIKIŞI YAPILDI!</b>\n"
        f"═══════════════════════════════\n"
        f"🏢 Firma: <b>{html.escape(q['firm'])}</b>\n\n" +
        ("\n".join(deducted) if deducted else "Stoktan parça düşülemedi.")
    )
    await cb.message.edit_text("✅ <b>Teklif kabul edildi, Elips stoğundan düşüldü ve Tamamlananlar'a kaydedildi.</b>", parse_mode="HTML")

# DURUMU SONRADAN DEĞİŞTİRME
@router.callback_query(F.data.startswith("q_set_status:"))
async def on_set_quote_status(cb: types.CallbackQuery):
    await cb.answer()
    _, quote_id, new_st = cb.data.split(":")
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return

    q["status"] = new_st
    save_quotes(quotes)
    st_title = "Beklemeye alındı" if new_st == "PENDING" else "Reddedildi olarak güncellendi"
    await cb.message.edit_text(f"👌 <b>{html.escape(q['firm'])}</b> teklifi <b>{st_title}</b>.", parse_mode="HTML")

# ORİJİNAL PDF DOSYASINI GERİ İNDİRME
@router.callback_query(F.data.startswith("q_download_pdf:"))
async def on_download_quote_pdf(cb: types.CallbackQuery):
    await cb.answer("PDF belgesi gönderiliyor...")
    quote_id = cb.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if q and q.get("pdf_file") and os.path.exists(q["pdf_file"]):
        await cb.message.answer_document(
            FSInputFile(q["pdf_file"]),
            caption=f"📄 <b>{html.escape(q['firm'])}</b> Fiyat Teklifi PDF Belgesi\n🔖 Ref: <code>{q.get('ref_no','-')}</code>",
            parse_mode="HTML"
        )
    else:
        await cb.message.answer("⚠️ Orijinal PDF dosyası bulunamadı.")

# ==============================================================================
#      2. TEKLİF SİLME (EMİN MİSİNİZ KORUMASIYLA)
# ==============================================================================
@router.callback_query(F.data.startswith("q_delete_confirm_prompt:"))
async def on_quote_delete_prompt(cb: types.CallbackQuery):
    await cb.answer()
    quote_id = cb.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Evet, Kalıcı Olarak Sil", callback_data=f"q_do_delete:{quote_id}")],
        [InlineKeyboardButton(text="❌ Vazgeç / Geri Dön", callback_data=f"q_view:{quote_id}")]
    ])
    await cb.message.edit_text(
        f"⚠️ <b>DİKKAT: TEKLİFİ KALICI SİLME</b>\n"
        f"═══════════════════════════════\n"
        f"🏢 <b>Firma:</b> <b>{html.escape(q['firm'])}</b>\n"
        f"🔖 <b>Ref:</b> <code>{q.get('ref_no','-')}</code>\n\n"
        f"Bu teklif kaydı ve sunucudaki PDF belgesi <b>kalıcı olarak silinecektir</b>. Emin misiniz?",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("q_do_delete:"))
async def on_quote_do_delete(cb: types.CallbackQuery):
    await cb.answer()
    quote_id = cb.data.split(":")[1]
    quotes = load_quotes()
    target_q = next((x for x in quotes if x["id"] == quote_id), None)
    if target_q:
        if target_q.get("pdf_file") and os.path.exists(target_q["pdf_file"]):
            try: os.remove(target_q["pdf_file"])
            except Exception: pass
        quotes = [x for x in quotes if x["id"] != quote_id]
        save_quotes(quotes)
        await cb.message.edit_text(f"🗑️ <b>{html.escape(target_q['firm'])}</b> teklifi kalıcı olarak silindi.", parse_mode="HTML")
    else:
        await cb.message.edit_text("⚠️ Teklif zaten silinmiş.")

# ==============================================================================
#      3. GEÇMİŞİ LİSTELEME VE İNCELEME
# ==============================================================================
@router.message(Command("bekleyenler", ignore_mention=True))
@router.message(F.text == "⏳ Bekleyen Teklifler")
async def show_pending_quotes(msg: types.Message):
    quotes = [q for q in load_quotes() if q.get("status") == "PENDING"]
    if not quotes:
        await msg.answer("ℹ️ Şu anda bekleyen bir teklif bulunmamaktadır.")
        return
    btns = [[InlineKeyboardButton(text=f"🟡 {q['firm']} ({str(q.get('date'))[:10]})", callback_data=f"q_view:{q['id']}")] for q in reversed(quotes[-15:])]
    await msg.answer("⏳ <b>BEKLEYEN TEKLİFLER:</b>\nİncelemek istediğiniz teklife dokunun:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.message(Command("tamamlananlar", ignore_mention=True))
@router.message(F.text == "✅ Tamamlanan Teklifler")
async def show_completed_quotes(msg: types.Message):
    quotes = [q for q in load_quotes() if q.get("status") == "APPROVED"]
    if not quotes:
        await msg.answer("ℹ️ Henüz tamamlanan/kabul edilen teklif bulunmamaktadır.")
        return
    btns = []
    for q in reversed(quotes[-15:]):
        src = " [TR]" if q.get("source") == "TR_DEPO" else " [Elips]"
        btns.append([InlineKeyboardButton(text=f"✅ {q['firm']}{src} ({str(q.get('date'))[:10]})", callback_data=f"q_view:{q['id']}")])
    await msg.answer("✅ <b>TAMAMLANAN TEKLİFLER:</b>\nDetayını veya PDF'ini görmek için dokunun:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.message(Command("teklifler", ignore_mention=True))
@router.message(F.text == "📂 Tüm Teklifler")
async def show_all_quotes(msg: types.Message):
    quotes = load_quotes()
    if not quotes:
        await msg.answer("ℹ️ Henüz kayıtlı teklif bulunmamaktadır.")
        return
    btns = []
    for q in reversed(quotes[-15:]):
        st_icon = "🟢" if q.get("status") == "APPROVED" else ("🔴" if q.get("status") == "REJECTED" else "🟡")
        btns.append([InlineKeyboardButton(text=f"{st_icon} {q['firm']} ({str(q.get('date'))[:10]})", callback_data=f"q_view:{q['id']}")])
    await msg.answer("📂 <b>TÜM TEKLİFLER ARŞİVİ:</b>\nDurumunu değiştirmek veya PDF'ini almak için seçin:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")

@router.callback_query(F.data.startswith("q_view:"))
async def on_quote_view(cb: types.CallbackQuery):
    await cb.answer()
    quote_id = cb.data.split(":")[1]
    quotes = load_quotes()
    q = next((x for x in quotes if x["id"] == quote_id), None)
    if not q: await cb.message.edit_text("⚠️ Teklif bulunamadı."); return
    await render_quote_card(cb.message, q, is_new=False)

# ==============================================================================
#      4. MANUEL TEKLİF HAZIRLAMA SİHİRBAZI (NİLAY HANIM METNİ)
# ==============================================================================
@router.message(Command("teklif", ignore_mention=True))
@router.message(F.text == "📝 Eliar'dan Teklif Al")
async def start_quote_wizard(msg: types.Message, state: FSMContext):
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

# ADET ALICI: 0 VEYA İPTAL İLE ATLAYIP DEVAM ETME
@router.message(QuoteState.waiting_qty, ~F.text.startswith("/"))
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
        await msg.answer("⚠️ Lütfen sayı girin (Vazgeçmek için <b>0</b> veya <b>iptal</b>):", parse_mode="HTML")
        return

    data = await state.get_data()
    p = data.get("sel_part", {})
    items = data.get("quote_items", [])
    items.append({"code": p.get("code", "KODSUZ"), "name": p.get("name", "Parça"), "qty": qty})
    await state.update_data(quote_items=items)

    await state.set_state(QuoteState.confirm_more)
    await msg.answer(f"✅ <b>{qty} Adet</b> <code>[{p.get('code', 'KODSUZ')}]</code> eklendi!\nNe yapmak istersin?", reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "q_more")
async def on_q_more(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(QuoteState.waiting_item_query)
    await cb.message.edit_text("🔍 Yeni parçanın kodunu veya adını yazın:")

@router.callback_query(F.data == "q_done")
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
    quotes.append({
        "id": f"TK-{int(time.time())}",
        "firm": firm,
        "date": get_now_uz().strftime("%d.%m.%Y %H:%M"),
        "status": "PENDING",
        "items": items,
        "pdf_file": None
    })
    save_quotes(quotes)

    text = f"📋 <b>KOPYALAMAYA HAZIR ELİAR TEKLİF METNİ:</b>\n═══════════════════════════════\n\n<code>{html.escape(fmt)}</code>\n\n═══════════════════════════════\n💡 <i>Metne dokunarak kopyalayabilir, Nilay Hanım'a gönderebilirsin.</i>"
    await cb.message.edit_text(text, parse_mode="HTML")
    await notify_both(f"📥 <b>YENİ TEKLİF TALEBİ:</b> {firm} ({len(items)} kalem)")
    await state.clear()
