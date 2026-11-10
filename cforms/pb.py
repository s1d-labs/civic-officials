"""Punjab: LBPAMS public result API (lbpams.punjab.gov.in, the JSON behind /public-result/). India only.

One POST per election type returns every winner of the Municipal General Election 2026 (poll 26.05.2026): type 4 = municipal
corporations (450), 5 = municipal councils (1,431), 6 = nagar panchayats (259); 2,140 in 111 bodies. One queue item = one type.
Not here: the five corporations elected in December 2024 (Amritsar, Jalandhar, Ludhiana, Patiala, Phagwara); neither this API
nor sec.punjab.gov.in lists them.
"""
import gzip
import json
import re

URL = "https://lbpams.punjab.gov.in/prodapi/api/ResultDeclarationEndpoint/GetPublicResultReportDetailed1"
TYPES = {4: "Municipal Corporation", 5: "Municipal Council", 6: "Nagar Panchayat"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def record(x, body_type):
    x = {k: " ".join(v.split()) if isinstance(v, str) else v for k, v in x.items()}
    m = re.search(r"(\d+)", x.get("WardName") or "")
    ward_no = str(int(m.group(1))) if m else (x.get("WardName") or "").strip()
    d = {"type": "councillor", "state": "PB", "body": x.get("LocalBodyName"), "body_type": body_type, "district": x.get("DistrictName"),
         "ward_no": ward_no, "ward": x.get("WardName"), "name": x.get("CandidateName"), "father_name": x.get("FatherName"),
         "party": x.get("PartyName"), "votes": x.get("TotalVotes"), "runner_up_votes": x.get("SecondHighestVotes"),
         "margin": x.get("WinningMargin"), "won_by": x.get("WonBy"), "unopposed": x.get("IsUnOppossed"),
         "photo": x.get("CandidateImage"), "status": x.get("Status"), "election": "Punjab 2026", "url": URL}
    return f"councillor:PB:{slug(d['body'] or '')}:{ward_no}", {k: v for k, v in d.items() if v not in (None, "")}


def fetch(p, get):
    t = int(p["election_type"])
    body = {"stateMasterId": 1, "districtMasterId": 0, "assemblyMasterId": 0, "electionTypeMasterIds": [t], "searchText": "",
            "pageNumber": 1, "pageSize": 5000}
    r = get(p.get("url", URL), method="POST", data=json.dumps(body), headers={"Content-Type": "application/json"})
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/PB/lbpams-2026-type{t}.json.gz", gzip.compress(r.content), "application/gzip")]
    try:
        js = r.json()
    except ValueError:
        return [], files, "not json"
    rows = [x for x in js.get("data") or [] if (x.get("Status") or "Winner") == "Winner"]
    if js.get("totalCount") and js["totalCount"] > len(js.get("data") or []):
        return [], files, f"only {len(js['data'])} of {js['totalCount']} rows"
    recs = [record(x, TYPES.get(t)) for x in rows]
    return recs, files, "" if recs else "no winners"
