"""Kerala: anganwadi centres with the anganwadi worker's name and phone, ward name and ward number, from the "Anganwady Details"
page of each local body's own website on lsgkerala.gov.in (https://<body>.lsgkerala.gov.in/en/page/anganwady-details). The page is
part of the new (2026) site template: one HTML table "Centre No. | Name of Anganwadi Worker | Phone Number | Centre Name |
Ward Name | Ward No.", e.g. Adimaly Grama Panchayat: 58 rows, all with a name and a mobile number (the page itself says
"58 Available Centres"). No date on the page.
Coverage on 2026-11-11: the template is live on some grama panchayat sites only (Adimaly yes; Adat, the municipalities Adoor and
Angamaly and the Thrissur corporation answer 404 for the page). Urban bodies are seeded anyway, so a body that moves to the new
template is read at the next run; a 404 item ends with "no page".
One queue item = one body. The reader maps columns by their header words, so a body that orders the columns differently still
reads right. Helper rows ("helper" in the header) are read into helper / helper_phone when a body gives them.
Records: dept women_child, level facility, layer anganwadi, area = centre name, post "Anganwadi Worker", name, phone,
centre_no, ward_no, ward_name, body (from the page title), local_body_code (LGD, from the payload). Record ids:
dept:civic_anganwadi_kl:<host prefix>-<centre no or ward-row>.
"""
import re
from urllib.parse import urlparse

from dforms import _esw

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_anganwadi_kl"
PATH = "/en/page/anganwady-details"
COLS = (("centre_no", re.compile(r"(?i)(centre|center|awc|anganwadi)\s*(no|number|code|id)|^no\.?$|^sl")),
        ("helper_phone", re.compile(r"(?i)helper.*(phone|mobile|contact)")),
        ("helper", re.compile(r"(?i)helper")),
        ("name", re.compile(r"(?i)worker|teacher|name of (the )?(aww|anganwadi)")),
        ("phone", re.compile(r"(?i)phone|mobile|contact")),
        ("ward_no", re.compile(r"(?i)ward\s*(no|number)")),
        ("ward_name", re.compile(r"(?i)ward")),
        ("centre", re.compile(r"(?i)(centre|center|anganwadi|awc)\s*(name)?|name of (the )?(centre|center)|place|location")))


def host_key(url):
    return urlparse(url).hostname.split(".")[0]


def items(get=None):
    """The seed file is the list (built from civic.ulb Kerala names, archive hosts and the panchayats known to have the page)."""
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def header_map(cells):
    out = {}
    for i, c in enumerate(cells):
        for k, rx in COLS:
            if k not in out and rx.search(c):
                out[k] = i
                break
    return out


def title_of(soup):
    t = soup.find("title")
    t = _esw.clean(t.get_text()) if t else ""
    return _esw.clean(t.split("|")[-1]) if "|" in t else ""


def parse(html, url, p=None):
    p = p or {}
    soup = _esw.soup(html)
    body = p.get("body") or title_of(soup)
    hk = host_key(url)
    recs, seen = [], set()
    for table in soup.find_all("table"):
        g = _esw.grid(table)
        if not g:
            continue
        cols = header_map(g[0])
        if "name" not in cols or not ({"phone", "centre", "centre_no"} & set(cols)):
            continue
        for n, row in enumerate(g[1:], 1):
            def cell(k):
                i = cols.get(k)
                return _esw.clean(row[i]) if i is not None and i < len(row) else ""
            name = re.sub(r"^\W+", "", cell("name"))
            phone = _esw.phones(cell("phone"))
            if not (name or phone) or name.lower() == g[0][cols["name"]].lower():
                continue
            cno = cell("centre_no")
            key = _esw.slug(f"{hk}-{cno}") if cno else f"{hk}-row-{n}"
            while key in seen:
                key += "-b"
            seen.add(key)
            recs.append(_esw.record(MODULE, key, dept="women_child", level="facility", layer="anganwadi",
                                    area=cell("centre") or (f"Anganwadi {cno}" if cno else ""), post="Anganwadi Worker",
                                    name=name, phone=phone, centre_no=cno, ward_no=cell("ward_no"), ward_name=cell("ward_name"),
                                    helper=cell("helper"), helper_phone=_esw.phones(cell("helper_phone")), body=body,
                                    local_body_code=p.get("local_body_code"), body_type=p.get("body_type"), state="KL",
                                    district=p.get("district"), office_id=key, source=url))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no page"
    files = [_esw.keep(MODULE, host_key(p["url"]), r.content)]
    recs = parse(r.text, p["url"], p)
    return recs, files, "" if recs else "no anganwadi table"
