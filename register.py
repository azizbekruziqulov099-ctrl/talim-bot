from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)
import json

with open("regions.json", "r", encoding="utf-8") as f:
    REGIONS = json.load(f)

user_state = {}
temp_user = {}

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

    # ROLE
    if user_state.get(user_id) == "role":

        temp_user[user_id] = {
            "role": message.text
        }

        user_state[user_id] = "full_info"

        await message.answer(
            "👤 Ma'lumotlarni kiriting:\n\n"
            "F.I.Sh:\n"
            "Tug‘ilgan sana:\n"
            "Jins:\n"
            "Viloyat:\n"
            "Tuman:"
        )

        return

    # FULL INFO
    elif user_state.get(user_id) == "full_info":

        lines = message.text.split("\n")

        data = {}

        for line in lines:

            if ":" in line:

                key, value = line.split(":", 1)

                data[key.strip()] = value.strip()

        temp_user[user_id]["full_name"] = data.get("F.I.Sh", "")
        temp_user[user_id]["birth_date"] = data.get("Tug‘ilgan sana", "")
        temp_user[user_id]["gender"] = data.get("Jins", "")
        temp_user[user_id]["region"] = data.get("Viloyat", "")
        temp_user[user_id]["district"] = data.get("Tuman", "")

        role = temp_user[user_id]["role"]

        if role == "🧒 O‘quvchi":

            user_state[user_id] = "education_type"

            await message.answer(
                "🎓 Ta'lim turini tanlang:",
                reply_markup=make_keyboard(
                    EDUCATION_TYPES
                )
            )

        else:

            user_state[user_id] = "teacher_subject"

            await message.answer(
                "📚 Faningizni kiriting:"
            )

        return

    # EDUCATION TYPE
    elif user_state.get(user_id) == "education_type":

        temp_user[user_id]["education_type"] = message.text

        if message.text == "🏫 Maktab":

            user_state[user_id] = "school_type"

            await message.answer(
                "🏫 Maktab turini tanlang:",
                reply_markup=make_keyboard(
                    SCHOOL_TYPES
                )
            )

        else:

            user_state[user_id] = "kindergarten"

            await message.answer(
                "🏡 Bog‘cha nomini kiriting:"
            )

        return

    elif user_state.get(user_id) == "kindergarten":

        temp_user[user_id]["kindergarten"] = message.text

        user_state[user_id] = "group"

        await message.answer(
            "👶 Guruh nomini kiriting:"
        )

        return

    elif user_state.get(user_id) == "group":

        temp_user[user_id]["group"] = message.text

        user_state[user_id] = None

        await message.answer(
            "✅ Registratsiya yakunlandi"
        )

        return

    # SCHOOL TYPE
    elif user_state.get(user_id) == "school_type":

        temp_user[user_id]["school_type"] = message.text

        user_state[user_id] = "school"

        await message.answer(
            "🏫 Maktab nomi yoki raqamini kiriting:"
        )

        return

    # SCHOOL
    elif user_state.get(user_id) == "school":

        temp_user[user_id]["school"] = message.text

        user_state[user_id] = "class"

        await message.answer(
            "🎓 Sinfni tanlang:",
            reply_markup=make_keyboard(
                CLASS_LEVELS
            )
        )

        return

    # CLASS
    elif user_state.get(user_id) == "class":

        temp_user[user_id]["class"] = message.text

        user_state[user_id] = "class_letter"

        await message.answer(
            "🔤 Harfni tanlang:",
            reply_markup=make_keyboard(
                CLASS_LETTERS
            )
        )

        return

    # CLASS LETTER
    elif user_state.get(user_id) == "class_letter":

        temp_user[user_id]["class_letter"] = message.text

        user_state[user_id] = None

        await message.answer(
            "✅ Registratsiya yakunlandi"
        )

        print(temp_user[user_id])

        return

    # TEACHER SUBJECT
    elif user_state.get(user_id) == "teacher_subject":

        temp_user[user_id]["subject"] = message.text

        user_state[user_id] = None

        await message.answer(
            "✅ O‘qituvchi registratsiyasi yakunlandi"
        )

        print(temp_user[user_id])

        return
