from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
import edge_tts
import asyncio
import matplotlib.pyplot as plt


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

    if question_type == "write_answer":

        user_state[user_id] = "text_answer"

        if (
            image_url
            and str(image_url).lower() != "nan"
            and str(image_url).strip() != ""
        ):

            await message.answer_photo(
                photo=image_url,
                caption=
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:",
                reply_markup=kb
            )

        else:

            await message.answer(
                f"⏱️ {time_limit} soniya\n\n"
                f"{question}\n\n"
                f"✍️ Javobni yozing:",
                reply_markup=kb
            )

        return

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
                    text=str(a),
                    callback_data="ans_A"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_b"
                ),
                InlineKeyboardButton(
                    text=str(b),
                    callback_data="ans_B"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_c"
                ),
                InlineKeyboardButton(
                    text=str(c),
                    callback_data="ans_C"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔊 Eshitish",
                    callback_data="speak_d"
                ),
                InlineKeyboardButton(
                    text=str(d),
                    callback_data="ans_D"
                )
            ]
        ]
    )


    if is_latex:

        image_file = (
            f"latex_{user_id}.png"
        )

        latex_to_image(
            question,
            image_file
        )

        await message.answer_photo(
            photo=FSInputFile(
                image_file
            )
        )

        await message.answer(
            "Savolni rasmda ko‘ring",
            reply_markup=kb
        )

    if (
        image_url
        and str(image_url).lower() != "nan"
        and str(image_url).strip() != ""
    ):
        cur.execute(
            "SELECT file_id FROM images WHERE name=%s",
            (image_url,)
        )
        row = cur.fetchone()

        if row:
            image_url = row[0]

        await message.answer_photo(
            photo=image_url,
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

async def speak_question(
    user_id,
    message
):

    session = test_sessions.get(
        user_id
    )

    if not session:
        return

    current = session["current"]

    test = session["questions"][current]

    question = test[0]

    language = test[11]

    if language == "uz":
        voice = "uz-UZ-SardorNeural"

    elif language == "ru":
        voice = "ru-RU-DmitryNeural"

    elif language == "en":
        voice = "en-US-GuyNeural"

    else:
        voice = "uz-UZ-SardorNeural"

    filename = (
        f"voice_{user_id}.mp3"
    )

    communicate = edge_tts.Communicate(
        text=question,
        voice=voice
    )

    await communicate.save(
        filename
    )

    await message.answer_voice(
        FSInputFile(filename)
    )

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
