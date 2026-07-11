"""video_admin.py — Mavzularga video biriktirish (Instagram/YouTube havolasidan).

Rasm tizimiga o'xshab ishlaydi:
  1. Admin mavzuni tanlaydi
  2. Instagram/YouTube havolasini yuboradi
  3. Bot yt-dlp orqali yuklaydi, Telegram'ga yuklaydi (file_id oladi)
  4. file_id saqlanadi — ENDI QAYTA YUKLAMAYDI, doim shu file_id dan foydalanadi
"""
import os
import re
import subprocess
import psycopg2
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

DATABASE_URL = os.getenv("DATABASE_URL", "")

VIDEO_LINK_REGEX = re.compile(
    r'https?://(www\.)?(instagram\.com|youtu\.be|youtube\.com|tiktok\.com)/\S+', re.I)

MAX_VAQT_SONIYA = 180      # yt-dlp uchun maksimal kutish
MAX_HAJM_MB = "48M"        # Telegram bot fayl limiti ~50MB


def db():
    return psycopg2.connect(DATABASE_URL)


def jadval():
    try:
        c = db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS videolar(
            id SERIAL PRIMARY KEY,
            kod TEXT UNIQUE,
            file_id TEXT,
            manba_link TEXT,
            yuklagan BIGINT,
            yaratildi TIMESTAMP DEFAULT NOW()
        )""")
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[video] jadval: {e}")
        return False


# ═══════════════ LINK ANIQLASH ═══════════════

def link_tanidimi(matn):
    """Xabar ichida video havolasi bormi? Bo'lsa havolani qaytaradi."""
    if not matn:
        return None
    m = VIDEO_LINK_REGEX.search(matn)
    return m.group(0) if m else None


# ═══════════════ SAQLASH / OLISH ═══════════════

def video_bormi(kod):
    """Bu kod uchun video allaqachon yuklanganmi? file_id qaytaradi yoki None."""
    try:
        c = db(); cr = c.cursor()
        cr.execute("SELECT file_id FROM videolar WHERE kod=%s", (kod,))
        r = cr.fetchone(); cr.close(); c.close()
        return r[0] if r and r[0] else None
    except Exception as e:
        print(f"[video] bormi: {e}")
        return None


def video_saqla(kod, file_id, manba_link, yuklagan):
    jadval()
    try:
        c = db(); cr = c.cursor()
        cr.execute("""INSERT INTO videolar(kod, file_id, manba_link, yuklagan)
            VALUES(%s,%s,%s,%s)
            ON CONFLICT(kod) DO UPDATE SET file_id=EXCLUDED.file_id,
                manba_link=EXCLUDED.manba_link, yuklagan=EXCLUDED.yuklagan""",
            (kod, file_id, manba_link, yuklagan))
        c.commit(); cr.close(); c.close()
        return True
    except Exception as e:
        print(f"[video] saqla: {e}")
        return False


def video_ochir(kod):
    try:
        c = db(); cr = c.cursor()
        cr.execute("DELETE FROM videolar WHERE kod=%s", (kod,))
        n = cr.rowcount
        c.commit(); cr.close(); c.close()
        return n > 0
    except Exception as e:
        print(f"[video] ochir: {e}")
        return False


# ═══════════════ ODDIY YUKLAB OLISH (mavzuga bog'liq emas) ═══════════════
# Havolaning o'zi kalit — bir marta yuklangan link qayta yuklanmaydi.

def link_keshi_jadval():
    try:
        c = db(); cr = c.cursor()
        cr.execute("""CREATE TABLE IF NOT EXISTS video_link_kesh(
            link TEXT PRIMARY KEY,
            file_id TEXT,
            yuklagan BIGINT,
            yaratildi TIMESTAMP DEFAULT NOW()
        )""")
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[video] link_keshi_jadval: {e}")


def link_keshi_bormi(link):
    """Bu havola avval yuklanganmi? file_id qaytaradi yoki None."""
    link_keshi_jadval()
    try:
        c = db(); cr = c.cursor()
        cr.execute("SELECT file_id FROM video_link_kesh WHERE link=%s", (link,))
        r = cr.fetchone(); cr.close(); c.close()
        return r[0] if r and r[0] else None
    except Exception as e:
        print(f"[video] link_keshi_bormi: {e}")
        return None


def link_keshiga_saqla(link, file_id, yuklagan):
    try:
        c = db(); cr = c.cursor()
        cr.execute("""INSERT INTO video_link_kesh(link, file_id, yuklagan)
            VALUES(%s,%s,%s) ON CONFLICT(link) DO UPDATE
            SET file_id=EXCLUDED.file_id""", (link, file_id, yuklagan))
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[video] link_keshiga_saqla: {e}")


# ═══════════════ YUKLASH (yt-dlp) ═══════════════

def yukla(link, chiqish_yol):
    """Havoladan videoni diskka yuklaydi. (muvaffaqiyat, xato_matni)"""
    try:
        natija = subprocess.run(
            ["yt-dlp", "-f", "mp4/bestvideo+bestaudio/best",
             "--recode-video", "mp4",
             "-o", chiqish_yol, "--no-playlist",
             "--max-filesize", MAX_HAJM_MB, link],
            capture_output=True, text=True, timeout=MAX_VAQT_SONIYA
        )
        if natija.returncode != 0:
            xato = (natija.stderr or "").strip()
            # Eng foydali qatorni ajratib olamiz
            qatorlar = [q for q in xato.split("\n") if q.strip()]
            qisqa = qatorlar[-1] if qatorlar else "Noma'lum xato"
            return (False, qisqa[:300])
        if not os.path.exists(chiqish_yol) or os.path.getsize(chiqish_yol) == 0:
            return (False, "Video fayli yaratilmadi (bo'sh yoki mavjud emas)")
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, f"⏱ {MAX_VAQT_SONIYA} soniyada yuklanmadi (juda uzun/sekin)")
    except FileNotFoundError:
        return (False, "❌ yt-dlp o'rnatilmagan (requirements.txt ga qo'shing)")
    except Exception as e:
        return (False, str(e)[:300])
