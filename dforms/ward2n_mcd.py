"""Municipal Corporation of Delhi (mcdonline.nic.in/portal): the officers of its 12 zones, from each zone's "Key Contacts" page.
The portal is one page; the menu "Zones" opens a zone with GET /portal/showSubMenu?menuguide=<zone guid> (JSON: the zone's sub
menus: "Key Contacts", "Duty roster of mali", "Swachhta Sainik", "Works done" ...) and a sub menu with
GET /portal/showContent?menuguide=<sub menu guid> (JSON; "menuName" holds the page HTML). Key Contacts (live sample 2026-11-11 of
Najafgarh zone, answers from Germany, not in archive.s1d.me; the page shows no date): a header with the Deputy Commissioner, then
one table per department (<div class='section-title'>: Department, Assessment and Collection, Education, Engineering,
Electrical, Project, DEMS, Sanitation, Horticulture, Health, Labour Welfare, Law, Veterinary, Account, Control Room):
S. No. | Name | Designation | Phone | Mobile | Email Address. One queue item per zone (the zone guids are in the portal's menu,
copied into ZONES). Two requests per item: the sub menu list, then the Key Contacts page. The page does not say which of the 250
wards each zone holds (no "wards" key). Posts are kept as written ("Dy. Comm.", "Ex. Engg. (M-I)", "CSI"); post_full gives the
long form of the common short forms. Record ids: dept:ward2n_mcd:<zone slug>:<department slug>:<post slug>:<name slug>.
"""
import json
import re

from dforms import _esw, _ward

MODULE = "ward2n_mcd"
BODY, LGD, STATE = "Municipal Corporation of Delhi", "X-DL-MCD", "DL"
BASE = "https://mcdonline.nic.in/portal"
ZONES = (("08e68a86-d9c6-4894-a5fa-43b1c3dce041", "Shahdara South Zone"), ("33588ce9-0e78-4ed5-a356-0edbe494fa46", "Civil Lines Zone"),
         ("344a5905-d3f0-41e5-b4e9-7a4d9bf5b45b", "Rohini Zone"), ("3e636f52-ae9f-48c6-80dc-70763595b80f", "West Zone"),
         ("40792a42-b3c6-491e-ba3d-053422edd5bc", "Shahdara North Zone"), ("521027b0-072e-40e9-b1c0-72c2ab94f49f", "Keshav Puram Zone"),
         ("601e37f8-dbf3-4719-93c6-1a90095d3bbe", "Central Zone"), ("63d07957-0dc3-4f7d-ae1b-5dadc4f46536", "South Zone"),
         ("808a4f82-3915-49e1-a7e7-6b1bbe608bda", "Karol Bagh Zone"), ("adad17f8-0e47-4a7c-99e0-0960c9ad651d", "Narela Zone"),
         ("adbbaa4a-7c94-4e24-b6e7-91c1c6c79911", "Najafgarh Zone"), ("d973d9b8-967c-41a9-b898-533093ebf33e", "City-SP Zone"))
# short forms on the pages -> long form (post_full) and wing
SHORT = ((r"^dy\.?\s*comm", "Deputy Commissioner", "administration"), (r"^(asstt?|asst)\.?\s*comm", "Assistant Commissioner", "administration"),
         (r"^jt\.?\s*a\s*&\s*c|^jt\.?\s*a&c", "Joint Assessor and Collector", "revenue"),
         (r"^dy\.?\s*a\s*&\s*c|^dy\.?\s*a&c", "Deputy Assessor and Collector", "revenue"), (r"\ba\s*&\s*c\b", "Assessor and Collector", "revenue"),
         (r"^(ex\.?\s*engg|e\.?e\.?)\b", "Executive Engineer", "engineering"), (r"^s\.?e\.?\b", "Superintending Engineer", "engineering"),
         (r"^chief\s*engg", "Chief Engineer", "engineering"), (r"^a\.?e\.?\b", "Assistant Engineer", "engineering"),
         (r"^j\.?e\.?\b", "Junior Engineer", "engineering"), (r"^dho\b", "Deputy Health Officer", "health"),
         (r"^c?amo\b", "Medical Officer", "health"), (r"^csi\b", "Chief Sanitary Inspector", "sanitation"),
         (r"^s\.?s\.?\b", "Sanitary Superintendent", "sanitation"), (r"^si\b|sanitary\s*insp", "Sanitary Inspector", "sanitation"),
         (r"^dd\s*\(?\s*vs", "Deputy Director (Veterinary Services)", "health"), (r"^dde\b", "Deputy Director of Education", "other"),
         (r"^(a|j)lo\b", "Law Officer", "other"), (r"^d?c?aco?\b|^aca\b|^dca\b", "Accounts Officer", "other"),
         (r"^apro\b", "Assistant Public Relations Officer", "other"))
DEPT_WING = (("assessment", "revenue"), ("engineering", "engineering"), ("project", "engineering"), ("electrical", "electrical"),
             ("dems", "sanitation"), ("sanitation", "sanitation"), ("horticulture", "horticulture"), ("health", "health"),
             ("veterinary", "health"), ("building", "planning"), ("town planning", "planning"))


def items(get=None):
    return [{"key": f"{MODULE}-{_esw.slug(z)}", "payload": {"reader": MODULE, "url": f"{BASE}/showSubMenu?menuguide={g}", "zone": z,
                                                           "state": STATE}} for g, z in ZONES]


def long_post(post):
    p = _esw.clean(post).lower()
    for rx, full, wing in SHORT:
        if re.search(rx, p):
            return full, wing
    return "", ""


def contacts_guid(data):
    """The guid of the zone's "Key Contacts" sub menu in a showSubMenu answer ({parent guid: [{menuGuide, menuName}, ...]})."""
    for v in (data or {}).values():
        for it in v or []:
            if re.search(r"(?i)contact", it.get("menuName") or ""):
                return it.get("menuGuide")
    return None


def parse(html, p, source=None):
    soup = _esw.soup(html)
    zone = p["zone"]
    seen, recs = set(), []
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g:
            continue
        head = [c.lower() for c in g[0]]
        if not any("name" in h for h in head) or not any("designation" in h for h in head):
            continue
        sec = t.find_previous(class_="section-title")
        dept = _esw.clean(sec.get_text()) if sec else ""
        rows = [dict(zip(head, r)) for r in g[1:]]
        for r in rows:
            name = _esw.clean(_ward.col(r, "name"))
            post = _esw.clean(_ward.col(r, "designation"))
            phone = " , ".join(x for x in (_ward.col(r, "phone"), _ward.col(r, "mobile")) if re.search(r"\d{5}", x or ""))
            email = _ward.col(r, "email")
            if not post or not (name or phone or email):
                continue
            full, wing = long_post(post)
            dw = next((w for k, w in DEPT_WING if k in dept.lower()), None)
            wing = wing if wing and wing != "other" else (dw or _ward.wing_of(post))
            key = f"{_esw.slug(zone)}:{_esw.slug(dept) or 'dept'}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}"
            recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=None, level="zone", area=zone,
                                     zone=zone, post=full if full in ("Deputy Commissioner", "Assistant Commissioner") else post,
                                     post_as_written=post if full in ("Deputy Commissioner", "Assistant Commissioner") else None,
                                     post_full=full or None, name=name, phone=phone, email=email, wing=wing,
                                     section=dept or None, source=source or p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (sub menu)"
    try:
        g = contacts_guid(r.json())
    except ValueError:
        return [], [_esw.keep(MODULE, f"{_esw.slug(p['zone'])}-submenu", r.content, "json")], "sub menu is not JSON"
    files = [_esw.keep(MODULE, f"{_esw.slug(p['zone'])}-submenu", r.content, "json")]
    if not g:
        return [], files, "no Key Contacts sub menu"
    url = f"{BASE}/showContent?menuguide={g}"
    c = get(url)
    if c is None:
        return [], files, "no answer (Key Contacts)"
    files.append(_esw.keep(MODULE, f"{_esw.slug(p['zone'])}-key-contacts", c.content, "json"))
    try:
        d = json.loads(c.content)
    except ValueError:
        return [], files, "Key Contacts is not JSON"
    html = d.get("menuName") or d.get("menuContentHtml") or ""
    recs = parse(html, p, source=url)
    why = "" if recs else ("Key Contacts is a PDF: " + d["pdfPath"] if d.get("pdfPath") else "no officer table in Key Contacts")
    return recs, files, why
