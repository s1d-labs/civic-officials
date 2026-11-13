"""Maharashtra: MSEDCL (Mahavitaran) officers. Answers from Germany. Two kinds of item (payload "kind"):

- "ee": www.mahadiscom.in/en/executive-engineer-of-msedcl/ = one page of small tables, about 540 rows (Executive Engineer Name,
  Region / Zone / Circle, Division, Contact). Header rows "Executive Engineer Name | Zone | | Contact" start a zone block, whose
  next row names the zone; "Circle | Division" blocks list one EE per division. Kept: the O&M divisions (level division, name +
  mobile, parents zone and circle). Not kept: non-area posts (Admin & Safety, Testing, CGRF, Civil, Enquiry, Training ...).
  last_updated = the page's dateModified. The page carries the list twice (an older and a newer accordion, the same rows):
  a row whose circle, division and phone were read already is skipped, so no "~2" copies.
- "zone": one of the 17 RTI lists (16 zones + corporate office) "<Zone>-Zone-APIO-PIO-AA-English.pdf" from
  /en/list-of-apios-pios-and-aa-under-right-to-information-act-2005/: zone, circle, division and sub-division offices with the
  PIO (EE / Dy.EE) and APIO (JE / AE) names, phones and the sub-division email (sdoNNNN@...). Each zone uses its own column
  order and the office cells wrap over many lines, so these are kept as page text (one "dept_pdf_page" record per page, text in
  layout mode) plus the PDF itself, for a later parse on the box.
Record ids: dept:power_msedcl:division-<circle>-<division>, dept:power_msedcl:pdf-<zone>-p<page>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, tr_pos, clean, phone, raw, pdf_pages, slug
import provenance

METHOD = "html table + pdf text (pypdf layout, one record per page)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.mahadiscom.in/en/executive-engineer-of-msedcl/"
NOT_AREA = re.compile(r"admin|safety|testing|cgrf|civil|enquiry|training|vigilance|store|project|it\b|planning|quality|"
                      r"monitoring|ht\b|billing|account|legal|cell|commercial|construction|infra|solar|mis\b", re.I)


def parse_ee(html, source=URL):
    m = re.search(r'"dateModified":"(\d{4}-\d{2}-\d{2})', html) or re.search(r'modified_time" content="(\d{4}-\d{2}-\d{2})', html)
    out = Out("power_msedcl", "MH", source, discom="MSEDCL", last_updated=m.group(1) if m else None)
    soup = BeautifulSoup(html, "lxml")
    mode, zone, seen = None, None, set()
    for tr in soup.find_all("tr"):
        c = cells(tr)
        tpos = tr_pos(tr)
        if len(c) < 4:
            provenance.skip_row(tr, 'skip: len(c) < 4')
            continue
        if c[0] == "Executive Engineer Name":
            mode = c[1].lower()
            continue
        name, where, div, mob = c[:4]
        if mode == "zone":
            zone = clean(where)
            continue
        if mode != "circle" or not clean(div) or NOT_AREA.search(div):
            provenance.skip_row(tr, 'skip: mode != "circle" or not clean(div) or NOT_AREA.search(div)')
            continue
        key = (slug(where), slug(div), re.sub(r"\D", "", mob or ""))
        if key in seen:                  # the page holds the whole list twice (two accordion copies); one division is also
            provenance.skip_row(tr, 'skip: key in seen')
            continue                     # listed twice in a circle with the same phone ("Latur | Latur | 7875762011")
        seen.add(key)
        name = re.sub(r"\s*\(I/C\)\s*$", " (I/C)", name)
        out.add(f"division-{where}-{div}", "division", div, post="Executive Engineer", name=name, phone_=phone(mob),
                parents={"zone": zone, "circle": where}, src_pos=tpos, method="html table")
    return out.recs


def pdf_records(content, p):
    zone = p.get("zone") or ""
    out = []
    for i, text in enumerate(pdf_pages(content), 1):
        if not text.strip():
            continue
        out.append((f"dept:power_msedcl:pdf-{slug(zone)}-p{i}",
                    {"type": "dept_pdf_page", "dept": "electricity", "discom": "MSEDCL", "state": "MH", "zone": zone, "page": i,
                     "text": text, "source": p["url"], "file": f"depts/power/power_msedcl/{slug(zone)}.pdf",
                     "levels": ["zone", "circle", "division", "subdivision"], "src_pos": {"page": i},
                     "method": "pdf text (pypdf layout, one record per page)"}))
    return out


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if p.get("kind") == "zone":
        files = [raw("power_msedcl", slug(p.get("zone") or "zone"), r.content, "pdf")]
        if r.content[:5] != b"%PDF-":
            return [], files, "not a pdf"
        try:
            recs = pdf_records(r.content, p)
        except Exception as e:
            return [], files, f"pdf: {type(e).__name__}"
        return recs, files, "" if recs else "empty pdf"
    files = [raw("power_msedcl", "executive-engineers", r.content, "html")]
    recs = parse_ee(r.text, url)
    return recs, files, "" if recs else "no divisions"
