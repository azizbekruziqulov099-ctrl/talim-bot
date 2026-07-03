"""
brain.py — SamTM Bot "miyasi"
GPT/AI API siz, to'liq o'zimiz yozgan
"""
import re, os, psycopg2
from difflib import SequenceMatcher

DATABASE_URL = os.getenv("DATABASE_URL")

# ══════════════════════════════════════
# 1. NIYAT (INTENT) QO'LLANMASI
# ══════════════════════════════════════
INTENTS = {
    "test_boshlash": {
        "patterns": [
            r"test\s*(ber|boshlash|ishla|qil|ket)",
            r"(sinov|tekshir|imtihon)",
            r"\d+\s*ta\s*test",
            r"test\s*(mavzu|qism|bo'lim)",
        ],
        "response": "TEST"
    },
    "dars_boshlash": {
        "patterns": [
            r"(dars|mavzu|o'rgan|o'qi)\s*(ber|boshlash|qil|ket|ochish)",
            r"(tushuntir|izohla)",
            r"\d+[-\.]\s*dars",
            r"(o'rganay|o'qiyman)",
        ],
        "response": "LESSON"
    },
    "natija_korish": {
        "patterns": [
            r"(natija|ball|baho|statistika|ko'rsat)",
            r"(qancha|necha)\s*(to'g'ri|xato)",
            r"(rivojlanish|progress|taraqqiyot)",
            r"bugun\s*(nima|qancha)\s*(o'rgandim|ishladim)",
        ],
        "response": "STATS"
    },
    "yordam": {
        "patterns": [
            r"(yordam|help|nima\s*qilaman|qanday)",
            r"(tushunmadim|bilmadim|ayt|ko'rsat)",
            r"(bot\s*nima|nima\s*qila\s*oladi)",
        ],
        "response": "HELP"
    },
    "salom": {
        "patterns": [
            r"^(salom|assalom|hi|hello|privet|zdravstvuy)",
            r"(qalay|yaxshimisan|nima\s*gap)",
        ],
        "response": "GREET"
    },
    "mavzu_savol": {
        "patterns": [
            r"(nima|kim|qachon|qayerda|qanday|necha|nechta)\s*\?",
            r"(nima\s*bu|bu\s*nima|tushuntir|izohla|ayt)",
            r"\?\s*$",
        ],
        "response": "QUESTION"
    },
    "mavzu_izlash": {
        "patterns": [
            r"(qayerda|qaysi|qanday)\s*(mavzu|dars|topik)",
            r"(mavzu|dars)\s*(bor|topil|qaysi)",
            r"(izla|qidir|top)\s*(mavzu|dars)",
        ],
        "response": "SEARCH"
    },
}

# ══════════════════════════════════════
# 2. NIYAT ANIQLASH
# ══════════════════════════════════════
def detect_intent(text: str) -> str:
    """Matndan niyatni aniqlaymiz."""
    t = text.lower().strip()
    for intent, data in INTENTS.items():
        for pattern in data["patterns"]:
            if re.search(pattern, t, re.IGNORECASE):
                return data["response"]
    return "UNKNOWN"

# ══════════════════════════════════════
# 3. MAVZU ANIQLASH (DB dan)
# ══════════════════════════════════════
def find_topic(text: str, grade: str = None) -> list:
    """Matndan mavzuni DB dan qidirish."""
    t = text.lower().strip()
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        # Grade bo'yicha filter
        grade_filter = "AND grade=%s" if grade else ""
        params = [f"%{t}%"]
        if grade:
            params.append(grade)
        cur.execute(f"""
            SELECT topic_code, kichik_name, subject_name, grade
            FROM dts_tree
            WHERE is_deleted=FALSE
              AND (
                LOWER(kichik_name) LIKE %s
                OR LOWER(mavzu_name) LIKE %s
                OR LOWER(subject_name) LIKE %s
              )
              {grade_filter}
            ORDER BY grade, subject_name
            LIMIT 5
        """, [f"%{t}%", f"%{t}%", f"%{t}%"] + ([grade] if grade else []))
        results = cur.fetchall()
        cur.close(); conn.close()
        return results
    except:
        return []

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def best_topic_match(text: str, grade: str = None) -> dict | None:
    """Eng mos mavzuni topadi."""
    results = find_topic(text, grade)
    if not results:
        return None
    # Eng yaxshi moslikni topamiz
    words = text.lower().split()
    best  = None
    best_score = 0
    for tc, kname, subj, gr in results:
        score = max(similarity(w, kname) for w in words)
        if score > best_score:
            best_score = score
            best = {"topic_code": tc, "kichik_name": kname,
                    "subject_name": subj, "grade": gr}
    return best if best_score > 0.4 else None

# ══════════════════════════════════════
# 4. ASOSIY FUNKSIYA
# ══════════════════════════════════════
async def process_message(text: str, user_id: int, grade: str = None) -> dict:
    """
    Xabarni tahlil qilib buyruqni qaytaramiz.
    Qaytadi: {"action": ..., "topic": ..., "message": ...}
    """
    intent  = detect_intent(text)
    topic   = best_topic_match(text, grade)

    result = {
        "intent":  intent,
        "topic":   topic,
        "action":  None,
        "message": None,
    }

    if intent == "GREET":
        result["message"] = (
            "👋 Salom! Men SamTM ta'lim yordamchisiman.\n\n"
            "Nima qilishingiz mumkin:\n"
            "📚 «greetings darsini ber» — dars boshlash\n"
            "🧪 «matematika testini ber» — test boshlash\n"
            "📊 «mening natijalarim» — statistika\n"
            "🔍 «numbers mavzusi qayerda» — qidirish"
        )

    elif intent == "TEST" and topic:
        result["action"]  = "START_TEST"
        result["message"] = f"🧪 {topic['kichik_name']} mavzusidan test boshlayman..."

    elif intent == "LESSON" and topic:
        result["action"]  = "START_LESSON"
        result["message"] = f"📖 {topic['kichik_name']} darsini boshlayman..."

    elif intent == "STATS":
        result["action"]  = "SHOW_STATS"
        result["message"] = "📊 Statistikangizni yuklamoqdaman..."

    elif intent == "SEARCH":
        if topic:
            result["message"] = (
                f"🔍 Topdim:\n"
                f"📚 {topic['subject_name']} → {topic['kichik_name']}\n"
                f"🏫 {topic['grade']}-sinf\n"
                f"🔑 {topic['topic_code']}"
            )
        else:
            result["message"] = f"🔍 «{text}» bo'yicha mavzu topilmadi."

    elif intent == "QUESTION" and topic:
        # Dars materialidan javob izlaymiz
        result["action"]  = "ANSWER_FROM_LESSON"
        result["topic"]   = topic

    elif intent == "HELP":
        result["message"] = (
            "🆘 Yordam:\n\n"
            "📚 Dars boshlash:\n"
            "  «greetings o'rganay» yoki «1-dars»\n\n"
            "🧪 Test:\n"
            "  «test ber» yoki «numbers testi»\n\n"
            "📊 Natijalar:\n"
            "  «natijalarim» yoki «statistika»\n\n"
            "🔍 Qidirish:\n"
            "  «animals mavzusi qayerda»"
        )

    else:
        # Mavzu topilmagan — qidiruv natijasi
        results = find_topic(text, grade)
        if results:
            lines = ["🔍 Shu so'z bilan topilgan mavzular:\n"]
            for tc, kname, subj, gr in results[:3]:
                lines.append(f"  📚 {kname} ({subj}, {gr}-sinf)")
            result["message"] = "\n".join(lines)
        else:
            result["message"] = (
                f"🤔 «{text[:50]}» ni tushunmadim.\n\n"
                "«yordam» yozing — nima qila olishimni ko'rasiz."
            )

    return result
