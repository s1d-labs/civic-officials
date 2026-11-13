"""Nagar Nigam Rudrapur (nagarnigamrudrapur.com, Uttarakhand; WordPress): the sanitation staff of every ward and the zonal office.
Two public pages (live sample 2026-11-13 from Mumbai, not in archive.s1d.me):
  /ward-supervisor-list/  table 1 "Sanitation Inspectors (सफाई निरीक्षक)": Name | Designation | Phone | Allocated Wards
                          ("वार्ड नं० 01 व 02 एवं वार्ड नं० 12 से 19 तक"); table 2 "Ward Sanitation Supervisors (पर्यावरण पर्यवेक्षक
                          सूची)": ward no | ward name | supervisor name | mobile (40 wards, 2018 delimitation; LGD still has 20).
  /zonal-office/          one table "Zonal Department (जोनल कार्यालय आवास विकास)": Name | Designation | Phone.
Records: inspectors at level "ward" with the wards in their charge; supervisors at level "ward", one record per person (a person
over two wards gets both wards, area_regional = the ward names); zonal office staff at level "zone", area "Awas Vikas Zonal
Office". Names and posts are Hindi: name / name_regional and post (English) / post_regional (as written).
Record ids: dept:ward3_rudrapur:<post slug>:<mobile or row>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_rudrapur"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Rudrapur", "248471", "UK", "Udham Singh Nagar"
URLS = {"supervisors": "https://www.nagarnigamrudrapur.com/ward-supervisor-list/",
        "zonal": "https://www.nagarnigamrudrapur.com/zonal-office/"}
ZONE_AREA = "Awas Vikas Zonal Office"
POSTS = ((r"परिचारक\s*/\s*प्र0?\s*कर", "Attendant (Tax Collector in charge)"), (r"जोनल\s*कार्यालय\s*प्रभारी", "Zonal Office In-Charge"), (r"पर्यावरण\s*पर्यवेक्षक", "Ward Sanitation Supervisor"),
         (r"कर\s*संग्रहकर्ता", "Tax Collector"), (r"जन्म\s*मृत्यु", "Junior Assistant (Birth and Death)"),
         (r"कनिष्ठ\s*सहायक", "Junior Assistant"), (r"लाइनमैन", "Attendant (Lineman in charge)"), (r"परिचारक", "Attendant"))


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": u, "state": STATE, "page": k}} for k, u in URLS.items()]


def en_post(post):
    p = _ward.hi_norm(post)
    m = re.search(r"\(([A-Za-z][^)]*)\)", p)      # "जोनल कार्यालय प्रभारी (Zonal Office In-Charge)"
    if m and not re.search(r"(?i)उपनल", m.group(1)):
        return _esw.clean(m.group(1))
    for rx, en in POSTS:
        if re.search(rx, p):
            return en
    return _ward.hi_post(post)


def hi_wards(text):
    """"वार्ड नं० 01 व 02 एवं वार्ड नं० 12 से 19 तक" -> 1, 2, 12..19."""
    t = _ward.hi_norm(text).replace("नं0", " ").replace("वार्ड", " ")
    t = re.sub(r"\s*से\s*", " to ", t).replace("तक", " ")
    t = re.sub(r"\s*(?:व|एवं|और)\s*", ", ", t)
    return _ward.wards_of(t)


def phone_of(s):
    return "" if re.fullmatch(r"[-\s.]*", s or "") else s


def parse_supervisors(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "Allocated Wards")[:1]:
        for r in rows:
            post, name, ph = _ward.col(r, "Designation"), _ward.col(r, "Name"), phone_of(_ward.col(r, "Phone"))
            ws = hi_wards(_ward.col(r, "Allocated"))
            en = en_post(post)
            recs.append(_ward.record(MODULE, f"{_esw.slug(en)}:{ph or len(recs)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="ward", area="Wards " + ", ".join(ws) if ws else "Wards",
                                     post=en, post_regional=post, name=name, name_regional=name, phone=ph, wards=ws,
                                     wards_note=None if ws else "no wards given", wing="sanitation",
                                     source=p["url"], src_pos=r.pos))
    people = {}
    for head, rows in _ward.header_tables(html, "Supervisor")[:1]:
        for r in rows:
            w, wname = _ward.col(r, "वार्ड नं"), _ward.col(r, "Ward Name")
            name, ph = _ward.col(r, "Supervisor"), phone_of(_ward.col(r, "Mobile"))
            if not re.fullmatch(r"\d{1,3}", w or "") or not (name or ph):
                continue
            g = people.setdefault((ph or name), {"name": name, "phone": ph, "wards": [], "names": [], "pos": []})
            g["wards"].append(str(int(w)))
            g["names"].append(wname)
            g["pos"].append(r.pos)
    for g in people.values():
        ws = g["wards"]
        area = ("Ward " if len(ws) == 1 else "Wards ") + ", ".join(ws)
        recs.append(_ward.record(MODULE, f"ward-sanitation-supervisor:{g['phone'] or len(recs)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area=area, area_regional=", ".join(g["names"]),
                                 post="Ward Sanitation Supervisor", post_regional="पर्यावरण पर्यवेक्षक", name=g["name"],
                                 name_regional=g["name"], phone=g["phone"], wards=ws, wing="sanitation",
                                 source=p["url"], src_pos=g["pos"][0] if len(g["pos"]) == 1 else
                                 {"rows": g["pos"], "note": "one person over these ward rows"}))
    return recs


def parse_zonal(html, p):
    seen, recs = set(), []
    for head, rows in _ward.header_tables(html, "Name", "Designation")[:1]:
        for r in rows:
            post, name, ph = _ward.col(r, "Designation"), _ward.col(r, "Name"), phone_of(_ward.col(r, "Phone"))
            if not (name or ph):
                continue
            en = en_post(post)
            recs.append(_ward.record(MODULE, f"zonal:{_esw.slug(en)}:{ph or len(recs)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=ZONE_AREA, zone=ZONE_AREA, post=en, post_regional=post,
                                     name=name, name_regional=name, phone=ph,
                                     role="head" if "प्रभारी" in post and "जोनल" in post else "staff",
                                     wing="revenue" if "कर" in post else None, source=p["url"], src_pos=r.pos))
    return recs


def parse(html, p):
    page = p.get("page") or next((k for k, u in URLS.items() if u == p.get("url")), "supervisors")
    return parse_zonal(html, p) if page == "zonal" else parse_supervisors(html, p)


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, p.get("page") or "page", r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no staff table"
