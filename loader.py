from aiogram import Bot, Dispatcher
import os
from aiogram.types import CallbackQuery

try:
    from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False
    SimpleCalendar = None
    SimpleCalendarCallback = None

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

if HAS_CALENDAR:
    @dp.callback_query(SimpleCalendarCallback.filter())
    async def process_simple_calendar(
        callback_query: CallbackQuery,
        callback_data: SimpleCalendarCallback
    ):
        from storage import user_state, temp_user
        from register import reg_status, make_keyboard
        selected, date = await SimpleCalendar().process_selection(
            callback_query, callback_data
        )
        if selected:
            user_id = callback_query.from_user.id
            temp_user[user_id]["birth_date"] = date.strftime("%d.%m.%Y")
            user_state[user_id] = "gender"
            await callback_query.message.edit_text(
                reg_status(temp_user[user_id]) + "\n\n👤 Jinsni tanlang:"
            )
            await callback_query.message.answer(
                "👤 Jinsni tanlang:",
                reply_markup=make_keyboard(["👨 Erkak","👩 Ayol"])
            )
