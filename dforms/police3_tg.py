"""Telangana police, sources that police_tg / police2s_tg do not read. Payload "form":
- "hyd": Hyderabad City Police, www.hyderabadpolice.gov.in/ps/<x>_ps.html, /acp/<x>_acp.html, /dcp/<x>_dcp.html (plain HTML,
  answers from Mumbai; abroad unchecked). A station page names the SHO (name, CUG mobile, rank), the station landlines and
  mobile, the patrol cars, the station email (written over two lines: "sho-cmnr-hyd@tspolice<br>.gov.in"), the detective
  inspector and the sector SIs (kept in "officers"), the ACP and DCP offices. ACP / DCP pages: name, designation, phones, email,
  jurisdiction. items(get) lists every page linked from know_your_ps.html.
- "hyd_dir": the same site's Important_Contacts.html, one table "S.No. | Name of the Officer | Rank | Office Phone Numbers |
  Mobile Number | Email ID" (CP, Addl. CP, Jt. CPs, DCPs ...): level district (heads) or unit.
- "cyb": Cyberabad Police Commissionerate, www.cyberabadpolice.gov.in/Preview?page_id=<n> (CKEditor tables "Label | : |
  Value"). Station pages (SHO, rank, cell; detective inspector; PS landline, PS number, cyber warrior, e-mail, location), ACP and
  DCP pages. items(get) lists the pages linked from the Law & Order page (page_id=273).
- "s3waas": a district portal page parsed by police_s3waas (Hanumakonda, Nagarkurnool, Mahabubnagar, Mahabubabad, Yadadri).
- "si_table": a district portal table "Sl.No | Name of the Officer | Place of working | Govt.No.s" (Mahabubabad: the SIs, who
  are the SHOs of the mandal stations). One record per row; a place with SI-I and SI-II gives two records.
Districts: Hyderabad City spans Hyderabad and part of Ranga Reddy; Cyberabad spans Ranga Reddy, Medchal-Malkajgiri and
Sangareddy. The station's district comes from STATION_DISTRICT (station names of civic.police_station in those districts),
else the commissionerate's main district. Record id dept:police3_tg:<form>:<district slug>:<station or post slug>."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from dforms import police_s3waas
from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html label/value text (Hyderabad, Cyberabad pages) + html table"     # source trail (provenance.py)

M = "police3_tg"
HYD = "https://www.hyderabadpolice.gov.in/"
CYB = "https://www.cyberabadpolice.gov.in/"

RR = "Ranga Reddy"
MED = "Medchal Malkajgiri"
SAN = "Sangareddy"
STATION_DISTRICT = {   # slug of the station name (no "PS") -> district, for stations outside the commissionerate's main district
    **{k: RR for k in ("adibatla", "balapur", "meerpet", "shamshabad", "rgia", "rgia-op", "pahadi-shareef", "pahadishareef",
                       "rajendra-nagar", "rajendranagar", "attapur", "mailardevpally", "narsingi", "gachibowli", "madhapur",
                       "raidurgam", "miyapur", "chandanagar", "rc-puram", "kokapet", "shankarpally", "moinabad", "chevella",
                       "shabad", "shadnagar", "kothur", "nandigama", "keshampet", "kondurg", "chowdarigudem", "amangal",
                       "talakondapally", "kadthal")},
    **{k: SAN for k in ("patancheru", "kollur", "ameenpur", "ida-bollaram", "bdl-bhanoor", "ramachandrapuram", "jinnaram",
                        "gummadidala")},
    **{k: MED for k in ("kphb", "balanagar", "kukatpally", "allapur", "medchal", "jeedimetla", "dundigal", "jagadgirigutta",
                        "pet-basheerbad", "suraram", "genome-valley", "bachupally", "sanathnagar", "shamirpet", "alwal")},
}


def station_district(station, default):
    k = slug(re.sub(r"\b(?:police station|p\.?s\.?)$", "", clean(station) or "", flags=re.I).strip(" -"))
    return STATION_DISTRICT.get(k, default)


def lines(node):
    out = []
    for t in node.get_text("\n").split("\n"):
        t = clean(t)
        if t:
            out.append(t)
    return out


def join_email(ls):
    """'sho-cmnr-hyd@tspolice' + '.gov.in' on the next line -> one address; '[at]' / '[dot]' forms too."""
    out = []
    for i, t in enumerate(ls):
        if out and t.startswith(".") and "@" in out[-1] and not out[-1].endswith((".in", ".com")):
            out[-1] += t
            continue
        out.append(t)
    return out


def emails(ls):
    found = []
    for t in ls:
        e = email(t)
        if e and e not in found:
            found.append(e)
    return ", ".join(found) or None


# ---------------------------------------------------------------- Hyderabad City

def hyd_items(html):
    out, seen = [], set()
    for path, kind in re.findall(r'href="((ps|acp|dcp)/[^"]+\.html)"', html):
        if path in seen:
            continue
        seen.add(path)
        out.append({"key": f"{M}:hyd:{path.rsplit('/', 1)[1][:-5]}",
                    "payload": {"reader": M, "form": "hyd", "kind": kind, "url": HYD + path, "state": "TG"}})
    return out


def after(ls, label, n=1):
    """The n lines after the first line equal to label (case-insensitive), or []."""
    low = [x.lower() for x in ls]
    try:
        i = low.index(label.lower())
    except ValueError:
        return []
    return ls[i + 1:i + 1 + n]


def section(ls, start, stops):
    low = [x.lower() for x in ls]
    if start.lower() not in low:
        return []
    i = low.index(start.lower()) + 1
    out = []
    for t in ls[i:]:
        if t.lower() in stops:
            break
        out.append(t)
    return out


def hyd_parse(html, url, kind):
    soup = BeautifulSoup(html, "lxml")
    for x in soup(["script", "style", "nav", "header", "footer"]):
        x.decompose()
    ls = join_email(lines(soup))
    title = clean(soup.title.get_text()) if soup.title else ""
    low = [x.lower() for x in ls]
    if "back" in low and low.index("back") > 0:          # the page heading is the line before "Back"
        title = ls[low.index("back") - 1]
    if kind == "ps":
        station = re.sub(r"\s+police station$", "", title, flags=re.I).strip() or title
        district = station_district(station, "Hyderabad")
        sho = after(ls, "Station House Officer (SHO)")
        mob = after(ls, "Mobile No")
        rank = after(ls, "Designation")
        loc = after(ls, "PS Location")
        contacts = section(ls, "Police Station Contacts", {"detective inspector", "sector details", "division details"})
        cars = [t for t in contacts if re.match(r"patro?l? car", t, re.I)]
        plain = [t for t in contacts if t not in cars]
        officers = []
        di = after(ls, "Detective Inspector", 3)
        if di and di[0].lower() != "mobile no":
            officers.append({"post": "Detective Inspector", "name": di[0], "phone": phones(di[2]) if len(di) > 2 else None})
        sec = section(ls, "Sector Details", {"sector area wise", "division details", "zone details", "strength details"})
        i = 0
        while i + 2 < len(sec) + 1 and i + 1 < len(sec):
            post, name = sec[i], sec[i + 1]
            ph = phones(sec[i + 2]) if i + 2 < len(sec) and re.search(r"\d{6}", sec[i + 2]) else None
            officers.append({"post": post, "name": name, "phone": ph})
            i += 3 if ph else 2
        strength = {}
        st = section(ls, "Strength Details", {"for any queries and suggestions regarding this website"})
        for j in range(0, len(st) - 1, 2):
            v = st[j + 1].strip(": ")
            if v.isdigit():
                strength[st[j]] = int(v)
        name = sho[0] if sho else None
        return [rec(M, f"hyd:{slug(district)}:{slug(station)}", area=station, post="SHO", rank=rank[0] if rank else None,
                    name=name, phone=phones(*(mob[:1] + [t for t in plain if "@" not in t])),
                    patrol_cars=phones(*(re.sub(r"^.*?:\s*", "", t) for t in cars)), email=emails(plain), address=loc[0] if loc else None, district=district,
                    state="TG", commissionerate="Hyderabad City", source=url, officers=officers, strength=strength or None,
                    src_pos={"label": "Station House Officer (SHO)"})]
    # acp / dcp
    name = after(ls, "Name")
    desig = after(ls, "Designation", 3)
    d = desig[0] if desig else None
    if desig and len(desig) > 1 and re.match(r"^of police$", desig[1], re.I):
        d = f"{desig[0]} {desig[1]}"
    mob = after(ls, "Mobile No")
    contact = section(ls, "Contact", {"jurisdiction"}) or section(ls, "Zonal Contacts", {"social network", "name"})
    juris = [re.sub(r"^PS\s+", "", t) for t in section(ls, "Jurisdiction", {"importatnt information", "important information",
             "for any queries and suggestions regarding this website", "close"}) if re.match(r"^PS\s", t)]
    area = re.sub(r"^(DCP|ACP)\s+", "", title, flags=re.I).strip()
    post = "DCP" if kind == "dcp" else "ACP"
    level = "district" if kind == "dcp" else "circle"
    district = station_district(re.sub(r"\s+zone$", "", area, flags=re.I), "Hyderabad")
    officers = []
    names = [i for i, x in enumerate(low) if x == "name"]
    for i in names[1:]:                                   # DCP pages: the Addl. DCP after the DCP
        blk = ls[i:i + 8]
        o = {"name": blk[1] if len(blk) > 1 else None}
        bl = [x.lower() for x in blk]
        if "mobile no" in bl:
            o["phone"] = phones(blk[bl.index("mobile no") + 1])
        if "designation" in bl:
            j = bl.index("designation") + 1
            o["post"] = " ".join(blk[j:j + 2]) if j + 1 < len(blk) and blk[j + 1].lower() == "of police" else blk[j]
        officers.append(o)
    return [rec(M, f"hyd:{kind}:{slug(area)}", level=level, office_type="zone" if kind == "dcp" else "circle", area=area,
                post=f"{post} {area}", rank=d, name=name[0] if name else None,
                phone=phones(*(mob[:1] + [re.sub(r"^.*?:\s*", "", t) for t in contact if "@" not in t and "[at]" not in t])),
                email=emails(contact), district=district, state="TG", commissionerate="Hyderabad City", source=url,
                jurisdiction=juris or None, officers=officers or None, src_pos={"label": "Name"})]


def hyd_dir_parse(html, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        for ri, tr in enumerate(t.find_all("tr")):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < 4 or not c[0].strip(". ").isdigit():
                provenance.skip_row(tr, 'skip: len(c) < 4 or not c[0].strip(". ").isdigit()')
                continue
            # rows lack the name cell when the post is vacant or unnamed: S.No | Rank | Office | Mobile? | Email
            if len(c) >= 6:
                name, rank, office, mobile, mail = c[1], c[2], c[3], c[4], c[5]
            else:
                name, rank, office = "", c[1], c[2]
                rest = c[3:]
                mail = next((x for x in rest if "[at]" in x or "@" in x), "")
                mobile = next((x for x in rest if x != mail), "")
            if re.match(r"^(sri|smt|ms|mr|dr)\b", rank, re.I) and not name:
                name, rank = rank, ""
            post = rank
            head = re.search(r"^(commissioner of police|addl\.? commissioner|jt\.? commissioner|dy\.? commissioner)", post, re.I)
            recs.append(rec(M, f"hyd_dir:{slug(post)}", level="district", office_type="office" if head else "unit",
                            area="Hyderabad City", post=post, name=name.rstrip(",") or None, phone=phones(office, mobile),
                            email=email(mail), district="Hyderabad", state="TG", commissionerate="Hyderabad City",
                            source=url, src_pos={"table": ti, "row": ri}))
    return uniq(recs)


# ---------------------------------------------------------------- Cyberabad

def cyb_items(html):
    m = re.search(r'id="row".*', html, re.S)
    body = m.group(0) if m else html
    out, seen = [], set()
    for pid, label in re.findall(r'<a[^>]*href="/?Preview\?page_id=(\d+)"[^>]*>(.*?)</a>', body, re.S):
        label = clean(re.sub(r"<[^>]+>|&nbsp;", " ", label)) or ""
        kind = "dcp" if re.match(r"^DCP", label) else "acp" if re.match(r"^ACP", label) else "ps" if re.search(r"\bPS$", label) else None
        if not kind or pid in seen:
            continue
        seen.add(pid)
        out.append({"key": f"{M}:cyb:{pid}", "payload": {"reader": M, "form": "cyb", "kind": kind, "label": label,
                                                         "url": f"{CYB}Preview?page_id={pid}", "state": "TG"}})
    return out


def pairs(ls):
    """'Label', ':', 'Value' triples -> [(label, value)] in page order; a ':' with no value gives ''."""
    out = []
    for i, t in enumerate(ls):
        if t == ":" and i > 0:
            v = ls[i + 1] if i + 1 < len(ls) and ls[i + 1] != ":" and (i + 2 >= len(ls) or ls[i + 2] != ":") else ""
            out.append((ls[i - 1].rstrip(" :."), v))
    return out


def cyb_parse(html, url, kind, label=""):
    soup = BeautifulSoup(html, "lxml")
    row = soup.find(id="row") or soup
    for x in row(["script", "style"]):
        x.decompose()
    ls = lines(row)
    pr = pairs(ls)
    title = ls[0] if ls else label
    val = lambda *names: next((v for k, v in pr if k.lower() in names and v and v.strip("-") != ""), None)  # noqa: E731
    if kind == "ps":
        station = re.sub(r"\s+", " ", title).strip()
        station = re.sub(r"\bPS$", "PS", station.title().replace("Ps", "PS")) if station.isupper() else station
        district = station_district(station, RR)
        names = [v for k, v in pr if k.lower() in ("sho", "name")]
        cells = [v for k, v in pr if k.lower().startswith("cell no")]
        officers = []
        if len(names) > 1:
            officers.append({"post": val("designation") or "Detective Inspector", "name": names[1],
                             "phone": phones(cells[1]) if len(cells) > 1 else None})
        loc = after(ls, "PS Location")
        return [rec(M, f"cyb:{slug(district)}:{slug(station)}", area=station, post="SHO", rank=val("rank"),
                    name=names[0] if names else None,
                    phone=phones(*(cells[:1] + [v for k, v in pr if k.lower() in ("land line", "ps no")])),
                    cyber_warrior=phones(val("cyber warrrior", "cyber warrior")), email=email(val("e-mail", "email") or ""),
                    address=loc[0] if loc else None, district=district, state="TG", commissionerate="Cyberabad", source=url,
                    officers=officers or None, src_pos={"label": "SHO"})]
    area = re.sub(r"^(DCP|ACP)\s+", "", re.sub(r"\s+", " ", title), flags=re.I).strip()
    zone = after(ls, "Zone")
    post = "DCP" if kind == "dcp" else "ACP"
    return [rec(M, f"cyb:{kind}:{slug(area)}", level="district" if kind == "dcp" else "circle",
                office_type="zone" if kind == "dcp" else "circle", area=area, post=f"{post} {area}", rank=val("designation"),
                name=val("name"), phone=phones(val("cell no", "mobile no"), val("land line")),
                email=email(val("email") or ""), zone=zone[0] if zone else None,
                district=station_district(re.sub(r"\s+zone$", "", area, flags=re.I), RR), state="TG",
                commissionerate="Cyberabad", source=url, src_pos={"label": "Name"})]


# ---------------------------------------------------------------- district portal SI table

def si_parse(html, url, district):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        rows = t.find_all("tr")
        if not rows:
            continue
        head = [clean(x.get_text(" ", strip=True)) or "" for x in rows[0].find_all(["th", "td"])]
        if not any(re.search(r"place of working", h, re.I) for h in head):
            continue
        hi = {k: next((i for i, h in enumerate(head) if re.search(p, h, re.I)), None)
              for k, p in (("name", r"name"), ("place", r"place"), ("phone", r"govt|phone|cell|mobile|contact|no\.?s$"))}
        title = clean(t.find_previous(["h1", "h2", "h3", "h4", "p", "strong"]).get_text(" ", strip=True)) if t.find_previous(
            ["h1", "h2", "h3", "h4", "p", "strong"]) else ""
        for ri, tr in enumerate(rows[1:], 1):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < len(head) or not c[hi["name"]]:
                provenance.skip_row(tr, 'skip: len(c) < len(head) or not c[hi["name"]]')
                continue
            place = c[hi["place"]]
            m = re.match(r"^(SI-?\s*[IV]+|W?SI|SHO|Inspector|Inspr\.?|CI)\s*[,:-]?\s*(.+)$", place, re.I)
            post = m.group(1).upper().replace(" ", "") if m else "SI"
            station = (m.group(2) if m else place).strip()
            recs.append(rec(M, f"si:{slug(district)}:{slug(station)}:{slug(post)}", area=station, post=post,
                            name=c[hi["name"]], phone=phones(c[hi["phone"]]) if hi["phone"] is not None else None,
                            district=district, state="TG", list_title=title or None, source=url,
                            src_pos={"table": ti, "row": ri}))
    return uniq(recs)


# ---------------------------------------------------------------- task

S3WAAS = [   # (url, district): district portal pages police_s3waas reads (checked on archive copies, 2026-11-13)
    ("https://hanumakonda.telangana.gov.in/public-utility-category/police-stations/", "Hanumakonda"),
    ("https://nagarkurnool.telangana.gov.in/police/", "Nagarkurnool"),
    ("https://nagarkurnool.telangana.gov.in/police-2/", "Nagarkurnool"),
    ("https://mahabubnagar.telangana.gov.in/public-utility-category/police-stations/", "Mahabubnagar"),
    ("https://mahabubabad.telangana.gov.in/public-utility-category/police-stations/", "Mahabubabad"),
    ("https://yadadri.telangana.gov.in/police/", "Yadadri Bhuvanagiri"),
]
SI_TABLES = [("https://mahabubabad.telangana.gov.in/police/", "Mahabubabad")]


def static_items():
    out = [{"key": f"{M}:hyd_dir", "payload": {"reader": M, "form": "hyd_dir", "url": HYD + "Important_Contacts.html",
                                               "state": "TG"}}]
    for url, d in S3WAAS:
        out.append({"key": f"{M}:s3waas:{slug(url.split('//')[1].rstrip('/'))}",
                    "payload": {"reader": M, "form": "s3waas", "url": url, "state": "TG", "district": d}})
    for url, d in SI_TABLES:
        out.append({"key": f"{M}:si:{slug(d)}", "payload": {"reader": M, "form": "si_table", "url": url, "state": "TG",
                                                            "district": d}})
    return out


def items(get):
    out = static_items()
    r = get(HYD + "know_your_ps.html")
    if r is not None:
        out += hyd_items(r.text)
    r = get(CYB + "Preview?page_id=273")
    if r is not None:
        out += cyb_items(r.text)
    return out


def fetch(p, get):
    form = p.get("form")
    if form == "s3waas":
        return police_s3waas.fetch({"state": "TG", **p}, get, M)
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = slug(url.split("//", 1)[1])[:120]
    if form == "hyd":
        recs = hyd_parse(r.text, url, p.get("kind") or url.split("/")[-2])
    elif form == "hyd_dir":
        recs = hyd_dir_parse(r.text, url)
    elif form == "cyb":
        recs = cyb_parse(r.text, url, p.get("kind", "ps"), p.get("label", ""))
        content = re.sub(rb"data:[a-z/+]+;base64,[A-Za-z0-9+/=]+", b"data:,", r.content)   # inline images: 1-2 MB per page
        return recs, [gz(M, name, content)], "" if recs else "no rows"
    elif form == "si_table":
        recs = si_parse(r.text, url, p["district"])
    else:
        return [], [], f"unknown form {form!r}"
    recs = [x for x in recs if x[1].get("name") or x[1].get("phone")]
    return recs, [gz(M, name, r.content)], "" if recs else "no rows"
