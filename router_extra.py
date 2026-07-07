"""
router_extra.py — QR, Badge, Dashboard, Jadval, Ommaviy xabar
Talim.py katta o'smaydi — alohida fayl
"""
import os, psycopg2, io, asyncio
from aiogram import Router
from aiogram.types import CallbackQuery, Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from storage import user_state, admin_state, temp_user

DATABASE_URL = os.getenv("DATABASE_URL","")
def db(): return psycopg2.connect(DATABASE_URL)

router = Router()

# ── QR KOD ──
def gen_qr(togarak_id: int, parol: str) -> bytes:
    try:
        import segno
        qr = segno.make(f"SamTM|{togarak_id}|{parol}")
        buf = io.BytesIO()
        qr.save(buf, kind="png", scale=8, border=2)
        buf.seek(0)
        return buf.read()
    except ImportError:
        # segno yo'q bo'lsa matn ko'rinishida
        return None

@router.callback_query(lambda c: c.data and c.data.startswith("tg_qr:"))
async def tg_qr_handler(call: CallbackQuery):
    tgid = int(call.data[6:])
    await call.answer()
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT nomi,parol FROM togaraklar WHERE id=%s",(tgid,))
    t = cur.fetchone(); cur.close(); conn.close()
    if not t: await call.message.answer("❌ Topilmadi"); return
    img = gen_qr(tgid, t[1])
    txt = f"📱 QR kod — {t[0]}\n\nID: {tgid}\nParol: {t[1]}\n\nO'quvchi skaner qilsa avtomatik qo'shiladi!"
    if img:
        await call.message.answer_photo(BufferedInputFile(img,"qr.png"), caption=txt)
    else:
        await call.message.answer(txt)

# ── BADGE TIZIMI ──
BADGES = {
    "dav_90": ("🏅 Doimiy", "90%+ davomat"),
    "dav_100": ("🥇 Kamchiliksiz", "100% davomat"),
    "baho_5": ("⭐ A'lochi", "5.0 o'rtacha baho"),
    "baho_4": ("✨ Yaxshi o'quvchi", "4.0+ baho"),
    "hw_10": ("📝 Mehnatsevar", "10+ vazifa topshirdi"),
    "top1": ("🏆 Birinchi", "To'garakda 1-o'rin"),
}

def check_badges(togarak_id: int, user_id: int) -> list:
    """O'quvchining badge larini aniqlash."""
    from togarak import get_student_progress
    from features import get_reyting
    sp = get_student_progress(togarak_id, user_id)
    badges = []
    if sp["yoqlama_pct"] == 100: badges.append("dav_100")
    elif sp["yoqlama_pct"] >= 90: badges.append("dav_90")
    if sp["avg_baho"] >= 5.0: badges.append("baho_5")
    elif sp["avg_baho"] >= 4.0: badges.append("baho_4")
    reyting = get_reyting(togarak_id)
    if reyting and reyting[0]["uid"] == user_id: badges.append("top1")
    return [(b, BADGES[b]) for b in badges if b in BADGES]

@router.callback_query(lambda c: c.data and c.data.startswith("stg_badges:"))
async def stg_badges_handler(call: CallbackQuery):
    tgid = int(call.data[11:])
    user_id = call.from_user.id
    await call.answer()
    badges = check_badges(tgid, user_id)
    if not badges:
        await call.message.answer("Hali badge yo'q. Faol bo'ling!"); return
    txt = "🏅 Sizning yutuqlaringiz:\n\n"
    for code, (icon_name, desc) in badges:
        txt += f"{icon_name} — {desc}\n"
    await call.message.answer(txt)

# ── HAFTALIK JADVAL ──
KUNLAR = ["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"]

@router.callback_query(lambda c: c.data and c.data.startswith("tg_jadval:"))
async def tg_jadval_handler(call: CallbackQuery):
    tgid = int(call.data[10:])
    await call.answer()
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("SELECT kun_nomi,boshlanish,tugash,xona FROM togarak_jadval WHERE togarak_id=%s ORDER BY kun_id,boshlanish",(tgid,))
        rows = cur.fetchall()
    except: rows = []
    cur.close(); conn.close()
    if not rows:
        await call.message.answer(
            "📅 Jadval qo'shilmagan.\n\nJadval qo'shish uchun:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Dars qo'shish",callback_data=f"tg_jadval_add:{tgid}")
            ]])
        ); return
    txt = "📅 Haftalik jadval:\n\n"
    for r in rows:
        txt += f"📌 {r[0]}: {r[1]}-{r[2]}"
        if r[3]: txt += f" ({r[3]})"
        txt += "\n"
    await call.message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish",callback_data=f"tg_jadval_add:{tgid}")]
    ]))

# ── OMMAVIY XABAR ──
@router.callback_query(lambda c: c.data and c.data.startswith("tg_broadcast:"))
async def tg_broadcast_handler(call: CallbackQuery):
    tgid = int(call.data[13:])
    user_id = call.from_user.id
    await call.answer()
    admin_state[user_id] = f"tg_broadcast:{tgid}"
    await call.message.answer(
        "📢 Barcha a'zolarga xabar yozing:\n(Matn, rasm yoki fayl yuborishingiz mumkin)"
    )

# ── ADMIN DASHBOARD ──
@router.message(lambda m: m.text == "📊 Dashboard")
async def admin_dashboard(message: Message):
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM togaraklar WHERE aktiv=TRUE")
    total_tg = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM togarak_azolar WHERE aktiv=TRUE")
    total_az = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM homework")
    total_hw = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE created_at >= NOW()-INTERVAL '7 days'")
    new_week = cur.fetchone()[0]
    cur.close(); conn.close()
    txt = (
        f"📊 Admin Dashboard\n{'─'*20}\n\n"
        f"👥 Jami foydalanuvchilar: {total_users:,}\n"
        f"📈 Yangi (hafta): +{new_week}\n\n"
        f"📚 Aktiv to'garaklar: {total_tg}\n"
        f"👨‍🎓 Jami a'zolar: {total_az}\n"
        f"📝 Uyga vazifalar: {total_hw}\n"
    )
    await message.answer(txt)


# ── TO'LOV ESLATMA SCHEDULER ──
async def tolov_eslatma_task(bot):
    """Har kuni 09:00 da to'lov muddati kelganlarni eslatadi."""
    while True:
        from datetime import datetime, date
        now = datetime.now()
        if now.hour == 9 and now.minute == 0:
            try:
                conn = db(); cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT a.user_id, t.nomi, t.oylik_summa, t.oylik_sana
                    FROM togarak_azolar a
                    JOIN togaraklar t ON t.id=a.togarak_id
                    WHERE a.aktiv=TRUE AND t.aktiv=TRUE
                    AND t.oylik_summa > 0
                    AND EXTRACT(DAY FROM CURRENT_DATE) = t.oylik_sana
                """)
                rows = cur.fetchall()
                cur.close(); conn.close()
                for r in rows:
                    try:
                        await bot.send_message(r[0],
                            f"💳 To'lov eslatmasi!\n📚 {r[1]}\n"
                            f"💰 {r[2]:,} so'm\n📅 Bugun to'lov kuni!")
                    except: pass
            except Exception as e:
                print(f"tolov_eslatma: {e}")
        await asyncio.sleep(60)
