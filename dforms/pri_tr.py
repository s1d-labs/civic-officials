"""Tripura: elected members of the Village Committees (VC) of the Tripura Tribal Areas Autonomous District Council (TTAADC),
general election 2026, from the State Election Commission's live result board sec-results.tripura.gov.in/sec (linked from
sec.tripura.gov.in "Result for TTAAD Village Committee Election 2026").

Structure (measured 2026-11-13 from Mumbai): the board is a static page (app.js) that POSTs JSON
{"key": "GP_Results_Summary"} to /electionresultscheduler/dashboard/get-data. One answer (5.4 MB) holds the whole state:
data[] = district {district_id (= LGD district code), district_name, block_results[] = block {block_id (= LGD code of the
block, the same id space as lgd.traditional_local_bodies.intermediate_panchayat_code), block_name, gp_results[] = village
committee {gp_id (SEC id), gp_name, constituency_result[] = seat {constituency_no_name "East Manu-I : Seat No-1 [UR]",
constituency_code, is_declared, winning_candidate_name, winning_party_name, candidate_data[] = every candidate {candidate_name,
party_name, party_full_name, gender, caste, vote_secured, is_winner, is_nota}}}}}.
On 2026-11-13: 8 districts, 52 blocks, 587 village committees, 4,594 seats, all declared.

Village Committees are the village-level local bodies of the TTAADC (Sixth Schedule area), in place of gram panchayats; the
LGD lists them as traditional local bodies (state 16, level Village), not in lgd.pri_local_bodies. Records: level "gp",
body_type "village_committee", role "member", post "Village Committee Member". The VC chairman is chosen later by the members
and is not on this board. The 2024 three-tier panchayat results (non-ADC area: 606 gram panchayats, 35 panchayat samitis,
8 zilla parishads) are not published on sec.tripura.gov.in ("no content available" on 2026-11-13).

One record per declared seat (the winner), with every candidate of the seat kept in "candidates" (all fields). A seat with one
candidate (no votes counted) gets status "elected unopposed" (1,644 of 4,594 on 2026-11-13). Record id:
pri:pri_tr:vc2026:<constituency_code>.
"""
import json
import re

from dforms import _pri

METHOD = "json api (SEC Tripura result board, dashboard/get-data GP_Results_Summary)"     # source trail (provenance.py)
MODULE = "pri_tr"
BOARD = "https://sec-results.tripura.gov.in/sec"
API = "https://sec-results.tripura.gov.in/electionresultscheduler/dashboard/get-data"
ELECTION = "TTAADC Village Committee General Election 2026"


def items(get=None):
    return [{"key": "pri_tr:vc2026", "payload": {"reader": MODULE, "url": API, "board": BOARD, "api_key": "GP_Results_Summary",
                                                  "state": "TR", "india_only": True, "route": "direct"}}]


def seat_parts(s):
    """'East Manu-I : Seat No-1 [UR]' -> ('East Manu-I', '1', 'UR')."""
    s = _pri.clean(s)
    m = re.match(r"^(.*?)\s*:\s*Seat\s*No\.?\s*-?\s*(\d+)\s*(?:\[([^\]]*)\])?\s*$", s, re.I)
    if not m:
        return s, "", ""
    return m.group(1).strip(), m.group(2), (m.group(3) or "").strip()


def records(data, url):
    out = []
    for di, d in enumerate(data or []):
        for bi, b in enumerate(d.get("block_results") or []):
            for gi, g in enumerate(b.get("gp_results") or []):
                for ci, c in enumerate(g.get("constituency_result") or []):
                    if not c.get("is_declared"):
                        continue
                    cands = c.get("candidate_data") or []
                    win = next((k for k in cands if k.get("is_winner") == 1 and not k.get("is_nota")), None)
                    name = (win or {}).get("candidate_name") or c.get("winning_candidate_name")
                    if not name:
                        continue
                    ward, seat_no, cat = seat_parts(c.get("constituency_no_name"))
                    code = c.get("constituency_code")
                    key = f"vc2026:{code}" if code is not None else f"vc2026:{d.get('district_id')}-{b.get('block_id')}-{g.get('gp_id')}-{ci}"
                    votes = (win or {}).get("vote_secured")
                    out.append(_pri.record(
                        MODULE, key, state="TR", level="gp", role="member", body_type="village_committee",
                        post="Village Committee Member", name=name, party=(win or {}).get("party_name") or c.get("winning_party_name"),
                        party_full=(win or {}).get("party_full_name"), gender=(win or {}).get("gender"), category=cat,
                        caste=(win or {}).get("caste"), votes=votes if isinstance(votes, int) else _pri.int_or_none(str(votes or "")),
                        body_name=g.get("gp_name"), sec_body_id=g.get("gp_id"), block=b.get("block_name"),
                        block_lgd_code=str(b["block_id"]) if b.get("block_id") is not None else None,
                        district=d.get("district_name"),
                        district_lgd_code=str(d["district_id"]) if d.get("district_id") is not None else None,
                        ward=ward, ward_no=seat_no, constituency=c.get("constituency_no_name"), constituency_code=code,
                        election=ELECTION, election_year=2026,
                        status="elected unopposed" if len([x for x in cands if not x.get("is_nota")]) == 1 else "won",
                        declared_by=c.get("declared_by"), winning_form=c.get("winning_form"),
                        candidates=cands,
                        source=BOARD, src_url=url,
                        src_pos={"index": [di, bi, gi, ci], "id": code,
                                 "path": f"data[{di}].block_results[{bi}].gp_results[{gi}].constituency_result[{ci}]"}))
    return out


def fetch(p, get):
    url = p.get("url") or API
    r = get(url, method="POST", data=json.dumps({"key": p.get("api_key", "GP_Results_Summary")}),
            headers={"Content-Type": "application/json", "Referer": BOARD + "/"})
    if r is None:
        return [], [], "no answer"
    try:
        j = r.json()
    except ValueError:
        return [], [], "not json"
    data = j.get("data")
    if isinstance(data, str):
        data = json.loads(data)
    recs = records(data, url)
    return recs, [], "" if recs else "no declared seats"
