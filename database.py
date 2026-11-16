import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On a host, point DB_PATH at a persistent disk (e.g. /data/trendthread.db)
DATABASE = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "trendthread.db"))


def get_connection():
    conn = sqlite3.connect(DATABASE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            searched_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS saved_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            trend_data TEXT NOT NULL,
            saved_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS geo_scores (
            geo TEXT NOT NULL,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            score REAL NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (geo, category, name));
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT);
        """)


def _rows(sql, args=()):
    with get_connection() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


# ---- history / saved ----
def add_history(category):
    with get_connection() as c:
        c.execute("INSERT INTO history (category) VALUES (?)", (category,))


def get_history(limit=50):
    return _rows("SELECT id, category, searched_at FROM history ORDER BY id DESC LIMIT ?", (limit,))


def save_trend(category, trend_data):
    with get_connection() as c:
        c.execute("INSERT INTO saved_trends (category, trend_data) VALUES (?, ?)", (category, trend_data))


def get_saved_trends():
    return _rows("SELECT id, category, trend_data, saved_at FROM saved_trends ORDER BY id DESC")


# ---- cached scores (per region/geo) ----
def upsert_scores(geo, category, scores):
    with get_connection() as c:
        c.executemany(
            """INSERT INTO geo_scores (geo, category, name, score, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(geo, category, name) DO UPDATE SET
               score = excluded.score, updated_at = CURRENT_TIMESTAMP""",
            [(geo, category, n, float(s)) for n, s in scores.items()],
        )


def get_scores(geo, category):
    return _rows("SELECT name, score FROM geo_scores WHERE geo = ? AND category = ? "
                 "ORDER BY score DESC", (geo, category))


def last_updated(category):
    rows = _rows("SELECT MAX(updated_at) AS t FROM geo_scores WHERE category = ?", (category,))
    return rows[0]["t"] if rows else None


def fresh_names(geo, category, hours):
    """Names whose score was stored within the last `hours` hours."""
    rows = _rows("SELECT name FROM geo_scores WHERE geo = ? AND category = ? "
                 "AND updated_at > datetime('now', ?)", (geo, category, f"-{hours} hours"))
    return {r["name"] for r in rows}


# ---- meta (refresh state) ----
def set_meta(key, value):
    with get_connection() as c:
        c.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


def get_meta(key, default=None):
    rows = _rows("SELECT value FROM meta WHERE key = ?", (key,))
    return rows[0]["value"] if rows else default
