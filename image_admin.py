"""
image_admin.py — Rasmlar boshqaruvi paneli
"""
import psycopg2
import os
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    BufferedInputFile
)

DATABASE_URL = os.getenv("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)


async def show_image_panel(message):
    """Rasm boshqaruvi bosh sahifasi"""
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    total = cur.fetchone()[0]
    
    # Guruhlash — topic_code bo'yicha (nomdan olish)
    cur.execute("""
        SELECT 
            SUBSTRING(name FROM '^(.+)-[0-9]+$') as prefix,
            COUNT(*) as cnt
        FROM images
        WHERE name ~ '^.+-[0-9]+$'
        GROUP BY prefix
        ORDER BY prefix
        LIMIT 20
    """)
    groups = cur.fetchall()
    
    # Duplikat nomlar
    cur.execute("""
        SELECT name, COUNT(*) as cnt
        FROM images
        GROUP BY name
        HAVING COUNT(*) > 1
    """)
    dups = cur.fetchall()
    cur.close(); conn.close()
    
    text = (
        f"🖼 Rasmlar boshqaruvi\n\n"
        f"📊 Jami rasm: {total}\n"
        f"📁 Guruhlar: {len(groups)}\n"
        f"⚠️ Takroriy: {len(dups)}\n\n"
        f"Quyidagi guruhlar topildi:"
    )
    
    kb_rows = []
    for prefix, cnt in groups[:15]:
        short = prefix[-20:] if len(prefix) > 20 else prefix
        kb_rows.append([InlineKeyboardButton(
            text=f"📁 {short} ({cnt})",
            callback_data=f"img_group:{prefix[:50]}"
        )])
    
    kb_rows.append([
        InlineKeyboardButton(text="🔍 Barcha rasmlar", callback_data="img_all:0"),
        InlineKeyboardButton(text="⚠️ Takroriylar", callback_data="img_dups"),
    ])
    kb_rows.append([
        InlineKeyboardButton(text="🗑 Barchasini tozalash", callback_data="img_clear_all"),
    ])
    
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


async def show_image_group(call, prefix):
    """Guruh ichidagi rasmlar"""
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT name, file_id FROM images
        WHERE name LIKE %s
        ORDER BY name
    """, (f"{prefix}%",))
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    if not rows:
        await call.answer("Rasmlar topilmadi!", show_alert=True)
        return
    
    text = f"📁 Guruh: {prefix}\n📊 Rasmlar: {len(rows)}\n\n"
    for name, _ in rows[:20]:
        text += f"• {name}\n"
    if len(rows) > 20:
        text += f"... va yana {len(rows)-20} ta\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Ko'rish (1-ta)", callback_data=f"img_view:{rows[0][0]}"),
            InlineKeyboardButton(text="🗑 Guruhni o'chirish", callback_data=f"img_del_group:{prefix[:50]}"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")]
    ])
    
    await call.message.edit_text(text, reply_markup=kb)


async def show_all_images(call, offset=0):
    """Barcha rasmlar ro'yxati"""
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images")
    total = cur.fetchone()[0]
    cur.execute("SELECT name, file_id FROM images ORDER BY name LIMIT 20 OFFSET %s", (offset,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    text = f"🖼 Barcha rasmlar ({total} ta)\n\n"
    for i, (name, _) in enumerate(rows):
        text += f"{offset+i+1}. {name}\n"
    
    kb_rows = []
    # Har bir rasm uchun ko'rish va o'chirish
    for name, _ in rows[:5]:
        short = name[-25:] if len(name) > 25 else name
        kb_rows.append([
            InlineKeyboardButton(text=f"👁 {short}", callback_data=f"img_view:{name}"),
            InlineKeyboardButton(text="🗑", callback_data=f"img_del:{name}"),
        ])
    
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"img_all:{offset-20}"))
    if offset + 20 < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"img_all:{offset+20}"))
    if nav:
        kb_rows.append(nav)
    kb_rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")])
    
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


async def view_image(call, name):
    """Rasmni ko'rsatish"""
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT file_id FROM images WHERE name=%s", (name,))
    row = cur.fetchone()
    cur.close(); conn.close()
    
    if not row:
        await call.answer("Rasm topilmadi!", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 O'chirish: {name[-20:]}", callback_data=f"img_del:{name}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_all:0")]
    ])
    
    await call.message.answer_photo(
        row[0],
        caption=f"🖼 {name}",
        reply_markup=kb
    )
    await call.answer()


async def delete_image(call, name):
    """Bitta rasmni o'chirish"""
    conn = db(); cur = conn.cursor()
    cur.execute("DELETE FROM images WHERE name=%s", (name,))
    conn.commit()
    cur.close(); conn.close()
    
    await call.answer(f"✅ O'chirildi: {name}", show_alert=True)


async def delete_group(call, prefix):
    """Guruhni o'chirish"""
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM images WHERE name LIKE %s", (f"{prefix}%",))
    cnt = cur.fetchone()[0]
    cur.execute("DELETE FROM images WHERE name LIKE %s", (f"{prefix}%",))
    conn.commit()
    cur.close(); conn.close()
    
    await call.answer(f"✅ {cnt} ta rasm o'chirildi!", show_alert=True)
    await show_image_panel(call.message)


async def show_duplicates(call):
    """Takroriy rasmlar"""
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT name, COUNT(*) as cnt
        FROM images
        GROUP BY name
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
    """)
    dups = cur.fetchall()
    cur.close(); conn.close()
    
    if not dups:
        await call.answer("Takroriy rasmlar yo'q!", show_alert=True)
        return
    
    text = f"⚠️ Takroriy rasmlar: {len(dups)} ta\n\n"
    for name, cnt in dups[:20]:
        text += f"• {name} ({cnt} marta)\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Hammasini tozalash", callback_data="img_del_dups")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="img_panel")]
    ])
    await call.message.edit_text(text, reply_markup=kb)


async def delete_duplicates(call):
    """Takroriylarni o'chirish"""
    conn = db(); cur = conn.cursor()
    cur.execute("""
        DELETE FROM images
        WHERE ctid NOT IN (
            SELECT MIN(ctid)
            FROM images
            GROUP BY name
        )
    """)
    cnt = cur.rowcount
    conn.commit()
    cur.close(); conn.close()
    
    await call.answer(f"✅ {cnt} ta takroriy o'chirildi!", show_alert=True)
    await show_image_panel(call.message)
