"""Bot security/state contract tests; no Telegram token/network/database required."""
import asyncio
import ast
import copy
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kabutar_web_auth import (
    AuthError, CANCEL_TEXT, Settings, callback_parts, install_kabutar_auth,
    is_site_command, is_web_start, own_contact_phone, private_sender, safe_origin,
    start_challenge, PendingStore,
)

TOKEN = "b" * 32
SECOND = "c" * 32
SETTINGS = Settings("https://backend.example.com", "x" * 32, "postgres://test", "https://talimkabutar.uz")


def message(text=None, uid=42, contact=None, chat_type="private", **extra):
    obj = NS(text=text, from_user=NS(id=uid, is_bot=False, first_name="Ali", last_name="Vali"),
             chat=NS(id=uid, type=chat_type), contact=contact, answers=[], edits=[], **extra)
    async def answer(text, **kwargs):
        obj.answers.append((text, kwargs))
    async def edit_reply_markup(**kwargs):
        obj.edits.append(kwargs)
    obj.answer, obj.edit_reply_markup = answer, edit_reply_markup
    return obj


def callback(data, uid=42, chat_id=42):
    obj = NS(data=data, from_user=NS(id=uid, is_bot=False, first_name="Ali", last_name="Vali"),
             message=message(uid=chat_id), answers=[])
    obj.message.from_user.id = 900000  # Telegram callback message author is the bot.
    async def answer(*args, **kwargs):
        obj.answers.append((args, kwargs))
    obj.answer = answer
    return obj


class MemoryStore:
    def __init__(self):
        self.rows = {}
    async def run(self, op, uid, **values):
        row = self.rows.get(uid)
        if op == "put":
            self.rows[uid] = dict(values, phase="contact", phone=None, busy=False)
            return True
        if op == "get":
            return copy.deepcopy(row)
        if not row or row["challenge"] != values.get("challenge", row["challenge"]):
            return None
        if op == "delete":
            del self.rows[uid]
            return True
        if op == "contact":
            if row["busy"]: return None
            row.update(phone=values["phone"], phase="approval")
        if op == "claim":
            if row["busy"] or not row["phone"]: return None
            row.update(busy=True, phase="submitting")
        if op == "retry":
            row.update(busy=False, phase="approval")
        return copy.deepcopy(row)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail_status = None
        self.site = SETTINGS.site
        self.confirm_event = None
    async def post(self, op, payload):
        self.calls.append((op, payload))
        if op == "inspect":
            return dict(status="pending", verification_code="013245", mode="login", expires_in=300, site=self.site)
        if self.confirm_event:
            await self.confirm_event.wait()
        if self.fail_status:
            raise AuthError(self.fail_status)
        return {"status": "confirmed"}


class FakeObserver:
    def __init__(self): self.handlers = []
    def register(self, callback, *filters): self.handlers.append((callback, filters))


def fake_aiogram():
    module, filters, classes = types.ModuleType("aiogram"), types.ModuleType("aiogram.filters"), types.ModuleType("aiogram.types")
    filters.BaseFilter = object
    for name in ("ReplyKeyboardMarkup", "KeyboardButton", "ReplyKeyboardRemove", "InlineKeyboardMarkup", "InlineKeyboardButton"):
        setattr(classes, name, lambda **kwargs: NS(**kwargs))
    sys.modules.update({"aiogram": module, "aiogram.filters": filters, "aiogram.types": classes})


class PureSecurityTests(unittest.TestCase):
    def test_exact_telegram_deeplink_parser(self):
        self.assertEqual(start_challenge("/start kb_" + TOKEN), TOKEN)
        self.assertEqual(start_challenge("/start@my_bot kb_" + TOKEN), TOKEN)
        for invalid in ("/start", "/start kb_x", "/start kb_" + TOKEN + " extra", "/start kb_<script>", "/help kb_" + TOKEN):
            self.assertIsNone(start_challenge(invalid))
        self.assertTrue(is_web_start(message("/start kb_bad")))
        self.assertFalse(is_web_start(message("/start")))

    def test_own_contact_required(self):
        contact = NS(user_id=42, phone_number="998901234567")
        self.assertEqual(own_contact_phone(message(contact=contact)), "+998901234567")
        self.assertIsNone(own_contact_phone(message(contact=NS(user_id=43, phone_number="+998901234567"))))
        self.assertIsNone(own_contact_phone(message(contact=NS(user_id=None, phone_number="+998901234567"))))
        self.assertIsNone(own_contact_phone(message(contact=contact, forward_origin=NS(type="user"))))
        self.assertIsNone(own_contact_phone(message(contact=contact, chat_type="group")))
        self.assertIsNone(own_contact_phone(message(contact=NS(user_id=42, phone_number="+998<script>"))))

    def test_private_chat_identity_and_bot_account(self):
        msg = message()
        self.assertTrue(private_sender(msg))
        msg.chat.id = 7
        self.assertFalse(private_sender(msg))
        msg.chat.id = 42
        msg.from_user.is_bot = True
        self.assertFalse(private_sender(msg))

    def test_origin_and_callback_validation(self):
        self.assertEqual(safe_origin("https://talimkabutar.uz/"), SETTINGS.site)
        self.assertEqual(safe_origin(" https://TalimKabutar.uz:443/ "), SETTINGS.site)
        self.assertEqual(safe_origin("http://api.railway.internal:8080", True), "http://api.railway.internal:8080")
        for invalid in ("javascript:bad", "http://example.com", "https://user:pass@host", "https://host/path", "https://host?next=evil", "https://host#bad"):
            with self.assertRaises(ValueError): safe_origin(invalid, True)
        self.assertEqual(callback_parts("kbweb:confirm:" + TOKEN), ("confirm", TOKEN))
        self.assertIsNone(callback_parts("kbweb:confirm:short"))

    def test_site_command_does_not_capture_lessons_or_start(self):
        for value in ("/sayt", "/kabutar", "/sayt@my_bot", "/kabutar "):
            self.assertTrue(is_site_command(message(value)))
        for value in ("/start", "/sayt extra", "sayt", "Kabutar haqida", "/kabutar_other"):
            self.assertFalse(is_site_command(message(value)))

    def test_configuration_diagnostic_returns_only_names(self):
        settings = Settings("https://user:private@bad", "sensitive", "", "http://bad")
        self.assertEqual(settings.validation_errors(), ["KABUTAR_AUTH_API_URL", "KABUTAR_SITE_URL",
                                                       "KABUTAR_BOT_AUTH_SECRET", "DATABASE_URL"])
        self.assertNotIn("sensitive", repr(settings.validation_errors()))
        with self.assertRaises(ValueError):
            settings.validate()
        for value in ("https://api.example:bad", "https://api.example:99999"):
            with self.assertRaises(ValueError):
                safe_origin(value)

    def test_site_allowlist_is_explicit_and_rejects_malformed_origins(self):
        configured = Settings(SETTINGS.api, SETTINGS.secret, SETTINGS.database, SETTINGS.site,
                              "https://WWW.talimkabutar.uz:443/, https://frontend.up.railway.app")
        self.assertEqual(configured.allowed_sites(), {SETTINGS.site, "https://www.talimkabutar.uz",
                                                     "https://frontend.up.railway.app"})
        self.assertEqual(configured.validation_errors(), [])
        self.assertEqual(SETTINGS.allowed_sites(), {SETTINGS.site})
        for invalid in ("http://www.talimkabutar.uz", "https://*.talimkabutar.uz",
                        "https://www.talimkabutar.uz,", "https://www.talimkabutar.uz/path",
                        "https://user:password@www.talimkabutar.uz"):
            settings = Settings(SETTINGS.api, SETTINGS.secret, SETTINGS.database, SETTINGS.site, invalid)
            self.assertEqual(settings.validation_errors(), ["KABUTAR_SITE_URLS"])
            with self.assertRaises(ValueError):
                settings.validate()

    def test_pending_schema_creation_serializes_replicas(self):
        queries = []
        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, query, values=None): queries.append((query, values))
        class Connection:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def cursor(self): return Cursor()
            def close(self): pass
        store = PendingStore("unused")
        with patch.object(store, "_connect", return_value=Connection()):
            store.ensure()
        self.assertIn("pg_advisory_xact_lock", queries[0][0])
        self.assertIn("CREATE TABLE", queries[1][0])
        self.assertTrue(store.ready)

    def test_bot_login_handlers_are_registered_before_imported_handlers(self):
        source = (Path(__file__).resolve().parents[1] / "Talim.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        install = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.Assign)
                       and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Name)
                       and node.value.func.id == "install_kabutar_auth")
        imported = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.ImportFrom)
                        and node.module == "admin_handlers")
        self.assertLess(install, imported)
        self.assertNotIn('text="🔗 Saytga ulanish kodi"', source)


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fake_aiogram()
        self.store, self.client = MemoryStore(), FakeClient()
        self.dp = NS(message=FakeObserver(), callback_query=FakeObserver())
        self.handlers = install_kabutar_auth(self.dp, SETTINGS, self.store, self.client)

    async def begin(self, token=TOKEN):
        msg = message("/start kb_" + token)
        await self.handlers["begin"](msg)
        return msg

    async def contact(self, uid=42, owner=42):
        msg = message(uid=uid, contact=NS(user_id=owner, phone_number="+998901234567"))
        await self.handlers["contact"](msg, copy.deepcopy(self.store.rows.get(uid)))
        return msg

    async def test_happy_flow_requires_two_steps_and_uses_actual_sender(self):
        msg = await self.begin()
        self.assertIn("013245", msg.answers[0][0])
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))
        await self.contact()
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))
        call = callback("kbweb:confirm:" + TOKEN)
        await self.handlers["button"](call)
        payload = self.client.calls[-1][1]
        self.assertEqual(payload["telegram_user_id"], 42)
        self.assertEqual(payload["contact_user_id"], 42)
        self.assertEqual(payload["phone"], "+998901234567")
        self.assertNotIn(42, self.store.rows)
        self.assertIn("Tasdiqlandi", call.message.answers[-1][0])

    async def test_foreign_contact_cannot_approve(self):
        await self.begin()
        msg = await self.contact(owner=777)
        self.assertEqual(self.store.rows[42]["phase"], "contact")
        await self.handlers["button"](callback("kbweb:confirm:" + TOKEN))
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))
        self.assertIn("O'Z", msg.answers[-1][0])

    async def test_callback_other_chat_cannot_take_over(self):
        await self.begin(); await self.contact()
        call = callback("kbweb:confirm:" + TOKEN, uid=777)
        await self.handlers["button"](call)
        self.assertTrue(call.answers[-1][1].get("show_alert"))
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))

    async def test_replaced_challenge_and_expired_state_rejected(self):
        await self.begin(); await self.contact(); await self.begin(SECOND)
        await self.handlers["button"](callback("kbweb:confirm:" + TOKEN))
        self.assertEqual(self.store.rows[42]["challenge"], SECOND)
        self.store.rows.clear()
        await self.handlers["button"](callback("kbweb:confirm:" + SECOND))
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))

    async def test_cancel_prevents_later_approval(self):
        await self.begin(); await self.contact()
        await self.handlers["button"](callback("kbweb:cancel:" + TOKEN))
        await self.handlers["button"](callback("kbweb:confirm:" + TOKEN))
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))

    async def test_duplicate_clicks_send_only_one_confirm(self):
        await self.begin(); await self.contact()
        self.client.confirm_event = asyncio.Event()
        first = asyncio.create_task(self.handlers["button"](callback("kbweb:confirm:" + TOKEN)))
        await asyncio.sleep(0)
        await self.handlers["button"](callback("kbweb:confirm:" + TOKEN))
        self.client.confirm_event.set()
        await first
        self.assertEqual(sum(op == "confirm" for op, _ in self.client.calls), 1)

    async def test_timeout_allows_retry_but_does_not_claim_success(self):
        await self.begin(); await self.contact()
        self.client.fail_status = 503
        call = callback("kbweb:confirm:" + TOKEN)
        await self.handlers["button"](call)
        self.assertEqual(self.store.rows[42]["phase"], "approval")
        self.assertNotIn("✅ Tasdiqlandi", call.message.answers[-1][0])
        self.client.fail_status = None
        await self.handlers["button"](call)
        self.assertIn("✅ Tasdiqlandi", call.message.answers[-1][0])

    async def test_foreign_site_inspection_denied(self):
        self.client.site = "https://attacker.example"
        await self.begin()
        self.assertFalse(self.store.rows)

    async def test_equivalent_canonical_site_is_accepted(self):
        self.client.site = "https://TalimKabutar.uz:443/"
        await self.begin()
        self.assertIn(42, self.store.rows)

    async def test_www_origin_works_only_when_explicitly_allowed(self):
        self.client.site = "https://www.talimkabutar.uz"
        await self.begin()
        self.assertFalse(self.store.rows)
        settings = Settings(SETTINGS.api, SETTINGS.secret, SETTINGS.database, SETTINGS.site,
                            "https://www.talimkabutar.uz")
        dp = NS(message=FakeObserver(), callback_query=FakeObserver())
        self.handlers = install_kabutar_auth(dp, settings, self.store, self.client)
        msg = await self.begin()
        self.assertIn(42, self.store.rows)
        self.assertIn("Sayt: https://www.talimkabutar.uz", msg.answers[-1][0])
        self.store.rows.clear()
        for origin in ("https://attacker.example", "https://www.talimkabutar.uz.attacker.example"):
            self.client.site = origin
            await self.begin()
            self.assertFalse(self.store.rows)
        entry = message("/sayt")
        await self.handlers["open_site"](entry)
        self.assertEqual(entry.answers[-1][1]["reply_markup"].inline_keyboard[0][0].url,
                         SETTINGS.site + "/#telegram")

    async def test_unconfigured_bot_explains_setup_without_consuming_challenge(self):
        dp = NS(message=FakeObserver(), callback_query=FakeObserver())
        with self.assertLogs("kabutar_web_auth", level="WARNING") as logs:
            handlers = install_kabutar_auth(dp, Settings("", "", "", SETTINGS.site), self.store, self.client)
        msg = message("/start kb_" + TOKEN)
        await handlers["begin"](msg)
        self.assertFalse(self.client.calls)
        self.assertFalse(self.store.rows)
        self.assertIn("to'liq sozlanmagan", msg.answers[-1][0])
        self.assertIn("KABUTAR_AUTH_API_URL", logs.output[0])

    async def test_old_cabinet_buttons_and_site_command_use_same_usable_entry(self):
        msg = message("/sayt")
        await self.handlers["open_site"](msg)
        expected = msg.answers[-1]
        self.assertIn("administrator bergan parol", expected[0])
        self.assertEqual(expected[1]["reply_markup"].inline_keyboard[0][0].url,
                         SETTINGS.site + "/#telegram")
        for data in ("kb_veb_kod", "kb_sayt_ulash"):
            call = callback(data)
            await self.handlers["old_link"](call)
            self.assertEqual(call.message.answers[-1][0], expected[0])
        self.assertFalse(self.client.calls)

    async def test_site_entry_callback_rejects_other_private_chat(self):
        call = callback("kb_sayt_ulash", uid=9, chat_id=42)
        await self.handlers["old_link"](call)
        self.assertTrue(call.answers[-1][1]["show_alert"])
        self.assertFalse(call.message.answers)

    async def test_pending_contact_survives_handler_reinstallation(self):
        await self.begin()
        other_dp = NS(message=FakeObserver(), callback_query=FakeObserver())
        handlers = install_kabutar_auth(other_dp, SETTINGS, self.store, self.client)
        msg = message(contact=NS(user_id=42, phone_number="+998901234567"))
        await handlers["contact"](msg, copy.deepcopy(self.store.rows[42]))
        self.assertEqual(self.store.rows[42]["phase"], "approval")

    async def test_normal_menu_clears_persistent_pending_flow(self):
        await self.begin()
        await self.handlers["clear_pending"](42)
        self.assertNotIn(42, self.store.rows)
        await self.handlers["button"](callback("kbweb:confirm:" + TOKEN))
        self.assertFalse(any(op == "confirm" for op, _ in self.client.calls))

    async def test_general_start_not_captured_and_legacy_callback_is_scoped(self):
        _, filters = self.dp.message.handlers[0]
        self.assertFalse(filters[0](message("/start")))
        self.assertFalse(filters[0](message("Matematika")))
        _, filters = self.dp.callback_query.handlers[-1]
        self.assertTrue(filters[0](NS(data="kb_sayt_ulash")))
        self.assertFalse(filters[0](NS(data="parent_link")))


if __name__ == "__main__":
    unittest.main()
