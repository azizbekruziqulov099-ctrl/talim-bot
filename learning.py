from aiogram import Router
from keyboards import get_main_keyboard

router = Router()

from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "🎯 Bugungi reja")
async def daily_plan(message: Message):
    await message.answer(
        "📅 Bugungi rejangiz tayyor.\n\n"
        "⏱ Tavsiya etilgan vaqt: 20 daqiqa\n"
        "🕖 O'quv vaqti: 07:00 - 23:00\n\n"
        "🚀 Boshlashga tayyormisiz?"
    )


@router.message(F.text == "📈 Rivojlanishim")
async def progress(message: Message):
    await message.answer("📈 Bilim profilingiz shakllanmoqda...")


@router.message(F.text == "🌍 Hamjamiyat")
async def community(message: Message):
    await message.answer(
        "🌍 Hamjamiyat\n\n"
        "🏫 Maktabim\n"
        "🏛 Tumanim\n"
        "📍 Viloyatim\n"
        "🇺🇿 Respublika"
    )


@router.message(F.text == "👤 Kabinet")
async def profile(message: Message):
    await message.answer(
        "👤 Shaxsiy kabinet\n\n"
        "⚙️ Sozlamalar\n"
        "👥 Do'st taklif qilish\n"
        "🧠 Bilimni baholash"
    )
