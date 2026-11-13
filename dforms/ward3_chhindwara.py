"""Chhindwara Nagar Palik Nigam (chhindwaranagarnigam.com, WordPress + Elementor): the health inspectors and the ward darogas of
every ward, and the officers with their zones. Two pages, one queue item each (payload "kind"); live samples from Mumbai on
2026-11-13, not in archive.s1d.me. Each page draws its tables as one Elementor top-level section per row, one column per cell
(dforms/_ward3_central.elementor_rows).
- "sanitation" (/team-sanitation/): "स्वास्थ्य विभाग के अधिकारीयों/कर्मचारियों की सूची": क्रमांक | नाम | पद | मोबाईल नंबर | वार्ड
  क्रमांक (6 rows: the health officer, "सभी वार्ड" = all wards, and 5 health inspectors with their ward ranges "23 -24, 34-40"),
  then "वार्ड दरोगा की सूची": वार्ड क्र. | वार्ड का नाम | नाम | मोबाईल नंबर (48 wards; a cell can name two darogas and two mobiles).
- "officers" (/municipal-officers/): नाम | पद | मोबाईल नंबर | छायाचित्र: the commissioner, deputy commissioner, executive engineer
  and the zonal officers ("जोनल अधिकारी जोन क्रमांक 1, 3 एवं 4 / प्रभारी योजना शाखा ..."). The page gives no ward list per zone.
Records: health inspectors and darogas at level "ward" (wards = their wards; a daroga's area_regional = the ward name; a cell with
two names -> two records, the mobiles in order); the health officer at level "body" (all wards); zonal officers at level "zone"
(one record per zone named); the other officers at level "body". Names and posts are Hindi: name without श्री / कु., name_regional
as written, post English, post_regional as written. Record ids: dept:ward3_chhindwara:<ward-n|wards-a-b|zone-n|body>:<post slug>:<mobile>.
"""
import re

from dforms import _esw, _ward, _ward3_central as c3
import provenance

METHOD = "html elementor rows"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_chhindwara"
BODY, LGD, STATE, DISTRICT = "Chhindwara Nagar Palik Nigam", "251026", "MP", "Chhindwara"
BASE = "https://chhindwaranagarnigam.com"
PAGES = {"sanitation": f"{BASE}/team-sanitation/", "officers": f"{BASE}/municipal-officers/"}
ALL_WARDS = [str(n) for n in range(1, 49)]


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "kind": k, "url": u, "state": STATE, "route": "abroad"}}
            for k, u in PAGES.items()]


def _names(cell):
    """Names in a cell that can hold two ("श्री अ श्री ब"): split before each title."""
    parts = [x.strip() for x in re.split(r"\s*/\s*|\n|(?=\s(?:श्रीमती|श्री|सुश्री|कु\.)\s)", _esw.clean(cell).replace("​", ""))]
    return [x for x in parts if x]


def _rec(recs, seen, key, **f):
    recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, **f))


def parse_sanitation(html, p):
    seen, recs, table = set(), [], None
    for cells, pos in c3.elementor_rows(html):
        head = " ".join(cells)
        if "वार्ड क्रमांक" in head and "पद" in head:
            table = "staff"
            continue
        if "वार्ड का नाम" in head:
            table = "daroga"
            continue
        if not cells or not cells[0].strip().isdigit():
            provenance.skip_row(cells, 'skip: not cells or not cells[0].strip().isdigit()')
            continue
        if table == "staff" and len(cells) >= 5:
            _, name, post, phone, wards = cells[:5]
            en = c3.post_en(post)
            mob = c3.phones_in(phone)
            if "सभी" in wards:
                _rec(recs, seen, f"body:{_esw.slug(en)}:{mob.split(',')[0]}", level="body", area=BODY, post=en, post_regional=post,
                     name=c3.strip_title(name), name_regional=name, phone=mob, wards=ALL_WARDS, wing="health", source=p["url"],
                     src_pos=pos, wards_note="सभी वार्ड (all wards)")
                continue
            w = _ward.wards_of(wards)
            area = ("Ward " if len(w) == 1 else "Wards ") + ", ".join(w)
            _rec(recs, seen, f"wards-{w[0] if w else 'x'}:{_esw.slug(en)}:{mob.split(',')[0]}", level="ward", area=area,
                 post=en, post_regional=post, name=c3.strip_title(name), name_regional=name, phone=mob, wards=w,
                 wing="health", source=p["url"], src_pos=pos)
        elif table == "daroga" and len(cells) >= 4:
            ward, wname, names, phone = cells[:4]
            w = str(int(ward))
            mobs = c3.phones_in(phone).split(", ")
            names = _names(names)
            for i, n in enumerate(names):
                mob = mobs[i] if len(names) > 1 and i < len(mobs) else ", ".join(m for m in mobs if m)
                _rec(recs, seen, f"ward-{w}:daroga:{mob.split(',')[0] or i}", level="ward", area=f"Ward {w}",
                     area_regional=_esw.clean(wname), post="Ward Daroga (sanitation supervisor)", post_regional="वार्ड दरोगा",
                     name=c3.strip_title(n), name_regional=n, phone=mob, wards=[w], wing="sanitation", source=p["url"], src_pos=pos)
    return recs


def parse_officers(html, p):
    """The page draws the officer list twice (two layouts): a row seen before (same name and post) is skipped."""
    seen, recs, done = set(), [], set()
    for cells, pos in c3.elementor_rows(html):
        if len(cells) < 3 or cells[0].strip() in ("नाम", "") or "पद" == cells[1].strip():
            provenance.skip_row(cells, 'skip: len(cells) < 3 or cells[0].strip() in ("नाम", "") or "पद" == cells[...')
            continue
        name, post, phone = cells[0], cells[1], cells[2]
        if not re.search(r"[ऀ-ॿ]", name) or not post.strip() or (_esw.clean(name), _esw.clean(post)) in done:
            provenance.skip_row(cells, 'skip: not re.search(r"[ऀ-ॿ]", name) or not post.strip() or (_esw.clean(na...')
            continue
        done.add((_esw.clean(name), _esw.clean(post)))
        mob = c3.phones_in(phone)
        duties = [d.strip() for d in post.split("/") if d.strip()]
        first = duties[0] if duties else post
        en = c3.post_en(first)
        zones = c3.zones_of(first)
        for z in zones or [None]:
            _rec(recs, seen, f"{'zone-' + z if z else 'body'}:{_esw.slug(en)}:{mob.split(',')[0] or len(recs)}",
                 level="zone" if z else "body", area=f"Zone {z}" if z else BODY, zone=f"Zone {z}" if z else None, post=en,
                 post_regional=_esw.clean(post), name=c3.strip_title(name), name_regional=name, phone=mob,
                 wing=c3.wing(first, en), source=p["url"], src_pos=pos)
    return recs


def parse(html, p):
    return parse_officers(html, p) if p.get("kind") == "officers" else parse_sanitation(html, p)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("kind", "page"), r.content)], "" if recs else "no officer rows"
