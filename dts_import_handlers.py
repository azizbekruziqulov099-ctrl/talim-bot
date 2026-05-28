from aiogram.types import Message
from difflib import SequenceMatcher
from openpyxl import load_workbook
from openpyxl import Workbook
from Talim import dp
import psycopg2
import os
import re
from aiogram import F
from aiogram.fsm.context import (
    FSMContext
)
from difflib import SequenceMatcher
from Talim import bot
from aiogram.types import FSInputFile
from aiogram.types import (

    Message,
    CallbackQuery,

    InlineKeyboardMarkup,
    InlineKeyboardButton

)
from aiogram.fsm.state import (
    State,
    StatesGroup
)
class DTSImportState(

    StatesGroup

):

    waiting_excel = State()

DATABASE_URL = os.getenv("DATABASE_URL")

dts_import_cache = {}

def normalize_text(text):

    if text is None:
        return ""

    text = str(text)

    text = text.lower()

    text = text.replace("ʻ", "'")
    text = text.replace("`", "'")
    text = text.replace("ʼ", "'")

    text = text.replace("–", "-")
    text = text.replace("—", "-")

    text = text.replace("_", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()

def get_subject_code(
    cur,
    subject_name
):

    subject_name = normalize_text(
        subject_name
    ).upper()

    cur.execute("""
    SELECT code
    FROM subjects
    WHERE name=%s
    """, (
        subject_name,
    ))

    row = cur.fetchone()

    if row:

        return row[0]

    cur.execute("""
    SELECT MAX(
        CAST(code AS INTEGER)
    )
    FROM subjects
    """)

    last_code = cur.fetchone()[0]

    next_code = str(
        (last_code or 0) + 1
    ).zfill(2)

    cur.execute("""
    INSERT INTO subjects (
        code,
        name
    )
    VALUES (%s, %s)
    """, (
        next_code,
        subject_name
    ))

    return next_code

def get_bob_code(

    cur,
    subject_code,
    quarter,
    bob_name

):

    bob_name = normalize_text(
        bob_name
    )

    cur.execute("""
    SELECT bob_code
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_name=%s
    LIMIT 1
    """, (
        subject_code,
        quarter,
        bob_name
    ))

    row = cur.fetchone()

    if row:

        return row[0]

    cur.execute("""
    SELECT MAX(
        CAST(bob_code AS INTEGER)
    )
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    """, (
        subject_code,
        quarter
    ))

    last_code = cur.fetchone()[0]

    next_code = str(
        (last_code or 0) + 1
    ).zfill(2)

    return next_code

def get_bolim_code(

    cur,
    subject_code,
    quarter,
    bob_code,
    bolim_name

):

    bolim_name = normalize_text(
        bolim_name
    )

    cur.execute("""
    SELECT bolim_code
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_name=%s
    LIMIT 1
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_name
    ))

    row = cur.fetchone()

    if row:

        return row[0]

    cur.execute("""
    SELECT MAX(
        CAST(bolim_code AS INTEGER)
    )
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    """, (
        subject_code,
        quarter,
        bob_code
    ))

    last_code = cur.fetchone()[0]

    next_code = str(
        (last_code or 0) + 1
    ).zfill(2)

    return next_code

def get_mavzu_code(

    cur,
    subject_code,
    quarter,
    bob_code,
    bolim_code,
    mavzu_name

):

    mavzu_name = normalize_text(
        mavzu_name
    )

    cur.execute("""
    SELECT mavzu_code
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    AND mavzu_name=%s
    LIMIT 1
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_name
    ))

    row = cur.fetchone()

    if row:

        return row[0]

    cur.execute("""
    SELECT MAX(
        CAST(mavzu_code AS INTEGER)
    )
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code
    ))

    last_code = cur.fetchone()[0]

    next_code = str(
        (last_code or 0) + 1
    ).zfill(2)

    return next_code

def get_kichik_code(

    cur,
    subject_code,
    quarter,
    bob_code,
    bolim_code,
    mavzu_code,
    kichik_name

):

    kichik_name = normalize_text(
        kichik_name
    )

    cur.execute("""
    SELECT kichik_code
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    AND mavzu_code=%s
    AND kichik_name=%s
    LIMIT 1
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code,
        kichik_name
    ))

    row = cur.fetchone()

    if row:

        return row[0]

    cur.execute("""
    SELECT MAX(
        CAST(kichik_code AS INTEGER)
    )
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    AND mavzu_code=%s
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code
    ))

    last_code = cur.fetchone()[0]

    next_code = str(
        (last_code or 0) + 1
    ).zfill(3)

    return next_code

def build_topic_code(

    subject_code,
    quarter,
    bob_code,
    bolim_code,
    mavzu_code,
    kichik_code

):

    return (
        f"{subject_code}-"
        f"{quarter}-"
        f"{bob_code}-"
        f"{bolim_code}-"
        f"{mavzu_code}-"
        f"{kichik_code}"
    )

def insert_row(

    cur,
    row

):

    grade = normalize_text(
        row[0]
    )

    subject_name = normalize_text(
        row[1]
    ).upper()

    quarter = normalize_text(
        row[2]
    )

    bob_name = normalize_text(
        row[3]
    )

    bolim_name = normalize_text(
        row[4]
    )

    mavzu_name = normalize_text(
        row[5]
    )

    kichik_name = normalize_text(
        row[6]
    )

    subject_code = get_subject_code(
        cur,
        subject_name
    )

    bob_code = get_bob_code(
        cur,
        subject_code,
        quarter,
        bob_name
    )

    bolim_code = get_bolim_code(
        cur,
        subject_code,
        quarter,
        bob_code,
        bolim_name
    )

    mavzu_code = get_mavzu_code(
        cur,
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_name
    )

    kichik_code = get_kichik_code(
        cur,
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code,
        kichik_name
    )

    topic_code = build_topic_code(

        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code,
        kichik_code

    )

    cur.execute("""
    SELECT 1
    FROM dts_tree
    WHERE topic_code=%s
    LIMIT 1
    """, (
        topic_code,
    ))

    exists = cur.fetchone()

    if exists:

        return {
            "status": "exists",
            "topic_code": topic_code
        }

    cur.execute("""
    INSERT INTO dts_tree (

        topic_code,

        grade,

        subject_code,
        subject_name,

        quarter,

        bob_code,
        bob_name,

        bolim_code,
        bolim_name,

        mavzu_code,
        mavzu_name,

        kichik_code,
        kichik_name

    )
    VALUES (

        %s,

        %s,

        %s,
        %s,

        %s,

        %s,
        %s,

        %s,
        %s,

        %s,
        %s,

        %s,
        %s

    )
    """, (

        topic_code,

        grade,

        subject_code,
        subject_name,

        quarter,

        bob_code,
        bob_name,

        bolim_code,
        bolim_name,

        mavzu_code,
        mavzu_name,

        kichik_code,
        kichik_name

    ))

    return {
        "status": "inserted",
        "topic_code": topic_code
    }

def analyze_import(
    cur,
    rows
):

    error_rows = []
    duplicate_rows = []
    existing_rows = []
    valid_rows = []

    seen = set()

    for i, row in enumerate(
        rows,
        start=2
    ):

        try:

            if len(row) < 7:

                error_rows.append({

                    "row_no": i,
                    "reason": "Ustunlar soni yetarli emas"

                })

                continue

            grade = normalize_text(
                row[0]
            )

            subject_name = normalize_text(
                row[1]
            )

            if subject_name:
                subject_name = subject_name.upper()

            quarter = normalize_text(
                row[2]
            )

            bob_name = normalize_text(
                row[3]
            )

            bolim_name = normalize_text(
                row[4]
            )

            mavzu_name = normalize_text(
                row[5]
            )

            kichik_name = normalize_text(
                row[6]
            )

            if not all([

                grade,
                subject_name,
                quarter,
                bob_name,
                bolim_name,
                mavzu_name,
                kichik_name

            ]):

                error_rows.append({

                    "row_no": i,
                    "reason": "Bo‘sh ustun bor"

                })

                continue

            subject_code = get_subject_code(
                cur,
                subject_name
            )

            bob_code = get_bob_code(
                cur,
                subject_code,
                quarter,
                bob_name
            )

            bolim_code = get_bolim_code(
                cur,
                subject_code,
                quarter,
                bob_code,
                bolim_name
            )

            mavzu_code = get_mavzu_code(
                cur,
                subject_code,
                quarter,
                bob_code,
                bolim_code,
                mavzu_name
            )

            kichik_code = get_kichik_code(
                cur,
                subject_code,
                quarter,
                bob_code,
                bolim_code,
                mavzu_code,
                kichik_name
            )

            topic_code = build_topic_code(

                subject_code,
                quarter,
                bob_code,
                bolim_code,
                mavzu_code,
                kichik_code

            )

            if topic_code in seen:

                duplicate_rows.append({

                    "row_no": i,
                    "topic_code": topic_code,
                    "reason": "Excel ichida takroriy"

                })

                continue

            seen.add(topic_code)

            cur.execute(

                """
                SELECT 1
                FROM dts_tree
                WHERE topic_code=%s
                LIMIT 1
                """,

                (topic_code,)

            )

            exists = cur.fetchone()

            if exists:

                existing_rows.append({

                    "row_no": i,
                    "topic_code": topic_code,
                    "reason": "Bazada mavjud"

                })

                continue

            valid_rows.append({

                "row_no": i,
                "row": row,
                "topic_code": topic_code

            })

        except Exception as e:

            error_rows.append({

                "row_no": i,
                "reason": str(e)

            })

    return {

        "error_rows": error_rows,
        "duplicate_rows": duplicate_rows,
        "existing_rows": existing_rows,
        "valid_rows": valid_rows

    }

def confirm_import(

    cur,
    valid_rows

):

    inserted_count = 0

    inserted_rows = []
    failed_rows = []

    for item in valid_rows:

        try:

            row = item["row"]
            row_no = item.get("row_no")
            topic_code = item.get("topic_code")

            result = insert_row(
                cur,
                row
            )

            if result.get("status") == "inserted":

                inserted_count += 1

                inserted_rows.append({

                    "row_no": row_no,
                    "topic_code": topic_code

                })

            else:

                failed_rows.append({

                    "row_no": row_no,
                    "topic_code": topic_code,
                    "reason": result.get(
                        "reason",
                        "Insert bajarilmadi"
                    )

                })

        except Exception as e:

            failed_rows.append({

                "row_no": item.get("row_no"),
                "topic_code": item.get("topic_code"),
                "reason": str(e)

            })

    return {

        "inserted_count": inserted_count,

        "inserted_rows": inserted_rows,

        "failed_rows": failed_rows

    }

@dp.callback_query(
    lambda c: c.data == "dts_navigator"
)
async def dts_navigator(

    call: CallbackQuery

):

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT
        subject_code,
        subject_name
    FROM dts_tree
    WHERE is_deleted=FALSE
    ORDER BY subject_code
    """)

    subjects = cur.fetchall()

    buttons = []

    for code, name in subjects:

        buttons.append([

            InlineKeyboardButton(

                text=f"📚 {name} [{code}]",

                callback_data=(
                    f"dts_subject_{code}"
                )

            )

        ])

    kb = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await call.message.edit_text(

        "📚 DTS Navigator",

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data.startswith(
        "dts_bob_"
    )
)
async def dts_bob(

    call: CallbackQuery

):

    _, _, subject_code, quarter, bob_code = (
        call.data.split("_")
    )

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT
        bolim_code,
        bolim_name
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND is_deleted=FALSE
    ORDER BY bolim_code
    """, (
        subject_code,
        quarter,
        bob_code
    ))

    bolimlar = cur.fetchall()

    buttons = []

    for code, name in bolimlar:

        buttons.append([

            InlineKeyboardButton(

                text=f"📑 {name} [{code}]",

                callback_data=(
                    f"dts_bolim_"
                    f"{subject_code}_"
                    f"{quarter}_"
                    f"{bob_code}_"
                    f"{code}"
                )

            )

        ])

    buttons.append([

        InlineKeyboardButton(

            text="⬅️ Orqaga",

            callback_data=(
                f"dts_quarter_"
                f"{subject_code}_"
                f"{quarter}"
            )

        )

    ])

    kb = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await call.message.edit_text(

        f"📖 Bob [{bob_code}]",

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data.startswith(
        "dts_bolim_"
    )
)
async def dts_bolim(

    call: CallbackQuery

):

    (
        _,
        _,
        subject_code,
        quarter,
        bob_code,
        bolim_code

    ) = call.data.split("_")

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT
        mavzu_code,
        mavzu_name
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    AND is_deleted=FALSE
    ORDER BY mavzu_code
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code
    ))

    mavzular = cur.fetchall()

    buttons = []

    for code, name in mavzular:

        buttons.append([

            InlineKeyboardButton(

                text=f"📝 {name} [{code}]",

                callback_data=(
                    f"dts_mavzu_"
                    f"{subject_code}_"
                    f"{quarter}_"
                    f"{bob_code}_"
                    f"{bolim_code}_"
                    f"{code}"
                )

            )

        ])

    buttons.append([

        InlineKeyboardButton(

            text="⬅️ Orqaga",

            callback_data=(
                f"dts_bob_"
                f"{subject_code}_"
                f"{quarter}_"
                f"{bob_code}"
            )

        )

    ])

    kb = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await call.message.edit_text(

        f"📑 Bo‘lim [{bolim_code}]",

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data.startswith(
        "dts_mavzu_"
    )
)
async def dts_mavzu(

    call: CallbackQuery

):

    (
        _,
        _,
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code

    ) = call.data.split("_")

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT
        kichik_code,
        kichik_name,
        topic_code
    FROM dts_tree
    WHERE subject_code=%s
    AND quarter=%s
    AND bob_code=%s
    AND bolim_code=%s
    AND mavzu_code=%s
    AND is_deleted=FALSE
    ORDER BY kichik_code
    """, (
        subject_code,
        quarter,
        bob_code,
        bolim_code,
        mavzu_code
    ))

    kichiklar = cur.fetchall()

    buttons = []

    for code, name, topic_code in kichiklar:

        buttons.append([

            InlineKeyboardButton(

                text=f"🔹 {name} [{code}]",

                callback_data=(
                    f"dts_small_"
                    f"{topic_code}"
                )

            )

        ])

    buttons.append([

        InlineKeyboardButton(

            text="⬅️ Orqaga",

            callback_data=(
                f"dts_bolim_"
                f"{subject_code}_"
                f"{quarter}_"
                f"{bob_code}_"
                f"{bolim_code}"
            )

        )

    ])

    kb = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await call.message.edit_text(

        f"📝 Mavzu [{mavzu_code}]",

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data.startswith(
        "dts_small_"
    )
)
async def dts_small(

    call: CallbackQuery

):

    topic_code = call.data.replace(
        "dts_small_",
        ""
    )

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    cur.execute("""
    SELECT

        topic_code,

        grade,

        subject_name,
        subject_code,

        quarter,

        bob_name,
        bob_code,

        bolim_name,
        bolim_code,

        mavzu_name,
        mavzu_code,

        kichik_name,
        kichik_code

    FROM dts_tree
    WHERE topic_code=%s
    AND is_deleted=FALSE
    LIMIT 1
    """, (
        topic_code,
    ))

    row = cur.fetchone()

    if not row:

        await call.answer(
            "Topilmadi"
        )

        return

    (
        topic_code,

        grade,

        subject_name,
        subject_code,

        quarter,

        bob_name,
        bob_code,

        bolim_name,
        bolim_code,

        mavzu_name,
        mavzu_code,

        kichik_name,
        kichik_code

    ) = row

    text = f"""

📌 Topic Code:
{topic_code}

🏫 Sinf:
{grade}

📚 Fan:
{subject_name} [{subject_code}]

🗓 Chorak:
{quarter}

📖 Bob:
{bob_name} [{bob_code}]

📑 Bo‘lim:
{bolim_name} [{bolim_code}]

📝 Mavzu:
{mavzu_name} [{mavzu_code}]

🔹 Kichik mavzu:
{kichik_name} [{kichik_code}]
"""

    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="⬅️ Orqaga",

                    callback_data=(
                        f"dts_mavzu_"
                        f"{subject_code}_"
                        f"{quarter}_"
                        f"{bob_code}_"
                        f"{bolim_code}_"
                        f"{mavzu_code}"
                    )

                )

            ]

        ]
    )

    await call.message.edit_text(

        text,

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data == "dts_menu"
)
async def dts_menu(

    message

):

    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="📥 Import DTS",

                    callback_data="dts_import"

                )

            ],

            [

                InlineKeyboardButton(

                    text="🧭 DTS Navigator",

                    callback_data="dts_navigator"

                )

            ],

            [

                InlineKeyboardButton(

                    text="🔎 DTS Qidiruv",

                    callback_data="dts_search"

                )

            ],

            [

                InlineKeyboardButton(

                    text="📤 Export DTS",

                    callback_data="dts_export"

                )

            ]

        ]
    )

    await message.answer(

        "📚 DTS Boshqaruv Paneli",

        reply_markup=kb

    )

@dp.callback_query(
    lambda c: c.data == "dts_import"
)
async def dts_import(

    call: CallbackQuery,

    state: FSMContext

):

    await state.set_state(
        DTSImportState.waiting_excel
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="⬅️ Orqaga",

                    callback_data="dts_menu"

                )

            ]

        ]
    )

    await call.message.edit_text(

        "📥 DTS excel faylini yuboring",

        reply_markup=kb

    )

@dp.message(
    DTSImportState.waiting_excel,
    F.document
)
async def dts_excel_import(

    message: Message,

    state: FSMContext

):
    
    print("EXCEL KELDI")

    await message.answer(
        "EXCEL KELDI"
     )

    document = message.document

    if not document:

        await message.answer(
            "❌ Excel yuboring"
        )

        return

    file_path = (
        f"temp/{document.file_name}"
    )

    await message.answer(
        "DOWNLOADGA KELDI"
    )

    await bot.download(
        document,
        destination=file_path
    )

    await message.answer(
        "EXCEL OCHILYAPTI"
    )
    wb = load_workbook(
        file_path
    )

    ws = wb.active

    rows = list(
        ws.iter_rows(
            min_row=2,
            values_only=True
        )
    )

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    await message.answer(
        "ANALYZE BOSHLANDI"
    )

    result = analyze_import(
        cur,
        rows
    )

    user_id = message.from_user.id

    dts_import_cache[user_id] = result

    text = f"""

📄 Jami qator:
{len(rows)}

✅ Qo‘shiladi:
{len(result["valid_rows"])}

⚠️ Takroriy:
{len(result["duplicate_rows"])}

⚠️ Bazada bor:
{len(result["existing_rows"])}

❌ Xato:
{len(result["error_rows"])}
"""

    kb = InlineKeyboardMarkup(
        inline_keyboard=[

            [

                InlineKeyboardButton(

                    text="✅ Import qilish",

                    callback_data=(
                        "dts_confirm_import"
                    )

                )

            ],

            [

                InlineKeyboardButton(

                    text="⬅️ Menu",

                    callback_data="dts_menu"

                )

            ]

        ]
    )

    await message.answer(

        text,

        reply_markup=kb

    )

    await state.clear()

@dp.callback_query(
    lambda c: c.data == "dts_confirm_import"
)
async def dts_confirm_import(

    call: CallbackQuery

):

    user_id = call.from_user.id

    cache = dts_import_cache.get(
        user_id
    )

    if not cache:

        await call.answer(
            "Cache topilmadi"
        )

        return

    valid_rows = cache[
        "valid_rows"
    ]

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    inserted_count = confirm_import(

        cur,
        valid_rows

    )

    conn.commit()

    await call.message.edit_text(
        f"""

        ✅ DTS import tugadi

        📥 Qo‘shildi:
        {inserted_count}
        """
    )



