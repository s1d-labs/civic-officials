"""West Bengal: elected members of the Zilla Parishads, Panchayat Samitis and Gram Panchayats, Panchayat General Election 2023
(poll 8 July 2023, result 11 July 2023), from the West Bengal State Election Commission result portal portal.wbsec.org
("Detail Result"; linked from wbsec.wb.gov.in; the old host wbsec.gov.in does not answer).

Structure (measured 2026-11-13 from Mumbai): an AngularJS page; the tree ZP -> PS (block) -> GP is inside the page's own script
(dforms/pri_wb_tree.json, built by seeds/build_pri_wb.py with LGD codes). The result list comes from an open JSON web method, the
same call the page makes, no login, no captcha (the captcha on the portal is for the officers' login only):
  POST https://portal.wbsec.org/Index.aspx/SelectCandidateVotesinFavourPortalList
  body {'CandidateFor':'GP'|'PS'|'ZP','PollingResultDateID':'1','PanchayatDirectoryID':'<GP id | PS id | ZP id>'}
  answer {"d": "<JSON text>"}: one row per contesting candidate: SeatID, SeatName ("MOAMARI/I-1", "MOAMARI/PS-1",
  "MEKHLIGANJ/ZP-1"), SeatIndex, CandidateName, GardianName, CandidateGender, Age, CandidateCategory, PartyAffiliation,
  VoteInFavour (int), Address, ElectoralPartSerialNo, PanchayatSamity, ZillaParisad, ResidenceWard.
The answer has no "won" flag: the winner of a seat is the candidate with the most votes (status "won (most votes)"); a seat with
one candidate gives status "only candidate in the result list"; equal top votes give every top candidate with status
"tie in the result list" (indicator: a lot draw decides; check the RO's declaration). Heads (Sabhadhipati, Sabhapati, Pradhan)
are elected later by the members and are not in this answer.
Records (pri_member, role member): one per winner, with runner_up, runner_up_votes, margin, candidates (count of contestants);
src_pos {"index": row in the answer, "id": SeatID}, src_url + src_sha256 of the answer (provenance.at), cells = the raw row.
Items: one per district (ZP seats, 1 POST) and one per block (PS seats + every GP of the block: 1 + about 10 POSTs).
Record ids: pri:pri_wb:<zp|ps|gp>:<SeatID>[:<SeatIndex> on a tie].
"""
import json
import re
import time
from collections import OrderedDict
from pathlib import Path

import provenance
from dforms import _pri

METHOD = "json web method (WBSEC result portal, all candidates per seat; winner = most votes)"
MODULE = "pri_wb"
API = "https://portal.wbsec.org/Index.aspx/SelectCandidateVotesinFavourPortalList"
PAGE = "https://portal.wbsec.org/"
ELECTION = "West Bengal Panchayat General Election 2023"
POSTS = {"gp": ("Gram Panchayat Member", "গ্রাম পঞ্চায়েত সদস্য"), "ps": ("Panchayat Samiti Member", "পঞ্চায়েত সমিতি সদস্য"),
         "zp": ("Zilla Parishad Member", "জেলা পরিষদ সদস্য")}
TREE = None


def tree():
    global TREE
    if TREE is None:
        TREE = json.loads((Path(__file__).parent / "pri_wb_tree.json").read_text())
    return TREE


def items(get=None):
    out = []
    for z in tree():
        out.append({"key": f"pri_wb:zp:{z['id']}", "payload": {"reader": MODULE, "url": PAGE, "level": "zp", "zp_id": z["id"],
                    "district": z["name"], "state": "WB", "route": "direct", "expected": 0}})
        for p in z["ps"]:
            out.append({"key": f"pri_wb:ps:{p['id']}", "payload": {"reader": MODULE, "url": PAGE, "level": "ps", "zp_id": z["id"],
                        "ps_id": p["id"], "district": z["name"], "block": p["name"], "state": "WB", "route": "direct",
                        "expected": 0}})
    return out


def body_of(level, unit_id):
    return "{'CandidateFor':'%s' ,'PollingResultDateID':'1' ,'PanchayatDirectoryID':'%d' }" % (level.upper(), int(unit_id))


def call(get, level, unit_id, tries=3):
    """(response, rows) or (response or None, None) after `tries` attempts (the host drops connections now and then)."""
    r = None
    for i in range(tries):
        r = get(API, method="POST", data=body_of(level, unit_id), headers={"Content-Type": "application/json; charset=utf-8"})
        if r is not None and getattr(r, "status_code", 200) == 200:
            try:
                return r, json.loads(r.json()["d"] or "[]")
            except (ValueError, KeyError, TypeError):
                pass
        if i + 1 < tries:
            time.sleep(3 * (i + 1))
    return r, None


def seat_no(name):
    m = re.search(r"-(\d+)\s*$", name or "")
    return m.group(1) if m else ""


def records(rows, r, level, body, z, p=None):
    """Winner records of one answer. body = the GP / PS / ZP entry of the tree (name, id, lgd)."""
    seats = OrderedDict()
    for i, row in enumerate(rows):
        seats.setdefault(row.get("SeatID"), []).append((i, row))
    out = []
    post, post_bn = POSTS[level]
    for sid, cands in seats.items():
        votes = [row.get("VoteInFavour") if isinstance(row.get("VoteInFavour"), int) else _pri.int_or_none(str(row.get("VoteInFavour")))
                 for _, row in cands]
        vv = [v if v is not None else -1 for v in votes]
        top = max(vv)
        winners = [k for k, v in enumerate(vv) if v == top]
        rest = sorted((v for k, v in enumerate(vv) if k not in winners), reverse=True)
        for k in winners:
            i, row = cands[k]
            others = sorted(((vv[j], cands[j][1]) for j in range(len(cands)) if j != k), key=lambda x: -x[0])
            ru = others[0][1] if others else None
            if len(cands) == 1:
                status = "only candidate in the result list"
            elif len(winners) > 1:
                status = "tie in the result list"
            else:
                status = "won (most votes)"
            key = f"{level}:{sid}" + (f":{row.get('SeatIndex')}" if len(winners) > 1 else "")
            seat = _pri.clean(row.get("SeatName"))
            out.append(_pri.record(
                MODULE, key, state="WB", level=level, role="member", post=post, post_regional=post_bn,
                name=row.get("CandidateName"), father_name=row.get("GardianName"), gender=row.get("CandidateGender"),
                category=row.get("CandidateCategory"), party=row.get("PartyAffiliation"), votes=votes[k],
                age=_pri.int_or_none(str(row.get("Age") or "")), address=_pri.clean(str(row.get("Address") or "")).strip('"'),
                electoral_part_serial=row.get("ElectoralPartSerialNo"), residence_ward=row.get("ResidenceWard"),
                body_name=body["name"], district=z["name"], block=(p or {}).get("name") or row.get("PanchayatSamity"),
                ward=seat, ward_no=seat_no(seat), seat_id=sid,
                lgd_code=body.get("lgd"), lgd_match=body.get("lgd_match"), lgd_ratio=body.get("lgd_ratio"),
                wbsec_body_id=body["id"], election=ELECTION, election_year=2023, poll_date="2023-07-08",
                result_date="2023-07-11", status=status, candidates=len(cands),
                runner_up=(ru or {}).get("CandidateName"), runner_up_party=(ru or {}).get("PartyAffiliation"),
                runner_up_votes=others[0][0] if others and others[0][0] >= 0 else None,
                margin=(top - rest[0]) if rest and top >= 0 and rest[0] >= 0 else None,
                source=PAGE, src_pos={"index": i, "id": sid}, cells={kk: vv2 for kk, vv2 in row.items()},
                **provenance.at(r, API)))
    return out


def fetch(p, get):
    z = next((x for x in tree() if x["id"] == p["zp_id"]), None)
    if z is None:
        return [], [], "district not in tree"
    recs, bad, units = [], [], []
    if p["level"] == "zp":
        units.append(("zp", z, None))
    else:
        ps = next((x for x in z["ps"] if x["id"] == p["ps_id"]), None)
        if ps is None:
            return [], [], "block not in tree"
        units.append(("ps", ps, ps))
        units += [("gp", g, ps) for g in ps["gp"]]
    for level, body, ps in units:
        r, rows = call(get, level, body["id"])
        if rows is None:
            bad.append(f"{level}:{body['id']}")
            continue
        recs += records(rows, r, level, body, z, ps)
    if bad:      # the item fails whole (no records) so the hub runs it again: a done item with missing units is never retried
        return [], [], f"no answer for {len(bad)} of {len(units)} units: {', '.join(bad[:5])}"
    return recs, [], "" if recs else "no rows"
