"""Kerala: the officials and employees of each municipality and corporation (Secretary, Assistant Secretary / Superintendent,
Health Inspectors, Revenue Inspector, engineers, clerks ...), from the body's own site, page /en/officials ("Officials &
Employees", Information Kerala Mission template, the same sites cforms/kl_heads.py and dforms/ulb_kl.py read). The sites answer
from outside India (the archive holds 41 copies saved by GitHub runners, 2026-11-11/12).

The page has one HTML table: Sl. No. | Name | Designation [| Section] [| Mob No. | Email] (English or Malayalam words: പേര്,
തസ്തിക; the header row may stand under a title row); a row with a single cell is a section heading
("Engineering Department") and is kept on the rows below it as "section". Columns are found by the header words. Some bodies draw
an organisation chart instead (Panoor: one name per cell, no header): those pages give no records here ("no officials table").
The footer's "Contact" block gives the office's email and phone: one "Office" record (post_from "directory") with them.
The page shows "Last reviewed and updated on <date>" on some sites: kept as last_updated.
One queue item = one body: payload {"reader": "th_kl", "url": "https://<site>/en/officials", "body", "body_type", "code" (LSGD
code), "district", "lgd_code", "state": "KL"}, made from seeds/councillors_kl_heads.json (93 bodies, LGD codes checked there).
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb

METHOD = "html table (officials page of the body)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "th_kl"
STATE = "KL"
COLS = [("name", r"name|പേര്"), ("post", r"designation|post|തസ്തിക|ഉദ്യോഗ"), ("phone", r"mob|phone|contact|tel|മൊബൈ|ഫോണ"),
        ("email", r"e-?\s?mail|ഇ-?\s?മെയി")]


def items(get=None):
    here = Path(__file__).resolve().parent.parent
    seed = json.loads((here / "seeds" / "councillors_kl_heads.json").read_text(encoding="utf-8"))
    out = []
    for it in seed:
        p = it["payload"]
        base = p["url"].rstrip("/")
        base = base[:-3] if base.endswith("/en") else base
        out.append({"key": f"th_kl-{p['code'].lower()}", "payload": {
            "reader": MODULE, "url": base + "/en/officials", "body": p["body"], "body_type": p.get("body_type"),
            "code": p["code"], "district": p.get("district"), "lgd_code": p.get("lgd_code"), "state": STATE,
            "india_only": False}})
    return out


def cells(tr):
    return [_esw.cell_text(c) for c in tr.find_all(["td", "th"])]


def two_scripts(v):
    """("Krishnagopal A", "കൃഷ്ണഗോപാൽ എ") from "Krishnagopal A | (കൃഷ്ണഗോപാൽ എ)"; a cell in one script stays whole (line breaks
    become spaces: "റവന്യൂ | ഇന്സ്പെക്ടര്" -> "റവന്യൂ ഇന്സ്പെക്ടര്")."""
    parts = [x.strip(" ()") for x in v.split("|") if x.strip(" ()")]
    lat = [x for x in parts if not re.search(r"[\u0d00-\u0d7f]", x)]
    ml = [x for x in parts if re.search(r"[\u0d00-\u0d7f]", x)]
    if lat and ml:
        return " ".join(lat), " ".join(ml)
    return " ".join(parts), ""


def rows(html):
    """[(pos, row dict)] of the officials table; None when the page has no table with Name and Designation columns."""
    soup = _esw.soup(html)
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = t.find_all("tr")
        if not trs:
            continue
        idx, hrow = {}, None
        for hi, tr in enumerate(trs[:3]):         # the header is the first row, or the row under a title row
            head = cells(tr)
            idx = {}
            for i, h in enumerate(head):
                for key, rx in COLS:
                    if key not in idx and re.search(rx, h, re.I):
                        idx[key] = i
                        break
            if "name" in idx and "post" in idx:
                hrow = hi
                break
        if hrow is None:
            continue
        out, section = [], None
        for ri, tr in enumerate(trs[hrow + 1:], hrow + 2):
            c = cells(tr)
            filled = [x for x in c if x]
            if len(filled) == 1 and not re.fullmatch(r"\d+\.?", filled[0]):
                section = filled[0]
                continue
            if len(c) <= max(idx["name"], idx["post"]):
                continue
            name, post = c[idx["name"]], c[idx["post"]]
            if not name or not re.search(r"[A-Za-zഀ-ൿ]{2}", name) or re.fullmatch(r"(?i)vacant|nil|-+", name):
                continue
            phone = c[idx["phone"]] if "phone" in idx and idx["phone"] < len(c) else ""
            m = re.search(r"(?i)[-–,]?\s*(phone|mob(ile)?)\s*(no)?[.:\s]*([\d\s-]{8,})$", post)
            if m:                       # "SECRETARY - Phone no: 9188955302" (Koothuparamba)
                post, phone = post[:m.start()].strip(" -–,"), phone or m.group(4)
            name, name_ml = two_scripts(name)
            post, post_ml = two_scripts(post)
            d = {"name": name, "name_regional": name_ml, "post": post or "Staff", "post_regional": post_ml,
                 "section": section, "cells": c,
                 "phone": phone,
                 "email": c[idx["email"]] if "email" in idx and idx["email"] < len(c) else ""}
            out.append(({"table": ti, "row": ri}, d))
        return out
    return None


def footer(html):
    """(email, phone, last_updated) of the page's footer contact block."""
    soup = _esw.soup(html)
    foot = soup.find("footer") or soup
    t = _esw.clean(foot.get_text(" "))
    em = _esw.emails(t)
    m = re.search(r"\b0\d{2,4}\s*-?\s*\d{6,8}\b", t)
    lu = re.search(r"Last reviewed and updated on\s*([0-9]{1,2}-[A-Za-z]{3}-[0-9]{4}(?:\s+[0-9:]+)?)", _esw.clean(soup.get_text(" ")))
    return em.split(", ")[0] if em else "", m.group(0) if m else "", lu.group(1) if lu else ""


def parse(html, p):
    rs = rows(html)
    recs, seen = [], set()
    em, ph, lu = footer(html)
    common = dict(district=p.get("district"), body_type=p.get("body_type"), source=p["url"], lgd_code=p.get("lgd_code"),
                  area_latin=p["body"], lsgd_code=p.get("code"), page=p["url"], last_updated=lu or None)
    for pos, d in rs or []:
        recs.append(_ulb.record(MODULE, STATE, p["body"], d["post"], seen, name=d["name"], phone=d["phone"], email=d["email"],
                                name_regional=d["name_regional"] or None, post_regional=d["post_regional"] or None,
                                section=d["section"], cells=d["cells"], src_pos=pos, **common))
    if em or ph:
        recs.append(_ulb.record(MODULE, STATE, p["body"], "Office", seen, phone=ph, email=em, post_from="directory",
                                src_pos={"block": "footer"}, **common))
    return recs, rs is not None


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs, had = parse(r.text, p)
    files = [_esw.keep(MODULE, p["code"].lower(), r.content, "html")]
    if not had:
        return recs, files, "no officials table" if not recs else ""
    return recs, files, "" if recs else "no rows"
