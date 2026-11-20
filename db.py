import sqlite3, os
DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
  city TEXT, role TEXT, source TEXT, url TEXT, posted TEXT,
  description TEXT, first_seen TEXT, last_seen TEXT, tagged_by TEXT
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c

def set_meta(c, k, v):
    c.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))

def get_meta(k, default=None):
    with conn() as c:
        r = c.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default
