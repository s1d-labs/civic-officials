"""Meghalaya: MePDCL official contact numbers, two text PDFs on meecl.nic.in (Eastern Zone, 2 pages; Western Zone, 1 page),
linked from the MeECL contact page. India only (times out from Germany; slow from India too). One queue item per PDF.

Layout: circle headings ("Ri Bhoi Distribution Circle"), then rows "Sl No | Designation & Name of Office | Mobile No", e.g.
"5  Assistant Executive Engineer, Nongpoh Urban Distribution Sub-Division  7085648929". No officer names, no e-mail.
Level from the post: Chief Engineer = zone, Superintending Engineer = circle, Executive Engineer = division (also when the office
name says sub-division, as the PDF writes it), Assistant Executive Engineer = sub-division. Helplines and the Director row are
left out. About 52 (Eastern) + 27 (Western) offices. Record id dept:power_mepdcl:<zone>-<post>-<office>.
The e-mail list (Official-Email-IDs.pdf, 2025-07) is not read: its link was not found.
"""
import re

from dforms._power import Out, clean, raw, pdf_pages, slug

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"     # source trail (provenance.py): how this reader reads its sources

# pdftotext puts the mobile last; pypdf's layout mode may put it first, glued to the text ("9245048628Director ...")
ROW = re.compile(r"^\s*(?:\d{1,2}\s+)?(?:(?P<m1>\d{10})\s*(?P<t1>\S.*?)|(?P<t2>.*?)\s+(?P<m2>\d{10}))\s*$")
DES = re.compile(r"^(Chief Engineer|Superintending Engineer|Executive Engineer|Assistant Executive Engineer)\b[^,]*,\s*(.+)$", re.I)
LEVEL = {"chief engineer": "zone", "superintending engineer": "circle", "executive engineer": "division",
         "assistant executive engineer": "subdivision"}


def area_of(office):
    """'Nongpoh Urban Distribution Sub-Division' -> 'Nongpoh Urban'; 'Shillong Distribution Circle, Shillong' -> 'Shillong'."""
    parts = [x.strip() for x in office.split(",")]
    a = parts[0]
    m = re.search(r"(?i)\s*(Distr?i?b?\w*\s+)?(Sub-Division|Division|Circle|Zone)\b\s*-?\s*([IVX]+)?", a)
    if m:
        a = a[:m.start()] + (f" {m.group(3)}" if m.group(3) else "")
        if a.strip().split()[0:1] == ["Revenue"] and len(parts) > 1:
            a = f"{parts[-1]} Revenue{(' ' + m.group(3)) if m.group(3) else ''}"
    a = re.sub(r"\s*\(Distribution\)", "", a, flags=re.I)
    return clean(a) or clean(office)


def parse_pages(pages, zone, source):
    out = Out("power_mepdcl", "ML", source, discom="MePDCL")
    circle, pend = None, ""
    for line in "\n".join(pages).splitlines():
        s = " ".join(line.split())
        if not s or re.match(r"(?i)^(Sl\.?\s*No|Key Helpline|Meghalaya Power)", s):
            continue
        m = ROW.match(line)
        if not m:
            if re.fullmatch(r"\d{1,2}", s):
                continue
            s = re.sub(r"^\d{1,2}\s+", "", s)
            if DES.match(s) or pend:
                pend = f"{pend} {s}".strip()
            elif re.search(r"(?i)\b(Circle|Zone)\b", s) and not DES.match(s):
                circle = s if re.search(r"(?i)circle", s) else circle
            continue
        mob, body = (m.group("m1"), m.group("t1")) if m.group("m1") else (m.group("m2"), m.group("t2"))
        text = f"{pend} {body}".strip()
        pend = ""
        d = DES.match(text)
        if not d:
            continue
        post, office = text.split(",", 1)[0].strip(), d.group(2).strip()
        lvl = LEVEL[d.group(1).lower()]
        if lvl == "zone":
            area = f"{zone} Zone"
        elif lvl == "circle":
            area = area_of(office)
            circle = office
        else:
            area = area_of(office)
        out.add(f"{zone}-{post}-{office}", lvl, area, post=post, phone_=mob,
                parents={"zone": f"{zone} Zone" if lvl != "zone" else None, "circle": circle if lvl in ("division", "subdivision") else None},
                office=office)
    return out.recs


def fetch(p, get):
    url, zone = p["url"], p.get("zone") or "Zone"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_mepdcl", f"{slug(zone)}-zone", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    try:
        pages = pdf_pages(r.content)
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = parse_pages(pages, zone, url)
    return recs, files, "" if recs else "no offices"
