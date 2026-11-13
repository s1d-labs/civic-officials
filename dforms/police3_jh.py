"""Jharkhand Police: www.jhpolice.gov.in/imp-contacts (Drupal view "Important Contacts", one page, 24 tables). Each table:
"Name | Rank/ Designation | Code (STD) | Office No. | Residence No. | Fax No. | Mobile No. | Email"; the range tables have a
<caption> ("South Chhotnagpur Range", "Dumka Range" ...) and list the range DIG and every district SP / SSP ("SP, Dumka",
"SSP Ranchi", "SP City, Jamshedpur", "SP, Traffic Ranchi"); the other tables are headquarters, CID, SB, ACB, JAP, training ...
E-mails are written "sp-dumka[at]jhpolice[dot]gov[dot]in". Kept: every row with a name or a number. District SP / SSP rows:
level district, district from the post (Chaibasa -> West Singhbhum, Jamshedpur -> East Singhbum, Saraikela -> Saraikela Kharsawan,
LGD spelling); SP City / Rural / Traffic: level district, office_type traffic for traffic, else office. Other rows: level state
(range DIG: level division). Office, residence and fax numbers get the row's STD code; fax goes to "fax".
Answers from Mumbai (2026-11-13); from abroad unchecked (police_jh notes the site answers only from India). One queue item = the
page. Record id dept:police3_jh:<table>-<row>-<post>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq

METHOD = "html table"

M = "police3_jh"
URL = "https://www.jhpolice.gov.in/imp-contacts"
DISTRICT = {
    "ranchi": "Ranchi", "lohardaga": "Lohardaga", "gumla": "Gumla", "simdega": "Simdega", "khunti": "Khunti",
    "chaibasa": "West Singhbhum", "west singhbhum": "West Singhbhum", "jamshedpur": "East Singhbum", "east singhbhum": "East Singhbum",
    "saraikela": "Saraikela Kharsawan", "dhanbad": "Dhanbad", "bokaro": "Bokaro", "hazaribagh": "Hazaribagh", "hazaribag": "Hazaribagh",
    "chatra": "Chatra", "koderma": "Koderma", "giridih": "Giridih", "ramgarh": "Ramgarh", "palamu": "Palamu", "latehar": "Latehar",
    "garhwa": "Garhwa", "dumka": "Dumka", "jamtara": "Jamtara", "deoghar": "Deoghar", "pakur": "Pakur", "sahebganj": "Sahebganj",
    "godda": "Godda",
}
SP = re.compile(r"^\s*S\.?S?\.?P\b\.?\s*(?:,\s*)?(?:(City|Rural|Traffic)\b\s*,?\s*)?(.*)$", re.I)


def dash(s):
    s = clean(s) or ""
    return "" if re.fullmatch(r"[-–\s,]*", s) else s


def mail(cell):
    t = re.sub(r"\s*\[\s*at\s*\]\s*", "@", clean(cell) or "")
    t = re.sub(r"\s*\[\s*dot\s*\]\s*", ".", t)
    out = []
    for m in re.finditer(r"[\w.\-]+@[\w.\-]+\.[a-z]{2,}", t):
        e = email(m.group(0))
        if e and e not in out:
            out.append(e)
    return ", ".join(out) or None


def with_std(std, cell):
    std = re.sub(r"\D", "", std or "")
    out = []
    for part in re.split(r"\s*[,/]\s*", dash(cell)):
        d = re.sub(r"\(.*?\)", "", part).strip()
        if not re.fullmatch(r"\d{5,12}", d):
            continue
        out.append(f"{std}-{d}" if std and len(d) <= 8 and not d.startswith("0") else d)
    return out


def district_post(post):
    """'SP, Dumka' -> ('Dumka', None); 'SP City, Jamshedpur' -> ('East Singhbum', 'City'); 'SP, Ops' -> (None, None)."""
    m = SP.match(clean(post) or "")
    if not m:
        return None, None
    rest = (m.group(2) or "").lower()
    sub = m.group(1)
    if not sub:
        m2 = re.search(r"\b(city|rural|traffic)\b", rest)
        sub = m2.group(1).title() if m2 else None
    for k, v in DISTRICT.items():
        if re.search(r"\b" + k + r"\b", rest):
            return v, (sub.title() if sub else None)
    return None, None


def parse(html, url=URL, state="JH"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        cap = t.find("caption")
        section = clean(cap.get_text(" ", strip=True)) if cap else None
        for ri, tr in enumerate(t.find_all("tr")):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < 8:
                continue
            name, post, std, office, resi, fax, mob, mails = c[:8]
            name = dash(name) or None
            if not post:
                continue
            nums = with_std(std, office) + with_std(std, resi) + [m for m in re.findall(r"\d{10,12}", dash(mob))]
            fx = with_std(std, fax)
            if not name and not nums and not dash(mails):
                continue
            dist, sub = district_post(post)
            if dist:
                level, otype, area = "district", ("traffic" if sub == "Traffic" else "office"), dist
            elif re.search(r"Range,?\s*DIG|DIG,?\s*Range", post, re.I):
                level, otype, area = "division", "office", section
            elif re.search(r"control", f"{name or ''} {post}", re.I):
                level, otype, area = "state", "control room", post
            else:
                level, otype, area = "state", "office", post
            d = dict(level=level, office_type=otype, area=area, post=post, name=name if name and not re.search(r"control|guest house", name, re.I) else None,
                     phone=phones(*nums), office_phone=", ".join(with_std(std, office)) or None,
                     residence_phone=", ".join(with_std(std, resi)) or None, fax=", ".join(fx) or None, email=mail(mails),
                     std=dash(std) or None, section=section, state=state, district=dist, sub_unit=sub, source=url,
                     src_pos={"table": ti, "row": ri})
            recs.append(rec(M, f"{ti}-{ri}-{slug(post)[:50]}", **d))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url, p.get("state", "JH"))
    return recs, [gz(M, "imp-contacts", r.content)], "" if recs else "no rows"
