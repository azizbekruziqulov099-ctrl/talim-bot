import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")


def get_next_topic(limit=10):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT topic_code,
               current_count,
               target_count
        FROM topic_generation
        WHERE current_count < target_count
        ORDER BY current_count ASC,
                 topic_code ASC
        LIMIT %s
    """, (limit,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

def increase_count(topic_code):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        UPDATE topic_generation
        SET current_count = current_count + 1,
            last_generated_at = NOW()
        WHERE topic_code = %s
    """, (topic_code,))

    conn.commit()

    cur.close()
    conn.close()

