"""
kitob_bazasi.py
PDF (kirill) → lotin → DB
Gemini/GPT kerak emas
"""
import os, re, psycopg2, asyncio

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

DATABASE_URL = os.getenv("DATABASE_URL","")
def db(): return psycopg2.connect(DATABASE_URL)

# ══ 1. KIRILL → LOTIN ══
CYRL_TO_LAT = {
    'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ё':'Yo',
    'Ж':'J','З':'Z','И':'I','Й':'Y','К':'K','Л':'L','М':'M',
    'Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U',
    'Ф':'F','Х':'X','Ц':'Ts','Ч':'Ch','Ш':'Sh','Щ':'Sh',
    'Ъ':"'",'Ь':'','Э':'E','Ю':'Yu','Я':'Ya',
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo',
    'ж':'j','з':'z','и':'i','й':'y','к':'k','л':'l','м':'m',
    'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u',
    'ф':'f','х':'x','ц':'ts','ч':'ch','ш':'sh','щ':'sh',
    'ъ':"'",'ь':'','э':'e','ю':'yu','я':'ya',
    'Ў':"O'",'ў':"o'",'Қ':'Q','қ':'q','Ғ':"G'",'ғ':"g'",
    'Ҳ':'H','ҳ':'h','Ҷ':'J','ҷ':'j',
}

def kyr_to_lat(text: str) -> str:
    result = ""; i = 0
    while i < len(text):
        two = text[i:i+2]
        if two in CYRL_TO_LAT:
            result += CYRL_TO_LAT[two]; i += 2
        elif text[i] in CYRL_TO_LAT:
            result += CYRL_TO_LAT[text[i]]; i += 1
        else:
            result += text[i]; i += 1
    return result

# ══ 2. MISOL/SAVOL AJRATISH ══
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

def find_section(text: str) -> str:
    m = re.search(r'(\d+-?§\.?\s*[^\n]+)', text)
    if m: return kyr_to_lat(m.group(1).strip()[:100])
    m = re.search(r'(\d+[\-–]\s*(?:mavzu|dars|bo\'lim)[^\n]*)', text, re.I)
    if m: return m.group(1).strip()[:100]
    return ""

# ══ 3. DB GA YUKLASH ══
async def load_book_to_db(file_path, sinf, fan="Matematika", muallif="", progress_cb=None):
    async def p(msg):
        if progress_cb: await progress_cb(msg)

    if PdfReader is None:
        await p("❌ pypdf kutubxonasi o'rnatilmagan!")
        return {"book_id":0,"pages":0,"exercises":0}

    reader = PdfReader(file_path)
    total = len(reader.pages)
    await p(f"📖 {total} bet o'qilmoqda...")

    conn = db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO books(title,fan,sinf,muallif,total_pages)
        VALUES(%s,%s,%s,%s,%s) RETURNING id
    """, (f"{fan} {sinf}-sinf", fan, sinf, muallif, total))
    book_id = cur.fetchone()[0]; conn.commit()

    saved_p = 0; saved_e = 0

    for i in range(total):
        try:
            raw = reader.pages[i].extract_text() or ""
        except: raw = ""
        if not raw.strip(): continue

        lat = kyr_to_lat(raw)
        section = find_section(raw)
        exercises = extract_exercises(lat)

        cur.execute("""
            INSERT INTO book_pages(book_id,page_num,section_name,full_text,exercise_count)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(book_id,page_num)
            DO UPDATE SET full_text=EXCLUDED.full_text,section_name=EXCLUDED.section_name
        """, (book_id, i+1, section, lat[:5000], len(exercises)))
        saved_p += 1

        for ex in exercises:
            cur.execute("""
                INSERT INTO book_exercises(book_id,page_num,mavzu,fan,sinf,savol)
                VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
            """, (book_id, i+1, section or f"Bet {i+1}", fan, sinf, ex[:500]))
            saved_e += 1

        if (i+1) % 10 == 0 or i == total-1:
            pct = round((i+1)*100/total)
            bar = "█" * (pct//10) + "░" * (10 - pct//10)
            await p(
                f"📖 Kitob yuklanmoqda...\n"
                f"{bar} {pct}%\n"
                f"📄 {i+1}/{total} bet\n"
                f"📐 {saved_e} misol topildi"
            )

    conn.commit(); cur.close(); conn.close()
    await p(f"✅ Saqlandi!\n📄 {saved_p} bet | 📐 {saved_e} misol\n🔑 Book ID: {book_id}")
    return {"book_id": book_id, "pages": saved_p, "exercises": saved_e}

# ══ 4. QIDIRUV ══
def search_book(query: str, sinf=None, fan=None, limit=10) -> list:
    try:
        conn = db(); cur = conn.cursor()
        params = [f"%{query}%", f"%{query}%"]
        sf = "AND b.sinf=%s" if sinf else ""
        ff = "AND b.fan=%s" if fan else ""
        if sinf: params.append(sinf)
        if fan:  params.append(fan)
        params.append(limit)
        cur.execute(f"""
            SELECT p.page_num, p.section_name, p.full_text, b.id, b.title
            FROM book_pages p JOIN books b ON b.id=p.book_id
            WHERE (p.full_text ILIKE %s OR p.section_name ILIKE %s) {sf} {ff}
            ORDER BY p.page_num LIMIT %s
        """, params)
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"page":r[0],"section":r[1],"text":r[2][:400],"book_id":r[3],"title":r[4]} for r in rows]
    except: return []

def get_page(book_id: int, page_num: int) -> dict:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT page_num,section_name,full_text FROM book_pages WHERE book_id=%s AND page_num=%s",
                   (book_id, page_num))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return {"page":row[0],"section":row[1],"text":row[2]}
    except: pass
    return {}

def get_exercises(book_id: int, page_num: int = None, mavzu: str = None, limit: int = 20) -> list:
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

def get_books(sinf=None) -> list:
    try:
        conn = db(); cur = conn.cursor()
        if sinf:
            cur.execute("SELECT id,title,sinf,fan,total_pages FROM books WHERE sinf=%s ORDER BY id",(sinf,))
        else:
            cur.execute("SELECT id,title,sinf,fan,total_pages FROM books ORDER BY id")
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"id":r[0],"title":r[1],"sinf":r[2],"fan":r[3],"pages":r[4]} for r in rows]
    except: return []
