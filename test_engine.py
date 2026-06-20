from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
import edge_tts
import asyncio
import matplotlib.pyplot as plt
import psycopg2
from pydub import AudioSegment
import uuid
import os
import re

DATABASE_URL = os.getenv("DATABASE_URL")


def render_text(text: str) -> str:
    """
    Teglarni olib tashlab matnni tozalaydi — ekranda ko'rsatish uchun.
    [en]Hello[/en] → Hello
    [ru]Привет[/ru] → Привет
    [skip]...[/skip] → ... (ko'rinadi)
    """
    if not text:
        return ""
    text = str(text)
    # Teglarni olib tashlash, matnni qoldirish
    text = re.sub(r'\[en\](.*?)\[/en\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[skip\](.*?)\[/skip\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[latex\](.*?)\[/latex\]', r'[\1]', text, flags=re.DOTALL)
    text = re.sub(r'\[img\](.*?)\[/img\]', '', text, flags=re.DOTALL)
    return text.strip()


def tts_text(text: str) -> str:
    """
    TTS uchun matnni tozalaydi — ovozda o'qish uchun.
    Teglarni, emojilarni olib tashlaydi.
    """
    if not text:
        return ""
    text = render_text(text)
    # Emoji olib tashlash
    text = re.sub(
        r'[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]+',
        ' ', text, flags=re.UNICODE
    )
    text = re.sub(r'[•\*\#\|\_\~\`━\-]{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


test_sessions = {}
user_state = {}


async def start_test(
    user_id,
    tests,
    message
):

    if not tests:

        await message.answer(
            "❌ Test topilmadi"
        )

        return

    test_sessions[user_id] = {
        "questions": tests,
        "current": 0,
        "correct": 0,
        "wrong": 0,
        "timer_task": None
    }

    await show_question(
        user_id,
        message
    )

async def show_question(
    user_id,
    message
):

    session = test_sessions.get(user_id)

    if not session:
        return

    current = session["current"]

    test = session["questions"][current]

    (
        question,
        a,
        b,
        c,
        d,
        correct,
        explanation,
        question_type,
        is_latex,
        image_url,
        audio_text,
        language,
        time_limit
    ) = test

    # Teglarni olib tashlash — ekranda tozalangan ko'rinsin
    question_show = render_text(question)
    a_show = render_text(str(a))
    b_show = render_text(str(b))
    c_show = render_text(str(c))
    d_show = render_text(str(d))


    if question_type == "write_answer":

        user_state[user_id] = "text_answer"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔊 Eshitish",
                        callback_data="speak_question"
                    ),
                    InlineKeyboardButton(
                        text="🛑 Tugatish",
                        callback_data="test_stop"
                    )
                ]
            ]
        )

        if image_url and str(image_url).strip():

            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()

            cur.execute(
                "SELECT file_id FROM images WHERE name=%s",
                (image_url.strip(),)
            )

            row = cur.fetchone()

            conn.close()

            if row:

                await message.answer_photo(
                    photo=row[0],
                    caption=
                    f"⏱️ {time_limit} soniya\n\n"
                    f"{question_show}\n\n"
                    f"✍️ Javobni yozing:",
                    reply_markup=kb
                )

            else:

                await message.answer(
                    f"⏱️ {time_limit} soniya\n\n"
                    f"{question_show}\n\n"
                    f"✍️ Javobni yozing:",
                    reply_markup=kb
                )

        else:

            await message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question_show}\n\n"
                f"✍️ Javobni yozing:",
                reply_markup=kb
            )

        return

    # ODDIY TESTLAR
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_question"
                ),
                InlineKeyboardButton(
                    text="🛑 Tugatish",
                    callback_data="test_stop"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_a"
                ),
                InlineKeyboardButton(
                    text=a_show,
                    callback_data="ans_A"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_b"
                ),
                InlineKeyboardButton(
                    text=b_show,
                    callback_data="ans_B"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_c"
                ),
                InlineKeyboardButton(
                    text=c_show,
                    callback_data="ans_C"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_d"
                ),
                InlineKeyboardButton(
                    text=d_show,
                    callback_data="ans_D"
                )
            ]
        ]
    )

    if is_latex:

        image_file = f"latex_{user_id}.png"

        latex_to_image(
            question,
            image_file
        )

        await message.answer_photo(
            photo=FSInputFile(image_file)
        )

        await message.answer(
            "Savolni rasmda ko‘ring",
            reply_markup=kb
        )

        return

    if (
        image_url
        and str(image_url).lower() != "nan"
        and str(image_url).strip() != ""
    ):

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            "SELECT file_id FROM images WHERE name=%s",
            (image_url.strip(),)
        )

        row = cur.fetchone()

        conn.close()

        if row:

            await message.answer_photo(
                photo=row[0],
                caption=
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}",
                reply_markup=kb
            )

        else:

            await message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}",
                reply_markup=kb
            )

    else:

        await message.answer(
            f"⏱️ {time_limit} soniya\n\n"
            f"{question}",
            reply_markup=kb
        )

async def check_button_answer(
    user_id,
    answer,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    current = session["current"]

    test = session["questions"][current]

    (
        question,
        a,
        b,
        c,
        d,
        correct,
        explanation,
        question_type,
        is_latex,
        image_url,
        audio_text,
        language,
        time_limit
    ) = test

    if answer == "A":
        selected = str(a)

    elif answer == "B":
        selected = str(b)

    elif answer == "C":
        selected = str(c)

    else:
        selected = str(d)

    if selected.strip() == str(correct).strip():

        session["correct"] += 1

        await message.answer(
            f"✅ To'g'ri\n\n📖 {explanation}"
        )

    else:

        session["wrong"] += 1

        await message.answer(
            f"❌ Noto'g'ri\n\n"
            f"To'g'ri javob: {correct}\n\n"
            f"📖 {explanation}"
        )

    await next_question(
        user_id,
        message
    )
    
async def check_text_answer(
    user_id,
    user_answer,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    current = session["current"]

    test = session["questions"][current]

    correct = str(
        test[5]
    ).strip().lower()

    user_answer = str(
        user_answer
    ).strip().lower()

    explanation = test[6]

    if user_answer == correct:

        session["correct"] += 1

        await message.answer(
            f"✅ To'g'ri\n\n📖 {explanation}"
        )

    else:

        session["wrong"] += 1

        await message.answer(
            f"❌ Noto'g'ri\n\n"
            f"To'g'ri javob: {test[5]}\n\n"
            f"📖 {explanation}"
        )

    await next_question(
        user_id,
        message
    )

async def next_question(
    user_id,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    session["current"] += 1

    if session["current"] >= len(
        session["questions"]
    ):

        await finish_test(
            user_id,
            message
        )

        return

    await show_question(
        user_id,
        message
    )    

async def finish_test(
    user_id,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    total = (
        session["correct"]
        +
        session["wrong"]
    )

    percent = round(
        session["correct"]
        * 100
        / total,
        1
    ) if total else 0

    await message.answer(
        f"""
🏁 Test tugadi

✅ To'g'ri: {session['correct']}
❌ Noto'g'ri: {session['wrong']}

📊 Natija: {percent}%
"""
    )

    if user_id in user_state:
        del user_state[user_id]

    del test_sessions[user_id]

async def stop_test(
    user_id,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    await finish_test(
        user_id,
        message
    )

async def speak_mixed_text(
    user_id,
    message,
    text
):

    blocks = parse_content(text)

    voice_map = {
        "text": "uz-UZ-SardorNeural",
        "en": "en-US-GuyNeural",
        "ru": "ru-RU-DmitryNeural",
        "de": "de-DE-ConradNeural"
    }

    for block in blocks:

        block_type = block.get("type")

        if block_type == "text":

            voice = voice_map["text"]
            content = block["content"]

        else:

            voice = voice_map.get(
                block_type,
                "uz-UZ-SardorNeural"
            )

            content = block["content"]

        filename = (
            f"voice_{user_id}.mp3"
        )

        communicate = edge_tts.Communicate(
            text=content,
            voice=voice
        )

        await communicate.save(
            filename
        )

        await message.answer_voice(
            FSInputFile(filename)
        )

async def speak_text(
    user_id,
    message,
    text
):

    session = test_sessions.get(user_id)

    if session:

        current = session["current"]
        test = session["questions"][current]

        language = str(test[11]).lower()

    else:

        language = "uz"

    voices = {
        "uz": "uz-UZ-SardorNeural",
        "ru": "ru-RU-DmitryNeural",
        "en": "en-US-GuyNeural",

        "kk": "kk-KZ-DauletNeural",      # Qozoq
        "kz": "kk-KZ-DauletNeural",

        "ky": "ky-KG-AzizNeural",        # Qirg'iz
        "kg": "ky-KG-AzizNeural",

        "tk": "tk-TM-MerdanNeural",      # Turkman

        "tr": "tr-TR-AhmetNeural",       # Turk

        "ko": "ko-KR-InJoonNeural",      # Koreys

        "ja": "ja-JP-KeitaNeural",       # Yapon

        "fr": "fr-FR-HenriNeural",       # Fransuz

        "it": "it-IT-DiegoNeural",       # Italyan

        "es": "es-ES-AlvaroNeural",      # Ispan

        "pt": "pt-BR-AntonioNeural",     # Portugal/Brazil
    
        "ar": "ar-SA-HamedNeural",      # Arab
    
        "fa": "fa-IR-DilaraNeural",     # Fors (Eron)
    
        "tg": "tg-TJ-???",              # Tojik (agar Edge TTS qo‘llasa)
    
        "mn": "mn-MN-???",              # Mo‘g‘ul (agar Edge TTS qo‘llasa)
    
        "zh": "zh-CN-YunxiNeural",      # Xitoy
    
        "de": "de-DE-ConradNeural",     # Nemis
    
        "hi": "hi-IN-MadhurNeural",     # Hind
    
        "ur": "ur-PK-AsadNeural",       # Urdu
    
        "bn": "bn-BD-NabanitaNeural",   # Bengal
    
        "pl": "pl-PL-MarekNeural",      # Polyak
    
        "nl": "nl-NL-MaartenNeural",    # Golland
    
        "sv": "sv-SE-MattiasNeural",    # Shved
    
        "fi": "fi-FI-HarriNeural",      # Fin
    
        "cs": "cs-CZ-AntoninNeural",    # Chex

    }

    voice = voices.get(
        language,
        "uz-UZ-SardorNeural"
    )

    filename = f"voice_{user_id}.mp3"

    communicate = edge_tts.Communicate(
        text=str(text),
        voice=voice
    )

    await communicate.save(filename)

    if (
        user_id in user_state
        and
        "voice_message_id" in user_state[user_id]
    ):

        try:

            await message.bot.delete_message(
                chat_id=message.chat.id,
                message_id=user_state[user_id]["voice_message_id"]
            )

        except:
            pass

    voice_msg = await message.answer_voice(
        FSInputFile(filename)
    )

    if user_id not in user_state:
        user_state[user_id] = {}

    user_state[user_id]["voice_message_id"] = (
        voice_msg.message_id
    )

async def speak_question(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    current = session["current"]
    test = session["questions"][current]
    await speak_text(user_id, message, tts_text(test[0]))

async def speak_a(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    current = session["current"]
    test = session["questions"][current]
    await speak_text(user_id, message, tts_text(test[1]))

async def speak_b(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    current = session["current"]
    test = session["questions"][current]
    await speak_text(user_id, message, tts_text(test[2]))

async def speak_c(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    current = session["current"]
    test = session["questions"][current]
    await speak_text(user_id, message, tts_text(test[3]))

async def speak_d(user_id, message):
    session = test_sessions.get(user_id)
    if not session:
        return
    current = session["current"]
    test = session["questions"][current]
    await speak_text(user_id, message, tts_text(test[4]))

def latex_to_image(latex_text, filename):

    fig = plt.figure()

    plt.text(
        0.05,
        0.5,
        f"${latex_text}$",
        fontsize=24
    )

    plt.axis("off")

    plt.savefig(
        filename,
        bbox_inches="tight"
    )

    plt.close()
