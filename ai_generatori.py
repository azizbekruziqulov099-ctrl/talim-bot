import json
from openai import AsyncOpenAI
from aiogram.filters import *
from openpyxl import load_workbook, Workbook
from loader import dp, bot
import os
import psycopg2
from aiogram import F
from aiogram.types import (
    Message,
    FSInputFile,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from aiogram.fsm.state import (
    State,
    StatesGroup
)

from aiogram.fsm.context import (
    FSMContext
)
class AIGeneratorState(StatesGroup):
    select_grade = State()
    search_grade = State()
    add_grade = State()

    select_subject = State()
    search_subject = State()
    add_subject = State()

    wait_file = State()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)

@dp.message(F.text == "🤖 AI Generator")
async def ai_generator_menu(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AIGeneratorState.select_grade
    )

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM ai_grades
        ORDER BY id
    """)

    grades = cur.fetchall()

    conn.close()

    keyboard = []

    for grade in grades:
        keyboard.append([
            KeyboardButton(text=grade[0])
        ])

    keyboard.append([
        KeyboardButton(text="🔍 Qidirish")
    ])

    keyboard.append([
        KeyboardButton(text="➕ Yangi sinf")
    ])

    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer(
        "📚 Sinfni tanlang yoki yarating",
        reply_markup=kb
    )

@dp.message(
    AIGeneratorState.select_grade,
    F.text == "🔍 Qidirish"
)
async def search_grade_start(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AIGeneratorState.search_grade
    )

    await message.answer(
        "🔍 Sinf nomini kiriting"
    )

@dp.message(
    AIGeneratorState.search_grade
)
async def search_grade(
    message: Message,
    state: FSMContext
):
    text = message.text.strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM ai_grades
        WHERE LOWER(name) LIKE LOWER(%s)
        ORDER BY name
        LIMIT 20
    """, (f"%{text}%",))

    rows = cur.fetchall()

    conn.close()

    if not rows:
        await message.answer(
            "❌ Hech narsa topilmadi"
        )
        return

    keyboard = []

    for row in rows:
        keyboard.append([
            KeyboardButton(text=row[0])
        ])

    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await state.set_state(
        AIGeneratorState.select_grade
    )

    await message.answer(
        "Topilgan sinflar:",
        reply_markup=kb
    )

@dp.message(
    AIGeneratorState.select_grade,
    F.text == "➕ Yangi sinf"
)
async def add_grade_start(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AIGeneratorState.add_grade
    )

    await message.answer(
        "Yangi sinf nomini yuboring"
    )

@dp.message(
    AIGeneratorState.add_grade
)
async def add_grade_save(
    message: Message,
    state: FSMContext
):
    grade_name = message.text.strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO ai_grades(name)
            VALUES(%s)
        """, (grade_name,))

        conn.commit()

        await message.answer(
            f"✅ {grade_name} qo'shildi"
        )

    except:
        await message.answer(
            "❌ Bu sinf allaqachon mavjud"
        )

    finally:
        conn.close()

    await state.set_state(
        AIGeneratorState.select_grade
    )

async def generate_topic_tree_batch(
        grade,
        subject,
        quarter,
        topics
):
    topics_text = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    prompt = f"""
Siz DTS va o‘quv dasturi bo‘yicha ekspert mutaxassissiz.

Sinf: {grade}
Fan: {subject}
Davr: {quarter}

Quyidagi mavzular:

{topics_text}

QOIDALAR

- Nazorat ishi, sinov ishi, takrorlash, mustahkamlash, loyiha, diagnostika va tahlil mavzularini e'tiborga olmang.
- Bir xil mazmundagi mavzular uchun aynan bir xil bob ishlating.
- Bir xil mazmundagi mavzular uchun aynan bir xil bo‘lim ishlating.
- Har bir mavzu uchun yangi bob yaratmang.
- Har bir mavzu uchun yangi bo‘lim yaratmang.
- Boblar soni imkon qadar 3 tadan 6 tagacha bo‘lsin.
- Bo‘limlar soni imkon qadar 15 tadan 20 tagacha bo‘lsin.
- Bob nomlarida chorak, semestr yoki raqamlar bo‘lmasin.
- Bo‘lim nomlarida chorak, semestr yoki raqamlar bo‘lmasin.
- Kichik mavzular 3 tadan 8 tagacha bo‘lsin.
- Kichik mavzular mazmunli bo‘lsin.
- Kichik mavzular 20 ta so‘zdan oshmasin.

Faqat JSON massiv qaytaring.

[
    {{
        "bob": "",
        "bolim": "",
        "mavzu": "",
        "kichik_mavzular": []
    }}
]
"""

    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "Siz DTS metodistisiz."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    try:
        return json.loads(
            response.choices[0].message.content
        )
    except:
        return []

def read_topics(file_path):
    wb = load_workbook(file_path)
    ws = wb.active

    ignore_words = [
        "nazorat",
        "sinov",
        "takrorlash",
        "mustahkamlash",
        "loyiha",
        "diagnostika",
        "tahlil",
        "yakuniy baholash"
    ]

    topics = []

    for row in ws.iter_rows(min_row=2, values_only=True):

        quarter = row[0]

        if not row[1]:
            continue

        topic = str(row[1]).strip()

        lower_topic = topic.lower()

        if any(
            word in lower_topic
            for word in ignore_words
        ):
            continue

        topics.append({
            "quarter": quarter,
            "topic": topic
        })

    return topics

def create_result_excel(rows, output_file):
    wb = Workbook()
    ws = wb.active

    ws.append([
        "Sinf",
        "Fan",
        "Chorak",
        "Bob",
        "Bo'lim",
        "Mavzu",
        "Kichik mavzu"
    ])

    for row in rows:
        ws.append(row)

    wb.save(output_file)

@dp.message(
    AIGeneratorState.wait_file,
    F.document
)
async def ai_generator_file(
        message: Message,
        state: FSMContext
):
    await message.answer("⏳ Fayl tahlil qilinmoqda...")

    file = await bot.get_file(
        message.document.file_id
    )

    os.makedirs(
        "temp",
        exist_ok=True
    )

    input_file = f"temp/{message.document.file_name}"

    await bot.download_file(
        file.file_path,
        destination=input_file
    )

    topics = read_topics(input_file)

    data = await state.get_data()

    grade = data["grade"]
    subject = data["subject"]

    result_rows = []

    CHUNK_SIZE = 40

    for i in range(0, len(topics), CHUNK_SIZE):

        chunk = topics[i:i + CHUNK_SIZE]

        quarter = chunk[0]["quarter"]

        topic_names = [
            x["topic"]
            for x in chunk
        ]

        results = await generate_topic_tree_batch(
            grade,
            subject,
            quarter,
            topic_names
        )

        for result in results:

            for km in result["kichik_mavzular"]:

                result_rows.append([
                    grade,
                    subject,
                    quarter,
                    result["bob"],
                    result["bolim"],
                    result["mavzu"],
                    km
                ])

    output_file = (
        f"temp/{grade}_{subject}_AI.xlsx"
    )

    create_result_excel(
        result_rows,
        output_file
    )

    await message.answer_document(
        FSInputFile(output_file),
        caption="✅ Tayyor"
    )

    await state.clear()

@dp.message(AIGeneratorState.select_grade)
async def select_grade(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        grade=message.text
    )

    await state.set_state(
        AIGeneratorState.select_subject
    )

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM ai_subjects
        ORDER BY name
    """)

    subjects = cur.fetchall()

    conn.close()

    keyboard = []

    for subject in subjects:
        keyboard.append([
            KeyboardButton(text=subject[0])
        ])

    keyboard.append([
        KeyboardButton(text="🔍 Qidirish")
    ])

    keyboard.append([
        KeyboardButton(text="➕ Yangi fan")
    ])

    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await message.answer(
        "📖 Fanni tanlang yoki yarating",
        reply_markup=kb
    )

@dp.message(
    AIGeneratorState.select_subject,
    F.text == "🔍 Qidirish"
)
async def search_subject_start(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AIGeneratorState.search_subject
    )

    await message.answer(
        "🔍 Fan nomini kiriting"
    )

@dp.message(
    AIGeneratorState.search_subject
)
async def search_subject(
    message: Message,
    state: FSMContext
):
    text = message.text.strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM ai_subjects
        WHERE LOWER(name) LIKE LOWER(%s)
        ORDER BY name
        LIMIT 20
    """, (f"%{text}%",))

    rows = cur.fetchall()

    conn.close()

    if not rows:
        await message.answer(
            "❌ Fan topilmadi"
        )
        return

    keyboard = []

    for row in rows:
        keyboard.append([
            KeyboardButton(text=row[0])
        ])

    kb = ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

    await state.set_state(
        AIGeneratorState.select_subject
    )

    await message.answer(
        "📖 Topilgan fanlar",
        reply_markup=kb
    )

@dp.message(
    AIGeneratorState.select_subject,
    F.text == "➕ Yangi fan"
)
async def add_subject_start(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        AIGeneratorState.add_subject
    )

    await message.answer(
        "Yangi fan nomini yuboring"
    )

@dp.message(
    AIGeneratorState.add_subject
)
async def add_subject_save(
    message: Message,
    state: FSMContext
):
    subject_name = message.text.strip()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO ai_subjects(name)
            VALUES(%s)
        """, (subject_name,))

        conn.commit()

        await message.answer(
            f"✅ {subject_name} qo'shildi"
        )

    except:
        await message.answer(
            "❌ Bu fan allaqachon mavjud"
        )

    finally:
        conn.close()

    await state.set_state(
        AIGeneratorState.select_subject
    )

@dp.message(AIGeneratorState.select_subject)
async def select_subject(
    message: Message,
    state: FSMContext
):
    await state.update_data(
        subject=message.text
    )

    await state.set_state(
        AIGeneratorState.wait_file
    )

    await message.answer(
        "📄 Excel fayl yuboring"
    )




