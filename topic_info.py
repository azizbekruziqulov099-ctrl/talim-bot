import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")


def get_topic_info(topic_code):

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            grade,
            subject_name,
            bob_name,
            bolim_name,
            mavzu_name,
            kichik_name
        FROM dts_tree
        WHERE topic_code = %s
        LIMIT 1
    """, (topic_code,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row