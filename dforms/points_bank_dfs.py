"""Bank branches of India with their map point: the Department of Financial Services bank branch layer on Bharatmaps (2022;
168,955 rows), as compiled by ramSeraph/indian_facilities (release "banking", Bharatmaps_DFS_Bank_Branches_2022.parquet).
Columns used: br_ifsc_cd, bank_name, br_name, br_add, br_pin_cod, br_city, br_mgr_nam, br_mgr_lan (branch landline), br_mgr_mob,
stcode11 / state_cd / state_name, dtname, sdtname, blkname, gpname, gpcode, br_type, bbox. Record id
dept:points_bank_dfs:<IFSC> (or the row number when the IFSC is missing); dept banking, layer bank_branch, area "<bank>, <branch>",
post "Branch Manager", name = manager when the file names one. The RBI IFSC list (dforms/central_banking.py) has the same
branches without a point. Seed: seeds/dept_points_bank_all.json; shared code dforms/_points.py.
"""
from dforms import _esw, _points

MODULE = "points_bank_dfs"
METHOD = _points.METHOD
COLUMNS = ["br_ifsc_cd", "bank_name", "br_name", "br_add", "br_pin_cod", "br_city", "br_mgr_nam", "br_mgr_lan", "br_mgr_mob",
           "stcode11", "state_cd", "state_name", "stname", "dtname", "sdtname", "blkname", "gpname", "gpcode", "br_type"]


def make(row, n, p):
    v = _points.val
    ifsc = (v(row.get("br_ifsc_cd")) or "").upper().replace(" ", "")
    bank, br = v(row.get("bank_name")), v(row.get("br_name"))
    if not bank and not br:
        return None, "no bank or branch name"
    ok = len(ifsc) == 11 and ifsc[4] == "0"
    return ifsc if ok else f"r{n}", dict(
        layer="bank_branch", dept="banking", area=", ".join(x for x in (bank, br) if x), post="Branch Manager",
        name=v(row.get("br_mgr_nam")), phone=_esw.phones(v(row.get("br_mgr_lan")) or "", v(row.get("br_mgr_mob")) or "") or None,
        bank=bank, ifsc=ifsc if ok else None, office_id=ifsc if ok else None, address=v(row.get("br_add")),
        pin=v(row.get("br_pin_cod")), city=v(row.get("br_city")),
        state=_points.state_of(row.get("stcode11"), row.get("state_cd"), row.get("state_name"), row.get("stname")),
        district=v(row.get("dtname")), subdistrict=v(row.get("sdtname")), block=v(row.get("blkname")), gp=v(row.get("gpname")),
        gp_lgd=v(row.get("gpcode")), branch_type=v(row.get("br_type")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
