"""
brain.py — O'z-o'zini o'qituvchi ta'lim yordamchisi
1. DB dan qidiradi
2. Topilmasa → Gemini/GPT dan oladi + DB ga saqlaydi
3. Keyingi safar DB dan javob beradi (mustaqil)
"""
import re, os, psycopg2, asyncio, aiohttp, json
from difflib import SequenceMatcher

DATABASE_URL = os.getenv("DATABASE_URL","")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY","")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY","")

# ══════════════════════════════════════
# 1. TIL ANIQLASH
# ══════════════════════════════════════
def detect_lang(text: str) -> str:
    t = text.lower()
    if sum(1 for c in t if c in "абвгдежзийклмнопрстуфхцчшщъыьэюяё") > 2:
        return "ru"
    en = {"what","how","where","when","why","the","is","are","hello","hi",
          "tell","explain","give","know","about","can","you","draw","show"}
    if len(set(re.findall(r"[a-zA-Z]+", t)) & en) >= 2:
        return "en"
    return "uz"

# ══════════════════════════════════════
# 2. IMLO TUZATISH
# ══════════════════════════════════════
FIXES = {
    "matimatika":"matematika","matim":"matematik","tist":"test",
    "bilay":"biladi","ayt":"ayt","hiz":"chiz","hizib":"chizib",
    "rasim":"rasm","niga":"nima uchun","qanha":"qancha",
    "qantay":"qanday","bilatimi":"biladimi","olatimi":"oladimi",
    "yordam":"yordam","tushuntir":"tushuntir","misil":"misol",
    "masila":"masala","kasr":"kasr","son":"son","darsi":"dars",
}

def fix_text(text: str) -> str:
    words = text.lower().split()
    return " ".join(FIXES.get(w, w) for w in words)

# ══════════════════════════════════════
# 3. NIYAT ANIQLASH
# ══════════════════════════════════════
def get_intent(text: str) -> str:
    t = text.lower()
    if re.search(r"^(salom|assalom|hi|hello|привет|ало)", t): return "GREET"
    if re.search(r"(nima qilolasan|yordam|help|что умеешь|nima bilasan)", t): return "HELP"
    if re.search(r"(rasm|chiz|draw|расс|сурат)", t): return "DRAW"
    if re.search(r"(test|sinov|imtihon|тест|quiz)", t): return "TEST"
    if re.search(r"(dars|o.rgan|tushuntir|урок|explain|lesson)", t): return "LESSON"
    if re.search(r"(misol|mashq|пример|example)", t): return "MISOL"
    if re.search(r"(masala|задача|problem|hisoblash)", t): return "MASALA"
    if re.search(r"(natija|statistika|результат|progress)", t): return "STATS"
    return "QUESTION"

# ══════════════════════════════════════
# 4. DB DAN QIDIRISH
# ══════════════════════════════════════
def search_knowledge(query: str, yosh: int = 10) -> dict | None:
    q = fix_text(query)
    words = [w for w in re.findall(r'\w{3,}', q) if not w.isdigit()]
    if not words: return None
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        like = " OR ".join(
            ["(keywords ILIKE %s OR savol ILIKE %s OR mavzu ILIKE %s)"] * len(words)
        )
        params = [f"%{w}%" for w in words for _ in range(3)]
        cur.execute(f"""
            SELECT mavzu, savol, javob, izoh, yosh_5_7, yosh_8_11, yosh_12plus, quality
            FROM knowledge_facts
            WHERE {like}
            ORDER BY quality DESC LIMIT 3
        """, params)
        rows = cur.fetchall(); cur.close(); conn.close()
        if not rows: return None
        best = rows[0]
        javob = (best[4] if yosh<=7 else best[5] if yosh<=11 else best[6]) or best[2]
        if not javob: return None
        return {"mavzu": best[0], "javob": javob, "izoh": best[3]}
    except: return None

def find_topic(text: str, grade: str = None) -> dict | None:
    q = fix_text(text).lower()
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        gf = "AND grade=%s" if grade else ""
        cur.execute(f"""
            SELECT topic_code, kichik_name, subject_name, grade
            FROM dts_tree
            WHERE is_deleted=FALSE AND (
                LOWER(kichik_name) LIKE %s OR LOWER(mavzu_name) LIKE %s)
            {gf} LIMIT 3
        """, [f"%{q}%"]*2 + ([grade] if grade else []))
        rows = cur.fetchall(); cur.close(); conn.close()
        if not rows: return None
        words = q.split()
        best, bs = None, 0
        for tc, kn, sn, gr in rows:
            sc = max(SequenceMatcher(None, w, kn.lower()).ratio() for w in words)
            if sc > bs: bs, best = sc, {"topic_code":tc,"kichik_name":kn,"subject_name":sn,"grade":gr}
        return best if bs > 0.25 else {"topic_code":rows[0][0],"kichik_name":rows[0][1],"subject_name":rows[0][2],"grade":rows[0][3]}
    except: return None

# ══════════════════════════════════════
# 5. GEMINI/GPT DAN JAVOB + DB GA SAQLASH
# ══════════════════════════════════════
async def ask_ai_and_save(question: str, lang: str = "uz", yosh: int = 10) -> str:
    """AI dan javob olib DB ga saqlaydi — keyingi safar AI kerak emas."""
    lang_txt = {"uz": "O'zbek tilida", "ru": "По-русски", "en": "In English"}.get(lang, "O'zbek tilida")
    yosh_txt = "5-7 yoshli bolaga" if yosh<=7 else "8-11 yoshli o'quvchiga" if yosh<=11 else "12+ yoshga"

    prompt = f"""{lang_txt} javob ber. Sen tajribali pedagogsan.
{yosh_txt} tushunarli tarzda javob ber.
Ta'lim sohasiga oid savolga qisqa, aniq javob ber (max 200 so'z).

Savol: {question}"""

    answer = ""
    source = "none"

    # Gemini
    if GEMINI_KEY and not answer:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            async with aiohttp.ClientSession() as s:
                async with s.post(url,
                    json={"contents":[{"parts":[{"text":prompt}]}],
                          "generationConfig":{"maxOutputTokens":400,"temperature":0.3}},
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        d = await r.json()
                        answer = d["candidates"][0]["content"]["parts"][0]["text"].strip()
                        source = "gemini"
        except: pass

    # GPT zaxira
    if OPENAI_KEY and not answer:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post("https://api.openai.com/v1/chat/completions",
                    json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"max_tokens":400},
                    headers={"Authorization":f"Bearer {OPENAI_KEY}"},
                    timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        d = await r.json()
                        answer = d["choices"][0]["message"]["content"].strip()
                        source = "gpt"
        except: pass

    # DB ga saqlash — keyingi safar ishlatamiz
    if answer:
        try:
            conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
            # Dublikat bo'lmasin
            cur.execute("SELECT id FROM knowledge_facts WHERE savol=%s LIMIT 1", (question,))
            if not cur.fetchone():
                kw = " ".join(re.findall(r'\w{4,}', question.lower())[:15])
                cur.execute("""
                    INSERT INTO knowledge_facts
                    (mavzu, fan, sinf, fact_type, savol, javob,
                     yosh_5_7, yosh_8_11, yosh_12plus, source_ai, quality, keywords)
                    VALUES(%s,'ta_lim','all','question',%s,%s,%s,%s,%s,%s,7,%s)
                """, (
                    question[:50], question, answer,
                    answer if yosh<=7 else "",
                    answer if 8<=yosh<=11 else "",
                    answer if yosh>=12 else "",
                    source, kw
                ))
                conn.commit()
            cur.close(); conn.close()
        except: pass

    return answer

# ══════════════════════════════════════
# 6. ASOSIY FUNKSIYA
# ══════════════════════════════════════
SALOM = {
    "uz": "👋 Salom! Men ta'lim yordamchisiman.\n\nIstalgan savolni yozing — matematika, biologiya, ingliz tili, fizika va boshqalar!\n\nBilmagan narsalarimni o'rganib borib, keyingi safar o'zim javob beraman 📚",
    "ru": "👋 Привет! Я образовательный помощник. Задавайте любые вопросы!",
    "en": "👋 Hello! I'm your educational assistant. Ask me anything!",
}
YORDAM = {
    "uz": (
        "🆘 Nima qila olaman:\n\n"
        "📚 «kasr nima?» — mavzu tushuntiraman\n"
        "📐 «misol ber» — misol ko'rsataman\n"
        "🧪 «test ber» — test boshlayman\n"
        "📖 «greetings darsini ber» — dars boshlayman\n"
        "🎨 «rasm chiz» — admin panel orqali\n\n"
        "Bilmagan narsalarimni Gemini/GPT dan o'rganib saqlayman 🤖"
    ),
    "ru": "🆘 Могу объяснять темы, давать примеры, тесты и уроки.",
    "en": "🆘 I can explain topics, give examples, tests and lessons.",
}

async def process_message(text: str, user_id: int,
                          grade: str = None, yosh: int = 10) -> dict:
    lang    = detect_lang(text)
    fixed   = fix_text(text)
    intent  = get_intent(fixed)
    result  = {"intent":intent, "topic":None, "action":None, "message":None, "lang":lang}

    # Salom
    if intent == "GREET":
        result["message"] = SALOM.get(lang, SALOM["uz"])
        return result

    # Yordam
    if intent == "HELP":
        result["message"] = YORDAM.get(lang, YORDAM["uz"])
        return result

    # Statistika
    if intent == "STATS":
        result["action"]  = "SHOW_STATS"
        result["message"] = "📊 Statistikangizni yuklamoqdaman..."
        return result

    # Rasm
    if intent == "DRAW":
        result["message"] = {
            "uz": "🎨 Rasm yaratish uchun admin paneliga murojaat qiling:\n«🎨 AI Rasm yaratish»",
            "en": "🎨 For image generation, use admin panel: «🎨 AI Image Generation»",
            "ru": "🎨 Для создания изображений используйте панель администратора.",
        }.get(lang)
        return result

    # Test
    topic = find_topic(fixed, grade)
    if intent == "TEST":
        if topic:
            result["action"]  = "START_TEST"
            result["topic"]   = topic
            result["message"] = f"🧪 {topic['kichik_name']} — test boshlanmoqda..."
        else:
            result["message"] = {"uz":"🧪 Qaysi mavzudan test? Aniqroq yozing.","ru":"🧪 По какой теме тест?","en":"🧪 Which topic for the test?"}.get(lang)
        return result

    # Dars
    if intent == "LESSON":
        if topic:
            result["action"]  = "START_LESSON"
            result["topic"]   = topic
            result["message"] = f"📖 {topic['kichik_name']} darsi boshlanmoqda..."
        else:
            result["message"] = {"uz":"📖 Qaysi mavzu? Aniqroq yozing.","ru":"📖 Какая тема?","en":"📖 Which topic?"}.get(lang)
        return result

    # SAVOL — avval DB, keyin AI
    kb = search_knowledge(fixed, yosh)
    if kb and kb.get("javob"):
        msg = f"📖 {kb['mavzu']}\n\n{kb['javob']}"
        if kb.get("izoh"): msg += f"\n\n💡 {kb['izoh']}"
        result["message"] = msg
        return result

    # DB da yo'q → Gemini/GPT
    if GEMINI_KEY or OPENAI_KEY:
        ai_ans = await ask_ai_and_save(text, lang, yosh)
        if ai_ans:
            result["message"] = f"🤖 {ai_ans}\n\n_(Bu javob saqlanadi — keyingi safar tezroq javob beraman)_"
            return result

    # Hech narsa topilmadi — mavzu dars bo'lsa
    if topic:
        result["action"]  = "START_LESSON"
        result["topic"]   = topic
        result["message"] = f"📖 {topic['kichik_name']} bo'yicha dars boshlayman..."
    else:
        result["message"] = {
            "uz": f"🤔 «{text[:30]}» haqida ma'lumot topilmadi.\n\nGemini kalitini qo'shing va men o'rganaman!",
            "ru": "🤔 Информация не найдена.",
            "en": "🤔 No information found.",
        }.get(lang)

    return result
