from keyboards import get_main_keyboard
from aiogram import Router, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)
import os
from pydub import AudioSegment
import psycopg2
import edge_tts
from aiogram.types import FSInputFile
import tempfile
from test_engine import speak_text
from storage import user_state
from teacher_engine import (
    build_lesson_steps,
    get_step_content
)
from teacher_engine import (
    create_lesson_state,
    current_text,
    build_board_text
)
from teacher_engine import (
    parse_content,
    render_content,
    build_ssml
)
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

DATABASE_URL = os.getenv("DATABASE_URL")

async def speak_mixed_text(
    user_id,
    message,
    text
):

    blocks = parse_content(text)

    voices = {
        "text": "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural",
        "ru": "ru-RU-DmitryNeural"
    }

    audio_files = []

    for i, block in enumerate(blocks):

        lang = block["type"]

        if lang == "text":
            voice = voices["text"]
        else:
            voice = voices.get(
                lang,
                voices["text"]
            )

        filename = f"part_{user_id}_{i}.mp3"

        content = str(block["content"]).strip()

        if not content:
            continue

        if not any(ch.isalnum() for ch in content):
            continue

        communicate = edge_tts.Communicate(
            text=content,
            voice=voice
        )

        try:

            await communicate.save(filename)

            # fayl mavjud va bo'sh emasligini tekshir
            if (
                os.path.exists(filename)
                and os.path.getsize(filename) > 0
            ):
                audio_files.append(filename)
            else:
                continue

        except:
            continue

    if not audio_files:
        await message.answer("🔇 Audio yaratib bo'lmadi")
        return

    try:

        combined = AudioSegment.empty()

        for file in audio_files:
            segment = AudioSegment.from_file(file, format="mp3")
            combined += segment

        final_file = f"mixed_{user_id}.mp3"

        combined.export(final_file, format="mp3")

        if (
            user_id in user_state
            and "voice_message_id" in user_state[user_id]
        ):
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=user_state[user_id]["voice_message_id"]
                )
            except:
                pass

        voice_msg = await message.answer_voice(
            FSInputFile(final_file)
        )

        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["voice_message_id"] = voice_msg.message_id

    except Exception as e:
        await message.answer(f"❌ Audio xatolik: {e}")

    finally:

        for file in audio_files:
            try:
                os.remove(file)
            except:
                pass

        try:
            os.remove(final_file)
        except:
            pass

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

async def open_teacher_lesson(message):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        topic_code = "TEST_001"

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:

            await message.answer(
                "❌ Dars topilmadi"
            )
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        user_id = message.from_user.id

        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["lesson"] = lesson
        user_state[user_id]["parts"] = parts
        user_state[user_id]["current_step"] = 0

        cur.execute("""
            DELETE FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        cur.execute("""
            INSERT INTO lesson_progress
            (
                user_id,
                topic_code,
                current_step,
                completed
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """, (
            user_id,
            topic_code,
            0,
            False
        ))

        conn.commit()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data="lesson_prev"
                    ),
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data="lesson_next"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔊 O'qib ber",
                        callback_data="lesson_tts"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="😕 Tushunmadim",
                        callback_data="lesson_help"
                    ),
                    InlineKeyboardButton(
                        text="❌ Darsni tugatish",
                        callback_data="lesson_finish"
                    )
                ]
            ]
        )
        msg = await message.answer(
    f"""
👨‍🏫 USTOZ DOSKASI

📚 {topic_code}

━━━━━━━━━━━━━━

{build_board_text(parts[0]) or render_content(parts[0])}
""",

            reply_markup=keyboard
        )

        user_state[user_id]["board_message_id"] = (
            msg.message_id
        )

    except Exception as e:

        await message.answer(
            f"❌ Xatolik:\n{e}"
        )

    finally:

        cur.close()
        conn.close()

async def lesson_next(user_id, message):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["help_mode"] = True

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()

        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        next_step = current_step + 1

        if next_step >= len(parts):

            await message.edit_text(
                "🏆 Dars yakunlandi"
            )

            return

        cur.execute("""
            UPDATE lesson_progress
            SET current_step = %s
            WHERE user_id = %s
        """, (
            next_step,
            user_id
        ))

        conn.commit()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data="lesson_prev"
                    ),
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data="lesson_next"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔊 O'qib ber",
                        callback_data="lesson_tts"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="😕 Tushunmadim",
                        callback_data="lesson_help"
                    ),
                    InlineKeyboardButton(
                        text="❌ Darsni tugatish",
                        callback_data="lesson_finish"
                    )
                ]
            ]
        )
        await message.edit_text(
            f"""
👨‍🏫 USTOZ DOSKASI

📚 {topic_code}  |  {next_step + 1}/{len(parts)} qadam

━━━━━━━━━━━━━━

{build_board_text(parts[next_step]) or render_content(parts[next_step])}
""",
            reply_markup=keyboard
        )

    finally:

        cur.close()
        conn.close()

async def lesson_tts(user_id, message):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()

        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        # 🔊 bosilsa — asosiy matnni o'qiydi
        text = parts[current_step]

        await speak_mixed_text(
            user_id,
            message,
            text
        )

    except Exception as e:

        import traceback
        await message.answer(traceback.format_exc())

    finally:

        cur.close()
        conn.close()

async def lesson_prev(user_id, message):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        if user_id in user_state:
            user_state[user_id]["help_mode"] = False

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()

        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        prev_step = current_step - 1

        if prev_step < 0:
            prev_step = 0

        cur.execute("""
            UPDATE lesson_progress
            SET current_step = %s
            WHERE user_id = %s
        """, (
            prev_step,
            user_id
        ))

        conn.commit()

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data="lesson_prev"
                    ),
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data="lesson_next"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔊 O'qib ber",
                        callback_data="lesson_tts"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="😕 Tushunmadim",
                        callback_data="lesson_help"
                    ),
                    InlineKeyboardButton(
                        text="❌ Darsni tugatish",
                        callback_data="lesson_finish"
                    )
                ]
            ]
        )

        await message.edit_text(
            f"""
👨‍🏫 USTOZ DOSKASI

📚 {topic_code}  |  {prev_step + 1}/{len(parts)} qadam

━━━━━━━━━━━━━━

{build_board_text(parts[prev_step]) or render_content(parts[prev_step])}
""",
            reply_markup=keyboard
        )

    finally:

        cur.close()
        conn.close()

async def lesson_help(
    user_id,
    message
):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()

        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        # izoh matni (simple_1..4)
        simple_map = {
            1: lesson[7] or "",
            2: lesson[8] or "",
            3: lesson[9] or "",
            4: lesson[10] or ""
        }

        simple_text = simple_map.get(current_step, "")
        main_text = parts[current_step]

        if not simple_text:
            simple_text = "Bu bosqich uchun izoh yo'q"

        # izoh doskada ko'rinadi + 🔊 bosilsa ovoz chiqadi
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data="lesson_prev"
                    ),
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data="lesson_next"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔊 Izohni o'qi",
                        callback_data="lesson_tts_help"
                    ),
                    InlineKeyboardButton(
                        text="🔙 Darsga qayt",
                        callback_data="lesson_back_main"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Darsni tugatish",
                        callback_data="lesson_finish"
                    )
                ]
            ]
        )

        await message.edit_text(
            f"👨‍🏫 USTOZ DOSKASI\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"💡 Izoh:\n\n"
            f"{render_content(simple_text)}\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"📖 Asosiy matn:\n\n"
            f"{build_board_text(main_text) or render_content(main_text)}",
            reply_markup=keyboard
        )

    except Exception as e:

        await message.answer(f"❌ Xatolik:\n{e}")

    finally:

        cur.close()
        conn.close()

async def lesson_tts_help(user_id, message):
    """🔊 Izohni o'qi bosilganda — izoh matnini ovozda o'qiydi"""

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()
        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()
        if not lesson:
            return

        simple_map = {
            1: lesson[7] or "",
            2: lesson[8] or "",
            3: lesson[9] or "",
            4: lesson[10] or ""
        }

        simple_text = simple_map.get(current_step, "")

        if not simple_text:
            simple_text = "Bu bosqich uchun izoh yo'q"

        await speak_mixed_text(user_id, message, simple_text)

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()


async def lesson_back_main(user_id, message):
    """🔙 Darsga qayt — asosiy dars matni qaytadi"""

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()
        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()
        if not lesson:
            return

        parts = [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ]

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️",
                        callback_data="lesson_prev"
                    ),
                    InlineKeyboardButton(
                        text="➡️",
                        callback_data="lesson_next"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔊 O'qib ber",
                        callback_data="lesson_tts"
                    ),
                    InlineKeyboardButton(
                        text="😕 Tushunmadim",
                        callback_data="lesson_help"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Darsni tugatish",
                        callback_data="lesson_finish"
                    )
                ]
            ]
        )

        await message.edit_text(
            f"👨‍🏫 USTOZ DOSKASI\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{build_board_text(parts[current_step]) or render_content(parts[current_step])}",
            reply_markup=keyboard
        )

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()




    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT topic_code, current_step
            FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        progress = cur.fetchone()

        if not progress:
            return

        topic_code = progress[0]
        current_step = progress[1]

        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            return

        simple_map = {
            1: lesson[7] or "",
            2: lesson[8] or "",
            3: lesson[9] or "",
            4: lesson[10] or ""
        }

        simple_text = simple_map.get(
            current_step,
            ""
        )

        if not simple_text:
            await message.answer("💡 Bu bosqich uchun izoh yo'q")
            return

        await speak_mixed_text(user_id, message, simple_text)

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()


async def lesson_finish(
    user_id,
    message
):

    if user_id in user_state:

        user_state.pop(user_id)

    conn = psycopg2.connect(
        DATABASE_URL
    )

    cur = conn.cursor()

    try:

        cur.execute("""
            DELETE FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        conn.commit()

        await message.edit_text(
            """
🏁 Dars yakunlandi

Rahmat.
"""
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
