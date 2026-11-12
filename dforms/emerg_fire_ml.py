"""Meghalaya Fire & Emergency Services (megfireservice.gov.in, saved on archive.s1d.me 2026-11-05).
- "Key Contacts" (keycontacts.html): table 1 = senior officers (IGP, SPs F&ES, Divisional Fire Service Officers, training
  officer): name, rank, office, phones, email. Table 2 = one row per fire station / fire camp / control room: the officer in
  charge by name and rank (Station Officer, Sub Officer), office phone ("NA" when none) and mobiles.
- "Fire Stations" (fire_stations.html): district of every station and camp, and its building status ("Own land and building",
  "Newly Sanctioned", "Non Functional ..."). The reader joins it to the contacts by the station's first word(s).
The pages show no date. Record ids: dept:emerg_fire_ml:st-<station>, off-<email or name>.
"""
import re

from dforms import _emerg, _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_ml"
URL = "https://megfireservice.gov.in/keycontacts.html"
STATIONS_URL = "https://megfireservice.gov.in/fire_stations.html"
ALIASES = {"rajbhavan": "governorhouse", "garompani": "garampani"}


def items(get=None):
    return _emerg.seed(MODULE)


def base(station):
    """'Shillong F&ES Station Station.' / 'Shillong Fire Station' -> 'shillong'; camps keep 'camp'."""
    s = re.sub(r"(?i)\b(f\s*&\s*es|fire|station|stn)\b\.?", " ", station or "")
    return re.sub(r"[^a-z]", "", s.lower())


def stations(html):
    """{base name: (district, remarks, name as written)} from fire_stations.html."""
    out = {}
    for t in _esw.soup(html).find_all("table"):
        for row in _esw.grid(t)[1:]:
            if len(row) >= 4 and row[2]:
                dist = re.sub(r"(?i)\s*d[si]s?tr?ict\s*$|\s*dsitrict\s*$", "", _emerg.clean(row[1])).title()
                out.setdefault(base(row[2]), (dist, _emerg.clean(row[3]), _emerg.clean(row[2]).rstrip(".")))
    return out


def phone_parts(text):
    t = _emerg.clean(text.replace("|", " "))
    office = re.search(r"\(?O(?:ffice)?\)\s*([^()]*?)(?=\(|Hot|Mobile|$)", t)
    office = _emerg.clean(office.group(1)).strip(" /") if office else ""
    office = "" if re.fullmatch(r"(?i)na|not available", office) else office
    mobiles = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", t)
    return office, mobiles


def name_post(cell):
    """'Shri. Ganesh Muktan, | Station Officer' or 'Shri Tura | Station Officer' -> (name, post)."""
    parts = [x.strip(" ,") for x in re.split(r"\s*\|\s*", cell) if x.strip(" ,")]
    if len(parts) == 1:
        m = re.match(r"(.+?),\s*((?:senior\s+)?(?:station|sub)\s+officer.*)$", parts[0], re.I)
        parts = [m.group(1), m.group(2)] if m else parts
    return _emerg.clean(parts[0]), _emerg.clean(" ".join(parts[1:])) or None


def records(html, stations_html, url, stations_url=None):
    st = stations(stations_html) if stations_html else {}
    ts = _esw.soup(html).find_all("table")
    recs, seen, used = [], set(), set()
    for t in ts:
        g = _esw.grid(t)
        if not g:
            continue
        head = " ".join(g[0]).lower()
        if "fire station" in head:                       # station table
            for row in g[1:]:
                if len(row) < 4 or not row[2]:
                    continue
                name, post = name_post(row[1])
                area = _emerg.clean(row[2])
                b = base(area)
                b = ALIASES.get(b, b)
                info = st.get(b)
                if info:
                    used.add(b)
                office, mobiles = phone_parts(row[3])
                key = _emerg.unique(f"st-{_emerg.slug(area)}", seen)
                recs.append(_emerg.record(
                    MODULE, key, "fire", dept="fire", level="facility", area=area, post=post or "Officer in charge",
                    name=name, phone=", ".join(([office] if office else []) + mobiles), landline=office,
                    mobile=", ".join(mobiles), short_codes=_emerg.short_codes(row[3]) if "Hot" in row[3] else None,
                    district=info[0] if info else None, building=info[1] if info else None, state="ML",
                    office_id=key, source=url, district_source=stations_url if info else None))
        elif "designation" in head:                      # senior officers
            for row in g[1:]:
                if len(row) < 3:
                    continue
                parts = [x.strip(" ,.") for x in row[1].split("|") if x.strip(" ,.")]
                if not parts:
                    continue
                name = re.sub(r",\s*(IPS|MPS)$", r" (\1)", parts[0])
                post = ", ".join(parts[1:-1]) if len(parts) > 2 else (parts[1] if len(parts) > 1 else None)
                place = parts[-1] if len(parts) > 2 else None
                office, mobiles = phone_parts(row[2])
                email = _emerg.emails(row[3]) if len(row) > 3 else ""
                key = _emerg.unique(f"off-{_emerg.slug(email.split('@')[0] if email else name)}", seen)
                recs.append(_emerg.record(
                    MODULE, key, "fire", dept="fire", level="state" if "Tura" not in (place or "") else "zone",
                    area=place or "Meghalaya", post=post, name=name, phone=", ".join(([office] if office else []) + mobiles),
                    landline=office, mobile=", ".join(mobiles), email=email, state="ML", office_id=key, source=url))
    # stations on the station list without a contact row (newly sanctioned, non functional ...)
    for b, (dist, remarks, name) in st.items():
        if b in used:
            continue
        key = _emerg.unique(f"st-{_emerg.slug(name)}", seen)
        recs.append(_emerg.record(MODULE, key, "fire", dept="fire", level="facility", area=name, post="Station Officer",
                                  district=dist, building=remarks, state="ML", office_id=key, source=stations_url))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_emerg.keep(MODULE, "keycontacts", r.content)]
    surl = p.get("stations_url", STATIONS_URL)
    s = get(surl) if surl else None
    if s is not None:
        files.append(_emerg.keep(MODULE, "fire_stations", s.content))
    recs = records(r.text, s.text if s is not None else "", url, surl)
    return recs, files, "" if recs else "no rows"
