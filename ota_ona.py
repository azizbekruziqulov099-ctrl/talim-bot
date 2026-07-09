"""ota_ona.py — Ota-ona va farzandni xavfsiz bog'lash.

Oqim:
  1. Farzand «🔗 Ota-onani ulash» bosadi → 6 xonali kod oladi (15 daqiqa)
  2. Ota-ona kodni kiritadi
  3. Farzandga so'rov boradi → tasdiqlaydi
  4. Bog'lanish o'rnatiladi

Kodsiz yoki tasdiqsiz hech kim ulanmaydi.
"""
import os
import random
import psycopg2
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL", "")
KOD_MUDDAT = 15          # daqiqa


def _db():
    return psycopg2.connect(DATABASE_URL)


def jadval():
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS farzand_kod(
            kod TEXT PRIMARY KEY,
            child_id BIGINT NOT NULL,
            muddat TIMESTAMP NOT NULL
        )""")
        cr.execute("""CREATE TABLE IF NOT EXISTS parent_child(
            id SERIAL PRIMARY KEY,
            parent_id BIGINT NOT NULL,
            child_id BIGINT NOT NULL
        )""")
        # Takror bog'lanishning oldini olamiz
        try:
            cr.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_pc_uniq
                ON parent_child(parent_id, child_id)""")
        except Exception:
            c.rollback()
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[ota_ona] jadval: {e}")
        return False


# ═══════════════ KOD ═══════════════

def kod_yarat(child_id):
    """Farzand uchun 6 xonali kod. Eski kodlari bekor qilinadi."""
    jadval()
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM farzand_kod WHERE child_id=%s OR muddat < NOW()", (child_id,))
        for _ in range(10):
            kod = f"{random.randint(100000, 999999)}"
            cr.execute("SELECT 1 FROM farzand_kod WHERE kod=%s", (kod,))
            if not cr.fetchone():
                break
        cr.execute("INSERT INTO farzand_kod(kod, child_id, muddat) VALUES(%s,%s,%s)",
                   (kod, child_id, datetime.now() + timedelta(minutes=KOD_MUDDAT)))
        c.commit(); cr.close(); c.close()
        return kod
    except Exception as e:
        print(f"[ota_ona] kod_yarat: {e}")
        return None


def kod_tekshir(kod):
    """Kod to'g'ri va muddati o'tmagan bo'lsa child_id qaytaradi."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM farzand_kod WHERE muddat < NOW()")
        cr.execute("SELECT child_id FROM farzand_kod WHERE kod=%s", (str(kod).strip(),))
        r = cr.fetchone()
        c.commit(); cr.close(); c.close()
        return r[0] if r else None
    except Exception as e:
        print(f"[ota_ona] kod_tekshir: {e}")
        return None


def kod_ochir(kod):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM farzand_kod WHERE kod=%s", (str(kod).strip(),))
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[ota_ona] kod_ochir: {e}")


# ═══════════════ BOG'LANISH ═══════════════

def bogla(parent_id, child_id):
    jadval()
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""INSERT INTO parent_child(parent_id, child_id) VALUES(%s,%s)
            ON CONFLICT DO NOTHING""", (parent_id, child_id))
        ok = cr.rowcount > 0
        c.commit(); cr.close(); c.close()
        return ok
    except Exception as e:
        print(f"[ota_ona] bogla: {e}")
        return False


def uzib_qoy(parent_id, child_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM parent_child WHERE parent_id=%s AND child_id=%s",
                   (parent_id, child_id))
        n = cr.rowcount
        c.commit(); cr.close(); c.close()
        return n > 0
    except Exception as e:
        print(f"[ota_ona] uzib: {e}")
        return False


def bogliqmi(parent_id, child_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT 1 FROM parent_child WHERE parent_id=%s AND child_id=%s",
                   (parent_id, child_id))
        r = cr.fetchone(); cr.close(); c.close()
        return bool(r)
    except Exception:
        return False


def farzandlar(parent_id):
    """[(child_id, ism, sinf)]"""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT p.child_id, COALESCE(u.full_name,'—'), COALESCE(u.class,'')
            FROM parent_child p LEFT JOIN users u ON u.user_id=p.child_id
            WHERE p.parent_id=%s ORDER BY u.full_name""", (parent_id,))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[ota_ona] farzandlar: {e}")
        return []


def otalar(child_id):
    """Farzandga bog'langan ota-onalar: [(parent_id, ism)]"""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT p.parent_id, COALESCE(u.full_name,'—')
            FROM parent_child p LEFT JOIN users u ON u.user_id=p.parent_id
            WHERE p.child_id=%s""", (child_id,))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[ota_ona] otalar: {e}")
        return []


def kim(user_id):
    """(ism, rol, sinf)"""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT full_name, role, class FROM users WHERE user_id=%s", (user_id,))
        r = cr.fetchone(); cr.close(); c.close()
        return r if r else (None, None, None)
    except Exception:
        return (None, None, None)
