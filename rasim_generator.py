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
            "2. Preserve EXACT colors, sizes, positions, actions the user stated.\n"
            "3. Do NOT add objects the user did not mention.\n"
            "4. Add ONLY: lighting, camera angle, background, texture, mood.\n"
            "5. Structure: [main subject with exact details], [action/pose], "
            "[setting/background], [lighting], [style keywords].\n"
            "6. Output ONLY the prompt. No quotes, no explanation, no 'Prompt:' prefix.\n"
            "7. Max 320 characters.\n\n"
            "EXAMPLES:\n"
            "Uzbek: 3 ta qizil olma stolda\n"
            "Prompt: Three red apples arranged on a wooden table, soft natural window light "
            "from the left, shallow depth of field, warm tones, photorealistic, sharp focus\n\n"
            "Uzbek: maktabda dars, o'qituvchi doskada yozmoqda\n"
            "Prompt: A teacher writing on a blackboard in a bright classroom, students seated "
            "at desks facing forward, morning sunlight through windows, warm educational "
            "atmosphere, detailed illustration\n\n"
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
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 250},
            }, timeout=aiohttp.ClientTimeout(total=25)) as r:
                data = await r.json()
                txt = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Tozalash: "Prompt:" prefiks, qo'shtirnoq, yangi qator
                for pre in ("Prompt:", "prompt:", "PROMPT:"):
                    if txt.startswith(pre): txt = txt[len(pre):].strip()
                txt = txt.strip('"').strip("'").replace("\n", " ").strip()
                print(f"[gemini] OK -> {txt[:100]}")
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
                        "Convert Uzbek image description to precise English FLUX prompt. "
                        "Be EXACT about counts, colors, objects, positions. "
                        f"Style: {style_desc}. Return ONLY prompt, max 300 chars."},
                    {"role": "user", "content": f"Uzbek: {tavsif}\nContext: {mavzu} {grade}"}],
                    "max_tokens": 200, "temperature": 0.5},
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
    return p


async def generate_cf_flux(prompt, steps=4):
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
    """Rasm: Cloudflare FLUX (bepul) -> Together -> DALL-E.
    is_admin=True -> 8 qadam (sifatli), aks holda 6."""
    prompt = await _tavsif_to_prompt(tavsif, mavzu, grade, style)
    steps = 8 if is_admin else 6
    img = await generate_cf_flux(prompt, steps=steps)
    if not img:
        img = await generate_together_flux(prompt, steps=steps)
    if not img and OPENAI_KEY:
        print("[smart] FLUX ishlamadi -> DALL-E")
        img = await generate_dalle(prompt)
    return (img, prompt)
