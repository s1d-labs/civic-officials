"""Assam: officers on the sites of the "Standardized Website Framework 2.0" (SWF, Drupal 10, NIC Assam: theme "swf", footer
"Standardized Website Framework 2.0 | Government of Assam"). Every district administration site <district>.assam.gov.in runs it,
and so do the state department sites (police, pnrd, fcsca, dhs ... .assam.gov.in).

The S3WaaS reader (whoswho.py) finds nothing on these sites: their officers are cards, not tables. Two pages per site:
- /whos-who: cards grouped under headings (div.whoswho-subtitle h6: "District Development Commissioner", "Co-District
  Commissioner", "Additional District Commissioner", "Assistant Commissioner" ...); each card (div.card_info) has the name
  (h6) and a list (ul.rim-hod-contacts): "Designation: ...", phone (fa-phone), e-mail (fa-envelope), office (fa-map-pin).
- /contact-us: the head of office (div.hod-contact-card: name h5, post h6) and the other officers (div.rim-contact-card: name h5,
  "Designation:", address, ul.phone-mobile, ul.fax-mail). E-mails are written "dc-kamrup[at]nic[dot]in".
The same officer is on both pages: one record per (name, post), the fields of both cards joined.

Measured 2026-11-12 from Mumbai: kamrup.assam.gov.in answers in 1.7 s; the hub's earlier district runs failed on these hosts
(GitHub runners: ConnectTimeout; Indian proxies: HTTP 504 and 429), so the items are India-only and the project should run
slowly (1 worker per host).

Records (depts.py contract): dept administration (district sites) or the payload's dept; level district, or subdivision for a
Co-District Commissioner / SDO (area = the place in the office address: "O/o the Co-District Commissioner, Rangia" -> Rangia),
or subdistrict for a Circle Officer; post = the designation, category = the heading on the Who's Who page, name, phone, email,
address, district + district_code (LGD, from the payload), page, last_updated (the page footer "Last Updated: 30-Oct-2026").
One queue item = one site (2 GETs). Ids: dept:swf_as:<host>:<slug of name>:<slug of post>.
"""
import re
from datetime import datetime

from dforms import _esw
import provenance

METHOD = "html cards (SWF Who's Who / Contact Us)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "swf_as"
PAGES = ["whos-who", "contact-us"]
# district site host -> (LGD district code, LGD name); Sribhumi = the former Karimganj district
DISTRICTS = {
    "bajali": ("739", "Bajali"), "baksa": ("616", "Baksa"), "barpeta": ("280", "Barpeta"), "biswanath": ("705", "Biswanath"),
    "bongaigaon": ("281", "Bongaigaon"), "cachar": ("282", "Cachar"), "charaideo": ("708", "Charaideo"), "chirang": ("612", "Chirang"),
    "darrang": ("283", "Darrang"), "dhemaji": ("284", "Dhemaji"), "dhubri": ("285", "Dhubri"), "dibrugarh": ("286", "Dibrugarh"),
    "dimahasao": ("299", "Dima Hasao"), "goalpara": ("287", "Goalpara"), "golaghat": ("288", "Golaghat"),
    "hailakandi": ("289", "Hailakandi"), "hojai": ("709", "Hojai"), "jorhat": ("290", "Jorhat"), "kamrup": ("291", "Kamrup"),
    "kamrupmetro": ("618", "Kamrup Metro"), "karbianglong": ("292", "Karbi Anglong"), "karimganj": ("293", "Sribhumi"),
    "sribhumi": ("293", "Sribhumi"), "kokrajhar": ("294", "Kokrajhar"), "lakhimpur": ("295", "Lakhimpur"), "majuli": ("706", "Majuli"),
    "morigaon": ("296", "Marigaon"), "nagaon": ("297", "Nagaon"), "nalbari": ("298", "Nalbari"), "sivasagar": ("300", "Sivasagar"),
    "sonitpur": ("301", "Sonitpur"), "southsalmaramankachar": ("707", "South Salmara Mancachar"), "tamulpur": ("756", "Tamulpur"),
    "tinsukia": ("302", "Tinsukia"), "udalguri": ("617", "Udalguri"), "westkarbianglong": ("710", "West Karbi Anglong"),
}
DEPT_SITES = {  # state department sites on SWF with a Who's Who / contact page (host -> dept key of civic-india/TAGGING.md)
    "police.assam.gov.in": "police", "pnrd.assam.gov.in": "rural_development", "fcsca.assam.gov.in": "food_supplies",
    "dhs.assam.gov.in": "health", "elementary.assam.gov.in": "education", "madhyamik.assam.gov.in": "education",
    "phe.assam.gov.in": "water", "pwdroads.assam.gov.in": "public_works", "landrevenue.assam.gov.in": "revenue",
    "transport.assam.gov.in": "transport", "sec.assam.gov.in": "elections",
}
PLACEHOLDER = re.compile(r"(?i)^(mr\.?|shri)?\s*(test|hod name|name)$")


def _t(el):
    return _esw.clean(el.get_text(" ")) if el is not None else ""


def _icon_items(ul_or_card):
    """(icon class, text) of each <li> or <p> with an <i class="fa ..."> icon."""
    out = []
    for li in ul_or_card.find_all(["li", "p"]):
        i = li.find("i", class_=re.compile(r"\bfa\b|fa-"))
        if i is None:
            continue
        cls = " ".join(i.get("class") or [])
        out.append((cls, _t(li)))
    return out


def _fields(card):
    """name, post, phone, email, address of one card (any of the three card kinds)."""
    f = {"name": "", "post": "", "phone": "", "email": "", "address": "", "fax": ""}
    h = card.find(["h6", "h5"])
    f["name"] = _t(h)
    if "hod-contact-card" in (card.get("class") or []):
        f["post"] = _t(card.find("h6"))
        f["name"] = _t(card.find("h5"))
    for el in card.find_all(["li", "p"]):
        t = _t(el)
        m = re.match(r"(?i)^designation\s*:?\s*(.*)$", t)
        if m and not f["post"]:
            f["post"] = m.group(1).strip(" :")
    for cls, t in _icon_items(card):
        if "phone" in cls or "mobile" in cls:
            f["phone"] = ", ".join(x for x in (f["phone"], _esw.phones(t)) if x)
        elif "envelope" in cls or "mail" in cls:
            f["email"] = ", ".join(x for x in (f["email"], _esw.emails(t)) if x)
        elif "fax" in cls:
            f["fax"] = _esw.phones(t)
        elif "map" in cls or "location" in cls:
            f["address"] = t
    return f


def cards(html):
    """[(category, fields)] of a Who's Who or Contact Us page."""
    soup = _esw.soup(html)
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    area = soup.find(id="swf_content_area") or soup
    out = []
    for n, card in enumerate(area.find_all("div", class_=re.compile(r"^(card_info|rim-contact-card|hod-contact-card)$")), 1):
        head = card.find_previous("div", class_="whoswho-subtitle")
        cat = _t(head.find("h6")) if head is not None else ""
        f = _fields(card)
        if not f["name"] or PLACEHOLDER.match(f["name"]):
            provenance.skip_row(card, 'skip: not f["name"] or PLACEHOLDER.match(f["name"])')
            continue
        f["_pos"] = {"selector": "#swf_content_area div.card_info|rim-contact-card|hod-contact-card", "card": n}   # source trail
        out.append((cat, f))
    return out


def page_updated(html):
    html = re.sub(r"(?s)<!--.*?-->", "", html or "")
    m = re.search(r"(?i)Last Updated\s*:?\s*(?:(?:<[^>]+>|&nbsp;)\s*)*(\d{1,2}-[A-Za-z]{3}-\d{4})", html)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def level_area(post, address, district):
    p = post.lower()
    place = re.sub(r"(?i)^.*?(commissioner|officer|sdo|sdm|circle)\s*(\(civil\))?\s*,?\s*", "", address or "").strip(" ,.")
    place = re.split(r",", place)[0].strip() if place else ""
    if re.search(r"co-?district commissioner|sub-?divisional|\bsdo\b|\bsdm\b", p):
        return "subdivision", place or district
    if re.search(r"circle officer|revenue circle", p):
        return "subdistrict", place or district
    return "district", district


def build(pages, p):
    """pages: [(url, html)] of one site -> records."""
    host = p.get("host") or re.sub(r"^https?://", "", p["url"]).split("/")[0]
    dept = p.get("dept") or "administration"
    district, code = p.get("district", ""), p.get("district_code", "")
    merged, order = {}, []
    for url, html in pages:
        lu = page_updated(html)
        for cat, f in cards(html):
            k = (_esw.slug(re.sub(r"(?i)^(shri|smt|sri|dr|mr|mrs|ms)\.?\s+", "", f["name"])), _esw.slug(f["post"]))
            if k not in merged:
                merged[k] = dict(f, category=cat, page=url, last_updated=lu)
                order.append(k)
                continue
            m = merged[k]
            m["_pos"] = {**m.get("_pos", {}), "also": m.get("_pos", {}).get("also", []) + [{"url": url, **f.get("_pos", {})}]}
            for x in ("phone", "email", "address", "fax"):
                if f[x] and f[x] not in m[x]:
                    m[x] = ", ".join(v for v in (m[x], f[x]) if v)
            if cat and not m["category"]:
                m["category"] = cat
    recs = []
    for k in order:
        f = merged[k]
        level, area = level_area(f["post"], f["address"], district or "Assam")
        recs.append(_esw.record(MODULE, f"{host}:{k[0]}:{k[1] or 'officer'}", dept=dept, level=level, area=area, post=f["post"],
                                category=f["category"] or None, name=f["name"], phone=f["phone"], email=f["email"],
                                fax=f["fax"] or None, address=f["address"], state="AS", district=district or None,
                                district_code=code or None, site=host, page=f["page"], source=f["page"],
                                last_updated=f["last_updated"], office_id=f"{host}:{k[0]}",
                                src_url=f["page"], src_pos=f.get("_pos")))   # "also": the same person on a later page (merged)
    return recs


def items(get=None):
    out = []
    for slug, (code, name) in sorted(DISTRICTS.items()):
        if slug == "karimganj":
            continue
        host = f"{slug}.assam.gov.in"
        out.append({"key": f"{MODULE}:{host}", "payload": {"reader": MODULE, "url": f"https://{host}/", "host": host, "state": "AS",
                                                            "district": name, "district_code": code, "dept": "administration",
                                                            "india_only": True}})
    for host, dept in sorted(DEPT_SITES.items()):
        out.append({"key": f"{MODULE}:{host}", "payload": {"reader": MODULE, "url": f"https://{host}/", "host": host, "state": "AS",
                                                            "dept": dept, "level": "state", "india_only": True}})
    return out


def fetch(p, get):
    base = p["url"].rstrip("/")
    pages, files, why = [], [], ""
    for name in PAGES:
        r = get(f"{base}/{name}")
        if r is None:
            why = why or f"no answer from /{name}"
            continue
        pages.append((getattr(r, "url", "") or f"{base}/{name}", r.text))
        files.append(_esw.keep(MODULE, f"{p.get('host') or base.split('//')[-1]}/{name}", r.content))
    if not pages:
        return [], [], why or "no answer"
    recs = build(pages, p)
    return recs, files, "" if recs else "no officer cards"
