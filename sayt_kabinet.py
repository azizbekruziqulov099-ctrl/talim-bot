"""Botdagi ixcham «Kabinetim»: Telegram'i saytga ulangan foydalanuvchi uchun.

Qisqa profil (ism, rol, sinf/kurs, KB raqam), test natijalari (nechta mavzu, o'rtacha foiz,
oxirgi natijalar) va saytni Telegram ichida ilova kabi ochadigan tugmalar:
«📝 Test ishlash», «📘 Mavzu o'rganish». Tugmalardagi bir martalik chipta bilan sayt
kod so'ramasdan ochiladi (backend: /auth/telegram/ticket).

Bot va backend bitta Postgres bazasidan foydalanadi; bu modul faqat o'qiydi.
"""
import html
from urllib.parse import urlencode

ROLE_NAMES = {"oquvchi": "O‘quvchi", "talaba": "Talaba", "oqituvchi": "O‘qituvchi", "ota-ona": "Ota-ona",
              "mustaqil": "Mustaqil o‘rganuvchi", "kabutar": "Rol tanlanmagan"}


def _role(user):
    learning = user.get("kabutar_learning_profile") or {}
    if isinstance(learning, dict) and learning.get("role") == "talaba":
        return "talaba"
    if "kurs" in str(user.get("class") or "").lower():
        return "talaba"
    return str(user.get("role") or "")


def fetch_summary(database_url, telegram_id, limit=5):
    """Telegram ID → {user_id, name, role, class, kb, tests:{count, average, attempts, last:[...]}} yoki None."""
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(database_url, connect_timeout=5)
    try:
        conn.autocommit = True
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""SELECT i.user_id, to_jsonb(u) AS u FROM kabutar_telegram_identity i
                       JOIN users u ON u.user_id=i.user_id WHERE i.telegram_id=%s""", (int(telegram_id),))
        row = cur.fetchone()
        if not row:
            return None
        user = row["u"] or {}
        uid = row["user_id"]
        tests = {"count": 0, "average": None, "attempts": None, "last": []}
        try:
            cur.execute("SELECT COUNT(*) AS n, ROUND(AVG(score)) AS avg FROM learned_topics WHERE user_id=%s", (uid,))
            stat = cur.fetchone() or {}
            tests["count"] = int(stat.get("n") or 0)
            tests["average"] = int(stat["avg"]) if stat.get("avg") is not None else None
            cur.execute("""SELECT lt.topic_code, lt.score, lt.learned_at,
                                  COALESCE(NULLIF(d.kichik_name,''),NULLIF(d.mavzu_name,''),NULLIF(d.bolim_name,''),d.bob_name) AS nom,
                                  d.subject_name
                           FROM learned_topics lt LEFT JOIN dts_tree d ON d.topic_code=lt.topic_code
                           WHERE lt.user_id=%s ORDER BY lt.learned_at DESC NULLS LAST LIMIT %s""", (uid, int(limit)))
            tests["last"] = [dict(r) for r in cur.fetchall()]
        except Exception:
            pass
        try:
            cur.execute("SELECT to_regclass('public.learning_events') IS NOT NULL AS bor")
            if (cur.fetchone() or {}).get("bor"):
                cur.execute("SELECT COUNT(*) AS n FROM learning_events WHERE user_id=%s AND event_type='test_attempt'", (uid,))
                tests["attempts"] = int((cur.fetchone() or {}).get("n") or 0)
        except Exception:
            pass
        return {"user_id": uid, "name": str(user.get("full_name") or "Foydalanuvchi"), "role": _role(user),
                "class": str(user.get("class") or ""), "kb": str(user.get("kabutar_id") or ""), "tests": tests}
    finally:
        conn.close()


def format_summary(summary):
    """HTML matn (parse_mode=HTML). Hamma foydalanuvchi matni escape qilinadi."""
    esc = lambda value: html.escape(str(value or ""), quote=False)
    parts = [ROLE_NAMES.get(summary.get("role"), "")]
    klass = summary.get("class") or ""
    if klass:
        parts.append(klass if "kurs" in klass.lower() or not klass.isdigit() else f"{klass}-sinf")
    if summary.get("kb"):
        parts.append(summary["kb"])
    lines = [f"👤 <b>{esc(summary.get('name'))}</b>", "🎭 " + esc(" · ".join(p for p in parts if p))]
    tests = summary.get("tests") or {}
    if tests.get("count"):
        line = f"📝 Testlar: <b>{tests['count']}</b> ta mavzu"
        if tests.get("average") is not None:
            line += f" · o‘rtacha <b>{tests['average']}%</b>"
        if tests.get("attempts"):
            line += f" · {tests['attempts']} urinish"
        lines += ["", line]
        if tests.get("last"):
            lines.append("Oxirgi natijalar:")
            for item in tests["last"]:
                name = item.get("nom") or item.get("topic_code") or "Mavzu"
                subject = f" ({item['subject_name']})" if item.get("subject_name") else ""
                when = item.get("learned_at")
                date = f" · {when.strftime('%d.%m')}" if hasattr(when, "strftime") else ""
                score = item.get("score")
                mark = "🟢" if (score or 0) >= 80 else "🟡" if (score or 0) >= 50 else "🔴"
                lines.append(f"{mark} {esc(str(name)[:60])}{esc(subject)} — <b>{score if score is not None else '—'}%</b>{date}")
    else:
        lines += ["", "📝 Hali test ishlamagansiz. Pastdagi tugma bilan boshlang."]
    lines += ["", "Test ishlash yoki mavzu o‘rganish uchun tugmani bosing — sayt shu yerda ilova kabi ochiladi."]
    return "\n".join(lines)


def site_link(site, ticket=None, go="home"):
    """Saytga havola. Chipta bo'lsa kod so'ramasdan kiradi (#tg_ticket=...&go=test)."""
    base = str(site or "").rstrip("/") + "/"
    if not ticket:
        return base
    return base + "#" + urlencode({"tg_ticket": ticket, "go": go})


def cabinet_rows(site, tickets, button_factory, web_app_factory=None):
    """Tugmalar qatori. tickets: {'test':..., 'organish':..., 'home':...} (bo'lmasa oddiy havola).
    web_app_factory mavjud bo'lsa Test/Mavzu Telegram ichida ilova sifatida ochiladi."""
    def open_button(text, go):
        url = site_link(site, tickets.get(go), go)
        if web_app_factory is not None:
            return button_factory(text=text, web_app=web_app_factory(url=url))
        return button_factory(text=text, url=url)
    return [
        [open_button("📝 Test ishlash", "test"), open_button("📘 Mavzu o‘rganish", "organish")],
        [button_factory(text="🌐 Saytni brauzerda ochish", url=site_link(site, tickets.get("home"), "home"))],
        [button_factory(text="🔄 Yangilash", callback_data="kbcab:refresh")],
    ]
