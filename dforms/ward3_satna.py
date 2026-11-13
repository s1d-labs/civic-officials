"""Satna Nagar Palik Nigam (satnamunicipalcorporation.com): the officers' departmental mobiles, with the zonal officers and the sub
engineers of each zone. One page, /contact.php (archive.s1d.me copy of 2026-11-11, vantage pool = GitHub runners abroad), table
"अधिकारियों/कर्मचारियों के विभागीय मोबाइल नम्बर": क्रमांक | नाम अधिकारी/कर्मचारी | पदनाम | मोबाइल नम्बर (30 rows on 2026-11-11).
The post text names the zone ("जोनल अधिकारी जोन क्र.02 एवं 05", "उपयंत्री जोन क्र.01"); the page gives no ward list per zone.
Records: a row whose post names zones -> one record per zone, level "zone" (area "Zone <n>"); the other rows (commissioner,
deputy commissioner, engineers, sanitation officers, law officer) -> level "body". Names and posts are Hindi: name = the name
without श्री / श्रीमती / सुश्री / डॉ., name_regional as written, post English (dforms/_ward3_central.post_en), post_regional as written.
Record ids: dept:ward3_satna:<zone-n or body>:<post slug>:<mobile>.
"""
from dforms import _esw, _ward, _ward3_central as c3

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_satna"
BODY, LGD, STATE, DISTRICT = "Satna Nagar Palik Nigam", "250781", "MP", "Satna"
URL = "https://satnamunicipalcorporation.com/contact.php"


def items(get=None):
    return [{"key": f"{MODULE}-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE, "route": "abroad"}}]


def parse(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "पदनाम", "मोबाइल"):
        for r in rows:
            name, post, phone = _ward.col(r, "नाम"), _ward.col(r, "पदनाम"), _ward.col(r, "मोबाइल")
            if not _ward.col(r, "क्रमांक").isdigit() or not post or not (name or phone):
                continue
            en = c3.post_en(post)
            zones = c3.zones_of(post)
            mob = c3.phones_in(phone) or phone
            for z in zones or [None]:
                lvl = "zone" if z else "body"
                area = f"Zone {z}" if z else BODY
                recs.append(_ward.record(MODULE, f"{'zone-' + z if z else 'body'}:{_esw.slug(en)}:{mob.split(',')[0] or len(recs)}",
                                         seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level=lvl, area=area,
                                         zone=area if z else None, post=en, post_regional=post, name=c3.strip_title(name),
                                         name_regional=name, phone=mob, wing=c3.wing(post, en), source=p["url"], src_pos=r.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "contact", r.content)], "" if recs else "no officer table"
