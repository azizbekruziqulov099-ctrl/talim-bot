import copy
import unittest
from types import SimpleNamespace as NS
import test_kabutar_web_auth as fixture
from kabutar_web_auth import install_kabutar_auth

class CodeClient(fixture.FakeClient):
    async def post(self, op, payload):
        result = await super().post(op,payload)
        if op == 'inspect': result['delivery']='code'
        elif op == 'code/issue': result.update(code='004281',role=payload.get('role'))
        return result

class BotCodeTests(unittest.IsolatedAsyncioTestCase):
    begin=fixture.FlowTests.begin
    contact=fixture.FlowTests.contact
    async def asyncSetUp(self):
        fixture.fake_aiogram()
        self.store,self.client=fixture.MemoryStore(),CodeClient()
        self.dp=NS(message=fixture.FakeObserver(),callback_query=fixture.FakeObserver())
        self.handlers=install_kabutar_auth(self.dp,fixture.SETTINGS,self.store,self.client)
    async def test_contact_shows_four_roles_and_selection_sends_code(self):
        await self.begin(); msg=await self.contact()
        challenge=self.store.rows[42]['challenge']
        self.assertNotEqual(challenge,fixture.TOKEN)
        buttons=msg.answers[-1][1]['reply_markup'].inline_keyboard
        actions=[row[0].callback_data for row in buttons]
        for role in ('oquvchi','talaba','oqituvchi','ota-ona'):
            self.assertIn(f'kbweb:role_{role}:{challenge}',actions)
        call=fixture.callback('kbweb:role_talaba:'+self.store.rows[42]['challenge'])
        await self.handlers['button'](call)
        self.assertEqual(self.client.calls[-1][1]['role'],'talaba')
        self.assertEqual(self.client.calls[-1][1]['telegram_user_id'],42)
        self.assertIn('<code>004281</code>',call.message.answers[0][0])
        self.assertNotIn(42,self.store.rows)
    async def test_role_click_without_contact_cannot_issue_code(self):
        await self.begin()
        await self.handlers['button'](fixture.callback('kbweb:role_talaba:'+self.store.rows[42]['challenge']))
        self.assertFalse(any(op=='code/issue' for op,_ in self.client.calls))
    async def test_role_callback_in_another_chat_is_denied(self):
        await self.begin();await self.contact()
        call=fixture.callback('kbweb:role_oqituvchi:'+self.store.rows[42]['challenge'],uid=777)
        await self.handlers['button'](call)
        self.assertTrue(call.answers[-1][1]['show_alert'])
        self.assertFalse(any(op=='code/issue' for op,_ in self.client.calls))
    async def test_code_delivery_failure_retains_retryable_request(self):
        await self.begin();await self.contact()
        call=fixture.callback('kbweb:role_oquvchi:'+self.store.rows[42]['challenge'])
        original=call.message.answer
        async def fail_code(text,**kwargs):
            if '<code>' in text: raise RuntimeError('Telegram unavailable')
            await original(text,**kwargs)
        call.message.answer=fail_code
        await self.handlers['button'](call)
        self.assertFalse(self.store.rows[42]['busy'])
        retry=fixture.callback('kbweb:role_oquvchi:'+self.store.rows[42]['challenge'])
        await self.handlers['button'](retry)
        self.assertIn('004281',retry.message.answers[0][0])
        self.assertNotIn(42,self.store.rows)
    async def test_persistent_pending_survives_handler_restart(self):
        await self.begin();await self.contact()
        restarted=install_kabutar_auth(self.dp,fixture.SETTINGS,self.store,self.client)
        call=fixture.callback('kbweb:role_ota-ona:'+self.store.rows[42]['challenge'])
        await restarted['button'](call)
        self.assertEqual(self.client.calls[-1][1]['role'],'ota-ona')
        self.assertIn('004281',call.message.answers[0][0])

if __name__=='__main__':unittest.main()
