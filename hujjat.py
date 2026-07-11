"""hujjat.py — Rasmdan matn o'qib (OCR), chiroyli PDF yoki Word hujjat yaratadi.

OCR — Gemini Vision API orqali (GEMINI_API_KEY talab qilinadi).
Chiqish — PDF (fpdf2) yoki DOCX (python-docx).

O'zbek harflari (o', g' kabi) uchun Unicode shrift kerak — buni bir nechta
manbadan (matplotlib bundle, tizim yo'llari) qidirib topamiz, birortasi
topilmasa oddiy shriftga tushamiz (maxsus harflar noto'g'ri chiqishi mumkin,
lekin dastur qulamaydi).
"""
import os
import json
import base64
import urllib.request
import urllib.error


# ═══════════════ 1. RASMDAN MATN O'QISH (OCR) ═══════════════

def matn_ol_rasmdan(rasm_yol):
    """Gemini Vision orqali rasmdagi matnni o'qiydi, tuzilmasini
    (paragraflar) saqlab qaytaradi. (matn, xato)"""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return (None, "GEMINI_API_KEY sozlanmagan (Railway muhitida yo'q)")

    try:
        with open(rasm_yol, "rb") as f:
            rasm_bytes = f.read()
        rasm_b64 = base64.b64encode(rasm_bytes).decode("utf-8")

        ext = rasm_yol.lower().rsplit(".", 1)[-1]
        mime = {"png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")

        prompt = (
            "Bu rasmdagi barcha matnni AYNAN, so'zma-so'z o'qib yoz. "
            "Paragraflar orasida bo'sh qator qoldir. Sarlavha bo'lsa "
            "birinchi qatorda alohida yoz. Rasmda yo'q narsa qo'shma, "
            "izoh-tushuntirish yozma, FAQAT rasmdagi matnni qaytar."
        )

        url = ("https://generativelanguage.googleapis.com/v1beta/"
               f"models/gemini-2.0-flash:generateContent?key={api_key}")
        body = json.dumps({
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime, "data": rasm_b64}}
                ]
            }]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            natija = json.loads(resp.read().decode("utf-8"))
        matn = natija["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not matn:
            return (None, "Rasmda matn topilmadi")
        return (matn, None)
    except urllib.error.HTTPError as e:
        return (None, f"Gemini xato ({e.code}): {e.read()[:200]}")
    except Exception as e:
        return (None, str(e)[:300])


# ═══════════════ 2. UNICODE SHRIFT QIDIRISH ═══════════════

_SHRIFT_KESH = None

def _unicode_shrift_topish():
    """O'zbek harflarini (o', g') to'g'ri ko'rsatadigan shrift qidiradi.
    Bir necha manbadan — birortasi ishlasa bo'ldi. Natija keshlanadi."""
    global _SHRIFT_KESH
    if _SHRIFT_KESH is not None:
        return _SHRIFT_KESH or None

    nomzodlar = []
    try:
        import matplotlib
        nomzodlar.append(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf"))
    except Exception:
        pass
    nomzodlar += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]
    for yol in nomzodlar:
        if os.path.exists(yol):
            _SHRIFT_KESH = yol
            return yol
    _SHRIFT_KESH = ""
    return None


# ═══════════════ 3. HUJJAT YARATISH ═══════════════

def matndan_pdf(matn, chiqish_yol, sarlavha=None):
    """Matndan chiroyli formatlangan PDF yaratadi. (muvaffaqiyat, xato)"""
    from fpdf import FPDF
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        shrift_yol = _unicode_shrift_topish()
        if shrift_yol:
            pdf.add_font("Unicode", "", shrift_yol)
            asosiy_shrift = "Unicode"
        else:
            asosiy_shrift = "Helvetica"

        # MUHIM: multi_cell() dan keyin kursor CHAP CHEKKAGA qaytmaydi —
        # o'ng chekkada qolib ketadi. Har chaqiruvdan oldin qo'lda
        # qaytarish shart, aks holda "joy yo'q" xatosi chiqadi.
        if sarlavha:
            pdf.set_font(asosiy_shrift, size=16)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 10, sarlavha)
            pdf.set_x(pdf.l_margin)
            pdf.ln(4)

        pdf.set_font(asosiy_shrift, size=12)
        for band in matn.split("\n"):
            pdf.set_x(pdf.l_margin)
            if band.strip():
                pdf.multi_cell(0, 8, band)
            else:
                pdf.ln(4)

        pdf.output(chiqish_yol)
        if not os.path.exists(chiqish_yol):
            return (False, "PDF fayli yaratilmadi")
        return (True, None)
    except Exception as e:
        return (False, str(e)[:300])


def matndan_docx(matn, chiqish_yol, sarlavha=None):
    """Matndan Word hujjat yaratadi. (muvaffaqiyat, xato)"""
    from docx import Document
    try:
        doc = Document()
        if sarlavha:
            doc.add_heading(sarlavha, level=1)
        for band in matn.split("\n"):
            if band.strip():
                doc.add_paragraph(band)
        doc.save(chiqish_yol)
        if not os.path.exists(chiqish_yol):
            return (False, "Word fayli yaratilmadi")
        return (True, None)
    except Exception as e:
        return (False, str(e)[:300])
