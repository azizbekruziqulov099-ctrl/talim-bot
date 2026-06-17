import re
import edge_tts
import matplotlib.pyplot as plt
from pydub import AudioSegment
import uuid
import os

VOICE_MAP = {
    "text": "uz-UZ-SardorNeural",
    "en": "en-US-GuyNeural",
    "ru": "ru-RU-DmitryNeural",
    "de": "de-DE-ConradNeural"
}

def build_ssml(text):

    blocks = parse_content(text)

    ssml = ""

    for block in blocks:

        ssml += block["content"] + " "

    return ssml.strip()

def parse_content(text):

    pattern = r"\[(\w+)\](.*?)\[/\1\]"

    result = []

    last_end = 0

    for match in re.finditer(
        pattern,
        text,
        re.DOTALL
    ):

        start, end = match.span()

        if start > last_end:

            plain_text = text[
                last_end:start
            ].strip()

            if plain_text:

                result.append(
                    {
                        "type": "text",
                        "lang": "uz",
                        "content": plain_text
                    }
                )

        tag = match.group(1)
        content = match.group(2).strip()

        result.append(
            {
                "type": tag,
                "content": content
            }
        )

        last_end = end

    if last_end < len(text):

        plain_text = text[
            last_end:
        ].strip()

        if plain_text:

            result.append(
                {
                    "type": "text",
                    "lang": "uz",
                    "content": plain_text
                }
            )

    return result

def render_content(text):

    blocks = parse_content(text)

    result = ""

    for block in blocks:

        result += block["content"] + " "

    return result.strip()

def render_content(text):

    blocks = parse_content(text)

    result = ""

    for block in blocks:

        result += block["content"] + " "

    return result.strip()

def build_lesson_steps(lesson):

    return [
        lesson[2],   # intro
        lesson[3],   # part_1
        lesson[4],   # part_2
        lesson[5],   # part_3
        lesson[6],   # part_4
        lesson[13]   # summary
    ]


def get_step_content(steps, step):

    if step < 0:
        return None

    if step >= len(steps):
        return None

    return steps[step]


def create_lesson_state(lesson):

    steps = build_lesson_steps(lesson)

    return {
        "current_step": 0,
        "steps": steps
    }


def next_step(state):

    if state["current_step"] >= len(state["steps"]) - 1:
        return False

    state["current_step"] += 1

    return True


def prev_step(state):

    if state["current_step"] <= 0:
        return False

    state["current_step"] -= 1

    return True


def current_text(state):

    return state["steps"][
        state["current_step"]
    ]


def lesson_finished(state):

    return (
        state["current_step"]
        >= len(state["steps"]) - 1
    )


def parse_languages(text):

    chunks = []

    pattern = r'\[(en|ru|de)\](.*?)\[/\1\]'

    pos = 0

    for match in re.finditer(pattern, text):

        start, end = match.span()

        if start > pos:

            chunks.append(
                ("uz", text[pos:start])
            )

        lang = match.group(1)

        content = match.group(2)

        chunks.append(
            (lang, content)
        )

        pos = end

    if pos < len(text):

        chunks.append(
            ("uz", text[pos:])
        )

    return chunks


def extract_tts_chunks(text):

    return parse_languages(text)


def parse_blocks(text):

    blocks = []

    tags = [
        "teacher",
        "important",
        "remember",
        "why",
        "example",
        "question",
        "exercise",
        "summary"
    ]

    for tag in tags:

        pattern = (
            rf'\[{tag}\](.*?)\[/{tag}\]'
        )

        for match in re.finditer(
            pattern,
            text,
            re.DOTALL
        ):

            blocks.append(
                {
                    "type": tag,
                    "content": match.group(1).strip()
                }
            )

    return blocks


def build_board_text(text):

    blocks = parse_blocks(text)

    result = []

    for block in blocks:

        if block["type"] == "teacher":

            result.append(
                f"👨‍🏫 Ustoz\n\n{block['content']}"
            )

        elif block["type"] == "important":

            result.append(
                f"⭐ Muhim\n\n{block['content']}"
            )

        elif block["type"] == "remember":

            result.append(
                f"📌 Eslab qoling\n\n{block['content']}"
            )

        elif block["type"] == "example":

            result.append(
                f"🎯 Misol\n\n{block['content']}"
            )

        elif block["type"] == "question":

            result.append(
                f"❓ Savol\n\n{block['content']}"
            )

        elif block["type"] == "exercise":

            result.append(
                f"✍️ Mashq\n\n{block['content']}"
            )

        elif block["type"] == "summary":

            result.append(
                f"📚 Xulosa\n\n{block['content']}"
            )

    return "\n\n━━━━━━━━━━━━━━\n\n".join(
        result
    )

def build_lesson_steps(lesson):

    return [
        lesson["intro"],
        lesson["part_1"],
        lesson["part_2"],
        lesson["part_3"],
        lesson["part_4"],
        lesson["summary"]
    ]


def get_step_content(steps, step):

    if step < 0:
        return None

    if step >= len(steps):
        return None

    return steps[step]

def lesson_to_dict(row):

    return {
        "topic_code": row[0],
        "intro": row[1],
        "part_1": row[2],
        "part_2": row[3],
        "part_3": row[4],
        "part_4": row[5],
        "simple_1": row[6],
        "simple_2": row[7],
        "example_1": row[8],
        "example_2": row[9],
        "exercise_1": row[10],
        "exercise_2": row[11],
        "summary": row[12]
    }

