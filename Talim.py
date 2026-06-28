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
from storage import user_state, temp_user, registration_message, reg_kbd_message
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
HOME2 = "🏠 Bosh ekran"

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

    # user_id INTEGER -> BIGINT (Telegram ID lari INTEGER chegarasidan oshib ketadi)
    try:
        cur.execute("ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT")
        cur.execute("ALTER TABLE survey_answers ALTER COLUMN user_id TYPE BIGINT")
        conn.commit()
    except Exception:
        conn.rollback()
    for _col_sql in [
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS kindergarten TEXT',
        'ALTER TABLE users ADD COLUMN IF NOT EXISTS "group" TEXT',
    ]:
        try: cur.execute(_col_sql); conn.commit()
        except Exception: conn.rollback()

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS error_log (
        id         SERIAL PRIMARY KEY,
        user_id    BIGINT,
        username   TEXT,
        error_text TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        is_read    BOOLEAN DEFAULT FALSE
    )
    """)

    # ===== Yetishmayotgan 10 ta jadval (auto-create, idempotent) =====
    cur.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS gender     TEXT
    """)
    cur.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS dts_tree (
        id SERIAL PRIMARY KEY,
        topic_code TEXT UNIQUE,
        grade TEXT, subject_code TEXT, subject_name TEXT, quarter TEXT,
        bob_code TEXT, bob_name TEXT, bolim_code TEXT, bolim_name TEXT,
        mavzu_code TEXT, mavzu_name TEXT, kichik_code TEXT, kichik_name TEXT,
        is_deleted BOOLEAN DEFAULT FALSE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dts_tree_grade_subj ON dts_tree (grade, subject_code, quarter)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dts_tree_active ON dts_tree (is_deleted)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS generated_tests (
        id SERIAL PRIMARY KEY,
        topic_code TEXT, difficulty TEXT, situation TEXT, question TEXT,
        option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
        correct_answer TEXT, explanation TEXT, question_type TEXT,
        is_latex BOOLEAN DEFAULT FALSE, image_url TEXT, audio_text TEXT,
        language TEXT, life_level TEXT, age_group TEXT, time_limit INTEGER
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_tests_topic ON generated_tests (topic_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_gen_tests_topic_diff ON generated_tests (topic_code, difficulty)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS teacher_lessons (
        id SERIAL PRIMARY KEY,
        topic_code TEXT UNIQUE,
        intro      TEXT, image_intro TEXT,
        part_1     TEXT, image_1 TEXT,
        part_2     TEXT, image_2 TEXT,
        part_3     TEXT, image_3 TEXT,
        part_4     TEXT, image_4 TEXT,
        part_5     TEXT, image_5 TEXT,
        part_6     TEXT, image_6 TEXT,
        part_7     TEXT, image_7 TEXT,
        simple_1   TEXT, simple_2 TEXT, simple_3 TEXT, simple_4 TEXT,
        simple_5   TEXT, simple_6 TEXT, simple_7 TEXT,
        example_1  TEXT, example_2 TEXT, example_3 TEXT,
        example_4  TEXT, example_5 TEXT,
        summary    TEXT
    )
    """)

    # Eski jadvalga yangi ustunlar qo'shish (mavjud ma'lumotlarga tegmaydi)
    for _col in [
        "image_intro TEXT", "image_1 TEXT", "image_2 TEXT", "image_3 TEXT",
        "image_4 TEXT",     "image_5 TEXT", "image_6 TEXT", "image_7 TEXT",
        "part_5 TEXT",  "part_6 TEXT",  "part_7 TEXT",
        "simple_5 TEXT","simple_6 TEXT","simple_7 TEXT",
        "example_3 TEXT","example_4 TEXT","example_5 TEXT",
        "image_e_1 TEXT","image_e_2 TEXT","image_e_3 TEXT",
        "image_e_4 TEXT","image_e_5 TEXT",
    ]:
        try:
            cur.execute(f"ALTER TABLE teacher_lessons ADD COLUMN IF NOT EXISTS {_col}")
            conn.commit()
        except Exception:
            conn.rollback()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS learned_topics (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        topic_code TEXT NOT NULL,
        score INTEGER DEFAULT 0,
        repeat_count INTEGER DEFAULT 0,
        learned_at TIMESTAMP DEFAULT NOW(),
        next_repeat DATE,
        UNIQUE (user_id, topic_code)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_user ON learned_topics (user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_repeat ON learned_topics (next_repeat)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_progress (
        user_id BIGINT PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_active DATE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lesson_progress (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL UNIQUE,
        topic_code TEXT,
        current_step INTEGER DEFAULT 0,
        completed BOOLEAN DEFAULT FALSE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_prog_user ON lesson_progress (user_id)")
    # Agar eski jadval UNIQUE siz bo'lsa — qo'shamiz
    try:
        cur.execute("ALTER TABLE lesson_progress ADD CONSTRAINT lesson_progress_user_id_key UNIQUE (user_id)")
        conn.commit()
    except Exception:
        conn.rollback()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        badge_code TEXT NOT NULL,
        earned_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (user_id, badge_code)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exams (
        id SERIAL PRIMARY KEY,
        title TEXT, grade TEXT, exam_date DATE,
        is_mandatory BOOLEAN DEFAULT FALSE,
        created_by BIGINT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exam_results (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        exam_id INTEGER REFERENCES exams(id) ON DELETE CASCADE,
        status TEXT DEFAULT 'pending',
        UNIQUE (user_id, exam_id)
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_results_user ON exam_results (user_id)")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_generation (
        topic_code TEXT PRIMARY KEY,
        current_count INTEGER DEFAULT 0,
        target_count INTEGER DEFAULT 10,
        last_generated_at TIMESTAMP
    )
    """)
    # ===== Yetishmayotgan jadvallar tugadi =====


    conn.commit()
    conn.close()

def get_grades():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT grade FROM (
            SELECT DISTINCT grade FROM dts_tree
        ) _g
        ORDER BY
            CASE WHEN grade ~ '^[0-9]+$' THEN grade::int ELSE 9999 END,
            grade
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

    caption = (message.caption or "").strip()

    # Agar caption "split:TOPIC_CODE:rows:cols:prefix" formatida bo'lsa
    # Misol: split:1-01-1-01-01-01-001:1:6:p  → -p-1..-p-6
    #        split:1-01-1-01-01-01-001:1:5:e  → -e-1..-e-5
    if caption.lower().startswith("split:"):
        parts = caption[6:].strip().split(":")
        topic_code = parts[0].strip()
        rows   = int(parts[1]) if len(parts) > 1 else 1
        cols   = int(parts[2]) if len(parts) > 2 else 6
        prefix = parts[3].strip() if len(parts) > 3 else "p"
        total  = rows * cols
        await message.answer(
            f"⏳ Rasm {rows}×{cols}={total} ga bo'linmoqda...\n"
            f"📌 Kod: {topic_code}-{prefix}-1 ... -{prefix}-{total}"
        )

        # Rasmni yuklab olish
        import io
        from PIL import Image

        file = await message.bot.get_file(message.photo[-1].file_id)
        buf = io.BytesIO()
        await message.bot.download_file(file.file_path, buf)
        buf.seek(0)
        img = Image.open(buf)
        W, H = img.size

        # 5 qator x 8 ustun = 40 ta (yoki berilgan o'lcham)
        cell_w = W // cols
        cell_h = H // rows

        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        saved = 0

        for row in range(rows):
            for col in range(cols):
                n = row * cols + col + 1
                if n > total:
                    break

                # Kesish
                x1 = col * cell_w
                y1 = row * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h
                piece = img.crop((x1, y1, x2, y2))

                # Telegram ga yuborish va file_id olish
                piece_buf = io.BytesIO()
                piece.save(piece_buf, format="JPEG")
                piece_buf.seek(0)

                from aiogram.types import BufferedInputFile
                name_preview = f"{topic_code}-{prefix}-{n}"
                sent = await message.answer_photo(
                    BufferedInputFile(piece_buf.read(), filename=f"{name_preview}.jpg"),
                    caption=name_preview
                )
                file_id = sent.photo[-1].file_id

                # DBga saqlash
                name = f"{topic_code}-{prefix}-{n}"
                cur.execute("""
                    INSERT INTO images(name, file_id)
                    VALUES(%s,%s)
                    ON CONFLICT (name) DO UPDATE SET file_id=EXCLUDED.file_id
                """, (name, file_id))
                saved += 1

        conn.commit()
        cur.close(); conn.close()
        await message.answer(
            f"✅ {saved} ta rasm saqlandi!\n"
            f"📁 {topic_code}-{prefix}-1 ... {topic_code}-{prefix}-{total}"
        )
        return

    # Oddiy rasm saqlash
    if not caption:
        await message.answer("Rasm nomini captionga yozing\n\nYoki 40 ga bo'lish uchun:\nsplit:TOPIC_CODE")
        return

    name = caption
    file_id = message.photo[-1].file_id
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO images(name, file_id)
    VALUES(%s,%s)
    ON CONFLICT (name)
    DO UPDATE SET file_id = EXCLUDED.file_id
    """, (name, file_id))
    conn.commit()
    cur.close(); conn.close()
    await message.answer(f"✅ Saqlandi: {name}")

# ====== START ======
def _save_error_log(user_id, username, error_text):
    """Xatoni bazaga yozadi (sinxron)."""
    try:
        conn_ = psycopg2.connect(DATABASE_URL)
        cur_  = conn_.cursor()
        cur_.execute(
            "INSERT INTO error_log(user_id, username, error_text) VALUES(%s,%s,%s)",
            (user_id, username, error_text[:1000])
        )
        conn_.commit(); cur_.close(); conn_.close()
    except Exception:
        pass

def _get_unread_errors():
    """O'qilmagan xatolar sonini qaytaradi."""
    try:
        conn_ = psycopg2.connect(DATABASE_URL)
        cur_  = conn_.cursor()
        cur_.execute("SELECT COUNT(*) FROM error_log WHERE is_read=FALSE")
        n = cur_.fetchone()[0]
        cur_.close(); conn_.close()
        return n
    except Exception:
        return 0

async def _notify_admins(error_text, user_id, username):
    """Adminlarga yangi xato haqida xabar yuboradi."""
    try:
        n = _get_unread_errors()
        txt = (
            f"🆘 Yangi xato #{n}\n"
            f"👤 User: {username} ({user_id})\n"
            f"❌ {error_text[:300]}"
        )
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, txt)
            except Exception:
                pass
    except Exception:
        pass

async def _error_and_home(source, user_id, err, label="Xato"):
    """Xato xabarini ko'rsatib, 2 soniyada bosh menyuga qaytaradi."""
    import traceback, asyncio
    tb = traceback.format_exc()
    short = str(err)[:200]

    # Username olish
    try:
        uname = source.from_user.username or str(user_id) if hasattr(source, "from_user") else str(user_id)
    except Exception:
        uname = str(user_id)

    # Bazaga saqlash
    _save_error_log(user_id, uname, f"{label}: {short}\n{tb[:500]}")

    # Foydalanuvchiga xabar
    try:
        msg_fn = source.answer if hasattr(source, "answer") else source.message.answer
        await msg_fn(f"⚠️ Xatolik yuz berdi.\n\nBosh menyuga qaytilmoqda...")
    except Exception:
        pass

    await asyncio.sleep(2)

    # Bosh menyuga qaytarish
    try:
        conn_ = psycopg2.connect(DATABASE_URL)
        cur_  = conn_.cursor()
        cur_.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
        row_  = cur_.fetchone()
        cur_.close(); conn_.close()
        role_ = row_[0] if row_ else "🧒 O'quvchi"
        if user_id in ADMINS: role_ = "Admin"
    except Exception:
        role_ = "🧒 O'quvchi"

    n_err = _get_unread_errors() if user_id in ADMINS else 0
    kb_ = get_main_keyboard(role_, unread_errors=n_err)
    try:
        msg_fn = source.answer if hasattr(source, "answer") else source.message.answer
        await msg_fn("🏠 Bosh menyu", reply_markup=kb_)
    except Exception:
        pass

    # Adminlarga xabardorlik
    await _notify_admins(f"{label}: {short}", user_id, uname)
    print(f"[ERROR] user={user_id} | {label}: {short}\n{tb}")


from aiogram.filters import Command

@dp.message(Command("menu"))
@dp.message(Command("cancel"))
@dp.message(Command("stop"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Har qanday holatda bosh menyuga qaytish."""
    uid = message.from_user.id
    try: await state.clear()
    except: pass
    user_state.pop(uid, None)
    from storage import lesson_state as _ls, temp_user as _tu
    from storage import registration_message as _rm
    _ls.pop(uid, None); _tu.pop(uid, None); _rm.pop(uid, None)
    from test_engine import test_sessions
    if uid in test_sessions:
        s_ = test_sessions.pop(uid, {})
        if s_.get("timer_task"):
            try: s_["timer_task"].cancel()
            except: pass
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); conn.close()
        role = row[0] if row else "🧒 O'quvchi"
    except: role = "🧒 O'quvchi"
    if uid in ADMINS: role = "Admin"
    await message.answer(
        "🏠 Bosh menyu",
        reply_markup=get_main_keyboard(role)
    )


@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    # /start — har qanday holatda barcha state tozalanadi
    uid = message.from_user.id
    try: await state.clear()
    except: pass
    user_state.pop(uid, None)
    from storage import lesson_state as _ls, temp_user as _tu
    from storage import registration_message as _rm, reg_kbd_message as _rkm
    _ls.pop(uid, None)
    _tu.pop(uid, None)
    _rm.pop(uid, None)
    _rkm.pop(uid, None)
    from test_engine import test_sessions
    if uid in test_sessions:
        s_ = test_sessions.pop(uid, {})
        if s_.get("timer_task"):
            try: s_["timer_task"].cancel()
            except: pass

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
            _n_err = _get_unread_errors()
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}"
                + (f"\n🆘 {_n_err} ta o'qilmagan xato bor!" if _n_err else ""),
                reply_markup=get_main_keyboard(role, unread_errors=_n_err)
            )
            return

        # O'quvchi uchun yoshga mos kutib olish
        if "quvchi" in role.lower() or role.strip() in ("🧒 O'quvchi", "🧒O'quvchi", "O'quvchi"):

            from progress import update_streak
            from student_dashboard import build_dashboard

            update_streak(message.from_user.id)

            try:
                text, keyboard = await build_dashboard(message.from_user.id)
            except Exception as _de:
                import traceback
                print(f"build_dashboard ERROR: {traceback.format_exc()}")
                text = "👋 Xush kelibsiz!"
                keyboard = None

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
                # Dashboard inline keyboard bilan + reply keyboard alohida (Telegram cheklovi)
                if keyboard:
                    await message.answer(text, reply_markup=keyboard)
                    # Reply keyboard uchun minimal xabar
                    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
                    await message.answer(
                        "─────────────────",
                        reply_markup=get_main_keyboard(role)
                    )
                else:
                    await message.answer(text, reply_markup=get_main_keyboard(role))
        else:
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}",
                reply_markup=get_main_keyboard(role)
            )

        return

    # YANGI FOYDALANUVCHI — inline registratsiya
    from register import start_registration
    await start_registration(message)

# Test import uchun vaqtincha fayl yo'llari (user_id -> path)
test_import_files = {}

async def prepare_test_import(message, user_id):
    """Excel ni yuklab, tekshirib, tasdiq so'raydi (darrov import qilmaydi)."""
    file = await bot.get_file(message.document.file_id)
    path = f"temp_import_{user_id}.xlsx"
    await bot.download_file(file.file_path, path)

    try:
        _xls = pd.ExcelFile(path)
        _sheet = "TESTLAR" if "TESTLAR" in _xls.sheet_names else _xls.sheet_names[0]
        df = pd.read_excel(path, sheet_name=_sheet)
    except Exception as _e:
        await message.answer(f"❌ Excel o'qib bo'lmadi: {_e}")
        admin_state[user_id] = None
        return

    if "topic_code" not in df.columns:
        await message.answer(
            "❌ Excel ustunlari mos emas.\n"
            "Birinchi qatorda 'topic_code, difficulty, question ...' ustunlari bo'lishi kerak."
        )
        admin_state[user_id] = None
        return

    valid = 0
    for _, r in df.iterrows():
        if not pd.isna(r.get("topic_code")) and not pd.isna(r.get("question")):
            valid += 1

    test_import_files[user_id] = path
    admin_state[user_id] = "test_import_confirm"

    await message.answer(
        f"📋 Faylda {valid} ta savol topildi.\n\nImport qilaylikmi?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(text="✅ Ha, import qil"),
                KeyboardButton(text="❌ Bekor"),
            ]],
            resize_keyboard=True
        )
    )


async def import_tests_excel(target, path, user_id):

    # Varaq nomi har qanday bo'lsa ishlasin: avval TESTLAR, bo'lmasa birinchi varaq
    try:
        _xls = pd.ExcelFile(path)
        _sheet = "TESTLAR" if "TESTLAR" in _xls.sheet_names else _xls.sheet_names[0]
        df = pd.read_excel(path, sheet_name=_sheet)
    except Exception as _e:
        await target.answer(f"❌ Excel o'qib bo'lmadi: {_e}")
        return

    if "topic_code" not in df.columns:
        await target.answer(
            "❌ Excel ustunlari mos emas.\n"
            "Birinchi qatorda 'topic_code, difficulty, question ...' ustunlari bo'lishi kerak."
        )
        return

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
                "is_latex": False if pd.isna(row["is_latex"]) else (row["is_latex"] not in (0, 0.0, False, "False", "false", "0")),
                "image_url": None if pd.isna(row["image_url"]) else str(row["image_url"]),
                "audio_text": None if pd.isna(row["audio_text"]) else str(row["audio_text"]),
                "language": "uz" if pd.isna(row["language"]) else str(row["language"]),
                "life_level": 1 if pd.isna(row["life_level"]) else int(row["life_level"]),
                "age_group": None if pd.isna(row["age_group"]) else str(row["age_group"]),
                "time_limit": 60 if pd.isna(row["time_limit"]) else int(row["time_limit"])
            }

            import psycopg2 as _pg
            _conn = _pg.connect(os.getenv("DATABASE_URL"))
            _cur = _conn.cursor()

            # Avval to'liq tekshiruv — duplikatmi? (question_type ham hisobga olinadi)
            _cur.execute("""
                SELECT COUNT(*) FROM generated_tests
                WHERE topic_code=%s AND question=%s
                  AND option_a=%s AND option_b=%s
                  AND option_c=%s AND option_d=%s
                  AND correct_answer=%s
                  AND COALESCE(question_type,'single_choice')=COALESCE(%s,'single_choice')
            """, (
                test_data["topic_code"], test_data["question"],
                test_data["option_a"], test_data["option_b"],
                test_data["option_c"], test_data["option_d"],
                test_data["correct_answer"],
                test_data["question_type"],
            ))
            already = _cur.fetchone()[0]

            if already > 0:
                result = "duplicate"
            else:
                try:
                    _cur.execute("""
                        INSERT INTO generated_tests
                        (topic_code, difficulty, situation, question,
                         option_a, option_b, option_c, option_d,
                         correct_answer, explanation, question_type,
                         is_latex, image_url, audio_text, language,
                         life_level, age_group, time_limit)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                %s::boolean,%s,%s,%s,%s,%s,%s)
                    """, (
                        test_data["topic_code"], test_data["difficulty"],
                        test_data["situation"], test_data["question"],
                        test_data["option_a"], test_data["option_b"],
                        test_data["option_c"], test_data["option_d"],
                        test_data["correct_answer"], test_data["explanation"],
                        test_data["question_type"],
                        test_data["is_latex"],
                        test_data["image_url"], test_data["audio_text"],
                        test_data["language"], test_data["life_level"],
                        test_data["age_group"], test_data["time_limit"],
                    ))
                    _conn.commit()
                    result = "saved"
                except Exception as _ex:
                    _conn.rollback()
                    result = f"error: {_ex}"

            _cur.close(); _conn.close()

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

    await target.answer(
        f"✅ Import tugadi\n\n"
        f"📥 Saqlandi: {success}\n"
        f"⚠️ Duplikat: {duplicates}\n"
        f"❌ Xato: {errors}"
    )

    if error_rows:

        await target.answer_document(
            FSInputFile("import_errors.xlsx"),
            caption="📋 Import xatolari hisoboti"
        )

    admin_state[user_id] = None

@dp.message()
async def handle_all(
    message: Message,
    state: FSMContext
):
    user_id = message.from_user.id
    try:
        await _handle_all_inner(message, state, user_id)
    except Exception as _e:
        await _error_and_home(message, user_id, _e, "Xatolik")


async def _handle_all_inner(message: Message, state: FSMContext, user_id: int):

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

    if message.text == "⚙️ Sozlamalar":
        from student_settings import show_settings
        await show_settings(message, user_id)
        return

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

    if message.text == "🏠 Bosh ekran":
        user_state[user_id] = None
        # Eski xabarlarni o'chirish
        try:
            for i in range(message.message_id - 1, message.message_id - 20, -1):
                try:
                    await bot.delete_message(message.chat.id, i)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            from student_dashboard import build_dashboard
            text, kb = await build_dashboard(user_id)
            await message.answer(text, reply_markup=kb)
        except Exception:
            pass
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
        row = cur2.fetchone()
        cur2.close(); conn2.close()
        await message.answer("🏠 Asosiy menyu", reply_markup=get_main_keyboard(row[0] if row else "🧒 O'quvchi"))
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

    # SOZLAMALAR HOLATLARI
    if user_state.get(user_id) == "change_name":
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2 = conn2.cursor()
        cur2.execute("UPDATE users SET full_name=%s WHERE user_id=%s", (message.text, user_id))
        conn2.commit(); cur2.close(); conn2.close()
        user_state[user_id] = None
        await message.answer(f"✅ Ism o'zgartirildi: {message.text}")
        return

    if user_state.get(user_id) == "change_bdate":
        try:
            from datetime import datetime
            bdate = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2 = conn2.cursor()
            cur2.execute("UPDATE users SET birth_date=%s WHERE user_id=%s", (bdate, user_id))
            conn2.commit(); cur2.close(); conn2.close()
            user_state[user_id] = None
            await message.answer(f"✅ Tug'ilgan kun saqlandi: {message.text}")
        except Exception:
            await message.answer("❌ Format xato! Masalan: 15.03.2015")
        return

    if user_state.get(user_id) == "change_school_settings":
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2 = conn2.cursor()
        cur2.execute("UPDATE users SET school=%s WHERE user_id=%s", (message.text, user_id))
        conn2.commit(); cur2.close(); conn2.close()
        user_state[user_id] = None
        await message.answer(f"✅ Maktab saqlandi: {message.text}")
        return

    # REGISTRATSIYA
    if user_state.get(user_id) and user_state.get(user_id) not in ("text_answer",):

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
        from dts_import_handlers import DTSImportState
        await state.set_state(DTSImportState.waiting_excel)
        await dts_excel_import(
            message,
            state
        )
        admin_state[user_id] = None
        return

    # Shablon import
    if message.document:
        from shablon_yaratish import handle_shablon_document, shablon_state
        if shablon_state.get(user_id, {}).get("step") == "import_wait":
            await handle_shablon_document(message, user_id, bot)
            return

    # Shablon mavzu matni
    from shablon_yaratish import shablon_state as sh_state, handle_shablon_message
    # Tugma bosilgan bo'lsa shablon_state ni o'tkazib yuboramiz
    _menu_btns = {
        "📋 Shablonlar","🧪 Test shablon","📥 Test import",
        "📋 Topik shablon","📥 Topik import",
        "📚 Dars shablon","📥 Dars import",
        "🔙 Admin menyu","📊 Test statistikasi",
        "🤖 AI Generator","📚 Shablon yaratish",
        "🔙 Ortga",
    }
    if (
        message.text not in _menu_btns
        and sh_state.get(user_id, {}).get("step") in ("sinf_fan", "mavzular")
    ):
        await handle_shablon_message(message, user_id)
        return



    if (
        admin_state.get(user_id) == "test_import"
        and message.document
    ):

        await prepare_test_import(message, user_id)

        return

    if user_state.get(message.from_user.id) == "in_test":
        # Test paytida matn yozsa — yumshoq eslatma
        try:
            await message.answer(
                "🧪 Test davom etyapti!\n"
                "Javob berish uchun tugmalardan foydalaning.\n\n"
                "Chiqish: /menu"
            )
        except: pass
        return

    if user_state.get(message.from_user.id) == "in_lesson":
        # Dars paytida matn yozsa — yumshoq eslatma
        try:
            await message.answer(
                "📖 Dars davom etyapti!\n"
                "Oldinga o'tish uchun tugmalardan foydalaning.\n\n"
                "Chiqish: /menu"
            )
        except: pass
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

    elif message.text == "🧪 Test sinovi":
        if user_id not in ADMINS:
            return
        from test_sinovi import show_sinov_start
        await show_sinov_start(message, user_id)
        return

    elif message.text == "👥 Foydalanuvchilar":
        if user_id not in ADMINS:
            return
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM users")
        total = cur2.fetchone()[0]
        cur2.execute("SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY COUNT(*) DESC")
        roles = cur2.fetchall()
        cur2.close(); conn2.close()
        text = f"👥 Foydalanuvchilar: {total} ta\n\n"
        for role, cnt in roles:
            text += f"• {role}: {cnt} ta\n"
        await message.answer(text)
        return

    elif message.text == "🖼 Rasmlar boshqaruvi":
        if user_id not in ADMINS:
            return
        from image_admin import show_image_panel
        await show_image_panel(message)
        return

    elif message.text == "📚 Shablon yaratish":
        if user_id not in ADMINS:
            return
        from shablon_yaratish import show_shablon_menu
        await show_shablon_menu(message, user_id)
        return

    elif message.text in ("🤖 AI Generator", "🧪 Test shablon"):
        if user_id not in ADMINS:
            return
        from ai_generatori import show_gen_start
        await show_gen_start(message, user_id)
        return

    elif message.text in ("📚 DTS boshqaruvi", "🧭 DTS topik boshqaruvi"):

        await dts_menu(
                message
            )
        return

    elif message.text == "📊 Test statistikasi":

        await message.answer(
            "📊 Test statistikasi / Generator",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📚 Mavzular statistikasi"),
                    KeyboardButton(text="📊 Generator statistikasi")],
                    [KeyboardButton(text="▶️ Generatorni boshlash"),
                    KeyboardButton(text="⏹ Generatorni to‘xtatish")],
                    [KeyboardButton(text="🔙 Ortga")]
                ],
                  resize_keyboard=True
            )
        )

        return

    elif message.text in ("🆘 Xatolar", ) or message.text.startswith("🆘 Xatolar"):
        if user_id not in ADMINS:
            return
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("""
            SELECT id, user_id, username, error_text, created_at
            FROM error_log
            ORDER BY created_at DESC
            LIMIT 20
        """)
        errors = cur2.fetchall()
        # O'qilgan deb belgilash
        cur2.execute("UPDATE error_log SET is_read=TRUE WHERE is_read=FALSE")
        conn2.commit(); cur2.close(); conn2.close()

        if not errors:
            await message.answer(
                "✅ Xatolar yo'q!",
                reply_markup=get_main_keyboard("Admin", unread_errors=0)
            )
            return

        lines = [f"🆘 So'nggi xatolar ({len(errors)} ta):\n"]
        for i, (eid, uid, uname, etxt, eat) in enumerate(errors, 1):
            t = eat.strftime("%d.%m %H:%M") if eat else "?"
            short = (etxt or "")[:150].replace("\n", " ")
            lines.append(f"{i}. [{t}] {uname}({uid})\n   {short}\n")

        # Uzun bo'lsa bo'lib yuborish
        text = "\n".join(lines)
        while text:
            await message.answer(text[:4096])
            text = text[4096:]

        await message.answer(
            "✅ Hammasi o'qilgan deb belgilandi.",
            reply_markup=get_main_keyboard("Admin", unread_errors=0)
        )
        return

    elif message.text == "📖 Darslar holati":
        if user_id not in ADMINS:
            return
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("""
            SELECT
                d.grade,
                d.subject_name,
                COUNT(DISTINCT d.topic_code)           AS jami,
                COUNT(DISTINCT l.topic_code)           AS bor,
                COUNT(DISTINCT d.topic_code) -
                COUNT(DISTINCT l.topic_code)           AS yoq
            FROM dts_tree d
            LEFT JOIN teacher_lessons l ON l.topic_code = d.topic_code
            WHERE d.is_deleted = FALSE
            GROUP BY d.grade, d.subject_name
            ORDER BY
                CASE WHEN d.grade ~ '^[0-9]+$' THEN d.grade::int ELSE 99 END,
                d.subject_name
        """)
        rows2 = cur2.fetchall()
        cur2.close(); conn2.close()

        if not rows2:
            await message.answer("📭 DTS daraxt bo'sh.")
            return

        lines = ["📖 Darslar holati\n"]
        cur_grade = None
        t_jami = t_bor = t_yoq = 0
        for grade, subj, jami, bor, yoq in rows2:
            if grade != cur_grade:
                cur_grade = grade
                lines.append(f"\n🎓 {grade}-sinf:")
            pct = round(bor*100/jami) if jami else 0
            bar = "🟩" if pct==100 else ("🟨" if pct>=50 else "🟥")
            lines.append(
                f"  {bar} {subj}\n"
                f"     ✅ {bor} dars bor  |  ❌ {yoq} yo'q  |  📚 {jami} jami ({pct}%)"
            )
            t_jami += jami; t_bor += bor; t_yoq += yoq

        pct_t = round(t_bor*100/t_jami) if t_jami else 0
        lines.append(
            f"\n━━━━━━━━━━━━━━\n"
            f"📊 Jami: ✅ {t_bor} | ❌ {t_yoq} | 📚 {t_jami} ({pct_t}%)"
        )
        await message.answer("\n".join(lines))
        return

    elif message.text == "📚 Mavzular statistikasi":
        if user_id not in ADMINS:
            return
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("""
            SELECT
                t.grade,
                t.subject_name,
                COUNT(DISTINCT t.topic_code)                              AS mavzu_soni,
                COUNT(g.id)                                               AS test_soni,
                COUNT(DISTINCT CASE WHEN g.id IS NULL THEN t.topic_code END) AS bosh_mavzu
            FROM dts_tree t
            LEFT JOIN generated_tests g ON g.topic_code = t.topic_code
            WHERE t.is_deleted = FALSE
            GROUP BY t.grade, t.subject_name
            ORDER BY t.grade, t.subject_name
        """)
        rows = cur2.fetchall()
        cur2.close(); conn2.close()

        if not rows:
            await message.answer("📭 Hozircha mavzu ma'lumoti yo'q.")
            return

        # Sinf bo'yicha guruhlash
        from collections import defaultdict
        by_grade = defaultdict(list)
        for grade, subj, mavzu, test, bosh in rows:
            by_grade[grade].append((subj, mavzu, test, bosh))

        lines = ["📊 Mavzular statistikasi\n"]
        total_m = total_t = total_b = 0
        for grade in sorted(by_grade.keys(), key=lambda x: int(x) if str(x).isdigit() else 99):
            lines.append(f"\n🎓 {grade}-sinf:")
            for subj, mavzu, test, bosh in by_grade[grade]:
                avg = round(test/mavzu, 1) if mavzu else 0
                bar = "🟩" if avg >= 5 else ("🟨" if avg >= 2 else "🟥")
                lines.append(
                    f"  {bar} {subj}\n"
                    f"     📚 {mavzu} mavzu | 🧪 {test} test | ⚠️ {bosh} bo'sh"
                )
                total_m += mavzu; total_t += test; total_b += bosh

        lines.append(
            f"\n━━━━━━━━━━━━━━\n"
            f"📊 Jami: {total_m} mavzu | {total_t} test | {total_b} bo'sh mavzu"
        )
        await message.answer("\n".join(lines))
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

        total = stats[0] or 0
        oson = stats[1] or 0
        orta = stats[2] or 0
        qiyin = stats[3] or 0
        murakkab = stats[4] or 0

        await message.answer(
            f"🔑 {topic_code}\n\n"
            f"🎓 Sinf: {info[0]}\n"
            f"📚 Fan: {info[1]}\n"
            f"🗓 Chorak: {info[2]}\n"
            f"📖 Bob: {info[3]}\n"
            f"📂 Bo'lim: {info[4]}\n"
            f"📘 Mavzu: {info[5]}\n"
            f"📌 Kichik mavzu: {info[6]}\n\n"
            f"📊 Jami test: {total}\n"
            f"🟢 Oson: {oson}\n"
            f"🟡 O'rta: {orta}\n"
            f"🟠 Qiyin: {qiyin}\n"
            f"🔴 Murakkab: {murakkab}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 Excel shablon", callback_data=f"ts_excel:{topic_code}"),
                    InlineKeyboardButton(text="📥 Import", callback_data=f"ts_import:{topic_code}"),
                ],
                [
                    InlineKeyboardButton(text="🤖 AI Yaratish", callback_data=f"ts_gen:{topic_code}"),
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ts_del:{topic_code}"),
                ],
                [
                    InlineKeyboardButton(text="👁 Testlarni ko'rish", callback_data=f"ts_view:{topic_code}:0"),
                ],
            ])
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

    # ===== 📋 SHABLONLAR — yagona shablon/import markazi =====
    elif message.text == "📋 Shablonlar":
        if user_id not in ADMINS:
            return
        await message.answer(
            "📋 Shablonlar va Import\n\n"
            "Chap — bo'sh shablon olish, o'ng — to'ldirilganni import qilish:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📋 Topik shablon"), KeyboardButton(text="📥 Topik import")],
                    [KeyboardButton(text="🧪 Test shablon"),  KeyboardButton(text="📥 Test import")],
                    [KeyboardButton(text="📚 Dars shablon"),  KeyboardButton(text="📥 Dars import")],
                    [KeyboardButton(text="🔙 Admin menyu")],
                ],
                resize_keyboard=True
            )
        )
        return

    elif message.text == "📋 Topik shablon":
        if user_id not in ADMINS:
            return
        from shablon_yaratish import shablon_state
        shablon_state[user_id] = {"step": "sinf_fan"}
        await message.answer(
            "📋 Topik kod uchun shablon\n\n"
            "Sinf va fanni yozing:\nMasalan: 1 Ingliz tili"
        )
        return

    elif message.text == "📥 Topik import":
        if user_id not in ADMINS:
            return
        from dts_import_handlers import DTSImportState
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        admin_state[user_id] = None
        await state.set_state(DTSImportState.waiting_excel)
        await message.answer(
            "📄 DTS Excel faylini yuboring\n\n"
            "Bekor qilish: /menu",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_import")
            ]])
        )
        return

    elif message.text == "📥 Test import":
        if user_id not in ADMINS:
            return
        admin_state[user_id] = "test_import"
        await message.answer("📥 Test import\n\nTo'ldirilgan Excel faylni yuboring:")
        return

    elif message.text == "✅ Ha, import qil" and admin_state.get(user_id) == "test_import_confirm":
        if user_id not in ADMINS:
            return
        path = test_import_files.get(user_id)
        admin_state[user_id] = None
        if not path or not os.path.exists(path):
            await message.answer("❌ Fayl topilmadi, qaytadan yuboring.",
                                 reply_markup=get_main_keyboard("Admin"))
            return
        await message.answer("⏳ Import qilinmoqda...", reply_markup=get_main_keyboard("Admin"))
        await import_tests_excel(message, path, user_id)
        try:
            os.remove(path)
        except Exception:
            pass
        test_import_files.pop(user_id, None)
        return

    elif message.text == "❌ Bekor" and admin_state.get(user_id) == "test_import_confirm":
        admin_state[user_id] = None
        path = test_import_files.pop(user_id, None)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        await message.answer("❌ Import bekor qilindi.",
                             reply_markup=get_main_keyboard("Admin"))
        return

    elif message.text == "📚 Dars shablon":
        if user_id not in ADMINS:
            return
        await lesson_admin.la_show_grades(message)
        return

    elif message.text == "📥 Dars import":
        if user_id not in ADMINS:
            return
        await state.set_state(lesson_admin.LessonAdminState.waiting_excel)
        await message.answer("📥 Dars import\n\nTo'ldirilgan Excel faylini yuboring:")
        return

    elif message.text == "🔙 Admin menyu":
        if user_id not in ADMINS:
            return
        await message.answer("⚙️ Admin menyusi", reply_markup=get_main_keyboard("Admin"))
        return
    # ===== Shablonlar markazi tugadi =====

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
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl import Workbook
        import io

        # Tanlangan mavzu kodini olish
        topic_code = ""
        grade = ""
        if user_id in topic_stats_state:
            topic_code = topic_stats_state[user_id].get("selected_topic", "")
            grade = str(topic_stats_state[user_id].get("grade", ""))

        # Sinf bo'yicha age_group
        age_map = {
            "1": "6-7", "2": "7-8", "3": "8-9", "4": "9-10",
            "5": "10-11", "6": "11-12", "7": "12-13", "8": "13-14",
            "9": "14-15", "10": "15-16", "11": "16-17"
        }
        age_group = age_map.get(grade, "10-11")

        wb = Workbook()
        ws = wb.active
        ws.title = "TESTLAR"

        headers = [
            "topic_code", "difficulty", "situation", "question",
            "option_a", "option_b", "option_c", "option_d",
            "correct_answer", "explanation", "question_type",
            "is_latex", "image_url", "audio_text", "language",
            "life_level", "age_group", "time_limit"
        ]

        # Header qatori
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="2E86AB")
            cell.alignment = Alignment(horizontal="center")

        # 40 ta qator — har biri uchun difficulty va nom
        def get_difficulty(n):
            if n <= 10: return "oson"
            elif n <= 20: return "o'rta"
            elif n <= 30: return "qiyin"
            else: return "murakkab"

        for i in range(1, 41):
            diff = get_difficulty(i)
            row = [
                topic_code,              # topic_code — o'zi
                diff,                    # difficulty
                "oddiy",                 # situation
                "",                      # question
                "",                      # option_a
                "",                      # option_b
                "",                      # option_c
                "",                      # option_d
                "",                      # correct_answer
                "",                      # explanation
                "single_choice",         # question_type
                False,                   # is_latex
                f"{topic_code}-{i}",     # image_url — kod-1, kod-2...
                "",                      # audio_text
                "uz",                    # language
                1,                       # life_level
                age_group,               # age_group
                60,                      # time_limit
            ]
            ws.append(row)
            # Difficulty rangini ko'rsatish
            colors = {"oson": "C8F7C5", "o'rta": "FFF3CD", "qiyin": "FFD7C4", "murakkab": "F5C6CB"}
            ws.cell(row=i+1, column=2).fill = PatternFill("solid", fgColor=colors.get(diff, "FFFFFF"))

        # Ustun kengliklari
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 10
        ws.column_dimensions['D'].width = 50
        for col in ['E','F','G','H']:
            ws.column_dimensions[col].width = 20
        ws.column_dimensions['I'].width = 15
        ws.column_dimensions['J'].width = 30

        # Ma'lumot varag'i
        ws2 = wb.create_sheet("MA'LUMOT")
        ws2.append(["Maydon", "Qiymatlar"])
        ws2.append(["difficulty", "oson | o'rta | qiyin | murakkab"])
        ws2.append(["situation", "oddiy | hayotiy | laboratoriya"])
        ws2.append(["question_type", "single_choice | write_answer | true_false"])
        ws2.append(["correct_answer", "A | B | C | D  (yoki matn)"])
        ws2.append(["is_latex", "True | False"])
        ws2.append(["language", "uz | ru | en"])
        ws2.append(["age_group", f"{age_group} (avtomatik)"])
        ws2.append(["time_limit", "60 (sekund)"])
        ws2.append(["", ""])
        ws2.append(["Mavzu kodi", topic_code or "—"])
        ws2.append(["Sinf", f"{grade}-sinf"])
        ws2.append(["", ""])
        ws2.append(["1-10 qator", "OSON 🟢"])
        ws2.append(["11-20 qator", "O'RTA 🟡"])
        ws2.append(["21-30 qator", "QIYIN 🟠"])
        ws2.append(["31-40 qator", "MURAKKAB 🔴"])

        # Xotiraga saqlash
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        fname = f"shablon_{topic_code or 'mavzu'}.xlsx"
        from aiogram.types import BufferedInputFile
        await message.answer_document(
            BufferedInputFile(buf.read(), filename=fname),
            caption=(
                f"📋 Test shabloni tayyor!\n\n"
                f"🔑 Mavzu kodi: {topic_code or '—'}\n"
                f"🎓 Sinf: {grade or '—'}\n"
                f"👶 Yosh guruhi: {age_group}\n\n"
                f"📝 40 ta qator:\n"
                f"🟢 1-10: Oson\n"
                f"🟡 11-20: O'rta\n"
                f"🟠 21-30: Qiyin\n"
                f"🔴 31-40: Murakkab\n\n"
                f"Faqat bo'sh ustunlarni to'ldiring!"
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
        elif message.text in (HOME, HOME2):

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
    # BIRINCHI call.answer() — Telegram "yuklanyapti" ni darhol to'xtatadi
    try:
        await call.answer()
    except Exception:
        pass
    try:
        await _test_buttons_inner(call, state, user_id)
    except Exception as _e:
        await _error_and_home(call, user_id, _e, "Xatolik")


async def _test_buttons_inner(call: CallbackQuery, state: FSMContext, user_id: int):

    # ═══ DTS NAVIGATOR ═══


    # ═══ BARCHA DTS_ CALLBACKLAR (to'liq) ═══
    if call.data.startswith("dts_"):
        import dts_import_handlers as _dts
        d = call.data

        # Navigator
        if d == "dts_navigator":      await _dts.dts_navigator(call); return
        if d == "dts_menu":           await _dts.dts_menu(call); return
        if d == "dts_search":         await _dts.dts_search(call); return
        if d == "dts_fast_search":    await _dts.dts_fast_search(call); return
        if d == "dts_adv_search":     await _dts.dts_adv_search(call); return
        if d == "dts_import":         await _dts.dts_import(call); return
        if d == "dts_confirm_import": await _dts.dts_confirm_import(call); return
        if d == "dts_problems":       await _dts.dts_problems(call); return
        if d == "dts_download_errors":await _dts.dts_download_errors(call); return
        if d == "dts_cancel_import":  await _dts.dts_cancel_import(call); return
        if d == "dts_export":
            try: await _dts.dts_export(call)
            except: pass
            return

        if d.startswith("dts_grade_"):   await _dts.dts_grade(call); return
        if d.startswith("dts_subject_"): await _dts.dts_subject(call); return
        if d.startswith("dts_quarter_"): await _dts.dts_quarter(call); return
        if d.startswith("dts_bob_"):     await _dts.dts_bob(call); return
        if d.startswith("dts_bolim_"):   await _dts.dts_bolim(call); return
        if d.startswith("dts_mavzu_"):   await _dts.dts_mavzu(call); return
        if d.startswith("dts_small_"):   await _dts.dts_small(call); return
        if d.startswith("dts_adv_"):     await _dts.dts_adv_grade(call); return
        return  # Noma'lum dts_ callback — jimgina o'tkazib yubor
    # ════════════════════════════

    if call.data.startswith("ts_start:"):
        topic_code = call.data.split(":")[1]
        from test_engine import start_test
        conn2 = psycopg2.connect(DATABASE_URL); cur2 = conn2.cursor()
        cur2.execute("""
            SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer, explanation, question_type,
                   is_latex, image_url, audio_text, language, time_limit
            FROM generated_tests WHERE topic_code=%s ORDER BY RANDOM() LIMIT 20
        """, (topic_code,))
        tests = cur2.fetchall(); cur2.close(); conn2.close()
        if not tests:
            await call.message.answer("❌ Bu mavzu uchun test yo'q!")
            return
        await start_test(call.from_user.id, tests, call.message)
        return

    # ═══════════════════════

    if call.data.startswith("next_lesson_"):
        topic_code = call.data.replace("next_lesson_", "")
        await open_teacher_lesson(call.message, topic_code, _user_id=call.from_user.id)
        await call.answer()
        return

    if call.data == "force_dashboard":
        await call.answer()
        try:
            from student_dashboard import build_dashboard_full
            text, kb = await build_dashboard_full(call.from_user.id)
            await call.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
        return

    if call.data == "go_sleep":
        await call.answer()
        await call.message.edit_text(
            "😴 Yaxshi uxlang!\n🌙 Ertaga yanada kuchli bo'lasiz! 💪"
        )
        return

    if call.data == "go_rest":
        await call.answer()
        await call.message.edit_text(
            "🎮 Yaxshi dam oling!\n"
            "Ruhiy kuch to'plash ham o'rganish! 💚"
        )
        return

    if call.data.startswith("sh_"):
        from shablon_yaratish import handle_shablon_callback
        await handle_shablon_callback(call, user_id)
        return

    if call.data.startswith("sinov_"):
        from test_sinovi import handle_sinov_callback
        await handle_sinov_callback(call, user_id)
        return

    if call.data.startswith("ts_"):
        parts = call.data.split(":")
        action = parts[0][3:]  # excel, import, gen, del, view

        if action == "excel":
            topic_code = parts[1]
            # Excel shablon yuborish
            topic_stats_state[user_id]["selected_topic"] = topic_code
            await call.answer()
            # Excel shablon generatsiya
            import openpyxl, io
            from openpyxl.styles import Font, PatternFill
            from aiogram.types import BufferedInputFile
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "TESTLAR"
            headers = ["topic_code","difficulty","situation","question","option_a","option_b","option_c","option_d","correct_answer","explanation","question_type","is_latex","image_url","audio_text","language","life_level","age_group","time_limit"]
            for col, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=h)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="2E86AB")
            conn_t = psycopg2.connect(DATABASE_URL)
            cur_t = conn_t.cursor()
            cur_t.execute("SELECT grade FROM dts_tree WHERE topic_code=%s LIMIT 1", (topic_code,))
            row_t = cur_t.fetchone()
            cur_t.close(); conn_t.close()
            grade = row_t[0] if row_t else "1"
            age_map = {"1":"6-7","2":"7-8","3":"8-9","4":"9-10","5":"10-11","6":"11-12","7":"12-13","8":"13-14","9":"14-15","10":"15-16","11":"16-17"}
            age_group = age_map.get(str(grade), "10-11")
            def get_diff(n):
                if n<=10: return "oson"
                elif n<=20: return "o'rta"
                elif n<=30: return "qiyin"
                else: return "murakkab"
            for i in range(1, 41):
                ws.append([topic_code, get_diff(i), "oddiy", "", "", "", "", "", "", "", "single_choice", False, f"{topic_code}-{i}", None, "uz", 1, age_group, 60])
            buf = io.BytesIO()
            wb.save(buf); buf.seek(0)
            await call.message.answer_document(
                BufferedInputFile(buf.read(), filename=f"shablon_{topic_code}.xlsx"),
                caption=f"📋 Shablon: {topic_code}"
            )

        elif action == "import":
            topic_code = parts[1]
            admin_state[user_id] = "test_import"
            await call.answer()
            await call.message.answer("📥 Excel fayl yuboring")

        elif action == "gen":
            topic_code = parts[1]
            await call.answer("🤖 AI yaratmoqda...", show_alert=True)
            # DTS dan ma'lumot olish
            conn_g = psycopg2.connect(DATABASE_URL)
            cur_g = conn_g.cursor()
            cur_g.execute("""
                SELECT grade, subject_name, mavzu_name, kichik_name
                FROM dts_tree WHERE topic_code=%s LIMIT 1
            """, (topic_code,))
            row_g = cur_g.fetchone()
            cur_g.close(); conn_g.close()
            if row_g:
                grade, subject, mavzu, kichik = row_g
                from ai_generatori import _generate_questions, _age_group
                msg = await call.message.answer(f"🤖 AI ishlamoqda...\n📌 {kichik}")
                try:
                    questions = await _generate_questions(grade, subject, mavzu, kichik, topic_code)
                    conn_s = psycopg2.connect(DATABASE_URL)
                    cur_s = conn_s.cursor()
                    for q in questions:
                        cur_s.execute("""
                            INSERT INTO generated_tests
                            (topic_code,question,option_a,option_b,option_c,option_d,
                             correct_answer,explanation,question_type,is_latex,
                             image_url,audio_text,language,life_level,age_group,
                             time_limit,difficulty,situation)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (topic_code, q.get("question",""), q.get("a",""), q.get("b",""),
                              q.get("c",""), q.get("d",""), q.get("correct",""),
                              q.get("explanation",""), q.get("question_type","single_choice"),
                              False, q.get("image_url"), None, "uz", 1,
                              _age_group(grade), q.get("time_limit",60),
                              q.get("difficulty","oson"), "oddiy"))
                    conn_s.commit(); cur_s.close(); conn_s.close()
                    await msg.edit_text(f"✅ {len(questions)} ta savol yaratildi!\n🔑 {topic_code}")
                except Exception as ex:
                    await msg.edit_text(f"❌ Xato: {ex}")

        elif action == "del":
            topic_code = parts[1]
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"ts_del_yes:{topic_code}"),
                    InlineKeyboardButton(text="❌ Yo'q", callback_data=f"ts_del_no:{topic_code}"),
                ]
            ]))
            await call.answer("⚠️ Tasdiqlang!")

        elif action == "del_yes":
            topic_code = parts[1]
            conn_d = psycopg2.connect(DATABASE_URL)
            cur_d = conn_d.cursor()
            cur_d.execute("DELETE FROM generated_tests WHERE topic_code=%s", (topic_code,))
            cnt = cur_d.rowcount
            conn_d.commit(); cur_d.close(); conn_d.close()
            await call.answer(f"✅ {cnt} ta test o'chirildi!", show_alert=True)
            await call.message.edit_reply_markup(reply_markup=None)

        elif action == "del_no":
            await call.answer("❌ Bekor qilindi")
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 Excel shablon", callback_data=f"ts_excel:{parts[1]}"),
                    InlineKeyboardButton(text="📥 Import", callback_data=f"ts_import:{parts[1]}"),
                ],
                [
                    InlineKeyboardButton(text="🤖 AI Yaratish", callback_data=f"ts_gen:{parts[1]}"),
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ts_del:{parts[1]}"),
                ],
                [
                    InlineKeyboardButton(text="👁 Testlarni ko'rish", callback_data=f"ts_view:{parts[1]}:0"),
                ],
            ]))

        elif action == "view":
            topic_code = parts[1]
            offset = int(parts[2]) if len(parts) > 2 else 0
            conn_v = psycopg2.connect(DATABASE_URL)
            cur_v = conn_v.cursor()
            cur_v.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=%s", (topic_code,))
            total_v = cur_v.fetchone()[0]
            cur_v.execute("""
                SELECT id, difficulty, question, correct_answer
                FROM generated_tests WHERE topic_code=%s
                ORDER BY difficulty, id LIMIT 5 OFFSET %s
            """, (topic_code, offset))
            tests = cur_v.fetchall()
            cur_v.close(); conn_v.close()

            text = f"👁 Testlar: {topic_code}\nJami: {total_v}\n\n"
            for tid, diff, q, correct in tests:
                text += f"[{diff}] {q[:60]}...\n✅ {correct[:30]}\n\n"

            nav = []
            if offset > 0:
                nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ts_view:{topic_code}:{offset-5}"))
            if offset + 5 < total_v:
                nav.append(InlineKeyboardButton(text="▶️", callback_data=f"ts_view:{topic_code}:{offset+5}"))

            kb_rows = []
            if nav: kb_rows.append(nav)
            kb_rows.append([InlineKeyboardButton(text="🗑 Barchasini o'chir", callback_data=f"ts_del:{topic_code}")])

            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
            await call.answer()

        return

    if call.data.startswith("gen_"):
        from ai_generatori import handle_gen_callback
        await handle_gen_callback(call, user_id)
        return

    if call.data.startswith("sts_"):
        from student_settings import handle_settings_callback
        await handle_settings_callback(call, user_id, user_state)
        return

    if call.data.startswith("img_"):
        from image_admin import handle_img_callback
        await handle_img_callback(call, user_id)
        return

    if call.data == "go_home_dashboard":
        await call.answer()
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s", (call.from_user.id,))
        row = cur2.fetchone()
        cur2.close(); conn2.close()
        role = row[0] if row else "🧒 O'quvchi"

        # Eski xabarlarni o'chirish
        try:
            for i in range(call.message.message_id, call.message.message_id - 20, -1):
                try:
                    await bot.delete_message(call.message.chat.id, i)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            from student_dashboard import build_dashboard
            text, kb = await build_dashboard(call.from_user.id)
            await bot.send_message(call.message.chat.id, text, reply_markup=kb)
        except Exception:
            pass
        await bot.send_message(
            call.message.chat.id,
            "🏠 Bosh menyu",
            reply_markup=get_main_keyboard(role)
        )
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

    if call.data in ("lesson_continue", "lesson_continue_force"):
        from datetime import datetime
        now        = datetime.now()
        hour       = now.hour
        weekday    = now.weekday()
        is_night   = hour >= 22 or hour < 6
        is_weekend = weekday >= 5
        forced     = call.data == "lesson_continue_force"

        if is_night and not forced:
            await call.answer("🌙 Tun vaqti! Uxlash sog'liq uchun muhim.", show_alert=True)
            return

        if is_weekend and not forced:
            await call.answer()
            await call.message.answer(
                "🏖 Bugun dam olish kuni!\n\nBaribir dars o'rganasizmi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Ha, o'rganaman", callback_data="lesson_continue_force"),
                    InlineKeyboardButton(text="🎮 Yo'q, dam olaman", callback_data="go_rest"),
                ]])
            )
            return

        await call.answer()
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
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

    if call.data.startswith("reg:"):
        from register import reg_callback
        await reg_callback(call)
        return

    if call.data.startswith("reg_yr:"):
        from register import reg_year_callback
        await reg_year_callback(call)
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

    if call.data == "cancel_import":
        await state.clear()
        admin_state.pop(user_id, None)
        await call.message.edit_text("❌ Import bekor qilindi")
        await call.message.answer("🏠 Bosh menyu", reply_markup=get_main_keyboard("Admin"))
        return

    if call.data.startswith("resume_lesson:"):
        from lesson_engine import build_lesson_data, show_main_step, LESSON_COLS
        await call.answer()
        tc  = call.data.split(":")[1]
        uid = call.from_user.id
        # lesson_progress dan step olish
        try:
            _conn = psycopg2.connect(DATABASE_URL); _cur = _conn.cursor()
            _cur.execute("SELECT current_step FROM lesson_progress WHERE user_id=%s AND topic_code=%s", (uid, tc))
            _row = _cur.fetchone()
            _step = _row[0] if _row else 0
            _cur.execute("SELECT * FROM teacher_lessons WHERE topic_code=%s", (tc,))
            _lesson = _cur.fetchone()
            _cur.execute("SELECT grade, subject_name, mavzu_name FROM dts_tree WHERE topic_code=%s LIMIT 1", (tc,))
            _t = _cur.fetchone()
            _cur.execute("SELECT full_name, gender FROM users WHERE user_id=%s", (uid,))
            _u = _cur.fetchone()
            _cur.close(); _conn.close()
        except Exception as _e:
            await call.message.answer(f"❌ Xato: {_e}"); return
        if not _lesson:
            await call.message.answer("❌ Dars topilmadi"); return
        _main, _simple = build_lesson_data(_lesson)
        lesson_state[uid] = {
            "topic_code": tc, "main_parts": _main, "simple_parts": _simple,
            "main_step": _step, "simple_step": 0, "mode": "main",
            "total": len(_main),
            "full_name": _u[0] if _u else "O'quvchi",
            "fan": _t[1] if _t else "", "mavzu": _t[2] if _t else tc,
            "gender": _u[1] if _u else "",
            "lesson_msg_id": None, "lesson_has_photo": False, "voice_msg_id": None,
        }
        user_state[uid] = "in_lesson"
        await call.message.answer(f"▶️ {_step+1}-qadamdan davom etilmoqda...")
        await show_main_step(uid, call.message.chat.id)
        return

    if call.data.startswith("restart_lesson:"):
        await call.answer()
        tc = call.data.split(":")[1]
        try:
            _conn = psycopg2.connect(DATABASE_URL); _cur = _conn.cursor()
            _cur.execute("DELETE FROM lesson_progress WHERE user_id=%s", (call.from_user.id,))
            _conn.commit(); _cur.close(); _conn.close()
        except: pass
        await open_teacher_lesson(call.message, topic_code=tc, _user_id=call.from_user.id)
        return

    if call.data == "lesson_prev":
        from lesson_engine import lesson_prev
        await call.answer()
        await lesson_prev(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_next":
        from lesson_engine import lesson_next
        await call.answer()
        await lesson_next(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_speak":
        from lesson_engine import lesson_speak
        await call.answer()
        await lesson_speak(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_help":
        from lesson_engine import lesson_help_open
        await call.answer()
        await lesson_help_open(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_help_next":
        from lesson_engine import lesson_help_next
        await call.answer()
        await lesson_help_next(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_help_prev":
        from lesson_engine import lesson_help_prev
        await call.answer()
        await lesson_help_prev(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_help_close":
        from lesson_engine import lesson_help_close
        await call.answer()
        await lesson_help_close(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_exit":
        from lesson_engine import lesson_exit
        await call.answer()
        await lesson_exit(call.from_user.id, call.message.chat.id)
        return

    if call.data == "lesson_finish_confirm":
        from lesson_engine import lesson_finish_and_test
        from storage import lesson_state as _ls
        await call.answer()
        tc = (_ls.get(call.from_user.id) or {}).get("topic_code", "")
        await lesson_finish_and_test(call.from_user.id, call.message.chat.id, tc)
        return


    if call.data in ("tset_start_quick", "tset_start_force"):
        from datetime import datetime
        now        = datetime.now()
        hour       = now.hour
        weekday    = now.weekday()
        is_night   = hour >= 22 or hour < 6
        is_weekend = weekday >= 5
        forced     = call.data == "tset_start_force"

        if is_night and not forced:
            await call.answer("🌙 Tun vaqti! Uxlash sog'liq uchun muhim.", show_alert=True)
            return

        if is_weekend and not forced:
            await call.answer()
            await call.message.answer(
                "🏖 Bugun dam olish kuni!\n\nBaribir test ishlaysizmi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Ha, test", callback_data="tset_start_force"),
                    InlineKeyboardButton(text="🎮 Yo'q, dam olaman", callback_data="go_rest"),
                ]])
            )
            return

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

    if call.data == "test_next_from_result":
        await call.answer()
        from test_engine import test_sessions, next_question
        session = test_sessions.get(call.from_user.id)
        if not session:
            await call.answer("❌ Test tugagan", show_alert=True)
            return
        await next_question(call.from_user.id, call.message)
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

async def notify_on_restart():
    """Bot yangilanganda foydalanuvchilarga xabar — dars/test holatini saqlab."""
    print("🔄 Foydalanuvchilarga xabar yuborilmoqda...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT user_id, role FROM users")
        users = cur.fetchall()
        # Dars o'rtada qolganlar
        cur.execute("""
            SELECT lp.user_id, lp.topic_code, lp.current_step,
                   d.subject_name, d.mavzu_name
            FROM lesson_progress lp
            LEFT JOIN dts_tree d ON d.topic_code = lp.topic_code
            WHERE lp.current_step > 0
        """)
        in_lesson = {r[0]: r for r in cur.fetchall()}
        cur.close(); conn.close()
    except Exception as e:
        print(f"DB xato (restart notify): {e}")
        return

    sent = 0
    for uid, role in users:
        try:
            role_str = str(role or "🧒 O'quvchi")
            if uid in ADMINS:
                role_str = "Admin"
            kb = get_main_keyboard(role_str)

            if uid in in_lesson:
                _, tc, step, subj, mavzu = in_lesson[uid]
                subj  = subj  or tc
                mavzu = mavzu or tc
                text = (
                    f"🔄 Bot yangilandi!\n\n"
                    f"📖 Siz {subj} — {mavzu} darsini o'tayotgan edingiz.\n"
                    f"📍 {step+1}-qadamda to'xtagan edingiz.\n\n"
                    f"Davom etish uchun 👇 Bugungi reja → Davom etish"
                )
            else:
                text = "🔄 Bot yangilandi!\n\nBosh menyuga qaytdingiz 🏠"

            await bot.send_message(uid, text, reply_markup=kb)
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    print(f"✅ {sent}/{len(users)} foydalanuvchiga xabar yuborildi")

async def _health_server():
    """Railway health check uchun oddiy HTTP server."""
    from aiohttp import web
    async def health(request):
        return web.Response(text="OK", status=200)
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("✅ Health server port 8080 da ishga tushdi")


async def main():
    print("BOT ISHGA TUSHDI 🚀")
    init_db()
    # Barcha state larni tozalash
    user_state.clear()
    from storage import lesson_state, temp_user, registration_message, reg_kbd_message
    lesson_state.clear()
    temp_user.clear()
    registration_message.clear()
    reg_kbd_message.clear()
    # Health server
    try:
        asyncio.create_task(_health_server())
    except Exception as _he:
        print(f"Health server xato: {_he}")
    # Foydalanuvchilar jimgina davom etaveradi (xabar yuborilmaydi)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
