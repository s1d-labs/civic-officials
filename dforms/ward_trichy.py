"""Tiruchirappalli City Municipal Corporation (www.trichycorporation.gov.in): the officers of its 5 zones (ward committee offices)
and the engineers of every ward. Answers from Germany and India (samples fetched 2026-11-11 from India; not in archive.s1d.me).
Two pages per zone N = 1..5 (one queue item reads both):
  /landing/wardofficers/N   one card per section engineer: <h4>name</h4><h4>post ("Junior Engineer -Div I")</h4>, "Office : ..",
                            "Mobile : ..", and <h6>"Ward - [1,2,3]<br/>J.E. Section Office<br/>Ammamandapam Division"</h6>.
  /landing/zonaladmins/N    one card per zone officer: <h4>name</h4><h6>post</h6> (Asst. Commissioner, Asst. Exe. Engineer, Asst.
                            Revenue Officer, Superintendent, Sanitary Officer ...), phones, and the office ("Ward Committee
                            Office-I, Srirangam Zone, ...").
Records: section engineers at level "ward" (wards from the card); zone officers at level "zone" with wards = every ward of that
zone's engineers (the ward-to-zone mapping). Every zonaladmins/N page (seen 2026-11-11 for N = 1, 3, 4, 5) also shows the zone I
officers ("Ward Committee Office-I, Srirangam Zone"): a zone officer card is kept only when its "Ward Committee Office-<roman>"
is zone N (cards without the office number are kept). "Vacant" posts are kept with vacant = true. Record ids:
dept:ward_trichy:z<N>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_trichy"
BODY, LGD, STATE, DISTRICT = "Tiruchirappalli City Municipal Corporation", "252749", "TN", "Tiruchirappalli"
BASE = "https://www.trichycorporation.gov.in/landing/"


def items(get=None):
    return [{"key": f"{MODULE}-zone{n}", "payload": {"reader": MODULE, "url": f"{BASE}wardofficers/{n}", "zonal": f"{BASE}zonaladmins/{n}",
                                                    "state": STATE, "zone_no": n}} for n in range(1, 6)]


def cards(html):
    """[(name, post, office phone, mobile, text after the phones)] of the officer cards of one page."""
    soup = _esw.soup(html)
    out = []
    for c in soup.find_all("div", class_="schedule-block-one"):
        heads = [_esw.clean(h.get_text()) for h in c.select(".content-box .text")[0].find_all(["h4", "h6"])] if c.select(".content-box .text") else []
        if not heads:
            continue
        name, post = heads[0], " ".join(heads[1:])
        lis = [_esw.clean(li.get_text()) for li in c.select("ul.post-info li")]
        office = next((re.sub(r"^Office\s*:\s*", "", x) for x in lis if x.startswith("Office")), "")
        mobile = next((re.sub(r"^Mobile\s*:\s*", "", x) for x in lis if x.startswith("Mobile")), "")
        low = c.find("div", class_="lower-content")
        for ul in low.find_all("ul") if low else []:
            ul.decompose()
        for br in low.find_all("br") if low else []:
            br.replace_with(" | ")
        rest = _esw.clean(low.get_text(" ")) if low else ""
        out.append((name, post, office, mobile, rest.strip(" |")))
    return out


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8}


def office_zone(text):
    """'Ward Committee Office-I, Srirangam Zone' -> 1; None when the text has no office number."""
    m = re.search(r"(?i)Ward\s*Committee\s*Office\s*[-–]?\s*([IVX]+|\d)\b", text or "")
    if not m:
        return None
    v = m.group(1).upper()
    return int(v) if v.isdigit() else ROMAN.get(v)


def parse(ward_html, zonal_html, p):
    n = p.get("zone_no") or int(re.search(r"/(\d+)$", p["url"]).group(1))
    seen, recs, allw, zname = set(), [], [], None
    for name, post, office, mobile, rest in cards(ward_html or ""):
        m = re.search(r"Ward\s*-?\s*\[([^\]]*)\]", rest)
        wards = _ward.wards_of(m.group(1)) if m else []
        allw += [w for w in wards if w not in allw]
        section = _esw.clean(rest[m.end():] if m else rest).strip(" |").replace(" | ", ", ")
        recs.append(_ward.record(MODULE, f"z{n}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward" if wards else "zone",
                                 area=("Ward " if len(wards) == 1 else "Wards ") + ", ".join(wards) if wards else f"Zone {n}",
                                 post=post, name=name, phone=", ".join(x for x in (mobile, office) if x), wards=wards,
                                 zone=f"Zone {n}", office=section or None, source=p["url"]))
    for name, post, office, mobile, rest in cards(zonal_html or ""):
        oz = office_zone(rest)
        if oz is not None and oz != n:
            continue                                     # zone I's officers, repeated on the page of zone n
        name = name.strip(" ,;")
        m = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+Zone", rest)
        zname = zname or (m.group(0) if m else None)
        recs.append(_ward.record(MODULE, f"z{n}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="zone", area=zname or f"Zone {n}", post=post, name=name,
                                 phone=", ".join(x for x in (mobile, office) if x), wards=allw or None, zone=f"Zone {n}",
                                 address=rest.replace(" | ", " ") or None, source=p.get("zonal") or p["url"]))
    if zname:
        for rid, d in recs:
            d["zone"] = f"Zone {n} {zname}"
    return recs


def fetch(p, get):
    r = get(p["url"])
    z = get(p["zonal"]) if p.get("zonal") else None
    if r is None and z is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"wardofficers-{p.get('zone_no')}", r.content)] if r is not None else []
    if z is not None:
        files.append(_esw.keep(MODULE, f"zonaladmins-{p.get('zone_no')}", z.content))
    recs = parse(r.text if r is not None else "", z.text if z is not None else "", p)
    return recs, files, "" if recs else "no officer cards"
