"""All India: the officers of the postal circles and regions (Chief Postmasters General, Postmasters General, Directors of Postal
Services, GPO directors ...) with name, phone and email, from the Department of Posts directory,
www.indiapost.gov.in/ministry/directory.
The page is a Next.js page: all 511 contacts (directorate and circles) are in the page itself, in the self.__next_f.push([1,"..."])
strings, as objects {"Address", "Department", "Designation", "Email" (written x[at]indiapost[dot]gov[dot]in), "Keyname": [section],
"Name" ("Vacant" for an empty post), "Phone", "EPABX", "Priority", "SectionPriority", "id": "contact-..."}. Only the rows of the
circle sections ("Maharashtra Circle", "North East Circle ", "Army Postal Service Circle" ...) are kept: about 230 rows.
The site refuses requests with no browser-like User-Agent (406 from its firewall); the family's own User-Agent is accepted from
this box and from India. One queue item. Record ids: dept:civic_post_dir_in:<circle slug>-<slug of designation>.
Level: "region" when the post names a region (PMG / DPS of a region), else "circle". Division heads (SSPOs) and postmasters of
single offices are not in this directory.
"""
import json
import re

from dforms import _civic, _esw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_post_dir_in"
URL = "https://www.indiapost.gov.in/ministry/directory"
PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
CONTACT = re.compile(r'\{"Address"\s*:(?:[^{}]|\{[^{}]*\})*?"id"\s*:\s*"contact-[^"]+"\}')
# posts of a circle that covers more than one state name their place: the state is taken from it (Goa Region of Maharashtra Circle,
# the divisions of North East Circle)
PLACES = [(re.compile(r"(?i)\b(goa|panaji)\b"), "GA"), (re.compile(r"(?i)\b(mizoram|aizawl|aizawal)\b"), "MZ"),
          (re.compile(r"(?i)\b(tripura|agartala)\b"), "TR"), (re.compile(r"(?i)\b(nagaland|kohima|dimapur)\b"), "NL"),
          (re.compile(r"(?i)\b(meghalaya|shillong)\b"), "ML"), (re.compile(r"(?i)\b(arunachal|itanagar)\b"), "AR"),
          (re.compile(r"(?i)\b(manipur|imphal)\b"), "MN"), (re.compile(r"(?i)\b(sikkim|gangtok)\b"), "SK"),
          (re.compile(r"(?i)\b(ladakh|leh)\b"), "LA"), (re.compile(r"(?i)\b(chandigarh)\b"), "CH")]


def state_of(post, circle):
    """The state of the first place the post names ("N.E.-I Region Agartala/ Aizawl" -> TR), else the circle's state."""
    hits = [(m.start(), code) for rx, code in PLACES for m in [rx.search(post)] if m]
    return min(hits)[1] if hits else (_civic.state_code(circle) or "IN")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "IN", "india_only": False, "expected": 230}}]


def contacts(html):
    """Every contact object in the page's flight data."""
    flight = "".join(json.loads('"' + c + '"') for c in PUSH.findall(html))
    out = []
    for m in CONTACT.finditer(flight):
        try:
            out.append(json.loads(m.group(0)))
        except ValueError:
            continue
    return out


def parse(html, url=URL):
    recs, seen = [], set()
    for c in contacts(html):
        circle = next((_esw.clean(k) for k in c.get("Keyname") or [] if _esw.clean(k).lower().endswith("circle")), "")
        if not circle:
            continue
        post = _esw.clean(c.get("Designation"))
        name = _esw.clean(c.get("Name"))
        vacant = name.lower() in ("vacant", "-", "")
        phone = _esw.phones(c.get("Phone") or "", c.get("EPABX") or "")
        email = _esw.emails(c.get("Email") or "")
        if vacant and not (phone or email):
            continue
        key = _civic.unique(f"{_esw.slug(circle)}-{_esw.slug(post)}", seen)
        recs.append(_civic.record(
            MODULE, key, "post", dept="postal", level="region" if re.search(r"(?i)\bregion\b", post) else "circle",
            area=post, post=post, name="" if vacant else name, phone=phone, email=email, address=c.get("Address"),
            circle=circle, state=state_of(post, circle), vacant=True if vacant else None, office_id=c.get("id"),
            source=url, source_org="Department of Posts directory"))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "directory", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
