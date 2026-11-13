"""Nagar Nigam Dehradun (nndehradun.uk.gov.in, NIC S3WaaS-style WordPress): the sanitation staff of its 100 wards. Two pages
(saved in archive.s1d.me 2026-11-05; neither shows a "Last Updated" date):
  /sanitation-section/   table "Sl. No./Ward No. | Ward Name | Supervisor Name | Mobile No. | Inspector Name | Mobile No.", one row
                         per ward (1-100): the ward's sanitation supervisor and its sanitation inspector.
  /list-of-supervisors/  table "Sl No. | Name (", Sanitation Inspector") | Mobile Number | Ward Numbers": six inspectors with
                         the wards (1-60) in their charge. This list is older than the 100-ward table (it stops at ward 60).
Records: supervisors one per ward (level "ward", wards [n], area_regional = the ward name as the table writes it); inspectors one
per person and page, with every ward the page gives them (level "ward"). Record ids:
dept:ward2n_dehradun:ward-<n>:sanitation-supervisor, dept:ward2n_dehradun:si:<mobile> (100-ward table),
dept:ward2n_dehradun:si-list:<mobile> (list of supervisors).
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_dehradun"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Dehradun", "248430", "UK", "Dehradun"
BASE = "https://nndehradun.uk.gov.in"
PAGES = {"sanitation-section": f"{BASE}/sanitation-section/", "list-of-supervisors": f"{BASE}/list-of-supervisors/"}


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": u, "state": STATE, "page": k}} for k, u in PAGES.items()]


def _rec(seen, key, **f):
    return _ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, wing="sanitation", **f)


def parse_section(html, p):
    seen, recs, insp = set(), [], {}
    for t in _esw.soup(html).find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g or not ("supervisor" in " ".join(g[0]).lower() and "inspector" in " ".join(g[0]).lower()):
            continue
        for vals, vp in zip(g[1:], gp[1:]):
            ward = re.sub(r"\D", "", vals[0])
            if not ward or len(vals) < 6:
                provenance.skipped('skip: not ward or len(vals) < 6')
                continue
            ward = str(int(ward))
            wname, sup, sup_mob, ins, ins_mob = (_esw.clean(v) for v in vals[1:6])
            if sup or sup_mob:
                recs.append(_rec(seen, f"ward-{ward}:sanitation-supervisor", level="ward", area=f"Ward {ward}",
                                 ward_name=wname or None, post="Sanitation Supervisor", name=sup,
                                 phone=sup_mob, wards=[ward], source=p["url"], src_pos=vp))
            if ins or ins_mob:
                k = re.sub(r"\D", "", ins_mob) or _esw.slug(ins)
                i = insp.setdefault(k, {"name": ins, "phone": ins_mob, "wards": [], "at": []})
                i["wards"].append(ward)
                i["at"].append(vp)
    for k, i in insp.items():
        recs.append(_rec(seen, f"si:{k}", level="ward", area="Wards " + ", ".join(i["wards"]), post="Sanitation Inspector",
                         name=i["name"], phone=i["phone"], wards=i["wards"], source=p["url"],
                         src_pos={"rows": i["at"], "note": "one inspector summed over these table rows"}))
    return recs


def parse_list(html, p):
    seen, recs = set(), []
    for _, rows in _ward.header_tables(html, "name", "mobile", "ward"):
        for r in rows:
            name_post = _ward.col(r, "name")
            name, _, post = name_post.partition(",")
            mob = _ward.col(r, "mobile")
            wards = _ward.wards_of(_ward.col(r, "ward"))
            if not (name and wards):
                provenance.skip_row(r, 'skip: not (name and wards)')
                continue
            k = re.sub(r"\D", "", mob) or _esw.slug(name)
            recs.append(_rec(seen, f"si-list:{k}", level="ward", area="Wards " + ", ".join(wards),
                             post=_esw.clean(post) or "Sanitation Inspector", name=name, phone=mob, wards=wards, source=p["url"],
                             src_pos=r.pos))
    return recs


def parse(html, p):
    return parse_list(html, p) if p.get("page") == "list-of-supervisors" else parse_section(html, p)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("page", "page"), r.content)], "" if recs else "no table"
