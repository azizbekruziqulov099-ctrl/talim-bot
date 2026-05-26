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

async def dts_subject(call):

    _, _, grade, subject = call.data.split("_", 3)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT quarter
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        ORDER BY quarter
    """, (
        grade,
        subject
    ))

    quarters = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for q in quarters:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{q[0]}-chorak",
                callback_data=f"dts_quarter_{grade}_{subject}_{q[0]}")
                ])

    kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="⬅️ Ortga",
                callback_data=f"dts_grade_{grade}"
            )
        ])
        

    await call.message.edit_text(
        f"📚 {subject} fani choragini tanlang:",
        reply_markup=kb
    )

    cur.close()
    conn.close()

async def dts_quarter(call):

    _, _, grade, subject, quarter = call.data.split("_", 4)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
        bob_code,
        bob_name
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        AND quarter=%s
        ORDER BY bob_code
    """, (
        grade,
        subject,
        quarter
    ))

    rows = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for row in rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=row[1],
                callback_data=f"dts_bob_{grade}_{subject}_{quarter}_{row[0]}"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"dts_subject_{grade}_{subject}"
        )
    ])

    await call.message.edit_text(
        f"{quarter}-chorak boblari",
        reply_markup=kb
    )

    cur.close()
    conn.close()

async def dts_bob(call):

    _, _, grade, subject, quarter, bob_code = call.data.split("_", 5)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
        bolim_code,
        bolim_name
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        AND quarter=%s
        AND bob_code=%s
        ORDER BY bolim_code
    """, (
        grade,
        subject,
        quarter,
        bob_code
    ))

    rows = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for row in rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=row[1],
                callback_data=
                f"dts_bolim_{grade}_{subject}_{quarter}_{bob_code}_{row[0]}"
            )
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"dts_quarter_{grade}_{subject}_{quarter}"
        )
    ])
    await call.message.edit_text(
        "Bo'limni tanlang:",
        reply_markup=kb
    )

    cur.close()
    conn.close()

async def dts_bolim(call):

    _, _, grade, subject, quarter, bob_code, bolim_code = call.data.split("_", 6)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
        mavzu_code,
        mavzu_name
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        AND quarter=%s
        AND bob_code=%s
        AND bolim_code=%s
        ORDER BY mavzu_code
    """, (
        grade,
        subject,
        quarter,
        bob_code,
        bolim_code
    ))

    rows = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for row in rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=row[1],
                callback_data=
                f"dts_mavzu_{grade}_{subject}_{quarter}_{bob_code}_{bolim_code}_{row[0]}"
            )
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"dts_bob_{grade}_{subject}_{quarter}_{bob_code}"
        )
    ])
    await call.message.edit_text(
        "Mavzuni tanlang:",
        reply_markup=kb
    )

    cur.close()
    conn.close()

async def dts_mavzu(call):

    _, _, grade, subject, quarter, bob_code, bolim_code, mavzu_code = call.data.split("_", 7)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT
        kichik_mavzu_code,
        kichik_mavzu_name
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        AND quarter=%s
        AND bob_code=%s
        AND bolim_code=%s
        AND mavzu_code=%s
        ORDER BY kichik_mavzu_code
    """, (
        grade,
        subject,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code
    ))

    rows = cur.fetchall()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    for row in rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=row[1],
                callback_data=
                f"dts_small_{grade}_{subject}_{quarter}_{bob_code}_{bolim_code}_{mavzu_code}_{row[0]}"
            )
        ])
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"dts_bolim_{grade}_{subject}_{quarter}_{bob_code}_{bolim_code}"
        )
    ])
    await call.message.edit_text(
        "Kichik mavzuni tanlang:",
        reply_markup=kb
    )

    cur.close()
    conn.close()

async def dts_small(call):

    _, _, grade, subject, quarter, bob_code, bolim_code, mavzu_code, kichik_code = call.data.split("_", 8)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT topic_code,
               kichik_mavzu_name
        FROM dts_tree
        WHERE track='DTS'
        AND grade=%s
        AND subject=%s
        AND quarter=%s
        AND bob_code=%s
        AND bolim_code=%s
        AND mavzu_code=%s
        AND kichik_mavzu_code=%s
        LIMIT 1
    """, (
        grade,
        subject,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code,
        kichik_code
    ))

    row = cur.fetchone()

    if not row:

        await call.answer(
            "Topilmadi"
        )

        return

    topic_code = row[0]
    name = row[1]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Test boshlash",
                    callback_data=f"dts_test_{topic_code}"
                )
            ]
        ]
    )
    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data=f"dts_mavzu_{grade}_{subject}_{quarter}_{bob_code}_{bolim_code}_{mavzu_code}"
        )
    ])
    await call.message.edit_text(
        f"📚 {name}",
        reply_markup=kb
    )

    cur.close()
    conn.close()


