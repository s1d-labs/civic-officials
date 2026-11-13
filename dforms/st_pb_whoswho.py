"""Punjab: Administrative Secretaries (punjab.gov.in, Who's Who, 2026-11-13).

Sources (WordPress pages of the state portal, HTML; archive copy of 2026-11-07, 172 KB):
- https://punjab.gov.in/government/whos-who/admin-secretaries/ : one table "LIST OF ADMINISTRATIVE SECRETARIES OF PUNJAB",
  columns "Name of the officer" (name, service, batch "(RR: 1992)") | "Present Posting" (the charges, joined by "and in addition").
- https://punjab.gov.in/government/whos-who/chief-secretary/ : the Chief Secretary's office phones and e-mail (table rows
  "Contact Details", "Email-ID", "Charges held"); they go on the Chief Secretary's records.
One record per charge: an officer with three charges gives three posts (the first is "main_charge": true). A charge
"Commissioner, Jalandhar Division" gets level division and the division's districts (dforms/st_div_pb.json); every other
charge is level state, department = the words after the post ("Principal Secretary, Water Resources" -> "Water Resources").
Route: punjab.gov.in answered dev-vps-3 (Mumbai) 2026-11-13; abroad unchecked -> proxy.
Ids: dept:st_pb_whoswho:<officer slug>:<n>.
"""
import re

from dforms import _esw, _state
import provenance

METHOD = "html table"
MODULE = "st_pb_whoswho"
URL = "https://punjab.gov.in/government/whos-who/admin-secretaries/"
CS_URL = "https://punjab.gov.in/government/whos-who/chief-secretary/"
BODY = "Government of Punjab, Civil Secretariat"
DIV_ALIAS = {"roopnagar": "Rupnagar", "ropar": "Rupnagar", "firozpur": "Ferozepur"}


def charges(text):
    """The charges of one "Present Posting" cell, in order."""
    t = _esw.clean(text).rstrip(".")
    parts = re.split(r"\s*,?\s*\band\s+in\s+add(?:i)?tion\b\s*,?\s*|\s*,?\s*\bin\s+add(?:i)?tion\b\s*,?\s*", t, flags=re.I)
    return [p.strip(" ,.;") for p in parts if p.strip(" ,.;")]


POST_HEAD = re.compile(r"(?i)^((?:special\s+|additional\s+|joint\s+|principal\s+|chief\s+|deputy\s+)*"
                       r"(?:chief secretary|secretary|commissioner|director|administrative secretary|managing director|"
                       r"chief executive officer|chairman|chief electoral officer|inspector general of prisons|nodal officer)"
                       r"(?:\s*-?\s*cum\s*-?\s*(?:financial commissioner|managing director))?(?:\s+to\s+the\s+(?:government of punjab|chief minister,?\s*punjab))?)"
                       r"\s*[,-]?\s*(.*)$")


def split_charge(c):
    """(post, department or office) of one charge: "Principal Secretary, Water Resources" -> ("Principal Secretary",
    "Water Resources"); a charge the pattern does not know stays whole as the post."""
    m = POST_HEAD.match(c)
    if not m:
        return c, ""
    return _esw.clean(m.group(1)), _esw.clean(m.group(2)).strip(" ,-")


def division_of(c):
    m = re.search(r"(?i)\bcommissioner,?\s+([A-Za-z]+)\s+division\b", c)
    if not m:
        return ""
    w = m.group(1)
    return DIV_ALIAS.get(w.lower(), w.title())


def parse(html, url=URL, cs=None):
    """Records of the Administrative Secretaries page. cs: {"phone", "email"} of the Chief Secretary page (or None)."""
    s = _esw.soup(html)
    out, seen = [], set()
    for t in s.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        for row, p in zip(rows, pos):
            if len(row) < 2 or re.search(r"(?i)name of the officer", row[0]):
                provenance.skip_row(row, 'skip: len(row) < 2 or re.search(r"(?i)name of the officer", row[0])')
                continue
            cell, posting = row[0], row[1]
            m = re.search(r"\(\s*(RR|SCS|PCS|NSCS)\s*:?\s*(\d{4})\s*\)", cell)
            name = _esw.clean(re.sub(r"\|", " ", cell[: m.start()] if m else cell)).strip(" ,")
            if not name:
                provenance.skip_row(row, 'skip: not name')
                continue
            slug = _esw.slug(re.sub(HONOR, "", name.split(",")[0]))
            base = slug
            n = 2
            while slug in seen:
                slug, n = f"{base}-{n}", n + 1
            seen.add(slug)
            chs = charges(posting)
            for i, c in enumerate(chs, 1):
                post, dept = split_charge(c)
                div = division_of(c)
                extra = {"post_kind": _state.post_kind(c) if div else _state.post_kind(re.sub(r"(?i)\s+to\s+the\s+.*$", "", post))
                         or _state.post_kind(post)}
                if cs and extra["post_kind"] == "chief_secretary":
                    extra.update(phone=cs.get("phone", ""), email=cs.get("email", ""), contact_source=CS_URL)
                out.append(_state.rec(
                    MODULE, f"{slug}:{i}", state="PB", level="division" if div else "state", post=post, name=name,
                    body=BODY if not div else f"Office of the Divisional Commissioner, {div}",
                    body_kind="division" if div else "secretariat", department=dept or None, division=div,
                    batch=(f"{m.group(1)}: {m.group(2)}" if m else None), charge=c, main_charge=(i == 1),
                    charges_of_officer=len(chs), posting=_esw.clean(posting), cells=row, src_url=url, src_pos=p, **extra))
    return out


HONOR = re.compile(r"(?i)^(sh|shri|smt|dr|mr|ms)\.?\s+")


def parse_cs(html):
    """{"phone", "email"} of the Chief Secretary page."""
    s = _esw.soup(html)
    d = {}
    for t in s.find_all("table"):
        for row in _esw.grid(t):
            if len(row) < 2:
                provenance.skip_row(row, 'skip: len(row) < 2')
                continue
            if re.search(r"(?i)contact", row[0]):
                d["phone"] = _esw.phones(row[1])
            elif re.search(r"(?i)e-?mail", row[0]):
                d["email"] = _esw.emails(row[1].replace("[@]", "[at]"))
    return d


def items(get=None):
    return [{"key": f"{MODULE}:admin-secretaries", "payload": {"reader": MODULE, "url": URL, "cs_url": CS_URL, "state": "PB",
                                                               "india_only": True, "route": "proxy"}}]


def fetch(p, get):
    cs, files = None, []
    if p.get("cs_url"):
        rc = get(p["cs_url"])
        if rc is not None and rc.status_code == 200:
            cs = parse_cs(rc.text)
            files.append(_esw.keep(MODULE, "chief-secretary", rc.content))
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], files, "no answer"
    files.append(_esw.keep(MODULE, "admin-secretaries", r.content))
    recs = parse(r.text, p["url"], cs)
    return recs, files, "" if recs else "no rows"
