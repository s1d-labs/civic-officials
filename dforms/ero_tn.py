"""Tamil Nadu: the ERO and the AERO of all 234 assembly constituencies and the 38 District Election Officers, from the CEO's
erolls.tn.gov.in pages ERO.aspx, AERO.aspx and DEO.aspx (acwithcandidate_be2019). Answers only from India.

ERO.aspx / AERO.aspx are ASP.NET forms: GET the page, then POST its hidden fields with ctl00$ContentPlaceHolder1$ddl_District=<id>
and btn_Submit=Submit (the same as a visitor who picks a district). The reply has one table: Sl.No, "No & Name of Assembly"
("11 - Dr.Radhakrishnan Nagar"), name, designation + office address ("ZONAL OFFICER/ ERO, | GCC ZONE-4, No.266, T.H Road ..."),
mobile. One queue item = one page and one district (38 + 38); DEO.aspx is one plain table (one GET, "Last Updated on 05/03/2025").
Record ids: dept:ero_tn:TN-AC-<no>:ero, dept:ero_tn:TN-AC-<no>:aero:<slug of designation>, dept:ero_tn:TN-DEO-<district>.
"""
import re

from dforms import _esw
from forms.aspnet import hidden
from dforms._water import pgrid
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_tn"
BASE = "https://www.erolls.tn.gov.in/acwithcandidate_be2019/"
DIST = "ctl00$ContentPlaceHolder1$ddl_District"
SUBMIT = "ctl00$ContentPlaceHolder1$btn_Submit"
POST = {"ero": "Electoral Registration Officer", "aero": "Assistant Electoral Registration Officer"}
# the district dropdown of ERO.aspx and AERO.aspx (the same ids on both pages)
DISTRICTS = {"31": "ARIYALUR", "35": "CHENGALPATTU", "2": "CHENNAI", "13": "COIMBATORE", "18": "CUDDALORE", "6": "DHARMAPURI",
             "14": "DINDIGUL", "11": "ERODE", "33": "KALLAKURICHI", "3": "KANCHEEPURAM", "30": "KANNIYAKUMARI", "15": "KARUR",
             "5": "KRISHNAGIRI", "24": "MADURAI", "38": "MAYILADUTHURAI", "19": "NAGAPATTINAM", "10": "NAMAKKAL", "17": "PERAMBALUR",
             "22": "PUDUKKOTTAI", "27": "RAMANATHAPURAM", "37": "RANIPET", "9": "SALEM", "23": "SIVAGANGA", "34": "TENKASI",
             "21": "THANJAVUR", "12": "THE NILGIRIS", "25": "THENI", "1": "THIRUVALLUR", "20": "THIRUVARUR", "28": "THOOTHUKUDI",
             "16": "TIRUCHIRAPPALLI", "29": "TIRUNELVELI", "36": "TIRUPATHUR", "32": "TIRUPPUR", "7": "TIRUVANNAMALAI", "4": "VELLORE",
             "8": "VILUPPURAM", "26": "VIRUDHUNAGAR"}
NO = re.compile(r"^\s*(\d{1,3})\s*[-–.]\s*(.+?)\s*$")


def items(get=None):
    out = [{"key": f"{MODULE}-deo", "payload": {"reader": MODULE, "url": BASE + "DEO.aspx", "state": "TN", "page": "deo",
                                               "india_only": True}}]
    for page in ("ero", "aero"):
        for v, name in sorted(DISTRICTS.items(), key=lambda x: int(x[0])):
            out.append({"key": f"{MODULE}-{page}-d{v}", "payload": {"reader": MODULE, "url": BASE + page.upper() + ".aspx", "state": "TN",
                                                                    "page": page, "district_value": v, "district": name.title(),
                                                                    "india_only": True}})
    return out


def _table(html):
    """(header, rows) of the first table that has an 'Sl.No' header."""
    for t in _esw.soup(html).find_all("table"):
        g = pgrid(t)
        if g and g[0] and g[0][0].lower().startswith("sl"):
            return [h.lower() for h in g[0]], g[1:]
    return [], []


def _col(head, row, *words):
    for h, v in zip(head, row):
        if all(w in h for w in words):
            return v
    return ""


def parse(html, page, district=None, url=None, src=None):
    """src: provenance.at() of the answer read (the postback: the same url as the first GET)."""
    src = src or {}
    head, rows = _table(html)
    recs, seen = [], set()
    if page == "deo":
        m = re.search(r"Last Updated on\s*(\d{2})/(\d{2})/(\d{4})", html)
        upd = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        for r in rows:
            m = NO.match(_col(head, r, "district"))
            if not m:
                continue
            dist = m.group(2).title()
            key = f"TN-DEO-{_esw.slug(dist)}"
            recs.append(_esw.record(MODULE, key, dept="elections", level="district", area=dist, post="District Election Officer",
                                    designation=_col(head, r, "designation"), name=_col(head, r, "name of the deo"),
                                    phone=_esw.phones(_col(head, r, "contact")), email=_esw.emails(_col(head, r, "email")),
                                    state="TN", district=dist, office_id=key, source=url or BASE + "DEO.aspx", last_updated=upd,
                                    src_pos=getattr(r, "pos", None)))
        return recs
    for r in rows:
        m = NO.match(_col(head, r, "assembly"))
        if not m:
            continue
        no, ac = int(m.group(1)), m.group(2)
        desig, _, addr = _col(head, r, "designation").partition(" | ")
        desig = desig.strip(" ,")
        office = f"TN-AC-{no}"
        key = f"{office}:ero" if page == "ero" else f"{office}:aero:{_esw.slug(desig) or _esw.slug(_col(head, r, f'name of the {page}'))}"
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", level="ac", area=f"{no} - {ac}", post=POST[page], designation=desig,
                                name=_col(head, r, f"name of the {page}"), phone=_esw.phones(_col(head, r, "mobile")), address=addr,
                                state="TN", district=district, office_id=office, source=url or BASE + page.upper() + ".aspx",
                                src_pos=getattr(r, "pos", None), **src))
    return recs


def fetch(p, get):
    page, url = p["page"], p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if page == "deo":
        recs = parse(r.text, page, url=url)
        return recs, [_esw.keep(MODULE, "deo", r.content)], "" if recs else "no rows"
    d = hidden(r.text)
    d.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", DIST: p["district_value"], SUBMIT: "Submit"})
    r2 = get(url, method="POST", data=d)
    if r2 is None:
        return [], [], "postback did not answer"
    files = [_esw.keep(MODULE, f"{page}-d{p['district_value']}", r2.content)]
    recs = parse(r2.text, page, p.get("district"), url, provenance.at(r2, url))
    return recs, files, "" if recs else "no rows"
