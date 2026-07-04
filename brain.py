"""
brain.py — Aqlli pedagogik yordamchi
- Fuzzy matching (imlo xatolarni tushunadi)
- Gemini API (aqlli javob)
- Ko'p tilli (uz/ru/en)
- Bilim bazasidan qidirish
"""
import re, os, psycopg2, asyncio
from difflib import SequenceMatcher

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY","")

# ══════════════════════════════════════
# TIL ANIQLASH
# ══════════════════════════════════════
def detect_lang(text: str) -> str:
    if not text: return "uz"
    t = text.lower().strip()
    ru_chars = set("абвгдежзийклмнопрстуфхцчшщъыьэюяё")
    if sum(1 for c in t if c in ru_chars) > 2: return "ru"
    en_words = {"what","how","where","when","why","the","is","are",
                "hello","hi","teach","explain","give","know","about"}
    if len(set(re.findall(r"[a-zA-Z]+", t)) & en_words) >= 2: return "en"
    return "uz"

# ══════════════════════════════════════
# FUZZY MATCHING — imlo xatolarni tushunish
# ══════════════════════════════════════
UZ_CORRECTIONS = {
    # Umumiy xatolar
    "matimatika":"matematika","matim":"matematik","matem":"matematik",
    "fizika":"fizika","kimiya":"kimyo","biyologiya":"biologiya",
    "ingliz":"ingliz tili","inglizha":"inglizcha","inglisha":"inglizcha",
    "ars":"dars","tist":"test","tisd":"test","savil":"savol",
    "bilay":"biladi","bilamam":"bilmayman","bilasan":"bilasanmi",
    "misil":"misol","masila":"masala","kasr":"kasr","kars":"kasr",
    "qushish":"qo'shish","ayirish":"ayirish","kupaytirilish":"ko'paytirish",
    "bulish":"bo'lish","teng":"teng","son":"son","raqam":"raqam",
    "gapir":"gapir","ayt":"ayt","tushuntir":"tushuntir","urgatr":"o'rgat",
    "nima":"nima","qantay":"qanday","qanha":"qancha","niga":"nima uchun",
}

def fix_typos(text: str) -> str:
    """Imlo xatolarini tuzatadi."""
    words = text.lower().split()
    fixed = []
    for w in words:
        # To'g'ridan lug'atdan
        if w in UZ_CORRECTIONS:
            fixed.append(UZ_CORRECTIONS[w]); continue
        # Fuzzy matching — 80%+ o'xshashlik
        best, best_score = w, 0
        for wrong, correct in UZ_CORRECTIONS.items():
            score = SequenceMatcher(None, w, wrong).ratio()
            if score > 0.8 and score > best_score:
                best, best_score = correct, score
        fixed.append(best)
    return " ".join(fixed)

# ══════════════════════════════════════
# NIYAT ANIQLASH
# ══════════════════════════════════════
INTENTS = {
    "GREET":    [r"^(salom|assalom|hi|hello|привет|ало|aloo)"],
    "HELP":     [r"(yordam|nima qilolasan|help|pomogi|справка|nima bilasan)"],
    "TEST":     [r"(test|sinov|imtihon|тест|quiz|exam)\s*(ber|boshlash|ishlash)?"],
    "LESSON":   [r"(dars|mavzu|o.rgan|tushuntir|урок|объясни|lesson|explain)"],
    "MISOL":    [r"(misol|mashq|пример|example|exercise)"],
    "MASALA":   [r"(masala|задача|problem|hisoblash|solve)"],
    "STATS":    [r"(natija|statistika|результат|results|progress)"],
    "QUESTION": [r"\?\s*$", r"(nima|qanday|qachon|necha|что|как|what|how)"],
}

def detect_intent(text: str) -> str:
    t = text.lower()
    for intent, patterns in INTENTS.items():
        for p in patterns:
            if re.search(p, t, re.I): return intent
    return "UNKNOWN"

# ══════════════════════════════════════
# MAVZU QIDIRISH (fuzzy)
# ══════════════════════════════════════
def find_topic(text: str, grade: str = None):
    t = fix_typos(text).lower()
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        gf = "AND grade=%s" if grade else ""
        cur.execute(f"""
            SELECT topic_code, kichik_name, subject_name, grade
            FROM dts_tree
            WHERE is_deleted=FALSE AND (
                LOWER(kichik_name) LIKE %s OR
                LOWER(mavzu_name) LIKE %s OR
                LOWER(subject_name) LIKE %s)
            {gf} LIMIT 5
        """, [f"%{t}%"]*3 + ([grade] if grade else []))
        rows = cur.fetchall(); cur.close(); conn.close()
        if not rows: return None
        words = t.split()
        best, bs = None, 0
        for tc,kn,sn,gr in rows:
            sc = max(SequenceMatcher(None,w,kn.lower()).ratio() for w in words)
            if sc > bs: bs, best = sc, {"topic_code":tc,"kichik_name":kn,"subject_name":sn,"grade":gr}
        return best if bs > 0.3 else {"topic_code":rows[0][0],"kichik_name":rows[0][1],"subject_name":rows[0][2],"grade":rows[0][3]}
    except: return None

# ══════════════════════════════════════
# BILIM BAZASIDAN QIDIRISH
# ══════════════════════════════════════
def search_db(text: str, yosh: int = 10):
    original = text
    text = fix_typos(text)
    words = re.findall(r'\w{3,}', text.lower())
    if not words: return None
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        like = " OR ".join(["keywords ILIKE %s OR savol ILIKE %s OR mavzu ILIKE %s"]*len(words))
        params = [f"%{w}%" for w in words for _ in range(3)]
        cur.execute(f"""
            SELECT mavzu, savol, javob, izoh, yosh_5_7, yosh_8_11, yosh_12plus, quality
            FROM knowledge_facts
            WHERE ({like})
            ORDER BY quality DESC LIMIT 3
        """, params)
        rows = cur.fetchall(); cur.close(); conn.close()
        if not rows: return None
        best = rows[0]
        javob = (best[4] if yosh<=7 else best[5] if yosh<=11 else best[6]) or best[2]
        return {"mavzu":best[0],"savol":best[1],"javob":javob,"izoh":best[3]}
    except: return None

# ══════════════════════════════════════
# GEMINI API
# ══════════════════════════════════════
async def ask_gemini(question: str, context: str = "", lang: str = "uz") -> str:
    if not GEMINI_KEY: return ""
    lang_map = {"uz":"O'zbek tilida javob ber.","ru":"Отвечай по-русски.","en":"Answer in English."}
    prompt = f"""{lang_map.get(lang,'')}
Sen ta'lim sohasidagi mutaxassis pedagogsan.
Quyidagi savol o'quvchidan keldi.

{f"Kontekst:{context}" if context else ""}

Savol: {question}

Qisqa, tushunarli, yoshga mos javob ber. Agar formula bo'lsa LaTeX formatida yoz."""
    try:
        import aiohttp
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        body = {"contents":[{"parts":[{"text":prompt}]}],
                "generationConfig":{"maxOutputTokens":500,"temperature":0.3}}
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url, json=body, timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    data = await r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Gemini: {e}")
    return ""

# ══════════════════════════════════════
# JAVOB MATNI
# ══════════════════════════════════════
SALOM = {
    "uz": "👋 Salom! Men ta'lim yordamchisiman.\n\nIstalgan savolni yozing — matematika, ingliz tili, fizika, pedagog qonunlari — hamma narsaga javob beraman!",
    "ru": "👋 Привет! Я образовательный помощник. Задавайте любые вопросы!",
    "en": "👋 Hello! I'm your educational assistant. Ask me anything!",
}
YORDAM = {
    "uz": "🆘 Nima qila olaman:\n\n📚 Mavzu tushuntirish: «kasr nima?», «qo'shish qoidasi»\n📐 Misol: «misol ber», «masala yech»\n🧪 Test: «test ber», «5 ta savol»\n📖 Dars: «greetings darsini ber»\n\nImlo xatosi bo'lsa ham tushunaman 😊",
    "ru": "🆘 Могу:\n📚 Объяснить тему\n📐 Дать примеры\n🧪 Тест\n📖 Урок",
    "en": "🆘 I can:\n📚 Explain topics\n📐 Give examples\n🧪 Tests\n📖 Lessons",
}
NOT_FOUND = {
    "uz": "🤔 Bu haqda bilim bazamda ma'lumot yo'q.\n\nAniqroq yozing:\n• «{q} nima?»\n• «{q} misol»",
    "ru": "🤔 Информация не найдена. Попробуйте переформулировать.",
    "en": "🤔 No info found. Try rephrasing.",
}

# ══════════════════════════════════════
# ASOSIY FUNKSIYA
# ══════════════════════════════════════
async def process_message(text: str, user_id: int,
                          grade: str = None, yosh: int = 10) -> dict:
    lang    = detect_lang(text)
    fixed   = fix_typos(text)
    intent  = detect_intent(fixed)
    topic   = find_topic(fixed, grade)
    result  = {"intent":intent,"topic":topic,"action":None,"message":None,"lang":lang}

    if intent == "GREET":
        result["message"] = SALOM.get(lang, SALOM["uz"])
        return result

    if intent == "HELP":
        result["message"] = YORDAM.get(lang, YORDAM["uz"])
        return result

    if intent == "STATS":
        result["action"]  = "SHOW_STATS"
        result["message"] = {"uz":"📊 Statistikangizni yuklamoqdaman...","ru":"📊 Загружаю...","en":"📊 Loading..."}.get(lang)
        return result

    if intent == "TEST" and topic:
        result["action"]  = "START_TEST"
        result["message"] = f"🧪 {topic['kichik_name']} — test boshlanmoqda..."
        return result

    if intent == "LESSON" and topic:
        result["action"]  = "START_LESSON"
        result["message"] = f"📖 {topic['kichik_name']} darsi boshlanmoqda..."
        return result

    # Savol yoki noma'lum → avval DB, keyin Gemini
    kb = search_db(fixed, yosh)
    if kb:
        izoh = kb.get("izoh","")
        msg  = f"📖 {kb['mavzu']}\n\n{kb['javob']}"
        if izoh: msg += f"\n\n💡 {izoh}"
        result["message"] = msg
        return result

    # DB da yo'q → Gemini ga yuboramiz
    if GEMINI_KEY:
        gemini_ans = await ask_gemini(text, lang=lang)
        if gemini_ans:
            result["message"] = f"🤖 {gemini_ans}"
            return result

    # Hech narsa topilmadi
    if topic:
        result["action"]  = "START_LESSON"
        result["message"] = f"📖 {topic['kichik_name']} bo'yicha dars boshlayman..."
    else:
        q = fixed[:20]
        result["message"] = NOT_FOUND.get(lang, NOT_FOUND["uz"]).format(q=q)

    return result
