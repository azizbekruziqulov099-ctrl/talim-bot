"""
student_dashboard.py — O'quvchi bosh ekrani

Xususiyatlar:
  • Vaqtga mos  (ertalab / kunduz / kech)
  • Yoshga mos  (junior 1-4 / middle 5-8 / senior 9-11)
  • Jinsga mos  salomlashuv
  • Maktab vaqt rejimi  (dars vaqti ogohlantirishi)
  • Tug'ilgan kun sovg'asi
  • "Yangilash" tugmasi
"""

from __future__ import annotations

import os
import re
import asyncio
from datetime import date, datetime, time as dtime

import psycopg2
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")


# ═══════════════════════════════════════════════════════
#  DB YORDAMCHI
# ═══════════════════════════════════════════════════════

def _db():
    return psycopg2.connect(DATABASE_URL)


def _fetch_user(user_id: int) -> dict | None:
    conn = _db(); cur = conn.cursor()
    cur.execute("""
        SELECT full_name, class, role, gender, birth_date
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return None
    return {
        "full_name":  row[0] or "O'quvchi",
        "grade":      row[1] or "5",
        "role":       row[2] or "O'quvchi",
        "gender":     row[3] or "",
        "birth_date": row[4],          # date | None
    }


# ═══════════════════════════════════════════════════════
#  VAQT YORDAMCHILARI
# ═══════════════════════════════════════════════════════

def _now_uz() -> datetime:
    """O'zbekiston vaqti (UTC+5)."""
    from datetime import timezone, timedelta
    tz_uz = timezone(timedelta(hours=5))
    return datetime.now(tz_uz)


def _time_block(now: datetime) -> str:
    """ertalab | kunduz | kech"""
    h = now.hour
    if 5 <= h < 12:
        return "ertalab"
    if 12 <= h < 18:
        return "kunduz"
    return "kech"


# Maktab dars jadvali (daqiqa): 8:00 – 13:30 (standart)
_SCHOOL_START = dtime(8, 0)
_SCHOOL_END   = dtime(13, 30)


def _is_school_time(now: datetime) -> bool:
    t = now.time()
    return (
        now.weekday() < 5           # dushanba–juma
        and _SCHOOL_START <= t <= _SCHOOL_END
    )


# ═══════════════════════════════════════════════════════
#  SINF GURUHI
# ═══════════════════════════════════════════════════════

def _grade_int(grade_str: str) -> int:
    m = re.search(r"\d+", str(grade_str))
    return int(m.group()) if m else 5


def _age_group(grade_str: str) -> str:
    g = _grade_int(grade_str)
    if g <= 4:  return "junior"
    if g <= 8:  return "middle"
    return "senior"


# ═══════════════════════════════════════════════════════
#  SALOMLASHUV MATNI
# ═══════════════════════════════════════════════════════

_GREET: dict[str, dict[str, str]] = {
    "junior": {
        "ertalab": "☀️ Xayrli tong",
        "kunduz":  "🌤 Salom",
        "kech":    "🌙 Kechqurun ham o'qish yaxshi",
    },
    "middle": {
        "ertalab": "🌅 Xayrli tong",
        "kunduz":  "👋 Salom",
        "kech":    "🌆 Kechqurun faol bo'lding",
    },
    "senior": {
        "ertalab": "🌄 Xayrli tong",
        "kunduz":  "💼 Salom",
        "kech":    "🌃 Kech o'quvchi — yaxshi qadam",
    },
}

_GENDER_ICON = {
    "Erkak":  "👦",
    "Ayol":   "👧",
    "":       "🧒",
}


def _greeting(user: dict, now: datetime) -> str:
    group  = _age_group(user["grade"])
    block  = _time_block(now)
    greet  = _GREET[group][block]
    name   = user["full_name"].split()[0]
    icon   = _GENDER_ICON.get(user.get("gender", ""), "🧒")
    return f"{greet}, {icon} {name}!"


# ═══════════════════════════════════════════════════════
#  TUG'ILGAN KUN
# ═══════════════════════════════════════════════════════

def _birthday_gift(user: dict, today: date) -> str | None:
    bd = user.get("birth_date")
    if not bd:
        return None
    try:
        bd_date = bd if isinstance(bd, date) else date.fromisoformat(str(bd))
    except Exception:
        return None
    if bd_date.month == today.month and bd_date.day == today.day:
        name = user["full_name"].split()[0]
        return (
            f"🎂🎉 Bugun sening tug'ilgan kuning, {name}!\n"
            f"Tabriklaymiz! Ko'p yasha, bilimdon bo'l! 🎁"
        )
    return None


# ═══════════════════════════════════════════════════════
#  PROGRESS BLOKLARI (yoshga mos)
# ═══════════════════════════════════════════════════════

def _progress_block(user_id: int, user: dict) -> str:
    from progress import get_progress, get_level, xp_display

    prog   = get_progress(user_id)
    xp     = prog["xp"]
    streak = prog["streak"]
    group  = _age_group(user["grade"])
    grade  = user["grade"]

    lines = []

    if group == "junior":
        stars = xp // 10
        plant = "🌱" if xp < 50 else "🌿" if xp < 150 else "🌳"
        bar   = "█" * min(10, xp // 20) + "░" * (10 - min(10, xp // 20))
        lines.append(f"{plant} O'sish: {bar}")
        lines.append(f"⭐ Yulduzlar: {stars}")

    elif group == "middle":
        lvl = get_level(xp)
        nxt_xp = [200, 500, 1000, 2000, 9999]
        cur_idx = [200, 500, 1000, 2000, 9999].index(
            min(n for n in nxt_xp if n > xp), 0
        ) if xp < 2000 else 4
        to_next = nxt_xp[cur_idx] - xp if xp < 2000 else 0
        lines.append(f"{lvl['icon']} {lvl['name']} — {xp} XP")
        if to_next:
            lines.append(f"🔜 Keyingi daraja: {to_next} XP kerak")

    else:  # senior
        pct = min(100, xp // 20)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"📈 Bilim darajasi: {bar} {pct}%")
        lines.append(xp_display(xp, grade))

    if streak > 1:
        fire = "🔥" * min(streak, 5)
        lines.append(f"{fire} Streak: {streak} kun!")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
#  ESLATMALAR BLOKI
# ═══════════════════════════════════════════════════════

def _reminders_block(user_id: int, user: dict, now: datetime) -> str:
    from progress import get_pending_exams, get_repeat_topics, get_upcoming_exams, get_next_topic

    grade   = user["grade"]
    lines   = []
    today   = now.date()

    # Majburiy imtihon
    pending   = get_pending_exams(user_id)
    mandatory = [e for e in pending if e[3]]
    if mandatory:
        e = mandatory[0]
        lines.append(f"🚨 MAJBURIY IMTIHON: {e[1]}")

    # Takrorlash
    repeats = get_repeat_topics(user_id)
    if repeats:
        lines.append(f"🔁 Takrorlash kutmoqda: {len(repeats)} ta mavzu")

    # Kelayotgan imtihon
    upcoming = get_upcoming_exams(user_id)
    if upcoming and not mandatory:
        days = (upcoming[0][1] - today).days
        lines.append(f"📅 {days} kun ichida imtihon: {upcoming[0][0]}")

    # Keyingi mavzu
    next_t = get_next_topic(user_id, grade)
    if next_t:
        lines.append(
            f"\n🎯 Keyingi mavzu:\n"
            f"   📚 {next_t[3]}\n"
            f"   📝 {next_t[2]}\n"
            f"   🔑 {next_t[1]}"
        )

    return "\n".join(lines) if lines else "✅ Hamma narsa joyida!"


# ═══════════════════════════════════════════════════════
#  MAKTAB VAQTI OGOHLANTIRISHRI
# ═══════════════════════════════════════════════════════

def _school_notice(now: datetime, group: str) -> str | None:
    if not _is_school_time(now):
        return None
    if group == "junior":
        return "🏫 Hozir dars vaqti — darsdan keyin o'qiymiz! 😊"
    if group == "middle":
        return "🏫 Dars vaqti. Botni darsdan keyin ochasiz!"
    return "📚 Dars jarayonida. Kechga saqla."


# ═══════════════════════════════════════════════════════
#  KLAVIATURA
# ═══════════════════════════════════════════════════════

def _dashboard_keyboard(user_id: int, user: dict) -> InlineKeyboardMarkup:
    from progress import get_pending_exams, get_repeat_topics, get_next_topic

    grade     = user["grade"]
    pending   = get_pending_exams(user_id)
    mandatory = [e for e in pending if e[3]]
    repeats   = get_repeat_topics(user_id)
    next_t    = get_next_topic(user_id, grade)

    rows = []

    # Majburiy imtihon tugmasi
    if mandatory:
        rows.append([InlineKeyboardButton(
            text=f"🚨 Imtihonni boshlash",
            callback_data=f"exam_start_{mandatory[0][0]}"
        )])

    # Darsni davom ettirish
    if next_t:
        rows.append([InlineKeyboardButton(
            text="▶️ Darsni davom ettirish",
            callback_data="lesson_continue"
        )])

    # Takrorlash
    if repeats:
        rows.append([InlineKeyboardButton(
            text=f"🔁 Takrorlash ({len(repeats)} ta)",
            callback_data="lesson_repeat"
        )])

    # Fanlar ro'yxati
    rows.append([InlineKeyboardButton(
        text="📚 Barcha fanlar",
        callback_data="show_subjects"
    )])

    # Progress
    rows.append([InlineKeyboardButton(
        text="📊 Mening progressim",
        callback_data="show_progress"
    )])

    # Yangilash
    rows.append([InlineKeyboardButton(
        text="🔄 Yangilash",
        callback_data="dashboard_refresh"
    )])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ═══════════════════════════════════════════════════════
#  ASOSIY FUNKSIYA
# ═══════════════════════════════════════════════════════

async def show_dashboard(message: Message, user_id: int | None = None) -> None:
    """
    Bosh ekranni yuboradi.
    message — aiogram Message yoki callback.message
    user_id — ixtiyoriy, default = message.from_user.id
    """
    uid   = user_id or message.from_user.id
    now   = _now_uz()
    today = now.date()

    # Foydalanuvchi ma'lumotlari
    user = _fetch_user(uid)
    if not user:
        await message.answer("❌ Avval ro'yxatdan o'ting.")
        return

    group = _age_group(user["grade"])

    sections: list[str] = []

    # 1. Tug'ilgan kun sovg'asi (eng yuqorida)
    gift = _birthday_gift(user, today)
    if gift:
        sections.append(gift)

    # 2. Salomlashuv
    sections.append(_greeting(user, now))

    # 3. Maktab vaqti ogohlantirishi
    notice = _school_notice(now, group)
    if notice:
        sections.append(notice)

    sections.append("━━━━━━━━━━━━━━")

    # 4. Progress bloki
    sections.append(_progress_block(uid, user))

    sections.append("━━━━━━━━━━━━━━")

    # 5. Eslatmalar
    sections.append(_reminders_block(uid, user, now))

    text = "\n".join(sections)

    keyboard = _dashboard_keyboard(uid, user)

    await message.answer(text, reply_markup=keyboard)


async def refresh_dashboard(call: CallbackQuery) -> None:
    """
    🔄 Yangilash tugmasi bosilganda mavjud xabarni tahrirlaydi.
    """
    uid   = call.from_user.id
    now   = _now_uz()
    today = now.date()

    user = _fetch_user(uid)
    if not user:
        await call.answer("❌ Foydalanuvchi topilmadi", show_alert=True)
        return

    group = _age_group(user["grade"])

    sections: list[str] = []

    gift = _birthday_gift(user, today)
    if gift:
        sections.append(gift)

    sections.append(_greeting(user, now))

    notice = _school_notice(now, group)
    if notice:
        sections.append(notice)

    sections.append("━━━━━━━━━━━━━━")
    sections.append(_progress_block(uid, user))
    sections.append("━━━━━━━━━━━━━━")
    sections.append(_reminders_block(uid, user, now))

    text     = "\n".join(sections)
    keyboard = _dashboard_keyboard(uid, user)

    try:
        await call.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await call.message.answer(text, reply_markup=keyboard)

    await call.answer("✅ Yangilandi")


# ═══════════════════════════════════════════════════════
#  PROGRESS EKRANI (alohida)
# ═══════════════════════════════════════════════════════

async def show_progress_screen(call: CallbackQuery) -> None:
    uid  = call.from_user.id
    user = _fetch_user(uid)
    if not user:
        await call.answer("❌ Topilmadi", show_alert=True)
        return

    from progress import get_progress, get_level, get_repeat_topics
    prog   = get_progress(uid)
    xp     = prog["xp"]
    streak = prog["streak"]
    lvl    = get_level(xp)
    grade  = user["grade"]

    conn = _db(); cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM learned_topics WHERE user_id = %s
    """, (uid,))
    learned = cur.fetchone()[0]
    cur.execute("""
        SELECT COUNT(*) FROM dts_tree
        WHERE grade = %s AND is_deleted = FALSE
    """, (grade,))
    total = cur.fetchone()[0]
    cur.close(); conn.close()

    pct = int(learned * 100 / total) if total else 0
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)

    repeats = get_repeat_topics(uid)

    text = (
        f"📊 {user['full_name'].split()[0]} — Progress\n"
        f"━━━━━━━━━━━━━━\n"
        f"{lvl['icon']} {lvl['name']} — {xp} XP\n"
        f"🔥 Streak: {streak} kun\n"
        f"━━━━━━━━━━━━━━\n"
        f"📚 O'rganilgan: {learned}/{total}\n"
        f"{bar} {pct}%\n"
        f"🔁 Takrorlash kerak: {len(repeats)} ta\n"
    )

    await call.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="dashboard_refresh")
        ]])
    )
    await call.answer()
