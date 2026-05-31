import psycopg2
from config import DATABASE_URL


def sync_topics_from_dts():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO topic_generation (
            topic_code
        )
        SELECT DISTINCT topic_code
        FROM dts_tree
        WHERE topic_code IS NOT NULL
          AND is_deleted = FALSE
        ON CONFLICT (topic_code)
        DO NOTHING
    """)

    conn.commit()

    cur.close()
    conn.close()
