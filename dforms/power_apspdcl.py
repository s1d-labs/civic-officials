"""APSPDCL (Andhra Pradesh Southern Power Distribution): https://www.apspdcl.in/phonenumbers.php. Answers from Germany.

One page, one queue item. Panels (h4.panel-title) = corporate office + 9 circles (Tirupati, Chittoor, Nellore, Sri Sathya Sai,
Anantapur, Kurnool, Nandyal, Kadapa, Annamayya); each row = #, designation, number. No names, no email, no address. The office
is written into the designation ("AE/O/Kallur", "DE / O / Adoni", "DEE/Town/1/Tirupati"): dforms/_power_ap.py reads it.
Rows do not follow the hierarchy in every circle (Kurnool lists all DEs first), so only the circle is given as parent.
About 1,095 rows: ~520 AE section rows, ~150 DEE/ADE sub-division rows, ~65 EE/DE division rows, the rest wing/staff posts.
Some circles list one office twice with the same phone, the post written two ways ("A.E/O/PENUKONDA" and "AE/O/PENUKONDA",
"AE / O / Panyam" and "AE/O/PANYAM"), and the Ananathapur panel repeats ten Sri Sathya Sai offices (Penukonda, Hindupur ...;
the district was split in 2022): a row with a post and phone read before is skipped, so the first panel's copy stays (before,
it became a second record, often "...~2").
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, cells, clean, phone, raw
from dforms._power_ap import classify
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.apspdcl.in/phonenumbers.php"
MOD = "power_apspdcl"


def circle_name(title):
    t = clean(title) or ""
    return clean(re.sub(r"\s*CIRCLE\s*$", "", t, flags=re.I)).title() if t else None


def parse(html, url=URL):
    out = Out(MOD, "AP", url, discom="APSPDCL")
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    for h in soup.select("h4.panel-title"):
        panel = h.find_parent(class_="panel") or h.parent
        title = clean(h.get_text(" ", strip=True))
        corporate = "CORPORATE" in (title or "").upper()
        circ = None if corporate else circle_name(title)
        for tr in panel.select("tbody tr") or panel.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = cells(tr)
            if len(c) < 3 or not clean(c[1]) or c[1].lower() == "designation":
                provenance.skip_row(tr, 'skip: len(c) < 3 or not clean(c[1]) or c[1].lower() == "designation"')
                continue
            desig = clean(c[1])
            key = (re.sub(r"[^a-z0-9]", "", desig.lower()), re.sub(r"\D", "", c[2] or ""))
            if key in seen:
                provenance.skip_row(tr, 'skip: key in seen')
                continue
            seen.add(key)
            if corporate:
                level, area, staff = "state", "APSPDCL Corporate Office", True
            else:
                level, area, staff = classify(desig, "circle", circ)
            out.add(f"{circ or 'corporate'}:{desig}", level, area, post=desig, phone_=phone(c[2]),
                    parents={"circle": circ} if circ and level != "circle" or (circ and staff) else None,
                    staff_post=True if staff else None)
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MOD, "phonenumbers", r.content, "html")]
    recs = parse(r.text, url)
    return recs, files, "" if recs else "no rows"
