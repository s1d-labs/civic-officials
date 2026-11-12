"""Delhi: New Delhi Municipal Council (LGD 276447), ndmc.gov.in/council_members.aspx (ASP.NET, server-rendered; saved in
archive.s1d.me 2026-11-11, status 200). Not India-only for the archive copy; the live site answers from Germany (not tested
again on 2026-11-11 because the archive copy is one day old).

Two tables, "Members" and "Ex-Officio Members". Each entry: <strong>name</strong>, then the post ("Chairperson & Member, NDMC",
"Member & Vice Chairperson, NDMC", "Additional Secretary (UT) & Member, NDMC", "MLA & Member, NDMC") and office / residence
lines; the next cell gives "Phone:" and "Email:". Records: one per named person. Roles: the Chairperson is appointed by the
Central Government and is the executive head of the Council (there is no Commissioner), so the Chairperson record gets role
"head" (role_note says why); Vice Chairperson -> deputy; every other member -> member (also the Union and Delhi secretaries who
sit as members: role_of() would read "Secretary" as a head). An entry with "-" as the name is left out. The "Ex-Officio Members"
table (the MP and MLAs of the area, in one cell each) is not read: civic-india sql/60 has the legislators.
The page shows no date.
Delhi Cantonment Board (X-DL-CANT) is not read: archive.s1d.me has no copy of a Cantonment Board page that names its officers.
"""
import re

from dforms import _esw, _ulb

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_dl"
STATE = "DL"
URL = "https://ndmc.gov.in/council_members.aspx"
P = {"body": "New Delhi Municipal Council", "district": "New Delhi", "lgd_code": "276447", "body_type": "NCT Municipal Council"}


def items(get=None):
    return [{"key": MODULE + "-ndmc", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": False}}]


def lines(td):
    return [x for x in (_esw.clean(s) for s in _esw.cell_text(td).split(" | ")) if x]


def parse(html, url=URL):
    cut = html.find("Ex-Officio Members")
    soup = _esw.soup(html[:cut] if cut > 0 else html)
    recs, seen = [], set()
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        strong = next((td.find("strong") for td in tds if td.find("strong")), None)
        if not strong or len(tds) < 2:
            continue
        name = _esw.clean(strong.get_text(" "))
        td = strong.find_parent("td")
        rest = lines(td)
        rest = rest[1:] if rest and rest[0] == name else rest
        post = rest[0] if rest else ""
        if not re.search(r"(?i)member|chair", post) or re.match(r"^\W*$", name) or re.search(r"(?i)designation", name):
            continue
        contact = " ".join(_esw.cell_text(x) for x in tds[tds.index(td) + 1:]) if td in tds else ""
        phone = _esw.phones(re.sub(r"(?i)\(fax\)|\d[\d -]*\(fax\)", " ", contact.split("Email")[0]))
        email = _esw.emails(contact)
        address = "; ".join(x for x in rest[1:] if not re.match(r"(?i)residence", x)) or None
        rid, d = _ulb.record(MODULE, STATE, P["body"], re.sub(r"(?i),\s*ndmc\s*$", "", post), seen, name=name, phone=phone,
                             email=email, district=P["district"], body_type=P["body_type"], source=url, lgd_code=P["lgd_code"],
                             address=address)
        if re.match(r"(?i)chairperson", post):
            d["role"], d["role_note"] = "head", "NDMC Act 1994: the Chairperson is the executive head; NDMC has no Commissioner"
        else:
            d["role"] = "deputy" if re.search(r"(?i)vice\s*chair", post) else "member"
        recs.append((rid, d))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "council-members", r.content)], "" if recs else "no rows"
