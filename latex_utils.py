import os
import re
import asyncio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from openai import AsyncOpenAI
import edge_tts
from pydub import AudioSegment

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────
# 1. LaTeX → Rasm (matplotlib)
# ─────────────────────────────────────────

def latex_to_image(latex_text: str, user_id: int) -> str:
    """
    LaTeX matnini chiroyli rasm qilib saqlaydi.
    Qaytaradi: fayl yo'li
    """

    # Tozalash — [latex]...[/latex] tegini olib tashlash
    formula = latex_text.strip()
    formula = re.sub(r'\[/?latex\]', '', formula).strip()

    # $ belgisi qo'shish agar yo'q bo'lsa
    if not formula.startswith("$"):
        formula = f"${formula}$"

    fig, ax = plt.subplots(figsize=(6, 1.5))
    fig.patch.set_facecolor("#F0F4F8")
    ax.set_facecolor("#F0F4F8")

    ax.text(
        0.5, 0.5,
        formula,
        fontsize=22,
        ha="center",
        va="center",
        color="#1F2937",
        usetex=False  # matplotlib built-in renderer
    )

    ax.axis("off")

    # Chiroyli chegara
    rect = patches.FancyBboxPatch(
        (0.02, 0.1), 0.96, 0.8,
        boxstyle="round,pad=0.05",
        linewidth=2,
        edgecolor="#3B82F6",
        facecolor="#EFF6FF",
        transform=ax.transAxes,
        zorder=0
    )
    ax.add_patch(rect)

    filename = f"latex_{user_id}.png"
    plt.savefig(
        filename,
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )
    plt.close(fig)

    return filename


# ─────────────────────────────────────────
# 2. LaTeX → O'zbek matni (OpenAI)
# ─────────────────────────────────────────

async def latex_to_uzbek(latex_text: str) -> str:
    """
    LaTeX formulasini o'zbek tilida tushunarli matnga aylantiradi.
    Misol: \frac{1}{2} → "bir ikkinchi"
    """

    formula = re.sub(r'\[/?latex\]', '', latex_text).strip()

    prompt = f"""Siz matematik formula o'qituvchisisiz.
Quyidagi LaTeX formulasini o'zbek tilida oddiy, tushunarli so'zlar bilan o'qing.
Faqat o'zbek tilida yozing, hech qanday izoh qo'shmang, faqat o'qiladigan matn.

Misollar:
\\frac{{1}}{{2}} → "bir ikkinchi"
x^2 → "x kvadrat"
\\sqrt{{x}} → "x ning kvadrat ildizi"
a + b = c → "a qo'shib b teng c"
\\frac{{a+b}}{{c}} → "a qo'shib b ning, c ga bo'linmasi"
2 \\times 3 → "ikki marta uch"
\\pi → "pi soni"
\\int_{{0}}^{{1}} → "noldan birgacha integral"

Formula: {formula}

Faqat o'qiladigan matnni yozing:"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    except Exception:
        # OpenAI ishlamasa — oddiy qoidalar bilan o'qiymiz
        return latex_simple_read(formula)


def latex_simple_read(formula: str) -> str:
    """
    OpenAI ishlamasa — qoidalar asosida LaTeX o'qish
    """
    text = formula

    replacements = [
        (r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 ning \2 ga bo\'linmasi'),
        (r'\\sqrt\{([^}]+)\}', r'\1 ning kvadrat ildizi'),
        (r'\\sqrt', 'kvadrat ildiz'),
        (r'\^2', ' kvadrat'),
        (r'\^3', ' kub'),
        (r'\^\{([^}]+)\}', r'\1 darajasi'),
        (r'\\times', ' marta '),
        (r'\\cdot', ' ko\'paytirish '),
        (r'\\div', ' bo\'lish '),
        (r'\\pi', 'pi soni'),
        (r'\\infty', 'cheksizlik'),
        (r'\\alpha', 'alfa'),
        (r'\\beta', 'beta'),
        (r'\\gamma', 'gamma'),
        (r'\\delta', 'delta'),
        (r'\\sum', 'yig\'indisi'),
        (r'\\int', 'integrali'),
        (r'\\leq', 'kichik yoki teng'),
        (r'\\geq', 'katta yoki teng'),
        (r'\\neq', 'teng emas'),
        (r'\\approx', 'taxminan'),
        (r'\\pm', 'musbat yoki manfiy'),
        (r'[{}$\\]', ' '),
        (r'\s+', ' '),
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)

    return text.strip()


# ─────────────────────────────────────────
# 3. LaTeX → Ovoz (OpenAI + TTS)
# ─────────────────────────────────────────

async def latex_to_voice(latex_text: str, user_id: int) -> str:
    """
    LaTeX formulasini o'qib, mp3 fayl qaytaradi.
    """

    uzbek_text = await latex_to_uzbek(latex_text)

    filename = f"latex_voice_{user_id}.mp3"

    communicate = edge_tts.Communicate(
        text=uzbek_text,
        voice="uz-UZ-SardorNeural"
    )

    await communicate.save(filename)

    return filename, uzbek_text


# ─────────────────────────────────────────
# 4. Matn ichidagi LaTeX/IMG teglarni ajratish
# ─────────────────────────────────────────

def parse_blocks(text: str) -> list:
    """
    Matn ichidagi barcha blokni ajratadi:
    - {'type': 'text', 'content': '...'}
    - {'type': 'latex', 'content': '...'}
    - {'type': 'img', 'content': 'https://...'}
    - {'type': 'en', 'content': '...'}
    - {'type': 'ru', 'content': '...'}
    """

    pattern = re.compile(
        r'\[latex\](.*?)\[/latex\]'
        r'|\[img\](.*?)\[/img\]'
        r'|\[en\](.*?)\[/en\]'
        r'|\[ru\](.*?)\[/ru\]',
        re.DOTALL
    )

    blocks = []
    last_end = 0

    for m in pattern.finditer(text):
        # Oldidagi oddiy matn
        if m.start() > last_end:
            chunk = text[last_end:m.start()].strip()
            if chunk:
                blocks.append({'type': 'text', 'content': chunk})

        if m.group(1) is not None:
            blocks.append({'type': 'latex', 'content': m.group(1).strip()})
        elif m.group(2) is not None:
            blocks.append({'type': 'img', 'content': m.group(2).strip()})
        elif m.group(3) is not None:
            blocks.append({'type': 'en', 'content': m.group(3).strip()})
        elif m.group(4) is not None:
            blocks.append({'type': 'ru', 'content': m.group(4).strip()})

        last_end = m.end()

    # Oxiridagi qoldiq matn
    if last_end < len(text):
        chunk = text[last_end:].strip()
        if chunk:
            blocks.append({'type': 'text', 'content': chunk})

    return blocks


# ─────────────────────────────────────────
# 5. Blokni Telegramga yuborish
# ─────────────────────────────────────────

async def send_blocks(message, blocks: list, user_id: int):
    """
    Har bir blokni tegishli tarzda yuboradi:
    - text → oddiy xabar
    - latex → rasm + ovoz
    - img → photo
    - en/ru → ovozda o'qiydi
    """
    from aiogram.types import FSInputFile

    for block in blocks:

        btype = block['type']
        content = block['content']

        if btype == 'text':
            if content:
                await message.answer(content)

        elif btype == 'latex':

            # Rasm yuborish
            try:
                img_path = latex_to_image(content, user_id)
                await message.answer_photo(
                    FSInputFile(img_path),
                    caption=f"📐 `{content}`",
                    parse_mode="Markdown"
                )
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                await message.answer(f"📐 Formula: `{content}`", parse_mode="Markdown")

            # Ovoz yuborish
            try:
                voice_path, uzbek = await latex_to_voice(content, user_id)
                await message.answer(f"🔊 _{uzbek}_", parse_mode="Markdown")
                from aiogram.types import FSInputFile as FI
                await message.answer_voice(FI(voice_path))
                if os.path.exists(voice_path):
                    os.remove(voice_path)
            except Exception:
                pass

        elif btype == 'img':

            try:
                await message.answer_photo(content)
            except Exception:
                await message.answer(f"🖼 [Rasm]({content})", parse_mode="Markdown")

        elif btype in ('en', 'ru'):

            voices = {
                'en': 'en-US-GuyNeural',
                'ru': 'ru-RU-DmitryNeural'
            }
            voice = voices.get(btype, 'uz-UZ-SardorNeural')

            await message.answer(f"`{content}`", parse_mode="Markdown")

            try:
                fname = f"lang_{user_id}.mp3"
                comm = edge_tts.Communicate(text=content, voice=voice)
                await comm.save(fname)
                if os.path.exists(fname) and os.path.getsize(fname) > 0:
                    from aiogram.types import FSInputFile as FI
                    await message.answer_voice(FI(fname))
                    os.remove(fname)
            except Exception:
                pass
