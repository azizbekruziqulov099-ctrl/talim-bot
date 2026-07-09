"""rasim_generator.py — Gemini tarjima (bepul) + Cloudflare FLUX (bepul)"""
import os, aiohttp, base64

CF_ACCOUNT = os.getenv("CF_ACCOUNT_ID", "")
CF_TOKEN = os.getenv("CF_API_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
TOGETHER_KEY = os.getenv("TOGETHER_API_KEY", "")

CF_FLUX = "@cf/black-forest-labs/flux-1-schnell"

STYLE_MAP = {
    "multik": "colorful cartoon illustration, child-friendly, clean lines, vibrant colors",
    "realistik": "photorealistic, natural lighting, high detail, sharp focus",
    "chizma": "clean educational diagram, labeled, simple line art, white background",
    "3d": "3D render, soft studio lighting, high quality",
    "akvarel": "watercolor painting, soft colors, artistic",
}


async def _gemini_prompt(tavsif, mavzu="", grade="", style_desc=""):
    """Gemini 2.5 Flash tarjima — BEPUL (1500/kun)."""
    if not GEMINI_KEY:
        return None
    try:
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}")
        instruction = (
            "You are an expert FLUX image-prompt writer. The user writes in Uzbek. "
            "Produce ONE English image prompt.\n\n"
            "CRITICAL RULES:\n"
            "1. Preserve EXACT numbers. '3 ta olma' = 'three apples' (not 'some apples').\n"
            "2. NEVER drop ANY item the user listed. If they list several colors or "
            "counts, EVERY single one must appear in the prompt. Losing even one is a failure.\n"
            "3. If the user's counts conflict (e.g. says '3 apples' then lists 6), "
            "ignore the total and keep EVERY listed group. Then state the real total.\n"
            "4. Preserve EXACT colors, sizes, positions, actions the user stated.\n"
            "5. Do NOT add objects the user did not mention.\n"
            "6. Add ONLY: lighting, camera angle, background, texture, mood.\n"
            "7. Output ONLY the prompt. No quotes, no explanation, no 'Prompt:' prefix.\n"
            "8. Length 150-320 characters. Never cut off mid-sentence.\n"
            "9. If people appear: they must be Central Asian / Uzbek "
            "(light-tan skin, dark hair). Write 'Uzbek children', 'Central Asian teacher'. "
            "NEVER produce Indian, African, or East Asian people unless the user asks.\n"
            "10. Settings default to a modern Uzbek school/home unless stated otherwise.\n\n"
            "EXAMPLES:\n"
            "Uzbek: 3 ta qizil olma stolda\n"
            "Prompt: Three red apples arranged on a wooden table, soft natural window light "
            "from the left, shallow depth of field, warm tones, photorealistic, sharp focus\n\n"
            "Uzbek: 3 ta olma 1 sariq 2 qizil 3 yashil\n"
            "Prompt: Six apples on a plain white surface: one yellow apple, two red apples, "
            "and three green apples, all clearly separated and countable, even soft lighting, "
            "top-down view, bright colors, sharp focus\n\n"
            "Uzbek: maktabda dars, o'qituvchi doskada yozmoqda\n"
            "Prompt: An Uzbek teacher writing on a blackboard in a bright modern classroom, "
            "Central Asian children seated at desks facing forward, morning sunlight through "
            "windows, warm educational atmosphere, detailed illustration\n\n"
            "Uzbek: uchburchak va kvadrat\n"
            "Prompt: A clean geometric diagram showing one triangle and one square side by "
            "side, black outlines on white background, simple flat vector style, educational\n\n"
            f"STYLE TO APPLY: {style_desc}\n\n"
            f"Uzbek: {tavsif}\n"
            f"Context: {mavzu} {grade}\n"
            "Prompt:"
        )
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json={
                "contents": [{"parts": [{"text": instruction}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500,
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            }, timeout=aiohttp.ClientTimeout(total=25)) as r:
                data = await r.json()
                cand = (data.get("candidates") or [{}])[0]
                # Token tugab qolganmi?
                if cand.get("finishReason") == "MAX_TOKENS":
                    print("[gemini] javob qirqildi (MAX_TOKENS)")
                    return None
                txt = cand["content"]["parts"][0]["text"].strip()
                for pre in ("Prompt:", "prompt:", "PROMPT:"):
                    if txt.startswith(pre): txt = txt[len(pre):].strip()
                txt = txt.strip('"').strip("'").replace("\n", " ").strip()
                # Juda qisqa yoki qirqilgan bo'lsa qabul qilmaymiz
                if len(txt) < 40:
                    print(f"[gemini] juda qisqa ({len(txt)}): {txt}")
                    return None
                print(f"[gemini] OK ({len(txt)}) -> {txt[:110]}")
                return txt
    except Exception as e:
        print(f"[gemini] xato: {e}")
        return None


async def _openai_prompt(tavsif, mavzu="", grade="", style_desc=""):
    """GPT-4o-mini — zaxira tarjima."""
    if not OPENAI_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": [
                    {"role": "system", "content":
                        "Convert Uzbek image description to a precise English FLUX prompt. "
                        "NEVER drop any item the user listed — every color and count must appear. "
                        "If counts conflict, keep all listed groups and state the real total. "
                        "Be EXACT about counts, colors, objects, positions. "
                        "If people appear, they MUST be Uzbek/Central Asian (light-tan skin, "
                        "dark hair). Never Indian, African, or East Asian unless asked. "
                        f"Style: {style_desc}. Return ONLY the prompt, 150-320 chars."},
                    {"role": "user", "content": f"Uzbek: {tavsif}\nContext: {mavzu} {grade}"}],
                    "max_tokens": 300, "temperature": 0.2},
                timeout=aiohttp.ClientTimeout(total=25)
            ) as r:
                data = await r.json()
                print("[gpt] OK")
                return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[gpt] xato: {e}")
        return None


async def _tavsif_to_prompt(tavsif, mavzu="", grade="", style="realistik"):
    """Tarjima: Gemini (bepul) -> GPT (zaxira) -> oddiy."""
    style_desc = STYLE_MAP.get(style, "high quality, detailed, sharp focus")
    p = await _gemini_prompt(tavsif, mavzu, grade, style_desc)
    if not p:
        p = await _openai_prompt(tavsif, mavzu, grade, style_desc)
    if not p:
        p = f"{tavsif}. {style_desc}"

    # Odam bor bo'lsa — markaziy osiyolik bo'lishini kafolatlaymiz
    low = p.lower()
    human_words = ("child", "children", "kid", "boy", "girl", "teacher", "student",
                   "people", "person", "man", "woman", "pupil", "family")
    if any(w in low for w in human_words):
        if not any(w in low for w in ("uzbek", "central asian")):
            p = p + ", Uzbek Central Asian people"
    return p


def _is_limit_error(txt: str) -> bool:
    """Cloudflare neuron limiti tugaganini aniqlaydi."""
    t = (txt or "").lower()
    keys = ("quota", "exceeded", "limit", "credits", "capacity",
            "3036", "10000", "neuron", "too many requests", "rate limit")
    return any(k in t for k in keys)


async def generate_cf_flux_ex(prompt, steps=4):
    """Cloudflare FLUX. Qaytaradi (rasm_bytes, xato).
    xato: None | 'limit' | 'no_key' | 'other'"""
    if not (CF_ACCOUNT and CF_TOKEN):
        return None, "no_key"
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/{CF_FLUX}"
        import random
        async with aiohttp.ClientSession() as s:
            async with s.post(
                url,
                headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"},
                json={"prompt": prompt[:2000], "steps": min(steps, 8),
                      "seed": random.randint(1, 999999)},
                timeout=aiohttp.ClientTimeout(total=90)
            ) as r:
                raw = await r.text()
                if r.status == 429:
                    print("[cf] LIMIT (429)")
                    return None, "limit"
                try:
                    data = await r.json(content_type=None)
                except Exception:
                    data = {}
                if not data.get("success"):
                    msg = str(data)[:300]
                    if _is_limit_error(msg) or _is_limit_error(raw[:300]):
                        print(f"[cf] LIMIT: {msg[:120]}")
                        return None, "limit"
                    print(f"[cf] xato: {msg[:150]}")
                    return None, "other"
                b64 = data["result"].get("image")
                if b64:
                    print("[cf] OK flux-1-schnell")
                    return base64.b64decode(b64), None
                return None, "other"
    except Exception as e:
        print(f"[cf] xato: {e}")
        return None, "other"


async def generate_cf_flux(prompt, steps=4):
    """Cloudflare Workers AI FLUX — BEPUL (10k neuron/kun)."""
    img, _ = await generate_cf_flux_ex(prompt, steps)
    return img


async def _generate_cf_flux_old(prompt, steps=4):
    """Cloudflare Workers AI FLUX — BEPUL (10k neuron/kun)."""
    if not (CF_ACCOUNT and CF_TOKEN):
        print("[cf] CF_ACCOUNT_ID yoki CF_API_TOKEN yo'q")
        return None
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/ai/run/{CF_FLUX}"
        import random
        async with aiohttp.ClientSession() as s:
            async with s.post(
                url,
                headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"},
                json={"prompt": prompt[:2000], "steps": min(steps, 8),
                      "seed": random.randint(1, 999999)},
                timeout=aiohttp.ClientTimeout(total=90)
            ) as r:
                data = await r.json()
                if not data.get("success"):
                    print(f"[cf] xato: {str(data)[:200]}")
                    return None
                b64 = data["result"].get("image")
                if b64:
                    print("[cf] OK flux-1-schnell")
                    return base64.b64decode(b64)
    except Exception as e:
        print(f"[cf] xato: {e}")
    return None


async def generate_pollinations(prompt, width=1024, height=1024, model="flux"):
    """Pollinations.ai — BEPUL, CHEKSIZ, kalitsiz. FLUX modeli."""
    import random, urllib.parse
    try:
        enc = urllib.parse.quote(prompt[:1500], safe="")
        url = (f"https://image.pollinations.ai/prompt/{enc}"
               f"?width={width}&height={height}&model={model}"
               f"&nologo=true&private=true&seed={random.randint(1,999999)}")
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=120)) as r:
                ctype = (r.headers.get("content-type") or "").lower()
                if r.status != 200:
                    print(f"[pollinations] status {r.status}")
                    return None
                if "image" not in ctype:
                    body = (await r.text())[:120]
                    print(f"[pollinations] rasm emas ({ctype}): {body}")
                    return None
                data = await r.read()
                if len(data) < 1000:
                    print(f"[pollinations] juda kichik ({len(data)} bayt)")
                    return None
                print(f"[pollinations] OK {model} ({len(data)//1024} KB)")
                return data
    except Exception as e:
        print(f"[pollinations] xato: {e}")
        return None


async def generate_together_flux(prompt, steps=4):
    """Together FLUX — zaxira (agar kalit bo'lsa)."""
    if not TOGETHER_KEY:
        return None
    for m in ("black-forest-labs/FLUX.1-schnell-Free", "black-forest-labs/FLUX.1-schnell"):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(
                    "https://api.together.xyz/v1/images/generations",
                    headers={"Authorization": f"Bearer {TOGETHER_KEY}",
                             "Content-Type": "application/json"},
                    json={"model": m, "prompt": prompt, "width": 1024, "height": 1024,
                          "steps": steps, "n": 1, "response_format": "b64_json"},
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as r:
                    data = await r.json()
                    if "data" not in data:
                        continue
                    b64 = data["data"][0].get("b64_json")
                    if b64:
                        print(f"[together] OK {m}")
                        return base64.b64decode(b64)
        except Exception as e:
            print(f"[together] {m}: {e}")
    return None


async def generate_dalle(prompt, size="1024x1024", quality="standard"):
    """DALL-E 3 — oxirgi zaxira (pullik)."""
    if not OPENAI_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size,
                      "quality": quality, "response_format": "url"},
                timeout=aiohttp.ClientTimeout(total=90)
            ) as r:
                data = await r.json()
                if "data" not in data: return None
                u = data["data"][0]["url"]
            async with s.get(u, timeout=aiohttp.ClientTimeout(total=60)) as ir:
                return await ir.read()
    except Exception as e:
        print(f"[dalle] {e}")
        return None


async def generate_hf(prompt):
    """Eski moslik — Cloudflare FLUX."""
    return await generate_cf_flux(prompt)


async def generate_flux(prompt, width=1024, height=1024, steps=4, model=None):
    """Eski moslik — Cloudflare FLUX."""
    return await generate_cf_flux(prompt, steps)


async def generate_smart(tavsif, mavzu="", grade="", style="realistik", hd=False, is_admin=False):
    """Rasm yaratish — rolga qarab.
    ADMIN  : ☁️ Cloudflare FLUX 8 qadam (eng sifatli) -> Pollinations -> DALL-E
    BOSHQA : 🌻 Pollinations (bepul, cheksiz)         -> Cloudflare -> Together
    Shunday qilib Cloudflare neuronlari admin uchun saqlanadi."""
    prompt = await _tavsif_to_prompt(tavsif, mavzu, grade, style)

    if is_admin:
        # Eng yuqori sifat
        img, err = await generate_cf_flux_ex(prompt, steps=8)
        if not img:
            print("[smart] admin: CF ishlamadi -> Pollinations")
            img = await generate_pollinations(prompt, width=1024, height=1024)
        if not img:
            img = await generate_together_flux(prompt, steps=8)
        if not img and OPENAI_KEY:
            print("[smart] admin: -> DALL-E HD")
            img = await generate_dalle(prompt, quality="hd")
    else:
        # O'quvchi / o'qituvchi / ota-ona — cheksiz bepul
        img = await generate_pollinations(prompt, width=1024, height=1024)
        if not img:
            print("[smart] user: Pollinations ishlamadi -> CF")
            img, err = await generate_cf_flux_ex(prompt, steps=4)
        if not img:
            img = await generate_together_flux(prompt, steps=4)

    return (img, prompt)
