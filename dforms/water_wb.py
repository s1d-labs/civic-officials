"""West Bengal: Public Health Engineering Department contact directory, www.wbphed.gov.in/en/contacts. Answers from Germany and India.
The page is an ASP.NET Core form: GET /en/contacts (session cookie + __RequestVerificationToken), then the visitor's search,
POST /en/contacts/searchContacts with Choose Office = PHE Directorate and one Designation; the answer lists every match as a card
(name, "<designation>, <division / sub-division>", office address, Ph. No., Fax, E-Mail), no paging (76 Executive Engineers).
The designation ids are read from the form each time (the payload's id is the fallback). One queue item = one designation:
Engineer in Chief, Chief Engineer, Assistant Chief Engineer, Senior Superintending Engineer, Superintending Engineer,
Deputy Superintending Engineer, Executive Engineer, Assistant Engineer, Junior Engineer.
Record ids: dept:water_wb:<slug of the card's post line, e.g. executive-engineer-jalpaiguri-division>[:n] (the same card found by
two searches gets the same id).
"""
import re

from dforms import _esw

MODULE = "water_wb"
FORM = "https://www.wbphed.gov.in/en/contacts"
SEARCH = "https://www.wbphed.gov.in/en/contacts/searchContacts"
DIRECTORATE = "1aa0de04-eabc-4d82-bb9a-67fba9424156"
DESIGNATIONS = {"Engineer in Chief": "2702ea63-0b32-41d6-b3b2-38256a19bde2", "Chief Engineer": "0d330fb6-5c0c-4f4b-9454-39fb5cf159d6",
                "Assistant Chief Engineer": "ff054b42-c544-414f-b5f9-0c8653a69032",
                "Senior Superintending Engineer": "ec82aadc-cb42-4ff6-84ef-0159a1d6b9fd",
                "Superintending Engineer": "bdebebe4-398f-42bf-ad09-62c5799ea59b",
                "Deputy Superintending Engineer": "72a563d7-fbfd-466c-95e0-043ea58854ba",
                "Executive Engineer": "d7e2f5aa-2a71-4715-b515-7c5367f8ad9d", "Assistant Engineer": "041a7c64-737b-4ce2-a91d-84420380b443",
                "Junior Engineer": "8e6cb43d-776f-4204-9430-d428485b79fb"}
ORG = "Public Health Engineering Department, West Bengal"


def items(get=None):
    return [{"key": f"{MODULE}-{_esw.slug(d)}", "payload": {"reader": MODULE, "url": FORM, "state": "WB", "designation": d,
                                                          "designation_id": i}} for d, i in DESIGNATIONS.items()]


def form_fields(html, designation, fallback_id):
    """The POST body a visitor's search sends, from the form page: token, office = PHE Directorate, the designation's id."""
    soup = _esw.soup(html)
    tok = soup.find("input", attrs={"name": "__RequestVerificationToken"})
    if not tok:
        return None
    sel = soup.find("select", id="DesignationId")
    did = next((o.get("value") for o in (sel.find_all("option") if sel else [])
                if _esw.clean(o.get_text()).lower() == designation.lower() and o.get("value")), fallback_id)
    dept = soup.find("select", id="AdvancedDepartmentId")
    dep = next((o.get("value") for o in (dept.find_all("option") if dept else [])
                if _esw.clean(o.get_text()) == "PHE Directorate"), DIRECTORATE)
    return {"DepartmentId": dep, "AdvancedDepartmentId": dep, "District": "", "Name": "", "DesignationId": did,
            "EngineeringWing": "", "ZoneId": "", "CircleId": "", "DivisionId": "", "SubDivisionId": "",
            "__RequestVerificationToken": tok.get("value", "")}


def _level(post):
    p = post.lower()
    if re.search(r"sub[\s-]*division", p):
        return "subdivision"
    if "junior engineer" in p or "section" in p:
        return "section"
    if "division" in p or "executive engineer" in p:
        return "division"
    if "circle" in p or "superintending" in p:
        return "circle"
    if "zone" in p:
        return "zone"
    return "state"


def parse(html, designation, url=SEARCH):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for card in soup.select("div.contact-person-panel"):
        h5 = card.find("h5")
        pp = h5.find_next_sibling("p") if h5 else None
        name = _esw.clean(h5.get_text()) if h5 else ""
        post = _esw.clean(pp.get_text()) if pp else designation
        right = card.select_one(".cpnal-right")
        info = {}
        for p in right.find_all("p") if right else []:
            t = _esw.clean(p.get_text(" "))
            m = re.match(r"Office\s*:\s*(.*)$", t)
            if m:
                info["address"] = m.group(1)
            m = re.match(r"Ph\.\s*No\.?\s*-?\s*(.*?)\s*Fax\s*-?\s*(.*)$", t)
            if m:
                info["phone"], info["fax"] = m.group(1), m.group(2)
            if t.lower().startswith("e-mail"):
                info["email"] = t
        office = post.split(",", 1)[1].strip() if "," in post else ""
        if not (name or info.get("phone") or info.get("email")):
            continue
        key = _esw.slug(post) if office else f"{_esw.slug(post)}:{_esw.slug(name)}"
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="water", level=_level(post), area=office, post=post, name=name,
                                phone=_esw.phones(info.get("phone")), fax=_esw.phones(info.get("fax")),
                                email=_esw.emails(info.get("email")), address=info.get("address"), state="WB",
                                office_id=f"WB-PHED-{_esw.slug(office)}" if office else None, org=ORG, source=FORM))
    return recs


def fetch(p, get):
    d = p["designation"]
    r = get(p.get("url", FORM))
    if r is None:
        return [], [], "no answer"
    data = form_fields(r.text, d, p.get("designation_id"))
    if not data:
        return [], [], "no search form"
    s = get(SEARCH, method="POST", data=data)
    if s is None:
        return [], [], "search did not answer"
    files = [_esw.keep(MODULE, f"search-{_esw.slug(d)}", s.content)]
    recs = parse(s.text, d)
    return recs, files, "" if recs else "no contacts"
