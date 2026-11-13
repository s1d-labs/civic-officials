"""Goa: state-level officers from the state portal www.goa.gov.in (WordPress, server rendered; checked 2026-11-13 from dev-vps-3,
archive.s1d.me copies of 2026-11-10). Payload "kind":
- "secretaries": https://www.goa.gov.in/secretaries/ : one card (div.apio_holder) per secretary: name with service and batch
  ("Dr. V. Candavelou, IAS (1997)"), post ("Chief Secretary", "Commissioner cum Secretary (Revenue)"), "Portfolios" (numbered
  list of departments), phone(s), e-mail(s) ("cs[hyphen]goa[at]nic[dot]in"), fax. About 20 cards.
- "deptdir": https://www.goa.gov.in/citizen/department-directory/ : one page (2.6 MB) with every department's officers, 1,087
  cards: name, designation, office address, e-mail, phone (+ fax). The page does not name the department of a card; the
  office address names it in most cards ("Administrative Reforms Department, Secretariat, Porvorim-Goa"): department = the
  address up to the first comma.
- "hod": https://www.goa.gov.in/government/head-of-the-departments/ : one table: DEPARTMENT | HOD DESIGNATION | OFFICIAL
  ADDRESS | EMAIL ID (193 rows, no names).
Records (dforms/_state.py): level state (Goa has two districts; a card whose address names North Goa / South Goa collectorate
gets district + district_code too), dept from the department words, post_kind from the post, portfolios as a list.
Route: the host answers from Mumbai (direct); abroad not checked. One queue item = one page (1 GET). Record ids:
dept:st_ga_portal:<kind>:<n> (n = card or row number on the page; the page order is stable between saves).
"""
import re

from dforms import _esw, _state

METHOD = "html cards (div.apio_holder) / html table"

M = "st_ga_portal"
URLS = {"secretaries": "https://www.goa.gov.in/secretaries/",
        "deptdir": "https://www.goa.gov.in/citizen/department-directory/",
        "hod": "https://www.goa.gov.in/government/head-of-the-departments/"}
DISTRICTS = [(r"north\s*goa", "551", "North Goa"), (r"south\s*goa", "552", "South Goa"), (r"kushavati", "793", "Kushavati")]


def _txt(el):
    if el is None:
        return ""
    for br in el.find_all("br"):
        br.replace_with(" | ")
    return _esw.clean(el.get_text(" "))


def cards(html):
    """[{name, post, portfolios, phone, email, fax, address, n}] of the div.apio_holder cards, in page order (n 1-based)."""
    soup = _esw.soup(html)
    out = []
    for n, c in enumerate(soup.select("div.apio_holder"), 1):
        name = _txt(c.select_one(".api_tab_pname"))
        post_el = c.select_one(".api_tab_pdesignation") or (c.select_one(".api_tab_pname").find_next_sibling("div")
                                                            if c.select_one(".api_tab_pname") else None)
        d = {"n": n, "name": name, "post": _txt(post_el), "portfolios": [], "phone": "", "email": "", "fax": "", "address": ""}
        for t in c.select(".dept_tab_title"):
            head = _esw.clean(t.get_text(" ")).lower()
            if head == "address":
                nxt = t.find_next_sibling("div")
                d["address"] = re.sub(r"\s*,(\s*,)+", ",", _txt(nxt).replace(" | ", ", "))
            elif head == "portfolios":
                nxt = t.find_parent("div").find_next_sibling("div") if t.find_next_sibling("div") is None else t.find_next_sibling("div")
                items = [x.strip() for x in _txt(nxt).split("|")]
                d["portfolios"] = [re.sub(r"^\d+\)\s*", "", x).strip() for x in items if x.strip()]
        for img in c.find_all("img"):
            alt = (img.get("alt") or "").lower()
            box = img.find_parent("div")
            val = box.find_next_sibling("div") if box is not None else None
            v = _txt(val)
            if "email" in alt:
                d["email"] = _esw.emails(v)
            elif "fax" in alt:
                d["fax"] = _esw.phones(v)
            elif "contact" in alt or "telephone" in alt or "phone" in alt:
                fax = re.findall(r"([\d\s/-]{6,})\(\s*fax\s*\)", v, re.I)
                d["fax"] = d["fax"] or _esw.phones(*fax)
                d["phone"] = _esw.phones(re.sub(r"[\d\s-]{6,}\(\s*fax\s*\)", " ", v, flags=re.I).replace("/", " , "))
        if name or d["post"]:
            out.append(d)
    return out


def _district(*texts):
    t = " ".join(texts)
    for rx, code, name in DISTRICTS:
        if re.search(rx, t, re.I):
            return code, name
    return "", ""


def parse(html, kind, url):
    recs = []
    if kind == "hod":
        soup = _esw.soup(html)
        for t in soup.find_all("table"):
            pos = []
            rows = _esw.grid(t, pos=pos)
            for row, sp in zip(rows, pos):
                if len(row) < 4 or re.fullmatch(r"(?i)department", _esw.clean(row[0])):
                    continue
                dept, post, addr, mail = (_esw.clean(x) for x in row[:4])
                addr = re.sub(r"\s*,(\s*,)+", ",", addr.replace(" | ", ", "))
                code, dname = _district(dept, addr)
                recs.append(_state.rec(M, f"hod:{sp['row']}", state="GA", level="district" if code else "state", post=post,
                                       body=dept, body_kind="department", department=dept, district=dname, district_code=code,
                                       email=_esw.emails(mail), address=addr, section="Head of the Departments",
                                       cells=row[:4], office_id=_esw.slug(dept), src_url=url, src_pos=sp))
        return recs
    for d in cards(html):
        dept = re.split(r",", d["address"])[0].strip() if d["address"] else ""
        if kind == "secretaries":          # "Secretary (Health)" -> Health; the Chief Secretary: the secretariat
            m = re.search(r"\(([^)]+)\)", d["post"])
            dept = m.group(1).strip() if m else "Secretariat"
        code, dname = _district(dept, d["address"]) if kind == "deptdir" else ("", "")
        recs.append(_state.rec(M, f"{kind}:{d['n']}", state="GA", level="district" if code else "state", post=d["post"],
                               name=d["name"], body="Secretariat, Government of Goa" if kind == "secretaries" else dept,
                               body_kind="secretariat" if kind == "secretaries" else "department",
                               department=dept, district=dname, district_code=code, phone=d["phone"], email=d["email"],
                               fax=d["fax"] or None, address=d["address"], portfolios=d["portfolios"] or None,
                               section={"secretaries": "Secretaries", "deptdir": "Department Directory"}[kind],
                               src_url=url, src_pos={"card": d["n"]}))
    return recs


def items(get=None):
    return [{"key": f"{M}:{k}", "payload": {"reader": M, "kind": k, "url": u, "state": "GA", "india_only": True,
                                            "route": "direct"}} for k, u in URLS.items()]


def fetch(p, get):
    url = p.get("url") or URLS[p["kind"]]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(M, p["kind"], r.content)]
    recs = parse(r.text, p["kind"], url)
    return recs, files, "" if recs else "no cards or rows"
