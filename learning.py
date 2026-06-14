from keyboards import get_main_keyboard

from aiogram import Router, F
from aiogram.types import Message

router = Router()

async def student_daily_plan(message):
    await message.answer("📅 Bugungi reja")

async def student_progress(message):
    await message.answer("📈 Rivojlanishim")

async def student_community(message):
    await message.answer("🌍 Hamjamiyat")

async def student_profile(message):
    await message.answer("👤 Kabinet")
