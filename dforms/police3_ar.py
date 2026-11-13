"""Arunachal Pradesh Police contact directory: http://arunpol.nic.in/contactdir.html (one HTML page, about 87 KB; https fails
the chain check, http works; the archive has a copy). 51 tables "Designation | Name | Office | Residence", each after a heading
block: "<UNIT OR DISTRICT, HQ TOWN>", "STD - 0xxxx", "e-mail address:- ...". Police headquarters units first (DGP, IGPs,
SB, crime, ACB, traffic, fire, PTC, prison ...), then one table per district (control room, Superintendent of Police, Dy.SPs,
SDPOs), then the battalions. No station (OC) rows.
Kept: every row with a name or a number. District tables: SP -> level district office; SDPO -> level subdivision (area = the
place after "SDPO"); control room -> level district, office_type control_room; others (Dy.SP HQ, ASP ...) -> level district
unit. Other tables: level state (office_type unit; battalions office_type battalion). Landlines written without STD code get
the heading's STD code ("223283" + STD 03792 -> "03792-223283"); fax numbers go to "fax". The heading e-mail goes on the SP
row (or the control room row when there is no SP row). One queue item = the page.
Record id dept:police3_ar:<unit or district slug>:<post slug>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table (heading block before each table)"     # source trail (provenance.py)

M = "police3_ar"
URL = "http://arunpol.nic.in/contactdir.html"
DISTRICTS = ["Anjaw", "Bichom", "Changlang", "Dibang Valley", "East Kameng", "East Siang", "Kamle", "Keyi Panyor", "Kra Daadi",
             "Kurung Kumey", "Leparada", "Lohit", "Longding", "Lower Dibang Valley", "Lower Siang", "Lower Subansiri", "Namsai",
             "Pakke Kessang", "Papum Pare", "Shi Yomi", "Siang", "Tawang", "Tirap", "Upper Siang", "Upper Subansiri",
             "West Kameng", "West Siang"]
_KEY = {re.sub(r"[^a-z]", "", d.lower()): d for d in DISTRICTS}


def district_of(heading):
    """'PAPUMPARE DISTRICT, ITANAGAR (ICR)' -> 'Papum Pare'; 'LEPA RADA DISTRICT, Basar' -> 'Leparada'; 'BICHOM, LAPANGPHUNG' ->
    'Bichom'; 'SPECIAL BRANCH' -> None."""
    head = re.split(r"\bDISTRICT\b|,", heading, maxsplit=1, flags=re.I)[0]
    return _KEY.get(re.sub(r"[^a-z]", "", head.lower()))


def heading_block(table):
    """(heading, std, e-mail text) from the strings before the table."""
    head = std = mail = None
    for s in table.find_all_previous(string=True, limit=40):
        s = clean(s)
        if not s:
            continue
        if std is None and re.match(r"^STD\s*[-–]", s, re.I):
            std = re.sub(r"\D", "", s) or ""
            continue
        if mail is None and re.match(r"^e-?mail", s, re.I):
            mail = s
            continue
        letters = re.sub(r"[^A-Za-z]", "", s)
        if len(letters) > 3 and (s.upper() == s or re.search(r"\bDISTRICT\b", s)) and not re.match(r"^(STD|E-?MAIL|M-)", s, re.I):
            head = s
            break
    return head, std or None, mail


def numbers(cell, std):
    """'2292203 Fax-2212425' -> (['0360-2292203' if std], ['0360-2212425']); 'M-9436851097' -> mobile."""
    cell = clean(cell) or ""
    fax = []
    m = re.search(r"Fax\s*[-:]?\s*([\d\s/,-]*)", cell, re.I)
    if m:
        fax = [x for x in re.findall(r"\d{5,}", m.group(1))]
        cell = cell[:m.start()] + " " + cell[m.end():]
    out = []
    for n in re.findall(r"\d[\d-]{4,}", re.sub(r"\bM\s*-\s*", " ", cell)):
        n = n.strip("-")
        if std and re.fullmatch(r"[1-9]\d{4,7}", n) and not re.fullmatch(r"[6-9]\d{9}", n):
            n = f"{std}-{n}"
        out.append(n)
    fax = [f"{std}-{f}" if std and not f.startswith("0") and len(f) < 9 else f for f in fax]
    return out, fax


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        head, std, mail = heading_block(t)
        district = district_of(head or "")
        unit = head or f"table {ti}"
        batt = bool(re.search(r"\bBN\b|battalion", unit, re.I))
        mails = [e for e in (email(x) for x in re.split(r"[,\s]+", re.sub(r"^e-?mail[^:]*:-?\s*", "", mail or "", flags=re.I)))
                 if e]
        rows = []
        for ri, tr in enumerate(t.find_all("tr")):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]
            if len(c) < 2 or c[0].lower() == "designation" or not c[0]:
                provenance.skip_row(tr, 'skip: len(c) < 2 or c[0].lower() == "designation" or not c[0]')
                continue
            rows.append((ri, c + [""] * (4 - len(c))))
        seen_sp = False
        for ri, c in rows:
            post, name, office, resid = c[0], c[1], c[2], c[3]
            o1, f1 = numbers(office, std)
            o2, f2 = numbers(resid, std)
            ph = phones(*(o1 + o2))
            if not name and not ph:
                provenance.skipped('skip: not name and not ph')
                continue
            common = dict(name=name or None, phone=ph, fax=phones(*(f1 + f2)), state="AR", source=url, unit_heading=head,
                          std=std, office_phone=office or None, residence_phone=resid or None, src_pos={"table": ti, "row": ri})
            key = f"{slug(district or unit)}:{slug(post)}"
            if district:
                if re.match(r"^(Supdt\.?\s*of\s*Police|SP|Superintendent of Police)\b", post, re.I) and not seen_sp:
                    seen_sp = True
                    recs.append(rec(M, key, level="district", office_type="office", area=district, post=post, district=district,
                                    email=", ".join(mails) or None, **common))
                elif re.match(r"^SDPO\b", post, re.I):
                    area = re.sub(r"^SDPO\s*[,(]?\s*|\)$", "", post, flags=re.I).strip() or district
                    recs.append(rec(M, key, level="subdivision", office_type="subdivision", area=area, post=post,
                                    district=district, **common))
                elif re.match(r"^control room", post, re.I):
                    recs.append(rec(M, key, level="district", office_type="control_room", area=district, post=post,
                                    district=district, **common))
                else:
                    recs.append(rec(M, key, level="district", office_type="unit", area=district, post=post, district=district,
                                    **common))
            else:
                recs.append(rec(M, key, level="state", office_type="battalion" if batt else "unit", area=unit, post=post,
                                **common))
    return uniq(recs)


def items(get=None):
    return [{"key": f"{M}:contactdir", "payload": {"reader": M, "url": URL, "state": "AR"}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [gz(M, "contactdir", r.content)], "" if recs else "no rows"
