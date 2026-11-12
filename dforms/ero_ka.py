"""Karnataka: ERO and AEROs of each assembly constituency, from the CEO's BLO data files (ceo.karnataka.gov.in/blo_data/ac/<AC>.json).
Answers only from India (Germany gets no connection).

One file per AC (1-224): {"no", "name", "district", "version", "parts": [[part no, polling station, BLO name, BLO phone, supervisor,
supervisor phone, AERO name, AERO phone, ERO name, ERO phone], ...]}. The ERO and AERO repeat on every part; this reader keeps one
record per distinct officer per AC with the parts they cover. "version" (20261019104155) is the file date. No email, no designation.
The BLOs of the same files are read by blo.py. One queue item = one AC.
Record ids: dept:ero_ka:KA-AC-<no>:ero (one per AC; a second ERO name gets :ero:<slug>), dept:ero_ka:KA-AC-<no>:aero:<slug of name>
(the files name no AERO office, so the name is the only key).
"""
from collections import Counter, OrderedDict

from dforms import _esw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ero_ka"
URL = "https://ceo.karnataka.gov.in/blo_data/ac/{}.json"
ACS = range(1, 225)


def items(get=None):
    return [{"key": f"{MODULE}-ac-{n}", "payload": {"reader": MODULE, "url": URL.format(n), "state": "KA", "ac": n, "india_only": True}}
            for n in ACS]


def _date(version):
    v = str(version or "")
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if len(v) >= 8 and v[:8].isdigit() else None


def _phone(s):
    s = str(s or "").strip()
    return s if sum(c.isdigit() for c in s) >= 6 else ""


def parse(doc, url):
    no, name, district = doc.get("no"), _esw.clean(doc.get("name")), _esw.clean(doc.get("district")).title()
    officers = OrderedDict()          # (role, name key) -> {"name", "phones": Counter, "parts": []}
    for ri, row in enumerate(doc.get("parts") or []):
        row = list(row) + [""] * (10 - len(row))
        for role, ni, pi in (("aero", 6, 7), ("ero", 8, 9)):
            n = _esw.clean(row[ni])
            if not n:
                continue
            o = officers.setdefault((role, _esw.slug(n)), {"name": n, "phones": Counter(), "parts": [], "at": []})
            if _phone(row[pi]):
                o["phones"][_phone(row[pi])] += 1
            o["parts"].append(str(row[0]))
            o["at"].append(ri)
    recs, eros = [], [k for k in officers if k[0] == "ero"]
    for (role, nk), o in officers.items():
        if role == "ero":
            key = f"KA-AC-{no}:ero" if nk == eros[0][1] else f"KA-AC-{no}:ero:{nk}"
            post = "Electoral Registration Officer"
        else:
            key = f"KA-AC-{no}:aero:{nk}"
            post = "Assistant Electoral Registration Officer"
        parts = o["parts"]
        recs.append(_esw.record(MODULE, key, dept="elections", level="ac", area=f"{no} - {name}", post=post, name=o["name"],
                                phone=", ".join(p for p, _ in o["phones"].most_common()), state="KA", district=district,
                                office_id=f"KA-AC-{no}", source=url, last_updated=_date(doc.get("version")),
                                parts=f"{len(parts)} parts" + (f" ({parts[0]}-{parts[-1]})" if parts else ""),
                                # source trail: the officer is named on these rows of the AC file's "parts" array (0-based)
                                src_pos={"key": "parts", "index": o["at"][0], **({"indexes": o["at"]} if len(o["at"]) > 1 else {}),
                                         "col": 6 if role == "aero" else 8}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"ac-{p.get('ac', 'x')}", r.content, "json")]
    try:
        doc = r.json()
    except ValueError:
        return [], files, "not json"
    recs = parse(doc, p["url"])
    return recs, files, "" if recs else "no officers"
