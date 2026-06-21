from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

def get_main_keyboard(role=None):

    if "🧒 O‘quvchi" in str(role):

        keyboard=[
            [
                KeyboardButton(text="🎯 Bugungi reja"),
                KeyboardButton(text="🧪 Bilimni sinash")
            ],
            [
                KeyboardButton(text="📈 Rivojlanishim"),
                KeyboardButton(text="👤 Kabinet")
            ],
            [
                KeyboardButton(text="🌍 Hamjamiyat"),
                KeyboardButton(text="⚙️ Sozlamalar")
            ]
        ]

    elif "👨‍🏫 O‘qituvchi" in str(role):

        keyboard = [
            [KeyboardButton(text="🧠 Bilimni sinash"),
             KeyboardButton(text="📊 Bilim darajam")],

            [KeyboardButton(text="👨‍🎓 O‘quvchilar natijasi"),
             KeyboardButton(text="🏫 Maktab statistikasi")],

            [KeyboardButton(text="🌍 Viloyat statistikasi"),
             KeyboardButton(text="📊 So‘rovnoma")],

            [KeyboardButton(text="⚙️ Akkaunt sozlamalari")]
        ]
    elif role == "Admin":

        keyboard = [
            [KeyboardButton(text="🇺🇿 Respublika statistikasi"),
            KeyboardButton(text="🤖 AI Generator"),
            KeyboardButton(text="🏫 Maktab statistikasi")],

            [KeyboardButton(text="🎓 Sinf statistikasi"),
            KeyboardButton(text="👨‍🎓 TOP o‘quvchilar"),
            KeyboardButton(text="👨‍🏫 TOP o‘qituvchilar")],

            [KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            KeyboardButton(text="📋 So‘rovnoma natijalari"),
            KeyboardButton(text="📚 BILIMNI SINASH bazasi")],

            [KeyboardButton(text="👥 Foydalanuvchilar statistikasi"),
            KeyboardButton(text="📚 DTS boshqaruvi"),
            KeyboardButton(text="🤖 Test generator")]
        ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
