import threading
import sqlite3
import json
import time

from models.db import DB_PATH


def _session():
    from services.linkedin_session import get_session
    return get_session()


def _update_status(url, status, error=None):
    with sqlite3.connect(DB_PATH, autocommit=True) as db:
        db.execute(
            "UPDATE profiles SET status=?, error=? WHERE url=?",
            (status, error, url),
        )
        db.commit()


def _save_profile(url, data, photo_blob, photo_ctype):
    with sqlite3.connect(DB_PATH, autocommit=True) as db:
        db.execute(
            "UPDATE profiles SET data=?, scraped_at=?, status=?, error=NULL, "
            "photo_blob=?, photo_content_type=? WHERE url=?",
            (
                json.dumps(data, ensure_ascii=False),
                int(time.time()),
                "done",
                photo_blob,
                photo_ctype,
                url,
            ),
        )
        db.commit()


def _download_photo(session, photo_url):
    if not photo_url:
        return None, None
    try:
        r = session.get(photo_url, timeout=30)
    except Exception:
        return None, None
    if r.status_code != 200 or not r.content:
        return None, None
    ctype = (r.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    return r.content, ctype


def _do_scrape(url):
    _update_status(url, "scraping")
    try:
        session = _session()
        if session is None:
            _update_status(url, "error", error="No LinkedIn session available")
            return

        from services.linkedin import get_profile, get_experience
        profile = get_profile(url, session)
        profile["experience"] = get_experience(url, session)

        blob, ctype = _download_photo(session, profile.get("photo_url", ""))
        _save_profile(url, profile, blob, ctype)
    except Exception as e:
        _update_status(url, "error", error=str(e))


def scrape_in_background(url):
    t = threading.Thread(target=_do_scrape, args=(url,), daemon=True)
    t.start()
