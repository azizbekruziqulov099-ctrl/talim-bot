"""shared.py — Barcha handlerlarga umumiy import va o'zgaruvchilar"""
import os, psycopg2, asyncio, re
from aiogram import Router
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
)
from storage import user_state, admin_state, temp_user, test_sessions

DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMINS = list(map(int, os.getenv("ADMINS", "0").split(",")))

# DB pool
try:
    from db_pool import db as _pool_db, release as _pool_release
    def _get_db_conn():
        try: return _pool_db()
        except: return psycopg2.connect(DATABASE_URL)
except:
    def _get_db_conn(): return psycopg2.connect(DATABASE_URL)

def render_text(t):
    if not t: return ""
    t = str(t)
    import re as _re
    t = _re.sub(r'\b(\d+)\.0\b', r'\1', t)
    t = _re.sub(r'\[uz\](.*?)\[/uz\]', r'\1', t, flags=_re.DOTALL)
    t = _re.sub(r'\[en\](.*?)\[/en\]', r'_\1_', t, flags=_re.DOTALL)
    t = _re.sub(r'\[ru\](.*?)\[/ru\]', r'\1', t, flags=_re.DOTALL)
    return t.strip()
