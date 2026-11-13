"""West Bengal: posting of every IAS officer of the cadre, and the key officers of the Personnel & Administrative Reforms
Department, from par.wb.gov.in (the department's own site):

1. https://par.wb.gov.in/writereaddata/WBCSdirectory/Posting%20of%20IAS%20Officers%20as%20on%2004112026.pdf (shown in an
   iframe on par.wb.gov.in/iasdirectory.php; 8 pages, 296 KB, Word 2007 text PDF, "POSTING OF IAS OFFICERS AS ON 04.11.2026"):
   "No. | Year | Name | Designation", 282 officers; the designation wraps over several lines and names the main post and
   each additional charge ("Additional Chief Secretary, Forest Department", "Divisional Commissioner, Presidency Division",
   "District Magistrate, Howrah", "... with additional charge of Commissioner, Jalpaiguri Division"). No phones or e-mails.
   The file name changes with each new list: the seed names the iframe page too (iasdirectory.php), and the reader follows the
   iframe when the PDF address no longer answers with a PDF.
2. https://par.wb.gov.in/key_people.php: "Name | Designation | Phone Number | Fax Number | Email-ID" (21 rows, HTML).

Records (level from the main post): state (secretariat and heads of departments; "posted_outside" for Government of India and
other posts outside the state), division (Divisional Commissioner: area = the division, districts from st_div_wb.json),
district (District Magistrate, ADM: district + LGD code). An additional charge of Divisional Commissioner gets a division record
of its own (post "Divisional Commissioner (additional charge)"). Ids: dept:st_wb_par:ias:<no>[:div:<division>],
dept:st_wb_par:key:<row>. Route: the host answered from Mumbai on 2026-11-13 (direct); the archive copies came through the
Indian proxy; abroad unchecked.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _field, _state, _st_ape
import provenance

METHOD = "pdf text (pdftotext -layout) row blocks by column; html table (header names)"
MODULE = "st_wb_par"
IAS_PAGE = "https://par.wb.gov.in/iasdirectory.php"
IAS_PDF = "https://par.wb.gov.in/writereaddata/WBCSdirectory/Posting%20of%20IAS%20Officers%20as%20on%2004112026.pdf"
KEY_PEOPLE = "https://par.wb.gov.in/key_people.php"
WB = {"alipurduar": "664", "bankura": "305", "birbhum": "307", "coochbehar": "308", "kochbihar": "308", "dakshindinajpur": "310",
      "darjeeling": "309", "hooghly": "312", "hugli": "312", "howrah": "313", "jalpaiguri": "314", "jhargram": "703",
      "kalimpong": "702", "kolkata": "315", "malda": "316", "maldah": "316", "murshidabad": "319", "nadia": "320",
      "north24parganas": "303", "paschimbardhaman": "704", "paschimmedinipur": "318", "purbabardhaman": "306",
      "purbamedinipur": "317", "purulia": "321", "south24parganas": "304", "uttardinajpur": "311",
      "north24paraganas": "303", "south24paganas": "304", "south24paraganas": "304"}
# sub-divisions the list names without their district (SDO rows) -> LGD district code
SUBDIV = {"barrackpore": "303", "barrackpur": "303", "bidhannagar": "303", "bongaon": "303", "basirhat": "303",
          "baruipur": "304", "canning": "304", "diamondharbour": "304", "kakdwip": "304", "alipore": "304"}
WB_NAME = {"664": "Alipurduar", "305": "Bankura", "307": "Birbhum", "308": "Cooch Behar", "310": "Dakshin Dinajpur",
           "309": "Darjeeling", "312": "Hooghly", "313": "Howrah", "314": "Jalpaiguri", "703": "Jhargram", "702": "Kalimpong",
           "315": "Kolkata", "316": "Malda", "319": "Murshidabad", "320": "Nadia", "303": "North 24 Parganas",
           "704": "Paschim Bardhaman", "318": "Paschim Medinipur", "306": "Purba Bardhaman", "317": "Purba Medinipur",
           "321": "Purulia", "304": "South 24 Parganas", "311": "Uttar Dinajpur"}
DIVS = {"presidency": "Presidency", "bardhaman": "Burdwan", "burdwan": "Burdwan", "medinipur": "Medinipur",
        "jalpaiguri": "Jalpaiguri", "malda": "Malda"}
ROW = re.compile(r"^\s*(\d{1,3})\.\s+(\d{4})\b")
OUTSIDE = re.compile(r"(?i)government of india|govt\.? of india|ministry of|\bGoI\b|central deputation|study leave|"
                     r"leave\b|awaiting posting|compulsory wait")
ADDL = re.compile(r"(?i)\s*\b(?:with|and)\s+(?:the\s+)?additional\s+charge\s+of\b")


def district_in(text):
    """(LGD code, name) of the first West Bengal district a post text names."""
    t = re.sub(r"[^a-z0-9]", "", (text or "").lower())
    best = None
    for k, code in WB.items():
        i = t.find(k)
        if i >= 0 and (best is None or i < best[0] or (i == best[0] and len(k) > best[2])):
            best = (i, code, len(k))
    return (best[1], WB_NAME[best[1]]) if best else ("", "")


DIST_POSTS = [("district_magistrate", r"(?i)^(?:the\s+)?(?:district magistrate|D\.?\s?M\.?(?=[\s,-]))"),
              ("adm", r"(?i)^(?:ADM\b|additional district magistrate)"),
              ("sdo", r"(?i)^(?:SDO\b|sub-?divisional officer)"),
              ("assistant_magistrate", r"(?i)^assistant magistrate")]


def district_kind(post):
    """Rank key of a district post ("DM-cum-DEO, Nadia", "D.M. cum D.E.O., Alipurduar", "ADM(LR), Nadia", "SDO, Kalna, ..."),
    or "" when the post is not a district one."""
    for k, rx in DIST_POSTS:
        if re.search(rx, _esw.clean(post)):
            return k
    return ""


def subdivision_of(post):
    m = re.match(r"(?i)^(?:SDO|sub-?divisional officer)\s*,\s*([^,]+)", _esw.clean(post))
    return m.group(1).strip() if m else ""


def divisions_in(text):
    """Division names a text gives as "Divisional Commissioner, X Division" / "Commissioner, X Division" / "Divisional
    Commissioner, X"."""
    out = []
    for m in re.finditer(r"(?i)\b(?:divisional\s+)?commissioner\s*,\s*([A-Za-z]+)(?:\s+division)?", text or ""):
        if not re.search(r"(?i)divisional|division", m.group(0)):
            provenance.skip_line(m, 'skip: not re.search(r"(?i)divisional|division", m.group(0))')
            continue
        d = DIVS.get(m.group(1).lower())
        if d and d not in out:
            out.append(d)
    return out


def blocks(text):
    """[(no, year, name, designation, src_pos)] of the layout text: a row starts with "N. YYYY"; its later lines add text to
    the name or the designation by the column the text starts in (the page's header line gives the columns)."""
    out, cur, name_col, des_col = [], None, 14, 40
    for pg, page in enumerate(text.split("\f"), 1):
        for ln, raw in enumerate(page.split("\n"), 1):
            if not raw.strip():
                provenance.skipped("empty")
                continue
            h = re.search(r"\bName\b.*\bDesignation\b", raw)
            if h and re.match(r"^\s*No\.", raw):
                name_col, des_col = raw.index("Name"), raw.index("Designation")
                continue
            if re.fullmatch(r"\s*\d{1,3}\s*", raw) and len(raw) - len(raw.lstrip()) > 20:   # page number
                provenance.skip_line(raw, 'skip: re.fullmatch(r"\\s*\\d{1,3}\\s*", raw) and len(raw) - len(raw.lstrip()...')
                continue
            if re.search(r"(?i)posting of ias officers", raw):
                provenance.skip_line(raw, 'skip: re.search(r"(?i)posting of ias officers", raw)')
                continue
            m = ROW.match(raw)
            if m:
                cur = {"no": m.group(1), "year": m.group(2), "name": [], "des": [],
                       "pos": {"page": pg, "line": ln, "line_text": raw}}
                out.append(cur)
                rest_at = m.end()
            elif cur is None:
                provenance.skip_line(raw, 'skip: cur is None')
                continue
            else:
                rest_at = 0
            for c in re.finditer(r"\S+(?: \S+)*", raw[rest_at:]):
                s, txt = c.start() + rest_at, c.group(0)
                if s >= des_col - 3:
                    cur["des"].append(txt)
                elif s >= name_col - 3:
                    cur["name"].append(txt)
                elif re.fullmatch(r"\d{1,2}", txt) and len(cur["year"]) == 4:
                    cur["year_tail"] = txt     # "224.   2020" / "2   Sh. ...": a stray digit of the year cell (kept)
    return [(b["no"], b["year"], _esw.clean(" ".join(b["name"])), _esw.clean(" ".join(b["des"])), b["pos"], b.get("year_tail"))
            for b in out]


def parse_ias(text, url):
    recs = []
    for no, year, name, des, pos, tail in blocks(text):
        main = ADDL.split(des)[0].strip(" ,.")
        addl = des[len(main):].strip(" ,.") if len(des) > len(main) else ""
        post = main
        dept = ""
        m = re.search(r"(?i),\s*((?:department|dept\.?)\s+of\s+[^,]+|[^,]*?(?:department|dept\.?))", main)
        if m:
            dept = m.group(1).strip()
        common = dict(state="WB", name=name, service="IAS", batch=year, batch_tail=tail, list_no=no, designation=des,
                      additional_charge=addl or None, src_url=url, src_pos=pos, section="Posting of IAS Officers")
        divs = divisions_in(main)
        dk = district_kind(main)
        code, dname = district_in(main) if dk else ("", "")
        if dk == "sdo" and not code:
            code = SUBDIV.get(re.sub(r"[^a-z]", "", subdivision_of(main).lower()), "")
            dname = WB_NAME.get(code, "")
        if divs and re.search(r"(?i)commissioner", main):
            recs.append(_state.rec(MODULE, f"ias:{no}", level="division", division=divs[0], post=post,
                                   post_kind="divisional_commissioner" if not re.search(r"(?i)assistant commissioner", main)
                                   else "other", body=f"Office of the Divisional Commissioner, {divs[0]} Division",
                                   body_kind="division", department="Department of Personnel & Administrative Reforms",
                                   dept="administration", **common))
        elif code:
            recs.append(_state.rec(MODULE, f"ias:{no}", level="district", district=dname, district_code=code, post=post,
                                   post_kind=dk, subdivision=subdivision_of(main) if dk == "sdo" else None,
                                   body=f"District administration, {dname}", body_kind="district", department="",
                                   dept="administration", **common))
        else:
            recs.append(_state.rec(MODULE, f"ias:{no}", level="state", post=post, post_kind=_st_ape.post_kind(post),
                                   body=dept or main, body_kind="department" if dept else "other", department=dept,
                                   posted_outside=True if OUTSIDE.search(main) else None, **common))
        for d in divisions_in(addl):
            if d in divs:
                continue
            recs.append(_state.rec(MODULE, f"ias:{no}:div:{d.lower()}", level="division", division=d,
                                   post="Divisional Commissioner (additional charge)", post_kind="divisional_commissioner",
                                   body=f"Office of the Divisional Commissioner, {d} Division", body_kind="division",
                                   department="Department of Personnel & Administrative Reforms", dept="administration",
                                   charge="additional", **common))
    return recs


def parse_key(html, url):
    recs = []
    for ti, t in enumerate(_st_ape.tables(html), 1):
        for d, pos, cells in _st_ape.header_rows(t):
            post, name = d.get("post", ""), d.get("name", "")
            if not (post or name):
                provenance.skip_row(d, 'skip: not (post or name)')
                continue
            recs.append(_state.rec(MODULE, f"key:{ti}:{pos['row']}", state="WB", level="state", post=post,
                                   post_kind=_st_ape.post_kind(post), name=name,
                                   body="Personnel & Administrative Reforms Department", body_kind="secretariat",
                                   department="Personnel & Administrative Reforms Department", dept="administration",
                                   phone=_esw.phones(d.get("phone")), fax=_esw.phones(d.get("fax")) or None,
                                   email=_esw.emails(d.get("email") or ""), src_url=url, src_pos=pos, cells=cells,
                                   section="Key People"))
    return recs


def iframe_pdf(html, url):
    m = re.search(r'(?i)<iframe[^>]+src\s*=\s*"([^"]+\.pdf)"', html or "")
    return urljoin(url, m.group(1).replace(" ", "%20")) if m else ""


def items(get=None):
    return [{"key": f"{MODULE}:ias", "payload": {"reader": MODULE, "kind": "ias", "url": IAS_PDF, "page_url": IAS_PAGE,
                                                 "state": "WB", "india_only": True, "route": "direct"}},
            {"key": f"{MODULE}:key", "payload": {"reader": MODULE, "kind": "key", "url": KEY_PEOPLE, "state": "WB",
                                                 "india_only": True, "route": "direct"}}]


def fetch(p, get):
    if p.get("kind") == "key":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        recs = parse_key(r.text, p["url"])
        return recs, [_esw.keep(MODULE, "key_people", r.content)], "" if recs else "no rows"
    url = p["url"]
    r = get(url)
    if (r is None or r.content[:5] != b"%PDF-") and p.get("page_url"):
        pg = get(p["page_url"])
        url = iframe_pdf(pg.text, p["page_url"]) if pg is not None else ""
        r = get(url) if url else None
    if r is None or r.content[:5] != b"%PDF-":
        return [], [], "no pdf"
    text, engine = _field.pdf_text_engine(r.content)
    recs = parse_ias(text, url)
    for _, d in recs:
        d["method"] = f"pdf text ({engine}) row blocks by column"
        d.update({k: v for k, v in provenance.at(r, url).items() if k == "src_sha256"})
    return recs, [(f"depts/{MODULE}/ias_posting.pdf", r.content, "application/pdf")], "" if recs else "no rows"
