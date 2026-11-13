"""Karnataka city corporations on the state's municipal web platform (<city>.mrc.gov.in, Drupal; dforms/ward_kamrc.py reads the
ward-wise staff pages of the same sites): the "City Staff" page, /en/city-staff, of the corporations whose ward-wise pages are
empty (Kalaburagi, Mangaluru, Raichur: the three ward tables hold ward numbers and no names, checked 2026-11-13). India only: the
sites answer over plain http from Mumbai (dev-vps-3, 2026-11-13); the Indian proxies gave up on them (hub, 2026-11-12).
The page is one table: Sl No | Name | Designation | Contact No | Photo, with one-cell section rows ("Commissioner Details",
"Engineering Section - 1", "Health Section", "Revenue Section", "Town Planning Section", ...). Kalaburagi writes names and posts
in Kannada; a row with an empty post takes its section's name as the post (Kalaburagi lists office managers that way).
Zonal Commissioners ("Zonal Commissioner ( Incharge ) Surathkal", "Zonal Commissioner1(Incharge)", Kannada "ವಲಯ ಆಯುಕ್ತರು") are
level "zone": area = the zone the post names ("Surathkal Zone", "Zone 1"), else "Zone (not named on the page)". The page does not
say which wards a zone holds. Every other post is level "body" (area = the corporation): deputy commissioners, executive /
assistant / junior engineers by wing, health officers and inspectors, revenue officers and inspectors, bill collectors, town
planning. Clerical posts (first / second division assistants, office managers and assistants, stenographers, typists, PAs,
programmers, accountants) are left out. Kannada posts get an English post from POSTS (post_regional keeps the Kannada).
Mangaluru's contact page (/en/contact-us) names its three zonal offices (Surathkal Zonal Office - 1, Lalbag - 2, Kadri - 3) with
address and phone: read too for Mangaluru (payload "contact").
One queue item = one corporation. Record ids: dept:ward3_kamrc_staff:<city>:<area slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_kamrc_staff"
STATE = "KA"
BODIES = {
    "kalaburagi": ("www.kalaburagicity.mrc.gov.in", "Kalaburagi City Corporation", "248127", "Kalaburagi"),
    "mangaluru": ("www.mangalurucity.mrc.gov.in", "Mangaluru City Corporation", "252021", "Dakshina Kannada"),
    "raichur": ("www.raichurcity.mrc.gov.in", "Raichur City Corporation", "251876", "Raichur"),
}
CONTACT = {"mangaluru"}
CLERICAL = re.compile(r"(?i)\b(f\.?\s?d\.?\s?a|s\.?\s?d\.?\s?a|(first|second)\s+division\s+assistant|office\s+(manager|assistant)|"
                      r"steno\w*|typist|p\.?a\b|programmer|accountant|accounts\s+superintendent|technical\s+asst|"
                      r"commissioner'?s\s+pa|committee\s+executive|data\s+entry|computer|driver|peon|attender)\b|"
                      r"ಕಛೇರಿ\s*ವ್ಯವಸ್ಥಾಪಕ|ಆಫೀಸ್\s*ಅಸಿಸ್ಟ|ಶೀಘ್ರಲಿಪಿ|ಸಮಿತಿ\s*ಕ|ಲೆಕ್ಕಿಗ|ಜೂನಿಯರ್\s*ಪ್ರೋಗ್ರಾಮರ್|ಪ್ರಥಮ\s*ದರ್ಜೆ|"
                      r"ದ್ವಿತೀಯ\s*ದರ್ಜೆ")
# Kannada post words -> English (the page writes "ಕರ‍್ಯಪಾಲಕ" for "ಕಾರ್ಯಪಾಲಕ": the ZWJ is taken out before matching)
POSTS = [
    ("ವಲಯ ಆಯುಕ್ತರು", "Zonal Commissioner"), ("ಉಪ ಆಯುಕ್ತರು", "Deputy Commissioner"), ("ಆಯುಕ್ತರು", "Commissioner"),
    ("ಸಹಾಯಕ ಕರ್ಯಪಾಲಕ ಅಭಿಯಂತರರು", "Assistant Executive Engineer"), ("ಸಹಾಯಕ ಕಾರ್ಯಪಾಲಕ ಅಭಿಯಂತರರು", "Assistant Executive Engineer"),
    ("ಕರ್ಯಪಾಲಕ ಅಭಿಯಂತರರು", "Executive Engineer"), ("ಕಾರ್ಯಪಾಲಕ ಅಭಿಯಂತರರು", "Executive Engineer"),
    ("ಸಹಾಯಕ ಅಭಿಯಂತರರು", "Assistant Engineer"), ("ಕಿರಿಯ ಅಭಿಯಂತರರು", "Junior Engineer"), ("ಪರಿಸರ ಅಭಿಯಂತರರು", "Environmental Engineer"),
    ("ಹಿರಿಯ ಆರೋಗ್ಯ ನಿರೀಕ್ಷಕರು", "Senior Health Inspector"), ("ಕಿರಿಯ ಆರೋಗ್ಯ ನಿರೀಕ್ಷಕರು", "Junior Health Inspector"),
    ("ಆರೋಗ್ಯ ನಿರೀಕ್ಷಕರು", "Health Inspector"), ("ಆರೋಗ್ಯಾಧಿಕಾರಿ", "Health Officer"), ("ಕಂದಾಯ ಅಧಿಕಾರಿ", "Revenue Officer"),
    ("ಕಂದಾಯ ನಿರೀಕ್ಷಕರು", "Revenue Inspector"), ("ಸಹಾಯಕ ನಗರ ಯೋಜನೆ ಅಧಿಕಾರಿ", "Assistant Town Planning Officer"),
    ("ನಗರ ಯೋಜನೆ ಅಧಿಕಾರಿ", "Town Planning Officer"), ("ವೆರ್ನರಿ ಇನ್ಸ್ಪೆಕ್ಟರ್", "Veterinary Inspector"),
    ("ಎಸ್ಟೇಟ್ ಆಫೀಸರ್", "Estate Officer"), ("ಕಮ್ಯುನಿಟಿ ಅಫರ್ಸ ಆಫೀಸರ", "Community Affairs Officer"),
    ("ಅಸಿಸ್ಟಂಟ್ ಸ್ಟ್ಯಾಟಿಸ್ಟಿಕಲ್ ಆಫೀಸರ್", "Assistant Statistical Officer"), ("ಆಡಿಟರ್", "Auditor"),
]
WINGS = [("ನೀರು ಸರಬರಾಜು ಮತ್ತು ಯುಜಿಡಿ", "Water Supply and UGD"), ("ಡಬ್ಲ್ಯೂಎಸ್", "Water Supply"), ("ಯುಜಿಡಿ", "UGD"),
         ("ವಿದ್ಯುತ್", "Electrical"), ("ಸಿವ್ಹಿಲ್", "Civil"), ("ಸಿವಿಲ್", "Civil"), ("ಅಭಿವೃದ್ದಿ", "Development"),
         ("ಸೂಪರಿಂಟೆಂಡಿಂಗ್ ಇಂಜಿನೀಯರ್", "Superintending Engineer"), ("ಆಡಳಿತ", "Administration")]
KANNADA = re.compile(r"[ಀ-೿]")
ZONAL = re.compile(r"(?i)zonal\s*commissioner|ವಲಯ\s*ಆಯುಕ್ತ")


def items(get=None):
    out = []
    for c, (host, _, _, _) in BODIES.items():
        p = {"reader": MODULE, "url": f"http://{host}/en/city-staff", "state": STATE, "city": c, "india_only": True,
             "route": "direct"}
        if c in CONTACT:
            p["contact"] = f"http://{host}/en/contact-us"
        out.append({"key": f"{MODULE}-{c}", "payload": p})
    return out


def english(post):
    """English post of a Kannada one ("ಕಿರಿಯ ಅಭಿಯಂತರರು (ಡಬ್ಲ್ಯೂಎಸ್)" -> "Junior Engineer (Water Supply)"), or None."""
    k = post.replace("‍", "").replace("‌", "")
    for kn, en in POSTS:
        if k.startswith(kn.replace("‍", "")):
            rest, wings = k[len(kn):], []
            for kw, w in WINGS:     # longest first in WINGS: "ನೀರು ಸರಬರಾಜು ಮತ್ತು ಯುಜಿಡಿ" before "ಯುಜಿಡಿ"
                if kw in rest:
                    wings.append(w)
                    rest = rest.replace(kw, " ")
            return en + (f" ({', '.join(dict.fromkeys(wings))})" if wings else "")
    return None


def zone_area(post):
    m = re.search(r"(?i)zonal\s*commissioner\s*(?:-|–)?\s*(\d+)", post)
    if m:
        return f"Zone {m.group(1)}"
    rest = re.sub(r"(?i)zonal\s*commissioner|\(\s*in\s*charge\s*\)|\(\s*incharge\s*\)|[-–()]", " ", post)
    rest = _esw.clean(rest)
    if rest and not KANNADA.search(rest):
        return f"{rest.title()} Zone"
    return "Zone (not named on the page)"


def rows(html):
    """[(section, name, post, phone, src_pos)] of the staff table (the table with a "Designation" heading)."""
    soup = _esw.soup(html)
    out = []
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        if not trs or "designation" not in trs[0].get_text(" ").lower():
            continue
        head = [_esw.clean(c.get_text(" ")).lower() for c in trs[0].find_all(["td", "th"])]
        try:
            ni, di, ci = head.index("name"), head.index("designation"), next(i for i, h in enumerate(head) if "contact" in h)
        except (ValueError, StopIteration):
            continue
        section = ""
        for ri, tr in enumerate(trs[1:], 2):
            cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) == 1 or (len(cells) > 1 and not any(cells[1:])):
                section = cells[0]
                continue
            if len(cells) <= max(ni, di, ci):
                continue
            out.append((section, cells[ni], cells[di] or section, cells[ci], {"table": ti, "row": ri}))
    return out


def zonal_offices(html):
    """[(office, address, phone, email, src_pos)] of Mangaluru's contact table ("Mangaluru City Corporation Lalbag Zonal Office - 2
    M.G. Road ..." | phone | fax | email | site)."""
    out = []
    soup = _esw.soup(html)
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        for ri, tr in enumerate(trs, 1):
            cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            text = " ".join(cells)
            m = re.search(r"(?i)([A-Za-z]+)\s+Zonal\s+Off\w*\s*-?\s*(\d+)", cells[0] if cells else "")
            if not m or len(cells) < 3:
                continue
            ph = re.sub(r"(\d{3,5})\s*-\s*(\d{6,8})", r"\1-\2", cells[2])
            out.append((f"{m.group(1).title()} Zonal Office - {m.group(2)}", cells[1], ph,
                        re.sub(r"\s*@\s*", "@", " ".join(cells[3:])), {"table": ti, "row": ri}))
    return out


def parse(html, p, contact_html=None):
    city = p["city"]
    host, body, lgd, district = BODIES[city]
    seen, recs = set(), []
    kw = dict(body=body, lgd=lgd, state=STATE, district=district, source=p["url"])
    for section, name, post, ph, pos in rows(html):
        name = re.sub(r"(?i)^(shri|smt|sri)\.?\s*$", "", name).strip()
        ph = re.sub(r"(\d{3,5})\s*-\s*(\d{6,8})", r"\1-\2", ph)
        if not post or CLERICAL.search(post) or not (name or ph):
            continue
        en = english(post) if KANNADA.search(post) else None
        post_en = en or post
        regional = post if en else None
        kn_name = bool(KANNADA.search(name))
        if ZONAL.search(post):
            area = zone_area(post_en if not en else post)
            if en:
                area = "Zone (not named on the page)"
            recs.append(_ward.record(MODULE, f"{city}:{_esw.slug(area)}:zonal-commissioner:{_esw.slug(name) or len(recs)}", seen,
                                     level="zone", area=area, zone=area, post=post_en, post_regional=regional, name=name,
                                     name_regional=name if kn_name else None, phone=ph, section=section or None,
                                     role="head", wing="administration", **kw, src_pos=pos))
        else:
            recs.append(_ward.record(MODULE, f"{city}:body:{_esw.slug(post_en)}:{_esw.slug(name) or len(recs)}", seen,
                                     level="body", area=body, post=post_en, post_regional=regional, name=name,
                                     name_regional=name if kn_name else None, phone=ph, section=section or None, **kw,
                                     src_pos=pos))
    if contact_html:
        for office, addr, ph, text, pos in zonal_offices(contact_html):
            zone = office.split(" Zonal")[0] + " Zone"
            recs.append(_ward.record(MODULE, f"{city}:{_esw.slug(zone)}:zonal-office", seen, level="zone", area=zone, zone=zone,
                                     post="Zonal Office", phone=ph, email=_esw.emails(text), address=addr or None,
                                     office_name=office, wing="administration", role="staff", body=body, lgd=lgd,
                                     state=STATE, district=district, source=p["contact"], src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{p['city']}-city-staff", r.content)]
    c = get(p["contact"]) if p.get("contact") else None
    if c is not None:
        files.append(_esw.keep(MODULE, f"{p['city']}-contact-us", c.content))
    recs = parse(r.text, p, c.text if c is not None else None)
    staff = [x for x in recs if x[1]["source"] == p["url"]]
    zones = [x for x in recs if x[1]["source"] != p["url"]]
    _ward.tag(staff, r, p["url"])
    if c is not None:
        _ward.tag(zones, c, p["contact"])
    return recs, files, "" if recs else "no staff table"
