"""Divisional commissioners' own S3WaaS portals (Madhya Pradesh: <division>divisionmp.nic.in, all 10 divisions; Chhattisgarh:
division-surguja.cg.gov.in, the only CG division with a portal on 2026-11-13: division-bastar / -raipur / -bilaspur / -durg
.cg.gov.in did not answer). Pages: "Who's Who" (/en/about-division/whos-who/ or /en/whos-who/), "Directory"
(/en/directory/, /en/contact-directory/) and "Contact Us" (/en/contact-us/). Each list is an S3WaaS table with a caption
(Division Office, Office Staff, Commissioner Office, District Magistrate and Collector ...), read with officials.tables();
a list with more than one page is paged with the site's own `ww_pages` / `dir_pages` call (the nonce the page carries), as
whoswho.py does. Checked: archive copies 2026-11-05/06 (saved from India) and live from dev-vps-3 2026-11-13 (Bhopal,
Gwalior, Surguja answer); abroad unchecked.

Records (_state.rec): level division (area = division, its LGD districts from dforms/st_div_<st>.json); a row that names a
Collector / District Magistrate of a district of the division gets level district and the district (LGD). post =
Designation, name = Name, phone, email (de-obfuscated), address, mobile / fax kept; every cell in "cells"; section = the
table caption. src_pos {"table", "row"} on the page, {"category", "paged", "item"} on pager answers (src_url = the ajax url).
Ids: dept:st_div_s3waas:<host>:<page slug>:<table>:<row> and dept:st_div_s3waas:<host>:<action>:<category>:<paged>:<item>.
One queue item = one portal (its 2-4 pages + pager calls).
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import officials
import provenance
from dforms import _esw, _state

METHOD = "html table (S3WaaS who's who / directory lists) + json api (ww_pages / dir_pages pager)"
MODULE = "st_div_s3waas"
HERE = Path(__file__).resolve().parent
MAX_AJAX = 40

COLLECTOR = re.compile(r"(?i)\b(collector|district magistrate|\bDM\b)")


def names(state):
    f = HERE / f"st_div_{state.lower()}.json"
    return json.loads(f.read_text()).get("district_names", {}) if f.exists() else {}


def nkey(s):
    return re.sub(r"[^a-z]", "", re.sub(r"\(.*?\)", "", (s or "").lower()))


def district_in(text, state, division):
    """(LGD code, LGD name) of a district of the division that the text names ("Collector Morena"); ("", "") if none."""
    _, codes = _state.districts_of(state, division)
    nm = names(state)
    t = nkey(text)
    for c in codes:
        n = nm.get(c, "")
        parts = [nkey(x) for x in re.split(r"[-()]", n) if nkey(x)]
        if any(p and len(p) >= 4 and p in t for p in parts):
            return c, n
    return "", ""


def cell(row, *keys):
    for k in row:
        if any(re.search(rx, k, re.I) for rx in keys):
            v = _esw.clean(row[k])
            if v:
                return v
    return ""


def rows_records(p, rows, caption, ids, poss, url, src):
    out = []
    st, div = p["state"], p["division"]
    for row, rid, pos in zip(rows, ids, poss):
        name = cell(row, r"^name$", r"^title$")
        post = cell(row, r"designation", r"^post$")
        if not (name or post):
            continue
        email = _esw.emails(" ".join(str(v) for k, v in row.items() if re.search(r"(?i)e-?mail", k)))
        phone = _esw.phones(*[str(v) for k, v in row.items() if re.search(r"(?i)phone|landline|contact|tel", k)])
        mobile = _esw.phones(*[str(v) for k, v in row.items() if re.search(r"(?i)mobile", k)])
        fax = cell(row, r"fax")
        level, kw = "division", {"division": div}
        if COLLECTOR.search(post + " " + name):
            code, en = district_in(name + " " + post, st, div)
            if code:
                level, kw = "district", {"division": div, "district": en, "district_code": code, "districts": [code]}
        if re.match(r"(?i)\W*(additional|addl|joint|jt|deputy|dy|assistant|asst)\b", post):
            pk = _state.post_kind(re.sub(r"(?i),?\s*\w+\s+division\W*$", "", post)) or None   # not the Commissioner himself
        elif re.fullmatch(r"(?i)\W*(divisional\s+)?commissioner\b.*", post) and level == "division":
            pk = "divisional_commissioner"
        else:
            pk = None
        out.append(_state.rec(
            MODULE, rid, state=st, level=level, post=post, post_kind=pk, name=name, body=f"Office of the Divisional Commissioner, {div}",
            body_kind="division", department="Revenue", dept="revenue" if level == "division" else "administration",
            phone=", ".join(x for x in (phone, mobile) if x), mobile=mobile or None, fax=fax or None, email=email,
            address=cell(row, r"address"), section=caption or None, host=p["host"], cells={k: v for k, v in row.items() if v},
            source=url, src_url=url, src_pos=pos, **{k: v for k, v in (src or {}).items() if k != "src_url"}, **kw))
    return out


def slug(url):
    return re.sub(r"[^a-z0-9]+", "-", urlparse(url).path.lower()).strip("-") or "home"


def parse_page(p, html, url, src=None):
    out = []
    for t in officials.tables(html):
        n = len(t.get("rows", []))
        poss = t.get("pos") or [{} for _ in range(n)]
        ids = [f"{p['host']}:{slug(url)}:{(ps or {}).get('table', 0)}:{(ps or {}).get('row', i + 1)}" for i, ps in enumerate(poss)]
        out += rows_records(p, t.get("rows", []), t.get("caption", ""), ids, poss, url, src)
    return out


def pager(p, html, url, get):
    out, calls = [], 0
    for kind in ("ww", "dir"):
        pg = officials.pager_blocks(html, kind)
        if not pg:
            continue
        for b in pg["blocks"]:
            k = 1
            while k < b["pages"] and calls < MAX_AJAX:
                r = get(pg["ajaxurl"], "POST", {"action": pg["action"], "paged": k, "tax_slug": b["slug"], "type": "next",
                                                "profile_image": pg["profile"], "filter": pg["filter"], "security": pg["nonce"]})
                calls += 1
                if r is None:
                    break
                rows = officials.ajax_rows(r.text)
                if not rows:
                    break
                ids = [f"{p['host']}:{pg['action']}:{b['slug']}:{k}:{i}" for i in range(1, len(rows) + 1)]
                poss = [{"category": b["slug"], "paged": k, "item": i} for i in range(1, len(rows) + 1)]
                out += rows_records(p, rows, b["name"], ids, poss, pg["ajaxurl"], provenance.at(r, pg["ajaxurl"]))
                try:
                    if str(json.loads(r.text).get("last")) == "1":
                        break
                except ValueError:
                    break
                k += 1
    return out


def fetch(p, get):
    recs, files, seen = [], [], set()
    for url in p["urls"]:
        r = get(url)
        if r is None or getattr(r, "status_code", 200) >= 400:
            continue
        html = r.text
        files.append(_esw.keep(MODULE, f"{p['host']}/{slug(url)}", r.content))
        for rid, d in parse_page(p, html, url) + pager(p, html, url, get):
            if rid not in seen:
                seen.add(rid)
                recs.append((rid, d))
    return recs, files, "" if recs else "no rows"
