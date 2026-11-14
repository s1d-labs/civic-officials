"""Schools of India with their map point: Bharatmaps school layer (NIC, UDISE+ school codes; 1,466,160 rows), as compiled by
ramSeraph/indian_facilities (release "education", Bharatmaps_Schooldata.parquet). Columns used: schcd (UDISE code), schname,
management, school_cat, school_typ, location (Rural / Urban), pincode, stcode11 / lgd_state_, dtname, lgd_distri, sdtname,
subdt_lgd, vilname, vilcode11, bbox (the point). Record id dept:points_school_bm:<UDISE code>; dept education, layer school,
area = school name (no head teacher in this file: civic-india joins the UDISE+ head teacher by office_id). Shared code and the
item format: dforms/_points.py. Seed: seeds/dept_points_school_all.json.
"""
from dforms import _points

MODULE = "points_school_bm"
METHOD = _points.METHOD
COLUMNS = ["schcd", "schname", "management", "school_cat", "school_typ", "location", "pincode", "stcode11", "lgd_state_",
           "dtname", "lgd_distri", "sdtname", "subdt_lgd", "vilname", "vilcode11"]


def make(row, n, p):
    v = _points.val
    code, name = v(row.get("schcd")), v(row.get("schname"))
    if not code or not name:
        return None, "no UDISE code or name"
    return code, dict(layer="school", dept="education", area=name, office_id=code, udise=code,
                      state=_points.state_of(row.get("stcode11"), row.get("lgd_state_")), district=v(row.get("dtname")),
                      district_lgd=v(row.get("lgd_distri")), subdistrict=v(row.get("sdtname")), subdistrict_lgd=v(row.get("subdt_lgd")),
                      village=v(row.get("vilname")), village_census=v(row.get("vilcode11")), pin=v(row.get("pincode")),
                      mgmt=v(row.get("management")), category=v(row.get("school_cat")), school_type=v(row.get("school_typ")),
                      rural_urban=v(row.get("location")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
