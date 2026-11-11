"""West Bengal district police sites with plain HTML tables (www.purbamedinipurpolice.gov.in, WordPress). Payload "form":
- "stations": /police-stations/: 'Name of P.S. | OC Name | Email Id | Contact' ("OC Kajal Dutta", "IC Shri Md. Kudrute Khoda":
  the post IC (inspector in charge) or OC (officer in charge) comes first in the name cell; the contact is the station CUG).
- "directory": /telephone-directory/: 'Designation | Name | Office | Residence | Mobile', with a heading row per police
  sub-division and its STD code ("TAMLUK SUB-DIVISION (STD-03228)"). Kept: SP / Addl. SP (level district), "SDPO, Tamluk"
  (subdivision), "CI Nandakumar" (circle, the circle inspector), "I/C Tamluk" / "O/C Moyna" / "IC Haldia Women PS"
  (police station) and "Incharge Choukhali Bazer OP" / "I/C Kolaghat BH" / "Incharge Tamluk TOP" (police post). Office and
  residence numbers get the section's STD code. Court, DIB, DEB, telecom, accounts, traffic and cell rows are left out.
The *police.wb.gov.in district sites (Bankura, Baruipur, Birbhum, Purba Bardhaman ...) are left out: their saved copies have
only the menu and the live sites did not answer (2026-11-11). Works from outside India. One queue item = one page.
Record id dept:police2n_wb:<district>:<station or office>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms.police_s3waas import grid

M = "police2n_wb"

HEADPOST = re.compile(r"^(I/?C|O/?C|IC|OC)\s+", re.I)
RANK = re.compile(r"^((?:L|W)?(?:SI|ASI|S\.I\.|A\.S\.I\.|Insp(?:r)?\.?|Inspector))\s+(?=[A-Z])")
UNIT = re.compile(r"court|\bGRO\b|DIB|\bDIO\b|\bDEB\b|\bDEO\b|DDI|telecom|telephone|accountant|\bHA\b|\bGOA\b|reserve|\bR\.?O\.?\b|"
                  r"\bMTO\b|\bTI\b|traffic|\bT/S\b|\bTCR\b|cell|DCRB|\bDCR\b|DTRS|\bMPB\b|anchor|\bAPI\b|control|D&T|\bHQ\b|Hqrs|"
                  r"Sub-Control", re.I)


def person(cell):
    """'SI Kajal Dutta' -> ('SI', 'Kajal Dutta'); 'Shri' -> (None, None); 'Shri Avisek Chakraborty, WBPS' -> (None, same)."""
    c = clean(cell) or ""
    if re.fullmatch(r"(?:Shri|Smt\.?|SI|ASI|LSI)?", c):
        return None, None
    m = RANK.match(c)
    if m:
        return m.group(1), c[m.end():].strip() or None
    return None, c


def station_area(label):
    a = re.sub(r"\s*\b(?:P\.?S\.?|Police Station)\s*$", "", clean(label) or "", flags=re.I).strip()
    return a


def stations(html, url, district, state="WB"):
    soup = BeautifulSoup(html, "lxml")
    d, recs = slug(district), []
    for t in soup.find_all("table"):
        rows = grid(t)
        if not rows or not any(re.search(r"name of p\.?s", c or "", re.I) for c in rows[0]):
            continue
        for r in rows[1:]:
            if len(r) < 4 or not r[0]:
                continue
            area = station_area(r[0])
            cell = clean(r[1]) or ""
            m = HEADPOST.match(cell)
            post = m.group(1).upper().replace("/", "") if m else "OC"
            rank, name = person(cell[m.end():] if m else cell)
            recs.append(rec(M, f"{d}:{slug(area)}", office_type="police station", area=area, post=post, name=name, rank=rank,
                            phone=phones(r[3]), email=email(r[2]), state=state, district=district, source=url))
    return uniq(recs)


def directory(html, url, district, state="WB"):
    soup = BeautifulSoup(html, "lxml")
    d, recs = slug(district), []
    for t in soup.find_all("table"):
        std, subdivision = None, None
        for r in grid(t):
            if not r or not any(r):
                continue
            if len(set(r)) == 1:
                m = re.search(r"^(.+?)\s+SUB-?DIVISION.*?STD-?\s*(0\d{2,4})", r[0], re.I)
                if m:
                    subdivision, std = m.group(1).title(), m.group(2)
                continue
            if len(r) < 5:
                continue
            label, who = clean(r[0]) or "", clean(r[1]) or ""
            if re.search(r"\d{5}", who) or label.lower() == "designation":
                continue
            rank, name = person(re.sub(r",?\s*\b(?:IPS|WBPS)\b\.?", "", who).strip(" ,"))
            name = re.sub(r"\s+WBPS$", "", name or "").strip() or None

            def land(x):
                x = re.sub(r"-?\s*F\b", "", x or "").strip()
                return "".join(f"{std}-{n}, " if std and len(n) in (6, 7) else f"{n}, " for n in re.findall(r"\d{5,8}", x)).strip(", ")
            ph = phones(", ".join(x for x in (r[4], land(r[2]), land(r[3])) if x))
            common = dict(name=name, rank=rank, phone=ph, state=state, district=district, source=url, police_subdivision=subdivision)
            if UNIT.search(label):
                continue
            m = re.match(r"^SDPO,?\s*(.+)$", label, re.I)
            if m:
                area = m.group(1).strip()
                recs.append(rec(M, f"{d}:sdpo-{slug(area)}", level="subdivision", office_type="subdivision", area=area,
                                post="SDPO", **common))
                continue
            m = re.match(r"^CI\s+(.+)$", label)
            if m:
                area = m.group(1).strip()
                recs.append(rec(M, f"{d}:circle-{slug(area)}", level="circle", office_type="circle", area=area,
                                post="Circle Inspector", **common))
                continue
            m = re.match(r"^(?:I/?C|In ?charge|Incharge)\s+(.+?\b(?:OP|TOP|BH|B/H))$", label, re.I)
            if m:
                area = m.group(1).strip()
                recs.append(rec(M, f"{d}:{slug(area)}", office_type="police post", area=area, post="In-charge", **common))
                continue
            m = re.match(r"^(I/?C|O/?C|IC|OC)\s+(.+)$", label, re.I)
            if m:
                area = station_area(m.group(2))
                recs.append(rec(M, f"{d}:{slug(area)}", office_type="police station", area=area,
                                post=m.group(1).upper().replace("/", ""), **common))
                continue
            if re.match(r"^(?:Superintendent of Police|Addl\.?\s*SP)", label, re.I):
                recs.append(rec(M, f"{d}:{slug(label)}", level="district", office_type="office", area=subdivision or district,
                                post=label, **common))
    return uniq(recs)


def fetch(p, get):
    url, form = p["url"], p.get("form", "stations")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    district = p.get("district") or ""
    recs = directory(r.text, url, district) if form == "directory" else stations(r.text, url, district)
    name = slug(re.sub(r"^https?://", "", url))[:80]
    return recs, [gz(M, name, r.content)], "" if recs else "no rows"
