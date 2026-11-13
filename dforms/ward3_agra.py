"""Agra Nagar Nigam (nagarnigamagra.com, WordPress): the zonal officers of its 4 zones with mobiles and the wards of each zone, and
the officers of every department. Two public pages (live sample 2026-11-13 from Mumbai; the home page is in archive.s1d.me from
the GitHub runners, these two pages are not):
  /contact/      one table in Hindi: a department heading row ("प्रशासनिक विभाग", "जोनल विभाग", "कर विभाग" ...), then
                 rows "" | नाम | पदनाम | मोबाइल; an "Email:" row gives the email of the row above. Zone officers are "जोनल अधिकारी
                 <zone> जोन"; the tax officers name their zone after the name ("श्री अवधेश कुमार (लोहामंडी जोन)").
  /zones-wards/  one table: the 4 zones (Chatta, Hari Parvat, Loha Mandi, Taj Ganj) as columns, a row of office addresses and a
                 row of "Corporate Wards" ("1-KAJIPADHA 14-KACHH PURA ...", 100 wards).
dforms/ward_agra.py reads the zones-wards page alone (zone offices without officers); this reader adds the people.
Records: zone officers and zone-named tax officers at level "zone" (area "<Zone> Zone", wards and ward_names of the zone, the
zone office address), everyone else at level "body" (department = the heading). Rows without a name and a mobile (posts shown
empty) and the Mayor (elected) are left out. Names and posts are Hindi: name / name_regional, post (English where known) /
post_regional. Record ids: dept:ward3_agra:<zone slug or body>:<post slug>:<mobile or row>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_agra"
BODY, LGD, STATE, DISTRICT = "Agra Nagar Nigam", "249062", "UP", "Agra"
URL = "https://nagarnigamagra.com/contact/"
ZONES_URL = "https://nagarnigamagra.com/zones-wards/"
ZONES = {"लोहामंडी": "Loha Mandi", "हरीपर्वत": "Hari Parvat", "छत्ता": "Chatta", "ताजगंज": "Taj Ganj"}
POSTS = ((r"^नगर\s*आयुक्त", "Municipal Commissioner"), (r"जोनल\s*अधिकारी", "Zonal Officer"), (r"मुख्य\s*नगर\s*स्वास्थ्य", "Chief City Health Officer"),
         (r"राजस्व\s*निरीक्षक", "Revenue Inspector"), (r"बिल\s*कलेक्टर", "Bill Collector"), (r"अमीन", "Amin"),
         (r"मुख्य\s*कर\s*निर्धारण", "Chief Tax Assessment Officer"), (r"पर्यावरण\s*अभियन्ता", "Environmental Engineer"),
         (r"मुख्य\s*अभियन्ता", "Chief Engineer"), (r"अपर\s+अभियंता", "Additional Engineer"), (r"महाप्रबन्धक", "General Manager"),
         (r"सचिव\s*/\s*अधिशासी\s*अभियन्ता", "Secretary / Executive Engineer"), (r"पशु", "Veterinary Officer"),
         (r"मुख्य\s*वित्त", "Chief Finance and Accounts Officer"), (r"सहायक\s*लेखाधिकारी", "Assistant Accounts Officer"),
         (r"लेखाधिकारी", "Accounts Officer"), (r"मुख्य\s*नगर\s*लेखा\s*परीक्षक", "Chief City Auditor"),
         (r"वरिष्ठ\s*लेखा\s*परीक्षक", "Senior Auditor"), (r"वरिष्ठ\s*लिपिक", "Senior Clerk"), (r"लिपिक", "Clerk"),
         (r"प्रभारी\s*प्रवर्तन\s*दल", "Enforcement Squad In-Charge"), (r"जे\W*सी\W*ओ", "JCO, Enforcement Task Force"),
         (r"एन\W*सी\W*ओ", "NCO, Enforcement Task Force"), (r"जन\s*सूचना\s*अधिकारी", "Public Information Officer"))


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def en_post(post):
    p = _ward.hi_norm(post)
    for rx, en in POSTS:
        if re.search(rx, p):
            return en
    return _ward.hi_post(post)


def zones_of(text):
    t = _ward.hi_norm(text)
    return [en for hi, en in ZONES.items() if hi in t]


def zone_wards(html):
    """{zone (English): {"wards": [(no, name)], "address": text}} from the zones-wards page."""
    out = {}
    if not html:
        return out
    for t in _esw.soup(html).find_all("table"):
        g = _esw.grid(t)
        if not g or not any(z in " ".join(g[0]) for z in ZONES.values()):
            continue
        head = [_esw.clean(c) for c in g[0]]
        addr = next((r for r in g if any(re.search(r"\d\.\s|Agra", c) for c in r)), None)
        wrow = next((r for r in g if sum(len(re.findall(r"\b\d{1,3}-[A-Z]", c)) for c in r) > 20), None)
        for i, z in enumerate(head):
            if z not in ZONES.values():
                continue
            ws = []
            if wrow and i < len(wrow):
                for m in re.finditer(r"\b(\d{1,3})-([A-Z][^0-9]*?)(?=\s+\d{1,3}-[A-Z]|$)", _esw.clean(wrow[i])):
                    ws.append((m.group(1), _esw.clean(m.group(2))))
            out[z] = {"wards": sorted(ws, key=lambda x: int(x[0])), "address": _esw.clean(addr[i]) if addr and i < len(addr) else None}
        break
    return out


def parse(html, p, zones_html=None):
    zw = zone_wards(zones_html)
    soup = _esw.soup(html)
    seen, recs, done = set(), [], {}
    for t in soup.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        sec, last = "", None
        for row, ps in zip(g, pos):
            cells = [_esw.clean(c) for c in row]
            filled = [c for c in cells if c]
            if len(filled) == 1 and len(set(cells)) == 1 or (len(cells) == 1 and filled):
                if not re.search(r"1533|dial", filled[0], re.I):
                    sec = filled[0]
                continue
            if len(cells) < 4 or "नाम" in cells[1] and "पद" in cells[2]:
                continue
            name, post, ph = cells[1], cells[2], cells[3]
            if re.match(r"(?i)e-?mail", post) and last is not None:
                last[1]["email"] = _esw.emails(ph) or last[1].get("email")
                continue
            if not (name and ph and post) or re.search(r"महापौर|मेयर", post) or not re.search(r"\d{6}", ph):
                last = None
                continue
            zs = zones_of(post) if "जोन" in post else zones_of(name) if "जोन" in name else []
            nm = _esw.clean(re.sub(r"\([^)]*जोन[^)]*\)", "", name))
            en = en_post(post)
            dept = sec or None
            if zs:
                for z in zs:
                    k = (z, en, ph)
                    if k in done:          # the zone officers are listed again under the birth / death office
                        done[k][1].setdefault("also_listed_under", []).append(dept)
                        continue
                    info = zw.get(z, {})
                    ws = info.get("wards", [])
                    area = f"{z} Zone"
                    last = _ward.record(MODULE, f"{_esw.slug(z)}:{_esw.slug(en)}:{re.sub(r'[^0-9]', '', ph)[:10]}", seen, body=BODY,
                                        lgd=LGD, state=STATE, district=DISTRICT, level="zone", area=area, zone=area, post=en,
                                        post_regional=post, name=nm, name_regional=nm, phone=ph, department=dept,
                                        address=info.get("address"), wards=[w for w, _ in ws] or None,
                                        ward_names=[f"{w}-{n}" for w, n in ws] or None,
                                        wards_note=None if ws else "zone not on the zones-wards page",
                                        role="head" if en == "Zonal Officer" else None,
                                        wing="revenue" if re.search(r"कर|राजस्व", post) else None, source=p["url"], src_pos=ps)
                    done[k] = last
                    recs.append(last)
                continue
            wing = ("revenue" if re.search(r"कर\s|राजस्व|बिल|अमीन", post + " ") or sec.startswith(("कर", "सम्पत्ति")) else
                    "water" if sec.startswith("जलकल") else "electrical" if sec.startswith("प्रकाश") else
                    "engineering" if sec.startswith("निर्माण") else "health" if sec.startswith("स्वास्थ्य") or "पशु" in sec else None)
            last = _ward.record(MODULE, f"body:{_esw.slug(en) or 'post'}:{re.sub(r'[^0-9]', '', ph)[:10]}", seen, body=BODY, lgd=LGD,
                                state=STATE, district=DISTRICT, level="body", area=BODY, post=en, post_regional=post, name=nm,
                                name_regional=nm, phone=ph, department=dept, wing=wing or _ward.wing_of(en),
                                source=p["url"], src_pos=ps)
            recs.append(last)
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    z = get(ZONES_URL)
    files = [_esw.keep(MODULE, "contact", r.content)]
    if z is not None and z.status_code == 200:
        files.append(_esw.keep(MODULE, "zones-wards", z.content))
    recs = parse(r.text, p, z.text if z is not None and z.status_code == 200 else None)
    _ward.tag(recs, r, p["url"], METHOD)
    for _, d in recs:          # the wards of a zone come from the second page
        if d.get("wards") and z is not None:
            d["wards_src"] = ZONES_URL
    return recs, files, "" if recs else "no officers table"
