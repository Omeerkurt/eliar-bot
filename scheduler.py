import asyncio, os, json
from aiohttp import web
from config import get_now_uz, notify_both, bot
from database import load_stocks, save_stocks, load_sales, save_sales

REPAIRS_FILE = "repairs_db.json"

# WebApp'in (GitHub Pages) sunucuyla sorunsuz konuşması için CORS filtresi
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except Exception as e:
            response = web.json_response({"error": str(e)}, status=500)
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# Canlı Stok, Satış ve Tamir Verilerini Telefona Gönderen Uç Nokta
async def handle_get_sync(request):
    repairs = []
    if os.path.exists(REPAIRS_FILE):
        try:
            with open(REPAIRS_FILE, "r", encoding="utf-8") as f:
                repairs = json.load(f)
        except Exception: pass
        
    data = {
        "stocks": load_stocks(),
        "sales": load_sales(),
        "repairs": repairs,
        "server_time": get_now_uz().isoformat()
    }
    return web.json_response(data)

# Telefondaki Değişiklikleri Sunucuya Kalıcı İşleyen Uç Nokta
async def handle_post_sync(request):
    try:
        body = await request.json()
        if "stocks" in body:
            save_stocks(body["stocks"])
        if "sales" in body:
            save_sales(body["sales"])
        if "repairs" in body:
            with open(REPAIRS_FILE, "w", encoding="utf-8") as f:
                json.dump(body["repairs"], f, ensure_ascii=False, indent=2)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def start_dummy_server():
    try:
        app = web.Application(middlewares=[cors_middleware])
        app.router.add_get('/', lambda r: web.Response(text="Elips Depo Aktif"))
        app.router.add_get('/api/sync', handle_get_sync)
        app.router.add_post('/api/sync', handle_post_sync)
        app.router.add_options('/api/sync', lambda r: web.Response(status=200))

        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        await web.TCPSite(runner, '0.0.0.0', port).start()
    except Exception:
        pass

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
