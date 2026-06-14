from keyboards import get_main_keyboard

from aiogram import Router, F
from aiogram.types import Message

import psycopg2
from storage import get_connection
DATABASE_URL = os.getenv("DATABASE_URL")


async def continue_learning(message: Message):

    user_id = message.from_user.id

    conn = get_connection()
    cur = conn.cursor()

    try:

        # foydalanuvchi sinfi
        cur.execute("""
            SELECT class
            FROM users
            WHERE user_id=%s
        """, (user_id,))

        user = cur.fetchone()

        if not user:
            await message.answer(
                "❌ Avval registratsiyadan o'ting."
            )
            return

        grade = user[0]

        # tugallanmagan birinchi mavzu
        cur.execute("""
            SELECT
                d.topic_code,
                d.subject_name,
                d.bob_name,
                d.bolim_name,
                d.mavzu_name,
                d.kichik_name
            FROM dts_tree d

            LEFT JOIN user_topic_progress p
            ON p.topic_code = d.topic_code
            AND p.user_id = %s

            WHERE d.grade = %s
            AND (
                p.status IS NULL
                OR p.status != 'completed'
            )

            ORDER BY d.topic_code
            LIMIT 1
        """, (
            user_id,
            grade
        ))

        topic = cur.fetchone()

        if not topic:

            await message.answer(
                "🎉 Tabriklayman!\n\n"
                "Siz ushbu sinfdagi barcha mavzularni tugatgansiz."
            )
            return

        topic_code = topic[0]
        subject_name = topic[1]
        bob_name = topic[2]
        bolim_name = topic[3]
        mavzu_name = topic[4]
        kichik_name = topic[5]

        await message.answer(
            f"📚 Fan: {subject_name}\n\n"
            f"📖 Bob:\n{bob_name}\n\n"
            f"📘 Bo'lim:\n{bolim_name}\n\n"
            f"📝 Mavzu:\n{mavzu_name}\n\n"
            f"📌 Kichik mavzu:\n{kichik_name}\n\n"
            f"🔑 Kod: {topic_code}\n\n"
            f"▶️ O'rganishni boshlash"
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
