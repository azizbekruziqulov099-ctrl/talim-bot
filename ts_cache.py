"""ts_cache.py — Tanlangan mavzu topic kodlarini saqlaydi.

Muammo: tugmada "40 ta" yozilgan, lekin bosilganda boshqa testlar chiqardi,
chunki topic_code lar qaytadan hisoblanardi.

Yechim: tugma yasalganda topic_code lar DB ga saqlanadi.
Tugma bosilganda AYNAN o'shalar o'qiladi. Hech qanday taxmin yo'q.
"""
import os, psycopg2

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _db():
    return psycopg2.connect(DATABASE_URL)


def _jadval(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS ts_sel(
        id SERIAL PRIMARY KEY,
        topic_codes TEXT[] NOT NULL,
        mavzu_name TEXT,
        grade TEXT,
        subject TEXT,
        test_soni INT DEFAULT 0,
        yaratilgan TIMESTAMP DEFAULT NOW()
    )""")


def saqla(topic_codes, mavzu_name, grade, subject, test_soni=0):
    """Topic kodlarini saqlaydi, id qaytaradi (callback_data uchun)."""
    if not topic_codes:
        return None
    try:
        c = _db(); cr = c.cursor()
        _jadval(cr)
        cr.execute("""INSERT INTO ts_sel(topic_codes, mavzu_name, grade, subject, test_soni)
            VALUES(%s,%s,%s,%s,%s) RETURNING id""",
            (list(topic_codes), mavzu_name, str(grade or ""), subject, test_soni))
        sid = cr.fetchone()[0]
        c.commit(); cr.close(); c.close()
        return sid
    except Exception as e:
        print(f"[ts_cache] saqla: {e}")
        return None


def ol(sel_id):
    """Saqlangan tanlovni qaytaradi yoki None."""
    try:
        c = _db(); cr = c.cursor()
        _jadval(cr); c.commit()
        cr.execute("""SELECT topic_codes, mavzu_name, grade, subject, test_soni
            FROM ts_sel WHERE id=%s""", (int(sel_id),))
        r = cr.fetchone(); cr.close(); c.close()
        if not r:
            return None
        return {"topic_codes": list(r[0] or []), "mavzu_name": r[1],
                "grade": r[2], "subject": r[3], "test_soni": r[4]}
    except Exception as e:
        print(f"[ts_cache] ol: {e}")
        return None


def tozala(kun=7):
    """Eski yozuvlarni o'chiradi."""
    try:
        c = _db(); cr = c.cursor()
        _jadval(cr)
        cr.execute("DELETE FROM ts_sel WHERE yaratilgan < NOW() - INTERVAL '%s days'", (kun,))
        n = cr.rowcount
        c.commit(); cr.close(); c.close()
        return n
    except Exception as e:
        print(f"[ts_cache] tozala: {e}")
        return 0
