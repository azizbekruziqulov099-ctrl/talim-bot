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
from storage import lesson_state, user_state

# teacher_engine dan kerakli funksiyalarni import qilish
try:
    from teacher_engine import build_board_text, render_content, parse_content, build_ssml
except ImportError:
    def build_board_text(text): return str(text) if text else ""
    def render_content(text): return str(text) if text else ""
    def parse_content(text): return [{"type": "text", "content": str(text)}]
    def build_ssml(text): return str(text) if text else ""
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

        vm_id = lesson_state.get(user_id, {}).get("voice_message_id") if isinstance(lesson_state.get(user_id), dict) else None
        if vm_id:
            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=vm_id
                )
            except Exception:
                pass

        voice_msg = await message.answer_voice(
            FSInputFile(final_file)
        )

        if not isinstance(lesson_state.get(user_id), dict):
            lesson_state[user_id] = {}

        lesson_state.setdefault(user_id, {})["voice_message_id"] = voice_msg.message_id

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

    text = lesson_state.get(user_id, {}).get("speak_text")

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

        # Dars o'rtada qolganmi? — lesson_progress tekshirish
        cur.execute("""
            SELECT lp.topic_code, lp.current_step,
                   d.subject_name, d.mavzu_name
            FROM lesson_progress lp
            LEFT JOIN dts_tree d ON d.topic_code = lp.topic_code
            WHERE lp.user_id = %s AND lp.current_step > 0
            LIMIT 1
        """, (user_id,))
        prog = cur.fetchone()
        if prog:
            tc, step, subj, mavzu = prog
            subj  = subj  or tc
            mavzu = mavzu or tc
            await message.answer(
                f"📖 Siz oldingi darsni o'rtada qoldirgansiz:\n"
                f"📚 {subj} — {mavzu}\n"
                f"📍 {step+1}-qadam\n\n"
                f"Davom etasizmi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="▶️ Davom etish",
                        callback_data=f"resume_lesson:{tc}"
                    ),
                    InlineKeyboardButton(
                        text="🗑 Boshidan boshlash",
                        callback_data=f"restart_lesson:{tc}"
                    ),
                ]])
            )
            cur.close(); conn.close()
            return

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
    from lesson_engine import build_lesson_data, show_main_step, LESSON_COLS
    conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
    try:
        uid     = _user_id or message.from_user.id
        chat_id = message.chat.id

        cur.execute("SELECT full_name, class, subject, gender FROM users WHERE user_id=%s", (uid,))
        urow = cur.fetchone()
        full_name = urow[0] if urow else "O'quvchi"
        sinf      = urow[1] if urow else "1"
        fan_user  = urow[2] if urow else ""
        gender    = urow[3] if urow else ""

        if not topic_code:
            from progress import get_next_topic
            nxt = get_next_topic(uid, sinf)
            if nxt: topic_code = nxt[0]
            else:
                await message.answer("🎉 Barcha mavzularni o'rgandingiz!")
                return

        # Ustunlarni aniq tartibda olamiz (SELECT * DB tartibiga bog'liq — xavfli)
        from lesson_engine import LESSON_COLS as _LC
        _sel_cols = ", ".join(c for c in _LC if c != "id")
        try:
            cur.execute(f"SELECT {_sel_cols} FROM teacher_lessons WHERE topic_code=%s", (topic_code,))
            _row = cur.fetchone()
            # id ustunini boshiga qo'shib LESSON_COLS bilan moslashtirish
            lesson = (None, *_row) if _row else None
        except Exception as _se:
            # Ustun yo'q bo'lsa (yangi ustunlar hali qo'shilmagan) — SELECT * dan fallback
            print(f"SELECT cols xato: {_se}, SELECT * ishlatilmoqda")
            cur.execute("SELECT * FROM teacher_lessons WHERE topic_code=%s", (topic_code,))
            lesson = cur.fetchone()
        if not lesson:
            await message.answer(f"📝 Bu mavzu uchun dars hali yozilmagan.\n🔑 {topic_code}")
            return

        cur.execute("SELECT grade, subject_name, mavzu_name FROM dts_tree WHERE topic_code=%s LIMIT 1", (topic_code,))
        trow = cur.fetchone()
        sinf  = trow[0] if trow else sinf
        fan   = trow[1] if trow else fan_user
        mavzu = trow[2] if trow else topic_code

        main_parts, simple_parts = build_lesson_data(lesson)
        if not main_parts:
            await message.answer("📭 Dars qismlari to'ldirilmagan.")
            return

        lesson_state[uid] = {
            "topic_code":    topic_code,
            "main_parts":    main_parts,
            "simple_parts":  simple_parts,
            "main_step":     0,
            "simple_step":   0,
            "mode":          "main",
            "total":         len(main_parts),
            "full_name":     full_name,
            "sinf":          sinf,
            "fan":           fan,
            "mavzu":         mavzu,
            "gender":        gender,
            "lesson_msg_id":   None,
            "lesson_has_photo": False,
            "voice_msg_id":    None,
        }
        user_state[uid] = "in_lesson"

        cur.execute("""
            INSERT INTO lesson_progress(user_id, topic_code, current_step)
            VALUES(%s,%s,0)
            ON CONFLICT(user_id) DO UPDATE SET topic_code=EXCLUDED.topic_code, current_step=0
        """, (uid, topic_code))
        conn.commit()

        await message.answer("📖 Dars boshlanmoqda...")
        await show_main_step(uid, chat_id)

    except Exception as e:
        import traceback; traceback.print_exc()
        await message.answer(f"❌ Xato: {e}")
    finally:
        cur.close(); conn.close()


async def lesson_next(user_id, message):
    """Keyingi qadamga o'tish."""
    from lesson_engine import show_lesson_step
    st = lesson_state.get(user_id) or {}
    if not isinstance(st, dict):
        await message.answer("❌ Dars holati topilmadi.")
        return
    parts   = st.get("parts", [])
    cur_idx = st.get("current_step", 0)
    total   = st.get("total", len(parts))
    if cur_idx + 1 >= total:
        return  # finish_confirm handle qiladi
    new_idx = cur_idx + 1
    lesson_state[user_id]["current_step"] = new_idx
    # DB yangilanish
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute(
            "UPDATE lesson_progress SET current_step=%s WHERE user_id=%s",
            (new_idx, user_id)
        )
        conn.commit(); cur.close(); conn.close()
    except Exception: pass
    await show_lesson_step(
        user_id, message.chat.id, new_idx, total, parts[new_idx],
        st.get("full_name","O'quvchi"), st.get("fan",""), st.get("mavzu","")
    )


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
    """Oldingi qadamga qaytish."""
    from lesson_engine import show_lesson_step
    st = lesson_state.get(user_id) or {}
    if not isinstance(st, dict):
        return
    parts   = st.get("parts", [])
    cur_idx = st.get("current_step", 0)
    total   = st.get("total", len(parts))
    if cur_idx <= 0:
        return
    new_idx = cur_idx - 1
    lesson_state[user_id]["current_step"] = new_idx
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute(
            "UPDATE lesson_progress SET current_step=%s WHERE user_id=%s",
            (new_idx, user_id)
        )
        conn.commit(); cur.close(); conn.close()
    except Exception: pass
    await show_lesson_step(
        user_id, message.chat.id, new_idx, total, parts[new_idx],
        st.get("full_name","O'quvchi"), st.get("fan",""), st.get("mavzu","")
    )


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

        u    = lesson_state.get(user_id) or {}
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

        topic_code = lesson_state.get(user_id, {}).get("topic_code", "TEST_001")

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
                    lesson_state.get(user_id, {}).get("mavzu", ""),
                    lesson_state.get(user_id, {}).get("fan", ""),
                    0, 0
                ))
                conn.commit()
            except Exception:
                pass

            await message.edit_text(
                f"✅ Dars muvaffaqiyatli tugallandi!\n\n"
                f"📘 {lesson_state.get(user_id, {}).get('mavzu', topic_code)}\n\n"
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
        if not isinstance(lesson_state.get(user_id), dict):
            lesson_state[user_id] = {}

        lesson_state.setdefault(user_id, {})["test_questions"] = questions
        lesson_state.setdefault(user_id, {})["test_index"]     = 0
        lesson_state.setdefault(user_id, {})["test_correct"]   = 0
        lesson_state.setdefault(user_id, {})["test_mode"]      = "consolidation"

        await send_test_question(user_id, message, questions, 0)

    except Exception as e:
        await message.answer(f"❌ Xatolik:\n{e}")

    finally:
        cur.close()
        conn.close()


async def send_test_question(user_id, message, questions, index):
    """Bitta test savolini yuboradi"""

    if index >= len(questions):
        correct = lesson_state.get(user_id, {}).get("test_correct", 0)
        total   = len(questions)
        pct     = int(correct / total * 100)

        emoji = "🏆" if pct >= 80 else "👍" if pct >= 60 else "💪"

        # lesson_history ga saqlash
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur  = conn.cursor()
            topic_code = lesson_state.get(user_id, {}).get("topic_code", "")
            cur.execute("""
                INSERT INTO lesson_history
                (user_id, topic_code, mavzu, fan, score, total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                topic_code,
                lesson_state.get(user_id, {}).get("mavzu", ""),
                lesson_state.get(user_id, {}).get("fan", ""),
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
        topic_code = lesson_state.get(user_id, {}).get("topic_code", "")
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

    u = lesson_state.get(user_id) or {}
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

            if user_id not in user_state or not isinstance(lesson_state.get(user_id), dict):
                lesson_state[user_id] = {}

            lesson_state.setdefault(user_id, {})["test_questions"] = questions
            lesson_state.setdefault(user_id, {})["test_index"]     = 0
            lesson_state.setdefault(user_id, {})["test_correct"]   = 0
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
        if not isinstance(lesson_state.get(user_id), dict):
            lesson_state[user_id] = {}
        lesson_state.setdefault(user_id, {})["test_correct"] = (
            user_state[user_id].get("test_correct", 0) + 1
        )
        result_text = "✅ To'g'ri!"
    else:
        result_text = f"❌ Noto'g'ri! To'g'ri javob: {correct}"

    if explanation:
        result_text += f"\n\n💡 {explanation}"

    next_index = index + 1
    if not isinstance(lesson_state.get(user_id), dict):
        lesson_state[user_id] = {}
    lesson_state.setdefault(user_id, {})["test_index"] = next_index
    lesson_state.setdefault(user_id, {})["last_result_text"] = result_text

    await message.answer(
        f"🧠 Mustahkamlash testi\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{result_text}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔊 O'qib ber",
                    callback_data="test_result_tts"
                )],
                [InlineKeyboardButton(
                    text="➡️ Keyingi savol",
                    callback_data="test_next_question"
                )]
            ]
        )
    )


async def lesson_speak(user_id, message):
    """Joriy dars qadamini ovozda o'qiydi."""
    from lesson_engine import speak_lesson_step
    st = lesson_state.get(user_id) or {}
    if not isinstance(st, dict): return
    parts   = st.get("parts", [])
    cur_idx = st.get("current_step", 0)
    if not parts or cur_idx >= len(parts): return
    # O'quvchi jinsi
    gender = ""
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT gender FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        gender = row[0] if row else ""
    except Exception: pass
    await speak_lesson_step(user_id, message.chat.id, parts[cur_idx]["text"], gender)


async def lesson_exit(user_id, message):
    """Darsdan chiqish."""
    from keyboards import get_main_keyboard
    st = lesson_state.pop(user_id, {})
    user_state.pop(user_id, None)
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("DELETE FROM lesson_progress WHERE user_id=%s", (user_id,))
        conn.commit(); cur.close(); conn.close()
    except Exception: pass
    # Rol olish
    role = "🧒 O'quvchi"
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: role = row[0]
    except Exception: pass
    try:
        await message.edit_reply_markup(reply_markup=None)
    except Exception: pass
    await message.answer("🏠 Bosh menyu", reply_markup=get_main_keyboard(role))


async def lesson_finish(
    user_id,
    message
):

    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    try:

        # Mavzu topic_code ni oldindan saqlab olamiz
        topic_code = lesson_state.get(user_id, {}).get("topic_code", "") if isinstance(lesson_state.get(user_id), dict) else ""
        grade      = lesson_state.get(user_id, {}).get("sinf", "") if isinstance(lesson_state.get(user_id), dict) else ""

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

        # Klaviaturani qaytarish
        await message.answer("👇", reply_markup=get_main_keyboard(role))

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
    import psycopg2, os
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    DB = os.getenv("DATABASE_URL")
    uid = message.from_user.id
    conn = psycopg2.connect(DB); cur = conn.cursor()
    cur.execute("SELECT full_name,role,class,birth_date,school,region FROM users WHERE user_id=%s",(uid,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row:
        await message.answer("❌ Profil topilmadi. /start bosing"); return

    name,role,cls,bdate,school,region = row
    txt = (
        f"👤 Kabinet\n\n"
        f"{'─'*20}\n"
        f"📛 Ism: {name or '—'}\n"
        f"🎭 Rol: {role or '—'}\n"
        f"🏫 Sinf: {cls or '—'}\n"
        f"🎂 Tug'ilgan: {bdate or '—'}\n"
        f"🏛 Maktab: {school or '—'}\n"
        f"{'─'*20}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ism o'zgartir",    callback_data="kb_change:name"),
         InlineKeyboardButton(text="🎭 Rol o'zgartir",    callback_data="kb_change:role")],
        [InlineKeyboardButton(text="🏫 Sinf o'zgartir",  callback_data="kb_change:class"),
         InlineKeyboardButton(text="🎂 Sana o'zgartir",  callback_data="kb_change:bdate")],
        [InlineKeyboardButton(text="🏛 Maktab o'zgartir",callback_data="kb_change:school")],
        [InlineKeyboardButton(text="🔄 Qayta ro'yxat",   callback_data="kb_rereg"),
         InlineKeyboardButton(text="🗑 Profilni o'chir",  callback_data="kb_delete")],
    ])
    await message.answer(txt, reply_markup=kb)
