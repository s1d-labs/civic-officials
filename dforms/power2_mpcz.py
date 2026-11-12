"""Madhya Pradesh: MP Madhya Kshetra Vidyut Vitaran Co. (MPMKVVCL, MPCZ, Bhopal) officer lists, portal.mpcz.in "Contact us".

One PDF per O&M circle, city circle, region office and the corporate office (portal.mpcz.in/upload_files/pdf/contact_us/<file>.pdf,
linked from portal.mpcz.in/web/contact-us/): 23 files, one queue item each. Each lists every officer of the circle: GM (circle),
DGM (division), Manager (= AE, sub-division / zone), Asst. Manager (= JE, distribution centre "D/c" = section level) with name,
designation, CUG mobile and e-mail; most files also give the division, sub-division and DC in merged cells. About 1,300 officers.
Each PDF has its own layout; dforms/_util2_pdfgrid.py reads them all (columns from the header words, merged cells from the grid
lines). The files carry their own date ("Date of Updation 15.10.2026", "As on 21 Oct'2026"), kept as last_updated.
MPCZ renamed posts in 2023 (SE -> GM, EE -> DGM, AE -> Manager, JE -> Assistant Manager); the PDFs mix old and new names.
Records "dept:power2_mpcz:<file>:<office>:<post>:<name>", level from the office name (D/c, zone -> section; S/D -> subdivision;
Dn -> division; circle; region -> zone), else from the post. The archive holds copies of all 23 files (2026-11-10).
"""
import re

from dforms import _power, _util2
from dforms._util2_pdfgrid import rows

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_mpcz"
BASE = "https://portal.mpcz.in/upload_files/pdf/contact_us/"
FILES = {  # file -> (circle or office name, district for the circle, kind)
    "corporateOfic_bpl": ("Corporate Office Bhopal", "Bhopal", "state"),
    "bhopalRegion_bpl": ("Bhopal Region", "Bhopal", "zone"),
    "gwlRegion_bpl": ("Gwalior Region", "Gwalior", "zone"),
    "cityCircleBpl_bpl": ("City Circle Bhopal", "Bhopal", "circle"),
    "cityCircleGwl_bpl": ("City Circle Gwalior", "Gwalior", "circle"),
    "oNmBpl_bpl": ("O&M Circle Bhopal", "Bhopal", "circle"),
    "oNmGwl_bpl": ("O&M Circle Gwalior", "Gwalior", "circle"),
    "oNmAshoknagar_bpl": ("O&M Circle Ashoknagar", "Ashoknagar", "circle"),
    "oNmBhind_bpl": ("O&M Circle Bhind", "Bhind", "circle"),
    "oNmDatia_bpl": ("O&M Circle Datia", "Datia", "circle"),
    "oNmGuna_bpl": ("O&M Circle Guna", "Guna", "circle"),
    "oNmHarda": ("O&M Circle Harda", "Harda", "circle"),
    "oNmMorena_bpl": ("O&M Circle Morena", "Morena", "circle"),
    "oNmNarmadapuram_bpl": ("O&M Circle Narmadapuram", "Narmadapuram", "circle"),
    "oNmRaisen_bpl": ("O&M Circle Raisen", "Raisen", "circle"),
    "oNmRajgarh_bpl": ("O&M Circle Rajgarh", "Rajgarh", "circle"),
    "oNmSehore_bpl": ("O&M Circle Sehore", "Sehore", "circle"),
    "oNmSheopur_bpl": ("O&M Circle Sheopur", "Sheopur", "circle"),
    "oNmShivpuri_bpl": ("O&M Circle Shivpuri", "Shivpuri", "circle"),
    "oNmVidisha_bpl": ("O&M Circle Vidisha", "Vidisha", "circle"),
    "betul": ("O&M Circle Betul", "Betul", "circle"),
    "area_store_guna": ("Area Store Guna", "Guna", "circle"),
    "area_store_gwalior_region": ("Area Store Gwalior Region", "Gwalior", "circle"),
}


def items(get=None):
    return [{"key": f"{MODULE}:{f}", "payload": {"reader": MODULE, "file": f, "url": BASE + f + ".pdf", "state": "MP",
                                                  "india_only": True}} for f in FILES]


def records(content, file, url):
    circle, district, kind = FILES.get(file, (file, None, "circle"))
    try:
        head = "\n".join(_power.pdf_pages(content)[:1])
    except Exception:
        head = ""
    out = _power.Out(MODULE, "MP", url, discom="MPMKVVCL", last_updated=_util2.updated(head[:1500]))
    for r in rows(content):
        post, name = _power.clean(r.get("post")), _util2.person(r.get("name"))
        if not (post or name):
            continue
        labels = [x for x in r["offices"] if not _power.EMAIL.search(x)]
        mails = [x for x in r["offices"] if _power.EMAIL.search(x)]
        heading = r.get("heading") if r.get("heading") and not re.search(r"complaint|toll\s*free|@|^\W*$|name\s*of|designation",
                                                                         r["heading"], re.I) else None
        office = labels[-1] if labels else heading
        level = (_util2.office_level(office) if office else None) or _util2.post_level(post) or kind
        if kind in ("state", "zone") and level in ("section", "subdivision", "division") and not _util2.office_level(office or ""):
            level = kind                       # head-office staff (Manager HR, DGM IT) are not field offices
        parents = {"circle": circle} if kind == "circle" else {"zone": circle} if kind == "zone" else {}
        for lab in labels[:-1] + ([heading] if heading and heading != office else []):
            lv = _util2.office_level(lab)
            if lv in ("division", "subdivision") and lv != level:
                parents.setdefault(lv, _util2.area_name(lab))
        area = _util2.area_name(office) if office else circle
        out.add(f"{file}:{area}:{post}:{name}", level, area, post=post, name=name,
                phone_=_power.phone(*(re.split(r"\s+-\s+|\s+(?=[6-9]\d{9}\b)", r.get("phone") or ""))),
                email_=_power.email(" ".join([r.get("email") or ""] + mails)), district=district, parents=parents,
                office=_power.clean(office), list=circle)
    return out.recs


def fetch(p, get):
    file = p.get("file") or re.sub(r"\.pdf$", "", p["url"].rsplit("/", 1)[-1])
    url = p.get("url") or BASE + file + ".pdf"
    r = get(url)
    if r is None or not r.content.startswith(b"%PDF"):
        return [], [], "no answer"
    recs = records(r.content, file, url)
    return recs, [_power.raw(MODULE, file, r.content, "pdf")], "" if recs else "no rows"
