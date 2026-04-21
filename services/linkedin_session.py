import os

_cached = None


def get_session():
    global _cached
    if _cached is not None:
        return _cached

    from services.linkedin import load_session, login

    try:
        _cached = load_session()
        return _cached
    except FileNotFoundError:
        pass

    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        return None

    _cached = login(email, password)
    return _cached
