from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import json, psycopg2, os, re
from keyboards import get_main_keyboard
from storage import user_state, temp_user, registration_message, reg_kbd_message
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")

with open("regions.json","r",encoding="utf-8") as f:
    REGIONS = json.load(f)

ROLES        = ["🧒 O'quvchi","👨‍🏫 O'qituvchi","👨‍👩‍👧 Ota-ona"]
EDU_TYPES    = ["👶 Maktabgacha","🏫 Maktab"]
MONTHS       = ["Yanvar","Fevral","Mart","Aprel","May","Iyun",
                "Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
MONTH_MAP    = {m:str(i+1).zfill(2) for i,m in enumerate(MONTHS)}
DAYS         = [str(i) for i in range(1,32)]
CLASS_LEVELS = [str(i) for i in range(1,12)]
CLASS_LETTERS= ["A","B","C","D","E","Bilmadim"]
SCHOOL_TYPES = [
    "🏫 Oddiy maktab","⭐️ Ixtisoslashtirilgan","🇺🇿 Prezident maktabi",
    "🧮 Al-Xorazmiy","🪖 Harbiy maktab","🎨 San'at maktabi","📖 IDUM"
]
CURRENT_YEAR = datetime.now().year
BIRTH_YEARS  = [str(i) for i in range(CURRENT_YEAR-100, CURRENT_YEAR)]

# ── reg_status ──
def reg_status(d):
    def v(key,label):
        val=d.get(key)
        return f"✅ {label}: {val}" if val else f"⬜ {label}"
    lines=["📋 Ro'yxatdan o'tish\n",
           v("full_name","F.I.Sh"), v("birth_date","Tug'ilgan sana"),
           v("gender","Jins"),      v("region","Viloyat"),
           v("district","Tuman"),   v("education_type","Ta'lim turi")]
    if d.get("education_type")=="🏫 Maktab":
        lines+=[v("school_type","Maktab turi"),v("school","Maktab"),
                v("class","Sinf"),v("class_letter","Harf")]
    else:
        lines+=[v("kindergarten","Bog'cha"),v("group","Guruh")]
    return "\n".join(lines)

# ── Inline klaviatura yordamchilari ──
def _ik(items, prefix, cols=2, back=None):
    """items ro'yxatidan inline klaviatura qil."""
    rows=[]
    row=[]
    for i,item in enumerate(items,1):
        cb = f"reg:{prefix}:{item}"[:64]
        row.append(InlineKeyboardButton(text=item, callback_data=cb))
        if i%cols==0:
            rows.append(row); row=[]
    if row: rows.append(row)
    if back:
        rows.append([InlineKeyboardButton(text="◀️ Orqaga",callback_data=f"reg:back:{back}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def year_inline_kb(digits=""):
    display = " ".join(digits[i] if i<len(digits) else "▢" for i in range(4))
    ok = len(digits)==4 and digits in BIRTH_YEARS
    rows=[
        [InlineKeyboardButton(text=display, callback_data="noop_yr")],
        [InlineKeyboardButton(text=str(n),callback_data=f"reg_yr:{n}") for n in [1,2,3]],
        [InlineKeyboardButton(text=str(n),callback_data=f"reg_yr:{n}") for n in [4,5,6]],
        [InlineKeyboardButton(text=str(n),callback_data=f"reg_yr:{n}") for n in [7,8,9]],
        [InlineKeyboardButton(text="⬅️",callback_data="reg_yr:back"),
         InlineKeyboardButton(text="0", callback_data="reg_yr:0"),
         InlineKeyboardButton(text="✅ Tasdiqlash" if ok else "—",
                              callback_data="reg_yr:ok" if ok else "noop_yr")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ── Board xabarini edit/yaratish ──
async def _show(bot, chat_id, user_id, text, kb=None):
    mid = registration_message.get(user_id)
    if mid:
        try:
            await bot.edit_message_text(
                text=text, chat_id=chat_id,
                message_id=mid, reply_markup=kb
            )
            return
        except Exception:
            try: await bot.delete_message(chat_id, mid)
            except: pass
    nm = await bot.send_message(chat_id, text, reply_markup=kb)
    registration_message[user_id] = nm.message_id

def validate_name(text):
    words = text.strip().split()
    return len(words)>=2 and all(len(w)>=2 and w[0].isupper() for w in words)

# ════════════════════════════════════════
#  MATN XABARLARI HANDLER (F.I.Sh, maktab, bog'cha, guruh)
# ════════════════════════════════════════
async def register_handler(message):
    user_id = message.from_user.id
    bot     = message.bot
    chat_id = message.chat.id
    state   = user_state.get(user_id)

    if state == "reg_fullname":
        name = message.text.strip()
        try: await message.delete()
        except: pass
        if not validate_name(name):
            await _show(bot, chat_id, user_id,
                reg_status(temp_user[user_id])+"\n\n❌ Familiyani to'liq kiriting")
            return
        temp_user[user_id]["full_name"] = name
        user_state[user_id] = "reg_birthyear"
        await _show(bot, chat_id, user_id,
            reg_status(temp_user[user_id])+"\n\n🎂 Tug'ilgan yilingizni kiriting:",
            year_inline_kb(""))

    elif state == "reg_school":
        try: await message.delete()
        except: pass
        if not message.text.isdigit():
            await _show(bot, chat_id, user_id,
                reg_status(temp_user[user_id])+"\n\n❌ Faqat raqam kiriting. Masalan: 25")
            return
        temp_user[user_id]["school"] = message.text
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(temp_user[user_id])+"\n\n🎓 Sinfni tanlang:",
            _ik(CLASS_LEVELS,"class",cols=4))

    elif state == "reg_kindergarten":
        try: await message.delete()
        except: pass
        temp_user[user_id]["kindergarten"] = message.text
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(temp_user[user_id])+"\n\n👶 Guruh nomini kiriting:")

    elif state == "reg_group":
        try: await message.delete()
        except: pass
        temp_user[user_id]["group"] = message.text
        await _finish(bot, chat_id, user_id, message)

# ════════════════════════════════════════
#  INLINE CALLBACK HANDLER
# ════════════════════════════════════════
async def reg_callback(call):
    user_id = call.from_user.id
    bot     = call.bot
    chat_id = call.message.chat.id
    data    = call.data  # "reg:prefix:value"

    if not data.startswith("reg:"):
        await call.answer(); return

    parts = data.split(":",2)
    if len(parts) < 3:
        await call.answer(); return
    _, prefix, value = parts

    d = temp_user.setdefault(user_id, {})

    # ── ROL ──
    if prefix == "role":
        d["role"] = value
        user_state[user_id] = "reg_fullname"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n👤 F.I.Sh kiriting:\nMasalan: Toshmatov Alisher")

    # ── OY ──
    elif prefix == "month":
        d["birth_month"] = MONTH_MAP.get(value, "01")
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n📅 Tug'ilgan kuningizni tanlang:",
            _ik(DAYS,"day",cols=5))

    # ── KUN ──
    elif prefix == "day":
        day = value.zfill(2)
        birth_date = f"{day}.{d.get('birth_month','01')}.{d.get('birth_year','2000')}"
        try:
            birth = datetime.strptime(birth_date,"%d.%m.%Y")
            today = datetime.now()
            age   = today.year-birth.year
            if (today.month,today.day)<(birth.month,birth.day): age-=1
            if age<2 or age>100: raise ValueError
        except:
            await _show(bot, chat_id, user_id,
                reg_status(d)+"\n\n❌ Sana noto'g'ri, qaytadan tanlang:",
                _ik(DAYS,"day",cols=5))
            await call.answer(); return
        d["birth_date"] = birth_date
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n👤 Jinsni tanlang:",
            _ik(["👨 Erkak","👩 Ayol"],"gender",cols=2))

    # ── JINS ──
    elif prefix == "gender":
        d["gender"] = value
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n🌍 Viloyatni tanlang:",
            _ik(list(REGIONS.keys()),"region",cols=2))

    # ── VILOYAT ──
    elif prefix == "region":
        d["region"] = value
        flat = [dist for row in REGIONS[value] for dist in row]
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n📍 Tumanni tanlang:",
            _ik(flat,"district",cols=2))

    # ── TUMAN ──
    elif prefix == "district":
        d["district"] = value
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n🎓 Ta'lim turini tanlang:",
            _ik(EDU_TYPES,"edutype",cols=1))

    # ── TA'LIM TURI ──
    elif prefix == "edutype":
        d["education_type"] = value
        user_state[user_id] = "reg_wait_inline"
        if value == "🏫 Maktab":
            await _show(bot, chat_id, user_id,
                reg_status(d)+"\n\n🏫 Maktab turini tanlang:",
                _ik(SCHOOL_TYPES,"schooltype",cols=1))
        else:
            await _show(bot, chat_id, user_id,
                reg_status(d)+"\n\n🏡 Bog'cha nomini kiriting:")
            user_state[user_id] = "reg_kindergarten"

    # ── MAKTAB TURI ──
    elif prefix == "schooltype":
        d["school_type"] = value
        user_state[user_id] = "reg_school"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n🏫 Maktab raqamini kiriting:\nMasalan: 25")

    # ── SINF ──
    elif prefix == "class":
        d["class"] = value
        user_state[user_id] = "reg_wait_inline"
        await _show(bot, chat_id, user_id,
            reg_status(d)+"\n\n🔤 Sinf harfini tanlang:",
            _ik(CLASS_LETTERS,"classletter",cols=3))

    # ── SINF HARFI → SAQLASH ──
    elif prefix == "classletter":
        d["class_letter"] = value
        await _finish(bot, chat_id, user_id, call.message)

    await call.answer()

# ── Tug'ilgan yil digit pad ──
async def reg_year_callback(call):
    user_id = call.from_user.id
    bot     = call.bot
    chat_id = call.message.chat.id
    if user_state.get(user_id) != "reg_birthyear":
        await call.answer(); return
    action = call.data.split(":")[1]
    digits = temp_user[user_id].get("year_digits","")
    if action=="back":    digits=digits[:-1]
    elif action=="ok":
        if len(digits)==4 and digits in BIRTH_YEARS:
            temp_user[user_id]["birth_year"]  = digits
            temp_user[user_id].pop("year_digits",None)
            user_state[user_id] = "reg_wait_inline"
            await _show(bot, chat_id, user_id,
                reg_status(temp_user[user_id])+"\n\n📅 Tug'ilgan oyingizni tanlang:",
                _ik(MONTHS,"month",cols=3))
            await call.answer(); return
        else:
            await call.answer("❌ Yil noto'g'ri"); return
    elif action.isdigit() and len(digits)<4:
        digits+=action
    temp_user[user_id]["year_digits"] = digits
    registration_message[user_id] = call.message.message_id
    try:
        await bot.edit_message_text(
            text=reg_status(temp_user[user_id])+"\n\n🎂 Tug'ilgan yilingizni kiriting:",
            chat_id=chat_id, message_id=call.message.message_id,
            reply_markup=year_inline_kb(digits)
        )
    except Exception:
        # Edit muvaffaqiyatsiz bo'lsa — yangi xabar yuboramiz
        try: await bot.delete_message(chat_id, call.message.message_id)
        except: pass
        nm = await bot.send_message(
            chat_id,
            reg_status(temp_user[user_id])+"\n\n🎂 Tug'ilgan yilingizni kiriting:",
            reply_markup=year_inline_kb(digits)
        )
        registration_message[user_id] = nm.message_id
    await call.answer()

# ── Yakuniy saqlash ──
async def _finish(bot, chat_id, user_id, message):
    d = temp_user[user_id]
    try:
        bdate = datetime.strptime(d.get("birth_date","01.01.2000"),"%d.%m.%Y").date()
    except: bdate = None
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=%s",(user_id,))
        if cur.fetchone():
            cur.execute("""UPDATE users SET
                role=%s,full_name=%s,birth_date=%s,gender=%s,
                region=%s,district=%s,education_type=%s,
                school_type=%s,school=%s,class=%s,class_letter=%s,
                kindergarten=%s,\"group\"=%s
                WHERE user_id=%s""", (
                d.get("role"),d.get("full_name"),bdate,d.get("gender"),
                d.get("region"),d.get("district"),d.get("education_type"),
                d.get("school_type"),d.get("school"),d.get("class"),d.get("class_letter"),
                d.get("kindergarten"),d.get("group"),user_id
            ))
        else:
            cur.execute("""INSERT INTO users(
                user_id,role,full_name,birth_date,gender,
                region,district,education_type,school_type,
                school,class,class_letter,kindergarten,"group")
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
                user_id,d.get("role"),d.get("full_name"),bdate,d.get("gender"),
                d.get("region"),d.get("district"),d.get("education_type"),
                d.get("school_type"),d.get("school"),d.get("class"),d.get("class_letter"),
                d.get("kindergarten"),d.get("group")
            ))
        conn.commit(); conn.close()
    except Exception as e:
        await message.answer(f"❌ DB xatosi: {e}\n\nAdmin bilan bog'laning.")
        user_state[user_id] = None; return

    await _show(bot, chat_id, user_id,
        reg_status(d)+"\n\n🎉 Ro'yxatdan o'tish yakunlandi!")
    await bot.send_message(
        chat_id,"Xush kelibsiz! 👋",
        reply_markup=get_main_keyboard(d["role"])
    )
    if d.get("role") in ("🧒 O'quvchi","O'quvchi"):
        try:
            from progress import create_auto_exams
            from datetime import date
            create_auto_exams(user_id,d.get("class","5"),date.today())
        except: pass
    registration_message.pop(user_id,None)
    reg_kbd_message.pop(user_id,None)
    user_state[user_id] = None

# ── Rol tanlash (start uchun) ──
async def start_registration(message):
    user_id = message.from_user.id
    temp_user[user_id] = {}
    user_state[user_id] = "reg_wait_inline"
    nm = await message.answer(
        "📋 Ro'yxatdan o'tish\n\nRolni tanlang:",
        reply_markup=_ik(ROLES,"role",cols=1)
    )
    registration_message[user_id] = nm.message_id
