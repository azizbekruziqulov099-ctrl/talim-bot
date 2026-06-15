from keyboards import get_main_keyboard

from aiogram import Router, F
from aiogram.types import Message
import os
import psycopg2
import edge_tts
from aiogram.types import FSInputFile
import tempfile
from test_engine import speak_text
from storage import user_state

DATABASE_URL = os.getenv("DATABASE_URL")

async def read_current_page(user_id, message, user_state):

    text = user_state.get(user_id, {}).get("speak_text")

    if not text:
        await message.answer(
            "❌ O'qiladigan matn topilmadi."
        )
        return

    await speak_text(
        user_id,
        message,
        text
    )

async def continue_learning(message: Message):

    user_id = message.from_user.id

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        # foydalanuvchi sinfi
        cur.execute("""
            SELECT class
            FROM users
            WHERE user_id = %s
        """, (user_id,))

        user = cur.fetchone()

        if not user:
            await message.answer(
                "❌ Avval registratsiyadan o'ting."
            )
            return

        grade = user[0]

        # shu sinfdagi birinchi mavzu
        cur.execute("""
            SELECT
                topic_code,
                subject_name,
                bob_name,
                bolim_name,
                mavzu_name,
                kichik_name
            FROM dts_tree
            WHERE grade = %s
            ORDER BY topic_code
            LIMIT 1
        """, (grade,))

        topic = cur.fetchone()

        cur.execute("""
            SELECT COUNT(*)
            FROM dts_tree
            WHERE grade = %s
        """, (grade,))

        total_topics = cur.fetchone()[0]

        completed_topics = 0

        if not topic:
            await message.answer(
                f"❌ {grade}-sinf uchun mavzu topilmadi."
            )
            return

        topic_code = topic[0]
        subject_name = topic[1]
        bob_name = topic[2]
        bolim_name = topic[3]
        mavzu_name = topic[4]
        kichik_name = topic[5]

        text = f"""
        ☀️ Xush kelibsiz!

        🎓 {grade}-sinf

        ━━━━━━━━━━━━━━

        📚 {subject_name}

        📍 Sizning navbatdagi mavzuingiz:

        📝 {mavzu_name}

        🗣 Kichik mavzu:
        {kichik_name}

        ━━━━━━━━━━━━━━

        📚 Jami mavzular: {total_topics} ta
        📖 Qolgan mavzular: {total_topics - completed_topics} ta

        ━━━━━━━━━━━━━━

        🔥 Bugungi vazifa

        Ushbu mavzuni o'rganing va
        bilim xaritangizdagi navbatdagi
        qadamni oching.

        🏆 Har bir tugatilgan mavzu
        sizni maqsadingizga yaqinlashtiradi.
        """

        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["speak_text"] = text

        await message.answer(
            text,
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [
                        KeyboardButton(text="🔊 O'qib berish")
                    ],
                    [
                        KeyboardButton(text="▶️ O'rganishni boshlash")
                    ],
                    [
                        KeyboardButton(text="📚 Barcha fanlar")
                    ],
                    [
                        KeyboardButton(text="⬅️ Ortga")
                    ]
                ],
                resize_keyboard=True
            )
        )

    except Exception as e:

        await message.answer(
            f"❌ Xatolik:\n{e}"
        )

    finally:

        cur.close()
        conn.close()

async def student_progress(message):
    await message.answer("📈 Rivojlanishim")

async def student_community(message):
    await message.answer("🌍 Hamjamiyat")

async def student_profile(message):
    await message.answer("👤 Kabinet")
