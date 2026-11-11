"""Shared parts of the north-west ulb2 readers (ulb2_hp, ulb2_hr, ulb2_la, ulb2_dl): read officer tables of a town body's own
site or of a page about the body, and make _ulb.record() records ("dept:<module>:<key>", dept town_body, level body).

- table_rows(table): the rows of one HTML table as {post, name, phone, email, ward}, when the table has a header row with a
  name column and a designation / post column ("Sr. No. | Designation | Name | Phone Number | Remark", "Name | Designation |
  Email | Mobile No", "Employee Name | Designation | Department"). Header cells may be <th> or <td><b>.
- crawl(p, get, module, state): one queue item = one body site. It reads the start page (p["url"]), checks that the page is the
  site of this body (the body name and a word for a town body are on the page; a parked domain page is refused), follows up to
  MAX_PAGES links of the same host whose address or text names officers, employees, elected members, a directory, contact or
  RTI, and reads every officer table on those pages. When no page gives a person, the site's own office email and phone
  (mailto: / tel: links, "Email ID :" text) give one record: post "Executive Officer" / "Secretary" when the mailbox is a post
  mailbox (eo-palwal@ulbharyana.gov.in; extra key post_from = "email", as ulb_pb does), else "Office" (role staff).
The payload gives the body as LGD writes it ("body"), its district, LGD code ("lgd_code") and type ("body_type"), so the
records tie to civic.ulb by the code (civic-india sql/87 reads lgd_code first).
"""
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw, _ulb

MAX_PAGES = 8
NAME = re.compile(r"(?i)^\W*(name|employee\s*name|officer'?s?\s*name|name\s*of\s*(the\s*)?(officer|official|employee|member|councill?or)s?|member\s*name)\b|^\W*नाम")
POST = re.compile(r"(?i)designation|\bpost\b|पद")
PHONE = re.compile(r"(?i)phone|mobile|contact|tel\b|landline|मोबाइल|फोन")
EMAIL = re.compile(r"(?i)e-?\s?mail")
WARD = re.compile(r"(?i)\bward\b|वार्ड")
LINK = re.compile(r"(?i)officer|employee|staff|elected|member|councill?or|directory|who'?s|contact|\brti\b|\bpio\b|\bdir\b")
SKIP_LINK = re.compile(r"(?i)login|register|admin|javascript:|mailto:|tel:|\.(pdf|jpe?g|png|docx?|xlsx?)$|rtiharyana|rtionline")
TOWN = re.compile(r"(?i)municipal|nagar|panchayat|council|committee|corporation|नगर")
PARKED = re.compile(r"(?i)(this\s+domain|domain\s+name)\s+(is\s+)?(for\s+sale|parked|may\s+be\s+for\s+sale)|buy\s+this\s+domain|parkingcrew|sedoparking")
EMPTY = re.compile(r"(?i)^\W*(-+|nil|n\.?a\.?|vacant|no\s+.*(found|available).*)\W*$")


def table_rows(table):
    """[{post, name, phone, email, ward}] of one table, [] when it has no name + designation header."""
    rows = _esw.grid(table)
    for i, row in enumerate(rows[:4]):
        cols, tels = {}, []
        for j, c in enumerate(row):
            c = c.split(" | ")[0]
            for k, rx in (("name", NAME), ("post", POST), ("email", EMAIL), ("phone", PHONE), ("ward", WARD)):
                if k == "phone" and rx.search(c) and not EMAIL.search(c) and j not in cols.values():
                    tels.append(j)          # every phone column ("Phone Number", "Mobile", "Landline No")
                    break
                if k not in cols and rx.search(c):
                    cols[k] = j
                    break
        if "name" in cols and "post" in cols:
            break
    else:
        return []
    out = []
    for row in rows[i + 1:]:
        if len(row) <= max(list(cols.values()) + tels) or row == rows[i]:
            continue
        v = {k: _esw.clean(row[j].replace(" | ", " ")) for k, j in cols.items()}
        v["phone"] = " , ".join(row[j] for j in tels if row[j] != row[cols["name"]])
        name, post = v.get("name", ""), v.get("post", "")
        if EMPTY.match(name) and not post:
            continue
        if EMPTY.match(name):
            name = ""
        phone = _esw.phones(v["phone"])
        email = _esw.emails(" ".join(row))
        if not post and not re.search(r"\w", v.get("ward") or ""):
            continue
        if not (name or phone or email):
            continue
        ward = v.get("ward") if re.search(r"\w", v.get("ward") or "") else None
        out.append({"post": post or "Ward Member", "name": name, "phone": phone, "email": email, "ward": ward})
    return out


def is_body_page(html, body):
    """The start page names the body (every word of one of the "|" alternatives, word match) and a town body word; a parked
    domain page is refused."""
    soup = _esw.soup(html)
    text = _esw.clean(soup.get_text(" "))[:20000]
    if PARKED.search(text) or not TOWN.search(text):
        return False
    low = text.lower()
    for alt in body.split("|"):
        words = [w for w in re.split(r"[^a-z]+", alt.lower()) if len(w) >= 3]
        if words and all(re.search(r"\b" + w + r"\b", low) for w in words):
            return True
    return False


def links(html, base):
    """Same-host links that name officer / contact pages, in page order, without repeats."""
    host = urlparse(base).netloc.lower().removeprefix("www.")
    out = []
    for a in _esw.soup(html).find_all("a", href=True):
        h = a["href"].strip()
        if SKIP_LINK.search(h) or "{{" in h:
            continue
        u = urljoin(base, h).split("#")[0]
        if urlparse(u).netloc.lower().removeprefix("www.") != host or u.rstrip("/") == base.rstrip("/"):
            continue
        if LINK.search(urlparse(u).path + " " + _esw.clean(a.get_text(" "))) and u not in out:
            out.append(u)
    return out[:MAX_PAGES]


def office(html):
    """(email, phone) of the office from mailto: / tel: links, else from "Email" / "Contact No" text."""
    soup = _esw.soup(html)
    mails = [a["href"][7:] for a in soup.find_all("a", href=True) if a["href"].lower().startswith("mailto:")]
    tels = [a["href"][4:] for a in soup.find_all("a", href=True) if a["href"].lower().startswith("tel:")]
    text = _esw.clean(soup.get_text(" "))
    email = _esw.emails(" ".join(mails)) or _esw.emails(" ".join(re.findall(r"(?i)e-?mail(?:\s*id)?\s*:?\s*(\S+)", text)))
    phone = _esw.phones(tels[0]) if tels else _esw.phones(" ".join(re.findall(r"(?i)(?:contact\s*(?:no|number)|phone)\s*\.?\s*:?\s*([+\d][\d\s()-]{6,})", text))[:1])
    if "x" * 5 in email.lower():
        email = ""
    return email.split(", ")[0] if email else "", phone.split(", ")[0] if phone else ""


def records(module, state, p, people, seen, office_email="", office_phone="", source=""):
    """_ulb.record() for each person (repeats of the same post + name dropped), else one "Office" record."""
    common = {"district": p.get("district"), "body_type": p.get("body_type"), "lgd_code": p.get("lgd_code")}
    out, done = [], set()
    for x in people:
        k = (x["post"].lower(), x["name"].lower(), x.get("ward"))
        if k in done:
            continue
        done.add(k)
        extra = {"ward": x["ward"]} if x.get("ward") else {}
        out.append(_ulb.record(module, state, p["body"], x["post"], seen, name=x["name"], phone=x["phone"], email=x["email"],
                               source=x.get("source") or source, **common, **extra))
    if not out and (office_email or office_phone):
        # a post mailbox names the post (Haryana: eo-palwal@ulbharyana.gov.in, secy-<town>@...), as ulb_pb does
        post = ("Executive Officer" if re.match(r"(?i)eo[-._]", office_email) else
                "Secretary" if re.match(r"(?i)secy?[-._]", office_email) else "Office")
        extra = {"post_from": "email"} if post != "Office" else {}
        out.append(_ulb.record(module, state, p["body"], post, seen, phone=office_phone, email=office_email, source=source,
                               **common, **extra))
    return out


def crawl(p, get, module, state):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(module, _esw.slug(p["body"]) + "-start", r.content)]
    if not is_body_page(r.text, p.get("match") or p["body"]):
        return [], files, "not the body's site"
    people, mail, tel = [], "", ""
    pages = [(p["url"], r.text)]
    for u in links(r.text, p["url"]):
        a = get(u)
        if a is None or not a.text:
            continue
        files.append(_esw.keep(module, _esw.slug(p["body"]) + "-" + (_esw.slug(urlparse(u).path) or "page"), a.content))
        pages.append((u, a.text))
    for u, html in pages:
        for t in _esw.soup(html).find_all("table"):
            people += [dict(x, source=u) for x in table_rows(t)]
        if not (mail and tel):
            m, t = office(html)
            mail, tel = mail or m, tel or t
    recs = records(module, state, p, people, set(), mail, tel, p["url"])
    return recs, files, "" if recs else "no rows"
