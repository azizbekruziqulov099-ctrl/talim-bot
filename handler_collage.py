"""handler_collage.py — Collage va rasm handlerlari"""
import psycopg2, asyncio, os, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, FSInputFile
from aiogram.fsm.context import FSMContext
from storage import user_state, admin_state, temp_user
DATABASE_URL = os.getenv("DATABASE_URL","")
ADMINS = list(map(int, os.getenv("ADMINS","0").split(",")))
def _get_db_conn(): return psycopg2.connect(DATABASE_URL)

async def handle_collage_msg(message, user_id, admin_state, user_state, temp_user, bot):
    """True qaytarsa ishladi"""

    # ── Collage rasm split handler ──
    # Caption: "split:TC:start:rows:cols" yoki "split:TC:start" (default 5x6)
    # Misol: "split:3-02-3:1:5:6" → TC=3-02-3, start=1, 5 qator, 6 ustun
    uid_sp = message.from_user.id

    # ── Collage rasm split handler ──
    _col_cap = (message.caption or "").strip()
    if True:
        # rasm_queue da kutayotgan kodlar bormi?
        try:
            conn_rq2=_get_db_conn();cur_rq2=conn_rq2.cursor()
            cur_rq2.execute("""CREATE TABLE IF NOT EXISTS rasm_queue
                (id SERIAL PRIMARY KEY, user_id BIGINT, kod TEXT,
                 done BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())""")
            conn_rq2.commit()
            cur_rq2.execute("SELECT COUNT(*) FROM rasm_queue WHERE user_id=%s AND done=FALSE",(uid_sp,))
            pending=(cur_rq2.fetchone() or [0])[0]
            cur_rq2.close();conn_rq2.close()
        except: pending=0
    if pending>0:
        ROWS_sp = 5; COLS_sp = 6
        total_sp = 30

        # rasm_queue dan keyingi 30 ta kodni olish
        conn_rq3=_get_db_conn();cur_rq3=conn_rq3.cursor()
        cur_rq3.execute("""SELECT id,kod FROM rasm_queue
            WHERE user_id=%s AND done=FALSE ORDER BY id LIMIT 30""",(uid_sp,))
        rows_rq=cur_rq3.fetchall()
        cur_rq3.close();conn_rq3.close()

        if not rows_rq:
            await message.answer("✅ Barcha rasmlar allaqachon saqlandi!")
            return

        batch_ids_rq = [r[0] for r in rows_rq]
        batch_kodlar = [r[1] for r in rows_rq]
        ROWS_sp = 5; COLS_sp = 6
        total_sp = len(batch_kodlar)
        status_sp = await message.answer(f"✂️ Qirqilmoqda... {len(batch_kodlar)} ta")

        try:
            from PIL import Image as PILImage
            from io import BytesIO
            from aiogram.types import BufferedInputFile

            # Rasmni yuklab olish
            photo = message.photo[-1]
            buf_p = BytesIO()
            await message.bot.download(photo.file_id, destination=buf_p)
            buf_p.seek(0)
            img = PILImage.open(buf_p)
            W, H = img.size

            COLS, ROWS = COLS_sp, ROWS_sp
            cw, ch = W // COLS, H // ROWS
            saved_sp = 0

            for i, kod in enumerate(batch_kodlar):
                r, c = i // COLS, i % COLS
                x1, y1 = c * cw, r * ch
                x2, y2 = x1 + cw, y1 + ch
                cell = img.crop((x1, y1, x2, y2))
                buf_c = BytesIO()
                cell.save(buf_c, format="PNG")
                buf_c.seek(0)
                try:
                    sent_sp = await message.bot.send_photo(
                        message.chat.id,
                        BufferedInputFile(buf_c.read(), f"{kod}.png"),
                        caption=f"🖼 {kod}"
                    )
                    fid_sp = sent_sp.photo[-1].file_id
                    conn_sp = _get_db_conn(); cur_sp = conn_sp.cursor()
                    cur_sp.execute("""INSERT INTO images(name,file_id) VALUES(%s,%s)
                        ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id""",(kod,fid_sp))
                    cur_sp.execute("UPDATE rasm_queue SET done=TRUE WHERE user_id=%s AND kod=%s",(uid_sp,kod))
                    conn_sp.commit(); cur_sp.close(); conn_sp.close()
                    saved_sp += 1
                except Exception as _e:
                    print(f"cell {kod}: {_e}")

            conn_rq4=_get_db_conn();cur_rq4=conn_rq4.cursor()
            cur_rq4.execute("SELECT COUNT(*) FROM rasm_queue WHERE user_id=%s AND done=FALSE",(uid_sp,))
            remaining=(cur_rq4.fetchone() or [0])[0]
            cur_rq4.close();conn_rq4.close()

            if remaining > 0:
                await status_sp.edit_text(
                    f"✅ {saved_sp} ta saqlandi!\n"
                    f"📊 Qolgan: {remaining} ta\n\n"
                    f"Keyingi collage yuboring 👇"
                )
            else:
                await status_sp.edit_text(
                    f"🎉 Hammasi tayyor!\n"
                    f"✅ {saved_sp} ta + avvalgisi = {new_idx} ta jami saqlandi!"
                )
                admin_state.pop(f"{user_id}_rasm_kodlar", None)
                admin_state.pop(f"{user_id}_rasm_idx", None)

        except Exception as _e:
            await status_sp.edit_text(f"❌ Split xato: {_e}")
        return

    caption = (message.caption or "").strip()

    # Agar caption "split:TOPIC_CODE:rows:cols:prefix" formatida bo'lsa
    # Misol: split:1-01-1-01-01-01-001:1:6:p  → -p-1..-p-6
    #        split:1-01-1-01-01-01-001:1:5:e  → -e-1..-e-5
    # msplit:QATOR:USTUN:TC1,TC2,TC3,...
    # Misol: msplit:5:2:TC1,TC2,TC3,TC4,TC5 → har TC dan 10 ta panel
    if caption.lower().startswith("msplit:"):
        parts = caption[7:].strip().split(":")
        rows   = int(parts[0]) if parts else 5
        cols   = int(parts[1]) if len(parts)>1 else 4
        tcs    = [t.strip() for t in parts[2].split(",") if t.strip()] if len(parts)>2 else []
        prefix = parts[3].strip() if len(parts)>3 else ""
        if not tcs:
            await message.answer("❌ TC kodlar yo'q! Format: msplit:5:4:TC1,TC2,..."); return
        panel_per_tc = rows * cols
        total = panel_per_tc * len(tcs)
        sep = f"-{prefix}-" if prefix else "-"
        await message.answer(
            f"⏳ msplit: {rows}×{cols}={panel_per_tc} panel × {len(tcs)} TC = {total} bo'lak\n"
            f"TC lar: {', '.join(tcs[:3])}{'...' if len(tcs)>3 else ''}"
        )
        buf = await message.bot.download(message.photo[-1].file_id)
        from PIL import Image as PILImage
        from io import BytesIO
        buf.seek(0)
        img = PILImage.open(buf)
        total_cols = cols
        total_rows = rows * len(tcs)
        w, h = img.size
        pw = w // total_cols
        ph = h // total_rows

        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        saved = 0
        for tc_idx, tc in enumerate(tcs):
            for r in range(rows):
                for c in range(cols):
                    n = r * cols + c + 1
                    global_row = tc_idx * rows + r
                    x1, y1 = c*pw, global_row*ph
                    x2, y2 = x1+pw, y1+ph
                    piece = img.crop((x1,y1,x2,y2))
                    pb = BytesIO(); piece.save(pb, format="JPEG", quality=90); pb.seek(0)
                    from aiogram.types import BufferedInputFile
                    sent = await message.answer_photo(
                        BufferedInputFile(pb.read(), f"{tc}{sep}{n}.jpg"),
                        caption=f"{tc}{sep}{n}"
                    )
                    fid = sent.photo[-1].file_id
                    name = f"{tc}{sep}{n}"
                    cur2.execute("""
                        INSERT INTO images(name, file_id)
                        VALUES(%s,%s)
                        ON CONFLICT(name) DO UPDATE SET file_id=EXCLUDED.file_id
                    """, (name, fid))
                    saved += 1
        conn2.commit(); cur2.close(); conn2.close()
        await message.answer(f"✅ {saved} ta rasm saqlandi!\n{len(tcs)} ta mavzu × {panel_per_tc} panel")
        return

    if caption.lower().startswith("split:"):
        parts  = caption[6:].strip().split(":")
        topic_code = parts[0].strip()
        rows   = int(parts[1]) if len(parts) > 1 else 1
        cols   = int(parts[2]) if len(parts) > 2 else 6
        prefix = parts[3].strip() if len(parts) > 3 else ""
        total  = rows * cols
        sep    = f"-{prefix}-" if prefix else "-"
        await message.answer(
            f"⏳ Rasm {rows}×{cols}={total} ga bo'linmoqda...\n"
            f"📌 {topic_code}{sep}1 ... {topic_code}{sep}{total}"
        )

        # Rasmni yuklab olish
        import io
        from PIL import Image

        file = await message.bot.get_file(message.photo[-1].file_id)
        buf = io.BytesIO()
        await message.bot.download_file(file.file_path, buf)
        buf.seek(0)
        img = Image.open(buf)
        W, H = img.size

        # 5 qator x 8 ustun = 40 ta (yoki berilgan o'lcham)
        cell_w = W // cols
        cell_h = H // rows

        conn = _get_db_conn()
        cur  = conn.cursor()
        saved = 0

        for row in range(rows):
            for col in range(cols):
                n = row * cols + col + 1
                if n > total:
                    break

                # Kesish
                x1 = col * cell_w
                y1 = row * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h
                piece = img.crop((x1, y1, x2, y2))

                # Telegram ga yuborish va file_id olish
                piece_buf = io.BytesIO()
                piece.save(piece_buf, format="JPEG")
                piece_buf.seek(0)

                from aiogram.types import BufferedInputFile
                name_preview = f"{topic_code}-{prefix}-{n}"
                sent = await message.answer_photo(
                    BufferedInputFile(piece_buf.read(), filename=f"{name_preview}.jpg"),
                    caption=name_preview
                )
                file_id = sent.photo[-1].file_id

                # DBga saqlash
                sep2 = f"-{prefix}-" if prefix else "-"
                name = f"{topic_code}{sep2}{n}"
                cur.execute("""
                    INSERT INTO images(name, file_id)
                    VALUES(%s,%s)
                    ON CONFLICT (name) DO UPDATE SET file_id=EXCLUDED.file_id
                """, (name, file_id))
                saved += 1

        conn.commit()
        cur.close(); conn.close()
        sep3 = f"-{prefix}-" if prefix else "-"
        await message.answer(
            f"✅ {saved} ta rasm saqlandi!\n"
            f"📁 {topic_code}{sep3}1 ... {topic_code}{sep3}{total}"
        )
        return

    # Oddiy rasm saqlash
    if not caption:
        await message.answer("Rasm nomini captionga yozing\n\nYoki 40 ga bo'lish uchun:\nsplit:TOPIC_CODE")
        return

    name = caption
    file_id = message.photo[-1].file_id
    conn = _get_db_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO images(name, file_id)
    VALUES(%s,%s)
    ON CONFLICT (name)
    DO UPDATE SET file_id = EXCLUDED.file_id
    """, (name, file_id))
    conn.commit()
    cur.close(); conn.close()
    await message.answer(f"✅ Saqlandi: {name}")

# ====== START ======
def _save_error_log(uid_sp, username, error_text):
    """Xatoni bazaga yozadi (sinxron)."""
    try:
        conn_ = _get_db_conn()
        cur_  = conn_.cursor()
        cur_.execute(
            "INSERT INTO error_log(uid_sp, username, error_text) VALUES(%s,%s,%s)",
            (uid_sp, username, error_text[:1000])
        )
        conn_.commit(); cur_.close(); conn_.close()
    except Exception:
        pass

def _get_unread_errors():
    """O'qilmagan xatolar sonini qaytaradi."""
    try:
        conn_ = _get_db_conn()
        cur_  = conn_.cursor()
        cur_.execute("SELECT COUNT(*) FROM error_log WHERE is_read=FALSE")
        n = cur_.fetchone()[0]
        cur_.close(); conn_.close()
        return n
    except Exception:
        return 0

async def _notify_admins(error_text, user_id, username):
    """Adminlarga yangi xato haqida xabar yuboradi."""
    try:
        n = _get_unread_errors()
        txt = (
            f"🆘 Yangi xato #{n}\n"
            f"👤 User: {username} ({user_id})\n"
            f"❌ {error_text[:300]}"
        )
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, txt)
            except Exception:
                pass
    except Exception:
        pass

async def _error_and_home(source, user_id, err, label="Xato"):
    """Xato xabarini ko'rsatib, 2 soniyada bosh menyuga qaytaradi."""
    import traceback, asyncio
    tb = traceback.format_exc()
    short = str(err)[:200]

    # Username olish
    try:
        uname = source.from_user.username or str(user_id) if hasattr(source, "from_user") else str(user_id)
    except Exception:
        uname = str(user_id)

    # Bazaga saqlash
    _save_error_log(user_id, uname, f"{label}: {short}\n{tb[:500]}")

    # Foydalanuvchiga xabar
    try:
        msg_fn = source.answer if hasattr(source, "answer") else source.message.answer
        await msg_fn(f"⚠️ Xatolik yuz berdi.\n\nBosh menyuga qaytilmoqda...")
    except Exception:
        pass

    await asyncio.sleep(2)

    # Bosh menyuga qaytarish
    try:
        conn_ = _get_db_conn()
        cur_  = conn_.cursor()
        cur_.execute("SELECT role FROM users WHERE user_id=%s", (uid_sp,))
        row_  = cur_.fetchone()
        cur_.close(); conn_.close()
        role_ = row_[0] if row_ else "🧒 O'quvchi"
        if user_id in ADMINS: role_ = "Admin"
    except Exception:
        role_ = "🧒 O'quvchi"

    n_err = _get_unread_errors() if user_id in ADMINS else 0
    kb_ = get_main_keyboard(role_, unread_errors=n_err)
    try:
        msg_fn = source.answer if hasattr(source, "answer") else source.message.answer
        await msg_fn("🏠 Bosh menyu", reply_markup=kb_)
    except Exception:
        pass

    # Adminlarga xabardorlik
    await _notify_admins(f"{label}: {short}", user_id, uname)
    print(f"[ERROR] user={user_id} | {label}: {short}\n{tb}")

from aiogram.filters import Command

@dp.message(Command("menu"))
@dp.message(Command("cancel"))
@dp.message(Command("stop"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Har qanday holatda bosh menyuga qaytish."""
    uid = message.from_user.id
    try: await state.clear()
    except: pass
    user_state.pop(uid, None)
    from storage import lesson_state as _ls, temp_user as _tu
    from storage import registration_message as _rm
    _ls.pop(uid, None); _tu.pop(uid, None); _rm.pop(uid, None)
    from test_engine import test_sessions, start_test
    if uid in test_sessions:
        s_ = test_sessions.pop(uid, {})
        if s_.get("timer_task"):
            try: s_["timer_task"].cancel()
            except: pass
    try:
        conn = _get_db_conn(); cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); conn.close()
        role = row[0] if row else "🧒 O'quvchi"
    except: role = "🧒 O'quvchi"
    if uid in ADMINS: role = "Admin"
    await message.answer(
        "🏠 Bosh menyu",
        reply_markup=get_main_keyboard(role)
    )

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    # /start — har qanday holatda barcha state tozalanadi
    uid = message.from_user.id
    try: await state.clear()
    except: pass
    user_state.pop(uid, None)
    from storage import lesson_state as _ls, temp_user as _tu
    from storage import registration_message as _rm, reg_kbd_message as _rkm
    _ls.pop(uid, None)
    _tu.pop(uid, None)
    _rm.pop(uid, None)
    _rkm.pop(uid, None)
    from test_engine import test_sessions
    if uid in test_sessions:
        s_ = test_sessions.pop(uid, {})
        if s_.get("timer_task"):
            try: s_["timer_task"].cancel()
            except: pass

    conn = _get_db_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT role, full_name, class FROM users WHERE user_id=%s",
        (message.from_user.id,)
    )

    user = cur.fetchone()

    conn.close()

    # RO'YXATDAN O'TGAN FOYDALANUVCHI
    if user:

        role, full_name, grade = user

        if message.from_user.id in ADMINS:
            role = "Admin"

        if role == "Admin":
            _n_err = _get_unread_errors()
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}"
                + (f"\n🆘 {_n_err} ta o'qilmagan xato bor!" if _n_err else ""),
                reply_markup=get_main_keyboard(role, unread_errors=_n_err)
            )
            return

        # O'quvchi uchun yoshga mos kutib olish
        if "quvchi" in role.lower() or role.strip() in ("🧒 O'quvchi", "🧒O'quvchi", "O'quvchi"):

            from progress import update_streak
            from student_dashboard import build_dashboard

            update_streak(message.from_user.id)

            try:
                text, keyboard = await build_dashboard(message.from_user.id)
            except Exception as _de:
                import traceback
                print(f"build_dashboard ERROR: {traceback.format_exc()}")
                text = "👋 Xush kelibsiz!"
                keyboard = None

            # Majburiy imtihon bormi?
            from progress import get_pending_exams
            pending   = get_pending_exams(message.from_user.id)
            mandatory = [e for e in pending if e[3]]

            if mandatory:
                exam = mandatory[0]
                await message.answer(
                    f"{text}\n\n"
                    f"🚨 MAJBURIY IMTIHON:\n"
                    f"📘 {exam[1]}\n"
                    f"📅 Sana: {exam[2]}",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text="▶️ Imtihonni boshlash",
                                callback_data=f"exam_start_{exam[0]}"
                            )],
                            [InlineKeyboardButton(
                                text="⏭ Keyinroq",
                                callback_data="exam_later"
                            )]
                        ]
                    )
                )
                await message.answer("👇", reply_markup=get_main_keyboard("🧒 O'quvchi"))
            else:
                # Dashboard inline keyboard bilan
                if keyboard:
                    await message.answer(text, reply_markup=keyboard)
                else:
                    await message.answer(text)
                # O'quvchi reply keyboard — har doim yuboriladi
                _student_kb = get_main_keyboard("🧒 O'quvchi")
                await message.answer("👇", reply_markup=_student_kb)
        else:
            await message.answer(
                f"👋 Qaytganingiz bilan!\n🎭 Rol: {role}",
                reply_markup=get_main_keyboard(role)
            )

        return

    # YANGI FOYDALANUVCHI — inline registratsiya
    from register import start_registration
    await start_registration(message)

# Test import uchun vaqtincha fayl yo'llari (user_id -> path)
test_import_files = {}

async def prepare_test_import(message, user_id):
    """Excel ni yuklab, tekshirib, tasdiq so'raydi (darrov import qilmaydi)."""
    file = await bot.get_file(message.document.file_id)
    path = f"temp_import_{user_id}.xlsx"
    await bot.download_file(file.file_path, path)

    try:
        _xls = pd.ExcelFile(path)
        _sheet = "TESTLAR" if "TESTLAR" in _xls.sheet_names else _xls.sheet_names[0]
        df = pd.read_excel(path, sheet_name=_sheet)
    except Exception as _e:
        await message.answer(f"❌ Excel o'qib bo'lmadi: {_e}")
        admin_state[user_id] = None
        return

    if "topic_code" not in df.columns:
        await message.answer(
            "❌ Excel ustunlari mos emas.\n"
            "Birinchi qatorda 'topic_code, difficulty, question ...' ustunlari bo'lishi kerak."
        )
        admin_state[user_id] = None
        return

    valid = 0
    for _, r in df.iterrows():
        if not pd.isna(r.get("topic_code")) and not pd.isna(r.get("question")):
            valid += 1

    test_import_files[user_id] = path
    admin_state[user_id] = "test_import_confirm"

    await message.answer(
        f"📋 Faylda {valid} ta savol topildi.\n\nImport qilaylikmi?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[
                KeyboardButton(text="✅ Ha, import qil"),
                KeyboardButton(text="❌ Bekor"),
            ]],
            resize_keyboard=True
        )
    )

async def import_tests_excel(target, path, user_id):

    # Varaq nomi har qanday bo'lsa ishlasin: avval TESTLAR, bo'lmasa birinchi varaq
    try:
        _xls = pd.ExcelFile(path)
        _sheet = "TESTLAR" if "TESTLAR" in _xls.sheet_names else _xls.sheet_names[0]
        df = pd.read_excel(path, sheet_name=_sheet)
    except Exception as _e:
        await target.answer(f"❌ Excel o'qib bo'lmadi: {_e}")
        return

    if "topic_code" not in df.columns:
        await target.answer(
            "❌ Excel ustunlari mos emas.\n"
            "Birinchi qatorda 'topic_code, difficulty, question ...' ustunlari bo'lishi kerak."
        )
        return

    success = 0
    duplicates = 0
    errors = 0
    error_rows = []

    # Fayldagi barcha topik kodlarni olish
    _all_tcs = df["topic_code"].dropna().astype(str).str.strip()
    _all_tcs = [tc for tc in _all_tcs.unique() if tc not in ("","nan")]

    # Har topik uchun eskiyi o'chiramiz (qayta import)
    if _all_tcs:
        import psycopg2 as _pg0
        _c0 = _pg0.connect(os.getenv("DATABASE_URL")); _cu0 = _c0.cursor()
        for _tc in _all_tcs:
            _cu0.execute("DELETE FROM generated_tests WHERE topic_code=%s", (_tc,))
        _c0.commit(); _cu0.close(); _c0.close()

    for index, row in df.iterrows():

        try:
            # Bo'sh qatorni o'tkazib yuborish
            _tc = row.get("topic_code","")
            _q  = row.get("question","")
            if pd.isna(_tc) or pd.isna(_q) or str(_tc).strip() in ("","nan") or str(_q).strip() in ("","nan"):
                continue

            test_data = {
                "topic_code": str(row["topic_code"]).strip(),
                "difficulty": str(row["difficulty"]).strip(),
                "situation": "" if pd.isna(row["situation"]) else str(row["situation"]),
                "question": str(row["question"]).strip(),
                "option_a": "" if pd.isna(row["option_a"]) else str(row["option_a"]),
                "option_b": "" if pd.isna(row["option_b"]) else str(row["option_b"]),
                "option_c": "" if pd.isna(row["option_c"]) else str(row["option_c"]),
                "option_d": "" if pd.isna(row["option_d"]) else str(row["option_d"]),
                "correct_answer": str(row["correct_answer"]).strip(),
                "explanation": "" if pd.isna(row["explanation"]) else str(row["explanation"]),
                "question_type": str(row["question_type"]).strip(),
                "is_latex": False if pd.isna(row["is_latex"]) else (row["is_latex"] not in (0, 0.0, False, "False", "false", "0")),
                "image_url": None if pd.isna(row["image_url"]) else str(row["image_url"]),
                "audio_text": None if pd.isna(row["audio_text"]) else str(row["audio_text"]),
                "language": "uz" if pd.isna(row["language"]) else str(row["language"]),
                "life_level": 1 if pd.isna(row["life_level"]) else int(row["life_level"]),
                "age_group": None if pd.isna(row["age_group"]) else str(row["age_group"]),
                "time_limit": 60 if pd.isna(row["time_limit"]) else int(row["time_limit"])
            }

            import psycopg2 as _pg
            _conn = _pg.connect(os.getenv("DATABASE_URL"))
            _cur = _conn.cursor()

            # Avval to'liq tekshiruv — duplikatmi? (question_type ham hisobga olinadi)
            _cur.execute("""
                SELECT COUNT(*) FROM generated_tests
                WHERE topic_code=%s AND question=%s
                  AND option_a=%s AND option_b=%s
                  AND option_c=%s AND option_d=%s
                  AND correct_answer=%s
                  AND COALESCE(question_type,'single_choice')=COALESCE(%s,'single_choice')
            """, (
                test_data["topic_code"], test_data["question"],
                test_data["option_a"], test_data["option_b"],
                test_data["option_c"], test_data["option_d"],
                test_data["correct_answer"],
                test_data["question_type"],
            ))
            already = _cur.fetchone()[0]

            if already > 0:
                result = "duplicate"
            else:
                try:
                    _cur.execute("""
                        INSERT INTO generated_tests
                        (topic_code, difficulty, situation, question,
                         option_a, option_b, option_c, option_d,
                         correct_answer, explanation, question_type,
                         is_latex, image_url, audio_text, language,
                         life_level, age_group, time_limit)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                %s::boolean,%s,%s,%s,%s,%s,%s)
                    """, (
                        test_data["topic_code"], test_data["difficulty"],
                        test_data["situation"], test_data["question"],
                        test_data["option_a"], test_data["option_b"],
                        test_data["option_c"], test_data["option_d"],
                        test_data["correct_answer"], test_data["explanation"],
                        test_data["question_type"],
                        test_data["is_latex"],
                        test_data["image_url"], test_data["audio_text"],
                        test_data["language"], test_data["life_level"],
                        test_data["age_group"], test_data["time_limit"],
                    ))
                    _conn.commit()
                    result = "saved"
                except Exception as _ex:
                    _conn.rollback()
                    result = f"error: {_ex}"

            _cur.close(); _conn.close()

            if result == "saved":
                success += 1

            elif result == "duplicate":

                duplicates += 1

                error_rows.append({
                    "row_number": index + 2,
                    "question": row.get("question"),
                    "error": "Duplikat yoki o'xshash savol"
                })

            else:
                errors += 1

        except Exception as e:

            errors += 1

            error_rows.append({
                "row_number": index + 2,
                "question": row.get("question"),
                "error": str(e)
            })

    if error_rows:

        error_file = "import_errors.xlsx"

        df_errors = pd.DataFrame(error_rows)

        df_errors.to_excel(
            error_file,
            index=False
        )

    await target.answer(
        f"✅ Import tugadi\n\n"
        f"📥 Saqlandi: {success}\n"
        f"⚠️ Duplikat: {duplicates}\n"
        f"❌ Xato: {errors}"
    )

    if error_rows:

        await target.answer_document(
            FSInputFile("import_errors.xlsx"),
            caption="📋 Import xatolari hisoboti"
        )

    admin_state[user_id] = None

@dp.message()
async def handle_all(
    message: Message,
    state: FSMContext
):
    user_id = message.from_user.id
    try:
        await _handle_all_inner(message, state, user_id)
    except Exception as _e:
        await _error_and_home(message, user_id, _e, "Xatolik")

async def _rq_save(source, user_id, name, rol, sinf):
    """Tez kirish — foydalanuvchini saqlash (multi-account)."""
    conn2=_get_db_conn(); cur2=conn2.cursor()
    rol_uz = {"student":"O'quvchi","teacher":"O'qituvchi","parent":"Ota-ona"}.get(rol,rol)
    sinf_txt = f"{sinf}-sinf" if sinf else ""
    try:
        # users jadvalini yangilash
        cur2.execute("""
            INSERT INTO users(user_id,full_name,role,class,is_verified)
            VALUES(%s,%s,%s,%s,TRUE)
            ON CONFLICT(user_id) DO UPDATE
            SET full_name=EXCLUDED.full_name, role=EXCLUDED.role, class=EXCLUDED.class
        """, (user_id, name, rol_uz, sinf_txt))
        # user_accounts da yangi indeks
        cur2.execute("SELECT MAX(account_index) FROM user_accounts WHERE telegram_id=%s",(user_id,))
        max_idx=(cur2.fetchone() or [None])[0]
        new_idx = 0 if max_idx is None else max_idx + 1
        # Barchasini nofaol
        cur2.execute("UPDATE user_accounts SET is_active=FALSE WHERE telegram_id=%s",(user_id,))
        # Yangi akkaunt qo'shish
        cur2.execute("""
            INSERT INTO user_accounts(telegram_id,account_index,full_name,role,class,is_active)
            VALUES(%s,%s,%s,%s,%s,TRUE)
            ON CONFLICT(telegram_id,account_index) DO UPDATE
            SET full_name=EXCLUDED.full_name,role=EXCLUDED.role,class=EXCLUDED.class,is_active=TRUE
        """, (user_id, new_idx, name, rol_uz, sinf_txt))
        conn2.commit()
    except Exception as e:
        print(f"rq_save: {e}")
    cur2.close(); conn2.close()
    user_state.pop(user_id, None)
    temp_user.pop(user_id, None)
    kb = get_main_keyboard(rol_uz)
    if hasattr(source, "answer"):
        await source.answer(f"✅ Xush kelibsiz, {name}!\n🎯 {rol_uz} {sinf_txt}", reply_markup=kb)
    else:
        await source.message.answer(f"✅ Xush kelibsiz, {name}!\n🎯 {rol_uz} {sinf_txt}", reply_markup=kb)

async def _save_quick_user(call, user_id):
    """rq_sinf callbackdan saqlash."""
    data = temp_user.get(user_id, {})
    name = data.get("full_name","Foydalanuvchi")
    rol  = data.get("role","student")
    sinf = data.get("class")
    await _rq_save(call, user_id, name, rol, sinf)

async def _handle_all_inner(message: Message, state: FSMContext, user_id: int):

    # Test paytida yozilgan xabarni o'chirish
    from test_engine import test_sessions
    if user_id in test_sessions:
        if user_state.get(user_id) != "text_answer":
            try:
                await message.delete()
            except Exception:
                pass
            return

    # Dars paytida yozilgan xabarni avtomatik o'chirish
    if isinstance(user_state.get(user_id), dict):
        if user_state[user_id].get("board_message_id"):
            try:
                await message.delete()
            except Exception:
                pass

    if user_state.get(user_id) == "user_rasm" and message.text:
        tavsif = message.text.strip()
        user_state[user_id] = None

        # Uzunlik tekshirish
        words = tavsif.split()
        if len(words) < 2:
            await message.answer("❌ Juda qisqa! Kamida 2 so'z yozing.\nMasalan: «qishki manzara, bolalar»")
            user_state[user_id] = "user_rasm"
            return
        if len(words) > 10:
            await message.answer(f"❌ Juda uzun ({len(words)} so'z)! Maksimal 10 so'z.\nQisqaroq yozing.")
            user_state[user_id] = "user_rasm"
            return

        # Limit qayta tekshirish
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        try:
            cur2.execute("SELECT COUNT(*) FROM images WHERE name LIKE %s AND created_at >= CURRENT_DATE",
                        (f"user_{user_id}_%",))
            today_count = cur2.fetchone()[0]
        except: today_count = 0
        cur2.close(); conn2.close()

        if today_count >= 2:
            await message.answer("⏰ Kunlik limit tugadi (2 ta). Ertaga qaytib keling!")
            return

        status_u = await message.answer(f"🎨 Chizilmoqda... «{tavsif[:50]}»")

        async def do_user_rasm():
            try:
                from rasim_generator import _tavsif_to_prompt, generate_hf, generate_dalle
                prompt = await _tavsif_to_prompt(tavsif, "ta'lim", "1", "multik")
                img = await generate_hf(prompt)
                if not img: img = await generate_dalle(prompt)
                if img:
                    from aiogram.types import BufferedInputFile
                    fname = f"user_{user_id}_{int(__import__('time').time())}"
                    sent = await message.answer_photo(
                        BufferedInputFile(img, f"{fname}.png"),
                        caption=f"🎨 {tavsif[:80]}"
                    )
                    # DB ga saqlash (limit uchun)
                    fid = sent.photo[-1].file_id
                    try:
                        conn3=_get_db_conn();cur3=conn3.cursor()
                        cur3.execute("INSERT INTO images(name,file_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                                    (fname,fid))
                        conn3.commit();cur3.close();conn3.close()
                    except: pass
                    # Qolgan limit
                    qolgan = 1 - (today_count)
                    msg = f"✅ Rasm tayyor!"
                    if qolgan > 0:
                        msg += f"\n📊 Bugun yana {qolgan} ta yaratish mumkin"
                    else:
                        msg += "\n⏰ Bugungi limit tugadi"
                    await status_u.edit_text(msg)
                else:
                    await status_u.edit_text("❌ Rasm yaratilmadi. Qayta urinib ko'ring.")
            except Exception as e:
                await status_u.edit_text(f"❌ Xato: {e}")

        asyncio.create_task(do_user_rasm())
        return

    # ── Report comment handler ──
    if str(admin_state.get(user_id) or "").startswith("edit_test_field:") and message.text:
        parts3 = admin_state[user_id].split(":")
        tid3 = int(parts3[1]); field3 = parts3[2]
        val3  = message.text.strip()
        admin_state.pop(user_id, None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute(f"UPDATE generated_tests SET {field3}=%s WHERE id=%s",(val3,tid3))
        conn2.commit();cur2.close();conn2.close()
        await message.answer(f"✅ Test #{tid3} yangilandi!\n🔑 {field3} = {val3[:60]}")
        return

    if str(user_state.get(user_id) or "").startswith("report_comment:") and message.text:
        cur_idx = int(str(user_state[user_id]).split(":")[1])
        comment = message.text.strip()
        user_state[user_id] = None

        from test_engine import test_sessions
        st2 = test_sessions.get(user_id) or {}
        tests = st2.get("questions", [])
        tc = st2.get("topic_code","")

        if cur_idx < len(tests):
            q = tests[cur_idx][0]
            conn2 = _get_db_conn(); cur2 = conn2.cursor()
            cur2.execute("SELECT id FROM generated_tests WHERE question=%s LIMIT 1", (q,))
            row2 = cur2.fetchone(); tid = row2[0] if row2 else None
            try:
                cur2.execute("""INSERT INTO test_corrections(test_id,topic_code,question,user_id,comment,status)
                    VALUES(%s,%s,%s,%s,%s,'new')
                    ON CONFLICT DO NOTHING""", (tid, tc, q[:200], user_id, comment))
                conn2.commit()
            except: pass
            cur2.close(); conn2.close()
            # Admin xabar
            for aid in ADMINS:
                try:
                    await bot.send_message(aid,
                        f"✏️ Xato test bildirish\n"
                        f"👤 {user_id}\n"
                        f"📝 {q[:100]}\n"
                        f"💬 {comment}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(
                                text="🔧 Shu testni tuzatish",
                                callback_data=f"admin_fix_test:{tid if tid else 0}"
                            )
                        ]])
                    )
                except: pass
        await message.answer("✅ Rahmat! Xabaringiz adminlarga yuborildi.\n⏩ Test davom etmoqda...")
        from test_engine import test_sessions, _advance
        st2 = test_sessions.get(user_id)
        if st2 and not st2.get("answered"):
            try: await _advance(user_id)
            except Exception as _te: print(f"test davom: {_te}")
        return

    if str(admin_state.get(user_id) or "").startswith("kitob_edit_text:") and message.text:
        parts3=str(admin_state[user_id]).split(":")
        book_id3,page3=int(parts3[1]),int(parts3[2])
        admin_state.pop(user_id,None)
        from kitob_bazasi import extract_exercises
        new_text=message.text.strip()
        exs=extract_exercises(new_text)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE book_pages SET full_text=%s,exercise_count=%s WHERE book_id=%s AND page_num=%s",
                    (new_text,len(exs),book_id3,page3))
        cur2.execute("DELETE FROM book_exercises WHERE book_id=%s AND page_num=%s",(book_id3,page3))
        for ex in exs:
            cur2.execute("INSERT INTO book_exercises(book_id,page_num,savol) VALUES(%s,%s,%s)",
                        (book_id3,page3,ex[:1000]))
        conn2.commit(); cur2.close(); conn2.close()
        await message.answer(f"✅ Bet {page3} yangilandi! ({len(exs)} misol)")
        return

    if str(admin_state.get(user_id) or "").startswith("kitob_search:") and message.text:
        book_id2=int(str(admin_state[user_id]).split(":")[1])
        query=message.text.strip()
        admin_state.pop(user_id,None)
        from kitob_bazasi import search_book
        results=[r for r in search_book(query) if r["book_id"]==book_id2]
        if not results:
            await message.answer(f"❌ '{query}' topilmadi"); return
        rows2=[[InlineKeyboardButton(text=f"📖 Bet {r['page']}",callback_data=f"kitob_bet:{book_id2}:{r['page']}")] for r in results[:10]]
        txt=f"🔍 '{query}' — {len(results)} ta bet:\n\n"
        for r in results[:5]:
            txt+=f"📄 Bet {r['page']}: {r['text'][:80]}...\n\n"
        await message.answer(txt[:2000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return

    # Tez kirish — ism yozish
    if str(user_state.get(user_id) or "").startswith("rq_name:") and message.text:
        rol = str(user_state[user_id]).split(":")[1]
        name = message.text.strip()
        user_state.pop(user_id, None)
        if rol == "student":
            # Sinf tanlash
            temp_user[user_id]["full_name"] = name
            rows2 = [[InlineKeyboardButton(text=f"{i}-sinf", callback_data=f"rq_sinf:{i}") for i in range(j, j+4)] for j in range(1, 12, 4)]
            await message.answer(
                f"✅ {name}\n\nSinfni tanlang:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
            )
        else:
            # O'qituvchi/ota-ona — to'g'ridan saqlash
            await _rq_save(message, user_id, name, rol, None)
        return


    return False
