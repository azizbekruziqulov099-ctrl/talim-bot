from aiogram.types import Message
from difflib import SequenceMatcher
from openpyxl import load_workbook
from openpyxl import Workbook
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

dts_import_cache = {}

def normalize_text(text):

    text = str(text).lower().strip()

    text = text.replace("ʻ", "")
    text = text.replace("'", "")
    text = text.replace("`", "")
    text = text.replace("’", "")
    text = text.replace("‘", "")

    text = text.replace(".", "")
    text = text.replace(",", "")

    while "  " in text:
        text = text.replace("  ", " ")

    return ratio >= 0.80




async def dts_import_file(
    message,
    bot,
    user_id
):

    file = await bot.get_file(
        message.document.file_id
    )

    filename = f"dts_{user_id}.xlsx"

    await bot.download_file(
        file.file_path,
        filename
    )

    wb = load_workbook(
        filename
    )

    ws = wb.active

    headers = []

    for cell in ws[1]:

        if cell.value is None:
            headers.append("")

        else:
            headers.append(
                str(cell.value).strip()
            )

    required = [
        "Sinf",
        "Fan",
        "Chorak",
        "Bob",
        "Bo'lim",
        "Mavzu",
        "Kichik mavzu"
    ]

    if headers[:7] != required:

        await message.answer(
            "❌ Excel formati noto'g'ri\n\n"
            "Kerak:\n"
            "Sinf | Fan | Chorak | Bob | Bo'lim | Mavzu | Kichik mavzu"
        )

        return

    rows = []

    for row in ws.iter_rows(
        min_row=2,
        values_only=True
    ):
        rows.append(row)

    errors = []

    for i, row in enumerate(
        rows,
        start=2
    ):

        if not row[0]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Sinf bo'sh"
            })

            continue

        if not row[1]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Fan bo'sh"
            })

            continue

        if not row[2]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Chorak bo'sh"
            })

            continue

        if not row[3]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Bob bo'sh"
            })

            continue

        if not row[4]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Bo'lim bo'sh"
            })

            continue

        if not row[5]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Mavzu bo'sh"
            })

            continue

        if not row[6]:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Kichik mavzu bo'sh"
            })

            continue

    await message.answer(
        f"✅ Excel formati to'g'ri\n\n"
        f"📄 Qatorlar: {len(rows)}\n"
        f"✅ Xato topilmadi"
    )

    valid_grades = [
        "1","2","3","4","5","6",
        "7","8","9","10","11"
    ]

    for i, row in enumerate(
        rows,
        start=2
    ):

        grade = str(
            row[0]
        ).strip()

        if grade not in valid_grades:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": f"Sinf noto'g'ri ({grade})"
            })

            continue

    await message.answer(
        "✅ Sinflar tekshirildi"
    )

    valid_quarters = [
        "1",
        "2",
        "3",
        "4"
    ]

    for i, row in enumerate(
        rows,
        start=2
    ):

        quarter = str(
            row[2]
        ).strip()

        if quarter not in valid_quarters:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": f"Chorak noto'g'ri ({quarter})"
            })
            continue

    await message.answer(
        "✅ Choraklar tekshirildi"
    )

    cur.execute("""
    SELECT DISTINCT subject
    FROM dts_tree
    """)

    subjects = {
        str(x[0]).upper().strip()
        for x in cur.fetchall()
    }

    subject_errors = []

    for i, row in enumerate(
        rows,
        start=2
    ):

        subject = str(
            row[1]
        ).upper().strip()

        if subject not in subjects:

            error_rows.append({
                "row_no": i,
                "row": row,
                "reason": f"Fan topilmadi ({subject})"
            })

            continue

    await message.answer(
        "✅ Fanlar tekshirildi"
    )

    seen = set()

    for i, row in enumerate(
        rows,
        start=2
    ):

        row_key = (
            str(row[0]).strip(),
            str(row[1]).upper().strip(),
            str(row[2]).strip(),
            str(row[3]).strip(),
            str(row[4]).strip(),
            str(row[5]).strip(),
            str(row[6]).strip()
        )

        if row_key in seen:

            duplicate_rows.append({
                "row_no": i,
                "row": row,
                "reason": "Takroriy qator"
            })

        else:

            seen.add(row_key)


    valid_rows = []
    error_rows = []
    duplicate_rows = []
    existing_rows = []
    similar_rows = []

    for i, row in enumerate(
        rows,
        start=2
    ):
        
        similar_found = False

        grade = str(
            row[0]
        ).strip()

        subject = str(
            row[1]
        ).upper().strip()

        quarter = str(
            row[2]
        ).strip()

        bob = str(
            row[3]
        ).strip()

        bolim = str(
            row[4]
        ).strip()

        mavzu = str(
            row[5]
        ).strip()

        kichik = str(
            row[6]
        ).strip()

        cur.execute("""
        SELECT
        kichik_mavzu_name
        FROM dts_tree
        WHERE grade=%s
        AND subject=%s
        AND quarter=%s
        """, (
            grade,
            subject,
            quarter
        ))

        db_rows = cur.fetchall()

    for db_row in db_rows:

        db_kichik = str(
            db_row[0]
        ).strip()

        if is_similar(
            kichik,
            db_kichik
        ):

            if normalize_text(
                kichik
            ) != normalize_text(
                db_kichik
            ):

                similar_rows.append({
                    "row_no": i,
                    "row": row,
                    "reason": f"O'xshash mavzu: {db_kichik}"
                })

                similar_found = True

                break

    cur.execute("""
    SELECT 1
    FROM dts_tree
    WHERE grade=%s
    AND subject=%s
    AND quarter=%s
    AND bob_name=%s
    AND bolim_name=%s
    AND mavzu_name=%s
    AND kichik_mavzu_name=%s
    LIMIT 1
    """, (
        grade,
        subject,
        quarter,
        bob,
        bolim,
        mavzu,
        kichik
    ))

    if cur.fetchone():

        existing_rows.append({
            "row_no": i,
            "row": row,
            "reason": "Bazada bor"
        })

    else:

        if not similar_found:

            valid_rows.append(row)

    dts_import_cache[user_id] = {
        "valid_rows": valid_rows,
        "error_rows": error_rows,
        "duplicate_rows": duplicate_rows,
        "existing_rows": existing_rows,
        "similar_rows": similar_rows
    }

    text = (
        f"📊 DTS tahlili\n\n"
        f"Jami: {len(rows)}\n"
        f"✅ Qo'shiladi: {len(valid_rows)}\n"
        f"⚠️ Bazada bor: {len(existing_rows)}\n"
        f"⚠️ O'xshash: {len(similar_rows)}\n"
        f"⚠️ Takroriy: {len(duplicate_rows)}\n"
        f"❌ Xato: {len(error_rows)}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[]
    )

    if existing_rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="👀 Bazada borlarni ko'rish",
                callback_data="dts_existing"
            )
        ])

    if similar_rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="👀 O'xshashlarni ko'rish",
                callback_data="dts_similar"
            )
        ])

    if duplicate_rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="👀 Takroriylarni ko'rish",
                callback_data="dts_duplicates"
            )
        ])

    if error_rows:

        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text="👀 Xatolarni ko'rish",
                callback_data="dts_errors"
            )
        ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="✅ Import qilish",
            callback_data="dts_import_confirm"
        ),
        InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data="dts_import_cancel"
        )
    ])

    kb.inline_keyboard.append([
        InlineKeyboardButton(
            text="📥 Muammolar.xlsx",
            callback_data="dts_problems"
        )
    ])

    await message.answer(
        text,
        reply_markup=kb
    )


async def dts_existing_show(
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    existing = data.get(
        "existing_rows",
        []
    )

    if not existing:

        await call.answer(
            "Ma'lumot yo'q"
        )

        return

    lines = []

    for item in existing[:30]:

        lines.append(
            f"{item['row_no']}-qator\n"
            f"Sabab: {item['reason']}"
        )

    text = (
        "⚠️ Bazada bor mavzular\n\n"
        + "\n\n".join(lines)
    )

    await call.message.answer(
        text
    )

async def dts_similar_show(
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    similar = data.get(
        "similar_rows",
        []
    )

    if not similar:

        await call.answer(
            "Ma'lumot yo'q"
        )

        return

    lines = []

    for item in similar[:30]:

        lines.append(
            f"{item['row_no']}-qator\n"
            f"Sabab: {item['reason']}"
        )

    text = (
        "⚠️ O'xshash mavzular\n\n"
        + "\n\n".join(lines)
    )

    await call.message.answer(
        text
    )
async def dts_import_cancel(
    call,
    user_id
):

    dts_import_cache.pop(
        user_id,
        None
    )

    await call.message.answer(
        "❌ Import bekor qilindi"
    )

async def dts_import_confirm(
        
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    rows = data.get(
        "valid_rows",
        []
    )

    if not rows:

        await call.answer(
            "Import uchun ma'lumot topilmadi"
        )

        return        
    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    bob_map = {}
    bolim_map = {}
    mavzu_map = {}
    kichik_map = {}

    added = 0

    await call.message.answer(
        f"🚀 Import boshlandi\n\n"
        f"Import qilinadigan qatorlar: {len(rows)}"
    )

    for row in rows:

        subject = str(
            row[1]
        ).upper()

        quarter = f"Q{row[2]}"

        bob = str(
            row[3]
        ).strip()

        bolim = str(
            row[4]
        ).strip()

        mavzu = str(
            row[5]
        ).strip()

        kichik = str(
            row[6]
        ).strip()

        if bob not in bob_map:
            bob_map[bob] = (
                len(bob_map) + 1
            )

        bob_no = bob_map[bob]

        bolim_key = (
            f"{bob}|{bolim}"
        )

        if bolim_key not in bolim_map:
            bolim_map[
                bolim_key
            ] = (
                len([
                    x
                    for x in bolim_map
                    if x.startswith(
                        f"{bob}|"
                    )
                ]) + 1
            )

        bolim_no = bolim_map[
            bolim_key
        ]

        mavzu_key = (
            f"{bolim_key}|{mavzu}"
        )

        if mavzu_key not in mavzu_map:
            mavzu_map[
                mavzu_key
            ] = (
                len([
                    x
                    for x in mavzu_map
                    if x.startswith(
                        f"{bolim_key}|"
                    )
                ]) + 1
            )

        mavzu_no = mavzu_map[
            mavzu_key
        ]

        kichik_key = (
            f"{mavzu_key}|{kichik}"
        )

        if kichik_key not in kichik_map:
            kichik_map[
                kichik_key
            ] = (
                len([
                    x
                    for x in kichik_map
                    if x.startswith(
                        f"{mavzu_key}|"
                    )
                ]) + 1
            )

        kichik_no = kichik_map[
            kichik_key
        ]

        topic_code = (
            f"{subject}-"
            f"{quarter}-"
            f"B{bob_no:02d}-"
            f"BL{bolim_no:02d}-"
            f"M{mavzu_no:02d}-"
            f"S{kichik_no:03d}"
        )

        cur.execute(
            """
            INSERT INTO dts_tree (
                topic_code,
                grade,
                quarter,
                subject,
                track,
                bob_code,
                bolim_code,
                mavzu_code,
                kichik_mavzu_code,
                bob_name,
                bolim_name,
                mavzu_name,
                kichik_mavzu_name
            )
            VALUES (
                %s,%s,%s,%s,
                'DTS',
                %s,%s,%s,%s,
                %s,%s,%s,%s
            )
            ON CONFLICT (topic_code)
            DO NOTHING
            """,
            (
                topic_code,
                str(row[0]),
                str(row[2]),
                subject,
                f"B{bob_no:02d}",
                f"BL{bolim_no:02d}",
                f"M{mavzu_no:02d}",
                f"S{kichik_no:03d}",
                bob,
                bolim,
                mavzu,
                kichik
            )
        )

        added += 1

    conn.commit()

    cur.execute("""
    SELECT COUNT(*)
    FROM dts_tree
    """)

    total_topics = cur.fetchone()[0]

    cur.close()
    conn.close()

    await call.message.answer(
        f"✅ DTS import tugadi\n\n"
        f"📥 Qo'shildi: {added}\n"
        f"📚 Jami mavzular: {total_topics}"
    )

    dts_import_cache.pop(
        user_id,
        None
    )

async def dts_errors_show(
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    errors = data.get(
        "error_rows",
        []
    )

    if not errors:

        await call.answer(
            "Ma'lumot yo'q"
        )

        return

    lines = []

    for item in errors[:30]:

        lines.append(
            f"{item['row_no']}-qator\n"
            f"Sabab: {item['reason']}"
        )

    await call.message.answer(
        "❌ Xatolar\n\n"
        + "\n\n".join(lines)
    )

async def dts_duplicates_show(
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    duplicates = data.get(
        "duplicate_rows",
        []
    )

    if not duplicates:

        await call.answer(
            "Ma'lumot yo'q"
        )

        return

    lines = []

    for item in duplicates[:30]:

        lines.append(
            f"{item['row_no']}-qator\n"
            f"Sabab: {item['reason']}"
        )

    await call.message.answer(
        "⚠️ Takroriy qatorlar\n\n"
        + "\n\n".join(lines)
    )

async def dts_problems_export(
    call,
    user_id
):

    data = dts_import_cache.get(
        user_id,
        {}
    )

    problems = (
        data.get("error_rows", [])
        + data.get("duplicate_rows", [])
        + data.get("existing_rows", [])
        + data.get("similar_rows", [])
    )

    if not problems:

        await call.answer(
            "Muammolar topilmadi"
        )

        return

    wb = Workbook()

    ws = wb.active

    ws.title = "Muammolar"

    ws.append([
        "Qator",
        "Sinf",
        "Fan",
        "Chorak",
        "Bob",
        "Bo'lim",
        "Mavzu",
        "Kichik mavzu",
        "Sabab"
    ])

    for item in problems:

        row = item["row"]

        ws.append([
            item["row_no"],
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            item["reason"]
        ])

    file_name = (
        f"dts_muammolar_{user_id}.xlsx"
    )

    wb.save(file_name)

    await call.message.answer_document(
        FSInputFile(file_name),
        caption="📥 DTS muammolar hisoboti"
    )

    os.remove(file_name)
