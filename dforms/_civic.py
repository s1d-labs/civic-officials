"""Shared helpers for the civic layer readers of fork C (dforms/civic_post_*, civic_csc_*, civic_fire_*): state names to the
two-letter codes the other readers use, numbers as coordinates, and one record() wrapper that adds the layer tag.
Built on dforms/_esw.py (record, clean, phones, emails, slug, keep, soup); _esw.py is not changed.
"""
import re

from dforms import _esw

STATES = {
    "andaman and nicobar islands": "AN", "andhra pradesh": "AP", "arunachal pradesh": "AR", "assam": "AS", "bihar": "BR",
    "chandigarh": "CH", "chhattisgarh": "CG", "chattisgarh": "CG", "dadra and nagar haveli": "DH", "daman and diu": "DH",
    "the dadra and nagar haveli and daman and diu": "DH", "dadra and nagar haveli and daman and diu": "DH", "delhi": "DL",
    "goa": "GA", "gujarat": "GJ", "haryana": "HR", "himachal pradesh": "HP", "jammu and kashmir": "JK", "jharkhand": "JH",
    "karnataka": "KA", "kerala": "KL", "ladakh": "LA", "lakshadweep": "LD", "madhya pradesh": "MP", "maharashtra": "MH",
    "manipur": "MN", "meghalaya": "ML", "mizoram": "MZ", "nagaland": "NL", "odisha": "OD", "orissa": "OD", "puducherry": "PY",
    "pondicherry": "PY", "punjab": "PB", "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN", "tamilnadu": "TN",
    "telangana": "TG", "tripura": "TR", "uttar pradesh": "UP", "uttarakhand": "UK", "uttaranchal": "UK", "west bengal": "WB",
}


def state_code(name):
    """'The Dadra And Nagar Haveli And Daman And Diu' -> 'DH'; '' when the name is not a state (the directory has 'Na')."""
    n = re.sub(r"\s+", " ", re.sub(r"&", " and ", (name or "").lower())).strip()
    n = re.sub(r"\s+circle$", "", n)
    return STATES.get(n, "")


def coord(v, lo, hi):
    """A latitude or longitude as a float inside India's box, else None ('NA', '0', a swapped pair ...)."""
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return round(f, 7) if lo <= f <= hi else None


def lat(v):
    return coord(v, 6.0, 37.6)


def lon(v):
    return coord(v, 68.0, 97.5)


def record(module, key, layer, **f):
    """_esw.record() with the extra key layer=<post|csc|fire>."""
    return _esw.record(module, key, layer=layer, **f)


def unique(key, seen):
    """key, or key-2, key-3 ... when the same key came before in this answer."""
    k, n = key, 1
    while k in seen:
        n += 1
        k = f"{key}-{n}"
    seen.add(k)
    return k


def s3waas_pages(p, get, module, max_pages=30):
    """S3WaaS public-utility category page p["url"] and its /page/N/ pages: ([(url, html)], files) or (None, []) if page 1 fails.
    Uses dforms/police_s3waas.next_pages() (imported, not changed)."""
    from urllib.parse import urlparse
    from dforms.police_s3waas import next_pages
    url = p["url"]
    r = get(url)
    if r is None:
        return None, []
    host = urlparse(url).netloc
    tag = _esw.slug(urlparse(url).path)[-60:]
    files = [_esw.keep(module, f"{host}-{tag}-p1", r.content)]
    pages = [(url, r.text)]
    base, more = next_pages(r.text, url)
    done = {1}
    more = set(more) - done
    while more and len(pages) < p.get("max_pages", max_pages):
        n = min(more)
        done.add(n)
        u = f"{base}page/{n}/"
        m = get(u)
        if m is None:
            break
        files.append(_esw.keep(module, f"{host}-{tag}-p{n}", m.content))
        pages.append((u, m.text))
        more = (more | next_pages(m.text, u)[1]) - done
    return pages, files


# ---------------------------------------------------------------- source trail (provenance.py)
_ROWS = {}


def tr_pos(tr):
    """src_pos of one <tr>: {"table": the table's place among the page's tables (as officials.tables / _esw.table_no),
    "row": the row's <tr> number inside that table (1-based, header counted, as officials.tables counts)}."""
    table = tr.find_parent("table")
    if table is None:
        return {}
    key = id(table)
    if key not in _ROWS or _ROWS[key][0] is not table:
        if len(_ROWS) > 64:
            _ROWS.clear()
        _ROWS[key] = (table, _esw.table_no(table), {id(t): n for n, t in enumerate(table.find_all("tr"), 1)})
    _, tno, rows = _ROWS[key]
    return {"table": tno, "row": rows.get(id(tr))}


def tag(recs, r, url=None, **extra):
    """Name the answer r (provenance.at: url asked + sha256 of the bytes) on every record of recs that names none yet, plus extra
    keys (method ...) where the record has none. Returns recs."""
    at = None
    for _, d in recs:
        if isinstance(d, dict) and "src_url" not in d and r is not None:
            if at is None:
                import provenance
                at = provenance.at(r, url)
            d.update(at)
        for k, v in extra.items():
            if v is not None and isinstance(d, dict):
                d.setdefault(k, v)
    return recs
