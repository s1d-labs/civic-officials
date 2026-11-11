"""Lucknow Nagar Nigam (lmc.up.nic.in): the zone officers of its 8 zones. One PDF, "Doorbhas Suchi" (telephone list,
/pdf/DoorbhasSuchi.pdf; PDF title "Doorbhas Suchi 01-10-2026.xlsx"; saved in archive.s1d.me 2026-11-05), one page, 33 rows:
क्रमांक | नाम | पदनाम | तैनाती (zone or head office) | मोबाइल. Names and posts are set in Kruti Dev (converted with dforms/_ward_kd.py),
the posting column is Unicode. Only rows posted to a zone ("जोन-3", "जोन 1, 3, 4, 7") are read: zonal officers (जोनल अधिकारी),
executive engineers of each zone, tahsildars and garden superintendents (each over a group of zones). Head-office rows (मुख्यालय)
are left out (the district / body directories have them). The PDF does not list the wards of each zone (no "wards" key).
Names are Hindi: name and name_regional carry the same text; post is English, post_regional as written.
Records: level "zone"; ids dept:ward2n_lucknow:<zones slug>:<post slug>.
"""
import re

from dforms import _esw, _ward, _ward_kd as kd

MODULE = "ward2n_lucknow"
BODY, LGD, STATE, DISTRICT = "Lucknow Nagar Nigam", "249234", "UP", "Lucknow"
URL = "https://lmc.up.nic.in/pdf/DoorbhasSuchi.pdf"
DEVA = re.compile(r"[ऀ-ॿ]")
POSTS = (("जोनल अधिकारी", "Zonal Officer"), ("प्रभारी अधिशासी अभियन्ता", "Executive Engineer (in charge)"),
         ("अधिशासी अभियन्ता", "Executive Engineer"), ("तहसीलदार", "Tahsildar"), ("उद्यान अधीक्षक", "Garden Superintendent"))
WINGS = {"Tahsildar": "revenue", "Garden Superintendent": "horticulture"}


def items(get=None):
    return [{"key": f"{MODULE}-doorbhas-suchi", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def rows(pages):
    """[(name kd, post kd, posting, [phones])] of the table rows."""
    out = []
    for pg in pages:
        for ln in pg.splitlines():
            cells = [c for c in re.split(r"\s{2,}", ln.strip()) if c]
            if not cells:
                continue
            if re.fullmatch(r"\d{1,3}", cells[0]) and len(cells) >= 3:
                cur = {"name": cells[1], "post": cells[2], "area": [], "phones": []}
                rest = cells[3:]
                out.append(cur)
            elif out:
                cur, rest = out[-1], cells
            else:
                continue
            for c in rest:
                if re.fullmatch(r"[\d/,\s-]+", c):
                    cur["phones"] += re.findall(r"\d{10,11}", c)
                elif DEVA.search(c):
                    cur["area"].append(c)
    return [(r["name"], r["post"], " ".join(r["area"]), r["phones"]) for r in out]


def parse(pages, p):
    seen, recs = set(), []
    for name_kd, post_kd, area, phones in rows(pages):
        area = _ward.hi_norm(area).replace("जेान", "जोन")
        zones = re.findall(r"\d+", area) if "जोन" in area else []
        if not zones:
            continue
        name = _esw.clean(kd.convert(name_kd))
        post_hi = _esw.clean(kd.convert(post_kd))
        en = next((e for h, e in POSTS if h in post_hi), None) or _ward.hi_post(post_hi)
        zl = ", ".join(zones)
        area_en = f"Zone {zl}" if len(zones) == 1 else f"Zones {zl}"
        recs.append(_ward.record(MODULE, f"zone-{'-'.join(zones)}:{_esw.slug(en)}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=area_en, area_regional=area, zone=area_en, post=en,
                                 post_regional=post_hi, name=name, name_regional=name or None, phone=", ".join(phones),
                                 wing=WINGS.get(en), last_updated="2026-10-01", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "doorbhas-suchi", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no zone rows (pdftotext missing?)"
