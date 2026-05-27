from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)

import psycopg2
import os
from keyboards import get_main_keyboard

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

async def dts_admin_menu(
    message
):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📥 DTS import"
                ),
                KeyboardButton(
                    text="📤 DTS export"
                )
            ],
            [
                KeyboardButton(
                    text="🗑 DTS delete"
                ),
                KeyboardButton(
                    text="♻ DTS restore"
                )
            ],
            [
                KeyboardButton(
                    text="📊 DTS statistika"
                )
            ],
            [
                KeyboardButton(
                    text="⬅ Ortga"
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📚 DTS boshqaruvi",
        reply_markup=kb
    )

async def admin_main_menu(
    message: Message
):

    await message.answer(
        "⚙️ Admin menyusi",
        reply_markup=get_main_keyboard(
            "Admin"
        )
    )

async def dts_statistics(
    message: Message
):

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*)
    FROM dts_tree
    """)

    total_topics = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(DISTINCT grade)
    FROM dts_tree
    """)

    grades = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(DISTINCT subject)
    FROM dts_tree
    """)

    subjects = cur.fetchone()[0]

    cur.close()
    conn.close()

    await message.answer(
        f"📊 DTS statistikasi\n\n"
        f"🏫 Sinflar: {grades}\n"
        f"📚 Fanlar: {subjects}\n"
        f"📝 Jami mavzular: {total_topics}"
    )

async def dts_import_menu(
    message: Message,
    admin_state,
    user_id
):

    admin_state[user_id] = "dts_import"

    await message.answer(
        "📄 DTS Excel faylini yuboring"
    )

async def dts_export_menu(
    message: Message
):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📤 Hammasini export"
                )
            ],
            [
                KeyboardButton(
                    text="📤 Sinf bo'yicha"
                ),
                KeyboardButton(
                    text="📤 Fan bo'yicha"
                )
            ],
            [
                KeyboardButton(
                    text="📤 Sinf + fan"
                )
            ],
            [
                KeyboardButton(
                    text="⬅ Ortga"
                )
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "📤 DTS export",
        reply_markup=kb
    )

async def dts_export_all(
    message: Message
):

    await message.answer(
        "📤 DTS export tayyorlanmoqda..."
    )

