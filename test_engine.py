"""
test_engine.py — Test tizimi
Ikki xabar: board (statistika) + q_msg (savol+tugmalar)
Natija: tugmalar o'rnida ✅/❌, izoh savol o'rnida, 4s turadi
"""
import os, asyncio, re, psycopg2
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, FSInputFile, BufferedInputFile
)
from loader import bot
from storage import user_state, test_sessions

DATABASE_URL = os.getenv("DATABASE_URL")

# ── Matnni tozalash ──
def render_text(t):
    """Matnni ko'rsatish uchun: [en]...[/en] → yotiq (italic)."""
    if not t: return ""
    t = str(t)
    t = re.sub(r'\[uz\](.*?)\[/uz\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[en\](.*?)\[/en\]', r'_\1_', t, flags=re.DOTALL)  # italic
    t = re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', t, flags=re.DOTALL)
    return t.strip()

def _tts_clean(t):
    """TTS uchun math va tinish belgilarini o'zbek tilida o'qitish."""
    if not t: return ""
    t = str(t).strip()
    t = re.sub(r'\[en\](.*?)\[/en\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[uz\](.*?)\[/uz\]', r'\1', t, flags=re.DOTALL)
    t = re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', t, flags=re.DOTALL)
    # Math belgilarini o'zbek tilida
    t = t.replace("×", " ko'paytirish ").replace("·", " ko'paytirish ")
    t = t.replace("÷", " bo'lish ")
    t = t.replace(" + ", " qo'shish ").replace("+", " qo'shish ")
    t = t.replace(" - ", " ayirish ")
    t = t.replace("= ?", " teng nima").replace("=?", " teng nima")
    t = t.replace("= ...", " teng nima").replace("=…", " teng nima")
    t = t.replace(" = ", " teng ").replace("=", " teng ")
    t = t.replace("?", " nima").replace("…", " ").replace("...", " ")
    t = t.replace("²", " kvadrat").replace("³", " kub")
    t = t.replace("√", " ildiz ").replace("%", " foiz")
    # Kasr: 1/2 → bir ikkinchi
    def kasr(m):
        suf={"2":"ikkinchi","3":"uchdan bir","4":"to'rtdan bir","5":"beshdаn bir","10":"o'ndan bir"}
        n,d=m.group(1),m.group(2)
        return f"{n} {suf.get(d, d+'-dan bir')}"
    t = re.sub(r'\b(\d+)/(\d+)\b', kasr, t)
    t = re.sub(r'[\-=#@!*]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _has_en(t):
    return '[en]' in str(t)

# ── Statistika xabari ──
def _board_text(s, result=""):
    total = len(s["questions"])
    ok, err = s["correct"], s["wrong"]
    done = ok + err
    bar = "🟩"*ok + "🟥"*err + "⬜"*max(0, min(20,total)-done)
    t = f"📊 {done}/{total} | ✅ {ok} | ❌ {err}\n{bar}"
    if result:
        t += f"\n{'━'*18}\n{result}\n{'━'*18}"
    return t

# ── Savol klaviaturasi ──
def _build_kb(a, b, c, d, tl=0):
    timer = f"⏱ {tl}s" if tl > 0 else "∞"
    rows = [[
        InlineKeyboardButton(text="🔊 O'qib berish", callback_data="speak_all"),
        InlineKeyboardButton(text=timer,              callback_data="noop_timer"),
        InlineKeyboardButton(text="🛑",               callback_data="test_stop"),
    ]]
    for num, (ans, cb) in enumerate([(a,"ans_A"),(b,"ans_B"),(c,"ans_C"),(d,"ans_D")], 1):
        label = str(ans) if ans else "—"
        rows.append([InlineKeyboardButton(text=f"{num}) {label}", callback_data=cb)])
    rows.append([InlineKeyboardButton(text="⏭ O'tkazish", callback_data="test_skip")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── DB dan rasm ──
async def _get_file_id(img_url):
    if not img_url or str(img_url).strip() in ("", "None", "nan"): return None
    name = str(img_url).strip()
    m = re.match(r'^(.+)-(\d+)$', name)
    if m:
        base, num = m.group(1), m.group(2)
        variants = [name, f"{base}-t-{num}", f"{base}-p-{num}"]
    else:
        variants = [name]
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        ph = ",".join(["%s"] * len(variants))
        cur.execute(f"SELECT file_id FROM images WHERE name IN ({ph}) LIMIT 1", variants)
        row = cur.fetchone(); cur.close(); conn.close()
        return row[0] if row else None
    except: return None


async def _photo_for(test, user_id=None):
    (q,a,b,c,d,correct,expl,qtype,is_latex,img_url,audio,lang,tl) = test
    # LaTeX rasm
    if is_latex and str(is_latex).lower() not in ("false","0","none",""):
        try:
            from latex_utils import latex_to_image as l2i
            p = l2i(q, user_id or 0)
            if p and os.path.exists(p): return FSInputFile(p)
        except: pass
    # image_url bo'yicha
    if img_url and str(img_url).strip() not in ("","None","nan"):
        url_str = str(img_url).strip()
        # LaTeX formula — rasm sifatida ko'rsat
        if url_str.startswith("$") or url_str.startswith("\\") or "$" in url_str:
            try:
                import matplotlib; matplotlib.use("Agg")
                import matplotlib.pyplot as plt, io as _io
                parts = url_str.split("$")
                fig = plt.figure(figsize=(8, 2))
                fig.patch.set_facecolor("white")
                ax = fig.add_axes([0,0,1,1]); ax.axis("off")
                ax.set_xlim(0,10); ax.set_ylim(0,2)
                x = 0.2; y = 1.0
                for idx, part in enumerate(parts):
                    if not part.strip(): continue
                    if idx % 2 == 0:
                        t = ax.text(x, y, part, fontsize=18, va="center",
                                   ha="left", color="black")
                    else:
                        t = ax.text(x, y, f"${part}$", fontsize=20,
                                   va="center", ha="left", color="#1a1a8c")
                    fig.canvas.draw()
                    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
                    x += bb.width/(fig.dpi*fig.get_figwidth()/10) + 0.1
                buf = _io.BytesIO()
                plt.savefig(buf, format="png", dpi=150,
                           bbox_inches="tight", facecolor="white", pad_inches=0.2)
                plt.close(); buf.seek(0)
                from aiogram.types import BufferedInputFile
                return BufferedInputFile(buf.read(), "formula.png")
            except: pass
        fid = await _get_file_id(url_str)
        if fid: return fid
    # Session topic_code + savol tartib raqami
    if user_id:
        from storage import test_sessions as _ts
        s = _ts.get(user_id)
        if s:
            tc  = s.get("topic_code","")
            cur = s.get("current", 0)
            n   = cur + 1
            if tc:
                # TC-N, TC-t-N, TC-p-N formatlarini sinab ko'ramiz
                for fmt in [f"{tc}-{n}", f"{tc}-t-{n}", f"{tc}-p-{n}"]:
                    fid = await _get_file_id(fmt)
                    if fid: return fid
    return None

# ── Xabar yuborish/edit ──
async def _edit_board(s, text):
    chat = s["board_chat_id"]
    mid  = s.get("board_msg_id")
    if mid:
        try:
            await bot.edit_message_text(text=text, chat_id=chat, message_id=mid)
            return
        except: pass
    nm = await bot.send_message(chat, text)
    s["board_msg_id"] = nm.message_id

async def _edit_question(s, q_text, kb, photo=None):
    chat = s["board_chat_id"]
    qmid = s.get("q_msg_id")
    if photo:
        cap = q_text[:1020]
        if s.get("q_has_photo") and qmid:
            try:
                await bot.edit_message_media(
                    chat_id=chat, message_id=qmid,
                    media=InputMediaPhoto(media=photo, caption=cap), reply_markup=kb)
                return
            except: pass
        if qmid:
            try: await bot.delete_message(chat, qmid)
            except: pass
        nm = await bot.send_photo(chat, photo, caption=cap, reply_markup=kb, parse_mode="Markdown")
        s["q_msg_id"] = nm.message_id; s["q_has_photo"] = True
    else:
        if s.get("q_has_photo") and qmid:
            try: await bot.delete_message(chat, qmid)
            except: pass
            qmid = None; s["q_has_photo"] = False
        if qmid:
            try:
                await bot.edit_message_text(text=q_text, chat_id=chat, message_id=qmid, reply_markup=kb, parse_mode="Markdown")
                return
            except:
                try: await bot.delete_message(chat, qmid)
                except: pass
                s["q_msg_id"] = None
        nm = await bot.send_message(chat, q_text, reply_markup=kb, parse_mode="Markdown")
        s["q_msg_id"] = nm.message_id; s["q_has_photo"] = False

# ── Ovoz ──
async def _stop_voice(s):
    """Avvalgi ovoz xabarini o'chirish."""
    chat = s.get("board_chat_id")
    for vid in s.get("voice_msgs", []):
        try: await bot.delete_message(chat, vid)
        except: pass
    s["voice_msgs"] = []

async def _tts_send(s, text, voice="uz-UZ-MadinaNeural"):
    """Matnni TTS ga berib ovoz yuborish."""
    try:
        import edge_tts
        from pydub import AudioSegment as AS
        from io import BytesIO
        clean = _tts_clean(text)
        if not clean.strip(): return
        fname = f"tts_{s.get('board_chat_id',0)}.mp3"
        await edge_tts.Communicate(text=clean[:400], voice=voice).save(fname)
        if not os.path.exists(fname) or os.path.getsize(fname) < 100: return
        nm = await bot.send_voice(s["board_chat_id"], FSInputFile(fname))
        s.setdefault("voice_msgs", []).append(nm.message_id)
    except Exception as e:
        print(f"TTS xato: {e}")
    finally:
        try: os.remove(fname)
        except: pass

async def speak_all_question(user_id):
    """Bitta audioda: savol → 1. A → 2. B → 3. C → 4. D"""
    try:
        import edge_tts
        from pydub import AudioSegment as AS
        from io import BytesIO

        s = test_sessions.get(user_id)
        if not s: return
        test = s["questions"][s["current"]]
        q,a,b,c,d = test[0],test[1],test[2],test[3],test[4]

        uz_voice = "uz-UZ-MadinaNeural"
        en_voice = "en-US-AriaNeural"

        # Keng O'zbek so'zlari ro'yxati
        UZ_WORDS = {
            "men","sen","u","biz","siz","ular","bu","shu","ha","yo'q",
            "va","lekin","ham","emas","bor","yo","yoki","uchun","bilan",
            "nima","qanday","qaysi","qachon","kim","qancha","qayer",
            "oila","ota","ona","bola","do'st","sinf","maktab","dars",
            "kitob","qalam","uy","shahar","ko'cha","bog'","daryo",
            "katta","kichik","yaxshi","yomon","yangi","eski","baland",
            "olma","non","suv","osh","go'sht","sabzi","tarvuz",
            "qizil","ko'k","yashil","sariq","oq","qora","ko'p","oz",
            "bir","ikki","uch","to'rt","besh","olti","yetti","sakkiz",
        }

        def pick_voice(raw_text):
            if _has_en(str(raw_text)): return en_voice
            clean = _tts_clean(str(raw_text)).lower()
            words = set(clean.split())
            # O'zbek so'zlari ko'p bo'lsa — o'zbek
            uz_cnt = len(words & UZ_WORDS)
            if uz_cnt >= 1: return uz_voice
            # Kirill harflari
            if any(c in "абвгдежзийклмнопрстуфхцчшщъыьэюя" for c in clean):
                return "ru-RU-DmitryNeural"
            # Faqat ingliz so'zlari bo'lsa
            en_chars = sum(1 for c in clean if c.isascii() and c.isalpha())
            all_chars = sum(1 for c in clean if c.isalpha())
            if all_chars > 3 and en_chars / all_chars > 0.90:
                return en_voice
            return uz_voice

        def split_by_lang(raw_text):
            """Matnni til bo'yicha bo'laklarga ajratadi."""
            import re
            if not raw_text: return []
            segments = []
            # [en]...[/en] va [ru]...[/ru] teglarini topamiz
            pattern = r'(\[en\](.*?)\[/en\]|\[ru\](.*?)\[/ru\])'
            last = 0
            for m in re.finditer(pattern, str(raw_text), re.DOTALL):
                # Tegdan oldingi uz matni
                before = raw_text[last:m.start()].strip()
                if before: segments.append((before, uz_voice))
                # Teglangan qism
                if m.group(0).startswith('[en]'):
                    segments.append((m.group(2), en_voice))
                else:
                    segments.append((m.group(3), "ru-RU-DmitryNeural"))
                last = m.end()
            # Qolgan qism
            rest = raw_text[last:].strip()
            if rest: segments.append((rest, uz_voice))
            return segments if segments else [(raw_text, uz_voice)]

        parts = []
        # Savol — til bo'yicha bo'laklarga ajratamiz
        for seg_text, seg_voice in split_by_lang(q):
            clean = _tts_clean(seg_text)
            if clean: parts.append((clean, seg_voice))
        # Javoblar
        for num, opt in enumerate([a,b,c,d], 1):
            txt = _tts_clean(str(opt or ""))
            if txt:
                seg_parts = split_by_lang(str(opt or ""))
                for seg_text, seg_voice in seg_parts:
                    clean = _tts_clean(seg_text)
                    if clean: parts.append((f"{num}. {clean}" if seg_text==str(opt or "").strip() else clean, seg_voice))

        combined = AS.silent(200)
        for text, voice in parts:
            if not text.strip(): continue
            tmp = f"tts_p_{user_id}_{abs(hash(text)%99999)}.mp3"
            try:
                await edge_tts.Communicate(text=text[:300], voice=voice).save(tmp)
                if os.path.exists(tmp) and os.path.getsize(tmp) > 100:
                    combined += AS.from_mp3(tmp)
                    combined += AS.silent(350)
            except: pass
            finally:
                try: os.remove(tmp)
                except: pass

        if len(combined) < 300: return
        # Avvalgi ovozni o'chirish
        await _stop_voice(s)
        fname = f"tts_q_{user_id}.mp3"
        combined.export(fname, format="mp3")
        nm = await bot.send_voice(s["board_chat_id"], FSInputFile(fname))
        s.setdefault("voice_msgs", []).append(nm.message_id)
    except Exception as e:
        print(f"speak_all xato: {e}")
    finally:
        try: os.remove(fname)
        except: pass

# ── Test boshlash ──
async def start_test(user_id, tests, message, timed=True):
    if not tests:
        await message.answer("❌ Test topilmadi"); return
    old = test_sessions.get(user_id, {})
    if old.get("timer_task"):
        try: old["timer_task"].cancel()
        except: pass
    user_state[user_id] = "in_test"

    bm = await message.answer("⏳ Test yuklanmoqda...")
    qm = await message.answer("...")

    test_sessions[user_id] = {
        "questions":     tests, "current": 0,
        "correct":       0,     "wrong":   0,
        "timer_task":    None,
        "board_chat_id": message.chat.id,
        "board_msg_id":  bm.message_id,
        "q_msg_id":      qm.message_id,
        "q_has_photo":   False,
        "voice_msgs":    [], "answered": False,
        "topic_code":    "",
        "timed":         timed,
    }
    await show_question(user_id)

# ── Savolni ko'rsatish ──
async def show_question(user_id, message=None):
    s = test_sessions.get(user_id)
    if not s: return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    s["answered"] = False

    # Avvalgi ovozni o'chirish
    await _stop_voice(s)

    cur   = s["current"]
    total = len(s["questions"])
    test  = s["questions"][cur]
    (q,a,b,c,d,correct,expl,qtype,is_latex,img_url,audio,lang,tl) = test
    q_s = render_text(q)
    a_s = render_text(str(a or ""))
    b_s = render_text(str(b or ""))
    c_s = render_text(str(c or ""))
    d_s = render_text(str(d or ""))
    try: tl = int(tl) if tl and int(tl) > 0 else 0
    except: tl = 0
    # Yozma savollarda default 60 sekund
    if qtype == "write_answer" and tl == 0:
        tl = 60
    # ts_timed=False bo'lsa timer o'chiq
    if not s.get("timed", True):
        tl = 0

    photo = await _photo_for(test, user_id)

    await _edit_board(s, _board_text(s))
    await asyncio.sleep(0.2)

    if qtype == "write_answer":
        user_state[user_id] = "text_answer"
        tmr = f"⏱ {tl}s" if tl > 0 else "∞"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔊 O'qib berish", callback_data="speak_all"),
             InlineKeyboardButton(text=tmr,               callback_data="noop_timer"),
             InlineKeyboardButton(text="🛑",              callback_data="test_stop")],
        ])
        q_text = f"✍️ {cur+1}/{total}\n\n{q_s}\n\n📝 Javobingizni yozing:"
        await _edit_question(s, q_text, kb, photo)
        asyncio.create_task(speak_all_question(user_id))
        if tl > 0:
            async def write_cd():
                left = tl
                while left > 0:
                    await asyncio.sleep(5); left = max(0, left-5)
                    sx = test_sessions.get(user_id)
                    if not sx or sx.get("answered"): return
                    # Timer tugmasini yangilash
                    try:
                        new_kb = InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(text="🔊 O'qib berish", callback_data="speak_all"),
                            InlineKeyboardButton(text=f"⏱ {left}s", callback_data="noop_timer"),
                            InlineKeyboardButton(text="🛑", callback_data="test_stop"),
                        ]])
                        await bot.edit_message_reply_markup(
                            chat_id=sx["board_chat_id"], message_id=sx["q_msg_id"],
                            reply_markup=new_kb)
                    except: pass
                sx = test_sessions.get(user_id)
                if not sx or sx.get("answered"): return
                sx["answered"] = True; sx["wrong"] += 1
                sx["timer_task"] = None; user_state[user_id] = "in_test"
                await _edit_board(sx, _board_text(sx, "⏱ Vaqt tugadi!"))
                await asyncio.sleep(1.5)
                if test_sessions.get(user_id): await _advance(user_id)
            s["timer_task"] = asyncio.create_task(write_cd())
        return

    user_state[user_id] = "in_test"
    kb     = _build_kb(a_s, b_s, c_s, d_s, tl)
    q_text = f"🧪 {cur+1}/{total}\n\n{q_s}"
    await _edit_question(s, q_text, kb, photo)

    # Avto TTS — yangi savol chiqganda o'qiladi
    asyncio.create_task(speak_all_question(user_id))

    if tl <= 0: return
    async def cd():
        left = tl
        while left > 0:
            await asyncio.sleep(5); left = max(0, left-5)
            sx = test_sessions.get(user_id)
            if not sx or sx.get("answered"): return
            if left > 0:
                try:
                    await bot.edit_message_reply_markup(
                        chat_id=sx["board_chat_id"], message_id=sx["q_msg_id"],
                        reply_markup=_build_kb(a_s, b_s, c_s, d_s, left)
                    )
                except: pass
        sx = test_sessions.get(user_id)
        if not sx or sx.get("answered"): return
        sx["answered"] = True; sx["wrong"] += 1; sx["timer_task"] = None
        await _edit_board(sx, _board_text(sx, "⏱ Vaqt tugadi!"))
        await asyncio.sleep(1.5)
        if test_sessions.get(user_id): await _advance(user_id)
    s["timer_task"] = asyncio.create_task(cd())

# ── Natijani ko'rsatish (o'rnida qoladi) ──
async def _show_result(user_id, result_text, result_kb, photo):
    """Natija: izoh savol o'rnida, 4s turadi, keyin keyingi savol."""
    s = test_sessions.get(user_id)
    if not s: return
    s["answered"] = True

    cur   = s["current"]
    total = len(s["questions"])
    test  = s["questions"][cur]
    q_s   = render_text(test[0])
    expl  = render_text(str(test[6] or ""))

    # Board yangilanadi
    await _edit_board(s, _board_text(s, result_text))

    # Savol xabari: natija + izoh (rasm saqlanadi!)
    izoh_text = ""
    if expl:
        izoh_text = f"\n\n💡 {expl}"
    q_text = f"🧪 {cur+1}/{total}\n\n{q_s}{izoh_text}"

    # Rasm saqlansin — photo beramiz
    await _edit_question(s, q_text, result_kb, photo)

    # 4 soniya turadi
    await asyncio.sleep(4.0)
    if not test_sessions.get(user_id): return
    await _advance(user_id)

async def _advance(user_id):
    s = test_sessions.get(user_id)
    if not s: return
    s["current"] += 1
    if s["current"] >= len(s["questions"]):
        await finish_test(user_id)
    else:
        await show_question(user_id)

# ── Tugma javob ──
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
    lab_map   = {k: render_text(str(v or "")) for k,v in sel_map.items()}
    selected  = sel_map.get(answer.upper(),"")

    if correct.upper() in ("A","B","C","D"):
        is_ok = answer.upper() == correct.upper()
        correct_key = correct.upper()
    else:
        is_ok = render_text(selected).strip().lower() == render_text(correct).strip().lower()
        correct_key = None
        for k,v in lab_map.items():
            if v.strip().lower() == render_text(correct).strip().lower():
                correct_key = k; break

    # ── Tugmalarni natija bilan yangilaymiz (o'rnida qoladi) ──
    rows = []
    for num, (k, cb) in enumerate([("A","ans_A"),("B","ans_B"),("C","ans_C"),("D","ans_D")], 1):
        label = lab_map[k]
        if k == answer.upper():
            icon = "✅" if is_ok else "❌"
            rows.append([InlineKeyboardButton(text=f"{icon} {label}", callback_data="noop_result")])
        elif not is_ok and k == correct_key:
            rows.append([InlineKeyboardButton(text=f"🟢 {label}", callback_data="noop_result")])
        else:
            rows.append([InlineKeyboardButton(text=f"  {label}", callback_data="noop_result")])

    # Xato bo'lsa "✏️ Xato" tugmasi
    if not is_ok:
        rows.append([InlineKeyboardButton(text="✏️ Xato test bildirish", callback_data=f"report_test:{s['current']}")])

    result_kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # Darhol tugmalarni yangilaymiz
    try:
        await bot.edit_message_reply_markup(
            chat_id=s["board_chat_id"], message_id=s["q_msg_id"], reply_markup=result_kb
        )
    except: pass

    if is_ok:
        s["correct"] += 1
        result_text = "✅ To'g'ri!"
    else:
        s["wrong"] += 1
        correct_show = lab_map.get(correct_key, render_text(correct)) if correct_key else render_text(correct)
        result_text = f"❌ Xato!  ✅ To'g'ri: {correct_show}"

    # Rasim olinadi (natijada ham ko'rinsin)
    photo = await _photo_for(test, user_id)

    await _show_result(user_id, result_text, result_kb, photo)

# ── Yozma javob ──
async def check_text_answer(user_id, user_answer, message):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"): return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    test    = s["questions"][s["current"]]
    correct = render_text(str(test[5] or "")).strip().lower()
    expl    = render_text(str(test[6] or ""))
    given   = render_text(user_answer.strip()).lower()
    is_ok   = given == correct or correct in given or given in correct

    photo = await _photo_for(test, user_id)
    noop_kb = InlineKeyboardMarkup(inline_keyboard=[])

    if is_ok:
        s["correct"] += 1
        result_text = f"✅ To'g'ri!"
        noop_kb = InlineKeyboardMarkup(inline_keyboard=[])
    else:
        s["wrong"] += 1
        result_text = f"❌ Xato!  ✅ To'g'ri: {render_text(test[5])}"
        noop_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✏️ Xato test bildirish", callback_data=f"report_test:{s['current']}")
        ]])

    s["answered"] = True
    if expl:
        result_text += f"\n\n💡 {expl[:300]}"
    await _edit_board(s, _board_text(s))
    # Yangi xabar yubormasdan mavjud savolni edit qilamiz
    try:
        noop_full = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=result_text[:40], callback_data="noop")
        ]] if len(result_text) < 40 else [])
        await bot.edit_message_text(
            text=result_text[:3000],
            chat_id=s["board_chat_id"],
            message_id=s["q_msg_id"],
            reply_markup=noop_kb
        )
    except:
        pass
    await asyncio.sleep(2)
    if test_sessions.get(user_id):
        await _advance(user_id)

# ── O'tkazib yuborish ──
async def test_skip(user_id):
    s = test_sessions.get(user_id)
    if not s or s.get("answered"): return
    s["answered"] = True; s["wrong"] += 1
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
        s["timer_task"] = None
    await _edit_board(s, _board_text(s, "⏭ O'tkazib yuborildi"))
    await asyncio.sleep(1.5)
    if test_sessions.get(user_id): await _advance(user_id)

# ── Test tugash ──
async def finish_test(user_id, message=None):
    s = test_sessions.pop(user_id, {})
    if not s: return
    if s.get("timer_task"):
        try: s["timer_task"].cancel()
        except: pass
    await _stop_voice(s)
    user_state[user_id] = None
    chat = s.get("board_chat_id")
    if not chat: return

    ok    = s.get("correct", 0)
    err   = s.get("wrong", 0)
    total = ok + err
    pct   = round(ok*100/max(total,1))

    if pct >= 90:   grade = "🏆 A'lo"
    elif pct >= 75: grade = "👍 Yaxshi"
    elif pct >= 50: grade = "📈 Qoniqarli"
    else:           grade = "📚 Mashq kerak"

    text = (
        f"🏁 Test yakunlandi!\n\n"
        f"✅ To'g'ri:  {ok}\n"
        f"❌ Noto'g'ri: {err}\n"
        f"📊 Natija: {pct}%  {grade}\n\n"
        f"{'🟩'*ok}{'🟥'*err}"
    )
    try: await bot.edit_message_text(text=text, chat_id=chat, message_id=s.get("board_msg_id"))
    except: await bot.send_message(chat, text)

    result_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Bosh menyuga qaytish", callback_data="go_home")
    ]])
    try:
        await bot.edit_message_reply_markup(chat_id=chat, message_id=s.get("q_msg_id"), reply_markup=result_kb)
    except: pass

async def stop_test(user_id, message): await finish_test(user_id, message)
async def next_question(user_id, message=None): await _advance(user_id)
async def speak_question(u, m): await speak_all_question(u)

async def speak_text(user_id, message, text):
    """Matnni TTS bilan o'qish (learning.py uchun)."""
    try:
        import edge_tts
        voice = "uz-UZ-MadinaNeural"
        fname = f"tts_st_{user_id}.mp3"
        clean = _tts_clean(text)
        if not clean: return
        await edge_tts.Communicate(text=clean[:400], voice=voice).save(fname)
        if os.path.exists(fname) and os.path.getsize(fname) > 100:
            await message.answer_voice(FSInputFile(fname))
    except Exception as e:
        print(f"speak_text xato: {e}")
    finally:
        try: os.remove(fname)
        except: pass
