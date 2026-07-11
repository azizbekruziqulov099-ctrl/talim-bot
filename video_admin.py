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
            id SERIAL PRIMARY KEY,
            link TEXT NOT NULL,
            turi TEXT NOT NULL DEFAULT 'video',
            file_id TEXT,
            yuklagan BIGINT,
            yaratildi TIMESTAMP DEFAULT NOW()
        )""")
        c.commit()
        # Eski sxema (link PRIMARY KEY, turi ustunisiz) bo'lsa — moslashtiramiz
        try:
            cr.execute("ALTER TABLE video_link_kesh ADD COLUMN IF NOT EXISTS turi TEXT NOT NULL DEFAULT 'video'")
            c.commit()
        except Exception:
            c.rollback()
        try:
            cr.execute("ALTER TABLE video_link_kesh DROP CONSTRAINT IF EXISTS video_link_kesh_pkey")
            c.commit()
        except Exception:
            c.rollback()
        try:
            cr.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_vlk_uniq
                ON video_link_kesh(link, turi)""")
            c.commit()
        except Exception:
            c.rollback()
        cr.close(); c.close()
    except Exception as e:
        print(f"[video] link_keshi_jadval: {e}")


def link_keshi_bormi(link, turi="video"):
    """Bu havola (shu turda) avval yuklanganmi? file_id qaytaradi yoki None."""
    link_keshi_jadval()
    try:
        c = db(); cr = c.cursor()
        cr.execute("SELECT file_id FROM video_link_kesh WHERE link=%s AND turi=%s",
                   (link, turi))
        r = cr.fetchone(); cr.close(); c.close()
        return r[0] if r and r[0] else None
    except Exception as e:
        print(f"[video] link_keshi_bormi: {e}")
        return None


def link_keshiga_saqla(link, file_id, yuklagan, turi="video"):
    try:
        c = db(); cr = c.cursor()
        cr.execute("""INSERT INTO video_link_kesh(link, turi, file_id, yuklagan)
            VALUES(%s,%s,%s,%s) ON CONFLICT(link, turi) DO UPDATE
            SET file_id=EXCLUDED.file_id""", (link, turi, file_id, yuklagan))
        c.commit(); cr.close(); c.close()
    except Exception as e:
        print(f"[video] link_keshiga_saqla: {e}")



# ═══════════════ YUKLASH (yt-dlp) ═══════════════

def yukla(link, chiqish_yol, faqat_audio=False):
    """Havoladan videoni (yoki faqat audiosini) diskka yuklaydi.
    (muvaffaqiyat, xato_matni)"""
    try:
        if faqat_audio:
            buyruq = ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                      "-o", chiqish_yol, "--no-playlist",
                      "--max-filesize", MAX_HAJM_MB, link]
        else:
            buyruq = ["yt-dlp", "-f", "mp4/bestvideo+bestaudio/best",
                      "--recode-video", "mp4",
                      "-o", chiqish_yol, "--no-playlist",
                      "--max-filesize", MAX_HAJM_MB, link]
        natija = subprocess.run(buyruq, capture_output=True, text=True, timeout=MAX_VAQT_SONIYA)
        if natija.returncode != 0:
            xato = (natija.stderr or "").strip()
            qatorlar = [q for q in xato.split("\n") if q.strip()]
            qisqa = qatorlar[-1] if qatorlar else "Noma'lum xato"
            return (False, qisqa[:300])
        # --audio-format mp3 fayl kengaytmasini o'zi almashtirishi mumkin —
        # chiqish_yol aynan mos kelmasa ham, papkada mp3 borligini tekshiramiz
        if faqat_audio and not os.path.exists(chiqish_yol):
            papka = os.path.dirname(chiqish_yol) or "."
            nomsiz = os.path.splitext(os.path.basename(chiqish_yol))[0]
            for f in os.listdir(papka):
                if f.startswith(nomsiz) and f.endswith(".mp3"):
                    chiqish_yol_topilgan = os.path.join(papka, f)
                    if os.path.getsize(chiqish_yol_topilgan) > 0:
                        os.replace(chiqish_yol_topilgan, chiqish_yol)
                        break
        if not os.path.exists(chiqish_yol) or os.path.getsize(chiqish_yol) == 0:
            return (False, "Fayl yaratilmadi (bo'sh yoki mavjud emas)")
        return (True, None)
    except subprocess.TimeoutExpired:
        return (False, f"⏱ {MAX_VAQT_SONIYA} soniyada yuklanmadi (juda uzun/sekin)")
    except FileNotFoundError:
        return (False, "❌ yt-dlp o'rnatilmagan (requirements.txt ga qo'shing)")
    except Exception as e:
        return (False, str(e)[:300])
