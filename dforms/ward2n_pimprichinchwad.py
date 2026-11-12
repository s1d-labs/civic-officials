"""Pimpri Chinchwad Municipal Corporation (pcmcindia.gov.in): its 10 zonal offices (क्षेत्रीय कार्यालय A, B, C, D, E, F, G, H, J, L),
each office's address, phones, email and prabhag (ward) numbers, and the Assistant Commissioner who heads each office.
Two kinds of page (plain HTML, Marathi; answer from Germany):
  /ward_info: one table per zone (id "a-zone" ...: name + address | "Phone no. ... Mo.9922501453/454 e mail:- ..."), then a table
  "प्रभाग क्र. | समाविष्ट भाग" (prabhag number in Devanagari digits | areas). In archive.s1d.me (saved 2026-11-05).
  /departments-details?Id=21,22,23,24,50,51,52,54,66,67: "विभाग - अ क्षेत्रीय कार्यालय", "HOD Information" table (Name, Designation,
  Email, Mobile No) and the office address. Not in archive.s1d.me (the city-sites-pun-pcmc crawl has the text only); live sample
  2026-11-11.
One queue item reads all 11 pages and joins them by the zone letter. Records (level "zone"): "<X>:zone-office" (post "Zonal Office",
address, phones, email, wards = the prabhag numbers) and "<X>:head" (the HOD: post in English, post_regional as written, name =
name_regional = the Marathi name as written, email, mobile, wards of the zone). Record ids: dept:ward2n_pimprichinchwad:<x>:...
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_pimprichinchwad"
BODY, LGD, STATE, DISTRICT = "Pimpri Chinchwad Municipal Corporation", "251528", "MH", "Pune"
BASE = "https://www.pcmcindia.gov.in"
URL = f"{BASE}/ward_info"
HOD_IDS = (21, 22, 23, 24, 50, 51, 52, 54, 66, 67)
LETTERS = {"अ": "A", "ब": "B", "क": "C", "ड": "D", "इ": "E", "फ": "F", "ग": "G", "ह": "H", "ज": "J", "ल": "L"}
REGIONAL = {v: f"{k} क्षेत्रीय कार्यालय" for k, v in LETTERS.items()}
POSTS = (("सहाय्यक आयुक्त", "Assistant Commissioner"), ("सहायक आयुक्त", "Assistant Commissioner"), ("उप आयुक्त", "Deputy Commissioner"),
         ("उपायुक्त", "Deputy Commissioner"), ("क्षेत्रीय अधिकारी", "Zonal Officer"), ("प्रशासन अधिकारी", "Administrative Officer"))
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def items(get=None):
    return [{"key": f"{MODULE}-zones", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def letter(text):
    m = re.match(r"\s*([अबकडइफगहजल])\s*(?:क्षेत्रीय|प्रभाग)", _esw.clean(text))
    return LETTERS.get(m.group(1)) if m else None


def mobiles(text):
    """'9922501453/454' -> 9922501453, 9922501454 (the site writes the second mobile as its last digits)."""
    out = []
    for a, rest in re.findall(r"([6-9]\d{9})((?:\s*/\s*\d{3,10})*)", text):
        out.append(a)
        for b in re.findall(r"\d{3,10}", rest):
            out.append(a[:10 - len(b)] + b if len(b) < 10 else b)
    return out


def zones(html):
    """{letter: {"name", "address", "phone", "email", "wards"}} from /ward_info."""
    soup = _esw.soup(html)
    out, cur = {}, None
    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if t.get("id", "").endswith("-zone") and g:
            cells = [c for c in g[0] if c]
            parts = [p.strip() for p in cells[0].split("|")]
            x = letter(parts[0])
            if not x:
                continue
            contact = re.sub(r"(?i)mail\s*:?-\s*", "mail: ", " | ".join(cells[1:]))
            phone = ", ".join(dict.fromkeys(_esw.phones(re.sub(r"(?i)mo\.?[\d/\s]+", " ", contact)).split(", ") + mobiles(contact)))
            cur = out[x] = {"name": parts[0], "address": ", ".join(p.strip(" ,") for p in parts[1:] if p.strip(" ,")),
                            "phone": phone.strip(", "), "email": _esw.emails(contact), "wards": [],
                            "pos": {"table": _esw.table_no(t), "selector": f"table#{t.get('id')}", "row": gp[0]["row"]}}
            continue
        if cur is not None and g and "प्रभाग" in g[0][0]:
            cur["pos"]["ward_table"] = _esw.table_no(t)
            for r, rp in zip(g[1:], gp[1:]):
                n = _esw.clean(r[0]).translate(DIGITS)
                if re.fullmatch(r"\d{1,3}", n) and n not in cur["wards"]:
                    cur["wards"].append(str(int(n)))
            cur = None
    return out


def hod(html):
    """(letter, {"name", "post", "email", "mobile", "address"}) from one /departments-details page, or (None, {})."""
    soup = _esw.soup(html)
    h = soup.find(lambda tag: tag.name in ("h2", "h3") and "विभाग" in tag.get_text())
    x = letter(_esw.clean(h.get_text()).split("-", 1)[-1]) if h else None
    if not x:
        return None, {}
    f = {}
    for tr in soup.select("div.commissionerSection table tr"):
        tds = tr.find_all("td")
        if len(tds) == 2:
            f[_esw.clean(tds[0].get_text()).lower()] = _esw.clean(tds[1].get_text(" "))
    addr = soup.select_one("div.department-info div.card-body")
    return x, {"name": f.get("name", ""), "post": f.get("designation", ""), "email": f.get("email", ""), "mobile": f.get("mobile no", ""),
               "address": _esw.clean(addr.get_text(" ")) if addr else ""}


def post_en(post):
    return next((en for hi, en in POSTS if hi in post), _ward.hi_post(post))


def parse(zone_html, hod_pages, p):
    """zone_html: /ward_info; hod_pages: [(url, html)] of the departments-details pages."""
    z = zones(zone_html) if zone_html else {}
    seen, recs = set(), []
    for x, d in z.items():
        recs.append(_ward.record(MODULE, f"{x.lower()}:zone-office", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone",
                                 area=f"{x} Zonal Office", area_regional=d["name"], zone=f"{x} Zone", post="Zonal Office",
                                 address=d["address"], phone=d["phone"], email=d["email"], wards=d["wards"], wing="administration",
                                 source=URL, src_url=p.get("url") or URL, src_pos=d.get("pos")))
    for url, html in hod_pages:
        x, h = hod(html)
        if not x or not (h["name"] or h["email"] or h["mobile"]):
            continue
        name = h["name"]
        recs.append(_ward.record(MODULE, f"{x.lower()}:head", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone",
                                 area=f"{x} Zonal Office", area_regional=z.get(x, {}).get("name") or REGIONAL[x],
                                 zone=f"{x} Zone", post=post_en(h["post"]), post_regional=h["post"], name=name, name_regional=name,
                                 email=h["email"], phone=h["mobile"], address=h["address"], wards=z.get(x, {}).get("wards"),
                                 source=url, src_url=url, src_pos={"selector": "div.commissionerSection table tr"}))
    return recs


def fetch(p, get):
    files, hods = [], []
    r = get(p["url"])
    zone_html = r.text if r is not None else ""
    if r is not None:
        files.append(_esw.keep(MODULE, "ward_info", r.content))
    for i in HOD_IDS:
        u = f"{BASE}/departments-details?Id={i}"
        a = get(u)
        if a is None:
            continue
        files.append(_esw.keep(MODULE, f"departments-details-{i}", a.content))
        hods.append((u, a.text))
    recs = parse(zone_html, hods, p)
    return recs, files, "" if recs else "no zone tables and no HOD pages"
