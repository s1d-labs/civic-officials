"""HPSEBL (Himachal Pradesh State Electricity Board Ltd): the contact list page
www.hpseb.in/irj/go/km/docs/internet/New_Website/Pages/contactlist.html. India only. One queue item (one page, about 600 rows).
The page is a run of small tables in hierarchy order: a one-cell heading row names the office ("CHIEF ENGINEER SHIMLA ZONE",
"SUPERINTENDING ENGINEER (OP) NAHAN", "THEOG (Sr Executive Engineer Electrical)"), the next row gives its officer (name,
landline, mobile), and 4-cell rows (Name, Subdivison, Landline, Mobile) list the Assistant Engineers of the division's
sub-divisions. Levels: zone (CE), circle (SE OP), division (Sr. XEN), sub-division (AE/AEE). The tables after
"CHIEF ENGINEER (ES)" are transmission and system offices (ES, P&T, design): left out.
Record id dept:power_hpsebl:<division>:<sub-division> (sub-divisions) or dept:power_hpsebl:<level>:<office>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, cells, clean, phone, raw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_hpsebl"
URL = "https://www.hpseb.in/irj/go/km/docs/internet/New_Website/Pages/contactlist.html"


def heading(text):
    """(level, office name) of a one-cell heading row, or (None, None)."""
    t = " ".join(text.split())
    m = re.match(r"(?i)^CHIEF ENGINEER\s+(.*\bZONE)$", t)
    if m:
        return "zone", m.group(1).title()
    if re.match(r"(?i)^CHIEF ENGINEER\s*\(", t):
        return "stop", t                       # CE (ES): transmission offices follow
    m = re.match(r"(?i)^SUPERINTENDING ENGINEER\s*\(OP\)\s*(.+)$", t)
    if m:
        return "circle", "Operation Circle " + m.group(1).title()
    if re.match(r"(?i)^(SUPERINTENDING ENGINEER|SE)\b", t):
        return "other", t
    m = re.match(r"(?i)^(.+?)\s*\(Sr\.? Executive Engineer Electrical\)\s*(.*)$", t)
    if m and m.group(1) and not m.group(1).startswith("("):
        return "division", " ".join((m.group(1).title() + " " + m.group(2)).split())
    return None, None


def parse(html, url=URL):
    out = Out(MOD, "HP", url, discom="HPSEBL")
    soup = BeautifulSoup(html, "lxml")
    zone = circle = division = None
    lvl = office = None
    head_taken = True
    skip = False
    for t in soup.find_all("table"):
        if t.find("table"):
            continue                           # wrapper tables: their rows are read from the inner tables
        for tr in t.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = [x for x in cells(tr)]
            if not any(c):
                provenance.skip_row(tr, 'skip: not any(c)')
                continue
            if len(c) == 1:
                k, name = heading(c[0])
                if k == "stop":
                    skip = True
                if k == "zone":
                    skip = False
                if skip or k in (None, "other"):
                    if k == "other":
                        lvl = None
                    continue
                lvl, office, head_taken = k, name, False
                if k == "zone":
                    zone, circle, division = name, None, None
                elif k == "circle":
                    circle, division = name, None
                elif k == "division":
                    division = name
                continue
            if skip or lvl is None:
                provenance.skip_row(tr, 'skip: skip or lvl is None')
                continue
            if c[0].lower() == "name":
                provenance.skip_row(tr, 'skip: c[0].lower() == "name"')
                continue
            if len(c) in (2, 3) and not head_taken:
                # the officer of the office named in the heading
                tel = phone(c[1]), phone(c[2]) if len(c) > 2 else None
                par = {"zone": zone if lvl != "zone" else None, "circle": circle if lvl == "division" else None}
                post = {"zone": "Chief Engineer", "circle": "Superintending Engineer (OP)",
                        "division": "Sr. Executive Engineer (Electrical)"}[lvl]
                out.add(f"{lvl}:{office}", lvl, office, post=post, name=c[0], phone_=", ".join(x for x in tel if x) or None,
                        parents=par)
                head_taken = True
                continue
            if len(c) == 4 and lvl == "division":
                name, sub, land, mob = c
                if not clean(sub):
                    provenance.skip_row(tr, 'skip: not clean(sub)')
                    continue
                out.add(f"{division}:{sub}", "subdivision", sub, post="Assistant Engineer (sub-division)", name=name,
                        phone_=phone(land, mob), parents={"zone": zone, "circle": circle, "division": division})
            else:
                provenance.skip_row(tr, 'skip: not (len(c) == 4 and lvl == "division")')
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, "contactlist", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
