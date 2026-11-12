"""Karnataka State Police (India only). Two kinds of payload:
- default: KSP police station locator, ksp.karnataka.gov.in/pslocator/en. The district <select> (ids 1..41: districts,
  commissionerates, railways, CID, coastal police) feeds GET /home-fetch?select=district_id&value=<id>&dependent=district_row_id,
  which answers <option value="ADDRESS!@#$%EMAIL!@#$%PHONE!@#$%CIRCLE!@#$%LAT!@#$%LNG">STATION</option>. Landline, station email
  and coordinates; no names, no mobiles. Placeholders (email@ksp.gov.in, 88888-888888, '---', lat 0) are left out.
  One queue item = one district id; items(get) lists them from /pslocator/en. Record id dept:police_ka:<district id>:<station>.
- "kind": "bcp": Bengaluru City Police law & order page, bcp.karnataka.gov.in/24/law-&-order-/en (its server sends a wrong
  intermediate; certs/ has GlobalSign GCC R46). One table per division: SL No | Police Station | Mobile | Phone. A row label
  starts with the rank: DCP (division), ACP (subdivision), PI (station inspector, the SHO). The page carries every table twice.
  Record id dept:police_ka:bcp:<label>. Designation CUG mobiles (94808xxxxx); no names."""
import re

from bs4 import BeautifulSoup

from dforms._police import ascii_digits, clean, email, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_ka"
BASE = "https://ksp.karnataka.gov.in"
LOCATOR = BASE + "/pslocator/en"
BCP = "https://bcp.karnataka.gov.in/24/law-&-order-/en"
SEP = "!@#$%"
STD = re.compile(r"(?<!\d)\(?(0\d{2,4})\)?(\s*-\s*|\s+|\)\s*)(\d{6,8})(?!\d)")


def ph(*cells):
    """phones(), but 'STD-number' with a separator stays a landline (_police.one_phone reads '08372-278213' as a mobile)."""
    out = []
    for c in cells:
        c = ascii_digits(str(c or ""))
        pos = 0
        for m in list(STD.finditer(c)) + [None]:
            seg = c[pos:m.start()] if m else c[pos:]
            out += (phones(seg) or "").split(", ")
            if m:
                out.append(f"{m.group(1)}-{m.group(3)}")
                pos = m.end()
    out = [x for i, x in enumerate(out) if x and x not in out[:i]]
    return ", ".join(out) or None


def fetch_url(district_id):
    return f"{BASE}/home-fetch?select=district_id&value={district_id}&dependent=district_row_id"


def districts(html):
    soup = BeautifulSoup(html, "lxml")
    sel = soup.find("select", id="district_id")
    return [(o["value"], clean(o.get_text())) for o in (sel.find_all("option") if sel else []) if o.get("value") not in (None, "", "0")]


def items(get):
    r = get(LOCATOR)
    if r is None:
        return []
    out = [{"key": f"{M}:{v}-{slug(n)}", "payload": {"reader": M, "url": fetch_url(v), "state": "KA", "district_id": v, "district": n,
                                                    "india_only": True}} for v, n in districts(r.text)]
    return out + [{"key": f"{M}:bcp", "payload": {"reader": M, "kind": "bcp", "url": BCP, "state": "KA", "india_only": True}}]


def _val(s):
    s = clean(s)
    return None if not s or set(s) <= set("-_ ") else s


def parse_options(html, district_id, district, url=LOCATOR):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for o in soup.find_all("option"):
        st, v = clean(o.get_text()), o.get("value") or ""
        if not v or SEP not in v or not st:
            continue
        addr, mail, phone, circle, lat, lng = (v.split(SEP) + [None] * 6)[:6]
        mail = email(_val(mail) or "")
        try:
            la, lo = float(lat), float(lng)
        except (TypeError, ValueError):
            la = lo = None
        ok = la is not None and 11 < la < 19 and 74 < lo < 79
        recs.append(rec(M, f"{district_id}:{slug(st)}", area=st, post="Station (landline)", phone=ph(_val(phone)),
                        email=None if mail == "email@ksp.gov.in" else mail, address=_val(addr), circle=_val(circle), state="KA",
                        district=district, lat=la if ok else None, lon=lo if ok else None, source=url))
    return uniq(recs)


RANK = re.compile(r"^(DCP|ACP|PI)\b\.?\s*", re.I)


def parse_bcp(html, url=BCP):
    soup = BeautifulSoup(html, "lxml")
    recs, seen = [], set()
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        head = " ".join(c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])).lower() if trs else ""
        if "police station" not in head or "mobile" not in head:
            continue
        division = None
        for tr in trs[1:]:
            c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(c) < 4 or not c[1]:
                continue
            label, mobile, phone = c[1], c[2], c[3]
            m = RANK.match(label)
            rank = m.group(1).upper() if m else "PI"
            area = clean(label[m.end():]) if m else label
            if rank == "DCP":
                division = area
            if (label, mobile) in seen:
                continue
            seen.add((label, mobile))
            level = {"DCP": "division", "ACP": "subdivision"}.get(rank, "police_station")
            post = {"DCP": "Deputy Commissioner of Police", "ACP": "Assistant Commissioner of Police"}.get(rank, "Police Inspector (SHO)")
            recs.append(rec(M, f"bcp:{slug(label)}", level=level, area=area, post=post, rank=rank, phone=ph(mobile, _val(phone)),
                            state="KA", district="Bengaluru City", division=division if rank != "DCP" else None, source=url))
    return uniq(recs)


def fetch(p, get):
    if p.get("kind") == "bcp":
        url = p.get("url", BCP)
        r = get(url)
        if r is None:
            return [], [], "no answer"
        recs = parse_bcp(r.text, url)
        return recs, [gz(M, "bcp-law-order.html", r.content)], "" if recs else "no rows"
    did = str(p["district_id"])
    r = get(p.get("url") or fetch_url(did))
    if r is None:
        return [], [], "no answer"
    recs = parse_options(r.text, did, p.get("district"))
    return recs, [gz(M, f"home-fetch-{did}.html", r.content)], "" if recs else "no stations"
