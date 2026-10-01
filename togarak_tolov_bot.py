"""REV96: botda to'garak/repetitor guruhining oylik to'lovlari — saytdagi «Davomat va to'lovlar» bilan bir xil jadval.

O'qituvchi: 💰 To'lovlar → oy bo'yicha ro'yxat (✅ to'lagan · 🟠 qisman · ❌ to'lamagan), bir bosishda «to'ladi»
deb belgilaydi yoki bekor qiladi. Kutilgan / yig'ilgan / qarz summasi avtomatik hisoblanadi.
"""
from datetime import date
from html import escape

OYLAR = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]


def month_key(offset=0, today=None):
    d = today or date.today()
    m, y = d.month + int(offset), d.year
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return f"{y}-{m:02d}"


def month_title(key):
    y, m = key.split("-")
    return f"{OYLAR[int(m) - 1]} {y}"


def som(n):
    return f"{int(n or 0):,}".replace(",", " ") + " so'm"


def build_view(nomi, price, rows, key):
    """rows: [(user_id, ism, summa|None)] → (matn, [(tugma_matni, callback_turi, user_id)])."""
    price = int(price or 0)
    lines = [f"💰 <b>{escape(str(nomi or ''))}</b> — {month_title(key)}", "─────────────"]
    buttons = []
    paid_total = debt = full = part = 0
    for uid, ism, summa in rows:
        ism = escape((ism or "O'quvchi").strip())
        if summa is None:
            lines.append(f"❌ {ism}")
            debt += price
            buttons.append((f"✅ {ism[:22]} to'ladi", "ok", uid))
        elif int(summa) >= price:
            full += 1
            paid_total += int(summa)
            lines.append(f"✅ {ism} — {som(summa)}")
            buttons.append((f"↩️ {ism[:22]} (bekor)", "undo", uid))
        else:
            part += 1
            paid_total += int(summa)
            debt += price - int(summa)
            lines.append(f"🟠 {ism} — {som(summa)} (qisman)")
            buttons.append((f"✅ {ism[:22]} to'liq to'ladi", "ok", uid))
    if not rows:
        lines.append("Guruhda hali o'quvchi yo'q.")
    lines += ["─────────────",
              f"👥 To'laganlar: {full}/{len(rows)}" + (f" (+{part} qisman)" if part else ""),
              f"📌 Kutilgan: {som(price * len(rows))}",
              f"💵 Yig'ildi: {som(paid_total)}",
              f"❗ Qarz: {som(debt)}"]
    if not price:
        lines.append("\nℹ️ Oylik summa kiritilmagan: ⚙️ Sozlamalar → 💰 Oylik summa.")
    return "\n".join(lines), buttons


def load_rows(cur, togarak_id, key):
    cur.execute("""SELECT a.user_id, u.full_name, t.summa
                   FROM togarak_azolar a JOIN users u ON u.user_id=a.user_id
                   LEFT JOIN togarak_tolovlar t ON t.togarak_id=a.togarak_id AND t.user_id=a.user_id AND t.oy=%s
                   WHERE a.togarak_id=%s AND a.aktiv=TRUE ORDER BY u.full_name""", (key, togarak_id))
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


async def handle(call, user_id, get_conn, admins, markup_cls, button_cls):
    """cb_togarak ichidan chaqiriladi. True — callback shu yerda ishlandi."""
    d = call.data or ""
    if not (d.startswith("tg_tolovlar:") or d.startswith("tg_tl_ok:") or d.startswith("tg_tl_undo:")):
        return False
    parts = d.split(":")
    tgid = int(parts[1])
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT nomi, COALESCE(oylik_summa,0), teacher_id FROM togaraklar WHERE id=%s", (tgid,))
        g = cur.fetchone()
        if not g or (int(g[2] or 0) != int(user_id) and user_id not in admins):
            await call.answer("Ruxsat yo'q", show_alert=True)
            return True
        if d.startswith("tg_tolovlar:"):
            off = int(parts[2]) if len(parts) > 2 else 0
        else:
            uid, off = int(parts[2]), int(parts[3]) if len(parts) > 3 else 0
            key = month_key(off)
            if d.startswith("tg_tl_ok:"):
                cur.execute("""INSERT INTO togarak_tolovlar(togarak_id,user_id,summa,oy,teacher_id) VALUES(%s,%s,%s,%s,%s)
                               ON CONFLICT(togarak_id,user_id,oy) DO UPDATE SET summa=EXCLUDED.summa""",
                            (tgid, uid, int(g[1] or 0), key, user_id))
            else:
                cur.execute("DELETE FROM togarak_tolovlar WHERE togarak_id=%s AND user_id=%s AND oy=%s", (tgid, uid, key))
            conn.commit()
        key = month_key(off)
        text, btns = build_view(g[0], g[1], load_rows(cur, tgid, key), key)
    finally:
        cur.close()
        conn.close()
    await call.answer()
    kb = [[button_cls(text=t, callback_data=f"tg_tl_{kind}:{tgid}:{uid}:{off}")] for t, kind, uid in btns[:50]]
    kb.append([button_cls(text="◀️", callback_data=f"tg_tolovlar:{tgid}:{off - 1}"),
               button_cls(text=month_title(month_key(off)), callback_data=f"tg_tolovlar:{tgid}:{off}"),
               button_cls(text="▶️", callback_data=f"tg_tolovlar:{tgid}:{off + 1}")])
    kb.append([button_cls(text="⬅️ Guruhga", callback_data=f"tg_info:{tgid}")])
    markup = markup_cls(inline_keyboard=kb)
    try:
        await call.message.edit_text(text[:3900], parse_mode="HTML", reply_markup=markup)
    except Exception:
        await call.message.answer(text[:3900], parse_mode="HTML", reply_markup=markup)
    return True
