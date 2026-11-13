"""Bihar: the Chief Minister's Secretariat lists of divisional commissioners and district magistrates (cmo.bihar.gov.in).

Files (text PDFs, 1 page each, checked 2026-11-13 from dev-vps-3, Mumbai; archive copies 2026-11-05/06):
- pdf/commissioner.pdf (9 KB): "List of Divisional Commissioner": SN | Commissionery | Mobile | Email-Id. 9 rows (no names:
  the post, its CUG mobile and e-mail). Level division; districts from dforms/st_div_br.json.
- pdf/dm.pdf (113 KB): SL. | District | E-Mail ID | Mobile | Short Code. 38 rows (no names). Level district (LGD district).
Some names wrap over two lines ("Bhagalpur" / "Commissionary", "Bettiah(West" / "Champaran)"): a text-only line joins the row
above, or the row below when it opens a bracket it does not close.
Record id dept:st_br_cmo:<commissioner|dm>:<SN>. src_pos = provenance.line_pos-style {"page", "line", "line_text"} of the
numbered line. One item = one PDF (one GET); the PDF is kept in the bucket. Route: abroad unchecked; answers from Mumbai (direct).
"""
import re

from dforms import _esw, _field, _state, st_lgd_upbrjh as lgd

METHOD = "pdf text (pdftotext -layout, else pypdf layout)"
MODULE = "st_br_cmo"
FILES = {"commissioner": "https://cmo.bihar.gov.in/pdf/commissioner.pdf", "dm": "https://cmo.bihar.gov.in/pdf/dm.pdf"}
DIVS = {"bhagalpur": "Bhagalpur", "darbhanga": "Darbhanga", "kosi": "Kosi", "koshi": "Kosi", "magadh": "Magadh", "munger": "Munger",
        "patna": "Patna", "purnia": "Purnia", "purnea": "Purnia", "saran": "Saran", "tirhut": "Tirhut"}


def rows_of(text):
    rows, pre = [], ""
    for pg, ptext in enumerate(text.split("\f"), 1):
        for n, raw in enumerate(ptext.split("\n"), 1):
            t = raw.strip()
            if not t:
                continue
            m = re.match(r"^(\d{1,2})\s{2,}(.*)$", t)
            if m and re.search(r"@|\d{10}", t):
                body = m.group(2)
                email = _esw.emails(body)
                nums = re.findall(r"(?<!\d)\d{5,10}(?!\d)", re.sub(r"\S+@\S+", " ", body))
                label = _esw.clean(re.sub(r"\S+@\S+|(?<!\d)\d{5,10}(?!\d)", " ", body))
                rows.append({"sn": m.group(1), "label": _esw.clean(f"{pre} {label}"), "email": email,
                             "mobile": next((x for x in nums if len(x) == 10), ""),
                             "short_code": next((x for x in nums if len(x) == 5), ""),
                             "pos": {"page": pg, "line": n, "line_text": raw}})
                pre = ""
            elif rows is not None and not re.search(r"\d|@", t) and not re.search(r"(?i)^(sn|sl|list of)", t):
                if t.count("(") > t.count(")"):
                    pre = t
                elif rows:
                    rows[-1]["label"] = _esw.clean(rows[-1]["label"] + " " + t)
    return rows


def parse(text, url, which):
    out = []
    for r in rows_of(text):
        phone = r["mobile"]
        if which == "commissioner":
            k = re.sub(r"[^a-z]", " ", r["label"].lower()).split()
            div = next((DIVS[w] for w in k if w in DIVS), r["label"])
            out.append(_state.rec(MODULE, f"commissioner:{r['sn']}", state="BR", level="division", post="Divisional Commissioner",
                                  body=f"Office of the Divisional Commissioner, {div}", body_kind="division",
                                  department="General Administration Department", dept="revenue", division=div, phone=phone,
                                  email=r["email"], label=r["label"], source=url, src_url=url, src_pos=r["pos"]))
        else:
            code, name = lgd.district("BR", r["label"])
            out.append(_state.rec(MODULE, f"dm:{r['sn']}", state="BR", level="district", post="District Magistrate",
                                  body=f"Collectorate, {name or r['label']}", body_kind="other", dept="administration",
                                  department="General Administration Department", district=name or r["label"],
                                  district_code=code, phone=phone, email=r["email"], short_code=r["short_code"] or None,
                                  label=r["label"], source=url, src_url=url, src_pos=r["pos"]))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "url": u, "which": k, "state": "BR", "india_only": True,
                                                 "route": "direct"}} for k, u in FILES.items()]


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    recs = parse(_field.pdf_text(r.content), p["url"], p["which"])
    return recs, [(f"depts/{MODULE}/{p['which']}.pdf", r.content, "application/pdf")], "" if recs else "no rows"
