"""Uttarakhand: the Block Development Officer of every development block (95 in LGD), with mobile, landline and email, from the
Directory of the Rural Development Department, ukrd.uk.gov.in/directory/ (S3WaaS, NIC cloud; answers from Germany too).

Structure: one page (about 170 KB) with the S3WaaS "tabular content" layout (div.s3waas-tabular-container data-content-type
"directory"): 16 sections (div.taxonomy-section, data-params = base64 {"term_id": N}), one per office: the Secretariat, the
Commissioner (Pauri), the 13 districts ("District Almora" ... "District Udham Singh Nagar") and the State Level Cell. Each section is
a table Name | Designation | Email | Mobile | Landline No | Address, 12 rows per page. A district table lists the CDO, PD DRDA, DDO,
APD, the ETC Acharya and then one row per block: "Block Development Officer" / "Incharge Block Development Officer" / "Add. Charge
Block Development Officer", address "Block Development Office, Hawalbagh" / "Development Block Raipur" / "Purola Block,".
Five districts have a second page (Almora, Chamoli, Nainital, Pauri Garhwal, Pithoragarh: about 15 more blocks). The page's own
pager (mu-plugins/shortcodes/assets/js/tabular_content.js) asks admin-ajax.php with action "directory_paginate", termParams (the
section's data-params), params (the container's data-params, with a WordPress nonce) and pageno; the answer is JSON
{"success": true, "data": {"content": "<tbody>...</tbody>", "pagination": ...}}. WP-Super-Cache serves the page for days, so its
nonce can be stale ({"success": false, "data": ["Invalid Nonce"]}): then the reader asks the page once more with a query string
(not cached) and repeats the call with the new nonce. If the pager still refuses, the first page of each section is kept.

One queue item: 1 GET + 5 POSTs (+ 1 GET and 5 POSTs again when the nonce is stale). Rows kept: the Block Development Officers
(dept rural_development, level block). Area = the block in the address ("Nandanagar (Ghat)" -> Ghat, the name in brackets is the
LGD block; the outer name goes to "area_local"). Districts are written as LGD writes them. Phones: mobile and landline as written
(a few mobiles on the page have 9 digits; they are kept as written). The page shows no date.
Record ids: dept:sub2_uk:UK-<district slug>:<block slug>[:n].

tabular_sections() / paginate() read any S3WaaS "tabular content" directory page and can be imported by other readers.
"""
import base64
import json
import re
import time

import provenance
from dforms import _esw

METHOD = "html table (S3WaaS tabular directory) + json api (directory_paginate pages)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "sub2_uk"
URL = "https://ukrd.uk.gov.in/directory/"
LGD = ["Almora", "Bageshwar", "Chamoli", "Champawat", "Dehradun", "Haridwar", "Nainital", "Pauri Garhwal", "Pithoragarh", "Rudraprayag",
       "Tehri Garhwal", "Udham Singh Nagar", "Uttarkashi"]
_LGD = {re.sub(r"[^a-z]", "", d.lower()): d for d in LGD}
BDO = re.compile(r"block\s+development\s+officer|\bB\.?\s?D\.?\s?O\b", re.I)


def items(get=None):
    return [{"key": MODULE, "payload": {"reader": MODULE, "url": URL, "state": "UK", "expected": 95}}]


def _b64json(s):
    try:
        return json.loads(base64.b64decode(s + "=" * (-len(s) % 4)).decode())
    except (ValueError, UnicodeDecodeError):
        return {}


def ajax_url(html):
    m = re.search(r'AwaasData\s*=\s*\{[^}]*"ajaxUrl"\s*:\s*"([^"]+)"', html)
    return m.group(1).replace("\\/", "/") if m else ""


def _rows(table, where=None):
    tp = []
    out = [(r, p) for r, p in zip(_esw.grid(table, pos=tp), tp) if not (r and r[0].strip().lower() == "name")]
    if where is not None:
        where.extend(p for _, p in out)
    return [r for r, _ in out]


def tabular_sections(html):
    """(container params (base64 string, as the page has it), [{"caption", "term_params", "term_id", "rows", "pages"}]) of an S3WaaS
    tabular directory page; rows are lists of cell texts (header row left out); pages = the highest page number in the pager."""
    soup = _esw.soup(html)
    box = soup.select_one("div.s3waas-tabular-content[data-params]")
    params = box.get("data-params", "") if box else ""
    out = []
    for sec in soup.select("div.taxonomy-section"):
        t = sec.find("table")
        if t is None:
            continue
        cap = t.find("caption")
        tp = sec.get("data-params", "")
        pages = [int(a["data-page-id"]) for a in sec.select("[data-page-id]") if str(a.get("data-page-id", "")).isdigit()]
        pos = []
        out.append({"caption": _esw.clean(cap.get_text(" ")) if cap else "", "term_params": tp, "term_id": _b64json(tp).get("term_id"),
                    "rows": _rows(t, pos), "pages": max(pages or [1]), "pos": pos})
    return params, out


def answer_rows(text, where=None):
    """Rows of one "directory_paginate" answer ([] when the answer is not a success)."""
    try:
        obj = json.loads(text)
    except ValueError:
        return []
    if not obj.get("success") or not isinstance(obj.get("data"), dict):
        return []
    content = obj["data"].get("content") or ""
    return _rows(_esw.soup(f"<table>{content}</table>").find("table"), where)


def stale(text):
    return "invalid nonce" in (text or "").lower()


def paginate(get, ajax, params, section, files, module=MODULE, tag="", where=None):
    """where: a list; when given, it gets (src_pos, provenance.at(answer)) for each row returned."""
    """The further pages of one section: (rows, stale nonce?). Each answer is kept in files."""
    rows = []
    for n in range(2, section["pages"] + 1):
        r = get(ajax, method="POST", data={"termParams": section["term_params"], "params": params, "pageno": n,
                                           "action": "directory_paginate"})
        if r is None:
            break
        files.append(_esw.keep(module, f"{tag}term-{section['term_id']}-p{n}", r.content, "json"))
        if stale(r.text):
            return rows, True
        pos = []
        got = answer_rows(r.text, pos)
        if not got:
            break
        rows += got
        if where is not None:
            src = provenance.at(r, ajax)
            where += [({"action": "directory_paginate", "term_id": section["term_id"], "pageno": n, "field": "data.content", **q}, src)
                      for q in pos]
    return rows, False


def district(caption):
    s = re.sub(r"(?i)^\s*district\s+", "", caption or "")
    return _LGD.get(re.sub(r"[^a-z]", "", s.lower()), s.strip().title())


AREA_STRIP = re.compile(r"(?i)\b(block\s+development\s+(office(r)?)?|block\s+dev\.?\s+office|development\s+block(\s+office)?|"
                        r"office|block|vikas\s*khand)\b")


def area_of(address, email=""):
    """("Ghat", "Nandanagar") from "Block Development office Nandanagar (Ghat)"; ("Hawalbagh", "") from "Block Development Office,
    Hawalbagh"; "Block Development officeTharali" -> Tharali."""
    s = re.sub(r"((?i:office|officer))(?=[A-Z])", r"\1 ", address or "")
    s = AREA_STRIP.sub(" ", s)
    s = _esw.clean(s).strip(" ,.-")
    m = re.match(r"^(.*?)\s*\(\s*([^)]+?)\s*\)\s*$", s)
    if m:
        return m.group(2).strip(" ,.-"), m.group(1).strip(" ,.-")
    return s, ""


def _person(name):
    n = _esw.clean(name).strip(" ,.")
    return "" if not re.search(r"[A-Za-z]{2}", n) or re.fullmatch(r"(?i)(vacant|n/?a|-+)", n) else n


def build(rows, dist, source, seen, where=None):
    """where: (src_pos, src) per row of rows."""
    recs = []
    for r, (pos, src) in zip(rows, where or [(None, {})] * len(rows)):
        if len(r) < 3 or not BDO.search(r[1]):
            provenance.skip_row(r, 'skip: len(r) < 3 or not BDO.search(r[1])')
            continue
        name, post, address = _person(r[0]), _esw.clean(r[1]).strip(" ,."), r[-1]
        mail_cells = [c for c in r[2:-1] if "[at]" in c.lower() or "@" in c]
        email = _esw.emails(" ".join(mail_cells))
        phone = _esw.phones(*[c for c in r[2:-1] if c not in mail_cells])
        area, local = area_of(address)
        if not area:
            provenance.skip_row(r, 'skip: not area')
            continue
        base = f"UK-{_esw.slug(dist)}:{_esw.slug(area)}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="rural_development", level="block", area=area, area_local=local, post=post,
                                name=name, phone=phone, email=email, address=address, district=dist, state="UK", source=source,
                                src_pos=pos, **(src or {})))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "directory", r.content)]
    params, sections = tabular_sections(r.text)
    ajax = ajax_url(r.text) or url.split("/directory")[0] + "/wp-admin/admin-ajax.php"
    extra, fresh, extra_at = {}, None, {}
    for s in sections:
        if s["pages"] < 2:
            continue
        at = []
        more, old = paginate(get, ajax, params, s, files, where=at)
        if old and fresh is None:        # the cached page's nonce is stale: ask the page once without the cache
            f = get(f"{url}?nc={int(time.time())}")
            fresh = tabular_sections(f.text)[0] if f is not None else ""
            if f is not None:
                files.append(_esw.keep(MODULE, "directory-fresh", f.content))
        if old and fresh:
            at = []
            more, _ = paginate(get, ajax, fresh, s, files, tag="fresh-", where=at)
        extra[s["term_id"]] = more
        extra_at[s["term_id"]] = at[:len(more)]
    recs, seen = [], set()
    for s in sections:
        if not s["caption"].lower().startswith("district"):
            continue
        page = provenance.at(r, url)
        where = [(q, page) for q in s.get("pos", [])] + extra_at.get(s["term_id"], [])
        rows = s["rows"] + extra.get(s["term_id"], [])
        recs += build(rows, district(s["caption"]), url, seen, where + [(None, {})] * (len(rows) - len(where)))
    return recs, files, "" if recs else "no rows"
