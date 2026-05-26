from aiogram.types import CallbackQuery
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
async def dts_grade(call: CallbackQuery):

    grade = call.data.replace(
        "dts_grade_",
        ""
    )

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute(
        """
        SELECT DISTINCT subject
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        ORDER BY subject
        """,
        (grade,)
    )

    subjects = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for subject in subjects:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=subject[0],
                callback_data=f"dts_subject_{grade}_{subject[0]}"
            )
        ])

    await call.message.edit_text(
        f"{grade}-sinf fanlari",
        reply_markup=kb
    )

    cur.close()
    conn.close()
