from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard(role=None, unread_errors=0):
    r = str(role or "").strip().lower()

    if any(x in r for x in ("quvchi", "student", "ota", "parent")):
        keyboard = [
            [
                KeyboardButton(text="🎯 Bugungi reja"),
                KeyboardButton(text="📚 Bilimni mustahkamlash"),
                KeyboardButton(text="🧪 Bilimni sinash"),
            ],
            [
                KeyboardButton(text="🤖 Yordamchi"),
                KeyboardButton(text="📈 Rivojlanishim"),
                KeyboardButton(text="👤 Kabinet"),
            ],
        ]

    elif any(x in r for x in ("qituvchi", "teacher")):
        keyboard = [
            [
                KeyboardButton(text="🧠 Bilimni sinash"),
                KeyboardButton(text="📊 Bilim darajam"),
            ],
            [KeyboardButton(text="⚙️ Akkaunt sozlamalari")],
        ]

    elif "admin" in r:
        err_label = f"🆘 Xatolar ({unread_errors})" if unread_errors > 0 else "🆘 Xatolar"
        keyboard = [
            [
                KeyboardButton(text="📋 Shablonlar"),
                KeyboardButton(text="📊 Test statistikasi"),
                KeyboardButton(text="📝 Shablon to'ldirish"),
            ],
            [
                KeyboardButton(text="📚 Kitoblar ▾"),
            ],
            [
                KeyboardButton(text="🧠 Bilimlar ▾"),
            ],
            [
                KeyboardButton(text="📊 Hisobotlar & Xatolar" + (f" 🔴{unread_errors}" if unread_errors > 0 else "")),
            ],
            [
                KeyboardButton(text="🖼 Rasmlar boshqaruvi"),
                KeyboardButton(text="🎨 AI Rasm yaratish"),
                KeyboardButton(text="👥 Foydalanuvchilar"),
                KeyboardButton(text="🧭 DTS topik boshqaruvi"),
            ],
            [
                KeyboardButton(text="📖 Darslar holati"),
                KeyboardButton(text="⚙️ Akkaunt sozlamalari"),
            ],
        ]

    else:
        keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
