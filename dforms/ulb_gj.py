"""Gujarat: Commissionerate of Municipalities Administration (COMA), communi.gujarat.gov.in. Two server-rendered pages, one queue item.

- Home/listofmunicipalities: one table of all 152 municipalities (nagarpalika): Sr. No., Zone Name (the six COMA regional zones, not
  districts), Municipality Name, Class (A-D), Name of Chief Officer, Cadre, Status (Regular / Charge / Deputation / Loan Service /
  Contract). No phone, no email. About 50 KB.
- Home/pramukhlist: one table of the same 152 municipalities: Sr. No., District, Municipality, Pramukh (President) Name, Mobile Number.
  About 475 KB (inline images). Both pages show "Last Updated : 03/11/2026" (saved by archive.s1d.me on 2026-11-06).
Records: one "Chief Officer" (role head) and one "Pramukh (President)" (role chair) per municipality. The two lists do not use the same
order (Sr. No. differ from row 61 on) and spell some names in other ways (Mehmedabad / Mahemdavad, Zalod / Jhalod, Chorvad / Chorwad):
- a chief officer takes the district of the pramukh row with the same name (key(): letters only, h dropped, w/b as v, z as j, no doubled
  letters; then the same without vowels, only when one row of each list has that key, because "Kadi" and "Kheda" share it);
- three pramukh rows have "-" for the municipality (Kadi, Idar, Dwarka on 2026-11-03): such a row takes the chief officer list's body at
  the same Sr. No. when that body is not named elsewhere in the pramukh list, else it is dropped.
Each record's area is the body name as its own list writes it. District names go out as LGD writes them where the list differs
(Kutch -> Kachchh, Panchmahal -> Panch Mahals: DISTRICTS). Answers only from India (2026-11-11: no answer from Germany in 30 s; the archive
copy was fetched from India). The 17 municipal corporations are in udd.gujarat.gov.in/corporations.php (directories.json item
gj-corporations), not here.
"""
import re

from dforms import _esw, _ulb

MODULE = "ulb_gj"
URL = "https://communi.gujarat.gov.in/Home/listofmunicipalities"
URL_PRAMUKH = "https://communi.gujarat.gov.in/Home/pramukhlist"
BODY_TYPE = "Municipality"
# the pramukh list's district names that LGD (and so civic-india sql/86) spells another way; without this "Mandvi (K)" of Kutch
# falls back to the state-wide name match and ties to Mandvi of Surat
DISTRICTS = {"kutch": "Kachchh", "panchmahal": "Panch Mahals"}


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "url_pramukh": URL_PRAMUKH, "state": "GJ", "india_only": True}}]


def key(name, paren=True, loose=False):
    """Key for one town name in both lists. h dropped, w/b -> v, z -> j, doubled letters once ("Zalod" = "Jhalod", "Chorvad" =
    "Chorwad"). loose: also no vowels after the first letter ("Mehmedabad" = "Mahemdavad"; also "Kadi" = "Kheda", so a loose key is
    used only when it is unique). paren: keep the first letter of a bracket ("Mandvi (K)" = "Mandvi (Kutch)" -> "mandvi k")."""
    s = (name or "").lower()
    tag = re.search(r"\(\s*([a-z])", s)
    s = re.sub(r"[^a-z]", "", re.sub(r"\([^)]*\)", " ", s))
    s = s.replace("w", "v").replace("b", "v").replace("z", "j").replace("h", "")
    if loose:
        s = s[:1] + re.sub(r"[aeiouy]", "", s[1:])
    s = re.sub(r"(.)\1+", r"\1", s)
    return f"{s} {tag.group(1)}" if paren and tag else s


def updated(html):
    m = re.search(r"Last\s*Updated\s*:?\s*(\d{1,2})/(\d{1,2})/(\d{4})", _esw.clean(_esw.soup(html).get_text(" ")))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def table(html, first):
    """Rows of the first table whose heading row has a cell matching first (regex), as dicts by lower-case heading."""
    for t in _esw.soup(html).find_all("table"):
        rows = _esw.grid(t)
        if rows and any(re.search(first, h, re.I) for h in rows[0]):
            head = [h.lower() for h in rows[0]]
            return [dict(zip(head, r)) for r in rows[1:] if len(r) >= len(head) - 1]
    return []


def col(row, rx):
    for k, v in row.items():
        if re.search(rx, k):
            return _esw.clean(v)
    return ""


def blank(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[-–.\s]*", s) else s


def parse(co_html, pramukh_html=None, url=URL, url_pramukh=URL_PRAMUKH):
    co = table(co_html, r"chief\s*officer")
    pr = table(pramukh_html, r"pramukh") if pramukh_html else []
    recs, seen = [], set()
    named = {key(col(r, r"^municipality")) for r in pr if blank(col(r, r"^municipality"))}
    by_sr = {col(r, r"sr"): col(r, r"municipality") for r in co}
    district, base, loose = {}, {}, {}
    for r in pr:
        body, dist = blank(col(r, r"^municipality")), blank(col(r, r"district"))
        dist = DISTRICTS.get(dist.lower(), dist)
        if not body:                                   # "-": the chief officer list's body at the same Sr. No., if it is free
            cand = blank(by_sr.get(col(r, r"sr"), ""))
            body = cand if cand and key(cand) not in named else ""
        r["_body"] = body
        if body and dist:
            district.setdefault(key(body), dist)
            base.setdefault(key(body, False), []).append((key(body), dist))
            loose.setdefault(key(body, False, True), []).append(dist)
    co_keys = {key(col(r, r"municipality")) for r in co}
    co_loose = [key(col(r, r"municipality"), False, True) for r in co]

    def district_of(body):
        """The pramukh list's district for a chief officer's body: the same key; a bare "Mandvi" takes the one Mandvi that no other
        row claims; else the loose key when one body of each list has it."""
        k = key(body)
        if k in district:
            return district[k]
        left = [d for pk, d in base.get(key(body, False), []) if pk == k or pk not in co_keys]
        if len(left) == 1:
            return left[0]
        lk = key(body, False, True)
        hits = loose.get(lk, [])
        return hits[0] if len(hits) == 1 and co_loose.count(lk) == 1 else None
    up_co = updated(co_html)
    for r in co:
        body = blank(col(r, r"municipality"))
        name = blank(col(r, r"chief\s*officer"))
        if not body or not name:
            continue
        recs.append(_ulb.record(MODULE, "GJ", body, "Chief Officer", seen, name=name, district=district_of(body), body_type=BODY_TYPE,
                                source=url, last_updated=up_co, zone=blank(col(r, r"zone")) or None, body_class=blank(col(r, r"class")) or None,
                                cadre=blank(col(r, r"cadre")) or None, status=blank(col(r, r"status")) or None))
    up_pr = updated(pramukh_html) if pramukh_html else None
    for r in pr:
        body = r.get("_body")
        name, phone = blank(col(r, r"pramukh|name")), blank(col(r, r"mobile"))
        if not body or not (name or phone):
            continue
        recs.append(_ulb.record(MODULE, "GJ", body, "Pramukh (President)", seen, name=name, phone=phone,
                                district=DISTRICTS.get(blank(col(r, r"district")).lower(), blank(col(r, r"district"))) or None, body_type=BODY_TYPE, source=url_pramukh, last_updated=up_pr))
    return recs


def fetch(p, get):
    url, url_p = p.get("url", URL), p.get("url_pramukh", URL_PRAMUKH)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "listofmunicipalities", r.content)]
    rp = get(url_p)
    if rp is not None:
        files.append(_esw.keep(MODULE, "pramukhlist", rp.content))
    recs = parse(r.text, rp.text if rp is not None else None, url, url_p)
    return recs, files, "" if recs else "no rows"
