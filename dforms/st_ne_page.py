"""North-east: one state-level contact page with a header table (commission "Who's Who", police telephone directory, office
telephone list), read by st_ne.table_rows. The seed says what the page is (payload "body", "body_kind", "dept", "level").
Pages seeded (each checked by hand on 2026-11-13 from dev-vps-3, Mumbai; seeds/dept_st_<xx>.json, "reader": "st_ne_page"):
megpolice.gov.in/telephone-directory (Meghalaya Police HQ: DGP, ADGPs, IGPs, DIGs, SPs, about 60 rows), meglc.gov.in/
telephone_directory.html (Labour Commissioner and district labour offices, 65), tcw.tripura.gov.in who-is-who (Tripura
Commission for Women, 5), secap.nic.in/telephone.htm (Arunachal State Election Commission, 5, expired certificate: the
pool's get() retries without TLS checks and marks tls_unverified), sec.mizoram.gov.in/page/officers-staff (Mizoram State
Election Commission, 29).
A row without a person name whose first cell is a post ("Secretary to the Commission") is a post-only record. A row that
repeats the header ("Name | Designation | Mobile") is left out. Record ids: dept:st_ne_page:<page key>:<table>-<row>.
"""
import re

from dforms import _esw, _state, st_ne
import provenance

METHOD = "html table (state-level contact page)"
MODULE = "st_ne_page"
DIST_WORDS = re.compile(r"(?i)\bdistrict\b|\bSP\b|superintendent of police")


def parse(html, p):
    out = []
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "")
        if re.fullmatch(r"(?i)name( of .*)?", name or "") or re.fullmatch(r"(?i)designation", post or ""):
            provenance.skip_row(r, 'skip: re.fullmatch(r"(?i)name( of .*)?", name or "") or re.fullmatch(r"(?...')
            continue
        office = ""
        if re.match(r"(?i)^(office|o/o|directorate|district|sub-?divisional)\b", name or ""):
            office, name = name, ""
        if name and not post and not st_ne.TITLE.match(name) and (st_ne.post_kind(name) or re.search(r"(?i)\b(to|of)\b", name)):
            name, post = "", name
        cont = " ".join(r.get(k, "") for k in ("contact", "phone", "email"))
        ph, em, addr = st_ne.contact(cont)
        if not ph:
            ph = _esw.phones(" ".join(c for c in r["cells"] if c not in (name, post)))
        pos = r["src_pos"]
        out.append(_state.rec(MODULE, f"{p['page_key']}:{pos['table']}-{pos['row']}", state=p["state"], level=p.get("level", "state"),
                              post=post, post_kind=st_ne.post_kind(post), name=name, body=p["body"], body_kind=p.get("body_kind", ""),
                              department=p.get("department") or p["body"], dept=p.get("dept") or st_ne.dept(p["body"], post),
                              phone=ph, email=em or _esw.emails(" ".join(r["cells"])), address=addr or r.get("address", ""),
                              place=r.get("place") or r.get("district"), office=office or None, section=r["section"] or None,
                              district_hint=True if DIST_WORDS.search(post) else None,
                              cells=r["cells"], src_url=p["url"], src_pos=pos))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p["page_key"], r.content)], "" if recs else "no rows"
