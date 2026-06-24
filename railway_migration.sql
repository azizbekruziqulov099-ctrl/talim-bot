-- =====================================================================
--  talim-bot  ->  Railway PostgreSQL  yetishmayotgan jadvallar migratsiyasi
--  Hammasi IF NOT EXISTS — bir necha marta ishga tushirsa ham xavfsiz.
--  Mavjud jadvallar (users, surveys, results, survey_answers, images,
--  lesson_history) Talim.py init_db() da yaratiladi — bu yerda YO'Q.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 0) USERS jadvaliga dashboard uchun yetishmayotgan ustunlar
--    (student_dashboard.py: gender, birth_date dan o'qiydi)
-- ---------------------------------------------------------------------
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE;

-- ---------------------------------------------------------------------
-- 1) DTS_TREE — DTS o'quv daraxti (eng muhim, 12 ta faylda ishlatiladi)
--    ON CONFLICT (topic_code) ishlashi uchun topic_code UNIQUE bo'lishi shart.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dts_tree (
    id            SERIAL PRIMARY KEY,
    topic_code    TEXT UNIQUE,
    grade         TEXT,
    subject_code  TEXT,
    subject_name  TEXT,
    quarter       TEXT,
    bob_code      TEXT,
    bob_name      TEXT,
    bolim_code    TEXT,
    bolim_name    TEXT,
    mavzu_code    TEXT,
    mavzu_name    TEXT,
    kichik_code   TEXT,
    kichik_name   TEXT,
    is_deleted    BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_dts_tree_grade_subj
    ON dts_tree (grade, subject_code, quarter);
CREATE INDEX IF NOT EXISTS idx_dts_tree_grade_subjname
    ON dts_tree (grade, subject_name);
CREATE INDEX IF NOT EXISTS idx_dts_tree_active
    ON dts_tree (is_deleted);

-- ---------------------------------------------------------------------
-- 2) GENERATED_TESTS — AI/import test savollari
--    is_latex BOOLEAN, time_limit INTEGER, qolgani TEXT.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_tests (
    id             SERIAL PRIMARY KEY,
    topic_code     TEXT,
    difficulty     TEXT,
    situation      TEXT,
    question       TEXT,
    option_a       TEXT,
    option_b       TEXT,
    option_c       TEXT,
    option_d       TEXT,
    correct_answer TEXT,
    explanation    TEXT,
    question_type  TEXT,
    is_latex       BOOLEAN DEFAULT FALSE,
    image_url      TEXT,
    audio_text     TEXT,
    language       TEXT,
    life_level     TEXT,
    age_group      TEXT,
    time_limit     INTEGER
);
CREATE INDEX IF NOT EXISTS idx_gen_tests_topic
    ON generated_tests (topic_code);
CREATE INDEX IF NOT EXISTS idx_gen_tests_topic_diff
    ON generated_tests (topic_code, difficulty);

-- ---------------------------------------------------------------------
-- 3) TEACHER_LESSONS — o'qituvchi tayyorlagan dars matnlari
--    SELECT * ishlatiladi; bir topic = bir dars => topic_code UNIQUE.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teacher_lessons (
    id          SERIAL PRIMARY KEY,
    topic_code  TEXT UNIQUE,
    intro       TEXT,
    part_1      TEXT,
    part_2      TEXT,
    part_3      TEXT,
    part_4      TEXT,
    simple_1    TEXT,
    simple_2    TEXT,
    simple_3    TEXT,
    simple_4    TEXT,
    example_1   TEXT,
    example_2   TEXT,
    exercise_1  TEXT,
    exercise_2  TEXT,
    summary     TEXT
);

-- ---------------------------------------------------------------------
-- 4) LEARNED_TOPICS — o'rganilgan mavzular (takrorlash intervali)
--    ON CONFLICT (user_id, topic_code) => UNIQUE(user_id, topic_code).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS learned_topics (
    id           SERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    topic_code   TEXT NOT NULL,
    score        INTEGER DEFAULT 0,
    repeat_count INTEGER DEFAULT 0,
    learned_at   TIMESTAMP DEFAULT NOW(),
    next_repeat  DATE,
    UNIQUE (user_id, topic_code)
);
CREATE INDEX IF NOT EXISTS idx_learned_user
    ON learned_topics (user_id);
CREATE INDEX IF NOT EXISTS idx_learned_repeat
    ON learned_topics (next_repeat);

-- ---------------------------------------------------------------------
-- 5) USER_PROGRESS — XP / streak / oxirgi faollik
--    ON CONFLICT (user_id) => user_id PRIMARY KEY.
--    last_active DATE (kod date.today() bilan solishtiradi).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_progress (
    user_id     BIGINT PRIMARY KEY,
    xp          INTEGER DEFAULT 0,
    streak      INTEGER DEFAULT 0,
    last_active DATE
);

-- ---------------------------------------------------------------------
-- 6) LESSON_PROGRESS — dars qaysi qadamda to'xtagani
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lesson_progress (
    id           SERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL,
    topic_code   TEXT,
    current_step INTEGER DEFAULT 0,
    completed    BOOLEAN DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_lesson_prog_user
    ON lesson_progress (user_id);

-- ---------------------------------------------------------------------
-- 7) ACHIEVEMENTS — yutuq nishonlari (badge)
--    ON CONFLICT DO NOTHING + RETURNING => UNIQUE(user_id, badge_code).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS achievements (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    badge_code TEXT NOT NULL,
    earned_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, badge_code)
);

-- ---------------------------------------------------------------------
-- 8) EXAMS — imtihonlar (exam_results dan oldin yaratiladi: FK uchun)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exams (
    id           SERIAL PRIMARY KEY,
    title        TEXT,
    grade        TEXT,
    exam_date    DATE,
    is_mandatory BOOLEAN DEFAULT FALSE,
    created_by   BIGINT
);

-- ---------------------------------------------------------------------
-- 9) EXAM_RESULTS — kim qaysi imtihonga biriktirilgani / holati
--    ON CONFLICT DO NOTHING => UNIQUE(user_id, exam_id).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_results (
    id      SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    exam_id INTEGER REFERENCES exams(id) ON DELETE CASCADE,
    status  TEXT DEFAULT 'pending',
    UNIQUE (user_id, exam_id)
);
CREATE INDEX IF NOT EXISTS idx_exam_results_user
    ON exam_results (user_id);

-- ---------------------------------------------------------------------
-- 10) TOPIC_GENERATION — AI generatsiya navbati
--     ON CONFLICT (topic_code) => topic_code PRIMARY KEY.
--     target_count kodda HECH QAYERDA o'rnatilmaydi => DEFAULT shart!
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topic_generation (
    topic_code        TEXT PRIMARY KEY,
    current_count     INTEGER DEFAULT 0,
    target_count      INTEGER DEFAULT 10,
    last_generated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_topic_gen_pending
    ON topic_generation (current_count);

-- =====================================================================
--  Tugadi. Tekshirish:  SELECT tablename FROM pg_tables
--                       WHERE schemaname='public' ORDER BY tablename;
-- =====================================================================
