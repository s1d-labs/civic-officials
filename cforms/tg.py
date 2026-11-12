"""Telangana: SEC "Know Your Public Representative - Urban" (tsec.gov.in/knowPRUrban.do), 2026 municipal election (id 190).
One item = one ULB. GET the form (session cookie + Struts TOKEN), then one POST for the "all contested candidates" report (A):
per ward a line "WARD Name : 1 , Reserved for : SC(W), Total Voters ... : 2875 , Total Vaild Votes : 2115 , Rejected Votes : 43 ,
NOTA Votes : 9", then one row per candidate (name, party, votes, status). Wards come in order; the ward label is "1" or
"Ward - 1", and where the source puts a name instead, the ward number is the position and the name goes to ward_name.
If A has no winners, the "only elected" report (E) is asked with the token from A's answer. India only. GHMC is not in it."""
import gzip
import re

from bs4 import BeautifulSoup

import provenance

METHOD = "html table (ASP.NET-style report grids after a POST)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://tsec.gov.in/"
TOKEN = "org.apache.struts.taglib.html.TOKEN"


def token(html):
    t = BeautifulSoup(html, "lxml").find("input", attrs={"name": TOKEN})
    return t["value"] if t else None


def cells(tr):
    return [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]


def num(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if s.isdigit() else None


def report_a(html):
    """Ward rows from the all-candidates report: one dict per ward with its winner (if any) and the ward totals."""
    grid = BeautifulSoup(html, "lxml").find("table", id="GridView1")
    wards, w = [], None
    for ri, tr in enumerate(grid.find_all("tr") if grid else [], 1):
        c = cells(tr)
        if len(c) == 1 and c[0].startswith("WARD Name"):
            f = dict((k.strip(), v.strip()) for k, v in (x.split(":", 1) for x in c[0].split(",") if ":" in x))
            label = f.get("WARD Name") or ""          # "1" or "Ward - 1"; one ward has a place name here (Isnapur 1: "ZPHS LAKDARAM")
            no = re.fullmatch(r"(?:Ward\s*-?\s*)?(\d+)", label, re.I)
            w = {"ward_no": no.group(1) if no else str(len(wards) + 1), "ward_name": None if no else label,
                 "reservation": f.get("Reserved for"), "electors": num(f.get("Total Voters in Municipality Ward")),
                 "valid_votes": num(f.get("Total Vaild Votes")), "rejected_votes": num(f.get("Rejected Votes")),
                 "nota_votes": num(f.get("NOTA Votes")), "cands": []}
            wards.append(w)
        elif len(c) == 5 and w is not None and c[0].isdigit():
            w["cands"].append({"name": c[1], "party": c[2], "votes": num(c[3]), "status": c[4], "_row": ri})
    return wards


def report_e(html):
    grid = BeautifulSoup(html, "lxml").find("table", id="GridView1")
    rows = [cells(tr) for tr in (grid.find_all("tr") if grid else [])]
    out = []
    for ri, c in enumerate(rows, 1):
        if len(c) == 6 and c[0].isdigit():
            no = re.fullmatch(r"(?:Ward\s*-?\s*)?(\d+)", c[1], re.I)
            out.append({"ward_no": no.group(1) if no else c[0], "ward_name": None if no else c[1], "reservation": c[2], "name": c[3],
                        "party": c[4], "result_status": c[5], "src_pos": {"table_id": "GridView1", "row": ri},
                        "method": "html table (elected-only report E)"})
    return out


def fetch(p, get):
    r = get(BASE + "knowPRUrban.do")
    tok = r is not None and token(r.text)
    if not tok:
        return [], [], "no form token"
    url = BASE + "knowPRUrban.se"
    form = {"mode": "getULBWMDetails", "property(knowYour)": "WM", "property(year)": "2026", "property(electionFor)": "190",
            "property(district_id)": p["district_id"], "property(ulb_id)": p["ulb_id"], "property(ward_id)": "0"}
    slug = re.sub(r"[^a-z0-9]+", "-", p["ulb"].lower()).strip("-")
    base = {"type": "councillor", "state": "TG", "body": p["ulb"], "district": p.get("district"), "election": "Telangana 2026",
            "url": BASE + "knowPRUrban.do", "district_id": p["district_id"], "ulb_id": p["ulb_id"]}
    r = get(url, method="POST", data={TOKEN: tok, **form, "property(typeOfReport)": "A"})
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/TG/{p['district_id']}-{p['ulb_id']}-{slug}-A.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = []
    for w in report_a(r.text):
        won = [c for c in w["cands"] if c["status"]]
        if len(won) != 1:
            continue
        c = won[0]
        others = sorted((x["votes"] for x in w["cands"] if x is not c and x["votes"] is not None), reverse=True)
        d = {**base, "ward_no": w["ward_no"], "ward_name": w["ward_name"], "reservation": w["reservation"], "name": c["name"],
             "party": c["party"], "votes": c["votes"], "result_status": c["status"], "candidates": len(w["cands"]),
             "electors": w["electors"], "valid_votes": w["valid_votes"], "rejected_votes": w["rejected_votes"], "nota_votes": w["nota_votes"]}
        if c["votes"] is not None and others:
            d["margin"] = c["votes"] - others[0]
        # source trail: the winner's row in report A (a POST to the same url as report E: named by its bytes)
        d.update({**provenance.at(r, url), "src_pos": {"table_id": "GridView1", "row": c["_row"]},
                  "method": "html table (all-candidates report A)"})
        recs.append((f"councillor:TG:{slug}:{w['ward_no']}", d))
    if not recs:                                   # no winners in A: ask for the elected-only report with the new token
        tok = token(r.text)
        r = tok and get(url, method="POST", data={TOKEN: tok, **form, "property(typeOfReport)": "E"})
        if r:
            files.append((f"councillors/TG/{p['district_id']}-{p['ulb_id']}-{slug}-E.html.gz", gzip.compress(r.content), "application/gzip"))
            recs = [(f"councillor:TG:{slug}:{e['ward_no']}", {**base, **e, **provenance.at(r, url)}) for e in report_e(r.text)]
    return recs, files, "" if recs else "no members"
