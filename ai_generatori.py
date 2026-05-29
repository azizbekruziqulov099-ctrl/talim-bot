import json
from openai import AsyncOpenAI
from aiogram.filters import *
from openpyxl import load_workbook, Workbook
from loader import dp, bot
import os
from aiogram import F
from aiogram.types import (
    Message,
    FSInputFile
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
    select_subject = State()
    wait_file = State()


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

    await message.answer(
        "Sinfni tanlang\nMasalan: 1-sinf"
    )

async def generate_topic_tree(
        grade: int,
        subject: str,
        quarter: int,
        topic: str
):
    prompt = f"""
Siz O‘zbekiston umumiy o‘rta ta'lim DTS eksperti, metodist va fan mutaxassisisiz.

KIRISH MA'LUMOTLARI

Sinf: {grade}
Fan: {subject}
Chorak: {quarter}
Mavzu: {topic}

VAZIFA

Berilgan mavzu uchun:

1. Mantiqan to‘g‘ri Bob yarating.
2. Mantiqan to‘g‘ri Bo‘lim yarating.
3. Mavzuni saqlang.
4. Mavzuning mazmunini ochib beruvchi 4 ta kichik mavzu yarating.

TALABLAR

- Sinf darajasi hisobga olinsin.
- Fan terminologiyasi saqlansin.
- Bob juda qisqa bo‘lmasin.
- Bo‘lim juda qisqa bo‘lmasin.
- Kichik mavzular 1-2 so‘zdan iborat bo‘lmasin.
- Kichik mavzular to‘liq mazmunli bo‘lsin.
- Kichik mavzular o‘quv dasturiga mos bo‘lsin.
- Kichik mavzular takrorlanmasin.
- Javob faqat o‘zbek tilida bo‘lsin.
- Hech qanday izoh yozmang.

JSON format:

{{
    "bob": "",
    "bolim": "",
    "mavzu": "{topic}",
    "kichik_mavzular": [
        "",
        "",
        "",
        ""
    ]
}}

Faqat JSON qaytaring.
"""

    response = await client.chat.completions.create(
        model="gpt-5.5",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "Siz DTS va o‘quv dasturlari bo‘yicha ekspert metodistsiz."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    result = response.choices[0].message.content.strip()

    try:
        return json.loads(result)

    except Exception:
        return {
            "bob": "",
            "bolim": "",
            "mavzu": topic,
            "kichik_mavzular": []
        }
    
def read_topics(file_path):
    wb = load_workbook(file_path)
    ws = wb.active

    topics = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        quarter = row[0]
        topic = row[1]

        if not topic:
            continue

        topics.append({
            "quarter": quarter,
            "topic": str(topic).strip()
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

    for item in topics:

        result = await generate_topic_tree(
            grade=grade,
            subject=subject,
            quarter=item["quarter"],
            topic=item["topic"]
        )

        for km in result["kichik_mavzular"]:

            result_rows.append([
                grade,
                subject,
                item["quarter"],
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
    grade = int(message.text.split("-")[0])

    await state.update_data(
        grade=grade
    )

    await state.set_state(
        AIGeneratorState.select_subject
    )

    await message.answer(
        "Fan nomini yuboring"
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




