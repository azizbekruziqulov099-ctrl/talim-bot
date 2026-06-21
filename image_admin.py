import psycopg2, os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)


async def show_image_panel(message):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    total = cur.fetchone()[0]

    cur.execute("""
        SELECT SUBSTRING(name FROM '^(.+)-[0-9]+$') as prefix, COUNT(*) as cnt
        FROM images
        WHERE name ~ '^.+-[0-9]+$'
        GROUP BY prefix
        ORDER BY prefix
        LIMIT 20
    """)
    groups = cur.fetchall()
    cur.close(); conn.close()

    text = (
        f"🖼 Rasmlar boshqaruvi\n\n"
        f"📊 Jami: {total} ta rasm\n"
        f"📁 Guruhlar: {len(groups)} ta\n\n"
        f"Guruhni tanlang:"
    )

    rows = []
    for prefix, cnt in groups[:15]:
        short = prefix[-25:] if len(prefix) > 25 else prefix
        rows.append([InlineKeyboardButton(
            text=f"📁 {short} ({cnt})",
            callback_data=f"img_g:{prefix[:45]}"
        )])

    rows.append([
        InlineKeyboardButton(text="📋 Barchasi", callback_data="img_all:0"),
        InlineKeyboardButton(text="🗑 Hammasini o'chir", callback_data="img_del_all"),
    ])

    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


async def handle_img_callback(call, user_id):
    data = call.data

    if data == "img_panel":
        await call.answer()
        await show_image_panel(call.message)

    elif data.startswith("img_g:"):
        prefix = data[6:]
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT name FROM images WHERE name LIKE %s ORDER BY name", (f"{prefix}%",))
        rows = cur.fetchall()
        cur.close(); conn.close()

        text = f"📁 {prefix}\n📊 {len(rows)} ta rasm\n\n"
        for r in rows[:30]:
            text += f"• {r[0]}\n"

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👁 Birinchisini ko'r", callback_data=f"img_v:{rows[0][0]}" if rows else "img_panel")],
            [InlineKeyboardButton(text="🗑 Guruhni o'chir", callback_data=f"img_dg:{prefix[:45]}")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")],
        ])
        await call.message.edit_text(text, reply_markup=kb)
        await call.answer()

    elif data.startswith("img_v:"):
        name = data[6:]
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🗑 O'chir", callback_data=f"img_d:{name}")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")],
            ])
            await call.message.answer_photo(row[0], caption=f"🖼 {name}", reply_markup=kb)
        await call.answer()

    elif data.startswith("img_d:"):
        name = data[6:]
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images WHERE name=%s", (name,))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ O'chirildi: {name}", show_alert=True)

    elif data.startswith("img_dg:"):
        prefix = data[7:]
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM images WHERE name LIKE %s", (f"{prefix}%",))
        cnt = cur.fetchone()[0]
        cur.execute("DELETE FROM images WHERE name LIKE %s", (f"{prefix}%",))
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ {cnt} ta rasm o'chirildi!", show_alert=True)
        await show_image_panel(call.message)

    elif data.startswith("img_all:"):
        offset = int(data[8:])
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM images")
        total = cur.fetchone()[0]
        cur.execute("SELECT name FROM images ORDER BY name LIMIT 20 OFFSET %s", (offset,))
        rows = cur.fetchall()
        cur.close(); conn.close()

        text = f"📋 Barcha rasmlar ({total} ta)\n\n"
        for i, (name,) in enumerate(rows):
            text += f"{offset+i+1}. {name}\n"

        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_all:{offset-20}"))
        if offset + 20 < total:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_all:{offset+20}"))

        kb_rows = []
        if nav:
            kb_rows.append(nav)
        kb_rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")])
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
        await call.answer()

    elif data == "img_del_all":
        await call.message.edit_text(
            "⚠️ Barcha rasmlarni o'chirasizmi?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Ha", callback_data="img_del_all_yes"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="img_panel"),
            ]])
        )
        await call.answer()

    elif data == "img_del_all_yes":
        conn = db(); cur = conn.cursor()
        cur.execute("DELETE FROM images")
        cnt = cur.rowcount
        conn.commit(); cur.close(); conn.close()
        await call.answer(f"✅ {cnt} ta rasm o'chirildi!", show_alert=True)
        await show_image_panel(call.message)
