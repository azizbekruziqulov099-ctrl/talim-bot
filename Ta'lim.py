import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from urllib.parse import quote
from aiogram.filters import *
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
import json
import random
import time
import edge_tts
from aiogram.types import FSInputFile
import os

API_TOKEN = os.getenv("BOT_TOKEN")

with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

ADMINS = [401251407]  

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

user_state = {}
temp_user = {}
user_test = {}
user_locks = {}
admin_state = {}
state_history = {}

def set_state(user_id, state):

    user_state[user_id] = state

    if user_id not in state_history:
        state_history[user_id] = []

    state_history[user_id].append(state)

# BUTTON ID (faqat shu bilan ishlaymiz)
BTN_SURVEY = "survey"
BTN_TEST = "test"
BTN_STATS = "stats"

BTN_MY = "my_stats"
BTN_GLOBAL = "global_stats"

SCHOOL_TYPES = [
    "🏫 Oddiy davlat maktabi",
    "⭐ Ixtisoslashgan (IDUM)",
    "🏆 Prezident maktabi",
    "🏢 Xususiy maktab"
]

BACK = "🔙 Ortga"
HOME = "🏠 Bosh menyu"
FINISH = "❌ Testni tugatish"

TEXT_TO_ID = {
    "📊 So‘rovnoma": BTN_SURVEY,
    "📚 BILIMNI SINASH": BTN_TEST,
    "📈 Statistika": BTN_STATS,
    "📊 Mening natijam": BTN_MY,
    "📈 Umumiy statistika": BTN_GLOBAL,
}

CLASSES = [
    "0-sinf",
    "1-sinf",
    "2-sinf",
    "3-sinf",
    "4-sinf",
    "5-sinf",
    "6-sinf",
    "7-sinf",
    "8-sinf",
    "9-sinf",
    "10-sinf",
    "11-sinf"
]

SUBJECTS_BY_LEVEL = {

    "👶 Boshlang‘ich": [
        "Matematika",
        "Ona tili",
        "O‘qish",
        "Tabiiy fan"
    ],

    "📘 O‘rta": [
        "Algebra",
        "Geometriya",
        "Fizika",
        "Kimyo",
        "Biologiya",
        "Tarix",
        "Geografiya"
    ],

    "🎓 Yuqori": [
        "Algebra",
        "Geometriya",
        "Fizika",
        "Kimyo",
        "Biologiya",
        "Huquq",
        "Iqtisod",
        "Informatika"
    ]
}

SUBJECTS_BY_CLASS = {

    "0-sinf": [
        ["🟢 Oson o‘yinlar","🟡 Qiziqarli topshiriqlar"],
        ["🟠 Diqqat sinovi","🔵 Mantiqiy o‘yinlar"],
        ["🟣 Rasmli jumboqlar"]
    ],

    "1-sinf": [
        ["Matematika", "Ona tili", "O‘qish"],
        ["Ingliz tili", "Tabiiy fan", "Tarbiya"],
        ["Musiqa", "Rasm"]
    ],

    "2-sinf": [
        ["Matematika", "Ona tili", "O‘qish"],
        ["Ingliz tili", "Tabiiy fan", "Tarbiya"],
        ["Musiqa", "Rasm"]
    ],

    "3-sinf": [
        ["Matematika", "Ona tili", "O‘qish"],
        ["Ingliz tili", "Tabiiy fan", "Tarbiya"],
        ["Musiqa", "Rasm"]
    ],

    "4-sinf": [
        ["Matematika", "Ona tili", "O‘qish"],
        ["Ingliz tili", "Tabiiy fan", "Tarbiya"],
        ["Musiqa", "Rasm"]
    ],

    "5-sinf": [
        ["Matematika", "Ona tili", "Adabiyot"],
        ["Ingliz tili", "Rus tili", "Tarix"],
        ["Biologiya", "Geografiya", "Informatika"],
        ["Texnologiya"]
    ],

    "6-sinf": [
        ["Matematika", "Ona tili", "Adabiyot"],
        ["Ingliz tili", "Rus tili", "Tarix"],
        ["Biologiya", "Geografiya", "Informatika"],
        ["Texnologiya"]
    ],

    "7-sinf": [
        ["Algebra", "Geometriya", "Fizika"],
        ["Kimyo", "Biologiya", "Tarix"],
        ["Geografiya", "Informatika", "Ingliz tili"],
        ["Ona tili", "Adabiyot"]
    ],

    "8-sinf": [
        ["Algebra", "Geometriya", "Fizika"],
        ["Kimyo", "Biologiya", "Tarix"],
        ["Geografiya", "Informatika", "Ingliz tili"],
        ["Ona tili", "Adabiyot"]
    ],

    "9-sinf": [
        ["Algebra", "Geometriya", "Fizika"],
        ["Kimyo", "Biologiya", "Tarix"],
        ["Geografiya", "Informatika", "Ingliz tili"],
        ["Ona tili", "Adabiyot"]
    ],

    "10-sinf": [
        ["Algebra", "Geometriya", "Fizika"],
        ["Kimyo", "Biologiya", "Tarix"],
        ["Huquq", "Iqtisod", "Geografiya"],
        ["Informatika", "Ingliz tili", "Ona tili"],
        ["Adabiyot"]
    ],

    "11-sinf": [
        ["Algebra", "Geometriya", "Fizika"],
        ["Kimyo", "Biologiya", "Tarix"],
        ["Huquq", "Iqtisod", "Geografiya"],
        ["Informatika", "Ingliz tili", "Ona tili"],
        ["Adabiyot"]
    ]
}

TEST_TYPES = [
    "1-chorak",
    "2-chorak",
    "3-chorak",
    "4-chorak",
    "📘 Yillik",
    "📝 DTS"
]

def base_keyboard(extra=[]):

    keyboard = []
    row = []

    for i, item in enumerate(extra, start=1):

        row.append(KeyboardButton(text=item))

        # har 3 tadan keyin yangi qator
        if i % 4 == 0:
            keyboard.append(row)
            row = []

    # qolganlari
    if row:
        keyboard.append(row)

    # pastki tugmalar
    keyboard.append([KeyboardButton(text=BACK)])
    keyboard.append([KeyboardButton(text=HOME)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def make_keyboard(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in items],
        resize_keyboard=True
    )

def question_nav_keyboard(test):

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➡️"),
                KeyboardButton(text=FINISH)
            ]
        ],
        resize_keyboard=True
    )

def get_main_keyboard(role=None):

    # O‘quvchi menyusi
    if role == "O‘quvchi":
        keyboard = [
            [KeyboardButton(text="📚 BILIMNI SINASH"),
            KeyboardButton(text="📊 Mening natijam")],
            [KeyboardButton(text="🎓 Sinf statistikasi"),
            KeyboardButton(text="🏫 Maktab statistikasi")],
            [KeyboardButton(text="📊 So‘rovnoma"),
            KeyboardButton(text="⚙️ Akkaunt sozlamalari")]
        ]
    # O‘qituvchi menyusi
    elif role == "O‘qituvchi":
            keyboard = [
                [KeyboardButton(text="🧠 Bilimni sinash"),
                KeyboardButton(text="📊 Bilim darajam")],
                [KeyboardButton(text="👨‍🎓 O‘quvchilar natijasi"),
                KeyboardButton(text="🏫 Maktab statistikasi")],
                [KeyboardButton(text="🌍 Viloyat statistikasi"),
                KeyboardButton(text="📊 So‘rovnoma")],
                [KeyboardButton(text="⚙️ Akkaunt sozlamalari")]
            ]
    elif role == "Admin":

        keyboard = [
            [KeyboardButton(text="🇺🇿 Respublika statistikasi"),
            KeyboardButton(text="🌍 Viloyat statistikasi")],
            [KeyboardButton(text="🏫 Maktab statistikasi"),
            KeyboardButton(text="🎓 Sinf statistikasi")],
            [KeyboardButton(text="👨‍🎓 TOP o‘quvchilar"),
            KeyboardButton(text="👨‍🏫 TOP o‘qituvchilar")],
            [KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            KeyboardButton(text="📋 So‘rovnoma natijalari")],
            [KeyboardButton(text="📚 BILIMNI SINASH bazasi")]
        ]
    

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def test_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ Orqaga"), KeyboardButton(text="➡️ Keyingi")]
        ],
        resize_keyboard=True
    )

def get_stats_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Mening natijam")],
            [KeyboardButton(text="📈 Umumiy statistika")],
            [KeyboardButton(text=BACK)],
            [KeyboardButton(text=HOME)]
        ],
        resize_keyboard=True
    )

def check_survey(user_id):

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT survey_done
    FROM users
    WHERE user_id=?
    """, (user_id,))

    row = cursor.fetchone()

    conn.close()

    if not row:
        return False

    return row[0] == 1


def init_db():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        survey_id INTEGER,
        answer TEXT
    )
    """)

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        full_name TEXT,
        role TEXT,
        region TEXT,
        district TEXT,
        school TEXT,
        class TEXT,
        survey_done INTEGER DEFAULT 0
    )
    """)

    # SURVEY
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS surveys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        question TEXT,
        q_type TEXT,
        a TEXT,
        b TEXT,
        c TEXT,
        d TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        class TEXT,
        subject TEXT,
        score INTEGER,
        total INTEGER,
        region TEXT,
        district TEXT,
        school TEXT,
        role TEXT
    )
    """)

    # QUESTIONS

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        class TEXT,
        level TEXT,
        subject TEXT,
        question TEXT,
        a TEXT,
        b TEXT,
        c TEXT,
        d TEXT,
        correct TEXT,
        test_type TEXT,
        difficulty TEXT,
        type TEXT,
        img TEXT,
        voice_type TEXT
    )
    """)

    conn.commit()
    conn.close()

@dp.message(Command("ovoz"))
async def test_ovoz(message: types.Message):

    communicate = edge_tts.Communicate(
        text="Salom Aziz",
        voice="uz-UZ-SardorNeural"
    )

    await communicate.save("temp.mp3")

    await message.answer_voice(
        FSInputFile("temp.mp3")
    )

# ====== START ======
@dp.message(CommandStart())
async def start(message: types.Message):

    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE user_id=?",
        (message.from_user.id,)
    )

    user = cursor.fetchone()
    conn.close()

    # AGAR OLDIN RO‘YXATDAN O‘TGAN BO‘LSA
    if user:

        role = user[0]

        if message.from_user.id in ADMINS:
            role = "Admin"

        await message.answer(
            f"Qaytganingiz bilan 😊\nSiz: {role}",
            reply_markup=get_main_keyboard(role)
        )

        return
    # AGAR YANGI USER BO‘LSA
    user_state[message.from_user.id] = "role"

    await message.answer(
        "Kim siz?",
        reply_markup=make_keyboard(["O‘quvchi", "O‘qituvchi"])
    )

@dp.message()
async def handle_all(message: types.Message):
    user_id = message.from_user.id

    # lock yaratish
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    # parallel message bloklash
    async with user_locks[user_id]:

        action = TEXT_TO_ID.get(message.text)

        # 🔙 ORTGA
        if message.text == BACK:

            user_id = message.from_user.id

            # history bo‘lsa
            if user_id in state_history and len(state_history[user_id]) > 1:

                # hozirgi state ni olib tashlash
                state_history[user_id].pop()

                # oldingi state
                prev_state = state_history[user_id][-1]

                user_state[user_id] = prev_state

                # CLASS ga qaytish
                if prev_state == "class":

                    await message.answer(
                        "Sinf tanlang:",
                        reply_markup=base_keyboard(CLASSES)
                    )
                    return

                # SUBJECT ga qaytish
                elif prev_state == "subject":

                    selected_class = temp_user[user_id]["class"]

                    subjects = SUBJECTS_BY_CLASS.get(selected_class)

                    flat_subjects = []

                    for row in subjects:
                        flat_subjects.extend(row)

                    await message.answer(
                        "Fan tanlang:",
                        reply_markup=base_keyboard(flat_subjects)
                    )
                    return

            # history yo‘q bo‘lsa
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT role FROM users
            WHERE user_id=?
            """, (user_id,))

            user = cursor.fetchone()
            conn.close()

            role = user[0] if user else None

            user_state[user_id] = None

            await message.answer(
                "🏠 Bosh menyu",
                reply_markup=get_main_keyboard(role)
            )

            return

        # ===== TEACHER TEST =====
        elif message.text == "🧠 Bilimni sinash":

            temp_user[message.from_user.id] = {
                "role": "O‘qituvchi"
            }

            user_state[message.from_user.id] = "teacher_level"

            await message.answer(
                "Yo‘nalishni tanlang:",
                reply_markup=base_keyboard([
                    "👶 Boshlang‘ich",
                    "📘 O‘rta",
                    "🎓 Yuqori"
                ])
            )

            return

        # ===== TEST BAZASI =====
        elif message.text == "📚 BILIMNI SINASH bazasi":

            if message.from_user.id not in ADMINS:
                return

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            text = "📚 BILIMNI SINASH bazasi\n"

            # ===== O'QUVCHI =====
            for cls in CLASSES:

                subjects = SUBJECTS_BY_CLASS.get(cls, [])

                flat_subjects = []

                for row in subjects:
                    flat_subjects.extend(row)

                row_text = []

                for subject in flat_subjects:

                    cursor.execute("""
                    SELECT COUNT(*)
                    FROM questions
                    WHERE class=? AND subject=?
                    """, (cls, subject))

                    count = cursor.fetchone()[0]

                    short = subject[:4]

                    row_text.append(f"{short}:{count}")

                text += f"\n\n🎓 {cls}\n"
                text += " ".join(row_text)

            # ===== O'QITUVCHI =====
            text += "\n\n━━━━━━━━━━\n"
            text += "👨‍🏫 O‘QITUVCHI\n"

            for level, subjects in SUBJECTS_BY_LEVEL.items():

                row_text = []

                for subject in subjects:

                    cursor.execute("""
                    SELECT COUNT(*)
                    FROM questions
                    WHERE level=? AND subject=?
                    """, (level, subject))

                    count = cursor.fetchone()[0]

                    short = subject[:4]

                    row_text.append(f"{short}:{count}")

                text += f"\n\n{level}\n"
                text += " ".join(row_text)

            # ===== SO'ROVNOMA =====
            cursor.execute("""
            SELECT COUNT(*)
            FROM surveys
            """)

            survey_count = cursor.fetchone()[0]

            text += (
                f"\n\n━━━━━━━━━━\n"
                f"📋 So‘rovnoma: {survey_count} ta"
            )

            conn.close()

            await message.answer(text)

            return

        elif message.text == "/addsurvey" and message.from_user.id in ADMINS:

            admin_state[message.from_user.id] = "survey_add"

            await message.answer(
                "Survey yuboring"
            )

            return

        elif admin_state.get(message.from_user.id) == "survey_add":

            text = message.text.strip()

            blocks = text.replace("\r", "").split("\n\n")

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            count = 0

            for block in blocks:

                lines = [
                    l.strip().replace("\r", "")
                    for l in block.split("\n")
                    if l.strip()
                ]

                if len(lines) < 7:
                    continue

                try:

                    role = lines[0].replace("ROLE:", "").strip()
                    question = lines[1].replace("QUESTION:", "").strip()
                    q_type = lines[2].replace("TYPE:", "").strip()

                    a = lines[3].replace("A:", "").strip()
                    b = lines[4].replace("B:", "").strip()
                    c = lines[5].replace("C:", "").strip()
                    d = lines[6].replace("D:", "").strip()

                    cursor.execute("""
                    INSERT INTO surveys (
                        role,
                        question,
                        q_type,
                        a,
                        b,
                        c,
                        d
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        role,
                        question,
                        q_type,
                        a,
                        b,
                        c,
                        d
                    ))

                    count += 1

                except Exception as e:
                    print(e)

            conn.commit()
            conn.close()

            admin_state[message.from_user.id] = None

            await message.answer(
                f"✅ {count} ta survey qo‘shildi"
            )

            return

    # ===== ADMIN MAKTAB =====
        elif message.text == "🏫 Maktab statistikasi":

            if message.from_user.id not in ADMINS:
                return

            user_state[message.from_user.id] = "admin_region"

            await message.answer(
                "Viloyat tanlang:",
                reply_markup=base_keyboard(REGIONS.keys())
            )

            return

        # ===== SURVEY RESULTS =====
        elif message.text == "📋 So‘rovnoma natijalari":

            if message.from_user.id not in ADMINS:
                return

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT surveys.question,
            survey_answers.answer,
            COUNT(*)
            FROM survey_answers
            JOIN surveys
            ON surveys.id = survey_answers.survey_id
            GROUP BY surveys.question, survey_answers.answer
            """)

            rows = cursor.fetchall()

            conn.close()

            if not rows:

                await message.answer(
                    "❌ Natijalar yo‘q"
                )
                return

            text = "📋 So‘rovnoma natijalari\n\n"

            current_question = ""

            for question, answer, count in rows:

                if question != current_question:

                    current_question = question

                    text += f"\n📝 {question}\n"

                text += f"• {answer} — {count} ta\n"

            await message.answer(text)

            return

        elif user_state.get(message.from_user.id) == "admin_region":

            temp_user[message.from_user.id]["admin_region"] = message.text

            districts = REGIONS.get(message.text, [])

            flat = []

            for row in districts:
                flat.extend(row)

            user_state[message.from_user.id] = "admin_district"

            await message.answer(
                "Tuman tanlang:",
                reply_markup=base_keyboard(flat)
            )

            return

        elif user_state.get(message.from_user.id) == "admin_district":

            temp_user[message.from_user.id]["admin_district"] = message.text

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT DISTINCT school
            FROM users
            WHERE district=?
            """, (message.text,))

            rows = cursor.fetchall()

            conn.close()

            schools = [r[0] for r in rows if r[0]]

            user_state[message.from_user.id] = "admin_school"

            await message.answer(
                "Maktab tanlang:",
                reply_markup=base_keyboard(schools)
            )

            return

        elif user_state.get(message.from_user.id) == "admin_school":

            school = message.text

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE school=?
            """, (school,))

            avg = cursor.fetchone()[0]

            conn.close()

            if avg is None:

                await message.answer(
                    "❌ Ma’lumot yo‘q"
                )
                return

            avg = round(avg, 1)

            bar = "█" * int(avg // 10)
            empty = "░" * (10 - int(avg // 10))

            text = (
                f"🏫 {school}\n\n"
                f"{bar}{empty}\n"
                f"📊 O‘rtacha: {avg}%"
            )

            await message.answer(text)

            user_state[message.from_user.id] = None

            return

        elif user_state.get(message.from_user.id) == "teacher_level":

            temp_user[message.from_user.id]["teacher_level"] = message.text

            subjects = SUBJECTS_BY_LEVEL.get(message.text, [])

            user_state[message.from_user.id] = "teacher_subject"

            await message.answer(
                "Fan tanlang:",
                reply_markup=base_keyboard(subjects)
            )

            return

        elif user_state.get(message.from_user.id) == "teacher_subject":

            temp_user[message.from_user.id]["subject"] = message.text

            user_state[message.from_user.id] = "test_type"

            await message.answer(
                "Test turini tanlang:",
                reply_markup=base_keyboard(TEST_TYPES)
            )

            return

        # 🏠 HOME
        elif message.text == HOME:

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT role FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            user = cursor.fetchone()
            conn.close()

            role = user[0] if user else None

            user_state[message.from_user.id] = None

            await message.answer(
                "🏠 Bosh menyu",
                reply_markup=get_main_keyboard(role)
            )
            return

        # ===== O'QITUVCHI BILIM DARAJASI =====
        elif message.text == "📊 Bilim darajam":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT subject,
            AVG(score * 100.0 / total)
            FROM results
            WHERE user_id=?
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cursor.fetchall()

            conn.close()

            if not rows:

                await message.answer(
                    "❌ Hali test ishlamagansiz"
                )
                return

            text = "🧠 Bilim darajangiz\n\n"

            total_avg = 0

            for subject, avg in rows:

                avg = round(avg, 1)

                total_avg += avg

                bar = "█" * int(avg // 10)
                empty = "░" * (10 - int(avg // 10))

                text += (
                    f"📘 {subject}\n"
                    f"{bar}{empty} {avg}%\n\n"
                )

            overall = round(total_avg / len(rows), 1)

            text += f"🎯 Umumiy bilim darajasi: {overall}%"

            await message.answer(text)

            return

        # ===== O'QUVCHILAR NATIJASI =====
        elif message.text == "👨‍🎓 O‘quvchilar natijasi":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE role='O‘quvchi'
            """)

            avg = cursor.fetchone()[0]

            conn.close()

            if avg is None:

                await message.answer(
                    "❌ Ma’lumot yo‘q"
                )
                return

            avg = round(avg, 1)

            bar = "█" * int(avg // 10)
            empty = "░" * (10 - int(avg // 10))

            text = (
                "👨‍🎓 O‘quvchilar natijasi\n\n"
                f"{bar}{empty}\n"
                f"📊 O‘rtacha: {avg}%"
            )

            await message.answer(text)

            return

        # ===== VILOYAT =====
        elif message.text == "🌍 Viloyat statistikasi":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT region FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            row = cursor.fetchone()

            if not row:
                conn.close()
                return

            region = row[0]

            cursor.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE region=?
            """, (region,))

            avg = cursor.fetchone()[0]

            conn.close()

            if avg is None:

                await message.answer(
                    "❌ Ma’lumot yo‘q"
                )
                return

            avg = round(avg, 1)

            bar = "█" * int(avg // 10)
            empty = "░" * (10 - int(avg // 10))

            text = (
                f"🌍 {region} statistikasi\n\n"
                f"{bar}{empty}\n"
                f"📊 O‘rtacha: {avg}%"
            )

            await message.answer(text)

            return

        # ===== RESPUBLIKA =====
        elif message.text == "🇺🇿 Respublika statistikasi":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            """)

            avg = cursor.fetchone()[0]

            conn.close()

            if avg is None:

                await message.answer(
                    "❌ Ma’lumot yo‘q"
                )
                return

            avg = round(avg, 1)

            bar = "█" * int(avg // 10)
            empty = "░" * (10 - int(avg // 10))

            text = (
                "🇺🇿 Respublika statistikasi\n\n"
                f"{bar}{empty}\n"
                f"📊 O‘rtacha: {avg}%"
            )

            await message.answer(text)

            return

        # ===== MENING NATIJAM =====
        elif message.text == "📊 Mening natijam":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT subject,
            AVG(score * 100.0 / total)
            FROM results
            WHERE user_id=?
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cursor.fetchall()

            conn.close()

            if not check_survey(message.from_user.id):

                await message.answer(
                    "❌ Avval so‘rovnomadan o‘ting."
                )

                return

            if not rows:

                await message.answer(
                    "❌ Hali natija yo‘q"
                )
                return

            text = "📊 Sizning natijalaringiz\n\n"

            total_avg = 0

            for subject, avg in rows:

                avg = round(avg, 1)

                total_avg += avg

                bar = "█" * int(avg // 10)
                empty = "░" * (10 - int(avg // 10))

                text += (
                    f"📘 {subject}\n"
                    f"{bar}{empty} {avg}%\n\n"
                )

            overall = round(total_avg / len(rows), 1)

            text += f"🎯 Umumiy o‘zlashtirish: {overall}%"

            await message.answer(text)

            return

        # ===== MAKTAB STATISTIKASI =====
        elif message.text == "🏫 Maktab statistikasi":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT school FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            row = cursor.fetchone()

            if not row:
                await message.answer("❌ Maktab topilmadi")
                conn.close()
                return

            school = row[0]

            cursor.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE school=?
            """, (school,))

            avg = cursor.fetchone()[0]

            conn.close()

            if avg is None:
                await message.answer("❌ Ma’lumot yo‘q")
                return

            avg = round(avg, 1)

            bar = "█" * int(avg // 10)
            empty = "░" * (10 - int(avg // 10))

            text = (
                f"🏫 Maktab statistikasi\n\n"
                f"{bar}{empty}\n"
                f"📊 O‘rtacha: {avg}%"
            )

            await message.answer(text)

            return



        elif message.text == "⚙️ Akkaunt sozlamalari":

            await message.answer(
                "Sozlamalar:",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="🔄 Rolni almashtirish")],
                        [KeyboardButton(text="🌍 Hududni almashtirish")],
                        [KeyboardButton(text="🏫 Maktabni almashtirish")],
                        [KeyboardButton(text="🎓 Sinfni almashtirish")],
                        [KeyboardButton(text=BACK)]
                    ],
                    resize_keyboard=True
                )
            )
        elif message.text == "🔄 Rolni almashtirish":

            user_state[message.from_user.id] = "change_role"

            await message.answer(
                "Yangi rolni tanlang:",
                reply_markup=make_keyboard(["O‘quvchi", "O‘qituvchi"])
            )

        elif user_state.get(message.from_user.id) == "change_role":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE users
            SET role=?
            WHERE user_id=?
            """, (
                message.text,
                message.from_user.id
            ))

            conn.commit()
            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                f"✅ Rol o‘zgartirildi: {message.text}",
                reply_markup=get_main_keyboard(message.text)
            )

        elif message.text == "🌍 Hududni almashtirish":

            user_state[message.from_user.id] = "change_region"

            await message.answer(
                "Viloyatni tanlang:",
                reply_markup=make_keyboard(REGIONS.keys())
            )

            return


        elif user_state.get(message.from_user.id) == "change_region":

            temp_user[message.from_user.id] = {
                "new_region": message.text
            }

            districts = REGIONS.get(message.text, [])

            flat = []

            for row in districts:
                flat.extend(row)

            user_state[message.from_user.id] = "change_district"

            await message.answer(
                "Tumanni tanlang:",
                reply_markup=base_keyboard(flat)
            )

            return


        elif user_state.get(message.from_user.id) == "change_district":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE users
            SET region=?, district=?
            WHERE user_id=?
            """, (
                temp_user[message.from_user.id]["new_region"],
                message.text,
                message.from_user.id
            ))

            conn.commit()

            cursor.execute(
                "SELECT role FROM users WHERE user_id=?",
                (message.from_user.id,)
            )

            role = cursor.fetchone()[0]

            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                "✅ Hudud o‘zgartirildi",
                reply_markup=get_main_keyboard(role)
            )

            return
        # ===== MAKTABNI ALMASHTIRISH =====

        elif message.text == "🏫 Maktabni almashtirish":

            user_state[message.from_user.id] = "change_school"

            await message.answer(
                "Yangi maktab nomi yoki raqamini kiriting:"
            )

            return

        elif user_state.get(message.from_user.id) == "change_school":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE users
            SET school=?
            WHERE user_id=?
            """, (
                message.text,
                message.from_user.id
            ))

            conn.commit()
            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                f"✅ Maktab o‘zgartirildi: {message.text}",
                reply_markup=get_main_keyboard(
                    temp_user[message.from_user.id]["role"]
                )
            )

            return

        # ===== SINFNI ALMASHTIRISH =====
        elif message.text == "🎓 Sinfni almashtirish":

            user_state[message.from_user.id] = "change_class"

            await message.answer(
                "Yangi sinfni tanlang:",
                reply_markup=base_keyboard(CLASSES)
            )

            return

        elif user_state.get(message.from_user.id) == "change_class":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            UPDATE users
            SET class=?
            WHERE user_id=?
            """, (
                message.text,
                message.from_user.id
            ))

            conn.commit()

            cursor.execute("""
            SELECT role FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            row = cursor.fetchone()

            conn.close()

            role = row[0] if row else "O‘quvchi"

            user_state[message.from_user.id] = None

            await message.answer(
                f"✅ Sinf o‘zgartirildi: {message.text}",
                reply_markup=get_main_keyboard(role)
            )

            return

        # ===== ADMIN =====
        elif message.text == "/admin" and message.from_user.id in ADMINS:
            admin_state[message.from_user.id] = "bulk"
            await message.answer("Testlarni yuboring (bulk formatda)")
            return

        elif user_state.get(message.from_user.id) == "role":
            temp_user[message.from_user.id] = {"role": message.text}
            user_state[message.from_user.id] = "region"

            await message.answer(
                "Viloyat tanlang:",
                reply_markup=base_keyboard(REGIONS.keys())
            )

        # ===== REGION =====
        elif user_state.get(message.from_user.id) == "region":
            temp_user[message.from_user.id]["region"] = message.text
            user_state[message.from_user.id] = "district"

            districts = REGIONS.get(message.text, [])

            flat_districts = []

            for row in districts:
                flat_districts.extend(row)

            await message.answer(
                "Tuman tanlang:",
                reply_markup=base_keyboard(flat_districts)
            )
    
        # ===== CLASS ===
        elif user_state.get(message.from_user.id) == "class":

            # sinfni saqlash
            selected_class = message.text.strip()

            temp_user[message.from_user.id]["class"] = selected_class

            # keyingi bosqich
            set_state(message.from_user.id, "subject")

            # shu sinfga mos fanlarni olish
            subjects = SUBJECTS_BY_CLASS.get(selected_class)

            # agar topilmasa
            if not subjects:
                await message.answer("Fan topilmadi ❌")
                return

            # nested list -> oddiy list
            flat_subjects = []

            for row in subjects:
                flat_subjects.extend(row)

            # fanlarni chiqarish
            await message.answer(
                "Fan tanlang:",
                reply_markup=base_keyboard(flat_subjects)
            )

            return
        
        # ===== SUBJECT =====
        elif user_state.get(message.from_user.id) == "subject":

            # fan saqlash
            temp_user[message.from_user.id]["subject"] = message.text

            # keyingi state
            set_state(message.from_user.id, "test_type")

            # test turi tanlash
            await message.answer(
                "Test turini tanlang:",
                reply_markup=base_keyboard(TEST_TYPES)
            )

            return

        elif user_state.get(message.from_user.id) == "test":

            if message.text not in ["➡️", "❌ Testni tugatish"]:
                await message.answer(
                    "👇 Javobni faqat tugmalar orqali tanlang."
                )
                return

            test = user_test[message.from_user.id]

            # TESTNI TUGATISH
            if message.text == FINISH:

                score = test["score"]
                total = len(test["questions"])

                await message.answer(
                    f"🏁 Test tugatildi\n\n"
                    f"📊 Natija: {score}/{total}",
                    reply_markup=get_main_keyboard(
                        temp_user[message.from_user.id]["role"]
                    )
                )

                user_state[message.from_user.id] = None
                user_test.pop(message.from_user.id, None)

                return

            # KEYINGI SAVOL
            if message.text == "➡️":

                # oxirgi savol bo‘lmasa
                if test["index"] < len(test["questions"]) - 1:

                    test["index"] += 1

                else:

                    await message.answer(
                        "❌ Oxirgi savol"
                    )

                    return

                test["question_start"] = time.time()
                test["question_uid"] = random.randint(100000,999999)
                test["expired"] = False
                test["answered"] = False

                q = test["questions"][test["index"]]

                difficulty = q[12]

                limit = 60

                if difficulty == "medium":
                    limit = 90

                elif difficulty == "hard":
                    limit = 120
                if q[14]:

                    await bot.send_photo(
                        message.chat.id,
                        photo=FSInputFile(
                            f"images/{q[14]}"
                        )
                    )
                # LATEX
                if q[13] and "latex" in str(q[13]).lower():

                    latex = q[5]

                    encoded = quote(f"\\dpi{{300}} \\huge {latex}")

                    url = f"https://latex.codecogs.com/png.image?{encoded}"

                    await bot.send_photo(
                        message.chat.id,
                        photo=url
                    )
                    markup = InlineKeyboardMarkup(
                        inline_keyboard=[

                            [
                                InlineKeyboardButton(
                                    text="🔊 Savol",
                                    callback_data="listen_q"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 A",
                                    callback_data="listen_a"
                                ),
                                InlineKeyboardButton(
                                    text=q[6],
                                    callback_data="a"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 B",
                                    callback_data="listen_b"
                                ),
                                InlineKeyboardButton(
                                    text=q[7],
                                    callback_data="b"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 C",
                                    callback_data="listen_c"
                                ),
                                InlineKeyboardButton(
                                    text=q[8],
                                    callback_data="c"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 D",
                                    callback_data="listen_d"
                                ),
                                InlineKeyboardButton(
                                    text=q[9],
                                    callback_data="d"
                                )
                            ]
                        ]
                    )

                    text = "⬆️ Savol yuqoridagi rasmda"
                else:
                    text = q[5]

                    markup = InlineKeyboardMarkup(
                        inline_keyboard=[

                            [
                                InlineKeyboardButton(
                                    text="🔊 Savol",
                                    callback_data="listen_q"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 A",
                                    callback_data="listen_a"
                                ),
                                InlineKeyboardButton(
                                    text=q[6],
                                    callback_data="a"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 B",
                                    callback_data="listen_b"
                                ),
                                InlineKeyboardButton(
                                    text=q[7],
                                    callback_data="b"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 C",
                                    callback_data="listen_c"
                                ),
                                InlineKeyboardButton(
                                    text=q[8],
                                    callback_data="c"
                                )
                            ],

                            [
                                InlineKeyboardButton(
                                    text="🔊 D",
                                    callback_data="listen_d"
                                ),
                                InlineKeyboardButton(
                                    text=q[9],
                                    callback_data="d"
                                )
                            ]
                        ]
                    )
                msg = await bot.send_message(
                    message.chat.id,
                    text,
                    reply_markup=markup
                )

            
                if q[15] in ["uz", "ru", "en"]:

                    voice = "uz-UZ-SardorNeural"

                    if q[15] == "ru":
                        voice = "ru-RU-DmitryNeural"

                    elif q[15] == "en":
                        voice = "en-US-GuyNeural"

                    communicate = edge_tts.Communicate(
                        text=q[5],
                        voice=voice
                    )

                    await communicate.save("temp.mp3")

                #    await bot.send_voice(
                  #      message.chat.id,
                  #      voice=FSInputFile("temp.mp3")
                 #   )

                    

                # eski countdownni o‘chirish
                if test.get("countdown_task"):
                    test["countdown_task"].cancel()

                # eski timerni o‘chirish
                if test.get("timer_task"):
                    test["timer_task"].cancel()
                test["expired"] = False
                test["answered"] = False

                # eski timerni o‘chirish
                old_task = test.get("timer_task")

                if old_task:
                    old_task.cancel()

                test["timer_task"] = asyncio.create_task(
                    question_timer(message.from_user.id, limit)
                )
                test["msg_id"] = msg.message_id

                return

            user_id = message.from_user.id

            test = user_test[user_id]

            if test.get("expired"):
                return

            if test.get("answered"):
                return

            test["answered"] = True

            q = test["questions"][test["index"]]

            difficulty = q[12]

            limit = 60

            if difficulty == "medium":
                limit = 90

            elif difficulty == "hard":
                limit = 120

            user_ans = message.text.lower()

            correct = q[10].lower()
            # eski timerlarni to‘xtatish
            try:
                if test.get("countdown_task"):
                    test["countdown_task"].cancel()
            except:
                pass

            try:
                if test.get("timer_task"):
                    test["timer_task"].cancel()
            except:
                pass
            if user_ans == correct:

                result_text = "✅ To‘g‘ri"
                test["score"] += 1

            else:

                result_text = (
                    f"❌ Noto‘g‘ri\n"
                    f"To‘g‘ri javob: {correct.upper()}"
                )

            # OXIRGI SAVOL
            if test["index"] >= len(test["questions"]) - 1:

                score = test["score"]
                total = len(test["questions"])

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()

                cursor.execute("""
                INSERT INTO results (
                    user_id,
                    class,
                    subject,
                    score,
                    total,
                    region,
                    district,
                    school,
                    role
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    temp_user[user_id].get("class"),
                    temp_user[user_id].get("subject"),
                    score,
                    total,
                    temp_user[user_id].get("region"),
                    temp_user[user_id].get("district"),
                    temp_user[user_id].get("school"),
                    temp_user[user_id].get("role")
                ))

                conn.commit()
                conn.close()

                await message.answer(
                    f"{result_text}\n\n"
                    f"🏁 Test tugadi\n"
                    f"📊 Natija: {score}/{total}"
                )

                await message.answer(
                    "🏠 Bosh menyu",
                    reply_markup=get_main_keyboard(
                        temp_user[user_id]["role"]
                    )
                )

                user_state[user_id] = None
                user_test.pop(user_id, None)

                return

            # KEYINGI SAVOL
            test["index"] += 1

            test["question_start"] = time.time()
            test["question_uid"] = random.randint(100000,999999)
            test["expired"] = False
            test["answered"] = False

            q = test["questions"][test["index"]]

            if q[14]:
                await bot.send_photo(
                    message.chat.id,
                    photo=FSInputFile(
                        f"images/{q[14]}"
                    )
                )

            difficulty = q[12]

            limit = 60

            if difficulty == "medium":
                limit = 90

            elif difficulty == "hard":
                limit = 120

                # LATEX
            if q[13] and "latex" in str(q[13]).lower():

                latex = q[5]

                encoded = quote(f"\\dpi{{300}} \\huge {latex}")

                url = f"https://latex.codecogs.com/png.image?{encoded}"

                await bot.send_photo(
                    message.chat.id,
                    photo=url
                )
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[

                        [
                            InlineKeyboardButton(
                                text="🔊 Savol",
                                callback_data="listen_q"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 A",
                                callback_data="listen_a"
                            ),
                            InlineKeyboardButton(
                                text=q[6],
                                callback_data="a"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 B",
                                callback_data="listen_b"
                            ),
                            InlineKeyboardButton(
                                text=q[7],
                                callback_data="b"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 C",
                                callback_data="listen_c"
                            ),
                            InlineKeyboardButton(
                                text=q[8],
                                callback_data="c"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 D",
                                callback_data="listen_d"
                            ),
                            InlineKeyboardButton(
                                text=q[9],
                                callback_data="d"
                            )
                        ]
                    ]
                )

            else:

                text = q[5]
                
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[

                        [
                            InlineKeyboardButton(
                                text="🔊 Savol",
                                callback_data="listen_q"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 A",
                                callback_data="listen_a"
                            ),
                            InlineKeyboardButton(
                                text=q[6],
                                callback_data="a"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 B",
                                callback_data="listen_b"
                            ),
                            InlineKeyboardButton(
                                text=q[7],
                                callback_data="b"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 C",
                                callback_data="listen_c"
                            ),
                            InlineKeyboardButton(
                                text=q[8],
                                callback_data="c"
                            )
                        ],

                        [
                            InlineKeyboardButton(
                                text="🔊 D",
                                callback_data="listen_d"
                            ),
                            InlineKeyboardButton(
                                text=q[9],
                                callback_data="d"
                            )
                        ]
                    ]
                )
            msg = await bot.send_message(
                message.chat.id,
                f"{result_text}\n\n{text}",
                reply_markup=markup
            )
            
            if q[15] in ["uz", "ru", "en"]:

                voice = "uz-UZ-SardorNeural"

                if q[15] == "ru":
                    voice = "ru-RU-DmitryNeural"

                elif q[15] == "en":
                    voice = "en-US-GuyNeural"

                communicate = edge_tts.Communicate(
                    text=q[5],
                    voice=voice
                )

                await communicate.save("temp.mp3")

          #      await bot.send_voice(
           #         message.chat.id,
            #        voice=FSInputFile("temp.mp3")
             #   )




            # eski countdownni o‘chirish
            if test.get("countdown_task"):
                test["countdown_task"].cancel()

            # eski timerni o‘chirish
            if test.get("timer_task"):
                test["timer_task"].cancel()
            test["expired"] = False
            test["answered"] = False

            # eski timerni o‘chirish
            old_task = test.get("timer_task")

            if old_task:
                old_task.cancel()

            test["timer_task"] = asyncio.create_task(
                question_timer(user_id, limit)
            )

            test["msg_id"] = msg.message_id

            return


        # ===== TEST TYPE =====
        elif user_state.get(message.from_user.id) == "test_type":

            temp_user[message.from_user.id]["test_type"] = message.text

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            # O‘qituvchi
            if temp_user[message.from_user.id]["role"] == "O‘qituvchi":

                questions = []

                selected_level = temp_user[message.from_user.id]["teacher_level"]
                subject = temp_user[message.from_user.id]["subject"]
                test_type = temp_user[message.from_user.id]["test_type"]

                # EASY
                cursor.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=?
                AND subject=?
                AND test_type=?
                AND difficulty='easy'
                ORDER BY RANDOM()
                LIMIT 10
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cursor.fetchall())

                # MEDIUM
                cursor.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=?
                AND subject=?
                AND test_type=?
                AND difficulty='medium'
                ORDER BY RANDOM()
                LIMIT 7
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cursor.fetchall())

                # HARD
                cursor.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=?
                AND subject=?
                AND test_type=?
                AND difficulty='hard'
                ORDER BY RANDOM()
                LIMIT 3
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cursor.fetchall())
            # O‘quvchi
            else:

                cursor.execute("""
                SELECT * FROM questions
                WHERE role='O‘quvchi'
                AND class=?
                AND subject=?
                AND test_type=?
                ORDER BY RANDOM()
                LIMIT 20
                """, (
                    temp_user[message.from_user.id]["class"],
                    temp_user[message.from_user.id]["subject"],
                    temp_user[message.from_user.id]["test_type"]
                ))

                questions = cursor.fetchall()

            conn.close()

            if not questions:
                await message.answer("Test topilmadi ❌")
                return

            user_test[message.from_user.id] = {
                "questions": questions,
                "index": 0,
                "score": 0,
                "answers": {},
                "question_start": time.time(),
                "expired": False,
                "answered": False,
                "timer_task": None,
                "countdown_task": None,
                "question_uid": random.randint(100000,999999),
            }
            test = user_test[message.from_user.id]

            user_state[message.from_user.id] = "test"

            q = questions[0]

            voice_type = q[15]
            difficulty = q[12]

            limit = 60

            if difficulty == "medium":
                limit = 90

            elif difficulty == "hard":
                limit = 120

            # LATEX SAVOL
            # RASM
            if q[14]:
                await bot.send_photo(
                    message.chat.id,
                    photo=FSInputFile(f"images/{q[14]}")
                )

            # LATEX
            if q[13] and "latex" in str(q[13]).lower():

                latex = q[5]

                encoded = quote(
                    f"\\dpi{{300}} \\huge {latex}"
                )

                url = f"https://latex.codecogs.com/png.image?{encoded}"

                await bot.send_photo(
                    message.chat.id,
                    photo=url
                )

                text = "Savol rasmi yuqorida ⬆️"

            else:
                text = q[5]

            markup = InlineKeyboardMarkup(
                inline_keyboard=[

                    [
                        InlineKeyboardButton(
                            text="🔊 Savol",
                            callback_data="listen_q"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 A",
                            callback_data="listen_a"
                        ),
                        InlineKeyboardButton(
                            text=q[6],
                            callback_data="a"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 B",
                            callback_data="listen_b"
                        ),
                        InlineKeyboardButton(
                            text=q[7],
                            callback_data="b"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 C",
                            callback_data="listen_c"
                        ),
                        InlineKeyboardButton(
                            text=q[8],
                            callback_data="c"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 D",
                            callback_data="listen_d"
                        ),
                        InlineKeyboardButton(
                            text=q[9],
                            callback_data="d"
                        )
                    ]
                ]
            )
            msg = await bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup
            )
           
            if q[15] in ["uz", "ru", "en"]:

                voice = "uz-UZ-SardorNeural"

                if q[15] == "ru":
                    voice = "ru-RU-DmitryNeural"

                elif q[15] == "en":
                    voice = "en-US-GuyNeural"

                communicate = edge_tts.Communicate(
                    text=q[5],
                    voice=voice
                )

                await communicate.save("temp.mp3")

             #   await bot.send_voice(
              #      message.chat.id,
               #     voice=FSInputFile("temp.mp3")
           #     )

            # eski countdownni o‘chirish
            if test.get("countdown_task"):
                test["countdown_task"].cancel()

            # eski timerni o‘chirish
            if test.get("timer_task"):
                test["timer_task"].cancel()

            test["expired"] = False
            test["answered"] = False

            # eski timerni o‘chirish
            old_task = test.get("timer_task")

            if old_task:
                old_task.cancel()

            test["timer_task"] = asyncio.create_task(
                question_timer(message.from_user.id, limit)
            )

            user_test[message.from_user.id]["msg_id"] = msg.message_id

            return

        elif user_state.get(message.from_user.id) == "school":

            temp_user[message.from_user.id]["school"] = message.text

            # agar o‘quvchi bo‘lsa sinf tanlaydi
            if temp_user[message.from_user.id]["role"] == "O‘quvchi":

                user_state[message.from_user.id] = "class_register"

                await message.answer(
                    "Sinf tanlang:",
                    reply_markup=base_keyboard(CLASSES)
                )

                return

            # o‘qituvchi bo‘lsa save
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO users (
                user_id, role, region,
                district, school, class
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.from_user.id,
                temp_user[message.from_user.id]["role"],
                temp_user[message.from_user.id]["region"],
                temp_user[message.from_user.id]["district"],
                f"{temp_user[message.from_user.id]['school_type']} - {message.text}",
                None
            ))

            conn.commit()
            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                "✅ Ro‘yxatdan o‘tdingiz",
                reply_markup=get_main_keyboard("O‘qituvchi")
            )

            return

        # ===== DISTRICT =====
        elif user_state.get(message.from_user.id) == "district":
            temp_user[message.from_user.id]["district"] = message.text
            user_state[message.from_user.id] = "school_type"

            await message.answer(
                "Maktab turini tanlang:",
                reply_markup=make_keyboard(SCHOOL_TYPES)
            )
            return
        
        # ===== SURVEY =====
        elif action == BTN_SURVEY:

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT role
            FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            user = cursor.fetchone()

            if not user:
                conn.close()
                return

            role = user[0]

            cursor.execute("""
            SELECT *
            FROM surveys
            WHERE role=?
            ORDER BY RANDOM()
            LIMIT 20
            """, (role,))

            surveys = cursor.fetchall()

            conn.close()

            if not surveys:

                await message.answer(
                    "❌ So‘rovnoma topilmadi"
                )
                return

            user_test[message.from_user.id] = {
                "surveys": surveys,
                "index": 0,
                "answers": {}
            }

            user_state[message.from_user.id] = "survey_work"

            q = surveys[0]

            text = (
                f"1/{len(surveys)}\n\n"
                f"{q[2]}\n\n"
                f"A) {q[4]}\n"
                f"B) {q[5]}\n"
                f"C) {q[6]}\n"
                f"D) {q[7]}"
            )

            await message.answer(text)

            return

            # ===== TEST =====
        elif action == BTN_TEST:

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT role FROM users
            WHERE user_id=?
            """, (message.from_user.id,))

            user = cursor.fetchone()
            conn.close()

            if not user:
                user_state[message.from_user.id] = "role"

                await message.answer(
                    "Kim siz?",
                    reply_markup=make_keyboard(["O‘quvchi", "O‘qituvchi"])
                )
                return

            role = user[0]

            temp_user[message.from_user.id] = {
                "role": role
            }

            # O‘quvchi
            if role == "O‘quvchi":

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()

                cursor.execute("""
                SELECT class FROM users
                WHERE user_id=?
                """, (message.from_user.id,))

                row = cursor.fetchone()

                conn.close()

                if not row or not row[0]:

                    await message.answer(
                        "❌ Avval sinfni sozlang.",
                        reply_markup=get_main_keyboard()
                    )
                    return

                selected_class = row[0]

                temp_user[message.from_user.id]["class"] = selected_class

                subjects = SUBJECTS_BY_CLASS.get(selected_class, [])

                flat_subjects = []

                for r in subjects:
                    flat_subjects.extend(r)

                set_state(message.from_user.id, "subject")

                await message.answer(
                    "Fan tanlang:",
                    reply_markup=base_keyboard(flat_subjects)
                )

                return

            # O‘qituvchi
            else:

                set_state(message.from_user.id, "subject")

                await message.answer(
                    "Fan tanlang:",
                    reply_markup=base_keyboard(["Matematika"])
                )

                return

        # ===== CLASS REGISTER =====
        elif user_state.get(message.from_user.id) == "class_register":

            temp_user[message.from_user.id]["class"] = message.text

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO users (
                user_id, role, region,
                district, school, class
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                message.from_user.id,
                temp_user[message.from_user.id]["role"],
                temp_user[message.from_user.id]["region"],
                temp_user[message.from_user.id]["district"],
                f"{temp_user[message.from_user.id]['school_type']} - {temp_user[message.from_user.id]['school']}",
                message.text
            ))

            conn.commit()
            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                "✅ Ro‘yxatdan o‘tdingiz",
                reply_markup=get_main_keyboard("O‘quvchi")
            )

            return

        elif user_state.get(message.from_user.id) == "survey_work":

            data = user_test[message.from_user.id]

            data["answers"][data["index"]] = message.text.upper()

            # oxiri
            if data["index"] >= len(data["surveys"]) - 1:

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()

                cursor.execute("""
                UPDATE users
                SET survey_done=1
                WHERE user_id=?
                """, (message.from_user.id,))

                conn.commit()
                conn.close()

                user_state[message.from_user.id] = None

                await message.answer(
                    "✅ So‘rovnoma tugadi",
                    reply_markup=get_main_keyboard(
                        temp_user[message.from_user.id]["role"]
                    )
                )

                return

            data["index"] += 1

            q = data["surveys"][data["index"]]

            text = (
                f"{data['index']+1}/{len(data['surveys'])}\n\n"
                f"{q[2]}\n\n"
                f"A) {q[4]}\n"
                f"B) {q[5]}\n"
                f"C) {q[6]}\n"
                f"D) {q[7]}"
            )

            await message.answer(text)

            return

        # ===== STAT =====
        elif action == BTN_STATS:
            await message.answer("Statistika:", reply_markup=get_stats_keyboard())

        elif admin_state.get(message.from_user.id) == "bulk":

            lines = [
                l.strip()
                for l in message.text.split("\n")
                if l.strip()
            ]

            if not lines[0].startswith("ROLE"):
                await message.answer("ROLE yo‘q ❌")
                return

            role = lines[0].split(":",1)[1].strip()

            cls = ""
            level = ""

            # ===== O‘QUVCHI =====
            if role == "O‘quvchi":

                if (
                    not lines[1].startswith("CLASS") or
                    not lines[2].startswith("SUBJECT") or
                    not lines[3].startswith("TEST_TYPE")
                ):
                    await message.answer("Format noto‘g‘ri ❌")
                    return

                cls = lines[1].split(":",1)[1].strip()
                subject = lines[2].split(":",1)[1].strip()
                test_type = lines[3].split(":",1)[1].strip()

            # ===== O‘QITUVCHI =====
            elif role == "O‘qituvchi":

                if (
                    not lines[1].startswith("LEVEL") or
                    not lines[2].startswith("SUBJECT") or
                    not lines[3].startswith("TEST_TYPE")
                ):
                    await message.answer("Format noto‘g‘ri ❌")
                    return

                level = lines[1].split(":",1)[1].strip()
                subject = lines[2].split(":",1)[1].strip()
                test_type = lines[3].split(":",1)[1].strip()

            else:
                await message.answer("ROLE xato ❌")
                return

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            i = 4
            count = 0

            while i < len(lines):

                if lines[i].startswith("Q:"):

                    try:

                        question = lines[i][2:].strip()

                        img = None
                        q_type = "single"
                        difficulty = "easy"
                        voice_type = "none"

                        step = 7

                        # IMG
                        if i+1 < len(lines) and lines[i+1].startswith("IMG:"):

                            img = lines[i+1].split(":",1)[1].strip()

                            i += 1
                            step += 1

                        # TYPE
                        if i+1 < len(lines) and lines[i+1].startswith("TYPE:"):

                            q_type = lines[i+1].split(":",1)[1].strip()

                            i += 1
                            step += 1

                        # DIFFICULTY
                        if i+1 < len(lines) and lines[i+1].startswith("DIFFICULTY:"):

                            difficulty = lines[i+1].split(":",1)[1].strip()

                            i += 1
                            step += 1

                            #ovoz
                        if i+1 < len(lines) and lines[i+1].startswith("VOICE:"):

                            voice_type = lines[i+1].split(":",1)[1].strip()

                            i += 1
                        if i+1 < len(lines) and lines[i+1].startswith("TYPE:"):

                            q_type = (
                                lines[i+1]
                                .split(":",1)[1]
                                .strip()
                                .lower()
                            )
                        a = lines[i+1].split(":",1)[1].strip()
                        b = lines[i+2].split(":",1)[1].strip()
                        c = lines[i+3].split(":",1)[1].strip()
                        d = lines[i+4].split(":",1)[1].strip()

                        correct = lines[i+5].split(":",1)[1].strip().lower()

                        cursor.execute("""
                        INSERT INTO questions (
                            role,
                            class,
                            level,
                            subject,
                            question,
                            a,
                            b,
                            c,
                            d,
                            correct,
                            test_type,
                            difficulty,
                            type,
                            img,
                            voice_type
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            role,
                            cls,
                            level,
                            subject,
                            question,
                            a,
                            b,
                            c,
                            d,
                            correct,
                            test_type,
                            difficulty,
                            q_type,
                            img,
                            voice_type
                        ))

                        count += 1

                        i += 6

                    except Exception as e:

                        await message.answer(
                            f"Xato format ❌\n\n{e}\n\nSavol: {lines[i]}"
                        )

                        break

                else:
                    i += 1

            conn.commit()
            conn.close()

            admin_state[message.from_user.id] = None

            await message.answer(f"{count} ta test qo‘shildi ✅")

        # ===== MY STATS =====
        elif action == BTN_MY:
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT subject, AVG(score*1.0/total) FROM results
            WHERE user_id=?
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                await message.answer("Sizda natija yo‘q ❌")
                return

            text = "📊 Sizning natijalaringiz:\n\n"

            for subject, avg in rows:
                percent = round(avg*100, 1)
                text += f"{subject}: {percent}%\n"

            await message.answer(text)
        # ===== GLOBAL =====
        elif action == BTN_GLOBAL:
            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT subject, AVG(score*1.0/total) FROM results
            GROUP BY subject
            """)

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                await message.answer("Ma’lumot yo‘q ❌")
                return

            text = "🌍 Umumiy statistika:\n\n"

            for subject, avg in rows:
                percent = round(avg*100, 1)
                text += f"{subject}: {percent}%\n"

            await message.answer(text)
        # ===== NUMBER (SAVE) =====
        elif message.text.isdigit():

            if user_state.get(message.from_user.id) == "survey":

                value = int(message.text)

                conn = sqlite3.connect("data.db")
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO survey (user_id, pressure) VALUES (?, ?)",
                    (message.from_user.id, value)
                )

                # ✅ survey bajarildi
                cursor.execute("""
                UPDATE users
                SET survey_done=1
                WHERE user_id=?
                """, (message.from_user.id,))

                conn.commit()
                conn.close()

                user_state[message.from_user.id] = None

                await message.answer(
                    "✅ So‘rovnoma yakunlandi",
                    reply_markup=get_main_keyboard()
                )

                return

        elif user_state.get(message.from_user.id) == "school_type":
            temp_user[message.from_user.id]["school_type"] = message.text
            user_state[message.from_user.id] = "school"

            if message.text == "🏫 Oddiy davlat maktabi":
                await message.answer("Maktab raqamini kiriting (masalan: 23)")
            elif message.text == "⭐ Ixtisoslashgan (IDUM)":
                await message.answer("IDUM maktab raqamini kiriting (masalan: 1, 2, ...)")
            elif message.text == "🏆 Prezident maktabi":
                await message.answer("Prezident maktabi nomini yozing (masalan: Toshkent PM)")
            else:
                await message.answer("Xususiy maktab nomini yozing")
            return
            


            # ❌ noto‘g‘ri formatdagi javob

        # ===== O'ZLASHTIRISH =====
        elif message.text == "📈 O‘zlashtirish":

            conn = sqlite3.connect("data.db")
            cursor = conn.cursor()

            cursor.execute("""
            SELECT subject,
            AVG(score * 100.0 / total)
            FROM results
            WHERE user_id=?
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cursor.fetchall()

            conn.close()

            if not rows:

                await message.answer(
                    "❌ Hali test ishlamagansiz"
                )
                return

            total_percent = 0

            text = "📊 O‘zlashtirish darajangiz\n\n"

            for subject, avg in rows:

                avg = round(avg, 1)

                total_percent += avg

                text += (
                    f"📘 {subject}: {avg}%\n"
                )

            overall = round(total_percent / len(rows), 1)

            text += (
                f"\n━━━━━━━━━━\n"
                f"🎯 Umumiy: {overall}%"
            )

            await message.answer(text)

            return

@dp.callback_query()
async def test_buttons(call: types.CallbackQuery):

    user_id = call.from_user.id
    await call.answer()

    if call.data.startswith("listen_"):

        q = user_test[user_id]["questions"][
            user_test[user_id]["index"]
        ]

        text = ""

        if call.data == "listen_q":
            text = q[5]

        elif call.data == "listen_a":
            text = q[6]

        elif call.data == "listen_b":
            text = q[7]

        elif call.data == "listen_c":
            text = q[8]

        elif call.data == "listen_d":
            text = q[9]

        voice = "uz-UZ-SardorNeural"

        if q[15] == "ru":
            voice = "ru-RU-DmitryNeural"

        elif q[15] == "en":
            voice = "en-US-GuyNeural"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice
        )

        await communicate.save("listen.mp3")

        await bot.send_voice(
            call.message.chat.id,
            voice=FSInputFile("listen.mp3")
        )

        return

    if user_state.get(user_id) != "test":
        return

    test = user_test[user_id]

    if test.get("answered"):
        return

    test["answered"] = True

    try:
        if test.get("timer_task"):
            test["timer_task"].cancel()
    except:
        pass

    q = test["questions"][test["index"]]
    old_q = q

    user_ans = call.data
    correct = old_q[10].lower()

    if user_ans == correct:

        test["score"] += 1

        result_text = "🎉 ✅ To‘g‘ri"

    else:

        correct_text = ""

        if correct == "a":
            correct_text = old_q[6]

        elif correct == "b":
            correct_text = old_q[7]

        elif correct == "c":
            correct_text = old_q[8]

        elif correct == "d":
            correct_text = old_q[9]
        result_text = (
            f"❌ Noto‘g‘ri\n\n"
            f"✅ To‘g‘ri javob: {correct_text}"
        )

    # oxirgi savol emas

    if test["index"] < len(test["questions"]) - 1:

        test["index"] += 1

        q = test["questions"][test["index"]]

        difficulty = q[12]

        limit = 60

        if difficulty == "medium":
            limit = 90

        elif difficulty == "hard":
            limit = 120

        test["question_uid"] = random.randint(100000,999999)
        test["answered"] = False
        test["expired"] = False
        if q[14]:

            await bot.send_photo(
                call.message.chat.id,
                photo=FSInputFile(
                    f"images/{q[14]}"
                )
            )
        if q[13] and "latex" in str(q[13]).lower():

            latex = q[5]

            encoded = quote(f"\\dpi{{300}} \\huge {latex}")

            url = f"https://latex.codecogs.com/png.image?{encoded}"

            await bot.send_photo(
                call.message.chat.id,
                photo=url
            )

            text = "Savol rasmi yuqorida ⬆️"

        else:

            text = q[5]

        markup = InlineKeyboardMarkup(
                inline_keyboard=[

                    [
                        InlineKeyboardButton(
                            text="🔊 Savol",
                            callback_data="listen_q"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 A",
                            callback_data="listen_a"
                        ),
                        InlineKeyboardButton(
                            text=q[6],
                            callback_data="a"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 B",
                            callback_data="listen_b"
                        ),
                        InlineKeyboardButton(
                            text=q[7],
                            callback_data="b"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 C",
                            callback_data="listen_c"
                        ),
                        InlineKeyboardButton(
                            text=q[8],
                            callback_data="c"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="🔊 D",
                            callback_data="listen_d"
                        ),
                        InlineKeyboardButton(
                            text=q[9],
                            callback_data="d"
                        )
                    ]
                ]
            )
        msg = await call.message.answer(
            f"{result_text}\n\n{text}",
            reply_markup=markup
        )  
        if q[15] in ["uz", "ru", "en"]:

            voice = "uz-UZ-SardorNeural"

            if q[15] == "ru":
                voice = "ru-RU-DmitryNeural"

            elif q[15] == "en":
                voice = "en-US-GuyNeural"

            filename = f"temp_{random.randint(1000,999999)}.mp3"

            communicate = edge_tts.Communicate(
                text=q[5],
                voice=voice
            )

            await communicate.save(filename)

          #  await bot.send_voice(
           #     call.message.chat.id,
            #    voice=FSInputFile(filename)
            #)

        # eski timerni o‘chirish
        try:
            if test.get("timer_task"):
                test["timer_task"].cancel()
        except:
            pass

        # YANGI TIMER
        test["timer_task"] = asyncio.create_task(
            question_timer(user_id, limit)
        )

        test["msg_id"] = msg.message_id
    # test tugasa
    else:

        await call.message.answer(
            f"🏁 Test tugadi\n\n"
            f"📊 Natija: {test['score']}/{len(test['questions'])}"
        )

        user_test.pop(user_id, None)

        user_state[user_id] = None

        conn = sqlite3.connect("data.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT role
        FROM users
        WHERE user_id=?
        """, (user_id,))

        row = cursor.fetchone()

        conn.close()

        role = row[0] if row else "O‘quvchi"

        await call.message.answer(
            "🏠 Bosh menyu",
            reply_markup=get_main_keyboard(role)
        )

async def question_timer(user_id, limit):

    try:

        if user_id not in user_test:
            return

        test = user_test[user_id]

        current_uid = test["question_uid"]

        timer_msg = await bot.send_message(
            user_id,
            f"⏰ {limit}"
        )

        start_time = time.time()

        while True:

            if user_id not in user_test:
                return

            test = user_test[user_id]

            # boshqa savolga o'tib ketgan bo‘lsa
            if current_uid != test["question_uid"]:
                return

            # javob berilgan bo‘lsa
            if test.get("answered"):
                return

            passed = int(time.time() - start_time)

            left = limit - passed

            if left <= 0:
                break

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=timer_msg.message_id,
                    text=f"⏰ {left}"
                )
            except:
                pass

            await asyncio.sleep(1)

        # vaqt tugadi
        test["expired"] = True

        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=timer_msg.message_id,
                text="⏰ 0"
            )
        except:
            pass

        await bot.send_message(
            user_id,
            "⏰ Vaqt tugadi!\n➡️ Keyingi savol..."
        )

        test["index"] += 1

        # TEST TUGADI
        if test["index"] >= len(test["questions"]):

            score = test["score"]
            total = len(test["questions"])

            await bot.send_message(
                user_id,
                f"🏁 Test tugadi\n\n📊 Natija: {score}/{total}"
            )

            user_test.pop(user_id, None)
            return

        q = test["questions"][test["index"]]
        

        difficulty = q[12]

        limit = 60

        if difficulty == "medium":
            limit = 90

        elif difficulty == "hard":
            limit = 120

        test["question_uid"] = random.randint(100000,999999)
        test["answered"] = False
        test["expired"] = False
        if q[14]:

            await bot.send_photo(
                user_id,
                photo=FSInputFile(
                    f"images/{q[14]}"
                )
            )        # LATEX
        if q[13] == "latex":

            latex = q[5]

            encoded = quote(f"\\dpi{{300}} \\huge {latex}")

            url = f"https://latex.codecogs.com/png.image?{encoded}"

            await bot.send_photo(
                user_id,
                photo=url
            )

            text = (
                f"{test['index']+1}/{len(test['questions'])}-savol\n\n"
                f"A) {q[6]}\n"
                f"B) {q[7]}\n"
                f"C) {q[8]}\n"
                f"D) {q[9]}"
            )
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=q[6],
                            callback_data="a"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=q[7],
                            callback_data="b"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=q[8],
                            callback_data="c"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=q[9],
                            callback_data="d"
                        )
                    ]
                ]
            )
        text = f"{q[5]}"

        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=q[6],
                        callback_data="a"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=q[7],
                        callback_data="b"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=q[8],
                        callback_data="c"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=q[9],
                        callback_data="d"
                    )
                ]
            ]
        )

        await bot.send_message(
            user_id,
            text,
            reply_markup=markup
        )

        test["timer_task"] = asyncio.create_task(
            question_timer(user_id, limit)
        )

    except asyncio.CancelledError:
        return

async def main():
    print("BOT ISHGA TUSHDI 🚀")
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())