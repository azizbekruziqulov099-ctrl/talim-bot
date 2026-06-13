from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

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
