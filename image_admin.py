"""
image_admin.py — Rasmlar boshqaruvi
topic_code prefix bo'yicha guruhlash + pagination
"""
import psycopg2, os, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")
def db(): return psycopg2.connect(DATABASE_URL)

async def safe_edit(call, text, kb):
    """Xabar turini tekshirib edit qiladi."""
    try:
        if call.message.text:
            await call.message.edit_text(text, reply_markup=kb)
        else:
            await call.message.answer(text, reply_markup=kb)
    except:
        await call.message.answer(text, reply_markup=kb)

async def show_image_panel(message):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    total = cur.fetchone()[0]
    # Topic prefix bo'yicha guruhlash
    cur.execute("""
        SELECT SUBSTRING(name FROM '^(.+)-[0-9]+$') as tc, COUNT(*) as cnt
        FROM images WHERE name ~ '^.+-[0-9]+$'
        GROUP BY tc ORDER BY tc LIMIT 50
    """)
    groups = cur.fetchall()
    cur.close(); conn.close()

    if not groups:
        await message.answer(f"🖼 Rasmlar: {total} ta\nHali guruhlanmagan.")
        return

    # DTS dan sinf/fan ma'lumotini olamiz
    tcs = [g[0] for g in groups]
    try:
        conn2 = db(); cur2 = conn2.cursor()
        ph = ",".join(["%s"]*len(tcs))
        cur2.execute(f"""
            SELECT topic_code, grade, subject_name, kichik_name
            FROM dts_tree WHERE topic_code IN ({ph})
        """, tcs)
        dts_map = {r[0]:r for r in cur2.fetchall()}
        cur2.close(); conn2.close()
    except: dts_map = {}

    # Sinf bo'yicha guruhlash
    by_grade = {}
    for tc, cnt in groups:
        info = dts_map.get(tc)
        grade = info[1] if info else "?"
        if grade not in by_grade: by_grade[grade] = 0
        by_grade[grade] += cnt

    rows = []
    for gr in sorted(by_grade.keys(),
                     key=lambda x: int(x) if str(x).isdigit() else 99):
        lbl = f"{gr}-sinf" if str(gr).isdigit() else str(gr)
        rows.append([InlineKeyboardButton(
            text=f"🏫 {lbl} ({by_grade[gr]} rasm)",
            callback_data=f"img_gr:{gr}"
        )])
    rows.append([
        InlineKeyboardButton(text="📋 Barchasi", callback_data="img_all:0"),
    ])
    await message.answer(
        f"🖼 Rasmlar boshqaruvi\n📊 Jami: {total} ta\n\nSinf tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )

async def handle_img_callback(call, user_id):
    data = call.data
    await call.answer()

    if data == "img_panel":
        await show_image_panel(call.message)
        return

    # SINF
    if data.startswith("img_gr:"):
        gr = data[7:]
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT SUBSTRING(i.name FROM '^(.+)-[0-9]+$') as tc, COUNT(*) as cnt
            FROM images i WHERE i.name ~ '^.+-[0-9]+$'
            GROUP BY tc
        """)
        all_groups = cur.fetchall()
        cur.close(); conn.close()

        tcs = [g[0] for g in all_groups]
        try:
            conn2 = db(); cur2 = conn2.cursor()
            ph = ",".join(["%s"]*len(tcs))
            cur2.execute(f"""SELECT topic_code,grade,subject_name,kichik_name
                FROM dts_tree WHERE topic_code IN ({ph})""", tcs)
            dts_map = {r[0]:r for r in cur2.fetchall()}
            cur2.close(); conn2.close()
        except: dts_map = {}

        by_subj = {}
        for tc, cnt in all_groups:
            info = dts_map.get(tc)
            if not info or str(info[1]) != str(gr): continue
            subj = info[2] or "Boshqa"
            if subj not in by_subj: by_subj[subj] = 0
            by_subj[subj] += cnt

        if not by_subj:
            await call.message.answer("Fan topilmadi."); return

        rows = [[InlineKeyboardButton(
            text=f"📚 {s} ({c})",
            callback_data=f"img_subj:{gr}:{s}"
        )] for s,c in sorted(by_subj.items())]
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="img_panel")])
        lbl = f"{gr}-sinf" if str(gr).isdigit() else str(gr)
        await safe_edit(call, f"🏫 {lbl} — Fan:", InlineKeyboardMarkup(inline_keyboard=rows))
        return

    # FAN
    if data.startswith("img_subj:"):
        parts = data[9:].split(":",1)
        gr, subj = parts[0], parts[1]
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT SUBSTRING(i.name FROM '^(.+)-[0-9]+$') as tc, COUNT(*) as cnt
            FROM images i WHERE i.name ~ '^.+-[0-9]+$'
            GROUP BY tc
        """)
        all_groups = cur.fetchall()
        cur.close(); conn.close()

        tcs = [g[0] for g in all_groups]
        try:
            conn2 = db(); cur2 = conn2.cursor()
            ph = ",".join(["%s"]*len(tcs))
            cur2.execute(f"SELECT topic_code,grade,subject_name,kichik_name FROM dts_tree WHERE topic_code IN ({ph})", tcs)
            dts_map = {r[0]:r for r in cur2.fetchall()}
            cur2.close(); conn2.close()
        except: dts_map = {}

        rows = []
        for tc, cnt in all_groups:
            info = dts_map.get(tc)
            if not info: continue
            if str(info[1]) != str(gr) or info[2] != subj: continue
            kn = info[3] or tc
            rows.append([InlineKeyboardButton(
                text=f"📝 {kn[:40]} ({cnt})",
                callback_data=f"img_tc:{tc}:0"
            )])

        if not rows:
            await call.message.answer("Mavzu topilmadi."); return

        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"img_gr:{gr}")])
        await safe_edit(call, f"📚 {subj} — Mavzu:", InlineKeyboardMarkup(inline_keyboard=rows))
        return

    # MAVZU RASMLAR
    if data.startswith("img_tc:"):
        parts = data[7:].split(":")
        tc, page = parts[0], int(parts[1]) if len(parts)>1 else 0
        PAGE = 8
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT name,file_id FROM images WHERE name LIKE %s ORDER BY name",
                   (f"{tc}-%",))
        all_imgs = cur.fetchall()
        cur.execute("SELECT grade,subject_name,kichik_name FROM dts_tree WHERE topic_code=%s LIMIT 1", (tc,))
        dts = cur.fetchone(); cur.close(); conn.close()

        total = len(all_imgs)
        page_imgs = all_imgs[page*PAGE:(page+1)*PAGE]
        mavzu_name = (dts[2] if dts else tc) or tc

        # Rasm tugmalari
        rows = []
        num_row = []
        for nm, fid in page_imgs:
            n = nm.split("-")[-1]
            num_row.append(InlineKeyboardButton(
                text=f"🖼{n}", callback_data=f"img_show:{nm}:{tc}:{page}"
            ))
        if num_row: rows.append(num_row)

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_tc:{tc}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PAGE+1}-{min((page+1)*PAGE,total)}/{total}", callback_data="noop"))
        if (page+1)*PAGE < total:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_tc:{tc}:{page+1}"))
        if nav: rows.append(nav)

        rows.append([
            InlineKeyboardButton(text="🗑 O'chir", callback_data=f"img_del_tc:{tc}"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="img_panel"),
        ])

        txt = f"📝 {mavzu_name}\n📊 {total} ta rasm\n\nRasm raqamini bosing:"
        if page_imgs:
            try:
                await call.message.answer_photo(
                    page_imgs[0][1], caption=txt,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
                )
            except:
                await call.message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return

    # BITTA RASM
    if data.startswith("img_show:"):
        parts = data[9:].split(":")
        name, tc, page = parts[0], parts[1], int(parts[2]) if len(parts)>2 else 0
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
        row = cur.fetchone()
        cur.execute("SELECT name FROM images WHERE name LIKE %s ORDER BY name", (f"{tc}-%",))
        all_names = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()

        if not row:
            await call.message.answer("❌ Rasm topilmadi"); return

        idx = all_names.index(name) if name in all_names else 0
        nav = []
        if idx > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_show:{all_names[idx-1]}:{tc}:{page}"))
        nav.append(InlineKeyboardButton(text=f"{idx+1}/{len(all_names)}", callback_data="noop"))
        if idx < len(all_names)-1:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_show:{all_names[idx+1]}:{tc}:{page}"))

        rows = [nav, [
            InlineKeyboardButton(text="🗑 O'chir", callback_data=f"img_del:{name}:{tc}:{page}"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"img_tc:{tc}:{page}"),
        ]]
        await call.message.answer_photo(
            row[0], caption=f"🖼 {name}\n{idx+1}/{len(all_names)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return

    # O'CHIRISH
    if data.startswith("img_del:"):
        parts = data[8:].split(":")
        name, tc, page = parts[0], parts[1], int(parts[2]) if len(parts)>2 else 0
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE name=%s", (name,))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"🗑 O'chirildi", show_alert=True)
        return

    if data.startswith("img_del_tc:"):
        tc = data[11:]
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE name LIKE %s", (f"{tc}-%",))
        n = cur.rowcount; conn.commit(); cur.close(); conn.close()
        await call.answer(f"🗑 {n} ta o'chirildi", show_alert=True)
        return

    # BARCHASI
    if data.startswith("img_all:"):
        page = int(data[8:]); PAGE = 20
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM images"); total = cur.fetchone()[0]
        cur.execute("SELECT name FROM images ORDER BY name LIMIT %s OFFSET %s",
                   (PAGE, page*PAGE))
        imgs = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()

        nav = []
        if page > 0: nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_all:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PAGE+1}-{min((page+1)*PAGE,total)}/{total}", callback_data="noop"))
        if (page+1)*PAGE < total: nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_all:{page+1}"))

        rows = [nav, [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="img_panel")]]
        lines = [f"📋 Barcha rasmlar ({total} ta)\n"] + [f"• {nm}" for nm in imgs]
        await safe_edit(call, "\n".join(lines[:25]), InlineKeyboardMarkup(inline_keyboard=rows))
        return
