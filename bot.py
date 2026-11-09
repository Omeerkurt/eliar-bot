import logging, asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, setup_bot_commands
from scheduler import automated_scheduler, start_dummy_server

# Modüler Router'ları İçe Aktar
from handlers.common import router as common_router
from handlers.stock import router as stock_router
from handlers.quotes import router as quotes_router
from handlers.webapp import router as webapp_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Router'ları Sisteme Kaydet
        dp.include_router(common_router)
        dp.include_router(stock_router)
        dp.include_router(quotes_router)
        dp.include_router(webapp_router)

        await bot.set_my_commands([
            types.BotCommand(command="start", description="Ana Menü"),
            types.BotCommand(command="stok", description="Depo Envanteri"),
            types.BotCommand(command="stokekle", description="Stok Ekle / Yeni Tanımla"),
            types.BotCommand(command="stoksil", description="Parça Sil"),
            types.BotCommand(command="teklif", description="Teklif Oluştur"),
            types.BotCommand(command="iptal", description="Açık İşlemi İptal Et")
        ])

        await start_dummy_server()
        asyncio.create_task(automated_scheduler(bot))
        logging.info(">>> ELIPS DEPO BOTU MODÜLER OLARAK AKTİF EDİLDİ <<<")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Hata: {e}")

if __name__ == "__main__":
    from aiogram import types
    asyncio.run(main())