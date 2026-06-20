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

async def clean_for_tts(text: str) -> str:
    """Matnni TTS uchun tozalaydi — faqat ovoz uchun"""
    import re

    # Teglarni olib tashlash
    text = re.sub(r'\[/?en\]|\[/?ru\]|\[/?latex\]|\[/?img\]|\[/?skip\]', '', text)

    # Emoji olib tashlash (ovozda o'qilmasin)
    text = re.sub(
        r'[\U0001F000-\U0001FFFF'
        r'\U00002600-\U000027BF'
        r'\U0001F900-\U0001F9FF'
        r'\U00002300-\U000023FF]+',
        ' ', text, flags=re.UNICODE
    )

    # Maxsus belgilar
    text = re.sub(r'[•\*\#\|\_\~\`]', ' ', text)
    text = re.sub(r'━+|-{3,}=+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('—', ',').strip()

    return text


async def speak_mixed_text(user_id, message, text):
    """Matn ichidagi barcha bloklarni qayta ishlaydi"""

    # Foydalanuvchi jinsi bo'yicha ovoz tanlash
    try:
        conn_v = psycopg2.connect(DATABASE_URL)
        cur_v  = conn_v.cursor()
        cur_v.execute("SELECT gender FROM users WHERE user_id=%s", (user_id,))
        g_row  = cur_v.fetchone()
        cur_v.close(); conn_v.close()
        gender = g_row[0] if g_row else ""
    except Exception:
        gender = ""

    uz_voice = "uz-UZ-MadinaNeural" if "Ayol" in str(gender) else "uz-UZ-SardorNeural"

    blocks = parse_blocks(text)

    voices = {
        "text": uz_voice,
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

        # Skip blok — ovozda o'qilmaydi, faqat ekranda ko'rinadi
        if btype == "skip":
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

        # Matnni TTS uchun tozala
        clean_content = await clean_for_tts(content)

        if not clean_content or not any(ch.isalnum() for ch in clean_content):
            continue

        communicate = edge_tts.Communicate(
            text=clean_content,
            voice=voice,
            rate="+0%",
            pitch="+0Hz"
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
    cur  = conn.cursor()

    try:

        cur.execute("""
            SELECT full_name, class FROM users
            WHERE user_id = %s
        """, (user_id,))
        user = cur.fetchone()

        if not user:
            await message.answer("❌ Avval registratsiyadan o'ting.")
            return

        full_name = user[0] or "O'quvchi"
        grade     = user[1] or "1"
        name      = full_name.split()[0]

        # Fanlar ro'yxati
        cur.execute("""
            SELECT DISTINCT subject_name
            FROM dts_tree
            WHERE grade = %s AND is_deleted = FALSE
            ORDER BY subject_name
        """, (grade,))
        subjects = [r[0] for r in cur.fetchall()]

        # Har fan uchun progress
        buttons = []
        fan_info = []

        for subj in subjects:
            cur.execute("""
                SELECT COUNT(*) FROM dts_tree
                WHERE grade=%s AND subject_name=%s AND is_deleted=FALSE
            """, (grade, subj))
            total = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM learned_topics lt
                JOIN dts_tree t ON t.topic_code = lt.topic_code
                WHERE lt.user_id=%s AND t.grade=%s AND t.subject_name=%s
            """, (user_id, grade, subj))
            learned = cur.fetchone()[0]

            pct = int(learned * 100 / total) if total else 0
            bar = "█" * (pct // 20) + "░" * (5 - pct // 20)

            icon = "✅" if pct == 100 else "📖" if pct > 0 else "🔒"
            buttons.append([InlineKeyboardButton(
                text=f"{icon} {subj} {bar} {pct}%",
                callback_data=f"fan_select|{grade}|{subj}"
            )])
            fan_info.append((subj, learned, total, pct))

        # Keyingi o'rganilmagan mavzu
        from progress import get_next_topic, get_repeat_topics
        next_topic = get_next_topic(user_id, grade)
        repeats    = get_repeat_topics(user_id)

        text = f"☀️ Salom, {name}!\n━━━━━━━━━━━━━━\n"

        if repeats:
            text += f"🔁 {len(repeats)} ta mavzu takrorlash kutmoqda!\n"

        if next_topic:
            text += (
                f"\n🎯 Keyingi mavzu:\n"
                f"📚 {next_topic[3]}\n"
                f"📝 {next_topic[2]}\n"
                f"🔑 {next_topic[1]}"
            )

        buttons.append([InlineKeyboardButton(
            text="▶️ Davom etish",
            callback_data="lesson_continue"
        )])
        buttons.append([InlineKeyboardButton(
            text="🔁 Takrorlash",
            callback_data="lesson_repeat"
        )])

        from aiogram.types import ReplyKeyboardRemove
        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()



async def open_teacher_lesson(message, topic_code=None, _user_id=None):

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    try:

        user_id = _user_id or message.from_user.id

        # O'quvchi ma'lumotlari
        cur.execute("""
            SELECT full_name, class, subject
            FROM users WHERE user_id = %s
        """, (user_id,))
        user_info = cur.fetchone()

        full_name = user_info[0] if user_info else "O'quvchi"
        sinf      = user_info[1] if user_info else "1"
        fan       = user_info[2] if user_info else ""

        # topic_code berilmagan bo'lsa — keyingi o'rganilmagan mavzuni top
        if not topic_code:
            from progress import get_next_topic
            next_row = get_next_topic(user_id, sinf)
            if next_row:
                topic_code = next_row[0]
            else:
                await message.answer(
                    "🎉 Barcha mavzularni o'rgandingiz!\n"
                    "Takrorlash uchun navigator dan foydalaning."
                )
                return

        # Dars matni
        cur.execute("""
            SELECT *
            FROM teacher_lessons
            WHERE topic_code = %s
        """, (topic_code,))

        lesson = cur.fetchone()

        if not lesson:
            await message.answer(
                f"📝 Bu mavzu uchun dars hali yozilmagan\n\n"
                f"🔑 {topic_code}\n\n"
                f"Admin tez orada qo'shadi! ⏳"
            )
            return

        # Mavzu nomi dts_tree dan
        cur.execute("""
            SELECT grade, subject_name, mavzu_name, kichik_name
            FROM dts_tree
            WHERE topic_code = %s
            LIMIT 1
        """, (topic_code,))
        topic_row = cur.fetchone()
        if topic_row:
            sinf_db = topic_row[0] or sinf
            fan_db  = topic_row[1] or fan
            mavzu   = topic_row[2] or topic_code
            sinf    = sinf_db
            fan     = fan_db
        else:
            mavzu = topic_code

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
                FROM generated_tests
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

    from aiogram.types import ReplyKeyboardRemove

    # Klaviaturani yashir
    await message.answer("📖 Dars boshlanmoqda...", reply_markup=ReplyKeyboardRemove())

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
        u = user_state.get(user_id, {})
        fn   = u.get('full_name', "O'quvchi") if isinstance(u, dict) else "O'quvchi"
        sinf = u.get('sinf', '') if isinstance(u, dict) else ''
        fan  = u.get('fan', '') if isinstance(u, dict) else ''
        mav  = u.get('mavzu', topic_code) if isinstance(u, dict) else topic_code
        bgun = u.get('bugun', '') if isinstance(u, dict) else ''

        await message.edit_text(
            f"👤 {fn} | {sinf}\n"
            f"📘 {fan} • {mav} • {bgun}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{build_board_text(parts[next_step]) or render_content(parts[next_step])}\n\n"
            f"📄 {next_step + 1}/{len(parts)} qadam",
            reply_markup=keyboard
        )

    except Exception as e:
        import traceback
        print(f"lesson_next ERROR: {traceback.format_exc()}")
        try:
            await message.answer(f"❌ Xatolik: {e}")
        except Exception:
            pass

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

        parts = [p for p in [
            lesson[2] or "",
            lesson[3] or "",
            lesson[4] or "",
            lesson[5] or "",
            lesson[6] or "",
            lesson[13] or ""
        ] if p.strip()]

        # 🔊 bosilsa — faqat shu qadamdagi asosiy matnni o'qiydi
        if current_step < len(parts):
            text = parts[current_step]
        else:
            text = parts[-1] if parts else ""

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

        u = user_state.get(user_id, {})
        fn   = u.get('full_name', "O'quvchi") if isinstance(u, dict) else "O'quvchi"
        sinf = u.get('sinf', '') if isinstance(u, dict) else ''
        fan  = u.get('fan', '') if isinstance(u, dict) else ''
        mav  = u.get('mavzu', topic_code) if isinstance(u, dict) else topic_code
        bgun = u.get('bugun', '') if isinstance(u, dict) else ''

        await message.edit_text(
            f"👤 {fn} | {sinf}\n"
            f"📘 {fan} • {mav} • {bgun}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{build_board_text(parts[prev_step]) or render_content(parts[prev_step])}\n\n"
            f"📄 {prev_step + 1}/{len(parts)} qadam",
            reply_markup=keyboard
        )

    except Exception as e:
        import traceback
        print(f"lesson_prev ERROR: {traceback.format_exc()}")
        try:
            await message.answer(
                f"👤 {fn} | {sinf}\n"
                f"📘 {fan} • {mav} • {bgun}\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"{build_board_text(parts[prev_step]) or render_content(parts[prev_step])}\n\n"
                f"📄 {prev_step + 1}/{len(parts)} qadam",
                reply_markup=keyboard
            )
        except Exception as e2:
            print(f"lesson_prev answer ERROR: {e2}")

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
            1: str(lesson[7] or ""),
            2: str(lesson[8] or ""),
            3: str(lesson[14] if len(lesson) > 14 and lesson[14] else (lesson[9] or "")),
            4: str(lesson[15] if len(lesson) > 15 and lesson[15] else (lesson[10] or ""))
        }

        simple_text = simple_map.get(current_step, "")
        if simple_text in ("None", "none"):
            simple_text = ""
        main_text = str(parts[current_step])

        u    = user_state.get(user_id, {}) if isinstance(user_state.get(user_id), dict) else {}
        fn   = u.get("full_name", "O'quvchi")
        sinf = u.get("sinf", "")
        fan  = u.get("fan", "")
        mav  = u.get("mavzu", topic_code)
        bgun = u.get("bugun", "")

        izoh = simple_text if simple_text else "Bu bosqich uchun izoh yo'q"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="⬅️", callback_data="lesson_prev"),
                    InlineKeyboardButton(text="➡️", callback_data="lesson_next")
                ],
                [
                    InlineKeyboardButton(text="🔊 Izohni o'qi", callback_data="lesson_tts_help"),
                    InlineKeyboardButton(text="🔙 Darsga qayt", callback_data="lesson_back_main")
                ],
                [
                    InlineKeyboardButton(text="❌ Darsni tugatish", callback_data="lesson_finish")
                ]
            ]
        )

        await message.edit_text(
            f"👤 {fn} | {sinf}\n"
            f"📘 {fan} • {mav} • {bgun}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{render_content(main_text)}\n\n"
            f"━━━━━━━━━━━━━━\n"
            f"💡 Izoh:\n\n"
            f"{render_content(izoh)}",
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
            1: str(lesson[7] or ""),
            2: str(lesson[8] or ""),
            3: str(lesson[14] if len(lesson) > 14 and lesson[14] else (lesson[9] or "")),
            4: str(lesson[15] if len(lesson) > 15 and lesson[15] else (lesson[10] or ""))
        }

        simple_text = simple_map.get(current_step, "")
        if simple_text in ("None", "none"):
            simple_text = ""

        if not simple_text:
            await speak_mixed_text(user_id, message, "Bu bosqich uchun izoh yo'q")
            return

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

        # Faqat tugmalarni asliga qaytaradi — ovoz yuklamaydi
        try:
            await message.edit_reply_markup(reply_markup=keyboard)
        except Exception:
            pass

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

        # generated_tests dan mavzu topic_code lari
        cur.execute("""
            SELECT DISTINCT topic_code
            FROM generated_tests
            WHERE topic_code LIKE %s
            LIMIT 20
        """, (topic_code[:10] + "%",))

        topic_codes = [r[0] for r in cur.fetchall()]

        if not topic_codes:
            topic_codes = [topic_code]

        # generated_tests dan savollar
        cur.execute("""
            SELECT question, option_a, option_b,
                   option_c, option_d, correct_answer,
                   explanation, question_type, image_url
            FROM generated_tests
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

        msg = "Zo'r natija! Davom eting! 🚀" if pct >= 80 else "Yaxshi urindi! Yana mashq qiling! 💡" if pct >= 60 else "Mavzuni qayta ko'rib chiqing! 📖"

        # XP qo'shish
        from progress import add_xp, update_streak, mark_learned, get_progress
        xp_reason = "test_100" if pct == 100 else "test_80" if pct >= 80 else "test_60" if pct >= 60 else "lesson"
        xp_earned = add_xp(user_id, xp_reason)
        streak    = update_streak(user_id)

        # Mavzuni o'rganilgan deb belgilash
        topic_code = user_state.get(user_id, {}).get("topic_code", "")
        if topic_code:
            mark_learned(user_id, topic_code, pct)

        # Nishon tekshirish
        prog = get_progress(user_id)

        # O'quvchi sinfi
        conn2 = psycopg2.connect(DATABASE_URL)
        cur2  = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        urow  = cur2.fetchone()
        grade = urow[0] if urow else "5"
        cur2.close(); conn2.close()

        xp_text = f"\n⭐ +{xp_earned} XP" if xp_earned else ""
        streak_text = f"\n🔥 Streak: {streak} kun!" if streak > 1 else ""

        await message.edit_text(
            f"{emoji} Test yakunlandi!\n\n"
            f"✅ To'g'ri: {correct}/{total} ({pct}%)\n"
            f"{xp_text}{streak_text}\n\n"
            f"{msg}",
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
    image_url  = q[8] if len(q) > 8 else None

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"🔊 Savol", callback_data="test_speak_q"),
            ],
            [InlineKeyboardButton(text=f"A) {option_a}", callback_data="test_answer_A"),
             InlineKeyboardButton(text=f"🔊", callback_data="test_speak_A")],
            [InlineKeyboardButton(text=f"B) {option_b}", callback_data="test_answer_B"),
             InlineKeyboardButton(text=f"🔊", callback_data="test_speak_B")],
            [InlineKeyboardButton(text=f"C) {option_c}", callback_data="test_answer_C"),
             InlineKeyboardButton(text=f"🔊", callback_data="test_speak_C")],
            [InlineKeyboardButton(text=f"D) {option_d}", callback_data="test_answer_D"),
             InlineKeyboardButton(text=f"🔊", callback_data="test_speak_D")],
        ]
    )

    text = (
        f"🧠 Mustahkamlash testi\n"
        f"━━━━━━━━━━━━━━\n"
        f"❓ {index + 1}/{len(questions)}\n\n"
        f"{question}"
    )

    # Rasm bor bo'lsa — alohida yuborish
    if image_url and str(image_url).strip() not in ("", "None", "nan"):
        try:
            # DB dan file_id olish
            conn2 = psycopg2.connect(DATABASE_URL)
            cur2  = conn2.cursor()
            cur2.execute("SELECT file_id FROM images WHERE name=%s", (image_url,))
            img_row = cur2.fetchone()
            cur2.close(); conn2.close()

            if img_row:
                await message.answer_photo(img_row[0], caption=text, reply_markup=keyboard)
                return
        except Exception:
            pass

    await message.edit_text(text, reply_markup=keyboard)


async def lesson_test_answer(user_id, message, answer):
    """Test javobini tekshiradi"""

    u = user_state.get(user_id, {})
    if not isinstance(u, dict):
        u = {}

    questions = u.get("test_questions", [])
    index     = u.get("test_index", 0)

    # user_state bo'sh bo'lsa — lesson_progress dan qayta yuklaymiz
    if not questions:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        try:
            cur.execute("""
                SELECT topic_code FROM lesson_progress WHERE user_id=%s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                await message.answer("❌ Test topilmadi. Qaytadan boshlang.")
                return

            topic_code = row[0]
            cur.execute("""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type, image_url
                FROM generated_tests
                WHERE topic_code=%s AND question IS NOT NULL
                ORDER BY RANDOM() LIMIT 5
            """, (topic_code,))
            questions = cur.fetchall()

            if not questions:
                await message.answer("❌ Savollar topilmadi.")
                return

            if user_id not in user_state or not isinstance(user_state.get(user_id), dict):
                user_state[user_id] = {}

            user_state[user_id]["test_questions"] = questions
            user_state[user_id]["test_index"]     = 0
            user_state[user_id]["test_correct"]   = 0
            index = 0
        finally:
            cur.close(); conn.close()

    if not questions or index >= len(questions):
        await message.answer("❌ Test tugadi yoki topilmadi.")
        return

    q             = questions[index]
    correct       = str(q[5] or "").strip()
    explanation   = q[6] or ""

    # correct_answer A/B/C/D yoki to'liq javob matni bo'lishi mumkin
    user_ans = answer.upper().strip()
    correct_upper = correct.upper().strip()

    # A/B/C/D formatida tekshirish
    opt_map = {
        "A": str(q[1] or "").strip().upper(),
        "B": str(q[2] or "").strip().upper(),
        "C": str(q[3] or "").strip().upper(),
        "D": str(q[4] or "").strip().upper(),
    }

    # To'g'ri javob A/B/C/D bo'lsa
    if correct_upper in ("A", "B", "C", "D"):
        is_correct = user_ans == correct_upper
    else:
        # To'g'ri javob matn bo'lsa — variant matni bilan solishtir
        selected_text = opt_map.get(user_ans, "")
        is_correct = selected_text == correct_upper

    if is_correct:
        if not isinstance(user_state.get(user_id), dict):
            user_state[user_id] = {}
        user_state[user_id]["test_correct"] = (
            user_state[user_id].get("test_correct", 0) + 1
        )
        result_text = "✅ To'g'ri!"
    else:
        result_text = f"❌ Noto'g'ri! To'g'ri javob: {correct}"

    if explanation:
        result_text += f"\n\n💡 {explanation}"

    next_index = index + 1
    if not isinstance(user_state.get(user_id), dict):
        user_state[user_id] = {}
    user_state[user_id]["test_index"] = next_index

    # Kalonka — to'g'ri/xato ovozda ham aytsin
    try:
        voice_text = "To'g'ri!" if is_correct else f"Noto'g'ri. To'g'ri javob {correct}"
        await speak_mixed_text(user_id, message, voice_text)
    except Exception:
        pass

    await message.answer(
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

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    try:

        # Mavzu topic_code ni oldindan saqlab olamiz
        topic_code = user_state.get(user_id, {}).get("topic_code", "") if isinstance(user_state.get(user_id), dict) else ""
        grade      = user_state.get(user_id, {}).get("sinf", "") if isinstance(user_state.get(user_id), dict) else ""

        if user_id in user_state:
            user_state.pop(user_id)

        cur.execute("""
            DELETE FROM lesson_progress
            WHERE user_id = %s
        """, (user_id,))

        conn.commit()

        # Rolni aniqla
        cur.execute("""
            SELECT role, class FROM users WHERE user_id = %s
        """, (user_id,))
        row   = cur.fetchone()
        role  = row[0] if row else "O'quvchi"
        grade = grade or (row[1] if row else "1")

        # Keyingi mavzuni top
        from progress import get_next_topic
        next_topic = get_next_topic(user_id, grade)

        await message.edit_text("🏁 Dars yakunlandi! Rahmat.")

        if next_topic:
            await message.answer(
                f"🎯 Keyingi mavzu tayyor:\n\n"
                f"📚 {next_topic[3]}\n"
                f"📝 {next_topic[2]}\n"
                f"🔑 {next_topic[1]}\n\n"
                f"Davom etasizmi?",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="▶️ Ha, davom etaman!",
                            callback_data=f"next_lesson_{next_topic[0]}"
                        )],
                        [InlineKeyboardButton(
                            text="🏠 Yo'q, keyinroq",
                            callback_data="go_home_dashboard"
                        )]
                    ]
                )
            )
        else:
            # Dashboard ko'rsatish
            try:
                from student_dashboard import build_dashboard
                text, kb = await build_dashboard(user_id)
                await message.answer(text, reply_markup=kb)
            except Exception:
                await message.answer(
                    "🎉 Barcha mavzularni o'zgandingiz!",
                    reply_markup=get_main_keyboard(role)
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
