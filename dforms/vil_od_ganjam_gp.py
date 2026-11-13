"""Odisha, Ganjam district: the Panchayat Executive Officer (PEO, the gram panchayat's secretary) of every gram panchayat with his
mobile, and on the same row the Sarpanch, the Panchayat Samiti member and (some blocks) the Zilla Parishad member with theirs,
from the district portal's "Gram Panchayat Directory" (ganjam.odisha.gov.in/or/gram-panchayat-directory, 3 listing pages,
22 rows = 22 blocks; checked 2026-11-13 from dev-vps-3, Mumbai). No other Odisha district portal had this page on 2026-11-13
(khordha, mayurbhanj, koraput: page without rows; cuttack, balasore, sundargarh: no answer from Mumbai).

A block row links either a detail page (15 blocks, e.g. /or/gram-panchayat-directory/buguda: HTML tables "SL NO. | GRAM
PANCHAYAT | PEO NAME | NUMBER | SARPANCH | NUMBER | PANCHAYAT SAMITI MEMBER | NUMBER" and a ZP table "SL NO. | ZP MEMBER NAME |
NUMBER") or a PDF printed from Excel (7 blocks, 2023-06 / 2025-04: "Name of the G.P | Name of the PEO | Mobile No. | Name of the
Sarapancha | Mobile No. | Name of the PS Member | Mobile No. | Name of the Z.P Member | Zone No | Mobile No.").
HTML: column roles from the header words; each NUMBER column belongs to the name column on its left. PDF (pdftotext -layout,
else pypdf layout): a line that starts with a serial number and has letters; cells as in dforms/vil_br_prd.cells_of (2+ space
gaps, phone numbers cut out); the first text cell is the GP, then name + phone per post in the header's order. Second lines of a
row (a second phone, "(Chairman)") are not read; the raw line is kept.

Records: PEO -> dept rural_development, level gram_panchayat, post "Panchayat Executive Officer", kind official; Sarpanch,
Panchayat Samiti member, ZP member -> kind elected (level gram_panchayat / gram_panchayat / zp_zone). area = the GP as written,
block = the block (payload, English), district Ganjam. src_pos: HTML {table, row}; PDF page + line.
One queue item = one block (1 GET). Ids: dept:vil_od_ganjam_gp:<block slug>:<t<table>-r<row> | p<page>-l<line>>:<post key>.
"""
import re

from dforms import _esw, _field
from dforms.vil_br_prd import cells_of
import provenance

METHOD = "html table (header words -> columns), or pdf text (pdftotext -layout, else pypdf layout) cells in header order"

MODULE = "vil_od_ganjam_gp"
POSTS = {"peo": ("Panchayat Executive Officer", "official", "gram_panchayat"),
         "sarpanch": ("Sarpanch", "elected", "gram_panchayat"),
         "ps": ("Panchayat Samiti Member", "elected", "gram_panchayat"),
         "zp": ("Zilla Parishad Member", "elected", "zp_zone")}
ROLE_WORDS = [("zp", r"\bz\.?\s*p\b|zilla"), ("ps", r"samiti|\bp\.?\s*s\b\.?"),
              ("sarpanch", r"sar[a]?panch"), ("peo", r"\bpeo\b|executive officer"),
              ("gp", r"gram\s*panchayat|g\.\s*p\b|name of the g"), ("phone", r"number|mobile|phone|contact"),
              ("sno", r"^s\.?\s*l\.?\s*no|^sl|^s\.?\s*no")]


def role(h):
    h = (h or "").lower()
    for r, rx in ROLE_WORDS:
        if re.search(rx, h):
            return r
    return ""


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "x"


def rec(p, url, key, post_key, name, phone, gp, pos, extra=None):
    post, kind, level = POSTS[post_key]
    d = {"type": "dept_office", "dept": "rural_development", "level": level, "kind": kind, "state": "OD", "post": post,
         "name": name, "phone": phone, "area": gp, "block": p.get("block", ""), "block_regional": p.get("block_regional", ""),
         "district": "Ganjam", "source": url, "src_url": url, "src_pos": pos, **(extra or {})}
    return (f"dept:{MODULE}:{slug(p.get('block'))}:{key}:{post_key}", {k: v for k, v in d.items() if v not in ("", None)})


def html_records(html, p, url):
    out = []
    for ti, table in enumerate(_esw.soup(html).find_all("table")):
        rows = table.find_all("tr")
        if not rows:
            continue
        header = [_esw.clean(c.get_text(" ")) for c in rows[0].find_all(["th", "td"])]
        roles = [role(h) for h in header]
        if not any(r in POSTS for r in roles):
            continue
        for ri, tr in enumerate(rows[1:], 1):
            cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if not any(cells):
                continue
            gp = next((c for c, r in zip(cells, roles) if r == "gp"), "")
            raw = dict(zip(header, cells))
            last = None
            people = {}
            for c, r in zip(cells, roles):
                if r in POSTS:
                    last = r
                    people.setdefault(r, {"name": c, "phone": ""})
                elif r == "phone" and last:
                    people[last]["phone"] = c
            for pk, v in people.items():
                if v["name"] or v["phone"]:
                    out.append(rec(p, url, f"t{ti + 1}-r{ri}", pk, v["name"], v["phone"], gp, {"table": ti + 1, "row": ri},
                                   {"cells": raw}))
    return out


def pdf_records(text, p, url):
    out, order = [], []
    for pg, ptext in enumerate(text.split("\f"), 1):
        lines = ptext.split("\n")
        for ln, raw in enumerate(lines, 1):
            low = raw.lower()
            if not order and "mobile" in low and not re.match(r"^\s*\d", raw):
                xs = {}                      # the header runs over 3 lines: each post word's column (x) on its own line
                for h in lines[max(0, ln - 2):ln + 1]:
                    for r, rx in ROLE_WORDS:
                        mm = re.search(rx, h.lower())
                        if r in POSTS and mm:
                            xs[r] = min(xs.get(r, 10 ** 6), mm.start())
                order = sorted(xs, key=xs.get)
                continue
            m = re.match(r"^\s*(\d{1,3})[.)]?\s+(.*\S)", raw)
            if not m or not order or not re.search(r"[A-Za-z]", m.group(2)):
                continue
            cells = cells_of(m.group(2))
            texts = [i for i, (k, _) in enumerate(cells) if k == "t"]
            if not texts:
                continue
            gp = cells[texts[0]][1]
            i, cur, people = 0, None, {}
            for k, v in cells[texts[0] + 1:]:
                if i >= len(order):
                    break
                if k == "t":
                    if cur is not None:
                        i += 1
                        if i >= len(order):
                            break
                    cur = people.setdefault(order[i], {"name": v, "phone": ""})
                else:
                    if cur is None or cur["phone"]:
                        if cur is not None:
                            i += 1
                        if i >= len(order):
                            break
                        cur = people.setdefault(order[i], {"name": "", "phone": ""})
                    cur["phone"] = v
            for pk, v in people.items():
                out.append(rec(p, url, f"p{pg}-l{ln}", pk, v["name"], v["phone"], gp, provenance.line_pos(pg, ln, raw)))
    return out


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if r.content[:5] == b"%PDF-":
        files = [(f"depts/{MODULE}/{slug(p.get('block'))}.pdf", r.content, "application/pdf")]
        recs = pdf_records(_field.pdf_text(r.content), p, url)
    else:
        files = [_esw.keep(MODULE, slug(p.get("block")), r.content)]
        recs = html_records(r.text, p, url)
    src = provenance.at(r, url)
    for _, d in recs:
        d.update(src)
    return recs, files, "" if recs else "no rows"
