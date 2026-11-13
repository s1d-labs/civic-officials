"""North India state commissions: "Who's Who" / "Directory & Contacts" tables of State Election Commission sites
(2026-11-13). One reader for the DBIM / WordPress pages that give one table with the columns Name | Designation and,
where present, Telephone | E-mail (headers matched by word, any order).

Sources (HTML, archive copies of 2026-11-05/06):
- Haryana SEC https://secharyana.gov.in/whos-who/ : Sr. No. | Name | Designation | Telephone | E-mail, 12 rows (State Election
  Commissioner, Secretary, District Attorney, accounts ...). Phones without STD code (Panchkula 0172).
- Uttarakhand SEC https://sec.uk.gov.in/whos-who/ (+ /whos-who/page/2): Name | Designation, 12 rows a page.
Payload: url, pages (more urls of the same list), state, body (the commission's name), dept (TAGGING key).
Records: level state, body_kind commission. A "Vacant" name gives vacant: true and no name.
Route: proxy (India; abroad unchecked).
Ids: dept:st_nt_commission:<state>-<body slug>:<page n>:<row>.
"""
import re

from dforms import _esw, _state
import provenance

METHOD = "html table"
MODULE = "st_nt_commission"
SOURCES = [
    {"url": "https://secharyana.gov.in/whos-who/", "state": "HR", "body": "State Election Commission, Haryana", "dept": "elections"},
    {"url": "https://sec.uk.gov.in/whos-who/", "pages": ["https://sec.uk.gov.in/whos-who/page/2"], "state": "UK",
     "body": "State Election Commission, Uttarakhand", "dept": "elections"},
]
COLS = [("name", r"^name"), ("post", r"designation|post"), ("phone", r"tele|phone|mobile|contact"), ("email", r"e-?mail")]


def header_map(row):
    m = {}
    for i, c in enumerate(row):
        for k, rx in COLS:
            if k not in m and re.search(rx, c.strip(), re.I):
                m[k] = i
                break
    return m if "name" in m and "post" in m else None


def parse(html, url, p, page_no=1):
    s = _esw.soup(html)
    out = []
    key = f"{p['state'].lower()}-{_esw.slug(p['body'])}"
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        hm = None
        for row, ps in zip(rows, pos):
            if hm is None:
                hm = header_map(row)
                continue
            get = lambda k: _esw.clean(row[hm[k]]) if k in hm and hm[k] < len(row) else ""  # noqa: E731
            name, post = get("name"), get("post")
            if not (name or post):
                provenance.skip_row(row, 'skip: not (name or post)')
                continue
            vac = bool(re.search(r"(?i)vacant", name))
            out.append(_state.rec(
                MODULE, f"{key}:{page_no}:{ps['row']}", state=p["state"], level="state", post=post,
                name="" if vac else name, vacant=True if vac else None, body=p["body"], body_kind="commission",
                department=p["body"], dept=p.get("dept"), phone=_esw.phones(get("phone")), email=_esw.emails(get("email")),
                cells=row, src_url=url, src_pos=ps))
        if out:
            break
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{s['state'].lower()}-{_esw.slug(s['body'])}",
             "payload": {"reader": MODULE, **s, "india_only": True, "route": "proxy"}} for s in SOURCES]


def fetch(p, get):
    recs, files = [], []
    for n, u in enumerate([p["url"]] + list(p.get("pages") or []), 1):
        r = get(u)
        if r is None or r.status_code != 200:
            if n == 1:
                return [], files, "no answer"
            continue
        files.append(_esw.keep(MODULE, f"{p['state'].lower()}-{_esw.slug(p['body'])}-{n}", r.content))
        recs += parse(r.text, u, p, n)
    return recs, files, "" if recs else "no rows"
