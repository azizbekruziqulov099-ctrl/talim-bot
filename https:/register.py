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

SCHOOL_TYPES = [
    "🏫 Oddiy maktab",
    "⭐ Ixtisoslashtirilgan maktab",
    "🇺🇿 Prezident maktabi",
    "🧮 Al-Xorazmiy maktabi",
    "🪖 Harbiy maktab",
    "🎨 San'at maktabi",
    "📖 IDUM"
]

CLASS_LETTERS = [
    "A", "B", "C", "D", "E"
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
            KeyboardButton(text=item)
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

elif user_state.get(message.from_user.id) == "district":

    temp_user[message.from_user.id]["district"] = message.text

    education = temp_user[
        message.from_user.id
    ]["education_level"]

    if education == "🏫 Maktab":

        user_state[
            message.from_user.id
        ] = "school_type"

        await message.answer(
            "🏫 Maktab turini tanlang:",
            reply_markup=make_keyboard(
                SCHOOL_TYPES
            )
        )

    else:

        user_state[
            message.from_user.id
        ] = "kindergarten"

        await message.answer(
            "🏡 Bog‘cha nomini kiriting:"
        )

    return
