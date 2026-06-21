"""
ai_generator.py — AI bilan test generatsiya qilish
Claude API orqali har mavzu uchun 40 ta savol
"""
import psycopg2, os, json, asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

def db(): return psycopg2.connect(DATABASE_URL)

# Generator holati
gen_state = {}  # user_id -> {grade, subject, selected_topics, ...}


# ─────────────────────────────────────────
# 1. SINF TANLASH
# ─────────────────────────────────────────
async def show_gen_start(message, user_id):
    gen_state[user_id] = {}
    grades = ["1","2","3","4","5","6","7","8","9","10","11"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"gen_grade:{g}")
         for g in grades[i:i+4]]
        for i in range(0, len(grades), 4)
    ])
    await message.answer("🤖 AI Test Generator\n\nSinfni tanlang:", reply_markup=kb)


# ─────────────────────────────────────────
# 2. FAN TANLASH
# ─────────────────────────────────────────
async def show_subjects(call, user_id, grade):
    gen_state[user_id] = {"grade": grade, "selected": []}
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT subject_name FROM dts_tree
        WHERE grade=%s AND is_deleted=FALSE
        ORDER BY subject_name
    """, (grade,))
    subjects = [r[0] for r in cur.fetchall()]
    cur.close(); conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s, callback_data=f"gen_subj:{s[:40]}")]
        for s in subjects
    ] + [[InlineKeyboardButton(text="◀️ Orqaga", callback_data="gen_start")]])

    await call.message.edit_text(
        f"🤖 AI Generator\n🎓 {grade}-sinf\n\nFanni tanlang:",
        reply_markup=kb
    )


# ─────────────────────────────────────────
# 3. KICHIK MAVZULAR RO'YXATI (checkbox)
# ─────────────────────────────────────────
async def show_topics(call, user_id, subject):
    state = gen_state.get(user_id, {})
    grade = state.get("grade", "1")
    state["subject"] = subject
    gen_state[user_id] = state

    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT topic_code, kichik_name, mavzu_name,
               (SELECT COUNT(*) FROM generated_tests WHERE topic_code=t.topic_code) as cnt
        FROM dts_tree t
        WHERE grade=%s AND subject_name=%s AND is_deleted=FALSE
        ORDER BY topic_code
        LIMIT 60
    """, (grade, subject))
    topics = cur.fetchall()
    cur.close(); conn.close()

    state["topics"] = {t[0]: {"kichik": t[1], "mavzu": t[2], "cnt": t[3]} for t in topics}
    selected = state.get("selected", [])

    state["filter"] = "empty"  # Default: faqat bo'sh mavzular
    gen_state[user_id] = state
    await _render_topics(call.message, user_id, selected, grade, subject, edit=True)


async def _render_topics(message, user_id, selected, grade, subject, edit=False):
    state = gen_state.get(user_id, {})
    topics_list = state.get("topics", {})
    filt = state.get("filter", "empty")
    page = state.get("page", 0)
    PAGE_SIZE = 15

    # Filterlash
    if filt == "empty":
        filtered = {k: v for k, v in topics_list.items() if v["cnt"] == 0}
    else:
        filtered = topics_list

    items = list(filtered.items())
    total = len(items)
    page_items = items[page*PAGE_SIZE:(page+1)*PAGE_SIZE]

    empty_cnt = sum(1 for v in topics_list.values() if v["cnt"] == 0)
    all_cnt = len(topics_list)

    text = (
        f"🤖 AI Generator\n"
        f"🎓 {grade}-sinf | 📚 {subject}\n\n"
        f"🔴 Bo'sh: {empty_cnt} ta | 📊 Jami: {all_cnt} ta\n"
        f"✅ Tanlangan: {len(selected)} ta\n"
        f"⚠️ Max 15 ta tanlang\n\n"
    )
    filter_label = "🔴 Faqat bo'sh mavzular" if filt == "empty" else "📋 Barcha mavzular"
    text += f"{filter_label} ({page*PAGE_SIZE+1}-{min((page+1)*PAGE_SIZE, total)}/{total}):"

    rows = []
    for code, info in page_items:
        is_sel = code in selected
        cnt = info["cnt"]
        name = info["kichik"][:22] if info["kichik"] else code[-15:]
        check = "✅" if is_sel else "⬜"
        status = f"✓{cnt}" if cnt > 0 else "✗0"
        rows.append([InlineKeyboardButton(
            text=f"{check} {name} [{status}]",
            callback_data=f"gen_toggle:{code}"
        )])

    # Navigatsiya
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"gen_page:{page-1}"))
    nav.append(InlineKeyboardButton(
        text=f"{'📋 Barchasi' if filt=='empty' else '🔴 Bo\'shlar'}",
        callback_data="gen_filter_toggle"
    ))
    if (page+1)*PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"gen_page:{page+1}"))
    rows.append(nav)

    bottom = [InlineKeyboardButton(text="◀️ Fan", callback_data="gen_subj_back")]
    if selected:
        bottom.append(InlineKeyboardButton(text="❌", callback_data="gen_clear"))
        bottom.append(InlineKeyboardButton(
            text=f"🚀 Boshlash ({len(selected)})",
            callback_data="gen_run"
        ))
    rows.append(bottom)

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ─────────────────────────────────────────
# 4. TOGGLE — mavzu belgilash/olib tashlash
# ─────────────────────────────────────────
async def toggle_topic(call, user_id, code):
    state = gen_state.get(user_id, {})
    selected = state.get("selected", [])

    if code in selected:
        selected.remove(code)
    else:
        if len(selected) >= 15:
            await call.answer("⚠️ Max 15 ta mavzu!", show_alert=True)
            return
        selected.append(code)

    state["selected"] = selected
    gen_state[user_id] = state
    grade = state.get("grade", "1")
    subject = state.get("subject", "")
    await _render_topics(call.message, user_id, selected, grade, subject, edit=True)
    await call.answer()


# ─────────────────────────────────────────
# 5. AI BILAN GENERATSIYA
# ─────────────────────────────────────────
async def run_generator(call, user_id):
    state = gen_state.get(user_id, {})
    selected = state.get("selected", [])
    topics_list = state.get("topics", {})
    grade = state.get("grade", "1")
    subject = state.get("subject", "")

    if not selected:
        await call.answer("❌ Mavzu tanlanmagan!", show_alert=True)
        return

    await call.answer()
    status_msg = await call.message.answer(
        f"🤖 AI ishlamoqda...\n"
        f"📚 {len(selected)} ta mavzu × 20 savol\n"
        f"📊 Jami: {len(selected)*20} ta savol\n"
        f"⏳ Taxminiy vaqt: {len(selected)*20} soniya\n\n"
        f"0/{len(selected)} ✅"
    )

    conn = db(); cur = conn.cursor()
    total_saved = 0
    errors = []

    for idx, code in enumerate(selected):
        info = topics_list.get(code, {})
        kichik = info.get("kichik", code)
        mavzu = info.get("mavzu", "")

        try:
            # Status yangilash
            await status_msg.edit_text(
                f"🤖 AI ishlamoqda...\n"
                f"📚 {len(selected)} ta mavzu\n\n"
                f"{idx}/{len(selected)} ✅\n"
                f"⏳ Hozir: {kichik[:40]}"
            )

            # AI dan savol olish
            questions = await _generate_questions(grade, subject, mavzu, kichik, code)

            if questions:
                # DBga saqlash
                for q in questions:
                    cur.execute("""
                        INSERT INTO generated_tests
                        (topic_code, question, option_a, option_b, option_c, option_d,
                         correct_answer, explanation, question_type, is_latex,
                         image_url, audio_text, language, life_level, age_group,
                         time_limit, difficulty, situation)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT DO NOTHING
                    """, (
                        code,
                        q.get("question",""),
                        q.get("a",""), q.get("b",""), q.get("c",""), q.get("d",""),
                        q.get("correct",""),
                        q.get("explanation",""),
                        q.get("question_type","single_choice"),
                        False,
                        q.get("image_url"),
                        None, "uz", 1,
                        _age_group(grade),
                        q.get("time_limit", 60),
                        q.get("difficulty","oson"),
                        "oddiy"
                    ))
                    total_saved += 1
                conn.commit()

        except Exception as ex:
            errors.append(f"{kichik[:30]}: {str(ex)[:50]}")

        await asyncio.sleep(1)  # Rate limit

    cur.close(); conn.close()

    # Yakuniy hisobot
    err_text = ""
    if errors:
        err_text = f"\n\n⚠️ Xatolar ({len(errors)}):\n" + "\n".join(errors[:5])

    await status_msg.edit_text(
        f"✅ Generatsiya tugadi!\n\n"
        f"📊 Saqlangan: {total_saved} ta savol\n"
        f"📚 Mavzular: {len(selected)} ta{err_text}\n\n"
        f"📥 Excel yaratilmoqda..."
    )

    # Excel eksport — rasmli savollar ko'rinib tursin
    try:
        excel_buf = await _export_to_excel(selected, topics_list, grade, subject)
        from aiogram.types import BufferedInputFile
        await call.message.answer_document(
            BufferedInputFile(excel_buf, filename=f"savol_{grade}sinf_{subject[:10]}.xlsx"),
            caption=(
                f"📊 {total_saved} ta savol\n"
                f"🖼 Rasmli savollar belgilangan\n\n"
                f"image_url ustunidagi nomlar bilan\n"
                f"rasm yasab split: bilan yuboring!"
            )
        )
    except Exception as ex:
        await call.message.answer(f"Excel xato: {ex}")


def _age_group(grade):
    m = {"1":"6-7","2":"7-8","3":"8-9","4":"9-10","5":"10-11",
         "6":"11-12","7":"12-13","8":"13-14","9":"14-15","10":"15-16","11":"16-17"}
    return m.get(str(grade), "10-11")


async def _export_to_excel(selected, topics_list, grade, subject):
    """Saqlangan savollarni Excel ga chiqarish"""
    import openpyxl, io
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "SAVOLLAR"

    headers = [
        "topic_code", "kichik_mavzu", "difficulty", "question_type",
        "question", "option_a", "option_b", "option_c", "option_d",
        "correct_answer", "explanation", "image_url", "time_limit"
    ]

    # Header
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2E86AB")
        cell.alignment = Alignment(horizontal="center")

    conn = db(); cur = conn.cursor()
    row_num = 2

    diff_colors = {
        "oson": "C8F7C5", "o'rta": "FFF3CD",
        "qiyin": "FFD7C4", "murakkab": "F5C6CB"
    }

    for code in selected:
        info = topics_list.get(code, {})
        kichik = info.get("kichik", code)

        cur.execute("""
            SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer, explanation, image_url, time_limit,
                   difficulty, question_type
            FROM generated_tests
            WHERE topic_code=%s
            ORDER BY difficulty, id
        """, (code,))
        rows = cur.fetchall()

        for r in rows:
            q, a, b, c, d, correct, expl, img, tl, diff, qtype = r

            ws.cell(row_num, 1).value = code
            ws.cell(row_num, 2).value = kichik
            ws.cell(row_num, 3).value = diff
            ws.cell(row_num, 4).value = qtype
            ws.cell(row_num, 5).value = q
            ws.cell(row_num, 6).value = a
            ws.cell(row_num, 7).value = b
            ws.cell(row_num, 8).value = c
            ws.cell(row_num, 9).value = d
            ws.cell(row_num, 10).value = correct
            ws.cell(row_num, 11).value = expl
            ws.cell(row_num, 12).value = img
            ws.cell(row_num, 13).value = tl

            # Rang — qiyinlikka qarab
            color = diff_colors.get(diff, "FFFFFF")
            for col in range(1, 14):
                ws.cell(row_num, col).fill = PatternFill("solid", fgColor=color)

            # Rasmli savolni belgilash
            if img:
                ws.cell(row_num, 12).font = Font(bold=True, color="FF0000")

            row_num += 1

        # Mavzular orasiga bo'sh qator
        row_num += 1

    cur.close(); conn.close()

    # Ustun kengliklari
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['E'].width = 50
    for col in ['F','G','H','I','J']:
        ws.column_dimensions[col].width = 20
    ws.column_dimensions['K'].width = 40
    ws.column_dimensions['L'].width = 25

    # Rasmlar varag'i — faqat rasmli savollar
    ws2 = wb.create_sheet("RASMLI SAVOLLAR")
    ws2.append(["image_url", "kichik_mavzu", "savol"])

    conn2 = db(); cur2 = conn2.cursor()
    for code in selected:
        info = topics_list.get(code, {})
        kichik = info.get("kichik", code)
        cur2.execute("""
            SELECT image_url, question FROM generated_tests
            WHERE topic_code=%s AND image_url IS NOT NULL
            ORDER BY id
        """, (code,))
        for img_url, q in cur2.fetchall():
            ws2.append([img_url, kichik, q])
    cur2.close(); conn2.close()

    ws2['A1'].font = Font(bold=True)
    ws2['B1'].font = Font(bold=True)
    ws2['C1'].font = Font(bold=True)
    ws2.column_dimensions['A'].width = 30
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 60

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


async def _generate_questions(grade, subject, mavzu, kichik, topic_code):
    """Claude API orqali 40 ta savol yaratish"""
    import aiohttp

    def diff(n):
        if n <= 10: return "oson"
        elif n <= 20: return "o'rta"
        elif n <= 30: return "qiyin"
        else: return "murakkab"

    def tl(n):
        if n <= 10: return 60
        elif n <= 20: return 55
        elif n <= 30: return 50
        else: return 50

    def eng_pct(n):
        if n <= 10: return "5-10%"
        elif n <= 20: return "20-30%"
        elif n <= 30: return "50%"
        else: return "70-80%"

    # Yosh guruhi
    age = _age_group(grade)

    # Fan tiliga qarab til rejimi
    is_lang_subject = any(x in subject.upper() for x in ["INGLIZ", "RUS", "ENGLISH"])

    if is_lang_subject:
        lang_note = f"""TIL QOIDASI (Ingliz tili fani uchun):
- OSON: O'zbekcha savol, ingliz so'zlar [en]...[/en] ichida (5-10%)
- O'RTA: Aralash, ingliz so'zlar teg ichida (25%)
- QIYIN: Ko'proq ingliz teg bilan (50%)
- MURAKKAB: Asosan ingliz teg bilan (75%)
- O'zbek so'zlar HECH QACHON teg ichida bo'lmasin"""
    else:
        lang_note = "Barcha savol va javoblar o'zbekcha bo'lsin. Atamalar bo'lsa izohlang."

    prompt = f"""Sen {grade}-sinf ({age} yosh) {subject} fani bo'yicha test yaratasang.
Mavzu: {mavzu} — {kichik}

VAZIFA: 20 ta test savoli yarat (har darajadan 5 ta):

DARAJALAR:
1. oson (5 ta, 60s): Eng oddiy — rasm/narsa/so'zni tanish. {grade}-sinf o'quvchisi uchun tushunarli.
2. o'rta (5 ta, 55s): O'rta qiyinlik — qo'llash, to'ldirish.
3. qiyin (5 ta, 50s): Qiyinroq — tushunish, tahlil.
4. murakkab (5 ta, 50s): Eng qiyin — sintez, amaliy qo'llash.

{lang_note}

QOIDA:
- correct: to'g'ri javobning aynan matni (A/B/C/D emas!)
- Savol ichida javob bo'lmasin (qavsda ham)
- Qisqa, aniq, yosh ({age})ga mos
- has_image: 20 savoldan 6 tasida true (rasmli savol)
- question_type: asosan "single_choice", 2 tasida "write_answer" (oson 1 ta, o'rta 1 ta)
- write_answer da option a/b/c/d bo'sh (""), correct = to'g'ri qisqa javob matni

JSON FORMATI (boshqa hech narsa yozma):
[
{{"question":"...","a":"...","b":"...","c":"...","d":"...","correct":"...","explanation":"...","difficulty":"oson","time_limit":60,"question_type":"single_choice","has_image":false}},
...
]"""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            data = await resp.json()
            text = data["content"][0]["text"]

            # JSON ni tozalab olish
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if not match:
                raise ValueError("JSON topilmadi")

            questions = json.loads(match.group())

            # Fieldlarni to'ldirish
            img_counter = 0
            for i, q in enumerate(questions):
                q.setdefault("difficulty", "oson")
                q.setdefault("time_limit", 60)
                q.setdefault("question_type", "single_choice")
                q.setdefault("has_image", False)

                # Rasmli savol uchun image_url
                if q.get("has_image"):
                    img_counter += 1
                    q["image_url"] = f"{topic_code}-{img_counter}"
                else:
                    q["image_url"] = None

                # write_answer uchun javoblarni tozalash
                if q.get("question_type") == "write_answer":
                    q["a"] = q["b"] = q["c"] = q["d"] = ""

            return questions


# ─────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────
async def handle_gen_callback(call, user_id):
    data = call.data

    if data == "gen_start":
        await call.answer()
        await show_gen_start(call.message, user_id)

    elif data.startswith("gen_grade:"):
        grade = data[10:]
        await call.answer()
        await show_subjects(call, user_id, grade)

    elif data.startswith("gen_subj:"):
        subject = data[9:]
        await call.answer()
        await show_topics(call, user_id, subject)

    elif data == "gen_subj_back":
        state = gen_state.get(user_id, {})
        grade = state.get("grade", "1")
        await call.answer()
        await show_subjects(call, user_id, grade)

    elif data.startswith("gen_toggle:"):
        code = data[11:]
        await toggle_topic(call, user_id, code)

    elif data == "gen_clear":
        state = gen_state.get(user_id, {})
        state["selected"] = []
        gen_state[user_id] = state
        grade = state.get("grade", "1")
        subject = state.get("subject", "")
        await _render_topics(call.message, user_id, [], grade, subject, edit=True)
        await call.answer("✅ Tozalandi")

    elif data.startswith("gen_page:"):
        page = int(data[9:])
        state = gen_state.get(user_id, {})
        state["page"] = page
        gen_state[user_id] = state
        selected = state.get("selected", [])
        grade = state.get("grade", "1")
        subject = state.get("subject", "")
        await _render_topics(call.message, user_id, selected, grade, subject, edit=True)
        await call.answer()

    elif data == "gen_filter_toggle":
        state = gen_state.get(user_id, {})
        state["filter"] = "all" if state.get("filter") == "empty" else "empty"
        state["page"] = 0
        gen_state[user_id] = state
        selected = state.get("selected", [])
        grade = state.get("grade", "1")
        subject = state.get("subject", "")
        await _render_topics(call.message, user_id, selected, grade, subject, edit=True)
        await call.answer()

    elif data == "gen_run":
        await run_generator(call, user_id)
