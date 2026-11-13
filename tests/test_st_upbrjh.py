"""State-level readers of Uttar Pradesh, Bihar and Jharkhand (dforms/st_up_*, st_br_*, st_jh_*): saved pages only, no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import _field, _state, st_br_cmo, st_br_phone, st_br_police, st_jh_police, st_jh_whoswho, st_lgd_upbrjh, st_up_police  # noqa: E402

D = Path(__file__).parent / "data"
MODULES = (st_br_cmo, st_br_phone, st_br_police, st_jh_police, st_jh_whoswho, st_up_police)


class Resp:
    def __init__(self, content, url=""):
        self.content, self.status_code, self.url = content, 200, url


def by_id(recs):
    out = dict(recs)
    assert len(out) == len(recs), "record ids repeat"
    return out


def test_methods_and_seeds():
    for m in MODULES:
        assert m.METHOD
    for st in ("up", "br", "jh"):
        items = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert items and len({i["key"] for i in items}) == len(items)
        for i in items:
            p = i["payload"]
            assert p["state"] == st.upper() and p["route"] in ("abroad", "proxy", "direct") and isinstance(p["india_only"], bool)
            assert (ROOT / "dforms" / f"{p['reader']}.py").exists()


def test_divisions_cover_every_district_once():
    import subprocess  # noqa: F401  (no DB here: the counts are the LGD counts of 2026-11-13)
    for st, n_div, n_dist in (("UP", 18, 75), ("BR", 9, 38), ("JH", 5, 24)):
        div = _state.divisions(st)
        codes = [c for v in div.values() for c in v]
        assert len(div) == n_div and len(codes) == n_dist == len(set(codes))
        assert set(codes) == set(st_lgd_upbrjh.DISTRICTS[st].values())
    assert _state.districts_of("UP", "Agra Range") == ("Agra", ["118", "143", "166", "167"])


def test_lgd_district_names():
    d = st_lgd_upbrjh.district
    assert d("UP", "SP, Kanpur Dehat") == ("156", "Kanpur Dehat")
    assert d("UP", "SSP Kanpur") == ("157", "Kanpur Nagar")
    assert d("BR", "Bettiah(West Champaran)") == ("211", "Pashchim Champaran")
    assert d("JH", "SP City, Dhanbad") == ("325", "Dhanbad")
    assert d("JH", "Zonal, IG") == ("", "")


def test_jh_whoswho_department_and_designation_pages():
    url = "https://jharkhand.gov.in/PDepartment/WebDirectory?department=0bfb179af3c357296c35d64d10a7c0b3"
    recs = by_id(st_jh_whoswho.parse((D / "st_jh_whoswho_dept_personnel.html").read_text(), url))
    assert len(recs) == 15
    sec = recs["dept:st_jh_whoswho:department-of-personnel-administrative-reforms-rajbhasha:secretary:shri-prawin-kumar-toppo-ias"]
    assert sec["post_kind"] == "secretary" and sec["service"] == "IAS" and sec["level"] == "state" and sec["state_code"] == "20"
    assert sec["src_pos"] == {"card": 2} and sec["src_url"] == url and sec["body_kind"] == "department"
    secys = st_jh_whoswho.parse((D / "st_jh_whoswho_post_secretary.html").read_text(), "u")
    assert len(secys) == 26 and {d["post_kind"] for _, d in secys} == {"secretary"}
    assert st_jh_whoswho.kind("Secretary to Honourable CM") == "secretary"
    assert len(st_jh_whoswho.items()) == 34 + 7


def test_jh_police_zone_and_hq():
    url = "https://www.jhpolice.gov.in/imp-contacts?field_spcon_location_nid=56780"
    recs = by_id(st_jh_police.parse((D / "st_jh_police_bokaro.html").read_text(), url, "56780"))
    assert len(recs) == 12
    ig = next(d for d in recs.values() if d["post"] == "Zonal, IG")
    assert ig["level"] == "division" and ig["division"] == "Bokaro Zone" and ig["post_kind"] == "igp"
    assert ig["email"] == "ig-bokaro@jhpolice.gov.in" and "districts" not in ig
    ssp = next(d for d in recs.values() if d["post"] == "SSP, Dhanbad")
    assert ssp["level"] == "district" and ssp["district_code"] == "325" and ssp["name"] == "Shri Prabhat Kumar"
    assert "9431120900" in ssp["phone"] and "(residence)" in ssp["phone"] and set(ssp["src_pos"]) == {"table", "row"}
    hq = by_id(st_jh_police.parse((D / "st_jh_police_all.html").read_text(), "u"))
    dgp = next(d for d in hq.values() if d.get("post") == "DGP")
    assert dgp["name"] == "Smt.Tadasha Mishra" and dgp["post_kind"] == "dgp" and dgp["phone"].startswith("0651-2400737")
    cs = next(d for d in hq.values() if d.get("post") == "Chief Secretary")
    assert cs["body"] == "Home Department" and cs["post_kind"] == "chief_secretary"


def test_up_police_pages():
    z = st_up_police.parse((D / "st_up_police_zoneagra.html").read_text(), "u", "zoneagra")
    assert len(z) == 2
    adg = dict(z)["dept:st_up_police:zoneagra:ips:1"]
    assert adg["level"] == "division" and adg["division"] == "Agra Zone" and adg["phone"] == "9454400178, 0562-2265736"
    assert adg["post_kind"] == "adgp" and adg["name"] == "SUVENDRA KR.BHAGAT" and "districts" not in adg
    r = dict(st_up_police.parse((D / "st_up_police_rangeagra.html").read_text(), "u", "rangeagra"))
    dig = r["dept:st_up_police:rangeagra:ips:1"]
    assert dig["post_kind"] == "dig" and dig["districts"] == ["118", "143", "166", "167"]
    hq = by_id(st_up_police.parse((D / "st_up_police_dgphq.html").read_text(), "u", "dgphq", True))
    assert len(hq) == 33
    dgp = hq["dept:st_up_police:dgphq:ips:1"]
    assert dgp["name"] == "RAJEEV KRISHNA" and dgp["post_kind"] == "dgp" and dgp["level"] == "state"
    assert hq["dept:st_up_police:dgphq:ips:2"]["post_kind"] == "adgp"
    dist = st_up_police.parse((D / "st_up_police_agra.html").read_text(), "u", "agra")
    assert dist and all(d["level"] == "district" and d["district_code"] == "118" for _, d in dist)
    items = st_up_police.items_from_home((D / "st_up_police_home.html").read_text())
    slugs = {i["payload"]["slug"] for i in items}
    assert len(items) == 121 and {"dgphq", "zoneagra", "rangeagra", "commlko"} <= slugs


def test_br_cmo_pdfs():
    c = by_id(st_br_cmo.parse(_field.pdf_text((D / "st_br_cmo_commissioner.pdf").read_bytes()), "u", "commissioner"))
    assert len(c) == 9
    bh = c["dept:st_br_cmo:commissioner:1"]
    assert bh["division"] == "Bhagalpur" and bh["districts"] == ["192", "190"] and bh["phone"] == "9473191433"
    assert bh["email"] == "divcom-bhg-bih@nic.in" and bh["src_pos"]["line_text"].strip().startswith("1")
    assert {d["division"] for d in c.values()} == set(_state.divisions("BR"))
    dm = st_br_cmo.parse(_field.pdf_text((D / "st_br_cmo_dm.pdf").read_bytes()), "u", "dm")
    assert len(dm) == 38 and len({d["district_code"] for _, d in dm}) == 38


def test_br_police_json():
    phq = st_br_police.parse(json.loads((D / "st_br_police_phq_p1.json").read_text()), "u", "phq")
    assert len(phq) == 20
    dgp = dict(phq)["dept:st_br_police:phq:2"]
    assert dgp["post"] == "DGP, Bihar, Patna." and dgp["post_kind"] == "dgp" and "9031829119" in dgp["phone"]
    assert dgp["src_pos"] == {"index": 2, "id": "2", "page": 1}
    f = dict(st_br_police.parse(json.loads((D / "st_br_police_field_p1.json").read_text()), "u", "field"))
    assert f["dept:st_br_police:field:1"]["level"] == "division" and f["dept:st_br_police:field:1"]["post_kind"] == "igp"
    assert f["dept:st_br_police:field:2"]["district_code"] == "212" and f["dept:st_br_police:field:2"]["level"] == "district"


def test_br_phone_fetch_and_parse():
    calls = []
    page = (D / "st_br_phone_12.html").read_bytes()

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        return Resp(page if "PhoneDirectory" in url else b"<html></html>", url)

    p = st_br_phone.items()[st_br_phone.items().index(next(i for i in st_br_phone.items() if i["payload"]["org_id"] == "12"))]["payload"]
    recs, files, why = st_br_phone.fetch(p, get)
    by_id(recs)
    assert why == "" and len(recs) == 118 and calls[1].endswith("resetULB&orgId=12") and files
    d = dict(recs)["dept:st_br_phone:12:1"]
    assert d["name"] == "Sri Vinay Kumar, IAS" and d["post_kind"] == "principal_secretary" and d["dept"] == "treasury"
    assert d["email"] == "finsecy-bih@nic.in" and d["src_pos"] == {"table": 1, "row": 2}
    cm = dict(st_br_phone.parse((D / "st_br_phone_1.html").read_text(), "u", "1"))
    assert cm["dept:st_br_phone:1:1"]["post_kind"] == "secretary" and cm["dept:st_br_phone:1:1"]["body_kind"] == "cm_office"


def test_up_portal_district_officials():
    from dforms import st_up_portal
    recs = by_id(st_up_portal.parse((D / "st_up_portal_district_officials.html").read_text()))
    kinds = {}
    for rid, d in recs.items():
        kinds.setdefault(rid.split(":")[2], []).append(d)
    assert {k: len(v) for k, v in kinds.items()} == {"divcom": 18, "dm": 75, "police": 75}
    agra = recs["dept:st_up_portal:divcom:agra"]
    assert agra["name"] == "Shri Nagendra Pratap" and agra["email"] == "commagr@nic.in" and agra["districts"] == ["118", "143", "166", "167"]
    assert all(d.get("districts") for d in kinds["divcom"])
    # the DM table's division groups agree with dforms/st_div_up.json
    for d in kinds["dm"]:
        assert d["district_code"] in _state.districts_of("UP", d["division_of_district"])[1]
    assert len({d["district_code"] for d in kinds["police"]}) == 75
    cp = next(d for d in kinds["police"] if d["district_code"] == "118")
    assert cp["post"] == "Commissioner of Police" and cp["name"] == "Shri Deepak Kumar"
