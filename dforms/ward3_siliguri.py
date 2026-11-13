"""Siliguri Municipal Corporation (www.siligurismc.in, plain PHP site): the officers of its 5 borough offices (wards 1-47) and the
sub-assistant engineers of each borough. Pages read (live sample 2026-11-13 from Mumbai, not in archive.s1d.me; route unchecked):
  borough-i.php, borough---ii.php ... borough---v.php   one page per borough (div.workingTextsWraper): a head line "Name of the
       Borough Officer with Contact No. : Sri X, Mobile : 9...", "Wards under this Borough : 36, 37, ...", then one table
       "Name of the Section | Their Activities | Required Documents | Concerned Person (head) and his/her contact number" (one
       or more people per cell, each "Name(designation) Mobile : number").
  public-works-department-pwd.php   table "Sl. No | Name | Designation | Phone": the assistant engineer and the sub-assistant
       engineers of the head office ("HO") and of each borough ("Sub-Assistant Engineer, Borough - IV").
One queue item reads all six pages (the PWD rows get their wards from the borough pages). Records: borough officer and section
heads at level "zone" (area "Borough No. V", wards = the borough's wards); head-office engineers at level "body".
Record ids: dept:ward3_siliguri:borough-<n>:<post slug>:<name slug or phone>.
"""
import re

from dforms import _esw, _ward

METHOD = "html tables + head lines (bs4)"     # source trail (provenance.py)

MODULE = "ward3_siliguri"
BODY, LGD, STATE, DISTRICT = "Siliguri Municipal Corporation", "249957", "WB", "Darjeeling"
BASE = "https://www.siligurismc.in/"
BOROUGHS = (("I", "borough-i.php"), ("II", "borough---ii.php"), ("III", "borough---iii.php"), ("IV", "borough---iv.php"),
            ("V", "borough---v.php"))
PWD = "public-works-department-pwd.php"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
MOB = re.compile(r"(?i)mob(?:ile)?\.?\s*[:\-]?\s*((?:\+?91)?[\d][\d\- ]{6,}\d)?")
HON = re.compile(r"(?:^|(?<=[\s.]))(?:Sri|Smt|Shri|Mr|Mrs|Ms)\b\.?\s*")
ABBR = {"S.I.": "Sanitary Inspector", "S.I": "Sanitary Inspector", "S.C.I": "Senior Conservancy Inspector",
        "S.C.I.": "Senior Conservancy Inspector", "SAE": "Sub-Assistant Engineer", "SAE,": "Sub-Assistant Engineer",
        "U.D.C": "Upper Division Clerk", "U.D.C.": "Upper Division Clerk"}


def items(get=None):
    return [{"key": f"{MODULE}-boroughs", "payload": {"reader": MODULE, "url": BASE + BOROUGHS[0][1], "state": STATE,
                                                       "route": "abroad", "route_note": "route unchecked: answered from Mumbai"}}]


def people(cell):
    """[(name, designation, phone)] of one 'Concerned Person' cell."""
    out, last = [], 0
    chunks = []
    cell = cell.replace("|", " ")
    for m in MOB.finditer(cell):
        chunks.append((cell[last:m.start()], (m.group(1) or "").strip()))
        last = m.end()
    tail = cell[last:]
    if _esw.clean(tail):
        chunks.append((tail, ""))
    for text, phone in chunks:
        names = [n for n in (_esw.clean(x).strip(" ,.;") for x in HON.split(text)) if n]
        for i, n in enumerate(names):
            desig = ""
            m = re.search(r"\(([^()]*)\)\s*$", n)
            if m and (re.search(r"(?i)assist", m.group(1)) or re.fullmatch(r"[A-Z.,\s]+", m.group(1))):
                desig, n = m.group(1).strip(" ,"), n[:m.start()].strip()
            m2 = re.search(r"\s+(S\.C\.I\.?|S\.I\.?)$", n)
            if m2:
                desig, n = m2.group(1), n[:m2.start()].strip()
            m3 = re.search(r"(?i)work\s*assist\w*\)?$", n)
            if m3:
                desig, n = "Work Assistant", n[:m3.start()].strip()
            desig = ABBR.get(desig, desig.replace("Assistent", "Assistant"))
            out.append((n.strip(" .,"), desig, phone if i == len(names) - 1 else ""))
    return [(n, d, p) for n, d, p in out if n or p]


def head(div):
    """(officer name, phone, wards) from the head lines of a borough page."""
    t = _esw.clean(div.get_text(" "))
    m = re.search(r"(?i)name\s+of\s+the\s+borough\s+officer[^:]*?[:\-]+\s*(.+?)\s*(?:,|\s)\s*(?:mob(?:ile)?|phone|contact\s*no)\.?"
                  r"\s*[:\-]*\s*([+\d][\d\- ]{6,}\d)", t)
    w = re.search(r"(?i)wards\s+under\s+this\s+borough\s*[:\-]*\s*([\d,\s&]+)", t)
    name = re.sub(r"(?i)^(sri|smt|shri|mr|mrs)\.?\s*", "", m.group(1)).strip(" ,") if m else ""
    return name, (m.group(2).strip() if m else ""), _ward.wards_of(w.group(1)) if w else []


def parse_borough(html, n, url, seen):
    soup = _esw.soup(html)
    div = soup.find("div", class_="workingTextsWraper") or soup
    name, phone, wards = head(div)
    area = f"Borough No. {n}"
    recs = []
    if name or phone:
        recs.append(_ward.record(MODULE, f"borough-{ROMAN[n]}:borough-officer", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=area, zone=area, post="Borough Officer", name=name,
                                 phone=phone, wards=wards, wing="administration", role="head", source=url,
                                 src_pos={"selector": "div.workingTextsWraper", "line": "Name of the Borough Officer"}))
    t = div.find("table")
    if t is None:
        return recs, wards
    for row, pos in _ward.grid_pos(t):
        if len(row) < 4 or re.search(r"(?i)name\s+of\s+the\s+section", row[0]):
            continue
        section = _esw.clean(row[0]).strip(" .")
        for pname, desig, ph in people(row[3]):
            if re.fullmatch(r"(?i)borough\s*officer", section):
                if name:
                    continue        # the head line already gave the borough officer
                post = "Borough Officer"
            else:
                post = f"{desig}, {section}" if desig else f"Section Head, {section}"
            recs.append(_ward.record(MODULE, f"borough-{ROMAN[n]}:{_esw.slug(section)}:{_esw.slug(pname) or ph}", seen, body=BODY,
                                     lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=area, zone=area, post=post,
                                     name=pname, phone=ph, wards=wards, wing=_ward.wing_of(section + " " + desig),
                                     duties=_esw.clean(row[1]) or None, source=url, src_pos=pos))
    return recs, wards


def parse_pwd(html, url, wards_of_borough, seen):
    recs = []
    for head_, rows in _ward.header_tables(html, "name", "designation"):
        for r in rows:
            name, desig, ph = _ward.col(r, "name"), _ward.col(r, "designation"), _ward.col(r, "phone")
            if not (name or ph):
                continue
            m = re.search(r"(?i)borough\s*-?\s*(IV|V|III|II|I)\b", desig)
            if m:
                n = m.group(1).upper()
                area = f"Borough No. {n}"
                kw = dict(level="zone", area=area, zone=area, wards=wards_of_borough.get(n))
                key = f"borough-{ROMAN[n]}"
            else:
                kw, key = dict(level="body", area=BODY), "ho"
            recs.append(_ward.record(MODULE, f"{key}:pwd:{_esw.slug(name) or ph}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, post=desig, name=name, phone=ph.replace(" / ", ", "),
                                     wing="engineering", source=url, src_pos=r.pos, **kw))
    return recs


def fetch(p, get):
    seen, recs, files, wards = set(), [], [], {}
    for n, path in BOROUGHS:
        url = BASE + path
        r = get(url)
        if r is None:
            continue
        files.append(_esw.keep(MODULE, f"borough-{ROMAN[n]}", r.content))
        got, w = parse_borough(r.text, n, url, seen)
        wards[n] = w
        recs += _ward.tag(got, r, url, METHOD)
    r = get(BASE + PWD)
    if r is not None:
        files.append(_esw.keep(MODULE, "pwd", r.content))
        recs += _ward.tag(parse_pwd(r.text, BASE + PWD, wards, seen), r, BASE + PWD, METHOD)
    if not files:
        return [], [], "no answer"
    return recs, files, "" if recs else "no officers found"
