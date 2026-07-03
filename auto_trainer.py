"""
auto_trainer.py — Avtomatik o'rganish tizimi
Gemini + GPT → DB → Mustaqil ekspert bot
"""
import os, asyncio, psycopg2, json, re, aiohttp
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL","")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY","")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY","")

# ══════════════════════════════════════
# EKSPERT PROFILLARI
# ══════════════════════════════════════
EXPERT_PROFILES = {
    "pedagog": {
        "role": "Sen 30 yillik tajribali o'zbek tili va adabiyoti o'qituvchisi, barcha fanlardan dars bera oladigan pedagogsan.",
        "topics": [
            "Matematika asoslari", "O'qish va yozish metodikasi",
            "Ingliz tili o'qitish", "Tabiatshunoslik", "Ona tili",
            "Rasm va musiqa", "Jismoniy tarbiya metodikasi",
        ]
    },
    "metodist": {
        "role": "Sen O'zbekiston ta'lim tizimining tajribali metodisti, dars reja tuza olasigan, uslub tavsiyalar bera oladigan mutaxassissan.",
        "topics": [
            "Dars rejasi tuzish", "Ta'lim texnologiyalari",
            "Interfaol metodlar", "Baholash tizimi",
            "DTS standartlari", "Kompetensiya asosida ta'lim",
        ]
    },
    "huquqshunos": {
        "role": "Sen O'zbekiston ta'lim qonunchiligini chuqur biladigan huquqshunossan.",
        "topics": [
            "O'zbekiston ta'lim qonuni", "DTS talablari",
            "O'qituvchi huquqlari", "O'quvchi huquqlari",
            "Ta'lim muassasalari qoidalari", "Akkreditatsiya talablari",
        ]
    },
    "psixolog": {
        "role": "Sen bolalar psixologiyasini yaxshi biladigan, yoshga mos ta'lim berish usullarini tavsiya qila oladigan pedagog-psixologsan.",
        "topics": [
            "Yoshga mos ta'lim", "Motivatsiya usullari",
            "Qiyin o'quvchilar bilan ishlash", "Ota-onalar bilan muloqot",
            "Stress va moslashish", "Iqtidorli bolalar",
        ]
    },
    "professor": {
        "role": "Sen ta'lim fanlari doktori, akademik darajadagi bilimga ega ilmiy muharrirsan.",
        "topics": [
            "Ilmiy yondashuv ta'limda", "Tadqiqot metodlari",
            "Innovatsion ta'lim", "Raqamli ta'lim texnologiyalari",
            "Xalqaro ta'lim standartlari", "PISA, TIMSS",
        ]
    },
}

# ══════════════════════════════════════
# AI PROVAYDERLAR
# ══════════════════════════════════════
async def ask_gemini(prompt: str) -> str:
    if not GEMINI_KEY: return ""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        body = {"contents":[{"parts":[{"text":prompt}]}],
                "generationConfig":{"maxOutputTokens":800,"temperature":0.4}}
        async with aiohttp.ClientSession() as s:
            async with s.post(url,json=body,timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status==200:
                    d=await r.json()
                    return d["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    return ""

async def ask_gpt(prompt: str) -> str:
    if not OPENAI_KEY: return ""
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"}
        body = {"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"max_tokens":800}
        async with aiohttp.ClientSession() as s:
            async with s.post(url,json=body,headers=headers,timeout=aiohttp.ClientTimeout(total=20)) as r:
                if r.status==200:
                    d=await r.json()
                    return d["choices"][0]["message"]["content"]
    except: pass
    return ""

async def ask_best(prompt: str) -> tuple:
    """Gemini va GPT dan yaxshisini oladi."""
    g = await ask_gemini(prompt)
    p = await ask_gpt(prompt)
    if g and p:
        return (g if len(g)>len(p) else p), ("gemini" if len(g)>len(p) else "gpt")
    if g: return g, "gemini"
    if p: return p, "gpt"
    return "", "none"

# ══════════════════════════════════════
# BILIM SAQLASH
# ══════════════════════════════════════
def save_knowledge(mavzu, profil, savol, javob, yosh_5_7="",
                   yosh_8_11="", yosh_12plus="", source="", quality=8):
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        # Takror bo'lmasin
        cur.execute("SELECT id FROM knowledge_facts WHERE savol=%s LIMIT 1", (savol,))
        if cur.fetchone():
            cur.close(); conn.close(); return False
        cur.execute("""
            INSERT INTO knowledge_facts
            (mavzu,fan,sinf,fact_type,savol,javob,yosh_5_7,yosh_8_11,
             yosh_12plus,source_ai,quality,keywords)
            VALUES(%s,%s,'all','ta_lim',%s,%s,%s,%s,%s,%s,%s,%s)
        """, (mavzu, profil, savol, javob,
              yosh_5_7, yosh_8_11, yosh_12plus,
              source, quality,
              " ".join(re.findall(r'\w{4,}', (savol+" "+mavzu).lower()))[:200]))
        conn.commit(); cur.close(); conn.close()
        return True
    except: return False

# ══════════════════════════════════════
# MAVZU BO'YICHA O'RGANISH
# ══════════════════════════════════════
async def learn_topic(profil_name: str, mavzu: str, progress_cb=None) -> int:
    profil = EXPERT_PROFILES.get(profil_name, EXPERT_PROFILES["pedagog"])
    saved  = 0

    prompt = f"""{profil['role']}

Mavzu: "{mavzu}"

Quyidagi JSON formatda 5 ta muhim bilim yoz:
[
  {{
    "savol": "...",
    "javob": "...(to'liq javob)",
    "yosh_5_7": "...(juda oddiy, bolalarga)",
    "yosh_8_11": "...(o'rta daraja)",
    "yosh_12plus": "...(ilmiy, to'liq)"
  }}
]

O'zbek tilida. Faqat JSON."""

    answer, source = await ask_best(prompt)
    if not answer: return 0

    try:
        arr = re.search(r'\[.*\]', answer, re.DOTALL)
        if not arr: return 0
        items = json.loads(arr.group())
        for item in items:
            ok = save_knowledge(
                mavzu=mavzu, profil=profil_name,
                savol=item.get("savol",""),
                javob=item.get("javob",""),
                yosh_5_7=item.get("yosh_5_7",""),
                yosh_8_11=item.get("yosh_8_11",""),
                yosh_12plus=item.get("yosh_12plus",""),
                source=source
            )
            if ok: saved += 1
    except: pass

    return saved

# ══════════════════════════════════════
# TO'LIQ O'QITISH (barcha profillar)
# ══════════════════════════════════════
async def train_all_profiles(progress_cb=None) -> dict:
    async def p(msg):
        if progress_cb: await progress_cb(msg)

    total = 0
    results = {}

    for profil_name, profil in EXPERT_PROFILES.items():
        await p(f"🎓 {profil_name.upper()} profili o'rganilmoqda...")
        profil_saved = 0

        for topic in profil["topics"]:
            saved = await learn_topic(profil_name, topic)
            profil_saved += saved
            await asyncio.sleep(1)  # API limit

        results[profil_name] = profil_saved
        total += profil_saved
        await p(f"✅ {profil_name}: {profil_saved} ta bilim")

    await p(
        f"\n🎉 Barcha profillar o'qitildi!\n"
        + "\n".join(f"  🎓 {k}: {v} ta" for k,v in results.items())
        + f"\n\n📊 Jami: {total} ta yangi bilim"
    )
    return results

# ══════════════════════════════════════
# AVTOMATIK KUNLIK VAZIFA
# ══════════════════════════════════════
async def daily_auto_train():
    """Har kunda avtomatik ishlaydi — bot o'z-o'zini o'qitadi."""
    print(f"[{datetime.now()}] Avtomatik o'qitish boshlandi...")
    try:
        results = await train_all_profiles()
        total   = sum(results.values())
        print(f"[{datetime.now()}] Yakunlandi: {total} ta yangi bilim")
    except Exception as e:
        print(f"[{datetime.now()}] Auto-train xato: {e}")

async def auto_train_scheduler():
    """24 soatda bir marta ishlaydigan scheduler."""
    while True:
        now = datetime.now()
        # Har kecha 03:00 da ishlaydi
        target_hour = 3
        hours_until = (target_hour - now.hour) % 24
        if hours_until == 0 and now.minute < 5:
            await daily_auto_train()
            await asyncio.sleep(3600)  # 1 soat kutish (qayta ishlamasin)
        else:
            await asyncio.sleep(300)   # 5 daqiqada tekshirish
