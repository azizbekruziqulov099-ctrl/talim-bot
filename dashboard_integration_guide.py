# ════════════════════════════════════════════════
#  Talim.py ga QO'SHIMCHA — student_dashboard
#  Faylning boshiga import qo'shing:
# ════════════════════════════════════════════════

from student_dashboard import (
    show_dashboard,
    refresh_dashboard,
    show_progress_screen,
)


# ────────────────────────────────────────────────
#  1.  /start da o'quvchi uchun — mavjud blokni
#      quyidagi bilan ALMASHTIRING:
# ────────────────────────────────────────────────

# ESkI KOD (o'chiring):
#   await message.answer(welcome_text, reply_markup=get_main_keyboard(role))

# YANGI KOD (qo'ying):
#   await show_dashboard(message, message.from_user.id)


# ────────────────────────────────────────────────
#  2.  handle_all ichida — "🎯 Bugungi reja" ni
#      ALMASHTIRING:
# ────────────────────────────────────────────────

# ESKI:
#   if message.text == "🎯 Bugungi reja":
#       await continue_learning(message)
#       return

# YANGI:
#   if message.text == "🎯 Bugungi reja":
#       await show_dashboard(message)
#       return


# ────────────────────────────────────────────────
#  3.  test_buttons (callback_query handler) ichiga
#      quyidagi bloklarni QO'SHING (mavjud if'lar
#      orasiga, yuqoriroqqa):
# ────────────────────────────────────────────────

DASHBOARD_CALLBACKS = """
    if call.data == "dashboard_refresh":
        await refresh_dashboard(call)
        return

    if call.data == "show_progress":
        await show_progress_screen(call)
        return

    if call.data == "show_subjects":
        # continue_learning mavjud funksiyasiga yo'naltiradi
        await call.answer()
        await continue_learning(call.message)
        return
"""

# ────────────────────────────────────────────────
#  4.  users jadvaliga YANGI USTUNLAR kerak
#      (agar mavjud bo'lmasa, bir marta ishlatiladi):
# ────────────────────────────────────────────────

MIGRATIONS = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;
"""

# Buni init_db() ichiga yoki alohida migration script sifatida qo'shing.
