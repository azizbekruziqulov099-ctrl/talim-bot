"""nazorat_test.py — Ota-ona farzandiga tezkor nazorat testi yuboradi.

Farqi o'qituvchi-imtihonidan: VAQT kuzatiladi (tezlik), natija ota-ona
paneliga 3 parametr bilan chiqadi:
  1. Aniqlik  — necha foiz to'g'ri
  2. Tezlik   — o'rtacha necha soniya/savol
  3. Dinamika — oldingi nazorat testiga nisbatan farq
"""
import os
import psycopg2
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Faol seanslar: {child_id: {...}}
_SEANS = {}


def _db():
    return psycopg2.connect(DATABASE_URL)


def jadval():
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS nazorat_test(
            id SERIAL PRIMARY KEY,
            parent_id BIGINT NOT NULL,
            child_id BIGINT NOT NULL,
            togarak_id INT,
            manba TEXT,
            topic_codes TEXT[],
            savol_soni INT DEFAULT 20,
            vaqt_limit_soniya INT,
            boshlandi TIMESTAMP,
            tugadi TIMESTAMP,
            togri INT DEFAULT 0,
            jami INT DEFAULT 0,
            foiz NUMERIC(5,2),
            sarflangan_soniya INT,
            vaqt_tugab_tugadimi BOOLEAN DEFAULT FALSE,
            yaratildi TIMESTAMP DEFAULT NOW()
        )""")
        # Eski qatorlarda ustun bo'lmasa qo'shamiz
        for _ust, _tur in (("vaqt_limit_soniya","INT"), ("vaqt_tugab_tugadimi","BOOLEAN DEFAULT FALSE")):
            try:
                cr.execute(f"ALTER TABLE nazorat_test ADD COLUMN IF NOT EXISTS {_ust} {_tur}")
            except Exception:
                c.rollback()
        cr.execute("""CREATE INDEX IF NOT EXISTS idx_nz_child
            ON nazorat_test(child_id, yaratildi DESC)""")
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[nz] jadval: {e}")
        return False


# ═══════════════ USTUN ANIQLASH (taxmin qilmaymiz) ═══════════════

def _ustunlar(jadval_nom):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT column_name FROM information_schema.columns
            WHERE table_name=%s""", (jadval_nom,))
        r = {x[0] for x in cr.fetchall()}
        cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[nz] ustunlar({jadval_nom}): {e}")
        return set()


# ═══════════════ MAVZU MANBASI ═══════════════

def _otilgan_royxat(togarak_id):
    """[(topic_code, mavzu_name)] — o'tilgan mavzular, ENG YANGISI birinchi.
    togarak_dars_log da vaqt ustuni bo'lsa shundan, bo'lmasa reja tartibidan."""
    try:
        c = _db(); cr = c.cursor()
        dl_kols = _ustunlar("togarak_dars_log")
        vaqt_u = next((u for u in ("sana", "vaqt", "created_at", "yaratilgan", "marked_at")
                       if u in dl_kols), None)

        if vaqt_u:
            cr.execute(f"""
                SELECT l.topic_code, COALESCE(d.mavzu_name, l.topic_code), MAX(l.{vaqt_u}) AS oxirgi
                FROM togarak_dars_log l
                LEFT JOIN dts_tree d ON d.topic_code = l.topic_code
                WHERE l.togarak_id=%s
                GROUP BY l.topic_code, d.mavzu_name
                ORDER BY oxirgi DESC
            """, (togarak_id,))
            r = [(tc, nm) for tc, nm, _ in cr.fetchall()]
        else:
            cr.execute("""
                SELECT r.topic_code, COALESCE(d.mavzu_name, r.topic_code)
                FROM togarak_reja r
                LEFT JOIN dts_tree d ON d.topic_code = r.topic_code
                WHERE r.togarak_id=%s AND r.completed=TRUE
                ORDER BY r.tartib DESC
            """, (togarak_id,))
            r = cr.fetchall()
        cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[nz] otilgan: {e}")
        return []


def manba_nomi(manba):
    return {"oxirgi": "📗 Oxirgi o'tilgan mavzu",
            "oldingi": "📙 Oldingi mavzu",
            "oxirgi10": "📚 Oxirgi 10 ta mavzu",
            "tanlov": "☑️ O'zim tanlayman"}.get(manba, manba)


def tanlangan_kodlar(togarak_id, indekslar):
    """_otilgan_royxat() dagi berilgan indekslardagi mavzularning kodlarini qaytaradi."""
    royxat = _otilgan_royxat(togarak_id)
    kodlar, nomlar = [], []
    for i in indekslar:
        if 0 <= i < len(royxat):
            kodlar.append(royxat[i][0])
            nomlar.append(royxat[i][1])
    return kodlar, nomlar


def manba_kodlari(togarak_id, manba):
    """manba: 'oxirgi' | 'oldingi' | 'oxirgi10' -> (topic_code lar, mavzu nomlari)."""
    royxat = _otilgan_royxat(togarak_id)
    if not royxat:
        return [], []
    if manba == "oxirgi":
        tanlangan = royxat[:1]
    elif manba == "oldingi":
        tanlangan = royxat[1:2] if len(royxat) > 1 else royxat[:1]
    elif manba == "oxirgi10":
        tanlangan = royxat[:10]
    else:
        tanlangan = royxat[:1]
    kodlar = [tc for tc, _ in tanlangan]
    nomlar = [nm for _, nm in tanlangan]
    return kodlar, nomlar


def test_soni_bor(topic_codes):
    if not topic_codes:
        return 0
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=ANY(%s)",
                   (list(topic_codes),))
        n = (cr.fetchone() or [0])[0]
        cr.close(); c.close()
        return n
    except Exception:
        return 0


# ═══════════════ VAQT VARIANTLARI ═══════════════

VAQT_VARIANTLARI = [
    ("30 daq", 30*60), ("40 daq", 40*60), ("50 daq", 50*60),
    ("1 soat", 60*60), ("1s 10 daq", 70*60), ("1s 30 daq", 90*60),
    ("2 soat", 120*60), ("2s 30 daq", 150*60), ("3 soat", 180*60),
]


def vaqt_matni(soniya):
    if not soniya:
        return "cheklanmagan"
    for nom, son in VAQT_VARIANTLARI:
        if son == soniya:
            return nom
    daq = soniya // 60
    return f"{daq} daq"


# ═══════════════ YARATISH VA YUBORISH ═══════════════

def yarat(parent_id, child_id, togarak_id, manba, topic_codes, savol_soni, vaqt_limit_soniya=None):
    jadval()
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""INSERT INTO nazorat_test
            (parent_id, child_id, togarak_id, manba, topic_codes, savol_soni, vaqt_limit_soniya)
            VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (parent_id, child_id, togarak_id, manba, list(topic_codes), savol_soni, vaqt_limit_soniya))
        nid = cr.fetchone()[0]
        c.commit(); cr.close(); c.close()
        return nid
    except Exception as e:
        print(f"[nz] yarat: {e}")
        return None


def ol(nz_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT id, parent_id, child_id, togarak_id, manba,
                   topic_codes, savol_soni, vaqt_limit_soniya
            FROM nazorat_test WHERE id=%s""", (nz_id,))
        r = cr.fetchone(); cr.close(); c.close()
        if not r:
            return None
        return {"id": r[0], "parent_id": r[1], "child_id": r[2], "togarak_id": r[3],
                "manba": r[4], "topic_codes": list(r[5] or []), "savol_soni": r[6],
                "vaqt_limit_soniya": r[7]}
    except Exception as e:
        print(f"[nz] ol: {e}")
        return None


# ═══════════════ SAVOL / SEANS (baholash.py bilan bir xil savol formati) ═══════════════

def savollar_ol(topic_codes, soni):
    import baholash as _bh
    return _bh.savollar_ol(topic_codes, soni)


def savol_yozmami(s):
    import baholash as _bh
    return _bh.savol_yozmami(s)


def savol_matni(s, idx, jami):
    import baholash as _bh
    return _bh.savol_matni(s, idx, jami)


def savol_kb(nz_id, idx, yozma=False):
    if yozma:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 To'xtatish", callback_data=f"nzstop:{nz_id}")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data=f"nzq:{nz_id}:{idx}:A"),
         InlineKeyboardButton(text="B", callback_data=f"nzq:{nz_id}:{idx}:B"),
         InlineKeyboardButton(text="C", callback_data=f"nzq:{nz_id}:{idx}:C"),
         InlineKeyboardButton(text="D", callback_data=f"nzq:{nz_id}:{idx}:D")],
        [InlineKeyboardButton(text="🛑 To'xtatish", callback_data=f"nzstop:{nz_id}")],
    ])


def seans_boshla(child_id, nz_id, savollar, vaqt_limit_soniya=None):
    _SEANS[child_id] = {"nz_id": nz_id, "savollar": savollar, "idx": 0,
                        "togri": 0, "boshlandi": datetime.now(),
                        "vaqt_limit": vaqt_limit_soniya}
    return _SEANS[child_id]


def seans(child_id):
    return _SEANS.get(child_id)


def seans_bekor(child_id):
    return _SEANS.pop(child_id, None)


def vaqt_tugadimi(child_id):
    """Umumiy vaqt limiti tugaganmi? Limit yo'q bo'lsa har doim False."""
    st = _SEANS.get(child_id)
    if not st or not st.get("vaqt_limit"):
        return False
    otgan = (datetime.now() - st["boshlandi"]).total_seconds()
    return otgan >= st["vaqt_limit"]


def qolgan_vaqt(child_id):
    """Necha soniya qoldi. Limit yo'q bo'lsa None."""
    st = _SEANS.get(child_id)
    if not st or not st.get("vaqt_limit"):
        return None
    otgan = (datetime.now() - st["boshlandi"]).total_seconds()
    return max(0, int(st["vaqt_limit"] - otgan))


def _keyingi(child_id, togri):
    st = _SEANS.get(child_id)
    if not st:
        return (togri, True, 0.0)
    if togri:
        st["togri"] += 1
    st["idx"] += 1
    tugadi = st["idx"] >= len(st["savollar"]) or vaqt_tugadimi(child_id)
    foiz = round(st["togri"] * 100.0 / max(1, len(st["savollar"])), 1)
    return (togri, tugadi, foiz)


def javob_tekshir(child_id, javob):
    st = _SEANS.get(child_id)
    if not st:
        return (False, True, 0.0)
    s = st["savollar"][st["idx"]]
    togri_harf = str(s[5] or "").strip().upper()[:1]
    togri = (javob.upper() == togri_harf)
    return _keyingi(child_id, togri)


def javob_tekshir_matn(child_id, matn):
    import baholash as _bh
    st = _SEANS.get(child_id)
    if not st:
        return (False, True, 0.0)
    s = st["savollar"][st["idx"]]
    togri = (_bh._normalash(matn) == _bh._normalash(s[5]))
    return _keyingi(child_id, togri)


def yakunla(child_id):
    """Testni yakunlaydi, DB ga vaqt+natija yozadi. dict qaytaradi yoki None."""
    st = _SEANS.pop(child_id, None)
    if not st:
        return None
    vaqt_bilan_tugadi = bool(st.get("vaqt_limit")) and \
        (datetime.now() - st["boshlandi"]).total_seconds() >= st["vaqt_limit"]
    tugadi_vaqt = datetime.now()
    sarflangan = max(1, int((tugadi_vaqt - st["boshlandi"]).total_seconds()))
    jami = len(st["savollar"]); togri = st["togri"]
    javob_bergan = st["idx"]   # nechta savolga ulgurgan
    foiz = round(togri * 100.0 / max(1, jami), 1)

    try:
        c = _db(); cr = c.cursor()
        cr.execute("""UPDATE nazorat_test SET boshlandi=%s, tugadi=%s, togri=%s,
            jami=%s, foiz=%s, sarflangan_soniya=%s, vaqt_tugab_tugadimi=%s WHERE id=%s""",
            (st["boshlandi"], tugadi_vaqt, togri, jami, foiz, sarflangan,
             vaqt_bilan_tugadi, st["nz_id"]))
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[nz] yakunla: {e}")

    return {"nz_id": st["nz_id"], "togri": togri, "jami": jami,
            "foiz": foiz, "sarflangan": sarflangan,
            "vaqt_bilan_tugadi": vaqt_bilan_tugadi, "javob_bergan": javob_bergan}


def bekor_qil(nz_id):
    """To'xtatilgan test — yarim qolgan deb belgilanadi (natija yo'q)."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM nazorat_test WHERE id=%s AND tugadi IS NULL", (nz_id,))
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[nz] bekor: {e}")


# ═══════════════ TARIX / TAHLIL (3 parametr) ═══════════════

def tarix(child_id, limit=10):
    """[(id, foiz, sarflangan_soniya, jami, yaratildi, manba)] — eng yangisi birinchi."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT id, foiz, sarflangan_soniya, jami, yaratildi, manba
            FROM nazorat_test WHERE child_id=%s AND tugadi IS NOT NULL
            ORDER BY yaratildi DESC LIMIT %s""", (child_id, limit))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[nz] tarix: {e}")
        return []


def tezlik_daraja(soniya_savol):
    if soniya_savol <= 15: return "⚡ Juda tez"
    if soniya_savol <= 30: return "🏃 Tez"
    if soniya_savol <= 60: return "🚶 O'rtacha"
    return "🐢 Sekin"


def tahlil(child_id):
    """Joriy natija + oldingisiga nisbatan farq. dict yoki None (tarix bo'sh bo'lsa)."""
    tar = tarix(child_id, limit=2)
    if not tar:
        return None
    jid, jfoiz, jsoniya, jjami, jsana, jmanba = tar[0]
    tez_joriy = round(jsoniya / max(1, jjami), 1)

    natija = {
        "foiz": float(jfoiz), "tezlik": tez_joriy, "jami": jjami,
        "sarflangan": jsoniya, "daraja_tezlik": tezlik_daraja(tez_joriy),
        "manba": manba_nomi(jmanba),
    }
    if len(tar) > 1:
        _, ofoiz, osoniya, ojami, _, _ = tar[1]
        tez_oldingi = round(osoniya / max(1, ojami), 1)
        natija["foiz_farqi"] = round(float(jfoiz) - float(ofoiz), 1)
        natija["tezlik_farqi"] = round(tez_oldingi - tez_joriy, 1)   # musbat = tezlashgan
    else:
        natija["foiz_farqi"] = None
        natija["tezlik_farqi"] = None
    return natija
