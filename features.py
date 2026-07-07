"""
features.py — Qo'shimcha funksiyalar
- Uyga vazifa
- Reyting
- Hisobot
- Eslatmalar
"""
import os, psycopg2
from datetime import date, datetime, timedelta

DATABASE_URL = os.getenv("DATABASE_URL","")
def db(): return psycopg2.connect(DATABASE_URL)

# ══ UYGA VAZIFA ══
def add_homework(togarak_id, teacher_id, mavzu, topshiriq, deadline=None):
    conn=db();cur=conn.cursor()
    cur.execute("""INSERT INTO homework(togarak_id,teacher_id,mavzu,topshiriq,deadline)
        VALUES(%s,%s,%s,%s,%s) RETURNING id""",
        (togarak_id,teacher_id,mavzu,topshiriq,deadline))
    hid=cur.fetchone()[0]; conn.commit(); cur.close(); conn.close()
    return hid

def get_homeworks(togarak_id, aktiv_only=True):
    conn=db();cur=conn.cursor()
    q = "AND deadline >= CURRENT_DATE" if aktiv_only else ""
    cur.execute(f"""SELECT h.id,h.mavzu,h.topshiriq,h.deadline,
        COUNT(s.id) as topshirildi
        FROM homework h LEFT JOIN homework_submit s ON s.hw_id=h.id
        WHERE h.togarak_id=%s {q} GROUP BY h.id ORDER BY h.deadline""",
        (togarak_id,))
    rows=cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"mavzu":r[1],"topshiriq":r[2],
             "deadline":r[3],"topshirildi":r[4]} for r in rows]

def submit_homework(hw_id, user_id, javob, fayl_id=None):
    conn=db();cur=conn.cursor()
    try:
        cur.execute("""INSERT INTO homework_submit(hw_id,user_id,javob,fayl_id)
            VALUES(%s,%s,%s,%s) ON CONFLICT(hw_id,user_id)
            DO UPDATE SET javob=EXCLUDED.javob,submitted_at=NOW()""",
            (hw_id,user_id,javob,fayl_id))
        conn.commit(); ok=True
    except: ok=False
    cur.close(); conn.close()
    return ok

def get_hw_submits(hw_id):
    conn=db();cur=conn.cursor()
    cur.execute("""SELECT s.id,u.full_name,u.class,s.javob,s.baho,s.submitted_at
        FROM homework_submit s JOIN users u ON u.user_id=s.user_id
        WHERE s.hw_id=%s ORDER BY s.submitted_at""", (hw_id,))
    rows=cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"ism":r[1],"sinf":r[2],"javob":r[3],
             "baho":r[4],"vaqt":r[5]} for r in rows]

def get_student_homeworks(togarak_id, user_id):
    conn=db();cur=conn.cursor()
    cur.execute("""SELECT h.id,h.mavzu,h.topshiriq,h.deadline,
        COALESCE(s.javob,'') as javob, s.baho
        FROM homework h LEFT JOIN homework_submit s
            ON s.hw_id=h.id AND s.user_id=%s
        WHERE h.togarak_id=%s AND h.deadline >= CURRENT_DATE
        ORDER BY h.deadline""", (user_id,togarak_id))
    rows=cur.fetchall(); cur.close(); conn.close()
    return [{"id":r[0],"mavzu":r[1],"topshiriq":r[2],
             "deadline":r[3],"javob":r[4],"baho":r[5]} for r in rows]

# ══ REYTING ══
def get_reyting(togarak_id, limit=10):
    conn=db();cur=conn.cursor()
    cur.execute("""
        SELECT u.user_id, u.full_name, u.class,
            COALESCE(AVG(b.baho),0)::numeric(4,1) as avg_b,
            COUNT(CASE WHEN y.holat='keldi' THEN 1 END)*100/NULLIF(COUNT(y.id),0) as davomat,
            COUNT(CASE WHEN s.baho IS NOT NULL THEN 1 END) as hw_done
        FROM togarak_azolar a
        JOIN users u ON u.user_id=a.user_id
        LEFT JOIN togarak_baholar b ON b.togarak_id=a.togarak_id AND b.user_id=a.user_id
        LEFT JOIN togarak_yoqlama y ON y.togarak_id=a.togarak_id AND y.user_id=a.user_id
        LEFT JOIN homework_submit s ON s.user_id=a.user_id
        WHERE a.togarak_id=%s AND a.aktiv=TRUE
        GROUP BY u.user_id, u.full_name, u.class
        ORDER BY avg_b DESC, davomat DESC
        LIMIT %s
    """, (togarak_id, limit))
    rows=cur.fetchall(); cur.close(); conn.close()
    return [{"uid":r[0],"ism":r[1],"sinf":r[2],
             "baho":float(r[3]),"davomat":r[4] or 0,"hw":r[5]} for r in rows]

# ══ HAFTALIK HISOBOT ══
def get_weekly_report(togarak_id, child_id):
    week_ago = date.today() - timedelta(days=7)
    conn=db();cur=conn.cursor()
    # Yoqlama
    cur.execute("""SELECT holat, COUNT(*) FROM togarak_yoqlama
        WHERE togarak_id=%s AND user_id=%s AND sana >= %s
        GROUP BY holat""", (togarak_id,child_id,week_ago))
    yoqlama={r[0]:r[1] for r in cur.fetchall()}
    # Baholar
    cur.execute("""SELECT AVG(baho)::numeric(4,1) FROM togarak_baholar
        WHERE togarak_id=%s AND user_id=%s AND created_at >= %s""",
        (togarak_id,child_id,week_ago))
    avg_b=(cur.fetchone() or [None])[0]
    # Uyga vazifa
    cur.execute("""SELECT COUNT(*) FROM homework_submit s
        JOIN homework h ON h.id=s.hw_id
        WHERE h.togarak_id=%s AND s.user_id=%s AND s.submitted_at >= %s""",
        (togarak_id,child_id,week_ago))
    hw_done=(cur.fetchone() or [0])[0]
    cur.close(); conn.close()
    return {
        "keldi": yoqlama.get("keldi",0),
        "kelmadi": yoqlama.get("kelmadi",0),
        "avg_baho": float(avg_b) if avg_b else 0,
        "hw_done": hw_done
    }

# ══ ESLATMA YUBORISH ══
async def send_notification(bot, user_id, matn):
    try:
        await bot.send_message(user_id, f"🔔 {matn}")
    except: pass

# ══ EXCEL HISOBOT ══
def generate_excel_report(togarak_id) -> bytes:
    import openpyxl, io
    from togarak import get_togarak_azolar, get_yoqlama_statistika, get_baholar
    wb = openpyxl.Workbook()
    # Yoqlama
    ws1 = wb.active; ws1.title = "Yoqlama"
    ws1.append(["Ism","Sinf","Keldi","Kelmadi","Kech","Davomat %"])
    for s in get_yoqlama_statistika(togarak_id):
        total=s["keldi"]+s["kelmadi"]+s["kech"]
        pct=round(s["keldi"]*100/total) if total else 0
        ws1.append([s["ism"],s["sinf"],s["keldi"],s["kelmadi"],s["kech"],pct])
    # Reyting
    ws2 = wb.create_sheet("Reyting")
    ws2.append(["#","Ism","Sinf","O'rt.baho","Davomat %"])
    for i,r in enumerate(get_reyting(togarak_id),1):
        ws2.append([i,r["ism"],r["sinf"],r["baho"],r["davomat"]])
    buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.read()
