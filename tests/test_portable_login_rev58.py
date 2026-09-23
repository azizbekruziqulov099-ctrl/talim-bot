import copy
import inspect
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS
from urllib.parse import parse_qs,urlsplit
import test_kabutar_web_auth as fixture
from kabutar_web_auth import AuthError, ensure_kabutar_auth, install_kabutar_auth

class CodeClient(fixture.FakeClient):
    async def post(self,operation,payload):
        result = await super().post(operation,payload)
        if operation == 'code/issue':
            result.update(code='004281',role=payload['role'],phone=payload['phone'],purpose=payload.get('purpose','login'),expires_in=300)
        return result

class PortableBotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture.fake_aiogram()
        self.store,self.client = fixture.MemoryStore(),CodeClient()
        self.dp=NS(message=fixture.FakeObserver(),callback_query=fixture.FakeObserver())
        self.handlers=install_kabutar_auth(self.dp,fixture.SETTINGS,self.store,self.client)

    async def contact(self):
        msg=fixture.message(contact=NS(user_id=42,phone_number= '+998901234567'))
        await self.handlers['contact'](msg,copy.deepcopy(self.store.rows[42]))
        return msg

    async def start(self,text='/sayt'):
        msg=fixture.message(text)
        if text.startswith('/start kb_'): await self.handlers['begin'](msg)
        else: await self.handlers['open_site'](msg)
        return msg

    async def test_new_user_no_website_visit_gets_code(self):
        entry=await self.start()
        self.assertTrue(entry.answers[-1][1]['reply_markup'].keyboard[0][0].request_contact)
        self.assertEqual(self.store.rows[42]['delivery'],'portable')
        self.assertFalse(self.client.calls)
        msg=await self.contact(); challenge=self.store.rows[42]['challenge']
        for role in ('oquvchi','talaba','oqituvchi','ota-ona'):
            self.assertTrue(any(button.callback_data==f'kbweb:role_{role}:{challenge}'
                for row in msg.answers[-1][1]['reply_markup'].inline_keyboard for button in row))
        call=fixture.callback('kbweb:role_talaba:'+challenge)
        await self.handlers['button'](call)
        self.assertEqual(self.client.calls[-1][0],'code/issue')
        self.assertIn('<code>004281</code>',call.message.answers[0][0])
        self.assertNotIn(42,self.store.rows)

    async def test_deep_link_and_plain_start_enter_same_flow_before_general_handler(self):
        await self.start('/start kb_login')
        challenge=self.store.rows[42]['challenge']
        _,filters=self.dp.message.handlers[1]
        self.assertTrue(filters[0](fixture.message('/start')))
        self.assertFalse(filters[0](fixture.message('/menu')))
        self.assertFalse(filters[0](fixture.message('/start other_bot_feature')))
        await self.start('/start')
        self.assertEqual(self.store.rows[42]['challenge'],challenge)

    async def test_restart_and_repeated_start_keep_verified_contact(self):
        await self.start(); await self.contact()
        challenge=self.store.rows[42]['challenge']
        restarted=install_kabutar_auth(self.dp,fixture.SETTINGS,self.store,self.client)
        msg=fixture.message('/start'); await restarted['open_site'](msg)
        self.assertEqual(self.store.rows[42]['challenge'],challenge)
        self.assertEqual(self.store.rows[42]['phone'],'+998901234567')
        self.assertIn('qaysi rolda',msg.answers[-1][0])

    async def test_old_browser_request_replaced_when_new_login_entry_clicked(self):
        self.store.rows[42]=dict(challenge=fixture.TOKEN,phone=None,busy=False,delivery='code')
        await self.start('/start kb_login')
        self.assertEqual(self.store.rows[42]['delivery'],'portable')
        self.assertNotEqual(self.store.rows[42]['challenge'],fixture.TOKEN)

    async def test_old_cabinet_button_starts_code_flow_instead_of_returning_to_site(self):
        for action in ('kb_veb_kod','kb_sayt_ulash'):
            self.store.rows.clear(); call=fixture.callback(action)
            await self.handlers['old_link'](call)
            self.assertEqual(self.store.rows[42]['delivery'],'portable')
            self.assertTrue(call.message.answers[-1][1]['reply_markup'].keyboard[0][0].request_contact)

    async def test_google_option_delivers_code_and_google_continuation_without_secret_in_url(self):
        await self.start(); await self.contact()
        call=fixture.callback('kbweb:role_google:'+self.store.rows[42]['challenge'])
        await self.handlers['button'](call)
        self.assertIn('<code>004281</code>',call.message.answers[0][0])
        url=call.message.answers[-1][1]['reply_markup'].inline_keyboard[0][0].url
        params=parse_qs(urlsplit(url).fragment)
        self.assertEqual(params,{'telegram_phone':['+998901234567'],'telegram_link':['1']})
        self.assertNotIn('004281',url)
        self.assertEqual(self.client.calls[-1][1]['purpose'], 'link')

    async def test_old_login_deep_link_gets_new_portable_code_instead_of_browser_approval(self):
        await self.start('/start kb_' + fixture.TOKEN)
        pending=self.store.rows[42]
        self.assertEqual(pending['delivery'],'portable')
        self.assertNotEqual(pending['challenge'],fixture.TOKEN)
        await self.contact()
        call=fixture.callback('kbweb:role_talaba:'+pending['challenge'])
        await self.handlers['button'](call)
        self.assertEqual(self.client.calls[-1][0],'code/issue')
        self.assertIn('<code>004281</code>',call.message.answers[0][0])

    async def test_expired_link_restarts_in_bot_without_sending_user_back_to_site(self):
        original=self.client.post
        async def expired(operation,payload):
            if operation=='inspect':raise AuthError(410)
            return await original(operation,payload)
        self.client.post=expired
        entry=await self.start('/start kb_' + fixture.TOKEN)
        self.assertEqual(self.store.rows[42]['delivery'],'portable')
        self.assertTrue(entry.answers[-1][1]['reply_markup'].keyboard[0][0].request_contact)

    async def test_site_command_replaces_stuck_request_with_a_fresh_challenge(self):
        await self.start(); await self.contact()
        old=self.store.rows[42]['challenge']
        await self.start('/sayt')
        self.assertNotEqual(self.store.rows[42]['challenge'],old)
        self.assertEqual(self.store.rows[42]['phase'],'contact')

    async def test_older_backend_must_not_issue_a_normal_login_code_for_gmail_choice(self):
        await self.start(); await self.contact()
        original=self.client.post
        async def old_backend(operation,payload):
            result=await original(operation,payload);result.pop('purpose',None);return result
        self.client.post=old_backend
        call=fixture.callback('kbweb:role_google:'+self.store.rows[42]['challenge'])
        await self.handlers['button'](call)
        self.assertFalse(any('<code>004281</code>' in text for text,_ in call.message.answers))
        self.assertIn('Backend',call.message.answers[-1][0])
        self.assertFalse(self.store.rows[42]['busy'])

    async def test_dispatcher_routes_start_contact_and_role_before_general_handlers(self):
        async def unwanted(_): self.fail('General bot handler intercepted web login')
        self.dp.message.register(unwanted,lambda _:True)
        self.dp.callback_query.register(unwanted,lambda _:True)
        async def dispatch(observer,event):
            for handler,filters in observer.handlers:
                kwargs={}
                for condition in filters:
                    result=condition(event)
                    if inspect.isawaitable(result):result=await result
                    if not result:break
                    if isinstance(result,dict):kwargs.update(result)
                else:
                    await handler(event,**kwargs);return
            self.fail('No handler')
        await dispatch(self.dp.message,fixture.message('/start kb_login'))
        await dispatch(self.dp.message,fixture.message(contact=NS(user_id=42,phone_number='+998901234567')))
        call=fixture.callback('kbweb:role_talaba:'+self.store.rows[42]['challenge'])
        await dispatch(self.dp.callback_query,call)
        self.assertIn('<code>004281</code>',call.message.answers[0][0])

    async def test_registration_is_idempotent_and_old_cabinet_fallback_uses_code_flow(self):
        count=len(self.dp.message.handlers)
        self.assertIs(ensure_kabutar_auth(self.dp),self.handlers)
        self.assertEqual(len(self.dp.message.handlers),count)
        with patch.object(sys.modules['aiogram.types'],'BufferedInputFile',NS,create=True), patch.dict(sys.modules,{'loader':NS(dp=self.dp),'psycopg2':NS()}):
            import cb_kabinet
            call=fixture.callback('kb_sayt_ulash');state={42:'old-state'}
            self.assertTrue(await cb_kabinet.handle_kb(call,42,{},state,{},None))
        self.assertNotIn(42,state)
        self.assertEqual(self.store.rows[42]['delivery'],'portable')
        self.assertTrue(call.message.answers[-1][1]['reply_markup'].keyboard[0][0].request_contact)

    async def test_code_delivery_error_is_retryable(self):
        await self.start(); await self.contact()
        challenge=self.store.rows[42]['challenge']
        self.client.fail_status=503
        await self.handlers['button'](fixture.callback('kbweb:role_talaba:'+challenge))
        self.assertFalse(self.store.rows[42]['busy'])
        self.client.fail_status=None
        retry=fixture.callback('kbweb:role_talaba:'+challenge)
        await self.handlers['button'](retry)
        self.assertIn('004281',retry.message.answers[0][0])

    async def test_wrong_contact_or_other_user_cannot_get_code(self):
        await self.start()
        wrong=fixture.message(contact=NS(user_id=888,phone_number='+998991234567'))
        await self.handlers['contact'](wrong,copy.deepcopy(self.store.rows[42]))
        self.assertIsNone(self.store.rows[42]['phone'])
        await self.handlers['button'](fixture.callback('kbweb:role_talaba:'+self.store.rows[42]['challenge'],uid=999))
        self.assertFalse(self.client.calls)

if __name__ == '__main__': unittest.main()
