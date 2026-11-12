"""Municipal Corporation Panipat (nagarnigampanipat.in): the cleaning inspectors (sanitary / assistant sanitary inspectors) and
the cleaning supervisors (daroga) of its 26 wards, from the page "Sanitation Structure" (/sanitation-structure/; WordPress; in
archive.s1d.me, saved 2026-11-06; the page was made 2020-09-07 and shows no later date). One table: Ward No | Cleaning Inspector
(rowspan over the wards of the inspector: "Sh. Parmjeet Singh Assistant Sanitary Inspector (Mob No. 9812173198)") | Cleaning
Supervisor (Daroga) | Mob No. A ward is split in beats ("4.1", "4.2"): the beat is kept in "beat", the ward number in "wards".
Records: one per inspector (level "ward", wards = the wards of the rowspan) and one per supervisor (level "ward", one ward).
Record ids: dept:ward2n_panipat:<ward-a-b...>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_panipat"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Panipat", "248521", "HR", "Panipat"
URL = "https://nagarnigampanipat.in/sanitation-structure/"


def items(get=None):
    return [{"key": f"{MODULE}-sanitation-structure", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def parse(html, p):
    seen, recs, insp = set(), [], {}
    for head, rows in _ward.header_tables(html, "ward", "inspector"):
        for r in rows:
            beat = _ward.col(r, "ward no", "ward")
            m = re.match(r"\s*(\d{1,3})(?:\.(\d+))?\s*$", beat)
            if not m:
                continue
            ward = str(int(m.group(1)))
            ins = _ward.col(r, "inspector")
            if ins:
                insp.setdefault(ins, [])
                if ward not in insp[ins]:
                    insp[ins].append(ward)
            sup, mob = _ward.col(r, "supervisor", "daroga"), _ward.col(r, "mob")
            if sup:
                recs.append(_ward.record(MODULE, f"ward-{ward}:cleaning-supervisor:{_esw.slug(sup)}", seen, body=BODY, lgd=LGD,
                                         state=STATE, district=DISTRICT, level="ward", area=f"Ward {ward}", post="Cleaning Supervisor (Daroga)",
                                         name=sup, phone=mob, wards=[ward], beat=beat.strip() if m.group(2) else None,
                                         wing="sanitation", source=p["url"]))
    for text, wards in insp.items():
        t = _esw.clean(text.replace("|", " "))
        mm = re.search(r"(?i)((?:assistant\s+)?sanitary\s+ins[pe]+ctor)", t)
        post = "Assistant Sanitary Inspector" if mm and "assistant" in mm.group(1).lower() else "Sanitary Inspector"
        name = _esw.clean(t[:mm.start()] if mm else re.sub(r"\(.*", "", t)).strip(" ,")
        recs.append(_ward.record(MODULE, f"ward-{'-'.join(wards)}:{_esw.slug(post)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area="Ward " + ", ".join(wards), post=post,
                                 post_as_written=mm.group(1) if mm else None, name=name,
                                 phone=" ".join(re.findall(r"[6-9]\d{9}", t)), wards=wards, wing="sanitation", source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "sanitation-structure", r.content)], "" if recs else "no ward table"
