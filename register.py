from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)
import json
import psycopg2
import os
from keyboards import get_main_keyboard
from storage import user_state, temp_user, registration_message
import re
from datetime import datetime
DATABASE_URL = os.getenv("DATABASE_URL")

with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

ROLES = [
    "🧒 O‘quvchi",
    "👨‍🏫 O‘qituvchi"
]

EDUCATION_TYPES = [
    "👶 Maktabgacha",
    "🏫 Maktab"
]

CURRENT_YEAR = datetime.now().year

BIRTH_YEARS = [
    str(i)
    for i in range(CURRENT_YEAR - 100, CURRENT_YEAR)
]

MONTHS = [
    "Yanvar",
    "Fevral",
    "Mart",
    "Aprel",
    "May",
    "Iyun",
    "Iyul",
    "Avgust",
    "Sentabr",
    "Oktabr",
    "Noyabr",
    "Dekabr"
]

DAYS = [str(i) for i in range(1, 32)]

CLASS_LEVELS = [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11"
]

SCHOOL_TYPES = [
    "🏫 Oddiy maktab",
    "⭐️ Ixtisoslashtirilgan maktab",
    "🇺🇿 Prezident maktabi",
    "🧮 Al-Xorazmiy maktabi",
    "🪖 Harbiy maktab",
    "🎨 San'at maktabi",
    "📖 IDUM"
]

CLASS_LETTERS = [
    "A", "B", "C", "D", "E", "Bilmadim"
]

def reg_status(data):

    return (
        "📋 Registratsiya\n\n"

        f"{'✅' if data.get('full_name') else '⬜'} F.I.Sh\n"
        f"{'✅' if data.get('birth_date') else '⬜'} Tug‘ilgan sana\n"
        f"{'✅' if data.get('gender') else '⬜'} Jins\n"
        f"{'✅' if data.get('region') else '⬜'} Viloyat\n"
        f"{'✅' if data.get('district') else '⬜'} Tuman\n"
        f"{'✅' if data.get('education_type') else '⬜'} Ta'lim turi\n"
        f"{'✅' if data.get('school_type') else '⬜'} Maktab turi\n"
        f"{'✅' if data.get('school') else '⬜'} Maktab\n"
        f"{'✅' if data.get('class') else '⬜'} Sinf\n"
        f"{'✅' if data.get('class_letter') else '⬜'} Harf"
    )

def make_keyboard(items):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=i)] for i in items],
        resize_keyboard=True
    )

def base_keyboard(items):

    keyboard = []
    row = []

    for i, item in enumerate(items, start=1):

        row.append(
            KeyboardButton(text=str(item))
        )

        if i % 4 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

async def update_reg_message(
    message,
    user_id,
    text,
    reply_markup=None
):
    try:
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=registration_message[user_id]
        )
    except:
        pass

    msg = await message.answer(
        text,
        reply_markup=reply_markup
    )

    registration_message[user_id] = msg.message_id

async def register_handler(message):

    user_id = message.from_user.id

    # ROLE
    if user_state.get(user_id) == "role":

        temp_user[user_id] = {
            "role": message.text
        }

        user_state[user_id] = "full_name"

        msg = await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n👤 F.I.Sh ni kiriting:\n\n"
            "Masalan:\n"
            "Familyangiz Ismingiz"
        )
        registration_message[user_id] = msg.message_id

        return

    elif user_state.get(user_id) == "full_name":

        name = message.text.strip()

        if len(name.split()) < 2:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ F.I.Sh ni to'liq kiriting"
            )

            return
        temp_user[user_id]["full_name"] = message.text

        try:
            await message.delete()
        except:
            pass

        user_state[user_id] = "birth_year"

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎂 Tug‘ilgan yilingizni tanlang:",
            base_keyboard(BIRTH_YEARS)
        )

        return

    elif user_state.get(user_id) == "birth_year":

        if message.text not in BIRTH_YEARS:
            return

        temp_user[user_id]["birth_year"] = message.text

        user_state[user_id] = "birth_month"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n📅 Tug‘ilgan oyingizni tanlang:",
            base_keyboard(MONTHS)
        )

        return

    elif user_state.get(user_id) == "birth_month":

        if message.text not in MONTHS:
            return

        month_map = {
            "Yanvar": "01",
            "Fevral": "02",
            "Mart": "03",
            "Aprel": "04",
            "May": "05",
            "Iyun": "06",
            "Iyul": "07",
            "Avgust": "08",
            "Sentabr": "09",
            "Oktabr": "10",
            "Noyabr": "11",
            "Dekabr": "12"
        }

        temp_user[user_id]["birth_month"] = month_map[message.text]

        user_state[user_id] = "birth_day"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n📅 Tug‘ilgan kuningizni tanlang:",
            base_keyboard(DAYS)
        )

        return

    elif user_state.get(user_id) == "birth_day":

        if message.text not in DAYS:
            return

        day = message.text.zfill(2)

        try:
            birth_date = (
                f"{day}."
                f"{temp_user[user_id]['birth_month']}."
                f"{temp_user[user_id]['birth_year']}"
            )

            datetime.strptime(
                birth_date,
                "%d.%m.%Y"
            )

        except:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Sana noto'g'ri"
            )

            return

        birth = datetime.strptime(
            birth_date,
            "%d.%m.%Y"
        )

        today = datetime.now()

        age = today.year - birth.year

        if (today.month, today.day) < (birth.month, birth.day):
            age -= 1

        if age < 2 or age > 100:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Yosh noto‘g‘ri kiritilgan"
            )

            return

        temp_user[user_id]["birth_date"] = birth_date
        user_state[user_id] = "gender"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n👤 Jinsni tanlang:",
            make_keyboard([
                "👨 Erkak",
                "👩 Ayol"
            ])
        )

        return

    elif user_state.get(user_id) == "gender":

        if message.text not in [
            "👨 Erkak",
            "👩 Ayol"
        ]:
            return

        temp_user[user_id]["gender"] = message.text

        user_state[user_id] = "region"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🌍 Viloyatni tanlang:",
            base_keyboard(REGIONS.keys())
        )

        return

    elif user_state.get(user_id) == "region":

        if message.text not in REGIONS:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Viloyatni tugmadan tanlang"
            )

            return

        temp_user[user_id]["region"] = message.text

        districts = REGIONS.get(
            message.text,
            []
        )

        flat = []

        for row in districts:
            flat.extend(row)

        user_state[user_id] = "district"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n📍 Tumanni tanlang:",
            base_keyboard(flat)
        )

        return

    elif user_state.get(user_id) == "district":

        temp_user[user_id]["district"] = message.text

        user_state[user_id] = "education_type"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Ta'lim turini tanlang:",
            make_keyboard(EDUCATION_TYPES)
        )

        return

    elif user_state.get(user_id) == "education_type":

        if message.text not in EDUCATION_TYPES:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Ta'lim turini tugmadan tanlang"
            )

            return

        temp_user[user_id]["education_type"] = message.text

        try:
            await message.delete()
        except:
            pass

        if message.text == "🏫 Maktab":

            user_state[user_id] = "school_type"

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n🏫 Maktab turini tanlang:",
                make_keyboard(SCHOOL_TYPES)
            )

        else:

            user_state[user_id] = "kindergarten"

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n🏡 Bog‘cha nomini kiriting:"
            )

        return

    elif user_state.get(user_id) == "kindergarten":

        temp_user[user_id]["kindergarten"] = message.text

        user_state[user_id] = "group"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n👶 Guruh nomini kiriting:"
        )

        return

    elif user_state.get(user_id) == "group":

        temp_user[user_id]["group"] = message.text

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            "🎉 Registratsiya yakunlandi!"
        )

        user_state[user_id] = None

        return

    elif user_state.get(user_id) == "school_type":

        if message.text not in SCHOOL_TYPES:

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Maktab turini tugmadan tanlang"
            )

            return

        temp_user[user_id]["school_type"] = message.text

        user_state[user_id] = "school"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🏫 Maktab raqamini kiriting:"
        )

        return
        
    elif user_state.get(user_id) == "school":

        if not message.text.isdigit():

            try:
                await message.bot.delete_message(
                    chat_id=message.chat.id,
                    message_id=registration_message[user_id]
                )
            except:
                pass

            await update_reg_message(
                message,
                user_id,
                reg_status(temp_user[user_id]) +
                "\n\n❌ Maktab raqamini kiriting\n\nMasalan:\n25"
            )

            return

        temp_user[user_id]["school"] = message.text

        user_state[user_id] = "class"

        try:
            await message.delete()
        except:
            pass
        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Sinfni tanlang:",
            make_keyboard(CLASS_LEVELS)
        )

        return
        
    elif user_state.get(user_id) == "class":

        if message.text not in CLASS_LEVELS:
            return

        temp_user[user_id]["class"] = message.text

        user_state[user_id] = "class_letter"

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🔤 Harfni tanlang:",
            make_keyboard(CLASS_LETTERS)
        )

        return
        
    elif user_state.get(user_id) == "class_letter":

        if message.text not in CLASS_LETTERS:
            return

        temp_user[user_id]["class_letter"] = message.text

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO users(
            user_id,
            role,
            full_name,
            birth_date,
            gender,
            region,
            district,
            education_type,
            school_type,
            school,
            class,
            class_letter
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id,
            temp_user[user_id].get("role"),
            temp_user[user_id].get("full_name"),

            datetime.strptime(
                temp_user[user_id].get("birth_date"),
                "%d.%m.%Y"
            ).date(),

            temp_user[user_id].get("gender"),
            temp_user[user_id].get("region"),
            temp_user[user_id].get("district"),
            temp_user[user_id].get("education_type"),
            temp_user[user_id].get("school_type"),
            temp_user[user_id].get("school"),
            temp_user[user_id].get("class"),
            temp_user[user_id].get("class_letter")
        ))

        conn.commit()
        conn.close()

        try:
            await message.delete()
        except:
            pass

        await update_reg_message(
            message,
            user_id,
            reg_status(temp_user[user_id]) +
            "\n\n🎉 Registratsiya yakunlandi!"
        )

        await message.answer(
            "Xush kelibsiz!",
            reply_markup=get_main_keyboard(
                temp_user[user_id]["role"]
            )
        )

        # O'quvchi uchun avtomatik imtihonlar yaratish
        if temp_user[user_id].get("role") in ("🧒 O'quvchi", "O'quvchi"):
            try:
                from progress import create_auto_exams
                from datetime import date
                create_auto_exams(
                    user_id,
                    temp_user[user_id].get("class", "5"),
                    date.today()
                )
            except Exception:
                pass

        registration_message.pop(user_id, None)

        user_state[user_id] = None

        return
