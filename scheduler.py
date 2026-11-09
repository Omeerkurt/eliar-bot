import asyncio, os
from aiohttp import web
from config import get_now_uz, notify_both, bot
from database import load_sales

async def automated_scheduler():
    last_week = ""
    while True:
        now = get_now_uz()
        today = now.strftime("%Y-%m-%d")
        # Cumartesi 12:30 Z-Raporu
        if now.weekday() == 5 and now.hour == 12 and now.minute == 30 and last_week != today:
            last_week = today
            sales = [s for s in load_sales() if s.get("status") == "APPROVED"]
            await notify_both(f"📢 <b>HAFTALIK Z-RAPORU (Cumartesi 12:30)</b>\n\nToplam Satış Hareketi: {len(sales)} işlem.")
        await asyncio.sleep(25)

async def start_dummy_server():
    try:
        app = web.Application()
        app.router.add_get('/', lambda r: web.Response(text="Elips Depo Aktif"))
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        await web.TCPSite(runner, '0.0.0.0', port).start()
    except Exception:
        pass
