"""Puducherry: fire stations and their station officers, from the Fire Service Department's "Officers details" PDF,
fire.py.gov.in/sites/default/files/directory-officers-and-employees.pdf (6 pages; page 1 = 16 officers: No. | Name | Designation |
Office Tel. No.; pages 2-6 = firemen by region with employee codes and no phones, not read). The PDF carries no date
(last_updated is left out); the contact page that links it says "Page last updated date: 05-08-2026". Answers from anywhere.
One queue item, 16 rows.
pypdf layout text: the cells wrap over several lines and the row number sits on the middle line, so each line goes to the nearest
numbered line (a tie goes to the row above), and each line's pieces (split on 2+ spaces) go to the nearest column of the header.
Record ids: dept:civic_fire_py:<slug of station or post>.
"""
import re

from dforms import _civic, _esw

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fire_py"
URL = "https://fire.py.gov.in/sites/default/files/directory-officers-and-employees.pdf"
ROW = re.compile(r"^\s*(\d{1,2})\.\s+\S")
STATION = re.compile(r"(?i)(?:of\s+)?([A-Za-z’'. ]+?)\s+Fire\s+Station")
DISTRICTS = {"mahe": "Mahe", "yanam": "Yanam", "karaikal": "Karaikal", "surakudy": "Karaikal"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "PY", "india_only": False, "expected": 16}}]


def columns(header):
    """Start columns of 'Name', 'Designation', 'Office Tel' in the header line."""
    return [header.find(w) for w in ("Name", "Designation", "Office Tel")]


def rows(text):
    """[(no, name, designation, phones)] from page 1's layout text."""
    lines = text.split("\n")
    head = next((i for i, x in enumerate(lines) if "Designation" in x and "Name" in x), None)
    if head is None:
        return []
    cols = columns(lines[head])
    body = []
    for x in lines[head + 1:]:
        if re.match(r"^\s*Sl\.?\s*No", x):
            break
        body.append(x)
    nums = [i for i, x in enumerate(body) if ROW.match(x)]
    if not nums:
        return []
    cells = {i: ["", "", ""] for i in nums}
    for i, x in enumerate(body):
        if not x.strip():
            continue
        owner = min(nums, key=lambda n: (abs(n - i), n > i))
        for m in re.finditer(r"\S(?:.*?\S)?(?=\s{2,}|\s*$)", x):
            piece, at = m.group(0), m.start()
            if i == owner and at < cols[0] and ROW.match(piece + " x"):
                continue
            k = min(range(3), key=lambda c: abs(cols[c] - at))
            cells[owner][k] = (cells[owner][k] + " " + piece).strip()
    out = []
    for n in nums:
        no = ROW.match(body[n]).group(1)
        name, post, tel = (_esw.clean(c) for c in cells[n])
        out.append((no, re.sub(r"^\d{1,2}\.\s*", "", name), post, tel))
    return out


def parse(text, url=URL):
    recs, seen = [], set()
    for no, name, post, tel in rows(text):
        post = re.sub(r"\s*-\s*", "-", post).replace("Officer-Additional", "Officer - Additional")
        m = STATION.search(post)
        station = _esw.clean(m.group(1)) if m else ""
        station = re.sub(r"(?i)^(station officer|officer in-charge|additional charge)[-,\s]*(of\s+)?", "", station).strip(" ,-")
        level = "facility" if station else "state"
        rank = re.split(r"[,]|\bof\b|-\s*Additional", post)[0].strip(" ,-") if station else post
        if station and "additional charge" in post.lower():
            rank = "Station Officer (Additional Charge)"
        key = _civic.unique(_esw.slug(station or post), seen)
        recs.append(_civic.record(
            MODULE, key, "fire", dept="fire", level=level, area=station or "Puducherry",
            office=f"{station} Fire Station" if station else "Fire Service Department, Puducherry", post=rank,
            name=re.sub(r"(?i)^thiru\.?\s*", "", name), name_title=name,
            phone=_esw.phones(tel), district=DISTRICTS.get(station.lower(), "Puducherry") if station else None, state="PY",
            office_id=f"PY-FIRE-{key}", row_no=int(no), source=url))
    return recs


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "officers", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    recs = parse(pages[0], p.get("url", URL)) if pages else []
    return recs, files, "" if recs else "no rows"
