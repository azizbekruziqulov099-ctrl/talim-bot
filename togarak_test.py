"""togarak_test.py — O'quvchi to'garak testlarini qulay tanlaydi.

Qoidalar:
  • Faqat O'TILGAN mavzular ochiq (togarak_reja.completed=TRUE)
  • 1 ta, 2 ta, 40 ta yoki barchasini belgilash mumkin
  • Tanlanganlardan RANDOM aralashtirib chiqadi
  • Maksimal 50 ta savol
"""
import os
import psycopg2
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL", "")
MAX_TEST = 50          # bir seansda maksimal savol


def _db():
    return psycopg2.connect(DATABASE_URL)


# ═══════════════ MA'LUMOT ═══════════════

def togarak_fan(togarak_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT fan, nomi FROM togaraklar WHERE id=%s", (togarak_id,))
        r = cr.fetchone(); cr.close(); c.close()
        return (r[0], r[1]) if r else (None, "To'garak")
    except Exception as e:
        print(f"[tt] fan: {e}")
        return (None, "To'garak")


def otilgan_mavzu_nomlari(togarak_id):
    """Rejada 'o'tilgan' deb belgilangan mavzu nomlari."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT mavzu FROM togarak_reja
            WHERE togarak_id=%s AND completed=TRUE AND mavzu IS NOT NULL""",
            (togarak_id,))
        r = [x[0] for x in cr.fetchall() if x[0]]
        cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[tt] reja: {e}")
        return []


def mavzular(togarak_id):
    """[(mavzu_name, [topic_codes], test_soni, ochiq)] — ochiq=o'tilgan."""
    fan, _ = togarak_fan(togarak_id)
    if not fan:
        return []
    otilgan = set(n.strip().lower() for n in otilgan_mavzu_nomlari(togarak_id))

    try:
        c = _db(); cr = c.cursor()
        cr.execute("""
            SELECT d.mavzu_name,
                   ARRAY_AGG(DISTINCT d.topic_code) AS kodlar,
                   COUNT(g.id) AS test_soni
            FROM dts_tree d
            JOIN generated_tests g ON g.topic_code = d.topic_code
            WHERE d.subject_name=%s AND d.is_deleted=FALSE
              AND d.mavzu_name IS NOT NULL
            GROUP BY d.mavzu_name
            HAVING COUNT(g.id) > 0
            ORDER BY d.mavzu_name
        """, (fan,))
        rows = cr.fetchall()
        cr.close(); c.close()
    except Exception as e:
        print(f"[tt] mavzular: {e}")
        return []

    natija = []
    for nom, kodlar, soni in rows:
        ochiq = (not otilgan) or (nom.strip().lower() in otilgan)
        natija.append((nom, list(kodlar), soni, ochiq))

    # Reja bo'sh bo'lsa — hammasi ochiq
    if not otilgan:
        return natija
    # Aks holda faqat ochiqlarni oldinga
    return sorted(natija, key=lambda x: (not x[3], x[0]))


def test_soni(topic_codes):
    if not topic_codes:
        return 0
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=ANY(%s)",
                   (list(topic_codes),))
        n = (cr.fetchone() or [0])[0]
        cr.close(); c.close()
        return n
    except Exception as e:
        print(f"[tt] soni: {e}")
        return 0


# ═══════════════ KLAVIATURA ═══════════════

def mavzu_kb(togarak_id, ro_yxat, tanlangan, sahifa=0, sahifa_hajmi=8):
    """Ko'p tanlovli mavzu ro'yxati."""
    boshi = sahifa * sahifa_hajmi
    bolak = ro_yxat[boshi:boshi + sahifa_hajmi]

    rows = []
    for i, (nom, kodlar, soni, ochiq) in enumerate(bolak, start=boshi):
        if not ochiq:
            rows.append([InlineKeyboardButton(
                text=f"🔒 {nom[:32]} — hali o'tilmagan",
                callback_data="tt_lock")])
            continue
        belgi = "☑️" if i in tanlangan else "⬜"
        rows.append([InlineKeyboardButton(
            text=f"{belgi} {nom[:32]} ({soni})",
            callback_data=f"tt_x:{togarak_id}:{i}")])

    nav = []
    if sahifa > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"tt_p:{togarak_id}:{sahifa-1}"))
    jami_sahifa = (len(ro_yxat) - 1) // sahifa_hajmi + 1
    if jami_sahifa > 1:
        nav.append(InlineKeyboardButton(text=f"{sahifa+1}/{jami_sahifa}", callback_data="tt_lock"))
    if boshi + sahifa_hajmi < len(ro_yxat):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"tt_p:{togarak_id}:{sahifa+1}"))
    if nav:
        rows.append(nav)

    ochiq_soni = sum(1 for m in ro_yxat if m[3])
    hammasi = len(tanlangan) >= ochiq_soni and ochiq_soni > 0
    rows.append([InlineKeyboardButton(
        text=("❎ Belgilashni bekor qil" if hammasi else f"✅ Barchasi ({ochiq_soni} mavzu)"),
        callback_data=f"tt_all:{togarak_id}")])

    if tanlangan:
        n = test_soni(_kodlar_yig(ro_yxat, tanlangan))
        chiqadi = min(n, MAX_TEST)
        rows.append([InlineKeyboardButton(
            text=f"▶️ Boshlash — {len(tanlangan)} mavzu, {chiqadi} savol",
            callback_data=f"tt_go:{togarak_id}")])

    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"stg_info:{togarak_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kodlar_yig(ro_yxat, tanlangan):
    kodlar = set()
    for i in tanlangan:
        if 0 <= i < len(ro_yxat):
            kodlar.update(ro_yxat[i][1])
    return sorted(kodlar)


def kodlar(ro_yxat, tanlangan):
    return _kodlar_yig(ro_yxat, tanlangan)


def nomlar(ro_yxat, tanlangan):
    return [ro_yxat[i][0] for i in sorted(tanlangan) if 0 <= i < len(ro_yxat)]
