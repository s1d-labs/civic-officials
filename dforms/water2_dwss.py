"""Punjab: Department of Water Supply & Sanitation (DWSS), dwss.punjab.gov.in/contact-us/ ("Contact Detail"). India only (times out
from Germany); the server needs TLS legacy renegotiation (see water2_pwssb). One queue item.

The page holds two Supsystic tables. Table 1: Rank | Address | Contact Detail | Photo: Minister, Administrative Secretary, Special
Secretary / Head of Department (SBM, JJM), Chief Engineers (PD&QA, South, Central, North), SE (Technical); the first cell is
"<b>Name</b></br> Post </br>". Table 2: "Name, Superintending Engineer" | "DWSS, Circle <town>" | "e-mail[at]punjab.gov.in phone(O)":
the 12 field circles (Patiala, Chandigarh, Hoshiarpur, Ludhiana, Ferozepur, Faridkot, Gurdaspur, Amritsar, Jalandhar, Bathinda,
Shri Muktsar Sahib, Sangrur). About 22 rows on 2026-11-11. No divisions or sub-divisions are published (none on the site's
menus or documents); "(AD)" after a name = additional charge. Names, phones, e-mails: yes. No date on the page.
Levels: Minister / Secretary / HoD / CE (PD&QA) / SE (Technical) -> state, CE (South / Central / North) -> zone, circle SE -> circle.
Record id dept:water2_dwss:<post>-<area>.
"""
import html as htmlmod
import re

from dforms import _esw
from dforms._water import unique
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "water2_dwss"
URL = "https://dwss.punjab.gov.in/contact-us/"
ORG = "Department of Water Supply & Sanitation, Punjab"


def items(get=None):
    return [{"key": f"{MODULE}:contact-us", "payload": {"reader": MODULE, "url": URL, "state": "PB", "india_only": True}}]


def raw_cell(td):
    """The cell's source text (data-original-value keeps the <b>name</b></br> post markup)."""
    return htmlmod.unescape(td.get("data-original-value") or td.decode_contents())


def name_post(cell):
    """(name, post) from '<b>Sh. X</b></br> Chief Engineer (South) </br>' or 'Sh. X, Superintending Engineer'."""
    m = re.match(r"(?is)\s*<b>(.*?)</b>(.*)$", cell)
    if m:
        name, post = m.group(1), m.group(2)
    else:
        txt = re.sub(r"<[^>]+>", " ", cell)
        name, _, post = txt.partition(",")
    post = re.sub(r"<[^>]+>", " ", post)
    post = re.sub(r"(?i)\s*Department of Water Supply\s*&\s*Sanitation\s*,?\s*Punjab", "", post)
    return _esw.clean(re.sub(r"<[^>]+>", " ", name)), _esw.clean(post)


def level(post):
    if re.search(r"(?i)chief\s+engineer\s*\((south|central|north)\)", post):
        return "zone"
    if re.search(r"(?i)superintending\s+engineer", post) and not re.search(r"(?i)\(SE-T\)|technical", post):
        return "circle"
    return "state"


def parse(html, url=URL):
    soup = _esw.soup(html)
    recs, seen = [], set()
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                provenance.skip_row(tr, 'skip: len(tds) < 3')
                continue
            name, post = name_post(raw_cell(tds[0]))
            addr = _esw.clean(_esw.cell_text(tds[1]))
            contact = _esw.clean(_esw.cell_text(tds[2]))
            if not name or re.fullmatch(r"(?i)rank", name):
                provenance.skip_row(tr, 'skip: not name or re.fullmatch(r"(?i)rank", name)')
                continue
            m = re.search(r"\((SE-T)\)(.*)$", name)
            if m or (post and re.match(r"\(SE-T\)", post)):        # "Sh. Naval Kishor (SE-T) (additonal charge)": post in brackets
                full = f"{name} {post}" if post else name
                name = full.split("(")[0]
                post = "Superintending Engineer (Technical)" + (" (additional charge)" if "addit" in full.lower() else "")
            lvl = level(post)
            circ = re.search(r"(?i)circle\s+(.+)$", addr)
            if lvl == "circle":
                area = f"{_esw.clean(circ.group(1))} Circle" if circ else addr
            else:
                m = re.search(r"\(([^)]+)\)", post)
                area = f"{m.group(1)} Zone" if lvl == "zone" and m else "Punjab"
            extra = {}
            m = re.search(r"\(\s*(AD|additional charge|additonal charge)\s*\)", name + " " + post, re.I)
            if m:
                extra["additional_charge"] = True
            nm = re.sub(r"\s*\((AD)\)\s*", " ", name)
            nm = re.sub(r"^(Sh|Smt|Shri|Dr)\.?\s+", "", _esw.clean(nm))
            key = unique(f"{_esw.slug(post)}-{_esw.slug(area)}", seen)
            nums = re.sub(r"(?i)\(\s*fax\s*\)", " ", re.sub(r"[\w.]+(\[at\]|@)[\w.\[\]-]+", " ", contact))
            recs.append(_esw.record(MODULE, key, dept="water", level=lvl, area=area, post=post, name=nm,
                                    phone=_esw.phones(nums) or None, email=_esw.emails(contact) or None, address=addr, state="PB",
                                    district=_esw.clean(circ.group(1)) if circ else None, source=url, org=ORG, **extra,
                                    src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_esw.keep(MODULE, "contact-us", r.content)], "" if recs else "no rows"
