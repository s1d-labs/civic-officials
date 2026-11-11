"""Kanpur Nagar Nigam (kmc.up.nic.in): the officers of its 6 zones and the wards of each zone. India only (no answer from Germany on
2026-11-11); both files are in archive.s1d.me (2026-11-05). One queue item reads two files:
  /key-contacts.html                      "मुख्य संपर्क": one table per department (heading before it: वरिष्ठ अधिकारी, स्वास्थ्य विभाग,
                                          अभियंत्रण विभाग, राजस्व विभाग ...), columns नाम | पद नाम | मोबाईल [| मेल आईडी | कार्यालय]; posts
                                          that name a zone ("जोनल अधिकारी जोन-1", "कर अधीक्षक जोन-3", "अवर अभियन्ता ज़ोन-2", "ज़ेड०एस०ओ ज़ोन-4")
                                          are the zone officers. Only those rows are read (the rest are head-office posts).
  /PDF_Files/others/zonewardlist.pdf      "DELIMITATION OF ZONES-2017": six columns ZONE-1 .. ZONE-6 of ward no + ward name (110 wards).
Names and posts are in Hindi: name and name_regional carry the same text; post = an English rendering of the Hindi post
(POSTS), post_regional = the post as written. Records: level "zone", wards = the zone's wards from the PDF.
Record ids: dept:ward_kanpur:z<N>:<wing>:<post slug>:<n>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward_kanpur"
BODY, LGD, STATE, DISTRICT = "Kanpur Nagar Nigam", "249286", "UP", "Kanpur Nagar"
URL = "https://kmc.up.nic.in/key-contacts.html"
ZONEPDF = "https://kmc.up.nic.in/PDF_Files/others/zonewardlist.pdf"
# Hindi post -> English (first match wins; the order puts the longer posts first)
POSTS = (
    (r"सहायक\s*नगर\s*आयुक्त", "Assistant Municipal Commissioner"), (r"जोनल\s*अधिकारी", "Zonal Officer"),
    (r"कर\s*निर्धारण\s*अधिकारी", "Tax Assessment Officer"), (r"कर\s*अधीक्षक", "Tax Superintendent"),
    (r"प्र0\s*अधि0\s*अभियं?(?:न्)?ता", "Executive Engineer (in charge)"),
    (r"अधि0\s*अभियं?(?:न्)?ता|अधिशा[षस]ी\s*अभियं?(?:न्)?ता", "Executive Engineer"),
    (r"सहायक\s*अभियं?(?:न्)?ता", "Assistant Engineer"), (r"अवर\s*अभियं?(?:न्)?ता", "Junior Engineer"),
    (r"जेड0?एस0?ओ|जेडएसओ|ZSO", "Zonal Sanitation Officer"), (r"सफाई\s*निरीक्षक", "Sanitary Inspector"),
    (r"स्वास्थ्य\s*अधिकारी", "Health Officer"), (r"कंप्यूटर\s*ऑपरेटर", "Computer Operator"), (r"प्रभारी\s*अधिकारी", "Officer in Charge"),
)
DEPTS = {"स्वास्थ्य": "sanitation", "अभियंत्रण": "engineering", "राजस्व": "revenue", "मार्ग प्रकाश": "electrical", "उद्यान": "horticulture",
         "सूचना प्रोद्योगिकी": "other", "वरिष्ठ अधिकारी": "administration", "जलकल": "water"}


def norm(s):
    """Hindi with nukta letters written as one code point or two, and ० as a dot / zero: one spelling."""
    s = _esw.clean(s).replace("ज़", "ज").replace("़", "").replace("०", "0")
    return s


def zones_of(post):
    m = re.search(r"जोन\s*[-–]?\s*((?:\d+\s*[,/&]?\s*)+)", norm(post))
    return [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []


def english(post):
    p = norm(post)
    for rx, en in POSTS:
        if re.search(rx, p):
            return en
    return p


def zone_wards(text):
    """{zone no: [ward numbers]} from the layout text of zonewardlist.pdf: ward numbers sit under the ZONE-n headings."""
    lines = text.splitlines()
    hi = next((i for i, ln in enumerate(lines) if len(re.findall(r"ZONE-\d", ln)) >= 6), None)
    wi = next((i for i, ln in enumerate(lines) if len(re.findall(r"WARD\s+WARD\s*NAME", ln)) >= 6), None)
    if hi is None or wi is None:
        return {}
    zones = [int(m.group(1)) for m in re.finditer(r"ZONE-(\d)", lines[hi])]
    # the ward-number columns start at each "WARD WARD NAME" of the second heading line (the ZONE-n words sit centred above)
    starts = list(zip([m.start() for m in re.finditer(r"WARD\s+WARD\s*NAME", lines[wi])], zones))
    out = {z: [] for _, z in starts}
    for ln in lines[wi + 1:]:
        if re.search(r"TOTAL", ln, re.I):
            break
        m = re.match(r"\s*(\d+)\s", ln)
        if not m:
            continue
        for t in re.finditer(r"(?<![\w(])(\d{1,3})(?=\s+[A-Za-z(])", ln[m.end():]):
            pos = t.start() + m.end()
            z = [z for s, z in starts if s <= pos + 4]
            if z:
                w = str(int(t.group(1)))
                if w not in out[z[-1]]:
                    out[z[-1]].append(w)
    return out


def parse(html, zw, p):
    soup = _esw.soup(html)
    seen, recs, n = set(), [], {}
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g or "नाम" not in g[0][0]:
            continue
        dept = next((x.strip() for x in t.find_all_previous(string=True, limit=8) if x.strip()), "")
        wing = next((w for k, w in DEPTS.items() if k in dept), None)
        for r in g[1:]:
            if len(r) < 3:
                continue
            name, post, phone = (_esw.clean(c) for c in r[:3])
            email = _esw.clean(r[3]) if len(r) > 3 else ""
            zs = zones_of(post)
            if not zs or not name:
                continue
            en = english(post)
            for z in zs:
                key = f"z{z}:{wing or 'dept'}:{_esw.slug(en) or 'post'}"
                n[key] = n.get(key, 0) + 1
                zone = f"Zone {z}"
                recs.append(_ward.record(MODULE, f"{key}:{n[key]}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                         level="zone", area=zone, zone=zone, post=en, post_regional=post, name=name,
                                         name_regional=name, phone="" if phone == "-" else phone, email=email,
                                         wards=zw.get(z) or None, wing=wing if wing and wing != "administration" else None,
                                         section=dept, source=p["url"]))
    return recs


def items(get=None):
    return [{"key": f"{MODULE}-key-contacts", "payload": {"reader": MODULE, "url": URL, "zone_pdf": ZONEPDF, "state": STATE,
                                                       "india_only": True}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "key-contacts", r.content)]
    zw = {}
    z = get(p.get("zone_pdf") or ZONEPDF)
    if z is not None:
        files.append(_esw.keep(MODULE, "zonewardlist", z.content, "pdf"))
        import subprocess
        try:
            out = subprocess.run(["pdftotext", "-layout", "-", "-"], input=z.content, capture_output=True, timeout=60).stdout
            zw = zone_wards(out.decode("utf-8", "replace"))
        except (OSError, subprocess.SubprocessError):
            zw = {}
        if not zw:
            zw = zone_wards("\n".join(_esw.pdf_pages(z.content)))
    recs = parse(r.text, zw, p)
    return recs, files, "" if recs else "no zone officers"
