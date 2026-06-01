from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton
)

async def start_generator(message):

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="▶️ Boshlash")],
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🔙 Ortga")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🤖 Test generator",
        reply_markup=kb
    )
