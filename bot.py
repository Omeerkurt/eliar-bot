import logging, asyncio
from aiogram import Dispatcher, types
from config import bot
from scheduler import automated_scheduler, start_dummy_server

# Modüler Router'lar
from handlers.common import router as common_router
from handlers.stock import router as stock_router
from handlers.quotes import router as quotes_router
from handlers.webapp import router as webapp_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
dp = Dispatcher()

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)

        # Modülleri Sisteme Bağla
        dp.include_router(common_router)
        dp.include_router(stock_router)
        dp.include_router(quotes_router)
        dp.include_router(webapp_router)

        # Komut Menüsü
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Ana Menü"),
            types.BotCommand(command="stok", description="Depo Envanteri"),
            types.BotCommand(command="stokekle", description="Stok Ekle / Yeni Tanımla"),
            types.BotCommand(command="stoksil", description="Parça Sil"),
            types.BotCommand(command="teklif", description="Teklif Oluştur"),
            types.BotCommand(command="iptal", description="Açık İşlemi İptal Et")
        ])

        await start_dummy_server()
        asyncio.create_task(automated_scheduler())
        
        logging.info(">>> ELIPS DEPO BOTU MODULER OLARAK AKTIF EDILDI <<<")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Hata: {e}")

if __name__ == "__main__":
    asyncio.run(main())
