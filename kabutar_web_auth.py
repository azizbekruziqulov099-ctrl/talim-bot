"""Kabutar web sign-in bridge; independent from selected bot/child profiles.

The bot verifies an own contact, asks for a role, then delivers a login code.
All login entrances issue a phone-bound code inside the bot. Only an explicit,
authenticated legacy account-link request retains browser-bound approval.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import secrets
import time
import threading
from dataclasses import dataclass
from urllib.parse import urlsplit

LOGGER = logging.getLogger(__name__)
CANCEL_TEXT = "❌ Kabutar kirishini bekor qilish"
CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")
CALLBACK_RE = re.compile(r"^kbweb:(confirm|cancel|role_google|role_oquvchi|role_talaba|role_oqituvchi|role_ota-ona):([A-Za-z0-9_-]{32})$")
ROLE_LABELS = {'oquvchi':'📚 O‘quvchi', 'talaba':'🎓 Talaba', 'oqituvchi':'👩‍🏫 O‘qituvchi', 'ota-ona':'👨‍👩‍👧 Ota-ona', 'admin':'Administrator'}
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
    parts = urlsplit(str(value or "").strip())
    host = (parts.hostname or "").lower()
    port = parts.port  # Reject invalid ports while checking configuration.
    internal = allow_internal and (host.endswith(".railway.internal") or host in ("localhost", "127.0.0.1"))
    if (parts.scheme != "https" and not (parts.scheme == "http" and internal)) or not host or re.search(r"[\s*]", host):
        raise ValueError("Kabutar URL HTTPS bo'lishi kerak")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Kabutar URL faqat origin bo'lishi kerak")
    authority = f"[{host}]" if ":" in host else host
    if port is not None and port != (443 if parts.scheme == "https" else 80):
        authority += f":{port}"
    return f"{parts.scheme}://{authority}"


def is_site_command(message):
    """Only a standalone command; lesson messages and normal /start stay intact."""
    return bool(re.fullmatch(r"/(?:sayt|kabutar)(?:@[A-Za-z0-9_]+)?\s*",
                             str(getattr(message, "text", "") or "")))


DEFAULT_AUTH_API_URL = "https://talimplatformasi-production.up.railway.app"


def derived_bot_secret(bot_token):
    """Same value as the backend's kabutar_auth.derived_bot_secret: used when
    KABUTAR_BOT_AUTH_SECRET is not set, since both services share BOT_TOKEN."""
    import hashlib
    import hmac
    token = str(bot_token or "").strip()
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", token):
        return ""
    return hmac.new(token.encode("utf-8"), b"kabutar-bot-auth-v1", hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class Settings:
    api: str
    secret: str
    database: str
    site: str
    site_urls: str = ""
    bot_token: str = ""

    @classmethod
    def environment(cls):
        return cls(
            api=(os.getenv("KABUTAR_AUTH_API_URL", "").strip()
                 or os.getenv("BAZA_URL", "").strip() or DEFAULT_AUTH_API_URL).rstrip("/"),
            secret=(os.getenv("KABUTAR_BOT_AUTH_SECRET", "").strip()
                    or derived_bot_secret(os.getenv("BOT_TOKEN", ""))),
            database=os.getenv("DATABASE_URL", "").strip(),
            site=os.getenv("KABUTAR_SITE_URL", "https://talimkabutar.uz").strip(),
            site_urls=os.getenv("KABUTAR_SITE_URLS", "").strip(),
            bot_token=os.getenv("BOT_TOKEN", "").strip(),
        )

    def allowed_sites(self):
        origins = {safe_origin(self.site)}
        if self.site_urls:
            # Explicit origins only: no suffix matching, wildcard or URLs learned
            # from a backend response. Empty entries are configuration mistakes.
            origins.update(safe_origin(value) for value in self.site_urls.split(","))
        return origins

    def validation_errors(self):
        """Safe field names for deployment logs; never return configuration values."""
        errors = []
        for name, value, internal in (("KABUTAR_AUTH_API_URL", self.api, True),
                                      ("KABUTAR_SITE_URL", self.site, False)):
            try:
                safe_origin(value, allow_internal=internal)
            except (ValueError, UnicodeError):
                errors.append(name)
        if self.site_urls:
            try:
                for value in self.site_urls.split(","):
                    safe_origin(value)
            except (ValueError, UnicodeError):
                errors.append("KABUTAR_SITE_URLS")
        if len(self.secret) < 32 and not self.bot_token:
            errors.append("KABUTAR_BOT_AUTH_SECRET")
        if not self.database:
            errors.append("DATABASE_URL")
        return errors

    def validate(self):
        if self.validation_errors():
            raise ValueError("Kabutar kirishining server sozlamalari yetishmayapti")

    def setup_message(self):
        """Explain the failing service/field without disclosing any values."""
        errors = self.validation_errors()
        details = {
            'KABUTAR_AUTH_API_URL': 'KABUTAR_AUTH_API_URL — bot xizmatida backendning to‘liq HTTPS manzilini kiriting; oxiriga /auth qo‘shmang.',
            'KABUTAR_BOT_AUTH_SECRET': 'KABUTAR_BOT_AUTH_SECRET — bot va backend xizmatlarida bir xil, kamida 32 belgili qiymat bo‘lsin (yoki ikkala xizmatda bir xil BOT_TOKEN bo‘lsa, bu o‘zgaruvchini umuman o‘chirib qo‘ying).',
            'DATABASE_URL': 'DATABASE_URL — bot xizmatiga PostgreSQL ulanishini biriktiring.',
            'KABUTAR_SITE_URL': 'KABUTAR_SITE_URL — saytning to‘liq HTTPS manzilini kiriting.',
            'KABUTAR_SITE_URLS': 'KABUTAR_SITE_URLS — faqat to‘liq HTTPS sayt manzillarini vergul bilan ajrating.',
        }
        return ('Telegram kodi berilmadi: bot ishlayotgan xizmatning sozlamalari to‘liq emas.\n\n'
                + '\n'.join(details[name] for name in errors)
                + '\n\nRailway’da aynan BOT ishlayotgan xizmat → Variables bo‘limini oching. '
                'Backendga qo‘shilgan Variable botga avtomatik o‘tmaydi. '
                'O‘zgarishlarni Deploy qiling, so‘ng botda /start bosing.')


class AuthError(Exception):
    def __init__(self, status=503, detail=None):
        self.status = status
        self.detail = detail
        super().__init__(f"Kabutar auth HTTP {status}")


ERROR_TEXT = {
    400: "Kirish so'rovi yaroqsiz. Botda /sayt orqali yangi kod oling.",
    401: "Bot va saytning kirish sozlamalari mos emas. Administrator: Railway'da bot va backend xizmatlarida BOT_TOKEN bir xil ekanini tekshirsin, backendda KABUTAR_BOT_USERNAME shu botning @nomi bo'lsin, so'ng ikkala xizmatni qayta Deploy qilsin.",
    403: "Bu so'rovni tasdiqlab bo'lmaydi. Botda /sayt orqali yangi kod oling.",
    404: "Kirish so'rovi topilmadi. Botda /sayt orqali yangi kod oling.",
    409: "Hisoblar o'rtasida mos kelmaslik bor. Hech qanday hisob ko'chirilmadi. Avval eski hisobingizga kirib Telegramni profilidan ulang.",
    410: "So'rov muddati tugagan yoki ishlatilgan. Botda /sayt orqali yangi kod oling.",
    429: "So'rovlar ko'paydi. Bir ozdan keyin botda /sayt orqali qayta urinib ko'ring.",
}


class BackendClient:
    def __init__(self, settings):
        self.settings = settings

    def auth_headers(self):
        """Every proof the bot has; the backend accepts any one that matches.
        So a KABUTAR_BOT_AUTH_SECRET set in only one service no longer gives 401."""
        headers = {}
        if self.settings.secret:
            headers["X-Kabutar-Bot-Secret"] = self.settings.secret
        derived = derived_bot_secret(self.settings.bot_token)
        if derived and derived != self.settings.secret:
            headers["X-Kabutar-Bot-Proof"] = derived
        if self.settings.bot_token:
            headers["X-Kabutar-Bot-Token"] = self.settings.bot_token
        return headers

    async def post(self, operation, payload):
        import aiohttp
        self.settings.validate()
        url = safe_origin(self.settings.api, allow_internal=True) + "/auth/telegram/" + operation
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12)) as session:
                async with session.post(
                    url, json=payload,
                    headers=self.auth_headers(),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        detail = None
                        if operation == 'code/issue' and response.status == 404:
                            raise AuthError(404, 'Bot ulangan backendda yangi kirish xizmati yo‘q. Backendga REV59 ni joylang va botdagi KABUTAR_AUTH_API_URL shu backend manziliga tengligini tekshiring.')
                        if response.status in (409, 422):
                            data = await response.json()
                            if isinstance(data.get('detail'), str): detail = data['detail'][:300]
                        raise AuthError(response.status, detail)
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
                    # A Python lock only guards this process. Two newly deployed
                    # replicas must not create the PostgreSQL type/table together.
                    cur.execute("SELECT pg_advisory_xact_lock(%s)", (31093110,))
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
                    # Eski revizsiyada yaratilgan jadvalda bu ustunlar/kenglik bo'lmasa
                    # INSERT yiqiladi va foydalanuvchi "Kirish xizmatidan javob olinmadi"
                    # ko'radi. Sxemani joyida moslaymiz — ma'lumot yo'qolmaydi.
                    for statement in (
                        "ALTER TABLE kabutar_bot_login_state ADD COLUMN IF NOT EXISTS mode VARCHAR(8) NOT NULL DEFAULT 'login'",
                        "ALTER TABLE kabutar_bot_login_state ADD COLUMN IF NOT EXISTS phase VARCHAR(16) NOT NULL DEFAULT 'contact'",
                        "ALTER TABLE kabutar_bot_login_state ADD COLUMN IF NOT EXISTS phone VARCHAR(16)",
                        "ALTER TABLE kabutar_bot_login_state ADD COLUMN IF NOT EXISTS sending_at TIMESTAMPTZ",
                        "ALTER TABLE kabutar_bot_login_state ADD COLUMN IF NOT EXISTS delivery TEXT NOT NULL DEFAULT 'approval'",
                        "ALTER TABLE kabutar_bot_login_state ALTER COLUMN challenge TYPE VARCHAR(64)",
                        "ALTER TABLE kabutar_bot_login_state ALTER COLUMN verification_code TYPE VARCHAR(12)",
                        "ALTER TABLE kabutar_bot_login_state ALTER COLUMN phone TYPE VARCHAR(32)",
                    ):
                        cur.execute(statement)
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
                        (telegram_id, challenge, verification_code, mode, phase, expires_at, delivery)
                        VALUES (%s,%s,%s,%s,'contact',NOW() + %s * INTERVAL '1 second',%s)
                        ON CONFLICT(telegram_id) DO UPDATE SET challenge=EXCLUDED.challenge,
                        verification_code=EXCLUDED.verification_code, mode=EXCLUDED.mode,
                        phase='contact', phone=NULL, sending_at=NULL, expires_at=EXCLUDED.expires_at, delivery=EXCLUDED.delivery""",
                        (telegram_id, values["challenge"], values["verification_code"], values["mode"], values["ttl"], values.get('delivery','approval')))
                    return True
                if operation == "delete":
                    cur.execute("DELETE FROM kabutar_bot_login_state WHERE telegram_id=%s AND challenge=%s", (telegram_id, values["challenge"]))
                    return cur.rowcount > 0
                cur.execute("""SELECT challenge,verification_code,mode,phase,phone,delivery,
                    (sending_at IS NOT NULL AND sending_at > NOW() - INTERVAL '30 seconds') AS busy
                    FROM kabutar_bot_login_state WHERE telegram_id=%s AND expires_at>NOW() FOR UPDATE""", (telegram_id,))
                row = cur.fetchone()
                if not row:
                    return None
                result = dict(zip(("challenge", "verification_code", "mode", "phase", "phone", "delivery", "busy"), row))
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
    configuration_errors = settings.validation_errors()
    configured = not configuration_errors
    if configuration_errors:
        LOGGER.warning("Kabutar web login configuration needs checking: %s",
                       ", ".join(configuration_errors))

    def contact_keyboard():
        return ReplyKeyboardMarkup(keyboard=[
            [KeyboardButton(text="📱 O'z telefon raqamimni ulashish", request_contact=True)],
            [KeyboardButton(text=CANCEL_TEXT)],
        ], resize_keyboard=True, one_time_keyboard=True)

    async def open_site(message):
        if not private_sender(message):
            await message.answer("Saytga kirish uchun botning shaxsiy chatida /sayt buyrug'ini yuboring.")
            return
        if not configured:
            await message.answer(settings.setup_message(), reply_markup=ReplyKeyboardRemove())
            return
        try:
            pending = await store.run('get', message.from_user.id)
            if pending and pending.get('busy'):
                await message.answer('Kod tayyorlanmoqda. Bir oz kuting.')
                return
            if pending and (pending.get('delivery') != 'portable' or is_site_command(message)):
                # Explicit /sayt or the new entry replaces an old browser-only
                # request, so its code cannot be confused with the new form.
                await store.run('delete',message.from_user.id,challenge=pending['challenge'])
                pending = None
            if pending and pending.get('phone'):
                await show_roles(message,pending)
                return
            if not pending:
                await store.run('put',message.from_user.id,challenge=secrets.token_urlsafe(24),
                    verification_code='000000',ttl=300,mode='login',delivery='portable')
            await message.answer(
                "Saytga kirish kodini shu botdan olasiz.\n\n"
                "1. Pastdagi tugma bilan o‘z telefon raqamingizni ulashing.\n"
                "2. Rolingizni tanlang.\n"
                "3. Bot bergan kodni saytda kiriting.\n\n"
                "Botning bosh menyusi: /menu",reply_markup=contact_keyboard())
        except Exception as exc:
            await fail(message,exc)

    async def show_roles(message,pending):
        challenge = pending['challenge']
        if pending.get('delivery') not in ('code','portable'):
            await message.answer('Telegramni mavjud hisobingizga ulashni tasdiqlang.',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text='✅ Telegramni ulash',callback_data=f'kbweb:confirm:{challenge}')]]))
            return
        await message.answer('Saytga qaysi rolda kirasiz? Mavjud hisobingizning roli saqlanadi.',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=ROLE_LABELS[role],callback_data=f'kbweb:role_{role}:{challenge}')]
                for role in ('oquvchi','talaba','oqituvchi','ota-ona')
            ] + [[InlineKeyboardButton(text='📧 Oldin Gmail bilan kirganman',callback_data=f'kbweb:role_google:{challenge}')],
                 [InlineKeyboardButton(text='❌ Bekor qilish',callback_data=f'kbweb:cancel:{challenge}')]]))

    async def fail(message, exc):
        status = exc.status if isinstance(exc, AuthError) else 503
        # Sabab logda to'liq ko'rinadi (sir, telefon yoki challenge yozilmaydi);
        # foydalanuvchiga esa kod beriladi — administrator shu kod bo'yicha topadi.
        LOGGER.warning("Kabutar web login unavailable (status=%s, error=%s)", status,
                       type(exc).__name__ if not isinstance(exc, AuthError) else "AuthError")
        matn = (exc.detail if isinstance(exc, AuthError) and exc.detail else None) or ERROR_TEXT.get(status,
            "Kod xizmatidan javob olinmadi. Birozdan keyin botda /sayt orqali qayta urinib ko'ring.")
        await message.answer(f"{matn}\n\n(Xato kodi: {status})", reply_markup=ReplyKeyboardRemove())

    async def begin(message):
        if not private_sender(message):
            await message.answer("Kabutarga kirishni botning shaxsiy chatida boshlang.")
            return
        if re.fullmatch(r'/start(?:@[A-Za-z0-9_]+)?\s+kb_login\s*', str(message.text or '')):
            await open_site(message)
            return
        challenge = start_challenge(message.text)
        if not challenge:
            await open_site(message)
            return
        if not configured:
            await open_site(message)
            return
        try:
            data = await client.post("inspect", {"challenge": challenge})
            # Old login URLs must not reopen the retired wait/return-to-site
            # loop. A new code belongs to this Telegram user, not that browser.
            if data.get('mode') != 'link':
                await open_site(message)
                return
            delivery = data.get('delivery', 'approval')
            if data.get("status") == "confirmed" and delivery != 'code':
                await message.answer("Bu kirish so'rovi allaqachon tasdiqlangan. Kirishni boshlagan sayt oynasiga qayting.", reply_markup=ReplyKeyboardRemove())
                return
            code = str(data.get("verification_code", ""))
            ttl = max(0, min(300, int(data.get("expires_in", 0))))
            if data.get("status") not in ("pending", "confirmed") or not re.fullmatch(r"\d{6}", code) or ttl <= 0:
                raise AuthError(410)
            if safe_origin(data.get("site")) not in settings.allowed_sites():
                raise AuthError(403)
            mode = "link" if data.get("mode") == "link" else "login"
            await store.run("put", message.from_user.id, challenge=challenge,
                            verification_code=code, ttl=ttl, mode=mode, delivery=delivery)
            title = "Telegramni mavjud Kabutar hisobingizga ulash" if mode == "link" else "Kabutar saytiga kirish"
            await message.answer(
                f"{title}\n\nSayt: {safe_origin(data['site'])}\nTekshiruv belgisi: {code}\n\n"
                "Shu olti raqam siz O'ZINGIZ ochgan Kabutar kirish oynasida ham bir xil bo'lishi kerak. "
                "Birov yuborgan havola, rasm yoki kod orqali tasdiqlamang.\n\n"
                "Belgilar mos bo'lsa, pastdagi tugma bilan o'z raqamingizni ulashing. "
                "Keyingi qadamda rolingizni tanlaysiz va sayt uchun kod olasiz. "
                "Bu SMS yoki Telegram akkauntingizga kirish kodi emas.",
                reply_markup=contact_keyboard())
        except Exception as exc:
            if isinstance(exc, AuthError) and exc.status in (400, 404, 410):
                await open_site(message)
                return
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
            if pending.get('delivery') in ('code','portable'):
                await message.answer('Telefon tasdiqlandi. Saytga qaysi rolda kirasiz?', reply_markup=ReplyKeyboardRemove())
                await show_roles(message,pending)
                return
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
                await message.answer("Kabutar kirishi bekor qilindi. Yangi kod uchun /sayt bosing.", reply_markup=ReplyKeyboardRemove())
                return
            if pending.get('mode') != 'link' and pending.get('delivery') != 'portable':
                from types import SimpleNamespace
                await open_site(SimpleNamespace(from_user=call.from_user,chat=message.chat,answer=message.answer))
                return
            role = action.removeprefix('role_') if action.startswith('role_') else None
            if role == 'google':
                if not pending.get('phone'):
                    await message.answer('Avval o‘z telefon raqamingizni ulashing.',reply_markup=contact_keyboard())
                    return
                # The site authenticates Google before this code can link accounts.
                # The fallback selection never replaces an existing account's role.
                role = 'oquvchi'
            if pending.get('delivery') in ('code','portable') and role not in ROLE_LABELS:
                await message.answer('Yuqoridagi tugmalardan rolingizni tanlang.')
                return
            pending = await store.run("claim", uid, challenge=challenge)
            if not pending:
                await message.answer("Tasdiqlash allaqachon yuborilmoqda yoki so'rov eskirgan. Saytdagi oynani tekshiring.")
                return
            try:
                operation = 'code/issue' if pending.get('delivery') == 'portable' else 'confirm'
                result = await client.post(operation, {
                    "challenge": challenge,
                    "telegram_user_id": uid,
                    "contact_user_id": uid,
                    "phone": pending["phone"],
                    "full_name": " ".join(filter(None, [call.from_user.first_name, call.from_user.last_name]))[:150],
                    **({'role':role} if role else {}),
                    **({'purpose':'link' if action == 'role_google' else 'login'} if operation == 'code/issue' else {}),
                })
                if result.get("status") != "confirmed":
                    raise AuthError()
                if operation == 'code/issue' and action == 'role_google' and result.get('purpose') != 'link':
                    raise AuthError(503, 'Backenddagi Gmailga ulash xizmati yangilanmagan. Backendni yangilab, /sayt orqali yangi kod oling.')
                if pending.get('delivery') in ('code','portable'):
                    code = str(result.get('code') or '')
                    if not re.fullmatch(r'\d{6}', code): raise AuthError(410)
                    portable = pending.get('delivery') == 'portable'
                    google = action == 'role_google'
                    from urllib.parse import urlencode
                    return_url = safe_origin(settings.site) + '/#' + urlencode({
                        'telegram_phone':pending['phone'], **({'telegram_link':'1'} if google else {})})
                    title = ('✅ Gmail hisobiga ulash kodi' if google else '✅ Saytga kirish kodi tayyor') if portable else f"✅ {ROLE_LABELS.get(result.get('role'), ROLE_LABELS.get(role, 'Profil'))}"
                    await message.answer(
                        f"{title}\n\n"
                        f"Saytga kirish kodi: <code>{code}</code>\n\n"
                        + (f"Telefon: <code>{pending['phone']}</code>\nKod {int(result.get('expires_in', 300))} soniya amal qiladi. "
                           "Saytda shu telefon raqami va kodni kiriting. Boshqalarga bermang."
                           if portable else "Shu kodni kirishni boshlagan saytdagi «Botdan olingan kod» maydoniga kiriting."),
                        parse_mode='HTML', reply_markup=ReplyKeyboardRemove())
                    if portable:
                        await message.answer(
                            'Avval o‘sha Gmail hisobingiz bilan kiring, so‘ng shu kod bilan Telegramni ulang.' if google else 'Kodni oldingiz. Endi saytga kiring:',
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                InlineKeyboardButton(text='🌐 Saytni ochish',url=return_url)]]))
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
            if pending.get('delivery') not in ('code','portable'):
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
        if (not call.message or not is_private(call.message.chat)
                or call.message.chat.id != call.from_user.id or call.from_user.is_bot):
            await call.answer("Kirishni botning shaxsiy chatida boshlang.", show_alert=True)
            return
        await call.answer()
        # callback.message.from_user belongs to the bot. Reuse the explanatory
        # content via a private message proxy with the actual requesting user.
        from types import SimpleNamespace
        await open_site(SimpleNamespace(from_user=call.from_user, chat=call.message.chat,
                                        answer=call.message.answer))

    # These handlers are deliberately registered before imported/general handlers.
    dp.message.register(begin, is_web_start)
    # A bare Start is also a valid entrance. Losing a deep-link parameter must
    # never clear the request or send the person into registration by accident.
    dp.message.register(open_site, lambda message: private_sender(message) and bool(
        re.fullmatch(r'/start(?:@[A-Za-z0-9_]+)?\s*', str(getattr(message,'text','') or ''))))
    dp.message.register(open_site, is_site_command)
    dp.message.register(cancel, lambda message: getattr(message, "text", None) == CANCEL_TEXT)
    dp.message.register(contact, PendingContact())
    dp.callback_query.register(button, lambda call: str(call.data or "").startswith("kbweb:"))
    dp.callback_query.register(old_link, lambda call: call.data in ("kb_sayt_ulash", "kb_veb_kod"))
    handlers = {"begin": begin, "contact": contact, "button": button, "cancel": cancel,
            "clear_pending": clear_pending, "open_site": open_site, "old_link": old_link}
    dp._kabutar_web_handlers = handlers
    return handlers


def ensure_kabutar_auth(dp):
    """One registration, before any bot entry point imports general handlers."""
    handlers = getattr(dp, '_kabutar_web_handlers', None)
    return handlers if handlers is not None else install_kabutar_auth(dp)
