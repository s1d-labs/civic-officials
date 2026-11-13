"""Tamil Nadu: the commissioner and the staff of each municipal corporation and municipality, from the body's own site on the
state platform www.tnurbantree.tn.gov.in/<site>/ (WordPress multisite, 155 sites; the same sites cforms/tn_heads.py reads for
the elected heads). The platform answers from outside India (checked from dev-vps-3 and in the archive, 2026-11-13).

The pages have no common address, so the reader asks the site's public WordPress API, as tn_heads does:
<site>/wp-json/wp/v2/pages?search=<term>&_fields=id,link,title,content,modified for "commissioner" and "ஆணையாளர்". The answers
hold every page of the site that has the word, with its last change ("modified"). Pages read:
- "Commissioner" / "ஆணையாளர்" / "Municipal Commissioner" / "City Municipal Commissioner" / "மாநகர ஆணையாளர்" (title): a label | value table (Name / ஆணையாளர் பெயர், Office Address,
  Phone / தொலைபேசி எண் / அலைபேசி எண், E-Mail / மின்னஞ்சல்). One "head" record per page; the newest page wins (the English and the
  Tamil page of one site name the same officer: the newest one is kept, the other is dropped).
- "All Staff Details" / "அனைத்து பிரிவு பணியாளர்கள்" (title): the public-disclosure staff table (S.No, Sanctioned Post Name, Name of
  the person/s currently employed, Grade, Gender, Age, Permanent / deputation, kind of work). One record per named row (no phones
  in this table); the newest page with the most rows wins.
- "Officers Details" / "அலுவலர் விவரங்கள்" (title): office | post | mobile table (no names). Rows whose office cell is the body's
  own office (the first row's office) give one record per post with the post's mobile; rows of other offices (police, hospital,
  taluk office ...) are left out.
Many sites carry pages copied from another town in 2019 (the "Who's Who" page of N. Baskar, "Contact us" of Tiruvannamalai). The
reader does not read "Who's Who" pages, and drops a Commissioner page whose commissioner mailbox (commr.<town>@tn.gov.in) names
another town than the site. Records keep the page's last change (page_modified); a page last changed before OLD_BEFORE gets
old_page true (the officer named there may have moved since).
One queue item = one site: payload {"reader": "th_tn", "url" (the site), "site", "name_en", "lgd_code", "state": "TN"}; the LGD
codes come from seeds/tn_heads_lgd.json (made for tn_heads). Record ids dept:th_tn:TN--<site>-<post>.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

from dforms import _esw, _ulb
import provenance

METHOD = "html table (in a WordPress search answer: json api)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "th_tn"
STATE = "TN"
BASE = "https://www.tnurbantree.tn.gov.in/"
TERMS = ("commissioner", "ஆணையாளர்")
OLD_BEFORE = "2024-01-01"
HEAD_TITLE = re.compile(r"^\s*(city\s+)?((municipal|corporation)\s+)?commissioner\s*$|^\s*(நகராட்சி\s*|மாநகராட்சி\s*|மாநகர\s*)?ஆணையாளர்\s*$",
                        re.I)
STAFF_TITLE = re.compile(r"all\s*staff|அனைத்து\s*பிரிவு", re.I)
OFFICERS_TITLE = re.compile(r"officers?\s*details?|அலுவலர்\s*விவர", re.I)
LABELS = [("name", r"name|பெயர்"), ("address", r"address|முகவரி"), ("email", r"e\s*[-–]?\s*mail|மின்னஞ்சல்|மெயில்"),
          ("phone", r"phone|mobile|cell|தொலைபேசி|அலைபேசி|கைபேசி"), ("post", r"position|designation|பதவி")]


def search_url(site, term):
    return f"{BASE}{site}/wp-json/wp/v2/pages?search={quote(term)}&_fields=id,link,title,content,modified&per_page=50"


def items(get=None):
    """One item per tnurbantree site of platform_sites.csv, with the LGD code of seeds/tn_heads_lgd.json."""
    import csv
    here = Path(__file__).resolve().parent.parent
    lgd = json.loads((here / "seeds" / "tn_heads_lgd.json").read_text(encoding="utf-8"))
    out = []
    with open(here / "platform_sites.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["state_code"] != "TN" or "tnurbantree" not in row["domain"] or row["name"].startswith("wpfc-"):
                continue
            site = row["name"]
            info = lgd.get(site) or {}
            out.append({"key": f"th_tn-{site}", "payload": {"reader": MODULE, "url": f"{BASE}{site}/", "site": site,
                        "name_en": info.get("name") or site.replace("-", " ").title(), "lgd_code": info.get("lgd_code"),
                        "state": STATE, "india_only": False}})
    return out


def text(el):
    return " ".join(el.get_text(" ", strip=True).split()).strip(" :-–")


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def foreign(email, site):
    """True when the page's commissioner mailbox names another town than the site (a page copied from another site)."""
    m = re.search(r"commr\.?\s*([a-z]+)", (email or "").lower())
    if not m:
        return False
    a, b = norm(m.group(1)), norm(site)
    return not (a[:4] == b[:4] or a in b or b in a)


def split_name(v):
    """("Thiru. J. VEERAVANJINATHAN", "B.Sc.") from "Thiru. J. VEERAVANJINATHAN, B.Sc.,"; the part after the first comma is cut
    off when it holds a degree, a service or a post ("THIRU . ARPIT JAIN, I.A.S., COMMISSIONER (I/C)")."""
    v = " ".join(v.split()).strip(" ,")
    if "," in v:
        a, b = v.split(",", 1)
        if re.search(r"(?i)\b(i\.?\s?a\.?\s?s|b\.\s?[a-z]|m\.\s?[a-z]|ph\.?\s?d)|\b(commissioner|mba|bsc|msc|be|me)\b", b):
            return a.strip(" ,"), b.strip(" ,")
    return v, ""


def head_page(html):
    """{name, phone, email, address, post, qualification} from a Commissioner page's label | value table."""
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for tr in soup.find_all("tr"):
        cells = [text(c) for c in tr.find_all(["td", "th"])]
        cells = [c for c in cells if c]
        if len(cells) < 2:
            provenance.skip_row(tr, 'skip: len(cells) < 2')
            continue
        label, val = cells[0], " ".join(cells[1:])
        for key, rx in LABELS:
            if re.search(rx, label, re.I):
                if key in ("phone",):
                    out["phone"] = ", ".join(x for x in (out.get("phone"), _esw.phones(val)) if x)
                elif key not in out:
                    out[key] = val
                break
    if not out.get("email"):
        out["email"] = _esw.emails(soup.get_text(" "))
    if out.get("name"):
        out["name"], out["qualification"] = split_name(out["name"])
    title = soup.find(["strong", "h1", "h2", "h3", "h4"])
    out["post_shown"] = text(title) if title else ""
    return out


def table_rows(html, want):
    """[(table no, row no, cells)] of the first table whose header row matches want (a regex over the joined header)."""
    soup = BeautifulSoup(html, "html.parser")
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = t.find_all("tr")
        head = " | ".join(text(c) for tr in trs[:3] for c in tr.find_all(["td", "th"]))
        if not re.search(want, head, re.I):
            continue
        return [(ti, ri, [text(c) for c in tr.find_all(["td", "th"])]) for ri, tr in enumerate(trs, 1)]
    return []


def staff_rows(html):
    """[(pos, post, name, extra)] of the All Staff Details table: rows that start with a serial number and name a person."""
    out = []
    for ti, ri, c in table_rows(html, r"sanctioned\s*post|name\s*of\s*the\s*person"):
        if len(c) < 3 or not re.fullmatch(r"\d{1,4}\.?", c[0]):
            provenance.skipped('skip: len(c) < 3 or not re.fullmatch(r"\\d{1,4}\\.?", c[0])')
            continue
        post, name = c[1], c[2]
        if not re.search(r"[A-Za-z஀-௿]{2,}", name) or re.fullmatch(r"(?i)(vacant|nil|-+|–+|—+)", name.strip()):
            provenance.skipped('skip: not re.search(r"[A-Za-z\u0b80-\u0bff]{2,}", name) or re.fullmatch(r"(?i)(vaca...')
            continue
        extra = {"grade": c[3] if len(c) > 3 else "", "gender": c[4] if len(c) > 4 else "", "age": c[5] if len(c) > 5 else "",
                 "service": c[6] if len(c) > 6 else "", "cells": c}
        out.append(({"table": ti, "row": ri}, post, name, extra))
    return out


def officer_rows(html):
    """[(pos, office, post, phone)] of the Officers Details table, only the body's own office rows (office of the first row)."""
    out, own = [], None
    for ti, ri, c in table_rows(html, r"அலுவலர்|officer|designation"):
        if len(c) < 3 or not re.fullmatch(r"\d{1,4}\.?", c[0]):
            provenance.skipped('skip: len(c) < 3 or not re.fullmatch(r"\\d{1,4}\\.?", c[0])')
            continue
        office, post = c[1], c[2]
        phone = _esw.phones(" ".join(c[3:])) if len(c) > 3 else ""
        own = own or office
        if office != own:
            provenance.skipped('skip: office != own')
            continue
        out.append(({"table": ti, "row": ri}, office, post, phone))
    return out


def parse(answers, p):
    """answers: [(api url, json text)]. Records of the commissioner, the staff table and the office's posts."""
    site, body, code = p["site"], p.get("name_en") or p["site"], p.get("lgd_code")
    pages = {}
    for url, raw in answers:
        try:
            js = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(js, list):
            continue
        for i, pg in enumerate(js):
            if isinstance(pg, dict) and pg.get("id") is not None and pg["id"] not in pages:
                pages[pg["id"]] = (url, i, pg)
    heads, staff, officers = [], [], []
    for pid, (url, i, pg) in pages.items():
        title = BeautifulSoup((pg.get("title") or {}).get("rendered") or "", "html.parser").get_text(" ").strip()
        html = (pg.get("content") or {}).get("rendered") or ""
        link = pg.get("link") or ""
        if link and not link.startswith(f"{BASE}{site}/"):
            continue
        meta = {"url": url, "index": i, "id": pid, "title": title, "link": link, "modified": (pg.get("modified") or "")}
        if HEAD_TITLE.search(title):
            h = head_page(html)
            if h.get("name") and not foreign(h.get("email"), site):
                heads.append((meta, h))
        elif STAFF_TITLE.search(title):
            rows = staff_rows(html)
            if rows:
                staff.append((meta, rows))
        elif OFFICERS_TITLE.search(title):
            rows = officer_rows(html)
            if rows:
                officers.append((meta, rows))
    recs, seen = [], set()

    def add(meta, post, pos, **f):
        old = meta["modified"][:10] < OLD_BEFORE if meta["modified"] else None
        recs.append(_ulb.record(MODULE, STATE, body, post, seen, source=meta["link"] or meta["url"], lgd_code=code,
                                area_latin=body, site=site, page=meta["link"], page_title=meta["title"],
                                page_modified=meta["modified"], old_page=old or None, src_url=meta["url"],
                                src_pos={"index": meta["index"], "id": meta["id"], **pos}, **f))
    if heads:
        heads.sort(key=lambda x: x[0]["modified"], reverse=True)
        meta, h = heads[0]
        add(meta, "Commissioner", {}, name=h["name"], phone=h.get("phone", ""), email=h.get("email", ""),
            address=h.get("address"), qualification=h.get("qualification") or None, post_shown=h.get("post_shown") or None,
            in_charge=bool(re.search(r"(?i)i/c|in\s*-?\s*charge|பொறுப்பு", h.get("qualification", "") + " " + h.get("post_shown", "")
                                     + " " + h.get("post", ""))) or None)
    if staff:
        staff.sort(key=lambda x: (len(x[1]), x[0]["modified"]), reverse=True)
        meta, rows = staff[0]
        for pos, post, name, extra in rows:
            if heads and _ulb.role_of(post) == "head":
                provenance.skipped('skip: heads and _ulb.role_of(post) == "head"')
                continue        # the commissioner already has the head record (with phone and mail)
            add(meta, post, pos, name=name, **{k: v for k, v in extra.items() if v})
    if officers:
        officers.sort(key=lambda x: x[0]["modified"], reverse=True)
        meta, rows = officers[0]
        for pos, office, post, phone in rows:
            if not phone:
                provenance.skipped('skip: not phone')
                continue
            add(meta, post, pos, phone=phone, office=office, post_from="directory")
    return recs


def fetch(p, get):
    answers, files, rs = [], [], []
    for term in TERMS:
        url = search_url(p["site"], term)
        r = get(url)
        if r is None or getattr(r, "status_code", 200) != 200:
            continue
        answers.append((url, r.text))
        rs.append((url, r))
        files.append(_esw.keep(MODULE, f"{p['site']}-{'en' if term.isascii() else 'ta'}", r.content, "json"))
    if not answers:
        return [], [], "no answer"
    recs = parse(answers, p)
    shas = {u: provenance.at(r, u).get("src_sha256") for u, r in rs}
    for _, d in recs:
        if shas.get(d.get("src_url")):
            d["src_sha256"] = shas[d["src_url"]]
    return recs, files, "" if recs else "no officer page"
