"""Tamil Nadu: Sub-Registrar offices from the Registration Department portal TNREGINET (tnreginet.gov.in/portal), the public
"SRO list" of the home page. India only. 595 offices (SROs, joint SROs, DROs ...), 10 per page, 60 pages.
Method (one queue item, the steps a visitor's browser makes): GET /portal/ (session cookie + the _csrf token in <meta name="_csrf">),
POST the language switch to English (UserLocaleID=en_US; the default text is Tamil), POST the sroList URL (page 1), then GET each
displaytag page link (d-<id>-p=<n>) that page 1 gives, up to its last page. Table id sroTable: Sr.No., Zone, Registration District,
Sub Registrar Office (SRO Name), Contact No, Address, Email. No officer names. The page shows no date.
Record ids: dept:sro_tn:TN-SRO-<slug of SRO name>.
"""
import html as htmlmod
import re
from urllib.parse import urljoin

from dforms import _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sro_tn"
BASE = "https://tnreginet.gov.in/portal/"
LIST = BASE + "webHP?requestType=ApplicationRH&actionVal=sroList&screenId=7000056&fromHome=1"
LANG = BASE + "webHP?requestType=ApplicationRH&actionVal=homePage&screenId=114&UserLocaleID=en_US"
MAX_PAGES = 80


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": LIST, "state": "TN", "india_only": True}}]


def csrf(html):
    m = re.search(r'<meta\s+name="_csrf"\s+content="([0-9a-fA-F-]{8,})"', html or "")
    return m.group(1) if m else None


def pages(html):
    """(link of page 2..last as given on the page, last page number) from the displaytag pager."""
    links = {}
    for m in re.finditer(r'href="([^"]*actionVal=sroList[^"]*?d-(\d+)-p=(\d+))"', html or ""):
        links[int(m.group(3))] = htmlmod.unescape(m.group(1))
    if not links:
        return None, 0
    last = max(links)
    tmpl = links[last]
    return tmpl, last


def total(html):
    m = re.search(r"([\d,]+) items found", html or "")
    return int(m.group(1).replace(",", "")) if m else None


def parse(html, url=LIST):
    t = _esw.soup(html).find("table", id="sroTable")
    if not t:
        return []
    rows = _esw.grid(t)
    head = [h.lower() for h in rows[0]] if rows else []
    col = {k: next((i for i, h in enumerate(head) if k in h), None) for k in ("sr", "zone", "district", "sro", "contact", "address", "email")}
    recs = []
    for row in rows[1:]:
        c = {k: (row[i] if i is not None and i < len(row) else "") for k, i in col.items()}
        name = c["sro"]
        if not name or not c["sr"].strip().isdigit():
            continue
        area = re.sub(r"_.*$", "", name).strip()          # "Aathur_Dindugal" -> "Aathur" (the suffix tells two Aathurs apart)
        post = "District Registrar" if re.search(r"\bDRO\b|District Registrar", name, re.I) else \
            "Joint Sub Registrar" if re.search(r"\bJoint\b|\bJSR\b", name, re.I) else "Sub Registrar"
        oid = f"TN-SRO-{_esw.slug(name)}"
        recs.append(_esw.record(MODULE, oid, dept="registration", level="district" if post == "District Registrar" else "subdistrict",
                                area=area, post=post, office=name, zone=c["zone"], phone=_esw.phones(c["contact"]),
                                email=_esw.emails(c["email"]), address=c["address"], state="TN", district=c["district"],
                                office_id=oid, source=url))
    return recs


def fetch(p, get):
    files, recs = [], {}
    r = get(BASE)
    if r is None:
        return [], [], "no answer"
    tok = csrf(r.text)
    if not tok:
        return [], [_esw.keep(MODULE, "portal", r.content)], "no csrf token on the portal page"
    data = {"preLoginUserLocaleID": "ta_IN", "formId": "HeaderForm", "attachmentName": "52", "_csrf": tok}
    r = get(f"{LANG}&_csrf={tok}", method="POST", data=data)
    if r is not None:
        tok = csrf(r.text) or tok
    r = get(f"{p.get('url', LIST)}&_csrf={tok}", method="POST", data={}, headers={"X-CSRF-TOKEN": tok})
    if r is None:
        return [], [], "sro list did not answer"
    files.append(_esw.keep(MODULE, "sro-list-p1", r.content))
    for rid, d in parse(r.text, LIST):
        recs[rid] = d
    tmpl, last = pages(r.text)
    want = total(r.text)
    for n in range(2, min(last, MAX_PAGES) + 1):
        u = urljoin(BASE, re.sub(r"(d-\d+-p=)\d+", rf"\g<1>{n}", tmpl))
        rp = get(u)
        if rp is None:
            continue
        files.append(_esw.keep(MODULE, f"sro-list-p{n}", rp.content))
        for rid, d in parse(rp.text, LIST):
            recs[rid] = d
    out = list(recs.items())
    why = "" if out else "no rows"
    if out and want and len(out) < want * 0.9:
        why = f"only {len(out)} of {want} offices"
    return out, files, why
