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

# ══════════════════════════════════════
# USLUBLAR
# ══════════════════════════════════════
STYLES = {
    "multik":   {
        "prompt": "cute cartoon style, Disney Pixar animation, vibrant colors, child-friendly, smooth lines",
        "model": "flux",
        "seed": 42
    },
    "hayotiy":  {
        "prompt": "ultra realistic photography style, photorealistic, DSLR camera, natural lighting, 8k",
        "model": "flux-realism",
        "seed": 100
    },
    "chizma":   {
        "prompt": "hand-drawn pencil sketch, detailed line art, black and white, educational diagram style",
        "model": "flux",
        "seed": 200
    },
    "akvarell": {
        "prompt": "watercolor painting, soft pastel colors, artistic brush strokes, dreamy atmosphere",
        "model": "flux",
        "seed": 300
    },
    "darslik":  {
        "prompt": "textbook scientific illustration, clean technical diagram, labeled, professional educational",
        "model": "flux",
        "seed": 400
    },
    "3d":       {
        "prompt": "3D render, Blender CGI, volumetric lighting, vibrant colors, smooth surfaces, professional",
        "model": "flux",
        "seed": 500
    },
    "komiks":   {
        "prompt": "comic book style, bold black outlines, flat bright colors, manga inspired, expressive",
        "model": "flux",
        "seed": 600
    },
}

DEFAULT_STYLE = "multik"  # Bolalar uchun default

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

def get_quality_suffix(style: str = "multik") -> str:
    style_cfg = STYLES.get(style, STYLES["multik"])
    if isinstance(style_cfg, dict):
        style_desc = style_cfg.get("prompt","")
    else:
        style_desc = str(style_cfg)
    return f"{style_desc}, high quality, white background, no text"

async def build_prompt(question: str, fan: str, style: str = "multik") -> str:
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

    return f"{obj}, {get_quality_suffix(style)}"

# ══════════════════════════════════════
# HUGGING FACE BILAN RASM
# ══════════════════════════════════════
async def generate_hf(prompt: str, style: str = "multik") -> bytes | None:
    """Pollinations.ai — BEPUL, API kerak emas, DNS muammosi yo'q."""
    import urllib.parse
    style_cfg = STYLES.get(style, STYLES["multik"])
    model = style_cfg.get("model", "flux")
    seed  = style_cfg.get("seed", 42)
    clean = prompt[:300]
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(clean)}?width=768&height=768&nologo=true&model={model}&seed={seed}"
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

    img_bytes = await generate_image(question, fan, sinf, style=style if 'style' in dir() else 'multik')
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


# ══════════════════════════════════════
# EXCEL DAN RASM YARATISH
# ══════════════════════════════════════
async def generate_from_excel(
    excel_bytes: bytes,
    bot,
    chat_id: int,
    progress_cb=None,
    style: str = "multik"
) -> dict:
    """
    RASMLAR varog'i bor Excel dan:
    Kod-N | Mavzu | Rasm tavsifi
    → Har birini chizib DB ga saqlaydi
    """
    import openpyxl
    from io import BytesIO

    async def p(msg):
        if progress_cb: await progress_cb(msg)

    wb = openpyxl.load_workbook(BytesIO(excel_bytes), data_only=True)

    if "RASMLAR" not in wb.sheetnames:
        return {"error": "RASMLAR varog'i topilmadi!"}

    ws_r = wb["RASMLAR"]

    # MALUMOT varaqdan sinf/fan info
    topic_info = {}
    if "MALUMOT" in wb.sheetnames:
        ws_m = wb["MALUMOT"]
        for r in range(2, ws_m.max_row+1):
            tc   = ws_m.cell(r,2).value
            sinf = ws_m.cell(r,3).value
            fan  = ws_m.cell(r,4).value
            mav  = ws_m.cell(r,9).value
            if tc: topic_info[str(tc)] = {"sinf":str(sinf or "1"),"fan":str(fan or "ta'lim"),"mavzu":str(mav or "")}

    # Rasm ro'yxatini yig'amiz
    items = []
    for r in range(2, ws_r.max_row+1):
        kod  = ws_r.cell(r,1).value
        mav  = ws_r.cell(r,2).value
        tavs = ws_r.cell(r,3).value
        if kod and tavs:
            tc   = "-".join(str(kod).split("-")[:-1])
            info = topic_info.get(tc, {})
            items.append({
                "kod":   str(kod),
                "tavsif": str(tavs),
                "mavzu":  str(mav or ""),
                "sinf":   info.get("sinf","1"),
                "fan":    info.get("fan","ta'lim"),
            })

    if not items:
        return {"error": "RASMLAR varog'ida ma'lumot yo'q!"}

    await p(f"🖼 {len(items)} ta rasm yaratiladi...\n⏱ Taxminan {len(items)*8//60} daqiqa")

    # DB da allaqachon bor bo'lganlarni o'tkazib yuboramiz
    existing = set()
    try:
        kods = [item["kod"] for item in items]
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        ph = ",".join(["%s"]*len(kods))
        cur.execute(f"SELECT name FROM images WHERE name IN ({ph})", kods)
        existing = {r[0] for r in cur.fetchall()}
        cur.close(); conn.close()
    except: pass

    todo = [item for item in items if item["kod"] not in existing]
    skipped = len(existing)
    created = errors = 0

    await p(f"📊 Jami: {len(items)} | Yangi: {len(todo)} | O\'tkazildi: {skipped}")

    # Parallel — 3 ta bir vaqtda
    BATCH = 3

    async def process_one(item, idx):
        nonlocal created, errors
        kod  = item["kod"]
        tavs = item["tavsif"]
        sinf = item["sinf"]
        fan  = item["fan"]
        try:
            prompt = await _tavsif_to_prompt(tavs, fan, sinf)
            if style != "multik":
                prompt += f", {get_quality_suffix(style)}"
            img = await generate_hf(prompt, style=style)
            if img:
                from aiogram.types import BufferedInputFile
                sent = await bot.send_photo(
                    chat_id,
                    BufferedInputFile(img, f"{kod}.png"),
                    caption=f"🖼 {kod}"
                )
                fid = sent.photo[-1].file_id
                conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
                cur.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                               ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                           (kod, fid))
                conn.commit(); cur.close(); conn.close()
                created += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
            print(f"Rasm {kod}: {e}")

    for i in range(0, len(todo), BATCH):
        batch = todo[i:i+BATCH]
        tasks = [process_one(item, i+j+1) for j,item in enumerate(batch)]
        await asyncio.gather(*tasks)
        done = min(i+BATCH, len(todo))
        pct  = round(done*100/len(todo)) if todo else 100
        await p(f"⏳ {pct}% ({done}/{len(todo)}) | ✅{created} | ❌{errors}")
        await asyncio.sleep(1)

    await p(
        f"🎉 Tayyor!\n"
        f"✅ Yaratildi: {created} ta\n"
        f"⏭ O'tkazildi: {skipped} ta (allaqachon bor)\n"
        f"❌ Xato: {errors} ta"
    )
    return {"created": created, "skipped": skipped, "errors": errors}


async def _tavsif_to_prompt(tavsif: str, fan: str, sinf: str) -> str:
    """O'zbek tavsifdan ingliz prompt yasaydi."""
    import os as _os
    _gemini_key = _os.getenv("GEMINI_API_KEY","")
    # Gemini bilan tarjima
    if _gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={_gemini_key}"
            req = f"""Translate this Uzbek image description to English for AI image generation.
Make it suitable for a {sinf}st grade {fan} educational illustration.
Keep it simple, cartoon style, child-friendly.
Uzbek: {tavsif}
Return ONLY the English prompt, max 30 words."""
            async with aiohttp.ClientSession() as sess:
                body = {
                    "contents": [{"parts": [{"text": req}]}],
                    "generationConfig": {"maxOutputTokens": 80}
                }
                async with sess.post(url, json=body,
                    timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        d = await r.json()
                        return d["candidates"][0]["content"]["parts"][0]["text"].strip() + ", educational cartoon, white background, colorful, child-friendly, no text"
        except: pass

    # Fallback — oddiy tarjima qoidalari
    t = tavsif.lower()
    words_map = {
        "bola":"child","ona":"mother","ota":"father","tinglayapti":"listening",
        "yordam":"helping","deyapti":"saying","o'qituvchi":"teacher",
        "sinfdosh":"classmate","do'st":"friend","o'yin":"playing",
        "maktab":"school","dars":"lesson","kitob":"book",
    }
    eng = tavsif
    for uz, en in words_map.items():
        eng = eng.replace(uz, en)
    return f"{eng}, grade {sinf} educational illustration, cartoon style, white background, colorful, no text"
