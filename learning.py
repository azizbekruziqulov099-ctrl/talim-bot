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
from latex_utils import (
    parse_blocks,
    send_blocks,
    latex_to_image,
    latex_to_voice
)

DATABASE_URL = os.getenv("DATABASE_URL")

async def speak_mixed_text(
    user_id,
    message,
    text
):
    """
    Matn ichidagi barcha bloklarni qayta ishlaydi:
    - [latex]...[/latex] → rasm + ovoz
    - [img]...[/img]     → photo
    - [en]...[/en]       → ingliz ovoz
    - [ru]...[/ru]       → rus ovoz
    - oddiy matn         → o'zbek ovoz
    """

    blocks = parse_blocks(text)

    voices = {
        "text": "uz-UZ-SardorNeural",
        "en":   "en-US-GuyNeural",
        "ru":   "ru-RU-DmitryNeural"
    }

    audio_files = []

    for i, block in enumerate(blocks):

        btype   = block["type"]
        content = str(block["content"]).strip()

        if not content:
            continue

        # LaTeX blok — rasm + ovoz alohida
        if btype == "latex":

            # Rasm
            try:
                img_path = latex_to_image(content, user_id)
                await message.answer_photo(
                    FSInputFile(img_path),
                    caption=f"📐 `{content}`",
                    parse_mode="Markdown"
                )
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception:
                await message.answer(
                    f"📐 `{content}`",
                    parse_mode="Markdown"
                )

            # Ovoz
            try:
                voice_path, uzbek = await latex_to_voice(content, user_id)
                if (
                    os.path.exists(voice_path)
                    and os.path.getsize(voice_path) > 0
                ):
                    audio_files.append(voice_path)
            except Exception:
                pass

            continue

        # Rasm blok
        if btype == "img":
            try:
                await message.answer_photo(content)
            except Exception:
                pass
            continue

        # Matn / en / ru — ovoz faylga
        voice = voices.get(btype, voices["text"])
        filename = f"part_{user_id}_{i}.mp3"

        if not any(ch.isalnum() for ch in content):
            continue

        communicate = edge_tts.Communicate(
            text=content,
            voice=voice
        )

        try:
            await communicate.save(filename)
            if (
                os.path.exists(filename)
                and os.path.getsize(filename) > 0
            ):
                audio_files.append(filename)
        except Exception:
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
            except Exception:
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
            except Exception:
                pass
        try:
            os.remove(final_file)
        except Exception:
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
        user_id = message.from_user.id

        # O'quvchi ma'lumotlari
        cur.execute("""
            SELECT full_name, class, subject
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        user_info = cur.fetchone()

        full_name = user_info[0] if user_info else "O'quvchi"
        sinf      = user_info[1] if user_info else ""
        fan       = user_info[2] if user_info else ""

        # Dars matni
        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            await message.answer("❌ Dars topilmadi")
            return

        # Mavzu nomi dts_tree dan
        cur.execute("""
            SELECT small_topic
            FROM dts_tree
            WHERE topic_code = %s
            LIMIT 1
        """, (topic_code,))
        topic_row = cur.fetchone()
        mavzu = topic_row[0] if topic_row else topic_code

        parts = [p for p in [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ] if p.strip()]

        from datetime import date
        bugun = date.today().strftime("%d.%m.%Y")

        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["lesson"]       = lesson
        user_state[user_id]["parts"]        = parts
        user_state[user_id]["current_step"] = 0
        user_state[user_id]["topic_code"]   = topic_code
        user_state[user_id]["full_name"]    = full_name
        user_state[user_id]["sinf"]         = sinf
        user_state[user_id]["fan"]          = fan
        user_state[user_id]["mavzu"]        = mavzu
        user_state[user_id]["bugun"]        = bugun

        cur.execute("""
            DELETE FROM lesson_progress WHERE user_id = %s
        """, (user_id,))

        cur.execute("""
            INSERT INTO lesson_progress
            (user_id, topic_code, current_step, completed)
            VALUES (%s, %s, %s, %s)
        """, (user_id, topic_code, 0, False))

        conn.commit()

        # ── BOSHIDA TAKRORLASH ──
        # Oxirgi o'rganilgan mavzudan savol bormi?
        cur.execute("""
            SELECT topic_code, mavzu
            FROM lesson_history
            WHERE user_id = %s
            ORDER BY learned_at DESC
            LIMIT 1
        """, (user_id,))

        last = cur.fetchone()

        if last:
            last_topic_code = last[0]
            last_mavzu      = last[1]

            cur.execute("""
                SELECT question, option_a, option_b,
                       option_c, option_d, correct_answer,
                       explanation
                FROM dts_tree
                WHERE topic_code = %s
                  AND question IS NOT NULL
                  AND option_a IS NOT NULL
                ORDER BY RANDOM()
                LIMIT 3
            """, (last_topic_code,))

            review_qs = cur.fetchall()

            if review_qs:
                # Takrorlash testini boshlaylik
                user_state[user_id]["review_questions"] = review_qs
                user_state[user_id]["review_index"]     = 0
                user_state[user_id]["review_correct"]   = 0
                user_state[user_id]["after_review"]     = "start_lesson"

                await message.answer(
                    f"🔁 Avval kechagi mavzuni eslab olaylik!\n\n"
                    f"📘 {last_mavzu}\n\n"
                    f"3 ta savol — tez javob bering! 💨",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(
                                text="▶️ Boshlash",
                                callback_data="review_start"
                            ),
                            InlineKeyboardButton(
                                text="⏭ O'tkazish",
                                callback_data="review_skip"
                            )
                        ]]
                    )
                )
                return

        # Takrorlash yo'q — darsni boshlash
        await start_main_lesson(message, user_id, parts, full_name, sinf, fan, mavzu, bugun)

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()


async def start_main_lesson(message, user_id, parts, full_name, sinf, fan, mavzu, bugun):
    """Asosiy darsni ko'rsatadi"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️", callback_data="lesson_prev"),
                InlineKeyboardButton(text="➡️", callback_data="lesson_next")
            ],
            [
                InlineKeyboardButton(text="🔊 O'qib ber", callback_data="lesson_tts"),
                InlineKeyboardButton(text="😕 Tushunmadim", callback_data="lesson_help")
            ],
            [
                InlineKeyboardButton(text="❌ Darsni tugatish", callback_data="lesson_finish")
            ]
        ]
    )

    msg = await message.answer(
        f"👤 {full_name} | {sinf}\n"
        f"📘 {fan} • {mavzu} • {bugun}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{build_board_text(parts[0]) or render_content(parts[0])}\n\n"
        f"📄 1/{len(parts)} qadam",
        reply_markup=keyboard
    )

    user_state[user_id]["board_message_id"] = msg.message_id


async def lesson_review_start(user_id, message):
    """Takrorlash testini boshlaydi"""

    questions = user_state.get(user_id, {}).get("review_questions", [])
    await send_review_question(user_id, message, questions, 0)


async def send_review_question(user_id, message, questions, index):
    """Takrorlash savolini yuboradi"""

    if index >= len(questions):
        # Takrorlash tugadi — darsni boshlash
        correct = user_state.get(user_id, {}).get("review_correct", 0)
        total   = len(questions)

        emoji = "🔥" if correct == total else "👍" if correct >= total // 2 else "💪"

        parts     = user_state.get(user_id, {}).get("parts", [])
        full_name = user_state.get(user_id, {}).get("full_name", "O'quvchi")
        sinf      = user_state.get(user_id, {}).get("sinf", "")
        fan       = user_state.get(user_id, {}).get("fan", "")
        mavzu     = user_state.get(user_id, {}).get("mavzu", "")
        bugun     = user_state.get(user_id, {}).get("bugun", "")

        await message.answer(
            f"{emoji} Takrorlash: {correct}/{total}\n\n"
            f"Endi yangi darsni boshlaymiz! 📖"
        )

        await start_main_lesson(
            message, user_id, parts,
            full_name, sinf, fan, mavzu, bugun
        )
        return

    q = questions[index]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"A) {q[1]}", callback_data="review_answer_A")],
            [InlineKeyboardButton(text=f"B) {q[2]}", callback_data="review_answer_B")],
            [InlineKeyboardButton(text=f"C) {q[3]}", callback_data="review_answer_C")],
            [InlineKeyboardButton(text=f"D) {q[4]}", callback_data="review_answer_D")]
        ]
    )

    await message.answer(
        f"🔁 Takrorlash | {index + 1}/{len(questions)}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"❓ {q[0]}",
        reply_markup=keyboard
    )


async def lesson_review_answer(user_id, message, answer):
    """Takrorlash javobini tekshiradi"""

    questions = user_state.get(user_id, {}).get("review_questions", [])
    index     = user_state.get(user_id, {}).get("review_index", 0)

    if not questions or index >= len(questions):
        return

    q          = questions[index]
    correct    = q[5]
    explanation = q[6] or ""

    is_correct = answer.upper() == correct.upper()

    if is_correct:
        user_state[user_id]["review_correct"] = (
            user_state[user_id].get("review_correct", 0) + 1
        )
        result = "✅ To'g'ri!"
    else:
        result = f"❌ Noto'g'ri! To'g'ri: {correct}"

    if explanation:
        result += f"\n💡 {explanation}"

    next_index = index + 1
    user_state[user_id]["review_index"] = next_index

    await message.answer(
        result,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="➡️ Keyingi",
                    callback_data="review_next"
                )
            ]]
        )
    )


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

        parts = [p for p in [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ] if p.strip()]

        next_step = current_step + 1

        if next_step >= len(parts):

            # Dars tugadi — mustahkamlash testiga o'tish
            await message.edit_text(
                f"🎉 Dars tugadi!\n\n"
                f"📘 {user_state.get(user_id, {}).get('mavzu', topic_code)}\n\n"
                f"Bilimingizni mustahkamlash uchun\n"
                f"5 ta savol javob bering! 🧠",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="▶️ Testni boshlash",
                            callback_data="lesson_consolidation_test"
                        ),
                        InlineKeyboardButton(
                            text="⏭ O'tkazib yuborish",
                            callback_data="lesson_finish"
                        )
                    ]]
                )
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
👤 {user_state.get(user_id, {}).get('full_name', 'O\'quvchi')} | {user_state.get(user_id, {}).get('sinf', '')}
📘 {user_state.get(user_id, {}).get('fan', '')} • {user_state.get(user_id, {}).get('mavzu', topic_code)} • {user_state.get(user_id, {}).get('bugun', '')}
━━━━━━━━━━━━━━

{build_board_text(parts[next_step]) or render_content(parts[next_step])}

📄 {next_step + 1}/{len(parts)} qadam
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
👤 {user_state.get(user_id, {}).get('full_name', 'O\'quvchi')} | {user_state.get(user_id, {}).get('sinf', '')}
📘 {user_state.get(user_id, {}).get('fan', '')} • {user_state.get(user_id, {}).get('mavzu', topic_code)} • {user_state.get(user_id, {}).get('bugun', '')}
━━━━━━━━━━━━━━

{build_board_text(parts[prev_step]) or render_content(parts[prev_step])}

📄 {prev_step + 1}/{len(parts)} qadam
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


async def lesson_consolidation_test(user_id, message):
    """Dars tugagach mustahkamlash testi — 5 savol"""

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        topic_code = user_state.get(user_id, {}).get("topic_code", "TEST_001")

        # dts_tree dan o'sha mavzu topic_code lari
        cur.execute("""
            SELECT topic_code
            FROM dts_tree
            WHERE topic_code LIKE %s
            LIMIT 20
        """, (topic_code[:10] + "%",))

        topic_codes = [r[0] for r in cur.fetchall()]

        if not topic_codes:
            topic_codes = [topic_code]

        # Savollar
        cur.execute("""
            SELECT question, option_a, option_b, 
                   option_c, option_d, correct_answer,
                   explanation, question_type
            FROM dts_tree
            WHERE topic_code = ANY(%s)
              AND question IS NOT NULL
              AND option_a IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 5
        """, (topic_codes,))

        questions = cur.fetchall()

        if not questions:
            # lesson_history ga saqlash
            try:
                cur.execute("""
                    INSERT INTO lesson_history
                    (user_id, topic_code, mavzu, fan, score, total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    topic_code,
                    user_state.get(user_id, {}).get("mavzu", ""),
                    user_state.get(user_id, {}).get("fan", ""),
                    0, 0
                ))
                conn.commit()
            except Exception:
                pass

            await message.edit_text(
                f"✅ Dars muvaffaqiyatli tugallandi!\n\n"
                f"📘 {user_state.get(user_id, {}).get('mavzu', topic_code)}\n\n"
                f"⚠️ Bu mavzu bo'yicha testlar hali qo'shilmagan.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(
                            text="🏠 Bosh menyu",
                            callback_data="lesson_finish"
                        )
                    ]]
                )
            )
            return

        # Testni user_state ga saqlaymiz
        if user_id not in user_state:
            user_state[user_id] = {}

        user_state[user_id]["test_questions"] = questions
        user_state[user_id]["test_index"]     = 0
        user_state[user_id]["test_correct"]   = 0
        user_state[user_id]["test_mode"]      = "consolidation"

        await send_test_question(user_id, message, questions, 0)

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()


async def send_test_question(user_id, message, questions, index):
    """Bitta test savolini yuboradi"""

    if index >= len(questions):
        correct = user_state.get(user_id, {}).get("test_correct", 0)
        total   = len(questions)
        pct     = int(correct / total * 100)

        emoji = "🏆" if pct >= 80 else "👍" if pct >= 60 else "💪"

        # lesson_history ga saqlash
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur  = conn.cursor()
            topic_code = user_state.get(user_id, {}).get("topic_code", "")
            cur.execute("""
                INSERT INTO lesson_history
                (user_id, topic_code, mavzu, fan, score, total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                topic_code,
                user_state.get(user_id, {}).get("mavzu", ""),
                user_state.get(user_id, {}).get("fan", ""),
                correct,
                total
            ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass

        await message.edit_text(
            f"{emoji} Test yakunlandi!\n\n"
            f"✅ To'g'ri: {correct}/{total} ({pct}%)\n\n"
            f"{'Zo\'r natija! Davom eting! 🚀' if pct >= 80 else 'Yaxshi urindi! Yana mashq qiling! 💡' if pct >= 60 else 'Mavzuni qayta ko\'rib chiqing! 📖'}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🏠 Bosh menyu",
                        callback_data="lesson_finish"
                    )
                ]]
            )
        )
        return

    q = questions[index]
    question   = q[0]
    option_a   = q[1]
    option_b   = q[2]
    option_c   = q[3]
    option_d   = q[4]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"A) {option_a}",
                callback_data=f"test_answer_A"
            )],
            [InlineKeyboardButton(
                text=f"B) {option_b}",
                callback_data=f"test_answer_B"
            )],
            [InlineKeyboardButton(
                text=f"C) {option_c}",
                callback_data=f"test_answer_C"
            )],
            [InlineKeyboardButton(
                text=f"D) {option_d}",
                callback_data=f"test_answer_D"
            )]
        ]
    )

    await message.edit_text(
        f"🧠 Mustahkamlash testi\n"
        f"━━━━━━━━━━━━━━\n"
        f"❓ {index + 1}/{len(questions)}\n\n"
        f"{question}",
        reply_markup=keyboard
    )


async def lesson_test_answer(user_id, message, answer):
    """Test javobini tekshiradi"""

    questions = user_state.get(user_id, {}).get("test_questions", [])
    index     = user_state.get(user_id, {}).get("test_index", 0)

    if not questions or index >= len(questions):
        return

    q             = questions[index]
    correct       = q[5]
    explanation   = q[6] or ""

    is_correct = answer.upper() == correct.upper()

    if is_correct:
        user_state[user_id]["test_correct"] = (
            user_state[user_id].get("test_correct", 0) + 1
        )
        result_text = "✅ To'g'ri!"
    else:
        result_text = f"❌ Noto'g'ri! To'g'ri javob: {correct}"

    if explanation:
        result_text += f"\n\n💡 {explanation}"

    next_index = index + 1
    user_state[user_id]["test_index"] = next_index

    await message.edit_text(
        f"🧠 Mustahkamlash testi\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{result_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="➡️ Keyingi savol",
                    callback_data="test_next_question"
                )
            ]]
        )
    )


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
