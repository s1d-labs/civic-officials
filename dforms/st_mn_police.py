"""Manipur: senior police officers from the Manipur Police site manipurpolice.gov.in/senior-officers/ (checked 2026-11-13 from
dev-vps-3, Mumbai: HTTP 200, 50 KB HTML, no captcha). One table: Sl. No. | Name of Officer | Current Posting | Official Tele.
No. | Residential Tele. No. | e-mail ID (about 15 rows: DGP, ADGPs, IGPs, DIGs and range / zone posts).
A posting that names a range or zone ("IGP (Zone-I)", "DIG (Range-II)") gets level division with that range as division
(Manipur has no st_div file: districts left empty). Record ids: dept:st_mn_police:<row>:<name slug>.
"""
import re

from dforms import _esw, _state, st_ne
import provenance

METHOD = "html table (manipurpolice.gov.in senior officers)"
MODULE = "st_mn_police"
URL = "https://manipurpolice.gov.in/senior-officers/"


def parse(html, url=URL):
    out = []
    for r in st_ne.table_rows(html):
        name, post = r.get("name", ""), r.get("post", "") or r.get("place", "")
        if not name:
            provenance.skip_row(r, 'skip: not name')
            continue
        cells = r["cells"]
        office = cells[3] if len(cells) > 3 else ""
        res = cells[4] if len(cells) > 4 else ""
        m = re.search(r"(?i)\b(range|zone|R|Z)\s*[-–]\s*([IVX]+|\d)\b", re.split(r"&|,|in addition|look after", post)[0])
        div = f"{'Range' if m.group(1).lower().startswith('r') else 'Zone'} {m.group(2).upper()}" if m else ""
        out.append(_state.rec(MODULE, f"{r['src_pos']['row']}:{_esw.slug(re.sub(r',.*$', '', name))[:60]}", state="MN",
                              level="division" if div else "state", division=div, post=post, post_kind=st_ne.post_kind(post),
                              name=name, body="Manipur Police Headquarters", body_kind="police", department="Home (Police)",
                              dept="police", phone=_esw.phones(office), phone_residence=_esw.phones(res) or None,
                              email=_esw.emails(r.get("email", "")), cells=cells, src_url=url, src_pos=r["src_pos"]))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:senior", "payload": {"reader": MODULE, "url": URL, "state": "MN", "india_only": False, "route": "direct"}}]


def fetch(p, get):
    r = get(p.get("url") or URL)
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p.get("url") or URL)
    return recs, [_esw.keep(MODULE, "senior-officers", r.content)], "" if recs else "no rows"
