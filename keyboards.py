from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

def get_main_keyboard(role=None):

    # O‘quvchi menyusi
    if role == "O‘quvchi":
        keyboard = [
            [KeyboardButton(text="📚 BILIMNI SINASH"),
             KeyboardButton(text="📚 DTS Navigator")],
            [KeyboardButton(text="🎓 Sinf statistikasi"),
            KeyboardButton(text="🏫 Maktab statistikasi")],
            [KeyboardButton(text="📊 So‘rovnoma"),
            KeyboardButton(text="⚙️ Akkaunt sozlamalari")]
        ]
    # O‘qituvchi menyusi
    elif role == "O‘qituvchi":
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
            [KeyboardButton(text="AAAAAAAAAAAA"),]
           
        ]
    

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
