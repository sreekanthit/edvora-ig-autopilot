import sqlite3
from .settings import DB
SCHEMA = """
CREATE TABLE IF NOT EXISTS media(media_id TEXT PRIMARY KEY, kind TEXT, posted_at TEXT, caption TEXT, permalink TEXT);
CREATE TABLE IF NOT EXISTS metrics(media_id TEXT, fetched_at TEXT, name TEXT, value REAL);
CREATE TABLE IF NOT EXISTS followers(day TEXT PRIMARY KEY, followers INTEGER, media_count INTEGER);
"""
def conn(path=None):
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path or DB); c.executescript(SCHEMA); return c
