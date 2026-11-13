"""Helpers of the state-level readers of fork APE (st_tg_*, st_od_*, st_wb_*, st_ap_*, st_an_*): HTML contact tables whose
first row names the columns (Name | Designation | Department | Phone | Email ...), read with header names, not positions.
"""
import re

from dforms import _esw

COLS = [  # header text -> field (first match wins)
    ("sn", r"^(s\.?\s*no|sl\.?\s*no|sr\.?\s*no|serial|#|no\.?)\.?$"),
    ("email", r"e-?\s*mail"),
    ("fax", r"\bfax\b"),
    ("residence", r"resi"),
    ("epabx", r"epabx|intercom|extn|\bext\b"),
    ("phone", r"phone|tel|mobile|contact|office\s*(no|number)|^office$"),
    ("district", r"district"),
    ("department", r"department|dept|office$|organi[sz]ation|wing|establishment|name of office"),
    ("post", r"designation|post\b|rank"),
    ("name", r"name"),
]


def col_of(h):
    t = _esw.clean(h).lower()
    for k, rx in COLS:
        if re.search(rx, t):
            return k
    return ""


def header_rows(table):
    """[(row dict field -> text, src_pos {table,row}, cells)] of one HTML table; the first row whose cells name at least two
    known columns is the header. Rows before it are skipped; a row with no cell text is skipped."""
    pos = []
    g = _esw.grid(table, pos=pos)
    head, out = None, []
    for row, p in zip(g, pos):
        if head is None:
            ks = [col_of(c) for c in row]
            if len([k for k in ks if k]) >= 2 and ("name" in ks or "post" in ks or "department" in ks):
                head = ks
            continue
        if row == g[0] or not any(_esw.clean(c) for c in row):
            continue
        d = {}
        for k, c in zip(head, row):
            if k and c and k not in d:
                d[k] = _esw.clean(c)
            elif k and c and d.get(k) != _esw.clean(c):
                d[k] = d[k] + " | " + _esw.clean(c)
        out.append((d, p, row))
    return out


def tables(html):
    return _esw.soup(html).find_all("table")


ABBR = [(r"\baddl?\.?(?=\s)", "Additional"), (r"\bprl\.?(?=\s)", "Principal"), (r"\bspl\.?(?=\s)", "Special"),
        (r"\bjt\.?(?=\s)", "Joint"), (r"\bdy\.?(?=\s)", "Deputy"), (r"\bsecy\b\.?", "Secretary"),
        (r"\bcommr\b\.?", "Commissioner"), (r"\bgovt\b\.?", "Government")]


def expand(post):
    """Post text with the usual abbreviations written out ("Addl. Chief Secretary" -> "Additional Chief Secretary"), for
    post_kind only (the record keeps the post as the source writes it)."""
    t = _esw.clean(post)
    for rx, full in ABBR:
        t = re.sub(rx, full, t, flags=re.I)
    return t


TO_HEAD = re.compile(r"(?i)\s*(?:to|of)\s+(?:the\s+)?(?:hon'?ble\s+)?(?:chief\s+minister|minister|governor|lt\.?\s*governor)\b.*$")


def post_kind(post):
    """_state.post_kind of a post with "to Chief Minister" / "to Governor" cut off first, so "Secretary to Chief Minister" is
    a secretary and "A.D.C to Governor" is not the Governor ("other" when the rest names no rank)."""
    from dforms import _state
    t = expand(post)
    if re.search(r"(?i)\bspecial chief secretary\b", t):
        return "acs"           # same grade as Additional Chief Secretary (Telangana, Andhra Pradesh)
    cut = TO_HEAD.sub("", t)
    if cut != t:
        return _state.post_kind(cut) or "other"
    return _state.post_kind(t)
