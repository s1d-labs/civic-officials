"""Thoothukudi City Municipal Corporation (thoothukudicorporation.com, the corporation's own site): its 4 zones (North, South,
East, West) with their wards, and each zone's Assistant Commissioner, Junior Engineer and Sanitary Officer. Three pages, read by
one item (live samples from Mumbai, dev-vps-3, 2026-11-13; not in archive.s1d.me; the pages show no date):
  /downloads/general-info-zones-and-wards   one table: Zone | Wards ("21-29,38-41,46,47") | Total number of wards
  /departments/zone                         one table per zone office: heading = the post ("ASSISTANT COMMISSIONER(ZONE)(i/c)"),
                                            rows Name | Address (names the zone) | Phone No, then other posts of the office
                                            as label | name rows ("JUNIOR ENGINEER | AMAL RAJ"; empty = no one named)
  /departments/sanitation                   one table per zone: heading "NORTH ZONE (Sanitary Officer)", Name | Address | Phone No
The zone of a block is the one its heading or address names. The office phone is given to the Assistant Commissioner and the
Sanitary Officer; a Junior Engineer row has a name only. Route: answers from India (dev-vps-3); abroad unchecked.
Records: level "zone" (area "North Zone"), wards from the zones page. Record ids: dept:ward3_thoothukudi:<zone slug>:<post slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_thoothukudi"
BODY, LGD, STATE, DISTRICT = "Thoothukudi City Municipal Corporation", "252970", "TN", "Thoothukudi"
BASE = "https://thoothukudicorporation.com"
URL = BASE + "/departments/zone"
WARDS_URL = BASE + "/downloads/general-info-zones-and-wards"
SAN_URL = BASE + "/departments/sanitation"
ZONE = re.compile(r"(?i)\b(north|south|east|west|central)\s*zone\b")


def items(get=None):
    return [{"key": f"{MODULE}-zones", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def zone_of(*texts):
    for t in texts:
        m = ZONE.search(t or "")
        if m:
            return m.group(1).title() + " Zone"
    return None


def zone_wards(html):
    """{"North Zone": ([wards], src_pos)} of the zones page."""
    out = {}
    soup = _esw.soup(html)
    for ti, t in enumerate(soup.find_all("table"), 1):
        for ri, tr in enumerate([x for x in t.find_all("tr") if x.find_parent("table") is t], 1):
            cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) >= 2 and zone_of(cells[0]):
                out[zone_of(cells[0])] = (_ward.wards_of(cells[1]), {"table": ti, "row": ri})
            else:
                provenance.skip_row(tr, 'skip: not (len(cells) >= 2 and zone_of(cells[0]))')
    return out


def post_name(s):
    s = _esw.clean(s)
    s = re.sub(r"(?i)\(\s*zone\s*\)", "", s)
    s = re.sub(r"(?i)^(north|south|east|west|central)\s*zone\s*\((.*)\)$", r"\2", s)
    ic = bool(re.search(r"(?i)\(\s*i/?c\s*\)", s))
    s = re.sub(r"(?i)\(\s*i/?c\s*\)", "", s).strip(" ()")
    s = " ".join(w.capitalize() if w.isupper() or w.islower() else w for w in s.split())
    return s + (" (In charge)" if ic else "")


def blocks(html):
    """[(zone, [(post, name, phone, address, row no)], table no)] of a page of officer tables (heading row + label | value rows)."""
    out = []
    soup = _esw.soup(html)
    for ti, t in enumerate(soup.find_all("table"), 1):
        rows = [x for x in t.find_all("tr") if x.find_parent("table") is t]
        th = rows[0].find("th") if rows else None
        if not th:
            continue
        head = _esw.clean(th.get_text(" "))
        kv = []
        for ri, tr in enumerate(rows[1:], 2):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                kv.append((_esw.clean(tds[0].get_text(" ")), _esw.clean(tds[1].get_text(" ")), ri))
            else:
                provenance.skip_row(tr, 'skip: not (len(tds) >= 2)')
        get = {k.lower(): (v, ri) for k, v, ri in kv}
        name, nrow = get.get("name", ("", 2))
        addr = get.get("address", ("", 0))[0]
        ph = get.get("phone no", ("", 0))[0]
        zone = zone_of(head, addr)
        if not zone or not head:
            continue
        people = [(post_name(head), name, ph, addr, nrow)]
        for k, v, ri in kv:
            if k.lower() in ("name", "address", "phone no") or not k:
                continue
            people.append((post_name(k), v, "", addr, ri))
        out.append((zone, people, ti))
    return out


def parse(pages, p):
    """pages: {"wards": html, "zone": html, "sanitation": html} (any may be missing)."""
    wards = zone_wards(pages.get("wards") or "")
    seen, recs, had = set(), [], set()
    for page in ("zone", "sanitation"):
        url = URL if page == "zone" else SAN_URL
        for zone, people, ti in blocks(pages.get(page) or ""):
            w, wpos = wards.get(zone, ([], None))
            for post, name, ph, addr, ri in people:
                if not (name or ph) or (zone, post, name.lower()) in had:     # East: "JUNIOR ENGINEER PANDI" twice
                    provenance.skipped('skip: not (name or ph) or (zone, post, name.lower()) in had')
                    continue
                had.add((zone, post, name.lower()))
                d = _ward.record(MODULE, f"{_esw.slug(zone)}:{_esw.slug(post)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=zone, zone=zone, post=post, name=name, phone=ph,
                                 address=addr, wards=w, source=url,
                                 wards_source=WARDS_URL if w else None, wards_pos=wpos,
                                 src_pos={"table": ti, "row": ri})
                recs.append((d, page))
    return recs


def fetch(p, get):
    pages, files, answers = {}, [], {}
    for key, url in (("wards", WARDS_URL), ("zone", URL), ("sanitation", SAN_URL)):
        r = get(url)
        if r is None:
            continue
        pages[key], answers[key] = r.text, (r, url)
        files.append(_esw.keep(MODULE, key, r.content))
    if "zone" not in pages and "sanitation" not in pages:
        return [], files, "no answer"
    recs = []
    for d, page in parse(pages, p):
        r, url = answers[page]
        recs += _ward.tag([d], r, url)
    return recs, files, "" if recs else "no zone officer tables"
