"""Telangana: elected Sarpanches and Ward Members of the gram panchayats, Ordinary Elections to Gram Panchayaths 2025
(TSEC election id 189), from the SEC "Election Results - Rural" dashboard (tsec.gov.in/dashboardresults.do).

Structure (measured 2026-11-13 from dev-vps-3, Mumbai):
- Summary: POST dashboardresults.se mode=getDatanew, property(election_year)=2025, property(election_rural_urban)=R,
  property(conducting_type)=D, property(election_for)= "GP#4#GRAMPANCHAYAT" (Sarpanch) or "W#6#GRAMPANCHAYAT" (Ward Member),
  property(election)=189. Table GridView1: one row per district (31 rural districts) with the count of posts by reservation and a
  link getResultsDetails('<district id>', '0', 'GRAMPANCHAYAT'). District ids are TSEC's own (Mulugu 32, Narayanpet 33).
- Detail (one queue item): the same form with mode=getResultsDetailsnew, property(sdistrictId)=<id>, property(partyCode)=0,
  property(electionType)=GRAMPANCHAYAT. One POST, no session or token needed (it answered without a cookie).
  Sarpanch: table GridView1, rows Sl No | Mandal Name | Grampanchayat Name | Reserved for | Name of the Contesting Candidate |
  Party affiliation | Result Status (only "Elected" rows seen: 472 of 472 in Adilabad; party is "IND" everywhere: GP polls are
  non-party).
  Ward Member: one table; a row "Name of the Mandal: <b>X</b> Name of the Gram Panchayat: <b>Y</b>" opens each GP, then rows
  Sl No | Ward Name ("Ward 1") | Reserved for | Name of the Elected Candidate | Result Status ("Elected" / "Unanimous" / "--").
  Rows with "--" (no candidate elected) give no record. Adilabad: 2,404 ward rows in 292 GPs on the detail page, while the
  summary counts 3,857 wards in 472 GPs (the detail page is incomplete there: indicator, checked 2026-11-13).
- MPTC / ZPTC: the dashboard has elections 148/157 (2019) and 188 (2025) but answers "Data Not Available" (2026-11-13):
  the 2025 MPTC/ZPTC poll results are not on the site; this reader does not read them.

Payload: {"kind": "form-pri_tg", "state": "TG", "url": dashboardresults.do, "post": "sarpanch" | "ward", "district_id",
"district", "election_id" (189), "election_year" (2025), "election", "lgd_district" (LGD ZP name), "expected"}.
LGD: match() by district -> mandal -> GP name, exact (cforms/_pri.Lgd) and then a close-spelling match inside the same mandal
(difflib ratio >= 0.85, mandal 0.8, and clearly better than the next name); data["lgd_match"] says "exact" / "close" / "".
Records (type pri_member, level gp): pri:TG:gp:<lgd code or names>:head (Sarpanch) or :w<ward no> (Ward Member).
"""
import difflib
import gzip
import re

from bs4 import BeautifulSoup

import provenance
from cforms import _pri

METHOD = "html table (TSEC rural election results dashboard, district detail report after one POST)"

URL = "https://tsec.gov.in/dashboardresults.do"
POST_URL = "https://tsec.gov.in/dashboardresults.se"
FOR = {"sarpanch": "GP#4#GRAMPANCHAYAT", "ward": "W#6#GRAMPANCHAYAT"}
_lgd = None


def lgd():
    global _lgd
    if _lgd is None:
        _lgd = _pri.Lgd("TG")
    return _lgd


def form(p, mode="getResultsDetailsnew"):
    d = {"mode": mode, "property(election_year)": str(p.get("election_year", "2025")), "property(election_rural_urban)": "R",
         "property(conducting_type)": "D", "property(election_for)": FOR[p["post"]],
         "property(election)": str(p.get("election_id", "189"))}
    if mode == "getResultsDetailsnew":
        d.update({"property(sdistrictId)": p["district_id"], "property(partyCode)": "0", "property(electionType)": "GRAMPANCHAYAT"})
    return d


def cells(tr):
    return [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td", recursive=False)]


def summary(html):
    """[(district id, district, mandals, total posts)] from a getDatanew answer."""
    grid = BeautifulSoup(html or "", "lxml").find("table", id="GridView1")
    out = []
    for tr in grid.find_all("tr") if grid else []:
        a = tr.find("a", onclick=re.compile(r"getResultsDetails"))
        m = a and re.search(r"getResultsDetails\('([^']*)'", a["onclick"])
        c = cells(tr)
        if m and len(c) >= 4:
            out.append((m.group(1), c[1], _pri.digits(c[2]), _pri.digits(c[3])))
    return out


def sarpanch_rows(html):
    grid = BeautifulSoup(html or "", "lxml").find("table", id="GridView1")
    out = []
    for ri, tr in enumerate(grid.find_all("tr") if grid else [], 1):
        c = cells(tr)
        if len(c) == 7 and c[0].isdigit() and c[4]:
            out.append({"sno": c[0], "block": c[1], "body": c[2], "reservation": c[3], "name": c[4], "party": c[5],
                        "result_status": c[6], "row": ri})
    return out


def ward_rows(html):
    soup = BeautifulSoup(html or "", "lxml")
    out = []
    mandal = gp = None
    for ri, tr in enumerate(soup.find_all("tr"), 1):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 1 and "Name of the Mandal" in tds[0].get_text():
            bs = [" ".join(b.get_text(" ", strip=True).split()) for b in tds[0].find_all("b")]
            mandal, gp = (bs + [None, None])[:2]
            continue
        c = cells(tr)
        if len(c) == 5 and c[0].isdigit() and mandal:
            if not c[3] or c[3] == "--":
                continue
            m = re.fullmatch(r"(?:ward\s*-?\s*(?:no\.?)?\s*)?(\d+)", c[1], re.I)
            out.append({"sno": c[0], "block": mandal, "body": gp, "ward": c[1], "ward_no": m.group(1) if m else c[1],
                        "reservation": c[2], "name": c[3], "result_status": c[4], "row": ri})
    return out


def _close(name, options, least=0.85):
    """The one option whose spelling is close to name (ratio >= least and 0.05 above the next), else None."""
    n = _pri.norm(name)
    if not n or not options:
        return None
    sc = sorted(((difflib.SequenceMatcher(None, n, _pri.norm(o)).ratio(), o) for o in options), reverse=True)
    if sc[0][0] >= least and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 0.05):
        return sc[0][1]
    return None


def match(district, mandal, gp):
    """(lgd code, how): exact through _pri.Lgd, else close spelling of district, mandal and GP inside the LGD tree."""
    L = lgd()
    code = L.match("gp", gp, district, mandal)
    if code:
        return code, "exact"
    zps = {r[2]: r[0] for r in L.rows if r[1] == "zp"}
    zp = zps.get(district) or zps.get(_close(district, list(zps)) or "")
    if not zp:
        return "", ""
    pss = {r[2]: r[0] for r in L.rows if r[1] == "ps" and r[4] == zp}
    ps = next((c for nm, c in pss.items() if _pri.norm(nm) == _pri.norm(mandal)), None) or pss.get(_close(mandal, list(pss), 0.8) or "")   # mandals: few per district, "ECHODA" = Ichoda
    if not ps:
        return "", ""
    gps = {}
    for r in L.rows:
        if r[1] == "gp" and r[4] == ps:
            gps.setdefault(r[2], []).append(r[0])
    exact = [c for nm, cs in gps.items() if _pri.norm(nm) == _pri.norm(gp) for c in cs]
    if len(exact) == 1:
        return exact[0], "exact"
    best = _close(gp, list(gps))
    if best and len(gps[best]) == 1:
        return gps[best][0], "close"
    return "", ""


def records(html, p, r=None):
    election = p.get("election") or "Telangana 2025 gram panchayat elections"
    dist = p.get("lgd_district") or p.get("district")
    base = {"district": p.get("district"), "election": election, "url": p.get("url") or URL, "district_id": p["district_id"],
            "tsec_election_id": str(p.get("election_id", "189"))}
    trail = provenance.at(r, POST_URL) if r is not None else {"src_url": POST_URL}
    recs = []
    if p["post"] == "sarpanch":
        for x in sarpanch_rows(html):
            code, how = match(dist, x["block"], x["body"])
            rid, d = _pri.record("TG", "gp", lgd_code=code, lgd_match=how, body=x["body"], block=x["block"], post="Sarpanch",
                                 name=x["name"], party=x["party"], reservation=x["reservation"], result_status=x["result_status"],
                                 head=True, **base, **trail, src_pos={"table_id": "GridView1", "row": x["row"], "sl_no": x["sno"]})
            recs.append((rid, d))
    else:
        for x in ward_rows(html):
            code, how = match(dist, x["block"], x["body"])
            rid, d = _pri.record("TG", "gp", lgd_code=code, lgd_match=how, body=x["body"], block=x["block"], post="Ward Member",
                                 name=x["name"], ward_no=x["ward_no"], ward_name=x["ward"], reservation=x["reservation"],
                                 result_status=x["result_status"], **base, **trail,
                                 src_pos={"row": x["row"], "sl_no": x["sno"], "mandal": x["block"], "gram_panchayat": x["body"]})
            recs.append((rid, d))
    seen = {}
    for i, (rid, d) in enumerate(recs):        # the same GP name twice in a mandal without an LGD code: keep both rows
        if rid in seen:
            recs[i] = (f"{rid}-r{d['src_pos']['row']}", d)
        seen[recs[i][0]] = True
    return recs


def fetch(p, get):
    r = get(POST_URL, method="POST", data=form(p))
    if r is None:
        return [], [], "no answer"
    slug = re.sub(r"[^a-z0-9]+", "-", (p.get("district") or "").lower()).strip("-")
    files = [(f"pri/TG/{p.get('election_id', '189')}-{p['post']}-{p['district_id']}-{slug}.html.gz", gzip.compress(r.content),
              "application/gzip")]
    recs = records(r.text, p, r)
    if not recs and "Data Not Available" in r.text:
        return [], files, "data not available"
    return recs, files, "" if recs else "no rows"
