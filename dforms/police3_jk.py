"""Jammu and Kashmir Police: jkpolice.gov.in/Police-Stations (one page, 23 tables, one per police district: Anantnag ..
Udhampur, with Awantipora, Handwara and Sopore as police districts of their own) and jkpolice.gov.in/Women-Police-Stations
(one table: Police Station | Telephone Numbers). Static HTML, no login, no captcha; answered from Mumbai on 2026-11-13
(police_jk's note of 2026-11-05 says it did not answer then).
Police-Stations tables: 'Sub Division | Police Station'; the first cell is 'SDPO Bijbehara (01932-234276)', 'DySP Tral',
'Dy. SP Hqrs (9596767703)' or empty (same sub-division as the row above); the second cell is one or more
'P/S Bijbehara (01932-234221, 2...)'. The heading before each table names the police district.
Kept: each station (level police_station, post SHO, area 'PS <name>' as police_jk writes it, phone = the station numbers as
published, subdivision) and each territorial SDPO / DySP (level subdivision); 'Dy. SP Hqrs' / DAR / Traffic heads are left as
the station's subdivision only. No names on this page.
Police district -> LGD district: Awantipora -> Pulwama, Handwara -> Kupwara, Sopore -> Baramulla; others the same name.
One queue item = one page (payload "page": "stations" or "women"). Record id dept:police3_jk:<police district>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police3_jk"
URL = "https://jkpolice.gov.in/Police-Stations"
WOMEN = "https://jkpolice.gov.in/Women-Police-Stations"
LGD = {"Awantipora": "Pulwama", "Handwara": "Kupwara", "Sopore": "Baramulla", "Bandipore": "Bandipora"}
PS_IN_CELL = re.compile(r"(P/S\s+[^()]+?)\s*(?:\(([^)]*)\))?(?=\s*P/S\s|$)")
SUB = re.compile(r"^(SDPO|Dy\.?\s*SP|DySP|DSP)\s+(.+?)\s*(?:\(([^)]*)\))?$", re.I)
SUB_UNIT = re.compile(r"\b(Hqrs?|HQ|DAR|Traffic|PCR|Crime|CID|Security|Lines|Women)\b", re.I)


def heading(t):
    h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "strong", "b", "button", "a"])
    return clean(h.get_text(" ", strip=True)) if h else None


def station_area(n):
    """'P/S Safakadal Near Idgah Srinagar' -> ('PS Safakadal', 'Near Idgah Srinagar')."""
    n = re.sub(r"^P/S\s+", "PS ", clean(n).strip(" ,."))
    m = re.match(r"^(.+?)\s+(Near\s+.+)$", n, re.I)
    return (m.group(1).strip(" ,"), m.group(2)) if m else (n, None)


def table_recs(t, ti, pdist, url):
    district = LGD.get(pdist, pdist)
    common = dict(state="JK", district=district, police_district=pdist, source=url)
    recs, sub = [], None
    for ri, tr in enumerate(t.find_all("tr")):
        c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
        if len(c) < 2:
            continue
        pos = {"table": ti, "row": ri}
        if c[0]:
            m = SUB.match(c[0])
            sub = (station_area(m.group(2))[0] if m else re.sub(r"\s*\(.*$", "", c[0])) or None
            if m and not SUB_UNIT.search(m.group(2)):
                post = "SDPO" if m.group(1).upper() == "SDPO" else "DySP"
                recs.append(rec(M, f"{slug(pdist)}:sdpo-{slug(sub)}", level="subdivision", office_type="subdivision",
                                post=post, area=sub, address=station_area(m.group(2))[1], phone=phones(m.group(3)), office=c[0], src_pos=pos,
                                **common))
        for n, num in PS_IN_CELL.findall(c[1]):
            area, where = station_area(n)
            otype = "women" if re.search(r"\bwomen\b", area, re.I) else "police station"
            recs.append(rec(M, f"{slug(pdist)}:{slug(area)}", level="police_station", office_type=otype, post="SHO", area=area,
                            phone=phones(num), telephone=num or None, address=where, subdivision=sub, src_pos=pos,
                            **common))
    return recs


def parse_stations(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        first = t.find("tr")
        head = (clean(first.get_text(" ", strip=True)) or "").lower() if first else ""
        if not ("police station" in head and "division" in head):
            continue
        pdist = heading(t)
        if not pdist:
            continue
        recs += table_recs(t, ti, pdist, url)
    seen, out = set(), []
    for rid, d in recs:                  # the same SDPO can repeat on several rows
        if rid in seen and d["level"] == "subdivision":
            continue
        seen.add(rid)
        out.append((rid, d))
    return uniq(out)


def parse_women(html, url=WOMEN, districts=()):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        for ri, tr in enumerate(t.find_all("tr")):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < 2 or not re.search(r"P/S|police station", c[0], re.I):
                continue
            area = station_area(c[0])[0]
            place = re.sub(r"^PS\s+Women\s*", "", area, flags=re.I).split(",")[-1].strip()
            dist = next((d for d in districts if d.lower() in area.lower()), None) or LGD.get(place, place) or None
            recs.append(rec(M, f"women:{slug(area)}", level="police_station", office_type="women", post="SHO", area=area,
                            phone=phones(c[1]), telephone=c[1], state="JK", district=dist, source=url,
                            src_pos={"table": ti, "row": ri}))
    return uniq(recs)


DISTRICTS = ("Anantnag", "Bandipora", "Baramulla", "Budgam", "Doda", "Ganderbal", "Jammu", "Kathua", "Kishtwar", "Kulgam",
             "Kupwara", "Poonch", "Pulwama", "Rajouri", "Ramban", "Reasi", "Samba", "Shopian", "Srinagar", "Udhampur")


def fetch(p, get):
    women = p.get("page") == "women"
    url = p.get("url") or (WOMEN if women else URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse_women(r.text, url, DISTRICTS) if women else parse_stations(r.text, url)
    return recs, [gz(M, "women" if women else "stations", r.content)], "" if recs else "no rows"
