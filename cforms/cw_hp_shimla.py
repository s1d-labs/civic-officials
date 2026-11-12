"""Himachal Pradesh: Municipal Corporation Shimla, councillors as the corporation lists them (shimlamc.hp.gov.in/Members/Index,
e-Nigam template by NIC). The SEC list (cforms/hp.py) has no rows for MC Shimla (elected May 2023, 34 wards).
One table: Photo | Name | Ward Name | Ward No. | Local Address | Permanent Address | Email ID | Contact No. Ward 35 "Common"
= nominated councillors; "Mayor MC Shimla" in the address cells marks the mayor. The list is kept by hand on the site and
some wards carry more than one name (older entries, a test row "Test User"): every row is kept except the test row, and a
ward with more than one name gets "ward_rows" (the number of names the site gives for it), so the loader can tell.
Checked 2026-11-12: 41 rows (40 kept), 30 of the 34 wards (11, 21, 24, 28 not listed), 4 nominated. Answers from outside India
(unchecked). One queue item: payload {"kind": "form-cw_hp_shimla", "state": "HP", "url"}.
Record id councillor:HP:shimla-mc:<ward>-<n> (nominated-<n> for ward 35)."""
import gzip
import re

from cforms import cp_common as cp

BODY, LGD = "Shimla Municipal Corporation", "248248"


def parse(html, url):
    rows = []
    for head, cells in cp.table_rows(html):
        if not head:
            continue
        ni, wi, wn = cp.column(head, r"^name"), cp.column(head, r"ward no"), cp.column(head, r"ward name")
        li, pa = cp.column(head, r"local address"), cp.column(head, r"permanent address")
        ei, pi = cp.column(head, r"e-?mail"), cp.column(head, r"contact")
        if ni is None or wi is None or ni >= len(cells):
            continue
        at = lambda i: cells[i] if i is not None and i < len(cells) else ""
        name = at(ni)
        if not name or re.search(r"\btest user\b", name, re.I):
            continue
        ward = re.sub(r"\D", "", at(wi)) or None
        addr = " / ".join(dict.fromkeys(x for x in (at(li), at(pa)) if x))
        nominated = at(wn).lower() == "common" or "nominated" in addr.lower()
        post = "Mayor" if re.search(r"\bmayor\b", addr, re.I) and not re.search(r"deputy", addr, re.I) else \
            "Deputy Mayor" if re.search(r"deputy mayor", addr, re.I) else "Nominated Councillor" if nominated else "Councillor"
        rows.append({"type": "councillor", "state": "HP", "body": BODY, "lgd_code": LGD, "ward_no": None if nominated else ward,
                     "ward_name": None if nominated else at(wn), "name": name, "position": post,
                     "address": None if re.fullmatch(r"(?i)(ward no\.? ?\d+|mc shimla|(deputy )?mayor mc shimla)", addr) else addr,
                     "email": cp.emails(at(ei)), "phone": cp.phones(at(pi)), "nominated": nominated or None,
                     "election": "MC Shimla 2023 (as listed on the corporation's site)", "url": url})
    per = {}
    for d in rows:
        if d["ward_no"]:
            per[d["ward_no"]] = per.get(d["ward_no"], 0) + 1
    out, seen = [], {}
    for d in rows:
        if d["ward_no"] and per[d["ward_no"]] > 1:
            d["ward_rows"] = per[d["ward_no"]]
        k = d["ward_no"] or "nominated"
        seen[k] = seen.get(k, 0) + 1
        out.append((f"councillor:HP:shimla-mc:{k}-{seen[k]}", {x: v for x, v in d.items() if v not in (None, "")}))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [("councillors/HP/shimla-mc-members.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no member table"
