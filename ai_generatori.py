import json
from openai import AsyncOpenAI
from aiogram.types import ReplyKeyboardRemove
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

    keyboard.append([
        KeyboardButton(text="🔍 Qidirish"),
        KeyboardButton(text="➕ Yangi sinf")
    ])

    row = []

    for i, grade in enumerate(grades, start=1):
        row.append(
            KeyboardButton(text=grade[0])
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)


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

async def generate_bobs(
        grade,
        subject,
        topics
):
    topics_text = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    prompt = f"""
Siz O‘zbekiston Respublikasi DTS, o‘quv dasturlari, metodika va darsliklar bo‘yicha eng tajribali ekspertlar guruhisiz.

SINF: {grade}

FAN: {subject}

MAVZULAR:

{topics_text}

VAZIFA

Barcha mavzularni birgalikda tahlil qiling.

Avval mavzulardagi asosiy tushunchalarni aniqlang.

Keyin mazmun jihatidan o‘xshash mavzularni guruhlang.

Keyin ushbu guruhlar asosida Boblar yarating.

ENG MUHIM QOIDALAR

- Bob mavzu emas.
- Bob fan tarkibidagi yirik mazmuniy birlik.
- Bob bir nechta bo‘lim va ko‘plab mavzularni o‘z ichiga olishi kerak.
- Bir xil mazmundagi mavzular bir Bobga joylashtirilishi kerak.
- Bir-biriga yaqin mavzular turli Boblarga ajratilmasin.
- Boblar DTS va o‘quv dasturi uslubida yozilsin.
- Boblar soni kamida 3 ta va ko‘pi bilan 6 ta bo‘lsin.
- Zarurat bo‘lmasa yangi Bob yaratmang.

TAQIQLANADI

Quyidagilar Bob bo‘la olmaydi:

- Fan nomi
- Mavzu nomi
- Nazorat ishi
- Sinov ishi
- Takrorlash
- Mustahkamlash
- Diagnostika
- Loyiha faoliyati
- Tahlil va tuzatish ishlari
- Yakuniy baholash

YOMON MISOLLAR

Kasrlar
Radius
Aylana
Fe'l
Ot
Sifat
Elektr toki
O'simlik

Bular juda tor tushunchalar yoki mavzulardir.

YAXSHI MISOLLAR

Sonlar va amallar

Geometrik tushunchalar

So‘z turkumlari

Elektr hodisalari

Tirik organizmlar

Tabiat va atrof-muhit

Bular ko‘plab mavzularni birlashtira oladigan yirik mazmuniy birliklardir.

NATIJA

Faqat JSON qaytaring.

[
    "Bob nomi",
    "Bob nomi",
    "Bob nomi"
]
"""

    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "Siz DTS va metodika bo‘yicha ekspert mutaxassissiz."
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

async def generate_bolims(
        grade,
        subject,
        bobs,
        topics
):
    bobs_text = "\n".join(
        [f"- {bob}" for bob in bobs]
    )

    topics_text = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    prompt = f"""
Siz DTS, o‘quv dasturlari va metodika bo‘yicha ekspert mutaxassissiz.

SINF: {grade}

FAN: {subject}

BOBLAR:

{bobs_text}

MAVZULAR:

{topics_text}

VAZIFA

Berilgan Boblar asosida Bo‘limlar yarating.

Bo‘limlar Bob tarkibidagi mazmuniy qismlar bo‘lsin.

ENG MUHIM QOIDALAR

- Bo‘lim mavzu emas.
- Bo‘lim Bobdan kichik, mavzudan katta bo‘lsin.
- Bir xil mazmundagi mavzular bitta Bo‘limga tushsin.
- Bo‘lim nomi mavzu nomidan olinmasin.
- Fan nomidan olinmasin.
- Bo‘limlar DTS uslubida yozilsin.
- Bo‘limlar soni 15 tadan 20 tagacha bo‘lsin.
- Har bir Bo‘lim albatta mavjud Boblardan biriga tegishli bo‘lsin.

TAQIQLANADI

Quyidagilar Bo‘lim bo‘la olmaydi:

- Nazorat ishi
- Sinov ishi
- Takrorlash
- Mustahkamlash
- Diagnostika
- Loyiha faoliyati
- Tahlil va tuzatish ishlari
- Yakuniy baholash

FAQAT JSON QAYTARING

[
    {{
        "bob": "",
        "bolim": ""
    }}
]
"""
    
    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "Siz DTS va metodika bo‘yicha ekspert mutaxassissiz."
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

async def generate_mapping(
        grade,
        subject,
        bobs,
        bolims,
        topics
):
    bobs_text = "\n".join(
        [f"- {bob}" for bob in bobs]
    )

    bolims_text = "\n".join(
        [
            f"- {x['bob']} -> {x['bolim']}"
            for x in bolims
        ]
    )

    topics_text = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    prompt = f"""
Siz DTS va metodika bo‘yicha ekspert mutaxassissiz.

SINF: {grade}

FAN: {subject}

BOBLAR:

{bobs_text}

BO‘LIMLAR:

{bolims_text}

MAVZULAR:

{topics_text}

VAZIFA

Har bir mavzuni eng mos Bob va Bo‘limga joylashtiring.

QOIDALAR

- Mavzu faqat bitta Bobga tegishli bo‘lsin.
- Mavzu faqat bitta Bo‘limga tegishli bo‘lsin.
- Yangi Bob yaratmang.
- Yangi Bo‘lim yaratmang.
- Faqat berilgan Bob va Bo‘limlardan foydalaning.
- Mantiqiy yaqinlikni saqlang.

FAQAT JSON QAYTARING

[
    {{
        "bob": "",
        "bolim": "",
        "mavzu": ""
    }}
]
"""

    response = await client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {
                "role": "system",
                "content": "Siz DTS eksperti va metodistsiz."
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

async def generate_small_topics_batch(
        grade,
        subject,
        topics
):
    topics_text = "\n".join(
        [f"- {topic}" for topic in topics]
    )

    prompt = f"""
Siz DTS va metodika bo‘yicha ekspert mutaxassissiz.

SINF: {grade}

FAN: {subject}

MAVZULAR:

{topics_text}

VAZIFA

Har bir mavzu uchun 4 tadan 8 tagacha
kichik mavzu yarating.

QOIDALAR

- Kichik mavzular mazmunli bo‘lsin.
- DTSga mos bo‘lsin.
- Takrorlanmasin.
- Bilim, ko‘nikma va amaliy faoliyatni qamrab olsin.
- Faqat mavzu ichidagi so‘zlarni takrorlamasin.

FAQAT JSON QAYTARING

[
    {{
        "mavzu": "",
        "kichik_mavzular": [
            "",
            ""
        ]
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
    await message.answer(
        "⏳ Fayl tahlil qilinmoqda..."
    )

    await message.answer(
        "📚 Boblar yaratilmoqda..."
    )

    file = await bot.get_file(
        message.document.file_id
    )

    os.makedirs(
        "temp",
        exist_ok=True
    )

    input_file = (
        f"temp/{message.document.file_name}"
    )

    await bot.download_file(
        file.file_path,
        destination=input_file
    )

    topics_data = read_topics(
        input_file
    )

    data = await state.get_data()

    grade = data["grade"]
    subject = data["subject"]

    topic_names = [
        x["topic"]
        for x in topics_data
    ]

    bobs = await generate_bobs(
        grade,
        subject,
        topic_names
    )

    if not bobs:
        await message.answer(
            "❌ Boblar yaratilmadi"
        )
        return

    await message.answer(
        "📖 Bo'limlar yaratilmoqda..."
    )

    bolims = await generate_bolims(
        grade,
        subject,
        bobs,
        topic_names
    )

    if not bolims:
        await message.answer(
            "❌ Bo'limlar yaratilmadi"
        )
        return    

    await message.answer(
        "🗂 Mavzular joylashtirilmoqda..."
    )

    mapping = await generate_mapping(
        grade,
        subject,
        bobs,
        bolims,
        topic_names
    )

    if not mapping:
        await message.answer(
            "❌ Mavzular joylashtirilmadi"
        )
        return

    result_rows = []

    mapped_topics = list(
        {
            x["mavzu"]
            for x in mapping
        }
    )

    topic_quarters = {
        x["topic"]: x["quarter"]
        for x in topics_data
    }

    await message.answer(
        "📝 Kichik mavzular yaratilmoqda..."
    )

    small_topics_data = await generate_small_topics_batch(
        grade,
        subject,
        mapped_topics
    )

    if not small_topics_data:
        await message.answer(
            "❌ Kichik mavzular yaratilmadi"
        )
        return

    small_topics_map = {
        x["mavzu"]: x["kichik_mavzular"]
        for x in small_topics_data
    }

    for item in mapping:

        for km in small_topics_map.get(
            item["mavzu"],
            []
        ):

            topic_data = next(
                (
                    x for x in topics_data
                    if x["topic"] == item["mavzu"]
                ),
                {}
            )

            quarter = topic_quarters.get(
                item["mavzu"],
                ""
            )

            result_rows.append([
                grade,
                subject,
                quarter,
                item["bob"],
                item["bolim"],
                item["mavzu"],
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
        caption=(
            f"✅ Tayyor\n\n"
            f"📚 Boblar: {len(bobs)}\n"
            f"📖 Bo'limlar: {len(bolims)}\n"
            f"🗂 Mavzular: {len(mapping)}"
        )
    )
    try:
        os.remove(input_file)
    except:
        pass

    try:
        os.remove(output_file)
    except:
        pass
    await state.clear()

    await message.answer(
        "🤖 AI Generator yakunlandi"
    )

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

    keyboard.append([
        KeyboardButton(text="🔍 Qidirish"),
        KeyboardButton(text="➕ Yangi fan")
    ])

    row = []

    for subject in subjects:
        row.append(
            KeyboardButton(text=subject[0])
        )

        if len(row) == 2:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)
    
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
        "📄 Excel fayl yuboring",
        reply_markup=ReplyKeyboardRemove()
    )
