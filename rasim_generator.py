"""
rasim_generator.py — AI rasm yaratish
Pollinations.ai (FLUX) — bepul, to'g'ridan prompt
"""
import os, asyncio, aiohttp, psycopg2, re, urllib.parse

DATABASE_URL = os.getenv("DATABASE_URL","")
OPENAI_KEY   = os.getenv("OPENAI_API_KEY","")

# ══════════════════════════════════════
# USLUBLAR
# ══════════════════════════════════════
STYLES = {
    "multik":   "cute cartoon style, Disney Pixar, vibrant colors, child-friendly",
    "hayotiy":  "realistic photo style, photorealistic, natural lighting",
    "chizma":   "hand-drawn pencil sketch, educational diagram, clean lines",
    "akvarell": "watercolor painting, soft pastel colors, artistic",
    "darslik":  "textbook scientific illustration, educational diagram, labeled",
    "3d":       "3D render, CGI, vibrant colors, professional",
    "komiks":   "comic book style, bold outlines, bright colors, fun",
}
DEFAULT_SUFFIX = "white background, no text, no letters, high quality, 4k"

def get_quality_suffix(style: str = "multik") -> str:
    style_desc = STYLES.get(style, STYLES["multik"])
    return f"{style_desc}, {DEFAULT_SUFFIX}"

# ══════════════════════════════════════
# O'ZBEK → INGLIZ LEKSIKA
# ══════════════════════════════════════
UZ_EN = {
    # Ranglar
    "och ko'k":"light blue","to'q ko'k":"dark blue","och yashil":"light green",
    "to'q yashil":"dark green","och sariq":"light yellow","yorqin":"bright",
    "och":"light","to'q":"dark","rangdagi":"colored","kulrang":"gray",
    "jigarrang":"brown","binafsha":"purple","qizil":"red","ko'k":"blue",
    "yashil":"green","sariq":"yellow","oq":"white","qora":"black",
    "pushti":"pink","to'q sariq":"orange","oltin":"golden",
    # Fon/joy
    "fon":"background","maydon":"field","osmon":"sky","dalada":"in field",
    "o'rtada":"in the center","pastda":"below","yuqorida":"above",
    "o'ng tomonda":"on the right","chap tomonda":"on the left",
    # Tabiat
    "quyosh":"sun","oy":"moon","yulduz":"star","bulut":"cloud",
    "yomg'ir":"rain","qor":"snow","shamol":"wind","tog'":"mountain",
    "daryo":"river","dengiz":"sea","ko'l":"lake","o'rmon":"forest",
    "daraxt":"tree","gul":"flower","o't":"grass","barg":"leaf",
    "plyaj":"beach","qumli":"sandy",
    # Fasl
    "yoz":"summer","qish":"winter","bahor":"spring","kuz":"autumn",
    "issiq":"hot","sovuq":"cold",
    # Odam/harakatlar
    "bola":"child","bolalar":"children","qiz":"girl","o'g'il":"boy",
    "o'quvchi":"student","o'qituvchi":"teacher","odam":"person",
    "ona":"mother","ota":"father","oila":"family",
    "o'tirmoqda":"sitting","turmoqda":"standing","yugurmoqda":"running",
    "o'ynamoqda":"playing","o'qimoqda":"reading","yozmoqda":"writing",
    "gapirmoqda":"talking","kulib":"smiling","charaqlab":"shining",
    "turibdi":"is standing","o'tiribo":"sitting",
    # Hayvon
    "mushuk":"cat","it":"dog","baliq":"fish","qush":"bird",
    "ot":"horse","sigir":"cow","qo'y":"sheep","tovuq":"chicken",
    "kapalak":"butterfly","hasharot":"insect",
    # Ob-havo
    "qorli":"snowy","yomg'irli":"rainy","quyoshli":"sunny",
    "bulutli":"cloudy","sovuq":"cold","issiq":"hot",
    # Maktab
    "maktab":"school","sinf":"classroom","dars":"lesson",
    "kitob":"book","qalam":"pencil","daftar":"notebook","doska":"blackboard",
    # Meva/sabzavot
    "olma":"apple","banan":"banana","uzum":"grapes","nok":"pear",
    "tarvuz":"watermelon","sabzi":"carrot","pomidor":"tomato",
    # Boshqa
    "uy":"house","shahar":"city","ko'cha":"street",
    "velosiped":"bicycle","mashina":"car","avtobus":"bus",
    "sport":"sports","futbol":"football","suzish":"swimming",
    "ikkita":"two","uchta":"three","to'rtta":"four","bitta":"one",
    "katta":"big","kichik":"small","baland":"tall","past":"short",
    # Ko'makchi so'zlar (o'chirish)
    "bilan":"","va":"","ham":"","ning":"","uchun":"","da":"","ga":"",
    "ni":"","dan":"","lar":"","ta":"","tadi":"","moqda":"","yotibdi":"",
}

def uz_to_en_prompt(tavsif: str) -> str:
    """Uzb tavsifni inglizcha promptga o'giradi."""
    t = tavsif.lower()
    # Avval ko'p so'zli iboralarni
    for uz, en in UZ_EN.items():
        if " " in uz:
            t = t.replace(uz, en)
    # Keyin yakka so'zlarni
    words = t.split()
    result_words = []
    for w in words:
        clean = re.sub(r"[^a-zA-Z0\u2018\u2019'-]", "", w)
        translated = UZ_EN.get(clean, UZ_EN.get(w, w))
        if translated:  # bo'sh string bo'lsa o'tkazib yuborish
            result_words.append(translated)
    result = " ".join(result_words)
    # Uzb harflarini olib tashlaymiz
    result = re.sub(r"[o'ʻgʻ]", "", result)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

async def _tavsif_to_prompt(tavsif: str, fan: str, sinf: str, style: str = "multik") -> str:
    """Tavsifdan rasm prompti yasaydi."""
    # Gemini yordamida tarjima
    gemini_key = os.getenv("GEMINI_API_KEY","")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            body = {
                "contents": [{"parts": [{"text":
                    f"Translate to English for AI image generation. "
                    f"Grade {sinf} {fan} educational illustration. "
                    f"Child-friendly, cartoon style. "
                    f"Description: {tavsif}\n"
                    f"Return ONLY the English prompt, max 25 words, no explanation."
                }]}],
                "generationConfig": {"maxOutputTokens": 60}
            }
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=body,
                                  timeout=aiohttp.ClientTimeout(total=8)) as r:
                    if r.status == 200:
                        d = await r.json()
                        eng = d["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return f"{eng}, {get_quality_suffix(style)}"
        except: pass

    # Fallback — lug'at orqali
    eng = uz_to_en_prompt(tavsif)
    return f"{eng}, grade {sinf} educational illustration, {get_quality_suffix(style)}"

# ══════════════════════════════════════
# POLLINATIONS.AI — BEPUL
# ══════════════════════════════════════
async def generate_hf(prompt: str, style: str = "multik") -> bytes | None:
    """Pollinations.ai FLUX bilan rasm yaratadi."""
    clean = prompt[:300].replace('"',"'")
    url = (f"https://image.pollinations.ai/prompt/"
           f"{urllib.parse.quote(clean)}"
           f"?width=768&height=768&nologo=true&model=flux&seed=42")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status == 200:
                    data = await r.read()
                    if len(data) > 5000:
                        return data
    except Exception as e:
        print(f"Pollinations xato: {e}")
    return None

async def generate_dalle(prompt: str) -> bytes | None:
    """DALL-E 3 zaxira."""
    if not OPENAI_KEY: return None
    try:
        url = "https://api.openai.com/v1/images/generations"
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        body = {"model":"dall-e-3","prompt":prompt,"n":1,
                "size":"1024x1024","quality":"standard"}
        async with aiohttp.ClientSession() as s:
            async with s.post(url,json=body,headers=headers,
                              timeout=aiohttp.ClientTimeout(total=60)) as r:
                if r.status == 200:
                    d = await r.json()
                    img_url = d["data"][0]["url"]
                    async with s.get(img_url) as ir:
                        return await ir.read()
    except Exception as e:
        print(f"DALL-E xato: {e}")
    return None

async def generate_image(question: str, fan: str = "ta'lim",
                         sinf: str = "1", style: str = "multik") -> bytes | None:
    """Savol asosida rasm yaratadi."""
    prompt = await _tavsif_to_prompt(question, fan, sinf, style)
    img = await generate_hf(prompt, style)
    if not img: img = await generate_dalle(prompt)
    return img

async def generate_and_save(topic_code, question, fan, sinf,
                            img_num, bot, chat_id, style="multik") -> str | None:
    name = f"{topic_code}-{img_num}"
    try:
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return row[0]
    except: pass

    img_bytes = await generate_image(question, fan, sinf, style)
    if not img_bytes: return None
    try:
        from aiogram.types import BufferedInputFile
        sent = await bot.send_photo(
            chat_id, BufferedInputFile(img_bytes, f"{name}.png"),
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
        print(f"Saqlash xato: {e}")
    return None

async def generate_from_excel(excel_bytes, bot, chat_id,
                              progress_cb=None, style="multik",
                              force=False) -> dict:
    import openpyxl
    from io import BytesIO

    async def p(msg):
        if progress_cb: await progress_cb(msg)

    wb = openpyxl.load_workbook(BytesIO(excel_bytes), data_only=True)
    if "RASMLAR" not in wb.sheetnames:
        return {"error": "RASMLAR varog'i topilmadi!"}

    ws_r = wb["RASMLAR"]
    topic_info = {}
    if "MALUMOT" in wb.sheetnames:
        ws_m = wb["MALUMOT"]
        for r in range(2, ws_m.max_row+1):
            tc   = ws_m.cell(r,2).value
            sinf = ws_m.cell(r,3).value
            fan  = ws_m.cell(r,4).value
            if tc: topic_info[str(tc)] = {"sinf":str(sinf or "1"),"fan":str(fan or "ta'lim")}

    items = []
    for r in range(2, ws_r.max_row+1):
        kod  = ws_r.cell(r,1).value
        mav  = ws_r.cell(r,2).value
        tavs = ws_r.cell(r,3).value
        if kod and tavs:
            tc   = "-".join(str(kod).split("-")[:-1])
            info = topic_info.get(tc, {})
            items.append({"kod":str(kod),"tavsif":str(tavs),
                         "sinf":info.get("sinf","1"),"fan":info.get("fan","ta'lim")})

    if not items:
        return {"error": "RASMLAR varog'ida ma'lumot yo'q!"}

    # DB da borlarni filtrlash
    existing = set()
    try:
        kods = [item["kod"] for item in items]
        conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
        ph = ",".join(["%s"]*len(kods))
        cur.execute(f"SELECT name FROM images WHERE name IN ({ph})", kods)
        existing = {r[0] for r in cur.fetchall()}
        cur.close(); conn.close()
    except: pass

    todo = items if force else [it for it in items if it["kod"] not in existing]
    skipped = 0 if force else len(existing)
    await p(f"📊 Jami: {len(items)} | Yangi: {len(todo)} | O'tkazildi: {skipped}")

    created = errors = 0
    for i in range(0, len(todo), 3):
        batch = todo[i:i+3]
        tasks = []
        for item in batch:
            async def one(it):
                nonlocal created, errors
                try:
                    prompt = await _tavsif_to_prompt(it["tavsif"],it["fan"],it["sinf"],style)
                    img = await generate_hf(prompt, style)
                    if img:
                        from aiogram.types import BufferedInputFile
                        sent = await bot.send_photo(
                            chat_id, BufferedInputFile(img,f"{it['kod']}.png"),
                            caption=f"🖼 {it['kod']}"
                        )
                        fid = sent.photo[-1].file_id
                        c2=psycopg2.connect(DATABASE_URL);cu2=c2.cursor()
                        cu2.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                            ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                            (it["kod"],fid))
                        c2.commit();cu2.close();c2.close()
                        created += 1
                    else: errors += 1
                except Exception as e:
                    errors += 1
                    print(f"rasm xato {it['kod']}: {e}")
            tasks.append(one(item))
        await asyncio.gather(*tasks)
        done = min(i+3, len(todo))
        pct = round(done*100/len(todo)) if todo else 100
        await p(f"⏳ {pct}% ({done}/{len(todo)}) | ✅{created} | ❌{errors}")
        await asyncio.sleep(2)

    await p(f"🎉 Tayyor!\n✅ {created} ta | ⏭ {skipped} ta | ❌ {errors} ta")
    return {"created":created,"skipped":skipped,"errors":errors}

async def generate_topic_images(topic_code, fan, sinf, count=20,
                                bot=None, chat_id=0, progress_cb=None, style="multik"):
    async def p(msg):
        if progress_cb: await progress_cb(msg)
    conn = psycopg2.connect(DATABASE_URL); cur = conn.cursor()
    cur.execute("SELECT id,question FROM generated_tests WHERE topic_code=%s ORDER BY id LIMIT %s",
               (topic_code, count))
    tests = cur.fetchall(); cur.close(); conn.close()
    created = skipped = errors = 0
    for i,(tid,question) in enumerate(tests,1):
        await p(f"🖼 {i}/{len(tests)} rasm...")
        try:
            fid = await generate_and_save(topic_code,question,fan,sinf,i,bot,chat_id,style)
            if fid:
                c2=psycopg2.connect(DATABASE_URL);cu2=c2.cursor()
                cu2.execute("UPDATE generated_tests SET image_url=%s WHERE id=%s",
                           (f"{topic_code}-{i}",tid))
                c2.commit();cu2.close();c2.close()
                created += 1
            else: skipped += 1
        except: errors += 1
        await asyncio.sleep(3)
    await p(f"✅ {created} | ⏭ {skipped} | ❌ {errors}")
    return {"created":created,"skipped":skipped,"errors":errors}

async def auto_generate_subject_images(fan, bot, chat_id, progress_cb=None):
    async def p(msg):
        if progress_cb: await progress_cb(msg)
    SUBJECTS = {
        "biologiya": [
            ("biologiya-skelet","human skeleton labeled bones educational"),
            ("biologiya-hujayra","plant cell animal cell structure diagram"),
            ("biologiya-yurak","human heart anatomy labeled educational"),
        ],
        "matematika": [
            ("matematika-geometriya","geometric shapes circle square triangle rectangle colorful"),
            ("matematika-kasrlar","fractions visual pie chart 1/2 1/3 1/4 educational"),
        ],
    }
    created = 0
    for subj, items in SUBJECTS.items():
        if fan.lower() not in subj and fan.lower() != "all": continue
        for name, prompt in items:
            full = f"{prompt}, educational illustration, white background, no text"
            img = await generate_hf(full)
            if img:
                try:
                    from aiogram.types import BufferedInputFile
                    sent = await bot.send_photo(
                        chat_id, BufferedInputFile(img,f"{name}.png"),
                        caption=f"🖼 {name}"
                    )
                    fid = sent.photo[-1].file_id
                    c=psycopg2.connect(DATABASE_URL);cu=c.cursor()
                    cu.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                        ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",
                        (name,fid))
                    c.commit();cu.close();c.close()
                    created += 1
                    await p(f"✅ {name}")
                except Exception as e:
                    await p(f"❌ {name}: {e}")
            await asyncio.sleep(3)
    await p(f"🎉 {created} ta rasm saqlandi!")
    return created
