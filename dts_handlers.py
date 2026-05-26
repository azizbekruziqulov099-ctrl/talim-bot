from aiogram import F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import psycopg2

import os

DATABASE_URL = os.getenv("DATABASE_URL")

async def dts_menu(message):

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT grade
        FROM dts_tree
        WHERE track='DTS'
        ORDER BY grade
    """)

    grades = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for grade in grades:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{grade[0]}-sinf",
                callback_data=f"dts_grade_{grade[0]}"
            )
        ])

    await message.answer(
        "📚 DTS sinfni tanlang:",
        reply_markup=kb
    )

    cur.close()
    conn.close()