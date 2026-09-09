"""Kabutar web sign-in bridge; independent from selected bot/child profiles.

The browser and this bot compare a six-digit label. It is NOT a login code.
Only the backend can consume a challenge and issue a browser session.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import threading
from dataclasses import dataclass
from urllib.parse import urlsplit

LOGGER = logging.getLogger(__name__)
CANCEL_TEXT = "❌ Kabutar kirishini bekor qilish"
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")
CALLBACK_RE = re.compile(r"^kbweb:(confirm|cancel):([A-Za-z0-9_-]{32})$")
CONTACT_FIELDS = ("forward_origin", "forward_from", "forward_sender_name")


def start_challenge(text):
    parts = str(text or "").split()
    if len(parts) != 2 or not re.fullmatch(r"/start(?:@[A-Za-z0-9_]+)?", parts[0]):
        return None
    token = parts[1][3:] if parts[1].startswith("kb_") else ""
    return token if CHALLENGE_RE.fullmatch(token) else None


def is_web_start(message):
    parts = str(getattr(message, "text", "") or "").split()
    return (len(parts) >= 2 and parts[0].split("@")[0] == "/start"
            and parts[1].startswith("kb_"))


def is_private(chat):
    return bool(chat and getattr(chat.type, "value", chat.type) == "private")


def private_sender(message):
    user = getattr(message, "from_user", None)
    chat = getattr(message, "chat", None)
    return bool(user and chat and is_private(chat)
                and chat.id == user.id and not getattr(user, "is_bot", False))


def own_contact_phone(message):
    """Never authenticate a forwarded contact or a manually supplied number."""
    contact = getattr(message, "contact", None)
    if not private_sender(message) or not contact:
        return None
    if contact.user_id != message.from_user.id:
        return None
    if any(getattr(message, field, None) for field in CONTACT_FIELDS):
        return None
    value = re.sub(r"[\s()\-]", "", str(contact.phone_number or ""))
    if not re.fullmatch(r"\+?[1-9]\d{6,14}", value):
        return None
    return "+" + value.lstrip("+")


def callback_parts(data):
    match = CALLBACK_RE.fullmatch(str(data or ""))
    return match.groups() if match else None


def safe_origin(value, allow_internal=False):
    parts = urlsplit(str(value or ""))
    host = parts.hostname or ""
    internal = allow_internal and (host.endswith(".railway.internal") or host in ("localhost", "127.0.0.1"))
    if (parts.scheme != "https" and not (parts.scheme == "http" and internal)) or not host:
        raise ValueError("Kabutar URL HTTPS bo'lishi kerak")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Kabutar URL faqat origin bo'lishi kerak")
    return f"{parts.scheme}://{parts.netloc}"


@dataclass(frozen=True)
class Settings:
    api: str
    secret: str
    database: str
    site: str

    @classmethod
    def environment(cls):
        return cls(
            api=os.getenv("KABUTAR_AUTH_API_URL", "").strip(),
            secret=os.getenv("KABUTAR_BOT_AUTH_SECRET", "").strip(),
            database=os.getenv("DATABASE_URL", "").strip(),
            site=os.getenv("KABUTAR_SITE_URL", "https://talimkabutar.uz").strip(),
        )

    def validate(self):
        safe_origin(self.api, allow_internal=True)
        safe_origin(self.site)
        if len(self.secret) < 32 or not self.database:
            raise ValueError("Kabutar kirishining server sozlamalari yetishmayapti")


class AuthError(Exception):
    def __init__(self, status=503):
        self.status = status
        super().__init__(f"Kabutar auth HTTP {status}")


ERROR_TEXT = {
    400: "Kirish so'rovi yaroqsiz. Saytdan yangi kirish so'rovi oching.",
    401: "Kirish xizmati sozlamasi tekshirilishi kerak. Hozircha Google orqali kiring.",
    403: "Bu so'rovni tasdiqlab bo'lmaydi. Saytda yangidan kirishni boshlang.",
    404: "Kirish so'rovi topilmadi. Saytdan yangi so'rov oching.",
    409: "Hisoblar o'rtasida mos kelmaslik bor. Hech qanday hisob ko'chirilmadi. Avval eski hisobingizga kirib Telegramni profilidan ulang.",
    410: "So'rov muddati tugagan yoki ishlatilgan. Saytdagi oynani tekshiring; kerak bo'lsa yangidan kirishni boshlang.",
    429: "So'rovlar ko'paydi. Bir ozdan keyin saytdan qayta urinib ko'ring.",
}


class BackendClient:
    def __init__(self, settings):
        self.settings = settings

    async def post(self, operation, payload):
        import aiohttp
        self.settings.validate()
        url = safe_origin(self.settings.api, allow_internal=True) + "/auth/telegram/" + operation
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session:
                async with session.post(
                    url, json=payload,
                    headers={"X-Kabutar-Bot-Secret": self.settings.secret},
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise AuthError(response.status)
                    result = await response.json()
                    if not isinstance(result, dict):
                        raise AuthError()
                    return result
        except AuthError:
            raise
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            # Never log the URL response body, secret, phone, or challenge.
            raise AuthError() from None


class PendingStore:
    """Short-lived PostgreSQL state survives bot restart and replica handoff."""
    def __init__(self, database):
        self.database = database
        self.ready = False
        self.lock = threading.Lock()
        self.last_cleanup = 0.0

    def _connect(self):
        import psycopg2
        return psycopg2.connect(self.database, connect_timeout=5)

    def ensure(self):
        if self.ready:
            return
        with self.lock:
            if self.ready:
                return
            conn = self._connect()
            try:
                with conn, conn.cursor() as cur:
                    cur.execute("""CREATE TABLE IF NOT EXISTS kabutar_bot_login_state (
                        telegram_id BIGINT PRIMARY KEY,
                        challenge VARCHAR(32) NOT NULL,
                        verification_code VARCHAR(6) NOT NULL,
                        mode VARCHAR(8) NOT NULL DEFAULT 'login',
                        phase VARCHAR(16) NOT NULL DEFAULT 'contact',
                        phone VARCHAR(16),
                        expires_at TIMESTAMPTZ NOT NULL,
                        sending_at TIMESTAMPTZ
                    )""")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_kabutar_bot_login_expiry ON kabutar_bot_login_state(expires_at)")
                self.ready = True
            finally:
                conn.close()

    def _run(self, operation, telegram_id, **values):
        self.ensure()
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                now = time.monotonic()
                if now - self.last_cleanup > 60:
                    cur.execute("DELETE FROM kabutar_bot_login_state WHERE expires_at <= NOW()")
                    self.last_cleanup = now
                if operation == "put":
                    cur.execute("""INSERT INTO kabutar_bot_login_state
                        (telegram_id, challenge, verification_code, mode, phase, expires_at)
                        VALUES (%s,%s,%s,%s,'contact',NOW() + %s * INTERVAL '1 second')
                        ON CONFLICT(telegram_id) DO UPDATE SET challenge=EXCLUDED.challenge,
                        verification_code=EXCLUDED.verification_code, mode=EXCLUDED.mode,
                        phase='contact', phone=NULL, sending_at=NULL, expires_at=EXCLUDED.expires_at""",
                        (telegram_id, values["challenge"], values["verification_code"], values["mode"], values["ttl"]))
                    return True
                if operation == "delete":
                    cur.execute("DELETE FROM kabutar_bot_login_state WHERE telegram_id=%s AND challenge=%s", (telegram_id, values["challenge"]))
                    return cur.rowcount > 0
                cur.execute("""SELECT challenge,verification_code,mode,phase,phone,
                    (sending_at IS NOT NULL AND sending_at > NOW() - INTERVAL '30 seconds') AS busy
                    FROM kabutar_bot_login_state WHERE telegram_id=%s AND expires_at>NOW() FOR UPDATE""", (telegram_id,))
                row = cur.fetchone()
                if not row:
                    return None
                result = dict(zip(("challenge", "verification_code", "mode", "phase", "phone", "busy"), row))
                if operation == "get":
                    return result
                if values.get("challenge", row[0]) != row[0]:
                    return None
                if operation == "contact":
                    if result["busy"]:
                        return None
                    cur.execute("UPDATE kabutar_bot_login_state SET phone=%s,phase='approval',sending_at=NULL WHERE telegram_id=%s", (values["phone"], telegram_id))
                    result.update(phone=values["phone"], phase="approval")
                    return result
                if operation == "claim":
                    if result["busy"] or not result["phone"] or result["phase"] not in ("approval", "submitting"):
                        return None
                    cur.execute("UPDATE kabutar_bot_login_state SET phase='submitting',sending_at=NOW() WHERE telegram_id=%s", (telegram_id,))
                    return result
                if operation == "retry":
                    cur.execute("UPDATE kabutar_bot_login_state SET phase='approval',sending_at=NULL WHERE telegram_id=%s", (telegram_id,))
                    return True
                raise ValueError("Unknown store operation")
        finally:
            conn.close()

    async def run(self, operation, telegram_id, **values):
        return await asyncio.to_thread(self._run, operation, telegram_id, **values)


def install_kabutar_auth(dp, settings=None, store=None, client=None):
    """Register before Talim.py's general /start, contact and callback handlers."""
    from aiogram.filters import BaseFilter
    from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
                               InlineKeyboardMarkup, InlineKeyboardButton)
    settings = settings or Settings.environment()
    store = store or PendingStore(settings.database)
    client = client or BackendClient(settings)
    try:
        settings.validate()
        configured = True
    except ValueError:
        configured = False

    def contact_keyboard():
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📱 O'z telefon raqamimni ulashish", request_contact=True)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ], resize_keyboard=True, one_time_keyboard=True)

    def website_keyboard():
        try:
            site = safe_origin(settings.site)
        except ValueError:
            site = "https://talimkabutar.uz"
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🌐 Kabutarni ochish", url=site)
        ]])

    async def fail(message, exc):
        status = exc.status if isinstance(exc, AuthError) else 503
        LOGGER.warning("Kabutar web login unavailable (status=%s)", status)
        await message.answer(ERROR_TEXT.get(status,
            "Kirish xizmatidan javob olinmadi. Saytdagi oynani tekshiring, birozdan keyin qayta urinib ko'ring."),
            reply_markup=ReplyKeyboardRemove())

    async def begin(message):
        if not private_sender(message):
            await message.answer("Kabutarga kirishni botning shaxsiy chatida boshlang.")
            return
        challenge = start_challenge(message.text)
        if not challenge:
            await message.answer("Kirish havolasi yaroqsiz. Kabutar saytida «Telegram orqali kirish»ni qayta bosing.")
            return
        try:
            data = await client.post("inspect", {"challenge": challenge})
            if data.get("status") == "confirmed":
                await message.answer("Bu kirish so'rovi allaqachon tasdiqlangan. Kirishni boshlagan sayt oynasiga qayting.", reply_markup=ReplyKeyboardRemove())
                return
            code = str(data.get("verification_code", ""))
            ttl = max(0, min(300, int(data.get("expires_in", 0))))
            if data.get("status") != "pending" or not re.fullmatch(r"\d{6}", code) or ttl <= 0:
                raise AuthError(410)
            if safe_origin(data.get("site")) != safe_origin(settings.site):
                raise AuthError(403)
            mode = "link" if data.get("mode") == "link" else "login"
            await store.run("put", message.from_user.id, challenge=challenge,
                            verification_code=code, ttl=ttl, mode=mode)
            title = "Telegramni mavjud Kabutar hisobingizga ulash" if mode == "link" else "Kabutar saytiga kirish"
            await message.answer(
                f"{title}\n\nSayt: {safe_origin(settings.site)}\nTekshiruv belgisi: {code}\n\n"
                "Shu olti raqam siz O'ZINGIZ ochgan Kabutar kirish oynasida ham bir xil bo'lishi kerak. "
                "Birov yuborgan havola, rasm yoki kod orqali tasdiqlamang.\n\n"
                "Belgilar mos bo'lsa, pastdagi tugma bilan o'z raqamingizni ulashing. "
                "Keyingi qadamda kirishni alohida tasdiqlaysiz. "
                "Bu SMS yoki Telegram akkauntingizga kirish kodi emas.",
                reply_markup=contact_keyboard())
        except Exception as exc:
            await fail(message, exc)

    class PendingContact(BaseFilter):
        async def __call__(self, message):
            if not configured or not getattr(message, "contact", None) or not private_sender(message):
                return False
            try:
                pending = await store.run("get", message.from_user.id)
            except Exception as exc:
                # A login contact must not silently authenticate via any fallback.
                await fail(message, exc)
                return {"kabutar_pending": None}
            return {"kabutar_pending": pending} if pending else False

    async def contact(message, kabutar_pending):
        if not kabutar_pending:
            return
        phone = own_contact_phone(message)
        if not phone:
            await message.answer("Faqat pastdagi tugma orqali O'Z telefon raqamingizni yuboring. Boshqa yoki uzatilgan kontakt qabul qilinmaydi.", reply_markup=contact_keyboard())
            return
        try:
            pending = await store.run("contact", message.from_user.id,
                                      challenge=kabutar_pending["challenge"], phone=phone)
            if not pending:
                raise AuthError(410)
            challenge = pending["challenge"]
            await message.answer("Telefon tasdiqlandi. Kirishni tasdiqlash qolgan.", reply_markup=ReplyKeyboardRemove())
            await message.answer(
                f"Sayt: {safe_origin(settings.site)}\nTekshiruv belgisi: {pending['verification_code']}\n"
                f"Telefon: •••• {phone[-4:]}\n\n"
                "Bu siz O'ZINGIZ ochgan brauzermi? Belgilar bir xil bo'lsa tasdiqlang. "
                "Botda tanlangan farzand yoki boshqa profil o'rniga telefon egasining Kabutar hisobi ishlatiladi.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Ha, shu brauzerda kiraman", callback_data=f"kbweb:confirm:{challenge}")],
                    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"kbweb:cancel:{challenge}")],
                ]))
        except Exception as exc:
            await fail(message, exc)

    async def button(call):
        parts = callback_parts(call.data)
        message = call.message
        # callback.message.from_user is the bot; authenticate call.from_user instead.
        if (not parts or not message or not is_private(message.chat)
                or message.chat.id != call.from_user.id or call.from_user.is_bot):
            await call.answer("Bu tasdiqlash sizga tegishli emas.", show_alert=True)
            return
        await call.answer()
        action, challenge = parts
        uid = call.from_user.id
        try:
            pending = await store.run("get", uid)
            if not pending or pending["challenge"] != challenge:
                raise AuthError(410)
            if action == "cancel":
                if pending["busy"]:
                    await message.answer("Tasdiqlash yuborilmoqda. Saytdagi kirish holatini tekshiring; kirilgan bo'lsa Profil → Chiqish orqali sessiyani yoping.")
                    return
                await store.run("delete", uid, challenge=challenge)
                await message.edit_reply_markup(reply_markup=None)
                await message.answer("Kabutar kirishi bekor qilindi. Yangi kirish uchun saytdan boshlang.", reply_markup=ReplyKeyboardRemove())
                return
            pending = await store.run("claim", uid, challenge=challenge)
            if not pending:
                await message.answer("Tasdiqlash allaqachon yuborilmoqda yoki so'rov eskirgan. Saytdagi oynani tekshiring.")
                return
            try:
                result = await client.post("confirm", {
                    "challenge": challenge,
                    "telegram_user_id": uid,
                    "contact_user_id": uid,
                    "phone": pending["phone"],
                    "full_name": " ".join(filter(None, [call.from_user.first_name, call.from_user.last_name]))[:150],
                })
                if result.get("status") != "confirmed":
                    raise AuthError()
            except Exception:
                await store.run("retry", uid, challenge=challenge)
                raise
            # Backend approval succeeded; a Telegram edit/cleanup failure must not
            # turn it into a false "login failed" message for the user.
            try:
                await store.run("delete", uid, challenge=challenge)
                await message.edit_reply_markup(reply_markup=None)
            except Exception:
                LOGGER.warning("Kabutar approved login cleanup deferred")
            await message.answer("✅ Tasdiqlandi. Kirishni boshlagan Kabutar brauzer oynasiga qayting — o'sha yerda hisobingiz ochiladi.", reply_markup=ReplyKeyboardRemove())
        except Exception as exc:
            await fail(message, exc)

    async def cancel(message):
        if not private_sender(message):
            return
        try:
            pending = await store.run("get", message.from_user.id)
            if pending:
                if pending["busy"]:
                    await message.answer("Tasdiqlash yuborilmoqda. Saytdagi holatni tekshiring; kirilgan bo'lsa Profil → Chiqishni bosing.")
                    return
                await store.run("delete", message.from_user.id, challenge=pending["challenge"])
            await message.answer("Kabutar kirish so'rovi yopildi. Bot bosh menyusi uchun /start bosing.", reply_markup=ReplyKeyboardRemove())
        except Exception as exc:
            await fail(message, exc)

    async def clear_pending(telegram_id):
        # /start, /menu and /cancel also end this separate, persistent flow.
        if not configured:
            return
        try:
            pending = await store.run("get", telegram_id)
            if pending:
                await store.run("delete", telegram_id, challenge=pending["challenge"])
        except Exception:
            LOGGER.warning("Kabutar pending login could not be cleared; it expires automatically")

    async def old_link(call):
        await call.answer()
        if call.message and is_private(call.message.chat):
            await call.message.answer("Kabutarga kirish uchun saytni ochib «Telegram orqali kirish»ni bosing. Eski ulash kodi bilan ma'lumotlarni ko'chirish o'chirilgan.", reply_markup=website_keyboard())

    # These handlers are deliberately registered before imported/general handlers.
    dp.message.register(begin, is_web_start)
    dp.message.register(cancel, lambda message: getattr(message, "text", None) == CANCEL_TEXT)
    dp.message.register(contact, PendingContact())
    dp.callback_query.register(button, lambda call: str(call.data or "").startswith("kbweb:"))
    dp.callback_query.register(old_link, lambda call: call.data in ("kb_sayt_ulash", "kb_veb_kod"))
    return {"begin": begin, "contact": contact, "button": button, "cancel": cancel, "clear_pending": clear_pending}
