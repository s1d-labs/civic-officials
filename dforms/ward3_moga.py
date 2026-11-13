"""Municipal Corporation Moga (mcmoga.punjab.gov.in, Punjab e-Nigam MC site): its employees by branch, from the PDF "Employee List"
(menu link on the home page; e-Nigam Azure store; "List of Employee MC Moga UPDATED", 2026-07-13, 4 pages; live sample
2026-11-13, answers from abroad).
Table: Sr.No | Name of Branch | (sr in branch) Name of Employee | Designation | Mobile No. The branch cell is merged over the
branch's rows; a branch starts where the serial in the branch goes back to 1 (or down). Branch text above a branch's first row
goes to that branch when the branch before it already has its own number line, else to the branch before.
Columns are cut at the heading's column starts of each page (pypdf layout text). Sanitation: chief sanitary inspectors, sanitary
inspectors, supervisors; Civil (B&R) and O&M: JEs; Fire, House Tax, Licence ... The list names no wards or zones: every record
is at level "body" (section = the branch). Head-count rows ("8 Fireman | Contract Basis") are left out. Officers who sit in several branches appear once per branch.
Record ids: dept:ward3_moga:<branch slug>:<post slug>:<mobile or name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_northb as h

METHOD = "pdf text (pypdf layout), columns cut at the heading"     # source trail (provenance.py)

MODULE = "ward3_moga"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Moga", "248347", "PB", "Moga"
HOME = "https://mcmoga.punjab.gov.in/Home"
PDF = ("https://enigambackuprestore.blob.core.windows.net/securefilestructure/MC/Moga/MCSubMenu/pdf/"
       "linkpdf_7_13_2026_3_767.List%20of%20Employee%20MC%20Moga%20UPDATED.pdf")
LINK = re.compile(r"(?i)employee\s*list")
HEAD = re.compile(r"(?i)name\s+of\s+employee")


def items(get=None):
    return [{"key": f"{MODULE}-employees", "payload": {"reader": MODULE, "url": HOME, "pdf": PDF, "state": STATE}}]


def cut(line, xs):
    """Cells of a line cut at the column starts xs (a word that crosses a start stays left)."""
    out, prev = [], 0
    for x in xs[1:] + [None]:
        if x is None:
            out.append(line[prev:])
            break
        i = min(x, len(line))
        while 0 < i < len(line) and not line[i - 1].isspace() and not line[i].isspace():
            i -= 1
        out.append(line[prev:i])
        prev = i
    return [_esw.clean(c) for c in out]


def table(pages):
    """[group dict(label, branch, rows=[dict(sr, name, post, phone, page, line, line_text)])]."""
    groups, cur, prev_sr, pending = [], None, None, []
    for pn, pg in enumerate(pages, 1):
        xs = None
        for ln, raw in enumerate(h.lines_of(pg), 1):
            if not raw.strip():
                continue
            hm = HEAD.search(raw)
            if hm:
                d = re.search(r"(?i)designation", raw)
                mo = re.search(r"(?i)mobile", raw)
                if d and mo:
                    xs = [0, hm.start() - 6, hm.start(), d.start(), mo.start() - 2]
                continue
            if xs is None:
                continue
            branch_col, sr_col, name, post, phone = cut(raw, xs)
            outer = re.match(r"^(\d{1,2})\s*(.*)$", branch_col)
            label, btext = (outer.group(1), outer.group(2)) if outer else (None, branch_col)
            if re.match(r"\d", name or ""):         # "8 Fireman | Contract Basis": a head count of contract staff, no person
                continue
            if re.fullmatch(r"\d{1,3}", sr_col or "") and name:
                sr = int(sr_col)
                if cur is None or prev_sr is None or sr == 1 or sr < prev_sr:
                    take_back = cur is not None and cur["label"] is None
                    cur = {"label": None, "branch": [], "rows": []}
                    groups.append(cur)
                    if pending:
                        if take_back and len(groups) > 1:
                            groups[-2]["branch"] += pending
                        else:
                            cur["branch"] += pending
                    pending = []
                prev_sr = sr
                cur["rows"].append({"sr": sr, "name": name, "post": post, "phone": phone, "page": pn, "line": ln,
                                    "line_text": raw})
                if label:
                    cur["label"] = label
                if btext:
                    cur["branch"].append(btext)
                continue
            # a line without a row: branch text, a wrapped designation, or the number of the branch
            if cur is not None and post and not name and not btext and not label:
                cur["rows"][-1]["post"] += " " + post
                continue
            if label and cur is not None and cur["label"] is None:
                cur["label"] = label
                if btext:
                    cur["branch"].append(btext)
                continue
            if btext:
                if cur is not None and cur["label"] is None:
                    cur["branch"].append(btext)
                else:
                    pending.append(btext)
    if pending and groups:
        groups[-1]["branch"] += pending
    for g in groups:
        g["branch"] = _esw.clean(" ".join(g["branch"]))
    return groups


def parse(pages, p):
    seen, recs = set(), []
    for g in table(pages):
        for r in g["rows"]:
            post = re.sub(r"(?i)sanitay", "Sanitary", r["post"])
            if not post:
                provenance.skip_row(r, 'skip: not post')
                continue
            ph = r["phone"] if re.search(r"\d{5}", r["phone"]) else ""
            key = f"{_esw.slug(g['branch'])[:40] or 'branch'}:{_esw.slug(post)[:40]}:{re.sub(r'[^0-9]', '', ph) or _esw.slug(r['name'])}"
            recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="body",
                                     area=BODY, post=post, name=r["name"], phone=ph, section=g["branch"] or None,
                                     section_no=g["label"], source=p.get("pdf") or PDF,
                                     src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"], row=r["sr"])))
    return recs


def fetch(p, get):
    url = p.get("pdf") or PDF
    home = get(p["url"]) if p.get("url") else None
    if home is not None:
        for a in _esw.soup(home.text).find_all("a", href=True):
            if LINK.search(a.get_text(" ")) and a["href"].lower().endswith(".pdf"):
                url = a["href"].replace(" ", "%20")
                break
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "employees", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, dict(p, pdf=url))
    return _ward.tag(recs, r, url, METHOD), files, "" if recs else "no rows"
