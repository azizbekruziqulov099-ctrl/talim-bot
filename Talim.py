try:
    from auto_trainer import auto_train_scheduler, train_all_profiles
except Exception as _ate:
    print(f"auto_trainer import xato: {_ate}")
    async def auto_train_scheduler(): pass
    async def train_all_profiles(*a, **k): return {}
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
from storage import user_state, temp_user, registration_message, reg_kbd_message, admin_state
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
try:
    from db_pool import db as _db_pool, release as _db_release, get_user_cached, invalidate_user
    _pool_available = True
except:
    _db_pool=None; _db_release=None; _pool_available=False

def _get_db_conn():
    """Connection pool dan ulanish olish."""
    if _pool_available and _db_pool:
        try: return _db_pool()
        except: pass
    return psycopg2.connect(DATABASE_URL)
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

conn = _get_db_conn()
cur = conn.cursor()

user_locks = {}
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

    conn = _get_db_conn()
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
    conn = _get_db_conn()
    cur = conn.cursor()

    # user_id INTEGER -> BIGINT (Telegram ID lari INTEGER chegarasidan oshib ketadi)
    try:
        cur.execute("ALTER TABLE users ALTER COLUMN user_id TYPE BIGINT")
        cur.execute("ALTER TABLE survey_answers ALTER COLUMN user_id TYPE BIGINT")
        conn.commit()
    except Exception:
        conn.rollback()
    # Books jadvali
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY, title TEXT, fan TEXT, sinf TEXT,
            muallif TEXT, total_pages INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )""")
        conn.commit()
    except: conn.rollback()
    for _add_col in [
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS total_pages INT DEFAULT 0",
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS fan TEXT",
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS sinf TEXT",
        "ALTER TABLE books ADD COLUMN IF NOT EXISTS muallif TEXT",
    ]:
        try: cur.execute(_add_col); conn.commit()
        except: conn.rollback()
    # book_pages, book_exercises
    try:
        cur.execute("""CREATE TABLE IF NOT EXISTS book_pages (
            id SERIAL PRIMARY KEY, book_id INT, page_num INT,
            section_name TEXT, full_text TEXT, exercise_count INT DEFAULT 0,
            UNIQUE(book_id,page_num)
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS book_exercises (
            id SERIAL PRIMARY KEY, book_id INT, page_num INT,
            mavzu TEXT, fan TEXT, sinf TEXT,
            ex_type TEXT DEFAULT 'misol', savol TEXT, qiyinlik TEXT DEFAULT 'orta'
        )""")
        conn.commit()
    except: conn.rollback()

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
    # Kitob va bilim jadvallari
    for _tbl in [
        "CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT, fan TEXT, sinf TEXT, muallif TEXT, file_id TEXT, created_at TIMESTAMP DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS book_sections (id SERIAL PRIMARY KEY, book_id INT, title TEXT, from_page INT, to_page INT, tartib INT)",
        "CREATE TABLE IF NOT EXISTS book_chunks (id SERIAL PRIMARY KEY, section_id INT, book_id INT, matn TEXT, latex TEXT, chunk_type TEXT, page_num INT, keywords TEXT)",
        "CREATE TABLE IF NOT EXISTS knowledge_facts (id SERIAL PRIMARY KEY, mavzu TEXT, fan TEXT, sinf TEXT, fact_type TEXT, savol TEXT, javob TEXT, izoh TEXT, yosh_5_7 TEXT, yosh_8_11 TEXT, yosh_12plus TEXT, source_ai TEXT, quality INT DEFAULT 5, book_id INT, chunk_text TEXT, keywords TEXT, created_at TIMESTAMP DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS weak_topics (id SERIAL PRIMARY KEY, mavzu TEXT, fan TEXT, error_count INT DEFAULT 1, last_error TIMESTAMP DEFAULT NOW(), UNIQUE(mavzu, fan))",
        "CREATE TABLE IF NOT EXISTS books (id SERIAL PRIMARY KEY, title TEXT, fan TEXT, sinf TEXT, muallif TEXT, total_pages INT, created_at TIMESTAMP DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS book_pages (id SERIAL PRIMARY KEY, book_id INT, page_num INT, section_name TEXT, full_text TEXT, exercise_count INT DEFAULT 0, UNIQUE(book_id,page_num))",
        "CREATE TABLE IF NOT EXISTS book_exercises (id SERIAL PRIMARY KEY, book_id INT, page_num INT, mavzu TEXT, fan TEXT, sinf TEXT, ex_type TEXT DEFAULT 'misol', savol TEXT, qiyinlik TEXT DEFAULT 'orta')",
        "CREATE TABLE IF NOT EXISTS rasm_queue (id SERIAL PRIMARY KEY, user_id BIGINT, kod TEXT, done BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS answer_feedback (id SERIAL PRIMARY KEY, question TEXT, answer_given TEXT, correct_answer TEXT, was_correct BOOLEAN, user_id BIGINT, created_at TIMESTAMP DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS book_exercises (id SERIAL PRIMARY KEY, book_id INT, section_id INT, mavzu TEXT, fan TEXT, sinf TEXT, ex_type TEXT, savol TEXT, yechim TEXT, javob TEXT, formula TEXT, qiyinlik TEXT DEFAULT 'orta', source_ai TEXT, created_at TIMESTAMP DEFAULT NOW())",
    ]:
        try: cur.execute(_tbl); conn.commit()
        except: conn.rollback()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS test_corrections (
        id SERIAL PRIMARY KEY,
        test_id INTEGER,
        topic_code TEXT,
        question TEXT,
        user_id BIGINT,
        comment TEXT,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT NOW()
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

    conn = _get_db_conn()
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

    conn = _get_db_conn()
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

    conn = _get_db_conn()
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

    conn = _get_db_conn()
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

    conn = _get_db_conn()
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

    conn = _get_db_conn()
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
    # Collage handlers → handler_collage.py
    try:
        from handler_collage import handle_collage_msg
        if await handle_collage_msg(message, user_id, admin_state, user_state, temp_user, bot): return
    except Exception as _ce: print(f"collage: {_ce}")
    # ══ TO'GARAK YARATISH STATE ══
    if user_state.get(user_id) == "tg_create_nomi" and message.text:
        temp_user[user_id]["tg_nomi"] = message.text.strip()
        user_state[user_id] = "tg_create_fan"
        await message.answer("📖 Fan nomini yozing (Matematika, Ingliz tili...):")
        return

    if user_state.get(user_id) == "tg_create_fan" and message.text:
        temp_user[user_id]["tg_fan"] = message.text.strip()
        user_state[user_id] = "tg_create_parol"
        await message.answer("🔑 Parol o'rnating (harf va raqam, 4 ta va ko'p):")
        return

    if user_state.get(user_id) == "tg_create_parol" and message.text:
        parol = message.text.strip()
        from togarak import check_parol
        if not check_parol(parol):
            await message.answer("❌ Parol kamida 4 belgi bo'lsin!"); return
        temp_user[user_id]["tg_parol"] = parol
        user_state[user_id] = "tg_create_oylik"
        await message.answer("💰 Oylik to'lov miqdorini yozing (so'mda, 0 = bepul):")
        return

    if user_state.get(user_id) == "tg_create_oylik" and message.text:
        try: summa = int(message.text.strip().replace(" ","").replace(",",""))
        except: summa = 0
        temp_user[user_id]["tg_summa"] = summa
        user_state[user_id] = "tg_create_sana"
        await message.answer("📅 Oylik to'lov kunini yozing (1-28):")
        return

    if user_state.get(user_id) == "tg_create_sana" and message.text:
        try: sana = max(1, min(28, int(message.text.strip())))
        except: sana = 1
        d = temp_user.get(user_id, {})
        from togarak import create_togarak
        tid = create_togarak(
            teacher_id=user_id,
            nomi=d.get("tg_nomi","To'garak"),
            fan=d.get("tg_fan",""),
            parol=d.get("tg_parol","0000"),
            oylik_summa=d.get("tg_summa",0),
            oylik_sana=sana
        )
        user_state.pop(user_id,None)
        await message.answer(
            f"✅ To'garak yaratildi!\n"
            f"📚 {d.get('tg_nomi')}\n"
            f"🔑 Parol: {d.get('tg_parol')}\n"
            f"🔢 ID: {tid}\n\n"
            f"O'quvchilarga ID va parolni bering!"
        )
        return

    # O'quvchi to'garakka qo'shilish
    if user_state.get(user_id) == "stg_join_id" and message.text:
        try: tgid = int(message.text.strip())
        except:
            await message.answer("❌ ID raqam bo'lishi kerak!"); return
        user_state.pop(user_id, None)
        from togarak import send_join_request
        res = send_join_request(tgid, user_id)
        if res["ok"]:
            # O'qituvchiga xabar yuborish
            try:
                conn2=_get_db_conn();cur2=conn2.cursor()
                cur2.execute("SELECT full_name,class FROM users WHERE user_id=%s",(user_id,))
                u=cur2.fetchone(); cur2.close(); conn2.close()
                uname = f"{u[0]} ({u[1] or ''})" if u else str(user_id)
                await message.bot.send_message(
                    res["teacher_id"],
                    f"📨 Yangi so'rov!\n👤 {uname}\n📚 {res['togarak_nomi']}\n\nQabul qilasizmi?",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="✅ Qabul", callback_data=f"tg_req_approve:{user_id}|{tgid}"),
                        InlineKeyboardButton(text="❌ Rad",   callback_data=f"tg_req_reject:{user_id}|{tgid}"),
                    ]])
                )
            except Exception as e:
                print(f"teacher notify: {e}")
            await message.answer(f"✅ So'rov yuborildi!\n⏳ O'qituvchi tasdiqlashini kuting.")
        else:
            await message.answer(res["msg"])
        return


    # Shaxsiy xabar yuborish
    if str(admin_state.get(user_id) or "").startswith("tg_send_pm:") and message.text:
        parts3=str(admin_state[user_id]).split(":")
        tgid3,uid3=int(parts3[1]),int(parts3[2])
        admin_state.pop(user_id,None)
        matn=message.text.strip()
        from togarak import send_group_message
        send_group_message(tgid3, user_id, matn, receiver_id=uid3)
        # Qabul qiluvchiga yuborish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(user_id,))
        sender_name=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        try:
            await message.bot.send_message(uid3, f"💬 {sender_name}:\n{matn}")
        except: pass
        await message.answer("✅ Yuborildi!")
        return

    if str(admin_state.get(user_id) or "").startswith("tg_reja_add_manual:") and message.text:
        tgid=int(str(admin_state[user_id]).split(":")[1])
        admin_state.pop(user_id,None)
        from togarak import add_to_reja
        add_to_reja(tgid, message.text.strip(), "maxsus")
        await message.answer(f"✅ '{message.text.strip()}' rejaga qo'shildi!")
        return

    if str(admin_state.get(user_id) or "").startswith("hw_submit:") and message.text:
        parts3=str(admin_state[user_id]).split(":")
        hw_id3,tgid3=int(parts3[1]),int(parts3[2])
        admin_state.pop(user_id,None)
        from features import submit_homework
        submit_homework(hw_id3,user_id,message.text.strip())
        # O'qituvchiga xabar
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT teacher_id,mavzu FROM homework WHERE id=%s",(hw_id3,))
        hw2=cur2.fetchone()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(user_id,))
        uname=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        if hw2:
            try: await message.bot.send_message(hw2[0],
                f"📝 Yangi topshiriq!\n👤 {uname}\n📌 {hw2[1]}\n\n{message.text[:200]}")
            except: pass
        await message.answer("✅ Vazifa topshirildi!")
        return

    if str(admin_state.get(user_id) or "").startswith("hw_new:") and message.text:
        parts3=str(admin_state[user_id]).split(":")
        tgid3,step=int(parts3[1]),parts3[2]
        if step=="mavzu":
            temp_user[user_id]["hw_mavzu"]=message.text.strip()
            admin_state[user_id]=f"hw_new:{tgid3}:topshiriq"
            await message.answer("📝 Topshiriq matnini yozing:")
        elif step=="topshiriq":
            temp_user[user_id]["hw_topshiriq"]=message.text.strip()
            admin_state[user_id]=f"hw_new:{tgid3}:deadline"
            await message.answer("📅 Deadline sanasini yozing (DD.MM.YYYY) yoki 'yoq' deng:")
        elif step=="deadline":
            admin_state.pop(user_id,None)
            mavzu=temp_user[user_id].get("hw_mavzu","")
            topshiriq=temp_user[user_id].get("hw_topshiriq","")
            deadline=None
            if message.text.strip().lower() not in ("yoq","yo'q","-"):
                try:
                    from datetime import datetime
                    deadline=datetime.strptime(message.text.strip(),"%d.%m.%Y").date()
                except: pass
            from features import add_homework
            from togarak import get_group_members, send_group_message
            hw_id=add_homework(tgid3,user_id,mavzu,topshiriq,deadline)
            # A'zolarga xabar
            members=get_group_members(tgid3)
            dl_txt=str(deadline) if deadline else "muddatsiz"
            for uid3 in members:
                try: await message.bot.send_message(uid3,
                    f"📝 Yangi uyga vazifa!\n📌 {mavzu}\n{topshiriq}\n📅 {dl_txt}")
                except: pass
            await message.answer(f"✅ Vazifa qo'shildi va {len(members)} ta o'quvchiga yuborildi!")
        return

    # Guruhga xabar yuborish
    if str(admin_state.get(user_id) or "").startswith("tg_send_msg:") and message.text:
        parts3=str(admin_state[user_id]).split(":")
        tgid3=int(parts3[1]); mode=parts3[2]
        admin_state.pop(user_id,None)
        from togarak import get_group_members, send_group_message
        matn=message.text.strip()
        members=get_group_members(tgid3)
        sent=0
        for uid3 in members:
            if uid3==user_id: continue
            try:
                await message.bot.send_message(uid3, f"📢 To'garak xabari:\n\n{matn}")
                sent+=1
            except: pass
        send_group_message(tgid3, user_id, matn)
        await message.answer(f"✅ Xabar {sent} ta a'zoga yuborildi!")
        return

    # To'garak o'chirish tasdiqlash
    if str(user_state.get(user_id) or "").startswith("tg_del_confirm:") and message.text:
        tgid = int(str(user_state[user_id]).split(":")[1])
        user_state.pop(user_id,None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT parol FROM togaraklar WHERE id=%s AND teacher_id=%s",(tgid,user_id))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        if not row2:
            await message.answer("❌ Topilmadi!"); return
        if message.text.strip() != row2[0]:
            await message.answer("❌ Parol noto'g'ri!"); return
        from togarak import delete_togarak
        delete_togarak(tgid,user_id)
        await message.answer("✅ To'garak o'chirildi!")
        return

    # Kabinet o'zgartirish
    if str(user_state.get(user_id) or "").startswith("kb_change_") and message.text:
        field = str(user_state[user_id]).replace("kb_change_","")
        val = message.text.strip()
        user_state.pop(user_id, None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        col_map = {"name":"full_name","bdate":"birth_date","school":"school"}
        col = col_map.get(field)
        if col:
            cur2.execute(f"UPDATE users SET {col}=%s WHERE user_id=%s",(val,user_id))
            conn2.commit()
        cur2.close(); conn2.close()
        labels = {"name":"Ism","bdate":"Tug'ilgan sana","school":"Maktab"}
        await message.answer(f"✅ {labels.get(field,field)} yangilandi: {val}")
        return

    if user_state.get(user_id) == "parent_link_id" and message.text:
        user_state.pop(user_id, None)
        try: child_id = int(message.text.strip())
        except:
            await message.answer("❌ Faqat raqam (ID) yozing!"); return
        # Farzand borligini tekshirish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name,class FROM users WHERE user_id=%s",(child_id,))
        child=cur2.fetchone()
        if not child:
            cur2.close(); conn2.close()
            await message.answer("❌ Bu ID bilan foydalanuvchi topilmadi!"); return
        try:
            cur2.execute("INSERT INTO parent_child(parent_id,child_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                        (user_id,child_id))
            conn2.commit()
        except: pass
        cur2.close(); conn2.close()
        await message.answer(f"✅ {child[0]} ({child[1] or '-'}) sizning farzandingiz sifatida ulandi!")
        return

    if str(admin_state.get(user_id) or "").startswith("parent_send_msg:") and message.text:
        teacher_id=int(str(admin_state[user_id]).split(":")[1])
        admin_state.pop(user_id, None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(user_id,))
        sender=(cur2.fetchone() or ["Ota-ona"])[0]; cur2.close(); conn2.close()
        try:
            await message.bot.send_message(teacher_id,
                f"📨 Ota-ona xabari ({sender}):\n{message.text}")
            await message.answer("✅ O'qituvchiga yuborildi!")
        except:
            await message.answer("❌ O'qituvchiga yuborib bo'lmadi.")
        return

    if str(admin_state.get(user_id) or "").startswith("tg_reja_vaqt_save:") and message.text:
        parts3=str(admin_state[user_id]).split(":"); tgid3,reja_id3,kun_id3=int(parts3[1]),int(parts3[2]),int(parts3[3])
        admin_state.pop(user_id,None)
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        vaqt=message.text.strip()
        conn2=_get_db_conn();cur2=conn2.cursor()
        try:
            cur2.execute("UPDATE togarak_reja SET dars_kuni=%s, dars_vaqt=%s WHERE id=%s",
                        (KUNLAR[kun_id3], vaqt, reja_id3))
            # Jadval jadvaliga ham qo'shamiz
            cur2.execute("DELETE FROM togarak_jadval WHERE togarak_id=(SELECT togarak_id FROM togarak_reja WHERE id=%s) AND kun_id=%s",(reja_id3,kun_id3))
            cur2.execute("""SELECT togarak_id FROM togarak_reja WHERE id=%s""",(reja_id3,))
            tg_id_r=(cur2.fetchone() or [tgid3])[0]
            cur2.execute("INSERT INTO togarak_jadval(togarak_id,kun_id,kun_nomi,boshlanish) VALUES(%s,%s,%s,%s)",
                        (tg_id_r,kun_id3,KUNLAR[kun_id3],vaqt))
            conn2.commit()
        except Exception as e: conn2.rollback(); print(f"reja_vaqt: {e}")
        cur2.close(); conn2.close()
        await message.answer(f"✅ {KUNLAR[kun_id3]}: {vaqt} — belgilandi!")
        return

    if str(admin_state.get(user_id) or "").startswith("tg_jadval_vaqt:") and message.text:
        parts3=str(admin_state[user_id]).split(":"); tgid3,kun_id3=int(parts3[1]),int(parts3[2])
        admin_state.pop(user_id,None)
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        vaqt=message.text.strip()
        bosh,tug="","" 
        if "-" in vaqt: bosh,tug=vaqt.split("-",1)
        else: bosh=vaqt
        conn2=_get_db_conn();cur2=conn2.cursor()
        try:
            cur2.execute("DELETE FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(tgid3,kun_id3))
            cur2.execute("INSERT INTO togarak_jadval(togarak_id,kun_id,kun_nomi,boshlanish,tugash) VALUES(%s,%s,%s,%s,%s)",
                        (tgid3,kun_id3,KUNLAR[kun_id3],bosh.strip(),tug.strip()))
            conn2.commit()
        except Exception as e: conn2.rollback(); print(f"jadval: {e}")
        cur2.close(); conn2.close()
        await message.answer(
            f"✅ {KUNLAR[kun_id3]}: {bosh.strip()} qo'shildi!\n\n"
            f"📅 Jadval ko'rish uchun to'garak menyusiga qayting."
        )
        return

    if str(admin_state.get(user_id) or "").startswith("tg_new_parol:") and message.text:
        tgid=int(str(admin_state[user_id]).split(":")[1])
        admin_state.pop(user_id,None)
        yangi=message.text.strip()
        if len(yangi)<4: await message.answer("❌ Kamida 4 belgi!"); return
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE togaraklar SET parol=%s WHERE id=%s AND teacher_id=%s",(yangi,tgid,user_id))
        conn2.commit(); cur2.close(); conn2.close()
        await message.answer(f"✅ Parol yangilandi!\n\n🔑 Yangi parol: <code>{yangi}</code>",parse_mode="HTML")
        return

    # Kitob o'chirish — parol tasdiqlash
    if str(admin_state.get(user_id) or "").startswith("kitob_del_confirm:") and message.text:
        book_id2=int(str(admin_state[user_id]).split(":")[1])
        entered=message.text.strip()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT parol,title FROM books WHERE id=%s",(book_id2,))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        if not row2:
            await message.answer("❌ Kitob topilmadi!"); admin_state.pop(user_id,None); return
        parol2,title2=row2
        if entered != (parol2 or "0000"):
            await message.answer(f"❌ Parol noto'g'ri! Kitob o'chirilmadi."); admin_state.pop(user_id,None); return
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("DELETE FROM book_exercises WHERE book_id=%s",(book_id2,))
        cur2.execute("DELETE FROM book_pages WHERE book_id=%s",(book_id2,))
        cur2.execute("DELETE FROM books WHERE id=%s",(book_id2,))
        conn2.commit();cur2.close();conn2.close()
        admin_state.pop(user_id,None)
        await message.answer(f"✅ '{title2}' o'chirildi!")
        return

    # Kitob paroli o'rnatish
    if str(admin_state.get(user_id) or "").startswith("kitob_set_parol:") and message.text:
        book_id2=int(str(admin_state[user_id]).split(":")[1])
        parol2=message.text.strip()
        if not (parol2.isdigit() and len(parol2)==4):
            await message.answer("❌ 4 xonali raqam yozing!"); return
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE books SET parol=%s WHERE id=%s",(parol2,book_id2))
        conn2.commit();cur2.close();conn2.close()
        admin_state.pop(user_id,None)
        await message.answer(f"✅ Parol {parol2} o'rnatildi!")
        return

    # Kitob bet navigatsiya
    if str(admin_state.get(user_id) or "").startswith("kitob_goto:") and message.text:
        try: page2 = int(message.text.strip())
        except:
            await message.answer("❌ Faqat raqam yozing!"); return
        book_id2 = int(str(admin_state[user_id]).split(":")[1])
        admin_state.pop(user_id, None)
        from kitob_bazasi import get_page, render_page_as_image
        pg = get_page(book_id2, page2)
        if not pg:
            await message.answer(f"❌ Bet {page2} topilmadi!"); return
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT total_pages FROM books WHERE id=%s",(book_id2,))
        tot2=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
        nav=[]
        if page2>1: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"kitob_bet:{book_id2}:{page2-1}"))
        nav.append(InlineKeyboardButton(text=f"📄 {page2}/{tot2}",callback_data=f"kitob_goto:{book_id2}"))
        if page2<tot2: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"kitob_bet:{book_id2}:{page2+1}"))
        kb2=InlineKeyboardMarkup(inline_keyboard=[nav,[
            InlineKeyboardButton(text="📝 Matn",callback_data=f"kitob_matn:{book_id2}:{page2}"),
            InlineKeyboardButton(text="🎯 Misollar",callback_data=f"kitob_test:{book_id2}:{page2}")
        ]])
        img2=await render_page_as_image(pg["text"],page2)
        caption2=f"📖 Bet {page2}" + (f" — {pg['section']}" if pg.get("section") else "")
        if img2:
            from aiogram.types import BufferedInputFile
            await message.answer_photo(BufferedInputFile(img2,f"bet_{page2}.png"),caption=caption2,reply_markup=kb2)
        else:
            await message.answer(pg["text"][:800],reply_markup=kb2)
        return

    # Qo'lda terish — ma'lumotlar
    if admin_state.get(user_id) == "kitob_qolda_info" and message.text:
        parts3 = message.text.strip().split("|")
        title3 = parts3[0].strip() if len(parts3)>0 else "Kitob"
        fan3   = parts3[1].strip() if len(parts3)>1 else "Fan"
        sinf3  = parts3[2].strip() if len(parts3)>2 else "1"
        mual3  = parts3[3].strip() if len(parts3)>3 else ""
        admin_state.pop(user_id, None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("INSERT INTO books(title,fan,sinf,muallif,total_pages) VALUES(%s,%s,%s,%s,0) RETURNING id",
                    (title3,fan3,sinf3,mual3))
        book_id3=cur2.fetchone()[0]; conn2.commit(); cur2.close(); conn2.close()
        admin_state[user_id] = f"kitob_qolda_bet:{book_id3}:1"
        await message.answer(
            f"✅ {title3} yaratildi!\n\n"
            "📝 Bet 1 matnini yozing:\n"
            "Tugash: <code>tugat</code>",
            parse_mode="HTML"
        )
        return

    # Qo'lda terish — betlar
    if str(admin_state.get(user_id) or "").startswith("kitob_qolda_bet:") and message.text:
        parts3 = str(admin_state[user_id]).split(":")
        book_id3, page_num3 = int(parts3[1]), int(parts3[2])
        text3 = message.text.strip()
        # Menu tugmalarini o'tkazib yuborish
        menu_items = {"📚 Kitoblar ▾","🚀 Mavzu tayyorla","📋 Shablonlar",
                     "🧠 Bilimlar ▾","📊 Hisobotlar & Xatolar","👥 Foydalanuvchilar",
                     "🖼 Rasmlar boshqaruvi","🎨 AI Rasm yaratish","⚙️ Akkaunt sozlamalari",
                     "📖 Darslar holati","🧭 DTS topik boshqaruvi"}
        if text3 in menu_items or text3.startswith("/"):
            return
        if text3.lower() in ("tugat","stop","done"):
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("UPDATE books SET total_pages=%s WHERE id=%s",(page_num3-1,book_id3))
            conn2.commit(); cur2.close(); conn2.close()
            admin_state.pop(user_id,None)
            await message.answer(f"✅ Kitob tayyor!\n📄 {page_num3-1} bet\n🔑 ID: {book_id3}")
            return
        from kitob_bazasi import extract_exercises
        exercises = extract_exercises(text3)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""INSERT INTO book_pages(book_id,page_num,full_text,exercise_count)
            VALUES(%s,%s,%s,%s) ON CONFLICT(book_id,page_num) DO UPDATE SET full_text=EXCLUDED.full_text""",
            (book_id3,page_num3,text3,len(exercises)))
        for ex in exercises:
            cur2.execute("INSERT INTO book_exercises(book_id,page_num,savol) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                        (book_id3,page_num3,ex[:1000]))
        cur2.execute("UPDATE books SET total_pages=GREATEST(total_pages,%s) WHERE id=%s",(page_num3,book_id3))
        conn2.commit(); cur2.close(); conn2.close()
        admin_state[user_id] = f"kitob_qolda_bet:{book_id3}:{page_num3+1}"
        # A4 rasm sifatida ko'rsat
        from kitob_bazasi import render_page_as_image
        img3 = await render_page_as_image(text3, page_num3)
        kb3 = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=f"📝 Bet {page_num3+1} yozing", callback_data=f"kitob_next_bet:{book_id3}:{page_num3+1}"),
            InlineKeyboardButton(text="✅ Kitobni tugatish", callback_data=f"kitob_qolda_tugat:{book_id3}:{page_num3}"),
        ]])
        caption3 = f"✅ Bet {page_num3} saqlandi ({len(exercises)} misol)"
        if img3:
            from aiogram.types import BufferedInputFile
            await message.answer_photo(BufferedInputFile(img3,f"bet_{page_num3}.png"), caption=caption3, reply_markup=kb3)
        else:
            await message.answer(caption3, reply_markup=kb3)
        return

    # ═══ BRAIN ═══
    if (user_id not in ADMINS
            and message.text
            and not message.text.startswith("/")
            and user_state.get(user_id) == "ai_mode"):  # FAQAT ai_mode da ishlaydi
        _skip = {
            "⚙️ Sozlamalar","🎯 Bugungi reja","📚 Bilimni mustahkamlash",
            "🧪 Bilimni sinash","📈 Rivojlanishim","🌍 Hamjamiyat","👤 Kabinet",
            "🤖 Yordamchi","👇","✅ Ha, import qil","❌ Bekor",
            "🔙 Ortga","🏠 Bosh menyu","🏠 Bosh ekran",
            "▶️ O'rganishni boshlash","🔊 O'qib berish",
        }
        if message.text not in _skip:
            try:
                from brain import process_message as _b
                _cn = _get_db_conn(); _cu = _cn.cursor()
                _cu.execute("SELECT class FROM users WHERE user_id=%s",(user_id,))
                _gr = _cu.fetchone(); _grade = str(_gr[0]) if _gr else None
                _cu.close(); _cn.close()
                _res = await _b(message.text, user_id, _grade)
                if _res.get("message"):
                    await message.answer(_res["message"])
                if _res.get("action") == "START_TEST" and _res.get("topic"):
                    _c2 = _get_db_conn(); _cu2 = _c2.cursor()
                    _cu2.execute("""SELECT question,option_a,option_b,option_c,option_d,
                           correct_answer,explanation,question_type,is_latex,
                           image_url,audio_text,language,time_limit
                           FROM generated_tests WHERE topic_code=%s
                           ORDER BY RANDOM() LIMIT 20""",
                        (_res["topic"]["topic_code"],))
                    _t = _cu2.fetchall(); _cu2.close(); _c2.close()
                    if _t: await start_test(user_id, _t, message)
                elif _res.get("action") == "START_LESSON" and _res.get("topic"):
                    await open_teacher_lesson(message,
                        topic_code=_res["topic"]["topic_code"], _user_id=user_id)
                elif _res.get("action") == "SHOW_STATS":
                    await continue_learning(message)
            except Exception as _be:
                print(f"brain: {_be}")
            return
    # ════════════════════════════════

    if message.text == "⚙️ Sozlamalar":
        from student_settings import show_settings
        await show_settings(message, user_id)
        return

    if message.text == "📚 Bilimni mustahkamlash":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        _gr = cur2.fetchone()
        _my_grade = str(_gr[0]) if _gr and _gr[0] else "1"

        # Dars bor fanlar (o'z sinfi + CEFR kabi raqamsiz sinflar)
        cur2.execute("""
            SELECT DISTINCT d.subject_name,
                   COUNT(tl.topic_code) as cnt,
                   d.grade
            FROM teacher_lessons tl
            JOIN dts_tree d ON d.topic_code = tl.topic_code
            WHERE (d.grade = %s OR d.grade !~ '^[0-9]+$')
              AND d.is_deleted = FALSE
            GROUP BY d.subject_name, d.grade
            ORDER BY d.grade, d.subject_name
        """, (_my_grade,))
        subjects = cur2.fetchall()
        cur2.close(); conn2.close()

        if not subjects:
            await message.answer("📚 Hali darslar yozilmagan. Admin darslar qo'shishi kerak!")
            return

        rows = []
        for subj, cnt, grade in subjects:
            lbl = f"{grade}-sinf" if str(grade).isdigit() else str(grade)
            icon = "⭐" if str(grade) == str(_my_grade) else "🌐"
            rows.append([InlineKeyboardButton(
                text=f"{icon} {subj} ({cnt} ta dars)",
                callback_data=f"mustah_subj:{grade}:{subj}"
            )])

        await message.answer(
            "📚 Bilimni mustahkamlash\nFan tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return

    if message.text == "📚 To'garaklar":
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s",(user_id,))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        role2 = str(row2[0] if row2 else "")
        from togarak import get_teacher_togaraklar, get_student_togaraklar, togarak_list_kb

        if "qituvchi" in role2:
            # O'QITUVCHI — o'z to'garaklari + yaratish
            tgs = get_teacher_togaraklar(user_id)
            rows2 = [[InlineKeyboardButton(
                text=f"📚 {t['nomi']} ({t['azolar']}/{t['max']})",
                callback_data=f"tg_info:{t['id']}"
            )] for t in tgs]
            rows2.append([InlineKeyboardButton(text="➕ Yangi to'garak ochish", callback_data="tg_yangi")])
            await message.answer(
                f"📚 Mening to'garaklarim ({len(tgs)} ta):",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
            )
        else:
            # O'QUVCHI — a'zo bo'lgan to'garaklar + izlash
            tgs = get_student_togaraklar(user_id)
            rows2 = [[InlineKeyboardButton(
                text=f"📚 {t['nomi']} | 👨‍🏫 {t['teacher']}",
                callback_data=f"stg_info:{t['id']}"
            )] for t in tgs]
            rows2.append([InlineKeyboardButton(text="🔍 To'garak izlash (ID bilan)", callback_data="stg_join")])
            txt = f"📚 Mening to'garaklarim ({len(tgs)} ta):"
            if not tgs:
                txt = "📚 Siz hali hech qaysi to'garakka a'zo emassiz.\n\n🔍 To'garak ID va parolini o'qituvchingizdan oling!"
            await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return

    # Ota-ona message handlers → handler_parent.py

    if message.text == "🎨 Rasm chizdir":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        try:
            cur2.execute("SELECT COUNT(*) FROM images WHERE name LIKE %s AND created_at >= CURRENT_DATE",
                        (f"user_{user_id}_%",))
            today_count = cur2.fetchone()[0]
        except: today_count = 0
        cur2.close(); conn2.close()

        if today_count >= 2:
            await message.answer(
                f"⏰ Kunlik limit: 2 ta rasm\n"
                f"✅ Bugun: {today_count} ta\n\n"
                "Ertaga yana 2 ta rasm yaratish mumkin!"
            )
            return

        qolgan = 2 - today_count
        user_state[user_id] = "user_rasm"
        await message.answer(
            f"🎨 Rasm yaratish\n\n"
            f"📊 Bugun qolgan: {qolgan} ta\n\n"
            "Nimani chizishni xohlaysiz?\n"
            "O'zbek tilida yozing:\n\n"
            "Masalan:\n"
            "• «3 ta qizil olma»\n"
            "• «maktabda dars»\n"
            "• «qishki manzara»"
        )
        return

    if message.text == "/id":
        await message.answer(f"🆔 Sizning Telegram ID ingiz:\n<code>{user_id}</code>\n\nOta-onangizga yuboring!", parse_mode="HTML")
        return

    if message.text == "/stop":
        user_state.pop(user_id, None)
        await message.answer("✅ AI yordamchi o'chirildi.")
        return

    if message.text == "🤖 Yordamchi":
        # Rolni aniqlash
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s",(user_id,))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        role2 = str(row2[0] if row2 else "")
        is_admin = user_id in ADMINS

        if is_admin:
            txt = ("🤖 Admin AI Yordamchi\n\n"
                   "Nima qila olaman:\n"
                   "• Foydalanuvchilar statistikasi\n"
                   "• Test yaratish maslahatlar\n"
                   "• DTS mavzu tahlili\n"
                   "• Excel/shablon yordam\n\n"
                   "Savolingizni yozing 👇")
        elif "qituvchi" in role2:
            txt = ("🤖 O'qituvchi AI Yordamchi\n\n"
                   "Nima qila olaman:\n"
                   "• Dars rejalari tuzish\n"
                   "• Savollar yaratish\n"
                   "• Mavzuni tushuntirish\n"
                   "• To'garak rejalash\n\n"
                   "Savolingizni yozing 👇")
        else:
            txt = ("🤖 O'quvchi AI Yordamchi\n\n"
                   "Nima qila olaman:\n"
                   "• Mavzuni tushuntiraman\n"
                   "• Misol yechamiz\n"
                   "• Test beraman\n"
                   "• Kitobdan misol beraman\n\n"
                   "Savolingizni yozing 👇")

        user_state[user_id] = "ai_mode"
        await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ AI ni o'chirish", callback_data="ai_stop")
        ]]))
        return

    if message.text == "🧪 Bilimni sinash":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        _gr = cur2.fetchone()
        _my_grade = str(_gr[0]) if _gr and _gr[0] else "1"

        # Barcha fanlar (sinf filtrsiz)
        cur2.execute("""
            SELECT DISTINCT d.subject_name,
                   COUNT(DISTINCT g.topic_code) as cnt,
                   d.grade
            FROM generated_tests g
            JOIN dts_tree d ON d.topic_code = g.topic_code
            WHERE d.is_deleted = FALSE
            GROUP BY d.subject_name, d.grade
            ORDER BY d.grade, d.subject_name
        """)
        subjects = cur2.fetchall()
        cur2.close(); conn2.close()

        if not subjects:
            await message.answer("🧪 Hali test mavjud emas. Admin testlar qo'shishi kerak!")
            return

        rows = []
        for subj, cnt, grade in subjects:
            icon = "⭐" if str(grade) == str(_my_grade) else "🌐"
            rows.append([InlineKeyboardButton(
                text=f"{icon} {subj} ({cnt} ta mavzu)",
                callback_data=f"sinash_subj:{grade}:{subj}"
            )])
        rows.append([InlineKeyboardButton(text="⚡ Tezkor (aralash 20ta)", callback_data="tset_start_quick")])

        await message.answer(
            "🧪 Bilimni sinash\nFan tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
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
        conn2 = _get_db_conn()
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
        from togarak import get_student_togaraklar, get_student_progress, get_togarak_progress
        from datetime import datetime
        tgs = get_student_togaraklar(user_id)
        bugun_id = datetime.now().weekday()
        KUNLAR = ["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"]

        txt = "📈 Rivojlanishim\n" + "─"*20 + "\n\n"
        rows2 = []

        if not tgs:
            txt += "📚 Hali hech qaysi to'garakka a'zo emassiz.\n"
        else:
            for t in tgs:
                prog = get_togarak_progress(t["id"])
                sp = get_student_progress(t["id"], user_id)
                bdaraja = "⭐ A'lo" if sp["avg_baho"]>=4.5 else ("👍 Yaxshi" if sp["avg_baho"]>=3.5 else ("📖 O'rta" if sp["avg_baho"]>0 else "—"))
                conn2=_get_db_conn();cur2=conn2.cursor()
                try:
                    cur2.execute("SELECT boshlanish FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(t["id"],bugun_id))
                    j=cur2.fetchone()
                except: j=None
                cur2.close(); conn2.close()
                txt += f"📚 {t['nomi']}\n"
                txt += f"  🧠 Bilim: {bdaraja} | 📋 Davomat: {sp['yoqlama_pct']}%\n"
                if j: txt += f"  🕐 Bugungi dars: {j[0]}\n"
                txt += f"  📊 O'tildi: {prog['pct']}% ({prog['done']}/{prog['total']})\n\n"
                rows2.append([
                    InlineKeyboardButton(text=f"📚 {t['nomi']} — Mavzular",callback_data=f"stg_albomlar:{t['id']}"),
                ])

        rows2.append([InlineKeyboardButton(text="🔍 To'garak izlash", callback_data="stg_join")])
        await message.answer(txt[:3000], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
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
        conn2 = _get_db_conn()
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
            conn2 = _get_db_conn()
            cur2 = conn2.cursor()
            cur2.execute("UPDATE users SET birth_date=%s WHERE user_id=%s", (bdate, user_id))
            conn2.commit(); cur2.close(); conn2.close()
            user_state[user_id] = None
            await message.answer(f"✅ Tug'ilgan kun saqlandi: {message.text}")
        except Exception:
            await message.answer("❌ Format xato! Masalan: 15.03.2015")
        return

    if user_state.get(user_id) == "change_school_settings":
        conn2 = _get_db_conn()
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
        conn = _get_db_conn()
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

    # ── Kitob yuklash matn handler ──
    if (str(admin_state.get(user_id) or "").startswith("ai_rasm_custom") and message.text):
        parts_s = admin_state[user_id].split(":")
        style = parts_s[1] if len(parts_s)>1 else "multik"
        tavsif = message.text.strip()
        admin_state.pop(user_id, None)
        status_r = await message.answer(f"🤔 Tushunmoqda...\n«{tavsif[:60]}»")

        async def do_smart_rasm():
            try:
                from rasim_generator import _tavsif_to_prompt, generate_hf, generate_dalle
                
                await status_r.edit_text(f"🔄 Tarjima qilinmoqda...\n«{tavsif[:60]}»")
                prompt = await _tavsif_to_prompt(tavsif, "ta'lim", "1", style)
                await status_r.edit_text(f"🎨 Chizilmoqda...\n📝 {prompt[:80]}...")

                img = await generate_hf(prompt)
                if not img:
                    img = await generate_dalle(prompt)

                if img:
                    from aiogram.types import BufferedInputFile
                    sent = await message.answer_photo(
                        BufferedInputFile(img, "rasm.png"),
                        caption=f"🎨 {tavsif[:80]}"
                    )
                    await status_r.edit_text(
                        f"✅ Tayyor!\n\nDB ga saqlash uchun nom yozing:\n"
                        f"Masalan: <code>1-01-1-01-01-01-001-1</code>",
                        parse_mode="HTML"
                    )
                    fid = sent.photo[-1].file_id
                    admin_state[user_id] = f"save_rasm:{fid}"
                else:
                    await status_r.edit_text("❌ Rasm yaratilmadi. Qayta urinib ko'ring.")
            except Exception as e:
                await status_r.edit_text(f"❌ {e}")

        asyncio.create_task(do_smart_rasm())
        return

    if admin_state.get(user_id) == "ai_rasm_custom" and message.text:
        tavsif = message.text.strip()
        admin_state.pop(user_id, None)
        status_r = await message.answer(f"⏳ Rasm yaratilmoqda...\n🖌 {tavsif[:60]}")
        async def do_custom_rasm():
            try:
                from rasim_generator import generate_dalle
                img_bytes = await generate_dalle(tavsif)
                if img_bytes:
                    from aiogram.types import BufferedInputFile
                    sent = await message.answer_photo(
                        BufferedInputFile(img_bytes, "rasm.png"),
                        caption=f"🎨 {tavsif[:100]}"
                    )
                    fid = sent.photo[-1].file_id
                    # Nomi so'raladi
                    admin_state[user_id] = f"save_rasm:{fid}"
                    await status_r.edit_text(
                        "✅ Rasm tayyor!\n\nDB ga saqlash uchun nom yozing:\n"
                        "Masalan: <code>1-01-1-01-01-01-001-1</code>",
                        parse_mode="HTML"
                    )
                else:
                    await status_r.edit_text("❌ Rasm yaratilmadi. API kalitni tekshiring.")
            except Exception as e:
                await status_r.edit_text(f"❌ {e}")
        asyncio.create_task(do_custom_rasm())
        return

    if (str(admin_state.get(user_id) or "").startswith("save_rasm:") and message.text):
        fid = admin_state[user_id].split(":",1)[1]
        name = message.text.strip()
        admin_state.pop(user_id, None)
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                        ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                    (name, fid))
        conn2.commit(); cur2.close(); conn2.close()
        await message.answer(f"✅ Saqlandi! Kod: <code>{name}</code>", parse_mode="HTML")
        return

    if admin_state.get(user_id) == "mtt_sinf_fan" and message.text:
        txt_sf = message.text.strip()
        if "|" not in txt_sf:
            await message.answer("❌ Format: <code>sinf | fan</code>\nMasalan: <code>2 | Ingliz tili</code>", parse_mode="HTML")
            return
        parts_sf = txt_sf.split("|", 1)
        gr_sf  = parts_sf[0].strip()
        fan_sf = parts_sf[1].strip()
        admin_state[user_id] = f"mtt_mavzu:{gr_sf}:{fan_sf}"
        await message.answer(
            f"✅ {gr_sf}-sinf | {fan_sf}\n\n"
            f"Endi chorak/mavzularni yozing:\n\n"
            f"1/ Alphabet review\n"
            f"1/ Hello Greetings\n"
            f"2/ My family\n"
            f"2/ My house\n\n"
            f"Format: chorak_raqami/ mavzu_nomi"
        )
        return

    if str(admin_state.get(user_id) or "").startswith("mtt_fan_input:") and message.text:
        gr_fi = admin_state[user_id].split(":")[1]
        fan_fi = message.text.strip()
        admin_state[user_id] = f"mtt_mavzu:{gr_fi}:{fan_fi}"
        await message.answer(
            f"✅ Fan: {fan_fi}\n\n"
            f"Endi mavzularni yozing:\n\n"
            f"1/ Alphabet review\n"
            f"1/ Hello Greetings\n"
            f"2/ My family\n\n"
            f"Format: chorak_raqami/ mavzu_nomi"
        )
        return

    if str(admin_state.get(user_id) or "").startswith("mtt_mavzu:") and message.text:
        parts3 = admin_state[user_id].split(":", 2)
        gr3, fan3 = parts3[1], parts3[2]
        admin_state.pop(user_id, None)
        text3 = message.text.strip()

        # Mavzularni parse qilish
        mavzular3 = []
        for line in text3.split("\n"):
            line = line.strip()
            if not line: continue
            if "/" in line:
                parts_l = line.split("/", 1)
                chorak_n = parts_l[0].strip()
                mavzu_n  = parts_l[1].strip()
                if mavzu_n:
                    mavzular3.append((chorak_n, mavzu_n))

        if not mavzular3:
            await message.answer("❌ Format noto'g'ri!\n\nMisol:\n1/ Alphabet review\n1/ Greetings\n2/ My family")
            admin_state[user_id] = f"mtt_mavzu:{gr3}:{fan3}"
            return

        await message.answer(f"⏳ DTS shablon yaratilmoqda...\n{len(mavzular3)} ta mavzu")

        # 1-QADAM: DTS shablon yaratish
        from shablon_yaratish import _create_shablon
        from aiogram.types import BufferedInputFile
        buf3 = await _create_shablon(gr3, fan3, mavzular3)
        fname3 = f"DTS_{gr3}sinf_{fan3[:15].replace(' ','_')}.xlsx"
        await message.answer_document(
            BufferedInputFile(buf3.read(), filename=fname3),
            caption=(
                f"1️⃣ DTS Shablon tayyor!\n"
                f"🏫 {gr3}-sinf | 📚 {fan3}\n"
                f"📝 {len(mavzular3)} ta mavzu x 2 qator\n\n"
                f"Bu faylni to'ldirib botga yuboring:\n"
                f"Bob, Bo'lim, Kichik mavzu ustunlarini\n\n"
                f"To'ldirib yuborilsa — DTS import qilinadi\n"
                f"va test shabloni tayyorlanadi!"
            )
        )
        # Test sozlamalari — DTS dan keyin
        admin_state[user_id] = f"mtt_test_sozlama:{gr3}:{fan3}"
        from ai_generatori import _gen_settings_kb, gen_state
        state4 = gen_state.get(user_id, {})
        state4["grade"] = gr3; state4["subject"] = fan3
        state4["mavzular_text"] = text3
        state4.setdefault("gen_groups",[
            {"diff":"oson",    "type":"single_choice","count":5},
            {"diff":"orta",    "type":"single_choice","count":5},
            {"diff":"qiyin",   "type":"single_choice","count":5},
            {"diff":"murakkab","type":"single_choice","count":5},
        ])
        gen_state[user_id] = state4
        await message.answer(
            f"2️⃣ Test shablon sozlamalari\n"
            f"🏫 {gr3}-sinf | 📚 {fan3}\n"
            f"📝 {len(mavzular3)} ta mavzu\n\n"
            f"Har qiyinlikdan nechta savol?",
            reply_markup=_gen_settings_kb(state4["gen_groups"])
        )
        return

    if admin_state.get(user_id) == "kitob_yuklash" and message.text:
        txt = message.text.strip().strip("`").strip()
        parts = [x.strip() for x in txt.split("|")]
        if len(parts) < 2:
            await message.answer(
                "❌ Format:\n<code>Kitob nomi | Fan | Sinf | Muallif</code>",
                parse_mode="HTML"
            )
            return
        admin_state[f"{user_id}_kitob_info"] = {
            "title":   parts[0],
            "fan":     parts[1] if len(parts)>1 else "",
            "sinf":    parts[2] if len(parts)>2 else "",
            "muallif": " | ".join(parts[3:]) if len(parts)>3 else "",
        }
        admin_state[user_id] = "kitob_yuklash_pdf"
        info = admin_state[f"{user_id}_kitob_info"]
        await message.answer(
            f"✅ Saqlandi:\n📖 {info['title']}\n"
            f"📚 {info['fan']} | 🏫 {info['sinf']}-sinf\n"
            f"✍️ {info['muallif']}\n\nPDF faylni yuboring 👇"
        )
        return

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

    # ── Excel RASMLAR varog'i bo'lsa — avtomatik rasm yaratish ──
    if (message.document and user_id in ADMINS and
            message.document.file_name and
            (message.document.file_name or "").endswith(".xlsx")):
        # RASMLAR varog'i borligini tekshiramiz
        from io import BytesIO
        buf_check = BytesIO()
        await message.bot.download(message.document.file_id, destination=buf_check)
        buf_check.seek(0)
        try:
            import openpyxl as _opx
            _wb = _opx.load_workbook(buf_check, data_only=True)
            if "RASMLAR" in _wb.sheetnames:
                _wb.close()
                buf_check.seek(0)
                xl_bytes2 = buf_check.read()
                admin_state[f"{user_id}_rasm_xl"] = xl_bytes2
                await message.answer(
                    "🖼 RASMLAR varog\'i topildi!\n\nQaysi uslubda chizilsin?",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🎠 Multik — bolalarga mos (tavsiya)", callback_data="xl_style:multik")],
                        [InlineKeyboardButton(text="📸 Hayotiy — realistik",              callback_data="xl_style:hayotiy")],
                        [InlineKeyboardButton(text="✏️ Chizma — darslik uslubi",          callback_data="xl_style:chizma")],
                        [InlineKeyboardButton(text="📚 Darslik — ta\'lim diagramma",     callback_data="xl_style:darslik")],
                        [InlineKeyboardButton(text="🎮 3D — hajmli",                      callback_data="xl_style:3d")],
                        [InlineKeyboardButton(text="⚡ Avto (multik) — hoziroq",          callback_data="xl_style:multik_auto")],
                        [InlineKeyboardButton(text="🔄 Qayta yaratish (eskilarni o\'chir)", callback_data="xl_style:multik_force")],
                    ])
                )
                return
            _wb.close()
        except: pass

    # ── Kitob PDF yuklash ──
    if (message.document and user_id in ADMINS and
            message.document.file_name and
            message.document.file_name.lower().endswith(".pdf")):
        # State bo'lmasa ham qabul qilamiz
        info = admin_state.get(f"{user_id}_kitob_info", {})
        if not info:
            # Fayl nomidan ma'lumot olish
            fname = message.document.file_name.replace(".pdf","")
            info = {"title": fname, "fan": "Matematika", "sinf": "7", "muallif": ""}
        title   = info.get("title", "Kitob")
        fan     = info.get("fan", "Matematika")
        sinf    = info.get("sinf", "7")
        muallif = info.get("muallif", "")
        fid     = message.document.file_id
        admin_state[user_id] = None
        admin_state.pop(f"{user_id}_kitob_info", None)
        status_k = await message.answer(
            f"📖 {title}\n⏳ PDF qabul qilindi, yuklanmoqda..."
        )

        async def do_process_kitob():
            try:
                import kitob_bazasi as _kb
                import tempfile, os as _os, aiohttp as _ah

                await status_k.edit_text("⏳ Fayl ma'lumoti olinmoqda...")
                print(f"[KITOB] get_file boshlandi")

                try:
                    file_info = await message.bot.get_file(fid)
                    file_path = file_info.file_path
                    print(f"[KITOB] file_path: {file_path}")
                except Exception as fe:
                    print(f"[KITOB] get_file xato: {fe}")
                    await status_k.edit_text(
                        f"❌ Fayl yuklab bo'lmadi!\n"
                        f"Sabab: {fe}\n\n"
                        f"Telegram 20MB dan katta fayllarni bermir.\n"
                        f"Faylni siqib (zip) yoki bo'lib yuboring."
                    )
                    return

                token = message.bot.token
                url = f"https://api.telegram.org/file/bot{token}/{file_path}"

                tmp_k = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                async with _ah.ClientSession() as sess:
                    async with sess.get(url, timeout=_ah.ClientTimeout(total=120)) as resp:
                        chunk_size = 65536
                        downloaded = 0
                        while True:
                            chunk = await resp.content.read(chunk_size)
                            if not chunk: break
                            tmp_k.write(chunk)
                            downloaded += len(chunk)
                            if downloaded % (1024*1024) == 0:
                                mb = downloaded // (1024*1024)
                                print(f"[KITOB] {mb}MB yuklanди")
                tmp_k.close()
                print(f"[KITOB] PDF saqlandi: {tmp_k.name}")

                async def upd(msg):
                    print(f"[KITOB] {msg}")
                    try: await status_k.edit_text(msg)
                    except: pass

                await upd("⏳ Boshlandi...")
                result = await _kb.load_book_to_db(
                    file_path=tmp_k.name,
                    sinf=sinf, fan=fan, muallif=muallif,
                    progress_cb=upd
                )
                _os.remove(tmp_k.name)
                await message.answer(
                    f"✅ Kitob saqlandi!\n📖 {title}\n"
                    f"📄 {result['pages']} bet | 📐 {result['exercises']} misol\n"
                    f"🔑 Book ID: {result['book_id']}"
                )
            except Exception as e:
                import traceback
                print(f"[KITOB ERROR] {e}\n{traceback.format_exc()}")
                await message.answer(f"❌ Xato: {e}")
            finally:
                admin_state.pop(user_id, None)
                admin_state.pop(f"{user_id}_kitob_info", None)

        asyncio.create_task(do_process_kitob())
        return

    # Excel handlers → handler_excel.py
    try:
        from handler_excel import handle_excel_msg
        if await handle_excel_msg(message, user_id, admin_state, user_state, temp_user, bot): return
    except Exception as _ee: print(f"excel: {_ee}")
    # ════════════════════════════

    # ═══ BARCHA DTS_ CALLBACKLAR (to'liq) ═══
    if call.data.startswith("dts_"):
        import dts_import_handlers as _dts
        d = call.data

        # Navigator
        if d == "dts_navigator":      await _dts.dts_navigator(call); return
        if d.startswith("dts_nav_"):
            page = int(d[8:])
            await _dts.dts_navigator(call, page=page); return
        if d.startswith("dts_del_topic:"):
            tc = d[14:]
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("UPDATE dts_tree SET is_deleted=TRUE WHERE topic_code=%s",(tc,))
            # Agar sinf bo'sh qolsa — sinf ham "yo'qoladi" (barcha topiklar o'chirilgan)
            conn2.commit();cur2.close();conn2.close()
            await call.answer("✅ Topik o'chirildi",show_alert=True)
            # Sahifani yangilash
            await _dts.dts_navigator(call)
            return
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


    if call.data.startswith("ts_settings:"):
        # ts_start ga yo'naltirish
        tc_set = call.data.split(":")[1]
        await call.answer()
        # ts_start handler ga pass qilamiz
        call.data = f"ts_start:{tc_set}"

    if call.data.startswith("ts_mavzu:"):
        mavzu_code = call.data[9:]
        # Shu mavzu_code dagi barcha topic_code lar bo'yicha testlar
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""SELECT DISTINCT topic_code FROM dts_tree
            WHERE mavzu_code=%s AND is_deleted=FALSE""", (mavzu_code,))
        topic_codes = [r[0] for r in cur2.fetchall()]
        if not topic_codes:
            topic_codes = [mavzu_code]
        cur2.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code = ANY(%s)",
                    (topic_codes,))
        cnt = cur2.fetchone()[0]
        cur2.execute("SELECT mavzu_name FROM dts_tree WHERE mavzu_code=%s LIMIT 1",(mavzu_code,))
        mname = (cur2.fetchone() or [mavzu_code])[0]
        cur2.close(); conn2.close()
        if cnt == 0:
            await call.message.answer(f"❌ '{mname}' mavzusi uchun test yo'q!"); return
        from storage import user_state as _us
        if not isinstance(_us.get(user_id), dict): _us[user_id] = {}
        _us[user_id].update({
            "ts_topic": topic_codes[0],
            "ts_topic_codes": topic_codes,
            "ts_mavzu_name": mname,
            "ts_count": 20, "ts_diff": "all",
            "ts_timed": True, "ts_write": False,
            "_ts_cnt_total": cnt
        })
        await call.message.answer(
            f"🧪 Mavzu: {mname[:50]}\n📊 Jami: {cnt} ta savol\n\nSozlamalarni tanlang:",
            reply_markup=_mk_ts_kb(_us[user_id], cnt)
        )
        return

    if call.data.startswith("ts_start:"):
        topic_code = call.data.split(":")[1]
        # Test sonini tekshirish
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=%s", (topic_code,))
        cnt = cur2.fetchone()[0]; cur2.close(); conn2.close()
        if cnt == 0:
            await call.message.answer("❌ Bu mavzu uchun test yo'q!")
            return
        # Sozlamalar ekrani
        from storage import user_state as _us
        if not isinstance(_us.get(user_id), dict): _us[user_id] = {}
        _us[user_id]["ts_topic"] = topic_code
        from storage import user_state as _us
        if not isinstance(_us.get(user_id), dict): _us[user_id] = {}
        _us[user_id].update({"ts_topic": topic_code, "ts_count": 20,
                              "ts_diff": "all", "ts_timed": True, "ts_write": False,
                              "_ts_cnt_total": cnt})
        await call.message.answer(
            f"🧪 Test: {topic_code}\n📊 Jami: {cnt} ta savol\n\nSozlamalarni tanlang:",
            reply_markup=_mk_ts_kb(_us[user_id], cnt)
        )
        return

    if (call.data.startswith("ts_cnt_") or call.data.startswith("ts_dif_")
            or call.data.startswith("ts_wr_") or call.data.startswith("ts_time_")):
        from storage import user_state as _us
        if not isinstance(_us.get(user_id), dict): _us[user_id] = {}
        st2 = _us[user_id]
        if call.data.startswith("ts_cnt_"):   st2["ts_count"] = int(call.data.split("_")[-1])
        elif call.data.startswith("ts_dif_"): st2["ts_diff"]  = call.data.replace("ts_dif_","")
        elif call.data == "ts_wr_1":          st2["ts_write"] = True
        elif call.data == "ts_wr_0":          st2["ts_write"] = False
        elif call.data == "ts_wr_mix":        st2["ts_write"] = "mix"
        elif call.data == "ts_time_1":        st2["ts_timed"] = True
        elif call.data == "ts_time_0":        st2["ts_timed"] = False
        elif call.data == "ts_time_mix":      st2["ts_timed"] = "mix"
        elif call.data == "ts_img_1":         st2["ts_img"]   = True
        elif call.data == "ts_img_0":         st2["ts_img"]   = False
        elif call.data == "ts_img_mix":       st2["ts_img"]   = "mix"
        await call.answer("✅")
        # Klaviaturani ✅ bilan yangilaymiz
        cnt_total = st2.get("_ts_cnt_total", 999)
        try:
            await call.message.edit_reply_markup(reply_markup=_mk_ts_kb(st2, cnt_total))
        except Exception: pass
        return

    if call.data.startswith("book_make:"):
        book_id3 = int(call.data.split(":")[1])
        await call.answer()
        status3 = await call.message.answer("⏳ Word fayllar tayyorlanmoqda...")
        async def do_make():
            try:
                from hujjat_generator import create_book_archive
                zip_buf, info = create_book_archive(book_id3, pages_per_chunk=15)
                if not zip_buf:
                    await status3.edit_text("❌ " + info); return
                from aiogram.types import BufferedInputFile
                await call.message.answer_document(
                    BufferedInputFile(zip_buf.read(), f"kitob_{book_id3}.zip"),
                    caption=info
                )
                await status3.delete()
            except Exception as e:
                await status3.edit_text(f"❌ Xato: {e}")
        asyncio.create_task(do_make())
        return

    if call.data == "book_full_pkg":
        await call.answer()
        admin_state[user_id] = "full_pkg"
        await call.message.answer(
            "📦 To'liq paket\n\nSinf va fanni yozing:\n<code>1 | Ingliz tili</code>",
            parse_mode="HTML"
        )
        return

    if call.data.startswith("train_book:"):
        parts2 = call.data.split(":")
        book_id2 = int(parts2[1])
        fan2  = parts2[2] if len(parts2)>2 else ""
        sinf2 = parts2[3] if len(parts2)>3 else ""
        await call.answer()
        status2 = await call.message.answer(
            f"🎓 O'qitish boshlanmoqda...\n"
            f"📖 Kitob #{book_id2} | {fan2} | {sinf2}-sinf\n\n"
            f"⏳ Bu bir necha daqiqa davom etishi mumkin..."
        )
        async def do_train():
            try:
                from pedagog_trainer import train_from_book
                async def prog(msg):
                    try: await status2.edit_text(msg)
                    except: pass
                result = await train_from_book(book_id2, fan2, sinf2, prog)
                await call.message.answer(
                    f"✅ O'qitish yakunlandi!\n"
                    f"🧠 {result['facts']} ta bilim saqlandio'n"
                    f"🧪 {result['tests']} ta test yaratildi\n"
                    f"Endi Gemini/GPT siz ham javob bera olaman!"
                )
            except Exception as e:
                await call.message.answer(f"❌ Xato: {e}")
        asyncio.create_task(do_train())
        return

    if call.data.startswith("report_test:"):
        cur_idx = int(call.data.split(":")[1])
        await call.answer()
        # Timer ni pauza qilamiz
        from storage import test_sessions as _ts2
        s2 = _ts2.get(user_id,{})
        if s2.get("timer_task"):
            try: s2["timer_task"].cancel()
            except: pass
            s2["timer_task"] = None
        user_state[user_id] = f"report_comment:{cur_idx}"
        await call.message.answer(
            "✏️ Xato haqida yozing:\n\n"
            "• Javob noto'g'ri\n"
            "• Savol tushunarsiz\n"
            "• Rasm mos emas\n\n"
            "Yozib yuboring → test davom etadi"
        )
        return

    if call.data.startswith("admin_fix_test:"):
        # Admin tuzatish paneli
        tid = int(call.data.split(":")[1])
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""
            SELECT g.id, g.topic_code, g.question, g.option_a, g.option_b, g.option_c, g.option_d,
                   g.correct_answer, g.explanation, g.image_url, g.question_type,
                   c.comment
            FROM generated_tests g
            LEFT JOIN test_corrections c ON c.test_id=g.id
            WHERE g.id=%s LIMIT 1
        """, (tid,))
        row2 = cur2.fetchone(); cur2.close(); conn2.close()
        if not row2:
            await call.message.answer("❌ Test topilmadi"); return
        text2 = (
            f"✏️ Test #{tid} tuzatish\n\n"
            f"📝 Savol:\n{row2[2]}\n\n"
            f"A) {row2[3]}\nB) {row2[4]}\nC) {row2[5]}\nD) {row2[6]}\n\n"
            f"✅ To'g'ri: {row2[7]}\n"
            f"💡 Izoh: {row2[8] or '-'}\n"
            f"🖼 Rasm: {row2[9] or '-'}\n"
            f"🔑 Tur: {row2[10]}\n\n"
            f"👤 Izoh: {row2[11] or '-'}"
        )
        await call.message.answer(
            text2,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Savolni o'zgartir", callback_data=f"edit_q:{tid}"),
                 InlineKeyboardButton(text="✅ To'g'rini o'zgartir", callback_data=f"edit_ans:{tid}")],
                [InlineKeyboardButton(text="💡 Izohni o'zgartir", callback_data=f"edit_expl:{tid}"),
                 InlineKeyboardButton(text="🖼 Rasmni o'zgartir", callback_data=f"edit_img:{tid}")],
                [InlineKeyboardButton(text="🗑 O'chir", callback_data=f"del_test:{tid}"),
                 InlineKeyboardButton(text="✅ OK (saqla)", callback_data=f"fix_ok:{tid}")],
            ])
        )
        return

    if call.data.startswith("edit_q:"):
        tid=int(call.data.split(":")[1])
        await call.answer()
        admin_state[user_id]=f"edit_test_field:{tid}:question"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT question FROM generated_tests WHERE id=%s",(tid,))
        row2=cur2.fetchone();cur2.close();conn2.close()
        await call.message.answer(f"✏️ Yangi savolni yozing:\n\nHozirgi:\n{row2[0] if row2 else ''}")
        return

    if call.data.startswith("edit_ans:"):
        tid=int(call.data.split(":")[1])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT option_a,option_b,option_c,option_d,correct_answer FROM generated_tests WHERE id=%s",(tid,))
        row2=cur2.fetchone();cur2.close();conn2.close()
        if row2:
            await call.message.answer(
                f"✅ To'g'ri javobni tanlang:\n\nA) {row2[0]}\nB) {row2[1]}\nC) {row2[2]}\nD) {row2[3]}\n\nHozir: {row2[4]}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"A) {row2[0][:30]}",callback_data=f"set_ans:{tid}:A")],
                    [InlineKeyboardButton(text=f"B) {row2[1][:30]}",callback_data=f"set_ans:{tid}:B")],
                    [InlineKeyboardButton(text=f"C) {row2[2][:30]}",callback_data=f"set_ans:{tid}:C")],
                    [InlineKeyboardButton(text=f"D) {row2[3][:30]}",callback_data=f"set_ans:{tid}:D")],
                ])
            )
        return

    if call.data.startswith("set_ans:"):
        parts2=call.data.split(":");tid=int(parts2[1]);ans=parts2[2]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE generated_tests SET correct_answer=%s WHERE id=%s",(ans,tid))
        conn2.commit();cur2.close();conn2.close()
        await call.answer(f"✅ To'g'ri javob {ans} ga o'zgartirildi",show_alert=True)
        return

    if call.data.startswith("edit_expl:"):
        tid=int(call.data.split(":")[1])
        await call.answer()
        admin_state[user_id]=f"edit_test_field:{tid}:explanation"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT explanation FROM generated_tests WHERE id=%s",(tid,))
        row2=cur2.fetchone();cur2.close();conn2.close()
        await call.message.answer(f"💡 Yangi izohni yozing:\n\nHozirgi:\n{row2[0] if row2 else '-'}")
        return

    if call.data.startswith("edit_img:"):
        tid=int(call.data.split(":")[1])
        await call.answer()
        admin_state[user_id]=f"edit_test_field:{tid}:image_url"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT image_url FROM generated_tests WHERE id=%s",(tid,))
        row2=cur2.fetchone();cur2.close();conn2.close()
        await call.message.answer(f"🖼 Yangi rasm kodini yozing:\n\nHozirgi: {row2[0] if row2 else '-'}\n\nMasalan: 3-02-1-001-1")
        return

    if call.data.startswith("fix_ok:"):
        tid = int(call.data.split(":")[1])
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("UPDATE test_corrections SET status='resolved' WHERE test_id=%s", (tid,))
        conn2.commit(); cur2.close(); conn2.close()
        await call.answer("✅ Belgilandi")
        await call.message.edit_reply_markup(reply_markup=None)
        return

    if call.data.startswith("del_test:"):
        if user_id not in ADMINS: return
        tid = int(call.data.split(":")[1])
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("DELETE FROM generated_tests WHERE id=%s", (tid,))
        cur2.execute("UPDATE test_corrections SET status='deleted' WHERE test_id=%s", (tid,))
        conn2.commit(); cur2.close(); conn2.close()
        await call.answer("🗑 O'chirildi", show_alert=True)
        await call.message.edit_text("🗑 Test o'chirildi")
        return

    if call.data == "ts_go":
        from storage import user_state as _us
        st2 = _us.get(user_id) if isinstance(_us.get(user_id), dict) else {}
        tc   = st2.get("ts_topic","")
        topic_codes = st2.get("ts_topic_codes", [tc] if tc else [])
        cnt2 = st2.get("ts_count", 20)
        diff = st2.get("ts_diff", "all")
        write= st2.get("ts_write", False)
        if not topic_codes:
            await call.answer("❌ Mavzu tanlanmagan — qayta tanlang", show_alert=True)
            return
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        diff_f = "" if diff=="all" else f"AND difficulty='{diff}'"
        # write: False=faqat test, True=faqat yozma, "mix"=aralash
        if write == "mix": type_f = ""
        elif write == True: type_f = "AND question_type = 'write_answer'"
        else: type_f = "AND question_type != 'write_answer'"
        img    = st2.get("ts_img", "mix")
        img_f  = "" if img=="mix" else ("AND image_url IS NOT NULL AND image_url != ''" if img==True else "AND (image_url IS NULL OR image_url = '')")
        cur2.execute(f"""
            SELECT question,option_a,option_b,option_c,option_d,
                   correct_answer,explanation,question_type,is_latex,
                   image_url,audio_text,language,time_limit
            FROM generated_tests WHERE topic_code=ANY(%s) {diff_f} {type_f} {img_f}
            ORDER BY RANDOM() LIMIT %s
        """, (topic_codes, cnt2))
        tests = cur2.fetchall(); cur2.close(); conn2.close()
        if not tests:
            await call.answer("❌ Bu filtr bo'yicha test topilmadi!", show_alert=True)
            return
        await call.answer()
        from test_engine import start_test
        timed_ = st2.get("ts_timed", True)
        await start_test(user_id, tests, call.message, timed=timed_)
        from storage import test_sessions as _ts
        if user_id in _ts:
            _ts[user_id]["topic_code"] = tc
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
            conn_t = _get_db_conn()
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
            conn_g = _get_db_conn()
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
                    conn_s = _get_db_conn()
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
            conn_d = _get_db_conn()
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
            conn_v = _get_db_conn()
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

    if call.data.startswith("gen_") or call.data.startswith("gg_cnt_") or call.data.startswith("gg_tp_") or call.data in ("gen_go", "gen_template"):
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
        conn2 = _get_db_conn()
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
        conn2 = _get_db_conn()
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
            conn2 = _get_db_conn()
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
        conn = _get_db_conn()
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
        await call.answer("✅ To'xtatildi")
        try: await call.message.delete()
        except: pass
        await stop_test(call.from_user.id, call.message)
        return

    if call.data == "test_stop_no":
        await call.answer("▶️ Davom etilmoqda!")
        try: await call.message.delete()
        except: pass
        return


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
    # Haftalik hisobot — har dushanba
    async def weekly_report_task():
        while True:
            import asyncio
            from datetime import datetime
            now = datetime.now()
            # Har dushanba 08:00 da
            if now.weekday() == 0 and now.hour == 8 and now.minute == 0:
                try:
                    from features import get_weekly_report
                    conn_ = _get_db_conn(); cur_ = conn_.cursor()
                    # Barcha ota-onalarga hisobot
                    cur_.execute("""SELECT p.parent_id, p.child_id, u.full_name,
                        a.togarak_id, t.nomi FROM parent_child p
                        JOIN users u ON u.user_id=p.child_id
                        JOIN togarak_azolar a ON a.user_id=p.child_id AND a.aktiv=TRUE
                        JOIN togaraklar t ON t.id=a.togarak_id AND t.aktiv=TRUE""")
                    rows_ = cur_.fetchall(); cur_.close(); conn_.close()
                    for r in rows_:
                        rep = get_weekly_report(r[3], r[1])
                        txt = (f"📊 Haftalik hisobot\n👤 {r[2]}\n📚 {r[4]}\n\n"
                               f"📋 Davomat: {rep['keldi']} kun keldi\n"
                               f"⭐ O'rt.baho: {rep['avg_baho']}\n"
                               f"📝 Vazifa: {rep['hw_done']} ta topshirdi")
                        try: await bot.send_message(r[0], txt)
                        except: pass
                except Exception as e:
                    print(f"weekly_report: {e}")
            await asyncio.sleep(60)
    # Extra routerlar ulash
    try:
        from router_extra import router as extra_router
        dp.include_router(extra_router)
    except Exception as e:
        print(f'router_extra: {e}')
    try:
        from handler_parent import router as parent_router
        dp.include_router(parent_router)
    except Exception as e:
        print(f'handler_parent: {e}')
    asyncio.create_task(weekly_report_task())
    try:
        from router_extra import tolov_eslatma_task
        asyncio.create_task(tolov_eslatma_task(bot))
    except: pass

    # Webhook yoki polling
    WEBHOOK_URL = os.getenv("WEBHOOK_URL","")
    if WEBHOOK_URL:
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        from aiohttp import web as _web2
        WEBHOOK_PATH = f"/webhook/{bot.token}"
        await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
        print(f"✅ Webhook: {WEBHOOK_URL}{WEBHOOK_PATH}")
        app2 = _web2.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app2, path=WEBHOOK_PATH)
        setup_application(app2, dp, bot=bot)
        runner2 = _web2.AppRunner(app2)
        await runner2.setup()
        site2 = _web2.TCPSite(runner2, "0.0.0.0", 8080)
        await site2.start()
        await asyncio.Event().wait()
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
