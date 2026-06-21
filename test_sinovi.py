"""
test_sinovi.py — Admin uchun test sinovi
Sinf → Fan → Mavzu → Test boshlash
"""
import psycopg2, os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")
sinov_state = {}  # user_id -> {grade, subject, ...}

def db(): return psycopg2.connect(DATABASE_URL)


async def show_sinov_start(message, user_id):
    sinov_state[user_id] = {}
    grades = ["1","2","3","4","5","6","7","8","9","10","11"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"sinov_grade:{g}")
         for g in grades[i:i+4]]
        for i in range(0, len(grades), 4)
    ])
    await message.answer("🧪 Test sinovi\n\nSinfni tanlang:", reply_markup=kb)


async def handle_sinov_callback(call, user_id):
    data = call.data

    # Sinf tanlash
    if data.startswith("sinov_grade:"):
        grade = data[12:]
        sinov_state[user_id] = {"grade": grade}
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT subject_name FROM dts_tree
            WHERE grade=%s AND is_deleted=FALSE
            ORDER BY subject_name
        """, (grade,))
        subjects = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=s, callback_data=f"sinov_subj:{s[:40]}")]
            for s in subjects
        ] + [[InlineKeyboardButton(text="◀️ Orqaga", callback_data="sinov_start")]])

        await call.message.edit_text(
            f"🧪 Test sinovi\n🎓 {grade}-sinf\n\nFanni tanlang:",
            reply_markup=kb
        )
        await call.answer()

    # Fan tanlash
    elif data.startswith("sinov_subj:"):
        subject = data[11:]
        state = sinov_state.get(user_id, {})
        grade = state.get("grade", "1")
        state["subject"] = subject
        sinov_state[user_id] = state

        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT t.topic_code, t.kichik_name, t.mavzu_name,
                   COUNT(g.id) as test_cnt
            FROM dts_tree t
            LEFT JOIN generated_tests g ON g.topic_code = t.topic_code
            WHERE t.grade=%s AND t.subject_name=%s AND t.is_deleted=FALSE
            GROUP BY t.topic_code, t.kichik_name, t.mavzu_name
            HAVING COUNT(g.id) > 0
            ORDER BY t.topic_code
            LIMIT 30
        """, (grade, subject))
        topics = cur.fetchall()
        cur.close(); conn.close()

        if not topics:
            await call.answer("❌ Testlar topilmadi!", show_alert=True)
            return

        state["topics"] = {t[0]: {"kichik": t[1], "mavzu": t[2], "cnt": t[3]} for t in topics}
        sinov_state[user_id] = state

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"📝 {t[1][:30]} ({t[3]}✓)",
                callback_data=f"sinov_topic:{t[0]}"
            )] for t in topics
        ] + [[InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"sinov_grade:{grade}")]])

        await call.message.edit_text(
            f"🧪 Test sinovi\n🎓 {grade}-sinf | 📚 {subject}\n\n"
            f"Mavzu tanlang ({len(topics)} ta):",
            reply_markup=kb
        )
        await call.answer()

    # Mavzu tanlash — testlar haqida ma'lumot
    elif data.startswith("sinov_topic:"):
        topic_code = data[12:]
        state = sinov_state.get(user_id, {})
        info = state.get("topics", {}).get(topic_code, {})

        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT difficulty, COUNT(*) FROM generated_tests
            WHERE topic_code=%s
            GROUP BY difficulty
        """, (topic_code,))
        diff_counts = {r[0]: r[1] for r in cur.fetchall()}
        cur.close(); conn.close()

        oson = diff_counts.get("oson", 0)
        orta = diff_counts.get("o'rta", 0)
        qiyin = diff_counts.get("qiyin", 0)
        murakkab = diff_counts.get("murakkab", 0)
        total = oson + orta + qiyin + murakkab

        text = (
            f"🧪 Test sinovi\n\n"
            f"📌 {info.get('kichik', topic_code)}\n"
            f"📚 {info.get('mavzu', '')}\n\n"
            f"📊 Jami: {total} ta test\n"
            f"🟢 Oson: {oson}\n"
            f"🟡 O'rta: {orta}\n"
            f"🟠 Qiyin: {qiyin}\n"
            f"🔴 Murakkab: {murakkab}\n\n"
            f"Qaysi darajadan boshlaysiz?"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🟢 Oson ({oson})", callback_data=f"sinov_start_test:{topic_code}:oson"),
                InlineKeyboardButton(text=f"🟡 O'rta ({orta})", callback_data=f"sinov_start_test:{topic_code}:o'rta"),
            ],
            [
                InlineKeyboardButton(text=f"🟠 Qiyin ({qiyin})", callback_data=f"sinov_start_test:{topic_code}:qiyin"),
                InlineKeyboardButton(text=f"🔴 Murakkab ({murakkab})", callback_data=f"sinov_start_test:{topic_code}:murakkab"),
            ],
            [
                InlineKeyboardButton(text=f"▶️ Barchasi ({total})", callback_data=f"sinov_start_test:{topic_code}:all"),
            ],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"sinov_subj:{state.get('subject', '')}")],
        ])

        await call.message.edit_text(text, reply_markup=kb)
        await call.answer()

    # Test boshlash
    elif data.startswith("sinov_start_test:"):
        parts = data.split(":")
        topic_code = parts[1]
        diff = parts[2] if len(parts) > 2 else "all"

        conn = db(); cur = conn.cursor()
        if diff == "all":
            cur.execute("""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type, is_latex,
                       image_url, audio_text, language, time_limit
                FROM generated_tests WHERE topic_code=%s
                ORDER BY RANDOM() LIMIT 20
            """, (topic_code,))
        else:
            cur.execute("""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type, is_latex,
                       image_url, audio_text, language, time_limit
                FROM generated_tests WHERE topic_code=%s AND difficulty=%s
                ORDER BY RANDOM()
            """, (topic_code, diff))
        tests = cur.fetchall()
        cur.close(); conn.close()

        if not tests:
            await call.answer("❌ Test topilmadi!", show_alert=True)
            return

        await call.answer()
        from test_engine import start_test
        await start_test(user_id, tests, call.message)

    elif data == "sinov_start":
        await call.answer()
        await show_sinov_start(call.message, user_id)
