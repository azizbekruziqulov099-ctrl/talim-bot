from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role=None):

    if "🧒 O'quvchi" in str(role):
        keyboard = [
            [
                KeyboardButton(text="🎯 Bugungi reja"),
                KeyboardButton(text="🧪 Bilimni sinash"),
                KeyboardButton(text="📈 Rivojlanishim"),
            ],
            [
                KeyboardButton(text="🌍 Hamjamiyat"),
                KeyboardButton(text="👤 Kabinet"),
                KeyboardButton(text="⚙️ Sozlamalar"),
            ],
        ]

    elif "👨‍🏫 O'qituvchi" in str(role):
        keyboard = [
            [
                KeyboardButton(text="🧠 Bilimni sinash"),
                KeyboardButton(text="📊 Bilim darajam"),
                KeyboardButton(text="👨‍🎓 O'quvchilar natijasi"),
            ],
            [
                KeyboardButton(text="🏫 Maktab statistikasi"),
                KeyboardButton(text="🌍 Viloyat statistikasi"),
                KeyboardButton(text="📊 So'rovnoma"),
            ],
            [
                KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            ],
        ]

    elif role == "Admin":
        keyboard = [
            [
                KeyboardButton(text="📋 Shablonlar"),
                KeyboardButton(text="📊 Test statistikasi"),
                KeyboardButton(text="🧪 Test sinovi"),
            ],
            [
                KeyboardButton(text="🖼 Rasmlar boshqaruvi"),
                KeyboardButton(text="👥 Foydalanuvchilar"),
                KeyboardButton(text="📋 So'rovnoma natijalari"),
            ],
            [
                KeyboardButton(text="🧭 DTS topik boshqaruvi"),
                KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            ],
        ]

    else:
        keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
