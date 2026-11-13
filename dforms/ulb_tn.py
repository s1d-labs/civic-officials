"""Tamil Nadu: the two statewide lists of town body heads.

1. Directorate of Town Panchayats (DTP), townpanchayat.in/town_panchayat_officials_contact_numbers.php (www. redirects to the bare
   host). One HTML table (490 bodies on 2026-11-11): S.No, TP Name, Office Number, Official EO Contact No. District heading rows
   ("Name of the District : Kancheepuram") stand between the bodies; the reader carries that district to each body. No names:
   the EO post has the official mobile, the office has its landline. One record per body: post "Executive Officer", phone =
   EO mobile, office_phone = the office landline. "-" means no number.
2. Commissionerate of Municipal Administration (CMA), tnurbantree.tn.gov.in/municipal-e-mail-ids/: one HTML table (165 rows, 158 bodies on 2026-11-11):
   Sl.No, Name of the District, Name of the ULB, Grade, Email Id; region heading rows ("Name of the Region: Chengalpattu"). No names,
   no phones: one record per body, post "Commissioner", the official email, grade.
Both pages show no date ("Last Updated" without a value on the CMA page). Both answer from outside India (checked from Germany).
Names follow the department's spelling (Madhuranthagam, Thiruthani, Podhaturpet); the district helps sql/86 tie them to civic.ulb.
"""
import re

from dforms import _esw, _ulb
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb_tn"
TP_URL = "https://townpanchayat.in/town_panchayat_officials_contact_numbers.php"
CMA_URL = "https://www.tnurbantree.tn.gov.in/municipal-e-mail-ids/"


def items(get=None):
    return [{"key": "ulb_tn-tp", "payload": {"reader": MODULE, "kind": "tp", "url": TP_URL, "state": "TN", "india_only": False}},
            {"key": "ulb_tn-cma", "payload": {"reader": MODULE, "kind": "cma", "url": CMA_URL, "state": "TN", "india_only": False}}]


def blank(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[-–.\s]*", s) else s


def parse_tp(html, url=TP_URL):
    recs, seen, district = [], set(), None
    for t in _esw.soup(html).find_all("table"):
        tp = []
        for row, pos in zip(_esw.grid(t, pos=tp), tp):
            m = re.match(r"(?i)name of the district\s*:?\s*(.+)", row[0])
            if m:
                district = _esw.clean(m.group(1))
                continue
            if len(row) < 4 or not re.fullmatch(r"\d+", row[0].strip()):
                provenance.skip_row(row, 'skip: len(row) < 4 or not re.fullmatch(r"\\d+", row[0].strip())')
                continue
            body, office, eo = blank(row[1]), blank(row[2]), blank(row[3])
            if not body or not (office or eo):
                provenance.skip_row(row, 'skip: not body or not (office or eo)')
                continue
            recs.append(_ulb.record(MODULE, "TN", body, "Executive Officer", seen, phone=eo, district=district,
                                    body_type="Town Panchayat", source=url, office_phone=_esw.phones(office) if office else None,
                                    src_pos=pos))
    return recs


def parse_cma(html, url=CMA_URL):
    recs, seen, region = [], set(), None
    for t in _esw.soup(html).find_all("table"):
        tp = []
        for row, pos in zip(_esw.grid(t, pos=tp), tp):
            m = re.match(r"(?i)name of the region\s*:?\s*(.+)", row[0])
            if m:
                region = _esw.clean(m.group(1))
                continue
            if len(row) < 5 or not re.fullmatch(r"\d+", row[0].strip()):
                provenance.skip_row(row, 'skip: len(row) < 5 or not re.fullmatch(r"\\d+", row[0].strip())')
                continue
            district, body, grade, email = blank(row[1]), blank(row[2]), blank(row[3]), _esw.emails(row[4])
            if not body or not email:
                provenance.skip_row(row, 'skip: not body or not email')
                continue
            recs.append(_ulb.record(MODULE, "TN", body, "Commissioner", seen, email=email, district=district or None,
                                    body_type="Municipality", source=url, grade=grade or None, region=region, src_pos=pos))
    return recs


def parse(html, kind="tp", url=None):
    return parse_tp(html, url or TP_URL) if kind == "tp" else parse_cma(html, url or CMA_URL)


def fetch(p, get):
    kind = p.get("kind", "tp")
    url = p.get("url") or (TP_URL if kind == "tp" else CMA_URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, kind, r.content)]
    recs = parse(r.text, kind, url)
    return recs, files, "" if recs else "no rows"
