import os
import psycopg2
import json
from topic_generation import get_next_topic, increase_count
from topic_info import get_topic_info
from prompt_builder import build_prompt


DATABASE_URL = os.getenv("DATABASE_URL")

def save_test(test_data):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

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
            explanation
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        test_data["topic_code"],
        test_data["difficulty"],
        test_data["situation"],
        test_data["question"],
        test_data["option_a"],
        test_data["option_b"],
        test_data["option_c"],
        test_data["option_d"],
        test_data["correct_answer"],
        test_data["explanation"]
    ))

    conn.commit()
    cur.close()
    conn.close()

topic_code = get_next_topic(1)[0][0]

prompt = build_prompt(
    topic_code,
    difficulty="oson",
    situation="oddiy"
)

print(prompt)
