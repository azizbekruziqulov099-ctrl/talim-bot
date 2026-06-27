"""
lesson_engine.py — Yangi dars ko'rsatish tizimi
Rasm + matn, dinamik qismlar, to'g'ri TTS
"""
import asyncio, os, re, psycopg2
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, InputMediaPhoto
)
from storage import lesson_state, user_state
from loader import bot

DATABASE_URL = os.getenv("DATABASE_URL")

# ─────────────── Ustun nomlari (tartibda) ───────────────
LESSON_COLS = [
    "id","topic_code",
    "intro","image_intro",
    "part_1","image_1","part_2","image_2","part_3","image_3",
    "part_4","image_4","part_5","image_5","part_6","image_6","part_7","image_7",
    "simple_1","simple_2","simple_3","simple_4",
    "simple_5","simple_6","simple_7",
    "example_1","example_2","example_3","example_4","example_5",
    "summary",
]

PART_LABELS = {
    "intro":   "📖 Kirish",
    "part":    "📘 Qism",
    "simple":  "💡 Sodda tushuntirish",
    "example": "📌 Misol",
    "summary": "📝 Xulosa",
}

# ─────────────── Matnni tozalash ───────────────
def clean_text(text):
    """Ko'rsatish uchun matnni tozalash — teglar saqlanadi."""
    if not text: return ""
    # [skip]...[/skip] olib tashlash
    t = re.sub(r'\[skip\](.*?)\[/skip\]', "", text, flags=re.DOTALL)
    # [img]...[/img] olib tashlash
    t = re.sub(r'\[img\](.*?)\[/img\]', "", t, flags=re.DOTALL)
    # [latex]...[/latex] ni ko'rsatish
    t = re.sub(r'\[latex\](.*?)\[/latex\]', r"[\1]", t, flags=re.DOTALL)
    return t.strip()

def tts_text(text):
    """TTS uchun matnni tozalash — teglar, emoji, maxsus belgilar olib tashlanadi."""
    if not text: return []
    # [en]...[/en] — ingliz tilida o'qish
    # [ru]...[/ru] — rus tilida o'qish
    # Qolgan matn — o'zbek tilida
    # Avval bo'laklarga ajratamiz
    segments = []
    # [en] va [ru] teglarini topamiz
    pattern = re.compile(r'(\[en\](.*?)\[/en\]|\[ru\](.*?)\[/ru\])', re.DOTALL)
    last = 0
    for m in pattern.finditer(text):
        # Tegdan oldingi matn (o'zbek)
        before = text[last:m.start()]
        before = _strip_for_tts(before)
        if before.strip():
            segments.append(("uz", before.strip()))
        # Tegli matn
        if "[en]" in m.group(0):
            en_txt = _strip_for_tts(m.group(2) or "")
            if en_txt.strip():
                segments.append(("en", en_txt.strip()))
        else:
            ru_txt = _strip_for_tts(m.group(3) or "")
            if ru_txt.strip():
                segments.append(("ru", ru_txt.strip()))
        last = m.end()
    # Oxirgi qism
    after = _strip_for_tts(text[last:])
    if after.strip():
        segments.append(("uz", after.strip()))
    return segments

def _strip_for_tts(text):
    """TTS uchun barcha teglar, emoji, maxsus belgilarni olib tashlash."""
    t = re.sub(r'\[\w+\](.*?)\[/\w+\]', r"\1", text, flags=re.DOTALL)
    t = re.sub(r'\[/?\w+\]', "", t)
    # Emoji olib tashlash
    t = re.sub(r'[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+', " ", t)
    # Maxsus belgilar
    t = re.sub(r'[•*#|_~`━\-]{2,}', " ", t)
    # Ko'p bo'shliqlarni tozalash
    t = re.sub(r'\s+', " ", t)
    return t.strip()

# ─────────────── Dars qismlarini dinamik qurish ───────────────
def build_parts(row):
    """
    teacher_lessons qatoridan dinamik parts ro'yxati quradi.
    Faqat to'ldirilgan qismlar kiritiladi.
    """
    d = dict(zip(LESSON_COLS, row))
    parts = []
    n_step = 0

    # Kirish
    if d.get("intro","") and str(d["intro"]).strip():
        n_step += 1
        parts.append({
            "type": "intro", "label": "📖 Kirish",
            "text": d["intro"], "image": d.get("image_intro",""),
            "step": n_step
        })

    # Qismlar (part_1 ... part_7)
    n_part = 0
    for i in range(1, 8):
        txt = d.get(f"part_{i}","") or ""
        img = d.get(f"image_{i}","") or ""
        if txt.strip():
            n_step += 1; n_part += 1
            parts.append({
                "type": "part", "label": f"📘 {n_part}-qism",
                "text": txt, "image": img,
                "step": n_step
            })

    # Sodda tushuntirish (simple_1 ... simple_7)
    n_simple = 0
    for i in range(1, 8):
        txt = d.get(f"simple_{i}","") or ""
        if txt.strip():
            n_step += 1; n_simple += 1
            parts.append({
                "type": "simple", "label": f"💡 {n_simple}-tushuntirish",
                "text": txt, "image": "",
                "step": n_step
            })

    # Misollar (example_1 ... example_5)
    n_ex = 0
    for i in range(1, 6):
        txt = d.get(f"example_{i}","") or ""
        if txt.strip():
            n_step += 1; n_ex += 1
            parts.append({
                "type": "example", "label": f"📌 {n_ex}-misol",
                "text": txt, "image": "",
                "step": n_step
            })

    # Xulosa
    if d.get("summary","") and str(d["summary"]).strip():
        n_step += 1
        parts.append({
            "type": "summary", "label": "📝 Xulosa",
            "text": d["summary"], "image": "",
            "step": n_step
        })

    return parts

# ─────────────── Rasimni olish ───────────────
async def _get_image(img_name):
    """images jadvalidan file_id oladi."""
    if not img_name or not str(img_name).strip(): return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (str(img_name).strip(),))
        row = cur.fetchone(); cur.close(); conn.close()
        return row[0] if row else None
    except Exception:
        return None

# ─────────────── Bitta qadamni ko'rsatish ───────────────
async def show_lesson_step(uid, chat_id, step_index, total, part, full_name, fan, mavzu):
    """Bitta dars qadamini ko'rsatadi. Rasm bo'lsa photo, bo'lmasa text."""
    state = lesson_state.setdefault(uid, {})
    old_mid   = state.get("lesson_msg_id")
    old_photo = state.get("lesson_has_photo", False)

    text  = clean_text(part["text"])
    label = part["label"]
    image = await _get_image(part.get("image",""))

    header = (
        f"👤 {full_name}  |  📚 {fan}\n"
        f"📍 {mavzu}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{label}  •  {step_index+1}/{total}\n\n"
    )
    full_text = header + text

    # Progress bar
    filled = round((step_index+1)/total * 10)
    progress = "🟩"*filled + "⬜"*(10-filled)

    # Keyboard
    rows = []
    nav = []
    if step_index > 0:
        nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data="lesson_prev"))
    if step_index < total - 1:
        nav.append(InlineKeyboardButton(text="▶️ Keyingi", callback_data="lesson_next"))
    else:
        nav.append(InlineKeyboardButton(text="✅ Darsni tugatish", callback_data="lesson_finish_confirm"))
    rows.append(nav)
    rows.append([
        InlineKeyboardButton(text="🔊", callback_data="lesson_speak"),
        InlineKeyboardButton(text=progress, callback_data="noop"),
        InlineKeyboardButton(text="🛑 Chiqish", callback_data="lesson_exit"),
    ])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    # Xabarni yangilash yoki yaratish
    if image:
        media = InputMediaPhoto(media=image, caption=full_text[:1024])
        if old_mid and old_photo:
            try:
                await bot.edit_message_media(
                    chat_id=chat_id, message_id=old_mid,
                    media=media, reply_markup=kb
                )
                state["lesson_msg_id"]   = old_mid
                state["lesson_has_photo"] = True
                return
            except Exception:
                pass
        if old_mid:
            try: await bot.delete_message(chat_id, old_mid)
            except: pass
        msg = await bot.send_photo(chat_id, image, caption=full_text[:1024], reply_markup=kb)
        state["lesson_msg_id"]   = msg.message_id
        state["lesson_has_photo"] = True
    else:
        if old_mid and old_photo:
            try: await bot.delete_message(chat_id, old_mid)
            except: pass
            old_mid = None
        if old_mid:
            try:
                await bot.edit_message_text(
                    text=full_text[:4096], chat_id=chat_id,
                    message_id=old_mid, reply_markup=kb
                )
                state["lesson_msg_id"]   = old_mid
                state["lesson_has_photo"] = False
                return
            except Exception:
                try: await bot.delete_message(chat_id, old_mid)
                except: pass
        msg = await bot.send_message(chat_id, full_text[:4096], reply_markup=kb)
        state["lesson_msg_id"]   = msg.message_id
        state["lesson_has_photo"] = False

# ─────────────── TTS ───────────────
async def speak_lesson_step(uid, chat_id, text, gender=""):
    """Bir dars qadamini ovozda o'qiydi."""
    import edge_tts
    from pydub import AudioSegment as AS
    voices = {
        "uz": "uz-UZ-MadinaNeural" if "Ayol" in str(gender) else "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural",
        "ru": "ru-RU-DmitryNeural",
    }
    segments = tts_text(text)
    if not segments: return

    combined = AS.silent(0)
    for lang, seg_text in segments:
        voice = voices.get(lang, voices["uz"])
        tmp = f"tts_les_{uid}_{abs(hash(seg_text))}.mp3"
        try:
            await edge_tts.Communicate(text=seg_text, voice=voice).save(tmp)
            if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
                combined += AS.from_mp3(tmp)
        except Exception:
            pass
        finally:
            try: os.remove(tmp)
            except: pass

    if len(combined) == 0: return
    fname = f"tts_lesson_{uid}.mp3"
    try:
        combined.export(fname, format="mp3")
        vm = await bot.send_voice(chat_id, FSInputFile(fname))
        # Eski ovoz xabarini o'chir
        state = lesson_state.setdefault(uid, {})
        old_vm = state.get("lesson_voice_id")
        if old_vm:
            try: await bot.delete_message(chat_id, old_vm)
            except: pass
        state["lesson_voice_id"] = vm.message_id
    except Exception:
        pass
    finally:
        try: os.remove(fname)
        except: pass
