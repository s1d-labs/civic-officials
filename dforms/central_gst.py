"""CBIC (Central GST and Central Excise) commissionerates and their officers from the zone websites. A page holds one or more
tables "S.No. | Name of Officer (S/Sh/Smt) | Designation | [Charges held] | [Landline] | Email ID | Office Address"
(cgstmumbai.gov.in/en/commissionerate/<kind>/<name>: executive, audit and appeal commissionerates of the Mumbai zone, 21 pages,
about 209 officers: Commissioner, Additional / Joint Commissioners, Deputy / Assistant Commissioners of each division).
fetch() reads every such table (any column order; header words decide the field). One record per officer: dept "gst"
(new key, see the report), level "division", area = commissionerate (payload "area" or the page path), post =
designation, charge (the division or section the officer holds), phone (landline, with payload "std" when the page writes it
without the STD code), email, address. Payload: url, state, zone, area, std. Record ids
dept:central_gst:<zone>:<area slug>:<officer slug>. Seed: seeds/dept_central_gst.json.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _esw
from dforms.police_s3waas import last_updated
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "central_gst"
TITLE = re.compile(r"^(?:(?:shri|smt|sri|sh|mr|mrs|ms|dr|km|kumari)(?:\.\s*|\s+))+", re.I)
COLS = (("name", r"name"), ("designation", r"designation|post"), ("charge", r"charge|division|section|work"),
        ("phone", r"landline|phone|tele|mobile|contact"), ("email", r"e-?\s?mail"), ("address", r"address"))


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def kinds(head):
    out = []
    for h in head:
        h = h.lower()
        k = next((k for k, pat in COLS if re.search(pat, h) and k not in out), None)
        out.append(k)
    return out


def phone(v, std):
    v = _esw.clean(v)
    if not re.search(r"\d{5}", v):
        return None
    if std and re.fullmatch(r"\d{6,8}", re.sub(r"[\s-]", "", v)):
        return f"{std}-{v}"
    return _esw.phones(v) or v


def officers(html, url, p):
    soup = _esw.soup(html)
    area = p.get("area") or urlparse(url).path.rstrip("/").split("/")[-1].replace("-", " ").title()
    lu = last_updated(html)
    recs, seen = [], set()
    for t in soup.find_all("table"):
        gpos = []
        g = _esw.grid(t, pos=gpos)
        if len(g) < 2:
            continue
        ks = kinds(g[0])
        if "name" not in ks or "designation" not in ks:
            continue
        for row, rp in zip(g[1:], gpos[1:]):
            f = {k: v for k, v in zip(ks, row) if k}
            name = TITLE.sub("", f.get("name", "")).strip(" ,")
            if not name or name.lower() in ("vacant", "-"):
                provenance.skip_row(row, 'skip: not name or name.lower() in ("vacant", "-")')
                continue
            key = f"{p.get('zone', 'x')}:{_esw.slug(area)}:{_esw.slug(name)}"
            n, k = 1, key
            while k in seen:
                n += 1
                k = f"{key}-{n}"
            seen.add(k)
            recs.append(_esw.record(
                MODULE, k, dept="gst", level="division", area=area, post=f.get("designation"), name=name,
                charge=f.get("charge") or None, phone=phone(f.get("phone", ""), p.get("std")),
                email=_esw.emails(f.get("email", "")), address=f.get("address"), zone=p.get("zone"),
                state=p["state"], district=p.get("district"), office_id=_esw.slug(area), source=url, last_updated=lu,
                agency="CBIC", src_pos=rp))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    tag = _esw.slug(urlparse(p["url"]).path)[-80:] or "home"
    files = [_esw.keep(MODULE, f"{p.get('zone', 'x')}-{tag}", r.content)]
    recs = officers(r.text, p["url"], p)
    return recs, files, "" if recs else "no officer tables"
