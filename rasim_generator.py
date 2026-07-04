"""
rasim_generator.py — Bepul AI rasm yaratish
Hugging Face FLUX.1 → Professional ta'lim rasmlari
Token: huggingface.co → Settings → Access Tokens (BEPUL)
"""
import os, asyncio, aiohttp, psycopg2, re

DATABASE_URL = os.getenv("DATABASE_URL","")
HF_TOKEN     = os.getenv("HF_TOKEN","")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY","")

# Modellar (yaxshidan oddiyga)
MODELS = [
    "black-forest-labs/FLUX.1-schnell",   # Eng yaxshi, tez, bepul
    "stabilityai/stable-diffusion-3.5-large",  # Alternativ
    "runwayml/stable-diffusion-v1-5",     # Zaxira
]

# ══════════════════════════════════════
# PROMPT YARATISH (fan + savoldan)
# ══════════════════════════════════════
SUBJECT_STYLE = {
    "biologiya":   "detailed biological illustration, scientific diagram, textbook style",
    "anatomiya":   "anatomical illustration, medical diagram, labeled, educational",
    "matematika":  "mathematical diagram, geometric shapes, colorful, educational",
    "fizika":      "physics diagram, scientific illustration, clear labels",
    "kimyo":       "chemistry diagram, molecular structure, educational",
    "geografiya":  "geographical map illustration, colorful, educational",
    "tarix":       "historical illustration, educational, detailed",
    "ingliz tili": "English vocabulary card, colorful illustration, simple",
    "ona tili":    "Uzbek language educational illustration, colorful",
    "default":     "educational illustration, colorful, school textbook style",
}

QUALITY_SUFFIX = ", high quality, professional, white background, no text, 4k"

async def build_prompt(question: str, fan: str) -> str:
    """Savol va fan asosida inglizcha prompt yasaydi."""
    fan_lower = fan.lower()
    style = next((v for k,v in SUBJECT_STYLE.items() if k in fan_lower),
                  SUBJECT_STYLE["default"])

    q = question.lower()

    # Mavzuni aniqlash
    if any(w in q for w in ["skelet","suyak","bone"]):
        obj = "human skeleton diagram with labeled bones"
    elif any(w in q for w in ["hujayra","cell"]):
        obj = "cell structure diagram with nucleus, mitochondria, cell wall"
    elif any(w in q for w in ["o'simlik","plant","gul","flower"]):
        obj = "plant anatomy cross-section with roots, stem, leaves, flower"
    elif any(w in q for w in ["hayvon","animal"]):
        obj = "animal anatomy diagram for educational purposes"
    elif any(w in q for w in ["suv","water","aylanish","cycle"]):
        obj = "water cycle diagram showing evaporation, clouds, rain, river"
    elif any(w in q for w in ["nechta","qancha","count","how many"]):
        # Sonni ajratamiz
        nums = re.findall(r'\d+', question)
        n = nums[0] if nums else "5"
        obj = f"{n} colorful cartoon objects for counting exercise"
    elif any(w in q for w in ["uchburchak","kvadrat","doira","geometri"]):
        obj = "geometric shapes diagram circle triangle square rectangle"
    elif any(w in q for w in ["xarita","map","geografiya"]):
        obj = "geographical educational map illustration"
    elif any(w in q for w in ["atom","molekula","element"]):
        obj = "atom and molecule diagram, chemistry educational"
    elif any(w in q for w in ["yorug","nur","light","fizik"]):
        obj = "physics light refraction diagram educational"
    else:
        # Savoldan kalit so'zlar
        words = [w for w in re.findall(r'\w{4,}', question) if not w.isdigit()]
        obj = f"educational illustration about {' '.join(words[:5])}" if words else "educational diagram"

    return f"{obj}, {style}{QUALITY_SUFFIX}"

# ══════════════════════════════════════
# HUGGING FACE BILAN RASM
# ══════════════════════════════════════
async def generate_hf(prompt: str) -> bytes | None:
    """Pollinations.ai — BEPUL, API kerak emas, DNS muammosi yo'q."""
    import urllib.parse
    clean = prompt.replace(",","").replace(".","")[:200]
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean)}?width=768&height=768&nologo=true&model=flux"
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status == 200:
                    data = await r.read()
                    if len(data) > 10000:
                        print(f"✅ Pollinations: {len(data)//1024}KB")
                        return data
    except Exception as e:
        print(f"Pollinations: {e}")
    
    # HF zaxira (token bo'lsa)
    if HF_TOKEN:
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        for model in MODELS:
            hf_url = f"https://api-inference.huggingface.co/models/{model}"
            try:
                async with aiohttp.ClientSession() as s2:
                    async with s2.post(hf_url,
                        json={"inputs": prompt, "parameters": {"num_inference_steps": 4}},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)) as r2:
                        if r2.status == 200:
                            data = await r2.read()
                            if len(data) > 10000: return data
            except Exception as e2:
                print(f"HF {model}: {e2}")
                continue
    return None

# ══════════════════════════════════════
# DALL-E ZAXIRA (agar HF ishlamasa)
# ══════════════════════════════════════
async def generate_dalle(prompt: str) -> bytes | None:
    if not OPENAI_KEY: return None
    try:
        url = "https://api.openai.com/v1/images/generations"
        h = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        body = {"model":"dall-e-3","prompt":prompt,"n":1,
                "size":"1024x1024","quality":"standard"}
        async with aiohttp.ClientSession() as s:
            async with s.post(url,json=body,headers=h,
                              timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status == 200:
                    d = await r.json()
                    img_url = d["data"][0]["url"]
                    async with s.get(img_url) as ir:
                        return await ir.read()
    except Exception as e:
        print(f"DALL-E: {e}")
    return None

# ══════════════════════════════════════
# ASOSIY FUNKSIYA
# ══════════════════════════════════════
async def generate_image(
    question: str,
    fan: str = "ta'lim",
    sinf: str = "1"
) -> bytes | None:
    """
    Savolga mos rasm yaratadi.
    Avval HF FLUX (bepul), keyin DALL-E (pullik zaxira).
    """
    prompt = await build_prompt(question, fan)
    print(f"🎨 Prompt: {prompt[:80]}...")

    # 1. Hugging Face (BEPUL)
    img = await generate_hf(prompt)
    if img:
        print("✅ HF FLUX dan olindi")
        return img

    # 2. DALL-E zaxira
    img = await generate_dalle(prompt)
    if img:
        print("✅ DALL-E dan olindi")
        return img

    print("❌ Hech biri ishlamadi")
    return None

async def generate_and_save(
    topic_code: str, question: str, fan: str,
    sinf: str, img_num: int, bot, chat_id: int
) -> str | None:
    """Rasm yaratib Telegram ga yuboradi va DB ga saqlaydi."""
    name = f"{topic_code}-{img_num}"

    # DB da bormi?
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return row[0]
    except: pass

    img_bytes = await generate_image(question, fan, sinf)
    if not img_bytes: return None

    try:
        from aiogram.types import BufferedInputFile
        sent = await bot.send_photo(
            chat_id,
            BufferedInputFile(img_bytes, f"{name}.png"),
            caption=f"🖼 {name}"
        )
        fid = sent.photo[-1].file_id
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                       ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                   (name, fid))
        conn.commit(); cur.close(); conn.close()
        return fid
    except Exception as e:
        print(f"Telegram: {e}")
    return None

async def generate_topic_images(
    topic_code, fan, sinf, count=20, bot=None, chat_id=0, progress_cb=None
):
    async def p(msg):
        if progress_cb: await progress_cb(msg)

    conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
    cur.execute("""SELECT id,question FROM generated_tests
                   WHERE topic_code=%s ORDER BY id LIMIT %s""",
               (topic_code, count))
    tests = cur.fetchall(); cur.close(); conn.close()

    created = skipped = errors = 0
    for i,(tid,question) in enumerate(tests,1):
        await p(f"🖼 {i}/{len(tests)} rasm yaratilmoqda...")
        try:
            fid = await generate_and_save(topic_code,question,fan,sinf,i,bot,chat_id)
            if fid:
                conn2=psycopg2.connect(DATABASE_URL);cur2=conn2.cursor()
                cur2.execute("UPDATE generated_tests SET image_url=%s WHERE id=%s",
                            (f"{topic_code}-{i}",tid))
                conn2.commit();cur2.close();conn2.close()
                created += 1
            else: skipped += 1
        except: errors += 1
        await asyncio.sleep(3)

    await p(f"✅ {created} rasm | ⏭ {skipped} o'tkazildi | ❌ {errors} xato")
    return {"created":created,"skipped":skipped,"errors":errors}


# ══════════════════════════════════════
# RASM O'QITISH — MAVZULAR BO'YICHA
# ══════════════════════════════════════
RASM_MAVZULAR = {
    "biologiya": [
        ("inson_skeleti", "human skeleton with labeled bones, anatomical diagram"),
        ("hujayra", "plant and animal cell structure, detailed educational diagram"),
        ("oshqozon", "human digestive system diagram, labeled organs"),
        ("yurak", "human heart anatomy, labeled diagram, educational"),
        ("miya", "human brain anatomy diagram, labeled regions"),
        ("o_simlik", "plant anatomy showing roots stem leaves flower, cross-section"),
        ("hasharot", "insect body parts diagram, labeled, educational"),
        ("baliq", "fish anatomy diagram, labeled organs, educational"),
    ],
    "fizika": [
        ("zig_zag_nur", "light refraction through prism, physics diagram, colorful"),
        ("elektr", "simple electric circuit diagram, battery bulb switch"),
        ("magnit", "magnetic field lines around bar magnet, educational diagram"),
        ("to_lqin", "wave types longitudinal transverse, physics educational"),
    ],
    "kimyo": [
        ("suv_molekula", "water molecule H2O structure, chemistry diagram"),
        ("atom", "atom structure with protons neutrons electrons, educational"),
        ("davriy_jadval", "periodic table of elements, colorful educational chart"),
    ],
    "matematika": [
        ("geometrik", "geometric shapes circle square triangle rectangle, colorful, labeled"),
        ("koordinat", "coordinate system XY axis, educational diagram"),
        ("kasrlar", "visual fractions pizza pie chart showing 1/2 1/3 1/4, colorful"),
        ("son_o_qi", "number line 1 to 10, colorful, educational for kids"),
    ],
    "geografiya": [
        ("yer", "layers of Earth cross-section, core mantle crust, educational"),
        ("ob_havo", "weather cycle diagram, clouds rain sun, educational"),
        ("suv_aylanishi", "water cycle diagram evaporation condensation rain, educational"),
    ],
}

async def auto_generate_subject_images(fan: str, bot, chat_id: int, progress_cb=None):
    """Fan uchun barcha bazaviy rasmlarni yaratadi."""
    async def p(msg):
        if progress_cb: await progress_cb(msg)

    subjects = {k:v for k,v in RASM_MAVZULAR.items() if k in fan.lower()}
    if not subjects:
        subjects = RASM_MAVZULAR

    created = 0
    for subj, items in subjects.items():
        await p(f"📚 {subj} rasmlari yaratilmoqda...")
        for name, prompt in items:
            full_prompt = f"{prompt}, professional educational illustration, white background, no text, high quality"
            img = await generate_hf(full_prompt)
            if not img:
                img = await generate_dalle(full_prompt) if OPENAI_KEY else None
            if img:
                try:
                    from aiogram.types import BufferedInputFile
                    sent = await bot.send_photo(
                        chat_id,
                        BufferedInputFile(img, f"{name}.png"),
                        caption=f"🖼 {subj}-{name}"
                    )
                    fid = sent.photo[-1].file_id
                    conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
                    cur.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                                   ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                               (f"{subj}-{name}", fid))
                    conn.commit(); cur.close(); conn.close()
                    created += 1
                    await p(f"✅ {subj}-{name}")
                except Exception as e:
                    await p(f"❌ {name}: {e}")
            await asyncio.sleep(3)

    await p(f"\n🎉 {created} ta rasm yaratildi va saqlandi!")
    return created
