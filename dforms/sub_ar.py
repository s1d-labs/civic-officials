"""Arunachal Pradesh: the Returning Officer of each of the 60 assembly constituencies (2024 elections), from the CEO's PDF
ceoarunachal.nic.in/componenthelper/getcomponentfile/32 ("Returning Officer for Assembly Constituencies in respect of Arunachal
Pradesh", 3 pages, 68 KB). Answers from Germany and India.

The ROs are the Deputy Commissioners, the Additional Deputy Commissioners, Sub-Divisional Officers and Extra Assistant
Commissioners who head the sub-divisions: the one public list of Arunachal's sub-division heads, with names and emails (no phones).
It names officers for the new districts Pakke Kessang (12-Pakke Kessang: SDO Lemmi), Lower Siang (28-Likabali, 36-Nari-Koyu: ADCs)
and Leparada (29-Basar: SDO Basar). The list dates from the 2024 elections: postings may have changed. The PDF shows no date.
Text in layout mode: one row per "N.  N-AC name  designation  name  email"; a wrapped cell continues on the next line in the same
column. dept elections, level ac (as dforms/ero_*), area "N - AC name", post Returning Officer; "subdivision" = the place in an
ADC / SDO / EAC designation ("Additional Deputy Commissioner, Lumla" -> Lumla); district only where the RO is the DC.
Record ids: dept:sub_ar:AR-AC-<no>:ro.
"""
import re

from dforms import _esw
import provenance

METHOD = "pdf text (pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub_ar"
URL = "https://ceoarunachal.nic.in/componenthelper/getcomponentfile/32"
ROW = re.compile(r"^\s*(\d{1,2})\.\s+(\d{1,2})\s*-\s*")
SUBDIV = re.compile(r"(?i)^(addi?t?i?onal deputy commissioner|additonal deputy commissioner|sub divisional officer|"
                    r"extra assistant commissioner)\s*,\s*(.+)$")


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "AR"}}]


def _chunks(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S(?:.*?\S)?(?=\s{2,}|\s*$)", line)]


def rows(pages, where=None):
    """[[ac, designation, name, email]] from the layout text; wrapped cells joined to the cell above them. where: a list; when
    given, it gets provenance.line_pos of each row's first line."""
    out, starts = [], []
    for pno, text in enumerate(pages, 1):
        for lno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            ch = _chunks(line)
            if ROW.match(line):
                ch = ch[1:]                                   # the serial number
                starts = [s for s, _ in ch]
                out.append([c for _, c in ch] + [""] * (4 - len(ch)))
                if where is not None:
                    where.append(provenance.line_pos(pno, lno, line))
            elif out and starts and len(line) - len(line.lstrip()) > 8:
                for s, c in ch:
                    k = min(range(len(starts)), key=lambda i: abs(starts[i] - s))
                    if abs(starts[k] - s) > 6 or k >= 4:
                        continue
                    prev = out[-1][k]
                    glue = "" if prev.endswith(("-", "/")) or c.startswith("/") else " "
                    out[-1][k] = (prev + glue + c).strip()
    return out


def parse(content, url=URL):
    return parse_pages(_esw.pdf_pages(content), url)


def parse_pages(pages, url=URL):
    """Records from the PDF's page texts (layout mode)."""
    recs, seen = [], set()
    where = []
    for (ac, desig, name, mail), pos in zip(rows(pages, where), where):
        m = re.match(r"^(\d{1,2})\s*-\s*(.+)$", ac)
        if not m:
            continue
        no, acname = int(m.group(1)), re.sub(r"\s*\((st|sc)\)\s*$", " (ST)", _esw.clean(m.group(2)), flags=re.I).strip()
        key = f"AR-AC-{no}:ro"
        if key in seen:
            continue
        seen.add(key)
        desig = _esw.clean(desig)
        sub = SUBDIV.match(desig)
        dc = re.match(r"(?i)^deputy commissioner\s*,\s*(.+)$", desig)
        rec = _esw.record(MODULE, key, dept="elections", level="ac", area=f"{no} - {acname}", post="Returning Officer",
                          designation=desig, name=_esw.clean(name), email=_esw.emails(mail.replace("/", " ")),
                          subdivision=sub.group(2).strip() if sub else "", district=dc.group(1).strip() if dc else "",
                          state="AR", office_id=f"AR-AC-{no}", source=url, src_pos=pos)
        if rec[1].get("name") or rec[1].get("email"):
            recs.append(rec)
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "returning_officers", r.content, ext="pdf")]
    recs = parse(r.content, url)
    return recs, files, "" if recs else "no rows"
