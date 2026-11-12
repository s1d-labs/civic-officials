"""Jammu and Kashmir: district S3WaaS sites (<district>.nic.in; jkpolice.gov.in does not answer). Works from outside India.
Tables seen in the archive (2026-11-05/06):
- 'Sub Division | Police Station' (Jammu /police-stations/, Budgam /police/, Anantnag /police-info/): cells 'SDPO X (phone)' and
  one or more 'P/S Y (phone)'.
- officers (Udhampur /police/): 'Name of Officers | Place of Posting | Cell/Telephone No.': 'SHO Police Station X', SDPOs.
- label and number (Baramulla /police/, Ganderbal /police-directory/): 'PS X' / '(SHO PS X)' / '(I/C PP X)' / 'SDPO X' | phone.
Kept: police stations and posts (level police_station) and SDPOs (level subdivision). One queue item = one district page.
Record id dept:police_jk:<district>:<station or subdivision>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_jk"
PS_IN_CELL = re.compile(r"(P/S\s+[^()]+?)\s*(?:\(([^)]*)\))?(?=\s*P/S\s|$)")
LABEL = re.compile(r"^\(?\s*(SHO\s+(?:PS|Police Station)|I/C\s+PP|PS|P/S|PP|SDPO|Police Station)\s+(.+?)\s*\)?$", re.I)
NAME = re.compile(r"^(Insp|PSI|SI|ASI|Sh|Smt|Shri|Dy)\b", re.I)
RANK = re.compile(r"^((?:Insp|PSI|SI|ASI|SgCt|HC)\.?)\s+(.+)$")


def _rec(p, kind, place, **f):
    place = clean(place).strip(" ,.")
    if kind == "SDPO":
        return rec(M, f"{slug(p['district'])}:sdpo-{slug(place)}", level="subdivision", area=place, post="SDPO", state="JK",
                   district=p["district"], source=p["url"], **f)
    area = place if re.search(r"\b(PS|P/S|PP|Police (Station|Post))\b", place) else f"{'PP' if kind == 'PP' else 'PS'} {place}"
    return rec(M, f"{slug(p['district'])}:{slug(area)}", area=area, post="SHO" if kind != "PP" else "Officer in charge",
               office_type="police post" if kind == "PP" else "police station", state="JK", district=p["district"],
               source=p["url"], **f)


def _kind(label):
    l = label.upper()
    return "SDPO" if l.startswith("SDPO") else "PP" if "PP" in l.split() else "PS"


def subdiv_table(t, p):
    recs, sub = [], None
    for tr in t.find_all("tr")[1:]:
        c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
        if len(c) < 2:
            continue
        m = re.match(r"SDPO\s+(.+?)\s*(?:\(([^)]*)\))?$", c[0])
        if m:
            recs.append(_rec(p, "SDPO", m.group(1), phone=phones(m.group(2)), subdivision=m.group(1)))
        if c[0]:                    # an empty first cell continues the subdivision of the row above
            sub = m.group(1) if m else (re.sub(r"\s*\(.*$", "", c[0]) or None)
        for n, num in PS_IN_CELL.findall(c[1]):
            recs.append(_rec(p, "PS", n, phone=phones(num), subdivision=sub))
    return recs


def label_table(t, p):
    recs = []
    for tr in t.find_all("tr"):
        c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
        for i, cell in enumerate(c):
            m = LABEL.match(cell)
            if not m:
                continue
            kind = _kind(m.group(1))
            name = c[i - 1] if i > 0 and NAME.match(c[i - 1]) else None
            rank = None
            if name:
                r = RANK.match(name)
                if r:
                    rank, name = r.group(1), r.group(2)
            num = " ".join(re.sub(r"\((?:O|R|F)\)", " ", x) for x in c[i + 1:])
            recs.append(_rec(p, kind, m.group(2), name=name, rank=rank, phone=phones(num)))
            break
    return recs


def parse(html, p):
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("#SkipContent") or soup
    recs = []
    for t in main.find_all("table"):
        first = t.find("tr")
        head = clean(first.get_text(" ", strip=True)).lower() if first else ""
        recs += subdiv_table(t, p) if "police station" in head and "sub" in head and "division" in head else label_table(t, p)
    seen, out = set(), []
    for rid, d in recs:           # the same SDPO repeats on each of its stations' rows
        k = (rid, tuple(sorted(d.items())))
        if k not in seen:
            seen.add(k)
            out.append((rid, d))
    return uniq(out)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"{slug(p['district'])}.html", r.content)]
    recs = parse(r.text, p)
    return recs, files, "" if recs else "no station rows"
