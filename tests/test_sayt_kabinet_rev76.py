import unittest
from datetime import datetime
from types import SimpleNamespace as NS

import test_kabutar_web_auth as fixture
from kabutar_web_auth import install_kabutar_auth, is_cabinet_command
from sayt_kabinet import cabinet_rows, format_summary, site_link

SUMMARY = {"user_id": 7, "name": "Ali <b>", "role": "oquvchi", "class": "7", "kb": "KB-1001",
           "tests": {"count": 3, "average": 78, "attempts": 5,
                     "last": [{"topic_code": "T1", "score": 85, "learned_at": datetime(2026, 9, 27), "nom": "Kasrlar", "subject_name": "Matematika"}]}}


class TicketClient(fixture.FakeClient):
    async def post(self, operation, payload):
        self.calls.append((operation, payload))
        if operation == 'ticket':
            return {'ticket': 'T' * 32, 'expires_in': 900}
        return await super().post(operation, payload)


class CabinetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture.fake_aiogram()
        self.store, self.client = fixture.MemoryStore(), TicketClient()
        self.dp = NS(message=fixture.FakeObserver(), callback_query=fixture.FakeObserver())
        async def cabinet(telegram_id):
            return SUMMARY if telegram_id == 42 else None
        self.handlers = install_kabutar_auth(self.dp, fixture.SETTINGS, self.store, self.client, cabinet=cabinet)

    async def test_linked_user_start_shows_cabinet_with_one_tap_buttons(self):
        msg = fixture.message('/start')
        await self.handlers['open_site'](msg)
        text, kwargs = msg.answers[-1]
        self.assertIn('Ali &lt;b&gt;', text)
        self.assertIn('78%', text)
        self.assertIn('Kasrlar', text)
        rows = kwargs['reply_markup'].inline_keyboard
        urls = [getattr(b, 'url', None) for row in rows for b in row]
        self.assertTrue(any(u and '#tg_ticket=' in u and 'go=test' in u for u in urls))
        self.assertEqual(sum(1 for op, _ in self.client.calls if op == 'ticket'), 3)
        self.assertNotIn(42, self.store.rows)  # login oqimi boshlanmadi

    async def test_unlinked_user_gets_login_flow(self):
        msg = fixture.message('/start', uid=43)
        await self.handlers['open_site'](msg)
        self.assertTrue(msg.answers[-1][1]['reply_markup'].keyboard[0][0].request_contact)

    async def test_sayt_command_still_gives_code_flow(self):
        msg = fixture.message('/sayt')
        await self.handlers['open_site'](msg)
        self.assertIn(42, self.store.rows)


class PureTests(unittest.TestCase):
    def test_links_and_commands(self):
        self.assertEqual(site_link('https://talimkabutar.uz', 'abc', 'test'), 'https://talimkabutar.uz/#tg_ticket=abc&go=test')
        self.assertEqual(site_link('https://talimkabutar.uz/', None), 'https://talimkabutar.uz/')
        self.assertTrue(is_cabinet_command(NS(text='/kabinet')))
        self.assertTrue(is_cabinet_command(NS(text='/natijalar@bot')))
        self.assertFalse(is_cabinet_command(NS(text='/kabinet x')))

    def test_web_app_buttons_and_empty_results(self):
        rows = cabinet_rows('https://s.uz', {'test': 'x' * 24}, lambda **k: NS(**k), lambda **k: NS(**k))
        self.assertEqual(rows[0][0].web_app.url, 'https://s.uz/#tg_ticket=' + 'x' * 24 + '&go=test')
        self.assertEqual(rows[0][1].web_app.url, 'https://s.uz/')
        text = format_summary({"name": "Vali", "role": "talaba", "class": "2 kurs", "tests": {"count": 0}})
        self.assertIn('Talaba · 2 kurs', text)
        self.assertIn('Hali test ishlamagansiz', text)


if __name__ == '__main__':
    unittest.main()
