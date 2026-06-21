"""
student_settings.py — O'quvchi sozlamalari paneli
"""
import psycopg2, os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")

def db(): return psycopg2.connect(DATABASE_URL)


async def show_settings(message, user_id):
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT full_name, class, gender, birth_date, 
               region, district, school, subject
        FROM users WHERE user_id=%s
    """, (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        await message.answer("❌ Ma'lumot topilmadi")
        return

    name, grade, gender, bdate, region, district, school, subject = row

    # Tug'ilgan sana
    bdate_str = bdate.strftime("%d.%m.%Y") if bdate else "Kiritilmagan"

    text = (
        f"⚙️ Sozlamalar\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"👤 Ism: {name or '—'}\n"
        f"🎓 Sinf: {grade or '—'}\n"
        f"🚻 Jins: {gender or '—'}\n"
        f"🎂 Tug'ilgan kun: {bdate_str}\n"
        f"📍 Viloyat: {region or '—'}\n"
        f"🏘 Tuman: {district or '—'}\n"
        f"🏫 Maktab: {school or '—'}\n"
        f"📚 Fan: {subject or '—'}\n"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Ism", callback_data="sts_name"),
            InlineKeyboardButton(text="🎓 Sinf", callback_data="sts_grade"),
            InlineKeyboardButton(text="🚻 Jins", callback_data="sts_gender"),
        ],
        [
            InlineKeyboardButton(text="🎂 Tug'ilgan kun", callback_data="sts_bdate"),
            InlineKeyboardButton(text="📍 Hudud", callback_data="sts_region"),
        ],
        [
            InlineKeyboardButton(text="🏫 Maktab", callback_data="sts_school"),
            InlineKeyboardButton(text="📚 Fan", callback_data="sts_subject"),
        ],
        [
            InlineKeyboardButton(text="🔔 Bildirishnomalar", callback_data="sts_notif"),
            InlineKeyboardButton(text="🌙 Tungi rejim", callback_data="sts_night"),
        ],
        [
            InlineKeyboardButton(text="🔄 Rolni almashtirish", callback_data="sts_role"),
        ],
    ])

    await message.answer(text, reply_markup=kb)


async def handle_settings_callback(call, user_id, user_state):
    data = call.data

    if data == "sts_name":
        user_state[user_id] = "change_name"
        await call.message.answer("✏️ Yangi ismingizni kiriting:")
        await call.answer()

    elif data == "sts_grade":
        grades = ["1","2","3","4","5","6","7","8","9","10","11"]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{g}-sinf", callback_data=f"sts_grade_set:{g}") 
             for g in grades[i:i+4]]
            for i in range(0, len(grades), 4)
        ])
        await call.message.answer("🎓 Sinfni tanlang:", reply_markup=kb)
        await call.answer()

    elif data.startswith("sts_grade_set:"):
        grade = data[14:]
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE users SET class=%s WHERE user_id=%s", (grade, user_id))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ Sinf: {grade}", show_alert=True)

    elif data == "sts_gender":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👦 O'g'il bola", callback_data="sts_gender_set:O'g'il bola"),
            InlineKeyboardButton(text="👧 Qiz bola", callback_data="sts_gender_set:Qiz bola"),
        ]])
        await call.message.answer("🚻 Jinsni tanlang:", reply_markup=kb)
        await call.answer()

    elif data.startswith("sts_gender_set:"):
        gender = data[15:]
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE users SET gender=%s WHERE user_id=%s", (gender, user_id))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ Jins: {gender}", show_alert=True)

    elif data == "sts_bdate":
        user_state[user_id] = "change_bdate"
        await call.message.answer(
            "🎂 Tug'ilgan kuningizni kiriting:\n"
            "Format: KK.OO.YYYY\n"
            "Masalan: 15.03.2015"
        )
        await call.answer()

    elif data == "sts_region":
        await call.answer()
        await call.message.answer(
            "📍 Viloyatni o'zgartirish uchun:\n"
            "Ro'yxatdan qayta o'ting yoki adminga murojaat qiling.",
        )

    elif data == "sts_school":
        user_state[user_id] = "change_school_settings"
        await call.message.answer("🏫 Maktab nomini kiriting:")
        await call.answer()

    elif data == "sts_subject":
        subjects = [
            "Matematika", "Ona tili", "Adabiyot", "Ingliz tili",
            "Tarix", "Geografiya", "Biologiya", "Fizika",
            "Kimyo", "Informatika", "Jismoniy tarbiya",
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=s, callback_data=f"sts_sub_set:{s}") 
             for s in subjects[i:i+2]]
            for i in range(0, len(subjects), 2)
        ])
        await call.message.answer("📚 Fanni tanlang:", reply_markup=kb)
        await call.answer()

    elif data.startswith("sts_sub_set:"):
        subject = data[12:]
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE users SET subject=%s WHERE user_id=%s", (subject, user_id))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ Fan: {subject}", show_alert=True)

    elif data == "sts_notif":
        await call.answer("🔔 Bildirishnomalar — tez kunda!", show_alert=True)

    elif data == "sts_night":
        await call.answer("🌙 Tungi rejim — tez kunda!", show_alert=True)

    elif data == "sts_role":
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🧒 O'quvchi", callback_data="sts_role_set:🧒 O'quvchi"),
            InlineKeyboardButton(text="👨‍🏫 O'qituvchi", callback_data="sts_role_set:👨‍🏫 O'qituvchi"),
        ]])
        await call.message.answer("🔄 Rolni tanlang:", reply_markup=kb)
        await call.answer()

    elif data.startswith("sts_role_set:"):
        role = data[13:]
        conn = db(); cur = conn.cursor()
        cur.execute("UPDATE users SET role=%s WHERE user_id=%s", (role, user_id))
        conn.commit(); cur.close(); conn.close()
        from keyboards import get_main_keyboard
        await call.message.answer(
            f"✅ Rol: {role}",
            reply_markup=get_main_keyboard(role)
        )
        await call.answer()
