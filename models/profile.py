import json
import time
from models.db import get_db


SUMMARY_KEYS = ("name", "headline", "location", "open_to_work", "open_to_hiring")


def add_profile(url):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO profiles (url, status) VALUES (?, 'pending')",
        (url,),
    )
    db.commit()


def list_profiles():
    sql = (
        "SELECT url, data, scraped_at, status, error, "
        "(photo_blob IS NOT NULL) AS has_photo "
        "FROM profiles ORDER BY COALESCE(scraped_at, 0) DESC"
    )
    rows = get_db().execute(sql).fetchall()

    out = []
    for row in rows:
        item = {
            "url": row["url"],
            "scraped_at": row["scraped_at"],
            "status": row["status"],
            "error": row["error"],
            "name": "",
            "headline": "",
            "location": "",
            "has_photo": bool(row["has_photo"]),
            "open_to_work": False,
            "open_to_hiring": False,
        }

        if row["data"]:
            try:
                parsed = json.loads(row["data"])
            except Exception:
                parsed = {}
            for k in SUMMARY_KEYS:
                if k in parsed:
                    item[k] = parsed[k]

        out.append(item)

    return out


def get_full_profile(url):
    row = get_db().execute(
        "SELECT data, status, error, (photo_blob IS NOT NULL) AS has_photo "
        "FROM profiles WHERE url = ?",
        (url,),
    ).fetchone()

    if not row:
        return None

    if row["data"]:
        data = json.loads(row["data"])
        data["_status"] = row["status"]
        data["has_photo"] = bool(row["has_photo"])
        return data

    return {
        "_status": row["status"],
        "_error": row["error"],
        "has_photo": False,
    }


def get_photo_blob(url):
    row = get_db().execute(
        "SELECT photo_blob, photo_content_type FROM profiles WHERE url = ?",
        (url,),
    ).fetchone()
    if not row:
        return None, None
    if row["photo_blob"] is None:
        return None, None
    ctype = row["photo_content_type"] or "image/jpeg"
    return bytes(row["photo_blob"]), ctype


def reset_to_pending(url):
    db = get_db()
    db.execute(
        "UPDATE profiles SET status='pending', error=NULL WHERE url=?",
        (url,),
    )
    db.commit()


def delete_profile(url):
    db = get_db()
    db.execute("DELETE FROM profiles WHERE url = ?", (url,))
    db.commit()
