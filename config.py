import os, time
from datetime import datetime
from aiogram import Bot
from aiogram.fsm.state import State, StatesGroup

# 1. ÖZBEKİSTAN SAAT DİLİMİ (Asia/Tashkent)
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

# CANLI TOKEN & SABİTLER
BOT_TOKEN = "9212674639:AAE3H17yvghBQmbbq86_kLwI-L5787KzwXQ"
OMER_CHAT_ID = 6915998444
KAMIL_CHAT_ID = 35013468
WEBAPP_URL = "https://omeerkurt.github.io/eliar-depo/"
TEST_MODE = False

STOCKS_FILE = "stocks_db.json"
SALES_FILE = "weekly_sales.json"
QUOTES_FILE = "submitted_quotes.json"
PDF_STORAGE_DIR = "stored_quotes_pdf"
os.makedirs(PDF_STORAGE_DIR, exist_ok=True)

# ORTAK BOT NESNESİ
bot = Bot(token=BOT_TOKEN)

# TÜM MODÜLLERİN KULLANDIĞI ORTAK DURUMLAR (FSM)
class QuoteState(StatesGroup):
    waiting_firm = State()
    waiting_item_query = State()
    waiting_qty = State()
    confirm_more = State()

class StockAddState(StatesGroup):
    waiting_query = State()
    waiting_qty = State()

async def notify_both(text: str, reply_markup=None, is_test=False):
    global TEST_MODE
    recipients = {OMER_CHAT_ID} if (TEST_MODE or is_test) else {OMER_CHAT_ID, KAMIL_CHAT_ID}
    if is_test or TEST_MODE:
        text += "\n\n🧪 <i>[TEST MODU: Kamil'e bildirim gitmedi]</i>"
    for cid in recipients:
        try: await bot.send_message(chat_id=cid, text=text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception: pass
