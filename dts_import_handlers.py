from aiogram.types import Message
from openpyxl import load_workbook
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

async def dts_import_file(
    message,
    bot,
    user_id
):
    pass

async def dts_import_file(
    message,
    bot,
    user_id
):

    await message.answer(
        "📄 DTS fayl qabul qilindi"
    )

