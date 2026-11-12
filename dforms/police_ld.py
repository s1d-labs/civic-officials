"""Lakshadweep Police: lakshadweeppolice.gov.in/police_stations (second table: Sl No | Name of Police Station | SHO Name |
Designation; the first row has an empty station cell) and the citizen charter PDF (downloads/citizen_charter_v2.pdf, 2018:
'OIC Police Station, <island>' office and residence landlines, and the station emails ps.oic<code>-lk@nic.in). Works from
outside India. The two sources are joined by island name (spellings differ: Agatti / Agathi, Androth / Andrott, Kiltan /
Kilthan, Chetlat / Chetlath). The one island the SHO table does not name gets the empty row, with a note. One queue item =
both files; payload url = the page, charter = the PDF. Record id dept:police_ld:<island>."""
import io
import re

from bs4 import BeautifulSoup

import provenance
from dforms._police import clean, email, gz, phones, rec, uniq

METHOD = "pdf text (pypdf) + html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_ld"
URL = "https://lakshadweeppolice.gov.in/police_stations"
CHARTER = "https://www.lakshadweeppolice.gov.in/downloads/citizen_charter_v2.pdf"
ISLANDS = {"Kavaratti": ["Kavaratti"], "Agatti": ["Agatti", "Agathi"], "Androth": ["Androth", "Andrott"], "Amini": ["Amini"],
           "Minicoy": ["Minicoy"], "Kiltan": ["Kiltan", "Kilthan"], "Chetlat": ["Chetlat", "Chetlath"], "Kadmath": ["Kadmath"],
           "Kalpeni": ["Kalpeni"]}


def island(s):
    s = (s or "").lower()
    return next((k for k, al in ISLANDS.items() if any(a.lower() in s for a in al)), None)


def sho_table(html):
    """{island: {name, rank, row_station}}; the row without a station name goes to the one island left over."""
    soup = BeautifulSoup(html, "lxml")
    out, blank = {}, []
    for tn, t in enumerate(soup.find_all("table"), 1):
        head = [clean(c.get_text(" ", strip=True)) for c in t.find_all("tr")[0].find_all(["td", "th"])] if t.find("tr") else []
        if not any("Police Station" in (h or "") for h in head):
            continue
        for rn, tr in enumerate(t.find_all("tr")[1:], 2):
            c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            if len(c) == 4:
                k = island(c[1])
                if k:
                    out[k] = {"name": c[2], "rank": c[3], "row_station": c[1], "pos": {"table": tn, "row": rn}}
            elif len(c) == 3:
                blank.append({"name": c[1], "rank": c[2], "pos": {"table": tn, "row": rn}})
    left = [k for k in ISLANDS if k not in out]
    if len(blank) == 1 and len(left) == 1:
        out[left[0]] = {**blank[0], "note": "station cell empty on the page; the only island the table does not name"}
    return out


def charter(text):
    """{island: {phone, email}} from the citizen charter text."""
    t = re.sub(r"\s+", " ", text or "")
    out = {}
    for k, al in ISLANDS.items():
        alt = "|".join(al)
        d = {}
        m = re.search(rf"OIC (?:Police Station,|PS) ?(?:{alt})\b.{{0,40}}?(0\d{{3,4}}-\d{{6,7}}) ?\(O\)(?: ?(0\d{{3,4}}-\d{{6,7}}) ?\(R\))?", t)
        if m:
            d["phone"], d["residence"] = m.group(1), m.group(2)
        m = re.search(rf"Police Station, (?:{alt}) (\S+\{{@\}}\S+)", t)
        if m:
            d["email"] = email(m.group(1).replace("{@}", "@").replace("{dot}", "."))
        if d:
            out[k] = d
    return out


def pdf_text(content, pages=None):
    """All pages' text; pages (a list) gets each page's text (source trail: which page a number is on)."""
    from pypdf import PdfReader
    ts = [(p.extract_text() or "") for p in PdfReader(io.BytesIO(content)).pages]
    if pages is not None:
        pages.extend(ts)
    return "\n".join(ts)


def page_of(pages, value):
    """1-based page whose text holds value (spaces ignored), else None."""
    v = re.sub(r"\s+", "", value or "")
    return next((i for i, t in enumerate(pages, 1) if v and v in re.sub(r"\s+", "", t)), None)


def fetch(p, get):
    url, curl = p.get("url", URL), p.get("charter", CHARTER)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "police_stations.html", r.content)]
    sho = sho_table(r.text)
    ch, why, pages = {}, "", []
    c = get(curl)
    if c is not None and c.content[:5] == b"%PDF-":
        files.append((f"depts/police/{M}/citizen_charter_v2.pdf", c.content, "application/pdf"))
        try:
            ch = charter(pdf_text(c.content, pages))
        except Exception as e:
            why = f"charter pdf: {type(e).__name__}"
    recs = []
    for k in ISLANDS:
        s, x = sho.get(k, {}), ch.get(k, {})
        if not s and not x:
            continue
        pos = dict(s.get("pos") or {})
        if x:       # phone / email from the citizen charter PDF: its page
            pos["charter_page"] = page_of(pages, x.get("phone") or (x.get("email") or "").split("@")[0])
        src = provenance.at(r, url) if s else provenance.at(c, curl)
        recs.append(rec(M, k.lower(), area=f"PS {k}", post="SHO", name=s.get("name"), rank=s.get("rank"),
                        phone=phones(x.get("phone"), x.get("residence")), email=x.get("email"), state="LD",
                        district="Lakshadweep", source=url, phone_source=curl if x.get("phone") else None,
                        notes=s.get("note"), src_pos={a: b for a, b in pos.items() if b is not None},
                        method=" + ".join(m for m, ok in (("html table", s), ("pdf text (pypdf)", x)) if ok), **src))
    recs = uniq(recs)
    return recs, files, "" if recs else (why or "no rows")
