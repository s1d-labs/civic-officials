"""Chhattisgarh: Urban Administration & Development Dept "Parshad search", uad.cg.gov.in/UrbanLocalBodies/ParshadsearchHome.aspx
(India only, no captcha). ASP.NET form: GET, then POST ddlNikay=<body id> + btnNikay=SEARCH. The answer is a GridView of 20 rows per
page (district, body, body type, councillor, ward no, ward name, address, email, office phone, mobile, party, first meeting date);
further pages are postbacks with __EVENTTARGET=Gview, __EVENTARGUMENT=Page$<n>. One queue item = one body.
The list is NOT the Feb 2025 term: in 2026-11 every body shows the 2019-20 councillors (first meeting 01/2020), a few bodies
the Dec 2021 or 2022-23 polls (first meeting 2022 / 2023), and 26 new bodies show nothing. The term comes from the first meeting
date of each row ("election", "first_meeting", "stale"). The SEC result system cgsecerms.cgstate.gov.in refuses connections.
items(get) lists the bodies of the dropdown (seeds/councillors_cg.json). Record id councillor:CG:<slug>:<ward no>."""
import gzip
import re

from bs4 import BeautifulSoup

import provenance
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET grid, paged by POST)"     # source trail (provenance.py): how this reader reads its sources

U = "https://uad.cg.gov.in/UrbanLocalBodies/ParshadsearchHome.aspx"
P = "ctl00$ContentPlaceHolder1$"
COLS = {"जिले का नाम": "district", "निकाय का नाम": "body", "निकाय का प्रकार": "body_type", "पार्षद का नाम": "name",
        "वार्ड क्रमांक": "ward_no", "वार्ड का नाम": "ward_name", "पार्षद का पता": "address", "ईमेल": "email",
        "कार्यालय दूरभाष नम्बर": "office_phone", "मोबाईल नम्बर": "phone", "राजनैतिक दल": "party", "प्रथम सम्मेलन तिथि": "first_meeting"}
NOMINATED = "शासन द्वारा नियुक्त"           # "appointed by the government" (aldermen): no ward
ZW = re.compile("[​-‍﻿]")

# Devanagari -> Latin, for slugs only (record ids must be ASCII): rough, with the usual schwa deletion.
_C = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ",
              "k kh g gh n ch chh j jh n t th d dh n t th d dh n p ph b bh m y r l v sh sh s h l".split()))
_C.update({"क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"})
_NUKTA = {"क": "q", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f"}
_V = dict(zip("अआइईउऊऋएऐओऔऑ", "a a i i u u ri e ai o au o".split()))
_M = dict(zip("ािीुूृेैोौॉॅ", "a i i u u ri e ai o au o e".split()))


def roman(s):
    words = []
    for word in re.split(r"[^ऀ-ॿA-Za-z0-9]+", ZW.sub("", s)):
        t = []                                    # [consonant, vowel, schwa?]
        for ch in word:
            if ch in _C:
                t.append([_C[ch], "a", True])
            elif ch == "़" and t:            # nukta
                t[-1][0] = next((v for k, v in _NUKTA.items() if _C[k] == t[-1][0]), t[-1][0])
            elif ch in _M and t:
                t[-1][1:] = [_M[ch], False]
            elif ch == "्" and t:            # virama
                t[-1][1:] = ["", False]
            elif ch in "ंँ":
                t.append(["", "n", False, "coda"])
            elif ch == "ः":
                t.append(["", "h", False, "coda"])
            elif ch in _V:
                t.append(["", _V[ch], False])
            elif ch.isascii():
                t.append([ch.lower(), "", False])
        if t and t[-1][2]:
            t[-1][1] = ""
        for i in range(len(t) - 2, 0, -1):        # V C(a) C V -> drop the a
            if t[i][2] and t[i - 1][1] and t[i + 1][0] and t[i + 1][1] and len(t[i + 1]) == 3:
                t[i][1] = ""
        for i in range(1, len(t)):                # "ाय" before a consonant reads "ai" (Raipur, Raigarh)
            if t[i][0] == "y" and not t[i][1] and t[i - 1][1] == "a" and len(t[i - 1]) == 3:
                t[i][0] = "i"
        out = ""
        for i, x in enumerate(t):
            if len(x) == 4 and x[1] == "n" and i + 1 < len(t) and t[i + 1][0][:1] in ("p", "b", "m"):
                out += "m"
            else:
                out += x[0] + x[1]
        words.append(out)
    return "-".join(w for w in words if w)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", roman(s).lower()).strip("-")


def clean(s):
    return " ".join(ZW.sub("", s or "").split())


def _rows(html, src=None):
    """Rows of the result grid; each carries "_pos" (its <tr> number) and "_src" (provenance.at of the page) for the trail."""
    g = BeautifulSoup(html, "lxml").find("table", id="ContentPlaceHolder1_Gview")
    trs = g.find_all("tr") if g else []
    if not trs:
        return []
    head = [clean(c.get_text(" ", strip=True)) for c in trs[0].find_all(["th", "td"])]
    out = []
    for ri, tr in enumerate(trs[1:], 2):
        c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(c) == len(head) and c[0].isdigit():
            out.append({COLS.get(h, h): v for h, v in zip(head, c)})
            out[-1]["_pos"], out[-1]["_src"] = {"table_id": "ContentPlaceHolder1_Gview", "row": ri}, src or {}
        else:
            provenance.skip_row(tr, 'skip: not (len(c) == len(head) and c[0].isdigit())')
    return out


def _search(get, value, resp=False):
    """The search answer's text (or (text, response) with resp=True)."""
    r = get(U)
    if r is None:
        return (None, None) if resp else None
    d = hidden(r.text)
    d.update({P + "ddlNikay": value, P + "btnNikay": "SEARCH"})
    r = get(U, method="POST", data=d)
    if resp:
        return (r.text, r) if r is not None else (None, None)
    return r.text if r is not None else None


def items(get):
    """One item per body of the dropdown; district and body type from page 1 of its list (none for bodies with no rows).
    The five "क्षेत्रीय कार्यालय" (regional offices) are left out."""
    r = get(U)
    if r is None:
        return []
    out = []
    for v, name in options(r.text, "ddlNikay"):
        if not v.isdigit() or name.startswith("क्षेत्रीय कार्यालय"):
            provenance.skip_line(v, 'skip: not v.isdigit() or name.startswith("क्षेत्रीय कार्यालय")')
            continue
        h = _search(get, v)
        rows = _rows(h) if h else []
        q = {"kind": "form-cg", "state": "CG", "url": U, "body_value": v, "body": clean(name)}
        if rows:
            q.update({"district": rows[0]["district"], "body_type": rows[0]["body_type"]})
        out.append({"key": f"cg-{v}", "payload": q})
    names = [slug(i["payload"]["body"]) for i in out]
    for i, n in zip(out, names):
        i["payload"]["slug"] = n if names.count(n) == 1 else f"{n}-{i['payload']['body_value']}"
    return out


def _term(date):
    m = re.search(r"(\d{4})$", date or "")
    if not m:
        return None, None
    y = int(m.group(1))
    return f"{y - 1}-{str(y)[2:]}", y


def fetch(p, get):
    v = p["body_value"]
    sl = p.get("slug") or slug(p["body"]) or f"body-{v}"
    h, resp = _search(get, v, resp=True)
    if not h:
        return [], [], "no answer"
    files, rows, page = [], [], 1
    while True:
        files.append((f"councillors/CG/uad-{v}-{sl}-p{page}.html.gz", gzip.compress(h.encode()), "application/gzip"))
        rows += _rows(h, {**provenance.at(resp, U), "paged": page})
        page += 1
        if f"Page${page}" not in h or page > 30:
            break
        d = hidden(h)
        d.update({"__EVENTTARGET": P + "Gview", "__EVENTARGUMENT": f"Page${page}", P + "ddlNikay": v})
        r = get(U, method="POST", data=d)
        if r is None:
            return [], files, f"page {page} did not answer"
        h, resp = r.text, r
    if not rows:
        return [], files, "no councillors listed"
    bodies = {r["body"] for r in rows}
    if len(bodies) > 1 or clean(p["body"]) not in bodies:
        return [], files, f"page shows {', '.join(sorted(bodies))}, not {p['body']}"
    # one record per ward: a later first meeting (a by-election) replaces the earlier member; aldermen get n1, n2 ...
    best, nominated = {}, []
    for r in rows:
        term, year = _term(r.get("first_meeting"))
        d = {"type": "councillor", "state": "CG", **{k: val for k, val in r.items() if k in COLS.values()},
             "election": f"Chhattisgarh ULB {term} election (UAD parshad list, first meeting {r.get('first_meeting')})" if term
             else "Chhattisgarh ULB (UAD parshad list)", "stale": bool(year and year < 2025), "url": U, "body_value": v,
             # source trail: every page of the grid is a POST to the same url: the answer is named by its bytes
             **{k: val for k, val in r["_src"].items() if k != "paged"},
             "src_pos": {**r["_pos"], "grid_page": r["_src"].get("paged")}}
        for k in ("phone", "office_phone", "email"):
            if d.get(k) in ("", "0", "-", None):
                d.pop(k, None)
        d = {k: val for k, val in d.items() if val not in (None, "")}
        if r.get("party") == NOMINATED or not r.get("ward_no", "").strip("0"):
            d["position"] = "nominated member"
            d.pop("ward_no", None)
            nominated.append(d)
            continue
        key = r["ward_no"]
        old = best.get(key)
        if old is None or _date(d.get("first_meeting")) >= _date(old.get("first_meeting")):
            best[key] = d
    recs = [(f"councillor:CG:{sl}:{k}", d) for k, d in best.items()]
    recs += [(f"councillor:CG:{sl}:n{i}", d) for i, d in enumerate(nominated, 1)]
    return recs, files, ""


def _date(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (0, 0, 0)
