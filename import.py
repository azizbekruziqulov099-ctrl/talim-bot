from aiogram import types

async def start_dts_import(message: types.Message):
    await message.answer(
        "TXT yoki XLSX fayl yuboring"
    )