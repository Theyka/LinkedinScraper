import sqlite3
import os
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "profiles.db")

EXTRA_COLUMNS = [
    ("status", "TEXT DEFAULT 'pending'"),
    ("error", "TEXT"),
    ("photo_blob", "BLOB"),
    ("photo_content_type", "TEXT"),
]


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = sqlite3.connect(DB_PATH, autocommit=True)
        db.row_factory = sqlite3.Row
        g._database = db
    return db


def close_db(exc=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def _legacy_data_column_is_not_null(db):
    cols = db.execute("PRAGMA table_info(profiles)").fetchall()
    for c in cols:
        if c[1] == "data":
            return c[3] == 1
    return False


def _rebuild_profiles_table(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS profiles_new (
            url        TEXT PRIMARY KEY,
            data       TEXT,
            scraped_at INTEGER,
            status     TEXT DEFAULT 'pending',
            error      TEXT
        )
    """)
    db.execute("""
        INSERT OR IGNORE INTO profiles_new (url, data, scraped_at, status, error)
        SELECT url, data, scraped_at,
               COALESCE(status, CASE WHEN data IS NOT NULL THEN 'done' ELSE 'pending' END),
               error
        FROM profiles
    """)
    db.execute("DROP TABLE profiles")
    db.execute("ALTER TABLE profiles_new RENAME TO profiles")


def init_db():
    with sqlite3.connect(DB_PATH, autocommit=True) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                url        TEXT PRIMARY KEY,
                data       TEXT,
                scraped_at INTEGER,
                status     TEXT DEFAULT 'pending',
                error      TEXT
            )
        """)

        for col, defn in EXTRA_COLUMNS:
            try:
                db.execute(f"ALTER TABLE profiles ADD COLUMN {col} {defn}")
                if col == "status":
                    db.execute("UPDATE profiles SET status='done' WHERE data IS NOT NULL")
            except Exception:
                pass

        if _legacy_data_column_is_not_null(db):
            _rebuild_profiles_table(db)
