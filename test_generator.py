import psycopg2
import json

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

fake_test = {
    "topic_code": "2-01-1-01-01-01-001",
    "difficulty": "oson",
    "situation": "oddiy",
    "question": "12 sonidan keyin qaysi son keladi?",
    "option_a": "13",
    "option_b": "14",
    "option_c": "15",
    "option_d": "16",
    "correct_answer": "A",
    "explanation": "12 dan keyin 13 keladi."
}

save_test(fake_test)

print("SAQLANDI")
