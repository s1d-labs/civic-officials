"""Thane Municipal Corporation (thanecity.gov.in): the page "प्रशासकीय अधिकाऱ्यांची यादी" (list of administrative officers,
/tmc/SectionInformation.html?editForm&rowId=9; the site sets a session cookie on the first redirect). Four tables with the header
अधिकाऱ्याचे नाव | पदनाम | ई-मेल आयडी | दुरध्वनी क्रमांक (name | post | email | phone):
  table 1  head office officers (commissioner, additional / deputy commissioners, heads of departments)  -> level "body"
  table 3  the deputy commissioners of the 3 परिमंडळ (circles), each over named प्रभाग समित्या       -> level "division"
  table 4  the assistant commissioners of the 9 प्रभाग समित्या (ward committees)                     -> level "zone"
A ward committee covers several electoral wards (प्रभाग); the page does not name them: wards_note says so.
Live sample from dev-vps-3 (Mumbai) 2026-11-13: 47 + 3 + 10 rows. The archive has only the home page (vantages IN, pool).
Names and posts are Marathi: name_regional / post_regional carry them too. Ids: dept:ward3_thane:<level>:<email or name slug>.
"""
import re

from dforms import _esw, _ward, _ward3_west as w3
import provenance

METHOD = "html table"

MODULE = "ward3_thane"
BODY, LGD, STATE, DISTRICT = "Thane Municipal Corporation", "251471", "MH", "Thane"
URL = "https://thanecity.gov.in/tmc/SectionInformation.html?editForm&rowId=9"
CIRCLE = re.compile(r"परिमंडळ\s*-?\s*([०-९\d]+)")
COMMITTEE = re.compile(r"(?:आयुक्त\s*[-–)]*|कार्यभार\)\s*[-–]?)\s*([^,()]+?)\s*प्रभाग\s*समिती")


def items(get=None):
    return [{"key": f"{MODULE}-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _digits(s):
    return s.translate(str.maketrans("०१२३४५६७८९", "0123456789"))


def parse(html, url=URL):
    seen, recs = set(), []
    for d in w3.officer_rows(html):
        post, name = _esw.clean(d.get("post")), _esw.clean(d.get("name"))
        if not post:
            provenance.skip_row(d, 'skip: not post')
            continue
        circle, committee = CIRCLE.search(post), COMMITTEE.search(post)
        extra = {}
        if circle and post.startswith("उप"):
            level, area = "division", f"Circle (Parimandal) {_digits(circle.group(1))}"
            extra["zone"] = area
            extra["ward_committees"] = _esw.clean(post.split(_esw.clean(circle.group(0)), 1)[-1]).strip(" )")
            role = "head"
        elif committee and "सहाय्यक आयुक्त" in post and ("प्रशासकीय" not in post):
            level = "zone"
            area = _esw.clean(committee.group(1)).strip(" -–") + " Ward Committee (Prabhag Samiti)"
            extra["wards_note"] = "the source names the ward committee, not its electoral wards"
            role = "head"
        else:
            level, area, role = "body", BODY, None
        key = (d.get("email") or "").split()[0] if d.get("email") else _esw.slug(name or post)[:40]
        recs.append(_ward.record(MODULE, f"{level}:{_esw.slug(key)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level=level, area=area, post=post, post_regional=post, name=name, name_regional=name or None,
                                 phone=d.get("phone") or "", email=d.get("email") or "", role=role, source=url,
                                 src_pos=d["pos"], **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "officers", r.content, "html")]
    recs = parse(r.content.decode("utf-8", "replace"), p["url"])
    return recs, files, "" if recs else "no officer table"
