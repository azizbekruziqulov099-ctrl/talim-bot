"""ota_panel.py — Ota-ona paneli.

Farzand haqida: yo'qlama, uy vazifasi, imtihon, baholar, umumiy nazorat.
Barcha so'rovlar himoyalangan — jadval bo'lmasa ham yiqilmaydi.
"""
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _db():
    return psycopg2.connect(DATABASE_URL)


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
    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        keldi = jami = 0
        for ustun in ("holat", "kelgan", "status"):
            r = _bir(f"""SELECT
                COUNT(*) FILTER (WHERE {ustun} IN ('keldi','1','true','bor')),
                COUNT(*)
                FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s""",
                (tid, child_id))
            if r and r[1]:
                keldi, jami = int(r[0] or 0), int(r[1] or 0)
                break
        if jami == 0:
            r = _bir("""SELECT COUNT(*) FROM togarak_yoqlama
                WHERE togarak_id=%s AND user_id=%s""", (tid, child_id))
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
    """[(togarak_nomi, baho, sana)]"""
    natija = []
    for tid, nomi, fan in togaraklari(child_id):
        for ustun in ("baho", "ball", "score"):
            r = _kop(f"""SELECT {ustun}, sana FROM togarak_baholar
                WHERE togarak_id=%s AND user_id=%s
                ORDER BY sana DESC LIMIT 10""", (tid, child_id))
            if r:
                natija += [(nomi, x[0], x[1]) for x in r]
                break
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
