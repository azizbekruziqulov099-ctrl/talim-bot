"""cb_kitob.py — Kitob callback handlerlari"""
import psycopg2, asyncio, os, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, FSInputFile
from storage import user_state, admin_state, temp_user
DATABASE_URL = os.getenv("DATABASE_URL","")
ADMINS = list(map(int, os.getenv("ADMINS","0").split(",")))
def _get_db_conn(): return psycopg2.connect(DATABASE_URL)

def _mavzu_hash(nom):
    """Mavzu nomining qisqa belgisi (Talim.py bilan bir xil)."""
    import hashlib
    return hashlib.md5((nom or "").strip().encode()).hexdigest()[:6]


async def handle_kitob(call, user_id, admin_state, user_state, temp_user, bot):
    d=call.data
    # ── KITOB CALLBACKS ──
    if call.data.startswith("kitob_parol:"):
        book_id2=int(call.data[12:]); await call.answer()
        admin_state[user_id]=f"kitob_set_parol:{book_id2}"
        await call.message.answer("🔑 Yangi 4 xonali parol yozing (masalan: 1234):")
        return True

    if call.data.startswith("kitob_davom:"):
        book_id2=int(call.data[12:])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT MAX(page_num) FROM book_pages WHERE book_id=%s",(book_id2,))
        last=(cur2.fetchone() or [0])[0] or 0
        cur2.close(); conn2.close()
        next_page = last + 1
        admin_state[user_id] = f"kitob_qolda_bet:{book_id2}:{next_page}"
        await call.message.answer(
            f"✍️ Davom etish — Bet {next_page}\n\n"
            f"📝 Bet {next_page} matnini yozing:\n"
            f"(Tugash: <code>tugat</code>)",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Kitobni tugatish",callback_data=f"kitob_qolda_tugat:{book_id2}:{last}")
            ]])
        )
        return True

    if call.data.startswith("kitob_edit_page:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        admin_state[user_id] = f"kitob_edit_text:{book_id2}:{page2}"
        from kitob_bazasi import get_page
        pg = get_page(book_id2, page2)
        cur_text = (pg.get("text") or "")[:300] if pg else ""
        await call.message.answer(
            f"✏️ Bet {page2} yangi matnini yozing:"
        )
        return True

    if call.data.startswith("kitob_del_page:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("DELETE FROM book_exercises WHERE book_id=%s AND page_num=%s",(book_id2,page2))
        cur2.execute("DELETE FROM book_pages WHERE book_id=%s AND page_num=%s",(book_id2,page2))
        conn2.commit(); cur2.close(); conn2.close()
        await call.message.answer(f"🗑 Bet {page2} o'chirildi!")
        return True

    if call.data.startswith("kitob_next_bet:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        await call.message.answer(
            f"📝 Bet {page2} matnini yozing (LaTeX):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Kitobni tugatish", callback_data=f"kitob_qolda_tugat:{book_id2}:{page2-1}")
            ]])
        )
        admin_state[user_id] = f"kitob_qolda_bet:{book_id2}:{page2}"
        return True

    if call.data.startswith("kitob_qolda_tugat:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); last_page=int(parts2[2])
        await call.answer()
        admin_state.pop(user_id, None)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE books SET total_pages=%s WHERE id=%s",(last_page,book_id2))
        conn2.commit(); cur2.close(); conn2.close()
        await call.message.answer(f"✅ Kitob saqlandi!\n📄 {last_page} bet\n🔑 ID: {book_id2}")
        return True

    if call.data == "kitob_qolda":
        await call.answer()
        admin_state[user_id] = "kitob_qolda_info"
        await call.message.answer(
            "✍️ Qo'lda terish\n\n"
            "Kitob ma'lumotlarini yozing:\n"
            "<code>Nom | Fan | Sinf | Muallif</code>\n\n"
            "Masalan:\n"
            "<code>Matematika | Matematika | 7 | Usmonov</code>",
            parse_mode="HTML"
        )
        return True

    if call.data == "kitob_upload":
        await call.answer()
        admin_state[user_id] = "kitob_yuklash"
        await call.message.answer(
            "📤 PDF faylni yuboring!\n\n"
            "Ixtiyoriy: avval ma'lumot yozing:\n"
            "<code>Nom | Fan | Sinf | Muallif</code>",
            parse_mode="HTML"
        )
        return True

    if call.data.startswith("kitob_info:"):
        book_id=int(call.data[11:])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT title,sinf,fan,muallif,total_pages FROM books WHERE id=%s",(book_id,))
        b=cur2.fetchone()
        cur2.execute("SELECT COUNT(*) FROM book_exercises WHERE book_id=%s",(book_id,))
        ex_cnt=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
        if b:
            await call.message.answer(
                f"📖 {b[0]}\n🏫 {b[1]}-sinf | 📚 {b[2]}\n"
                f"📄 {b[4]} bet | 📐 {ex_cnt} misol\n🔑 ID: {book_id}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📖 Betlarni ko'rish",callback_data=f"kitob_bet:{book_id}:1")],
                    [InlineKeyboardButton(text="✍️ Davom ettirish",callback_data=f"kitob_davom:{book_id}")],
                    [InlineKeyboardButton(text="🔍 Qidiruv",callback_data=f"kitob_qidir:{book_id}"),
                     InlineKeyboardButton(text="🔑 Parol",callback_data=f"kitob_parol:{book_id}")],
                    [InlineKeyboardButton(text="🗑 O'chirish",callback_data=f"kitob_del:{book_id}")],
                ])
            )
        return True

    if call.data.startswith("kitob_bet:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        from kitob_bazasi import get_page, get_exercises, render_page_as_image
        pg=get_page(book_id2,page2)
        if not pg:
            await call.message.answer("❌ Bet topilmadi"); return True
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT total_pages FROM books WHERE id=%s",(book_id2,))
        tot2=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
        nav=[]
        if page2>1: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"kitob_bet:{book_id2}:{page2-1}"))
        nav.append(InlineKeyboardButton(text=f"📄 {page2}/{tot2}",callback_data=f"kitob_goto:{book_id2}"))
        if page2<tot2: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"kitob_bet:{book_id2}:{page2+1}"))
        rows2=[nav,[
            InlineKeyboardButton(text="✏️ Tahrirlash",callback_data=f"kitob_edit_page:{book_id2}:{page2}"),
            InlineKeyboardButton(text="🎯 Misollar",callback_data=f"kitob_test:{book_id2}:{page2}")
        ],[
            InlineKeyboardButton(text="🗑 Betni o'chir",callback_data=f"kitob_del_page:{book_id2}:{page2}"),
            InlineKeyboardButton(text="🗑 Kitobni o'chir",callback_data=f"kitob_del:{book_id2}"),
        ]]
        caption=f"📖 Bet {page2}"
        if pg.get("section"): caption+=f" — {pg['section']}"
        kb=InlineKeyboardMarkup(inline_keyboard=rows2)
        img=await render_page_as_image(pg["text"],page2)

        # Matnli ko'rinish — edit ishlaydi, yo'qolmaydi
        page_txt = pg["text"][:800] if pg.get("text") else ""
        full_txt = f"📖 Bet {page2}"
        if pg.get("section"): full_txt += f" — {pg['section']}"
        full_txt += f"\n\n{page_txt}"

        try:
            await call.message.edit_text(full_txt, reply_markup=kb)
        except:
            try: await call.message.delete()
            except: pass
            await call.message.answer(full_txt, reply_markup=kb)
        return True

    if call.data.startswith("kitob_write:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
    if call.data.startswith("kitob_goto:"):
        book_id2=int(call.data[11:])
        await call.answer()
        admin_state[user_id] = f"kitob_goto:{book_id2}"
        await call.message.answer("📄 Qaysi betga o'tmoqchisiz? Raqam yozing:")
        return True

    if call.data.startswith("kitob_matn:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        from kitob_bazasi import get_page
        pg = get_page(book_id2, page2)
        if not pg:
            await call.message.answer("❌ Bet topilmadi"); return True
        txt = pg.get("text","")
        for i in range(0, min(len(txt), 8000), 4000):
            await call.message.answer(txt[i:i+4000])
        await call.message.answer(
            f"📖 Bet {page2}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ O'zgartirish", callback_data=f"kitob_write:{book_id2}:{page2}")],
                [InlineKeyboardButton(text="⬅️ Betga qaytish", callback_data=f"kitob_bet:{book_id2}:{page2}")],
            ])
        )
        return True

    if call.data.startswith("kitob_qidir:"):
        book_id2=int(call.data[12:]); await call.answer()
        admin_state[user_id]=f"kitob_search:{book_id2}"
        await call.message.answer("🔍 So'z yozing:"); return True

    if call.data.startswith("kitob_del:"):
        book_id2=int(call.data[10:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT title FROM books WHERE id=%s",(book_id2,))
        b2=cur2.fetchone(); cur2.close(); conn2.close()
        title2=b2[0] if b2 else "Kitob"
        admin_state[user_id]=f"kitob_del_confirm:{book_id2}"
        await call.message.answer(
            f"⚠️ '{title2}' ni o'chirmoqchimisiz?\n\n"
            f"Tasdiqlash uchun kitob parolini yozing\n"
            f"(Standart parol: 0000)"
        )
        return True

    if call.data.startswith("kitob_test:"):
        parts2=call.data.split(":"); book_id2=int(parts2[1]); page2=int(parts2[2])
        await call.answer()
        from kitob_bazasi import get_exercises
        exs=get_exercises(book_id2,page_num=page2,limit=20)
        if not exs: await call.message.answer("❌ Misol topilmadi!"); return True
        txt=f"📐 {page2}-bet misollari ({len(exs)} ta):\n\n"
        for i,e in enumerate(exs,1): txt+=f"{i}. {e[:100]}\n\n"
        await call.message.answer(txt[:3000]); return True

    if call.data.startswith("sin_gr:"):
        gr=call.data[7:]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT d.subject_name, COUNT(DISTINCT g.topic_code) as cnt
            FROM generated_tests g JOIN dts_tree d ON d.topic_code=g.topic_code
            WHERE d.grade=%s AND d.is_deleted=FALSE
            GROUP BY d.subject_name ORDER BY d.subject_name""",(gr,))
        fans=cur2.fetchall(); cur2.close(); conn2.close()
        rows2=[[InlineKeyboardButton(text=f"📚 {f} ({c} mavzu)",callback_data=f"sin_fan:{gr}:{f}")] for f,c in fans]
        rows2.append([InlineKeyboardButton(text="⬅️",callback_data="menu_bilim_sin")])
        try: await call.message.edit_text(f"🏫 {gr}-sinf — Fan:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"🏫 {gr}-sinf — Fan:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("sin_fan:"):
        # sin_fan:gr:fan  yoki  sin_fan:gr:fan:page
        raw = call.data[8:]
        parts2 = raw.rsplit(":", 1)
        # page oxirida raqam bo'lsa
        try:
            page = int(parts2[-1])
            fan_gr = parts2[0].split(":", 1)
            gr, fan2 = fan_gr[0], fan_gr[1]
        except:
            parts2b = raw.split(":", 1); gr, fan2 = parts2b[0], parts2b[1]
            page = 0

        await call.answer()
        PAGE = 10
        conn2=_get_db_conn();cur2=conn2.cursor()
        # MAVZU darajasi — kichik mavzular ko'rinmaydi
        cur2.execute("""SELECT d.mavzu_name, d.mavzu_code,
                   ARRAY_AGG(DISTINCT d.topic_code) AS kodlar,
                   COUNT(g.id) as cnt
            FROM generated_tests g JOIN dts_tree d ON d.topic_code=g.topic_code
            WHERE d.grade=%s AND d.subject_name=%s AND d.is_deleted=FALSE
            AND d.mavzu_code IS NOT NULL
            GROUP BY d.mavzu_name, d.mavzu_code ORDER BY d.mavzu_code""",(gr,fan2))
        mavzular=cur2.fetchall(); cur2.close(); conn2.close()

        total = len(mavzular)
        page_items = mavzular[page*PAGE:(page+1)*PAGE]

        import ts_cache
        rows2=[]
        for mname, mcode, kodlar, cnt in page_items:
            sid = ts_cache.saqla(kodlar, mname, gr, fan2, cnt)
            cb = f"ts_sel:{sid}" if sid else f"ts_mavzu:{mcode}|{gr}|{_mavzu_hash(mname)}"
            rows2.append([InlineKeyboardButton(
                text=f"📝 {(mname or mcode)[:38]} ({cnt})",
                callback_data=cb
            )])

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"sin_fan:{gr}:{fan2}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PAGE+1}-{min((page+1)*PAGE,total)}/{total}", callback_data="noop"))
        if (page+1)*PAGE < total:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"sin_fan:{gr}:{fan2}:{page+1}"))
        if nav: rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="⬅️", callback_data=f"sin_gr:{gr}")])

        try: await call.message.edit_text(f"📚 {fan2} — Mavzu ({total} ta):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"📚 {fan2} — Mavzu ({total} ta):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("sin_mavzu:"):
        tc2=call.data[10:]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=%s",(tc2,))
        cnt2=cur2.fetchone()[0]
        cur2.execute("SELECT kichik_name FROM dts_tree WHERE topic_code=%s LIMIT 1",(tc2,))
        kn2=(cur2.fetchone() or [tc2])[0]; cur2.close(); conn2.close()
        try: await call.message.edit_text(
            f"📝 {kn2}\n📊 {cnt2} ta test\n\nQanday boshlash?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Tez (20 ta aralash)", callback_data=f"ts_start:{tc2}")],
                [InlineKeyboardButton(text="⚙️ Sozlamalar bilan",    callback_data=f"ts_settings:{tc2}")],
                [InlineKeyboardButton(text="⬅️", callback_data="menu_bilim_sin")],
            ])
        )
        except: pass
        return True

    if call.data == "mustah_back":
        await call.message.delete()
        return True

    if call.data.startswith("stnav_grade:"):
        grade = call.data.split(":")[1]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""
            SELECT DISTINCT subject_name FROM dts_tree
            WHERE grade=%s AND is_deleted=FALSE ORDER BY subject_name
        """, (grade,))
        subjects = [r[0] for r in cur2.fetchall()]
        cur2.close(); conn2.close()
        rows = [[InlineKeyboardButton(text=f"📘 {s}", callback_data=f"stnav_subj:{grade}:{s}")]
                for s in subjects]
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="stnav_back_grade")])
        await call.message.edit_text(
            f"🏫 {grade + '-sinf' if str(grade).isdigit() else grade}\nFan tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data.startswith("stnav_subj:"):
        parts2 = call.data.split(":")
        grade, subj = parts2[1], ":".join(parts2[2:])
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        cur2.execute("""
            SELECT DISTINCT mavzu_name, mavzu_code FROM dts_tree
            WHERE grade=%s AND subject_name=%s AND is_deleted=FALSE
            ORDER BY mavzu_code
        """, (grade, subj))
        mavzular = cur2.fetchall()
        cur2.close(); conn2.close()
        rows = []
        for mavzu_name, mavzu_code in mavzular[:20]:
            # Test soni
            rows.append([InlineKeyboardButton(
                text=f"📝 {mavzu_name}",
                callback_data=f"stnav_topic:{grade}:{subj}:{mavzu_code}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"stnav_grade:{grade}")])
        await call.message.edit_text(
            f"📘 {subj}\nMavzu tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data.startswith("stnav_topic:"):
        parts2 = call.data.split(":")
        grade, subj, mavzu_code = parts2[1], parts2[2], parts2[3]
        conn2 = _get_db_conn(); cur2 = conn2.cursor()
        # Kichik mavzular
        cur2.execute("""
            SELECT DISTINCT kichik_name, topic_code FROM dts_tree
            WHERE grade=%s AND subject_name=%s AND mavzu_code=%s AND is_deleted=FALSE
            ORDER BY kichik_name
        """, (grade, subj, mavzu_code))
        kichiklar = cur2.fetchall()
        # Test sonlari
        rows = []
        for kichik_name, topic_code in kichiklar:
            cur2.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=%s", (topic_code,))
            cnt = cur2.fetchone()[0]
            rows.append([InlineKeyboardButton(
                text=f"{'✅' if cnt>0 else '❌'} {kichik_name} ({cnt} ta)",
                callback_data=f"ts_start:{topic_code}"
            )])
        cur2.close(); conn2.close()
        rows.append([InlineKeyboardButton(
            text="⬅️ Orqaga", callback_data=f"stnav_subj:{grade}:{subj}"
        )])
        await call.message.edit_text(
            f"📝 Mavzu tanlang:\n(✅=test bor, ❌=hali yo'q)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return True

    if call.data == "stnav_back_grade":
        # Bilimni sinash ga qaytish
        await call.message.delete()
        return True
    # ════════════════════════════

    return False
