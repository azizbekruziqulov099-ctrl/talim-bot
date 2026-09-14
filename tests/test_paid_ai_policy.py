"""Offline regression checks: configured keys never opt into paid calls.

Provider transports and unavailable DB/Telegram dependencies are replaced by
local doubles. The exercised provider functions are the real bot modules.
"""
import ast
import asyncio
import importlib.util
import io
import os
from pathlib import Path
import sys
import types
import unittest
import aiohttp
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paid_ai_policy as policy


def module(name):
    pg = types.ModuleType("psycopg2")
    pg.connect = Mock(name="database_connection")
    telegram = types.ModuleType("aiogram.types")
    telegram.InlineKeyboardMarkup = Mock()
    telegram.InlineKeyboardButton = Mock()
    audio = types.ModuleType("pydub")
    audio.AudioSegment = Mock()
    replacements = {"psycopg2": pg, "aiogram.types": telegram,
                    "edge_tts": types.ModuleType("edge_tts"), "pydub": audio}
    spec = importlib.util.spec_from_file_location("paid_checks_" + name, ROOT / (name + ".py"))
    loaded = importlib.util.module_from_spec(spec)
    # Test credentials are inert placeholders, never sent to a live service.
    with patch.dict(sys.modules, replacements), patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-only-openai", "TOGETHER_API_KEY": "test-only-together",
        "GEMINI_API_KEY": "", "ALLOW_PAID_AI": "false",
    }):
        spec.loader.exec_module(loaded)
    return loaded


class FakeResponse:
    status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return {
            "choices": [{"message": {"content": "A clear educational answer."}}],
            "candidates": [{"content": {"parts": [{"text": "Gemini explanation."}]}}],
            "data": [{"b64_json": "cGljdHVyZQ==", "url": "https://example.invalid/image"}],
        }

    async def read(self):
        return b"picture"


class FakeSession:
    def __init__(self):
        self.urls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse()

    def get(self, url, **kwargs):
        self.urls.append(url)
        return FakeResponse()


class PaidAIConfigurationTests(unittest.TestCase):
    def test_absent_or_invalid_setting_stays_disabled_even_with_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}, clear=True):
            self.assertFalse(policy.paid_ai_enabled())
            for value in ("", "false", "0", "no", "off", "enabled", "yesplease", "1", "yes", "on"):
                os.environ["ALLOW_PAID_AI"] = value
                self.assertFalse(policy.paid_ai_enabled(), value)

    def test_explicit_true_settings(self):
        for value in ("true", " TRUE "):
            with self.subTest(value=value), patch.dict(os.environ, {"ALLOW_PAID_AI": value}):
                self.assertTrue(policy.paid_ai_enabled())

    def test_client_import_and_disabled_calls_do_not_load_sdk(self):
        for value in (None, "false", "1", "yes", "on"):
            with self.subTest(setting=value), patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}, clear=True):
                if value is not None:
                    os.environ["ALLOW_PAID_AI"] = value
                client_module = module("openai_client")
                with patch.object(client_module.importlib, "import_module") as factory:
                    for call in (client_module.client.chat.completions.create,
                                 client_module.client.images.generate,
                                 client_module.async_client.chat.completions.create):
                        with self.assertRaises(policy.PaidAIDisabledError):
                            call(model="test")
                    factory.assert_not_called()

    def test_explicitly_enabled_sync_client_and_retained_method_recheck_gate(self):
        clients = module("openai_client")
        create = Mock(return_value="response")
        generate = Mock(return_value="image")
        sdk = types.SimpleNamespace(OpenAI=Mock(return_value=types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)),
            images=types.SimpleNamespace(generate=generate))))
        retained = clients.client.chat.completions.create
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "true", "OPENAI_API_KEY": "test-only"}), \
                patch.object(clients.importlib, "import_module", return_value=sdk):
            self.assertEqual(retained(model="test"), "response")
            self.assertEqual(clients.client.images.generate(model="test"), "image")
            sdk.OpenAI.assert_called_once()
            os.environ["ALLOW_PAID_AI"] = "false"
            with self.assertRaises(policy.PaidAIDisabledError):
                retained(model="test")
            create.assert_called_once()

    def test_missing_key_when_enabled_reports_safe_configuration_error(self):
        clients = module("openai_client")
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "true", "OPENAI_API_KEY": ""}), \
                patch.object(clients.importlib, "import_module") as factory:
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                clients.client.chat.completions.create(model="test")
            factory.assert_not_called()


class PaidAIProviderTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.brain = module("brain")
        cls.auto = module("auto_trainer")
        cls.pedagog = module("pedagog_trainer")
        cls.images = module("rasim_generator")
        cls.latex = module("latex_utils")
        cls.generator = module("ai_generatori")

    async def test_all_direct_paid_wrappers_skip_transport_by_default(self):
        calls = [(self.brain.ask_ai_and_save, ("savol",), ""),
                 (self.auto.ask_gpt, ("savol",), ""),
                 (self.pedagog.ask_gpt, ("savol",), None),
                 (self.images._openai_prompt, ("rasm",), None),
                 (self.images.generate_together_flux, ("rasm",), None),
                 (self.images.generate_dalle, ("rasm",), None)]
        for value in (None, "false", "1", "yes", "on"):
            with self.subTest(setting=value), patch.dict(os.environ, {}, clear=True), \
                    patch("aiohttp.ClientSession") as session:
                if value is not None:
                    os.environ["ALLOW_PAID_AI"] = value
                for function, args, expected in calls:
                    with self.subTest(function=function.__qualname__):
                        self.assertEqual(await function(*args), expected)
                session.assert_not_called()

    async def test_explicit_enable_reaches_paid_transports_and_preserves_results(self):
        calls = [(self.auto.ask_gpt, "A clear educational answer."),
                 (self.pedagog.ask_gpt, "A clear educational answer."),
                 (self.images._openai_prompt, "A clear educational answer."),
                 (self.images.generate_together_flux, b"picture"),
                 (self.images.generate_dalle, b"picture")]
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "true"}):
            for function, expected in calls:
                session = FakeSession()
                with self.subTest(function=function.__name__), \
                        patch("aiohttp.ClientSession", return_value=session), redirect_stdout(io.StringIO()):
                    self.assertEqual(await function("test prompt"), expected)
                    self.assertTrue(session.urls)
                    self.assertTrue(any("api.openai.com" in url or "api.together.xyz" in url
                                        for url in session.urls))

    async def test_gemini_can_respond_without_paid_fallback(self):
        session = FakeSession()
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.object(self.brain, "GEMINI_KEY", "test-only-gemini"), \
                patch("aiohttp.ClientSession", return_value=session):
            self.assertEqual(await self.brain.ask_ai_and_save("test"), "Gemini explanation.")
        self.assertEqual(len(session.urls), 1)
        self.assertIn("generativelanguage.googleapis.com", session.urls[0])

    async def test_paid_brain_fallback_is_available_only_after_opt_in(self):
        session = FakeSession()
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "true"}), \
                patch("aiohttp.ClientSession", return_value=session):
            self.assertEqual(await self.brain.ask_ai_and_save("test"), "A clear educational answer.")
        self.assertEqual(session.urls, ["https://api.openai.com/v1/chat/completions"])

    async def test_trainers_keep_gemini_result_without_second_paid_request(self):
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}):
            for trainer in (self.auto, self.pedagog):
                with self.subTest(trainer=trainer.__name__), \
                        patch.object(trainer, "ask_gemini", AsyncMock(return_value="A complete Gemini teaching answer.")), \
                        patch("aiohttp.ClientSession") as session:
                    answer, source = await trainer.ask_best("test")
                    self.assertEqual(source, "gemini")
                    self.assertEqual(answer, "A complete Gemini teaching answer.")
                    session.assert_not_called()

    async def test_failed_free_images_never_trigger_paid_network(self):
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.object(self.images, "_gemini_prompt", AsyncMock(return_value=None)), \
                patch.object(self.images, "generate_cf_flux_ex", AsyncMock(return_value=(None, "limit"))), \
                patch.object(self.images, "generate_pollinations", AsyncMock(return_value=None)), \
                patch("aiohttp.ClientSession") as session, redirect_stdout(io.StringIO()):
            for admin in (False, True):
                image, prompt = await self.images.generate_smart("uchta olma", is_admin=admin)
                self.assertIsNone(image)
                self.assertIn("uchta olma", prompt)
            session.assert_not_called()

    async def test_latex_uses_local_reading_when_paid_disabled(self):
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.object(self.latex, "client") as client:
            self.assertEqual(await self.latex.latex_to_uzbek("[latex]x^2[/latex]"), "x kvadrat")
            client.chat.completions.create.assert_not_called()

    async def test_async_sdk_call_is_lazy_and_works_after_explicit_enable(self):
        clients = module("openai_client")
        create = AsyncMock(return_value="async response")
        sdk = types.SimpleNamespace(AsyncOpenAI=Mock(return_value=types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))))
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "true", "OPENAI_API_KEY": "test-only"}), \
                patch.object(clients.importlib, "import_module", return_value=sdk):
            self.assertEqual(await clients.async_client.chat.completions.create(model="test"), "async response")
            create.assert_awaited_once()

    async def test_question_generation_fails_before_sdk_or_pedagogy_work(self):
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.object(self.generator, "client") as client:
            with self.assertRaises(policy.PaidAIDisabledError):
                await self.generator._generate_questions("5", "Matematika", "Kasr", "Kasr", "test")
            client.chat.completions.create.assert_not_called()

    async def test_bot_generator_reports_disabled_before_database_work(self):
        call = types.SimpleNamespace(data="gen_run", answer=AsyncMock(),
                                     message=types.SimpleNamespace(answer=AsyncMock()))
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.dict(self.generator.gen_state, {42: {"selected": ["topic"]}}), \
                patch.object(self.generator, "db") as database:
            await self.generator.run_generator(call, 42)
            database.assert_not_called()
            self.assertIn(policy.DISABLED_MESSAGE, call.message.answer.await_args.args[0])

    async def test_manual_template_is_not_blocked_by_paid_gate(self):
        call = types.SimpleNamespace(data="gen_template", answer=AsyncMock(),
                                     message=types.SimpleNamespace(answer=AsyncMock()))
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), \
                patch.dict(self.generator.gen_state, {42: {"selected": ["topic"]}}), \
                patch.object(self.generator, "_generate_template", AsyncMock()) as generate:
            await self.generator.run_generator(call, 42)
            generate.assert_awaited_once()

    async def test_cli_generator_does_not_prompt_or_advance_topics_when_disabled(self):
        tree = ast.parse((ROOT / "test_generator.py").read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "generate_tests")
        namespace = {"paid_ai_enabled": policy.paid_ai_enabled,
                     "DISABLED_MESSAGE": policy.DISABLED_MESSAGE,
                     "input": Mock(), "get_next_topic": Mock(), "increase_count": Mock()}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "test_generator.py", "exec"), namespace)
        with patch.dict(os.environ, {"ALLOW_PAID_AI": "false"}), redirect_stdout(io.StringIO()):
            namespace["generate_tests"]()
        for name in ("input", "get_next_topic", "increase_count"):
            namespace[name].assert_not_called()


if __name__ == "__main__":
    unittest.main()
