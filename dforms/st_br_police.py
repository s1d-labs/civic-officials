"""Bihar Police: contact lists of the new police.bihar.gov.in (React page; the data comes from the site's own open JSON handlers,
the same calls the public "Contact" pages make; no key, no token):
- PhqContactHandler.ashx?page=N&pageSize=20: Police Headquarters posts (DGP, ADGs, IGs, DIGs, AIGs of each PHQ division):
  {"totalRecords": 131, "totalPages": 7, "data": [{"sno", "rank" (the post), "designation" (the PHQ division), "mobile",
  "std_code", "office_no", "email", "full_office_number"}]}. Level state.
- FieldOfficerHandler.ashx?action=getall&lang=en&page=N&pageSize=20: field posts by range: {"totalRecords": 76, "data":
  [{"sl_no", "range" ("Central Range Patna"), "designation" ("IG Central Range, Patna", "SSP, Patna", "City SP (East) Patna"),
  "std_code", "office_no", "residence", "fax", "mobile", "email"}]}. IG / DIG of a range -> level division (the range); SSP / SP
  of a district -> level district (LGD district from the post); others -> division.
The lists name posts, not persons (no names). One item = one handler, all its pages (7 + 4 GETs, 2 s apart). Each answer is
kept in the bucket. Record id dept:st_br_police:<phq|field>:<sno>. src_pos {"index", "id", "page"}; src_url = the page's url.
Route: answers from Mumbai (direct); abroad unchecked.
"""
import json
import time

from dforms import _esw, _state, st_lgd_upbrjh as lgd

METHOD = "json api (site's own handler)"
MODULE = "st_br_police"
URLS = {"phq": "https://police.bihar.gov.in/PhqContactHandler.ashx?page={}&pageSize=20",
        "field": "https://police.bihar.gov.in/FieldOfficerHandler.ashx?action=getall&lang=en&page={}&pageSize=20"}


def std(code, nums):
    code = (code or "").strip()
    if code and not code.startswith("0"):
        code = "0" + code
    out = []
    for x in (nums or "").split("/"):
        x = x.strip()
        if not x or x == code:
            continue
        out.append(f"{code}-{x}" if code and x[:1].isdigit() and not x.startswith("0") and len(x) <= 8 else x)
    return " / ".join(out)


def parse(doc, url, which, page=1):
    out = []
    for i, d in enumerate(doc.get("data") or [], 1):
        sno = str(d.get("sno") or d.get("sl_no") or f"{page}-{i}")
        office = std(d.get("std_code"), d.get("office_no"))
        parts = [office, _esw.clean(d.get("mobile"))]
        if (d.get("residence") or "").strip():
            parts.append(std(d.get("std_code"), d["residence"]) + " (residence)")
        if (d.get("fax") or "").strip():
            parts.append(std(d.get("std_code"), d["fax"]) + " (fax)")
        phone = ", ".join(x for x in parts if x and x != " (residence)" and x != " (fax)")
        pos = {"index": i, "id": sno, "page": page}
        if which == "phq":
            post, group = _esw.clean(d.get("rank")), _esw.clean(d.get("designation"))
            out.append(_state.rec(MODULE, f"phq:{sno}", state="BR", level="state", post=post, dept="police",
                                  body=f"Bihar Police Headquarters: {group}" if group else "Bihar Police Headquarters",
                                  body_kind="police", department="Home Department", section=group, phone=phone,
                                  email=_esw.emails(d.get("email")), raw=d, source=url, src_url=url, src_pos=pos))
        else:
            post, rng = _esw.clean(d.get("designation")), _esw.clean(d.get("range"))
            p = post.lower().replace(".", "")
            code, name = lgd.district("BR", post)
            if code and any(w in p.split() or w + "," in p for w in ("ssp", "sp", "srp")) and "range" not in p:
                level, div = "district", ""
            else:
                level, div, code, name = "division", rng, "", ""
            out.append(_state.rec(MODULE, f"field:{sno}", state="BR", level=level, post=post, dept="police",
                                  body=f"Bihar Police: {rng}" if rng else "Bihar Police", body_kind="police",
                                  department="Home Department", division=div, districts=[] if level == "division" else None,
                                  district=name, district_code=code, police_range=rng or None, phone=phone,
                                  email=_esw.emails(d.get("email")), raw=d, source=url, src_url=url, src_pos=pos))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": u.format(1), "which": k, "state": "BR",
                                                 "india_only": True, "route": "direct"}} for k, u in URLS.items()]


def fetch(p, get):
    recs, files, page, pages = [], [], 1, 1
    while page <= pages and page <= 50:
        url = URLS[p["which"]].format(page)
        r = get(url)
        if r is None:
            return recs, files, "" if recs else "no answer"
        try:
            doc = json.loads(r.content)
        except ValueError:
            return recs, files, "" if recs else "not json"
        files.append(_esw.keep(MODULE, f"{p['which']}-p{page}", r.content, "json"))
        tp = doc.get("totalPages")
        pages = int(tp) if str(tp).isdigit() else 1
        recs += parse(doc, url, p["which"], page)
        page += 1
        if page <= pages:
            time.sleep(2)
    return recs, files, "" if recs else "no rows"
