"""Fair price shops (PDS ration shops) of India with their map point: the PDS layer of the Department of Food and Public
Distribution on Bharatmaps (2023; 423,738 rows), as compiled by ramSeraph/indian_facilities (release "govt-services",
Bharatmaps_DoFD_PDS_2023.parquet). Columns used: fpscode (the state's FPS code, the same code as the state ePoS FPS lists
read by dforms/civic_fps*_<st>.py), statecode / stcode11 / state_lgd, dtname, dist_lgd, sdtname, subdt_lgd, block_name,
block_lgd, gp_name, gp_code, vilname11, vil_lgd, bbox. The file names no shop keeper: area "Fair price shop <code>"; civic-india
takes the dealer from the ePoS rows with the same code. Record id dept:points_fps_dofd:<state>-<FPS code>; dept food_supplies,
layer fps. Seed: seeds/dept_points_fps_all.json; shared code dforms/_points.py.
"""
from dforms import _points

MODULE = "points_fps_dofd"
METHOD = _points.METHOD
COLUMNS = ["fpscode", "statecode", "stcode11", "state_lgd", "stname", "dtname", "dist_lgd", "sdtname", "subdt_lgd", "block_name",
           "block_lgd", "gp_name", "gp_code", "vilname11", "vil_lgd"]


def make(row, n, p):
    v = _points.val
    code = v(row.get("fpscode"))
    if not code:
        return None, "no FPS code"
    st = _points.state_of(row.get("stcode11"), row.get("state_lgd"), row.get("statecode"), row.get("stname"))
    return f"{st or 'x'}-{code}", dict(layer="fps", dept="food_supplies", area=f"Fair price shop {code}", office_id=code, fps_id=code,
                                      state=st, district=v(row.get("dtname")), district_lgd=v(row.get("dist_lgd")),
                                      subdistrict=v(row.get("sdtname")), subdistrict_lgd=v(row.get("subdt_lgd")),
                                      block=v(row.get("block_name")), block_lgd=v(row.get("block_lgd")), gp=v(row.get("gp_name")),
                                      gp_lgd=v(row.get("gp_code")), village=v(row.get("vilname11")), lgd_code=v(row.get("vil_lgd")))


def fetch(p, get):
    return _points.fetch(p, get, MODULE, make, COLUMNS)
