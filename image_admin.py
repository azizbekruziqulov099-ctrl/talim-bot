"""
image_admin.py — Rasmlar boshqaruvi
Sinf → Fan → Mavzu → Rasmlar (pagination)
"""
import psycopg2, os, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")

def db(): return psycopg2.connect(DATABASE_URL)

def get_topic_info(name: str) -> dict:
    """topic_code ni DTS dan topadi."""
    # name = "1-01-2-02-03-02-002-5" → tc = "1-01-2-02-03-02-002"
    m = re.match(r'^(.+)-(\d+)$', name)
    if not m: return {}
    tc = m.group(1)
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT grade, subject_name, kichik_name
            FROM dts_tree WHERE topic_code=%s LIMIT 1
        """, (tc,))
        row = cur.fetchone(); cur.close(); conn.close()
        if row: return {"grade":row[0],"subject":row[1],"mavzu":row[2],"tc":tc}
    except: pass
    return {"tc": tc}

# ══════════════════════════════════════
# ASOSIY PANEL
# ══════════════════════════════════════
async def show_image_panel(message):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    total = cur.fetchone()[0]
    # Sinflar
    cur.execute("""
        SELECT grade, cnt FROM (
            SELECT d.grade, COUNT(i.id) as cnt
            FROM images i
            JOIN dts_tree d ON d.topic_code = SUBSTRING(i.name FROM '^(.+)-[0-9]+$')
            WHERE i.name ~ '^.+-[0-9]+$'
            GROUP BY d.grade
        ) _g
        ORDER BY CASE WHEN grade ~ '^[0-9]+$' THEN grade::int ELSE 99 END
    """)
    grades = cur.fetchall()
    cur.close(); conn.close()

    rows = []
    for gr, cnt in grades:
        lbl = f"{gr}-sinf" if str(gr).isdigit() else str(gr)
        rows.append([InlineKeyboardButton(
            text=f"🏫 {lbl} ({cnt} rasm)",
            callback_data=f"img_gr:{gr}"
        )])
    rows.append([
        InlineKeyboardButton(text="📋 Barchasi (tartibsiz)", callback_data="img_all:0"),
        InlineKeyboardButton(text="➕ Rasm qo'shish",       callback_data="img_add"),
    ])

    await message.answer(
        f"🖼 Rasmlar boshqaruvi\n📊 Jami: {total} ta\n\nSinf tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )

# ══════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════
async def handle_img_callback(call, user_id):
    data = call.data

    # ── ASOSIY PANEL ──
    if data == "img_panel":
        await call.answer()
        await show_image_panel(call.message)
        return

    # ── SINF ──
    if data.startswith("img_gr:"):
        gr = data[7:]
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT d.subject_name, COUNT(i.id) as cnt
            FROM images i
            JOIN dts_tree d ON d.topic_code = SUBSTRING(i.name FROM '^(.+)-[0-9]+$')
            WHERE d.grade=%s AND i.name ~ '^.+-[0-9]+$'
            GROUP BY d.subject_name ORDER BY d.subject_name
        """, (gr,))
        subjects = cur.fetchall(); cur.close(); conn.close()

        rows = [[InlineKeyboardButton(
            text=f"📚 {s} ({cnt})",
            callback_data=f"img_subj:{gr}:{s}"
        )] for s,cnt in subjects]
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="img_panel")])
        await call.answer()
        lbl = f"{gr}-sinf" if str(gr).isdigit() else str(gr)
        await call.message.edit_text(
            f"🏫 {lbl} — Fan tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return

    # ── FAN ──
    if data.startswith("img_subj:"):
        parts = data[9:].split(":",1)
        gr, subj = parts[0], parts[1]
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT d.kichik_name, d.topic_code, COUNT(i.id) as cnt
            FROM images i
            JOIN dts_tree d ON d.topic_code = SUBSTRING(i.name FROM '^(.+)-[0-9]+$')
            WHERE d.grade=%s AND d.subject_name=%s AND i.name ~ '^.+-[0-9]+$'
            GROUP BY d.kichik_name, d.topic_code
            ORDER BY d.topic_code
        """, (gr, subj))
        topics = cur.fetchall(); cur.close(); conn.close()

        rows = [[InlineKeyboardButton(
            text=f"📝 {kn[:35]} ({cnt})",
            callback_data=f"img_tc:{tc}:0"
        )] for kn,tc,cnt in topics]
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"img_gr:{gr}")])
        await call.answer()
        await call.message.edit_text(
            f"📚 {subj} — Mavzu tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
        return

    # ── MAVZU RASMLAR (PAGINATION) ──
    if data.startswith("img_tc:"):
        parts = data[7:].split(":")
        tc, page = parts[0], int(parts[1]) if len(parts)>1 else 0
        PAGE = 5
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT name, file_id FROM images
            WHERE name LIKE %s ORDER BY name
        """, (f"{tc}-%",))
        all_imgs = cur.fetchall()
        # DTS dan ma'lumot
        cur.execute("SELECT grade,subject_name,kichik_name FROM dts_tree WHERE topic_code=%s LIMIT 1", (tc,))
        dts = cur.fetchone(); cur.close(); conn.close()

        total = len(all_imgs)
        page_imgs = all_imgs[page*PAGE:(page+1)*PAGE]

        mavzu_name = dts[2] if dts else tc
        gr = dts[0] if dts else ""
        subj = dts[1] if dts else ""

        await call.answer()
        # Birinchi rasmni ko'rsatamiz
        if page_imgs:
            name, fid = page_imgs[0]
            rows = []
            # Rasm nomerlari
            num_row = []
            for i, (nm, _) in enumerate(page_imgs):
                n = nm.split("-")[-1]
                num_row.append(InlineKeyboardButton(
                    text=f"🖼{n}", callback_data=f"img_show:{nm}:{tc}:{page}"
                ))
            rows.append(num_row)
            # Navigatsiya
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_tc:{tc}:{page-1}"))
            nav.append(InlineKeyboardButton(text=f"{page*PAGE+1}-{min((page+1)*PAGE,total)}/{total}", callback_data="noop"))
            if (page+1)*PAGE < total:
                nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_tc:{tc}:{page+1}"))
            if nav: rows.append(nav)
            rows.append([
                InlineKeyboardButton(text="🗑 Mavzuni o'chir", callback_data=f"img_del_tc:{tc}"),
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"img_subj:{gr}:{subj}"),
            ])
            # Rasmni yuborish
            try:
                await call.message.answer_photo(
                    fid,
                    caption=f"🖼 {name}\n📝 {mavzu_name}\n📊 {total} ta rasm",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
                )
            except:
                await call.message.answer(
                    f"📝 {mavzu_name}\n📊 {total} ta rasm",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
                )
        return

    # ── BITTA RASM KO'RISH ──
    if data.startswith("img_show:"):
        parts = data[9:].split(":")
        name, tc, page = parts[0], parts[1], int(parts[2]) if len(parts)>2 else 0
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
        row = cur.fetchone()
        # Barcha rasmlar shu mavzudan
        cur.execute("SELECT name FROM images WHERE name LIKE %s ORDER BY name", (f"{tc}-%",))
        all_names = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()

        if not row:
            await call.answer("❌ Rasm topilmadi", show_alert=True); return

        idx = all_names.index(name) if name in all_names else 0
        prev_name = all_names[idx-1] if idx > 0 else None
        next_name = all_names[idx+1] if idx < len(all_names)-1 else None

        nav = []
        if prev_name:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_show:{prev_name}:{tc}:{page}"))
        nav.append(InlineKeyboardButton(text=f"{idx+1}/{len(all_names)}", callback_data="noop"))
        if next_name:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_show:{next_name}:{tc}:{page}"))

        rows = [nav, [
            InlineKeyboardButton(text="🗑 O'chir", callback_data=f"img_del:{name}:{tc}:{page}"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"img_tc:{tc}:{page}"),
        ]]
        await call.answer()
        try:
            await call.message.answer_photo(
                row[0],
                caption=f"🖼 {name}\n{idx+1}/{len(all_names)}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
            )
        except: pass
        return

    # ── O'CHIRISH ──
    if data.startswith("img_del:"):
        parts = data[8:].split(":")
        name, tc, page = parts[0], parts[1], int(parts[2]) if len(parts)>2 else 0
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE name=%s", (name,))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"🗑 {name} o'chirildi", show_alert=True)
        # Mavzuga qaytamiz
        await handle_img_callback(type('obj',(object,),{'data':f'img_tc:{tc}:{page}','answer':call.answer,'message':call.message,'from_user':call.from_user})(), user_id)
        return

    if data.startswith("img_del_tc:"):
        tc = data[11:]
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE name LIKE %s", (f"{tc}-%",))
        deleted = cur.rowcount; conn.commit(); cur.close(); conn.close()
        await call.answer(f"🗑 {deleted} ta rasm o'chirildi", show_alert=True)
        await call.message.delete()
        return

    # ── BARCHASI ──
    if data.startswith("img_all:"):
        page = int(data[8:])
        PAGE = 20
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM images")
        total = cur.fetchone()[0]
        cur.execute("SELECT name FROM images ORDER BY name LIMIT %s OFFSET %s",
                   (PAGE, page*PAGE))
        imgs = [r[0] for r in cur.fetchall()]
        cur.close(); conn.close()

        lines = [f"📋 Barcha rasmlar ({total} ta)\n"]
        for nm in imgs:
            lines.append(f"• {nm}")

        nav = []
        if page > 0: nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_all:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PAGE+1}-{min((page+1)*PAGE,total)}/{total}", callback_data="noop"))
        if (page+1)*PAGE < total: nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_all:{page+1}"))

        rows = [nav] if nav else []
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="img_panel")])
        await call.answer()
        await call.message.edit_text("\n".join(lines[:25]),
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return
