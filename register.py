from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)
import json
import psycopg2
import os
from keyboards import get_main_keyboard
from storage import user_state, temp_user

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


async def register_handler(message):

    user_id = message.from_user.id

    print("REGISTER_HANDLER KELDI")
    print("STATE =", user_state.get(user_id))
    print("TEXT =", message.text)

    # ROLE
    if user_state.get(user_id) == "role":

        temp_user[user_id] = {
            "role": message.text
        }

        user_state[user_id] = "full_name"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n👤 F.I.Sh ni kiriting:"
        )

        return

    elif user_state.get(user_id) == "full_name":

        temp_user[user_id]["full_name"] = message.text

        user_state[user_id] = "birth_date"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🎂 Tug‘ilgan sanani kiriting:"
        )

        return

    elif user_state.get(user_id) == "birth_date":

        temp_user[user_id]["birth_date"] = message.text

        user_state[user_id] = "gender"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n👤 Jinsni tanlang:",
            reply_markup=make_keyboard([
                "👨 Erkak",
                "👩 Ayol"
            ])
        )

        return

    elif user_state.get(user_id) == "gender":

        temp_user[user_id]["gender"] = message.text

        user_state[user_id] = "region"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🌍 Viloyatni tanlang:",
            reply_markup=base_keyboard(
                REGIONS.keys()
            )
        )

        return

    elif user_state.get(user_id) == "region":

        temp_user[user_id]["region"] = message.text

        districts = REGIONS.get(
            message.text,
            []
        )

        flat = []

        for row in districts:
            flat.extend(row)

        user_state[user_id] = "district"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n📍 Tumanni tanlang:",
            reply_markup=base_keyboard(flat)
        )

        return

    elif user_state.get(user_id) == "district":

        temp_user[user_id]["district"] = message.text

        user_state[user_id] = "education_type"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Ta'lim turini tanlang:",
            reply_markup=make_keyboard(
                EDUCATION_TYPES
            )
        )

        return

    elif user_state.get(user_id) == "education_type":

        temp_user[user_id]["education_type"] = message.text

        if message.text == "🏫 Maktab":

            user_state[user_id] = "school_type"

            await message.answer(
                reg_status(temp_user[user_id]) +
                "\n\n🏫 Maktab turini tanlang:",
                reply_markup=make_keyboard(
                    SCHOOL_TYPES
                )
            )

        else:

            user_state[user_id] = "kindergarten"

            await message.answer(
                reg_status(temp_user[user_id]) +
                "\n\n🏡 Bog‘cha nomini kiriting:"
            )

        return


    elif user_state.get(user_id) == "kindergarten":

        temp_user[user_id]["kindergarten"] = message.text

        user_state[user_id] = "group"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n👶 Guruh nomini kiriting:"
        )

        return


    elif user_state.get(user_id) == "group":

        temp_user[user_id]["group"] = message.text

        user_state[user_id] = None

        await message.answer(
            "✅ Registratsiya yakunlandi"
        )

        return


    elif user_state.get(user_id) == "school_type":

        temp_user[user_id]["school_type"] = message.text

        user_state[user_id] = "school"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🏫 Maktab nomi yoki raqamini kiriting:"
        )

        return


    elif user_state.get(user_id) == "school":

        temp_user[user_id]["school"] = message.text

        user_state[user_id] = "class"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🎓 Sinfni tanlang:",
            reply_markup=make_keyboard(
                CLASS_LEVELS
            )
        )

        return


    elif user_state.get(user_id) == "class":

        temp_user[user_id]["class"] = message.text

        user_state[user_id] = "class_letter"

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🔤 Harfni tanlang:",
            reply_markup=make_keyboard(
                CLASS_LETTERS
            )
        )

        return


    elif user_state.get(user_id) == "class_letter":

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
            temp_user[user_id].get("birth_date"),
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

        user_state[user_id] = None

        await message.answer(
            reg_status(temp_user[user_id]) +
            "\n\n🎉 Registratsiya yakunlandi!",
            reply_markup=get_main_keyboard(
                temp_user[user_id].get("role")
            )
        )

        return
