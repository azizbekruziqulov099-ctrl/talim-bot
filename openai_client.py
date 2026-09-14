"""Lazy, opt-in OpenAI clients; importing the bot requires no OpenAI key.

Keep the existing ``client.chat.completions.create(...)`` interface. Check the
paid-service setting at the final call, even if a caller retained a method.
"""
import importlib
import os
import threading

from paid_ai_policy import require_paid_ai


class _ClientOwner:
    def __init__(self, asynchronous=False):
        self.asynchronous = asynchronous
        self.instance = None
        self.lock = threading.Lock()

    def get(self):
        require_paid_ai()
        if self.instance is None:
            with self.lock:
                if self.instance is None:
                    key = os.getenv("OPENAI_API_KEY", "").strip()
                    if not key:
                        raise RuntimeError("OPENAI_API_KEY serverda sozlanmagan.")
                    sdk = importlib.import_module("openai")
                    factory = sdk.AsyncOpenAI if self.asynchronous else sdk.OpenAI
                    self.instance = factory(api_key=key)
        return self.instance


class _GuardedPath:
    def __init__(self, owner, path=()):
        self._owner = owner
        self._path = path

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return _GuardedPath(self._owner, self._path + (name,))

    def __call__(self, *args, **kwargs):
        target = self._owner.get()
        for name in self._path:
            target = getattr(target, name)
        return target(*args, **kwargs)


client = _GuardedPath(_ClientOwner())
async_client = _GuardedPath(_ClientOwner(asynchronous=True))
