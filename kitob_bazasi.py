"""
kitob_bazasi.py — Kitob yuklash va tahlil tizimi
Digital PDF, skanerlangan PDF, Word — hammasi qo'llab-quvvatlanadi
"""
import os, re, asyncio, psycopg2
from io import BytesIO
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")

# ══════════════════════════════════════
# LaTeX konvertori
# ══════════════════════════════════════
UNICODE_TO_LATEX = {
    "½": r"\frac{1}{2}", "⅓": r"\frac{1}{3}", "¼": r"\frac{1}{4}",
    "¾": r"\frac{3}{4}", "√": r"\sqrt{}", "∛": r"\sqrt[3]{}",
    "²": "^{2}", "³": "^{3}", "⁴": "^{4}", "⁻¹": "^{-1}",
    "₁": "_{1}", "₂": "_{2}", "₃": "_{3}", "₀": "_{0}",
    "∑": r"\sum", "∫": r"\int", "∏": r"\prod",
    "π": r"\pi", "∞": r"\infty", "∅": r"\emptyset",
    "≤": r"\leq", "≥": r"\geq", "≠": r"\neq",
    "≈": r"\approx", "≡": r"\equiv", "∝": r"\propto",
    "×": r"\times", "÷": r"\div", "±": r"\pm",
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma",
    "δ": r"\delta", "θ": r"\theta", "λ": r"\lambda",
    "μ": r"\mu", "σ": r"\sigma", "φ": r"\phi",
    "→": r"\rightarrow", "←": r"\leftarrow",
    "↑": r"\uparrow", "↓": r"\downarrow",
    "∈": r"\in", "∉": r"\notin", "⊂": r"\subset",
    "∪": r"\cup", "∩": r"\cap",
}

def text_to_latex(text: str) -> Optional[str]:
    """Matndan LaTeX formula yasaydi."""
    if not text: return None
    result = text
    for uni, latex in UNICODE_TO_LATEX.items():
        result = result.replace(uni, latex)
    # Oddiy kasr: a/b → \frac{a}{b}
    result = re.sub(r'(\w+)\s*/\s*(\w+)', r'\\frac{\1}{\2}', result)
    # Daraja: x^2 → x^{2}
    result = re.sub(r'(\w)\^(\w+)', r'\1^{\2}', result)
    # O'zgarmagan bo'lsa None qayt
    return f"${result}$" if result != text else None

def is_formula_line(line: str) -> bool:
    """Bu qator formula ekanligini aniqlaydi."""
    formula_chars = set("=+-×÷²³√∑∫πα≤≥≠½¼¾∞")
    symbols = sum(1 for c in line if c in formula_chars)
    total   = len(line.strip())
    if total == 0: return False
    # 30%+ maxsus belgi bo'lsa yoki = bor bo'lsa
    return symbols / total > 0.3 or ('=' in line and len(line) < 80)

def is_header_line(line: str, page_num: int) -> bool:
    """Sarlavha qatorini aniqlaydi."""
    line = line.strip()
    if not line: return False
    # 1.2.3 yoki § yoki KATTA HARF
    if re.match(r'^(\d+\.)+\s+\w', line): return True
    if re.match(r'^§\s*\d+', line): return True
    if re.match(r'^[IVX]+\.\s+\w', line): return True  # Roman raqam
    if len(line) < 60 and line.isupper(): return True
    if len(line) < 50 and line[0].isupper() and line.endswith(":"): return True
    return False

# ══════════════════════════════════════
# PDF o'quvchi
# ══════════════════════════════════════
async def extract_pdf_digital(pdf_bytes: bytes) -> list:
    """Digital PDF dan matn va rasmlarni ajratadi."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return []

    doc    = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages  = []

    for page_num, page in enumerate(doc, 1):
        page_data = {
            "page":    page_num,
            "text":    "",
            "blocks":  [],
            "images":  [],
            "is_scan": False,
        }
        # Matn ajratish
        text = page.get_text("text")
        if len(text.strip()) < 50:
            page_data["is_scan"] = True
        else:
            page_data["text"] = text
            blocks = []
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text_block, block_no, block_type = block
                if block_type == 0 and text_block.strip():
                    blocks.append({
                        "text":     text_block.strip(),
                        "is_formula": is_formula_line(text_block),
                        "is_header":  is_header_line(text_block, page_num),
                        "y_pos":    y0,
                    })
            page_data["blocks"] = sorted(blocks, key=lambda b: b["y_pos"])

        # Rasmlar
        for img_idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_img = doc.extract_image(xref)
            if base_img and base_img.get("image"):
                page_data["images"].append({
                    "page":    page_num,
                    "idx":     img_idx,
                    "ext":     base_img.get("ext","png"),
                    "data":    base_img["image"],
                    "size":    len(base_img["image"]),
                })

        pages.append(page_data)
        # Har 50 betda yield — bot xabar yuborishi uchun
        if page_num % 50 == 0:
            await asyncio.sleep(0)  # Event loop ga imkon

    doc.close()
    return pages

async def extract_pdf_ocr(pdf_bytes: bytes, lang: str = "uzb+eng") -> list:
    """Skanerlangan PDF dan OCR bilan matn ajratadi."""
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError:
        return []

    doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []

    for page_num, page in enumerate(doc, 1):
        # Sahifani rasmga aylantirish (300 DPI)
        mat  = fitz.Matrix(300/72, 300/72)
        pix  = page.get_pixmap(matrix=mat)
        img  = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # OCR
        text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        pages.append({
            "page":    page_num,
            "text":    text,
            "blocks":  [],
            "images":  [],
            "is_scan": True,
        })
        await asyncio.sleep(0)

    doc.close()
    return pages

# ══════════════════════════════════════
# Matnni bo'limlarga ajratish
# ══════════════════════════════════════
def split_into_sections(pages: list) -> list:
    """Sahifalardan bo'limlar yasaydi."""
    sections    = []
    cur_section = {"title": "Kirish", "from_page": 1, "chunks": [], "images": []}

    for page_data in pages:
        page_num = page_data["page"]
        blocks   = page_data.get("blocks") or []
        images   = page_data.get("images") or []
        cur_section["images"].extend(images)

        if page_data.get("is_scan") or not blocks:
            # OCR matn — paragraf bo'yicha ajrat
            text = page_data.get("text","")
            for para in text.split("\n\n"):
                para = para.strip()
                if len(para) > 30:
                    chunk_type = "formula" if is_formula_line(para) else "matn"
                    latex = text_to_latex(para) if chunk_type == "formula" else None
                    cur_section["chunks"].append({
                        "matn":      para,
                        "latex":     latex,
                        "type":      chunk_type,
                        "page":      page_num,
                    })
            continue

        for block in blocks:
            txt = block["text"].strip()
            if not txt: continue

            if block["is_header"] and len(txt) < 100:
                # Yangi bo'lim boshlandi
                if cur_section["chunks"] or cur_section["images"]:
                    cur_section["to_page"] = page_num
                    sections.append(cur_section)
                cur_section = {
                    "title":     txt,
                    "from_page": page_num,
                    "chunks":    [],
                    "images":    [],
                }
            else:
                chunk_type = "formula" if block["is_formula"] else "matn"
                latex = text_to_latex(txt) if chunk_type == "formula" else None
                cur_section["chunks"].append({
                    "matn":  txt,
                    "latex": latex,
                    "type":  chunk_type,
                    "page":  page_num,
                })

    if cur_section["chunks"] or cur_section["images"]:
        cur_section["to_page"] = pages[-1]["page"] if pages else 1
        sections.append(cur_section)

    return sections

# ══════════════════════════════════════
# DB ga saqlash
# ══════════════════════════════════════
def save_book_to_db(title, fan, sinf, muallif, file_id, sections):
    """Kitobni DB ga saqlaydi."""
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    # books jadvali
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title TEXT, fan TEXT, sinf TEXT,
            muallif TEXT, file_id TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS book_sections (
            id SERIAL PRIMARY KEY,
            book_id INT, title TEXT,
            from_page INT, to_page INT, tartib INT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS book_chunks (
            id SERIAL PRIMARY KEY,
            section_id INT, book_id INT,
            matn TEXT, latex TEXT,
            chunk_type TEXT, page_num INT,
            keywords TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS book_images (
            id SERIAL PRIMARY KEY,
            section_id INT, book_id INT,
            file_id TEXT, page_num INT,
            caption TEXT, ext TEXT
        )
    """)

    cur.execute(
        "INSERT INTO books(title,fan,sinf,muallif,file_id) VALUES(%s,%s,%s,%s,%s) RETURNING id",
        (title, fan, sinf, muallif, file_id)
    )
    book_id = cur.fetchone()[0]

    for idx, sec in enumerate(sections):
        cur.execute(
            "INSERT INTO book_sections(book_id,title,from_page,to_page,tartib) VALUES(%s,%s,%s,%s,%s) RETURNING id",
            (book_id, sec["title"], sec.get("from_page",1), sec.get("to_page",1), idx)
        )
        sec_id = cur.fetchone()[0]

        for chunk in sec["chunks"]:
            # Kalit so'zlar (qidiruv uchun)
            words   = re.findall(r'\b\w{4,}\b', chunk["matn"].lower())
            keywords = " ".join(set(words[:20]))
            cur.execute(
                """INSERT INTO book_chunks(section_id,book_id,matn,latex,chunk_type,page_num,keywords)
                   VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                (sec_id, book_id, chunk["matn"], chunk.get("latex"),
                 chunk["type"], chunk["page"], keywords)
            )

    conn.commit()
    cur.close()
    conn.close()
    return book_id

# ══════════════════════════════════════
# ASOSIY FUNKSIYA — BOT dan chaqiriladi
# ══════════════════════════════════════
async def process_book(
    pdf_bytes: bytes,
    title: str,
    fan: str,
    sinf: str,
    muallif: str,
    file_id: str,
    progress_cb=None,  # async func(text) — progress xabari
) -> dict:
    """
    PDF ni to'liq qayta ishlaydi.
    progress_cb har bosqichda chaqiriladi.
    """
    async def p(msg):
        if progress_cb:
            await progress_cb(msg)

    await p("📖 PDF tahlil qilinmoqda...")

    # 1) Digital yoki skan aniqlash
    is_scanned = False
    try:
        import fitz
        doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
        n    = len(doc)
        text = doc[0].get_text("text") if n > 0 else ""
        is_scanned = len(text.strip()) < 50
        doc.close()
    except: pass

    await p(f"📄 Jami {n} bet | Tur: {'Skanerlangan 📷' if is_scanned else 'Digital ✅'}")

    # 2) Matn ajratish
    if is_scanned:
        await p("🔍 OCR boshlanmoqda (sekin bo'lishi mumkin)...")
        pages = await extract_pdf_ocr(pdf_bytes)
    else:
        pages = await extract_pdf_digital(pdf_bytes)

    await p(f"✅ {len(pages)} bet o'qildi | Bo'limlarga ajratilmoqda...")

    # 3) Bo'limlarga ajratish
    sections = split_into_sections(pages)
    await p(f"📚 {len(sections)} ta bo'lim topildi | DB ga saqlanmoqda...")

    # 4) DB ga saqlash
    book_id = save_book_to_db(title, fan, sinf, muallif, file_id, sections)

    # Statistika
    total_chunks = sum(len(s["chunks"]) for s in sections)
    total_imgs   = sum(len(s["images"]) for s in sections)
    formulas     = sum(1 for s in sections for c in s["chunks"] if c["type"]=="formula")

    await p(
        f"✅ Kitob saqlandi!\n"
        f"📚 {len(sections)} ta bo'lim\n"
        f"📝 {total_chunks} ta matn parchalari\n"
        f"🔢 {formulas} ta formula (LaTeX)\n"
        f"🖼 {total_imgs} ta rasm\n"
        f"🔑 Book ID: {book_id}"
    )

    return {
        "book_id":  book_id,
        "sections": len(sections),
        "chunks":   total_chunks,
        "formulas": formulas,
        "images":   total_imgs,
    }

# ══════════════════════════════════════
# QIDIRISH
# ══════════════════════════════════════
def search_book(query: str, fan: str = None, sinf: str = None, limit: int = 5) -> list:
    """Bilim bazasidan qidiradi."""
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    words   = re.findall(r'\b\w{3,}\b', query.lower())
    like_q  = " OR ".join(["bc.keywords LIKE %s"] * len(words))
    params  = [f"%{w}%" for w in words]
    fan_f   = "AND b.fan=%s" if fan else ""
    sinf_f  = "AND b.sinf=%s" if sinf else ""
    if fan:  params.append(fan)
    if sinf: params.append(sinf)
    params.append(limit)

    cur.execute(f"""
        SELECT bc.matn, bc.latex, bc.chunk_type, bc.page_num,
               bs.title as section, b.title as book, b.fan, b.sinf
        FROM book_chunks bc
        JOIN book_sections bs ON bs.id = bc.section_id
        JOIN books b ON b.id = bc.book_id
        WHERE ({like_q}) {fan_f} {sinf_f}
        ORDER BY bc.page_num
        LIMIT %s
    """, params)

    results = cur.fetchall()
    cur.close(); conn.close()
    return [
        {
            "matn":    r[0], "latex":   r[1],
            "type":    r[2], "page":    r[3],
            "section": r[4], "book":    r[5],
            "fan":     r[6], "sinf":    r[7],
        }
        for r in results
    ]
