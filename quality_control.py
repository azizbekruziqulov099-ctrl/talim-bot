"""
quality_control.py — Xatolarni oldini olish va o'z-o'zini yaxshilash
"""
import re, os, psycopg2, asyncio

DATABASE_URL = os.getenv("DATABASE_URL")

# ══════════════════════════════════════
# TIL ANIQLASH
# ══════════════════════════════════════
def detect_lang(text: str) -> str:
    """Matn tilini aniqlaydi: uz | ru | en"""
    if not text: return "uz"
    text = text.lower()
    # O'zbek harflari
    uz_chars = set("gʻoʻıñ") | set("'")
    uz_words = {"nima","qanday","qachon","kim","bu","va","emas","bilan",
                "uchun","kerak","yaxshi","bilaman","o'rganish"}
    # Rus harflari
    ru_chars = set("абвгдежзийклмнопрстуфхцчшщъыьэюяё")
    ru_words = {"что","как","где","когда","почему","это","для","учебник"}
    # Ingliz
    en_words = {"what","how","where","when","why","this","for","the","is","are"}

    words = set(re.findall(r'\b\w+\b', text))
    ru_score = sum(1 for c in text if c in ru_chars) + len(words & ru_words)*3
    en_score = len(words & en_words)*3 + (1 if all(c.isascii() for c in text if c.isalpha()) else 0)*2
    uz_score = sum(1 for c in text if c in uz_chars) + len(words & uz_words)*3

    if ru_score > en_score and ru_score > uz_score: return "ru"
    if en_score > uz_score: return "en"
    return "uz"

# ══════════════════════════════════════
# KO'P TIL PROMPTLARI
# ══════════════════════════════════════
LANG_PROMPTS = {
    "uz": {
        "system": "Sen o'zbek tilida gapiradigan mutaxassis pedagogsan.",
        "answer": "O'zbek tilida javob ber.",
        "greet":  "Salom! Men ta'lim yordamchisiman.",
        "notfound": "Kechirasiz, bu mavzu bo'yicha ma'lumot topa olmadim.",
        "explain_5_7": "5-7 yoshli bolaga oddiy misol bilan tushuntir:",
        "explain_8_11": "8-11 yoshli o'quvchiga tushunarli tarzda tushuntir:",
        "explain_12plus": "12+ yoshga ilmiy, to'liq tushuntir:",
    },
    "ru": {
        "system": "Ты профессиональный педагог, говоришь по-русски.",
        "answer": "Отвечай на русском языке.",
        "greet":  "Привет! Я образовательный помощник.",
        "notfound": "Извините, информация по этой теме не найдена.",
        "explain_5_7": "Объясни для ребёнка 5-7 лет с простым примером:",
        "explain_8_11": "Объясни для ученика 8-11 лет понятно:",
        "explain_12plus": "Объясни научно и полно для 12+ лет:",
    },
    "en": {
        "system": "You are a professional educator who speaks English.",
        "answer": "Answer in English.",
        "greet":  "Hello! I am an educational assistant.",
        "notfound": "Sorry, I couldn't find information on this topic.",
        "explain_5_7": "Explain for a 5-7 year old child with a simple example:",
        "explain_8_11": "Explain for an 8-11 year old student clearly:",
        "explain_12plus": "Explain scientifically and fully for 12+ years:",
    }
}

def get_prompt(lang: str, key: str) -> str:
    return LANG_PROMPTS.get(lang, LANG_PROMPTS["uz"]).get(key, "")

# ══════════════════════════════════════
# SIFAT NAZORATI
# ══════════════════════════════════════
async def validate_answer(question: str, answer1: str, answer2: str, lang="uz") -> dict:
    """
    2 ta AI javobini taqqoslaydi.
    Agar mos kelsa → ishonchli
    Agar farq katta bo'lsa → tekshirish kerak
    """
    if not answer1 and not answer2:
        return {"quality": 0, "answer": "", "reliable": False}
    if not answer1: return {"quality": 5, "answer": answer2, "reliable": True}
    if not answer2: return {"quality": 5, "answer": answer1, "reliable": True}

    # Uzunlikni taqqoslaymiz
    len1, len2 = len(answer1), len(answer2)
    # Kalit so'zlarni taqqoslaymiz
    words1 = set(re.findall(r'\b\w{4,}\b', answer1.lower()))
    words2 = set(re.findall(r'\b\w{4,}\b', answer2.lower()))
    overlap = len(words1 & words2) / max(len(words1 | words2), 1)

    if overlap > 0.4:
        # Mos keladi — yaxshiroqni olish
        best = answer1 if len1 > len2 else answer2
        return {"quality": 9, "answer": best, "reliable": True, "overlap": overlap}
    elif overlap > 0.2:
        # Qisman mos
        best = answer1 if len1 > len2 else answer2
        return {"quality": 6, "answer": best, "reliable": True, "overlap": overlap}
    else:
        # Farq katta — ikkalasini birlashtirish
        combined = f"{answer1}\n\n---\n\n{answer2}"
        return {"quality": 4, "answer": combined, "reliable": False, "overlap": overlap}

def check_answer_quality(answer: str) -> dict:
    """Javob sifatini tekshiradi."""
    if not answer or len(answer) < 20:
        return {"ok": False, "reason": "Juda qisqa"}
    if answer.strip().startswith("{") or answer.strip().startswith("["):
        return {"ok": False, "reason": "JSON formatda (xato)"}
    if len(answer) > 5000:
        return {"ok": False, "reason": "Juda uzun"}
    return {"ok": True}

# ══════════════════════════════════════
# XATOLARDAN O'RGANISH
# ══════════════════════════════════════
def init_feedback_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS answer_feedback (
            id          SERIAL PRIMARY KEY,
            question    TEXT,
            answer_given TEXT,
            correct_answer TEXT,
            was_correct BOOLEAN,
            user_id     BIGINT,
            knowledge_id INT,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weak_topics (
            id          SERIAL PRIMARY KEY,
            mavzu       TEXT,
            fan         TEXT,
            error_count INT DEFAULT 1,
            last_error  TIMESTAMP DEFAULT NOW(),
            UNIQUE(mavzu, fan)
        )
    """)
    conn.commit(); cur.close(); conn.close()

def record_mistake(question: str, given: str, correct: str,
                   user_id: int, mavzu: str, fan: str):
    """Xatoni qayd etadi va zaif mavzularni belgilaydi."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO answer_feedback(question,answer_given,correct_answer,
                                        was_correct,user_id)
            VALUES(%s,%s,%s,FALSE,%s)
        """, (question, given, correct, user_id))

        # Zaif mavzuni belgilash
        cur.execute("""
            INSERT INTO weak_topics(mavzu,fan,error_count)
            VALUES(%s,%s,1)
            ON CONFLICT(mavzu,fan) DO UPDATE
            SET error_count = weak_topics.error_count + 1,
                last_error  = NOW()
        """, (mavzu, fan))

        # Shu mavzudagi bilimning sifatini tushirish
        cur.execute("""
            UPDATE knowledge_facts
            SET quality = GREATEST(quality - 1, 1)
            WHERE mavzu=%s AND fan=%s
        """, (mavzu, fan))

        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        print(f"record_mistake xato: {e}")

def get_weak_topics(fan: str = None, limit: int = 10) -> list:
    """Eng ko'p xato qilingan mavzular."""
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    fan_f = "WHERE fan=%s" if fan else ""
    params = ([fan] if fan else []) + [limit]
    cur.execute(f"""
        SELECT mavzu, fan, error_count
        FROM weak_topics
        {fan_f}
        ORDER BY error_count DESC
        LIMIT %s
    """, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"mavzu":r[0],"fan":r[1],"xato":r[2]} for r in rows]

async def retrain_weak_topics(fan: str, sinf: str, progress_cb=None):
    """Zaif mavzularni qayta o'qitadi."""
    weak = get_weak_topics(fan)
    if not weak:
        return {"message": "Zaif mavzu yo'q — tizim yaxshi ishlayapti!"}

    if progress_cb:
        await progress_cb(f"🔄 {len(weak)} ta zaif mavzu qayta o'qitilmoqda...")

    from pedagog_trainer import ask_best, make_analysis_prompt
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    fixed = 0
    for w in weak[:5]:  # Eng muhim 5 tasini
        cur.execute("""
            SELECT chunk_text FROM knowledge_facts
            WHERE mavzu=%s AND fan=%s LIMIT 1
        """, (w["mavzu"], fan))
        row = cur.fetchone()
        if not row: continue

        # Qayta tahlil
        prompt = make_analysis_prompt(row[0], fan, sinf)
        new_answer, ai = await ask_best(prompt)
        if new_answer:
            cur.execute("""
                UPDATE knowledge_facts
                SET javob=%s, source_ai=%s, quality=8
                WHERE mavzu=%s AND fan=%s
            """, (new_answer, ai, w["mavzu"], fan))
            # Zaif mavzu hisoblagichini nolga tushirish
            cur.execute("""
                UPDATE weak_topics SET error_count=0 WHERE mavzu=%s AND fan=%s
            """, (w["mavzu"], fan))
            fixed += 1

    conn.commit(); cur.close(); conn.close()
    return {"fixed": fixed, "total": len(weak)}
