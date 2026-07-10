"""baholash.py — To'garak imtihonlari, baho va reyting.

Yakuniy baho:
    imtihon × 80%  +  uy vazifasi × 10%  +  mustaqil test × 10%

Imtihon ikki xil:
    yozma — o'qituvchi 1..100 foiz qo'yadi
    test  — bot savol beradi, foizni o'zi hisoblaydi

Imtihon yurituvchisi shu modulda — test_engine ga bog'liq emas.
"""
import os
import random
import psycopg2
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL", "")

W_IMTIHON = 0.80
W_VAZIFA  = 0.10
W_TEST    = 0.10

# Faol imtihon seanslari: {user_id: {...}}
_SEANS = {}


def _db():
    return psycopg2.connect(DATABASE_URL)


def jadval():
    """Jadvallarni yaratadi (idempotent)."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS togarak_imtihon(
            id SERIAL PRIMARY KEY,
            togarak_id INT NOT NULL,
            teacher_id BIGINT,
            nomi TEXT,
            turi TEXT DEFAULT 'yozma',
            topic_codes TEXT[],
            savol_soni INT DEFAULT 20,
            aktiv BOOLEAN DEFAULT TRUE,
            sana TIMESTAMP DEFAULT NOW()
        )""")
        cr.execute("""CREATE TABLE IF NOT EXISTS imtihon_natija(
            id SERIAL PRIMARY KEY,
            imtihon_id INT NOT NULL,
            user_id BIGINT NOT NULL,
            foiz NUMERIC(5,2) DEFAULT 0,
            manba TEXT DEFAULT 'teacher',
            izoh TEXT,
            sana TIMESTAMP DEFAULT NOW(),
            UNIQUE(imtihon_id, user_id)
        )""")
        cr.execute("""CREATE INDEX IF NOT EXISTS idx_imt_tog
            ON togarak_imtihon(togarak_id)""")
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[baho] jadval: {e}")
        return False


# ═══════════════ IMTIHON YARATISH ═══════════════

def imtihon_yarat(togarak_id, teacher_id, nomi, turi="yozma",
                  topic_codes=None, savol_soni=20):
    jadval()
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""INSERT INTO togarak_imtihon
            (togarak_id, teacher_id, nomi, turi, topic_codes, savol_soni)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
            (togarak_id, teacher_id, nomi, turi,
             list(topic_codes) if topic_codes else None, savol_soni))
        iid = cr.fetchone()[0]
        c.commit(); cr.close(); c.close()
        return iid
    except Exception as e:
        print(f"[baho] yarat: {e}")
        return None


def imtihon_ol(imtihon_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT id, togarak_id, teacher_id, nomi, turi,
                   topic_codes, savol_soni, aktiv
            FROM togarak_imtihon WHERE id=%s""", (imtihon_id,))
        r = cr.fetchone(); cr.close(); c.close()
        if not r:
            return None
        return {"id": r[0], "togarak_id": r[1], "teacher_id": r[2],
                "nomi": r[3], "turi": r[4],
                "topic_codes": list(r[5] or []), "savol_soni": r[6],
                "aktiv": r[7]}
    except Exception as e:
        print(f"[baho] ol: {e}")
        return None


def imtihonlar(togarak_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT i.id, i.nomi, i.turi, i.sana,
                   (SELECT COUNT(*) FROM imtihon_natija n WHERE n.imtihon_id=i.id)
            FROM togarak_imtihon i
            WHERE i.togarak_id=%s AND i.aktiv=TRUE
            ORDER BY i.sana DESC LIMIT 20""", (togarak_id,))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[baho] ro'yxat: {e}")
        return []


def baho_qoy(imtihon_id, user_id, foiz, manba="teacher", izoh=None):
    """Foiz 0..100 oralig'ida saqlanadi."""
    foiz = max(0, min(100, float(foiz)))
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""INSERT INTO imtihon_natija(imtihon_id,user_id,foiz,manba,izoh)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(imtihon_id,user_id) DO UPDATE
            SET foiz=EXCLUDED.foiz, manba=EXCLUDED.manba,
                izoh=EXCLUDED.izoh, sana=NOW()""",
            (imtihon_id, user_id, foiz, manba, izoh))
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[baho] qoy: {e}")
        return False


def natijalar(imtihon_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT n.user_id, u.full_name, n.foiz, n.manba
            FROM imtihon_natija n
            LEFT JOIN users u ON u.user_id=n.user_id
            WHERE n.imtihon_id=%s ORDER BY n.foiz DESC""", (imtihon_id,))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[baho] natija: {e}")
        return []


# ═══════════════ UY ISHI (20%) ═══════════════

def vazifa_foizi(togarak_id, user_id):
    """Uy vazifasi topshirilgan foizi."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COUNT(*) FROM homework WHERE togarak_id=%s", (togarak_id,))
        jami = (cr.fetchone() or [0])[0]
        if not jami:
            cr.close(); c.close(); return 0.0
        topshirdi = 0
        for jadval_nom in ("homework_javoblar", "homework_answers", "hw_javoblar"):
            try:
                cr.execute(f"""SELECT COUNT(DISTINCT j.homework_id) FROM {jadval_nom} j
                    JOIN homework h ON h.id=j.homework_id
                    WHERE h.togarak_id=%s AND j.user_id=%s""",
                    (togarak_id, user_id))
                topshirdi = (cr.fetchone() or [0])[0]
                break
            except Exception:
                c.rollback(); continue
        cr.close(); c.close()
        return round(topshirdi * 100.0 / jami, 1)
    except Exception as e:
        print(f"[baho] vazifa: {e}")
        return 0.0


def mustaqil_test_foizi(togarak_id, user_id):
    """Mustaqil ishlagan testlarning o'rtacha foizi."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT fan FROM togaraklar WHERE id=%s", (togarak_id,))
        fan = (cr.fetchone() or [None])[0]
        if not fan:
            cr.close(); c.close(); return 0.0
        cr.execute("""SELECT AVG(score * 100.0 / NULLIF(total,0))
            FROM results WHERE user_id=%s AND subject ILIKE %s""",
            (user_id, f"%{fan}%"))
        r = cr.fetchone()
        cr.close(); c.close()
        return round(float(r[0]), 1) if r and r[0] is not None else 0.0
    except Exception as e:
        print(f"[baho] mustaqil: {e}")
        return 0.0


def imtihon_ortacha(togarak_id, user_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT AVG(n.foiz) FROM imtihon_natija n
            JOIN togarak_imtihon i ON i.id=n.imtihon_id
            WHERE i.togarak_id=%s AND n.user_id=%s""", (togarak_id, user_id))
        r = cr.fetchone(); cr.close(); c.close()
        return round(float(r[0]), 1) if r and r[0] is not None else None
    except Exception as e:
        print(f"[baho] o'rtacha: {e}")
        return None


def yakuniy(togarak_id, user_id):
    """Yakuniy baho va tarkibiy qismlari."""
    imt = imtihon_ortacha(togarak_id, user_id)
    vaz = vazifa_foizi(togarak_id, user_id)
    tst = mustaqil_test_foizi(togarak_id, user_id)

    if imt is None:
        # Imtihon hali yo'q — qolgan ikkisi teng bo'linadi
        ball = vaz * 0.5 + tst * 0.5
        imtihon_bor = False
    else:
        ball = imt * W_IMTIHON + vaz * W_VAZIFA + tst * W_TEST
        imtihon_bor = True

    return {"yakuniy": round(ball, 1), "imtihon": imt, "vazifa": vaz,
            "test": tst, "imtihon_bor": imtihon_bor}


def daraja(foiz):
    if foiz >= 90: return "🏆 A'lo"
    if foiz >= 75: return "⭐ Yaxshi"
    if foiz >= 60: return "👍 Qoniqarli"
    if foiz > 0:   return "📖 Harakat kerak"
    return "—"


# ═══════════════ REYTING ═══════════════

def reyting(togarak_id):
    """[(user_id, ism, yakuniy, imtihon, vazifa, test)] — kamayish tartibida."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT a.user_id, COALESCE(u.full_name,'—')
            FROM togarak_azolar a
            LEFT JOIN users u ON u.user_id=a.user_id
            WHERE a.togarak_id=%s AND a.aktiv=TRUE""", (togarak_id,))
        azolar = cr.fetchall(); cr.close(); c.close()
    except Exception as e:
        print(f"[baho] reyting: {e}")
        return []

    natija = []
    for uid, ism in azolar:
        y = yakuniy(togarak_id, uid)
        natija.append((uid, ism, y["yakuniy"], y["imtihon"], y["vazifa"], y["test"]))
    natija.sort(key=lambda x: x[2], reverse=True)
    return natija


# ═══════════════ TEST IMTIHONI (o'z yurituvchisi) ═══════════════

def savollar_ol(topic_codes, soni):
    """Imtihon savollarini oladi — test va yozma javobli ARALASH.
    Har savol o'z turida ko'rsatiladi (question_type orqali)."""
    if not topic_codes:
        return []
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer,
                   COALESCE(NULLIF(image_file_id,''), NULL) AS rasm,
                   COALESCE(question_type, 'multiple_choice') AS turi
            FROM generated_tests
            WHERE topic_code=ANY(%s)
            ORDER BY RANDOM() LIMIT %s""", (list(topic_codes), int(soni)))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[baho] savollar: {e}")
        return []


def seans_boshla(user_id, imtihon_id, savollar):
    _SEANS[user_id] = {"imtihon_id": imtihon_id, "savollar": savollar,
                       "idx": 0, "togri": 0}
    return _SEANS[user_id]


def seans(user_id):
    return _SEANS.get(user_id)


def seans_tugat(user_id):
    return _SEANS.pop(user_id, None)


def savol_yozmami(s):
    """Savol yozma javobli turdami?"""
    turi = s[7] if len(s) > 7 else "multiple_choice"
    return turi == "write_answer"


def savol_kb(imtihon_id, idx, yozma=False):
    if yozma:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 To'xtatish", callback_data=f"imstop:{imtihon_id}")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data=f"imq:{imtihon_id}:{idx}:A"),
         InlineKeyboardButton(text="B", callback_data=f"imq:{imtihon_id}:{idx}:B"),
         InlineKeyboardButton(text="C", callback_data=f"imq:{imtihon_id}:{idx}:C"),
         InlineKeyboardButton(text="D", callback_data=f"imq:{imtihon_id}:{idx}:D")],
        [InlineKeyboardButton(text="🛑 To'xtatish", callback_data=f"imstop:{imtihon_id}")],
    ])


def savol_matni(s, idx, jami):
    q = s[0]
    if savol_yozmami(s):
        return (f"📝 Savol {idx+1}/{jami}\n\n{q}\n\n"
                f"✍️ Javobingizni yozib yuboring:")
    a, b, cc, d = s[1], s[2], s[3], s[4]
    return (f"📝 Savol {idx+1}/{jami}\n\n{q}\n\n"
            f"A) {a}\nB) {b}\nC) {cc}\nD) {d}")


def _normalash(matn):
    """Yozma javobni solishtirish uchun soddalashtiradi:
    kichik harf, vergul->nuqta (o'nlik kasr), boshqa tinish belgilari bo'sh joyga,
    so'z ichidagi/o'rtasidagi nuqta (o'nlik kasr) saqlanadi, bosh/oxiridagi olinadi."""
    import re
    t = str(matn or "").strip().lower()
    t = t.replace(",", ".")
    t = re.sub(r"[^\w\s.\-]", " ", t, flags=re.UNICODE)
    t = re.sub(r"(?<!\d)\.(?!\d)", " ", t)      # raqamlar orasida bo'lmagan nuqta -> bo'sh joy
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _keyingi(user_id, togri):
    """Javobdan keyingi umumiy hisob — harf yoki matn javobidan qat'iy nazar."""
    st = _SEANS.get(user_id)
    if not st:
        return (togri, True, 0.0)
    if togri:
        st["togri"] += 1
    st["idx"] += 1
    tugadi = st["idx"] >= len(st["savollar"])
    foiz = round(st["togri"] * 100.0 / max(1, len(st["savollar"])), 1)
    return (togri, tugadi, foiz)


def javob_tekshir(user_id, javob):
    """A/B/C/D javob uchun. (togri_mi, tugadi_mi, foiz)"""
    st = _SEANS.get(user_id)
    if not st:
        return (False, True, 0.0)
    s = st["savollar"][st["idx"]]
    togri_harf = str(s[5] or "").strip().upper()[:1]
    togri = (javob.upper() == togri_harf)
    return _keyingi(user_id, togri)


def javob_tekshir_matn(user_id, matn):
    """Yozma javob uchun — soddalashtirib solishtiradi. (togri_mi, tugadi_mi, foiz)"""
    st = _SEANS.get(user_id)
    if not st:
        return (False, True, 0.0)
    s = st["savollar"][st["idx"]]
    togri = (_normalash(matn) == _normalash(s[5]))
    return _keyingi(user_id, togri)
