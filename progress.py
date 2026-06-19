"""
progress.py — XP, streak, imtihon, nishonlar
"""
import os
import psycopg2
from datetime import date, timedelta, datetime

DATABASE_URL = os.getenv("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)


# ─────────────────────────────────────────
# SINF GURUHI
# ─────────────────────────────────────────

def get_group(grade):
    """1-4 → junior, 5-8 → middle, 9-11 → senior"""
    try:
        g = int(str(grade).replace("-sinf", "").strip())
        if g <= 4:   return "junior"
        elif g <= 8: return "middle"
        else:        return "senior"
    except:
        return "middle"


# ─────────────────────────────────────────
# XP TIZIMI
# ─────────────────────────────────────────

XP_RULES = {
    "lesson":      30,   # dars o'qish
    "test_100":    50,   # test 100%
    "test_80":     30,   # test 80%+
    "test_60":     15,   # test 60%+
    "streak_7":    100,  # 7 kun streak
    "streak_3":    30,   # 3 kun streak
    "new_topic":   20,   # yangi mavzu boshlash
    "exam_pass":   100,  # imtihon o'tish
}

def xp_display(xp, grade):
    """Yoshga mos XP ko'rinishi"""
    group = get_group(grade)
    if group == "junior":
        stars = xp // 10
        return f"⭐ {stars} yulduz"
    elif group == "middle":
        level = get_level(xp)
        return f"{level['icon']} {xp} XP"
    else:
        pct = min(100, xp // 20)
        return f"📈 {pct}% bilim"

def get_level(xp):
    levels = [
        {"min": 0,    "icon": "🥉", "name": "Yangi"},
        {"min": 200,  "icon": "🥈", "name": "O'rganuvchi"},
        {"min": 500,  "icon": "🥇", "name": "Bilimdon"},
        {"min": 1000, "icon": "💎", "name": "Ustoz"},
        {"min": 2000, "icon": "👑", "name": "Chempion"},
    ]
    for lvl in reversed(levels):
        if xp >= lvl["min"]:
            return lvl
    return levels[0]

def add_xp(user_id, reason):
    """XP qo'shadi, streak yangilaydi"""
    points = XP_RULES.get(reason, 0)
    if not points:
        return 0

    conn = db(); cur = conn.cursor()

    cur.execute("""
        INSERT INTO user_progress (user_id, xp, streak, last_active)
        VALUES (%s, %s, 1, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            xp = user_progress.xp + %s,
            last_active = %s
        RETURNING xp, streak, last_active
    """, (user_id, points, date.today(), points, date.today()))

    row = cur.fetchone()
    conn.commit(); cur.close(); conn.close()
    return points


# ─────────────────────────────────────────
# STREAK
# ─────────────────────────────────────────

def update_streak(user_id):
    """Kunlik streak yangilaydi"""
    conn = db(); cur = conn.cursor()

    cur.execute("""
        SELECT streak, last_active FROM user_progress
        WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()

    today = date.today()

    if not row:
        cur.execute("""
            INSERT INTO user_progress (user_id, streak, last_active)
            VALUES (%s, 1, %s)
        """, (user_id, today))
        conn.commit(); cur.close(); conn.close()
        return 1

    streak, last_active = row

    if last_active == today:
        cur.close(); conn.close()
        return streak
    elif last_active == today - timedelta(days=1):
        streak += 1
    else:
        streak = 1

    bonus = 0
    if streak == 3:  bonus = XP_RULES["streak_3"]
    if streak == 7:  bonus = XP_RULES["streak_7"]

    cur.execute("""
        UPDATE user_progress
        SET streak = %s, last_active = %s, xp = xp + %s
        WHERE user_id = %s
    """, (streak, today, bonus, user_id))

    conn.commit(); cur.close(); conn.close()
    return streak


def get_progress(user_id):
    """O'quvchi progress ma'lumotlari"""
    conn = db(); cur = conn.cursor()

    cur.execute("""
        SELECT xp, streak, last_active
        FROM user_progress WHERE user_id = %s
    """, (user_id,))
    row = cur.fetchone()
    cur.close(); conn.close()

    if not row:
        return {"xp": 0, "streak": 0, "last_active": None}
    return {"xp": row[0], "streak": row[1], "last_active": row[2]}


# ─────────────────────────────────────────
# O'RGANILGAN MAVZULAR
# ─────────────────────────────────────────

def mark_learned(user_id, topic_code, score=100):
    """Kichik mavzuni o'rganilgan deb belgilaydi"""
    conn = db(); cur = conn.cursor()

    # Ebbinghaus — keyingi takrorlash
    next_repeat = date.today() + timedelta(days=1)

    cur.execute("""
        INSERT INTO learned_topics
        (user_id, topic_code, score, next_repeat)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id, topic_code) DO UPDATE SET
            score = %s,
            repeat_count = learned_topics.repeat_count + 1,
            learned_at = NOW(),
            next_repeat = %s
    """, (user_id, topic_code, score, next_repeat, score, next_repeat))

    conn.commit(); cur.close(); conn.close()


def get_next_topic(user_id, grade, subject_code=None):
    """Keyingi o'rganilmagan kichik mavzuni topadi"""
    conn = db(); cur = conn.cursor()

    query = """
        SELECT t.topic_code, t.kichik_name, t.mavzu_name,
               t.subject_name
        FROM dts_tree t
        LEFT JOIN learned_topics lt
            ON lt.topic_code = t.topic_code
            AND lt.user_id = %s
        WHERE t.grade = %s
          AND t.is_deleted = FALSE
          AND lt.topic_code IS NULL
    """
    params = [user_id, grade]

    if subject_code:
        query += " AND t.subject_code = %s"
        params.append(subject_code)

    query += " ORDER BY t.topic_code LIMIT 1"

    cur.execute(query, params)
    row = cur.fetchone()
    cur.close(); conn.close()
    return row


def get_repeat_topics(user_id):
    """Takrorlash kerak bo'lgan mavzular"""
    conn = db(); cur = conn.cursor()

    cur.execute("""
        SELECT lt.topic_code, t.kichik_name, t.subject_name,
               lt.score, lt.next_repeat
        FROM learned_topics lt
        JOIN dts_tree t ON t.topic_code = lt.topic_code
        WHERE lt.user_id = %s
          AND lt.next_repeat <= %s
        ORDER BY lt.next_repeat
        LIMIT 5
    """, (user_id, date.today()))

    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


# ─────────────────────────────────────────
# IMTIHONLAR
# ─────────────────────────────────────────

def create_auto_exams(user_id, grade, registered_at):
    """Ro'yxatdan o'tgan sanaga qarab avtomatik imtihonlar yaratadi"""
    conn = db(); cur = conn.cursor()

    reg_date = registered_at if isinstance(registered_at, date) else date.today()

    exams = []

    # Oylik — har 30 kunda
    for i in range(1, 13):
        exam_date = reg_date + timedelta(days=30 * i)
        exams.append({
            "title": f"Oylik imtihon #{i}",
            "grade": grade,
            "exam_date": exam_date,
            "is_mandatory": False,
            "created_by": "bot"
        })

    # Choraklik — har 90 kunda
    for i in range(1, 5):
        exam_date = reg_date + timedelta(days=90 * i)
        exams.append({
            "title": f"{i}-chorak imtihoni",
            "grade": grade,
            "exam_date": exam_date,
            "is_mandatory": False,
            "created_by": "bot"
        })

    # Yarim yillik — 180 kunda
    exams.append({
        "title": "Yarim yillik imtihon",
        "grade": grade,
        "exam_date": reg_date + timedelta(days=180),
        "is_mandatory": False,
        "created_by": "bot"
    })

    # Yillik — 365 kunda
    exams.append({
        "title": "Yillik imtihon",
        "grade": grade,
        "exam_date": reg_date + timedelta(days=365),
        "is_mandatory": False,
        "created_by": "bot"
    })

    for exam in exams:
        cur.execute("""
            INSERT INTO exams (title, grade, exam_date, is_mandatory, created_by)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
        """, (
            exam["title"], exam["grade"],
            exam["exam_date"], exam["is_mandatory"],
            exam["created_by"]
        ))
        row = cur.fetchone()
        if row:
            exam_id = row[0]
            cur.execute("""
                INSERT INTO exam_results (user_id, exam_id, status)
                VALUES (%s, %s, 'pending')
                ON CONFLICT DO NOTHING
            """, (user_id, exam_id))

    conn.commit(); cur.close(); conn.close()


def get_pending_exams(user_id):
    """Bugungi va o'tgan imtihonlar"""
    conn = db(); cur = conn.cursor()

    cur.execute("""
        SELECT e.id, e.title, e.exam_date,
               e.is_mandatory, er.status
        FROM exam_results er
        JOIN exams e ON e.id = er.exam_id
        WHERE er.user_id = %s
          AND e.exam_date <= %s
          AND er.status = 'pending'
        ORDER BY e.is_mandatory DESC, e.exam_date
    """, (user_id, date.today()))

    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def get_upcoming_exams(user_id):
    """Kelayotgan imtihonlar (7 kun ichida)"""
    conn = db(); cur = conn.cursor()

    cur.execute("""
        SELECT e.title, e.exam_date, e.is_mandatory
        FROM exam_results er
        JOIN exams e ON e.id = er.exam_id
        WHERE er.user_id = %s
          AND e.exam_date > %s
          AND e.exam_date <= %s
          AND er.status = 'pending'
        ORDER BY e.exam_date
        LIMIT 3
    """, (user_id, date.today(), date.today() + timedelta(days=7)))

    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


# ─────────────────────────────────────────
# KIRISH EKRANI MATNI
# ─────────────────────────────────────────

def build_welcome(user_id, full_name, grade):
    """Yoshga mos kutib olish matni"""
    group   = get_group(grade)
    prog    = get_progress(user_id)
    xp      = prog["xp"]
    streak  = prog["streak"]
    pending = get_pending_exams(user_id)
    repeats = get_repeat_topics(user_id)
    upcoming = get_upcoming_exams(user_id)

    # Ism qisqartirish
    name = full_name.split()[0] if full_name else "O'quvchi"

    lines = []

    # ── 1-4 sinf ──
    if group == "junior":
        stars  = xp // 10
        plant  = "🌱" if xp < 50 else "🌿" if xp < 150 else "🌳"
        lines.append(f"🌟 Salom, {name}! Bugun ham o'ynaymizmi? 🎮")
        lines.append(f"{plant} O'simlik: {'█' * min(10, xp//20)}{'░' * (10 - min(10, xp//20))}")
        lines.append(f"⭐ Yulduzlar: {stars}")
        if streak > 1:
            lines.append(f"🔥 {streak} kun ketma-ket!")

    # ── 5-8 sinf ──
    elif group == "middle":
        level = get_level(xp)
        lines.append(f"⚔️ Salom, Qahramon {name}!")
        lines.append(f"{level['icon']} {level['name']} — {xp} XP")
        if streak > 1:
            lines.append(f"🔥 Streak: {streak} kun")

    # ── 9-11 sinf ──
    else:
        pct = min(100, xp // 20)
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"📊 Salom, {name}!")
        lines.append(f"📈 Bilim: {bar} {pct}%")
        if streak > 1:
            lines.append(f"🔥 {streak} kun faol")

    lines.append("━━━━━━━━━━━━━━")

    # Majburiy imtihon
    mandatory = [e for e in pending if e[3]]
    if mandatory:
        lines.append(f"🚨 Majburiy imtihon: {mandatory[0][1]}")

    # Oddiy eslatma
    optional = [e for e in pending if not e[3]]
    if optional:
        lines.append(f"🔔 Imtihon: {optional[0][1]}")

    # Takrorlash
    if repeats:
        lines.append(f"🔁 Takrorlash: {len(repeats)} ta mavzu")

    # Kelayotgan imtihon
    if upcoming and not mandatory:
        days = (upcoming[0][1] - date.today()).days
        lines.append(f"📅 {days} kun ichida: {upcoming[0][0]}")

    return "\n".join(lines)


# ─────────────────────────────────────────
# NISHONLAR
# ─────────────────────────────────────────

BADGES = {
    "first_lesson":  {"icon": "🎯", "name": "Birinchi dars!"},
    "lessons_10":    {"icon": "📚", "name": "10 dars o'qidi"},
    "lessons_50":    {"icon": "🦅", "name": "50 dars — izlanuvchan"},
    "streak_3":      {"icon": "🔥", "name": "3 kun ketma-ket"},
    "streak_7":      {"icon": "⚡", "name": "Haftalik qahramon"},
    "exam_pass":     {"icon": "🏆", "name": "Imtihon o'tdi"},
    "topic_master":  {"icon": "👑", "name": "Mavzu ustasi"},
}

def check_badges(user_id, xp, streak, lessons_count):
    """Yangi nishon tekshiradi va beradi"""
    conn = db(); cur = conn.cursor()

    new_badges = []

    checks = []
    if lessons_count >= 1:  checks.append("first_lesson")
    if lessons_count >= 10: checks.append("lessons_10")
    if lessons_count >= 50: checks.append("lessons_50")
    if streak >= 3:         checks.append("streak_3")
    if streak >= 7:         checks.append("streak_7")

    for badge in checks:
        cur.execute("""
            INSERT INTO achievements (user_id, badge_code)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING badge_code
        """, (user_id, badge))
        if cur.fetchone():
            new_badges.append(BADGES[badge])

    conn.commit(); cur.close(); conn.close()
    return new_badges
