"""Rajasthan: SEC "Winner & Runner Up Candidates", https://sec.rajasthan.gov.in/Winner_Runner.aspx?code=CEM (India only).
ASP.NET postbacks: Election Type 2 (Urban Local Body) + Election 1 (General) + Period (61 = "SEP 2026") -> District -> ULB.
The ULB postback returns the whole ward table (district, ULB, ward no, ward reservation, Winner/Runner, name, gender, age,
candidate category, party, votes). One queue item = one ULB, four requests. Only the winners become records.
items(get) lists every ULB of the period (the seed list, seeds/councillors_rj.json). Record id councillor:RJ:<slug>:<ward no>."""
import gzip
import re

from bs4 import BeautifulSoup

import provenance
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET result page after dropdown postbacks)"     # source trail (provenance.py): how this reader reads its sources

U = "https://sec.rajasthan.gov.in/Winner_Runner.aspx?code=CEM"
P = "ctl00$ContentPlaceHolder1$"
BASE = {"ElecType": "2", "Election": "1"}


def _post(get, html, target, fields, resp=False):
    """The page after the postback: its text, or (text, response) with resp=True (source trail)."""
    d = hidden(html)
    d.update({"__EVENTTARGET": P + target, "__EVENTARGUMENT": "", **{P + k: v for k, v in fields.items()}})
    r = get(U, method="POST", data=d)
    if resp:
        return (r.text, r) if r is not None else (None, None)
    return r.text if r is not None else None


def _selected(html, name_end):
    soup = BeautifulSoup(html, "lxml")
    sel = next((s for s in soup.find_all("select") if (s.get("name") or "").endswith(name_end)), None)
    o = sel.find("option", selected=True) if sel else None
    return " ".join(o.get_text(" ", strip=True).split()) if o else None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def items(get, period="61"):
    r = get(U)
    if r is None:
        return []
    f = {**BASE, "Period": period}
    h = _post(get, r.text, "Period", f)
    out = []
    for dv, dname in options(h, "DistrictDropDownList"):
        h2 = _post(get, h, "DistrictDropDownList", {**f, "DistrictDropDownList": dv})
        if h2 is None:
            raise RuntimeError(f"district {dname} did not answer")
        for uv, uname in options(h2, "PanchayatSamitiDropDownList"):
            out.append({"key": f"rj-{period}-{uv}", "payload": {
                "kind": "form-rj", "state": "RJ", "url": U, "period": period, "district_value": dv, "district": dname,
                "ulb_value": uv, "body": uname}})
    names = [i["payload"]["body"] for i in out]
    for i in out:      # two names repeat across districts (Laxmangarh, Rajgarh): their slug carries the district
        q = i["payload"]
        q["slug"] = slug(q["body"] + (" " + q["district"] if names.count(q["body"]) > 1 else ""))
    return out


def fetch(p, get):
    r = get(U)
    if r is None:
        return [], [], "no answer"
    f = {**BASE, "Period": p.get("period", "61")}
    h = _post(get, r.text, "Period", f)
    f["DistrictDropDownList"] = p["district_value"]
    h = h and _post(get, h, "DistrictDropDownList", f)
    f["PanchayatSamitiDropDownList"] = p["ulb_value"]
    h, last = _post(get, h, "PanchayatSamitiDropDownList", f, resp=True) if h else (None, None)
    if not h:
        return [], [], "postback did not answer"
    sl = p.get("slug") or slug(p["body"])
    files = [(f"councillors/RJ/{p.get('period', '61')}-{p['ulb_value']}-{sl}.html.gz", gzip.compress(h.encode()), "application/gzip")]
    election = " ".join(x for x in ("Rajasthan ULB", _selected(h, "$Election"), _selected(h, "$Period")) if x)
    soup = BeautifulSoup(h, "lxml")
    recs, seen = [], {}
    src = provenance.at(last, U)       # every step is a POST to the same url: the answer is named by its bytes
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = t.find_all("tr")
        head = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[0].find_all(["th", "td"])] if trs else []
        if "Result" not in head or "Ward No." not in head:
            continue
        for ri, tr in enumerate(trs[1:], 2):
            c = dict(zip(head, (" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"]))))
            if c.get("Result", "").lower() != "winner":
                provenance.skip_row(tr, 'skip: c.get("Result", "").lower() != "winner"')
                continue
            if c.get("ULB Name") and c["ULB Name"] != p["body"]:
                return [], files, f"page shows {c['ULB Name']}, not {p['body']}"
            ward = c.get("Ward No.") or str(len(recs) + 1)
            seen[ward] = seen.get(ward, 0) + 1
            rid = f"councillor:RJ:{sl}:{ward}" + (f"-{seen[ward]}" if seen[ward] > 1 else "")
            d = {"type": "councillor", "state": "RJ", "body": c.get("ULB Name") or p["body"], "district": c.get("District Name") or p["district"],
                 "ward_no": ward, "name": c.get("Name"), "party": c.get("Party Name"), "reservation": c.get("Ward Reservation"),
                 "votes": c.get("Votes Secured"), "gender": c.get("Gender"), "age": c.get("Age"), "category": c.get("Candidate Category"),
                 "election": election, "url": U, "ulb_value": p["ulb_value"], **src, "src_pos": {"table": ti, "row": ri}}
            recs.append((rid, {k: v for k, v in d.items() if v not in (None, "")}))
    return recs, files, "" if recs else "no winners in the table"
