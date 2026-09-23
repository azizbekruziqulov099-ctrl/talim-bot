from aiogram import Bot, Dispatcher
import os

try:
    from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
except:
    pass

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Install web sign-in before any entry point imports general bot handlers.
from kabutar_web_auth import ensure_kabutar_auth
_kabutar_web_handlers = ensure_kabutar_auth(dp)
