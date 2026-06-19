import os
import io
import pandas as pd
import psycopg2
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from aiogram import F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from loader import dp, bot
from storage import user_state

DATABASE_URL = os.getenv("DATABASE_URL")
ADMINS = [int(x) for x in os.getenv("ADMINS", "401251407").split(",")]

PAGE_SIZE = 10


class LessonAdminState(StatesGroup):
    waiting_excel = State()


# ─────────────────────────────────────────
# YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────

def db():
    return psycopg2.connect(DATABASE_URL)


def back_btn(callback_data, text="⬅️ Ortga"):
    return [InlineKeyboardButton(text=text, callback_data=callback_data)]


def admin_menu_btn():
    return [InlineKeyboardButton(text="🏠 Admin menyu", callback_data="lesson_admin_home")]


def paginate(items, page, prefix, label_fn):
    """10 talik sahifalash"""
    start   = page * PAGE_SIZE
    end     = start + PAGE_SIZE
    chunk   = items[start:end]
    buttons = []

    for item in chunk:
        buttons.append([InlineKeyboardButton(
            text=label_fn(item),
            callback_data=f"{prefix}{item[0]}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"{prefix}page_{page-1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page+1}/{(len(items)-1)//PAGE_SIZE+1}",
        callback_data="noop"
    ))
    if end < len(items):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"{prefix}page_{page+1}"))
    if nav:
        buttons.append(nav)

    return buttons


# ─────────────────────────────────────────
# 1. KIRISH — Admin menyudan
# ─────────────────────────────────────────

@dp.message(F.text == "📝 Dars boshqaruvi")
async def lesson_admin_entry(message: Message):
    if message.from_user.id not in ADMINS:
        return
    await show_grades(message)


async def show_grades(message_or_call, page=0):
    conn = db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT DISTINCT grade FROM dts_tree
        WHERE is_deleted=FALSE ORDER BY grade
    """)
    grades = cur.fetchall()
    cur.close()
    conn.close()

    buttons = paginate(
        grades, page,
        prefix="la_grade_",
        label_fn=lambda r: f"🏫 {r[0]}-sinf"
    )
    buttons.append(admin_menu_btn())

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "📝 Dars boshqaruvi\n\nSinf tanlang:"

    if isinstance(message_or_call, Message):
        await message_or_call.answer(text, reply_markup=kb)
    else:
        await message_or_call.message.edit_text(text, reply_markup=kb)


# ─────────────────────────────────────────
# 2. SINF → FAN
# ─────────────────────────────────────────

@dp.callback_query(F.data.startswith("la_grade_"))
async def la_grade(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.answer()

    data = call.data.replace("la_grade_", "")

    if data.startswith("page_"):
        page = int(data.replace("page_", ""))
        await show_grades(call, page)
        return

    grade = data
    conn  = db()
    cur   = conn.cursor()
    cur.execute("""
        SELECT DISTINCT subject_code, subject_name
        FROM dts_tree
        WHERE grade=%s AND is_deleted=FALSE
        ORDER BY subject_name
    """, (grade,))
    subjects = cur.fetchall()
    cur.close()
    conn.close()

    buttons = []
    for code, name in subjects:
        buttons.append([InlineKeyboardButton(
            text=f"📘 {name}",
            callback_data=f"la_sub|{grade}|{code}"
        )])

    buttons.append(back_btn("la_back_grades"))
    buttons.append(admin_menu_btn())

    await call.message.edit_text(
        f"📝 {grade}-sinf\nFan tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ─────────────────────────────────────────
# 3. FAN → MAVZULAR (10 talik, dars bor/yo'q)
# ─────────────────────────────────────────

@dp.callback_query(F.data.startswith("la_sub|"))
async def la_subject(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.answer()

    parts        = call.data.split("|")
    grade        = parts[1]
    subject_code = parts[2]
    page         = int(parts[3]) if len(parts) > 3 else 0

    conn = db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT DISTINCT mavzu_code, mavzu_name
        FROM dts_tree
        WHERE grade=%s AND subject_code=%s AND is_deleted=FALSE
        ORDER BY mavzu_code
    """, (grade, subject_code))
    mavzular = cur.fetchall()

    # Har mavzu uchun: teacher_lessons da bor/yo'q
    cur.execute("""
        SELECT DISTINCT t.mavzu_code,
               COUNT(DISTINCT t.mavzu_code) as total,
               COUNT(DISTINCT tl.topic_code) as filled
        FROM dts_tree t
        LEFT JOIN teacher_lessons tl ON tl.topic_code = t.topic_code
        WHERE t.grade=%s AND t.subject_code=%s AND t.is_deleted=FALSE
        GROUP BY t.mavzu_code
    """, (grade, subject_code))
    raw_stats = cur.fetchall()

    # Soddaroq: mavzu_code → filled > 0 bo'lsa bor
    stats = {}
    for mavzu_code, _, filled in raw_stats:
        stats[mavzu_code] = filled

    cur.execute("""
        SELECT DISTINCT subject_name FROM dts_tree
        WHERE grade=%s AND subject_code=%s LIMIT 1
    """, (grade, subject_code))
    subj_row = cur.fetchone()
    subject_name = subj_row[0] if subj_row else subject_code

    cur.close()
    conn.close()

    # Sahifalash
    start = page * PAGE_SIZE
    end   = start + PAGE_SIZE
    chunk = mavzular[start:end]

    buttons = []
    for code, name in chunk:
        filled = stats.get(code, 0)
        icon   = "✅" if filled > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {name}",
            callback_data=f"la_mav|{grade}|{subject_code}|{code}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"la_sub|{grade}|{subject_code}|{page-1}"
        ))
    nav.append(InlineKeyboardButton(
        text=f"{page+1}/{(len(mavzular)-1)//PAGE_SIZE+1}",
        callback_data="noop"
    ))
    if end < len(mavzular):
        nav.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"la_sub|{grade}|{subject_code}|{page+1}"
        ))
    if nav:
        buttons.append(nav)

    buttons.append(back_btn(f"la_grade_{grade}"))
    buttons.append(admin_menu_btn())

    total_all  = len(mavzular)
    filled_all = sum(1 for v in stats.values() if v > 0)

    await call.message.edit_text(
        f"📝 {grade}-sinf | {subject_name}\n"
        f"Mavzular: {filled_all}/{total_all} ta dars bor\n\n"
        f"✅ Dars bor  ❌ Bo'sh",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ─────────────────────────────────────────
# 4. MAVZU → KICHIK MAVZULAR + SHABLON/IMPORT
# ─────────────────────────────────────────

@dp.callback_query(F.data.startswith("la_mav|"))
async def la_mavzu(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.answer()

    parts        = call.data.split("|")
    grade        = parts[1]
    subject_code = parts[2]
    mavzu_code   = parts[3]

    conn = db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT kichik_code, kichik_name, topic_code,
               subject_name, mavzu_name,
               quarter, bob_name, bolim_name
        FROM dts_tree
        WHERE grade=%s AND subject_code=%s AND mavzu_code=%s
          AND is_deleted=FALSE
        ORDER BY kichik_code
    """, (grade, subject_code, mavzu_code))
    rows = cur.fetchall()

    if not rows:
        await call.message.edit_text("❌ Kichik mavzular topilmadi")
        cur.close()
        conn.close()
        return

    topic_codes = [r[2] for r in rows]
    cur.execute("""
        SELECT topic_code FROM teacher_lessons
        WHERE topic_code = ANY(%s)
    """, (topic_codes,))
    existing = {r[0] for r in cur.fetchall()}

    cur.close()
    conn.close()

    subject_name = rows[0][3]
    mavzu_name   = rows[0][4]
    quarter      = rows[0][5]
    bob_name     = rows[0][6]
    bolim_name   = rows[0][7]

    filled = len([r for r in rows if r[2] in existing])
    total  = len(rows)

    buttons = []
    for code, name, topic_code, *_ in rows:
        icon = "✅" if topic_code in existing else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {name}",
            callback_data=f"la_small_{topic_code}"
        )])

    buttons.append([InlineKeyboardButton(
        text="📥 Shablon yuklab ol",
        callback_data=f"la_tmpl|{grade}|{subject_code}|{mavzu_code}"
    )])
    buttons.append([InlineKeyboardButton(
        text="📤 Import qilish",
        callback_data=f"la_imp|{grade}|{subject_code}|{mavzu_code}"
    )])
    buttons.append(back_btn(f"la_sub|{grade}|{subject_code}"))
    buttons.append(admin_menu_btn())

    await call.message.edit_text(
        f"📝 {grade}-sinf | {subject_name}\n"
        f"📖 {mavzu_name}\n"
        f"📌 {quarter}-chorak | {bob_name} | {bolim_name}\n"
        f"━━━━━━━━━━━━━━\n"
        f"Kichik mavzular: {filled}/{total} to'liq\n\n"
        f"✅ Dars bor  ❌ Bo'sh",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ─────────────────────────────────────────
# 5. SHABLON YUKLAB OLISH
# ─────────────────────────────────────────

@dp.callback_query(F.data.startswith("la_tmpl|"))
async def la_template(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        return
    await call.answer("📥 Shablon tayyorlanmoqda...")

    parts        = call.data.split("|")
    grade        = parts[1]
    subject_code = parts[2]
    mavzu_code   = parts[3]

    conn = db()
    cur  = conn.cursor()

    cur.execute("""
        SELECT kichik_code, kichik_name, topic_code,
               subject_name, mavzu_name
        FROM dts_tree
        WHERE grade=%s AND subject_code=%s AND mavzu_code=%s
          AND is_deleted=FALSE
        ORDER BY kichik_code
    """, (grade, subject_code, mavzu_code))
    rows = cur.fetchall()

    topic_codes = [r[2] for r in rows]
    cur.execute("""
        SELECT topic_code, intro, part_1, part_2, part_3, part_4,
               simple_1, simple_2, example_1, example_2,
               exercise_1, exercise_2, summary
        FROM teacher_lessons
        WHERE topic_code = ANY(%s)
    """, (topic_codes,))
    lessons = {r[0]: r for r in cur.fetchall()}

    cur.close()
    conn.close()

    subject_name = rows[0][3] if rows else ""
    mavzu_name   = rows[0][4] if rows else ""

    filepath = make_excel(rows, lessons, grade, subject_name, mavzu_name)

    await call.message.answer_document(
        FSInputFile(filepath),
        caption=(
            f"📥 Shablon tayyor!\n\n"
            f"🏫 {grade}-sinf | {subject_name}\n"
            f"📖 {mavzu_name}\n\n"
            f"✅ Yashil — dars bor (tahrirlasa bo'ladi)\n"
            f"⬜ Oq — bo'sh, to'ldiring\n\n"
            f"To'ldirib yuborish uchun 👇"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📤 Import qilish",
                callback_data=f"la_imp|{grade}|{subject_code}|{mavzu_code}"
            )
        ]])
    )

    if os.path.exists(filepath):
        os.remove(filepath)


def make_excel(rows, lessons, grade, subject_name, mavzu_name):
    wb  = Workbook()
    thin   = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    HEADER = "1F4E79"
    EXISTS = "E2EFDA"
    EMPTY  = "FFFFFF"
    FIXED  = "D6E4F0"

    columns = [
        ("topic_code", 16),
        ("grade",       8),
        ("subject",    18),
        ("mavzu",      22),
        ("intro",      45),
        ("part_1",     45),
        ("part_2",     45),
        ("part_3",     45),
        ("part_4",     45),
        ("simple_1",   38),
        ("simple_2",   38),
        ("example_1",  38),
        ("example_2",  38),
        ("exercise_1", 38),
        ("exercise_2", 38),
        ("summary",    45),
    ]

    # ── Sheet 1: DARSLAR ──
    ws = wb.active
    ws.title = "DARSLAR"

    ws.merge_cells(f"A1:{get_column_letter(len(columns))}1")
    t = ws["A1"]
    t.value     = f"📝 {grade}-sinf | {subject_name} | {mavzu_name}"
    t.font      = Font(bold=True, color="FFFFFF", name="Arial", size=12)
    t.fill      = PatternFill("solid", start_color=HEADER)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    for col, (name, width) in enumerate(columns, 1):
        c           = ws.cell(row=2, column=col, value=name)
        c.font      = Font(bold=True, color="FFFFFF", name="Arial", size=9)
        c.fill      = PatternFill("solid", start_color=HEADER)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border    = border
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[2].height = 25

    col_map = {name: i+1 for i, (name, _) in enumerate(columns)}
    editable = {"intro","part_1","part_2","part_3","part_4",
                "simple_1","simple_2","example_1","example_2",
                "exercise_1","exercise_2","summary"}

    for row_idx, (kichik_code, kichik_name, topic_code, *_) in enumerate(rows, 3):
        lesson    = lessons.get(topic_code)
        is_filled = lesson is not None

        lesson_map = {}
        if lesson:
            keys = ["topic_code","intro","part_1","part_2","part_3","part_4",
                    "simple_1","simple_2","example_1","example_2",
                    "exercise_1","exercise_2","summary"]
            lesson_map = {k: (lesson[i] or "") for i, k in enumerate(keys)}

        fixed = {
            "topic_code": topic_code,
            "grade":      grade,
            "subject":    subject_name,
            "mavzu":      kichik_name,
        }

        for col_name, col_idx in col_map.items():
            if col_name in fixed:
                val = fixed[col_name]
                bg  = FIXED
            elif col_name in editable:
                val = lesson_map.get(col_name, "")
                bg  = EXISTS if is_filled else EMPTY
            else:
                val = ""
                bg  = EMPTY

            c           = ws.cell(row=row_idx, column=col_idx, value=val)
            c.font      = Font(name="Arial", size=10)
            c.fill      = PatternFill("solid", start_color=bg)
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border    = border

        ws.row_dimensions[row_idx].height = 80

    # ── Sheet 2: NAMUNA ──
    ws2 = wb.create_sheet("NAMUNA")
    ws2.merge_cells(f"A1:{get_column_letter(len(columns))}1")
    n           = ws2["A1"]
    n.value     = "✅ NAMUNA — qanday to'ldirish kerak"
    n.font      = Font(bold=True, color="FFFFFF", name="Arial", size=12)
    n.fill      = PatternFill("solid", start_color="375623")
    n.alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 30

    for col, (name, width) in enumerate(columns, 1):
        c           = ws2.cell(row=2, column=col, value=name)
        c.font      = Font(bold=True, color="FFFFFF", name="Arial", size=9)
        c.fill      = PatternFill("solid", start_color=HEADER)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border    = border
        ws2.column_dimensions[get_column_letter(col)].width = width

    sample = [
        "TEST_001", grade, subject_name, "Namuna kichik mavzu",
        "🌟 Bugun qiziqarli mavzuni o'rganamiz!\nSiz hech o'ylab ko'rganmisiz...",
        "📖 1-qism. [en]Hello[/en] degani...\n[latex]\\frac{1}{2}[/latex]",
        "📌 2-qism. Qoidalar:\n• Birinchi...\n• Ikkinchi...",
        "", "",
        "💡 Oddiyroq: ...",
        "",
        "🎬 Misol: ...",
        "", "", "",
        "✅ Bugun o'rgandik:\n1) ...\n2) ..."
    ]
    for col, val in enumerate(sample, 1):
        c           = ws2.cell(row=3, column=col, value=val)
        c.font      = Font(name="Arial", size=10)
        c.fill      = PatternFill("solid", start_color="FFFFFF")
        c.alignment = Alignment(vertical="top", wrap_text=True)
        c.border    = border
    ws2.row_dimensions[3].height = 120

    # ── Sheet 3: TEGLAR ──
    ws3 = wb.create_sheet("TEGLAR")
    ws3.column_dimensions["A"].width = 30
    ws3.column_dimensions["B"].width = 55

    ws3.merge_cells("A1:B1")
    t           = ws3["A1"]
    t.value     = "🏷 TEG FORMATLARI VA QOIDALAR"
    t.font      = Font(bold=True, color="FFFFFF", name="Arial", size=12)
    t.fill      = PatternFill("solid", start_color="7030A0")
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws3.row_dimensions[1].height = 28

    tags = [
        ("TEG", "MISOL / IZOH"),
        ("[en]...[/en]", "[en]Hello[/en] — inglizcha, boshqa ovozda"),
        ("[ru]...[/ru]", "[ru]Привет[/ru] — ruscha ovozda"),
        ("[latex]...[/latex]", "[latex]\\frac{1}{2}[/latex] — formula rasmi + ovoz"),
        ("[img]nom[/img]", "[img]kasrlar_rasm[/img] — DB dagi rasm"),
        ("", ""),
        ("MAJBURIY", "intro, part_1, part_2, summary — bo'sh qoldirmang!"),
        ("IXTIYORIY", "part_3, part_4, simple_*, example_*, exercise_*"),
    ]
    for i, (a, b) in enumerate(tags, 2):
        for col, val in [(1, a), (2, b)]:
            c           = ws3.cell(row=i, column=col, value=val)
            c.font      = Font(bold=(i == 2 or a == "MAJBURIY"), name="Arial", size=10)
            c.alignment = Alignment(vertical="center", wrap_text=True)
            c.border    = border
            if i == 2 or a == "MAJBURIY":
                c.fill = PatternFill("solid", start_color="D9D9D9")
        ws3.row_dimensions[i].height = 28

    filepath = f"lesson_{grade}_{mavzu_name[:15]}.xlsx"
    wb.save(filepath)
    return filepath


# ─────────────────────────────────────────
# 6. IMPORT
# ─────────────────────────────────────────

@dp.callback_query(F.data.startswith("la_imp|"))
async def la_import_prompt(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return
    await call.answer()

    parts        = call.data.split("|")
    grade        = parts[1]
    subject_code = parts[2]
    mavzu_code   = parts[3]

    await state.update_data(import_meta=call.data)
    await state.set_state(LessonAdminState.waiting_excel)

    await call.message.answer(
        "📤 To'ldirilgan Excel faylini yuboring:\n\n"
        "⚠️ Faqat 'DARSLAR' sheetidagi ma'lumotlar saqlanadi"
    )


@dp.message(LessonAdminState.waiting_excel)
async def la_import_excel(message: Message, state: FSMContext):
    if not message.document:
        await message.answer("❌ Excel fayl yuboring")
        return

    file = await bot.get_file(message.document.file_id)
    buf  = io.BytesIO()
    await bot.download_file(file.file_path, buf)
    buf.seek(0)

    try:
        df = pd.read_excel(buf, sheet_name="DARSLAR", dtype=str)
    except Exception as e:
        await message.answer(f"❌ Excel o'qib bo'lmadi:\n{e}")
        await state.clear()
        return

    conn = db()
    cur  = conn.cursor()

    added   = 0
    updated = 0
    skipped = 0

    def v(row, col):
        val = row.get(col, "")
        return "" if str(val) in ("nan", "None", "") else str(val).strip()

    for _, row in df.iterrows():
        topic_code = v(row, "topic_code")
        intro      = v(row, "intro")

        if not topic_code or not intro:
            skipped += 1
            continue

        cur.execute(
            "SELECT id FROM teacher_lessons WHERE topic_code=%s",
            (topic_code,)
        )
        exists = cur.fetchone()

        fields = (
            intro,
            v(row, "part_1"), v(row, "part_2"),
            v(row, "part_3"), v(row, "part_4"),
            v(row, "simple_1"), v(row, "simple_2"),
            v(row, "example_1"), v(row, "example_2"),
            v(row, "exercise_1"), v(row, "exercise_2"),
            v(row, "summary")
        )

        if exists:
            cur.execute("""
                UPDATE teacher_lessons SET
                    intro=%s, part_1=%s, part_2=%s, part_3=%s, part_4=%s,
                    simple_1=%s, simple_2=%s, example_1=%s, example_2=%s,
                    exercise_1=%s, exercise_2=%s, summary=%s
                WHERE topic_code=%s
            """, (*fields, topic_code))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO teacher_lessons
                (topic_code, intro, part_1, part_2, part_3, part_4,
                 simple_1, simple_2, example_1, example_2,
                 exercise_1, exercise_2, summary)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (topic_code, *fields))
            added += 1

    conn.commit()
    cur.close()
    conn.close()
    await state.clear()

    await message.answer(
        f"✅ Import tugadi!\n\n"
        f"➕ Yangi qo'shildi: {added}\n"
        f"✏️ Yangilandi: {updated}\n"
        f"⏭ O'tkazildi (bo'sh): {skipped}"
    )


# ─────────────────────────────────────────
# 7. ORTGA QAYTISH
# ─────────────────────────────────────────

@dp.callback_query(F.data == "la_back_grades")
async def la_back_grades(call: CallbackQuery):
    await call.answer()
    await show_grades(call)


@dp.callback_query(F.data == "lesson_admin_home")
async def la_home(call: CallbackQuery):
    await call.answer()
    await call.message.delete()


@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
