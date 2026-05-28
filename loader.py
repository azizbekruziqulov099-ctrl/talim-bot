from aiogram import Bot, Dispatcher, types
import psycopg2
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)
bot = Bot(token=API_TOKEN)

dp = Dispatcher()
