"""Tripura: the 8 district police sites (<d>police.tripura.gov.in), each with a contact table: officer name and rank, "O/C <station>
PS" (officer in charge), phones, email. Column order differs per district (name and post in one cell or in two; one phone cell
or office / residence / mobile). Rows whose post is O/C, OC or I/C of a PS, OP, TOP or police post are the stations (only
these are kept; SP and SDPO rows are not). Emails are written "ocxyz tripurapolice [dot] nic [dot] in"
(the [at] is missing); the reader puts the @ back. Answers only from India. One queue item = one district page.
Record id dept:police_tr:<district>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
from dforms.police_s3waas import grid

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_tr"
OC = re.compile(r"(?:^|[\s,(])(?:I/C\s+)?(O/C|O\.C\.?|OC|I/C)\s+(.+)$", re.I)
OC_FIRST = re.compile(r"(?:^|[\s,(])(O/C|O\.C\.?|OC)\s+(.+)$")
UNIT = re.compile(r"\b(PS|P\.S\.?|Police Station|OP|TOP|Police Post|Out ?Post)\b\.?", re.I)
RANK = re.compile(r"^((?:I/C\s+)?(?:W/|Women\s+)?(?:Inspr|Inpsr|Inspector|Insp|SI|ASI|W/?SI|W/?ASI|Sub[- ]Inspector)\.?"
                  r"(?:\s*\((?:UB|AB)\))?\.?)[\s,.]+", re.I)
MAILDOM = re.compile(r"([\w.\-]+)\s*(?:\[\s*at\s*\]|@)?\s+((?:tripurapolice|nic|gov)(?:\s*\[\s*dot\s*\]\s*\w+)+)", re.I)
LABEL = re.compile(r"\((?:L|O|Office|Resi|PS|Fax|R|M)\)|Landline Number:?|Mobile(?: Phone)?(?: Number| No\.?)?[:.]?|e-?mail:?.*$",
                   re.I)


def mails(text):
    out = []
    for m in MAILDOM.finditer(text or ""):
        e = email(f"{m.group(1)}[at]{m.group(2)}")
        if e and e not in out:
            out.append(e)
    if not out:
        e = email(text)
        if e:
            out.append(e)
    return out


def tel(text, std=None):
    """'222-041 (03825)' -> 03825-222041; '264-365' with STD CODE-03823 -> 03823-264365; the rest as _police.phones()."""
    t = MAILDOM.sub(" , ", text or "")
    t = re.sub(r"\S+@\S+|\S*\[\s*(?:at|dot)\s*\]\S*", " , ", t)
    out = []
    for m in re.finditer(r"(\d{3})\s*-\s*(\d{3})\s*\((0\d{3,4})\)", t):
        out.append(f"{m.group(3)}-{m.group(1)}{m.group(2)}")
    t = re.sub(r"(\d{3})\s*-\s*(\d{3})\s*\((0\d{3,4})\)", " , ", t)
    if std:
        for m in re.finditer(r"(?<![\d-])(\d{3})-(\d{3})(?![\d-])", t):
            out.append(f"{std}-{m.group(1)}{m.group(2)}")
        t = re.sub(r"(?<![\d-])(\d{3})-(\d{3})(?![\d-])", " , ", t)
    t = re.sub(r"\((0\d{3,4})\)\s*(\d)", r"\1-\2", t)
    t = LABEL.sub(" , ", t)
    t = re.sub(r"(?<=\d) (?=\d{3}\b)", "", t)           # '7627 938 118' -> '7627938118'
    for n in (phones(t) or "").split(", "):
        if n and n not in out:
            out.append(n)
    mob = [n for n in out if "-" not in n and len(n) == 10]
    return ", ".join(mob + [n for n in out if n not in mob]) or None


def split_name(s):
    s = clean(s or "").strip(" ,.")
    m = RANK.match(s + " ")
    if m:
        return m.group(1).strip(" ,"), s[m.end():].strip(" ,.") or None
    return None, s or None


def parse(html, district, url):
    soup = BeautifulSoup(html, "lxml")
    recs, std = [], None
    for t in soup.find_all("table"):
        for row in grid(t):
            cells = [clean(c) or "" for c in row]
            joined = " ".join(cells)
            m = re.search(r"STD\s*CODE\s*[-:]?\s*(0\d{3,4})", joined, re.I)
            if m and not re.search(r"\b(O/C|OC|I/C)\b", joined):
                std = m.group(1)
                continue
            idx, hit = None, None
            for i, c in enumerate(cells):
                mm = OC_FIRST.search(c) or OC.search(c)
                if mm and UNIT.search(mm.group(2)) or (mm and mm.group(1).upper().startswith("O") and len(mm.group(2)) < 40
                                                     and not re.search(r"traffic|\bRI\b|cell|unit", mm.group(2), re.I)):
                    idx, hit = i, mm
                    break
            if hit is None:
                continue
            station = re.sub(r"\s*\(.*$", "", hit.group(2)).strip(" ,.")
            station = re.split(r"\s+(?:\d{3}|e-?mail)", station)[0].strip(" ,.")
            before = cells[idx][:hit.start()].strip(" ,(")
            rank, name = split_name(before) if before else (None, None)
            used = {idx}
            if not name and idx > 0 and cells[idx - 1] and not re.fullmatch(r"[\d.]+", cells[idx - 1]):
                rank, name = split_name(cells[idx - 1])
                used.add(idx - 1)
            if idx > 1 and not rank and RANK.match(cells[idx - 1] + " ") and len(cells[idx - 1]) < 15:
                rank = cells[idx - 1].strip(" ,")       # Gomati: rank in its own cell
                used.add(idx - 1)
            rest = " , ".join(c for i, c in enumerate(cells) if i not in used and not re.fullmatch(r"\d{1,3}\.?", c))
            otype = "police post" if re.search(r"\b(OP|TOP|Police Post|Out ?Post)\b", station, re.I) else "police station"
            ms = mails(rest) or mails(cells[idx])
            under = re.search(r"\(Under ([^)]+)\)", joined)
            recs.append(rec(M, f"{slug(district)}:{slug(station)}", area=station, office_type=otype,
                            post="O/C" if hit.group(1).upper().startswith("O") else "I/C", name=name, rank=rank,
                            phone=tel(rest, std), email=ms[0] if ms else None, parent_station=under.group(1) if under else None,
                            state="TR", district=district, source=url))
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("district") or "", url)
    m = re.search(r'<meta[^>]*article:modified_time[^>]*>', r.text)
    m = m and re.search(r'content="(\d{4}-\d{2}-\d{2})', m.group(0))
    for _, d in recs:
        if m:
            d["last_updated"] = m.group(1)
    return recs, [gz(M, f"{slug(p.get('district') or url)}-contact.html", r.content)], "" if recs else "no O/C rows"
