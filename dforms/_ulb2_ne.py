"""Shared helper of the North-East ulb2 readers (dforms/ulb2_mn.py, ulb2_nl.py, ulb2_sk.py): district portal pages (S3WaaS / NIC)
whose tables name the officer of a town body in one row ("EO, Oinam & Kwakta", "MEO, Namchi Municipal Council", "MUNICIPAL
COMMISSINER, GMC", "ADC and Administrator MMC").

One queue item = one page. The payload gives the page and its rules: "rules" = [[regex, body, lgd_code, body_type], ...]. A table
row whose designation matches the regex (case-insensitive) gives one record for that body; one row can match two rules ("EO,
Oinam & Kwakta" heads two councils). An optional fifth item sets the role when role_of() cannot read the post: "MEO" (Municipal
Executive Officer, Sikkim) and the page's own spelling "MUNICIPAL COMMISSINER" are heads; the post text stays as written and the
record says role_from = "rule". Column roles come from the header row (name / designation / phone, contact, mobile / email);
rows shorter than the header are aligned from the right (the first columns are often spanned cells). The same body, post and name
seen twice (the same officer under two assembly constituencies) give one record. Post, name and phone stay as the page writes
them; area = the body name as LGD writes it; lgd_code ties the record to civic.ulb.
"""
import re

from dforms import _esw, _ulb

COLS = (("name", r"name"), ("post", r"designation|post"), ("phone", r"phone|contact|mobile|tel"), ("email", r"e-?mail"))


def last_updated(html):
    """'Last Updated: 16.10.2026' (S3WaaS footer) -> '2026-10-16', else None."""
    m = re.search(r"(?i)last\s*updated\s*(?:on)?\s*:?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", _esw.clean(_esw.soup(html).get_text(" ")))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def roles(header):
    """{role: column index} from a header row; the first column that matches wins ("Phone Office" before "Mobile No")."""
    out = {}
    for i, h in enumerate(header):
        for role, rx in COLS:
            if role not in out and re.search(rx, h, re.I) and not (role == "name" and re.search(r"(?i)designation", h)):
                out[role] = i
                break
    return out


def rows(html):
    """[(row dict name/post/phone/email)] of every table with a name and a designation column."""
    out = []
    for t in _esw.soup(html).find_all("table"):
        g = _esw.grid(t, lambda td: _esw.clean(td.get_text(" ")))
        if not g:
            continue
        cols = roles(g[0])
        if "name" not in cols or "post" not in cols:
            continue
        # the mobile column too, when the table has an office phone column and a mobile column
        mob = next((i for i, h in enumerate(g[0]) if re.search(r"(?i)mobile", h) and i != cols.get("phone")), None)
        width = len(g[0])
        for r in g[1:]:
            off = width - len(r)                     # a short row: the first (spanned) columns are missing

            def at(i):
                return r[i - off] if i is not None and 0 <= i - off < len(r) else ""
            cell = {k: at(i) for k, i in cols.items()}
            cell["phone"] = ", ".join(x for x in (cell.get("phone", ""), at(mob)) if _esw.clean(x))
            out.append(cell)
    return out


def parse(module, state, html, rules, district=None, url=""):
    recs, seen, done = [], set(), set()
    lu = last_updated(html)
    for row in rows(html):
        post = _esw.clean(row.get("post"))
        for rx, body, lgd, btype, *role in rules:
            if not post or not re.search(rx, post, re.I):
                continue
            k = (body, post.lower(), _esw.clean(row.get("name")).lower())
            if k in done:
                continue
            done.add(k)
            recs.append(_ulb.record(module, state, body, post, seen, name=row.get("name", ""), phone=row.get("phone", ""),
                                    email=row.get("email", ""), district=district, body_type=btype, source=url,
                                    lgd_code=lgd or None, last_updated=lu))
            if role and role[0] and recs[-1][1]["role"] != role[0]:
                recs[-1][1].update(role=role[0], role_from="rule")
    return recs


def fetch(module, state, p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(module, _esw.slug(p["url"].split("//", 1)[1]), r.content)]
    recs = parse(module, state, r.text, p["rules"], p.get("district"), p["url"])
    return recs, files, "" if recs else "no rows"
