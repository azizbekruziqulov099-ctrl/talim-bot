"""akkaunt.py — Akkauntlarni boshqarish.

Muammo: ilgari user_id telegram_id dan hisoblanardi
        (idx=0 -> tg, idx=N -> tg*1000+N).
        Shuning uchun akkauntni boshqa telefonga ko'chirib bo'lmasdi.

Yechim: user_accounts.uid ustuni — ichki ID telefonga bog'lanmaydi.
        Ko'chirish = yangi telefonga shu uid bilan qator qo'shish.

Cheklov: bitta telefonda maksimal 3 ta akkaunt.
"""
import os
import random
import string
import psycopg2
from datetime import datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL", "")

MAX_AKKAUNT = 3          # bir telefonda
KOD_MUDDAT  = 30         # daqiqa (ko'chirish kodi)


def _db():
    return psycopg2.connect(DATABASE_URL)


def jadval():
    """uid ustuni + ko'chirish kodlari jadvali."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS user_accounts(
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            account_index INT NOT NULL,
            full_name TEXT, role TEXT, class TEXT,
            is_active BOOLEAN DEFAULT FALSE,
            UNIQUE(telegram_id, account_index)
        )""")
        c.commit()

        # uid ustuni (eski bazalar uchun)
        try:
            cr.execute("ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS uid BIGINT")
            c.commit()
        except Exception:
            c.rollback()

        # Eski qatorlarni to'ldiramiz (eski qoida bo'yicha)
        try:
            cr.execute("""UPDATE user_accounts SET uid =
                CASE WHEN account_index=0 THEN telegram_id
                     ELSE telegram_id*1000 + account_index END
                WHERE uid IS NULL""")
            n = cr.rowcount
            c.commit()
            if n:
                print(f"[akkaunt] {n} ta qatorga uid yozildi")
        except Exception as e:
            c.rollback(); print(f"[akkaunt] backfill: {e}")

        try:
            cr.execute("CREATE INDEX IF NOT EXISTS idx_ua_uid ON user_accounts(uid)")
            c.commit()
        except Exception:
            c.rollback()

        cr.execute("""CREATE TABLE IF NOT EXISTS kochirish_kod(
            kod TEXT PRIMARY KEY,
            uid BIGINT NOT NULL,
            muddat TIMESTAMP NOT NULL,
            yaratgan BIGINT
        )""")
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[akkaunt] jadval: {e}")
        return False


# ═══════════════ AKKAUNTLAR ═══════════════

def akkauntlar(telegram_id):
    """[(uid, account_index, ism, rol, sinf, aktiv)] — shu telefondagilar."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT uid, account_index, full_name, role, class, is_active
            FROM user_accounts WHERE telegram_id=%s ORDER BY account_index""",
            (telegram_id,))
        r = cr.fetchall(); cr.close(); c.close()
        return r
    except Exception as e:
        print(f"[akkaunt] ro'yxat: {e}")
        return []


def soni(telegram_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COUNT(*) FROM user_accounts WHERE telegram_id=%s", (telegram_id,))
        n = (cr.fetchone() or [0])[0]
        cr.close(); c.close()
        return n
    except Exception:
        return 0


def joy_bormi(telegram_id):
    return soni(telegram_id) < MAX_AKKAUNT


def yangi_uid():
    """Telefonga bog'liq bo'lmagan ichki ID."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COALESCE(MAX(uid), 0) FROM user_accounts")
        eng = (cr.fetchone() or [0])[0] or 0
        cr.execute("SELECT COALESCE(MAX(user_id), 0) FROM users")
        eng2 = (cr.fetchone() or [0])[0] or 0
        cr.close(); c.close()
        return max(int(eng), int(eng2)) + 1
    except Exception as e:
        print(f"[akkaunt] yangi_uid: {e}")
        return int(datetime.now().timestamp() * 1000)


def keyingi_index(telegram_id):
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT COALESCE(MAX(account_index),-1)+1
            FROM user_accounts WHERE telegram_id=%s""", (telegram_id,))
        n = (cr.fetchone() or [0])[0]
        cr.close(); c.close()
        return int(n)
    except Exception:
        return 0


def telefon(uid):
    """uid qaysi telefonda? (xabar yuborish uchun)"""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("""SELECT telegram_id FROM user_accounts WHERE uid=%s
            ORDER BY is_active DESC LIMIT 1""", (uid,))
        r = cr.fetchone(); cr.close(); c.close()
        return r[0] if r else None
    except Exception:
        return None


# ═══════════════ KO'CHIRISH ═══════════════

def kochirish_kod(uid, yaratgan_tg):
    """Akkauntni boshqa telefonga o'tkazish uchun kod."""
    jadval()
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM kochirish_kod WHERE uid=%s OR muddat < NOW()", (uid,))
        harflar = string.ascii_uppercase.replace("O", "").replace("I", "")
        raqam = "23456789"
        for _ in range(10):
            kod = "".join(random.choice(harflar + raqam) for _ in range(8))
            cr.execute("SELECT 1 FROM kochirish_kod WHERE kod=%s", (kod,))
            if not cr.fetchone():
                break
        cr.execute("""INSERT INTO kochirish_kod(kod, uid, muddat, yaratgan)
            VALUES(%s,%s,%s,%s)""",
            (kod, uid, datetime.now() + timedelta(minutes=KOD_MUDDAT), yaratgan_tg))
        c.commit(); cr.close(); c.close()
        return kod
    except Exception as e:
        print(f"[akkaunt] kod: {e}")
        return None


def kod_tekshir(kod):
    """(uid, yaratgan_tg) yoki None."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("DELETE FROM kochirish_kod WHERE muddat < NOW()")
        cr.execute("SELECT uid, yaratgan FROM kochirish_kod WHERE kod=%s",
                   (str(kod).strip().upper(),))
        r = cr.fetchone()
        c.commit(); cr.close(); c.close()
        return (r[0], r[1]) if r else None
    except Exception as e:
        print(f"[akkaunt] kod_tekshir: {e}")
        return None


def kochirish_bajar(kod, yangi_tg):
    """Akkauntni yangi telefonga ulaydi. (ok, xabar)"""
    t = kod_tekshir(kod)
    if not t:
        return (False, "❌ Kod noto'g'ri yoki muddati o'tgan.")
    uid, eski_tg = t

    if not joy_bormi(yangi_tg):
        return (False, f"❌ Bu telefonda allaqachon {MAX_AKKAUNT} ta akkaunt bor.")

    try:
        c = _db(); cr = c.cursor()
        # Shu uid bu telefonda bormi?
        cr.execute("SELECT 1 FROM user_accounts WHERE telegram_id=%s AND uid=%s",
                   (yangi_tg, uid))
        if cr.fetchone():
            cr.close(); c.close()
            return (False, "ℹ️ Bu akkaunt allaqachon shu telefonda.")

        cr.execute("SELECT full_name, role, class FROM users WHERE user_id=%s", (uid,))
        u = cr.fetchone()
        if not u:
            cr.close(); c.close()
            return (False, "❌ Akkaunt topilmadi.")

        idx = keyingi_index(yangi_tg)
        cr.execute("UPDATE user_accounts SET is_active=FALSE WHERE telegram_id=%s", (yangi_tg,))
        cr.execute("""INSERT INTO user_accounts
            (telegram_id, account_index, uid, full_name, role, class, is_active)
            VALUES(%s,%s,%s,%s,%s,%s,TRUE)""",
            (yangi_tg, idx, uid, u[0], u[1], u[2]))
        cr.execute("DELETE FROM kochirish_kod WHERE kod=%s", (str(kod).strip().upper(),))
        c.commit(); cr.close(); c.close()
        print(f"[akkaunt] uid={uid} -> tg={yangi_tg} idx={idx}")
        return (True, f"✅ {u[0]} akkaunti ulandi.")
    except Exception as e:
        print(f"[akkaunt] kochirish: {e}")
        return (False, f"❌ Xato: {e}")


def uzib_qoy(telegram_id, uid):
    """Akkauntni shu telefondan olib tashlaydi (ma'lumot o'chmaydi)."""
    try:
        c = _db(); cr = c.cursor()
        cr.execute("SELECT COUNT(*) FROM user_accounts WHERE uid=%s", (uid,))
        n = (cr.fetchone() or [0])[0]
        if n <= 1:
            cr.close(); c.close()
            return (False, "❌ Bu yagona telefon. Avval boshqa telefonga ulang.")
        cr.execute("DELETE FROM user_accounts WHERE telegram_id=%s AND uid=%s",
                   (telegram_id, uid))
        ok = cr.rowcount > 0
        # Aktiv qolmasa birinchisini yoqamiz
        cr.execute("""UPDATE user_accounts SET is_active=TRUE
            WHERE id=(SELECT id FROM user_accounts WHERE telegram_id=%s
                      ORDER BY account_index LIMIT 1)
              AND NOT EXISTS(SELECT 1 FROM user_accounts
                             WHERE telegram_id=%s AND is_active=TRUE)""",
            (telegram_id, telegram_id))
        c.commit(); cr.close(); c.close()
        return (ok, "🔓 Akkaunt bu telefondan uzildi." if ok else "⚠️ Topilmadi.")
    except Exception as e:
        print(f"[akkaunt] uzib: {e}")
        return (False, f"❌ {e}")
