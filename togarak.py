"""
togarak.py — To'garak boshqaruvi
O'qituvchi: yaratish, o'chirish, yoqlama, a'zolar
O'quvchi: qo'shilish, chiqish, ko'rish
"""
import os, psycopg2, re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL","")
def db(): return psycopg2.connect(DATABASE_URL)

# ══ PAROL TEKSHIRISH ══
def check_parol(parol: str) -> bool:
    """4 dan ko'p belgi, harf yoki raqam."""
    return len(parol) >= 4

# ══ O'QITUVCHI FUNKSIYALARI ══

def get_teacher_togaraklar(teacher_id: int) -> list:
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.nomi, t.fan, t.parol, t.max_talaba, t.oylik_sana, t.oylik_summa,
               COUNT(a.id) as azolar_soni
        FROM togaraklar t
        LEFT JOIN togarak_azolar a ON a.togarak_id=t.id AND a.aktiv=TRUE
        WHERE t.teacher_id=%s AND t.aktiv=TRUE
        GROUP BY t.id ORDER BY t.created_at DESC
    """, (teacher_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"nomi":r[1],"fan":r[2],"parol":r[3],
             "max":r[4],"oylik_sana":r[5],"oylik_summa":r[6],"azolar":r[7]} for r in rows]

def create_togarak(teacher_id, nomi, fan, parol, max_t=25, oylik_sana=1, oylik_summa=0) -> int:
    conn = db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO togaraklar(nomi,fan,teacher_id,parol,max_talaba,oylik_sana,oylik_summa)
        VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (nomi,fan,teacher_id,parol,max_t,oylik_sana,oylik_summa))
    tid = cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return tid

def delete_togarak(togarak_id, teacher_id) -> bool:
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE togaraklar SET aktiv=FALSE WHERE id=%s AND teacher_id=%s",
               (togarak_id, teacher_id))
    ok = cur.rowcount > 0; conn.commit(); cur.close(); conn.close()
    return ok

def get_togarak_azolar(togarak_id: int) -> list:
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.full_name, u.class, a.qoshilgan
        FROM togarak_azolar a
        JOIN users u ON u.user_id=a.user_id
        WHERE a.togarak_id=%s AND a.aktiv=TRUE
        ORDER BY u.full_name
    """, (togarak_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"uid":r[0],"ism":r[1],"sinf":r[2],"sana":r[3]} for r in rows]

def remove_azо(togarak_id, user_id, teacher_id) -> bool:
    conn = db(); cur = conn.cursor()
    # Teacher egasi ekanligini tekshirish
    cur.execute("SELECT id FROM togaraklar WHERE id=%s AND teacher_id=%s",(togarak_id,teacher_id))
    if not cur.fetchone():
        cur.close(); conn.close(); return False
    cur.execute("UPDATE togarak_azolar SET aktiv=FALSE WHERE togarak_id=%s AND user_id=%s",
               (togarak_id,user_id))
    ok = cur.rowcount > 0; conn.commit(); cur.close(); conn.close()
    return ok

# ══ O'QUVCHI FUNKSIYALARI ══

def get_student_togaraklar(user_id: int) -> list:
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.nomi, t.fan, u.full_name, t.oylik_sana, t.oylik_summa, a.qoshilgan
        FROM togarak_azolar a
        JOIN togaraklar t ON t.id=a.togarak_id
        JOIN users u ON u.user_id=t.teacher_id
        WHERE a.user_id=%s AND a.aktiv=TRUE AND t.aktiv=TRUE
        ORDER BY a.qoshilgan DESC
    """, (user_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"nomi":r[1],"fan":r[2],"teacher":r[3],
             "oylik_sana":r[4],"oylik_summa":r[5],"qoshilgan":r[6]} for r in rows]

def join_togarak(togarak_id, user_id, parol) -> dict:
    """O'quvchini to'garakka qo'shish."""
    conn = db(); cur = conn.cursor()
    # To'garakni topish
    cur.execute("SELECT parol,max_talaba,nomi FROM togaraklar WHERE id=%s AND aktiv=TRUE",
               (togarak_id,))
    t = cur.fetchone()
    if not t:
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ To'garak topilmadi!"}
    if t[0] != parol:
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ Parol noto'g'ri!"}
    # A'zolar soni tekshirish
    cur.execute("SELECT COUNT(*) FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE",(togarak_id,))
    cnt = cur.fetchone()[0]
    if cnt >= t[1]:
        cur.close(); conn.close()
        return {"ok": False, "msg": f"❌ To'garak to'ldi (max {t[1]} ta)!"}
    # Faqat 1 ta to'garakka ruxsat (admin chiqishi mumkin)
    cur.execute("SELECT COUNT(*) FROM togarak_azolar WHERE user_id=%s AND aktiv=TRUE",(user_id,))
    if cur.fetchone()[0] >= 1:
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ Siz allaqachon bir to'garakka a'zostsiz!"}
    try:
        cur.execute("INSERT INTO togarak_azolar(togarak_id,user_id) VALUES(%s,%s)",
                   (togarak_id,user_id))
        conn.commit()
    except:
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ Xato yuz berdi!"}
    cur.close(); conn.close()
    return {"ok": True, "msg": f"✅ '{t[2]}' to'garakka qo'shildingiz!"}

def leave_togarak(togarak_id, user_id) -> bool:
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE togarak_azolar SET aktiv=FALSE WHERE togarak_id=%s AND user_id=%s",
               (togarak_id,user_id))
    ok = cur.rowcount > 0; conn.commit(); cur.close(); conn.close()
    return ok

# ══ YOQLAMA ══

def save_yoqlama(togarak_id, user_id, holat, izoh="") -> bool:
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO togarak_yoqlama(togarak_id,user_id,holat,izoh,sana)
            VALUES(%s,%s,%s,%s,CURRENT_DATE)
            ON CONFLICT(togarak_id,user_id,sana)
            DO UPDATE SET holat=EXCLUDED.holat,izoh=EXCLUDED.izoh
        """, (togarak_id,user_id,holat,izoh))
        conn.commit(); ok=True
    except Exception as e:
        print(f"save_yoqlama xato: {e}")
        conn.rollback(); ok=False
    cur.close(); conn.close()
    return ok

def get_yoqlama_bugun(togarak_id: int) -> list:
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT a.user_id, u.full_name, u.class,
               COALESCE(y.holat,'kelmadi') as holat
        FROM togarak_azolar a
        JOIN users u ON u.user_id=a.user_id
        LEFT JOIN togarak_yoqlama y ON y.togarak_id=a.togarak_id
            AND y.user_id=a.user_id AND y.sana=CURRENT_DATE
        WHERE a.togarak_id=%s AND a.aktiv=TRUE
        ORDER BY u.full_name
    """, (togarak_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"uid":r[0],"ism":r[1],"sinf":r[2],"holat":r[3]} for r in rows]

def get_yoqlama_statistika(togarak_id: int, oy: int = None) -> list:
    conn = db(); cur = conn.cursor()
    oy_filter = "AND EXTRACT(MONTH FROM y.sana)=%s" if oy else ""
    params = [togarak_id]
    if oy: params.append(oy)
    cur.execute(f"""
        SELECT u.full_name, u.class,
               COUNT(CASE WHEN y.holat='keldi' THEN 1 END) as keldi,
               COUNT(CASE WHEN y.holat='kelmadi' THEN 1 END) as kelmadi,
               COUNT(CASE WHEN y.holat='kech' THEN 1 END) as kech
        FROM togarak_azolar a
        JOIN users u ON u.user_id=a.user_id
        LEFT JOIN togarak_yoqlama y ON y.togarak_id=a.togarak_id
            AND y.user_id=a.user_id {oy_filter}
        WHERE a.togarak_id=%s AND a.aktiv=TRUE
        GROUP BY u.full_name, u.class
        ORDER BY u.full_name
    """, params + [togarak_id])
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"ism":r[0],"sinf":r[1],"keldi":r[2],"kelmadi":r[3],"kech":r[4]} for r in rows]

# ══ KEYBOARD YARATUVCHILAR ══

def togarak_list_kb(togaraklar: list, prefix="tg") -> InlineKeyboardMarkup:
    """To'garaklar ro'yxati — 1 ta to'garak = 1 qator."""
    rows = []
    for t in togaraklar:
        cnt = t.get("azolar",0)
        rows.append([InlineKeyboardButton(
            text=f"📚 {t['nomi']} ({cnt}/{t['max']})",
            callback_data=f"{prefix}_info:{t['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ══ QO'SHILISH SO'ROVI ══

def send_join_request(togarak_id: int, user_id: int) -> dict:
    """O'quvchi so'rov yuboradi."""
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT nomi, teacher_id, max_talaba FROM togaraklar WHERE id=%s AND aktiv=TRUE",(togarak_id,))
    t = cur.fetchone()
    if not t:
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ To'garak topilmadi!"}
    # Allaqachon a'zo
    cur.execute("SELECT id FROM togarak_azolar WHERE togarak_id=%s AND user_id=%s AND aktiv=TRUE",(togarak_id,user_id))
    if cur.fetchone():
        cur.close(); conn.close()
        return {"ok": False, "msg": "❌ Siz allaqachon a'zostsiz!"}
    # Allaqachon so'rov
    cur.execute("SELECT id,status FROM togarak_requests WHERE togarak_id=%s AND user_id=%s",(togarak_id,user_id))
    req = cur.fetchone()
    if req and req[1] == "pending":
        cur.close(); conn.close()
        return {"ok": False, "msg": "⏳ So'rovingiz ko'rib chiqilmoqda!"}
    # Jami a'zolar
    cur.execute("SELECT COUNT(*) FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE",(togarak_id,))
    cnt = cur.fetchone()[0]
    if cnt >= t[2]:
        cur.close(); conn.close()
        return {"ok": False, "msg": f"❌ To'garak to'ldi ({t[2]} ta limit)!"}
    # So'rov yaratish
    try:
        cur.execute("""INSERT INTO togarak_requests(togarak_id,user_id,status)
            VALUES(%s,%s,'pending') ON CONFLICT(togarak_id,user_id)
            DO UPDATE SET status='pending', created_at=NOW()""",
            (togarak_id, user_id))
        conn.commit()
    except Exception as e:
        cur.close(); conn.close()
        return {"ok": False, "msg": f"❌ Xato: {e}"}
    cur.close(); conn.close()
    return {"ok": True, "teacher_id": t[1], "togarak_nomi": t[0]}

def get_pending_requests(teacher_id: int) -> list:
    """O'qituvchining kutayotgan so'rovlari."""
    conn = db(); cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.togarak_id, r.user_id, u.full_name, u.class, t.nomi
        FROM togarak_requests r
        JOIN togaraklar t ON t.id=r.togarak_id
        JOIN users u ON u.user_id=r.user_id
        WHERE t.teacher_id=%s AND r.status='pending'
        ORDER BY r.created_at
    """, (teacher_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"tg_id":r[1],"uid":r[2],"ism":r[3],"sinf":r[4],"tg_nomi":r[5]} for r in rows]

def approve_request(req_id: int, teacher_id: int) -> dict:
    """So'rovni tasdiqlash."""
    conn = db(); cur = conn.cursor()
    cur.execute("""SELECT r.togarak_id, r.user_id FROM togarak_requests r
        JOIN togaraklar t ON t.id=r.togarak_id
        WHERE r.id=%s AND t.teacher_id=%s AND r.status='pending'""",
        (req_id, teacher_id))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        return {"ok": False}
    tg_id, uid = row
    cur.execute("UPDATE togarak_requests SET status='approved' WHERE id=%s",(req_id,))
    try:
        cur.execute("INSERT INTO togarak_azolar(togarak_id,user_id) VALUES(%s,%s)",(tg_id,uid))
    except: pass
    conn.commit(); cur.close(); conn.close()
    return {"ok": True, "togarak_id": tg_id, "user_id": uid}

def reject_request(req_id: int, teacher_id: int) -> bool:
    conn = db(); cur = conn.cursor()
    cur.execute("""UPDATE togarak_requests r SET status='rejected'
        FROM togaraklar t WHERE r.togarak_id=t.id
        AND r.id=%s AND t.teacher_id=%s""", (req_id, teacher_id))
    ok = cur.rowcount > 0; conn.commit(); cur.close(); conn.close()
    return ok

# ══ GURUH XABARLARI ══

def send_group_message(togarak_id: int, sender_id: int, matn: str, receiver_id=None) -> bool:
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO togarak_messages(togarak_id,sender_id,receiver_id,matn)
            VALUES(%s,%s,%s,%s)""", (togarak_id, sender_id, receiver_id, matn))
        conn.commit(); ok=True
    except: ok=False
    cur.close(); conn.close()
    return ok

def get_group_members(togarak_id: int) -> list:
    """Guruh a'zolarini olish (xabar yuborish uchun)."""
    conn = db(); cur = conn.cursor()
    cur.execute("""SELECT a.user_id FROM togarak_azolar a
        WHERE a.togarak_id=%s AND a.aktiv=TRUE""", (togarak_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return [r[0] for r in rows]


# ══ CHIQISH SO'ROVI ══
def send_leave_request(togarak_id: int, user_id: int) -> dict:
    conn = db(); cur = conn.cursor()
    cur.execute("SELECT t.teacher_id, t.nomi, u.full_name FROM togaraklar t, users u WHERE t.id=%s AND u.user_id=%s",(togarak_id,user_id))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row: return {"ok":False,"msg":"❌ Topilmadi"}
    return {"ok":True,"teacher_id":row[0],"tg_nomi":row[1],"user_name":row[2]}

def confirm_leave(togarak_id: int, user_id: int) -> bool:
    conn = db(); cur = conn.cursor()
    cur.execute("UPDATE togarak_azolar SET aktiv=FALSE WHERE togarak_id=%s AND user_id=%s",(togarak_id,user_id))
    ok=cur.rowcount>0; conn.commit(); cur.close(); conn.close()
    return ok

# ══ BAHOLASH ══
def save_baho(togarak_id, user_id, baho, izoh="", teacher_id=None):
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO togarak_baholar(togarak_id,user_id,baho,izoh,teacher_id)
            VALUES(%s,%s,%s,%s,%s)""", (togarak_id,user_id,baho,izoh,teacher_id))
        conn.commit()
    except: conn.rollback()
    cur.close(); conn.close()

def get_baholar(togarak_id, user_id=None):
    conn = db(); cur = conn.cursor()
    if user_id:
        cur.execute("""SELECT b.baho, b.izoh, b.created_at, u.full_name
            FROM togarak_baholar b JOIN users u ON u.user_id=b.teacher_id
            WHERE b.togarak_id=%s AND b.user_id=%s ORDER BY b.created_at DESC LIMIT 10""",
            (togarak_id,user_id))
    else:
        cur.execute("""SELECT u.full_name, AVG(b.baho)::numeric(4,1), COUNT(b.id)
            FROM togarak_baholar b JOIN users u ON u.user_id=b.user_id
            WHERE b.togarak_id=%s GROUP BY u.full_name ORDER BY u.full_name""", (togarak_id,))
    rows=cur.fetchall(); cur.close(); conn.close()
    return rows

# ══ TO'LOV ══
def save_tolov(togarak_id, user_id, summa, oy, teacher_id):
    conn = db(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO togarak_tolovlar(togarak_id,user_id,summa,oy,teacher_id)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(togarak_id,user_id,oy)
            DO UPDATE SET summa=EXCLUDED.summa""",
            (togarak_id,user_id,summa,oy,teacher_id))
        conn.commit()
    except: conn.rollback()
    cur.close(); conn.close()

def get_tolov_status(togarak_id, user_id=None):
    conn = db(); cur = conn.cursor()
    if user_id:
        cur.execute("""SELECT oy, summa, created_at FROM togarak_tolovlar
            WHERE togarak_id=%s AND user_id=%s ORDER BY oy DESC LIMIT 6""",
            (togarak_id,user_id))
    else:
        from datetime import date
        cur_month = date.today().strftime("%Y-%m")
        cur.execute("""SELECT u.full_name, u.class,
            CASE WHEN t.id IS NOT NULL THEN '✅' ELSE '❌' END as holat
            FROM togarak_azolar a JOIN users u ON u.user_id=a.user_id
            LEFT JOIN togarak_tolovlar t ON t.togarak_id=a.togarak_id
                AND t.user_id=a.user_id AND t.oy=%s
            WHERE a.togarak_id=%s AND a.aktiv=TRUE ORDER BY u.full_name""",
            (cur_month, togarak_id))
    rows=cur.fetchall(); cur.close(); conn.close()
    return rows

# ══ GURUH XABARLARI ══
def get_guruh_xabarlar(togarak_id: int, limit: int = 20) -> list:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT m.matn, u.full_name, u.role, m.created_at
            FROM togarak_messages m
            JOIN users u ON u.user_id=m.sender_id
            WHERE m.togarak_id=%s AND m.receiver_id IS NULL
            ORDER BY m.created_at DESC LIMIT %s
        """, (togarak_id, limit))
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"matn":r[0],"ism":r[1],"rol":r[2],"vaqt":r[3]} for r in reversed(rows)]
    except: return []

def get_personal_messages(togarak_id, user1, user2, limit=20):
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT m.matn, m.sender_id, u.full_name, m.created_at
            FROM togarak_messages m
            JOIN users u ON u.user_id=m.sender_id
            WHERE m.togarak_id=%s AND (
                (m.sender_id=%s AND m.receiver_id=%s) OR
                (m.sender_id=%s AND m.receiver_id=%s)
            )
            ORDER BY m.created_at DESC LIMIT %s
        """, (togarak_id, user1, user2, user2, user1, limit))
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"matn":r[0],"sender":r[1],"ism":r[2],"vaqt":r[3]} for r in reversed(rows)]
    except: return []

# ══ DARS REJASI ══
def get_reja(togarak_id: int) -> list:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""
            SELECT r.id, r.topic_code, r.tartib, r.tur, r.kun, r.izoh, r.completed,
                   r.dars_kuni, r.dars_vaqt
            FROM togarak_reja r
            WHERE r.togarak_id=%s ORDER BY r.tartib
        """, (togarak_id,))
        rows = cur.fetchall(); cur.close(); conn.close()
        return [{"id":r[0],"code":r[1],"tartib":r[2],"tur":r[3],
                 "kun":r[4],"izoh":r[5],"completed":r[6],
                 "dars_kuni":r[7],"dars_vaqt":r[8]} for r in rows]
    except: return []

def add_to_reja(togarak_id, topic_code, tur="dars", kun=None, izoh="") -> int:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(tartib),0)+1 FROM togarak_reja WHERE togarak_id=%s",(togarak_id,))
        tartib = cur.fetchone()[0]
        cur.execute("""INSERT INTO togarak_reja(togarak_id,topic_code,tartib,tur,kun,izoh)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING id""",
            (togarak_id,topic_code,tartib,tur,kun,izoh))
        rid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
        return rid
    except: return 0

def mark_dars_done(togarak_id, topic_code, teacher_id) -> bool:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("""INSERT INTO togarak_dars_log(togarak_id,topic_code,teacher_id)
            VALUES(%s,%s,%s) ON CONFLICT DO NOTHING""",(togarak_id,topic_code,teacher_id))
        cur.execute("UPDATE togarak_reja SET completed=TRUE WHERE togarak_id=%s AND topic_code=%s",
                   (togarak_id,topic_code))
        conn.commit(); cur.close(); conn.close()
        return True
    except: return False

def get_togarak_progress(togarak_id: int) -> dict:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM togarak_reja WHERE togarak_id=%s",(togarak_id,))
        total=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM togarak_reja WHERE togarak_id=%s AND completed=TRUE",(togarak_id,))
        done=cur.fetchone()[0]
        cur.execute("SELECT topic_code FROM togarak_reja WHERE togarak_id=%s AND completed=FALSE ORDER BY tartib LIMIT 1",(togarak_id,))
        next_r=cur.fetchone(); cur.close(); conn.close()
        pct=round(done*100/total) if total else 0
        return {"total":total,"done":done,"pct":pct,"next":next_r[0] if next_r else None}
    except: return {"total":0,"done":0,"pct":0,"next":None}

def get_student_progress(togarak_id, user_id) -> dict:
    try:
        conn = db(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s AND holat='keldi'",(togarak_id,user_id))
        keldi=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM togarak_yoqlama WHERE togarak_id=%s AND user_id=%s",(togarak_id,user_id))
        jami=cur.fetchone()[0]
        cur.execute("SELECT AVG(baho) FROM togarak_baholar WHERE togarak_id=%s AND user_id=%s",(togarak_id,user_id))
        avg_b=(cur.fetchone() or [None])[0]
        cur.close(); conn.close()
        pct=round(keldi*100/jami) if jami else 0
        return {"yoqlama_pct":pct,"avg_baho":round(float(avg_b),1) if avg_b else 0,"keldi":keldi,"jami":jami}
    except: return {"yoqlama_pct":0,"avg_baho":0,"keldi":0,"jami":0}
