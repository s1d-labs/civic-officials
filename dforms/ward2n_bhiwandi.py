"""Bhiwandi-Nizampur Shahar Mahanagarpalika (bncmc.gov.in): the officers of its 5 ward committee (prabhag samiti) offices. One page
per office, department.php?department_id=53..57 ("Ward Committee No. 1" .. "No. 5"; English; answers from Germany, redirects to
www.; live sample 2026-11-11 of no. 1; the archive holds the other department pages, not these 5). Each page: one table
"Name | Designation | Mobile No | Email ID" (the Assistant Commissioner who heads the office and the Office Superintendent) and
"Contact Information" with the office address. The pages do not list the election wards of each office (no "wards" key).
Records: level "zone", area "Ward Committee <n>". Record ids: dept:ward2n_bhiwandi:wc<n>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_bhiwandi"
BODY, LGD, STATE, DISTRICT = "Bhiwandi-Nizampur Shahar Mahanagarpalika", "251477", "MH", "Thane"
URL = "https://www.bncmc.gov.in/department.php?department_id={id}"
OFFICES = {1: 53, 2: 54, 3: 55, 4: 56, 5: 57}


def items(get=None):
    return [{"key": f"{MODULE}-wc{n}", "payload": {"reader": MODULE, "url": URL.format(id=i), "state": STATE, "office": n}}
            for n, i in OFFICES.items()]


def parse(html, p):
    soup = _esw.soup(html)
    n = p["office"]
    area = f"Ward Committee {n}"
    h = soup.find(string=re.compile(r"Ward Committee No\.?\s*\d"))
    if h:
        m = re.search(r"No\.?\s*(\d+)", h)
        if m and int(m.group(1)) != n:
            return []
    text = _esw.clean(soup.get_text(" "))
    m = re.search(r"Address:\s*(.*?)\s*Contact:\s*([\d\s/()-]+)", text)
    address, office_phone = (m.group(1), m.group(2)) if m else ("", "")
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "Name", "Designation", "Mobile", soup=soup)[:1]:
        for r in rows:
            post = _ward.col(r, "Designation")
            name = re.sub(r"^-+$", "", _ward.col(r, "Name"))
            if not post:
                continue
            post = re.sub(r"(?i)commisioner", "Commissioner", post)
            post = post[0].upper() + post[1:]
            recs.append(_ward.record(MODULE, f"wc{n}:{_esw.slug(post)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                     level="zone", area=area, zone=area, post=post, name=name,
                                     phone=re.sub(r"^-+$", "", _ward.col(r, "Mobile")), email=_ward.col(r, "Email"),
                                     address=address, office_phone=_esw.clean(office_phone) or None,
                                     wing="administration" if re.search(r"(?i)commissioner|superintendent", post) else None,
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, f"wc{p['office']}", r.content)], "" if recs else "no officer table"
