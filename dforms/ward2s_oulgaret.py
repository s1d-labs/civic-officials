"""Oulgaret (Ozhukarai) Municipality, Puducherry (oulmun.in): its field staff (engineers, sanitary inspectors and maistries, bill
collectors, work inspectors, surveyor) from the municipality's own "List of Employees" PDF. Puducherry has no municipal
corporation (LGD: 5 municipalities: Ozhukarai, Pondicherry, Karaikal, Yanam, Mahe); Oulgaret is the largest (42 wards, 3.0
lakh people in 2011). The file /sites/default/files/2026-10/listofemployees.pdf (6 pages, linked from oulmun.in "List of
Employees"; answers from Germany, live 2026-11-11; not in archive.s1d.me) is one table: Sl. No. | Name of the Employee |
Designation | Pay Level, then the sanitary workers. It gives no phones and no wards or sections, so the records are at level
"body" (a body-wide staff list of field posts, no zone or ward mapping). Clerks, drivers, data entry operators, peons and the
sanitary workers are left out (not field officials). The PDF shows no date; its upload folder is 2026-10.
Other sources checked: lad.py.gov.in (Local Administration Department) pages of the municipalities give history and ward names only.
One queue item = the PDF; the reader keeps the PDF (bucket) and parses its pdftotext -layout text, so the parse can run again
from the saved copy. Record ids: dept:ward2s_oulgaret:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2s_oulgaret"
BODY, LGD, STATE, DISTRICT = "Oulgaret Municipality", "253093", "PY", "Puducherry"
URL = "https://oulmun.in/sites/default/files/2026-10/listofemployees.pdf"
ROW = re.compile(r"^\s*(?:\d+)?\s*(\S.*?)\s{2,}(\S.*?)\s{2,}(\d{1,2})\s*$")
FIELD = re.compile(r"(?i)engineer|sanitary\s+(inspector|maistry)|bill\s+collector|work\s+inspector|surveyor|gard[e]?ner\s+maistry|"
                   r"health|revenue|commissioner|manager|town\s+planning")


def items(get=None):
    return [{"key": f"{MODULE}-employees", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": False}}]


def parse(pages, p):
    seen, recs = set(), []
    for page in pages:
        for line in page.splitlines():
            m = ROW.match(line)
            if not m:
                continue
            name, post, pay = (_esw.clean(x) for x in m.groups())
            if not FIELD.search(post) or re.search(r"(?i)designation", post):
                continue
            post = re.sub(r"\s*Gr\.?\s*-?\s*", " Gr.", post).replace("Gardner", "Gardener")
            recs.append(_ward.record(MODULE, f"{_esw.slug(post)}:{_esw.slug(name)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="body", area=BODY, post=post, name=name, pay_level=pay,
                                     source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, [_esw.keep(MODULE, "listofemployees", r.content, "pdf")], "" if recs else "no field staff rows"
