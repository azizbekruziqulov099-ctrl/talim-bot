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

HOME_BTN = [InlineKeyboardButton(text="🏠 Bosh ekran", callback_data="go_home_dashboard")]


def _build_kb(a, b, c, d, time_left=0):
    timer_text = f"⏱ {time_left}s" if time_left > 0 else "∞"
    return InlineKeyboardMarkup(inline_keyboard=[
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
        HOME_BTN,
    ])


def render_text(text: str) -> str:
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
    text = render_text(text)
    text = re.sub(
        r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+',
        ' ', text, flags=re.UNICODE
    )
    text = re.sub(r'[•\*\#\|\_\~\`━\-]{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _build_board_text(session, extra=""):
    """Bitta doskadagi to'liq matn — SYNC"""
    total   = len(session["questions"])
    correct = session["correct"]
    wrong   = session["wrong"]
    done    = correct + wrong
    bar     = "🟩" * correct + "🟥" * wrong + "⬜" * max(0, min(20, total) - done)
    header  = f"📊 {done}/{total} | ✅ {correct} | ❌ {wrong}\n{bar}\n━━━━━━━━━━━━━━"
    return header + "\n\n" + extra if extra else header


async def _go_next(user_id, correct_answer, reason=""):
    """Vaqt tugaganda yoki javob berilganda keyingi savolga o'tish"""
    s = test_sessions.get(user_id)
    if not s:
        return
    chat_id    = s.get("board_chat_id")
    msg_id     = s.get("board_msg_id")
    correct_tx = render_text(str(correct_answer))

    # Natija ko'rsat
    if reason:
        txt = _build_board_text(s, reason + f"\n✅ To'g'ri: {correct_tx}")
        try:
            await bot.edit_message_text(txt, chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass
        await asyncio.sleep(2)

    # Keyingi savolga
    s = test_sessions.get(user_id)
    if not s:
        return
    s["current"] += 1
    if s["current"] >= len(s["questions"]):
        await finish_test(user_id)
    else:
        await show_question(user_id)


async def start_test(user_id, tests, message):
    if not tests:
        await message.answer("❌ Test topilmadi")
        return

    old_s = test_sessions.get(user_id, {})
    if old_s.get("timer_task"):
        try:
            old_s["timer_task"].cancel()
        except Exception:
            pass

    try:
        for i in range(message.message_id, message.message_id - 25, -1):
            try:
                await bot.delete_message(message.chat.id, i)
            except Exception:
                pass
    except Exception:
        pass

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
        "answered":      False,
    }

    await show_question(user_id)


async def show_question(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s:
        return

    # Timer to'xtatish
    if s.get("timer_task"):
        try:
            s["timer_task"].cancel()
            s["timer_task"] = None
        except Exception:
            pass

    s["answered"] = False

    chat_id  = s.get("board_chat_id")
    msg_id   = s.get("board_msg_id")
    current  = s["current"]
    total    = len(s["questions"])
    test     = s["questions"][current]

    (
        question, a, b, c, d,
        correct, explanation,
        question_type, is_latex,
        image_url, audio_text,
        language, time_limit
    ) = test

    q_show = render_text(question)
    a_show = render_text(str(a or ""))
    b_show = render_text(str(b or ""))
    c_show = render_text(str(c or ""))
    d_show = render_text(str(d or ""))

    # Ovoz xabarlarini o'chirish
    for vid in s.get("voice_msgs", []):
        try:
            await bot.delete_message(chat_id, vid)
        except Exception:
            pass
    s["voice_msgs"] = []

    # Rasm tepada
    old_img = s.get("img_msg_id")
    if old_img:
        try:
            await bot.delete_message(chat_id, old_img)
        except Exception:
            pass
        s["img_msg_id"] = None

    has_image = False
    if is_latex and str(is_latex).lower() not in ("false", "0", "none", ""):
        try:
            from latex_utils import latex_to_image as _l2i
            img_path = _l2i(question, user_id)
            if img_path and os.path.exists(img_path):
                im = await bot.send_photo(chat_id, FSInputFile(img_path))
                s["img_msg_id"] = im.message_id
                os.remove(img_path)
                has_image = True
        except Exception:
            pass
    elif image_url and str(image_url).strip() not in ("", "None", "nan"):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur  = conn.cursor()
            cur.execute("SELECT file_id FROM images WHERE name=%s", (image_url.strip(),))
            row  = cur.fetchone()
            cur.close(); conn.close()
            if row:
                im = await bot.send_photo(chat_id, row[0])
                s["img_msg_id"] = im.message_id
                has_image = True
        except Exception:
            pass

    if has_image and msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
        s["board_msg_id"] = None
        msg_id = None

    try:
        tl = int(time_limit) if time_limit and int(time_limit) > 0 else 0
    except Exception:
        tl = 0

    s["time_left"] = tl
    header = _build_board_text(s)

    # YOZMA TEST
    if question_type == "write_answer":
        user_state[user_id] = "text_answer"
        timer_text = f"⏱ {tl}s" if tl > 0 else "∞"
        text = f"{header}\n\n✍️ Yozma savol {current+1}/{total}\n\n{q_show}\n\n📝 Javobingizni yozing:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔊", callback_data="speak_question"),
             InlineKeyboardButton(text=timer_text, callback_data="noop_timer"),
             InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop")],
            HOME_BTN,
        ])
        try:
            if msg_id:
                await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=kb)
            else:
                nm = await bot.send_message(chat_id, text, reply_markup=kb)
                s["board_msg_id"] = nm.message_id
                msg_id = nm.message_id
        except Exception:
            nm = await bot.send_message(chat_id, text, reply_markup=kb)
            s["board_msg_id"] = nm.message_id
            msg_id = nm.message_id

        if tl > 0:
            async def write_cd():
                left = tl
                while left > 0:
                    await asyncio.sleep(5)
                    left = max(0, left - 5)
                    sx = test_sessions.get(user_id)
                    if not sx or sx.get("answered"):
                        return
                    if left > 0:
                        try:
                            await bot.edit_message_reply_markup(
                                chat_id=sx["board_chat_id"],
                                message_id=sx["board_msg_id"],
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="🔊", callback_data="speak_question"),
                                     InlineKeyboardButton(text=f"⏱ {left}s", callback_data="noop_timer"),
                                     InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop")],
                                    HOME_BTN,
                                ])
                            )
                        except Exception:
                            pass
                # Vaqt tugadi
                sx = test_sessions.get(user_id)
                if not sx or sx.get("answered"):
                    return
                sx["answered"] = True
                sx["wrong"] += 1
                user_state[user_id] = None
                txt = _build_board_text(sx, f"⏰ Vaqt tugadi!\n✅ To'g'ri: {render_text(str(correct))}")
                try:
                    await bot.edit_message_text(txt, chat_id=sx["board_chat_id"], message_id=sx["board_msg_id"])
                except Exception:
                    pass
                await asyncio.sleep(2)
                sx = test_sessions.get(user_id)
                if not sx:
                    return
                sx["current"] += 1
                if sx["current"] >= len(sx["questions"]):
                    await finish_test(user_id)
                else:
                    await show_question(user_id)
            s["timer_task"] = asyncio.create_task(write_cd())
        return

    # TUGMALI TEST
    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    text = f"{header}\n\n🧪 Savol {current+1}/{total}\n\n{q_show}"
    kb   = _build_kb(a_show, b_show, c_show, d_show, tl)

    try:
        if msg_id:
            await bot.edit_message_text(text, chat_id=chat_id, message_id=msg_id, reply_markup=kb)
        else:
            nm = await bot.send_message(chat_id, text, reply_markup=kb)
            s["board_msg_id"] = nm.message_id
            msg_id = nm.message_id
    except Exception:
        nm = await bot.send_message(chat_id, text, reply_markup=kb)
        s["board_msg_id"] = nm.message_id
        msg_id = nm.message_id

    if tl <= 0:
        return

    async def cd():
        left = tl
        while left > 0:
            await asyncio.sleep(5)
            left = max(0, left - 5)
            sx = test_sessions.get(user_id)
            if not sx or sx.get("answered"):
                return
            if left > 0:
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=sx["board_chat_id"],
                        message_id=sx["board_msg_id"],
                        reply_markup=_build_kb(a_show, b_show, c_show, d_show, left)
                    )
                except Exception:
                    pass
        # Vaqt tugadi
        sx = test_sessions.get(user_id)
        if not sx or sx.get("answered"):
            return
        sx["answered"] = True
        sx["wrong"] += 1
        txt = _build_board_text(sx, f"⏰ Vaqt tugadi!\n✅ To'g'ri: {render_text(str(correct))}")
        try:
            await bot.edit_message_text(txt, chat_id=sx["board_chat_id"], message_id=sx["board_msg_id"])
        except Exception:
            pass
        await asyncio.sleep(2)
        sx = test_sessions.get(user_id)
        if not sx:
            return
        sx["current"] += 1
        if sx["current"] >= len(sx["questions"]):
            await finish_test(user_id)
        else:
            await show_question(user_id)

    s["timer_task"] = asyncio.create_task(cd())


async def _show_result(user_id, message, result_text):
    s = test_sessions.get(user_id)
    if not s:
        return
    s["answered"] = True

    # Timer to'xtatish
    if s.get("timer_task"):
        try:
            s["timer_task"].cancel()
            s["timer_task"] = None
        except Exception:
            pass

    chat_id = s.get("board_chat_id")
    msg_id  = s.get("board_msg_id")
    txt     = _build_board_text(s, result_text)

    try:
        if msg_id:
            await bot.edit_message_text(txt, chat_id=chat_id, message_id=msg_id, reply_markup=None)
        else:
            nm = await bot.send_message(chat_id, txt)
            s["board_msg_id"] = nm.message_id
    except Exception:
        try:
            nm = await bot.send_message(chat_id, txt)
            s["board_msg_id"] = nm.message_id
        except Exception:
            pass

    await asyncio.sleep(2)

    s = test_sessions.get(user_id)
    if not s:
        return
    s["current"] += 1
    if s["current"] >= len(s["questions"]):
        await finish_test(user_id)
    else:
        await show_question(user_id)


async def check_button_answer(user_id, answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"):
        return

    if s.get("timer_task"):
        try:
            s["timer_task"].cancel()
            s["timer_task"] = None
        except Exception:
            pass

    test    = s["questions"][s["current"]]
    a, b, c, d = test[1], test[2], test[3], test[4]
    correct    = str(test[5] or "").strip()
    explanation = render_text(str(test[6] or ""))

    sel_map = {"A": str(a), "B": str(b), "C": str(c), "D": str(d)}
    selected = sel_map.get(answer.upper(), "")

    if correct.upper() in ("A", "B", "C", "D"):
        is_ok = answer.upper() == correct.upper()
        correct_show = render_text(sel_map.get(correct.upper(), correct))
    else:
        is_ok = render_text(selected).strip().lower() == render_text(correct).strip().lower()
        correct_show = render_text(correct)

    if is_ok:
        s["correct"] += 1
        result = "🎉 To'g'ri! Ajoyib! ✅"
    else:
        s["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri javob: {correct_show}"

    if explanation:
        result += f"\n\n💡 {explanation}"

    await _show_result(user_id, message, result)


async def check_text_answer(user_id, user_answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"):
        return

    if s.get("timer_task"):
        try:
            s["timer_task"].cancel()
            s["timer_task"] = None
        except Exception:
            pass

    test        = s["questions"][s["current"]]
    correct     = render_text(str(test[5] or "")).strip().lower()
    user_answer = str(user_answer).strip().lower()
    explanation = render_text(str(test[6] or ""))

    if user_answer == correct:
        s["correct"] += 1
        result = "🎉 To'g'ri! Ajoyib! ✅"
    else:
        s["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri javob: {render_text(str(test[5]))}"

    if explanation:
        result += f"\n\n💡 {explanation}"

    user_state[user_id] = None
    await _show_result(user_id, message, result)


async def next_question(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s:
        return
    s["current"] += 1
    if s["current"] >= len(s["questions"]):
        await finish_test(user_id)
    else:
        await show_question(user_id)


async def finish_test(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s:
        return

    if s.get("timer_task"):
        try:
            s["timer_task"].cancel()
        except Exception:
            pass

    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    correct = s["correct"]
    wrong   = s["wrong"]
    total   = correct + wrong
    pct     = round(correct * 100 / total, 1) if total else 0
    emoji   = "🏆" if pct >= 80 else "👍" if pct >= 60 else "💪"

    txt = (
        f"{emoji} Test yakunlandi!\n\n"
        f"✅ To'g'ri: {correct}\n"
        f"❌ Noto'g'ri: {wrong}\n"
        f"📊 Natija: {pct}%"
    )

    chat_id = s.get("board_chat_id")
    msg_id  = s.get("board_msg_id")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Bosh menyuga qaytish", callback_data="go_home_dashboard")
    ]])

    try:
        if msg_id and chat_id:
            await bot.edit_message_text(txt, chat_id=chat_id, message_id=msg_id, reply_markup=kb)
        elif chat_id:
            await bot.send_message(chat_id, txt, reply_markup=kb)
    except Exception:
        if chat_id:
            try:
                await bot.send_message(chat_id, txt, reply_markup=kb)
            except Exception:
                pass

    test_sessions.pop(user_id, None)


async def stop_test(user_id, message):
    await finish_test(user_id, message)


async def speak_text(user_id, message, text):
    s = test_sessions.get(user_id)
    language = "uz"
    if s:
        try:
            language = str(s["questions"][s["current"]][11]).lower()
        except Exception:
            pass

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
    clean = tts_clean(text)
    if not clean or not any(c.isalnum() for c in clean):
        return

    filename = f"tts_{user_id}.mp3"
    try:
        communicate = edge_tts.Communicate(text=clean, voice=voices.get(language, voices["uz"]))
        await communicate.save(filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            vm = await message.answer_voice(FSInputFile(filename))
            sx = test_sessions.get(user_id)
            if sx is not None:
                sx.setdefault("voice_msgs", []).append(vm.message_id)
    except Exception:
        pass
    finally:
        try:
            os.remove(filename)
        except Exception:
            pass


async def speak_question(user_id, message):
    s = test_sessions.get(user_id)
    if s:
        await speak_text(user_id, message, s["questions"][s["current"]][0])

async def speak_a(user_id, message):
    s = test_sessions.get(user_id)
    if s:
        await speak_text(user_id, message, s["questions"][s["current"]][1])

async def speak_b(user_id, message):
    s = test_sessions.get(user_id)
    if s:
        await speak_text(user_id, message, s["questions"][s["current"]][2])

async def speak_c(user_id, message):
    s = test_sessions.get(user_id)
    if s:
        await speak_text(user_id, message, s["questions"][s["current"]][3])

async def speak_d(user_id, message):
    s = test_sessions.get(user_id)
    if s:
        await speak_text(user_id, message, s["questions"][s["current"]][4])


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
