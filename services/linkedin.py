import base64
import curl_cffi
import html as _html
import json
import os
import re
import urllib.parse

COOKIES_FILE = "cookies.json"

HEADERS_NAV = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "priority": "u=0, i",
    "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _get_input(html, name):
    for q in ('"', "'"):
        m = re.search(
            rf'<input[^>]+name={q}{re.escape(name)}{q}[^>]+value={q}([^{q}]*){q}',
            html, re.DOTALL,
        )
        if m:
            return m.group(1)
        m = re.search(
            rf'<input[^>]+value={q}([^{q}]*){q}[^>]+name={q}{re.escape(name)}{q}',
            html, re.DOTALL,
        )
        if m:
            return m.group(1)
    return ""


def login(email, password):
    s = curl_cffi.Session(impersonate="chrome")

    s.get(
        "https://www.linkedin.com/",
        headers={**HEADERS_NAV, "sec-fetch-site": "none", "referer": ""},
        timeout=120,
    )

    r = s.get(
        "https://www.linkedin.com/login",
        headers={**HEADERS_NAV, "referer": "https://www.linkedin.com/"},
        timeout=120,
    )
    html = r.text

    field_names = [
        "csrfToken", "sIdString", "pageInstance", "loginCsrfParam",
        "parentPageKey", "trk", "authUUID", "session_redirect",
    ]
    fields = {}
    for name in field_names:
        fields[name] = _get_input(html, name)

    cookies = dict(s.cookies)
    if not fields["csrfToken"]:
        fields["csrfToken"] = cookies.get("JSESSIONID", "")
    if not fields["loginCsrfParam"]:
        bcookie = cookies.get("bcookie", "")
        m = re.search(r'v=2&([a-f0-9\-]+)', bcookie)
        fields["loginCsrfParam"] = m.group(1) if m else ""

    form = {
        "csrfToken": fields["csrfToken"],
        "session_key": email,
        "ac": "0",
        "loginFailureCount": "0",
        "sIdString": fields["sIdString"],
        "pkSupported": "true",
        "parentPageKey": fields["parentPageKey"],
        "pageInstance": fields["pageInstance"],
        "trk": fields["trk"],
        "authUUID": fields["authUUID"],
        "session_redirect": fields["session_redirect"],
        "loginCsrfParam": fields["loginCsrfParam"],
        "fp_data": "default",
        "apfc": "{}",
        "_d": "d",
        "showGoogleOneTapLogin": "true",
        "showAppleLogin": "true",
        "showMicrosoftLogin": "true",
        "controlId": "d_checkpoint_lg_consumer_login-login_submit_button",
        "session_password": password,
        "rememberMeOptIn": "true",
    }

    r = s.post(
        "https://www.linkedin.com/checkpoint/lg/login-submit",
        data=form,
        headers={
            **HEADERS_NAV,
            "cache-control": "max-age=0",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.linkedin.com",
            "referer": "https://www.linkedin.com/login",
        },
        timeout=120,
    )

    if "/feed" not in str(r.url):
        raise RuntimeError(f"Login failed. Redirected to: {r.url}")

    cookies_out = dict(s.cookies)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies_out, f, indent=2)
    print(f"Login successful. Saved {len(cookies_out)} cookies to {COOKIES_FILE}")
    return s


def load_session():
    if not os.path.exists(COOKIES_FILE):
        raise FileNotFoundError(
            f"No saved session found ({COOKIES_FILE}). Run login() first."
        )

    with open(COOKIES_FILE) as f:
        cookies = json.load(f)

    s = curl_cffi.Session(impersonate="chrome")
    for name, value in cookies.items():
        s.cookies.set(name, value, domain=".linkedin.com")

    print(f"Loaded session from {COOKIES_FILE} ({len(cookies)} cookies)")
    return s


def _photo_from_aria_label(html):
    i = html.find('aria-label="Profile photo"')
    if i == -1:
        return ""
    window = html[i:i + 4000]

    srcset_m = re.search(r'srcset="([^"]+)"', window)
    if srcset_m:
        entries = []
        for part in srcset_m.group(1).split(","):
            part = part.strip()
            mm = re.match(r'(\S+)\s+(\d+)w', part)
            if mm:
                entries.append((int(mm.group(2)), mm.group(1)))
        if entries:
            entries.sort(key=lambda x: x[0])
            return _html.unescape(entries[-1][1])

    src_m = re.search(
        r'src="(https://media\.licdn\.com[^"]+profile-(?:displayphoto|framedphoto)[^"]+)"',
        window,
    )
    if src_m:
        return _html.unescape(src_m.group(1))
    return ""


def _photo_from_render_payload(html):
    m = re.search(r'profilePictureRenderPayload\\":\\"([A-Za-z0-9+/=]+)\\"', html)
    if not m:
        return ""

    try:
        decoded = base64.b64decode(m.group(1) + "==")
    except Exception:
        return ""

    root_m = re.search(
        rb'(https://media\.licdn\.com/[\x20-\x7e]+?_)(?=[\x00-\x1f])',
        decoded,
    )
    if not root_m:
        return ""
    root = root_m.group(1).decode("utf-8", errors="replace")

    suffixes = re.findall(
        rb'(\d+_\d+/profile-(?:displayphoto|framedphoto)-[\x20-\x7e]+?\?e=\d+[\x20-\x7e]+?)(?=[\x00-\x1f]|",urn|$)',
        decoded,
    )
    if not suffixes:
        return ""

    best = suffixes[0]
    best_w = int(best.split(b"_", 1)[0])
    for sfx in suffixes[1:]:
        w = int(sfx.split(b"_", 1)[0])
        if w > best_w:
            best = sfx
            best_w = w

    return root + best.decode("utf-8", errors="replace")


def _topcard_photo(html):
    url = _photo_from_aria_label(html)
    if url:
        return url
    return _photo_from_render_payload(html)


def _first(pattern, text, group=1, flags=re.DOTALL):
    m = re.search(pattern, text, flags)
    if not m:
        return ""
    return m.group(group).strip()


def _parse_profile(html):
    profile_url = _first(r'href="(https://www\.linkedin\.com/in/[^"?#]+)"', html)

    name = _first(
        r'href="https://www\.linkedin\.com/in/[^"]*/"[^>]*>.*?<h2[^>]*>([^<]+)</h2>',
        html,
    )

    photo_url = _topcard_photo(html)

    followers = _first(r'([\d,]+)\s*followers', html)
    connections = _first(r'([\d,+]+)</p>\s*<p[^>]*>connections</p>', html)
    location = _first(
        r'<p[^>]*>([^<]+)</p><p[^>]*>·</p><p[^>]*><a[^>]*contact-info',
        html,
    )

    name_pos = html.find(f'>{name}<')
    tail = html[name_pos + len(name) + 1:] if name_pos != -1 else html
    headline = _first(r'<p[^>]*>([^<]{20,})</p>', tail)

    education = _first(r'<p[^>]*>([^<]+ · [^<]+)</p>', html)

    open_to_work = False
    open_to_work_roles = ""
    otw = re.search(r'<strong>Open to work</strong>', html)
    if otw:
        open_to_work = True
        snippet = html[otw.end():otw.end() + 400]
        m = re.search(r'<p[^>]*>([^<]+)</p>', snippet)
        if m:
            open_to_work_roles = _html.unescape(m.group(1).strip())

    open_to_hiring = False
    open_to_hiring_role = ""
    open_to_hiring_company = ""
    hm = re.search(r'<strong>Hiring:\s*([^<]+)</strong>', html)
    if hm:
        open_to_hiring = True
        open_to_hiring_role = _html.unescape(hm.group(1).strip())
        snippet = html[hm.end():hm.end() + 400]
        cm = re.search(r'<p[^>]*>([^<]+)</p>', snippet)
        if cm:
            open_to_hiring_company = _html.unescape(cm.group(1).strip())
    elif re.search(r'Open to hiring', html, re.IGNORECASE):
        open_to_hiring = True

    return {
        "name": _html.unescape(name),
        "profile_url": profile_url,
        "photo_url": photo_url,
        "headline": _html.unescape(headline),
        "education": _html.unescape(education),
        "location": _html.unescape(location),
        "followers": followers,
        "connections": connections,
        "open_to_work": open_to_work,
        "open_to_work_roles": open_to_work_roles,
        "open_to_hiring": open_to_hiring,
        "open_to_hiring_role": open_to_hiring_role,
        "open_to_hiring_company": open_to_hiring_company,
    }


def get_profile(url, session):
    r = session.get(
        url,
        headers={**HEADERS_NAV, "referer": "https://www.linkedin.com/feed/"},
        timeout=120,
    )
    return _parse_profile(r.text)


def _extract_profile_urn(html):
    m = re.search(r'fsd_profile(?:%3A|:)(ACoAA[A-Za-z0-9_-]+)', html)
    return m.group(1) if m else ""


def _company_logo_from_vector(v):
    if not v:
        return ""
    root = v.get("rootUrl", "")
    artifacts = v.get("artifacts", [])
    if not root or not artifacts:
        return ""

    best = None
    for a in artifacts:
        if a.get("width", 0) >= 100:
            best = a
            break
    if best is None:
        best = artifacts[-1]

    return root + best.get("fileIdentifyingUrlPathSegment", "")


def _extract_company_logo(item):
    logo = item.get("logo") or {}

    url = _company_logo_from_vector(logo.get("vectorImage") or {})
    if url:
        return url

    for attr in logo.get("attributes") or []:
        dd = attr.get("detailData") or {}
        for key in ("companyLogo", "nonEntityCompanyLogo"):
            nested = dd.get(key) or {}
            url = _company_logo_from_vector(nested.get("vectorImage") or {})
            if url:
                return url

    return ""


def _fmt_date(d):
    if not d:
        return "Present"
    month = d.get("month", 0)
    year = d.get("year", "")
    if month:
        return f"{MONTHS[month]} {year}".strip()
    return str(year)


def _parse_experience_voyager(data):
    included = data.get("included", [])

    employment_types = {}
    company_names = {}
    company_logos = {}

    for item in included:
        t = item.get("$type")
        if t == "com.linkedin.voyager.dash.identity.profile.EmploymentType":
            employment_types[item["entityUrn"]] = item.get("name", "")
        elif t == "com.linkedin.voyager.dash.organization.Company":
            urn = item["entityUrn"]
            company_names[urn] = item.get("name", "")
            logo = _extract_company_logo(item)
            if logo:
                company_logos[urn] = logo

    entries = []
    for item in included:
        if item.get("$type") != "com.linkedin.voyager.dash.identity.profile.Position":
            continue

        title = _html.unescape(item.get("title") or "")
        description = _html.unescape(item.get("description") or "")
        location = _html.unescape(
            item.get("locationName") or item.get("geoLocationName") or ""
        )
        company = _html.unescape(item.get("companyName") or "")

        company_urn = item.get("companyUrn", "")
        if company_urn and company_urn in company_names:
            company = company_names[company_urn]

        logo_url = company_logos.get(company_urn, "")
        employment_type = employment_types.get(item.get("employmentTypeUrn", ""), "")

        dr = item.get("dateRange") or {}
        start = dr.get("start") or {}
        end = dr.get("end")

        date_range = f"{_fmt_date(start)} - {_fmt_date(end) if end else 'Present'}"

        start_sort = start.get("year", 0) * 12 + start.get("month", 0)
        if not end:
            end_sort = 999999
        else:
            end_sort = end.get("year", 0) * 12 + end.get("month", 0)

        entries.append({
            "title": title,
            "company": company,
            "employment_type": employment_type,
            "date_range": date_range,
            "location": location,
            "description": description,
            "logo_url": logo_url,
            "_sort": (end_sort, start_sort),
        })

    entries.sort(key=lambda e: e["_sort"], reverse=True)
    for e in entries:
        del e["_sort"]

    return entries


def get_experience(profile_url, session):
    base = profile_url.rstrip("/")

    r = session.get(
        base + "/",
        headers={**HEADERS_NAV, "referer": "https://www.linkedin.com/feed/"},
        timeout=120,
    )
    urn = _extract_profile_urn(r.text)
    if not urn:
        raise RuntimeError("Could not extract profile URN from page")

    csrf = dict(session.cookies).get("JSESSIONID", "")
    encoded_urn = urllib.parse.quote(f"urn:li:fsd_profile:{urn}")
    api_url = (
        f"https://www.linkedin.com/voyager/api/identity/dash/profilePositionGroups"
        f"?q=viewee&profileUrn={encoded_urn}"
        f"&decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfilePositionGroup-60"
    )

    api_headers = {
        "accept": "application/vnd.linkedin.normalized+json+2.1",
        "accept-language": "en-US,en;q=0.9",
        "csrf-token": csrf,
        "referer": base + "/",
        "user-agent": HEADERS_NAV["user-agent"],
        "x-li-lang": "en_US",
        "x-restli-protocol-version": "2.0.0",
    }

    resp = session.get(api_url, headers=api_headers, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"Experience API returned {resp.status_code}")

    return _parse_experience_voyager(resp.json())
