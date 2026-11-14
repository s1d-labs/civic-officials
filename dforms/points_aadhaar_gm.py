"""Aadhaar enrolment and update centres with their map point: the Grammanchitra Aadhaar centre layer on Bharatmaps (79,023 rows),
as compiled by ramSeraph/indian_facilities (release "govt-services", Bharatmaps_Grammanchitra_Aadhar_Centers.parquet). Columns
used: objectid, center_nam, center_add, vtc, post_offic, pincode, enrolment (services), stcode11 / state_lgd / state, dtname,
dist_lgd, sdtname, subdt_lgd, block_name, gp_name, vilname11, vil_lgd, bbox. The file has no centre code: record id
dept:points_aadhaar_gm:<objectid>; dept digital_services, layer aadhaar, area = centre name. Seed:
seeds/dept_points_aadhaar_all.json; shared code dforms/_points.py.
"""
from dforms import _points

MODULE = "points_aadhaar_gm"
METHOD = _points.METHOD
COLUMNS = ["objectid", "center_nam", "center_add", "vtc", "post_offic", "pincode", "enrolment", "stcode11", "state_lgd", "state",
           "dtname", "dist_lgd", "sdtname", "subdt_lgd", "block_name", "gp_name", "vilname11", "vil_lgd"]


def make(row, n, p):
    v = _points.val
    oid, name = v(row.get("objectid")), v(row.get("center_nam"))
    if not oid or not name:
        return None, "no object id or centre name"
    return oid, dict(layer="aadhaar", dept="digital_services", area=f"Aadhaar centre: {name}", address=v(row.get("center_add")),
                     place=v(row.get("vtc")), post_office=v(row.get("post_offic")), pin=v(row.get("pincode")),
                     services=v(row.get("enrolment")),
                     state=_points.state_of(row.get("stcode11"), row.get("state_lgd"), row.get("state")),
                     district=v(row.get("dtname")), district_lgd=v(row.get("dist_lgd")), subdistrict=v(row.get("sdtname")),
                     subdistrict_lgd=v(row.get("subdt_lgd")), block=v(row.get("block_name")), gp=v(row.get("gp_name")),
                     village=v(row.get("vilname11")), lgd_code=v(row.get("vil_lgd")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
