import json, html
from aiogram import Router, F, types
from config import OMER_CHAT_ID, get_now_uz, notify_both, bot
import config
from database import load_stocks, save_stocks, load_sales, save_sales, safe_stock_qty

router = Router()

@router.message(F.web_app_data)
async def handle_webapp(msg: types.Message):
    try: p = json.loads(msg.web_app_data.data)
    except Exception: return
    op = p.get("sender") or ("Ömer" if msg.chat.id == OMER_CHAT_ID else "Kamil")
    is_test = bool(p.get("test_mode", False))
    dir_t = p.get("direction")

    if dir_t == "TEST_MODE_TOGGLE":
        config.TEST_MODE = bool(p.get("active", False))
        st_text = "AÇILDI" if config.TEST_MODE else "KAPATILDI"
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
            await notify_both(bot, f"📥 <b>STOK ARTIRILDI</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n📈 <b>+{delta}</b> | Yeni: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>", is_test=is_test)
        elif p.get("action") == "DECREASE":
            dest = p.get("destination", "Bilinmeyen")
            if target: target["qty"] = max(0, safe_stock_qty(target.get("qty", 0)) - delta); new_q = target["qty"]
            else: new_q = safe_stock_qty(p.get("current_qty", 0))
            save_stocks(stocks)
            sales = load_sales()
            sales.append({"id": f"SLS-{int(time.time())}", "firm": dest, "source": "ELIPS_DEPO", "items": [{"code": code, "name": name, "qty": delta}], "status": "APPROVED", "date": get_now_uz().strftime("%d.%m.%Y %H:%M"), "timestamp": get_now_uz().isoformat()})
            save_sales(sales)
            await notify_both(bot, f"📤 <b>STOK ÇIKIŞI / SATIŞ</b>\n🏢 {html.escape(dest)}\n⚙️ <code>[{code}]</code> (-{delta} Adet)\n📉 Kalan: <b>{new_q} ADT</b>\n👷‍♂️ Yapan: <b>{op}</b>", is_test=is_test)

    elif dir_t == "STOCK_DELETE":
        code, name, silent = str(p.get("code") or ""), str(p.get("name") or "İsimsiz"), bool(p.get("silent", False))
        stocks = [s for s in load_stocks() if str(s.get("code", "")).lower() != code.lower()]
        save_stocks(stocks)
        if not silent:
            await notify_both(bot, f"🗑️ <b>PARÇA SİLİNDİ</b>\n⚙️ <code>[{code}]</code> {html.escape(name)}\n👷‍♂️ Yapan: <b>Ömer</b>", is_test=is_test)

    elif dir_t == "REPAIR_UPDATE":
        f_name, model, sn, st, issue = p.get("firm"), p.get("model"), p.get("sn"), p.get("status_text"), p.get("issue")
        await notify_both(
            bot,
            f"🖥️ <b>EKRAN TAMİR GÜNCELLEMESİ</b>\n═══════════════════════════════\n"
            f"🏢 Firma: <b>{html.escape(str(f_name))}</b>\n"
            f"📱 Model: <b>{html.escape(str(model))}</b> (SN: <code>{html.escape(str(sn))}</code>)\n"
            f"⚠️ Arıza: <i>{html.escape(str(issue))}</i>\n"
            f"📍 Durum: <b>{html.escape(str(st))}</b>\n"
            f"👷‍♂️ Güncelleyen: <b>{op}</b>",
            is_test=is_test
        )