"""Tiruppur City Municipal Corporation (www.tnurbantree.tn.gov.in/tiruppur/, the Tamil Nadu urban local body WordPress platform):
its 4 zones with their wards and the zone officers' phones, from the "Citizen Charter" page (/tiruppur/citizen-charter/). Live
sample from Mumbai (dev-vps-3) 2026-11-13 (44 s answer; not in archive.s1d.me; the page shows no date). The platform answers
slowly or not at all from Germany (ward2s_tnurban, 2026-11-11): India only.
The page is the state's citizen charter template, in HTML tables:
  "Sl. No. | Division | Wards"   one row per zone ("Zone – I") with its wards ("1, 9, 10, ...")
  "Designation (and Phone Nos.)" blocks, one per service: First / Second / Third contact | posts | phones; the first-contact cell
                                  lists one post per zone ("Zonal Asst.Commissioner – I" .. "– IV", "Sanitary Officer – I" ..)
                                  and the phone cell one number per line in the same order. The other contacts are body-wide
                                  posts (City Engineer, City Health Officer, Assistant Engineer (Electrical), Commissioner).
The same block repeats for many services: one record per post (and zone); the services are kept as "services" and every table
that names the post is in src_pos. Phones are local numbers without the STD code; the reader adds 0421 (Tiruppur) to 6-8 digit
numbers. The page names no officers (posts and phones only).
Other Tamil Nadu corporations on the same platform (Hosur, Erode, Tirunelveli: checked 2026-11-13) have no zone table in their
charter page (Tirunelveli: a PDF). Record ids: dept:ward3_tiruppur:<zone-n | body>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_tiruppur"
BODY, LGD, STATE, DISTRICT, STD = "Tiruppur City Municipal Corporation", "252621", "TN", "Tiruppur", "0421"
URL = "https://www.tnurbantree.tn.gov.in/tiruppur/citizen-charter/"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
ZONE_POST = re.compile(r"^(.*?)\s*[–—-]\s*([IVX]{1,4})\s*$")
PHONE = re.compile(r"(?<!\d)(\d[\d -]{5,12}\d)(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-citizen-charter", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True,
                                                             "route": "direct"}}]


def lines(td):
    """The text lines of a cell: its <p> blocks and <br> breaks, cleaned, without empty lines."""
    for br in td.find_all("br"):
        br.replace_with("\n")
    for p in td.find_all("p"):
        p.insert_before("\n")
    return [x for x in (_esw.clean(t) for t in td.get_text().split("\n")) if x]


def phone(s):
    out = []
    for m in PHONE.finditer(s):
        n = re.sub(r"[ -]", "", m.group(1))
        if not n.isdigit():
            continue
        out.append(f"{STD}-{n}" if 6 <= len(n) <= 8 else n)
    return ", ".join(out)


def post_name(s):
    s = re.sub(r"(?i)\bAsst\.?\s*", "Assistant ", s)
    s = re.sub(r"(?i)^corporation\s+", "", s).strip(" .")
    return _esw.clean(s)


def zones_table(soup):
    """{zone no: (zone label, [wards], src_pos)} of the "Division | Wards" table."""
    out = {}
    for ti, t in enumerate(soup.find_all("table"), 1):
        rows = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        if not rows or not re.search(r"(?i)division.*wards", _esw.clean(rows[0].get_text(" "))):
            continue
        for ri, tr in enumerate(rows, 1):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            m = re.match(r"(?i)zone\s*[–—-]?\s*([IVX]{1,4})\b", _esw.clean(tds[1].get_text(" ")))
            if m and m.group(1) in ROMAN:
                out[ROMAN[m.group(1)]] = (_esw.clean(tds[1].get_text(" ")), _ward.wards_of(tds[2].get_text(" ")),
                                          {"table": ti, "row": ri})
    return out


def contacts(soup):
    """[(post, zone no or None, phone, tier, src_pos)] of every "First / Second / Third contact" row."""
    out = []
    for ti, t in enumerate(soup.find_all("table"), 1):
        rows = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        for ri, tr in enumerate(rows, 1):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            tier = _esw.clean(tds[0].get_text(" "))
            if not re.search(r"(?i)\b(first|second|third|initial)\b.*\b(contact|complaint)\b", tier):
                continue
            posts, phones = lines(tds[1]), lines(tds[2])
            pos = {"table": ti, "row": ri}
            if len(posts) > 1 and len(posts) == len(phones):
                pairs = list(zip(posts, phones))
            else:
                pairs = [(p, ", ".join(phones)) for p in posts]
            for p, ph in pairs:
                m = ZONE_POST.match(p)
                z = ROMAN.get(m.group(2)) if m else None
                out.append((post_name(m.group(1) if z else p), z, phone(ph), tier, pos))
    return out


def parse(html, p):
    soup = _esw.soup(html)
    zones = zones_table(soup)
    seen, recs, people = set(), [], {}
    for post, z, ph, tier, pos in contacts(soup):
        g = people.setdefault((post, z), {"phones": [], "pos": [], "tiers": []})
        for x in ph.split(", "):
            if x and x not in g["phones"]:
                g["phones"].append(x)
        if pos not in g["pos"]:
            g["pos"].append(pos)
        if tier not in g["tiers"]:
            g["tiers"].append(tier)
    kw = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=p["url"])
    for (post, z), g in people.items():
        if z:
            label, wards, zpos = zones.get(z, (f"Zone {z}", [], None))
            area = f"Zone {z}"
            recs.append(_ward.record(MODULE, f"{_esw.slug(area)}:{_esw.slug(post)}", seen, level="zone", area=area,
                                     area_regional=None, zone=area, post=post, phone=", ".join(g["phones"]), wards=wards,
                                     contact_tier=", ".join(g["tiers"]), **kw,
                                     src_pos={"rows": g["pos"] + ([zpos] if zpos else []),
                                              "note": "posts and phones of these rows; the last row: the zone's wards"}))
        else:
            recs.append(_ward.record(MODULE, f"body:{_esw.slug(post)}", seen, level="body", area=BODY, post=post,
                                     phone=", ".join(g["phones"]), contact_tier=", ".join(g["tiers"]), **kw,
                                     src_pos={"rows": g["pos"]}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "citizen-charter", r.content)], "" if recs else "no zone contacts in the page"
