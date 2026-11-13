"""Bihar: the state portal's Phone Directory (state.bihar.gov.in, "Phone Directory" on every department's portal page), one
table per department secretariat: Sr.No. | Department | Name | Division/Office | Designation | Office No | Fax No. |
Mobile No. | Email-ID. Each department fills its own list (Finance 124 rows, CM Secretariat 13, Home 1 on 2026-11-13).

How the site shows one department (checked 2026-11-13 from dev-vps-3, Mumbai): the portal keeps the chosen department in the
session. GET main/ULBHome.html?resetULB&orgId=<id> (the department <select> of the portal does this) sets it, then GET
main/PhoneDirectory.html?getPhoneDirectory shows that department's list. orgId 1 = CM Secretariat. The host's certificate
chain fails verification (curl: unable to get local issuer certificate): the pool's get() retries once without the check and
the records get tls_unverified. No captcha, no login.
Records: level state, body = the department, body_kind department (cm_office for the CM Secretariat), post = Designation,
section = Division/Office. Record id dept:st_br_phone:<orgId>:<data row n> (Sr.No. repeats inside one list; kept as list_no). src_pos {"table", "row"}.
One item = one department (3 GETs: home for the cookie, resetULB, directory). Route: direct (answers from Mumbai); abroad unchecked.
"""
from dforms import _esw, _state

METHOD = "html table (state portal phone directory, department chosen in the session)"
MODULE = "st_br_phone"
BASE = "https://state.bihar.gov.in/main/"
ORGS = {"1": "CM Secretariat", "3": "Cabinet Secretariat Department", "7": "Disaster Management Department",
        "4": "General Administration Department", "5": "Home Department", "10": "Information and Public Relations Department",
        "6": "Law Department", "2": "Parliamentary Affairs Department", "8": "Planning and Development Department",
        "9": "Vigilance Department", "18": "Education Department", "19": "Health Department", "58": "Higher Education Department",
        "28": "Science, Technology and Technical Education Department", "56": "Youth, Employment and Skill Development Department",
        "45": "Art and Culture Department", "55": "Department of Sports", "44": "Tourism Department",
        "11": "Revenue and Land Reforms Department", "13": "Commercial Taxes Department", "12": "Finance Department",
        "17": "Mines & Geology Department", "15": "Prohibition Excise & Registration Department (Excise)",
        "49": "Prohibition Excise & Registration Department (Registration)", "16": "Transport Department",
        "41": "BC & EBC Welfare Department", "40": "Labour Resources and Migrant Workers Welfare Department",
        "42": "Minority Welfare Department", "43": "SC and ST Welfare Department", "39": "Social Welfare Department",
        "50": "Bihar Vikas Mission", "54": "Election Department Bihar", "20": "Building Construction Department",
        "57": "Civil Aviation Department", "26": "Department of Industries", "22": "Energy Department",
        "27": "Information Technology Department", "24": "Public Health Engineering Department", "21": "Road Construction Department",
        "23": "Rural Works Department", "25": "Urban Development and Housing Department",
        "36": "Environment, Forest & Climate Change Department", "29": "Agriculture Department", "35": "Co-operative Department",
        "30": "Dairy, Fisheries and Animal Resources Department", "34": "Food & Consumer Protection Department",
        "37": "Minor Water Resources Department", "33": "Panchayati Raj Department", "32": "Rural Development Department",
        "38": "Sugarcane Industries Department", "31": "Water Resources Department"}
COLS = (("sno", "sr"), ("dept", "department"), ("name", "name"), ("office", "division"), ("post", "designation"),
        ("tel", "office no"), ("fax", "fax"), ("mobile", "mobile"), ("email", "email"))


def kind(post):
    """_state.post_kind, except "Secretary to (Hon'ble) Chief Minister / CM" -> secretary (the generic minister pattern takes it)."""
    import re as _re
    if _re.search(r"(?i)^(special |additional |joint |deputy |under |private )?secretary\s+to\b", post or ""):
        return _state.post_kind(_re.sub(r"(?i)\s+to\b.*$", "", post))
    return _state.post_kind(post)


def parse(html, url, org):
    s = _esw.soup(html)
    t = s.find("table", id="product-table") or next((x for x in s.find_all("table") if "Designation" in x.get_text()), None)
    if t is None:
        return []
    pos = []
    rows = _esw.grid(t, pos=pos)
    if not rows:
        return []
    head = [h.lower() for h in rows[0]]
    col = {k: next((i for i, h in enumerate(head) if w in h), None) for k, w in COLS}
    out = []
    for n, (cells, sp) in enumerate(zip(rows[1:], pos[1:]), 1):
        g = lambda k: _esw.clean(cells[col[k]]) if col[k] is not None and col[k] < len(cells) else ""
        name, post = g("name"), g("post")
        if not (name or post):
            continue
        dept = g("dept") or ORGS.get(org, "")
        phone = ", ".join(x for x in (g("tel"), g("mobile"), f"{g('fax')} (fax)" if g("fax") else "") if x.strip(". -"))
        sno = g("sno") if g("sno").isdigit() else str(n)
        out.append(_state.rec(MODULE, f"{org}:{n}", list_no=sno, state="BR", level="state", post=post, name=name, post_kind=kind(post) or None,
                              body=ORGS.get(org) or dept, body_kind="cm_office" if org == "1" else "department",
                              department=ORGS.get(org) or dept, department_as_listed=dept, section=g("office") or None,
                              phone=phone, email=_esw.emails(g("email")), org_id=org, cells=cells, source=url, src_url=url,
                              src_pos=sp))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{o}", "payload": {"reader": MODULE, "url": BASE + "PhoneDirectory.html?getPhoneDirectory",
                                                 "org_id": o, "label": d, "state": "BR", "india_only": True, "route": "direct"}}
            for o, d in ORGS.items()]


def fetch(p, get):
    org = str(p["org_id"])
    if get(BASE + "CitizenHome.html") is None:
        return [], [], "no answer"
    if get(f"{BASE}ULBHome.html?resetULB&orgId={org}") is None:
        return [], [], "no answer (department page)"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (directory)"
    recs = parse(r.content.decode("utf-8", "replace"), p["url"], org)
    return recs, [_esw.keep(MODULE, f"org-{org}", r.content)], "" if recs else "no rows"
