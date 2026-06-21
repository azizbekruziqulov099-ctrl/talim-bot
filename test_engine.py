"""
test_engine.py — Test tizimi (bitta doskada, rasm tepada, yozma/tugmali)
"""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
import edge_tts
import asyncio
import psycopg2
from pydub import AudioSegment
import os
import re

from storage import user_state
from keyboards import get_main_keyboard
from loader import bot

DATABASE_URL = os.getenv("DATABASE_URL")

test_sessions = {}


def render_text(text: str) -> str:
    """Teglarni olib, matnni tozalaydi"""
    if not text:
        return ""
    text = str(text)
    text = re.sub(r'\[en\](.*?)\[/en\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[skip\](.*?)\[/skip\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[latex\](.*?)\[/latex\]', r'[\1]', text, flags=re.DOTALL)
    text = re.sub(r'\[img\](.*?)\[/img\]', '', text, flags=re.DOTALL)
    return text.strip()


def tts_clean(text: str) -> str:
    """TTS uchun emoji va teglarni olib tashlaydi"""
    text = render_text(text)
    text = re.sub(
        r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+',
        ' ', text, flags=re.UNICODE
    )
    text = re.sub(r'[•\*\#\|\_\~\`━\-]{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ─────────────────────────────────────────
# TEST BOSHLASH
# ─────────────────────────────────────────

async def start_test(user_id, tests, message):
    if not tests:
        await message.answer("❌ Test topilmadi")
        return

    # Eski session tozalash
    old_s = test_sessions.get(user_id, {})
    if old_s.get("timer_task"):
        try:
            old_s["timer_task"].cancel()
        except Exception:
            pass

    # Yuqoridagi xabarlarni o'chirish
    try:
        for i in range(message.message_id, message.message_id - 25, -1):
            try:
                await bot.delete_message(message.chat.id, i)
            except Exception:
                pass
    except Exception:
        pass

    # Savol xabari
    msg = await message.answer("⏳ Test yuklanmoqda...")

    test_sessions[user_id] = {
        "questions":     tests,
        "current":       0,
        "correct":       0,
        "wrong":         0,
        "timer_task":    None,
        "board_msg_id":  msg.message_id,
        "board_chat_id": msg.chat.id,
        "img_msg_id":    None,
        "voice_msgs":    [],
    }

    await show_question(user_id, message)


# ─────────────────────────────────────────
# SAVOL KO'RSATISH
# ─────────────────────────────────────────

async def show_question(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return

    # Timer to'xtatish
    if session.get("timer_task"):
        try:
            session["timer_task"].cancel()
            session["timer_task"] = None
        except Exception:
            pass

    board_chat_id = session.get("board_chat_id")

    # Ovoz xabarlarini o'chirish
    for vid in session.get("voice_msgs", []):
        try:
            await bot.delete_message(board_chat_id, vid)
        except Exception:
            pass
    session["voice_msgs"] = []

    current = session["current"]
    total   = len(session["questions"])
    test    = session["questions"][current]

    (
        question, a, b, c, d,
        correct, explanation,
        question_type, is_latex,
        image_url, audio_text,
        language, time_limit
    ) = test

    question_show = render_text(question)
    a_show = render_text(str(a or ""))
    b_show = render_text(str(b or ""))
    c_show = render_text(str(c or ""))
    d_show = render_text(str(d or ""))

    board_chat_id = session.get("board_chat_id") or message.chat.id
    board_msg_id  = session.get("board_msg_id")

    # ── RASM TEPADA ──
    # Eski rasm o'chirish
    old_img = session.get("img_msg_id")
    if old_img:
        try:
            await bot.delete_message(board_chat_id, old_img)
        except Exception:
            pass
        session["img_msg_id"] = None

    has_image = False

    # LaTeX rasmi
    if is_latex and str(is_latex).lower() not in ("false", "0", "none", ""):
        try:
            from latex_utils import latex_to_image
            img_path = latex_to_image(question, user_id)
            if img_path and os.path.exists(img_path):
                img_msg = await bot.send_photo(board_chat_id, FSInputFile(img_path))
                session["img_msg_id"] = img_msg.message_id
                os.remove(img_path)
                has_image = True
        except Exception:
            pass

    # DB rasmi
    elif image_url and str(image_url).strip() not in ("", "None", "nan"):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur  = conn.cursor()
            cur.execute("SELECT file_id FROM images WHERE name=%s", (image_url.strip(),))
            row  = cur.fetchone()
            cur.close(); conn.close()
            if row:
                img_msg = await bot.send_photo(board_chat_id, row[0])
                session["img_msg_id"] = img_msg.message_id
                has_image = True
        except Exception:
            pass

    # Rasm yuborilgandan keyin savol xabarini yangilash uchun
    # eski board_msg_id ni o'chirib, yangi xabar yuboramiz
    if has_image and board_msg_id:
        try:
            await bot.delete_message(board_chat_id, board_msg_id)
        except Exception:
            pass
        session["board_msg_id"] = None
        board_msg_id = None

    # ── YOZMA TEST ──
    if question_type == "write_answer":
        user_state[user_id] = "text_answer"

        try:
            tl = int(time_limit) if time_limit and int(time_limit) > 0 else 0
        except Exception:
            tl = 0

        session["time_left"] = tl
        timer_text = f"⏱ {tl}s" if tl > 0 else "∞"

        text = (
            f"✍️ Yozma savol {current+1}/{total}\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"{question_show}\n\n"
            f"📝 Javobingizni yozing:"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔊",        callback_data="speak_question"),
            InlineKeyboardButton(text=timer_text,  callback_data="noop_timer"),
            InlineKeyboardButton(text="🛑 Stop",   callback_data="test_stop"),
        ]])

        try:
            if board_msg_id:
                await bot.edit_message_text(
                    text, chat_id=board_chat_id,
                    message_id=board_msg_id, reply_markup=kb
                )
            else:
                msg = await message.answer(text, reply_markup=kb)
                session["board_msg_id"]  = msg.message_id
                session["board_chat_id"] = msg.chat.id
                board_msg_id  = msg.message_id
                board_chat_id = msg.chat.id
        except Exception:
            msg = await message.answer(text, reply_markup=kb)
            session["board_msg_id"]  = msg.message_id
            session["board_chat_id"] = msg.chat.id
            board_msg_id  = msg.message_id
            board_chat_id = msg.chat.id

        # Yozma testda ham countdown
        if tl > 0:
            async def write_countdown():
                left = tl
                while left > 0:
                    await asyncio.sleep(5)
                    left = max(0, left - 5)

                    s = test_sessions.get(user_id)
                    if not s:
                        return

                    s["time_left"] = left

                    if left > 0:
                        new_kb = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="🔊",  callback_data="speak_question"),
                            InlineKeyboardButton(text=f"⏱ {left}s", callback_data="noop_timer"),
                            InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop"),
                        ]])
                        try:
                            await bot.edit_message_reply_markup(
                                chat_id=s.get("board_chat_id"),
                                message_id=s.get("board_msg_id"),
                                reply_markup=new_kb
                            )
                        except Exception:
                            pass

                # Vaqt tugadi
                s = test_sessions.get(user_id)
                if not s or s.get("current") != current:
                    return

                # user_state tozalash
                user_state[user_id] = None
                s["wrong"] += 1

                try:
                    await bot.edit_message_text(
                        f"⏰ Vaqt tugadi!\n\n✅ To'g'ri javob: {render_text(str(correct))}",
                        chat_id=s.get("board_chat_id"),
                        message_id=s.get("board_msg_id")
                    )
                except Exception:
                    pass

                await asyncio.sleep(2)
                await next_question(user_id, None)

            task = asyncio.create_task(write_countdown())
            session["timer_task"] = task

        return

    # ── TUGMALI TEST ──
    # user_state ni tozalash (oldingi yozma testdan)
    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    try:
        tl = int(time_limit) if time_limit and int(time_limit) > 0 else 0
    except Exception:
        tl = 0

    session["time_left"] = tl

    timer_text = f"⏱ {tl}s" if tl > 0 else "∞"

    kb = _build_kb(a_show, b_show, c_show, d_show, tl)

    text = (
        f"🧪 Savol {current+1}/{total}\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{question_show}"
    )

    try:
        if board_msg_id:
            await bot.edit_message_text(
                text, chat_id=board_chat_id,
                message_id=board_msg_id, reply_markup=kb
            )
        else:
            msg = await message.answer(text, reply_markup=kb)
            session["board_msg_id"]  = msg.message_id
            session["board_chat_id"] = msg.chat.id
    except Exception:
        msg = await message.answer(text, reply_markup=kb)
        session["board_msg_id"]  = msg.message_id
        session["board_chat_id"] = msg.chat.id

    # ── COUNTDOWN ──
    if tl <= 0:
        return

    async def countdown():
        left = tl
        while left > 0:
            await asyncio.sleep(5)
            left = max(0, left - 5)

            s = test_sessions.get(user_id)
            if not s:
                return

            s["time_left"] = left

            if left > 0:
                new_kb = _build_kb(a_show, b_show, c_show, d_show, left)
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=s.get("board_chat_id"),
                        message_id=s.get("board_msg_id"),
                        reply_markup=new_kb
                    )
                except Exception:
                    pass

        # Vaqt tugadi — faqat shu savolda bo'lsa
        s = test_sessions.get(user_id)
        if not s or s.get("current") != current:
            return

        s["wrong"] += 1
        try:
            await bot.edit_message_text(
                f"⏰ Vaqt tugadi!\n\n✅ To'g'ri javob: {render_text(str(correct))}",
                chat_id=s.get("board_chat_id"),
                message_id=s.get("board_msg_id")
            )
        except Exception:
            pass

        await asyncio.sleep(2)
        s = test_sessions.get(user_id)
        if s and s.get("current") == current:
            await next_question(user_id, None)

    task = asyncio.create_task(countdown())
    session["timer_task"] = task


def _build_kb(a, b, c, d, time_left=0):
    timer_text = f"⏱ {time_left}s" if time_left > 0 else "∞"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔊", callback_data="speak_question"),
                InlineKeyboardButton(text=timer_text, callback_data="noop_timer"),
                InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop"),
            ],
            [InlineKeyboardButton(text=a, callback_data="ans_A"),
             InlineKeyboardButton(text="🔊", callback_data="speak_a")],
            [InlineKeyboardButton(text=b, callback_data="ans_B"),
             InlineKeyboardButton(text="🔊", callback_data="speak_b")],
            [InlineKeyboardButton(text=c, callback_data="ans_C"),
             InlineKeyboardButton(text="🔊", callback_data="speak_c")],
            [InlineKeyboardButton(text=d, callback_data="ans_D"),
             InlineKeyboardButton(text="🔊", callback_data="speak_d")],
        ]
    )


# ─────────────────────────────────────────
# JAVOB TEKSHIRISH
# ─────────────────────────────────────────

async def _update_progress_bar(user_id):
    """Progress barni yangilaydi"""
    session = test_sessions.get(user_id)
    if not session:
        return
    bar_msg_id    = session.get("bar_msg_id")
    board_chat_id = session.get("board_chat_id")
    if not bar_msg_id or not board_chat_id:
        return
    correct = session["correct"]
    wrong   = session["wrong"]
    done    = correct + wrong
    total   = len(session["questions"])
    show    = min(total, 20)
    ratio   = done / total if total else 0
    filled  = round(ratio * show)
    ok_part  = min(correct, filled)
    err_part = filled - ok_part
    bar = "🟩" * ok_part + "🟥" * err_part + "⬜" * (show - filled)
    pct = round(done * 100 / total) if total else 0
    try:
        await bot.edit_message_text(
            f"📊 {bar}\n✅ {correct}  ❌ {wrong}  📊 {done}/{total} ({pct}%)",
            chat_id=board_chat_id,
            message_id=bar_msg_id
        )
    except Exception:
        pass


async def _show_result(user_id, message, result_text):
    session = test_sessions.get(user_id)
    if not session:
        return

    board_chat_id = session.get("board_chat_id")
    board_msg_id  = session.get("board_msg_id")

    correct = session["correct"]
    wrong   = session["wrong"]
    done    = correct + wrong
    total   = len(session["questions"])

    bar = "🟩" * correct + "🟥" * wrong + "⬜" * (total - done)
    full_text = f"{result_text}\n\n{bar}\n✅ {correct}  ❌ {wrong}  📊 {done}/{total}"

    try:
        if board_msg_id:
            await bot.edit_message_text(
                full_text,
                chat_id=board_chat_id,
                message_id=board_msg_id
            )
        else:
            await bot.send_message(board_chat_id, full_text)
    except Exception:
        pass

    await asyncio.sleep(2)
    await next_question(user_id, None)


async def check_button_answer(user_id, answer, message):
    session = test_sessions.get(user_id)
    if not session:
        return

    # Timer to'xtatish
    if session.get("timer_task"):
        try:
            session["timer_task"].cancel()
            session["timer_task"] = None
        except Exception:
            pass

    current = session["current"]
    test    = session["questions"][current]

    a, b, c, d   = test[1], test[2], test[3], test[4]
    correct      = str(test[5] or "").strip()
    explanation  = render_text(str(test[6] or ""))

    sel_map = {"A": str(a), "B": str(b), "C": str(c), "D": str(d)}
    selected = sel_map.get(answer.upper(), "")

    # To'g'ri javob A/B/C/D yoki matn
    if correct.upper() in ("A","B","C","D"):
        is_ok = answer.upper() == correct.upper()
        correct_show = render_text(sel_map.get(correct.upper(), correct))
    else:
        is_ok = render_text(selected).strip().lower() == render_text(correct).strip().lower()
        correct_show = render_text(correct)

    if is_ok:
        session["correct"] += 1
        result = "🎉 To'g'ri! Ajoyib! ✅"
    else:
        session["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri javob: {correct_show}"

    if explanation:
        result += f"\n\n💡 {explanation}"

    await _show_result(user_id, message, result)


async def check_text_answer(user_id, user_answer, message):
    session = test_sessions.get(user_id)
    if not session:
        return

    # Timer to'xtatish
    if session.get("timer_task"):
        try:
            session["timer_task"].cancel()
            session["timer_task"] = None
        except Exception:
            pass

    current = session["current"]
    test    = session["questions"][current]

    correct     = render_text(str(test[5] or "")).strip().lower()
    user_answer = str(user_answer).strip().lower()
    explanation = render_text(str(test[6] or ""))

    if user_answer == correct:
        session["correct"] += 1
        result = "🎉 To'g'ri! Ajoyib! ✅"
    else:
        session["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri javob: {render_text(str(test[5]))}"

    if explanation:
        result += f"\n\n💡 {explanation}"

    # user_state tozalash
    user_state[user_id] = None

    await _show_result(user_id, message, result)


# ─────────────────────────────────────────
# KEYINGI / YAKUNLASH
# ─────────────────────────────────────────

async def next_question(user_id, message=None):
    session = test_sessions.get(user_id)
    if not session:
        return

    session["current"] += 1

    if session["current"] >= len(session["questions"]):
        await finish_test(user_id, message)
        return

    # message yo'q bo'lsa — bot orqali fake message yaratamiz
    if message is None:
        chat_id = session.get("board_chat_id")
        if not chat_id:
            return

        class FakeMessage:
            def __init__(self, cid):
                self.chat = type('C', (), {'id': cid})()
                self.from_user = type('U', (), {'id': user_id})()
                self.bot = bot
                self.message_id = None

            async def answer(self, text, **kwargs):
                return await bot.send_message(chat_id, text, **kwargs)

            async def answer_voice(self, voice, **kwargs):
                return await bot.send_voice(chat_id, voice, **kwargs)

            async def edit_text(self, text, **kwargs):
                pass

            async def delete(self):
                pass

        message = FakeMessage(chat_id)

    await show_question(user_id, message)


async def finish_test(user_id, message=None):
    session = test_sessions.get(user_id)
    if not session:
        return

    # Timer to'xtatish
    if session.get("timer_task"):
        try:
            session["timer_task"].cancel()
        except Exception:
            pass

    # user_state tozalash
    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    correct = session["correct"]
    wrong   = session["wrong"]
    total   = correct + wrong
    pct     = round(correct * 100 / total, 1) if total else 0

    emoji = "🏆" if pct >= 80 else "👍" if pct >= 60 else "💪"

    result_text = (
        f"{emoji} Test yakunlandi!\n\n"
        f"✅ To'g'ri: {correct}\n"
        f"❌ Noto'g'ri: {wrong}\n"
        f"📊 Natija: {pct}%"
    )

    board_chat_id = session.get("board_chat_id")
    board_msg_id  = session.get("board_msg_id")
    bar_msg_id    = session.get("bar_msg_id")

    # Progress bar xabarini o'chirish
    if bar_msg_id and board_chat_id:
        try:
            await bot.delete_message(board_chat_id, bar_msg_id)
        except Exception:
            pass

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Bosh menyuga qaytish", callback_data="go_home_dashboard")
    ]])

    try:
        if board_msg_id and board_chat_id:
            await bot.edit_message_text(
                result_text, chat_id=board_chat_id,
                message_id=board_msg_id, reply_markup=kb
            )
        elif message:
            await message.answer(result_text, reply_markup=kb)
        elif board_chat_id:
            await bot.send_message(board_chat_id, result_text, reply_markup=kb)
    except Exception:
        if board_chat_id:
            try:
                await bot.send_message(board_chat_id, result_text, reply_markup=kb)
            except Exception:
                pass

    if user_id in test_sessions:
        del test_sessions[user_id]


async def stop_test(user_id, message):
    await finish_test(user_id, message)


# ─────────────────────────────────────────
# OVOZ
# ─────────────────────────────────────────

async def speak_text(user_id, message, text):
    session = test_sessions.get(user_id)
    language = "uz"
    if session:
        try:
            language = str(session["questions"][session["current"]][11]).lower()
        except Exception:
            pass

    # Jinsga qarab ovoz
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT gender FROM users WHERE user_id=%s", (user_id,))
        row  = cur.fetchone()
        cur.close(); conn.close()
        gender = row[0] if row else ""
    except Exception:
        gender = ""

    voices = {
        "uz": "uz-UZ-MadinaNeural" if "Ayol" in str(gender) else "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural",
        "ru": "ru-RU-DmitryNeural",
    }

    voice    = voices.get(language, voices["uz"])
    clean    = tts_clean(text)

    if not clean or not any(c.isalnum() for c in clean):
        return

    filename = f"tts_{user_id}.mp3"
    try:
        communicate = edge_tts.Communicate(text=clean, voice=voice)
        await communicate.save(filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            voice_msg = await message.answer_voice(FSInputFile(filename))
            # Ovoz xabarini ro'yxatga qo'shish
            s = test_sessions.get(user_id)
            if s is not None:
                if "voice_msgs" not in s:
                    s["voice_msgs"] = []
                s["voice_msgs"].append(voice_msg.message_id)
    except Exception as e:
        pass
    finally:
        try:
            os.remove(filename)
        except Exception:
            pass


async def speak_question(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    q = session["questions"][session["current"]]
    await speak_text(user_id, message, q[0])


async def speak_a(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    await speak_text(user_id, message, session["questions"][session["current"]][1])


async def speak_b(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    await speak_text(user_id, message, session["questions"][session["current"]][2])


async def speak_c(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    await speak_text(user_id, message, session["questions"][session["current"]][3])


async def speak_d(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    await speak_text(user_id, message, session["questions"][session["current"]][4])


# ─────────────────────────────────────────
# LATEX (eski funksiya — boshqa joylardan chaqiriladi)
# ─────────────────────────────────────────

def latex_to_image(latex_text, filename):
    try:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(6, 2))
        plt.text(0.05, 0.5, f"${latex_text}$", fontsize=24)
        plt.axis("off")
        plt.savefig(filename, bbox_inches="tight", dpi=150)
        plt.close(fig)
    except Exception:
        pass
