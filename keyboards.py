from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role=None, unread_errors=0):
    r = str(role or "").strip().lower()

    # O'quvchi (barcha variantlar)
    if any(x in r for x in ("quvchi", "student", "ota", "parent")):
        keyboard = [
            [
                KeyboardButton(text="🎯 Bugungi reja"),
                KeyboardButton(text="📚 Bilimni mustahkamlash"),
                KeyboardButton(text="🧪 Bilimni sinash"),
            ],
            [
                KeyboardButton(text="📈 Rivojlanishim"),
                KeyboardButton(text="🌍 Hamjamiyat"),
                KeyboardButton(text="👤 Kabinet"),
            ],
        ]

    # O'qituvchi
    elif any(x in r for x in ("qituvchi", "teacher")):
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
            [KeyboardButton(text="⚙️ Akkaunt sozlamalari")],
        ]

    # Admin
    elif "admin" in r:
        err_label = f"🆘 Xatolar ({unread_errors})" if unread_errors > 0 else "🆘 Xatolar"
        keyboard = [
            [
                KeyboardButton(text="📋 Shablonlar"),
                KeyboardButton(text="📊 Test statistikasi"),
                KeyboardButton(text="📖 Kitob yaratish"),
            ],
            [
                KeyboardButton(text="🖼 Rasmlar boshqaruvi"),
                KeyboardButton(text="👥 Foydalanuvchilar"),
                KeyboardButton(text="📋 So'rovnoma natijalari"),
            ],
            [
                KeyboardButton(text="🧭 DTS topik boshqaruvi"),
                KeyboardButton(text="📖 Darslar holati"),
                KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            ],
            [
                KeyboardButton(text="📚 Bilimni mustahkamlash"),
                KeyboardButton(text="🧪 Bilimni sinash"),
                KeyboardButton(text=err_label),
            ],
        ]

    else:
        keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
