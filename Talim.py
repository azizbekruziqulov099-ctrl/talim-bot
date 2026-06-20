from admin_handlers import *
from learning import *
from generator_handlers import *
from test_engine import *
from register import *
from learning import continue_learning
import asyncio
from aiogram.types import ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, types
from urllib.parse import quote
from aiogram.filters import *
from dts_import_handlers import *
from ai_generatori import *
from storage import user_state, temp_user
from keyboards import get_main_keyboard
from loader import dp, bot
from test_generator import save_test
from aiogram import F
import pandas as pd
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from learning import (
    lesson_next,
    lesson_prev,
    lesson_tts,
    lesson_tts_help,
    lesson_back_main,
    lesson_consolidation_test,
    lesson_test_answer,
    send_test_question,
    lesson_review_start,
    lesson_review_answer,
    send_review_question,
    start_main_lesson,
    open_teacher_lesson,
    continue_learning
)
import lesson_admin
import student_dashboard
import json
import random
import time
import edge_tts
from aiogram.types import FSInputFile
import psycopg2
import re
import os
import subprocess
from openpyxl import Workbook
from openpyxl.styles import Font

with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

ADMINS = [401251407]

DATABASE_URL = os.getenv("DATABASE_URL")
API_TOKEN = os.getenv("BOT_TOKEN")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

user_locks = {}
admin_state = {}
state_history = {}
generator_process = None
topic_stats_state = {}

wb = Workbook()

# README
ws1 = wb.active
ws1.title = "README"

ws1["A1"] = "DIFFICULTY"
ws1["A1"].font = Font(bold=True)

ws1["A2"] = "oson"
ws1["A3"] = "o'rta"
ws1["A4"] = "qiyin"
ws1["A5"] = "murakkab"

ws1["C1"] = "QUESTION_TYPE"
ws1["C1"].font = Font(bold=True)

ws1["C2"] = "single_choice"
ws1["C3"] = "multiple_choice"
ws1["C4"] = "true_false"
ws1["C5"] = "write_answer"
ws1["C6"] = "image_question"

ws1["E1"] = "LIFE_LEVEL"
ws1["E1"].font = Font(bold=True)

ws1["E2"] = "0"
ws1["E3"] = "1"
ws1["E4"] = "2"
ws1["E5"] = "3"
ws1["E6"] = "4"

ws1["G1"] = "LANGUAGE"
ws1["G1"].font = Font(bold=True)

ws1["G2"] = "uz"
ws1["G3"] = "ru"
ws1["G4"] = "en"


# TESTLAR
ws2 = wb.create_sheet("TESTLAR")

headers = [
    "topic_code",
    "difficulty",
    "situation",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer",
    "explanation",
    "question_type",
    "is_latex",
    "image_url",
    "audio_text",
    "language",
    "life_level",
    "age_group",
    "time_limit"
]

for col_num, header in enumerate(headers, start=1):
    cell = ws2.cell(row=1, column=col_num)
    cell.value = header
    cell.font = Font(bold=True)


# NAMUNA
ws3 = wb.create_sheet("NAMUNA")

ws3.append(headers)

ws3.append([
    "_1_01_01_01_01_001",
    "oson",
    "oddiy",
    "What animal gives us milk?",
    "Cow",
    "Cat",
    "Dog",
    "Horse",
    "Cow",
    "A cow gives milk",
    "single_choice",
    False,
    "",
    "",
    "uz",
    1,
    "10-11",
    60
])

wb.save("test_import_template.xlsx")

print("test_import_template.xlsx yaratildi")

# BUTTON ID (faqat shu bilan ishlaymiz)
BTN_SURVEY = "survey"
BTN_STATS = "stats"

BTN_MY = "my_stats"
BTN_GLOBAL = "global_stats"

BACK = "🔙 Ortga"
HOME = "🏠 Bosh menyu"

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

ZERO_TEST_TYPES = [
    "🔤 Harflar",
    "📖 So‘zlar",
    "🖼 Rasmli o‘yin",
    "🎵 Eshit va top",
    "🎁 Aralash"
]

def set_state(user_id, state):

    user_state[user_id] = state

    if user_id not in state_history:
        state_history[user_id] = []

    state_history[user_id].append(state)

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

    # subject ustuni — eski DB uchun
    cur.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS subject TEXT
    """)

    # Dars tarixi — takrorlash va statistika uchun
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lesson_history (
        id          SERIAL PRIMARY KEY,
        user_id     INTEGER NOT NULL,
        topic_code  TEXT NOT NULL,
        mavzu       TEXT,
        fan         TEXT,
        score       INTEGER DEFAULT 0,
        total       INTEGER DEFAULT 0,
        learned_at  TIMESTAMP DEFAULT NOW()
    )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_lesson_history_user
        ON lesson_history(user_id, learned_at DESC)
    """)

    conn.commit()
    conn.close()

def get_grades():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT grade
        FROM dts_tree
        ORDER BY grade
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]

def get_subjects_by_grade(grade):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT subject_name
        FROM dts_tree
        WHERE grade = %s
        ORDER BY subject_name
    """, (grade,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [row[0] for row in rows]

def get_topics_by_grade_subject(
    grade,
    subject_name
):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            topic_code,
            kichik_name
        FROM dts_tree
        WHERE grade = %s
        AND subject_name = %s
        ORDER BY topic_code
    """, (
        grade,
        subject_name
    ))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def get_topic_name(topic_code):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            grade,
            subject_name,
            quarter,
            bob_name,
            bolim_name,
            mavzu_name,
            kichik_name
        FROM dts_tree
        WHERE topic_code=%s
        LIMIT 1
    """, (topic_code,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row

def get_topic_test_count(topic_code):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM generated_tests
        WHERE topic_code=%s
    """, (topic_code,))

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return count

def get_topic_statistics(topic_code):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT

            COUNT(*) as total,

            SUM(
                CASE
                WHEN difficulty='oson'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN difficulty='o''rta'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN difficulty='qiyin'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN difficulty='murakkab'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN question_type='single_choice'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN question_type='multiple_choice'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN question_type='true_false'
                THEN 1
                ELSE 0
                END
            ),

            SUM(
                CASE
                WHEN question_type='write_answer'
                THEN 1
                ELSE 0
                END
            )

        FROM generated_tests
        WHERE topic_code=%s
    """, (topic_code,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row

async def show_topics_page(
    message,
    user_id
):

    data = topic_stats_state[user_id]

    topics = data["topics"]
    page = data["page"]

    start = page * 10
    end = start + 10

    current_topics = topics[start:end]

    keyboard = []

    text = "📚 MAVZULAR\n\n"

    for row in current_topics:

        topic_code = row[0]
        kichik_name = row[1]

        count = get_topic_test_count(
            topic_code
        )

        keyboard.append([
            KeyboardButton(
                text=f"{kichik_name} ({count})"
            )
        ])

        topic_stats_state[user_id][
            f"topic_{kichik_name} ({count})"
        ] = topic_code

    keyboard.append([
        KeyboardButton(text="⬅️ Oldingi"),
        KeyboardButton(text="➡️ Keyingi")
    ])

    keyboard.append([
        KeyboardButton(text="🔍 Mavzu qidirish")
    ])

    keyboard.append([
        KeyboardButton(text="🔙 Ortga")
    ])

    await message.answer(
        text,
        reply_markup=ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        )
    )
    
@dp.message(F.photo)
async def save_image(message: types.Message):
    if message.from_user.id not in ADMINS:
        return
    if not message.caption:
        await message.answer(
            "Rasm nomini captionga yozing")
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
        f"✅ Saqlandi: {name}")

# ====== START ======
@dp.message(CommandStart())
async def start(message: types.Message):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute(
        "SELECT role, full_name, class FROM users WHERE user_id=%s",
        (message.from_user.id,)
    )

    user = cur.fetchone()

    conn.close()

    # RO'YXATDAN O'TGAN FOYDALANUVCHI
    if user:

        role, full_name, grade = user

        if message.from_user.id in ADMINS:
            role = "Admin"

        if role == "Admin":
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}",
                reply_markup=get_main_keyboard(role)
            )
            return

        # O'quvchi uchun yoshga mos kutib olish
        if "quvchi" in role.lower() or role.strip() in ("🧒 O'quvchi", "🧒O'quvchi", "O'quvchi"):

            from progress import update_streak
            from student_dashboard import build_dashboard

            update_streak(message.from_user.id)

            text, keyboard = await build_dashboard(message.from_user.id)

            # Majburiy imtihon bormi?
            from progress import get_pending_exams
            pending   = get_pending_exams(message.from_user.id)
            mandatory = [e for e in pending if e[3]]

            if mandatory:
                exam = mandatory[0]
                await message.answer(
                    f"{text}\n\n"
                    f"🚨 MAJBURIY IMTIHON:\n"
                    f"📘 {exam[1]}\n"
                    f"📅 Sana: {exam[2]}",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text="▶️ Imtihonni boshlash",
                                callback_data=f"exam_start_{exam[0]}"
                            )],
                            [InlineKeyboardButton(
                                text="⏭ Keyinroq",
                                callback_data="exam_later"
                            )]
                        ]
                    )
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard
                )
                await message.answer(
                    "👇",
                    reply_markup=get_main_keyboard(role)
                )
        else:
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}",
                reply_markup=get_main_keyboard(role)
            )

        return

    # YANGI FOYDALANUVCHI
    user_state[message.from_user.id] = "role"

    await message.answer(
        "🎓 TA'LIM PLATFORMASI\n\n"
        "Xush kelibsiz!\n\n"
        "Platformadan foydalanish uchun "
        "o'zingizga mos rolni tanlang.",
        reply_markup=make_keyboard([
            "🧒 O‘quvchi",
            "👨‍🏫 O‘qituvchi",
            "👨‍👩‍👧 Ota-ona"
        ])
    )

async def import_tests_excel(message):

    file = await bot.get_file(
        message.document.file_id
    )

    path = "temp_import.xlsx"

    await bot.download_file(
        file.file_path,
        path
    )

    df = pd.read_excel(path,sheet_name="TESTLAR")

    success = 0
    duplicates = 0
    errors = 0

    error_rows = []

    for index, row in df.iterrows():

        try:

            test_data = {
                "topic_code": str(row["topic_code"]).strip(),
                "difficulty": str(row["difficulty"]).strip(),
                "situation": "" if pd.isna(row["situation"]) else str(row["situation"]),
                "question": str(row["question"]).strip(),
                "option_a": "" if pd.isna(row["option_a"]) else str(row["option_a"]),
                "option_b": "" if pd.isna(row["option_b"]) else str(row["option_b"]),
                "option_c": "" if pd.isna(row["option_c"]) else str(row["option_c"]),
                "option_d": "" if pd.isna(row["option_d"]) else str(row["option_d"]),
                "correct_answer": str(row["correct_answer"]).strip(),
                "explanation": "" if pd.isna(row["explanation"]) else str(row["explanation"]),
                "question_type": str(row["question_type"]).strip(),
                "is_latex": False if pd.isna(row["is_latex"]) else row["is_latex"],
                "image_url": None if pd.isna(row["image_url"]) else str(row["image_url"]),
                "audio_text": None if pd.isna(row["audio_text"]) else str(row["audio_text"]),
                "language": "uz" if pd.isna(row["language"]) else str(row["language"]),
                "life_level": 1 if pd.isna(row["life_level"]) else int(row["life_level"]),
                "age_group": None if pd.isna(row["age_group"]) else str(row["age_group"]),
                "time_limit": 60 if pd.isna(row["time_limit"]) else int(row["time_limit"])
            }

            result = save_test(test_data)

            if result == "saved":
                success += 1

            elif result == "duplicate":

                duplicates += 1

                error_rows.append({
                    "row_number": index + 2,
                    "question": row.get("question"),
                    "error": "Duplikat yoki o'xshash savol"
                })

            else:
                errors += 1

        except Exception as e:

            errors += 1

            error_rows.append({
                "row_number": index + 2,
                "question": row.get("question"),
                "error": str(e)
            })

    if error_rows:

        error_file = "import_errors.xlsx"

        df_errors = pd.DataFrame(error_rows)

        df_errors.to_excel(
            error_file,
            index=False
        )

    await message.answer(
        f"✅ Import tugadi\n\n"
        f"📥 Saqlandi: {success}\n"
        f"⚠️ Duplikat: {duplicates}\n"
        f"❌ Xato: {errors}"
    )

    if error_rows:

        await message.answer_document(
            FSInputFile("import_errors.xlsx"),
            caption="📋 Import xatolari hisoboti"
        )

    admin_state[message.from_user.id] = None

@dp.message()
async def handle_all(
    message: Message,
    state: FSMContext
):
    
    user_id = message.from_user.id

    # Test paytida yozilgan xabarni o'chirish
    from test_engine import test_sessions
    if user_id in test_sessions:
        if user_state.get(user_id) != "text_answer":
            try:
                await message.delete()
            except Exception:
                pass
            return

    # Dars paytida yozilgan xabarni avtomatik o'chirish
    if isinstance(user_state.get(user_id), dict):
        if user_state[user_id].get("board_message_id"):
            try:
                await message.delete()
            except Exception:
                pass

    if message.text == "🧪 Bilimni sinash":
        await message.answer(
            "🧪 Bilimni sinash\n\nQanday test ishlaysiz?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="⚡ Tezkor test (20 ta, aralash)",
                        callback_data="tset_start_quick"
                    )],
                    [InlineKeyboardButton(
                        text="⚙️ Sozlamalar bilan boshlash",
                        callback_data="test_settings"
                    )],
                    [InlineKeyboardButton(
                        text="📚 Navigator (fan/mavzu tanlash)",
                        callback_data="dts_navigator"
                    )],
                ]
            )
        )
        return

    if message.text == "🎯 Bugungi reja":
        await continue_learning(message)
        return

    if message.text == "🔊 O'qib berish":

        await read_current_page(
            message.from_user.id,
            message,
            user_state
        )

        return

    if message.text == "▶️ O'rganishni boshlash":

        await open_teacher_lesson(message)

        return

    if message.text == "📈 Rivojlanishim":
        await student_progress(message)
        return

    if message.text == "🌍 Hamjamiyat":
        await student_community(message)
        return

    if message.text == "👤 Kabinet":
        await student_profile(message)
        return

    if user_id not in temp_user:
        temp_user[user_id] = {}

    if user_id not in user_state:
        user_state[user_id] = None

    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    # REGISTRATSIYA
    if user_state.get(user_id):

        await register_handler(message)
        return

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

    if (
        admin_state.get(user_id) == "dts_import"
        and message.document
    ):

        await dts_excel_import(
            message,
            state
        )

        return

    if (
        admin_state.get(user_id) == "test_import"
        and message.document
    ):

        await import_tests_excel(
            message
        )

        return

    if user_state.get(message.from_user.id) == "text_answer":

        await check_text_answer(
            message.from_user.id,
            message.text,
            message
        )

        return

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
                    [KeyboardButton(text="📄 Excel shablon"),
                    KeyboardButton(text="📥 Test import qilish")],
                    [KeyboardButton(text="📚 Mavzular statistikasi"),
                    KeyboardButton(text="▶️ Generatorni boshlash")],
                    [KeyboardButton(text="⏹ Generatorni to‘xtatish"),
                    KeyboardButton(text="📊 Generator statistikasi")],
                    [KeyboardButton(text="📚 Mavzular statistikasi"),
                    KeyboardButton(text="🔙 Ortga")]
                ],               
                  resize_keyboard=True
            )
        )

        return

    elif message.text == "📚 Mavzular statistikasi":

        grades = get_grades()

        keyboard = []

        for grade in grades:

            keyboard.append([
                KeyboardButton(
                    text=f"{grade}-sinf"
                )
            ])

        keyboard.append([
            KeyboardButton(text="🔙 Ortga")
        ])

        await message.answer(
            "📚 Sinfni tanlang",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True
            )
        )

        return

    elif message.text.endswith("-sinf"):

        grade = message.text.replace("-sinf", "")

        topic_stats_state[user_id] = {
            "grade": grade,
            "level": "subjects"
        }

        subjects = get_subjects_by_grade(
            grade
        )

        keyboard = []

        for subject in subjects:

            keyboard.append([
                KeyboardButton(text=subject)
            ])

        keyboard.append([
            KeyboardButton(text="🔙 Ortga")
        ])

        await message.answer(
            "📖 Fanni tanlang",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True
            )
        )

        return

    elif (
        user_id in topic_stats_state
        and f"topic_{message.text}" in topic_stats_state[user_id]
    ):
        topic_stats_state[user_id]["level"] = "topic_stats"
        topic_code = topic_stats_state[user_id][
            f"topic_{message.text}"
        ]

        info = get_topic_name(topic_code)
        stats = get_topic_statistics(topic_code)

        topic_stats_state[user_id]["selected_topic"] = topic_code

        await message.answer(
            f"🔑 {topic_code}\n\n"

            f"🎓 Sinf: {info[0]}\n"
            f"📚 Fan: {info[1]}\n"
            f"🗓 Chorak: {info[2]}\n"
            f"📖 Bob: {info[3]}\n"
            f"📂 Bo'lim: {info[4]}\n"
            f"📘 Mavzu: {info[5]}\n"
            f"📌 Kichik mavzu: {info[6]}\n\n"

            f"📊 Jami test: {stats[0]}\n"
            f"🟢 Oson: {stats[1] or 0}\n"
            f"🟡 O'rta: {stats[2] or 0}\n"
            f"🟠 Qiyin: {stats[3] or 0}\n"
            f"🔴 Murakkab: {stats[4] or 0}",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📄 Excel shablon")],
                    [KeyboardButton(text="📥 Test import qilish")],
                    [KeyboardButton(text="🔙 Ortga")]
                ],
                resize_keyboard=True
            )
        )

        return


    elif message.text == "📥 Test import qilish":

        admin_state[user_id] = "test_import"

        await message.answer(
            "Excel fayl yuboring"
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
        user_id in topic_stats_state
        and "grade" in topic_stats_state[user_id]
        and "topics" not in topic_stats_state[user_id]
    ):

        grade = topic_stats_state[user_id]["grade"]

        subject_name = message.text

        topics = get_topics_by_grade_subject(
            grade,
            subject_name
        )

        topic_stats_state[user_id]["subject"] = subject_name
        topic_stats_state[user_id]["topics"] = topics
        topic_stats_state[user_id]["page"] = 0
        topic_stats_state[user_id]["level"] = "topics"

        await show_topics_page(
            message,
            user_id
        )

        return

    elif message.text == "⬅️ Oldingi":

        if user_id not in topic_stats_state:
            return

        if topic_stats_state[user_id]["page"] > 0:

            topic_stats_state[user_id]["page"] -= 1

        await show_topics_page(
            message,
            user_id
        )

        return

    elif message.text == "➡️ Keyingi":

        if user_id not in topic_stats_state:
            return

        total = len(
            topic_stats_state[user_id]["topics"]
        )

        current_page = topic_stats_state[user_id]["page"]

        max_page = (total - 1) // 10

        if current_page < max_page:

            topic_stats_state[user_id]["page"] += 1

        await show_topics_page(
            message,
            user_id
        )

        return

    elif message.text == "🔙 Ortga":

        if user_id not in topic_stats_state:
            return

        level = topic_stats_state[user_id].get("level")

        if level == "topic_stats":

            topic_stats_state[user_id]["level"] = "topics"

            await show_topics_page(
                message,
                user_id
            )

            return

        elif level == "topics":

            grade = topic_stats_state[user_id]["grade"]

            keyboards = []

            subjects = get_subjects_by_grade(
                grade
            )

            for subject in subjects:
                keyboards.append([
                    KeyboardButton(
                        text=subject
                    )
                ])

            keyboards.append([
                KeyboardButton(
                    text="🔙 Ortga"
                )
            ])

            topic_stats_state[user_id]["level"] = "subjects"

            await message.answer(
                "📖 Fanni tanlang",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboards,
                    resize_keyboard=True
                )
            )

            return

        elif level == "subjects":

            grade = topic_stats_state[user_id]["grade"]

            subjects = get_subjects_by_grade(
                grade
            )

            keyboard = []

            for subject in subjects:

                keyboard.append([
                    KeyboardButton(
                        text=subject
                    )
                ])

            keyboard.append([
                KeyboardButton(
                    text="🔙 Ortga"
                )
            ])

            await message.answer(
                "📖 Fanni tanlang",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True
                )
            )

            return

    elif "-" in message.text:

        topic_code = message.text.strip()

        info = get_topic_name(
            topic_code
        )

        if not info:
            return

        stats = get_topic_statistics(
            topic_code
        )

        mavzu = info[0]
        kichik = info[1]

        await message.answer(

            f"🔑 {topic_code}\n\n"

            f"📖 Mavzu:\n"
            f"{mavzu}\n\n"

            f"📌 Kichik mavzu:\n"
            f"{kichik}\n\n"

            f"📊 Jami test: {stats[0]}\n\n"

            f"🟢 Oson: {stats[1] or 0}\n"
            f"🟡 O'rta: {stats[2] or 0}\n"
            f"🟠 Qiyin: {stats[3] or 0}\n"
            f"🔴 Murakkab: {stats[4] or 0}\n\n"

            f"📝 Single choice: {stats[5] or 0}\n"
            f"☑️ Multiple choice: {stats[6] or 0}\n"
            f"✅ True/False: {stats[7] or 0}\n"
            f"✍️ Write answer: {stats[8] or 0}"
        )

        return

    elif message.text == "📄 Excel shablon":

        await message.answer_document(
            FSInputFile("test_import_template.xlsx"),
            caption="📋 Test import shabloni"
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

        cur.execute("""
            SELECT COUNT(*)
            FROM dts_tree
        """)
        total_topics = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(DISTINCT topic_code)
            FROM generated_tests
        """)
        completed_topics = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM generated_tests
        """)
        total_tests = cur.fetchone()[0]

        remaining_topics = total_topics - completed_topics

        progress = round(
            completed_topics * 100 / total_topics,
            1
        ) if total_topics else 0

        cur.close()
        conn.close()

        await message.answer(
            f"📚 Jami mavzular: {total_topics}\n"
            f"✅ Test yaratilgan mavzular: {completed_topics}\n"
            f"❌ Qolgan mavzular: {remaining_topics}\n"
            f"📝 Jami testlar: {total_tests}\n"
            f"📈 Progress: {progress}%"
        )

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

      #  action = TEXT_TO_ID.get(message.text)

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
            cur.execute("SELECT role FROM users WHERE user_id=%s", (message.from_user.id,))
            user = cur.fetchone()
            conn.close()

            role = user[0] if user else None
            user_state[message.from_user.id] = None

            # Oxirgi 10 xabarni o'chirish
            try:
                for i in range(message.message_id - 1, message.message_id - 15, -1):
                    try:
                        await message.bot.delete_message(message.chat.id, i)
                    except Exception:
                        pass
            except Exception:
                pass

            from student_dashboard import build_dashboard
            try:
                text, kb = await build_dashboard(message.from_user.id)
                await message.answer(text, reply_markup=kb)
            except Exception:
                pass
            await message.answer("👇 Menyu:", reply_markup=get_main_keyboard(role))
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
                reply_markup=make_keyboard(["🧒 O‘quvchi", "👨‍🏫 O‘qituvchi"])
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

            role = row[0] if row else "🧒 O‘quvchi"

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

            role = row[0] if row else "🧒 O‘quvchi"

            user_state[message.from_user.id] = None

            await message.answer(
                f"✅ Sinf o‘zgartirildi: {message.text}",
                reply_markup=get_main_keyboard(role)
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

@dp.callback_query()
async def test_buttons(call: CallbackQuery, state: FSMContext):

    user_id = call.from_user.id

    if call.data.startswith("next_lesson_"):
        topic_code = call.data.replace("next_lesson_", "")
        await open_teacher_lesson(call.message, topic_code, _user_id=call.from_user.id)
        await call.answer()
        return

    if call.data == "go_home_dashboard":
        await call.answer()
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s", (call.from_user.id,))
        row = cur2.fetchone()
        cur2.close(); conn2.close()
        role = row[0] if row else "🧒 O'quvchi"
        try:
            from student_dashboard import build_dashboard
            text, kb = await build_dashboard(call.from_user.id)
            await call.message.answer(text, reply_markup=kb)
        except Exception:
            pass
        await call.message.answer("Bosh menyu:", reply_markup=get_main_keyboard(role))
        return

    if call.data == "go_home":
        await call.answer()
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s", (call.from_user.id,))
        row = cur2.fetchone()
        cur2.close(); conn2.close()
        role = row[0] if row else "🧒 O'quvchi"
        await call.message.answer(
            "🏠 Asosiy menyu",
            reply_markup=get_main_keyboard(role)
        )
        return

    if call.data == "lesson_continue":
        await call.answer()
        await call.message.delete()
        # call.message.from_user yo'q — shuning uchun alohida yuboring
        await open_teacher_lesson(call.message, _user_id=call.from_user.id)
        return

    if call.data == "lesson_repeat":
        from progress import get_repeat_topics
        topics = get_repeat_topics(call.from_user.id)
        if topics:
            topic_code = topics[0][0]
            await open_teacher_lesson(call.message, topic_code, _user_id=call.from_user.id)
        else:
            await call.answer("Takrorlanadigan mavzu yo'q!", show_alert=True)
        await call.answer()
        return

    if call.data.startswith("fan_select|"):
        parts      = call.data.split("|")
        grade      = parts[1]
        subj       = parts[2]
        from progress import get_next_topic
        next_topic = get_next_topic(call.from_user.id, grade, None)
        if next_topic and next_topic[3] == subj:
            await open_teacher_lesson(call.message, next_topic[0], _user_id=call.from_user.id)
        else:
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2  = conn2.cursor()
            cur2.execute("""
                SELECT t.topic_code FROM dts_tree t
                LEFT JOIN learned_topics lt
                    ON lt.topic_code=t.topic_code AND lt.user_id=%s
                WHERE t.grade=%s AND t.subject_name=%s
                  AND lt.topic_code IS NULL AND t.is_deleted=FALSE
                ORDER BY t.topic_code LIMIT 1
            """, (call.from_user.id, grade, subj))
            row = cur2.fetchone()
            cur2.close(); conn2.close()
            if row:
                await open_teacher_lesson(call.message, row[0], _user_id=call.from_user.id)
            else:
                await call.answer(f"✅ {subj} tugallangan!", show_alert=True)
        await call.answer()
        return

    if call.data == "exam_later":
        await call.answer("⏰ Keyinroq eslatiladi")
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id=%s", (call.from_user.id,))
        row  = cur.fetchone()
        cur.close(); conn.close()
        role = row[0] if row else "🧒 O'quvchi"
        await call.message.delete()
        await call.message.answer("🏠 Asosiy menyu", reply_markup=get_main_keyboard(role))
        return

    if call.data == "dts_import":

        await dts_import(
            call,
            state
        )

        return


    if call.data.startswith("ans_"):

        answer = call.data.replace(
            "ans_",
            ""
        )

        await check_button_answer(
            call.from_user.id,
            answer,
            call.message
        )

        return

    if call.data == "test_stop":
        await call.answer()
        await call.message.answer(
            "🛑 Testni to'xtatmoqchimisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Ha, to'xtat", callback_data="test_stop_yes"),
                InlineKeyboardButton(text="❌ Yo'q, davom", callback_data="test_stop_no"),
            ]])
        )
        return

    if call.data == "test_stop_yes":
        await call.answer()
        await stop_test(call.from_user.id, call.message)
        return

    if call.data == "test_stop_no":
        await call.answer("Davom etilmoqda!")
        try:
            await call.message.delete()
        except Exception:
            pass
        return

    if call.data == "speak_question":

        await speak_question(
            call.from_user.id,
            call.message
        )

        return

    if call.data == "speak_a":

        await speak_a(
            call.from_user.id,
            call.message
        )

        return

    if call.data == "speak_b":

        await speak_b(
            call.from_user.id,
            call.message
        )
        return

    if call.data == "speak_c":

        await speak_c(
            call.from_user.id,
            call.message
        )
        return

    if call.data == "speak_d":

        await speak_d(
            call.from_user.id,
            call.message
        )
        return

    if call.data == "lesson_prev":

        print(f"DEBUG: lesson_prev called by {call.from_user.id}")

        await lesson_prev(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "lesson_next":

        await lesson_next(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "review_start":

        await lesson_review_start(
            call.from_user.id,
            call.message
        )
        await call.answer()
        return

    if call.data == "review_skip":

        user_id   = call.from_user.id
        parts     = user_state.get(user_id, {}).get("parts", [])
        full_name = user_state.get(user_id, {}).get("full_name", "O'quvchi")
        sinf      = user_state.get(user_id, {}).get("sinf", "")
        fan       = user_state.get(user_id, {}).get("fan", "")
        mavzu     = user_state.get(user_id, {}).get("mavzu", "")
        bugun     = user_state.get(user_id, {}).get("bugun", "")

        await start_main_lesson(
            call.message, user_id,
            parts, full_name, sinf, fan, mavzu, bugun
        )
        await call.answer()
        return

    if call.data.startswith("review_answer_"):

        answer = call.data.replace("review_answer_", "")
        await lesson_review_answer(
            call.from_user.id,
            call.message,
            answer
        )
        await call.answer()
        return

    if call.data == "review_next":

        user_id   = call.from_user.id
        questions = user_state.get(user_id, {}).get("review_questions", [])
        index     = user_state.get(user_id, {}).get("review_index", 0)

        await send_review_question(
            user_id, call.message, questions, index
        )
        await call.answer()
        return

    if call.data == "lesson_consolidation_test":

        await lesson_consolidation_test(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "test_result_tts":
        u = user_state.get(call.from_user.id, {})
        text = u.get("last_result_text", "") if isinstance(u, dict) else ""
        if text:
            from learning import speak_mixed_text
            await speak_mixed_text(call.from_user.id, call.message, text)
        await call.answer()
        return

    if call.data.startswith("test_speak_"):
        what  = call.data.replace("test_speak_", "")
        u     = user_state.get(call.from_user.id, {})
        questions = u.get("test_questions", []) if isinstance(u, dict) else []
        index     = u.get("test_index", 0) if isinstance(u, dict) else 0

        if questions and index < len(questions):
            q = questions[index]
            opt_map = {"q": q[0], "A": q[1], "B": q[2], "C": q[3], "D": q[4]}
            text = opt_map.get(what, "")
            if text:
                from learning import speak_mixed_text
                await speak_mixed_text(call.from_user.id, call.message, str(text))
        await call.answer()
        return

    if call.data.startswith("test_answer_"):

        answer = call.data.replace("test_answer_", "")

        await lesson_test_answer(
            call.from_user.id,
            call.message,
            answer
        )

        await call.answer()

        return

    if call.data == "test_next_question":

        user_id   = call.from_user.id
        questions = user_state.get(user_id, {}).get("test_questions", [])
        index     = user_state.get(user_id, {}).get("test_index", 0)

        await send_test_question(
            user_id,
            call.message,
            questions,
            index
        )

        await call.answer()

        return

    if call.data == "lesson_tts":

        await lesson_tts(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "lesson_tts_help":

        await lesson_tts_help(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "lesson_back_main":

        await lesson_back_main(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "lesson_help":

        await lesson_help(
            call.from_user.id,
            call.message
        )

        await call.answer()

        return

    if call.data == "lesson_finish":

        await call.message.edit_text(
            "⚠️ Darsni tugatmoqchimisiz?\n\n"
            "Tugatmasangiz progress saqlanmaydi.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Ha, tugataman",
                            callback_data="lesson_finish_yes"
                        ),
                        InlineKeyboardButton(
                            text="↩️ Yo'q, davom",
                            callback_data="lesson_finish_no"
                        )
                    ]
                ]
            )
        )
        await call.answer()
        return

    if call.data == "lesson_finish_yes":

        await lesson_finish(
            call.from_user.id,
            call.message
        )

        await call.answer()
        return

    if call.data == "lesson_finish_no":

        # Tugmalarni qaytarish
        await lesson_back_main(
            call.from_user.id,
            call.message
        )

        await call.answer()
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

    elif call.data.startswith(
        "test_grade_"
    ):

        grade = call.data.replace(
            "test_grade_",
            ""
        )

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

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

        return

    elif call.data.startswith("test_subject_"):

        (
            _,
            _,
            grade,
            subject_code
        ) = call.data.split("_")

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
                AND subject_code=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (
            grade,
            subject_code
        ))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

        return

    elif call.data.startswith("test_quarter_"):

        (
            _,
            _,
            grade,
            subject_code,
            quarter
        ) = call.data.split("_")

        print("CALL:", call.data)
        print("PARAMS:", grade, subject_code, quarter)

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                question, option_a, option_b,
                option_c, option_d,
                correct_answer, explanation,
                question_type, is_latex,
                image_url, audio_text,
                language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code
                FROM dts_tree
                WHERE grade=%s
                AND subject_code=%s
                AND quarter=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (
            grade,
            subject_code,
            quarter
        ))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

        return

    elif call.data.startswith("test_bob_"):

        (
            _,
            _,
            grade,
            subject_code,
            quarter,
            bob_code
        ) = call.data.split("_")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                question, option_a, option_b,
                option_c, option_d,
                correct_answer, explanation,
                question_type, is_latex,
                image_url, audio_text,
                language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code
                FROM dts_tree
                WHERE grade=%s
                AND subject_code=%s
                AND quarter=%s
                AND bob_code=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (
            grade,
            subject_code,
            quarter,
            bob_code
        ))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

        return

    elif call.data.startswith("test_bolim_"):

        (
            _,
            _,
            grade,
            subject_code,
            quarter,
            bob_code,
            bolim_code
        ) = call.data.split("_")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                question, option_a, option_b,
                option_c, option_d,
                correct_answer, explanation,
                question_type, is_latex,
                image_url, audio_text,
                language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code
                FROM dts_tree
                WHERE grade=%s
                AND subject_code=%s
                AND quarter=%s
                AND bob_code=%s
                AND bolim_code=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (
            grade,
            subject_code,
            quarter,
            bob_code,
            bolim_code
        ))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

        return

    elif call.data.startswith("test_mavzu_"):

        (
            _,
            _,
            grade,
            subject_code,
            quarter,
            bob_code,
            bolim_code,
            mavzu_code
        ) = call.data.split("_")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT
                question, option_a, option_b,
                option_c, option_d,
                correct_answer, explanation,
                question_type, is_latex,
                image_url, audio_text,
                language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code
                FROM dts_tree
                WHERE grade=%s
                AND subject_code=%s
                AND quarter=%s
                AND bob_code=%s
                AND bolim_code=%s
                AND mavzu_code=%s
            )
            ORDER BY RANDOM()
            LIMIT 20
        """, (
            grade,
            subject_code,
            quarter,
            bob_code,
            bolim_code,
            mavzu_code
        ))

        tests = cur.fetchall()

        cur.close()
        conn.close()

        await start_test(
            call.from_user.id,
            tests,
            call.message
        )

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

    if call.data == "tset_start_quick":
        await call.answer()
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        row = cur2.fetchone()
        grade = row[0] if row else "5"
        cur2.execute("""
            SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer, explanation, question_type, is_latex,
                   image_url, audio_text, language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code FROM dts_tree WHERE grade=%s AND is_deleted=FALSE
            )
            AND question IS NOT NULL AND option_a IS NOT NULL
            ORDER BY RANDOM() LIMIT 20
        """, (grade,))
        tests = cur2.fetchall()
        cur2.close(); conn2.close()
        if not tests:
            await call.answer("❌ Testlar topilmadi!", show_alert=True)
            return
        await start_test(user_id, tests, call.message)
        return

    if call.data == "noop_timer":
        await call.answer("⏱ Vaqt ketmoqda...")
        return

    if call.data == "test_settings":
        await call.answer()
        from storage import user_state as us
        if not isinstance(us.get(user_id), dict):
            us[user_id] = {}
        us[user_id]["test_settings"] = {
            "count": 20, "diff": "all",
            "timed": True, "images": True,
            "write": False
        }
        await call.message.answer(
            "⚙️ Test sozlamalari:\n\n"
            "Savollar soni, qiyinlik, vaqt va turini tanlang:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📝 20 ta", callback_data="tset_count_20"),
                        InlineKeyboardButton(text="📝 40 ta", callback_data="tset_count_40"),
                        InlineKeyboardButton(text="📝 60 ta", callback_data="tset_count_60"),
                    ],
                    [
                        InlineKeyboardButton(text="🟢 Oson", callback_data="tset_diff_oson"),
                        InlineKeyboardButton(text="🟡 O'rta", callback_data="tset_diff_orta"),
                        InlineKeyboardButton(text="🔴 Qiyin", callback_data="tset_diff_qiyin"),
                        InlineKeyboardButton(text="🌈 Aralash", callback_data="tset_diff_all"),
                    ],
                    [
                        InlineKeyboardButton(text="⏱ Vaqtli", callback_data="tset_time_on"),
                        InlineKeyboardButton(text="∞ Vaqtsiz", callback_data="tset_time_off"),
                    ],
                    [
                        InlineKeyboardButton(text="🖼 Rasmli", callback_data="tset_img_on"),
                        InlineKeyboardButton(text="📝 Rasmsiz", callback_data="tset_img_off"),
                    ],
                    [
                        InlineKeyboardButton(text="✍️ Yozuvli", callback_data="tset_write_on"),
                        InlineKeyboardButton(text="🔘 Yozuvsiz", callback_data="tset_write_off"),
                    ],
                    [InlineKeyboardButton(text="▶️ Boshlash", callback_data="tset_start")]
                ]
            )
        )
        return

    if call.data.startswith("tset_"):
        from storage import user_state as us
        if not isinstance(us.get(user_id), dict):
            us[user_id] = {}
        if "test_settings" not in us[user_id]:
            us[user_id]["test_settings"] = {
                "count": 20, "diff": "all",
                "timed": True, "images": True, "write": False
            }

        s = us[user_id]["test_settings"]

        if call.data.startswith("tset_count_"):
            s["count"] = int(call.data.replace("tset_count_", ""))
            await call.answer(f"✅ {s['count']} ta savol")
        elif call.data.startswith("tset_diff_"):
            s["diff"] = call.data.replace("tset_diff_", "")
            diff_names = {"oson": "Oson 🟢", "orta": "O'rta 🟡", "qiyin": "Qiyin 🔴", "all": "Aralash 🌈"}
            await call.answer(f"✅ {diff_names.get(s['diff'], s['diff'])}")
        elif call.data == "tset_time_on":
            s["timed"] = True
            await call.answer("✅ Vaqtli")
        elif call.data == "tset_time_off":
            s["timed"] = False
            await call.answer("✅ Vaqtsiz")
        elif call.data == "tset_img_on":
            s["images"] = True
            await call.answer("✅ Rasmli")
        elif call.data == "tset_img_off":
            s["images"] = False
            await call.answer("✅ Rasmsiz")
        elif call.data == "tset_write_on":
            s["write"] = True
            await call.answer("✅ Yozuvli savollar ham")
        elif call.data == "tset_write_off":
            s["write"] = False
            await call.answer("✅ Faqat tugmali savollar")

        # Klaviaturani yangilash
        if not call.data == "tset_start":
            def c(cond): return "✅ " if cond else ""
            count = s["count"]
            diff  = s["diff"]
            timed = s["timed"]
            imgs  = s["images"]
            write = s.get("write", False)
            new_kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"{c(count==20)}20 ta", callback_data="tset_count_20"),
                    InlineKeyboardButton(text=f"{c(count==40)}40 ta", callback_data="tset_count_40"),
                    InlineKeyboardButton(text=f"{c(count==60)}60 ta", callback_data="tset_count_60"),
                ],
                [
                    InlineKeyboardButton(text=f"{c(diff=='oson')}🟢 Oson",   callback_data="tset_diff_oson"),
                    InlineKeyboardButton(text=f"{c(diff=='orta')}🟡 O'rta",  callback_data="tset_diff_orta"),
                    InlineKeyboardButton(text=f"{c(diff=='qiyin')}🔴 Qiyin", callback_data="tset_diff_qiyin"),
                    InlineKeyboardButton(text=f"{c(diff=='all')}🌈 Aralash", callback_data="tset_diff_all"),
                ],
                [
                    InlineKeyboardButton(text=f"{c(timed)}⏱ Vaqtli",    callback_data="tset_time_on"),
                    InlineKeyboardButton(text=f"{c(not timed)}∞ Vaqtsiz", callback_data="tset_time_off"),
                ],
                [
                    InlineKeyboardButton(text=f"{c(imgs)}🖼 Rasmli",     callback_data="tset_img_on"),
                    InlineKeyboardButton(text=f"{c(not imgs)}📝 Rasmsiz", callback_data="tset_img_off"),
                ],
                [
                    InlineKeyboardButton(text=f"{c(write)}✍️ Yozuvli",     callback_data="tset_write_on"),
                    InlineKeyboardButton(text=f"{c(not write)}🔘 Yozuvsiz", callback_data="tset_write_off"),
                ],
                [InlineKeyboardButton(text="▶️ Boshlash", callback_data="tset_start")]
            ])
            try:
                await call.message.edit_reply_markup(reply_markup=new_kb)
            except Exception:
                pass
            return
        elif call.data == "tset_start":
            # Test boshlash
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2  = conn2.cursor()
            cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
            row = cur2.fetchone()
            grade = row[0] if row else "5"

            diff_filter = "" if s["diff"] == "all" else f"AND difficulty='{s['diff']}'"

            # Yozuvli yoki yozuvsiz
            if s.get("write"):
                type_filter = ""  # Barcha turlar
            else:
                type_filter = "AND question_type != 'write_answer'"

            cur2.execute(f"""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type, is_latex,
                       image_url, audio_text, language, time_limit
                FROM generated_tests
                WHERE topic_code IN (
                    SELECT topic_code FROM dts_tree WHERE grade=%s AND is_deleted=FALSE
                )
                AND question IS NOT NULL
                {diff_filter}
                {type_filter}
                ORDER BY RANDOM()
                LIMIT %s
            """, (grade, s["count"]))
            tests = cur2.fetchall()
            cur2.close(); conn2.close()

            if not tests:
                await call.answer("❌ Testlar topilmadi!", show_alert=True)
                return

            # Vaqtsiz bo'lsa time_limit = 0
            if not s["timed"]:
                tests = [(*t[:12], 0) for t in tests]

            await call.answer()
            await start_test(user_id, tests, call.message)
        return

    elif True:  # test_sessions tekshiruvi test_engine da
        await call.answer(
            "♻️ Bot yangilangan. Qayta boshlang.",
            show_alert=True
        )
        return

async def main():
    print("BOT ISHGA TUSHDI 🚀")
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
