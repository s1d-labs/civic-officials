"""Haryana: officers of the Chief Secretary's organisation (csharyana.gov.in "Contact Us", 2026-11-13).

Source: https://csharyana.gov.in/contact-us (WordPress page, HTML, 145 KB; archive copy of 2026-11-13). One table,
"Telephone numbers of officers of chief secretary organisation": Sr. No. | Name | Present Posting | Telephone Office |
Telephone Residences (in practice mobiles) | EPBAX (intercom) | Office Address. 64 rows: Chief Secretary, ACS / Principal
Secretary / Secretaries of GAD, HR, Personnel, Vigilance, joint / deputy / under secretaries, branch superintendents.
Office numbers are written without the STD code (Chandigarh 0172); kept as written, "std": "0172" says so.
One record per row, level state, body "Chief Secretary Office, Haryana", department = the words after the post.
Route: answered dev-vps-3 (Mumbai) 2026-11-13 in the archive; abroad unchecked -> proxy.
Ids: dept:st_hr_cs:<Sr. No.>.
"""
import re

from dforms import _esw, _state
import provenance

METHOD = "html table"
MODULE = "st_hr_cs"
URL = "https://csharyana.gov.in/contact-us"
BODY = "Chief Secretary Office, Government of Haryana"
POST_RX = re.compile(r"(?i)^((?:chief|additional chief|principal|special|joint|deputy|under|commissioner\s*&)?\s*secretary"
                     r"(?:\s+to\s+(?:government|govt)\.?,?\s*haryana)?|(?:deputy\s+)?superintendent|protocol officer|chief librarian|"
                     r"ad\.?o-?i*)\s*,?\s*(.*)$")


def split_post(t):
    m = POST_RX.match(_esw.clean(t))
    if not m:
        return _esw.clean(t), ""
    return _esw.clean(m.group(1)), _esw.clean(m.group(2)).strip(" ,.")


def parse(html, url=URL):
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        if not rows or not any(re.search(r"(?i)present posting", c) for r in rows[:2] for c in r):
            continue
        for row, p in zip(rows, pos):
            if len(row) < 7 or not re.fullmatch(r"\d{1,3}", row[0].strip()):
                provenance.skip_row(row, 'skip: len(row) < 7 or not re.fullmatch(r"\\d{1,3}", row[0].strip())')
                continue
            sn, name, posting, off, res, epbax, addr = (_esw.clean(c) for c in row[:7])
            post, dept = split_post(posting)
            dash = lambda x: "" if re.fullmatch(r"[-–\s]*", x) else x  # noqa: E731
            out.append(_state.rec(
                MODULE, sn, state="HR", level="state", post=post, name=name, body=BODY, body_kind="secretariat",
                department=dept or None, posting=posting, post_kind=_state.post_kind(posting) or None,
                phone=_esw.phones(dash(off), dash(res)), phone_office=dash(off) or None, phone_residence=dash(res) or None,
                intercom=dash(epbax) or None, std="0172", address=addr, list_no=sn, cells=row, src_url=url, src_pos=p))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:contact-us", "payload": {"reader": MODULE, "url": URL, "state": "HR", "india_only": True,
                                                        "route": "proxy"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "contact-us", r.content)], "" if recs else "no rows"
