"""Arunachal Pradesh: district S3WaaS sites (<district>.nic.in). The police pages differ by district, so the reader takes the
form the page has:
- cards: /public-utility-category/police-station/ (Tirap): title 'Police Station, X', address, 'Phone :'. Paged /page/N/.
- tables: /police/ (East Siang, Kurung Kumey, Upper Siang, Lohit, Changlang, Dibang Valley): header names the columns
  (name, designation, station or place, phone columns). Kept: rows of a police station (OC / O/C / Officer-in-Charge, or
  a station column); fire, wireless, SB and reserve rows are left out.
- list: Itanagar Capital Police contacts: 'N. OC PS X Mobile no: ... Email: ...' (and SDPOs).
- blocks: Tawang /police/: '<X> Police Station' / 'Address:' / 'Contact:'.
Works from outside India (arunpol.nic.in itself has senior officers only). One queue item = one district page.
Record id dept:police_ar:<district>:<station>."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

M = "police_ar"
STATION = re.compile(r"\bO/?C\b|Officer[- ]in[- ]Charge|Police Station|\bP\.?S\.?(?=\W|$)", re.I)
OTHER = re.compile(r"Fire|\bFS\b|Control Room|\(SB\)|\bSB\b|\bWT\b|\bRI\b|Reserve|\bMTO\b|\bPC\b|Traffic|Duty Officer|-cum-CI", re.I)
OC = re.compile(r"^\s*(?:O/?C|Officer[- ]in[- ]Charge)\b(?:-cum-[\w()]+)?[\s,.:-]*", re.I)
COLS = {"name": re.compile(r"^(name(?! of police)|contact person)", re.I),
        "post": re.compile(r"designation|rank", re.I),
        "station": re.compile(r"name of police station|place of posting", re.I)}
PHONE_COL = re.compile(r"phone|mobile|contact|office|residence|landline", re.I)


def _rank(name):
    m = re.search(r"\(([^)]*)\)\s*$", name or "")
    if m and re.search(r"Insp|SI|ASI|Const|HC", m.group(1)):
        return clean(name[:m.start()].rstrip(", ")), m.group(1).strip(" .") + "."
    return name, None


def _area(post, place, district):
    base = clean(OC.sub("", post or "")).strip(" ,.") if post else ""
    if place and place.lower() not in base.lower():
        base = f"{base}, {place}" if base else place
    if base.lower() in ("police station", "ps", ""):
        base = f"Police Station, {district}"
    return base


def tables(soup, p):
    recs = []
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs:
            continue
        head = [clean(c.get_text(" ", strip=True)) or "" for c in trs[0].find_all(["td", "th"])]
        col = {k: next((i for i, h in enumerate(head) if rx.search(h)), None) for k, rx in COLS.items()}
        ph = [i for i, h in enumerate(head) if PHONE_COL.search(h) and i not in col.values()]
        if not ph or (col["post"] is None and col["station"] is None):
            continue
        for tr in trs[1:]:
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]
            if len(c) != len(head):
                continue
            g = lambda k: c[col[k]] if col[k] is not None else ""   # noqa: E731
            name, post, place = g("name"), g("post"), g("station")
            if OC.match(name) and not OC.match(post):          # 'Officer-in-Charge | Miao': the post sits in the name cell
                name, post, place = "", name, place or post
            label = f"{post} {place}"
            if not STATION.search(label) or OTHER.search(label):
                continue
            if col["post"] is not None and col["name"] is not None and not OC.match(post) and "Police Station" not in post:
                continue                                         # staff of a station, not its officer in charge
            name, rank = _rank(name)
            recs.append(_rec(p, _area(post, place, p["district"]), post="Officer in charge", name=name or None, rank=rank,
                             phone=phones(*(c[i] for i in ph))))
    return recs


def cards(soup, p):
    recs = []
    for li in soup.select("li.public-utlty-catg, .public-utlty-catg"):
        h = li.find(["h2", "h3"])
        if not h:
            continue
        items = [clean(x.get_text(" ", strip=True)) for x in li.select("ul.pubutility-list > li")]
        text = " | ".join(i for i in items if i)
        addr = items[0] if items and not re.match(r"(Phone|Email|Website|Pincode)", items[0] or "") else None
        m = re.search(r"Phone\s*:\s*([^|]+)", text)
        e = re.search(r"Email\s*:\s*([^|]+)", text)
        recs.append(_rec(p, clean(h.get_text(" ", strip=True)), post="Station", phone=phones(m.group(1)) if m else None,
                         email=email(e.group(1)) if e else None, address=addr))
    return recs


def listing(soup, p):
    recs = []
    text = clean(soup.get_text(" ", strip=True))
    for chunk in re.split(r"\s(?=\d{1,2}\.\s)|\s(?=[A-Z]{4,} JURISDICTION:)", text):
        m = re.match(r"\d{1,2}\.\s+(.+?)\s+Mobile(?: no)?\s*:\s*([\d\s/​]+)(?:.*?Email(?: Id)?\s*:\s*(\S+@\S+))?", chunk, re.I)
        if not m:
            continue
        post = clean(m.group(1))
        if OTHER.search(post):
            continue
        if re.match(r"SDPO\b", post):
            recs.append(_rec(p, re.sub(r"^SDPO\s*", "", post), level="subdivision", post="SDPO", phone=phones(m.group(2)),
                             email=email(m.group(3))))
        elif OC.match(post):
            recs.append(_rec(p, _area(post, None, p["district"]), post="Officer in charge", phone=phones(m.group(2)),
                             email=email(m.group(3))))
    return recs


def blocks(soup, p):
    lines = [clean(x) for x in soup.get_text("\n", strip=True).split("\n")]
    recs = []
    for i, ln in enumerate(lines):
        if not re.search(r"Police Station$", ln or "") or len(ln) > 60 or ln.startswith("Police stations"):
            continue
        addr = num = None
        for j in range(i + 1, min(i + 7, len(lines))):
            if re.search(r"Police Station$", lines[j] or ""):
                break
            if lines[j] == "Address:" and j + 1 < len(lines):
                addr = lines[j + 1]
            if lines[j] in ("Contact:", "Phone:") and j + 1 < len(lines):
                num = lines[j + 1]
        recs.append(_rec(p, ln, post="Station", phone=phones((num or "").rstrip(".")), address=addr))
    return recs


def _rec(p, area, level="police_station", **f):
    area = re.sub(r"\s+,", ",", area or "")
    return rec(M, f"{slug(p['district'])}:{slug(area)}", level=level, area=area, state="AR", district=p["district"],
               source=p["url"], **f)


FORMS = {"cards": cards, "tables": tables, "list": listing, "blocks": blocks}


def fetch(p, get):
    form = FORMS[p.get("form", "tables")]
    url, recs, files, n = p["url"], [], [], 0
    while url and n < 10:
        r = get(url)
        if r is None:
            break
        n += 1
        files.append(gz(M, f"{slug(p['district'])}-{n}.html", r.content))
        soup = BeautifulSoup(r.text, "lxml")
        main = soup.select_one("#SkipContent") or soup.select_one("main") or soup
        for x in main(["script", "style", "nav", "header", "footer"]):
            x.decompose()
        recs += form(main, p)
        nxt = soup.select_one("a.next.page-numbers, .pagination a.next") if p.get("form") == "cards" else None
        url = urljoin(url, nxt["href"]) if nxt and nxt.get("href") else None
    if n == 0:
        return [], [], "no answer"
    recs = uniq(recs)
    return recs, files, "" if recs else "no station rows"
