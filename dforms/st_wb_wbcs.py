"""West Bengal: present posting of every W.B.C.S. (Executive) officer, from par.wb.gov.in (Personnel & Administrative Reforms
Department): https://par.wb.gov.in/writereaddata/WBCSdirectory/wbcs_officers_list_ason-04-11-2026.pdf (iframe of
par.wb.gov.in/wbcsdirectory.php; 118 pages, 694 KB, TCPDF text PDF, "W.B.C.S.(Exe.) OFFICERS OF WEST BENGAL CADRE", about 1,670
officers by the last serial number).
Columns: Sl No | Name/Idcode (name, "(CS1993059 )" ID code, "Dob- 02-11-1966") | Batch | Present Posting (the post, then the
office or department on the next lines) | Posting Address. Cells are centred and wrap; the later pages print the cells closer
together. A row starts with "<serial> <NAME> <batch year>"; the row line itself gives the column starts that its later lines are
sorted by (name side before the batch year, address side after the middle between the posting and the address).
Records: level district when the posting or address names a West Bengal district (BDO, SDO, Deputy Magistrate posts: with
LGD district code), else level state (secretariat Special / Joint / Deputy Secretaries, directorates, boards). Every field of
the row is kept: id_code, dob (public on the source), batch, posting_office, address. No phones or e-mails in the source.
One queue item = the whole file (the reader reads every page; parse on the runner, not on dev-vps-3). Ids:
dept:st_wb_wbcs:<id code, else serial>. Route: par.wb.gov.in answered from Mumbai 2026-11-13 (direct); abroad unchecked.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _field, _state, _st_ape
from dforms.st_wb_par import WB, WB_NAME, SUBDIV, district_in
import provenance

METHOD = "pdf text (pdftotext -layout) row blocks, columns from each row line"
MODULE = "st_wb_wbcs"
PAGE = "https://par.wb.gov.in/wbcsdirectory.php"
PDF = "https://par.wb.gov.in/writereaddata/WBCSdirectory/wbcs_officers_list_ason-04-11-2026.pdf"
ROW = re.compile(r"^(\s*)(\d{1,4})\s+(\S.*?)\s+((?:19|20)\d\d)\b(.*)$")
SKIP = re.compile(r"(?i)W\.B\.C\.S\.|^\s*Sl\s+Name|^\s*No\.\s*$|End Of Report|Developed by IT Cell|Powered by TCPDF|Page \d+/\d+")


def blocks(text):
    out, cur = [], None
    for pg, page in enumerate(text.split("\f"), 1):
        for ln, raw in enumerate(page.split("\n"), 1):
            if not raw.strip() or SKIP.search(raw):
                continue
            m = ROW.match(raw)
            if m and not re.match(r"\s*\(", m.group(3)) and not re.search(r"(?i)\bdob\b", m.group(3)):
                rest_at = m.start(5)
                chunks = [(c.start() + rest_at, c.group(0)) for c in re.finditer(r"\S+(?: \S+)*", raw[rest_at:])]
                cur = {"sl": m.group(2), "name": [m.group(3).strip()], "batch": m.group(4), "post": [], "addr": [],
                       "side": [], "batch_at": m.start(4), "pos": {"page": pg, "line": ln, "line_text": raw}}
                if chunks:
                    cur["post"].append(chunks[0][1])
                    p_end = chunks[0][0] + len(chunks[0][1])
                    if len(chunks) > 1:
                        cur["addr"] += [c for _, c in chunks[1:]]
                        cur["cut"] = (p_end + chunks[1][0]) / 2
                    else:
                        cur["cut"] = p_end + 12
                else:
                    cur["cut"] = m.end(4) + 40
                out.append(cur)
                continue
            if cur is None:
                continue
            for c in re.finditer(r"\S+(?: \S+)*", raw):
                s, t = c.start(), c.group(0)
                if s < cur["batch_at"] - 2 and s + len(t) <= cur["batch_at"] + 2:
                    cur["side"].append(t)
                elif s >= cur["cut"]:
                    cur["addr"].append(t)
                else:
                    cur["post"].append(t)
    return out


def split_side(side):
    """Name continuation, ID code and date of birth from the lines under the name."""
    code = dob = ""
    rest = []
    for t in side:
        m = re.search(r"\(\s*([A-Z]{2}\d{6,})\s*\)", t)
        if m:
            code = m.group(1)
            continue
        m = re.search(r"(?i)dob\s*-?\s*(\d{2}-\d{2}-\d{4})", t)
        if m:
            dob = m.group(1)
            continue
        rest.append(t)
    return rest, code, dob


def place(text):
    """(LGD code, district name) of a posting / address: "DIST- MALDA", a district name, or a sub-division seat."""
    code, name = district_in(text)
    if not code:
        k = re.sub(r"[^a-z]", "", (text or "").lower())
        for sd, c in SUBDIV.items():
            if sd in k:
                return c, WB_NAME[c]
    return code, name


DIST_POST = re.compile(r"(?i)\b(B\.?D\.?O|block development|S\.?D\.?O|sub-?divisional|dy\.?\s*magistrate|deputy magistrate|"
                       r"district magistrate|A\.?D\.?M|additional district|executive magistrate|D\.?L\.?R\.?O|S\.?D\.?L\.?R\.?O|"
                       r"district|collector)")


def parse(text, url):
    recs, seen = [], set()
    for b in blocks(text):
        extra_name, code, dob = split_side(b["side"])
        name = _esw.clean(" ".join(b["name"] + extra_name))
        post = b["post"][0] if b["post"] else ""
        office = _esw.clean(" ".join(b["post"][1:]))
        addr = _esw.clean(" ".join(b["addr"]))
        dcode, dname = place(office + " " + addr) if DIST_POST.search(post + " " + office) else ("", "")
        key = code or f"sl{b['sl']}"
        if key in seen:
            key = f"{key}:{b['sl']}"
        seen.add(key)
        common = dict(state="WB", post=post, post_kind=_st_ape.post_kind(post), name=name, service="WBCS(Exe)",
                      id_code=code or None, dob=dob or None, batch=b["batch"], list_no=b["sl"], posting_office=office or None,
                      address=addr, src_url=url, src_pos=b["pos"], section="W.B.C.S.(Exe.) officers of West Bengal cadre")
        if dcode:
            recs.append(_state.rec(MODULE, key, level="district", district=dname, district_code=dcode, dept="administration",
                                   body=office or f"District administration, {dname}", body_kind="district",
                                   department=office, **common))
        else:
            recs.append(_state.rec(MODULE, key, level="state", body=office, department=office,
                                   body_kind="department" if re.search(r"(?i)dep(t|artment)", office) else "other",
                                   posted_outside=True if re.search(r"(?i)on leave|awaiting|compulsory wait|deputation", post + office)
                                   else None, **common))
    return recs


def iframe_pdf(html, url):
    m = re.search(r'(?i)<iframe[^>]+src\s*=\s*"([^"]+\.pdf)"', html or "")
    return urljoin(url, m.group(1).replace(" ", "%20")) if m else ""


def items(get=None):
    return [{"key": f"{MODULE}:list", "payload": {"reader": MODULE, "url": PDF, "page_url": PAGE, "state": "WB",
                                                  "india_only": True, "route": "direct"}}]


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if (r is None or r.content[:5] != b"%PDF-") and p.get("page_url"):
        pg = get(p["page_url"])
        url = iframe_pdf(pg.text, p["page_url"]) if pg is not None else ""
        r = get(url) if url else None
    if r is None or r.content[:5] != b"%PDF-":
        return [], [], "no pdf"
    text, engine = _field.pdf_text_engine(r.content)
    recs = parse(text, url)
    sha = provenance.at(r, url).get("src_sha256")
    for _, d in recs:
        d["method"] = f"pdf text ({engine}) row blocks"
        if sha:
            d["src_sha256"] = sha
    return recs, [(f"depts/{MODULE}/wbcs_list.pdf", r.content, "application/pdf")], "" if recs else "no rows"
