"""student_dashboard.py — O'quvchi bosh ekrani (mustaqil, xatoga chidamli)"""
import os, random
from datetime import datetime, date, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _db():
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


def _safe(fn, default=None):
    """Har qanday xatoni yutadi — dashboard hech qachon buzilmaydi."""
    try:
        return fn()
    except Exception as e:
        print(f"[dashboard] {fn.__name__ if hasattr(fn,'__name__') else '?'}: {e}")
        return default


# ═══════════════════ KUN REJIMI ═══════════════════

def _kun_rejimi():
    """Soatga qarab salomlashuv va rejim."""
    h = datetime.now().hour
    if 5 <= h < 11:
        return "🌅", "Xayrli tong", "Ertalabki mashg'ulot vaqti — miya eng tiniq payt"
    if 11 <= h < 17:
        return "☀️", "Xayrli kun", "Kunduzgi vaqt — mustahkamlash uchun qulay"
    if 17 <= h < 21:
        return "🌆", "Xayrli kech", "Kechki takrorlash — bugun o'rganganni mustahkamlang"
    return "🌙", "Xayrli tun", "Kech bo'ldi — dam olish ham o'qish kabi muhim"


KUNLAR = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

MASLAHATLAR = [
    "Kuniga 25 daqiqa diqqat bilan o'qish — 2 soat chalg'igan o'qishdan foydali.",
    "Yangi mavzuni o'qigach, kitobni yopib o'zingizga aytib bering.",
    "Xato qilgan savolni belgilab qo'ying — ertaga qayta yeching.",
    "Ertalab qiyin mavzuni, kechqurun takrorlashni oling.",
    "Har 45 daqiqada 5 daqiqa tanaffus qiling — miya tiklanadi.",
    "O'rganganingizni do'stingizga tushuntiring — eng kuchli usul.",
    "Uxlashdan oldin 10 daqiqa takrorlash — xotirada uzoq qoladi.",
    "Bir kunda ko'p emas, har kuni oz — natija shundan chiqadi.",
    "Savolni tushunmasangiz, uni bo'laklarga bo'ling.",
    "Telefon yoningizda bo'lmasa, diqqat 2 barobar oshadi.",
    "Yozib o'rganish — o'qib o'rganishdan mustahkamroq.",
    "Har kuni bir yangi so'z — yilda 365 ta so'z.",
]


def _kunlik_maslahat(user_id):
    """Har kuni bir xil maslahat (kun bo'yicha barqaror)."""
    idx = (date.today().toordinal() + int(user_id) % 7) % len(MASLAHATLAR)
    return MASLAHATLAR[idx]


# ═══════════════════ MA'LUMOTLAR ═══════════════════

def _user_info(uid):
    conn = _db(); cur = conn.cursor()
    cur.execute("SELECT full_name, class, school FROM users WHERE user_id=%s", (uid,))
    r = cur.fetchone(); cur.close(); conn.close()
    if not r:
        return {"ism": "O'quvchi", "sinf": "", "maktab": ""}
    return {"ism": r[0] or "O'quvchi", "sinf": r[1] or "", "maktab": r[2] or ""}


def _bugungi_darslar(uid):
    """Bugun o'qituvchi belgilagan mavzular (to'garaklardan)."""
    conn = _db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.nomi, r.izoh, r.dars_vaqt
            FROM togarak_azolar a
            JOIN togaraklar t ON t.id = a.togarak_id
            JOIN togarak_reja r ON r.togarak_id = t.id
            WHERE a.user_id=%s AND a.aktiv=TRUE
              AND r.dars_sana = CURRENT_DATE
            ORDER BY r.dars_vaqt NULLS LAST
            LIMIT 5
        """, (uid,))
        rows = cur.fetchall()
    except Exception as e:
        conn.rollback(); rows = []
        print(f"[dashboard] bugungi: {e}")
    cur.close(); conn.close()
    return [{"togarak": r[0], "mavzu": r[1] or "—", "vaqt": r[2] or ""} for r in rows]


def _otilgan_mavzular(uid, kun=7):
    """Oxirgi N kunda o'qituvchi o'tib bo'lgan mavzular."""
    conn = _db(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.nomi, r.izoh, r.dars_sana
            FROM togarak_azolar a
            JOIN togaraklar t ON t.id = a.togarak_id
            JOIN togarak_reja r ON r.togarak_id = t.id
            WHERE a.user_id=%s AND a.aktiv=TRUE
              AND r.completed = TRUE
              AND r.dars_sana >= CURRENT_DATE - (%s || ' days')::INTERVAL
            ORDER BY r.dars_sana DESC
            LIMIT 5
        """, (uid, kun))
        rows = cur.fetchall()
    except Exception as e:
        conn.rollback(); rows = []
        print(f"[dashboard] otilgan: {e}")
    cur.close(); conn.close()
    return [{"togarak": r[0], "mavzu": r[1] or "—",
             "sana": r[2].strftime("%d.%m") if r[2] else ""} for r in rows]


def _vazifalar(uid):
    """Bajarilmagan uy vazifalari. Ustun nomlari har xil bo'lishi mumkin."""
    conn = _db(); cur = conn.cursor()
    rows = []
    # 1-urinish: homework_javoblar orqali
    try:
        cur.execute("""
            SELECT h.id, t.nomi, h.mavzu, h.deadline
            FROM togarak_azolar a
            JOIN togaraklar t ON t.id = a.togarak_id
            JOIN homework h ON h.togarak_id = t.id
            WHERE a.user_id=%s AND a.aktiv=TRUE
              AND NOT EXISTS (
                  SELECT 1 FROM homework_javoblar j
                  WHERE j.homework_id = h.id AND j.user_id = %s
              )
            ORDER BY h.deadline NULLS LAST
            LIMIT 5
        """, (uid, uid))
        rows = cur.fetchall()
    except Exception:
        conn.rollback()
        # 2-urinish: javoblar jadvalisiz
        try:
            cur.execute("""
                SELECT h.id, t.nomi, h.mavzu, h.deadline
                FROM togarak_azolar a
                JOIN togaraklar t ON t.id = a.togarak_id
                JOIN homework h ON h.togarak_id = t.id
                WHERE a.user_id=%s AND a.aktiv=TRUE
                ORDER BY h.deadline NULLS LAST
                LIMIT 5
            """, (uid,))
            rows = cur.fetchall()
        except Exception as e:
            conn.rollback()
            print(f"[dashboard] vazifa: {e}")
    cur.close(); conn.close()

    out = []
    for r in rows:
        muddat = ""
        d = r[3]
        if d:
            try:
                dd = d.date() if hasattr(d, "date") else d
                qolgan = (dd - date.today()).days
                if qolgan == 0: muddat = "bugun!"
                elif qolgan > 0: muddat = f"{qolgan} kun"
                else: muddat = "kechikdi"
            except Exception:
                muddat = ""
        out.append({"togarak": r[1], "mavzu": r[2] or "—", "muddat": muddat})
    return out


def _test_statistika(uid):
    """Test natijalari — o'zlashtirish."""
    conn = _db(); cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(score),0), COALESCE(SUM(total),0)
        FROM results WHERE user_id=%s
    """, (uid,))
    r = cur.fetchone() or (0, 0, 0)
    cur.close(); conn.close()
    soni, ball, jami = (r[0] or 0), (r[1] or 0), (r[2] or 0)
    foiz = round(ball * 100 / jami) if jami else 0
    return {"testlar": soni, "foiz": foiz}


def _streak(uid):
    """Ketma-ket kunlar (user_progress)."""
    conn = _db(); cur = conn.cursor()
    try:
        cur.execute("SELECT streak FROM user_progress WHERE user_id=%s", (uid,))
        r = cur.fetchone()
    except Exception:
        conn.rollback(); r = None
    cur.close(); conn.close()
    return (r[0] if r else 0) or 0


def _togarak_soni(uid):
    conn = _db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM togarak_azolar WHERE user_id=%s AND aktiv=TRUE", (uid,))
    r = cur.fetchone(); cur.close(); conn.close()
    return (r[0] if r else 0) or 0


def _togarak_qisqa(uid):
    """Bosh ekran uchun BIR QATORLIK dastur+loyiha xulosasi.
    Bir nechta to'garak bo'lsa — birinchisini ko'rsatadi, qolganini +N deb qo'shadi."""
    conn = _db(); cur = conn.cursor()
    cur.execute("""SELECT t.id, t.nomi FROM togarak_azolar a
        JOIN togaraklar t ON t.id=a.togarak_id
        WHERE a.user_id=%s AND a.aktiv=TRUE AND t.aktiv=TRUE
        ORDER BY t.nomi""", (uid,))
    tgs = cur.fetchall()
    if not tgs:
        cur.close(); conn.close()
        return None

    tid, nomi = tgs[0]
    try:
        cur.execute("""SELECT COUNT(*), COUNT(*) FILTER (WHERE completed=TRUE)
            FROM togarak_reja WHERE togarak_id=%s""", (tid,))
        r = cur.fetchone() or (0, 0)
    except Exception:
        conn.rollback(); r = (0, 0)
    jami, otilgan = (r[0] or 0), (r[1] or 0)
    foiz = round(otilgan * 100 / jami) if jami else 0

    loyiha_soni = 0
    try:
        cur.execute("""SELECT COUNT(*) FROM imtihon_natija n
            JOIN togarak_imtihon i ON i.id=n.imtihon_id
            WHERE i.togarak_id=%s AND n.user_id=%s AND i.turi='loyiha'""", (tid, uid))
        loyiha_soni = (cur.fetchone() or [0])[0]
    except Exception:
        conn.rollback()
    cur.close(); conn.close()

    matn = f"{otilgan}/{jami} mavzu ({foiz}%)" if jami else "mavzu belgilanmagan"
    if loyiha_soni:
        matn += f" · 🎨 {loyiha_soni} loyiha"
    qolgan = len(tgs) - 1
    if qolgan:
        matn += f"  <i>(+{qolgan} to'garak)</i>"
    return matn


# ═══════════════════ BOSH EKRAN ═══════════════════

async def build_dashboard(uid):
    """O'quvchi bosh ekrani — IXCHAM. Tafsilot tugmalarda."""
    u = _safe(lambda: _user_info(uid), {"ism": "O'quvchi", "sinf": "", "maktab": ""})
    emoji, salom, _ = _kun_rejimi()
    bugun = datetime.now()
    kun_nomi = KUNLAR[bugun.weekday()]
    ism = (u["ism"] or "O'quvchi").split()[0]

    darslar = _safe(lambda: _bugungi_darslar(uid), [])
    vz = _safe(lambda: _vazifalar(uid), [])
    st = _safe(lambda: _test_statistika(uid), {"testlar": 0, "foiz": 0})
    sk = _safe(lambda: _streak(uid), 0)

    t = [f"{emoji} <b>{salom}, {ism}!</b>"]
    sinf = f" · 🎓 {u['sinf']}" if u["sinf"] else ""
    t.append(f"📅 {bugun.strftime('%d.%m')} · {kun_nomi}{sinf}")
    t.append("━━━━━━━━━━━━━━")

    # Bugungi dars — 1 qator
    if darslar:
        d = darslar[0]
        vaqt = f" · {d['vaqt']}" if d["vaqt"] else ""
        qosh = f" (+{len(darslar)-1})" if len(darslar) > 1 else ""
        t.append(f"📌 <b>Bugun:</b> {d['mavzu'][:32]}{vaqt}{qosh}")
    else:
        t.append("📌 <b>Bugun:</b> dars belgilanmagan")

    # Vazifa — 1 qator
    if vz:
        shoshilinch = sum(1 for v in vz if v["muddat"] in ("bugun!", "kechikdi"))
        ogoh = f"  ⚠️ {shoshilinch} shoshilinch" if shoshilinch else ""
        t.append(f"📝 <b>Vazifa:</b> {len(vz)} ta{ogoh}")
    else:
        t.append("📝 <b>Vazifa:</b> yo'q ✅")

    # Statistika — 1 qator
    stat = f"🎯 {st['foiz']}%   🧪 {st['testlar']} ta"
    if sk > 0:
        stat += f"   🔥 {sk} kun"
    t.append(stat)

    # To'garak dasturi — qisqa xulosa (tafsilot "To'garaklarim" tugmasida)
    tg_qisqa = _safe(lambda: _togarak_qisqa(uid), None)
    if tg_qisqa:
        t.append(f"📗 <b>Dastur:</b> {tg_qisqa}")

    t.append("")
    t.append(f"💡 <i>{_kunlik_maslahat(uid)}</i>")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Bugungi dars", callback_data="dash_bugun"),
         InlineKeyboardButton(text="📝 Vazifalar", callback_data="dash_vazifa")],
        [InlineKeyboardButton(text="📚 To'garaklarim", callback_data="dash_togarak"),
         InlineKeyboardButton(text="🏫 Maktab", callback_data="dash_maktab")],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="dash_refresh")],
    ])
    return "\n".join(t), kb


async def build_bugungi(uid):
    """Bugungi darslar + yaqinda o'tilgan mavzular."""
    darslar = _safe(lambda: _bugungi_darslar(uid), [])
    otil = _safe(lambda: _otilgan_mavzular(uid), [])
    _, _, rejim = _kun_rejimi()

    t = ["📌 <b>Bugungi dars</b>", ""]
    if darslar:
        for d in darslar:
            vaqt = f"  ⏰ {d['vaqt']}" if d["vaqt"] else ""
            t.append(f"<b>{d['mavzu']}</b>")
            t.append(f"   👥 {d['togarak']}{vaqt}")
            t.append("")
    else:
        t.append("Bugun dars belgilanmagan.")
        t.append("")

    if otil:
        t.append("📗 <b>Yaqinda o'tilgan</b>")
        for o in otil:
            t.append(f"   • {o['mavzu'][:38]} <i>({o['sana']})</i>")
        t.append("")

    t.append(f"<i>{rejim}</i>")
    return "\n".join(t), _orqaga_kb()


# ═══════════════════ TO'GARAK STATISTIKASI ═══════════════════

async def build_togarak_stat(uid):
    """To'garaklar bo'yicha alohida statistika."""
    try:
        conn = _db(); cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.nomi, t.fan
            FROM togarak_azolar a
            JOIN togaraklar t ON t.id = a.togarak_id
            WHERE a.user_id=%s AND a.aktiv=TRUE AND t.aktiv=TRUE
            ORDER BY t.nomi
        """, (uid,))
        tgs = cur.fetchall()
    except Exception as e:
        print(f"[dashboard] togarak_stat: {e}")
        return "📚 <b>To'garaklarim</b>\n\n⚠️ Ma'lumot yuklanmadi.", _orqaga_kb()

    if not tgs:
        cur.close(); conn.close()
        return ("📚 <b>To'garaklarim</b>\n\nSiz hali to'garakka a'zo emassiz.\n"
                "«📚 To'garaklar» menyusidan qo'shiling."), _orqaga_kb()

    t = ["📚 <b>To'garaklarim</b>", ""]
    for tid, nomi, fan in tgs:
        # Davomat
        try:
            cur.execute("""
                SELECT COUNT(*), COUNT(*) FILTER (WHERE holat IN ('keldi','kech'))
                FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s
            """, (tid, uid))
            y = cur.fetchone() or (0, 0)
        except Exception:
            conn.rollback(); y = (0, 0)
        dav = round((y[1] or 0) * 100 / y[0]) if y[0] else 100

        # Baholar
        try:
            cur.execute("""
                SELECT COUNT(*), COALESCE(AVG(baho),0)
                FROM togarak_baholar WHERE togarak_id=%s AND user_id=%s
            """, (tid, uid))
            b = cur.fetchone() or (0, 0)
        except Exception:
            conn.rollback(); b = (0, 0)

        # O'tilgan mavzular
        try:
            cur.execute("""
                SELECT COUNT(*), COUNT(*) FILTER (WHERE completed=TRUE)
                FROM togarak_reja WHERE togarak_id=%s
            """, (tid,))
            r = cur.fetchone() or (0, 0)
        except Exception:
            conn.rollback(); r = (0, 0)
        prog = round((r[1] or 0) * 100 / r[0]) if r[0] else 0

        # Loyiha ishlari
        try:
            cur.execute("""SELECT COUNT(*), COALESCE(AVG(n.foiz),0) FROM imtihon_natija n
                JOIN togarak_imtihon i ON i.id=n.imtihon_id
                WHERE i.togarak_id=%s AND n.user_id=%s AND i.turi='loyiha'""", (tid, uid))
            lo = cur.fetchone() or (0, 0)
        except Exception:
            conn.rollback(); lo = (0, 0)

        t.append(f"<b>{nomi}</b> <i>({fan or '—'})</i>")
        t.append(f"   📈 Davomat: {dav}%")
        if b[0]:
            t.append(f"   ⭐ O'rtacha baho: {round(float(b[1]),1)} ({b[0]} ta)")
        t.append(f"   📗 Dastur: {prog}% ({r[1]}/{r[0]} mavzu)")
        if lo[0]:
            t.append(f"   🎨 Loyiha: {lo[0]} ta, o'rtacha {round(float(lo[1]),1)}%")
        t.append("")

    cur.close(); conn.close()
    return "\n".join(t), _orqaga_kb()


# ═══════════════════ MAKTAB STATISTIKASI ═══════════════════

async def build_maktab_stat(uid):
    """Maktab / test natijalari bo'yicha alohida statistika."""
    try:
        conn = _db(); cur = conn.cursor()
        cur.execute("SELECT class, school FROM users WHERE user_id=%s", (uid,))
        u = cur.fetchone() or ("", "")
        sinf, maktab = (u[0] or ""), (u[1] or "")

        cur.execute("""
            SELECT COUNT(*), COALESCE(SUM(score),0), COALESCE(SUM(total),0)
            FROM results WHERE user_id=%s
        """, (uid,))
        r = cur.fetchone() or (0, 0, 0)
    except Exception as e:
        print(f"[dashboard] maktab_stat: {e}")
        return "🏫 <b>Maktab statistikasi</b>\n\n⚠️ Ma'lumot yuklanmadi.", _orqaga_kb()

    soni, ball, jami = r[0] or 0, r[1] or 0, r[2] or 0
    foiz = round(ball * 100 / jami) if jami else 0

    t = ["🏫 <b>Maktab statistikasi</b>", ""]
    if maktab: t.append(f"🏫 {maktab}")
    if sinf: t.append(f"🎓 {sinf}")
    t.append("")

    if soni == 0:
        t.append("Hali test yechmagansiz.")
        t.append("«🧪 Bilimni sinash» dan boshlang!")
        cur.close(); conn.close()
        return "\n".join(t), _orqaga_kb()

    t.append("📊 <b>Umumiy o'zlashtirish</b>")
    t.append(f"   🎯 Foiz: {foiz}%")
    t.append(f"   ✅ To'g'ri: {ball} / {jami}")
    t.append(f"   🧪 Testlar: {soni} ta")
    t.append("")

    if foiz >= 86: baho, izoh = "5 (a'lo)", "Ajoyib natija!"
    elif foiz >= 71: baho, izoh = "4 (yaxshi)", "Yaxshi, biroz mehnat kerak"
    elif foiz >= 56: baho, izoh = "3 (qoniqarli)", "Takrorlash foydali bo'ladi"
    else: baho, izoh = "2", "Mavzularni qaytadan o'rganing"
    t.append(f"📋 <b>Baho: {baho}</b>")
    t.append(f"<i>{izoh}</i>")
    t.append("")

    # Fanlar bo'yicha
    try:
        cur.execute("""
            SELECT subject, COALESCE(SUM(score),0), COALESCE(SUM(total),0)
            FROM results WHERE user_id=%s AND subject IS NOT NULL
            GROUP BY subject ORDER BY 3 DESC LIMIT 6
        """, (uid,))
        fanlar = cur.fetchall()
    except Exception:
        conn.rollback(); fanlar = []
    if fanlar:
        t.append("📚 <b>Fanlar bo'yicha</b>")
        for f, b2, j2 in fanlar:
            p = round((b2 or 0) * 100 / j2) if j2 else 0
            bar = "█" * (p // 10) + "░" * (10 - p // 10)
            t.append(f"   {f}")
            t.append(f"   {bar} {p}%")
        t.append("")

    # Sinfdoshlar orasida o'rin
    if sinf:
        try:
            cur.execute("""
                SELECT user_id, SUM(score)*100.0/NULLIF(SUM(total),0) AS f
                FROM results
                WHERE user_id IN (SELECT user_id FROM users WHERE class=%s)
                GROUP BY user_id HAVING SUM(total)>0
                ORDER BY f DESC
            """, (sinf,))
            reyting = cur.fetchall()
            orin = next((i + 1 for i, x in enumerate(reyting) if x[0] == uid), None)
            if orin:
                t.append(f"🏆 <b>{sinf} da o'rningiz: {orin} / {len(reyting)}</b>")
        except Exception:
            conn.rollback()

    cur.close(); conn.close()
    return "\n".join(t), _orqaga_kb()


# ═══════════════════ VAZIFALAR ═══════════════════

async def build_vazifalar(uid):
    vz = _safe(lambda: _vazifalar(uid), [])
    if not vz:
        return "📝 <b>Vazifalar</b>\n\n✅ Bajarilmagan vazifa yo'q!", _orqaga_kb()
    t = [f"📝 <b>Vazifalar</b> ({len(vz)} ta)", ""]
    for i, v in enumerate(vz, 1):
        t.append(f"<b>{i}. {v['mavzu']}</b>")
        t.append(f"   👥 {v['togarak']}")
        if v["muddat"]:
            t.append(f"   ⏰ {v['muddat']}")
        t.append("")
    return "\n".join(t), _orqaga_kb()


def _orqaga_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Bosh ekran", callback_data="dash_refresh")
    ]])
