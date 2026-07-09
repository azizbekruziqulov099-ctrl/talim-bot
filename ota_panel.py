"""ota_panel.py — Ota-ona paneli.

Farzand haqida: yo'qlama, uy vazifasi, imtihon, baholar, umumiy nazorat.
Barcha so'rovlar himoyalangan — jadval bo'lmasa ham yiqilmaydi.
"""
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _db():
    return psycopg2.connect(DATABASE_URL)


_KOL_CACHE = {}

def _ustunlar(jadval):
    """Jadvaldagi haqiqiy ustun nomlari va turlarini DB dan aniqlaydi.
    Taxmin qilish o'rniga — bilib ishlatamiz, xato spam bo'lmaydi."""
    if jadval in _KOL_CACHE:
        return _KOL_CACHE[jadval]
    kols = {}
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name=%s""", (jadval,))
        kols = {r[0]: r[1] for r in cr.fetchall()}
        cr.close(); c.close()
        if not kols:
            print(f"[op] ⚠️ jadval topilmadi: {jadval}")
    except Exception as e:
        print(f"[op] ustunlar({jadval}): {e}")
    _KOL_CACHE[jadval] = kols
    return kols


def _topuvchi(kols, nomzodlar, tur_ichida=None):
    """kols dan mos ustunni topadi: avval aniq nom, keyin tur bo'yicha."""
    for n in nomzodlar:
        if n in kols:
            return n
    if tur_ichida:
        for col, tur in kols.items():
            if any(t in tur for t in tur_ichida):
                return col
    return None


def _bir(sql, args=(), zaxira=None):
    try:
        c = _db(); cr = c.cursor()
        cr.execute(sql, args)
        r = cr.fetchone()
        cr.close(); c.close()
        return r if r else zaxira
    except Exception as e:
        print(f"[op] {e}")
        return zaxira


def _kop(sql, args=()):
    try:
        c = _db(); cr = c.cursor()
        cr.execute(sql, args)
        r = cr.fetchall()
        cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[op] {e}")
        return []


def farzand_info(child_id):
    r = _bir("SELECT full_name, class, school FROM users WHERE user_id=%s", (child_id,))
    return {"ism": (r[0] if r else "—"), "sinf": (r[1] if r else ""),
            "maktab": (r[2] if r else "")}


def togaraklari(child_id):
    return _kop("""SELECT t.id, t.nomi, t.fan
        FROM togarak_azolar a JOIN togaraklar t ON t.id=a.togarak_id
        WHERE a.user_id=%s AND a.aktiv=TRUE AND t.aktiv=TRUE""", (child_id,))


# ═══════════════ YO'QLAMA ═══════════════

def yoqlama(child_id):
    """[(togarak_nomi, keldi, jami, foiz)]"""
    kols = _ustunlar("togarak_yoqlama")
    holat_u = _topuvchi(kols, ["holat", "status", "kelgan", "keldimi", "bor", "davomat"])

    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        keldi = jami = 0
        if holat_u:
            r = _bir(f"""SELECT
                COUNT(*) FILTER (WHERE {holat_u}::text IN
                    ('keldi','kech','1','true','True','TRUE','t','bor')),
                COUNT(*)
                FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s""",
                (tid, child_id))
            if r:
                keldi, jami = int(r[0] or 0), int(r[1] or 0)
        else:
            r = _bir("SELECT COUNT(*) FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s",
                     (tid, child_id))
            jami = int(r[0]) if r else 0
        foiz = round(keldi * 100.0 / jami, 1) if jami else 0.0
        natija.append((nomi, keldi, jami, foiz))
    return natija


# ═══════════════ UY VAZIFASI ═══════════════

def vazifalar(child_id):
    """[(togarak_nomi, mavzu, deadline, topshirdimi)]"""
    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        hw = _kop("""SELECT id, mavzu, deadline FROM homework
            WHERE togarak_id=%s ORDER BY id DESC LIMIT 10""", (tid,))
        for hid, mavzu, dl in hw:
            topshirdi = False
            for jadval in ("homework_javoblar", "homework_answers", "hw_javoblar"):
                r = _bir(f"""SELECT 1 FROM {jadval}
                    WHERE homework_id=%s AND user_id=%s LIMIT 1""", (hid, child_id))
                if r:
                    topshirdi = True
                    break
            natija.append((nomi, mavzu or "—", dl, topshirdi))
    return natija


# ═══════════════ IMTIHON ═══════════════

def imtihonlar(child_id):
    """[(imtihon_nomi, foiz, turi, sana)]"""
    return _kop("""SELECT i.nomi, n.foiz, i.turi, n.sana
        FROM imtihon_natija n JOIN togarak_imtihon i ON i.id=n.imtihon_id
        WHERE n.user_id=%s ORDER BY n.sana DESC LIMIT 15""", (child_id,))


# ═══════════════ BAHOLAR ═══════════════

def baholar(child_id):
    """[(togarak_nomi, baho, sana)] — sana bo'lmasa None qaytadi."""
    kols = _ustunlar("togarak_baholar")
    if not kols:
        return []
    baho_u = _topuvchi(kols, ["baho", "ball", "score", "natija", "foiz"])
    if not baho_u:
        return []
    sana_u = _topuvchi(kols, ["sana", "vaqt", "created_at", "yaratilgan", "tarix", "sanasi"],
                       tur_ichida=["timestamp", "date"])
    tartib_u = sana_u or ("id" if "id" in kols else None)

    sel = f"{baho_u}, {sana_u}" if sana_u else f"{baho_u}, NULL"
    tartib_sql = f"ORDER BY {tartib_u} DESC" if tartib_u else ""

    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        r = _kop(f"""SELECT {sel} FROM togarak_baholar
            WHERE togarak_id=%s AND user_id=%s {tartib_sql} LIMIT 10""",
            (tid, child_id))
        natija += [(nomi, x[0], x[1]) for x in r]
    return natija


def test_natijalari(child_id):
    """[(fan, foiz, sana)] — mustaqil ishlagan testlar."""
    return _kop("""SELECT subject, ROUND(score*100.0/NULLIF(total,0)), id
        FROM results WHERE user_id=%s ORDER BY id DESC LIMIT 10""", (child_id,))


# ═══════════════ UMUMIY NAZORAT ═══════════════

def nazorat(child_id):
    """Barcha to'garaklar bo'yicha yakuniy ko'rsatkich."""
    try:
        import baholash as _bh
    except Exception:
        return []
    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        y = _bh.yakuniy(tid, child_id)
        y["togarak"] = nomi
        y["daraja"] = _bh.daraja(y["yakuniy"])
        # Reytingdagi o'rni
        try:
            r = _bh.reyting(tid)
            orni = next((i + 1 for i, x in enumerate(r) if x[0] == child_id), None)
            y["orin"] = orni
            y["jami"] = len(r)
        except Exception:
            y["orin"] = None; y["jami"] = 0
        natija.append(y)
    return natija
