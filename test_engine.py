from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile,
    InputMediaPhoto
)
import edge_tts, asyncio, psycopg2, os, re
from storage import user_state
from loader import bot

DATABASE_URL = os.getenv("DATABASE_URL")
test_sessions = {}
HOME_BTN = [InlineKeyboardButton(text="🏠 Bosh ekran", callback_data="go_home_dashboard")]

# ─────────────── text helpers ───────────────
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

# ─────────────── progress board ───────────────
def _board(s, extra=""):
    total = len(s["questions"])
    ok, err = s["correct"], s["wrong"]
    done = ok + err
    bar = "🟩"*ok + "🟥"*err + "⬜"*max(0, min(20, total) - done)
    h = f"📊 {done}/{total} | ✅ {ok} | ❌ {err}\n{bar}\n━━━━━━━━━━━━━━"
    return h + "\n\n" + extra if extra else h

# ─────────────── smart answer keyboard ───────────────
# Kalta javoblar (≤18 belgi) — 2 ustun chap tugma + 🔊 o'ng
# Uzun javoblar          — bitta qator (to'liq kenglik)
def _build_kb(a, b, c, d, tl=0):
    t = f"⏱ {tl}s" if tl > 0 else "∞"
    ctrl = [
        InlineKeyboardButton(text="🔊", callback_data="speak_question"),
        InlineKeyboardButton(text=t,    callback_data="noop_timer"),
        InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop"),
    ]
    rows = [ctrl]
    for ans, cb, spk in [
        (a, "ans_A", "speak_a"),
        (b, "ans_B", "speak_b"),
        (c, "ans_C", "speak_c"),
        (d, "ans_D", "speak_d"),
    ]:
        label = str(ans) if ans else "—"
        if len(label) <= 18:
            rows.append([
                InlineKeyboardButton(text=label, callback_data=cb),
                InlineKeyboardButton(text="🔊",  callback_data=spk),
            ])
        else:
            rows.append([InlineKeyboardButton(text=label, callback_data=cb)])
            rows.append([InlineKeyboardButton(text="🔊",  callback_data=spk)])
    rows.append(HOME_BTN)
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ─────────────── rasmni cache'dan olish ───────────────
async def _get_file_id(img_url):
    """img_url bo'yicha images jadvalidan file_id qaytaradi."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (img_url.strip(),))
        row = cur.fetchone(); cur.close(); conn.close()
        return row[0] if row else None
    except:
        return None

# ─────────────── bitta xabarni yangilash ───────────────
async def _update_msg(s, text, kb, photo=None):
    """
    photo = file_id / FSInputFile yoki None.
    Agar photo bo'lsa → send_photo (birinchi marta) yoki edit_message_media.
    Bo'lmasa → edit_message_text.
    Barcha narsa bitta board_msg_id ga yoziladi — xabar uchib-chiqmaydi.
    """
    chat = s["board_chat_id"]
    mid  = s.get("board_msg_id")

    if photo:
        media = InputMediaPhoto(media=photo, caption=text)
        if s.get("board_has_photo") and mid:
            try:
                await bot.edit_message_media(
                    chat_id=chat, message_id=mid, media=media, reply_markup=kb
                )
                return
            except Exception:
                pass
        # Yangi rasm xabari yuboramiz (birinchi marta yoki xato bo'lsa)
        if mid:
            try: await bot.delete_message(chat, mid)
            except: pass
        nm = await bot.send_photo(chat, photo, caption=text, reply_markup=kb)
        s["board_msg_id"]   = nm.message_id
        s["board_has_photo"] = True
    else:
        # Oldingi xabar rasm bo'lgan bo'lsa, uni o'chir
        if s.get("board_has_photo") and mid:
            try: await bot.delete_message(chat, mid)
            except: pass
            mid = None
        if mid:
            try:
                await bot.edit_message_text(
                    text=text, chat_id=chat, message_id=mid, reply_markup=kb
                )
                s["board_has_photo"] = False
                return
            except Exception:
                pass
        nm = await bot.send_message(chat, text, reply_markup=kb)
        s["board_msg_id"]   = nm.message_id
        s["board_has_photo"] = False

# ─────────────── test boshlash ───────────────
async def start_test(user_id, tests, message):
    if not tests:
        await message.answer("❌ Test topilmadi")
        return
    old = test_sessions.get(user_id, {})
    if old.get("timer_task"):
        try: old["timer_task"].cancel()
        except: pass

    # 25 xabar o'chirmaydi — faqat "yuklanmoqda" xabarini yuboramiz
    user_state[user_id] = "in_test"          # yozishni bloklaydi
    msg = await message.answer("⏳ Test yuklanmoqda...")
    test_sessions[user_id] = {
        "questions":   tests,
        "current":     0,
        "correct":     0,
        "wrong":       0,
        "timer_task":  None,
        "board_msg_id":   msg.message_id,
        "board_chat_id":  msg.chat.id,
        "board_has_photo": False,
        "voice_msgs":  [],
        "answered":    False,
    }
    await show_question(user_id)

# ─────────────── savolni ko'rsatish ───────────────
async def show_question(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s: return

    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    s["answered"] = False

    # eski ovozlarni o'chir
    chat = s["board_chat_id"]
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

    try: tl = int(tl) if tl and int(tl) > 0 else 0
    except: tl = 0
    s["time_left"] = tl

    header = _board(s)

    # ── Rasmni aniqlash ──
    photo = None
    if is_latex and str(is_latex).lower() not in ("false", "0", "none", ""):
        try:
            from latex_utils import latex_to_image as l2i
            p = l2i(q, user_id)
            if p and os.path.exists(p):
                photo = FSInputFile(p)
        except: pass
    elif img_url and str(img_url).strip() not in ("", "None", "nan"):
        photo = await _get_file_id(img_url)

    # ── Yozma savol ──
    if qtype == "write_answer":
        user_state[user_id] = "text_answer"
        tmr = f"⏱ {tl}s" if tl > 0 else "∞"
        text = (f"{header}\n\n✍️ Savol {cur+1}/{total}\n\n{q_s}"
                f"\n\n📝 Javobingizni yozing:")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔊", callback_data="speak_question"),
             InlineKeyboardButton(text=tmr,  callback_data="noop_timer"),
             InlineKeyboardButton(text="🛑 Stop", callback_data="test_stop")],
            HOME_BTN,
        ])
        await _update_msg(s, text, kb, photo)
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
                await _advance(user_id)
            s["timer_task"] = asyncio.create_task(write_cd())
        return

    user_state[user_id] = "in_test"
    text = f"{header}\n\n🧪 Savol {cur+1}/{total}\n\n{q_s}"
    kb   = _build_kb(a_s, b_s, c_s, d_s, tl)
    await _update_msg(s, text, kb, photo)

    if tl <= 0: return

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
        await _advance(user_id)
    s["timer_task"] = asyncio.create_task(cd())

# ─────────────── natijani ko'rsatish ───────────────
async def _show_result(user_id, message, result_text):
    s = test_sessions.get(user_id)
    if not s: return
    s["answered"] = True
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    txt = _board(s, result_text)
    # Natijada rasm shart emas — faqat tekst
    await _update_msg(s, txt, None)
    await asyncio.sleep(1.5)
    await _advance(user_id)

async def _advance(user_id):
    s = test_sessions.get(user_id)
    if not s: return
    s["current"] += 1
    if s["current"] >= len(s["questions"]):
        await finish_test(user_id)
    else:
        await show_question(user_id)

# ─────────────── javob tekshirish ───────────────
async def check_button_answer(user_id, answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"): return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    test = s["questions"][s["current"]]
    a,b,c,d   = test[1],test[2],test[3],test[4]
    correct   = str(test[5] or "").strip()
    expl      = render_text(str(test[6] or ""))
    sel_map   = {"A":str(a),"B":str(b),"C":str(c),"D":str(d)}
    selected  = sel_map.get(answer.upper(),"")
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
    test    = s["questions"][s["current"]]
    correct = render_text(str(test[5] or "")).strip().lower()
    user_answer = str(user_answer).strip().lower()
    expl    = render_text(str(test[6] or ""))
    if user_answer == correct:
        s["correct"] += 1
        result = "🎉 To'g'ri! ✅"
    else:
        s["wrong"] += 1
        result = f"❌ Xato!\n✅ To'g'ri: {render_text(str(test[5]))}"
    if expl: result += f"\n\n💡 {expl}"
    user_state[user_id] = None
    await _show_result(user_id, message, result)

# ─────────────── test tugash / to'xtatish ───────────────
async def next_question(user_id, message=None):
    await _advance(user_id)

async def finish_test(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s: return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
    user_state[user_id] = None
    ok, err = s["correct"], s["wrong"]
    total   = ok + err
    pct     = round(ok*100/total, 1) if total else 0
    emoji   = "🏆" if pct>=80 else "👍" if pct>=60 else "💪"
    txt = (f"{emoji} Test yakunlandi!\n\n"
           f"✅ To'g'ri:   {ok}\n"
           f"❌ Noto'g'ri: {err}\n"
           f"📊 Natija:    {pct}%")
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Bosh menyuga qaytish", callback_data="go_home_dashboard")
    ]])
    await _update_msg(s, txt, kb)
    test_sessions.pop(user_id, None)

async def stop_test(user_id, message):
    await finish_test(user_id, message)

# ─────────────── TTS ───────────────
async def speak_text(user_id, message, text):
    s    = test_sessions.get(user_id)
    lang = "uz"
    if s:
        try: lang = str(s["questions"][s["current"]][11]).lower()
        except: pass
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT gender FROM users WHERE user_id=%s", (user_id,))
        row  = cur.fetchone(); cur.close(); conn.close()
        gender = row[0] if row else ""
    except: gender = ""
    voices = {
        "uz": "uz-UZ-MadinaNeural" if "Ayol" in str(gender) else "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural",
        "ru": "ru-RU-DmitryNeural",
    }
    import re as _re
    from pydub import AudioSegment as _AS
    _pts  = _re.split(r'\[en\](.*?)\[/en\]', str(text), flags=_re.DOTALL)
    _segs = []
    for _i, _p in enumerate(_pts):
        _cl = tts_clean(_p) if _i % 2 == 0 else _p.strip()
        _cl = _re.sub(r'\s+', ' ', _cl).strip()
        if not _cl or not any(_c.isalnum() for _c in _cl): continue
        _v  = voices["en"] if _i % 2 == 1 else voices.get(lang, voices["uz"])
        _segs.append((_cl, _v))
    if not _segs: return
    _comb = _AS.silent(duration=0)
    for _st, _sv in _segs:
        _tmp = f"tts_tmp_{user_id}_{abs(hash(_st))}.mp3"
        try:
            _comm = edge_tts.Communicate(text=_st, voice=_sv)
            await _comm.save(_tmp)
            if os.path.exists(_tmp) and os.path.getsize(_tmp) > 0:
                _comb += _AS.from_mp3(_tmp)
        except: pass
        finally:
            try: os.remove(_tmp)
            except: pass
    if len(_comb) == 0: return
    fname = f"tts_{user_id}.mp3"
    try:
        _comb.export(fname, format="mp3")
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
