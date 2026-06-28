"""
lesson_engine.py — To'liq qayta yozilgan dars tizimi

Oqim:
  intro → part_1..7 → example_1..5 → 5 ta oson test
  [😕 Tushunmadim] → simple_1..7 → ✅ Tushundim → davom

  Har qadam: avto ovoz, rasm (agar bo'lsa), matn
  Bitta xabar (edit) — uchib-chiqmaydi
"""
import asyncio, os, re, psycopg2
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, InputMediaPhoto
)
from storage import lesson_state, user_state
from loader import bot

DATABASE_URL = os.getenv("DATABASE_URL")

LESSON_COLS = [
    "id", "topic_code",
    "intro", "image_intro",
    "part_1", "image_1", "part_2", "image_2", "part_3", "image_3",
    "part_4", "image_4", "part_5", "image_5", "part_6", "image_6", "part_7", "image_7",
    "simple_1", "simple_2", "simple_3", "simple_4",
    "simple_5", "simple_6", "simple_7",
    "example_1", "example_2", "example_3", "example_4", "example_5",
    "image_e_1", "image_e_2", "image_e_3", "image_e_4", "image_e_5",
    "summary",
]

# ─── Matnni tozalash ───
def clean_text(t):
    if not t: return ""
    t = re.sub(r'\[skip\](.*?)\[/skip\]', '', str(t), flags=re.DOTALL)
    t = re.sub(r'\[img\](.*?)\[/img\]',  '', t, flags=re.DOTALL)
    t = re.sub(r'\[latex\](.*?)\[/latex\]', r'[\1]', t, flags=re.DOTALL)
    return t.strip()

def _strip_for_tts(t):
    t = re.sub(r'\[\w+\](.*?)\[/\w+\]', r'\1', str(t), flags=re.DOTALL)
    t = re.sub(r'\[/?\w+\]', '', t)
    t = re.sub(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', ' ', t)
    t = re.sub(r'[•*#|_~`━\-]{2,}', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def tts_segments(text):
    """Matnni (lang, text) bo'laklarga ajratadi."""
    segs = []
    pat = re.compile(r'(\[en\](.*?)\[/en\]|\[ru\](.*?)\[/ru\])', re.DOTALL)
    last = 0
    for m in pat.finditer(text):
        before = _strip_for_tts(text[last:m.start()])
        if before.strip():
            segs.append(('uz', before.strip()))
        if '[en]' in m.group(0):
            t = _strip_for_tts(m.group(2) or '')
            if t: segs.append(('en', t))
        else:
            t = _strip_for_tts(m.group(3) or '')
            if t: segs.append(('ru', t))
        last = m.end()
    after = _strip_for_tts(text[last:])
    if after.strip():
        segs.append(('uz', after.strip()))
    return segs

# ─── Rasm ───
async def _get_image(name):
    if not name or not str(name).strip() or str(name).strip() in ('', 'None', 'nan', 'rasm_nomi'):
        return None
    try:
        c = psycopg2.connect(DATABASE_URL).cursor()
        c.execute("SELECT file_id FROM images WHERE name=%s", (str(name).strip(),))
        r = c.fetchone(); c.close()
        return r[0] if r else None
    except:
        return None

# ─── Qismlarni qurish ───
def build_lesson_data(row):
    """lesson qatoridan main_parts va simple_parts ajratadi."""
    d = dict(zip(LESSON_COLS, row))
    def v(k): return str(d.get(k) or '').strip()

    main_parts = []

    # Kirish
    if v('intro'):
        main_parts.append({'label': '📖 Kirish', 'text': v('intro'), 'image': v('image_intro')})

    # Qismlar
    for i in range(1, 8):
        if v(f'part_{i}'):
            main_parts.append({'label': f'📘 {i}-qism', 'text': v(f'part_{i}'), 'image': v(f'image_{i}')})

    # Misollar
    for i in range(1, 6):
        if v(f'example_{i}'):
            main_parts.append({'label': f'📌 {i}-misol', 'text': v(f'example_{i}'), 'image': v(f'image_e_{i}')})

    # Simple (tushuntirish) — alohida
    simple_parts = []
    for i in range(1, 8):
        if v(f'simple_{i}'):
            simple_parts.append({'label': f'💡 Tushuntirish', 'text': v(f'simple_{i}'), 'image': ''})

    return main_parts, simple_parts

# ─── Xabarni yangilash ───
async def _send_or_edit(chat_id, uid, text, kb, photo=None):
    """Bitta xabarni edit yoki qayta yaratadi."""
    st = lesson_state.setdefault(uid, {})
    mid = st.get('lesson_msg_id')
    has_photo = st.get('lesson_has_photo', False)

    if photo:
        media = InputMediaPhoto(media=photo, caption=text[:1024])
        if has_photo and mid:
            try:
                await bot.edit_message_media(chat_id=chat_id, message_id=mid, media=media, reply_markup=kb)
                return
            except: pass
        if mid:
            try: await bot.delete_message(chat_id, mid)
            except: pass
        msg = await bot.send_photo(chat_id, photo, caption=text[:1024], reply_markup=kb)
        st['lesson_msg_id'] = msg.message_id
        st['lesson_has_photo'] = True
    else:
        if has_photo and mid:
            try: await bot.delete_message(chat_id, mid)
            except: pass
            mid = None
            st['lesson_has_photo'] = False
        if mid:
            try:
                await bot.edit_message_text(text=text[:4096], chat_id=chat_id, message_id=mid, reply_markup=kb)
                return
            except:
                try: await bot.delete_message(chat_id, mid)
                except: pass
        msg = await bot.send_message(chat_id, text[:4096], reply_markup=kb)
        st['lesson_msg_id'] = msg.message_id
        st['lesson_has_photo'] = False

# ─── Klaviatura ───
def _main_kb(step, total, has_simple):
    rows = []
    nav = []
    if step > 0:
        nav.append(InlineKeyboardButton(text='◀️ Oldingi', callback_data='lesson_prev'))
    if step < total - 1:
        nav.append(InlineKeyboardButton(text='▶️ Keyingi', callback_data='lesson_next'))
    else:
        nav.append(InlineKeyboardButton(text='✅ Tugatish', callback_data='lesson_finish_confirm'))
    rows.append(nav)

    row2 = [InlineKeyboardButton(text='🔊 Eshitish', callback_data='lesson_speak')]
    if has_simple:
        row2.append(InlineKeyboardButton(text='😕 Tushunmadim', callback_data='lesson_help'))
    rows.append(row2)
    rows.append([InlineKeyboardButton(text='🛑 Chiqish', callback_data='lesson_exit')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _simple_kb(step, total):
    rows = []
    nav = []
    if step > 0:
        nav.append(InlineKeyboardButton(text='◀️ Oldingi izoh', callback_data='lesson_help_prev'))
    if step < total - 1:
        nav.append(InlineKeyboardButton(text='▶️ Keyingi izoh', callback_data='lesson_help_next'))
    rows.append(nav) if nav else None
    rows.append([InlineKeyboardButton(text='✅ Tushundim — davom', callback_data='lesson_help_close')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ─── Progress bar ───
def _progress(step, total):
    filled = round((step + 1) / total * 8) if total else 0
    return '🟩' * filled + '⬜' * (8 - filled)

# ─── Header ───
def _header(full_name, fan, mavzu, step, total, label):
    pr = _progress(step, total)
    return (
        f'👤 {full_name}  |  📚 {fan}\n'
        f'📍 {mavzu}\n'
        f'━━━━━━━━━━━━━━\n'
        f'{label}  •  {step+1}/{total}  {pr}\n\n'
    )

# ─── TTS yubor ───
async def _auto_speak(uid, chat_id, text, gender=''):
    """Avto ovoz — fon da ishlaydi, xatoda jim qoladi."""
    try:
        import edge_tts
        from pydub import AudioSegment as AS
        voices = {
            'uz': 'uz-UZ-MadinaNeural' if 'Ayol' in str(gender) else 'uz-UZ-SardorNeural',
            'en': 'en-US-GuyNeural',
            'ru': 'ru-RU-DmitryNeural',
        }
        segs = tts_segments(text)
        if not segs: return
        combined = AS.silent(0)
        for lang, seg in segs:
            voice = voices.get(lang, voices['uz'])
            tmp = f'tts_{uid}_{abs(hash(seg)%99999)}.mp3'
            try:
                await edge_tts.Communicate(text=seg, voice=voice).save(tmp)
                if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                    combined += AS.from_mp3(tmp)
            except: pass
            finally:
                try: os.remove(tmp)
                except: pass
        if len(combined) == 0: return
        fname = f'tts_les_{uid}.mp3'
        combined.export(fname, format='mp3')
        vm = await bot.send_voice(chat_id, FSInputFile(fname))
        # Eski ovozni o'chirish
        st = lesson_state.get(uid, {})
        old = st.get('voice_msg_id') if isinstance(st, dict) else None
        if old:
            try: await bot.delete_message(chat_id, old)
            except: pass
        if isinstance(st, dict):
            st['voice_msg_id'] = vm.message_id
    except Exception:
        pass
    finally:
        try: os.remove(fname)
        except: pass

# ═══════════════════════════════════════════
#  ASOSIY FUNKSIYALAR
# ═══════════════════════════════════════════

async def show_main_step(uid, chat_id):
    """Joriy asosiy qadamni ko'rsatadi + avto ovoz."""
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    parts       = st.get('main_parts', [])
    simples     = st.get('simple_parts', [])
    step        = st.get('main_step', 0)
    full_name   = st.get('full_name', "O'quvchi")
    fan         = st.get('fan', '')
    mavzu       = st.get('mavzu', '')
    gender      = st.get('gender', '')

    if not parts or step >= len(parts): return
    part  = parts[step]
    total = len(parts)
    text  = clean_text(part['text'])
    label = part['label']
    photo = await _get_image(part.get('image', ''))

    header  = _header(full_name, fan, mavzu, step, total, label)
    full    = header + text
    kb      = _main_kb(step, total, bool(simples))

    await _send_or_edit(chat_id, uid, full, kb, photo)

    # Avto ovoz (fon da)
    asyncio.create_task(_auto_speak(uid, chat_id, text, gender))


async def show_simple_step(uid, chat_id):
    """Tushunmadim — joriy simple qadamni ko\'rsatadi. Rasm saqlanadi."""
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    simples   = st.get('simple_parts', [])
    step      = st.get('simple_step', 0)
    full_name = st.get('full_name', "O\'quvchi")
    fan       = st.get('fan', '')
    mavzu     = st.get('mavzu', '')
    gender    = st.get('gender', '')
    if not simples or step >= len(simples): return
    part  = simples[step]
    total = len(simples)
    text  = clean_text(part['text'])
    # Joriy main part rasmi saqlansin
    main_parts = st.get('main_parts', [])
    main_step  = st.get('main_step', 0)
    cur_image  = None
    if main_parts and main_step < len(main_parts):
        cur_image = await _get_image(main_parts[main_step].get('image', ''))
    header = (
        f"👤 {full_name}  |  📚 {fan}\n"
        f"📍 {mavzu}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💡 Tushuntirish  •  {step+1}/{total}  {_progress(step, total)}\n\n"
    )
    kb = _simple_kb(step, total)
    await _send_or_edit(chat_id, uid, header + text, kb, cur_image)
    asyncio.create_task(_auto_speak(uid, chat_id, text, gender))


async def lesson_help_open(uid, chat_id):
    st = lesson_state.setdefault(uid, {})
    if not isinstance(st, dict): return
    simples = st.get('simple_parts', [])
    if not simples:
        await bot.send_message(chat_id, "ℹ️ Bu mavzu uchun qo\'shimcha tushuntirish yo\'q.")
        return
    # Joriy part ga mos simple ni topamiz
    main_parts = st.get('main_parts', [])
    main_step  = st.get('main_step', 0)
    cur_part   = main_parts[main_step] if main_parts and main_step < len(main_parts) else {}
    cur_label  = cur_part.get('label', '')
    # "📘 2-qism" → 2 → simple_parts[1]
    import re as _re
    m = _re.search(r'(\d+)-qism', cur_label)
    matched_idx = 0
    if m:
        part_num = int(m.group(1))
        matched_idx = min(part_num - 1, len(simples) - 1)
    st['simple_step'] = max(0, matched_idx)
    st['mode'] = 'tushunmadim'
    await show_simple_step(uid, chat_id)


async def lesson_next(uid, chat_id):
    st = lesson_state.setdefault(uid, {})
    if not isinstance(st, dict): return
    parts = st.get('main_parts', [])
    step  = st.get('main_step', 0)
    if step + 1 >= len(parts): return
    st['main_step'] = step + 1
    _save_progress(uid, step + 1)
    await show_main_step(uid, chat_id)


async def lesson_prev(uid, chat_id):
    st = lesson_state.setdefault(uid, {})
    if not isinstance(st, dict): return
    step = st.get('main_step', 0)
    if step <= 0: return
    st['main_step'] = step - 1
    _save_progress(uid, step - 1)
    await show_main_step(uid, chat_id)


async def lesson_help_open(uid, chat_id):
    st = lesson_state.setdefault(uid, {})
    if not isinstance(st, dict): return
    if not st.get('simple_parts'):
        await bot.send_message(chat_id, "ℹ️ Bu mavzu uchun qo'shimcha tushuntirish yo'q.")
        return
    st['simple_step'] = 0
    st['mode'] = 'tushunmadim'
    await show_simple_step(uid, chat_id)


async def lesson_help_next(uid, chat_id):
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    simples = st.get('simple_parts', [])
    step    = st.get('simple_step', 0)
    if step + 1 >= len(simples):
        # Oxirgi — asosiy darsga qayt
        st['mode'] = 'main'
        await show_main_step(uid, chat_id)
        return
    st['simple_step'] = step + 1
    await show_simple_step(uid, chat_id)


async def lesson_help_prev(uid, chat_id):
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    step = st.get('simple_step', 0)
    if step <= 0: return
    st['simple_step'] = step - 1
    await show_simple_step(uid, chat_id)


async def lesson_help_close(uid, chat_id):
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    st['mode'] = 'main'
    await show_main_step(uid, chat_id)


async def lesson_speak(uid, chat_id):
    st = lesson_state.get(uid) or {}
    if not isinstance(st, dict): return
    mode   = st.get('mode', 'main')
    gender = st.get('gender', '')
    if mode == 'tushunmadim':
        simples = st.get('simple_parts', [])
        step    = st.get('simple_step', 0)
        text = clean_text(simples[step]['text']) if simples and step < len(simples) else ''
    else:
        parts = st.get('main_parts', [])
        step  = st.get('main_step', 0)
        text = clean_text(parts[step]['text']) if parts and step < len(parts) else ''
    if text:
        await _auto_speak(uid, chat_id, text, gender)


async def lesson_exit(uid, chat_id):
    from keyboards import get_main_keyboard
    lesson_state.pop(uid, None)
    user_state.pop(uid, None)
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("DELETE FROM lesson_progress WHERE user_id=%s", (uid,))
        conn.commit(); cur.close(); conn.close()
    except: pass
    role = "🧒 O'quvchi"
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id=%s", (uid,))
        r = cur.fetchone(); cur.close(); conn.close()
        if r: role = r[0]
    except: pass
    await bot.send_message(chat_id, "🏠 Bosh menyu", reply_markup=get_main_keyboard(role))


async def lesson_finish_and_test(uid, chat_id, topic_code):
    """Dars tugadi → 5 ta oson test boshlash."""
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("""
            SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer, explanation, question_type,
                   is_latex, image_url, audio_text, language, time_limit
            FROM generated_tests
            WHERE topic_code=%s AND difficulty IN ('easy','Easy','oson','Oson')
            ORDER BY RANDOM() LIMIT 5
        """, (topic_code,))
        tests = cur.fetchall()
        if not tests:
            # difficulty bo'lsa ham bo'lmasa oling
            cur.execute("""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type,
                       is_latex, image_url, audio_text, language, time_limit
                FROM generated_tests
                WHERE topic_code=%s
                ORDER BY RANDOM() LIMIT 5
            """, (topic_code,))
            tests = cur.fetchall()
        cur.execute("DELETE FROM lesson_progress WHERE user_id=%s", (uid,))
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Test yuklanmadi: {e}")
        await lesson_exit(uid, chat_id)
        return

    lesson_state.pop(uid, None)
    user_state[uid] = None

    if not tests:
        await bot.send_message(chat_id, "✅ Dars tugadi! Bu mavzu uchun test hali yo'q.")
        await lesson_exit(uid, chat_id)
        return

    await bot.send_message(
        chat_id,
        f"🎉 Dars tugadi! Endi 5 ta savol — bilimingizni tekshiramiz! 🧠"
    )
    from test_engine import start_test
    class FakeMsg:
        def __init__(self, cid, bot_):
            self.chat = type('C', (), {'id': cid})()
            self.bot = bot_
        async def answer(self, *a, **kw):
            return await bot.send_message(self.chat.id, *a, **kw)
    await start_test(uid, tests, FakeMsg(chat_id, bot))


def _save_progress(uid, step):
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute(
            "UPDATE lesson_progress SET current_step=%s WHERE user_id=%s",
            (step, uid)
        )
        conn.commit(); cur.close(); conn.close()
    except: pass


# ─── build_parts (lesson_admin.py uchun qoldirilgan) ───
def build_parts(row):
    main_parts, _ = build_lesson_data(row)
    return main_parts
