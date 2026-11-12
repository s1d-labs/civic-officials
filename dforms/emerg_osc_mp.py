"""Madhya Pradesh: One Stop Centres (Sakhi OSC, women in distress, linked to Women Helpline 181), one per district, from the
Women and Child Development department's list "वन स्टॉप सेंटर जानकारी" (https://mpwcdmis.gov.in/Downloads/OSC/M.P.%20OSC_list.Pdf,
3 pages, 52 rows (52 districts) on the copy of 2026-11-06). Columns: S.No, District, OSC Address, Concerned CA (the Centre
Administrator, named),
OSC phone no. (STD code without the 0 and the number in two cells), Mail Id. The page has no date.

The table is ruled: full-width horizontal rules separate the rows, vertical rules the columns. A cell's text is printed on several
lines, centred, so line-by-line reading mixes rows; this reader takes each text piece's position from pypdf (via
dforms/_util2_pdfgrid.page_parts(), imported, not changed) and puts it in the band between two full-width rules and the column
between two vertical rules. Column roles come from the header words.
mpwcdmis.gov.in did not answer from Germany (2026-11-11, time-out): india_only. archive.s1d.me holds a copy.
Records: dept women_child, level facility, layer emerg_osc, area "One Stop Centre <district>", post "Centre Administrator",
name, phone as written ("7362 260260"), std_code ("07362"), email, address. Ids: dept:emerg_osc_mp:<district slug>.
"""
import io
import re

from dforms import _emerg

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_osc_mp"
URL = "https://mpwcdmis.gov.in/Downloads/OSC/M.P.%20OSC_list.Pdf"
ROLES = (("sn", r"s\.?\s*no"), ("email", r"mail"), ("phone", r"phone"), ("name", r"\bCA\b|concerned|administrator"),
         ("address", r"address"), ("district", r"district"))


def items(get=None):
    return _emerg.seed(MODULE)


def _uniq(xs, tol=3.0):
    out = []
    for x in sorted(xs):
        if not out or x - out[-1] > tol:
            out.append(x)
    return out


def parts(content):
    """[(texts, hlines, vlines)] of each page (dforms/_util2_pdfgrid.page_parts)."""
    import pypdf
    from dforms._util2_pdfgrid import page_parts
    reader = pypdf.PdfReader(io.BytesIO(content))
    return [page_parts(reader, page) for page in reader.pages]


def bands(pages):
    """Each table row as {role: text} (header row and title left out); pages = parts(content)."""
    rows, roles = [], None
    for texts, hl, vl in pages:
        if not vl or not hl:
            continue
        cols = _uniq([x for x, _, _ in vl])
        left, right = cols[0], cols[-1]
        ys = _uniq([y for x0, x1, y in hl if x0 <= left + 5 and x1 >= right - 5])
        cells = {}
        for x, y, t in texts:
            b = next((i for i in range(len(ys) - 1) if ys[i] <= y < ys[i + 1]), None)
            c = next((i for i in range(len(cols) - 1) if cols[i] <= x + 1 < cols[i + 1]), None)
            if b is not None and c is not None:
                cells.setdefault(b, {}).setdefault(c, []).append((-y, x, t))
        for b in sorted(cells, reverse=True):      # top of the page first
            row = {c: _emerg.clean(" ".join(t for _, _, t in sorted(v))) for c, v in cells[b].items()}
            head = " ".join(row.values())
            if re.search(r"(?i)mail\s*id", head) and re.search(r"(?i)district", head):
                roles, last = {}, None
                for c in range(len(cols) - 1):
                    r = next((r for r, pat in ROLES if re.search(pat, row.get(c, ""), re.I)), None)
                    if r is None and last == "phone":
                        r = "phone"                # the phone header spans the STD and number cells
                    roles[c] = r
                    last = r if r else last
                continue
            if roles is None or not re.fullmatch(r"\d{1,3}", row.get(next((c for c, r in roles.items() if r == "sn"), 0), "")):
                continue
            out = {}
            for c, r in roles.items():
                if r and row.get(c):
                    out[r] = (out[r] + " " + row[c]) if r in out else row[c]
            rows.append(out)
    return rows


def records(content, url, pages=None):
    recs, seen = [], set()
    for r in bands(pages if pages is not None else parts(content)):
        dist = _emerg.clean(r.get("district"))
        if not dist:
            continue
        dist = dist.title() if dist.isupper() or dist.islower() else dist
        key = _emerg.unique(_emerg.slug(dist), seen)
        ph = _emerg.clean(r.get("phone"))
        m = re.fullmatch(r"0?(\d{2,4})\s+(\d{5,8})", ph or "")
        recs.append(_emerg.record(
            MODULE, key, "osc", dept="women_child", level="facility", area=f"One Stop Centre {dist}",
            post="Centre Administrator", name=r.get("name"), phone=ph, std_code=f"0{m.group(1)}" if m else None,
            email=_emerg.emails(r.get("email") or ""), address=r.get("address"), district=dist, state="MP",
            office_id=key, source=url))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_emerg.keep(MODULE, "osc-list", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    recs = records(r.content, url)
    return recs, files, "" if recs else "no rows"
