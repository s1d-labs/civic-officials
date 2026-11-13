"""Gujarat: the municipal commissioners of the 17 municipal corporations, from the Urban Development and Urban Housing Department's
list, udd.gujarat.gov.in/corporations.php ("List of Municipal Corporations": Sr.No, Name, Officer Name, Designation, E-Mail ID,
Website). One HTML table, about 43 KB; archive.s1d.me copy saved 2026-11-05 (status 200). The page shows no date. The table is
broken HTML (the first row has no <tr>), so the reader reads the <td> cells in groups of six after the heading row.

Why a reader of its own: ulb_gj (communi.gujarat.gov.in) covers the 152 municipalities (nagarpalika) only, and the generic directory
item gj-corporations (directories.json) put the city name in the name column and tied every row to Ahmedabad (251096) in
civic.official (checked 2026-11-11). Mahesana (LGD 251068, made a corporation in 2025) had no official at all.

Records: one per corporation, post as the list writes it ("Municipal Commissioner", role head), name, email, website. The list
names each corporation by its city only ("Mehsana", "Navsari"); CODES gives the LGD local body code of each (civic.ulb, type
Municipal Corporation, 2026-11-11), so sql/87 ties by code. A row whose city is not in CODES still goes out, without lgd_code.
Not India-only (the archive copy came from India; the reader asks for no other page).
"""
import re

from dforms import _esw, _ulb
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_gj"
STATE = "GJ"
URL = "https://udd.gujarat.gov.in/corporations.php"
# city as the list writes it (lower case, letters only) -> (LGD code, LGD district)
CODES = {"ahmedabad": ("251096", "Ahmedabad"), "surat": ("251231", "Surat"), "vadodara": ("251209", "Vadodara"),
         "rajkot": ("251120", "Rajkot"), "bhavnagar": ("251165", "Bhavnagar"), "jamnagar": ("251133", "Jamnagar"),
         "gandhinagar": ("276440", "Gandhinagar"), "junagadh": ("251147", "Junagadh"), "vapi": ("251264", "Valsad"),
         "navsari": ("251245", "Navsari"), "nadiad": ("251187", "Kheda"), "anand": ("251174", "Anand"),
         "mehsana": ("251068", "Mahesana"), "mahesana": ("251068", "Mahesana"), "morbi": ("251118", "Morbi"),
         "gandhidham": ("251050", "Kachchh"), "surendranagar": ("251114", "Surendranagar"), "porbandar": ("251138", "Porbandar")}


def items(get=None):
    return [{"key": "ulb2_gj-corporations", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": False}}]


def rows(html, where=None):
    """[(city, officer, designation, email, website)] from the corporations table."""
    soup = _esw.soup(html)
    t = soup.find("table", class_="Listtable") or soup.find("table")
    if t is None:
        return []
    out = []
    cells = t.find_all("td")
    for i in range(0, len(cells) - 5, 6):
        c = cells[i:i + 6]
        pos = {"table": _esw.table_no(t), "td": i + 1}     # source trail: the row's first <td> among the table's <td>
        if not re.fullmatch(r"\d+", _esw.clean(c[0].get_text(" "))):
            continue
        a = c[5].find("a", href=True)
        out.append((_esw.clean(c[1].get_text(" ")), _esw.clean(c[2].get_text(" ")), _esw.clean(c[3].get_text(" ")),
                    _esw.clean(c[4].get_text(" ")), a["href"].strip() if a else ""))
        if where is not None:
            where.append(pos)
    return out


def parse(html, url=URL):
    recs, seen, where = [], set(), []
    for (city, name, post, email, site), pos in zip(rows(html, where), where):
        if not city or not (name or email):
            provenance.skipped('skip: not city or not (name or email)')
            continue
        code, district = CODES.get(re.sub(r"[^a-z]", "", city.lower()), (None, None))
        extra = {"lgd_code": code} if code else {}
        if site:
            extra["website"] = site
        recs.append(_ulb.record(MODULE, STATE, city, post or "Municipal Commissioner", seen, name=name, email=email, district=district,
                                body_type="Municipal Corporation", source=url, src_pos=pos, **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "corporations", r.content)], "" if recs else "no rows"
