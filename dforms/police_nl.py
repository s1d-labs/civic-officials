"""Nagaland: police rows on the S3WaaS district helpline pages (<district>.nic.in/helpline/). Works from outside India.
Tables "Sl. No | Department/Organization/Agency | Contact Number" (Kohima, Dimapur) or "Sl.No | Police Station/Outpost |
Contact No." (Phek). Kohima lists each station twice: "OC North PS" (the officer in charge's CUG) and "North PS" (the station's
line); both go on one record (phone = OC first). SP / Commissioner rows are district offices, SDPO rows subdivision offices.
police_mn uses rows() for Manipur. One queue item = one district page. Record id dept:police_nl:<district>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import clean, gz, phones, rec, slug
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_nl"
OC = re.compile(r"^(?:Police Station\s*[–-]\s*)?(?:O/?C|I/?C|OC|IC)\s+(.+)$", re.I)
PS = re.compile(r"\b(P\.?S\.?|Police Station|Out-?\s?Post|Police Post|PP)\b", re.I)
SKIP = re.compile(r"traffic|helpline|control room|crime|cyber cell|fire|hospital", re.I)
DIST = re.compile(r"^(Superintendent of Police|Commissioner of Police|SP)\b", re.I)
SUBDIV = re.compile(r"^SDPO\b", re.I)


def base(name):
    """'North PS' / 'Women Police Station' / 'Kohima North P.S.' -> 'North' / 'Women' / 'Kohima North'."""
    b = re.sub(r"\s*\b(P\.?S\.?|Police Station)\s*$", "", name, flags=re.I).strip(" .-–")
    return b or name


def rows(html, where=None):
    """(label, number cell, officer cell or None, table is a station list) for every row of every table."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        head = [clean(c.get_text(" ", strip=True)) or "" for c in trs[0].find_all(["th", "td"])]
        station_list = any(re.search(r"police station|outpost", h, re.I) for h in head)
        officer_col = next((i for i, h in enumerate(head) if re.search(r"officer", h, re.I)), None)
        for tr in trs[1:]:
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]
            if len(c) < 3 or c[1] == head[1]:
                provenance.skip_row(tr, 'skip: len(c) < 3 or c[1] == head[1]')
                continue
            officer = c[officer_col] if officer_col is not None and officer_col < len(c) else None
            out.append((c[1], c[-1], officer, station_list))
            if where is not None:
                where.append(_civic.tr_pos(tr))
    return out


def last_updated(html):
    m = re.search(r"Last Updated:?\s*(?:<[^>]+>\s*)*(\d{2})[./-](\d{2})[./-](\d{4})", html)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def records(module, html, p):
    state, district, url = p["state"], p["district"], p["url"]
    upd = last_updated(html)
    by = {}
    order = []
    where, pos_of = [], {}
    for ri, (label, num, officer, station_list) in enumerate(rows(html, where)):
        ph = phones(num)
        if not ph or re.fullmatch(r"x+", num or "", re.I):
            provenance.skipped('skip: not ph or re.fullmatch(r"x+", num or "", re.I)')
            continue
        m = OC.match(label)
        if DIST.match(label) or SUBDIV.match(label):
            level = "district" if DIST.match(label) else "subdivision"
            key = f"{slug(district)}:{slug(label)}"
            by[key] = dict(level=level, area=district if level == "district" else label, post=label, phone=ph)
            order.append(key)
            pos_of[key] = [where[ri]]
            continue
        if not (station_list or m or PS.search(label)) or SKIP.search(label):
            provenance.skipped('skip: not (station_list or m or PS.search(label)) or SKIP.search(label)')
            continue
        name = m.group(1) if m else label
        post_kind = "police post" if re.search(r"out-?\s?post|police post|\bPP\b", name, re.I) else "police station"
        b = base(name) if post_kind == "police station" else name
        key = f"{slug(district)}:{slug(b)}"
        d = by.get(key)
        if d is None:
            d = by[key] = dict(level="police_station", area=f"{b} PS" if post_kind == "police station" else b, office_type=post_kind,
                               post="Officer in charge")
            order.append(key)
        pos_of.setdefault(key, []).append(where[ri])
        if m:
            d["oc_phone"] = ph
        else:
            d["station_phone"] = ph
        if officer and officer.lower() != "office":
            d["name"] = officer
    recs = []
    for key in order:
        d = by[key]
        ph = phones(d.pop("oc_phone", None), d.pop("station_phone", None), d.pop("phone", None))
        ps = pos_of.get(key) or []
        recs.append(rec(module, key, **d, phone=ph, state=state, district=district, source=url, last_updated=upd,
                        src_pos=ps[0] if len(ps) == 1 else {"rows": ps}))
    return recs


def fetch(p, get, module=M):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(module, f"{slug(p['district'])}.html", r.content)]
    recs = records(module, r.text, p)
    return recs, files, "" if recs else "no police rows"
