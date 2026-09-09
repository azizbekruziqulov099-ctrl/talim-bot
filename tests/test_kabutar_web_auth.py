"""Bot security/state contract tests; no Telegram token/network/database required."""
import asyncio
import copy
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kabutar_web_auth import (
    AuthError, CANCEL_TEXT, Settings, callback_parts, install_kabutar_auth,
    is_web_start, own_contact_phone, private_sender, safe_origin, start_challenge,
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
        self.assertEqual(safe_origin("http://api.railway.internal:8080", True), "http://api.railway.internal:8080")
        for invalid in ("javascript:bad", "http://example.com", "https://user:pass@host", "https://host/path", "https://host?next=evil", "https://host#bad"):
            with self.assertRaises(ValueError): safe_origin(invalid, True)
        self.assertEqual(callback_parts("kbweb:confirm:" + TOKEN), ("confirm", TOKEN))
        self.assertIsNone(callback_parts("kbweb:confirm:short"))


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
