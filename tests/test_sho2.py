"""Offline tests of the SHO readers dforms/sho2_*.py on FULL saved pages in tests/data/sho/ (archive.s1d.me captures, 2026-11-05).
Counts are exact for these pages."""
import json

import provenance
from esw_common import ROOT, check_records, fake_get, mod


def load_seed(name):
    return json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text(encoding="utf-8"))


# ---- sho2_mh (Satara district police, satarapolice.gov.in) ----
SAT_PAGES = (1, 8, 14, 31)


def sat_run(pages=SAT_PAGES, senior=True):
    provenance.rows_reset()
    m = mod("sho2_mh")
    p = m.items()[0]["payload"]
    routes = {f"{p['base']}/policestation?ps={n}": f"sho/mh_satara_ps{n}.html" for n in pages}
    if senior:
        routes[p["url"]] = "sho/mh_satara_senior.html"
    recs, files, why = m.fetch(p, fake_get(routes))
    return recs, files, why, provenance.rows(len(recs))


def test_sho2_mh_items_match_seed():
    s = load_seed("sho2_mh")
    assert mod("sho2_mh").items() == s and len(s) == 1
    p = s[0]["payload"]
    assert p["ps"] == list(range(1, 33)) and p["india_only"] and p["route"] == "direct" and p["dc"] == "494"


def test_sho2_mh_satara_stations_and_officers():
    recs, files, why, rows = sat_run()
    assert why == "" and len(files) == 5 and len(recs) == 15          # 11 senior officer cards + 4 stations
    check_records(recs, "sho2_mh", "police")
    lv = {}
    for _, d in recs:
        lv[d["level"]] = lv.get(d["level"], 0) + 1
    assert lv == {"district": 4, "subdivision": 7, "police_station": 4}
    assert rows == {"rows_seen": 15, "rows_used": 15, "rows_skipped": {}, "rows_not_data": {}}
    d = dict(recs)
    s1 = d["dept:sho2_mh:satara:ps:1"]
    assert s1["name"] == "श्री एस जी म्हेत्रे" and s1["sho_rank"] == "PI" and s1["phone"] == "9223006104, 9371931371"
    assert s1["area"] == "Satara City" and s1["area_regional"] == "सातारा शहर" and s1["subdivision"] == "सातारा विभाग"
    assert s1["telephone"] == "02162230580" and s1["email"] == "sataracityps.satara@mahapolice.gov.in"
    assert round(s1["lat"], 4) == 17.687 and round(s1["lon"], 4) == 73.9973 and s1["district_lgd"] == "494"
    assert len(s1["officers"]) == 12 and s1["officers"][0] == {"name": "श्री. एस. बी. मोरे", "post": "पोलीस उपनिरीक्षक", "phone": "9881484596"}
    assert s1["src_pos"] == {"page": "station", "ps": 1}
    wai = d["dept:sho2_mh:satara:ps:8"]
    assert wai["area"] == "Wai" and wai["sho_rank"] == "PI" and "officers" not in wai
    m31 = d["dept:sho2_mh:satara:ps:31"]
    assert m31["area"] == "Malharpeth" and m31["sho_rank"] == "API" and m31["rank"] == "सहा. पोलिस निरीक्षक"
    sp = [v for v in d.values() if v["post"] == "पोलिस अधीक्षक"][0]
    assert sp["level"] == "district" and sp["phone"] == "9223006101" and sp["email"] == "sp.satara@mahapolice.gov.in"
    karad = [v for v in d.values() if v["level"] == "subdivision" and v["area"] == "कराड"][0]
    assert karad["name"] == "श्रीमती. रा. सं. पाटील" and karad["phone"] == "9223006117, 9168806676"
    assert sum(1 for v in d.values() if v.get("office_type") == "unit") == 2


def test_sho2_mh_station_names_all_mapped():
    m = mod("sho2_mh")
    assert len(m.STATION_EN) == 32 and len(set(m.STATION_EN.values())) == 32


def test_sho2_mh_no_answer_and_missing_pages():
    recs, files, why, rows = sat_run(pages=(1,), senior=False)
    assert why == "" and len(recs) == 1 and len(files) == 1
    m = mod("sho2_mh")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")
