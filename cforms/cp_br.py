"""Bihar councillor contacts from the nagar nigams' own sites (records "councillor_contact", see cforms/cp_common.py).
One queue item = one body. Patna Municipal Corporation: www.pmc.bihar.gov.in/ward-councillors.aspx, one table
(Sr. No., Name of Ward Councillors, Contact No., Ward No.; "Ward-12"), one member per ward, English names. Record id cp:BR:<SEC slug>:<ward>. The SEC records
(cforms/br.py, Hindi names) have one member per ward too, so record_for = councillor:BR:<SEC slug>:<ward> (payload
"sec_slug"). Rows of a ward that the page repeats keep their order (-2)."""
import gzip
import re

from cforms.cp_common import clean, column, emails, keyed, phones, record, slug, table_rows, useful, ward_no
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

NAME = (r"name of (the )?ward councillors?|councillor|\bname\b|नाम",)
PHONE = (r"contact|mobile|phone|मोबाइल|दूरभाष",)
WARD = (r"^ward|वार्ड",)
TITLE = re.compile(r"^(sri|shri|smt|mr|mrs|ms|md|dr)\.?\s+", re.I)


def members(html, p):
    recs = []
    for head, cells in table_rows(html):
        ni, pi, wi = column(head, *NAME), column(head, *PHONE), column(head, *WARD)
        if None in (ni, pi, wi) or max(ni, pi, wi) >= len(cells):
            provenance.skipped('skip: None in (ni, pi, wi) or max(ni, pi, wi) >= len(cells)')
            continue
        name = TITLE.sub("", clean(cells[ni]) or "")
        ward = ward_no(cells[wi])
        if not name:
            provenance.skipped('skip: not name')
            continue
        recs.append(record("BR", p["body"], ward, name, p["url"], phone=phones(cells[pi]), email=emails(" ".join(cells)),
                           ward_label=cells[wi], lgd_code=p.get("lgd_code"),
                           record_for=f"councillor:BR:{p['sec_slug']}:{ward}" if ward and p.get("sec_slug") else None,
                           pos=cells.pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    key = p.get("sec_slug") or slug(p["body"])           # Hindi body names give an empty slug: the SEC slug names the body
    files = [(f"councillors/BR/cp-{key}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = useful(members(r.text, p))
    return keyed("BR", key, recs), files, "" if recs else "no members with contacts"
