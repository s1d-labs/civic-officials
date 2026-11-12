"""Bihar: chief councillors (मुख्य पार्षद: mayor of a nagar nigam, chairperson of a nagar parishad / nagar panchayat) and deputy
chief councillors (उप मुख्य पार्षद), directly elected since 2022, from the same State Election Commission result pages as the
ward councillors (cforms/br.py: sec.bihar.gov.in/ForPublic/ResultP1/P2/P3/P4/Result2025.aspx, India only, no captcha).
The form is the same with ddl_Post = 1 (मुख्य पार्षद) or 2 (उप मुख्य पार्षद); the body has no ward list, so "Show" lists the
candidates of the post with their votes, the winner marked "(विजेता)".
One queue item = one body (the payload of the br.py item, kind "form-br_head"); a later page (by-election) replaces the winner of
an earlier one. Record id councillor:BR:<slug>:chair (chief councillor) or :vice (deputy).
"""
import gzip
import html as htmlmod

import provenance
from cforms.br import BASE, COUNTING, WIN, ZW, _label, _post, _result, _votes, winner
from forms.aspnet import options

METHOD = "html table (ASP.NET result page, one POST per post)"
POSTS = {"1": ("chair", "मुख्य पार्षद"), "2": ("vice", "उप मुख्य पार्षद")}


def position(key, body_type_value):
    if body_type_value == "1":
        return "Mayor" if key == "chair" else "Deputy Mayor"
    return "Chairperson" if key == "chair" else "Vice Chairperson"


def head_form(get, page, p, post):
    """The page after posting post, district, type and body; None + why when the body is not on this page."""
    url = BASE + page + ".aspx"
    r = get(url)
    if r is None:
        return None, "no answer"
    f = {"ddl_Post": post}
    h = _post(get, url, r.text, "ddl_Post", f)
    f["ddlDistrict"] = p["district_value"]
    h = h and _post(get, url, h, "ddlDistrict", f)
    f["ddlNPType"] = p["type"]
    h = h and _post(get, url, h, "ddlNPType", f)
    if h and p["body_value"] not in [v for v, _ in options(h, "ddlPanchayat")]:
        return None, f"body {p['body_value']} not on {page} for post {post}"
    f["ddlPanchayat"] = p["body_value"]
    h = h and _post(get, url, h, "ddlPanchayat", f)
    return (h, f) if h else (None, "postback did not answer")


def head_record(rows, p, key, page, url, label, resp=None):
    c, how = winner(rows)
    if c is None:
        return None
    others = sorted((_votes(x.get("कुल प्राप्त मत")) or 0 for x in rows if x is not c), reverse=True)
    votes = _votes(c.get("कुल प्राप्त मत"))
    d = {"type": "councillor", "state": "BR", "body": c.get("नगर निकाय") or p.get("body"), "body_type": p.get("body_type"),
         "district": c.get("जिला") or p.get("district"), "subdivision": c.get("अनुमंडल"), "post": c.get("पद"),
         "position": position(key, p.get("type")), "ward_no": key,
         "name": " ".join(ZW.sub("", WIN.sub(" ", c.get("प्रत्याशी का नाम", ""))).split()), "votes": votes,
         "candidates": len(rows), "margin": votes - others[0] if votes is not None and others else None,
         "winner_by": how if how != "marked" else None, "election": label, "url": url, "result_page": page,
         "body_value": p["body_value"], **(provenance.at(resp, url) if resp is not None else {}),
         "src_pos": {"table_id": "ctl00_ContentPlaceHolder1_RPDetails",
                     "row": next(i for i, x in enumerate(rows) if x is c) + 2, "post_posted": c.get("पद")}}
    return {k: v for k, v in d.items() if v not in (None, "")}


def fetch(p, get):
    sl = p["slug"]
    won, files, why = {}, [], []
    for page in p["pages"]:
        url = BASE + page + ".aspx"
        saved = []
        for post, (key, _) in POSTS.items():
            h, f = head_form(get, page, p, post)
            if h is None:
                why.append(f"{page}/{post}: {f}")
                continue
            label = _label(h)
            r, resp = _post(get, url, h, "", f, resp=True)
            if r is None:
                why.append(f"{page}/{post}: no answer")
                continue
            msg, rows, table = _result(r)
            saved.append(f"<section data-post=\"{post}\"><p>{htmlmod.escape(msg)}</p>{table}</section>")
            if COUNTING in msg and not rows:
                continue
            d = head_record(rows, p, key, page, url, label, resp)
            if d:
                won[key] = d
        if saved:
            doc = f"<html><head><meta charset=\"utf-8\"></head><body>{''.join(saved)}</body></html>"
            files.append((f"councillors/BR/{page}-{p['body_value']}-{sl}-heads.html.gz", gzip.compress(doc.encode()),
                          "application/gzip"))
    recs = [(f"councillor:BR:{sl}:{k}", d) for k, d in won.items()]
    return recs, files, "" if recs else ("; ".join(why) or "no winners")


def seed_items(br_items):
    """The br.py body items as head items (same payload, kind form-br_head)."""
    return [{"key": "brh-" + it["key"].split("-", 1)[1], "payload": {**it["payload"], "kind": "form-br_head"}} for it in br_items]
