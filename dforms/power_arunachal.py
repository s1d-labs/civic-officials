"""Arunachal Pradesh: Department of Power contact list, power.arunachal.gov.in/contact.php. India only (times out from Germany).
One page, one table, one queue item (about 120 rows).

The table has heading rows (one cell: "<X> ELECTRICAL ZONE", "ARUNACHAL PRADESH ELECTRICAL CIRCLE - V, ZIRO", "<X> ELECTRICAL
DIVISION, <town>") and officer rows (Name of Officer, Designation, Mobile, E-Mail ID; email as x [at] y [dot] z). Kept: the head of
each zone (Chief Engineer), circle (Superintending Engineer) and division (Executive Engineer), and the sub-divisions
("Asstt Engr, <town>"). Not kept: staff posts (PA, accounts, plain "Assistant Engineer") and the electrical inspectorate.
Record id dept:power_arunachal:<level>-<office>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, phone, raw

URL = "https://power.arunachal.gov.in/contact.php"
HEADS = {"zone": re.compile(r"^Chief Engineer", re.I), "circle": re.compile(r"^(Superintending Engineer|SE\b)", re.I),
         "division": re.compile(r"^Executive Engineer", re.I)}
SUB = re.compile(r"^(?:Asstt\.?|Assistant)\s*Engr\.?,\s*(.+?)(?:\s+I/C)?$", re.I)


def heading(t):
    """(level, area) of a heading row, or (None, None)."""
    u = t.upper()
    if "INSPECTORATE" in u:
        return "other", t
    if u.endswith("ZONE"):
        return "zone", t.title()
    m = re.search(r"CIRCLE\s*[–-]\s*([IVX]+)\s*,\s*(.+)$", u)
    if m:
        return "circle", f"{m.group(2).title()} (Circle {m.group(1)})"
    m = re.match(r"(.+?)\s+ELECTRICAL DIVISION", u)
    if m:
        return "division", m.group(1).title()
    return None, None


def parse(html, source=URL):
    out = Out("power_arunachal", "AR", source, discom="Department of Power, Arunachal Pradesh")
    soup = BeautifulSoup(html, "lxml")
    cur = {"zone": None, "circle": None, "division": None}
    office_lvl, office = None, None
    for tr in soup.select("table tr"):
        c = cells(tr)
        if len(c) == 1 and c[0]:
            lvl, area = heading(c[0])
            if lvl in cur:
                cur[lvl] = c[0]
                if lvl == "zone":
                    cur["circle"] = cur["division"] = None
                elif lvl == "circle":
                    cur["division"] = None
            office_lvl, office = lvl, (area, c[0])
            continue
        if len(c) < 4 or c[0] == "Name of Officer" or office_lvl in (None, "other"):
            continue
        name, des, mob, em = c[:4]
        par = {"zone": cur["zone"], "circle": cur["circle"], "division": cur["division"]}
        m = SUB.match(des)
        if m:
            town = clean(m.group(1))
            out.add(f"subdivision-{town}", "subdivision", town, post=des, name=name, phone_=phone(mob), email_=email(em),
                    parents={k: v for k, v in par.items()})
        elif HEADS.get(office_lvl) and HEADS[office_lvl].match(des):
            par = {k: v for k, v in par.items() if k != office_lvl and
                   (office_lvl == "division" or (office_lvl == "circle" and k == "zone"))}
            out.add(f"{office_lvl}-{office[0]}", office_lvl, office[0], post=des, name=name, phone_=phone(mob), email_=email(em),
                    parents=par, office=office[1])
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_arunachal", "contact", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no offices"
