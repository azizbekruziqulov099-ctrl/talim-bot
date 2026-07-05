from aiogram import Bot, Dispatcher
import os

try:
    from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
except:
    pass

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
