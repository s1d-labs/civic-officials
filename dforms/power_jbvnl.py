"""JBVNL (Jharkhand Bijli Vitran Nigam): https://jbvnl.co.in/know-your-officers and https://jbvnl.co.in/hqofficer. Answers from
Germany.

Two queue items. know-your-officers (~500 KB) has one table per office type: Section (Junior Manager, ~277), Sub-Division
(Manager, ~108), Division (Senior Manager, ~44), Circle (Dy. General Manager, ~15), Area Board (General Manager, 7; no phone).
Rows = office type, designation, office name, phone, mail id (+ alternate mail). No officer names and no parent column: the
mail ids carry codes but no tree, so parents are left out. "NOT OPEND" rows (a section not opened yet) are skipped.
hqofficer = headquarters (department, designation, officer name, email), kept as level "state".
The page shows "last updated on - DD-MM-YYYY". About 450 offices + ~12 headquarters officers.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, cells, clean, email, phone, raw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power_jbvnl"
URL = "https://jbvnl.co.in/know-your-officers"
LEVEL = {"section": "section", "sub-division": "subdivision", "subdivision": "subdivision", "division": "division",
         "circle": "circle", "area board": "zone", "area": "zone"}


def updated(html):
    m = re.search(r"(?i)last\s*updated\s*on\s*-?\s*(\d{1,2})-(\d{1,2})-(\d{4})", html)
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def parse_offices(html, url=URL):
    out = Out(MOD, "JH", url, discom="JBVNL", last_updated=updated(html))
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        rows = [cells(tr) for tr in trs]
        head = next((r for r in rows if r and r[0].lower() == "office type"), None)
        if not head:
            continue
        kind = next((clean(c[0]) for c in rows if len(c) >= 4 and clean(c[0]) and c[0].lower() != "office type"), None)
        for c, tr in zip(rows, trs):
            out.src = {"src_pos": tr_pos(tr)}
            if len(c) < 4 or c[0].lower() == "office type":
                provenance.skip_row(c, 'skip: len(c) < 4 or c[0].lower() == "office type"')
                continue
            kind = clean(c[0]) or kind                # Area Board rows leave the type empty after the first one
            level = LEVEL.get((kind or "").lower())
            area = clean(c[2])
            if not level or not area or area.upper().startswith("NOT OPEN"):
                provenance.skip_row(c, 'skip: not level or not area or area.upper().startswith("NOT OPEN")')
                continue
            ph = phone(c[3]) if "@" not in c[3] else None
            mails = [m for m in (email(x) for x in c[3 if ph is None else 4:]) if m]
            key = f"{level}:{area}:{mails[0].split('@')[0]}" if mails else f"{level}:{area}"
            out.add(key, level, area.title(), post=clean(c[1]), phone_=ph, email_=", ".join(mails) or None)
    out.src = {}
    return out.recs


def parse_hq(html, url):
    out = Out(MOD, "JH", url, discom="JBVNL", last_updated=updated(html))
    soup = BeautifulSoup(html, "lxml")
    for tr in soup.find_all("tr"):
        out.src = {"src_pos": tr_pos(tr)}
        c = cells(tr)
        if len(c) < 3 or c[0].lower() == "department":
            provenance.skip_row(tr, 'skip: len(c) < 3 or c[0].lower() == "department"')
            continue
        dept, post, name = clean(c[0]), clean(c[1]), clean(c[2])
        out.add(f"hq:{dept}:{post}:{name}", "state", "JBVNL Headquarters", post=f"{post} ({dept})" if dept else post, name=name,
                email_=email(c[3]) if len(c) > 3 else None)
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    hq = "hqofficer" in url
    files = [raw(MOD, "hqofficer" if hq else "know-your-officers", r.content, "html")]
    recs = parse_hq(r.text, url) if hq else parse_offices(r.text, url)
    return recs, files, "" if recs else "no rows"
