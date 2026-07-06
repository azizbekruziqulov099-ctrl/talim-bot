"""
kitob_bazasi.py
PDF → rasm → Gemini Vision → LaTeX → DB
"""
import os, re, psycopg2, asyncio, base64, json, subprocess, tempfile

DATABASE_URL = os.getenv("DATABASE_URL","")
def db(): return psycopg2.connect(DATABASE_URL)

async def page_to_image(pdf_path: str, page_num: int) -> bytes | None:
    """PDF betni rasmga aylantiradi (pdftoppm yoki PyMuPDF)."""
    # 1. pdftoppm
    try:
        import shutil
        if shutil.which("pdftoppm"):
            tmp = tempfile.mkdtemp()
            out = os.path.join(tmp, "page")
            subprocess.run([
                "pdftoppm", "-r", "200",
                "-f", str(page_num), "-l", str(page_num), "-png",
                pdf_path, out
            ], capture_output=True, timeout=30)
            imgs = sorted([f for f in os.listdir(tmp) if f.endswith(".png")])
            if imgs:
                with open(os.path.join(tmp, imgs[0]), "rb") as f:
                    return f.read()
    except Exception as e:
        pass

    # 2. PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    except Exception as e:
        pass

    return None

async def gemini_read_pdf_page(pdf_path: str, page_num: int) -> str:
    """Gemini ga PDF betni to'g'ridan yuborib o'qitadi."""
    import aiohttp
    key = os.getenv("GEMINI_API_KEY","")
    if not key: return ""
    try:
        # Faqat o'sha betni ajratib yuborish
        from pypdf import PdfReader, PdfWriter
        import io
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        writer.add_page(reader.pages[page_num - 1])
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        pdf_b64 = base64.b64encode(buf.read()).decode()

        body = {
            "contents":[{"parts":[
                {"inline_data":{"mime_type":"application/pdf","data":pdf_b64}},
                {"text":(
                    "Bu O'zbek matematika darsligi sahifasi.\n"
                    "Barcha matnni to'liq o'qi:\n"
                    "- Har bir misol raqami yangi qatorda bo'lsin\n"
                    "- Kasrlarni: a/b yoki \\frac{a}{b} shaklida yoz\n"
                    "- Darajalarni: x^2 shaklida yoz\n"
                    "- Ildizni: sqrt(x) yoki \\sqrt{x} shaklida yoz\n"
                    "- Hech qanday izoh yozma, faqat matnni qaytar\n"
                    "- O'zbek tilida yoz"
                )}
            ]}],
            "generationConfig":{"maxOutputTokens":4000}
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=body, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    d = await r.json()
                    return d["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"gemini_pdf: {e}")
    return ""

def find_section(text: str) -> str:
    m = re.search(r'(\d+-?§\.?\s*[^\n]+)', text)
    if m: return m.group(1).strip()[:100]
    return ""

def extract_exercises(text: str) -> list:
    examples = []; cur = ""
    for line in text.split("\n"):
        line = line.strip()
        if re.match(r'^\d+[\.\)]\s', line):
            if cur: examples.append(cur.strip())
            cur = line
        elif cur and line:
            cur += " " + line
    if cur: examples.append(cur.strip())
    return [e for e in examples if len(e) > 15]

async def load_book_to_db(file_path, sinf, fan="Matematika", muallif="", progress_cb=None):
    async def p(msg):
        if progress_cb: await progress_cb(msg)

    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        total = len(reader.pages)
    except Exception as e:
        await p(f"❌ PDF o'qib bo'lmadi: {e}"); return {"book_id":0,"pages":0,"exercises":0}

    await p(f"📖 {total} bet o'qilmoqda (Gemini Vision)...")

    conn = db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO books(title,fan,sinf,muallif,total_pages)
        VALUES(%s,%s,%s,%s,%s) RETURNING id
    """, (f"{fan} {sinf}", fan, sinf, muallif, total))
    book_id = cur.fetchone()[0]; conn.commit()

    saved_p = saved_e = 0

    for i in range(total):
        page_num = i + 1
        try:
            # Gemini PDF betni to'g'ridan o'qiydi
            latex_text = await gemini_read_pdf_page(file_path, page_num)
            if not latex_text:
                # Fallback: pypdf
                from pypdf import PdfReader as PR
                r2 = PR(file_path)
                latex_text = r2.pages[i].extract_text() or ""

            section = find_section(latex_text)
            exercises = extract_exercises(latex_text)

            cur.execute("""
                INSERT INTO book_pages(book_id,page_num,section_name,full_text,exercise_count)
                VALUES(%s,%s,%s,%s,%s) ON CONFLICT(book_id,page_num)
                DO UPDATE SET full_text=EXCLUDED.full_text,section_name=EXCLUDED.section_name
            """, (book_id, page_num, section, latex_text[:8000], len(exercises)))
            saved_p += 1

            for ex in exercises:
                cur.execute("""
                    INSERT INTO book_exercises(book_id,page_num,mavzu,fan,sinf,savol)
                    VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
                """, (book_id, page_num, section or f"Bet {page_num}", fan, sinf, ex[:1000]))
                saved_e += 1

        except Exception as e:
            print(f"Bet {page_num}: {e}")

        if page_num % 10 == 0 or page_num == total:
            conn.commit()
            pct = round(page_num*100/total)
            bar = "█"*(pct//10) + "░"*(10-pct//10)
            await p(f"{bar} {pct}%\n📄 {page_num}/{total} bet | 📐 {saved_e} misol")
        await asyncio.sleep(0.1)

    conn.commit(); cur.close(); conn.close()
    await p(f"✅ Saqlandi!\n📄 {saved_p} bet | 📐 {saved_e} misol\n🔑 Book ID: {book_id}")
    return {"book_id": book_id, "pages": saved_p, "exercises": saved_e}

def search_book(query, sinf=None, fan=None, limit=10):
    try:
        conn = db(); cur = conn.cursor()
        params = [f"%{query}%", f"%{query}%"]
        sf = "AND b.sinf=%s" if sinf else ""
        ff = "AND b.fan=%s" if fan else ""
        if sinf: params.append(sinf)
        if fan:  params.append(fan)
        params.append(limit)
        cur.execute(f"""
            SELECT p.page_num,p.section_name,p.full_text,b.id,b.title
            FROM book_pages p JOIN books b ON b.id=p.book_id
            WHERE (p.full_text ILIKE %s OR p.section_name ILIKE %s) {sf} {ff}
            ORDER BY p.page_num LIMIT %s
        """, params)
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"page":r[0],"section":r[1],"text":r[2][:400],"book_id":r[3],"title":r[4]} for r in rows]
    except: return []

def get_page(book_id, page_num):
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT page_num,section_name,full_text FROM book_pages WHERE book_id=%s AND page_num=%s",
                   (book_id, page_num))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return {"page":row[0],"section":row[1],"text":row[2]}
    except: pass
    return {}

def get_exercises(book_id, page_num=None, mavzu=None, limit=20):
    try:
        conn = db(); cur = conn.cursor()
        if page_num:
            cur.execute("SELECT savol FROM book_exercises WHERE book_id=%s AND page_num=%s LIMIT %s",
                       (book_id, page_num, limit))
        elif mavzu:
            cur.execute("SELECT savol FROM book_exercises WHERE book_id=%s AND mavzu ILIKE %s LIMIT %s",
                       (book_id, f"%{mavzu}%", limit))
        else:
            cur.execute("SELECT savol FROM book_exercises WHERE book_id=%s LIMIT %s",(book_id,limit))
        rows = cur.fetchall(); cur.close(); conn.close()
        return [r[0] for r in rows]
    except: return []

def get_books(sinf=None):
    try:
        conn = db(); cur = conn.cursor()
        if sinf:
            cur.execute("SELECT id,title,sinf,fan,total_pages FROM books WHERE sinf=%s ORDER BY id",(sinf,))
        else:
            cur.execute("SELECT id,title,sinf,fan,total_pages FROM books ORDER BY id")
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"id":r[0],"title":r[1],"sinf":r[2],"fan":r[3],"pages":r[4]} for r in rows]
    except: return []

async def render_page_as_image(page_text, page_num):
    """Matndan matplotlib rasm."""
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        mpl.rcParams['text.usetex'] = False
        import io

        # LaTeX belgilarini oddiy matn sifatida ko'rsat
        def safe(t):
            return (t.replace('\\','\\\\')
                     .replace('$','\\$')
                     .replace('^','\\^{}')
                     .replace('_','\\_')
                     .replace('%','\\%')
                     .replace('&','\\&'))

        lines = [l.strip() for l in page_text.split('\n') if l.strip()][:35]

        fig, ax = plt.subplots(figsize=(8, 11))
        ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')
        fig.patch.set_facecolor('white')

        ax.text(0.5, 0.98, f"Bet {page_num}", ha='center', va='top',
                fontsize=13, fontweight='bold', fontfamily='DejaVu Sans')

        y = 0.93
        for line in lines:
            if y < 0.02: break
            w = 'bold' if re.match(r'^\d+-?§', line) else 'normal'
            # LaTeX escaping o'rniga oddiy text renderer
            try:
                ax.text(0.03, y, line[:90], ha='left', va='top',
                       fontsize=9, fontweight=w, color='#111',
                       fontfamily='monospace',
                       transform=ax.transAxes)
            except: pass
            y -= 0.028

        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=130, bbox_inches='tight', facecolor='white')
        plt.close()
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"render: {e}")
        return None
