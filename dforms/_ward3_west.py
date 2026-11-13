"""Shared helpers of the ward3 readers of West India corporations (dforms/ward3_<city>.py, branch ward-staff-west).
officer_rows(html): the rows of every officer table of a page (a table whose header row names a name column and a post / phone /
email column, in English, Marathi, Hindi or Gujarati), as dicts {name, post, email, phone, cells, pos}; pos = {"table", "row"}
(source trail, the same numbering as _esw.grid)."""
import re

from dforms import _esw

COLS = (
    ("name", r"(name|नाव|नाम|નામ)"),
    ("post", r"(designation|post|पदनाम|पद|हुद्दा|હોદ્દો|જગ્યા)"),
    ("email", r"(e-?\s?mail|ई-?\s?मेल|ઈ-?\s?મેલ|ઇમેલ)"),
    ("phone", r"(phone|mobile|contact|tel|दुरध्वनी|दूरध्वनी|भ्रमणध्वनी|मोबा|फोन|संपर्क|મોબાઈલ|ફોન|સંપર્ક)"),
    ("area", r"(ward|zone|office|area|प्रभाग|विभाग|क्षेत्र|झोन|कार्यालय|વોર્ડ|ઝોન|કચેરી)"),
)


def header_map(cells):
    """{field: column index} of a header row; a cell takes the first field that matches and is not taken yet."""
    out = {}
    for i, c in enumerate(cells):
        t = _esw.clean(c).lower()
        if not t or len(t) > 60:
            continue
        for field, rx in COLS:
            if field not in out and re.search(rx, t):
                out[field] = i
                break
    return out


def officer_rows(html):
    s = _esw.soup(html)
    out = []
    for table in s.find_all("table"):
        pos = []
        g = _esw.grid(table, pos=pos)
        hm, start = {}, 0
        for k, row in enumerate(g[:3]):
            hm = header_map(row)
            if "name" in hm and len(hm) >= 2:
                start = k + 1
                break
        else:
            continue
        for row, p in zip(g[start:], pos[start:]):
            if header_map(row).get("name") is not None and len(header_map(row)) >= 3:
                continue        # a repeated header row
            d = {f: (row[i] if i < len(row) else "") for f, i in hm.items()}
            d["cells"], d["pos"] = row, p
            out.append(d)
    return out
