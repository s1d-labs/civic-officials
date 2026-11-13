"""Nagpur Municipal Corporation (nmcnagpur.gov.in): the 10 zone offices and their officers. Answers from Germany and India; the
zone pages are in archive.s1d.me (2026-11-11). One page per zone (/laxmi-nagar, /dharampeth, /hanuman-nagar, /dhantoli,
/nehru-nagar, /gandhi-bagh, /satranjipura, /lakadganj, /ashi-nagar, /mangalwari; slugs from /site-map). Each page has:
  1. a box table: "<Zone> Zone No. NN" | the Assistant Commissioner's name | post | "Contact No :- <mobile>" | OFFICE ADDRESS;
  2. officer tables (Sr. No. | Name | Designation | Contact No) with section rows (colspan) "Public Works Department",
     "Health Medicine & Sanitation", "Tax Department", "Light Department" ...: executive / deputy / junior engineers, zonal
     officer (CSO), zonal medical officer, sanitation inspectors, tax inspectors, light department engineers.
The pages do not say which of the 38 electoral prabhags each zone holds (that list is not on the site), so records have no
"wards" key; zone = "Zone NN <name>". One more item, /zonal-officers, lists the zonal officer (CSO) of each zone with mobile.
Records: level "zone". Record ids: dept:ward_nagpur:z<NN>:<section slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_nagpur"
BODY, LGD, STATE, DISTRICT = "Nagpur Municipal Corporation", "251362", "MH", "Nagpur"
BASE = "https://nmcnagpur.gov.in/"
ZONES = ("laxmi-nagar", "dharampeth", "hanuman-nagar", "dhantoli", "nehru-nagar", "gandhi-bagh", "satranjipura", "lakadganj",
         "ashi-nagar", "mangalwari")
WINGS = {"public works": "engineering", "health": "sanitation", "tax": "revenue", "light": "electrical", "water": "water",
         "town planning": "planning", "garden": "horticulture"}


def items(get=None):
    out = [{"key": f"{MODULE}-{z}", "payload": {"reader": MODULE, "url": BASE + z, "state": STATE, "zone_no": i + 1}}
           for i, z in enumerate(ZONES)]
    out.append({"key": f"{MODULE}-zonal-officers", "payload": {"reader": MODULE, "url": BASE + "zonal-officers", "state": STATE,
                                                               "kind": "zonal-officers"}})
    return out


def parse_zone(html, p):
    soup = _esw.soup(html)
    seen, recs = set(), []
    zone, zno, address = None, p.get("zone_no"), None
    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        m = re.search(r"([A-Za-z .()]+?)\s*Zone\s*No\.?\s*0?(\d+)", g[0][0] if g and g[0] else "")
        if m and not zone:
            zno = int(m.group(2))
            zone = f"Zone {zno:02d} {m.group(1).strip()}"
            lines = [_esw.clean(r[-1]) for r in g[1:] if _esw.clean(r[-1])]
            ai = next((i for i, x in enumerate(lines) if x.upper().startswith("OFFICE ADDRESS")), None)
            address = lines[ai + 1] if ai is not None and ai + 1 < len(lines) else None
            head = [x for x in lines[:ai if ai is not None else len(lines)]]
            phone = next((x for x in head if re.search(r"(?i)contact", x)), "")
            name = next((x for x in head if re.match(r"(?i)(shri|smt|mrs?|ms|dr)\.?\s", x)), head[0] if head else "")
            post = next((x for x in head if x not in (name, phone)), "Assistant Commissioner")
            recs.append((name, post, phone, "Zone office", {"table": _esw.table_no(t), "kind": "zone head box (lines of one cell)"}))
            continue
        if not any(len(r) >= 4 and _esw.clean(r[0]).isdigit() for r in g):
            continue
        section = "Zone office"
        for r, rp in zip(g, gp):
            cells = [_esw.clean(c) for c in r]
            if len(set(cells)) == 1 and cells[0] and not cells[0].isdigit():
                section = cells[0]
                continue
            if len(cells) < 4 or cells[1].lower() == "name":
                provenance.skip_row(r, 'skip: len(cells) < 4 or cells[1].lower() == "name"')
                continue
            name, post, phone = cells[1], cells[2], cells[3]
            if name or phone:
                recs.append((name, post, phone, section, rp))
    zone = zone or f"Zone {zno:02d}" if zno else (zone or "Zone")
    out = []
    for name, post, phone, section, pos in recs:
        post = post.replace("Engg.", "Engineer")
        wing = next((w for k, w in WINGS.items() if k in section.lower()), None)
        if section == "Zone office" or wing is None or _ward.wing_of(post) in ("health", "water", "planning"):
            wing = _ward.wing_of(post)
        out.append(_ward.record(MODULE, f"z{zno:02d}:{_esw.slug(section)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}", seen,
                                body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone, post=post,
                                name=name, phone=phone, address=address, wing=wing, section=section, source=p["url"],
                                src_pos=pos))
    return out


def parse_zonal(html, p):
    soup = _esw.soup(html)
    seen, out = set(), []
    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g or "zone" not in " ".join(g[0]).lower():
            continue
        for r, rp in zip(g[1:], gp[1:]):
            if len(r) < 4:
                provenance.skip_row(r, 'skip: len(r) < 4')
                continue
            name, zno, zname, phone = (_esw.clean(c) for c in r[:4])
            m = re.search(r"\d+", zno)
            if not m:
                provenance.skip_row(r, 'skip: not m')
                continue
            zone = f"Zone {int(m.group(0)):02d} {zname}"
            out.append(_ward.record(MODULE, f"z{int(m.group(0)):02d}:zonal-officer:{_esw.slug(name)}", seen, body=BODY, lgd=LGD,
                                    state=STATE, district=DISTRICT, level="zone", area=zone, zone=zone,
                                    post="Zonal Officer / Chief Sanitary Officer", name=name, phone=phone, wing="sanitation",
                                    source=p["url"], src_pos=rp))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, p["url"].rstrip("/").rsplit("/", 1)[-1], r.content)]
    recs = parse_zonal(r.text, p) if p.get("kind") == "zonal-officers" else parse_zone(r.text, p)
    return recs, files, "" if recs else "no officer tables"
