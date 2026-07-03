"""
pedagog_trainer.py — Ko'p AI dan o'rganib bilim bazasi to'ldirish
Gemini, GPT, Claude — kimidan yaxshi kelsa shu saqlanadi
"""
import os, re, asyncio, psycopg2, json, hashlib
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY","")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY","")

# ══════════════════════════════════════
# DB — Bilim jadvallari
# ══════════════════════════════════════
def init_knowledge_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_facts (
            id          SERIAL PRIMARY KEY,
            mavzu       TEXT,
            fan         TEXT,
            sinf        TEXT,
            fact_type   TEXT,  -- 'tarif','qoida','misol','formula','savol_javob'
            savol       TEXT,
            javob       TEXT,
            izoh        TEXT,
            yosh_5_7    TEXT,  -- 5-7 yosh uchun tushuntirish
            yosh_8_11   TEXT,  -- 8-11 yosh uchun
            yosh_12plus TEXT,  -- 12+ yosh uchun
            source_ai   TEXT,  -- qaysi AI yozdi
            quality     INT DEFAULT 5, -- 1-10 baho
            book_id     INT,
            chunk_text  TEXT,
            keywords    TEXT,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kf_mavzu ON knowledge_facts(mavzu)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kf_fan ON knowledge_facts(fan)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kf_type ON knowledge_facts(fact_type)")
    conn.commit(); cur.close(); conn.close()

# ══════════════════════════════════════
# AI CHAQIRUVLAR
# ══════════════════════════════════════
async def ask_gemini(prompt: str) -> Optional[str]:
    """Gemini dan javob olish."""
    if not GEMINI_KEY: return None
    try:
        import aiohttp
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        body = {"contents":[{"parts":[{"text": prompt}]}]}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body, timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini xato: {e}")
    return None

async def ask_gpt(prompt: str) -> Optional[str]:
    """OpenAI GPT dan javob olish."""
    if not OPENAI_KEY: return None
    try:
        import aiohttp
        url  = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        body = {"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"max_tokens":1000}
        async with aiohttp.ClientSession() as session:
            async with session.post(url,json=body,headers=headers,timeout=aiohttp.ClientTimeout(total=30)) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GPT xato: {e}")
    return None

async def ask_best(*prompts_and_keys) -> tuple[str, str]:
    """
    Bir necha AI dan javob olib eng yaxshisini qaytaradi.
    Qaytadi: (javob, ai_nomi)
    """
    prompt = prompts_and_keys[0]
    tasks  = {
        "gemini": ask_gemini(prompt),
        "gpt":    ask_gpt(prompt),
    }
    results = {}
    for name, coro in tasks.items():
        try:
            r = await coro
            if r and len(r.strip()) > 20:
                results[name] = r
        except: pass

    if not results:
        return "", "none"

    # Uzunroq va batafsilroq javobni tanlash
    best = max(results.items(), key=lambda x: len(x[1]))
    return best[1], best[0]

# ══════════════════════════════════════
# BILIM AJRATISH PROMPTLARI
# ══════════════════════════════════════
def make_analysis_prompt(chunk_text: str, fan: str, sinf: str) -> str:
    return f"""Sen mutaxassis pedagog va darslik muallifisin.
Quyidagi {fan} darsligidagi matnni tahlil qil ({sinf}-sinf uchun):

MATN:
{chunk_text[:2000]}

Quyidagi JSON formatda javob ber:
{{
  "mavzu": "mavzu nomi",
  "fact_type": "tarif|qoida|misol|formula|savol_javob",
  "savol": "bu mavzu haqida asosiy savol",
  "javob": "to'liq javob",
  "izoh": "qo'shimcha izoh",
  "yosh_5_7": "5-7 yoshli bolaga qanday tushuntirasan (juda oddiy, misol bilan)",
  "yosh_8_11": "8-11 yoshli o'quvchiga tushuntirish",
  "yosh_12plus": "12+ yosh uchun to'liq ilmiy tushuntirish",
  "keywords": "kalit so'zlar vergul bilan"
}}

Faqat JSON qayt, boshqa hech narsa yozma."""

def make_test_prompt(chunk_text: str, fan: str, sinf: str) -> str:
    return f"""Sen {fan} fani bo'yicha {sinf}-sinf uchun test muallifisin.

MATN:
{chunk_text[:1500]}

Bu matnga asoslanib 5 ta test savoli yoz. JSON formatda:
[
  {{
    "savol": "savol matni",
    "A": "variant A",
    "B": "variant B",
    "C": "variant C",
    "D": "variant D",
    "togri": "A",
    "izoh": "nima uchun A to'g'ri",
    "qiyinlik": "oson|orta|qiyin"
  }}
]

Faqat JSON, boshqa narsa yozma."""

# ══════════════════════════════════════
# ASOSIY O'QITISH FUNKSIYASI
# ══════════════════════════════════════
async def train_from_book(
    book_id:     int,
    fan:         str,
    sinf:        str,
    progress_cb  = None
) -> dict:
    """Kitobni tahlil qilib bilim bazasini to'ldiradi."""

    async def p(msg):
        if progress_cb: await progress_cb(msg)

    init_knowledge_db()
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    # Kitobning bo'limlarini olamiz
    cur.execute("""
        SELECT bc.id, bc.matn, bc.chunk_type, bc.latex, bs.title
        FROM book_chunks bc
        JOIN book_sections bs ON bs.id = bc.section_id
        WHERE bc.book_id = %s
        ORDER BY bc.page_num
    """, (book_id,))
    chunks = cur.fetchall()
    cur.close(); conn.close()

    await p(f"📚 {len(chunks)} ta matn bo'lagi tahlil qilinadi...")

    total_facts = 0
    total_tests = 0
    errors      = 0

    # Har 5 ta chunk ni birlashtirib tahlil qilamiz
    batch_size = 5
    for i in range(0, len(chunks), batch_size):
        batch   = chunks[i:i+batch_size]
        batch_text = "\n\n".join(c[1] for c in batch if c[1])

        if len(batch_text.strip()) < 100:
            continue

        section_title = batch[0][4] if batch else "Mavzu"

        # 1) Bilim ajratish
        analysis_prompt = make_analysis_prompt(batch_text, fan, sinf)
        analysis_raw, ai_name = await ask_best(analysis_prompt)

        if analysis_raw:
            try:
                # JSON tozalash
                json_str = re.search(r'\{.*\}', analysis_raw, re.DOTALL)
                if json_str:
                    data = json.loads(json_str.group())
                    conn2 = psycopg2.connect(DATABASE_URL)
                    cur2  = conn2.cursor()
                    cur2.execute("""
                        INSERT INTO knowledge_facts
                        (mavzu,fan,sinf,fact_type,savol,javob,izoh,
                         yosh_5_7,yosh_8_11,yosh_12plus,
                         source_ai,book_id,chunk_text,keywords)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        data.get("mavzu", section_title),
                        fan, sinf,
                        data.get("fact_type","matn"),
                        data.get("savol",""),
                        data.get("javob",""),
                        data.get("izoh",""),
                        data.get("yosh_5_7",""),
                        data.get("yosh_8_11",""),
                        data.get("yosh_12plus",""),
                        ai_name, book_id,
                        batch_text[:500],
                        data.get("keywords","")
                    ))
                    conn2.commit(); cur2.close(); conn2.close()
                    total_facts += 1
            except Exception as e:
                errors += 1

        # 2) Test savollar yaratish
        test_prompt = make_test_prompt(batch_text, fan, sinf)
        test_raw, _ = await ask_best(test_prompt)

        if test_raw:
            try:
                json_arr = re.search(r'\[.*\]', test_raw, re.DOTALL)
                if json_arr:
                    tests = json.loads(json_arr.group())
                    conn3 = psycopg2.connect(DATABASE_URL)
                    cur3  = conn3.cursor()
                    for t in tests[:5]:
                        cur3.execute("""
                            INSERT INTO generated_tests
                            (topic_code,difficulty,question,
                             option_a,option_b,option_c,option_d,
                             correct_answer,explanation,question_type,language)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'single_choice','uz')
                            ON CONFLICT DO NOTHING
                        """, (
                            f"book-{book_id}-{i}",
                            t.get("qiyinlik","orta"),
                            t.get("savol",""),
                            t.get("A",""), t.get("B",""),
                            t.get("C",""), t.get("D",""),
                            t.get("togri","A"),
                            t.get("izoh",""),
                        ))
                    conn3.commit(); cur3.close(); conn3.close()
                    total_tests += len(tests)
            except: errors += 1

        # Progress
        done = min(i + batch_size, len(chunks))
        pct  = round(done * 100 / len(chunks))
        if pct % 20 == 0 or done == len(chunks):
            await p(f"⏳ {pct}% | ✅ {total_facts} bilim | 🧪 {total_tests} test")

        await asyncio.sleep(0.5)  # API limit uchun

    await p(
        f"🎓 O'qitish yakunlandi!\n"
        f"✅ {total_facts} ta bilim saqlandi\n"
        f"🧪 {total_tests} ta test yaratildi\n"
        f"❌ {errors} ta xato (o'tkazib yuborildi)"
    )
    return {"facts": total_facts, "tests": total_tests, "errors": errors}

# ══════════════════════════════════════
# MUSTAQIL JAVOB BERISH (AI siz)
# ══════════════════════════════════════
def answer_from_knowledge(
    query:   str,
    fan:     str = None,
    sinf:    str = None,
    yosh:    int = 10
) -> dict:
    """
    Bilim bazasidan javob topadi.
    Hech qanday AI kerak emas!
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()

    words  = re.findall(r'\b\w{3,}\b', query.lower())
    like_q = " OR ".join(["keywords LIKE %s OR savol ILIKE %s OR mavzu ILIKE %s"]*len(words))
    params = []
    for w in words:
        params += [f"%{w}%", f"%{w}%", f"%{w}%"]
    fan_f  = "AND fan=%s" if fan else ""
    sinf_f = "AND sinf=%s" if sinf else ""
    if fan:  params.append(fan)
    if sinf: params.append(sinf)

    cur.execute(f"""
        SELECT mavzu, fact_type, savol, javob, izoh,
               yosh_5_7, yosh_8_11, yosh_12plus, keywords
        FROM knowledge_facts
        WHERE ({like_q}) {fan_f} {sinf_f}
        ORDER BY quality DESC
        LIMIT 3
    """, params)
    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        return {"found": False, "message": f"«{query}» bo'yicha ma'lumot topilmadi."}

    # Yoshga mos tushuntirishni tanlash
    best = rows[0]
    if yosh <= 7:
        tushuntirish = best[5] or best[3]  # yosh_5_7
    elif yosh <= 11:
        tushuntirish = best[6] or best[3]  # yosh_8_11
    else:
        tushuntirish = best[7] or best[3]  # yosh_12plus

    return {
        "found":       True,
        "mavzu":       best[0],
        "savol":       best[2],
        "javob":       tushuntirish,
        "izoh":        best[4],
        "qo'shimcha":  [r[3] for r in rows[1:] if r[3]],
    }
