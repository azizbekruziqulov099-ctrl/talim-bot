"""
db_pool.py — Connection pooling va cache
1M foydalanuvchi uchun optimallashtirilgan
"""
import os, psycopg2
from psycopg2 import pool
from functools import lru_cache
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL","")

# Connection pool — 5 dan 20 gacha ulanish
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = pool.ThreadedConnectionPool(
                minconn=5, maxconn=20,
                dsn=DATABASE_URL
            )
        except Exception as e:
            print(f"Pool error: {e}")
    return _pool

def db():
    """Pool dan ulanish olish."""
    p = get_pool()
    if p:
        return p.getconn()
    return psycopg2.connect(DATABASE_URL)

def release(conn):
    """Ulanishni poolga qaytarish."""
    p = get_pool()
    if p and conn:
        try: p.putconn(conn)
        except: pass

# Cache — tez-tez o'zgarmaydigan ma'lumotlar
_cache = {}
_cache_ttl = {}

def cache_get(key: str):
    if key in _cache:
        if _cache_ttl.get(key, 0) > datetime.now().timestamp():
            return _cache[key]
        del _cache[key]
    return None

def cache_set(key: str, value, ttl: int = 300):
    """ttl = sekundlarda (default 5 daqiqa)."""
    _cache[key] = value
    _cache_ttl[key] = datetime.now().timestamp() + ttl

def cache_del(key: str):
    _cache.pop(key, None)
    _cache_ttl.pop(key, None)

def get_user_cached(user_id: int) -> dict | None:
    """Foydalanuvchi ma'lumotini cache dan olish."""
    key = f"user:{user_id}"
    cached = cache_get(key)
    if cached: return cached
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id,full_name,role,class FROM users WHERE user_id=%s",(user_id,))
        row = cur.fetchone(); cur.close()
        if row:
            data = {"id":row[0],"name":row[1],"role":row[2],"class":row[3]}
            cache_set(key, data, 600)  # 10 daqiqa
            return data
    except: pass
    finally: release(conn)
    return None

def invalidate_user(user_id: int):
    """Foydalanuvchi cache ni tozalash (ma'lumot o'zgarganda)."""
    cache_del(f"user:{user_id}")
