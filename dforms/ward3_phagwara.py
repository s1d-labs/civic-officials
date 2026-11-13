"""Municipal Corporation Phagwara (mcphagwara.punjab.gov.in, Punjab e-Nigam MC site, mcid=1009): its officers by branch, from the
PDF "MC Officials" (menu link on the home page; e-Nigam Azure store; "Officers as on 21-09-2026", 3 pages; live sample
2026-11-13, answers from abroad).
Rows: Sr. No. | Name | Designation | Mobile No. | Remarks ("Addl. Charge Ludhiana (Monday, Tuesday & Wednesday)"), under
centred branch headings (Account Branch, Building Branch, Engineering Branch, Sanitation Branch, Punjab Water Supply & Sewage
Board ...). A designation that wraps ("Senior Assistant-cum-" / "Inspector", "(Handicaped)") is joined; other lines without a
serial number are headings. The elected Mayor, Senior Deputy Mayor and Deputy Mayor (first table) are left out (councillor
data). The list names no wards or zones: records are at level "body" (section = the heading).
Record ids: dept:ward3_phagwara:<section slug>:<post slug>:<mobile or name slug>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward3_northb as h

METHOD = "pdf text (pypdf layout) rows under headings"     # source trail (provenance.py)

MODULE = "ward3_phagwara"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Phagwara", "248286", "PB", "Kapurthala"
HOME = "https://mcphagwara.punjab.gov.in/Home"
PDF = ("https://enigambackuprestore.blob.core.windows.net/securefilestructure/MC/Phagwara/MCSubMenu/pdf/"
       "linkpdf_9_21_2026_7_433.MC%20Staff%2021-09-26.pdf")
LINK = re.compile(r"(?i)mc\s*officials|staff")
PHONE = re.compile(r"^(?:[6-9]\d{4}[\s-]?\d{5}|0\d{2,4}[\s-]?\d{6,8}|-{2,})$")
ELECTED = re.compile(r"(?i)^(mayor|senior\s+deputy\s+mayor|deputy\s+mayor)$")


def items(get=None):
    return [{"key": f"{MODULE}-officials", "payload": {"reader": MODULE, "url": HOME, "pdf": PDF, "state": STATE}}]


REMARK_X = 70     # Remarks column (layout text column); headings are centred left of it


def joins(prev, nxt):
    """True when the remark line nxt continues the remark prev of the row above (else it belongs to the next row)."""
    return bool(prev) and (nxt[:1] in "(&" or prev.endswith(("&", "Charge", "-")) or prev.count("(") > prev.count(")"))


def table(pages):
    out, section, cur, pending = [], None, None, []
    for pn, pg in enumerate(pages, 1):
        for ln, raw in enumerate(h.lines_of(pg), 1):
            if not raw.strip() or re.search(r"(?i)sr\.?\s*no\.?\s+name", raw):
                continue
            runs = [(m.start(), _esw.clean(m.group(0))) for m in re.finditer(r"\S+(?:\s{1,2}\S+)*", raw)]
            if re.fullmatch(r"\d{1,3}", runs[0][1]) and len(runs) >= 3:
                sr = runs[0][1]
                cells = [t for _, t in runs[1:]]
                ph_i = next((i for i, t in enumerate(cells) if PHONE.match(t)), None)
                if ph_i is None or ph_i < 2:
                    name, post = cells[0], " ".join(cells[1:2])
                    phone, remark = "", " ".join(cells[2:])
                else:
                    name, post = cells[0], " ".join(cells[1:ph_i])
                    phone, remark = cells[ph_i], " ".join(cells[ph_i + 1:])
                cur = {"sr": sr, "name": name, "post": post, "phone": "" if phone.startswith("-") else phone,
                       "remark": pending + [remark],
                       "section": section, "page": pn, "line": ln, "line_text": raw, "x_post": runs[2][0] if len(runs) > 2 else 0}
                out.append(cur)
                pending = []
                continue
            if len(runs) == 1:
                x, t = runs[0]
                if x >= REMARK_X:            # a remark line: the rest of the row above, or the start of the next row's
                    last = _esw.clean(" ".join(cur["remark"])) if cur is not None else ""
                    if cur is not None and not pending and joins(last, t):
                        cur["remark"].append(t)
                    else:
                        pending.append(t)
                    continue
                if cur is not None and abs(x - cur["x_post"]) <= 2 and (cur["post"].endswith("-") or t.startswith("(")):
                    cur["post"] = _esw.clean(cur["post"] + ("" if cur["post"].endswith("-") else " ") + t)
                    continue
                section = re.sub(r"(?i)^municipal corporation phagwara'?s?\s*", "", t)
                cur = None
    for r in out:
        r["remark"] = _esw.clean(" ".join(x for x in r["remark"] if x))
    return out


def parse(pages, p):
    seen, recs = set(), []
    for r in table(pages):
        if not r["post"] or ELECTED.match(r["post"]):
            continue
        sec = r["section"] or ""
        key = f"{_esw.slug(sec)[:40] or 'officers'}:{_esw.slug(r['post'])[:40]}:{re.sub(r'[^0-9]', '', r['phone']) or _esw.slug(r['name'])}"
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="body", area=BODY,
                                 post=r["post"], name=r["name"], phone=r["phone"], section=sec or None, note=r["remark"] or None,
                                 source=p.get("pdf") or PDF,
                                 src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"], row=int(r["sr"]))))
    return recs


def fetch(p, get):
    url = p.get("pdf") or PDF
    home = get(p["url"]) if p.get("url") else None
    if home is not None:
        for a in _esw.soup(home.text).find_all("a", href=True):
            if LINK.search(a.get_text(" ")) and a["href"].lower().endswith(".pdf"):
                url = a["href"].replace(" ", "%20")
                break
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "officials", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, dict(p, pdf=url))
    return _ward.tag(recs, r, url, METHOD), files, "" if recs else "no rows"
