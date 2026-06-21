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
                KeyboardButton(text="🤖 AI Generator"),
                KeyboardButton(text="📊 Mavzular statistikasi"),
                KeyboardButton(text="🧪 Test sinovi"),
            ],
            [
                KeyboardButton(text="📚 DTS boshqaruvi"),
                KeyboardButton(text="🖼 Rasmlar boshqaruvi"),
                KeyboardButton(text="📝 Dars boshqaruvi"),
            ],
            [
                KeyboardButton(text="👥 Foydalanuvchilar"),
                KeyboardButton(text="📋 So'rovnoma natijalari"),
                KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            ],
            [
                KeyboardButton(text="🤖 Test generator"),
                KeyboardButton(text="📚 BILIMNI SINASH bazasi"),
                KeyboardButton(text="📥 Test import qilish"),
            ],
        ]

    else:
        keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
