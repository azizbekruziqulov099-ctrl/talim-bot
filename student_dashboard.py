"""
student_dashboard.py — Bosh ekran moduli
Vaqtga, yoshga, jinsga mos dinamik bosh ekran
"""
import os
import psycopg2
from datetime import datetime, date, timedelta
from aiogram import F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from loader import dp, bot
from storage import user_state
from keyboards import get_main_keyboard

DATABASE_URL = os.getenv("DATABASE_URL")


def db():
    return psycopg2.connect(DATABASE_URL)


# ─────────────────────────────────────────
# VAQT ANIQLASH
# ─────────────────────────────────────────

def get_time_greeting(hour: int, group: str, gender: str, name: str) -> str:
    """Vaqt va yoshga mos salomlashish"""

    is_girl = "Ayol" in str(gender)

    if group == "junior":
        # 1-4 sinf
        if 6 <= hour < 12:
            emoji = "☀️"
            msg = f"Xayrli tong, {'qizaloq' if is_girl else 'botir'} {name}! 🌸" if is_girl else f"Xayrli tong, {name}! 💪"
        elif 12 <= hour < 17:
            emoji = "🌤"
            msg = f"Salom, {name}! Tushlikdan keyin o'ynaymizmi? 🎮"
        elif 17 <= hour < 21:
            emoji = "🌙"
            msg = f"Kechki o'yin vaqti, {name}! ⭐"
        else:
            emoji = "😴"
            msg = f"Uxlash vaqti, {name}! Ertaga davom etamiz 🌙"

    elif group == "middle":
        # 5-8 sinf
        if 6 <= hour < 12:
            emoji = "⚔️"
            msg = f"Xayrli tong, {'Malika' if is_girl else 'Qahramon'} {name}! Bugun ham g'alaba qozonamiz!"
        elif 12 <= hour < 17:
            emoji = "🎯"
            msg = f"Salom, {name}! Missiya davom etmoqda!"
        elif 17 <= hour < 21:
            emoji = "🔥"
            msg = f"Kechki mashg'ulot, {name}! Streak uzilmasin!"
        else:
            emoji = "💤"
            msg = f"Dam olish vaqti, {name}! Ertaga yangi rekord! 🏆"

    else:
        # 9-11 sinf
        if 6 <= hour < 12:
            emoji = "📊"
            msg = f"Xayrli tong, {name}! Imtihonga tayyorlanish davom etmoqda."
        elif 12 <= hour < 17:
            emoji = "📚"
            msg = f"Salom, {name}! Bilim — kelajak kaliti."
        elif 17 <= hour < 21:
            emoji = "🧠"
            msg = f"Kechki tayyorgarlik, {name}. Maqsadga yana bir qadam!"
        else:
            emoji = "🌙"
            msg = f"Kech bo'ldi, {name}. Yaxshi dam oling — erta tetik bo'lasiz."

    return f"{emoji} {msg}"


def get_time_warning(hour: int, group: str) -> str | None:
    """Vaqt bo'yicha ogohlantirish"""
    if group == "junior" and hour >= 21:
        return "😴 Uxlash vaqti! Sog'liq — birinchi o'rinda."
    if group == "middle" and hour >= 23:
        return "💤 Kech bo'ldi! Erta yotish — yaxshi natija."
    if group == "senior" and hour >= 0 and hour < 5:
        return "⚠️ Tun yarimidan oshdi. Dam oling!"
    return None


# ─────────────────────────────────────────
# PROGRESS BLOKLARI
# ─────────────────────────────────────────

def get_progress_block(user_id: int, grade: str, group: str) -> str:
    """Yoshga mos progress ko'rsatish"""
    conn = db(); cur = conn.cursor()

    try:
        # XP va streak
        cur.execute("""
            SELECT xp, streak FROM user_progress
            WHERE user_id = %s
        """, (user_id,))
        prog = cur.fetchone()
        xp     = prog[0] if prog else 0
        streak = prog[1] if prog else 0

        # O'rganilgan mavzular
        cur.execute("""
            SELECT COUNT(*) FROM learned_topics
            WHERE user_id = %s
        """, (user_id,))
        learned = cur.fetchone()[0]

        # Bugungi darslar
        cur.execute("""
            SELECT COUNT(*) FROM lesson_history
            WHERE user_id = %s AND DATE(learned_at) = %s
        """, (user_id, date.today()))
        today_lessons = cur.fetchone()[0]

        if group == "junior":
            stars = xp // 10
            plant = "🌱" if xp < 50 else "🌿" if xp < 200 else "🌳"
            bar   = "█" * min(10, xp // 20) + "░" * (10 - min(10, xp // 20))
            lines = [
                f"{plant} O'simlik: {bar}",
                f"⭐ Yulduzlar: {stars}",
                f"📖 O'rganildi: {learned} mavzu",
            ]
            if streak > 1:
                lines.append(f"🔥 {streak} kun ketma-ket!")
            if today_lessons > 0:
                lines.append(f"✅ Bugun: {today_lessons} ta dars")

        elif group == "middle":
            from progress import get_level
            level = get_level(xp)
            bar   = "█" * min(10, xp // 100) + "░" * (10 - min(10, xp // 100))
            lines = [
                f"{level['icon']} {level['name']} — {xp} XP",
                f"📈 {bar}",
                f"📖 {learned} mavzu o'rganildi",
            ]
            if streak > 1:
                lines.append(f"🔥 Streak: {streak} kun")
            if today_lessons > 0:
                lines.append(f"✅ Bugun: {today_lessons} ta dars")

        else:
            # 9-11 sinf — foiz va tahlil
            cur.execute("""
                SELECT COUNT(*) FROM dts_tree
                WHERE grade = %s AND is_deleted = FALSE
            """, (grade,))
            total = cur.fetchone()[0] or 1
            pct   = min(100, int(learned * 100 / total))
            bar   = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines = [
                f"📈 Bilim darajasi: {bar} {pct}%",
                f"📖 {learned}/{total} mavzu",
            ]
            if streak > 1:
                lines.append(f"🔥 {streak} kun faol")
            if today_lessons > 0:
                lines.append(f"✅ Bugun: {today_lessons} ta dars")

        return "\n".join(lines)

    finally:
        cur.close(); conn.close()


# ─────────────────────────────────────────
# BUGUNGI REJA
# ─────────────────────────────────────────

def get_daily_plan(user_id: int, grade: str) -> str:
    """Bugungi reja"""
    conn = db(); cur = conn.cursor()

    try:
        from progress import get_next_topic, get_repeat_topics
        next_topic = get_next_topic(user_id, grade)
        repeats    = get_repeat_topics(user_id)

        lines = ["🎯 Bugungi reja:"]

        if repeats:
            lines.append(f"🔁 Takrorlash: {len(repeats)} ta mavzu")

        if next_topic:
            lines.append(f"📘 Yangi: {next_topic[1]}")
        else:
            lines.append("🎉 Barcha mavzular o'rganildi!")

        # Kutilayotgan imtihon
        from progress import get_upcoming_exams
        upcoming = get_upcoming_exams(user_id)
        if upcoming:
            days = (upcoming[0][1] - date.today()).days
            if days <= 3:
                lines.append(f"⚠️ {days} kunda imtihon: {upcoming[0][0]}")

        return "\n".join(lines)

    finally:
        cur.close(); conn.close()


# ─────────────────────────────────────────
# TUG'ILGAN KUN
# ─────────────────────────────────────────

def check_birthday(user_id: int) -> str | None:
    """Tug'ilgan kunni tekshiradi"""
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT birth_date FROM users WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return None

        bdate = row[0]
        today = date.today()

        if hasattr(bdate, 'month'):
            if bdate.month == today.month and bdate.day == today.day:
                age = today.year - bdate.year
                return f"🎂 Bugun sening tug'ilgan kunin! {age} yoshga to'lding! 🎉🎁"
        return None
    except Exception:
        return None
    finally:
        cur.close(); conn.close()


# ─────────────────────────────────────────
# MAKTAB VAQT REJIMI
# ─────────────────────────────────────────

SCHOOL_SCHEDULE = {
    "1": {"start": 8, "end": 13},
    "2": {"start": 8, "end": 13},
    "3": {"start": 8, "end": 14},
    "4": {"start": 8, "end": 14},
    "5": {"start": 8, "end": 15},
    "6": {"start": 8, "end": 15},
    "7": {"start": 8, "end": 15},
    "8": {"start": 8, "end": 16},
    "9": {"start": 8, "end": 16},
    "10": {"start": 8, "end": 16},
    "11": {"start": 8, "end": 16},
}

def get_school_status(grade: str, hour: int, weekday: int) -> str | None:
    """Maktab vaqt holati"""
    # Shanba/Yakshanba
    if weekday >= 5:
        return "🏖 Bugun dam olish kuni!"

    schedule = SCHOOL_SCHEDULE.get(str(grade).replace("-sinf", ""), {})
    if not schedule:
        return None

    start = schedule["start"]
    end   = schedule["end"]

    if start <= hour < end:
        return f"🏫 Hozir maktab vaqti ({start}:00-{end}:00)"
    elif hour < start:
        mins = (start - hour) * 60
        return f"⏰ Maktabga {mins} daqiqa qoldi"
    else:
        return f"🏠 Maktab tugadi. Uyda o'rganish vaqti!"


# ─────────────────────────────────────────
# ASOSIY DASHBOARD QURISH
# ─────────────────────────────────────────

async def build_dashboard(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """To'liq dashboard matni va tugmalarini qaytaradi"""

    conn = db(); cur = conn.cursor()

    try:
        cur.execute("""
            SELECT full_name, class, gender, birth_date, region, district
            FROM users WHERE user_id = %s
        """, (user_id,))
        row = cur.fetchone()

        if not row:
            return "❌ Foydalanuvchi topilmadi", InlineKeyboardMarkup(inline_keyboard=[])

        full_name = row[0] or "O'quvchi"
        grade     = str(row[1] or "5")
        gender    = row[2] or ""
        region    = row[4] or ""
        district  = row[5] or ""

        name = full_name.split()[0]

        # Sinf guruhi
        try:
            g = int(grade.replace("-sinf", "").strip())
            group = "junior" if g <= 4 else "middle" if g <= 8 else "senior"
        except Exception:
            group = "middle"

        now     = datetime.now()
        hour    = now.hour
        weekday = now.weekday()

        lines = []

        # 1. Tug'ilgan kun
        bday = check_birthday(user_id)
        if bday:
            lines.append(bday)
            lines.append("")

        # 2. Salomlashish
        greeting = get_time_greeting(hour, group, gender, name)
        lines.append(greeting)

        # 3. Vaqt ogohlantirishlar
        warning = get_time_warning(hour, group)
        if warning:
            lines.append(warning)

        # 4. Maktab holati
        school_status = get_school_status(grade, hour, weekday)
        if school_status:
            lines.append(school_status)

        lines.append("━━━━━━━━━━━━━━")

        # 5. Progress
        try:
            prog_block = get_progress_block(user_id, grade, group)
            lines.append(prog_block)
        except Exception:
            pass

        lines.append("━━━━━━━━━━━━━━")

        # 6. Bugungi reja
        try:
            plan = get_daily_plan(user_id, grade)
            lines.append(plan)
        except Exception:
            pass

        # 7. Joylashuv
        if region:
            lines.append(f"━━━━━━━━━━━━━━")
            lines.append(f"📍 {region}, {district}")

        text = "\n".join(lines)

        # Tugmalar
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="▶️ Darsni boshlash", callback_data="lesson_continue"),
                    InlineKeyboardButton(text="🔄 Yangilash",       callback_data="dashboard_refresh")
                ],
                [
                    InlineKeyboardButton(text="📊 Statistika",  callback_data="dashboard_stats"),
                    InlineKeyboardButton(text="📅 Reja",        callback_data="dashboard_plan")
                ]
            ]
        )

        return text, keyboard

    finally:
        cur.close(); conn.close()


# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────

@dp.callback_query(F.data == "dashboard_refresh")
async def dashboard_refresh(call: CallbackQuery):
    """Dashboardni yangilash"""
    await call.answer("🔄 Yangilanmoqda...")
    try:
        text, keyboard = await build_dashboard(call.from_user.id)
        await call.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        await call.answer(f"❌ Xatolik: {e}", show_alert=True)


@dp.callback_query(F.data == "dashboard_stats")
async def dashboard_stats(call: CallbackQuery):
    """Statistika"""
    await call.answer()
    conn = db(); cur = conn.cursor()

    try:
        user_id = call.from_user.id

        cur.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        row   = cur.fetchone()
        grade = str(row[0] if row else "5")

        cur.execute("SELECT COUNT(*) FROM learned_topics WHERE user_id=%s", (user_id,))
        learned = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM lesson_history
            WHERE user_id=%s AND DATE(learned_at)=%s
        """, (user_id, date.today()))
        today = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM lesson_history
            WHERE user_id=%s AND learned_at >= %s
        """, (user_id, date.today() - timedelta(days=7)))
        week = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM lesson_history
            WHERE user_id=%s AND learned_at >= %s
        """, (user_id, date.today() - timedelta(days=30)))
        month = cur.fetchone()[0]

        cur.execute("SELECT xp, streak FROM user_progress WHERE user_id=%s", (user_id,))
        prog   = cur.fetchone()
        xp     = prog[0] if prog else 0
        streak = prog[1] if prog else 0

        cur.execute("""
            SELECT COUNT(*) FROM dts_tree
            WHERE grade=%s AND is_deleted=FALSE
        """, (grade,))
        total = cur.fetchone()[0] or 1
        pct   = min(100, int(learned * 100 / total))

        text = (
            f"📊 STATISTIKA\n"
            f"━━━━━━━━━━━━━━\n"
            f"📈 Bilim darajasi: {pct}%\n"
            f"📖 O'rganildi: {learned}/{total}\n"
            f"━━━━━━━━━━━━━━\n"
            f"✅ Bugun: {today} dars\n"
            f"📅 Bu hafta: {week} dars\n"
            f"🗓 Bu oy: {month} dars\n"
            f"━━━━━━━━━━━━━━\n"
            f"⭐ XP: {xp}\n"
            f"🔥 Streak: {streak} kun"
        )

        await call.message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Ortga", callback_data="dashboard_refresh")
            ]])
        )

    finally:
        cur.close(); conn.close()


@dp.callback_query(F.data == "dashboard_plan")
async def dashboard_plan(call: CallbackQuery):
    """Haftalik reja"""
    await call.answer()
    conn = db(); cur = conn.cursor()

    try:
        user_id = call.from_user.id
        cur.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        row   = cur.fetchone()
        grade = str(row[0] if row else "5")

        from progress import get_next_topic, get_repeat_topics, get_upcoming_exams
        next_topic = get_next_topic(user_id, grade)
        repeats    = get_repeat_topics(user_id)
        upcoming   = get_upcoming_exams(user_id)

        lines = ["📅 HAFTALIK REJA\n━━━━━━━━━━━━━━"]

        if repeats:
            lines.append(f"🔁 Takrorlash ({len(repeats)} ta):")
            for r in repeats[:3]:
                lines.append(f"  • {r[1]}")

        if next_topic:
            lines.append(f"\n📘 Keyingi dars:\n  {next_topic[1]}")

        if upcoming:
            lines.append("\n📅 Kelayotgan imtihonlar:")
            for ex in upcoming:
                days = (ex[1] - date.today()).days
                icon = "🚨" if ex[2] else "🔔"
                lines.append(f"  {icon} {ex[0]} — {days} kun")

        if not repeats and not next_topic and not upcoming:
            lines.append("🎉 Hamma narsa joyida!")

        await call.message.answer(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Ortga", callback_data="dashboard_refresh")
            ]])
        )

    finally:
        cur.close(); conn.close()
