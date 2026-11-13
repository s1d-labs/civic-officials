"""Shared parts of the town office staff readers (dforms/town2_<platform>.py, 2026-11-13): the staff of a town body (Chief Officer /
Commissioner / Executive Officer, engineers, health officers and inspectors, revenue officers and inspectors, town planners,
accountants, office staff) from the staff page of a state platform that holds one site per town body.

staff_rows(html) reads every HTML table whose heading row has a name column and a designation (post) column. Rows with one text
cell (or text in the first cell only) are section headings ("Engineering Section Details", "Health Section"): the rows under them
get that section. A row with an empty post takes the section as its post. A row whose name says the post is vacant ("1-Post
Vacant", "Vacant", "Vaccant") or gives no name ("-", empty) is not a record: it is counted with provenance.skipped("vacant post")
or skipped("no name").

record() makes one dept_office record: dept "town_body", level "body", area = the body as the platform names it, lgd_code when the
platform list gives it, role from _ulb.role_of(post) ("head" for the Chief Officer / Commissioner, "deputy" for an Assistant /
Deputy Commissioner, else "staff"), section, post_from "staff page". The record id holds the site, the post and the name, so the
same person in the same post keeps the same id when the page changes order.
"""
import re

import provenance
from dforms import _esw, _ulb
from dforms._water import unique

COLS = {
    "name": re.compile(r"(?i)^(name|officer'?s?\s*name|employee\s*name|name\s*of\s*(the\s*)?(officer|employee|staff))\b|ಹೆಸರು|^नाम|"
                       r"అధికారి\s*పేరు|^పేరు"),
    "post": re.compile(r"(?i)^(designation|post|rank)\b|ಹುದ್ದೆ|ಪದನಾಮ|^पद|హోదా"),
    "phone": re.compile(r"(?i)contact|mobile|phone|cell|ಮೊಬೈಲ್|ದೂರವಾಣಿ|मोबाइल|फोन|ఫోన్|మొబైల్"),
    "email": re.compile(r"(?i)e-?\s?mail|ಇ-?ಮೇಲ್|ई-?मेल"),
}
VACANT = re.compile(r"(?i)^\s*(\d+\s*[-.)]?\s*)?(post\s*)?va+c+a+n+t\w*\b|^\s*(post\s*)?vacant\s*post|ಖಾಲಿ|रिक्त")
NO_NAME = re.compile(r"(?i)^[\s\-–—.*/_]*$|^(nil|n/?a|none|not\s*available)$")
SERIAL = re.compile(r"^\s*\d{1,3}\s*[.)]?\s*$")
ZONAL = re.compile(r"(?i)\bzonal\s*(commissioner|officer)\b|\bzone\s*officer\b|ವಲಯ\s*ಆಯುಕ್ತ")


def header_map(cells, cols=None):
    """{field: column index} of a heading row, or None when it has no name or no post column. cols: the column words
    ({field: regex}; default COLS)."""
    h = {}
    for i, c in enumerate(cells):
        t = _esw.clean(c)
        for f, rx in (cols or COLS).items():
            if f not in h and rx.search(t):
                h[f] = i
                break
    return h if "name" in h and "post" in h else None


def staff_rows(html, cols=None):
    """[{section, name, post, phone, email, cells, pos}] of the staff tables of a page (pos = {"table", "row"} as _esw.grid gives
    them). Rows left out are counted (provenance). cols: the column words (default COLS; dforms/_town3.py adds more scripts)."""
    soup = _esw.soup(html)
    out, last = [], None          # last: (heading map, row width, section) of the staff table before this one
    for t in soup.find_all("table"):
        pos = []
        rows = _esw.grid(t, pos=pos)
        h, section = None, ""
        for cells, where in zip(rows, pos):
            texts = [_esw.clean(c) for c in cells]
            if h is None:
                h = header_map(texts, cols)
                if h is not None:
                    provenance.skipped("header")
                    continue
                if last and len(texts) == last[1] and any(texts):
                    # a table without a heading row right after a staff table, with the same columns: its continuation
                    h, section = last[0], ""
                else:
                    provenance.skip_row(texts, "before the heading row")
                    continue
            if header_map(texts, cols):            # a repeated heading row
                provenance.skipped("header")
                continue
            filled = [x for x in texts if x and not NO_NAME.match(x)]
            if not filled or all(SERIAL.match(x) for x in filled):     # empty, or a serial number and nothing else
                provenance.skipped("empty")
                continue
            if len(set(filled)) == 1:          # a section heading: one text cell (colspan rows repeat it in every column)
                section = filled[0]
                provenance.skipped("header")
                continue
            g = {f: (texts[i] if i < len(texts) else "") for f, i in h.items()}
            if not g["post"] and section:
                g["post"] = section
            if not g["post"]:
                provenance.skip_row(texts, "no post")
                continue
            if VACANT.search(g["name"]):
                provenance.skipped("vacant post")
                continue
            if NO_NAME.match(g["name"]):
                provenance.skipped("no name")
                continue
            out.append({"section": g.get("section") or section, "name": g["name"], "post": g["post"].replace(" | ", " "), "phone": g.get("phone", ""),
                        "email": g.get("email", ""), "cells": texts, "pos": where})
        if h is not None:
            last = (h, max(set(map(len, rows)), key=[len(r) for r in rows].count), section)     # the usual row width
    return out


def record(module, state, site, body, row, seen, *, district=None, lgd_code=None, source="", slug=None, **extra):
    """(record id, data) for one staff row of staff_rows() (or a dict with the same keys). slug: the function that makes the
    post and name parts of the id (default _esw.slug, a-z0-9 only; dforms/_town3.py keeps letters of every script)."""
    post = _esw.clean(row["post"])
    name = _esw.clean(row["name"])
    slug = slug or _esw.slug
    key = unique(f"{site}:{slug(post)[:60] or 'post'}:{slug(name)[:60] or 'x'}", seen)
    phone = _esw.phones(row.get("phone", "")) if row.get("phone") else ""
    email = _esw.emails(" ".join(x for x in (row.get("email", ""), row.get("phone", "")) if x))
    role = _ulb.role_of(post)
    if ZONAL.search(post):
        role = "zonal"
    provenance.used()
    return _esw.record(module, key, dept="town_body", level="body", area=_esw.clean(body), post=post, name=name, phone=phone,
                       email=email, state=state, district=_esw.clean(district) or None, lgd_code=lgd_code or None, role=role,
                       section=row.get("section") or None, office_id=f"{state}-ULB-{_esw.slug(district or '')}-{_esw.slug(body)}",
                       post_from="staff page", site=site, cells=row.get("cells"), src_pos=row.get("pos"), source=source,
                       **extra)
