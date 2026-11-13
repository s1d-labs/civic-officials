"""Bihar: State Election Commission municipal results, sec.bihar.gov.in/ForPublic/<page>.aspx (India only, no captcha, no party:
Bihar municipal polls are non-party). Pages: ResultP1 / ResultP2 = general election 2022, phase 1 / 2 (both list every body; a body
of the other phase answers "मतगणना की प्रक्रिया जारी है"), ResultP3 = phase 3 (postponed bodies and wards), ResultP4 = 2023
by-elections, Result2025 = 2025 general (new nagar panchayats) and by-elections. P3, P4 and 2025 list only their own bodies and wards.
ASP.NET postbacks: ddl_Post=3 (ward councillor) + ddlDistrict -> ddlNPType (1 nigam, 2 parishad, 3 panchayat) -> ddlPanchayat (body
id: gives the ward list) -> btnFilter=Show with ddlWard. One request per ward; the table lists every candidate with votes and the
winner carries "(विजेता)". There is no listing page per body. One queue item = one body; payload "pages" = the pages that carry
results for it, oldest first; a later page (by-election) replaces the winner of the same ward.
Record id councillor:BR:<slug>:<ward no>."""
import gzip
import html as htmlmod
import re

from bs4 import BeautifulSoup

import provenance
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET result page, one POST per ward)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://sec.bihar.gov.in/ForPublic/"
P = "ctl00$ContentPlaceHolder1$"
COUNTING = "मतगणना"                       # "counting in progress": this body is not on this page
ZW = re.compile("[\u200b-\u200d\ufeff]")
WIN = re.compile(r"\s*\((विजेता|निर्विरोध)[^)]*\)\s*")


def _post(get, url, html, target, fields, resp=False):
    """The page after the postback: its text, or (text, response) with resp=True (source trail)."""
    d = hidden(html)
    d.update({"__EVENTTARGET": P + target if target else "", "__EVENTARGUMENT": "", **{P + k: v for k, v in fields.items()}})
    if not target:
        d[P + "btnFilter"] = "Show"
    r = get(url, method="POST", data=d)
    if resp:
        return (r.text, r) if r is not None else (None, None)
    return r.text if r is not None else None


def _result(html):
    soup = BeautifulSoup(html, "lxml")
    m = soup.find(id="ctl00_ContentPlaceHolder1_lblMsg")
    g = soup.find("table", id="ctl00_ContentPlaceHolder1_RPDetails")
    rows = []
    if g:
        trs = g.find_all("tr")
        head = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[0].find_all(["th", "td"])] if trs else []
        for tr in trs[1:]:
            c = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
            if len(c) == len(head):
                rows.append(dict(zip(head, c)))
            else:
                provenance.skip_row(tr, 'skip: not (len(c) == len(head))')
    return (m.get_text(" ", strip=True) if m else ""), rows, (str(g) if g else "")


def _label(html):
    soup = BeautifulSoup(html, "lxml")
    h1 = next((h.get_text(" ", strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)), "")
    crumb = soup.select_one("li.breadcrumb-item.active")
    return " ".join(x for x in (h1, f"({crumb.get_text(' ', strip=True)})" if crumb else "") if x)


def _votes(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if s.isdigit() else None


def winner(rows):
    """(winner row, how): the row marked विजेता / निर्विरोध, else the only candidate, else the single highest vote."""
    marked = [r for r in rows if WIN.search(r.get("प्रत्याशी का नाम", ""))]
    if len(marked) == 1:
        return marked[0], "marked"
    if len(rows) == 1:
        return rows[0], "only candidate"
    v = sorted(((_votes(r.get("कुल प्राप्त मत")), i) for i, r in enumerate(rows)), reverse=True)
    if len(v) > 1 and v[0][0] is not None and v[0][0] > (v[1][0] or 0):
        return rows[v[0][1]], "most votes"
    return None, None


def body_form(get, page, p):
    """GET the page and post district, type and body. Returns (html with the ward list, ward numbers) or (None, why)."""
    url = BASE + page + ".aspx"
    r = get(url)
    if r is None:
        return None, "no answer"
    f = {"ddl_Post": "3", "ddlDistrict": p["district_value"]}
    h = _post(get, url, r.text, "ddlDistrict", f)
    f["ddlNPType"] = p["type"]
    h = h and _post(get, url, h, "ddlNPType", f)
    if h and p["body_value"] not in [v for v, _ in options(h, "ddlPanchayat")]:
        return None, f"body {p['body_value']} not on {page}"
    f["ddlPanchayat"] = p["body_value"]
    h = h and _post(get, url, h, "ddlPanchayat", f)
    if not h:
        return None, "postback did not answer"
    return h, [v for v, _ in options(h, "ddlWard")]


def fetch(p, get):
    sl = p["slug"]
    won, files, why = {}, [], []
    for page in p["pages"]:
        url = BASE + page + ".aspx"
        h, wards = body_form(get, page, p)
        if h is None:
            why.append(f"{page}: {wards}")
            continue
        label = _label(h)
        f = {"ddl_Post": "3", "ddlDistrict": p["district_value"], "ddlNPType": p["type"], "ddlPanchayat": p["body_value"]}
        saved, counting = [], 0
        for w in wards:
            r, resp = _post(get, url, h, "", {**f, "ddlWard": w}, resp=True)
            if r is None:
                saved.append(f"<!-- ward {w}: no answer -->")
                continue
            h = r
            msg, rows, table = _result(r)
            saved.append(f"<section data-ward=\"{w}\"><p>{htmlmod.escape(msg)}</p>{table}</section>")
            if COUNTING in msg and not rows:
                counting += 1
                if counting >= 3 and not won:            # not this body's phase
                    break
                continue
            c, how = winner(rows)
            if c is None:
                continue
            others = sorted((_votes(x.get("कुल प्राप्त मत")) or 0 for x in rows if x is not c), reverse=True)
            votes = _votes(c.get("कुल प्राप्त मत"))
            d = {"type": "councillor", "state": "BR", "body": c.get("नगर निकाय") or p.get("body"), "body_type": p.get("body_type"),
                 "district": c.get("जिला") or p.get("district"), "subdivision": c.get("अनुमंडल"), "post": c.get("पद"),
                 "ward_no": c.get("वार्ड") or w, "name": " ".join(ZW.sub("", WIN.sub(" ", c.get("प्रत्याशी का नाम", ""))).split()), "votes": votes,
                 "candidates": len(rows), "margin": votes - others[0] if votes is not None and others else None,
                 "winner_by": how if how != "marked" else None, "election": label, "url": url, "result_page": page,
                 "body_value": p["body_value"],
                 # source trail: every ward is a POST to the same url, so the answer is named by its bytes; the winner's row
                 **provenance.at(resp, url),
                 "src_pos": {"table_id": "ctl00_ContentPlaceHolder1_RPDetails",
                             "row": next(i for i, x in enumerate(rows) if x is c) + 2, "ward_posted": w}}
            won[w] = {k: v for k, v in d.items() if v not in (None, "")}
        doc = f"<html><head><meta charset=\"utf-8\"><title>{htmlmod.escape(label)}</title></head><body>{''.join(saved)}</body></html>"
        files.append((f"councillors/BR/{page}-{p['body_value']}-{sl}.html.gz", gzip.compress(doc.encode()), "application/gzip"))
    recs = [(f"councillor:BR:{sl}:{w}", d) for w, d in won.items()]
    return recs, files, "" if recs else ("; ".join(why) or "no winners")
