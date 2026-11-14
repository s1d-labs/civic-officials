"""Anganwadi centres of India with their map point: the ICDS anganwadi layer of PM GatiShakti (Ministry of WCD; 1,224,038 rows),
as compiled by ramSeraph/indian_facilities (release "health", GatiShakti_ICDS_Anganvadis.parquet). Columns used: awc_code,
awc_name, project (ICDS project), sector, state_ut / stcode_lg / st_2011, district, dtcode_lg, taluka, sdtcode_lg, vil_name11,
vil_2011, bbox. Codes are written as floats ("31587010108.0"); the reader drops ".0". Record id dept:points_awc_gs:<AWC code>
(-2, -3 ... when a code repeats in one item); dept women_child, layer anganwadi, area = centre name. Seed:
seeds/dept_points_awc_all.json; shared code dforms/_points.py.
"""
from dforms import _points

MODULE = "points_awc_gs"
METHOD = _points.METHOD
COLUMNS = ["awc_code", "awc_name", "project", "sector", "state_ut", "stcode_lg", "st_2011", "district", "dtcode_lg", "taluka",
           "sdtcode_lg", "vil_name11", "vil_2011"]


def make(row, n, p):
    v = _points.val
    code, name = v(row.get("awc_code")), v(row.get("awc_name"))
    if not code and not name:
        return None, "no AWC code or name"
    st = _points.state_of(row.get("stcode_lg"), row.get("st_2011"), row.get("state_ut"))
    return code or f"r{n}", dict(layer="anganwadi", dept="women_child", area=f"Anganwadi {name}" if name and not name.lower().startswith("anganwadi") else name or f"Anganwadi {code}",
                                 office_id=code, state=st, district=v(row.get("district")), district_lgd=v(row.get("dtcode_lg")),
                                 subdistrict=v(row.get("taluka")), subdistrict_lgd=v(row.get("sdtcode_lg")),
                                 village=v(row.get("vil_name11")), village_census=v(row.get("vil_2011")),
                                 icds_project=v(row.get("project")), sector=v(row.get("sector")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
