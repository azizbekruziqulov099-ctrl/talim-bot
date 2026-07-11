from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
def get_main_keyboard(role=None, unread_errors=0):
    r = str(role or "").strip().lower()
    if any(x in r for x in ("ota","parent","ona")):
        keyboard = [
            [KeyboardButton(text="👶 Farzandim"),       KeyboardButton(text="📊 Nazorat")],
            [KeyboardButton(text="📋 Yoqlama"),         KeyboardButton(text="⭐ Baholar")],
            [KeyboardButton(text="📝 Uy imtihoni"),     KeyboardButton(text="💬 O'qituvchi")],
            [KeyboardButton(text="🤖 Yordamchi"),       KeyboardButton(text="👤 Kabinet")],
        ]
    elif any(x in r for x in ("quvchi","student")):
        keyboard = [
            [KeyboardButton(text="🎯 Bugungi reja"),    KeyboardButton(text="🧪 Bilimni sinash")],
            [KeyboardButton(text="📚 Bilimni mustahkamlash"), KeyboardButton(text="📈 Rivojlanishim")],
            [KeyboardButton(text="📚 To'garaklar"),     KeyboardButton(text="🎨 Rasm chizdir")],
            [KeyboardButton(text="🤖 Yordamchi"),       KeyboardButton(text="👤 Kabinet")],
        ]
    elif any(x in r for x in ("qituvchi","teacher")):
        keyboard = [
            [KeyboardButton(text="🧠 Bilimni sinash"),  KeyboardButton(text="📊 Bilim darajam")],
            [KeyboardButton(text="📚 To'garaklar"),     KeyboardButton(text="📊 Imtihon")],
            [KeyboardButton(text="🎨 Rasm chizdir"),    KeyboardButton(text="🤖 Yordamchi")],
            [KeyboardButton(text="👤 Kabinet")],
        ]
    elif "admin" in r:
        err = f" 🔴{unread_errors}" if unread_errors > 0 else ""
        keyboard = [
            [KeyboardButton(text="🚀 Mavzu tayyorla"),  KeyboardButton(text="📊 Test statistikasi"),
             KeyboardButton(text="📋 Shablonlar"),       KeyboardButton(text="📝 Shablon to'ldirish")],
            [KeyboardButton(text="📚 Kitoblar ▾"),       KeyboardButton(text="🧠 Bilimlar ▾"),
             KeyboardButton(text="🖼 Rasmlar boshqaruvi"), KeyboardButton(text="🎨 AI Rasm yaratish")],
            [KeyboardButton(text="🎥 Video havola"),     KeyboardButton(text="📤 Video fayl"),
             KeyboardButton(text="📝 Video matni"),      KeyboardButton(text="🎵 Audio matni")],
            [KeyboardButton(text=f"📊 Hisobotlar & Xatolar{err}"), KeyboardButton(text="👥 Foydalanuvchilar"),
             KeyboardButton(text="🧭 DTS topik boshqaruvi"), KeyboardButton(text="📚 To'garaklar")],
            [KeyboardButton(text="🤖 Yordamchi"),        KeyboardButton(text="📖 Darslar holati"),
             KeyboardButton(text="👤 Kabinet")],
        ]
    else:
        keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
