"""Explicit opt-in for the bot's OpenAI and Together API calls.

An API key alone never authorizes a paid fallback. This switch does not control
Gemini, Cloudflare, other providers, their account billing, or hosting costs.
"""
import os


DISABLED_MESSAGE = (
    "Pullik OpenAI/Together xizmati o‘chirilgan. "
    "API kaliti borligi bu xizmatni avtomatik yoqmaydi."
)


class PaidAIDisabledError(RuntimeError):
    """Safe message for callers that already report generation failures."""


def paid_ai_enabled():
    return os.getenv("ALLOW_PAID_AI", "false").strip().lower() == "true"


def require_paid_ai():
    if not paid_ai_enabled():
        raise PaidAIDisabledError(DISABLED_MESSAGE)
