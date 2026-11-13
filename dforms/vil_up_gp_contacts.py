"""Uttar Pradesh: gram panchayat contact lists on district portals (S3WaaS): per gram panchayat the Panchayat Sachiv (gram
panchayat secretary: Gram Panchayat Adhikari / Gram Vikas Adhikari), the Gram Pradhan, the Panchayat Sahayak, the Rozgar
Sevak and the ration dealer (kotedar), each with a mobile number.
Measured 2026-11-13: Hathras "Panchayat Sachiv, Gram Pradhan, Panchayat sahayak, Rojgar sewak, Ration Dealer Contact List"
(https://hathras.nic.in/panchayat-sachivgram-pradhan-panchayat-sahayak-rojgar-sewak-ration-dealer-contact-list/, one HTML
table, 462 gram panchayats in 7 blocks, last updated 04.08.2026; archive copy 2026-11-06).

Reading: the header row is the first row with two or more "<role> Name" / "<role> Mobile" columns; each "Mobile" column
belongs to the role named in its header (or the nearest name column on its left). Roles by header words: sachiv / secretary
/ VDO / GPA; pradhan / sarpanch; panchayat sahayak; rojgar / rozgar sevak; ration dealer / kotedar; BLO; ASHA; anganwadi.
"NA" / "-" / "vacant" is no name. Block and gram panchayat columns give the place.

Records: one per role per gram panchayat row that names a person or gives a mobile: level "gram_panchayat", area = the gram
panchayat as written, block, district, state; dept rural_development (sachiv, pradhan, sahayak, rozgar sevak), food_supplies
(ration dealer), elections (BLO), health (ASHA), women_child (anganwadi). The Pradhan record has elected: true. Every record
keeps the whole row (header -> text) in table_row. Ids: dept:vil_up_gp_contacts:<host>:<tag>:<row>:<role>.
"""
import re
from urllib.parse import urlparse

from dforms import _esw, _field

METHOD = "html table (header words -> role name / mobile column pairs)"

MODULE = "vil_up_gp_contacts"
ROLE_RX = [  # role key, header regex, post, post_regional, dept
    ("sachiv", r"sachiv|secretary|\bvdo\b|\bgpa\b|panchayat adhikari|vikas adhikari|सचिव", "Panchayat Secretary (Sachiv)", "पंचायत सचिव", "rural_development"),
    ("sahayak", r"sahayak|सहायक", "Panchayat Sahayak", "पंचायत सहायक", "rural_development"),
    ("pradhan", r"pradhan|sarpanch|प्रधान", "Gram Pradhan", "ग्राम प्रधान", "rural_development"),
    ("rozgar", r"ro[jz]gar|रोजगार", "Rozgar Sevak", "रोजगार सेवक", "rural_development"),
    ("ration", r"ration|kotedar|dealer|कोटेदार", "Ration Dealer (Kotedar)", "कोटेदार", "food_supplies"),
    ("blo", r"\bblo\b|booth level", "Booth Level Officer", "बीएलओ", "elections"),
    ("asha", r"\basha\b|आशा", "ASHA", "आशा", "health"),
    ("aww", r"anganwadi|आंगनबाड़ी", "Anganwadi Worker", "आंगनबाड़ी कार्यकर्त्री", "women_child"),
]
MOBILE = re.compile(r"(?i)mobile|phone|contact|मोबाइल|मो\.?\s*नं")
NAME = re.compile(r"(?i)name|नाम")
NO_NAME = re.compile(r"(?i)^\s*(na|n/a|n\.a\.?|-+|vacant|nil|none|रिक्त)\s*$")


def role_of(h):
    for key, rx, *_ in ROLE_RX:
        if re.search(rx, h, re.I):
            return key
    return None


def columns(header):
    """{role: {"name": i, "mobile": [i]}}, block column, gp column, serial column."""
    out, last, block, gp, sno = {}, None, None, None, None
    for i, h in enumerate(header):
        h = _esw.clean(h)
        role = role_of(h)
        if re.search(r"(?i)^(sr|s|sl)\.?\s*no|^क्र", h):
            sno = i
        elif re.search(r"(?i)block|ब्लॉक|विकास खण्ड|विकासखंड", h) and not role:
            block = i
        elif re.search(r"(?i)gram panchayat|panchayat name|ग्राम पंचायत|village", h) and not role:
            gp = i
        elif MOBILE.search(h):
            r = role or last
            if r:
                out.setdefault(r, {}).setdefault("mobile", []).append(i)
        elif role:
            out.setdefault(role, {})["name"] = i
            last = role
    return out, block, gp, sno


def records(html, url, p):
    host = urlparse(url).netloc
    tag = p.get("tag") or _esw.slug(urlparse(url).path)[-50:] or "page"
    lu = _field.last_updated(html)
    meta = {k: (post, preg, dept) for k, _, post, preg, dept in ROLE_RX}
    out, ids = [], set()
    for table in _esw.soup(html).find_all("table"):
        gpos = []
        g = _esw.grid(table, pos=gpos)
        hi = next((i for i, r in enumerate(g[:5]) if len(columns(r)[0]) >= 2), None)
        if hi is None:
            continue
        header = [_esw.clean(c) for c in g[hi]]
        cols, bi, gi, si = columns(header)
        for n, (r, pos) in enumerate(zip(g[hi + 1:], gpos[hi + 1:]), 1):
            cells = [_esw.clean(c) for c in r]
            if cells[:len(header)] == header or len(set(cells)) == 1:
                continue

            def cell(i):
                return cells[i] if i is not None and i < len(cells) else ""
            gp, block, sno = cell(gi), cell(bi), cell(si)
            raw = {header[i] or f"col{i + 1}": c for i, c in enumerate(cells) if c and i < len(header)}
            rowkey = _esw.slug(sno) if re.fullmatch(r"\d{1,5}", sno or "") else str(n)
            for role, c in cols.items():
                name = cell(c.get("name"))
                if NO_NAME.match(name):
                    name = ""
                phone = _esw.phones(*[cell(i) for i in c.get("mobile", []) if not NO_NAME.match(cell(i))])
                if not (name or phone):
                    continue
                post, preg, dept = meta[role]
                key = f"{host}:{tag}:{rowkey}:{role}"
                while f"dept:{MODULE}:{key}" in ids:
                    key += "-b"
                rid, d = _esw.record(MODULE, key, dept=dept, level="gram_panchayat", area=gp, post=post, post_regional=preg,
                                     role=role, elected=True if role == "pradhan" else None, name=name, phone=phone,
                                     state=p.get("state"), district=p.get("district"), block=block, office_id=key,
                                     source=url, src_url=url, src_pos=pos, method=METHOD, last_updated=lu or p.get("last_updated"),
                                     table_row=raw)
                ids.add(rid)
                out.append((rid, d))
    return out


def items(get=None):
    return _field.seed(MODULE)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = p.get("tag") or _esw.slug(urlparse(p["url"]).path)[-50:] or "page"
    files = [_esw.keep(MODULE, f"{host}-{tag}", r.content, "pdf" if r.content[:5] == b"%PDF-" else "html")]
    if r.content[:5] == b"%PDF-":
        return [], files, "PDF list: kept in the bucket, no PDF reader yet"
    recs = records(r.text, p["url"], p)
    return recs, files, "" if recs else "no gram panchayat contact table"
