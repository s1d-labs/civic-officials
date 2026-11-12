"""West Bengal: elected ward councillors of the municipal general elections (Kolkata Municipal Corporation, December 2021; 108
municipalities and 4 corporations, February-March 2022; later polls and bye-elections), from the State Election Commission's
results portal "MUNICIPAL GENERAL ELECTIONS, 2022" (portal.wbme.org, linked from wbsec.wb.gov.in), page "Detailed Result".

The page is an AngularJS app on ASP.NET page methods (POST, JSON body, answer {"d": "<JSON text>"}); no login, no captcha:
- Index.aspx/PopulateDistrictWiseMunicipality {}: 22 districts -> subdivisions -> 129 bodies (ID, Name). Kolkata appears as
  16 boroughs ("KOLKATA MUNICIPAL CORPORATION BOROUGH - I" = wards 1-9 ...); ward numbers are the corporation's own (1-144).
- Index.aspx/SelectMunicipalityWisePollResultDate {"MunicipalityDirectoryID": id}: the polls with results (ID, ElectionType,
  PollResultDate dd/mm/yyyy). Empty for Howrah (no election since its board's term ended in 2018).
- Index.aspx/SelectCandidateVotesinFavourPortalList {MunicipalityDirectoryID, MunicipalitySeatID: 0 (= all seats),
  PanchayatPollDateID}: every candidate of every seat: SeatName "WARD-7", SeatIndex (rank, 1 = most votes), CandidateName,
  GardianName, Age, CandidateGender, CandidateCategory, PartyAffiliation (AITC, BJP, CPI(M) ...), Address, ResidenceWard,
  ElectoralPartSerialNo, VoteInFavour.
The portal names no winner: the winner of a seat is the candidate with the most votes (SeatIndex 1); a tie for first place
is kept with "tie": true. A seat of a later poll (bye-election) replaces the same seat of an earlier one. Every candidate is kept in
the record ("candidates") and every answer goes to the bucket (councillors/WB/).
Tested 2026-11-12 from dev-vps-3 (Mumbai): Alipurduar (ID 220, poll 3, result 02/03/2022) 83 candidates, 20 wards; KMC
borough I (ID 162, poll 1, result 21/12/2021) 57 candidates, wards 1-9. India-only or not: not tested from abroad.
Queue items: seeds/councillors_cw_wb.json, one per body, with the LGD code (cw_wb_lgd() below: 129 bodies -> 113 LGD bodies,
Kolkata's 16 boroughs share 250299). Record id councillor:WB:<lgd code or wbme-<ID>>:<ward no>.
"""
import datetime
import gzip
import json
import re

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://portal.wbme.org/Index.aspx/"
ELECTION = "West Bengal municipal general elections 2021-22 (State Election Commission)"
HEADERS = {"Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest"}


def call(get, method, body):
    r = get(BASE + method, method="POST", data=json.dumps(body), headers=HEADERS)
    if r is None:
        return None, None
    try:
        return json.loads(json.loads(r.text)["d"] or "[]"), r.content
    except (ValueError, KeyError, TypeError):
        return None, r.content


def norm(s):
    return " ".join(str(s if s is not None else "").replace("\xa0", " ").replace("Â", "").split())


def rdate(s):
    try:
        return datetime.datetime.strptime(s or "", "%d/%m/%Y").date()
    except ValueError:
        return datetime.date.min


def winners(cands, poll, p):
    """Candidates of one poll -> {ward no: record data}."""
    seats = {}
    for c in cands:
        seats.setdefault(norm(c.get("SeatName")), []).append(c)
    out = {}
    for seat, cs in seats.items():
        m = re.search(r"(\d+)", seat)
        if not m:
            continue
        votes = [c.get("VoteInFavour") if isinstance(c.get("VoteInFavour"), int) else -1 for c in cs]
        top = max(votes)
        first = [c for c, v in zip(cs, votes) if v == top]
        w = sorted(first, key=lambda c: c.get("SeatIndex") or 99)[0]
        rest = sorted((v for v in votes if v != top or len(first) > 1), reverse=True)
        d = {"type": "councillor", "state": "WB", "body": norm(w.get("PanchayatSamity")) or p.get("body"),
             "body_en": p.get("body_en"), "lgd_code": p.get("lgd_code"), "district": norm(w.get("ZillaParisad")) or p.get("district"),
             "ward_no": str(int(m.group(1))), "ward_name": seat, "seat_id": w.get("SeatID"), "position": "Councillor",
             "name": norm(w.get("CandidateName")), "father_or_husband": norm(w.get("GardianName")), "age": norm(w.get("Age")),
             "gender": norm(w.get("CandidateGender")), "category": norm(w.get("CandidateCategory")),
             "party": norm(w.get("PartyAffiliation")), "address": norm(w.get("Address")),
             "residence_ward": norm(w.get("ResidenceWard")), "electoral_roll_part_serial": norm(w.get("ElectoralPartSerialNo")),
             "votes": str(top) if top >= 0 else None,
             "margin": str(top - rest[0]) if rest and top >= 0 and len(first) == 1 else None,
             "tie": True if len(first) > 1 else None, "single_candidate": True if len(cs) == 1 else None,
             "candidates": cs, "n_candidates": len(cs), "election": f"{ELECTION}: {norm(poll.get('ElectionType'))}, result "
             f"{norm(poll.get('PollResultDate'))}", "result_date": norm(poll.get("PollResultDate")), "poll_id": poll.get("ID"),
             "url": "https://portal.wbme.org/", "wbme_id": p.get("wbme_id")}
        out[d["ward_no"]] = {k: v for k, v in d.items() if v not in (None, "")}
    return out


def fetch(p, get):
    mid = p["wbme_id"]
    polls, raw = call(get, "SelectMunicipalityWisePollResultDate", {"MunicipalityDirectoryID": mid})
    if polls is None:
        return [], [], "no answer (poll list)"
    files = [(f"councillors/WB/wbme-{mid}-polls.json.gz", gzip.compress(raw), "application/gzip")]
    if not polls:
        return [], files, "no poll with results (body under an administrator?)"
    seats = {}
    for poll in sorted(polls, key=lambda x: rdate(x.get("PollResultDate"))):
        cands, raw = call(get, "SelectCandidateVotesinFavourPortalList",
                          {"MunicipalityDirectoryID": str(mid), "MunicipalitySeatID": "0", "PanchayatPollDateID": str(poll.get("ID"))})
        if cands is None:
            return [], files, f"no answer (results of poll {poll.get('ID')})"
        files.append((f"councillors/WB/wbme-{mid}-poll{poll.get('ID')}.json.gz", gzip.compress(raw), "application/gzip"))
        seats.update(winners(cands, poll, p))      # a later poll (bye-election) replaces the seat
    place = p.get("lgd_code") or f"wbme-{mid}"
    recs = [(f"councillor:WB:{place}:{w}", d) for w, d in sorted(seats.items(), key=lambda x: int(x[0]))]
    return recs, files, "" if recs else "no candidates"


def items(get):
    """Queue items from the portal's own body list (the seed file holds the same list with LGD codes added by hand)."""
    ds, _ = call(get, "PopulateDistrictWiseMunicipality", {})
    out = []
    for dist in ds or []:
        for sub in dist.get("SubDivisions") or []:
            for m in sub.get("Municipalities") or []:
                out.append({"key": f"cw-wb-wbme-{m['ID']}", "payload": {"kind": "form-cw_wb", "state": "WB", "url": "https://portal.wbme.org/",
                            "wbme_id": m["ID"], "body": norm(m.get("Name")), "district": norm(dist.get("Name"))}})
    return out
