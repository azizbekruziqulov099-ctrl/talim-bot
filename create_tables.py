"""
create_tables.py — talim-bot uchun yetishmayotgan jadvallarni Railway PostgreSQL
bazasida yaratadi. railway_migration.sql faylini o'qib, bitta tranzaksiyada bajaradi.

ISHGA TUSHIRISH (Railway):
    railway run python create_tables.py
yoki DATABASE_URL ni qo'lda berib:
    DATABASE_URL="postgresql://..." python create_tables.py

Bir necha marta ishga tushirsa ham xavfsiz (hamma narsa IF NOT EXISTS).
"""

import os
import sys
import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
SQL_FILE = os.path.join(HERE, "railway_migration.sql")

# Migratsiyadan keyin shu jadvallar mavjudligini tekshiramiz
EXPECTED = [
    "dts_tree", "generated_tests", "teacher_lessons", "learned_topics",
    "user_progress", "lesson_progress", "achievements", "exams",
    "exam_results", "topic_generation",
]


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL topilmadi. `railway run python create_tables.py` deb ishga tushiring.")
        return 1

    if not os.path.exists(SQL_FILE):
        print(f"❌ {SQL_FILE} topilmadi. railway_migration.sql shu papkada bo'lsin.")
        return 1

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()

    print("→ Railway bazasiga ulanyapman...")
    conn = psycopg2.connect(db_url)
    try:
        with conn:                      # commit/rollback avtomatik
            with conn.cursor() as cur:
                cur.execute(sql)         # butun migratsiya bitta tranzaksiyada
        print("✅ Migratsiya bajarildi.\n")

        # Tekshirish
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            )
            existing = {r[0] for r in cur.fetchall()}

        print("Jadvallar holati:")
        all_ok = True
        for t in EXPECTED:
            ok = t in existing
            all_ok = all_ok and ok
            print(f"   {'✅' if ok else '❌'} {t}")

        print("\nBazadagi BARCHA jadvallar:")
        for t in sorted(existing):
            print("   -", t)

        return 0 if all_ok else 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
