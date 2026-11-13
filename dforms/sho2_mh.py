"""Maharashtra: police station officers (the station in-charge, PI or API, with name and mobiles) and the sub-division / district
officers from the Satara district police site satarapolice.gov.in (PHP site by Dreamcare Developers; the other Dreamcare police
sites, Akola, Dhule, Beed, Solapur Rural, Palghar, Thane Rural, Navi Mumbai, moved to the state Next.js template that police2s_mh
reads). Pages (Marathi text, Devanagari digits; archive.s1d.me captures of 2026-11-05):
- /policestation?ps=<n> (n = 1..32; the site's own list comes from /getpolicestations, which answered 406 "Mod_Security" to a
  plain GET from dev-vps-3 on 2026-11-13, so the payload carries the ids): <h2 title="<station> Police Station">, the in-charge
  card (<h3 title=name>, <h4 title=rank>, tel: links = mobiles), "Telephone No.", "Division" (the SDPO sub-division), "Email
  ID", "Address", a Google Maps embed (!2d<lon>!3d<lat>), and the table "Police Station officers | Post | Mobile No." (APIs,
  PSIs of the station: kept in "officers").
- /Senior_Officers: cards (h4 title = name, p title = post, lanlandSvg = office number, mobSvg = mobile, mailto): SP, Addl. SP,
  the seven SDPOs ("उपविभागीय पोलीस अधिकारी (सातारा विभाग)": level subdivision, area = the sub-division), DySP (Home) and branch
  heads (level district, office_type unit).
Station names are Marathi on the page. area_regional = the name as written; area = the English name from STATION_EN below (the
reader's own table, checked against the civic.police_station names of LGD district 494 on 2026-11-13), so the loader ties the
station by name; lat / lon come from the page's map embed. A station whose Marathi name is not in STATION_EN keeps the
Marathi name as area. route "direct", india_only (the site's API refused a GET from Mumbai; the station pages are read from the
archive copies first). Record ids: dept:sho2_mh:satara:ps:<n> and dept:sho2_mh:satara:officer:<slug of post>-<slug of name>.
"""
import re

import provenance
from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug

METHOD = "html cards and table (Satara police site)"

MODULE = "sho2_mh"
STATE = "MH"
SITES = {
    "satara": {"base": "https://satarapolice.gov.in", "district": "Satara", "dc": "494", "ps": list(range(1, 33))},
}
STATION_EN = {
    "सातारा शहर": "Satara City", "सातारा तालुका": "Satara Taluka", "बोरगाव": "Borgaon", "कराड शहर": "Karad City",
    "कराड तालुका": "Karad Taluka", "तळबीड": "Talbid", "उंब्रज": "Umbraj", "वाई": "Wai", "महाबळेश्वर": "Mahabaleshwar",
    "पाचगणी": "Panchgani", "मेढा": "Medha", "भुईंज": "Bhuinj", "कोरेगाव": "Koregaon", "पुसेगाव": "Pusegaon",
    "रहिमतपूर": "Rahimatpur", "वाठार": "Wathar", "वडूज": "Vaduj", "दहीवाडी": "Dahiwadi", "म्हसवड": "Mhaswad", "औंध": "Aundh",
    "फलटण शहर": "Phaltan City", "फलटण ग्रामीण": "Phaltan Gramin", "लोणंद": "Lonand", "खंडाळा": "Khandala", "पाटण": "Patan",
    "कोयनानगर": "Koynanagar", "ढेबेवाडी": "Dhebewadi", "शिरवळ": "Shirwal", "शाहूपुरी": "Shahupuri", "सायबर": "Cyber",
    "मल्हारपेठ": "Malharpeth", "मसूर": "Masur",
}
# rank words of the in-charge (Marathi): PI = पोलीस निरीक्षक, API = सहाय्यक / सहायक / सहा. पोलीस निरीक्षक, PSI = पोलीस उपनिरीक्षक
API = re.compile(r"सहा")
PSI = re.compile(r"उपनिरीक्षक")
PI = re.compile(r"निरीक्षक")
SDPO = re.compile(r"उपविभागीय\s*पोलीस\s*अधिकारी\s*\(([^)]+)\)")
TOP = re.compile(r"^(पोलिस|पोलीस)\s*अधीक्षक$|अपर\s*पोलीस\s*अधीक्षक")


def items(get=None):
    out = []
    for site, s in SITES.items():
        out.append({"key": f"{MODULE}-{site}", "payload": {
            "reader": MODULE, "url": f"{s['base']}/Senior_Officers", "site": site, "base": s["base"], "district": s["district"],
            "dc": s["dc"], "ps": s["ps"], "state": STATE, "india_only": True, "route": "direct"}})
    return out


def _soup(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


def _t(s):
    return clean(ascii_digits(s or ""))


def sho_rank(rank):
    r = rank or ""
    if API.search(r):
        return "API"
    if PSI.search(r):
        return "PSI"
    if PI.search(r):
        return "PI"
    return None


def parse_station(html):
    """dict(station, name, rank, mobiles, telephone, division, email, address, lat, lon, officers[]) of one station page; None
    when the page has no station heading."""
    soup = _soup(html)
    h2 = soup.find("h2", title=re.compile(r"Police Station\s*$"))
    if h2 is None:
        return None
    station = _t(re.sub(r"\s*Police Station\s*$", "", h2["title"]))
    card = soup.find("div", class_="card-up")
    name = rank = None
    mobiles = []
    if card is not None:
        h3 = card.find("h3")
        h4 = card.find("h4", title=True)
        name = _t(h3.get("title") or h3.get_text(" ")) if h3 else None
        rank = _t(h4["title"]) if h4 else None
        mobiles = [_t(a.get_text(" ")) for a in card.find_all("a", href=re.compile(r"^tel:"))]
    labels = {}
    for p in soup.find_all("p", title=True):
        lab = p.find("span")
        if lab is None:
            continue
        key = _t(lab.get_text(" ")).rstrip(" :")
        val = p.find("span", class_="txt-val")
        labels.setdefault(key, _t(val.get_text(" ")) if val else _t(p.get_text(" ").split(":", 1)[-1]))
    lat = lon = None
    for f in soup.find_all("iframe", src=True):
        m = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", f["src"])
        if m:
            lon, lat = float(m.group(1)), float(m.group(2))
            break
    officers = []
    for tb in soup.find_all("table"):
        head = tb.find("thead")
        if head is None or "Police Station officers" not in head.get_text(" "):
            continue
        for i, tr in enumerate(tb.find_all("tr")):
            if tr.parent.name == "thead":
                continue
            cells = [_t(td.get_text(" ")) for td in tr.find_all("td")]
            if len(cells) < 2 or not cells[0]:
                provenance.skip_row(cells, "no name")
                continue
            officers.append({"name": cells[0], "post": cells[1], "phone": phones(cells[2]) if len(cells) > 2 else None})
    return {"station": station, "name": name, "rank": rank, "mobiles": mobiles, "telephone": labels.get("Telephone No."),
            "division": labels.get("Division"), "email": labels.get("Email ID"), "address": labels.get("Address"),
            "lat": lat, "lon": lon, "officers": officers}


def station_record(d, site, district, dc, url, ps_id, extra):
    area = STATION_EN.get(d["station"]) or d["station"]
    officers = [{k: v for k, v in o.items() if v} for o in d["officers"]]
    return rec(MODULE, f"{site}:ps:{ps_id}", level="police_station", post="Police Station In-charge", rank=d["rank"],
               sho_rank=sho_rank(d["rank"]), name=d["name"], phone=phones(*d["mobiles"]), telephone=phones(d["telephone"]),
               email=email(d["email"] or ""), address=d["address"], area=area, area_regional=d["station"], station=d["station"],
               subdivision=d["division"], officers=officers, lat=d["lat"], lon=d["lon"], state=STATE, district=district,
               district_lgd=dc, site=site, source=url, src_pos={"page": "station", "ps": ps_id}, **extra)


def parse_officers(html):
    """[dict(name, post, telephone, mobile, email, pos)] of the Senior_Officers cards."""
    soup = _soup(html)
    out = []
    for i, w in enumerate(soup.find_all("div", class_="card-wrapper-sr"), 1):
        up = w.find("div", class_="card-up")
        h4 = up.find("h4") if up else None
        p = up.find("p") if up else None
        name = _t(h4.get("title") or h4.get_text(" ")) if h4 else ""
        post = _t(p.get("title") or p.get_text(" ")) if p else ""
        tel, mob, mail = [], [], None
        for row in w.find_all("div", class_="marg-10"):
            img = row.find("img")
            kind = (img.get("src") or "") if img else ""
            for a in row.find_all("a", href=True):
                if a["href"].startswith("mailto:"):
                    mail = mail or email(a["href"][7:])
                elif a["href"].startswith("tel:") and _t(a.get_text(" ")):
                    (tel if "lanland" in kind else mob).append(_t(a.get_text(" ")))
        out.append({"name": name, "post": post, "telephone": phones(*tel), "mobile": phones(*mob), "email": mail, "pos": i})
    return out


def officer_records(rows, site, district, dc, url, extra):
    recs, seen = [], set()
    for o in rows:
        if not o["name"] or not o["post"]:
            provenance.skip_row([o["name"], o["post"]], "no name or post")
            continue
        if not (o["mobile"] or o["telephone"] or o["email"]):
            provenance.skip_row([o["name"], o["post"]], "no phone or email")
            continue
        m = SDPO.search(o["post"])
        if m:
            level, office_type, area = "subdivision", None, _t(re.sub(r"\s*विभाग\s*$", "", m.group(1)))
        elif TOP.search(o["post"]):
            level, office_type, area = "district", None, district
        else:
            level, office_type, area = "district", "unit", district
        key = f"{site}:officer:{slug(o['post'])}-{slug(o['name'])}"
        if key in seen:
            provenance.skipped("same card twice")
            continue
        seen.add(key)
        provenance.used()
        recs.append(rec(MODULE, key, level=level, office_type=office_type, post=o["post"], name=o["name"], phone=o["mobile"],
                        telephone=o["telephone"], email=o["email"], area=area, state=STATE, district=district,
                        district_lgd=dc, site=site, source=url, src_pos={"page": "senior officers", "card": o["pos"]},
                        **extra))
    return recs


def fetch(p, get):
    base, site, district, dc = p["base"], p["site"], p["district"], p.get("dc")
    files, recs, answered, why = [], [], 0, []
    r = get(p["url"])
    if r is not None:
        answered += 1
        files.append(gz(MODULE, f"{site}-senior-officers", r.content))
        recs += officer_records(parse_officers(r.text), site, district, dc, p["url"], provenance.at(r, p["url"]))
    for n in p.get("ps", []):
        u = f"{base}/policestation?ps={n}"
        r = get(u)
        if r is None:
            why.append(f"ps {n}: no answer")
            continue
        answered += 1
        files.append(gz(MODULE, f"{site}-ps-{n}", r.content))
        d = parse_station(r.text)
        if d is None:
            provenance.skipped("page without a station")
            continue
        if not (d["name"] or d["mobiles"] or d["telephone"] or d["email"]):
            provenance.skipped("station without officer or number")
            continue
        provenance.used()
        recs.append(station_record(d, site, district, dc, u, n, provenance.at(r, u)))
    if not answered:
        return [], [], "no answer"
    return recs, files, "" if recs else "no officer rows"
