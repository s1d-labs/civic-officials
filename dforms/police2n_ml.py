"""Meghalaya Police. Payload "form":
- "contacts": a district police site's contact page (jowaipolice.gov.in/contacts.html, West Jaintia Hills): one table per unit
  ("Jowai Sadar", "Nartiang Police Station", "Amlarem Sub Division" ...), columns Name | Designation/Rank | Place of Posting |
  Mobile Number | Email ID. Kept: the officer in charge of each police station ("CI cum Officer In-Charge, Amlarem PS"), of each
  out post, beat house and police post ("In-charge Saitsama OP", "In-charge, Ummulong BH"), the SDPOs (level subdivision) and
  the SP and Addl. SPs (level district). Sub-inspectors without a charge, branches (DSB, crime, MPRO, courts, fire, PCR,
  reserve, traffic) are left out.
- "shillong": shillongpolice.gov.in/contacts.html (East Khasi Hills, "UPDATED ON dd.mm.yyyy"): a table 'Place of Posting |
  Office | Mobile No. | Res. | Fax | EPBX | Email Address' ("O/C Sadar PS", "SDPO (Sohra)", "I/C Cantonment BH"; three
  stations share one rowspan cell with one <div> per row) and a table 'Name of PS/BH/OP/PCR | Office Telephone | Mobile No.'.
  No officer names. Office numbers are written without the STD code; 0364 (Shillong) is added, other codes are on the page
  (Sohra 03637, Pynursla 03638 ...) and are added for the stations named there.
- "stations": megpolice.gov.in/know-your-police-station: every police station of the state under its district heading
  ("East Khasi Hills D.E.F"); names only (the links are "#").
- "directory": megpolice.gov.in/telephone-directory: 'Name | Designation | Civil (STD-0364) Office / Residence | EPABX | Mobile':
  kept are the district SPs ("SP, West Garo Hills, Tura": level district, with name and mobile).
Answers only from India (this box gets no connection, 2026-11-11). One queue item = one page. Record id dept:police2n_ml:<district>:<station or office>."""
import re

from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms.police_s3waas import grid
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2n_ml"

UNIT = re.compile(r"\bDSB\b|D\.S\.B|crime branch|infiltration|DCRB|MPRO|court|\bPSI\b|fire|F\s*&\s*ES|reserve|traffic|PCR|"
                  r"control room|\bIBI\b|\bRO\b", re.I)
INCHARGE = re.compile(r"(?:Officer\s+)?In[- ]?charge|\bO/?C\b|\bI/?C\b", re.I)
KIND = [(re.compile(r"\b(?:P\.?S|Police Station)\b", re.I), "police station"),
        (re.compile(r"\b(?:OP|Out ?Post|BH|Beat House|PP|Police Post|BOP|LCS)\b", re.I), "police post")]
SUBDIV = re.compile(r"Sub[- ]Divisional Police Officer|\bSDPO\b", re.I)
SP = re.compile(r"^(?:Addl\.?\s*)?Superintendent of Police|^SP\b|^Addl\.?\s*S\.?P\b", re.I)


def station_of(text):
    """'CI cum Officer In-Charge, Amlarem PS' -> ('Amlarem', 'police station'); 'In-charge Saitsama OP' -> ('Saitsama OP', 'police post')."""
    t = clean(text) or ""
    t = re.sub(r"^.*?(?:Officer\s+)?In[- ]?charge\s*,?\s*", "", t, flags=re.I) if INCHARGE.search(t) else t
    t = re.sub(r"^(?:O/?C|I/?C)\s+", "", t, flags=re.I).strip(" ,.")
    for pat, kind in KIND:
        if pat.search(t):
            if kind == "police station":
                t = re.sub(r"\s*\b(?:P\.?S\.?|Police Station)\s*$", "", t, flags=re.I).strip(" ,.")
            return t, kind
    return None, None


def contacts(html, url, district, state="ML"):
    soup = BeautifulSoup(html, "lxml")
    d, recs = slug(district), []
    for t in soup.find_all("table"):
        rows = grid(t)
        if not rows or not any(re.search(r"place of posting", c or "", re.I) for c in rows[0]):
            continue
        for r in rows[1:]:
            if len(r) < 5:
                provenance.skip_row(r, 'skip: len(r) < 5')
                continue
            name, rank, posting, mobile, mail = (clean(x) for x in r[1:6])
            text = f"{rank} {posting}"
            common = dict(name=name or None, phone=phones(mobile), email=email(mail), state=state, district=district, source=url)
            if SUBDIV.search(text):
                area = re.sub(r"(?i)^.*?(?:Sub[- ]Divisional Police Officer|SDPO)\s*,?\s*", "", rank or "").strip() or \
                    re.sub(r"(?i)\s*Sub[- ]Division\s*$", "", posting or "").strip()
                recs.append(rec(M, f"{d}:sdpo-{slug(area)}", level="subdivision", office_type="subdivision", area=area,
                                post="SDPO", **common))
            elif SP.search(rank or "") and not UNIT.search(rank or ""):
                recs.append(rec(M, f"{d}:{slug(rank)}", level="district", office_type="office", area=district,
                                post=re.sub(r",\s*$", "", rank), **common))
            elif INCHARGE.search(posting or "") and not UNIT.search(posting or ""):
                area, kind = station_of(posting)
                if not area:
                    provenance.skip_row(r, 'skip: not area')
                    continue
                post = "OC" if kind == "police station" else "In-charge"
                recs.append(rec(M, f"{d}:{slug(area)}", office_type=kind, area=area, post=post, designation=posting,
                                rank=rank or None, **common))
    return uniq(recs)


STD = {"sohra": "03637", "mawsynram": "03637", "shella": "03637", "pynursla": "03638", "mawryngkneng": "0364", "mawngap": "0364"}


def shillong(html, url, district="East Khasi Hills", state="ML"):
    soup = BeautifulSoup(html, "lxml")
    d, recs = slug(district), []
    m = re.search(r"UPDATED ON\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", soup.get_text(" "), re.I)
    lu = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None
    mails = {}

    def office(n, place):
        n = re.sub(r"[^\d/ ]", "", n or "").strip(" /")
        if not n:
            return None
        std = STD.get(slug(place).split("-")[0], "0364")
        return ", ".join(f"{std}-{x}" if not x.startswith("0") else x for x in re.split(r"\s*/\s*|\s+", n) if len(x) >= 5)

    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        head = [clean(c.get_text(" ", strip=True)) or "" for c in (trs[1].find_all("td") if len(trs) > 1 else [])]
        if not any("place of posting" in h.lower() for h in head):
            continue
        pending = []
        for tr in trs[2:]:
            tds = tr.find_all("td")
            if not tds:
                provenance.skip_row(tr, 'skip: not tds')
                continue
            cells = [clean(c.get_text(" ", strip=True)) or "" for c in tds]
            if len(tds) == 8:
                lab = tds[1]
                divs = [clean(x.get_text(" ", strip=True)) for x in lab.find_all("div")]
                span = int(lab.get("rowspan") or 1)
                labels = divs if span > 1 and len(divs) == span else [cells[1]]
                label, pending = labels[0], labels[1:]
                vals = cells[2:]
            elif len(tds) == 7 and pending:
                label, pending = pending[0], pending[1:]
                vals = cells[1:]
            else:
                continue
            off, mob, res, fax, epbx, mail = (vals + [""] * 6)[:6]
            mail = email(mail.replace("(Official)", ""))
            sm = re.match(r"^(?:O/C(?:\s+Cum\s+C\.I\.)?|I/C)\s+(.+?)(?:\s+PS)?$", label, re.I)
            if re.match(r"^SDPO\s*\((.+)\)", label, re.I):
                area = re.match(r"^SDPO\s*\((.+)\)", label, re.I).group(1)
                recs.append(rec(M, f"{d}:sdpo-{slug(area)}", level="subdivision", office_type="subdivision", area=area,
                                post="SDPO", phone=phones(mob) or office(off, area), email=mail, epabx=epbx or None,
                                state=state, district=district, source=url, last_updated=lu))
                recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
            elif re.match(r"^SP\s+EKH$", label, re.I):
                recs.append(rec(M, f"{d}:sp", level="district", office_type="office", area=district, post="SP", phone=office(off, ""),
                                email=mail, state=state, district=district, source=url, last_updated=lu))
                recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
            elif sm and not re.search(r"traffic|PCR", label, re.I):
                mails[mob.strip()] = (label, mail, epbx)
    for t in soup.find_all("table"):
        rows = grid(t)
        if not rows or not any(re.search(r"name of ps", c or "", re.I) for c in rows[0]):
            continue
        for r in rows[1:]:
            if len(r) < 4 or not r[1]:
                provenance.skip_row(r, 'skip: len(r) < 4 or not r[1]')
                continue
            label = clean(r[1])
            if re.search(r"PCR", label):
                provenance.skip_row(r, 'skip: re.search(r"PCR", label)')
                continue
            kind = "police post" if re.search(r"\b(BH|OP)\b", label) else "police station"
            area = re.sub(r"\s*\bP\.?\s?S\.?$", "", label).strip()
            lab, mail, epbx = mails.get((r[3] or "").strip(), (None, None, None))
            recs.append(rec(M, f"{d}:{slug(area)}", office_type=kind, area=area, post="OC" if kind == "police station" else "In-charge",
                            phone=", ".join(x for x in (phones(r[3]), office(r[2], area)) if x) or None, email=mail,
                            epabx=epbx or None, state=state, district=district, source=url, last_updated=lu))
    return uniq(recs)


def stations(html, url, state="ML"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        district = None
        for tr in t.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 1 or "table-heading" in (tr.get("class") or []):
                district = re.sub(r"\s*D\.?E\.?F\.?\s*$", "", clean(tr.get_text(" ", strip=True)) or "").strip() or None
                continue
            for td in tds:
                label = clean(td.get_text(" ", strip=True))
                if not label:
                    continue
                area = re.sub(r"\s*\bPS$", "", label).strip()
                recs.append(rec(M, f"{slug(district or 'state')}:{slug(area)}", office_type="police station", area=area,
                                post="OC", state=state, district=district, source=url))
                recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
    return uniq(recs)


def directory(html, url, state="ML"):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        for r in grid(t):
            if len(r) < 7:
                provenance.skip_row(r, 'skip: len(r) < 7')
                continue
            m = re.match(r"^SP,?\s+([A-Za-z \-]+?(?:Hills|Bhoi))\s*,", clean(r[1]) or "", re.I)
            if not m or re.search(r"\(", r[1]):
                provenance.skip_row(r, 'skip: not m or re.search(r"\\(", r[1])')
                continue
            district = m.group(1).title().replace("Ri Bhoi", "Ri-Bhoi")
            ph = phones(re.sub(r"(?i)fax[:\- ]*\d+", "", r[2]), r[6])
            recs.append(rec(M, f"{slug(district)}:sp", level="district", office_type="office", area=district, post="SP",
                            name=clean(r[0]) or None, phone=ph, state=state, district=district, source=url))
    return uniq(recs)


def fetch(p, get):
    url, form = p["url"], p.get("form", "contacts")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if form == "shillong":
        recs = shillong(r.text, url, p.get("district", "East Khasi Hills"))
    elif form == "stations":
        recs = stations(r.text, url)
    elif form == "directory":
        recs = directory(r.text, url)
    else:
        recs = contacts(r.text, url, p.get("district") or "")
    name = slug(re.sub(r"^https?://", "", url))[:80]
    return recs, [gz(M, name, r.content)], "" if recs else "no rows"
