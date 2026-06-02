from admin_handlers import *
from generator_handlers import *
import asyncio
from aiogram.types import ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, types
from urllib.parse import quote
from aiogram.filters import *
from dts_import_handlers import *
from ai_generatori import *
from keyboards import get_main_keyboard
from loader import dp, bot
from aiogram import F
from aiogram.fsm.context import FSMContext
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
import psycopg2
import re
import os
import subprocess
with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

ADMINS = [401251407]

DATABASE_URL = os.getenv("DATABASE_URL")
API_TOKEN = os.getenv("BOT_TOKEN")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

user_state = {}
temp_user = {}
user_test = {}
user_locks = {}
admin_state = {}
state_history = {}
test_sessions = {}
generator_process = None



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

LEVELS = [
    (0, "🌱", "Nihol"),
    (500, "🌿", "O'smoqda"),
    (1500, "🌳", "Bilimli"),
    (3000, "🥈", "Ekspert"),
    (5000, "🥇", "Usta")
]

TEXT_TO_ID = {
    "📊 So‘rovnoma": BTN_SURVEY,
    "📚 BILIMNI SINASH": BTN_TEST,
    "📈 Statistika": BTN_STATS,
    "📈 Umumiy statistika": BTN_GLOBAL,
}
CLASSES = [
    "🏫 Oddiy 0-sinf",
    "⭐ IDUM 0-sinf",
    "🏆 Prezident 0-sinf",
    "🏢 Xususiy 0-sinf",

    "🏫 Oddiy 1-sinf",
    "⭐ IDUM 1-sinf",
    "🏆 Prezident 1-sinf",
    "🏢 Xususiy 1-sinf",

   "🏫 Oddiy 2-sinf",
    "⭐ IDUM 2-sinf",
    "🏆 Prezident 2-sinf",
    "🏢 Xususiy 2-sinf",

   "🏫 Oddiy 3-sinf",
    "⭐ IDUM 3-sinf",
    "🏆 Prezident 3-sinf",
    "🏢 Xususiy 3-sinf",

   "🏫 Oddiy 4-sinf",
    "⭐ IDUM 4-sinf",
    "🏆 Prezident 4-sinf",
    "🏢 Xususiy 4-sinf",

   "🏫 Oddiy 5-sinf",
    "⭐ IDUM 5-sinf",
    "🏆 Prezident 5-sinf",
    "🏢 Xususiy 5-sinf",

   "🏫 Oddiy 6-sinf",
    "⭐ IDUM 6-sinf",
    "🏆 Prezident 6-sinf",
    "🏢 Xususiy 6-sinf",

   "🏫 Oddiy 7-sinf",
    "⭐ IDUM 7-sinf",
    "🏆 Prezident 7-sinf",
    "🏢 Xususiy 7-sinf",

   "🏫 Oddiy 8-sinf",
    "⭐ IDUM 8-sinf",
    "🏆 Prezident 8-sinf",
    "🏢 Xususiy 8-sinf",

   "🏫 Oddiy 9-sinf",
    "⭐ IDUM 9-sinf",
    "🏆 Prezident 9-sinf",
    "🏢 Xususiy 9-sinf",

   "🏫 Oddiy 10-sinf",
    "⭐ IDUM 10-sinf",
    "🏆 Prezident 10-sinf",
    "🏢 Xususiy 10-sinf",

   "🏫 Oddiy 11-sinf",
    "⭐ IDUM 11-sinf",
    "🏆 Prezident 11-sinf",
    "🏢 Xususiy 11-sinf",

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

LEVELS = [
    (0, "🥚", "Boshlanish"),
    (500, "🐣", "O'rganuvchi"),
    (1500, "🦅", "Usta")
]

SUBJECTS_BY_CLASS = {

    "0-sinf": [
        ["🔤 O‘zbekcha so‘zlar","🇬🇧 English Kids"],
        ["🇷🇺 Русский детям","🔢 Sonlar olami"],
        ["🎨 Ranglar","🐶 Hayvonlar"],
        ["🧩 Jumboqlar","👀 Diqqat"],
        ["🎯 Mantiqiy o‘yinlar"]
    ]
}

# 1-4 sinf
PRIMARY_SUBJECTS = [
    ["Matematika", "Ona tili", "O‘qish"],
    ["Ingliz tili", "Tabiiy fan", "Tarbiya"],
    ["Musiqa", "Rasm"]
]

# 5-6 sinf
MIDDLE_SUBJECTS = [
    ["Matematika", "Ona tili", "Adabiyot"],
    ["Ingliz tili", "Rus tili", "Tarix"],
    ["Biologiya", "Geografiya", "Informatika"],
    ["Texnologiya"]
]

# 7-9 sinf
UPPER_SUBJECTS = [
    ["Algebra", "Geometriya", "Fizika"],
    ["Kimyo", "Biologiya", "Tarix"],
    ["Geografiya", "Informatika", "Ingliz tili"],
    ["Ona tili", "Adabiyot"]
]

# 10-11 sinf
HIGH_SUBJECTS = [
    ["Algebra", "Geometriya", "Fizika"],
    ["Kimyo", "Biologiya", "Tarix"],
    ["Huquq", "Iqtisod", "Geografiya"],
    ["Informatika", "Ingliz tili", "Ona tili"],
    ["Adabiyot"]
]

for school in [
    "🏫 Oddiy",
    "⭐ IDUM",
    "🏆 Prezident",
    "🏢 Xususiy"
]:
    # 0
    SUBJECTS_BY_CLASS["🏫 Oddiy 0-sinf"] = SUBJECTS_BY_CLASS["0-sinf"]
    SUBJECTS_BY_CLASS["⭐ IDUM 0-sinf"] = SUBJECTS_BY_CLASS["0-sinf"]
    SUBJECTS_BY_CLASS["🏆 Prezident 0-sinf"] = SUBJECTS_BY_CLASS["0-sinf"]
    SUBJECTS_BY_CLASS["🏢 Xususiy 0-sinf"] = SUBJECTS_BY_CLASS["0-sinf"]

    # 1-4
    SUBJECTS_BY_CLASS[f"{school} 1-sinf"] = PRIMARY_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 2-sinf"] = PRIMARY_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 3-sinf"] = PRIMARY_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 4-sinf"] = PRIMARY_SUBJECTS

    # 5-6
    SUBJECTS_BY_CLASS[f"{school} 5-sinf"] = MIDDLE_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 6-sinf"] = MIDDLE_SUBJECTS

    # 7-9
    SUBJECTS_BY_CLASS[f"{school} 7-sinf"] = UPPER_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 8-sinf"] = UPPER_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 9-sinf"] = UPPER_SUBJECTS

    # 10-11
    SUBJECTS_BY_CLASS[f"{school} 10-sinf"] = HIGH_SUBJECTS
    SUBJECTS_BY_CLASS[f"{school} 11-sinf"] = HIGH_SUBJECTS

ZERO_TEST_TYPES = [
    "🔤 Harflar",
    "📖 So‘zlar",
    "🖼 Rasmli o‘yin",
    "🎵 Eshit va top",
    "🎁 Aralash"
]

TEST_TYPES = [
    "1-chorak",
    "2-chorak",
    "3-chorak",
    "4-chorak",
    "📘 Yillik",
    "📝 DTS"
]

def set_state(user_id, state):

    user_state[user_id] = state

    if user_id not in state_history:
        state_history[user_id] = []

    state_history[user_id].append(state)

def get_level(xp):

    current_icon = "🌱"
    current_name = "Nihol"

    for need_xp, icon, name in LEVELS:

        if xp >= need_xp:

            current_icon = icon
            current_name = name

    return current_icon, current_name

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

def get_stats_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 DTS")],
            [KeyboardButton(text="📈 Umumiy statistika")],
            [KeyboardButton(text=BACK)],
            [KeyboardButton(text=HOME)]
        ],
        resize_keyboard=True
    )

def check_survey(user_id):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
    SELECT survey_done
    FROM users
    WHERE user_id=%s
    """, (user_id,))

    row = cur.fetchone()

    conn.close()

    if not row:
        return False

    return row[0] == 1


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()



    cur.execute("""
    CREATE TABLE IF NOT EXISTS survey_answers (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        survey_id INTEGER,
        answer TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS images(
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        file_id TEXT
    )
    """)

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS surveys (
        id SERIAL PRIMARY KEY,
        role TEXT,
        question TEXT,
        q_type TEXT,
        a TEXT,
        b TEXT,
        c TEXT,
        d TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id SERIAL PRIMARY KEY,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id SERIAL PRIMARY KEY,
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
        voice_type TEXT,
        school_type TEXT           
    )
    """)

    conn.commit()
    conn.close()

@dp.message(F.photo)
async def save_image(message: types.Message):

    if message.from_user.id not in ADMINS:
        return

    if not message.caption:
        await message.answer(
            "Rasm nomini captionga yozing"
        )
        return

    name = message.caption.strip()

    file_id = message.photo[-1].file_id

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO images(
        name,
        file_id
    )
    VALUES(%s,%s)
    ON CONFLICT (name)
    DO UPDATE SET
    file_id = EXCLUDED.file_id
    """, (name, file_id))
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ Saqlandi: {name}"
    )

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

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(
        "SELECT role FROM users WHERE user_id=%s",
        (message.from_user.id,)
    )

    user = cur.fetchone()
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
async def handle_all(
    message: Message,
    state: FSMContext
):
    user_id = message.from_user.id
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
        UPDATE users
        SET last_seen=NOW()
        WHERE user_id=%s
        """, (user_id,))

        conn.commit()
        conn.close()

    except:
        pass

    if message.document:

        await dts_excel_import(
            message,
            state
        )

        return

    elif user_id not in temp_user:
        temp_user[user_id] = {}

    elif user_id not in user_state:
        user_state[user_id] = None

    # lock yaratish
    elif user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    elif user_state.get(message.from_user.id) == "text_answer":

        user_answer = message.text.strip()

        session = test_sessions.get(
            message.from_user.id
        )

        if not session:
            return

        current = session["current"]

        test = session["questions"][current]

        correct = test[5]

        if user_answer.lower() == str(correct).lower():

            session["correct"] += 1

            await message.answer(
                "✅ To'g'ri"
            )

        else:

            session["wrong"] += 1

            await message.answer(
                f"❌ Noto'g'ri\n\nTo'g'ri javob: {correct}"
            )

        session["current"] += 1

        if session["current"] >= len(
            session["questions"]
        ):

            await message.answer(
                f"""
    🏁 Test tugadi

    ✅ To'g'ri: {session['correct']}
    ❌ Noto'g'ri: {session['wrong']}
    """
            )

            del test_sessions[
                message.from_user.id
            ]

            return

        current = session["current"]

        test = session["questions"][current]

        (
            question,
            a,
            b,
            c,
            d,
            correct,
            explanation,
            question_type,
            is_latex,
            image_url,
            audio_text,
            language,
            time_limit
        ) = test

        if question_type == "write_answer":

            await message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:"
            )

            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(a),
                        callback_data="ans_A"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(b),
                        callback_data="ans_B"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(c),
                        callback_data="ans_C"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(d),
                        callback_data="ans_D"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛑 Testni tugatish",
                        callback_data="test_stop"
                    )
                ]
            ]
        )

        await message.answer(
            f"⏱️ {time_limit} soniya\n\n"
            f"{question}",
            reply_markup=kb
        )

    if message.text == "👥 Foydalanuvchilar statistikasi":

        if message.from_user.id not in ADMINS:
            return

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE DATE(last_seen)=CURRENT_DATE
        """)
        today = cur.fetchone()[0]

        cur.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE last_seen >= NOW() - INTERVAL '30 day'
        """)
        month = cur.fetchone()[0]

        conn.close()

        await message.answer(
            f"👥 Jami foydalanuvchilar: {total}\n\n"
            f"📅 Bugun kirganlar: {today}\n"
            f"🗓 Oxirgi 30 kun: {month}"
        )

        return

    elif message.text == "📚 DTS boshqaruvi":

        await dts_menu(
                message
            )
        return

    elif message.text == "🤖 Test generator":

        await message.answer(
            "Generator boshqaruvi",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="▶️ Generatorni boshlash")],
                    [KeyboardButton(text="⏹ Generatorni to‘xtatish")],
                    [KeyboardButton(text="📊 Generator statistikasi")],
                    [KeyboardButton(text="🔙 Ortga")]
                ],
                resize_keyboard=True
            )
        )

        return

    elif message.text == "▶️ Generatorni boshlash":

        global generator_process

        if generator_process and generator_process.poll() is None:

            await message.answer(
                "Generator ishlayapti"
            )

            return

        generator_process = subprocess.Popen(
            ["python", "test_generator.py"]
        )

        await message.answer(
            "Generator ishga tushdi"
        )

        return

    elif message.text == "⏹ Generatorni to‘xtatish":

        if generator_process and generator_process.poll() is None:

            generator_process.terminate()

            await message.answer(
                "Generator to‘xtatildi"
            )

        else:

            await message.answer(
                "Generator ishlamayapti"
            )

        return
    elif message.text == "📊 Generator statistikasi":

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM generated_tests"
        )

        tests = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM topic_generation"
        )

        topics = cur.fetchone()[0]

        conn.close()

        await message.answer(
            f"📚 Mavzular: {topics}\n"
            f"📝 Testlar: {tests}"
        )

        return

    elif message.text == "📚 DTS":

        await message.answer(
            "TEST"
        )

        return

    elif message.text == "📥 DTS import":

        await dts_import_menu(
            message,
            admin_state,
            user_id
        )

        return

    elif (
        admin_state.get(user_id) == "dts_import"
        and message.document
    ):

        await dts_import_file(
            message,
            bot,
            user_id
        )

        return

    elif message.text == "⬅ Ortga":

        await admin_main_menu(
            message
        )

        return

    elif message.text == "📊 DTS statistika":

        await dts_statistics(
            message
        )

        return

    elif message.text == "📤 DTS export":

        await dts_export_menu(
            message
        )

        return

    elif message.text == "📤 Hammasini export":

        await dts_export_all(
            message
        )

        return
        
    # parallel message bloklash
    
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
        
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

                elif prev_state == "db_school":

                    await message.answer(
                        "🏫 Maktab turini tanlang:",
                        reply_markup=base_keyboard([
                            "all",
                            "🏫 Oddiy",
                            "⭐ IDUM",
                            "🏆 Prezident",
                            "🏢 Xususiy"
                        ])
                    )
                    return

                elif prev_state == "db_class":

                    school = temp_user[user_id].get("db_school")

                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()

                    cur.execute("""
                    SELECT class, COUNT(*)
                    FROM questions
                    WHERE role='O‘quvchi'
                    AND school_type=%s
                    GROUP BY class
                    ORDER BY class
                    """, (school,))

                    rows = cur.fetchall()

                    conn.close()

                    classes = [
                        f"{cls} ({cnt})"
                        for cls, cnt in rows
                    ]

                    await message.answer(
                        "🎓 Sinfni tanlang:",
                        reply_markup=base_keyboard(classes)
                    )
                    return

                elif prev_state == "db_subject":

                    selected_class = temp_user[user_id]["db_class"]

                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()

                    cur.execute("""
                    SELECT subject, COUNT(*)
                    FROM questions
                    WHERE class=%s
                    GROUP BY subject
                    ORDER BY subject
                    """, (selected_class,))

                    rows = cur.fetchall()

                    conn.close()

                    subjects = [
                        f"{subject} ({cnt})"
                        for subject, cnt in rows
                    ]

                    await message.answer(
                        "📘 Fan tanlang:",
                        reply_markup=base_keyboard(subjects)
                    )
                    return

                elif prev_state == "db_test":

                    selected_class = temp_user[user_id]["db_class"]
                    subject = temp_user[user_id]["db_subject"]

                    conn = psycopg2.connect(DATABASE_URL)
                    cur = conn.cursor()

                    cur.execute("""
                    SELECT test_type, COUNT(*)
                    FROM questions
                    WHERE class=%s
                    AND subject=%s
                    GROUP BY test_type
                    ORDER BY test_type
                    """, (selected_class, subject))

                    rows = cur.fetchall()

                    conn.close()

                    tests = [
                        f"{test_type} ({cnt})"
                        for test_type, cnt in rows
                    ]

                    await message.answer(
                        "📝 Test turini tanlang:",
                        reply_markup=base_keyboard(tests)
                    )
                    return

            # history yo‘q bo‘lsa
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT role FROM users
            WHERE user_id=%s
            """, (user_id,))

            user = cur.fetchone()
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

        elif message.text == "📚 BILIMNI SINASH bazasi":

            if user_id not in ADMINS:
                return

            await message.answer(
                "📚 Savollar boshqaruvi",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="👨‍🎓 O‘quvchi bazasi")],
                        [KeyboardButton(text="👨‍🏫 O‘qituvchi bazasi")],
                        [KeyboardButton(text="📋 So‘rovnoma bazasi")],
                        [KeyboardButton(text=BACK)]
                    ],
                    resize_keyboard=True
                )
            )

            return

        elif message.text == "👨‍🎓 O‘quvchi bazasi":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT DISTINCT school_type
            FROM questions
            WHERE role='O‘quvchi'
            ORDER BY school_type
            """)

            rows = cur.fetchall()

            conn.close()

            schools = [r[0] for r in rows if r[0]]

            set_state(user_id, "db_school")

            await message.answer(
                "🏫 Maktab turini tanlang:",
                reply_markup=base_keyboard(schools)
            )

            return

        elif user_state.get(user_id) == "db_school":

            temp_user[user_id]["db_school"] = message.text

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT class, COUNT(*)
            FROM questions
            WHERE role='O‘quvchi'
            AND school_type=%s
            GROUP BY class
            ORDER BY class
            """, (message.text,))

            rows = cur.fetchall()

            conn.close()

            classes = []

            for cls, cnt in rows:
                classes.append(f"{cls} ({cnt})")

            set_state(user_id, "db_class")

            await message.answer(
                "🎓 Sinfni tanlang:",
                reply_markup=base_keyboard(classes)
            )

            return

        elif user_state.get(user_id) == "db_class":

            selected_class = message.text.split(" (")[0]

            temp_user[user_id]["db_class"] = selected_class

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT subject, COUNT(*)
            FROM questions
            WHERE class=%s
            GROUP BY subject
            ORDER BY subject
            """, (selected_class,))

            rows = cur.fetchall()

            conn.close()

            subjects = []

            for subject, cnt in rows:
                subjects.append(f"{subject} ({cnt})")

            set_state(user_id, "db_subject")

            await message.answer(
                "📘 Fan tanlang:",
                reply_markup=base_keyboard(subjects)
            )

            return

        elif user_state.get(user_id) == "db_subject":

            subject = message.text.split(" (")[0]

            temp_user[user_id]["db_subject"] = subject

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT test_type, COUNT(*)
            FROM questions
            WHERE class=%s
            AND subject=%s
            GROUP BY test_type
            ORDER BY test_type
            """, (
                temp_user[user_id]["db_class"],
                subject
            ))

            rows = cur.fetchall()

            conn.close()

            tests = []

            for test_type, cnt in rows:
                tests.append(f"{test_type} ({cnt})")

            set_state(user_id, "db_test")

            await message.answer(
                "📝 Test turini tanlang:",
                reply_markup=base_keyboard(tests)
            )

            return

        elif user_state.get(user_id) == "db_test":

            test_type = message.text.split(" (")[0]

            temp_user[user_id]["db_test"] = test_type

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT id, question
            FROM questions
            WHERE class=%s
            AND subject=%s
            AND test_type=%s
            ORDER BY id
            """, (
                temp_user[user_id]["db_class"],
                temp_user[user_id]["db_subject"],
                test_type
            ))

            rows = cur.fetchall()

            conn.close()

            if not rows:

                await message.answer("Savollar topilmadi ❌")
                return

            text = (
                f"📚 {temp_user[user_id]['db_class']}\n"
                f"📘 {temp_user[user_id]['db_subject']}\n"
                f"📝 {test_type}\n\n"
            )

            temp_user[user_id]["current_questions"] = rows

            set_state(user_id, "question_list")

            for i, (qid, question) in enumerate(rows, start=1):
                text += f"{i}. {question}\n"

            await message.answer(
                text[:4000],
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="🗑 Savol(lar)ni o‘chirish")],
                        [KeyboardButton(text="🗑 Shu blokni o‘chirish")],
                        [KeyboardButton(text="🔙 Ortga")]
                    ],
                    resize_keyboard=True
                )
            )
            return

        elif (
            user_state.get(user_id) == "question_list"
            and message.text == "🗑 Savol(lar)ni o‘chirish"
        ):

            set_state(user_id, "delete_questions")

            await message.answer(
                "Qaysi savollarni o‘chirasiz?\n\n"
                "Misollar:\n"
                "2\n"
                "2,5,8\n"
                "2-7"
            )

            return

        elif user_state.get(user_id) == "delete_questions":

            rows = temp_user[user_id].get("current_questions", [])

            selected = set()

            try:

                for part in message.text.split(","):

                    part = part.strip()

                    if "-" in part:

                        start, end = part.split("-")

                        start = int(start.strip())
                        end = int(end.strip())

                        if start > end:
                            start, end = end, start

                        for x in range(start, end + 1):
                            selected.add(x)

                    else:

                        selected.add(int(part))

            except:

                await message.answer(
                    "Format xato ❌\n\n"
                    "Misollar:\n"
                    "2\n"
                    "2,5,8\n"
                    "2-7"
                )
                return

            ids = []

            for num in selected:

                if 1 <= num <= len(rows):

                    ids.append(rows[num - 1][0])

            if not ids:

                await message.answer("Savol topilmadi ❌")
                return

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            DELETE FROM questions
            WHERE id = ANY(%s)
            """, (ids,))

            deleted = cur.rowcount

            conn.commit()
            conn.close()

            await message.answer(
                f"✅ {deleted} ta savol o‘chirildi"
            )
            set_state(user_id, "question_list")

            return

        elif (
            user_state.get(user_id) == "question_list"
            and message.text == "🗑 Shu blokni o‘chirish"
        ):

            rows = temp_user[user_id].get("current_questions", [])

            temp_user[user_id]["block_delete_count"] = len(rows)

            set_state(user_id, "confirm_block_delete")

            await message.answer(
                f"⚠️ Shu blokdagi {len(rows)} ta savol o‘chirilsinmi?\n\n"
                f"📚 {temp_user[user_id]['db_class']}\n"
                f"📘 {temp_user[user_id]['db_subject']}\n"
                f"📝 {temp_user[user_id]['db_test']}",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="✅ Ha")],
                        [KeyboardButton(text="❌ Yo‘q")],
                        [KeyboardButton(text="🔙 Ortga")]
                    ],
                    resize_keyboard=True
                )
            )

            return

        elif (
            user_state.get(user_id) == "confirm_block_delete"
            and message.text == "✅ Ha"
        ):

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            DELETE FROM questions
            WHERE class=%s
            AND subject=%s
            AND test_type=%s
            """, (
                temp_user[user_id]["db_class"],
                temp_user[user_id]["db_subject"],
                temp_user[user_id]["db_test"]
            ))

            deleted = cur.rowcount

            conn.commit()
            conn.close()

            await message.answer(
                f"✅ {deleted} ta savol o‘chirildi"
            )

            set_state(user_id, "db_test")

            return

        elif (
            user_state.get(user_id) == "confirm_block_delete"
            and message.text == "❌ Yo‘q"
        ):

            set_state(user_id, "question_list")

            await message.answer(
                "Bekor qilindi ✅",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text="🗑 Savol(lar)ni o‘chirish")],
                        [KeyboardButton(text="🗑 Shu blokni o‘chirish")],
                        [KeyboardButton(text="🔙 Ortga")]
                    ],
                    resize_keyboard=True
                )
            )

            return

        # ===== SURVEY RESULTS =====
        elif message.text == "📋 So‘rovnoma natijalari":

            if message.from_user.id not in ADMINS:
                return

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT surveys.question,
            survey_answers.answer,
            COUNT(*)
            FROM survey_answers
            JOIN surveys
            ON surveys.id = survey_answers.survey_id
            GROUP BY surveys.question, survey_answers.answer
            """)

            rows = cur.fetchall()

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT DISTINCT school
            FROM users
            WHERE district=%s
            """, (message.text,))

            rows = cur.fetchall()

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE school=%s
            """, (school,))

            avg = cur.fetchone()[0]

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT role FROM users
            WHERE user_id=%s
            """, (message.from_user.id,))

            user = cur.fetchone()
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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT subject,
            AVG(score * 100.0 / total)
            FROM results
            WHERE user_id=%s
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cur.fetchall()

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE role='O‘quvchi'
            """)

            avg = cur.fetchone()[0]

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT region users
            WHERE user_id=%s
            """, (message.from_user.id,))

            row = cur.fetchone()

            if not row:
                conn.close()
                return

            region = row[0]

            cur.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE region=%s
            """, (region,))

            avg = cur.fetchone()[0]

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            """)

            avg = cur.fetchone()[0]

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

       # ===== MAKTAB STATISTIKASI =====
        elif message.text == "🏫 Maktab statistikasi":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT school FROM users
            WHERE user_id=%s
            """, (message.from_user.id,))

            row = cur.fetchone()

            if not row:
                await message.answer("❌ Maktab topilmadi")
                conn.close()
                return

            school = row[0]

            cur.execute("""
            SELECT AVG(score * 100.0 / total)
            FROM results
            WHERE school=%s
            """, (school,))

            avg = cur.fetchone()[0]

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            UPDATE users
            SET role=%s
            WHERE user_id=%s
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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            UPDATE users
            SET region=%s, district=%s
            WHERE user_id=%s
            """, (
                temp_user[message.from_user.id]["new_region"],
                message.text,
                message.from_user.id
            ))

            conn.commit()

            cur.execute(
                "SELECT role FROM users WHERE user_id=%s",
                (message.from_user.id,)
            )

            role = cur.fetchone()[0]

            conn.close()

            user_state[message.from_user.id] = None

            await message.answer(
                "✅ Hudud o‘zgartirildi",
                reply_markup=get_main_keyboard(role)
            )

            return

# ===== MAKTABNI ALMASHTIRISH =====

        elif message.text == "🏫 Maktabni almashtirish":

            user_state[user_id] = "change_school_type"

            await message.answer(
                "Maktab turini tanlang:",
                reply_markup=make_keyboard(SCHOOL_TYPES)
            )

            return


        elif user_state.get(user_id) == "change_school_type":

            temp_user[user_id]["new_school_type"] = message.text

            user_state[user_id] = "change_school"

            await message.answer(
                "Maktab raqami kiriting:"
            )

            return


        elif user_state.get(user_id) == "change_school":

            temp_user[user_id]["new_school"] = (
                f"{temp_user[user_id]['new_school_type']} - {message.text}"
            )

            school_type = temp_user[user_id]["new_school_type"]

            if school_type == "🏫 Oddiy davlat maktabi":
                classes = [c for c in CLASSES if "🏫 Oddiy" in c]

            elif school_type == "⭐ Ixtisoslashgan (IDUM)":
                classes = [c for c in CLASSES if "⭐ IDUM" in c]

            elif school_type == "🏆 Prezident maktabi":
                classes = [c for c in CLASSES if "🏆 Prezident" in c]

            else:
                classes = [c for c in CLASSES if "🏢 Xususiy" in c]

            user_state[user_id] = "change_school_class"

            await message.answer(
                "Sinfni tanlang:",
                reply_markup=base_keyboard(classes)
            )

            return


        elif user_state.get(user_id) == "change_school_class":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            UPDATE users
            SET school=%s, class=%s
            WHERE user_id=%s
            """, (
                temp_user[user_id]["new_school"],
                message.text,
                user_id
            ))

            conn.commit()

            cur.execute("""
            SELECT role
            FROM users
            WHERE user_id=%s
            """, (user_id,))

            row = cur.fetchone()

            conn.close()

            role = row[0] if row else "O‘quvchi"

            user_state[user_id] = None

            await message.answer(
                "✅ Maktab va sinf o‘zgartirildi",
                reply_markup=get_main_keyboard(role)
            )

            return


        # ===== SINFNI ALMASHTIRISH =====
        elif message.text == "🎓 Sinfni almashtirish":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT school
            FROM users
            WHERE user_id=%s
            """, (message.from_user.id,))

            row = cur.fetchone()

            conn.close()

            school = row[0] if row else ""

            if "🏫 Oddiy" in school:
                classes = [c for c in CLASSES if "🏫 Oddiy" in c]

            elif "⭐ IDUM" in school:
                classes = [c for c in CLASSES if "⭐ IDUM" in c]

            elif "🏆 Prezident" in school:
                classes = [c for c in CLASSES if "🏆 Prezident" in c]

            else:
                classes = [c for c in CLASSES if "🏢 Xususiy" in c]

            user_state[message.from_user.id] = "change_class"

            await message.answer(
                "Yangi sinfni tanlang:",
                reply_markup=base_keyboard(classes)
            )

            return


        elif user_state.get(message.from_user.id) == "change_class":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            UPDATE users
            SET class=%s
            WHERE user_id=%s
            """, (
                message.text,
                message.from_user.id
            ))

            conn.commit()

            cur.execute("""
            SELECT role FROM users
            WHERE user_id=%s
            """, (message.from_user.id,))

            row = cur.fetchone()

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

            # nested list -> 🏫 Oddiy list
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
            temp_user[message.from_user.id]["subject"] = message.text
            set_state(message.from_user.id, "quarter")
            selected_class = temp_user[message.from_user.id].get("class", "")
           
            """
            if "0-sinf" in selected_class:
                await message.answer(
                    "O‘yin turini tanlang:",
                    reply_markup=base_keyboard(ZERO_TEST_TYPES)
                )
            else:
                await message.answer(
                    "Test turini tanlang:",
                    reply_markup=base_keyboard(TEST_TYPES)
                )
            return
            """
            
           
        elif user_state.get(message.from_user.id) == "test":
            if message.text not in ["❌ Testni tugatish"]:
                await message.answer(
                    "👇 Javobni faqat tugmalar orqali tanlang."
                )
                return
            test = user_test[message.from_user.id]
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

                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()

                cur.execute("""
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                
                user_test.pop(user_id, None)
                user_state[user_id] = None

                return

            # KEYINGI SAVOL
            test["index"] += 1

            test["question_start"] = time.time()
            test["question_uid"] = random.randint(100000,999999)
            test["expired"] = False
            test["processing"] = False
            test["answered"] = False

            q = test["questions"][test["index"]]

            if q[14]:

                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()

                cur.execute(
                    "SELECT file_id FROM images WHERE name=%s",
                    (q[14],)
                )

                row = cur.fetchone()

                conn.close()

                if row:

                    await bot.send_photo(
                        message.chat.id,
                        photo=row[0]
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

                encoded = quote(
                    f"\\dpi{{300}} \\huge {latex}"
                )

                await bot.send_photo(
                    message.chat.id,
                    photo=url
                )

                text = "Savol rasmi yuqorida ⬆️"

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
                        ],[
                        InlineKeyboardButton(
                            text="❌ Testni tugatish",
                            callback_data="finish"
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
                        ],[
                        InlineKeyboardButton(
                            text="❌ Testni tugatish",
                            callback_data="finish"
                        ) 
                    ]
                    ]
                )

            
            await bot.send_message(
                message.chat.id,
                "📚 Test boshlandi",
                reply_markup=ReplyKeyboardRemove()
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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            # O‘qituvchi
            if temp_user[message.from_user.id]["role"] == "O‘qituvchi":

                questions = []

                selected_level = temp_user[message.from_user.id]["teacher_level"]
                subject = temp_user[message.from_user.id]["subject"]
                test_type = temp_user[message.from_user.id]["test_type"]

                # EASY
                cur.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=%s
                AND subject=%s
                AND test_type=%s
                AND difficulty='easy'
                ORDER BY RANDOM()
                LIMIT 10
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cur.fetchall())

                # MEDIUM
                cur.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=%s
                AND subject=%s
                AND test_type=%s
                AND difficulty='medium'
                ORDER BY RANDOM()
                LIMIT 7
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cur.fetchall())

                # HARD
                cur.execute("""
                SELECT * FROM questions
                WHERE role='O‘qituvchi'
                AND level=%s
                AND subject=%s
                AND test_type=%s
                AND difficulty='hard'
                ORDER BY RANDOM()
                LIMIT 3
                """, (
                    selected_level,
                    subject,
                    test_type
                ))

                questions.extend(cur.fetchall())

            if user_id not in temp_user:
                await message.answer(
                    "♻️ Bot yangilangan. Testni qayta boshlang."
                )
                return

            # O‘quvchi
            else:

                if "🏫 Oddiy" in temp_user[user_id]["class"]:
                    school_type = "🏫 Oddiy"
                elif "⭐ IDUM" in temp_user[user_id]["class"]:
                    school_type = "⭐ IDUM"
                elif "🏆 Prezident" in temp_user[user_id]["class"]:
                    school_type = "🏆 Prezident"
                elif "🏢 Xususiy" in temp_user[user_id]["class"]:
                    school_type = "🏢 Xususiy"
                else:
                    school_type = "all"

                cur.execute("""
                SELECT *
                FROM questions
                WHERE role='O‘quvchi'
                AND class=%s
                AND subject=%s
                AND test_type=%s
                AND school_type IN (%s, 'all')
                ORDER BY RANDOM()
                LIMIT 20
                """, (
                    temp_user[user_id]["class"],
                    temp_user[user_id]["subject"],
                    temp_user[user_id]["test_type"],
                    school_type
                ))

                questions = cur.fetchall()

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

                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()

                cur.execute(
                    "SELECT file_id FROM images WHERE name=%s",
                    (q[14],)
                )

                row = cur.fetchone()

                conn.close()

                if row:

                    await bot.send_photo(
                        message.chat.id,
                        photo=row[0]
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
                    ],[
                        InlineKeyboardButton(
                            text="❌ Testni tugatish",
                            callback_data="finish"
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

                school_type = temp_user[message.from_user.id]["school_type"]

                if school_type == "🏫 Oddiy davlat maktabi":
                    classes = [c for c in CLASSES if "🏫 Oddiy" in c]
                elif school_type == "⭐ Ixtisoslashgan (IDUM)":
                    classes = [c for c in CLASSES if "⭐ IDUM" in c]

                elif school_type == "🏆 Prezident maktabi":
                    classes = [c for c in CLASSES if "🏆 Prezident" in c]

                else:
                    classes = [c for c in CLASSES if "🏢 Xususiy" in c]

                await message.answer(
                    "Sinf tanlang:",
                    reply_markup=base_keyboard(classes)
                )

                return
            # o‘qituvchi bo‘lsa save
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO users (
                user_id, role, region,
                district, school, class
            )
            VALUES (%s, %s, %s, %s, %s, %s)
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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT role
            FROM users
            WHERE user_id=%s
            """, (message.from_user.id,))

            user = cur.fetchone()

            if not user:
                conn.close()
                return

            role = user[0]

            cur.execute("""
            SELECT *
            FROM surveys
            WHERE role=%s
            ORDER BY RANDOM()
            LIMIT 20
            """, (role,))

            surveys = cur.fetchall()

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
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
                SELECT class
                FROM users
                WHERE user_id=%s
            """, (message.from_user.id,))

            row = cur.fetchone()

            if not row:
                await message.answer(
                    "❌ Sinf topilmadi"
                )
                return

            selected_class = row[0]

            grade = re.search(r"\d+", selected_class).group()
            
            cur.execute("""
                SELECT DISTINCT subject_name
                FROM dts_tree
                WHERE grade=%s
                ORDER BY subject_name
            """, (grade,))

            print("GRADE =", grade)
          #   print("SUBJECTS =", subjects)

            subjects = cur.fetchall()

            cur.close()
            conn.close()

            buttons = []

            for (subject,) in subjects:
                buttons.append(subject)

            await message.answer(
                f"{grade}-sinf fanlari",
                reply_markup=base_keyboard(buttons)
            )
        # ===== CLASS REGISTER =====
        elif user_state.get(message.from_user.id) == "class_register":

            temp_user[message.from_user.id]["class"] = message.text

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO users (
                user_id, role, region,
                district, school, class
            )
            VALUES (%s, %s, %s, %s, %s, %s)
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

                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()

                cur.execute("""
                UPDATE users
                SET survey_done=1
                WHERE user_id=%s
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

                cls = ""
                subject = ""
                test_type = "DTS"

            # ===== O‘QITUVCHI =====
            elif role == "O‘qituvchi":

                level = "D1"
                subject = ""
                test_type = "DTS"

            else:
                await message.answer("ROLE xato ❌")
                return

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            i = 1
            count = 0

            while i < len(lines):

                if lines[i].startswith("Q:"):

                    try:

                        question = lines[i][2:].strip()

                        img = None
                        q_type = "single"
                        difficulty = "easy"
                        voice_type = "none"

                        topic = ""
                        category = ""
                        subtopic = ""

                        framework = ""
                        skill = ""

                        grade = ""
                        quarter = ""

                        steam = ""
                        future_skill = ""

                        age_group = ""
                        exam_type = ""

                        # YANGI MAYDONLAR
                        topic_code = ""
                        bloom = ""
                        timss = ""
                        pisa = ""
                        four_k = ""
                        comp = ""
                        goal = ""
                        qtype_new = "Q1"
                        src = ""
                        lang = "UZ"
                        author = ""
                        sch = ""

                        time_limit = 60
                        weight = 1
                        is_latex = False

                        track = ""
                        bob_code = ""
                        bolim_code = ""
                        mavzu_code = ""
                        kichik_mavzu_code = ""

                        audio_file = ""
                        video_file = ""
                        explanation = ""
                        answer_explanation = ""

                        data = {}

                        j = i + 1

                        while j < len(lines):

                            if lines[j].startswith("Q:"):
                                break

                            if ":" in lines[j]:
                                key, value = lines[j].split(":", 1)
                                data[key.strip().upper()] = value.strip()

                            j += 1

                        # ESKI MAYDONLAR
                        q_type = data.get("TYPE", "text")

                        img = data.get("IMG") or data.get("IMAGE")

                        category = data.get("CATEGORY", "")
                        subtopic = data.get("SUBTOPIC", "")

                        framework = data.get("FRAMEWORK", "")
                        skill = data.get("SKILL", "")

                        grade = data.get("GRADE", "")
                        quarter = data.get("QUARTER", "")

                        steam_code = data.get("STEAM", "")
                        future_skill = data.get("SKILL", "")

                        age_group = data.get("AGE_GROUP", "")
                        exam_type = data.get("EXAM_TYPE", "")

                        # YANGI STANDART

                        level = data.get("LEVEL", "D1").upper()

                        topic_code = (
                            data.get("TOPIC", "")
                            .strip()
                            .upper()
                        )

                        track = ""
                        bob_code = ""
                        bolim_code = ""
                        mavzu_code = ""
                        kichik_mavzu_code = ""

                        cur.execute("""
                        SELECT
                        grade,
                        quarter,
                        subject,
                        category,
                        topic,
                        subtopic,
                        track,
                        bob_code,
                        bolim_code,
                        mavzu_code,
                        kichik_mavzu_code
                        FROM dts_tree
                        WHERE topic_code=%s
                        """, (topic_code,))
                        dts_row = cur.fetchone()

                        if not dts_row:
                            raise Exception(
                                f"DTS topilmadi: {topic_code}"
                            )

                        grade = dts_row[0]
                        quarter = dts_row[1]
                        subject = dts_row[2]
                        category = dts_row[3]
                        topic = dts_row[4]
                        subtopic = dts_row[5]

                        track = dts_row[6]

                        bob_code = dts_row[7]
                        bolim_code = dts_row[8]
                        mavzu_code = dts_row[9]
                        kichik_mavzu_code = dts_row[10]

                        level = data.get("LEVEL", "D1").upper() 

                        bloom = data.get("BLOOM", "")
                        timss = data.get("TIMSS", "")
                        pisa = data.get("PISA", "")
                        four_k = data.get("4K", "")
                        comp = data.get("COMP", "")
                        goal = data.get("GOAL", "")

                        qtype_new = data.get("QTYPE", "Q1")

                        src = data.get("SRC", "")
                        lang = data.get("LANG", "UZ")
                        author = data.get("AUTHOR", "")
                        sch = data.get("SCH", "")

                        audio_file = data.get("AUDIO", "")
                        video_file = data.get("VIDEO", "")

                        explanation = data.get("EXPLANATION", "")
                        answer_explanation = data.get(
                            "ANSWER_EXPLANATION",
                            ""
                        )

                        try:
                            time_limit = int(
                                data.get("TIME", "60")
                            )
                        except:
                            time_limit = 60

                        try:
                            weight = int(
                                data.get("WEIGHT", "1")
                            )
                        except:
                            weight = 1

                        is_latex = (
                            data.get("LATEX", "0").upper()
                            in ["1", "YES", "TRUE"]
                        )

                        voice_type = data.get("VOICE", "none")
                        difficulty = data.get(
                            "DIFFICULTY",
                            "easy"
                        )

                        school_type = data.get(
                            "SCHOOL",
                            "all"
                        )

                        a = data.get("A")
                        b = data.get("B")
                        c = data.get("C")
                        d = data.get("D")

                        correct = (
                            data.get("ANSWER", "")
                            .strip()
                            .lower()
                        )

                        i = j - 1
                        # =========================
                        # VALIDATION
                        # =========================

                        VALID_LEVELS = {
                            "D1", "D2", "D3", "D4", "D5"
                        }

                        VALID_BLOOM = {
                            "B1", "B2", "B3",
                            "B4", "B5", "B6"
                        }

                        VALID_TIMSS = {
                            "T1", "T2", "T3"
                        }

                        VALID_PISA = {
                            "P1", "P2", "P3"
                        }

                        VALID_4K = {
                            "K1", "K2", "K3", "K4"
                        }

                        VALID_STEAM = {
                            "S1", "S2", "S3", "S4", "S5"
                        }

                        VALID_COMP = {
                            "C1", "C2", "C3", "C4", "C5"
                        }

                        VALID_GOAL = {
                            "G1", "G2", "G3", "G4", "G5"
                        }

                        VALID_QTYPE = {
                            "Q1", "Q2", "Q3", "Q4",
                            "Q5", "Q6", "Q7", "Q8",
                            "Q9", "Q10", "Q11"
                        }

                        VALID_SRC = {
                            "SRC1", "SRC2", "SRC3",
                            "SRC4", "SRC5", "SRC6",
                            "SRC7", "SRC8", "SRC9"
                        }

                        VALID_SCH = {
                            "SCH1", "SCH2", "SCH3",
                            "SCH4", "SCH5", "SCH6",
                            "SCH7"
                        }

                        VALID_LANG = {
                            "UZ", "RU", "EN", "KK"
                        }

                        VALID_ANSWERS = {
                            "a", "b", "c", "d"
                        }

                        # LEVEL
                        if level not in VALID_LEVELS:
                            level = "D1"

                        # BLOOM
                        if bloom not in VALID_BLOOM:
                            bloom = ""

                        # TIMSS
                        if timss not in VALID_TIMSS:
                            timss = ""

                        # PISA
                        if pisa not in VALID_PISA:
                            pisa = ""

                        # 4K
                        if four_k not in VALID_4K:
                            four_k = ""

                        # STEAM
                        if steam not in VALID_STEAM:
                            steam = ""

                        # COMP
                        if comp not in VALID_COMP:
                            comp = ""

                        # GOAL
                        if goal not in VALID_GOAL:
                            goal = ""

                        # QTYPE
                        if qtype_new not in VALID_QTYPE:
                            qtype_new = "Q1"

                        # SRC
                        if src not in VALID_SRC:
                            src = ""

                        # SCH
                        if sch not in VALID_SCH:
                            sch = ""

                        # LANG
                        lang = lang.upper()

                        if lang not in VALID_LANG:
                            lang = "UZ"

                        # TIME LIMIT
                        if time_limit < 10:
                            time_limit = 10

                        if time_limit > 3600:
                            time_limit = 3600

                        # WEIGHT
                        if weight < 1:
                            weight = 1

                        if weight > 10:
                            weight = 10

                        # ANSWER
                        if correct not in VALID_ANSWERS:
                            correct = "a"

                        if not topic_code:
                            raise Exception("TOPIC yo'q")

                        if not a or not b or not c or not d:
                            raise Exception("A B C D variantlar to'liq emas")

                        if correct not in ["a", "b", "c", "d"]:
                            raise Exception("ANSWER xato")

                        # IMAGE
                        if img:
                            img = img.strip()

                        # AUDIO
                        if audio_file:
                            audio_file = audio_file.strip()

                        # VIDEO
                        if video_file:
                            video_file = video_file.strip()

                        # AUTHOR
                        if author:
                            author = author[:100]

                        # TOPIC CODE
                        if topic_code:
                            topic_code = topic_code.strip().upper()

                        # QUESTION
                        question = question.strip()

                        if not question:
                            continue

                        # OPTIONS

                        if a:
                            a = a.strip()

                        if b:
                            b = b.strip()

                        if c:
                            c = c.strip()

                        if d:
                            d = d.strip()

                        # EXPLANATIONS

                        if explanation:
                            explanation = explanation.strip()

                        if answer_explanation:
                            answer_explanation = answer_explanation.strip()

                        # LATEX AUTO

                        if "\\frac" in question:
                            is_latex = True

                        if "\\sqrt" in question:
                            is_latex = True

                        if "\\sum" in question:
                            is_latex = True

                        if "\\int" in question:
                            is_latex = True

                        # AUDIO AUTO

                        if audio_file:
                            qtype_new = "Q6"

                        # IMAGE AUTO

                        if img and qtype_new == "Q1":
                            qtype_new = "Q5"

                        # VIDEO AUTO

                        if video_file:
                            qtype_new = "Q5"

                        # XP / DIFFICULTY

                        if level == "D1" and weight == 1:
                            weight = 1

                        elif level == "D2" and weight == 1:
                            weight = 2

                        elif level == "D3" and weight == 1:
                            weight = 3

                        elif level == "D4" and weight == 1:
                            weight = 4

                        elif level == "D5" and weight == 1:
                            weight = 5
                        cur.execute("""
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
                            voice_type,
                            school_type,
                            topic,
                            category,
                            subtopic,
                            framework,
                            skill,
                            grade,
                            quarter,
                            steam,
                            future_skill,
                            age_group,
                            exam_type,

                            topic_code,
                            bloom,
                            timss,
                            pisa,
                            four_k,
                            comp,
                            goal,
                            qtype,
                            src,
                            sch,
                            lang,

                            time_limit,
                            weight,
                            author,
                            is_latex,

                            audio_file,
                            video_file,
                            explanation,
                            answer_explanation,

                            track,
                            bob_code,
                            bolim_code,
                            mavzu_code,
                            kichik_mavzu_code
                        )
                        VALUES (
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,
                            %s,%s,

                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,
                            %s,

                            %s,%s,%s,%s,

                            %s,%s,%s,%s,

                            %s,%s,%s,%s,%s
                        )
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
                            voice_type,

                            school_type,
                            topic,
                            category,
                            subtopic,
                            framework,

                            skill,
                            grade,
                            quarter,
                            steam,
                            future_skill,

                            age_group,
                            exam_type,

                            topic_code,
                            bloom,
                            timss,
                            pisa,
                            four_k,

                            comp,
                            goal,
                            qtype_new,
                            src,
                            sch,

                            lang,

                            time_limit,
                            weight,
                            author,
                            is_latex,

                            audio_file,
                            video_file,
                            explanation,
                            answer_explanation,

                            track,
                            bob_code,
                            bolim_code,
                            mavzu_code,
                            kichik_mavzu_code
                        ))
                        count += 1

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

        elif action == BTN_GLOBAL:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT subject, AVG(score*1.0/total) FROM results
            GROUP BY subject
            """)

            rows = cur.fetchall()
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
        elif message.text and message.text.isdigit():

            if user_state.get(message.from_user.id) == "survey":

                value = int(message.text)

                conn = psycopg2.connect(DATABASE_URL)
                cur = conn.cursor()

                cur.execute(
                    "INSERT INTO survey (user_id, pressure) VALUES (%s, %s)",
                    (message.from_user.id, value)
                )

                # ✅ survey bajarildi
                cur.execute("""
                UPDATE users
                SET survey_done=1
                WHERE user_id=%s
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
                await message.answer("⭐ IDUM maktab raqamini kiriting (masalan: 1, 2, ...)")
            elif message.text == "🏆 Prezident maktabi":
                await message.answer("🏆 Prezident maktabi nomini yozing (masalan: Toshkent PM)")
            else:
                await message.answer("🏢 Xususiy maktab nomini yozing")
            return
            


            # ❌ noto‘g‘ri formatdagi javob

        # ===== O'ZLASHTIRISH =====
        elif message.text == "📈 O‘zlashtirish":

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute("""
            SELECT subject,
            AVG(score * 100.0 / total)
            FROM results
            WHERE user_id=%s
            GROUP BY subject
            """, (message.from_user.id,))

            rows = cur.fetchall()

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
async def test_buttons(call: CallbackQuery, state: FSMContext):

    user_id = call.from_user.id

    if call.data == "dts_import":

        await dts_import(
            call,
            state
        )

        return

    elif call.data.startswith(
        "test_grade_"
    ):

        grade = call.data.replace(
            "test_grade_",
            ""
        )

        await call.answer()

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                question,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                explanation,
                question_type,
                is_latex,
                image_url,
                audio_text,
                language,
                time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code
                FROM dts_tree
                WHERE grade=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (grade,))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        test_sessions[call.from_user.id] = {
            "questions": tests,
            "current": 0,
            "correct": 0,
            "wrong": 0
        }

        if not tests:
            await call.message.answer(
                "❌ Test topilmadi"
            )
            return

        test = tests[0]

        if image_url:

            await call.message.answer_photo(
                photo=image_url
            )

        (
            question,
            a,
            b,
            c,
            d,
            correct,
            explanation,
            question_type,
            is_latex,
            image_url,
            audio_text,
            language,
            time_limit
        ) = test

        if question_type == "write_answer":

            await call.message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:"
            )

            user_state[call.from_user.id] = "text_answer"

            return

        await call.message.answer(
            f"TYPE = {question_type}"
        )

        if question_type == "write_answer":

            await call.message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:"
            )

            set_state(
                call.from_user.id,
                "text_answer"
            )

            return


        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(a),
                        callback_data="ans_A"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(b),
                        callback_data="ans_B"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(c),
                        callback_data="ans_C"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(d),
                        callback_data="ans_D"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛑 Testni tugatish",
                        callback_data="test_stop"
                    )
                ]
            ]
        )
        await call.message.answer(
            f"⏱ {time_limit} soniya\n\n"
            f"{question}",
            reply_markup=kb
        )
        return

    if call.data.startswith("ans_"):

        user_id = call.from_user.id

        session = test_sessions.get(user_id)

        if not session:
            return

        answer = call.data.replace("ans_", "")

        current = session["current"]

        test = session["questions"][current]

        if image_url:

            await call.message.answer_photo(
                photo=image_url
            )

        (
            question,
            a,
            b,
            c,
            d,
            correct,
            explanation,
            question_type,
            is_latex,
            image_url,
            audio_text,
            language,
            time_limit
        ) = test

        if answer == "A":
            selected = str(a)

        elif answer == "B":
            selected = str(b)

        elif answer == "C":
            selected = str(c)

        else:
            selected = str(d)

        if selected.strip() == str(correct).strip():
            session["correct"] += 1
            await call.answer("✅ To'g'ri")
        else:
            session["wrong"] += 1
            await call.answer("❌ Noto'g'ri")

        session["current"] += 1

        if session["current"] >= len(session["questions"]):

            total = session["correct"] + session["wrong"]

            percent = round(
                session["correct"] * 100 / total,
                1
            ) if total else 0

            await call.message.answer(
                f"""
    🏁 Test tugadi

    ✅ To'g'ri: {session['correct']}
    ❌ Noto'g'ri: {session['wrong']}

    📊 Natija: {percent}%
    """
            )

            del test_sessions[user_id]

            return

        current = session["current"]

        test = session["questions"][current]

        if image_url:

            await call.message.answer_photo(
                photo=image_url
            )

        (
            question,
            a,
            b,
            c,
            d,
            correct,
            explanation,
            question_type,
            is_latex,
            image_url,
            audio_text,
            language,
            time_limit
        ) = test

        if question_type == "write_answer":

            user_state[user_id] = "text_answer"

            await call.message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:"
            )

            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=str(a),
                        callback_data="ans_A"
                    ),
                    InlineKeyboardButton(
                        text=str(b),
                        callback_data="ans_B"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=str(c),
                        callback_data="ans_C"
                    ),
                    InlineKeyboardButton(
                        text=str(d),
                        callback_data="ans_D"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🛑 Testni tugatish",
                        callback_data="test_stop"
                    )
                ]
            ]
        )

        await call.message.answer(
            f"⏱️ {time_limit} soniya\n\n{question}",
            reply_markup=kb
        )

        return

    elif call.data == "test_stop":

        session = test_sessions.get(
            call.from_user.id
        )

        if not session:
            return

        total = (
            session["correct"] +
            session["wrong"]
        )

        percent = round(
            session["correct"] * 100 / total,
            1
        ) if total else 0

        await call.message.answer(
            f"""
    🏁 Test tugatildi

    ✅ To'g'ri: {session['correct']}
    ❌ Noto'g'ri: {session['wrong']}

    📊 Natija: {percent}%
    """
        )

        del test_sessions[
            call.from_user.id
        ]

        return

    elif call.data == "dts_navigator":

        await dts_navigator(call)

        return   

    elif call.data.startswith(
        "dts_nav_"
    ):

        page = int(
            call.data.split("_")[-1]
        )

        await dts_navigator(
            call,
            page
        )

        return

    elif call.data.startswith(
        "dts_grade_"
    ):

        await dts_grade(call)

        return

    elif call.data.startswith(
        "dts_subject_"
    ):

        await dts_subject(call)

        return

    elif call.data.startswith(
        "dts_quarter_"
    ):

        await dts_quarter(call)

        return

    elif call.data.startswith(
        "dts_bob_"
    ):

        await dts_bob(call)

        return

    elif call.data.startswith(
        "dts_bolim_"
    ):

        await dts_bolim(call)

        return

    elif call.data.startswith(
        "dts_mavzu_"
    ):

        await dts_mavzu(call)

        return

    elif call.data.startswith(
        "dts_small_"
    ):

        await dts_small(call)

        return

    elif call.data == "dts_menu":

        await dts_menu(call.message)

        return

    elif call.data == "dts_confirm_import":

        await dts_confirm_import(call)

        return

    elif call.data == "dts_problems":

        await dts_problems(call)

        return

    elif call.data == "dts_download_errors":

        await dts_download_errors(call)

        return

    elif call.data == "dts_cancel_import":

        await dts_cancel_import(call)

        return

    # =========================
    # test_buttons
    # =========================

    elif call.data == "dts_search":
        await dts_search(call)
        return

    elif call.data == "dts_fast_search":
        await dts_fast_search(
            call,
            state
        )
        return

    elif call.data == "dts_adv_search":
        await dts_adv_search(call)
        return

    elif call.data.startswith(
        "dts_adv_grade_"
    ):
        await dts_adv_grade(call)
        return

    elif call.data == "dts_export":

        await dts_export(call)

        return

    elif user_id not in user_test:
        await call.answer(
            "♻️ Bot yangilangan.  qayta boshlang.",
            show_alert=True
        )
        return
    await call.answer()

    test = user_test[user_id]

    if call.data == "finish":

        await call.message.answer(
            "Testni tugatmoqchimisiz?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Ha",
                            callback_data="finish_yes"
                        ),
                        InlineKeyboardButton(
                            text="❌ Yo‘q",
                            callback_data="finish_no"
                        )
                    ]
                ]
            )
        )
        return

    if call.data == "finish_no":

        await call.message.delete()

        return
  
    if call.data == "finish_yes":

        try:
            if test.get("timer_task"):
                test["timer_task"].cancel()
        except:
            pass

        score = test["score"]
        total = len(test["questions"])

        await call.message.answer(
            f"🏁 Test tugadi\n\n📊 Natija: {score}/{total}"
        )

        user_test.pop(user_id, None)
        user_state[user_id] = None

        return
    if test.get("expired", False):
        await call.answer(
            "⏰ Vaqt tugagan"
        )
        return

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
        await call.answer(
            "Bu savolga javob berilgan ✅"
        )
        return

    test["answered"] = True
    try:
        if test.get("timer_task"):
            test["timer_task"].cancel()
    except:
        pass

    q = test["questions"][test["index"]]
    old_q = q

    if ":" in call.data:

        user_ans, uid = call.data.split(":")

        if str(test["question_uid"]) != uid:
            await call.answer(
                "Bu eski savol ⏳"
            )
            return

    else:
        user_ans = call.data

    correct = old_q[10].lower()

    subject = old_q[4]

    topic = old_q[17]
    category = old_q[18]
    subtopic = old_q[19]
    topic_code = old_q[28]
    cur.execute("""
    SELECT
    quarter,
    track
    FROM dts_tree
    WHERE topic_code=%s
    """, (topic_code,))

    dts_row = cur.fetchone()

    quarter_code = None
    track_code = None

    if dts_row:
        quarter_code = dts_row[0]
        track_code = dts_row[1]

    bloom = old_q[29]
    timss = old_q[30]
    pisa = old_q[31]
    four_k = old_q[32]
    comp = old_q[33]
    goal = old_q[34]

    level = old_q[3]

    if user_ans == correct:

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # student_progress
        cur.execute("""
        INSERT INTO student_progress
        (user_id, subject, category, topic, subtopic,
        correct, wrong)
        VALUES (%s,%s,%s,%s,%s,1,0)
        ON CONFLICT (
            user_id,
            subject,
            category,
            topic,
            subtopic
        )
        DO UPDATE SET
        correct = student_progress.correct + 1,
        last_update = NOW()
        """, (
            user_id,
            subject,
            category,
            topic,
            subtopic
        ))

        # topic_progress
        cur.execute("""
        INSERT INTO topic_progress
        (user_id, topic_code, correct, wrong)
        VALUES (%s,%s,1,0)
        ON CONFLICT (user_id, topic_code)
        DO UPDATE SET
        correct = topic_progress.correct + 1
        """, (
            user_id,
            topic_code
        ))

        # level_progress
        cur.execute("""
        INSERT INTO level_progress
        (user_id, level_code, correct, wrong)
        VALUES (%s,%s,1,0)
        ON CONFLICT (user_id, level_code)
        DO UPDATE SET
        correct = level_progress.correct + 1
        """, (
            user_id,
            level
        ))

        # bloom
        cur.execute("""
        INSERT INTO framework_progress
        (
            user_id,
            framework_type,
            framework_code,
            correct,
            wrong
        )
        VALUES (%s,'BLOOM',%s,1,0)
        ON CONFLICT (
            user_id,
            framework_type,
            framework_code
        )
        DO UPDATE SET
        correct = framework_progress.correct + 1
        """, (
            user_id,
            bloom
        ))

        conn.commit()
        conn.close()

        test["score"] += 1

        result_text = "🎉 ✅ To‘g‘ri"

    else:

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # student_progress

        cur.execute("""
        INSERT INTO student_progress
        (
            user_id,
            subject,
            category,
            topic,
            subtopic,
            correct,
            wrong
        )
        VALUES (%s,%s,%s,%s,%s,0,1)
        ON CONFLICT (
            user_id,
            subject,
            category,
            topic,
            subtopic
        )
        DO UPDATE SET
        wrong = student_progress.wrong + 1,
        last_update = NOW()
        """, (
            user_id,
            subject,
            category,
            topic,
            subtopic
        ))

        # topic_progress

        cur.execute("""
        INSERT INTO topic_progress
        (
            user_id,
            topic_code,
            correct,
            wrong
        )
        VALUES (%s,%s,0,1)
        ON CONFLICT (
            user_id,
            topic_code
        )
        DO UPDATE SET
        wrong = topic_progress.wrong + 1
        """, (
            user_id,
            topic_code
        ))

        # level_progress

        cur.execute("""
        INSERT INTO level_progress
        (
            user_id,
            level_code,
            correct,
            wrong
        )
        VALUES (%s,%s,0,1)
        ON CONFLICT (
            user_id,
            level_code
        )
        DO UPDATE SET
        wrong = level_progress.wrong + 1
        """, (
            user_id,
            level
        ))

        # BLOOM

        cur.execute("""
        INSERT INTO framework_progress
        (
            user_id,
            framework_type,
            framework_code,
            correct,
            wrong
        )
        VALUES (%s,'BLOOM',%s,0,1)
        ON CONFLICT (
            user_id,
            framework_type,
            framework_code
        )
        DO UPDATE SET
        wrong = framework_progress.wrong + 1
        """, (
            user_id,
            bloom
        ))

        conn.commit()
        conn.close()

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                "SELECT file_id FROM images WHERE name=%s",
                (q[14],)
            )

            row = cur.fetchone()

            conn.close()

            if row:
                await bot.send_photo(
                    call.message.chat.id,
                    photo=row[0]
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
                    ],[
                        InlineKeyboardButton(
                            text="❌ Testni tugatish",
                            callback_data="finish"
                        ) 
                    ]
                ]
            )
        await call.message.answer(
            "keyingi savol",
            reply_markup=ReplyKeyboardRemove()
        )

        msg = await call.message.answer(
            f"{result_text}\n\n{text}",
            reply_markup=markup
        )  
       
        if q[15] in ["uz", "ru", 
        "en"]:

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

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
        SELECT role
        FROM users
        WHERE user_id=%s
        """, (user_id,))

        row = cur.fetchone()

        conn.close()

        role = row[0] if row else "O‘quvchi"

        await call.message.answer(
            "🏠 Bosh menyu",
            reply_markup=get_main_keyboard(role)
        )

async def question_timer(user_id, limit):

    if user_id not in user_test:
        return

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

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                "SELECT file_id FROM images WHERE name=%s",
                (q[14],)
            )

            row = cur.fetchone()

            conn.close()

            if row:
                await bot.send_photo(
                    user_id,
                    photo=row[0]
                )      
             # LATEX
        if q[13] and "latex" in str(q[13]).lower():

            latex = q[5]

            encoded = quote(
                f"\\dpi{{300}} \\huge {latex}"
            )

            url = f"https://latex.codecogs.com/png.image?{encoded}"

            await bot.send_photo(
                user_id,
                photo=url
            )

            text = "Savol rasmi yuqorida ⬆️"
            
        if q[13] and "latex" in str(q[13]).lower():
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
                            ],[
                                InlineKeyboardButton(
                                    text="❌ Testni tugatish",
                                    callback_data="finish"
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
