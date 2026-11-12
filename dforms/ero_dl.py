"""Delhi: EROs and AEROs of all 70 assembly constituencies, from the CEO Delhi site (ceodelhinet.nic.in). Answers only from India.

Two pages, one plain GET each, one HTML table of 70 rows, no paging:
- page "ero": EROContactn.aspx (table ..._EROContacts): S. No., AC No., AC Name, Distt. Name, ERO Name, Designation (SDM / ADM),
  Address of ERO's Office, Phone Office, Mobile Number, Email-ID ([at]/[dot]), Fax.
- page "aero": NewContactPagen.aspx (table ..._GrdContact): the AERO in charge of the AC's Voter Registration and EPIC Centre, with the
  centre's address, phone, mobile, fax, email.
The pages show no date. One queue item = one page.
Record ids: dept:ero_dl:DL-AC-<no>:ero and dept:ero_dl:DL-AC-<no>:aero:voter-centre.
"""
from dforms import _esw
from dforms._water import pgrid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_dl"
BASE = "https://ceodelhinet.nic.in/ceodelhiweb/"
PAGES = {"ero": ("EROContactn.aspx", "ctl00_ContentPlaceHolder1_EROContacts"),
         "aero": ("NewContactPagen.aspx", "ctl00_ContentPlaceHolder1_GrdContact")}


def items(get=None):
    return [{"key": f"{MODULE}-{pg}", "payload": {"reader": MODULE, "url": BASE + f, "state": "DL", "page": pg, "india_only": True}}
            for pg, (f, _) in PAGES.items()]


def _col(c, *names):
    for k, v in c.items():
        if any(n in k for n in names):
            return v
    return ""


def parse(html, page, url):
    soup = _esw.soup(html)
    t = soup.find("table", id=PAGES[page][1]) or max(soup.find_all("table"), key=lambda x: len(x.find_all("tr")), default=None)
    if t is None:
        return []
    rows = pgrid(t)
    head = [h.lower() for h in rows[0]] if rows else []
    recs = []
    for row in rows[1:]:
        c = dict(zip(head, row))
        no = _col(c, "ac no").strip()
        if not no.isdigit():
            continue
        ac, name = f"DL-AC-{int(no)}", _col(c, "ac name").title()
        f = dict(dept="elections", level="ac", area=f"{int(no)} - {name}", phone=_esw.phones(_col(c, "phone"), _col(c, "mobile")),
                 email=_esw.emails(_col(c, "email")), state="DL", district=_col(c, "distt"), office_id=ac, source=url)
        if page == "ero":
            recs.append(_esw.record(MODULE, f"{ac}:ero", post="Electoral Registration Officer", designation=_col(c, "designation"),
                                    name=_col(c, "ero name"), address=_col(c, "address"), src_pos=row.pos, **f))
        else:
            recs.append(_esw.record(MODULE, f"{ac}:aero:voter-centre", post="Assistant Electoral Registration Officer",
                                    designation="AERO, Voter Registration and EPIC Centre", name=_col(c, "aero name"),
                                    address=_col(c, "location"), src_pos=row.pos, **f))
    return recs


def fetch(p, get):
    page = p.get("page", "ero")
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, page, r.content)]
    recs = parse(r.text, page, p["url"])
    return recs, files, "" if recs else "no rows"
