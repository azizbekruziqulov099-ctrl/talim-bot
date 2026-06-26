from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import json, psycopg2, os, re
from keyboards import get_main_keyboard
from storage import user_state, temp_user, registration_message, reg_kbd_message
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

ROLES           = ["🧒 O'quvchi", "👨‍🏫 O'qituvchi"]
EDUCATION_TYPES = ["👶 Maktabgacha", "🏫 Maktab"]
CURRENT_YEAR    = datetime.now().year
BIRTH_YEARS     = [str(i) for i in range(CURRENT_YEAR - 100, CURRENT_YEAR)]
MONTHS = ["Yanvar","Fevral","Mart","Aprel","May","Iyun",
          "Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
DAYS            = [str(i) for i in range(1, 32)]
CLASS_LEVELS    = [str(i) for i in range(1, 12)]
CLASS_LETTERS   = ["A","B","C","D","E","Bilmadim"]
SCHOOL_TYPES    = [
    "🏫 Oddiy maktab","⭐️ Ixtisoslashtirilgan maktab",
    "🇺🇿 Prezident maktabi","🧮 Al-Xorazmiy maktabi",
    "🪖 Harbiy maktab","🎨 San'at maktabi","📖 IDUM"
]
MONTH_MAP = {
    "Yanvar":"01","Fevral":"02","Mart":"03","Aprel":"04",
    "May":"05","Iyun":"06","Iyul":"07","Avgust":"08",
    "Sentabr":"09","Oktabr":"10","Noyabr":"11","Dekabr":"12"
}

# ─────────── reg_status: to'ldirilgan qiymatlari ko'rinadi ───────────
def reg_status(data):
    def v(key, label):
        val = data.get(key)
        if val:
            return f"✅ {label}: {val}"
        return f"⬜ {label}"
    lines = [
        "📋 Ro'yxatdan o'tish\n",
        v("full_name",      "F.I.Sh"),
        v("birth_date",     "Tug'ilgan sana"),
        v("gender",         "Jins"),
        v("region",         "Viloyat"),
        v("district",       "Tuman"),
        v("education_type", "Ta'lim turi"),
    ]
    if data.get("education_type") == "🏫 Maktab":
        lines += [
            v("school_type",  "Maktab turi"),
            v("school",       "Maktab"),
            v("class",        "Sinf"),
            v("class_letter", "Harf"),
        ]
    else:
        lines += [
            v("kindergarten", "Bog'cha"),
            v("group",        "Guruh"),
        ]
    return "\n".join(lines)

# ─────────── klaviaturalar ───────────
def make_keyboard(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in items],
        resize_keyboard=True
    )

def base_keyboard(items):
    keyboard, row = [], []
    for i, item in enumerate(items, start=1):
        row.append(KeyboardButton(text=str(item)))
        if i % 4 == 0:
            keyboard.append(row); row = []
    if row: keyboard.append(row)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def year_inline_kb(digits=""):
    """0-9 pad, backspace, confirm — inline (editlash uchun)."""
    display = ""
    for i in range(4):
        display += digits[i] if i < len(digits) else "▢"
        if i < 3: display += " "
    confirm_ok = len(digits) == 4 and digits in BIRTH_YEARS
    rows = [
        [InlineKeyboardButton(text=display, callback_data="noop_yr")],
        [InlineKeyboardButton(text=str(n), callback_data=f"reg_yr:{n}") for n in [1,2,3]],
        [InlineKeyboardButton(text=str(n), callback_data=f"reg_yr:{n}") for n in [4,5,6]],
        [InlineKeyboardButton(text=str(n), callback_data=f"reg_yr:{n}") for n in [7,8,9]],
        [
            InlineKeyboardButton(text="⬅️", callback_data="reg_yr:back"),
            InlineKeyboardButton(text="0",  callback_data="reg_yr:0"),
            InlineKeyboardButton(
                text="✅ Tasdiqlash" if confirm_ok else "—",
                callback_data="reg_yr:ok" if confirm_ok else "noop_yr"
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ─────────── bitta xabar edit qilish ───────────
async def _update_board(bot, chat_id, user_id, text, reply_kb=None):
    """
    Asosiy holat xabarini EDIT qiladi (delete+send emas → uchib-chiqmaydi).
    reply_kb — ReplyKeyboardMarkup (ixtiyoriy).
    """
    mid = registration_message.get(user_id)

    # 1) Boardni edit qil
    if mid:
        try:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=mid,
                reply_markup=None
            )
        except Exception:
            # Edit bo'lmadi (inline klaviatura bor edi) — o'chir va qayta yubor
            try: await bot.delete_message(chat_id, mid)
            except: pass
            nm = await bot.send_message(chat_id, text)
            registration_message[user_id] = nm.message_id
    else:
        nm = await bot.send_message(chat_id, text)
        registration_message[user_id] = nm.message_id

    # 2) Eski klaviatura xabarini o'chir
    old_kbd = reg_kbd_message.get(user_id)
    if old_kbd:
        try: await bot.delete_message(chat_id, old_kbd)
        except: pass
        reg_kbd_message.pop(user_id, None)

    # 3) Yangi reply klaviatura xabarini yubor
    if reply_kb:
        km = await bot.send_message(chat_id, "👇", reply_markup=reply_kb)
        reg_kbd_message[user_id] = km.message_id

async def _update_board_inline(bot, chat_id, user_id, text, inline_kb):
    """Inline klaviaturali xabarni EDIT qiladi."""
    mid = registration_message.get(user_id)
    # Eski reply klaviatura xabarini o'chir
    old_kbd = reg_kbd_message.get(user_id)
    if old_kbd:
        try: await bot.delete_message(chat_id, old_kbd)
        except: pass
        reg_kbd_message.pop(user_id, None)

    if mid:
        try:
            await bot.edit_message_text(
                text=text, chat_id=chat_id, message_id=mid,
                reply_markup=inline_kb
            )
            return
        except Exception:
            try: await bot.delete_message(chat_id, mid)
            except: pass
    nm = await bot.send_message(chat_id, text, reply_markup=inline_kb)
    registration_message[user_id] = nm.message_id

# ─────────── F.I.Sh tekshirish ───────────
def validate_name(text):
    """
    Kamida 2 ta so'z, har biri katta harf bilan boshlansin,
    har biri kamida 2 ta belgidan iborat bo'lsin.
    """
    words = text.strip().split()
    if len(words) < 2:
        return False
    return all(
        len(w) >= 2 and w[0].isupper()
        for w in words
    )

# ─────────── asosiy handler ───────────
async def register_handler(message):
    user_id  = message.from_user.id
    bot      = message.bot
    chat_id  = message.chat.id
    state    = user_state.get(user_id)

    # ── ROL ──
    if state == "role":
        temp_user[user_id] = {"role": message.text}
        user_state[user_id] = "full_name"
        text = reg_status(temp_user[user_id]) + "\n\n👤 F.I.Sh ni kiriting:\nMasalan: Toshmatov Alisher"
        nm = await bot.send_message(chat_id, text)
        registration_message[user_id] = nm.message_id
        return

    # ── F.I.Sh ──
    elif state == "full_name":
        name = message.text.strip()
        try: await message.delete()
        except: pass
        if not validate_name(name):
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Familiyani to'liq kiriting"
            )
            return

        temp_user[user_id]["full_name"] = name
        user_state[user_id] = "birth_year"
        text = (reg_status(temp_user[user_id]) +
                "\n\n🎂 Tug'ilgan yilingizni kiriting:")
        await _update_board_inline(
            bot, chat_id, user_id, text,
            year_inline_kb("")
        )
        return

    # ── TUG'ILGAN OY ──
    elif state == "birth_month":
        if message.text not in MONTHS:
            return
        temp_user[user_id]["birth_month"] = MONTH_MAP[message.text]
        user_state[user_id] = "birth_day"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n📅 Tug'ilgan kuningizni tanlang:",
            base_keyboard(DAYS)
        )
        return

    # ── TUG'ILGAN KUN ──
    elif state == "birth_day":
        if message.text not in DAYS:
            return
        day = message.text.zfill(2)
        birth_date = (
            f"{day}.{temp_user[user_id]['birth_month']}."
            f"{temp_user[user_id]['birth_year']}"
        )
        try:
            birth = datetime.strptime(birth_date, "%d.%m.%Y")
            today = datetime.now()
            age   = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            if age < 2 or age > 100:
                raise ValueError("yosh")
        except Exception:
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Sana noto'g'ri, qaytadan tanlang:",
                base_keyboard(DAYS)
            )
            return
        temp_user[user_id]["birth_date"] = birth_date
        user_state[user_id] = "gender"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n👤 Jinsni tanlang:",
            make_keyboard(["👨 Erkak", "👩 Ayol"])
        )
        return

    # ── JINS ──
    elif state == "gender":
        if message.text not in ["👨 Erkak", "👩 Ayol"]:
            return
        temp_user[user_id]["gender"] = message.text
        user_state[user_id] = "region"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🌍 Viloyatni tanlang:",
            base_keyboard(list(REGIONS.keys()))
        )
        return

    # ── VILOYAT ──
    elif state == "region":
        if message.text not in REGIONS:
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Viloyatni tugmadan tanlang:",
                base_keyboard(list(REGIONS.keys()))
            )
            return
        temp_user[user_id]["region"] = message.text
        flat = [d for row in REGIONS[message.text] for d in row]
        user_state[user_id] = "district"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n📍 Tumanni tanlang:",
            base_keyboard(flat)
        )
        return

    # ── TUMAN ──
    elif state == "district":
        temp_user[user_id]["district"] = message.text
        user_state[user_id] = "education_type"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Ta'lim turini tanlang:",
            make_keyboard(EDUCATION_TYPES)
        )
        return

    # ── TA'LIM TURI ──
    elif state == "education_type":
        if message.text not in EDUCATION_TYPES:
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Ta'lim turini tugmadan tanlang:",
                make_keyboard(EDUCATION_TYPES)
            )
            return
        temp_user[user_id]["education_type"] = message.text
        if message.text == "🏫 Maktab":
            user_state[user_id] = "school_type"
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n🏫 Maktab turini tanlang:",
                make_keyboard(SCHOOL_TYPES)
            )
        else:
            user_state[user_id] = "kindergarten"
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n🏡 Bog'cha nomini kiriting:"
            )
        return

    # ── BOG'CHA ──
    elif state == "kindergarten":
        try: await message.delete()
        except: pass
        temp_user[user_id]["kindergarten"] = message.text
        user_state[user_id] = "group"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n👶 Guruh nomini kiriting:"
        )
        return

    # ── GURUH ──
    elif state == "group":
        try: await message.delete()
        except: pass
        temp_user[user_id]["group"] = message.text
        user_state[user_id] = None
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎉 Ro'yxatdan o'tish yakunlandi!"
        )
        return

    # ── MAKTAB TURI ──
    elif state == "school_type":
        if message.text not in SCHOOL_TYPES:
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Maktab turini tugmadan tanlang:",
                make_keyboard(SCHOOL_TYPES)
            )
            return
        temp_user[user_id]["school_type"] = message.text
        user_state[user_id] = "school"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🏫 Maktab raqamini kiriting:\nMasalan: 25"
        )
        return

    # ── MAKTAB RAQAMI ──
    elif state == "school":
        try: await message.delete()
        except: pass
        if not message.text.isdigit():
            await _update_board(
                bot, chat_id, user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Faqat raqam kiriting. Masalan: 25"
            )
            return
        temp_user[user_id]["school"] = message.text
        user_state[user_id] = "class"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Sinfni tanlang:",
            make_keyboard(CLASS_LEVELS)
        )
        return

    # ── SINF ──
    elif state == "class":
        if message.text not in CLASS_LEVELS:
            return
        temp_user[user_id]["class"] = message.text
        user_state[user_id] = "class_letter"
        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🔤 Sinf harfini tanlang:",
            make_keyboard(CLASS_LETTERS)
        )
        return

    # ── SINF HARFI — YAKUNIY SAQLASH ──
    elif state == "class_letter":
        if message.text not in CLASS_LETTERS:
            return
        temp_user[user_id]["class_letter"] = message.text

        try:
            bdate = datetime.strptime(
                temp_user[user_id].get("birth_date","01.01.2000"), "%d.%m.%Y"
            ).date()
        except Exception:
            bdate = None

        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur  = conn.cursor()
            # Avval mavjudligini tekshiramiz
            cur.execute("SELECT user_id FROM users WHERE user_id=%s", (user_id,))
            exists = cur.fetchone()
            if exists:
                cur.execute("""
                    UPDATE users SET
                        role=%s, full_name=%s, birth_date=%s, gender=%s,
                        region=%s, district=%s, education_type=%s,
                        school_type=%s, school=%s, class=%s, class_letter=%s
                    WHERE user_id=%s
                """, (
                    temp_user[user_id].get("role"),
                    temp_user[user_id].get("full_name"),
                    bdate,
                    temp_user[user_id].get("gender"),
                    temp_user[user_id].get("region"),
                    temp_user[user_id].get("district"),
                    temp_user[user_id].get("education_type"),
                    temp_user[user_id].get("school_type"),
                    temp_user[user_id].get("school"),
                    temp_user[user_id].get("class"),
                    temp_user[user_id].get("class_letter"),
                    user_id,
                ))
            else:
                cur.execute("""
                    INSERT INTO users(
                        user_id, role, full_name, birth_date, gender,
                        region, district, education_type, school_type,
                        school, class, class_letter
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    user_id,
                    temp_user[user_id].get("role"),
                    temp_user[user_id].get("full_name"),
                    bdate,
                    temp_user[user_id].get("gender"),
                    temp_user[user_id].get("region"),
                    temp_user[user_id].get("district"),
                    temp_user[user_id].get("education_type"),
                    temp_user[user_id].get("school_type"),
                    temp_user[user_id].get("school"),
                    temp_user[user_id].get("class"),
                    temp_user[user_id].get("class_letter"),
                ))
            conn.commit(); conn.close()
        except Exception as _db_err:
            await message.answer(f"❌ DB xatosi: {_db_err}\n\nAdmin bilan bog'laning.")
            user_state[user_id] = None
            return

        await _update_board(
            bot, chat_id, user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎉 Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!"
        )
        await bot.send_message(
            chat_id, "Xush kelibsiz! 👋",
            reply_markup=get_main_keyboard(temp_user[user_id]["role"])
        )

        if temp_user[user_id].get("role") in ("🧒 O'quvchi", "O'quvchi"):
            try:
                from progress import create_auto_exams
                from datetime import date
                create_auto_exams(user_id, temp_user[user_id].get("class","5"), date.today())
            except Exception:
                pass

        registration_message.pop(user_id, None)
        reg_kbd_message.pop(user_id, None)
        user_state[user_id] = None
        return


# ─────────── Tug'ilgan yil inline callback handler ───────────
async def reg_year_callback(call):
    """
    callback_data = "reg_yr:0" ... "reg_yr:9" | "reg_yr:back" | "reg_yr:ok"
    """
    user_id = call.from_user.id
    bot     = call.bot
    chat_id = call.message.chat.id

    if user_state.get(user_id) != "birth_year":
        await call.answer()
        return

    action = call.data.split(":")[1]
    digits = temp_user[user_id].get("year_digits", "")

    if action == "back":
        digits = digits[:-1]
    elif action == "ok":
        if len(digits) == 4 and digits in BIRTH_YEARS:
            temp_user[user_id]["birth_year"] = digits
            temp_user[user_id].pop("year_digits", None)
            user_state[user_id] = "birth_month"
            # birth_date ko'rsatish uchun faqat yil hozircha
            temp_user[user_id]["_yr_display"] = digits
            text = (reg_status(temp_user[user_id]) +
                    "\n\n📅 Tug'ilgan oyingizni tanlang:")
            await _update_board_inline(
                bot, chat_id, user_id, text, None
            )
            await _update_board(
                bot, chat_id, user_id, text,
                base_keyboard(MONTHS)
            )
            await call.answer()
            return
        else:
            await call.answer("❌ Yil noto'g'ri", show_alert=False)
            return
    elif action.isdigit():
        if len(digits) < 4:
            digits += action
    else:
        await call.answer()
        return

    temp_user[user_id]["year_digits"] = digits
    text = (reg_status(temp_user[user_id]) +
            "\n\n🎂 Tug'ilgan yilingizni kiriting:")
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=year_inline_kb(digits)
        )
    except Exception:
        pass
    await call.answer()
