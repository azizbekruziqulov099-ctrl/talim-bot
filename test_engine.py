from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
import edge_tts, asyncio, psycopg2, os, re
from storage import user_state
from loader import bot

DATABASE_URL = os.getenv("DATABASE_URL")
test_sessions = {}
HOME_BTN = [InlineKeyboardButton(text="🏠 Bosh ekran", callback_data="go_home_dashboard")]


def render_text(text):
    if not text: return ""
    t = str(text)
    t = re.sub(r'\[en\](.*?)\[/en\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[skip\](.*?)\[/skip\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[latex\](.*?)\[/latex\]', r'[\1]', t, flags=re.DOTALL)
    t = re.sub(r'\[img\](.*?)\[/img\]', '', t, flags=re.DOTALL)
    return t.strip()


def tts_clean(text):
    t = render_text(text)
    t = re.sub(r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', ' ', t)
    t = re.sub(r'[•\*\#\|\_\~\`━\-]{2,}', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def _board(s, extra=""):
    total = len(s["questions"])
    ok, err = s["correct"], s["wrong"]
    done = ok + err
    bar = "🟩"*ok + "🟥"*err + "⬜"*max(0, min(20,total)-done)
    h = f"📊 {done}/{total} | ✅ {ok} | ❌ {err}\n{bar}\n━━━━━━━━━━━━━━"
    return h + "\n\n" + extra if extra else h


def _build_kb(a, b, c, d, tl=0):
    t = f"⏱ {tl}s" if tl > 0 else "∞"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊", callback_data="speak_question"),
         InlineKeyboardButton(text=t, callback_data="noop_timer"),
         InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop")],
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


async def _send_board(s, text, kb=None):
    """Doskaga xabar yuboradi — edit yoki yangi"""
    chat = s.get("board_chat_id")
    mid  = s.get("board_msg_id")
    try:
        if mid:
            await bot.edit_message_text(text, chat_id=chat, message_id=mid, reply_markup=kb)
            return
    except Exception:
        pass
    # edit ishlamadi — yangi xabar
    try:
        nm = await bot.send_message(chat, text, reply_markup=kb)
        s["board_msg_id"] = nm.message_id
    except Exception:
        pass


async def _advance(user_id):
    """Keyingi savolga o'tish yoki test yakunlash"""
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

    old = test_sessions.get(user_id, {})
    if old.get("timer_task"):
        try: old["timer_task"].cancel()
        except: pass

    try:
        for i in range(message.message_id, message.message_id - 25, -1):
            try: await bot.delete_message(message.chat.id, i)
            except: pass
    except: pass

    msg = await message.answer("⏳ Test yuklanmoqda...")
    test_sessions[user_id] = {
        "questions": tests, "current": 0, "correct": 0, "wrong": 0,
        "timer_task": None, "board_msg_id": msg.message_id,
        "board_chat_id": msg.chat.id, "img_msg_id": None,
        "voice_msgs": [], "answered": False,
    }
    await show_question(user_id)


async def show_question(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s:
        return

    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None

    s["answered"] = False
    chat = s.get("board_chat_id")

    # Ovoz xabarlarini o'chirish
    for vid in s.get("voice_msgs", []):
        try: await bot.delete_message(chat, vid)
        except: pass
    s["voice_msgs"] = []

    cur   = s["current"]
    total = len(s["questions"])
    test  = s["questions"][cur]

    (q, a, b, c, d, correct, expl,
     qtype, is_latex, img_url, audio, lang, tl) = test

    q_s = render_text(q)
    a_s = render_text(str(a or ""))
    b_s = render_text(str(b or ""))
    c_s = render_text(str(c or ""))
    d_s = render_text(str(d or ""))

    # Rasm
    old_img = s.get("img_msg_id")
    if old_img:
        try: await bot.delete_message(chat, old_img)
        except: pass
        s["img_msg_id"] = None

    if is_latex and str(is_latex).lower() not in ("false","0","none",""):
        try:
            from latex_utils import latex_to_image as l2i
            p = l2i(q, user_id)
            if p and os.path.exists(p):
                im = await bot.send_photo(chat, FSInputFile(p))
                s["img_msg_id"] = im.message_id
                os.remove(p)
                mid = s.get("board_msg_id")
                if mid:
                    try: await bot.delete_message(chat, mid)
                    except: pass
                    s["board_msg_id"] = None
        except: pass
    elif img_url and str(img_url).strip() not in ("","None","nan"):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur2 = conn.cursor()
            cur2.execute("SELECT file_id FROM images WHERE name=%s", (img_url.strip(),))
            row = cur2.fetchone()
            cur2.close(); conn.close()
            if row:
                im = await bot.send_photo(chat, row[0])
                s["img_msg_id"] = im.message_id
                mid = s.get("board_msg_id")
                if mid:
                    try: await bot.delete_message(chat, mid)
                    except: pass
                    s["board_msg_id"] = None
        except: pass

    try: tl = int(tl) if tl and int(tl) > 0 else 0
    except: tl = 0
    s["time_left"] = tl

    header = _board(s)

    # YOZMA TEST
    if qtype == "write_answer":
        user_state[user_id] = "text_answer"
        tmr = f"⏱ {tl}s" if tl > 0 else "∞"
        text = f"{header}\n\n✍️ Yozma savol {cur+1}/{total}\n\n{q_s}\n\n📝 Javobingizni yozing:"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔊", callback_data="speak_question"),
             InlineKeyboardButton(text=tmr, callback_data="noop_timer"),
             InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop")],
            HOME_BTN,
        ])
        await _send_board(s, text, kb)

        if tl > 0:
            async def write_cd():
                left = tl
                while left > 0:
                    await asyncio.sleep(5)
                    left = max(0, left - 5)
                    sx = test_sessions.get(user_id)
                    if not sx or sx.get("answered"): return
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
                        except: pass
                sx = test_sessions.get(user_id)
                if not sx or sx.get("answered"): return
                sx["answered"] = True
                sx["wrong"] += 1
                user_state[user_id] = None
                await bot.send_message(sx["board_chat_id"],
                    f"⏰ Vaqt tugadi!\n✅ To'g'ri: {render_text(str(correct))}")
                await asyncio.sleep(2)
                await _advance(user_id)
            s["timer_task"] = asyncio.create_task(write_cd())
        return

    # TUGMALI TEST
    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    text = f"{header}\n\n🧪 Savol {cur+1}/{total}\n\n{q_s}"
    kb = _build_kb(a_s, b_s, c_s, d_s, tl)
    await _send_board(s, text, kb)

    if tl <= 0:
        return

    async def cd():
        left = tl
        while left > 0:
            await asyncio.sleep(5)
            left = max(0, left - 5)
            sx = test_sessions.get(user_id)
            if not sx or sx.get("answered"): return
            if left > 0:
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=sx["board_chat_id"],
                        message_id=sx["board_msg_id"],
                        reply_markup=_build_kb(a_s, b_s, c_s, d_s, left)
                    )
                except: pass
        sx = test_sessions.get(user_id)
        if not sx or sx.get("answered"): return
        sx["answered"] = True
        sx["wrong"] += 1
        # Yangi xabar yuborish — edit emas
        await bot.send_message(sx["board_chat_id"],
            f"⏰ Vaqt tugadi!\n✅ To'g'ri: {render_text(str(correct))}")
        await asyncio.sleep(2)
        await _advance(user_id)

    s["timer_task"] = asyncio.create_task(cd())


async def _show_result(user_id, message, result_text):
    s = test_sessions.get(user_id)
    if not s: return
    s["answered"] = True
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None

    txt = _board(s, result_text)
    await _send_board(s, txt)
    await asyncio.sleep(2)
    await _advance(user_id)


async def check_button_answer(user_id, answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"): return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None

    test = s["questions"][s["current"]]
    a,b,c,d = test[1],test[2],test[3],test[4]
    correct = str(test[5] or "").strip()
    expl = render_text(str(test[6] or ""))
    sel_map = {"A":str(a),"B":str(b),"C":str(c),"D":str(d)}
    selected = sel_map.get(answer.upper(),"")

    if correct.upper() in ("A","B","C","D"):
        is_ok = answer.upper() == correct.upper()
        correct_show = render_text(sel_map.get(correct.upper(), correct))
    else:
        is_ok = render_text(selected).strip().lower() == render_text(correct).strip().lower()
        correct_show = render_text(correct)

    if is_ok:
        s["correct"] += 1
        result = "🎉 To'g'ri! ✅"
    else:
        s["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri: {correct_show}"
    if expl: result += f"\n\n💡 {expl}"
    await _show_result(user_id, message, result)


async def check_text_answer(user_id, user_answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"): return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None

    test = s["questions"][s["current"]]
    correct = render_text(str(test[5] or "")).strip().lower()
    user_answer = str(user_answer).strip().lower()
    expl = render_text(str(test[6] or ""))

    if user_answer == correct:
        s["correct"] += 1
        result = "🎉 To'g'ri! ✅"
    else:
        s["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri: {render_text(str(test[5]))}"
    if expl: result += f"\n\n💡 {expl}"
    user_state[user_id] = None
    await _show_result(user_id, message, result)


async def next_question(user_id, message=None):
    await _advance(user_id)


async def finish_test(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s: return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
    if user_state.get(user_id) == "text_answer":
        user_state[user_id] = None

    ok, err = s["correct"], s["wrong"]
    total = ok + err
    pct = round(ok*100/total,1) if total else 0
    emoji = "🏆" if pct>=80 else "👍" if pct>=60 else "💪"
    txt = f"{emoji} Test yakunlandi!\n\n✅ To'g'ri: {ok}\n❌ Noto'g'ri: {err}\n📊 Natija: {pct}%"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Bosh menyuga qaytish", callback_data="go_home_dashboard")
    ]])
    chat = s.get("board_chat_id")
    mid  = s.get("board_msg_id")
    try:
        if mid: await bot.edit_message_text(txt, chat_id=chat, message_id=mid, reply_markup=kb)
        else: await bot.send_message(chat, txt, reply_markup=kb)
    except:
        try: await bot.send_message(chat, txt, reply_markup=kb)
        except: pass
    test_sessions.pop(user_id, None)


async def stop_test(user_id, message):
    await finish_test(user_id, message)


async def speak_text(user_id, message, text):
    s = test_sessions.get(user_id)
    lang = "uz"
    if s:
        try: lang = str(s["questions"][s["current"]][11]).lower()
        except: pass
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT gender FROM users WHERE user_id=%s", (user_id,))
        row = cur.fetchone(); cur.close(); conn.close()
        gender = row[0] if row else ""
    except: gender = ""
    voices = {
        "uz": "uz-UZ-MadinaNeural" if "Ayol" in str(gender) else "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural", "ru": "ru-RU-DmitryNeural",
    }
    clean = tts_clean(text)
    if not clean or not any(c.isalnum() for c in clean): return
    fname = f"tts_{user_id}.mp3"
    try:
        comm = edge_tts.Communicate(text=clean, voice=voices.get(lang, voices["uz"]))
        await comm.save(fname)
        if os.path.exists(fname) and os.path.getsize(fname) > 0:
            vm = await message.answer_voice(FSInputFile(fname))
            sx = test_sessions.get(user_id)
            if sx: sx.setdefault("voice_msgs", []).append(vm.message_id)
    except: pass
    finally:
        try: os.remove(fname)
        except: pass


async def speak_question(user_id, message):
    s = test_sessions.get(user_id)
    if s: await speak_text(user_id, message, s["questions"][s["current"]][0])

async def speak_a(user_id, message):
    s = test_sessions.get(user_id)
    if s: await speak_text(user_id, message, s["questions"][s["current"]][1])

async def speak_b(user_id, message):
    s = test_sessions.get(user_id)
    if s: await speak_text(user_id, message, s["questions"][s["current"]][2])

async def speak_c(user_id, message):
    s = test_sessions.get(user_id)
    if s: await speak_text(user_id, message, s["questions"][s["current"]][3])

async def speak_d(user_id, message):
    s = test_sessions.get(user_id)
    if s: await speak_text(user_id, message, s["questions"][s["current"]][4])


def latex_to_image(latex_text, filename):
    try:
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(6, 2))
        plt.text(0.05, 0.5, f"${latex_text}$", fontsize=24)
        plt.axis("off")
        plt.savefig(filename, bbox_inches="tight", dpi=150)
        plt.close(fig)
    except: pass
