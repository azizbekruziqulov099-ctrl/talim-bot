from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

user_state = {}
temp_user = {}

EDUCATION_LEVELS = [
    "👶 Maktabgacha",
    "🏫 Maktab",
    "🎓 Bakalavr",
    "🎓 Magistratura",
    "🎓 Doktorantura"
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
    "A",
    "B",
    "C",
    "D",
    "E",
    "Bilmayman"
]

def make_keyboard(items):

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i)]
            for i in items
        ],
        resize_keyboard=True
    )

REGISTER_STATES = [
    "role",
    "education_level",
    "region",
    "district",
    "school_type",
    "class",
    "class_letter",
    "invite_code"
]
