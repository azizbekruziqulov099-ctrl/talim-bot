from aiogram import Bot, Dispatcher
import os

API_TOKEN = os.getenv(
    "BOT_TOKEN"
)

bot = Bot(
    token=API_TOKEN
)

dp = Dispatcher()
