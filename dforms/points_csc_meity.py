"""Common Service Centres of India with their map point: the MeitY CSC layer on Bharatmaps (2022; 401,268 rows), as compiled by
ramSeraph/indian_facilities (release "govt-services", Bharatmaps_MeitY_CSCs_2022.parquet). Columns used: cscid, vle_name (the
village level entrepreneur who runs the centre), csc_loc (address), pincode, st_name / stcode11 / state_lgd, dt_name, dist_lgd,
blk_name, sdtname, subdt_lgd, village_na, village_co, bbox. Record id dept:points_csc_meity:<CSC id>; dept digital_services,
layer csc, area "CSC <village>", name = VLE, post "Village Level Entrepreneur (CSC operator)". Seed:
seeds/dept_points_csc_all.json; shared code dforms/_points.py.
"""
from dforms import _points

MODULE = "points_csc_meity"
METHOD = _points.METHOD
COLUMNS = ["cscid", "vle_name", "csc_loc", "pincode", "st_name", "stcode11", "state_lgd", "dt_name", "dist_lgd", "blk_name",
           "sdtname", "subdt_lgd", "village_na", "village_co"]


def make(row, n, p):
    v = _points.val
    code = v(row.get("cscid"))
    if not code:
        return None, "no CSC id"
    place = v(row.get("village_na")) or v(row.get("blk_name")) or v(row.get("dt_name"))
    vle = v(row.get("vle_name"))
    return code, dict(layer="csc", dept="digital_services", area=f"CSC {place}" if place else f"CSC {code}", office_id=code,
                      name=vle, post="Village Level Entrepreneur (CSC operator)" if vle else None, address=v(row.get("csc_loc")),
                      pin=v(row.get("pincode")), state=_points.state_of(row.get("stcode11"), row.get("state_lgd"), row.get("st_name")),
                      district=v(row.get("dt_name")), district_lgd=v(row.get("dist_lgd")), block=v(row.get("blk_name")),
                      subdistrict=v(row.get("sdtname")), subdistrict_lgd=v(row.get("subdt_lgd")), village=v(row.get("village_na")),
                      lgd_code=v(row.get("village_co")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
