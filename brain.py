"""
brain.py — Ko'p tilli, o'z-o'zini yaxshilaydigan pedagog miyasi
Uz | Ru | En — hamma tilda ishlaydi
AI siz javob beradi (bilim DB dan)
"""
import re, os, psycopg2
from difflib import SequenceMatcher

DATABASE_URL = os.getenv("DATABASE_URL")

# ══════════════════════════════════════
# NIYAT QO'LLANMASI (3 tilda)
# ══════════════════════════════════════
INTENTS = {
    "MISOL": [
        r"misol(lar)?|mashq|topshiriq",
        r"пример|задание|упражнение",
        r"example|exercise|practice",
    ],
    "MASALA": [
        r"masala(lar)?|muammo|hisoblash",
        r"задача|вычисли|реши",
        r"problem|solve|calculate",
    ],

    "TEST": [
        r"test\s*(ber|boshlash|ishla|qil)", r"sinov", r"imtihon",
        r"тест|проверь|экзамен", r"test|quiz|exam",
    ],
    "LESSON": [
        r"(dars|mavzu|o'rgan|tushuntir|izohla)",
        r"(урок|объясни|расскажи|учить)",
        r"(lesson|explain|teach|tell me about)",
    ],
    "STATS": [
        r"(natija|statistika|rivojlanish|ball)",
        r"(статистика|результат|прогресс)",
        r"(stats|results|progress|score)",
    ],
    "SEARCH": [
        r"(qayerda|qaysi|izla|qidir|top)\s*(mavzu|dars)",
        r"(найди|поиск|где)\s*(тему|урок)",
        r"(find|search|where)\s*(topic|lesson)",
    ],
    "GREET": [
        r"^(salom|assalom|hi|hello|привет|здравствуй)",
        r"^(qalay|nima gap|как дела|what's up)",
    ],
    "HELP": [
        r"(yordam|help|pomogi|справка)",
    ],
    "QUESTION": [
        r"\?\s*$",
        r"(nima|qanday|qachon|necha|kim)",
        r"(что|как|когда|почему|кто)",
        r"(what|how|when|why|who|which)",
    ],
    "RETRAIN": [
        r"(yangilash|qayta o'rgat|yaxshila)",
        r"(обновить|переучить|улучшить)",
        r"(retrain|update|improve)",
    ],
}

def detect_intent(text: str) -> str:
    t = text.lower().strip()
    for intent, patterns in INTENTS.items():
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                return intent
    return "UNKNOWN"

# ══════════════════════════════════════
# MAVZU QIDIRISH
# ══════════════════════════════════════
def find_topic(text: str, grade: str = None, lang: str = "uz") -> list:
    t = text.lower().strip()
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        grade_f = "AND grade=%s" if grade else ""
        cur.execute(f"""
            SELECT topic_code, kichik_name, subject_name, grade
            FROM dts_tree
            WHERE is_deleted=FALSE
              AND (LOWER(kichik_name) LIKE %s OR LOWER(mavzu_name) LIKE %s
                   OR LOWER(subject_name) LIKE %s)
              {grade_f}
            ORDER BY grade, subject_name LIMIT 5
        """, ([f"%{t}%"]*3 + ([grade] if grade else [])))
        rows = cur.fetchall(); cur.close(); conn.close()
        return rows
    except: return []

def best_topic(text: str, grade: str = None, lang: str = "uz"):
    results = find_topic(text, grade, lang)
    if not results: return None
    words = text.lower().split()
    best_r, best_s = None, 0
    for tc, kname, subj, gr in results:
        score = max(SequenceMatcher(None, w, kname.lower()).ratio() for w in words)
        if score > best_s: best_s, best_r = score, {"topic_code":tc,"kichik_name":kname,"subject_name":subj,"grade":gr}
    return best_r if best_s > 0.35 else ({"topic_code":results[0][0],"kichik_name":results[0][1],"subject_name":results[0][2],"grade":results[0][3]} if results else None)

# ══════════════════════════════════════
# BILIM BAZASIDAN JAVOB
# ══════════════════════════════════════
def answer_from_db(text: str, fan: str = None, sinf: str = None, yosh: int = 10, lang: str = "uz") -> dict:
    words  = re.findall(r'\b\w{3,}\b', text.lower())
    if not words: return {"found": False}
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        like_clauses = " OR ".join(["keywords ILIKE %s OR savol ILIKE %s OR mavzu ILIKE %s"] * len(words))
        params = []
        for w in words: params += [f"%{w}%"]*3
        fan_f  = "AND fan=%s" if fan else ""
        sinf_f = "AND sinf=%s" if sinf else ""
        if fan: params.append(fan)
        if sinf: params.append(sinf)

        cur.execute(f"""
            SELECT mavzu, fact_type, savol, javob, izoh,
                   yosh_5_7, yosh_8_11, yosh_12plus, quality
            FROM knowledge_facts
            WHERE ({like_clauses}) {fan_f} {sinf_f}
            ORDER BY quality DESC, id DESC LIMIT 3
        """, params)
        rows = cur.fetchall(); cur.close(); conn.close()
    except: return {"found": False}

    if not rows: return {"found": False}
    best = rows[0]
    # Misol/masalalarni ham qidiramiz
    try:
        conn2 = psycopg2.connect(DATABASE_URL); cur2 = conn2.cursor()
        ph2 = ",".join(["%s"]*len(words))
        cur2.execute(f"""
            SELECT ex_type, savol, yechim, javob, qiyinlik
            FROM book_exercises
            WHERE mavzu ILIKE ANY(ARRAY[{",".join(["%s"]*len(words))}])
               OR savol ILIKE ANY(ARRAY[{",".join(["%s"]*len(words))}])
            ORDER BY id LIMIT 3
        """, [f"%{w}%" for w in words]*2)
        exercises = cur2.fetchall()
        cur2.close(); conn2.close()
    except: exercises = []
    javob = (best[5] if yosh<=7 else best[6] if yosh<=11 else best[7]) or best[3]
    return {
        "found":  True,
        "mavzu":  best[0],
        "savol":  best[2],
        "javob":  javob,
        "izoh":   best[4],
        "extra":  [r[3] for r in rows[1:] if r[3]],
    }

# ══════════════════════════════════════
# KO'P TILLIK JAVOBLAR
# ══════════════════════════════════════
HELP_TEXT = {
    "uz": (
        "🆘 Yordam:\n\n"
        "📚 Dars: «greetings darsini ber» yoki «kasr nima?»\n"
        "🧪 Test: «matematika testi» yoki «test ber»\n"
        "📊 Natija: «mening natijalarim»\n"
        "🔍 Qidirish: «animals mavzusi qayerda»\n\n"
        "🌐 Rus: можно писать по-русски\n"
        "🌐 Ingliz: you can write in English"
    ),
    "ru": (
        "🆘 Помощь:\n\n"
        "📚 Урок: «объясни дроби» или «урок по математике»\n"
        "🧪 Тест: «тест по математике» или «дай тест»\n"
        "📊 Результат: «мои результаты»\n"
        "🔍 Поиск: «где тема animals»"
    ),
    "en": (
        "🆘 Help:\n\n"
        "📚 Lesson: «explain fractions» or «start a lesson»\n"
        "🧪 Test: «math test» or «give me a test»\n"
        "📊 Stats: «my results»\n"
        "🔍 Search: «where is topic animals»"
    ),
}

GREET_TEXT = {
    "uz": "👋 Salom! Men ta'lim yordamchisiman.\n\nIstalgan savolingizni yozing:\n• «kasr nima?»\n• «misol ber»\n• «test ber»",
    "ru": "👋 Привет! Я образовательный помощник.\n\nЗадайте любой вопрос:",
    "en": "👋 Hello! I'm an educational assistant.\n\nAsk me anything:",
}

NOT_FOUND = {
    "uz": "🤔 Bu haqda ma'lumot bazamda yo'q.\n\nBoshqa savol bering yoki aniqroq yozing:\n• «kasr nima?»\n• «qo'shish qoidasi»",
    "ru": "🤔 Информация не найдена. Попробуйте другой вопрос.",
    "en": "🤔 No info found. Try asking differently.",
}

# ══════════════════════════════════════
# ASOSIY FUNKSIYA
# ══════════════════════════════════════
async def process_message(text: str, user_id: int, grade: str = None, yosh: int = 10) -> dict:
    from quality_control import detect_lang
    lang   = detect_lang(text)
    intent = detect_intent(text)
    topic  = best_topic(text, grade, lang)

    result = {"intent": intent, "topic": topic, "action": None, "message": None, "lang": lang}

    if intent == "GREET":
        result["message"] = GREET_TEXT.get(lang, GREET_TEXT["uz"])

    elif intent == "HELP":
        result["message"] = HELP_TEXT.get(lang, HELP_TEXT["uz"])

    elif intent == "QUESTION":
        # 1. Bilim bazasidan qidirish
        kb = answer_from_db(text, yosh=yosh, lang=lang)
        if kb.get("found"):
            izoh = kb.get("izoh","")
            extra = kb.get("extra",[])
            msg = f"📖 {kb['mavzu']}\n\n{kb['javob']}"
            if izoh: msg += f"\n\n💡 {izoh}"
            if extra: msg += f"\n\n📌 Qo'shimcha:\n" + "\n".join(f"• {e[:100]}" for e in extra[:2])
            result["message"] = msg
        elif topic:
            result["action"]  = "START_LESSON"
            result["message"] = {
                "uz": f"📖 {topic['kichik_name']} bo'yicha dars boshlayman...",
                "ru": f"📖 Начинаю урок по теме {topic['kichik_name']}...",
                "en": f"📖 Starting lesson on {topic['kichik_name']}...",
            }.get(lang)
        else:
            result["message"] = NOT_FOUND.get(lang)

    elif intent == "TEST" and topic:
        result["action"]  = "START_TEST"
        result["message"] = {
            "uz": f"🧪 {topic['kichik_name']} mavzusidan test boshlayman...",
            "ru": f"🧪 Начинаю тест по теме {topic['kichik_name']}...",
            "en": f"🧪 Starting test on {topic['kichik_name']}...",
        }.get(lang)

    elif intent == "LESSON" and topic:
        result["action"]  = "START_LESSON"
        result["message"] = {
            "uz": f"📖 {topic['kichik_name']} darsini boshlayman...",
            "ru": f"📖 Начинаю урок {topic['kichik_name']}...",
            "en": f"📖 Starting lesson {topic['kichik_name']}...",
        }.get(lang)

    elif intent == "STATS":
        result["action"]  = "SHOW_STATS"
        result["message"] = {
            "uz": "📊 Statistikangizni yuklamoqdaman...",
            "ru": "📊 Загружаю вашу статистику...",
            "en": "📊 Loading your statistics...",
        }.get(lang)

    elif intent == "SEARCH":
        if topic:
            result["message"] = {
                "uz": f"🔍 Topildi:\n📚 {topic['subject_name']} → {topic['kichik_name']}\n🏫 {topic['grade']}-sinf\n🔑 {topic['topic_code']}",
                "ru": f"🔍 Найдено:\n📚 {topic['subject_name']} → {topic['kichik_name']}\n🏫 {topic['grade']} класс",
                "en": f"🔍 Found:\n📚 {topic['subject_name']} → {topic['kichik_name']}\n🏫 Grade {topic['grade']}",
            }.get(lang)
        else:
            result["message"] = NOT_FOUND.get(lang)

    elif intent == "RETRAIN":
        result["action"]  = "RETRAIN"
        result["message"] = {
            "uz": "🔄 Zaif mavzular qayta o'qitilmoqda...",
            "ru": "🔄 Переобучаю слабые темы...",
            "en": "🔄 Retraining weak topics...",
        }.get(lang)

    else:
        # Har qanday matn uchun bilim bazasidan qidiramiz
        kb = answer_from_db(text, yosh=yosh, lang=lang)
        if kb.get("found"):
            izoh = kb.get("izoh","")
            result["message"] = f"📖 {kb['mavzu']}\n\n{kb['javob']}"
            if izoh: result["message"] += f"\n\n💡 {izoh}"
        elif topic:
            result["action"]  = "START_LESSON"
            result["message"] = f"📖 {topic['kichik_name']} bo\'yicha dars boshlayman..."
        else:
            result["message"] = NOT_FOUND.get(lang, NOT_FOUND["uz"])

    return result
