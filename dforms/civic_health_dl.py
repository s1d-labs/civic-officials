"""Delhi: Delhi Government allopathic dispensaries (DGD), seed urban PHCs (Seed PUHC) and polyclinics, from the DGHS list
dgehs.delhi.gov.in/sites/default/files/DGHS/generic_multiple_files/list_of_dgds_seed_puhcs_polyclinic.pdf (21 pages, ~250 rows,
no date on the file; the archive saved it 2026-11-10). Columns: district, S.No., assembly constituency no. and name, type
(DGD / Seed PUHC / Polyclinic), "name: full address", attached hospital, date of opening, ownership of the building, contact no.
The list names no doctor: post "Medical Officer" (the officer in charge). One queue item (one GET).
pypdf layout text keeps the columns apart: a row starts with "<district>  <S.No.>  [<AC no>  <AC name>]  <type>  <name: address>";
the next lines continue the address column (and sometimes carry the date, ownership or phone further right).
Records: dept health, level facility, layer health, area = facility name (before the colon), address, facility_type, ac (ECI AC no),
ac_name, district, attached hospital, opened, building, phone. Record ids: dept:civic_health_dl:DL-<district>-<S.No.>.
"""
import re

from provenance import line_pos
from dforms import _esw
import provenance

METHOD = "pdf text (pypdf layout), columns from the header"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_health_dl"
URL = "https://dgehs.delhi.gov.in/sites/default/files/DGHS/generic_multiple_files/list_of_dgds_seed_puhcs_polyclinic.pdf"
TYPE = re.compile(r"(?i)^(dgd|seed\s*puhc|spuhc|poly\s*clinic|aam aadmi polyclinic|puhc|uphc)$")
COLS = (("addr", "Full Address"), ("hospital", "Attached Hospital"), ("opened", "Date of opening"), ("building", "Ownership"),
        ("phone", "Contact"))
CHUNK = re.compile(r"\S+(?: \S+)*")
START = re.compile(r"^\s*([A-Z][A-Za-z]+(?:[ -][A-Za-z]+)*)\s{2,}(\d{1,3})\s{2,}(.*)$")
HEAD = re.compile(r"(?i)list of delhi govt|^\s*district\s+s\.|^\s*no\.\s+no\.|puhc/polyclinic|than dhs|building/pvt")


def chunks(line):
    return [(m.start(), m.group()) for m in CHUNK.finditer(line)]


def columns(line):
    """{column: x} from a page header line, or None."""
    xs = {k: line.find(h) for k, h in COLS}
    return xs if min(xs.values()) >= 0 else None


DATE = re.compile(r"(?i)^(\d{1,2}\s?[./-]\s?\d{1,2}\s?[./-]\s?\d{2,4}|\d{1,2}-[a-z]{3,9}-\d{2,4}|(19|20)\d\d|under process)$")
PHONE = re.compile(r"(?i)^((\+?91[\s-]?)?\(?0?\d[\d\s,/()-]{5,}\d(\s*extn\.?\s*\d*)?|na|n\.a\.?|\d+\s*extn\.?)$")
OWN = re.compile(r"(?i)\b(dhs|private|rented|govt|own|other than|mcd|dda|ndmc)\b")


def col_of(x, t, xs, row):
    """Column of one chunk. The address column is the only one whose x the header gives right (the right-hand columns are
    spaced differently in the header and the rows), so the others are told apart by their content."""
    if x + 6 < xs["hospital"]:
        return "addr"
    if re.fullmatch(r"\d{3,5}", t) and row["phone"] and row["phone"][-1].lower().rstrip(".").endswith("extn"):
        return "phone"                          # "22301945 extn." + "3030" on the next line
    if DATE.match(t):
        return "opened"
    if PHONE.match(t):
        return "phone"
    if OWN.search(t) and len(t) <= 30:
        return "building"
    return "hospital"


def start_row(line, xs):
    m = START.match(line)
    if not m or m.group(1).lower() == "district":
        return None
    cs = chunks(line)[2:]                       # district, S.No.
    row = {"district": m.group(1), "sno": m.group(2), "ac": "", "ac_name": "", "type": "",
           "addr": [], "hospital": [], "opened": [], "building": [], "phone": []}
    i = 0
    if i < len(cs) and re.fullmatch(r"\d{1,2}", cs[i][1]):
        row["ac"] = cs[i][1]
        i += 1
    if i < len(cs) and not TYPE.match(cs[i][1]) and cs[i][0] + 6 < xs["addr"]:
        row["ac_name"] = cs[i][1]
        i += 1
    if i >= len(cs) or not TYPE.match(cs[i][1]):
        return None
    row["type"] = cs[i][1]
    for j, (x, t) in enumerate(cs[i + 1:]):
        row["addr" if j == 0 else col_of(x, t, xs, row)].append(t)
    return row


def finish(row, url):
    text = _esw.clean(" ".join(row["addr"]))
    name, _, addr = text.partition(":")
    name, addr = _esw.clean(name), _esw.clean(addr) or text
    phone = _esw.phones(re.sub(r"(?i)\s*extn\.?\s*", " extn ", " ".join(x for x in row["phone"] if not re.fullmatch(r"(?i)na|n\.a\.?", x))))
    t = row["type"].lower().replace(" ", "")
    ftype = "Polyclinic" if "poly" in t else "Seed PUHC" if "puhc" in t or "uphc" in t else "Dispensary (DGD)"
    key = f"DL-{_esw.slug(row['district'])}-{row['sno']}"
    return _esw.record(MODULE, key, dept="health", level="facility", layer="health", area=name, post="Medical Officer",
                       facility_type=ftype, address=addr, phone=phone, state="DL", district=row["district"],
                       ac=int(row["ac"]) if row["ac"] else None, ac_name=row["ac_name"],
                       hospital=_esw.clean(" ".join(row["hospital"])), opened=_esw.clean(" ".join(row["opened"])),
                       building=_esw.clean(" ".join(row["building"])), office_id=key, source=url, src_pos=row.get("pos"))


def parse(pages, url=URL):
    out, row, xs = {}, None, None
    for pn, page in enumerate(pages, 1):
        for ln_no, line in enumerate(page.splitlines(), 1):
            h = columns(line)
            if h:
                xs = h
                continue
            if not line.strip() or HEAD.search(line) or not xs:
                provenance.skip_line(line, 'skip: not line.strip() or HEAD.search(line) or not xs')
                continue
            r = start_row(line, xs)
            if r:
                if row:
                    rid, d = finish(row, url)
                    out.setdefault(rid, (rid, d))
                row = r
                row["pos"] = line_pos(pn, ln_no, line)
                continue
            if row:
                for x, t in chunks(line):
                    row[col_of(x, t, xs, row)].append(t)
    if row:
        rid, d = finish(row, url)
        out.setdefault(rid, (rid, d))
    return [v for v in out.values() if v[1].get("area")]


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "DL"}}]


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "list-of-dgds-seed-puhcs-polyclinic", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
