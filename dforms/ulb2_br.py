"""Bihar: the Urban Development & Housing Department's contact list of the officers who run every urban body (PDF, 9 pages, made
2026-01-08, posted on the state portal on 2026-01-09). India only (no answer from Germany on 2026-11-11; vpsin got 539,663 bytes).

Sections (heading "Contact No. of ..."), one row per body: Sl., Name of ULB ("<town> Nagar Nigam|Nagar Parishad|Nagar Panchayat"),
Name of Officer, Contact No (10-digit mobiles, sometimes written "77630 04227" or "74840-95916"):
- Municipal Commissioners/Executive Officers (Nagar Nigam): 19 corporations, post "Municipal Commissioner" (role head)
- Executive Officers, Circle Offices, Patna Nagar Nigam: 6 circles ("Azimabad Anchal"), post "Executive Officer, <circle>", body Patna
  (role staff: the officer of a circle, not of the body)
- Additional/Deputy Municipal Commissioners (Nagar Nigam): 19 rows, one or more officers each (role deputy)
- Executive Officers (Nagar Parishad): 89 councils; Executive Officers (Nagar Panchayat): 156 town panchayats (role head). Some rows
  add a second officer "(Urban Administration)".

The text is read with pypdf's plain mode: the PDF is a Word table, and its content stream gives each cell's lines in order (body,
officer names, then their phones). The layout mode puts the lines of tall cells above and below the row line, so it does not show
which row a line belongs to. In a row with several officers the phones follow in the same order as the names. Where the counts do
not agree (2 rows on 2026-01-08: Purnea deputies, Khagaul), no phone goes on a person: the row's phones go in "row_phones".

Every body name ties to an LGD body by dforms/ulb2_br_lgd.json ("<name>|<type>": [lgd_code, LGD district]), made 2026-11-11 by
name similarity and sound key in Bihar with type checked, and 32 spellings set by hand (Ara = Arrah, D.Dalmiya = Dehri
Dalmianagar, Itadhi = Itarhi, Kodha = Korha, Turki-Kudhani = Kurhani, Purvi Kusheshwarasthan = Kusheswar Asthan East ...).
civic-india sql/46 reads the same PDF into civic.official_dir but misses rows whose phone is split or missing and 11 spellings, so
20 Bihar towns had no official. A body name not in the table gives a record without lgd_code (district unknown).
"""
import io
import json
import re
from pathlib import Path

from dforms import _esw, _ulb
import provenance

METHOD = "pdf text (pypdf plain mode)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_br"
STATE = "BR"
URL = "https://betastate.bihar.gov.in/file_2/FileUpload/2026/Jan/09-Jan-2026/19/DyPage/062d1115-4ac3-46f7-96d2-59a58fbc7c96.pdf"
LGD = json.loads((Path(__file__).with_name("ulb2_br_lgd.json")).read_text())
PH = re.compile(r"(?<!\d)(\d[\d\s-]{8,13}\d)(?!\d)")
ROW = re.compile(r"^\s*(\d+)?\s*(.+?\s(?:Nagar\s+)+(?:Nigam|Parishad|Panchayat)|.+?\sAnchal)(?=\s|$)(.*)$", re.I)
HEAD = re.compile(r"Contact No\. of (.+)", re.I)
TYPE = re.compile(r"^(.+?)\s+((?:Nagar\s+)+(?:Nigam|Parishad|Panchayat))$", re.I)


def items(get=None):
    return [{"key": f"{MODULE}-udhd-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def pages_of(content):
    """Plain text of each page (pypdf); a text answer (a saved extract) is split at form feeds."""
    if content[:5] != b"%PDF-":
        return content.decode("utf-8", "replace").split("\f")
    from pypdf import PdfReader
    try:
        return [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(content)).pages]
    except Exception:
        return []


def _phones(s):
    out = []
    for m in PH.finditer(s):
        d = re.sub(r"\D", "", m.group(1))
        if len(d) == 10:
            out.append(d)
    return out, PH.sub(" ", s)


def rows(pages):
    """[{"sec", "no", "body", "names", "phones"}] in the order of the list."""
    sec = cur = None
    out = []
    for pno, pg in enumerate(pages, 1):
        for lno, line in enumerate(pg.split("\n"), 1):
            s = line.strip()
            if not s or re.match(r"(?i)^(sl\.|govt\. of|urban development)", s):
                provenance.skip_line(line, 'skip: not s or re.match(r"(?i)^(sl\\.|govt\\. of|urban development)", s)')
                continue
            h = HEAD.search(s)
            if h:
                if s[:h.start()].strip() and cur:        # the last row of a section can share its line with the next heading
                    cur["phones"] += _phones(s[:h.start()])[0]
                sec, cur = _esw.clean(h.group(1)), None
                continue
            m = ROW.match(s)
            if m and sec:
                cur = {"sec": sec, "no": m.group(1), "body": _esw.clean(m.group(2)), "names": [], "phones": [],
                       "pos": {"page": pno, "line": lno, "line_text": line}}     # the row's first line (source trail)
                out.append(cur)
                rest = m.group(3)
            elif cur is None:
                provenance.skip_line(line, 'skip: cur is None')
                continue
            else:
                rest = s
            ph, txt = _phones(rest)
            txt = _esw.clean(re.sub(r"^\s*\d+\s*", "", txt))
            if re.search(r"[A-Za-z]", txt):
                cur["names"].append(txt)
            cur["phones"] += ph
    return out


def post_of(sec, body):
    s = sec.lower()
    if "circle" in s:
        return "Executive Officer, " + re.sub(r"(?i)\s+anchal$", "", body) + " Circle"
    if "additional" in s or "deputy" in s:
        return "Additional/Deputy Municipal Commissioner"
    if "commissioner" in s:
        return "Municipal Commissioner"
    return "Executive Officer"


def parse(pages, url=URL):
    recs, seen = [], set()
    for r in rows(pages):
        if not r["names"]:
            continue
        circle = "circle" in r["sec"].lower()
        if circle:
            name, btype = "Patna", "Nagar Nigam"
        else:
            m = TYPE.match(r["body"])
            name, btype = _esw.clean(m.group(1)), re.sub(r"(?i)^(nagar\s+)+", "Nagar ", m.group(2))
        lgd, district = LGD.get(f"{name}|{btype}", (None, None))
        post = post_of(r["sec"], r["body"])
        names, phones = r["names"], r["phones"]
        if len(names) == 1:
            given = [", ".join(phones)]
        elif len(names) == len(phones):
            given = phones
        else:
            given = [""] * len(names)
        for i, (person, ph) in enumerate(zip(names, given)):
            p = post
            m = re.search(r"\(([^)]*)\)\s*$", person)
            if m:                                    # "Sri Ravi kumar (Urban Administration)": a second officer of the body
                person, p = _esw.clean(person[:m.start()]), f"{post} ({m.group(1)})"
            extra = {"row_phones": ", ".join(phones)} if phones and not any(given) else {}
            rec = _ulb.record(MODULE, STATE, name, p, seen, name=person, phone=ph, district=district, body_type=btype, source=url,
                              lgd_code=lgd, list_section=r["sec"], list_name=r["body"], src_pos=r.get("pos"), **extra)
            if circle or (m and i):              # a circle officer, or the "(Urban Administration)" officer next to the EO
                rec[1]["role"] = "staff"
            recs.append(rec)
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    pages = pages_of(r.content)
    files = [_esw.keep(MODULE, "udhd-contacts", r.content, "pdf" if r.content[:5] == b"%PDF-" else "txt")]
    recs = parse(pages, p["url"])
    return recs, files, "" if recs else "no rows"
