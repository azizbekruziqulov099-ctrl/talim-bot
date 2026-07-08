"""cb_test_nav.py — Test navigator callback handlerlari"""
import psycopg2, asyncio, os, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, FSInputFile
from storage import user_state, admin_state, temp_user
DATABASE_URL = os.getenv("DATABASE_URL","")
ADMINS = list(map(int, os.getenv("ADMINS","0").split(",")))
def _get_db_conn(): return psycopg2.connect(DATABASE_URL)

async def handle_test_nav(call, user_id, admin_state, user_state, temp_user, bot):
    d=call.data
    # ═══ O'QUVCHI TEST NAVIGATOR ═══
    if call.data.startswith("sinash_subj:"):
        parts2 = call.data.split(":", 2)
        grade2 = parts2[1]; subj2 = parts2[2]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        # Mavzu darajasida DISTINCT — kichik mavzular ko'rinmaydi
        cur2.execute("""
            SELECT d.mavzu_name, d.mavzu_code,
                   COUNT(g.id) as test_cnt
            FROM dts_tree d
            JOIN generated_tests g ON g.topic_code = d.topic_code
            WHERE d.subject_name=%s AND d.is_deleted=FALSE
            AND d.mavzu_code IS NOT NULL
            GROUP BY d.mavzu_name, d.mavzu_code
            ORDER BY d.mavzu_code
        """, (subj2,))
        topics2 = cur2.fetchall()
        cur2.close(); conn2.close()

        rows = []
        for mname, mcode, cnt in topics2:
            rows.append([InlineKeyboardButton(
                text=f"📝 {(mname or mcode)[:40]} ({cnt} ta)",
                callback_data=f"ts_mavzu:{mcode}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="sinash_back")])
        await call.message.edit_text(
            f"🧪 {subj2}\n{len(topics2)} ta mavzu (faqat test borlar):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data == "sinash_back":
        await call.message.delete()
        return True

    if call.data.startswith("mustah_subj:"):
        parts2 = call.data.split(":", 2)
        grade2 = parts2[1]; subj2 = parts2[2]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""
            SELECT tl.topic_code, d.kichik_name
            FROM teacher_lessons tl
            JOIN dts_tree d ON d.topic_code = tl.topic_code
            WHERE d.grade=%s AND d.subject_name=%s AND d.is_deleted=FALSE
            ORDER BY tl.topic_code
        """, (grade2, subj2))
        topics2 = cur2.fetchall()
        cur2.execute("SELECT topic_code FROM lesson_progress WHERE user_id=%s", (call.from_user.id,))
        studied2 = {r[0] for r in cur2.fetchall()}
        cur2.close(); conn2.close()

        rows = []
        for tc, kname in topics2:
            icon = "✅" if tc in studied2 else "📖"
            rows.append([InlineKeyboardButton(
                text=f"{icon} {kname[:45]}",
                callback_data=f"mustah_lesson:{tc}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="mustah_back")])
        await call.message.edit_text(
            f"📚 {subj2}\n✅=o'tilgan  📖=yangi\n{len(topics2)} ta mavzu:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data.startswith("mustah_lesson:"):
        tc = call.data.split(":")[1]
        await call.answer()
        # Darsni boshlash
        await open_teacher_lesson(call.message, topic_code=tc, _user_id=call.from_user.id)
        return True

    if call.data.startswith("mustah_other:"):
        page = int(call.data.split(":")[1])
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (call.from_user.id,))
        _gr = cur2.fetchone(); _my_grade = str(_gr[0]) if _gr else "1"
        cur2.execute("""
            SELECT tl.topic_code, d.kichik_name, d.subject_name, d.grade
            FROM teacher_lessons tl
            JOIN dts_tree d ON d.topic_code = tl.topic_code
            WHERE d.grade != %s AND d.is_deleted = FALSE
            ORDER BY d.grade, d.subject_name, tl.topic_code
        """, (_my_grade,))
        other = cur2.fetchall()
        cur2.execute("SELECT topic_code FROM lesson_progress WHERE user_id=%s", (call.from_user.id,))
        studied_set = {r[0] for r in cur2.fetchall()}
        cur2.close(); conn2.close()

        PAGE = 20
        start = page * PAGE
        end   = min(start + PAGE, len(other))
        page_items = other[start:end]

        rows = []
        for tc, kname, subj, grade in page_items:
            icon = "✅" if tc in studied_set else "📖"
            lbl  = f"{grade}-sinf" if str(grade).isdigit() else str(grade)
            rows.append([InlineKeyboardButton(
                text=f"{icon} [{lbl}] {kname[:35]}",
                callback_data=f"mustah_lesson:{tc}"
            )])
        nav = []
        if page > 0:     nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"mustah_other:{page-1}"))
        if end < len(other): nav.append(InlineKeyboardButton(text="➡️", callback_data=f"mustah_other:{page+1}"))
        if nav: rows.append(nav)
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="mustah_back")])
        await call.message.edit_text(
            f"🌐 Boshqa sinflar darslar ({len(other)} ta):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data.startswith("mustah_all:"):
        grade = call.data.split(":")[1]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        # O'z sinfi + CEFR kabi boshqalar
        cur2.execute("""
            SELECT grade FROM (SELECT DISTINCT grade FROM dts_tree WHERE is_deleted=FALSE) _g
            ORDER BY CASE WHEN grade ~ '^[0-9]+$' THEN grade::int ELSE 9999 END, grade
        """)
        all_grades = [r[0] for r in cur2.fetchall()]
        cur2.close(); conn2.close()

        # O'z sinfi + raqamsiz sinflar
        rows = []
        if grade in all_grades:
            rows.append([InlineKeyboardButton(
                text=f"⭐ {grade}-sinf" if str(grade).isdigit() else f"⭐ {grade}",
                callback_data=f"stnav_grade:{grade}"
            )])
        for g in all_grades:
            if str(g) == str(grade): continue
            if str(g).isdigit(): continue
            rows.append([InlineKeyboardButton(
                text=str(g),
                callback_data=f"stnav_grade:{g}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="mustah_back")])
        await call.message.edit_text("📖 Sinf tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return True

    if call.data == "err_unread":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""SELECT id,user_id,username,error_text,created_at FROM error_log WHERE is_read=FALSE ORDER BY created_at DESC LIMIT 10""")
        rows2 = cur2.fetchall()
        cur2.execute("UPDATE error_log SET is_read=TRUE WHERE is_read=FALSE")
        conn2.commit(); cur2.close(); conn2.close()
        if not rows2:
            await call.answer("O'qilmagan xato yo'q!", show_alert=True); return True
        await call.answer()
        for row2 in rows2:
            uid2, uname, etxt, cat = row2[1], row2[2], row2[3], row2[4]
            d = cat.strftime('%d.%m %H:%M') if cat else ""
            await call.message.answer(f"🔴 Xato\n👤 {uname or uid2}\n🕐 {d}\n❌ {str(etxt)[:300]}")
        return True

    if call.data == "err_read":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""SELECT username,error_text,created_at FROM error_log WHERE is_read=TRUE ORDER BY created_at DESC LIMIT 10""")
        rows2 = cur2.fetchall(); cur2.close(); conn2.close()
        await call.answer()
        if not rows2:
            await call.message.answer("O'qilgan xatolar yo'q."); return True
        lines2 = ["O'qilgan xatolar:\n"]
        for uname, etxt, cat in rows2:
            d = cat.strftime('%d.%m') if cat else ""
            lines2.append(f"• {uname}: {str(etxt)[:60]}... [{d}]")
        await call.message.answer("\n".join(lines2))
        return True

    if call.data == "err_clear":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("DELETE FROM error_log WHERE is_read=TRUE")
        deleted = cur2.rowcount; conn2.commit(); cur2.close(); conn2.close()
        await call.answer(f"{deleted} ta o'qilgan xato o'chirildi", show_alert=True)
        return True

    if call.data == "rep_test":
        await call.answer()
        from jadval_generator import test_results_text, test_results_excel
        from aiogram.types import BufferedInputFile
        await call.message.answer(test_results_text())
        try:
            buf = test_results_excel()
            await call.message.answer_document(
                BufferedInputFile(buf.read(), "test_natijalari.xlsx"),
                caption="📊 Test natijalari"
            )
        except: pass
        return True

    if call.data == "rep_prog":
        await call.answer()
        from jadval_generator import student_progress_text, student_progress_excel
        from aiogram.types import BufferedInputFile
        await call.message.answer(student_progress_text())
        try:
            buf = student_progress_excel()
            await call.message.answer_document(
                BufferedInputFile(buf.read(), "taraqqiyot.xlsx"),
                caption="📈 Taraqqiyot"
            )
        except: pass
        return True

    if call.data == "rep_plan":
        await call.answer()
        admin_state[user_id] = "dars_rejasi"
        await call.message.answer(
            "📅 Sinf va fanni yozing:\n<code>1 | Ingliz tili</code>",
            parse_mode="HTML"
        )
        return True

    if call.data == "menu_kitob_yuklash":
        admin_state[user_id] = "kitob_yuklash"
        await call.answer()
        await call.message.answer(
            "📖 Kitob yuklash\n\nFormat: Kitob nomi | Fan | Sinf | Muallif\n"
            "Masalan: <code>Matematika 1 | Matematika | 1 | Mirzayev</code>",
            parse_mode="HTML"
        ); return True

    if call.data == "menu_kitob_oqit":
        await call.answer()
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT id,title,fan,sinf FROM books ORDER BY id DESC LIMIT 10")
        books2 = cur2.fetchall(); cur2.close(); conn2.close()
        if not books2:
            await call.message.answer("❌ Hali kitob yuklanmagan."); return True
        rows2 = [[InlineKeyboardButton(
            text=f"📖 {b[1][:25]} ({b[2]}, {b[3]}-sinf)",
            callback_data=f"train_book:{b[0]}:{b[2]}:{b[3]}"
        )] for b in books2]
        await call.message.answer(
            "🎓 Qaysi kitobni o'qitamiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        ); return True

    if call.data == "menu_kitob_word":
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT id,title,fan,sinf FROM books ORDER BY id DESC LIMIT 10")
        books2 = cur2.fetchall(); cur2.close(); conn2.close()
        if not books2:
            await call.message.answer("❌ Hali kitob yuklanmagan."); return True
        rows2 = [[InlineKeyboardButton(
            text=f"📖 {b[1][:25]}",
            callback_data=f"book_make:{b[0]}"
        )] for b in books2]
        await call.answer()
        await call.message.answer(
            "📦 Qaysi kitobdan Word yasaymiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        ); return True

    if call.data.startswith("rasm_grade:"):
        gr = call.data.split(":")[1]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT DISTINCT d.subject_name FROM dts_tree d
            JOIN generated_tests g ON g.topic_code=d.topic_code
            WHERE d.grade=%s AND d.is_deleted=FALSE ORDER BY d.subject_name""", (gr,))
        fans = [r[0] for r in cur2.fetchall()]; cur2.close(); conn2.close()
        rows2 = [[InlineKeyboardButton(
            text=f"📚 {f}", callback_data=f"rasm_fan:{gr}:{f}"
        )] for f in fans]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="rasm_back")])
        await call.answer()
        await call.message.edit_text(
            f"🏫 {gr}-sinf — Fan tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        ); return True

    if call.data.startswith("rasm_fan:"):
        parts2=call.data.split(":",2); gr,fan2=parts2[1],parts2[2]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT DISTINCT d.kichik_name, d.topic_code,
            COUNT(g.id) as cnt,
            EXISTS(SELECT 1 FROM images i WHERE i.name LIKE d.topic_code||'-%') as has_img
            FROM dts_tree d
            JOIN generated_tests g ON g.topic_code=d.topic_code
            WHERE d.grade=%s AND d.subject_name=%s AND d.is_deleted=FALSE
            GROUP BY d.kichik_name, d.topic_code ORDER BY d.topic_code""", (gr,fan2))
        topics2=cur2.fetchall(); cur2.close(); conn2.close()
        rows2=[]
        for kname,tc,cnt,has_img in topics2:
            icon = "🖼" if has_img else "❌"
            rows2.append([InlineKeyboardButton(
                text=f"{icon} {kname[:35]} ({cnt}ta test)",
                callback_data=f"ai_rasm:{tc}:{fan2}:{gr}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"rasm_grade:{gr}")])
        await call.answer()
        await call.message.edit_text(
            f"📚 {fan2} — Mavzu tanlang:\n🖼=rasm bor ❌=rasm yo'q",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        ); return True

    if call.data.startswith("mtt_gr:"):
        gr = call.data[7:]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("SELECT DISTINCT subject_name FROM dts_tree WHERE grade=%s AND is_deleted=FALSE ORDER BY subject_name", (gr,))
        fans = [r[0] for r in cur2.fetchall()]; cur2.close(); conn2.close()
        rows2 = [[InlineKeyboardButton(text=f"📚 {f}", callback_data=f"mtt_fan:{gr}:{f}")] for f in fans]
        rows2.append([InlineKeyboardButton(text="✏️ Fan nomini o'zim yozaman", callback_data=f"mtt_fan_text:{gr}")])
        rows2.append([InlineKeyboardButton(text="⬅️", callback_data="mtt_back")])
        await call.answer()
        await call.message.edit_text(f"🏫 {gr}-sinf — Fan tanlang yoki o'zingiz yozing:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("mtt_fan_text:"):
        gr = call.data[13:]
        await call.answer()
        admin_state[user_id] = f"mtt_fan_input:{gr}"
        await call.message.answer(f"🏫 {gr}-sinf\n\nFan nomini yozing:\nMasalan: Ingliz tili")
        return True

    if call.data.startswith("mtt_fan:"):
        parts2 = call.data[8:].split(":",1); gr,fan2 = parts2[0],parts2[1]
        await call.answer()
        admin_state[user_id] = f"mtt_mavzu:{gr}:{fan2}"
        await call.message.answer(
            f"🚀 Mavzu tayyorlash\n"
            f"🏫 {gr}-sinf | 📚 {fan2}\n\n"
            f"Chorak va mavzularni yozing:\n\n"
            f"1/ Alphabet review\n"
            f"1/ Hello Greetings\n"
            f"2/ My family\n"
            f"2/ My house\n"
            f"...\n\n"
            f"Har qator: chorak_raqami/ mavzu_nomi"
        )
        return True

    if call.data.startswith("mtt_do:"):
        tc = call.data[7:]
        await call.answer()
        status3 = await call.message.answer(f"⏳ {tc} tayyorlanmoqda...")
        async def do_mtt():
            try:
                from mavzu_tayyorlovchi import tayyorla_mavzu
                async def pg(msg):
                    try: await status3.edit_text(msg)
                    except: pass
                result = await tayyorla_mavzu(tc, call.message.bot, call.message.chat.id, pg)
                if result.get("error"):
                    await call.message.answer(f"❌ {result['error']}")
                else:
                    await status3.delete()
            except Exception as e:
                await status3.edit_text(f"❌ {e}")
        asyncio.create_task(do_mtt())
        return True

    if call.data == "mtt_back":
        await call.answer(); await call.message.delete(); return True

    if call.data == "rasm_back":
        await call.answer(); await call.message.delete(); return True

    if call.data == "ai_rasm_auto":
        await call.answer()
        await call.message.answer(
            "📚 Qaysi fan uchun rasmlar generatsiya qilinsin?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧬 Biologiya",   callback_data="ai_auto:biologiya")],
                [InlineKeyboardButton(text="📐 Matematika",  callback_data="ai_auto:matematika")],
                [InlineKeyboardButton(text="⚡ Fizika",       callback_data="ai_auto:fizika")],
                [InlineKeyboardButton(text="🌍 Geografiya",  callback_data="ai_auto:geografiya")],
                [InlineKeyboardButton(text="📝 Ingliz tili", callback_data="ai_auto:ingliz tili")],
                [InlineKeyboardButton(text="🔬 Kimyo",       callback_data="ai_auto:kimyo")],
                [InlineKeyboardButton(text="⭐ Barcha fanlar", callback_data="ai_auto:all")],
            ])
        )
        return True

    if call.data.startswith("ai_auto:"):
        fan2 = call.data.split(":",1)[1]
        await call.answer()
        status_aa = await call.message.answer(f"⏳ {fan2} rasmlari yaratilmoqda...")
        async def do_auto():
            try:
                from rasim_generator import auto_generate_subject_images
                async def pg(msg):
                    try: await status_aa.edit_text(msg)
                    except: pass
                n = await auto_generate_subject_images(
                    fan2 if fan2!="all" else "all",
                    call.message.bot, call.message.chat.id, pg
                )
                await call.message.answer(f"✅ {n} ta rasm saqlandi!")
            except Exception as e:
                await status_aa.edit_text(f"❌ {e}")
        asyncio.create_task(do_auto())
        return True

    if call.data == "ai_rasm_custom":
        await call.answer()
        await call.message.answer(
            "🎨 Uslub tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎠 Multik (bolalar uchun)", callback_data="rasm_style:multik")],
                [InlineKeyboardButton(text="📸 Hayotiy (realistik)",     callback_data="rasm_style:hayotiy")],
                [InlineKeyboardButton(text="✏️ Chizma (qo'lda)",         callback_data="rasm_style:chizma")],
                [InlineKeyboardButton(text="🎨 Akvarel (bo'yoq)",        callback_data="rasm_style:akvarell")],
                [InlineKeyboardButton(text="📚 Darslik (ta'lim)",        callback_data="rasm_style:darslik")],
                [InlineKeyboardButton(text="🎮 3D (hajmli)",             callback_data="rasm_style:3d")],
                [InlineKeyboardButton(text="💬 Komiks (qiziqarli)",      callback_data="rasm_style:komiks")],
            ])
        )
        return True

    if call.data.startswith("xl_style:"):
        _raw = call.data.split(":")[1]
        force2 = "force" in _raw
        style2 = _raw.replace("_auto","").replace("_force","")
        xl_bytes2 = admin_state.pop(f"{user_id}_rasm_xl", None)
        if not xl_bytes2:
            await call.answer("❌ Fayl topilmadi, qayta yuboring", show_alert=True); return True
        await call.answer()
        style_names = {
            "multik":"🎠 Multik","hayotiy":"📸 Hayotiy","chizma":"✏️ Chizma",
            "akvarell":"🎨 Akvarel","darslik":"📚 Darslik","3d":"🎮 3D"
        }
        status_xl = await call.message.answer(
            f"✅ Uslub: {style_names.get(style2,style2)}\n"
            f"⏳ Rasmlar yaratilmoqda..."
        )
        async def do_xl_rasm():
            try:
                from rasim_generator import generate_from_excel
                async def pg(msg):
                    try: await status_xl.edit_text(msg)
                    except: pass
                result = await generate_from_excel(
                    xl_bytes2, call.message.bot,
                    call.message.chat.id, pg, style=style2, force=force2
                )
                if result.get("error"):
                    await call.message.answer(f"❌ {result['error']}")
            except Exception as e:
                await call.message.answer(f"❌ {e}")
        asyncio.create_task(do_xl_rasm())
        return True

    if call.data.startswith("rasm_style:"):
        style = call.data.split(":")[1]
        admin_state[user_id] = f"ai_rasm_custom:{style}"
        await call.answer()
        style_names = {
            "multik":"🎠 Multik","hayotiy":"📸 Hayotiy","chizma":"✏️ Chizma",
            "akvarell":"🎨 Akvarel","darslik":"📚 Darslik","3d":"🎮 3D","komiks":"💬 Komiks"
        }
        await call.message.answer(
            f"✅ Uslub: {style_names.get(style,style)}\n\n"
            f"Endi rasm tavsifini yozing:\n"
            f"Masalan: «bola onasiga gul berayapti»\n"
            f"yoki «teacher writing on blackboard»"
        )
        return True

    if call.data.startswith("ai_rasm:"):
        parts2 = call.data.split(":")
        tc, fan2, sinf2 = parts2[1], parts2[2], parts2[3] if len(parts2)>3 else "1"
        await call.answer()
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute(
            "SELECT question FROM generated_tests WHERE topic_code=%s LIMIT 5",
            (tc,)
        )
        questions = [r[0] for r in cur2.fetchall()]; cur2.close(); conn2.close()
        rows2 = [[InlineKeyboardButton(
            text=f"🖼 {q[:45]}...",
            callback_data=f"ai_rasm_q:{tc}:{fan2}:{sinf2}:{i}"
        )] for i,q in enumerate(questions[:5],1)]
        rows2.append([InlineKeyboardButton(
            text="🖼 Hammasi uchun (20 ta) — $0.80",
            callback_data=f"ai_rasm_all:{tc}:{fan2}:{sinf2}"
        )])
        await call.message.edit_text(
            f"🎨 {fan2} — {tc}\n\nQaysi savol uchun rasm?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        )
        return True

    if call.data.startswith("ai_rasm_q:"):
        parts2 = call.data.split(":")
        tc, fan2, sinf2, num = parts2[1], parts2[2], parts2[3], int(parts2[4])
        await call.answer()
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute(
            "SELECT id, question FROM generated_tests WHERE topic_code=%s LIMIT %s",
            (tc, num)
        )
        rows2 = cur2.fetchall(); cur2.close(); conn2.close()
        if not rows2: return
        tid, question = rows2[-1]
        status_r = await call.message.answer(f"⏳ Rasm yaratilmoqda...\n📝 {question[:60]}")
        async def do_rasm():
            try:
                from rasim_generator import generate_and_save
                fid = await generate_and_save(tc, question, fan2, sinf2, num, bot, call.message.chat.id)
                if fid:
                    conn3 = _get_db_conn(); cur3 = conn3.cursor()
                    cur3.execute("UPDATE generated_tests SET image_url=%s WHERE id=%s",
                                (f"{tc}-{num}", tid))
                    conn3.commit(); cur3.close(); conn3.close()
                    await status_r.edit_text(f"✅ Rasm saqlandi! Kod: {tc}-{num}")
                else:
                    await status_r.edit_text("❌ Rasm yaratishda xato.")
            except Exception as e:
                await status_r.edit_text(f"❌ {e}")
        asyncio.create_task(do_rasm())
        return True

    if call.data.startswith("ai_rasm_all:"):
        parts2 = call.data.split(":")
        tc, fan2, sinf2 = parts2[1], parts2[2], parts2[3] if len(parts2)>3 else "1"
        await call.answer()
        status_r = await call.message.answer(f"⏳ 20 ta rasm yaratilmoqda (taxm. 2 daqiqa)...")
        async def do_all_rasm():
            try:
                from rasim_generator import generate_topic_images
                async def prog(msg):
                    try: await status_r.edit_text(msg)
                    except: pass
                await generate_topic_images(tc, fan2, sinf2, 20, bot,
                                           call.message.chat.id, prog)
            except Exception as e:
                await status_r.edit_text(f"❌ {e}")
        asyncio.create_task(do_all_rasm())
        return True

    if call.data == "menu_ai_train":
        await call.answer()
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")):
            await call.message.answer("❌ GEMINI_API_KEY yoki OPENAI_API_KEY kerak!\nRailway → Variables ga qo'shing.")
            return True
        status_at = await call.message.answer(
            "🤖 Universal ekspert o'qitish boshlandi...\n"
            "5 profil: pedagog, metodist, huquqshunos, psixolog, professor"
        )
        async def do_train_all():
            try:
                async def prog(msg):
                    try: await status_at.edit_text(msg)
                    except: pass
                result = await train_all_profiles(prog)
                total = sum(result.values())
                await call.message.answer(f"🎉 Tayyor! {total} ta yangi bilim qo'shildi.")
            except Exception as e:
                await call.message.answer(f"❌ {e}")
        asyncio.create_task(do_train_all())
        return True

    if call.data == "menu_bilim_qidir":
        await call.answer()
        admin_state[user_id] = "kitob_qidirish"
        await call.message.answer("🔍 Qidiruv so'zini yozing:"); return True

    if call.data == "menu_bilim_must":
        await call.answer()
        await call.message.answer("📚 Bilimni mustahkamlash — o'quvchi menyusida."); return True

    if call.data == "menu_bilim_sin":
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT grade FROM (
            SELECT DISTINCT d.grade FROM generated_tests g
            JOIN dts_tree d ON d.topic_code=g.topic_code WHERE d.is_deleted=FALSE
        ) _g ORDER BY CASE WHEN grade~'^[0-9]+$' THEN grade::int ELSE 99 END""")
        grades=[r[0] for r in cur2.fetchall()]; cur2.close(); conn2.close()
        if not grades:
            await call.message.answer("❌ Hali test mavjud emas!"); return True
        rows2=[[InlineKeyboardButton(
            text=f"🏫 {g}-sinf" if str(g).isdigit() else f"📚 {g}",
            callback_data=f"sin_gr:{g}"
        )] for g in grades]
        await call.message.answer("🧪 Bilimni sinash\n\nSinf tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True


    return False
