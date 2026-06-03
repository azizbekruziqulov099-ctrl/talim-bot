import os
import psycopg2
import json
from topic_generation import get_next_topic, increase_count
from topic_info import get_topic_info
from prompt_builder import build_prompt
from openai_client import client
from rapidfuzz import fuzz
import random
DATABASE_URL = os.getenv("DATABASE_URL")
print("1-BOSQICH")

def is_similar(new_question, old_questions):

    for q in old_questions:

        score = fuzz.ratio(
            new_question.lower(),
            q.lower()
        )

        if score >= 100:
            return True

    return False

def save_test(test_data):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Dublikat tekshirish

    cur.execute("""
        SELECT 1
        FROM generated_tests
        WHERE topic_code=%s
        AND question=%s
        LIMIT 1
    """, (
        test_data["topic_code"],
        test_data["question"]
    ))

    old_questions = get_last_questions(
        test_data["topic_code"],
        limit=100
    )

    if is_similar(
        test_data["question"],
        old_questions
    ):
        print("⚠️ O'XSHASH SAVOL")
        cur.close()
        conn.close()
        return

    if cur.fetchone():
        print("⚠️ DUPLIKAT TEST")
        cur.close()
        conn.close()
        return

    # Single choice validatsiya

    if test_data.get("question_type") == "single_choice":

        variants = [
            test_data.get("option_a"),
            test_data.get("option_b"),
            test_data.get("option_c"),
            test_data.get("option_d")
        ]

        if test_data.get("correct_answer") not in variants:
            print("❌ JAVOB VARIANTLAR ICHIDA YO'Q")
            cur.close()
            conn.close()
            return

    cur.execute("""
        INSERT INTO generated_tests (
            topic_code,
            difficulty,
            situation,
            question,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation,
            question_type,
            is_latex,
            image_url,
            audio_text,
            language,
            life_level,
            age_group,
            time_limit
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s
        )
    """, (
        test_data["topic_code"],
        test_data["difficulty"],
        test_data["situation"],
        test_data["question"],
        test_data.get("option_a"),
        test_data.get("option_b"),
        test_data.get("option_c"),
        test_data.get("option_d"),
        test_data["correct_answer"],
        test_data.get("explanation"),
        test_data.get("question_type", "single_choice"),
        test_data.get("is_latex", False),
        test_data.get("image_url"),
        test_data.get("audio_text"),
        test_data.get("language", "uz"),
        test_data.get("life_level", 0),
        test_data.get("age_group"),
        test_data.get("time_limit", 60)
    ))

    conn.commit()

    cur.close()
    conn.close()


    text = f"{mavzu} {kichik}".lower()

    text = (
        text
        .replace("'", "")
        .replace("‘", "")
        .replace("`", "")
    )

    return "umumiy"

def get_last_questions(topic_code, limit=60):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT question
        FROM generated_tests
        WHERE topic_code=%s
        ORDER BY id DESC
        LIMIT %s
    """, (topic_code, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [r[0] for r in rows]


while True:

    topics = get_next_topic(1)

    if not topics:
        print("HAMMA MAVZULAR TUGADI")
        break

    topic_code = topics[0][0]

    info = get_topic_info(topic_code)

    grade, subject, bob, bolim, mavzu, kichik = info

    print("GRADE:", grade)
    print("SUBJECT:", subject)
    print("MAVZU:", mavzu)
    print("KICHIK:", kichik)

    print("2-BOSQICH")

    test_types = (
        ["single_choice"] * 30 +
        ["multiple_choice"] * 5 +
        ["true_false"] * 5 +
        ["write_answer"] * 20
        # ["image_question"] * 0
    )

    difficulties = (
        ["oson"] * 30 +
        ["o'rta"] * 15 +
        ["qiyin"] * 10 +
        ["murakkab"] * 5
    )

    life_levels = (
        [0] * 20 +
        [1] * 15 +
        [2] * 10 +
        [3] * 10 +
        [4] * 5
    )

    for i, question_type in enumerate(test_types):

        last_questions = get_last_questions(
            topic_code,
            limit=60
        )

        difficulty = difficulties[i]
        life_level = life_levels[i]

        prompt = build_prompt(
            topic_code,
            difficulty=difficulty,
            situation="oddiy",
            question_type=question_type,
            last_questions=last_questions
        )

        print("3-BOSQICH")
        print("4-BOSQICH GPTGA YUBORILAYAPTI")

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=1.2,
                top_p=0.95
            )

        except Exception as e:
            print(f"GPT XATO: {e}")
            continue

        print("5-BOSQICH GPT JAVOB BERDI")

        content = response.choices[0].message.content

        content = content.replace("\n", "")
        content = content.strip()

        try:
            test_data = json.loads(content)

            if test_data.get("question_type") == "image_question":

                print("🖼 RASM YARATILAYAPTI")

                image_prompt = test_data.get("image_prompt")

                image = client.images.generate(
                    model="gpt-image-1",
                    prompt=image_prompt,
                    size="1024x1024"
                )

                print(image)

            allowed_types = [
                "single_choice",
                "multiple_choice",
                "true_false",
                "write_answer",
                "image_question"
            ]

            if test_data.get("question_type") not in allowed_types:
                test_data["question_type"] = question_type

            test_data["topic_code"] = topic_code
            test_data["difficulty"] = difficulty
            test_data["situation"] = "oddiy"

            print(test_data)

            save_test(test_data)

            print(f"✅ SAQLANDI: {question_type}")

        except Exception as e:

            print(f"❌ XATO: {question_type}")
            print(e)

    increase_count(topic_code)

    print("🎉 MAVZU TUGADI")
