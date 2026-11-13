"""State-level readers of fork APE (Telangana, Odisha, West Bengal): saved archive copies and PDF excerpts only, no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import _field, _st_ape, st_od_portal, st_tg_portal, st_wb_par, st_wb_wbcs  # noqa: E402

DATA = Path(__file__).parent / "data"


class Resp:
    def __init__(self, content, url=""):
        self.content, self.url, self.status_code = content, url, 200
        self.text = content.decode("utf-8", "replace")


def by_id(recs):
    return dict(recs)


def test_methods_and_seeds():
    for m in (st_tg_portal, st_od_portal, st_wb_par, st_wb_wbcs):
        assert m.METHOD
    for st, n in (("tg", 2), ("od", 81), ("wb", 3)):
        its = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert len(its) == n and len({i["key"] for i in its}) == n
        assert all(i["payload"]["route"] in ("abroad", "proxy", "direct") and i["payload"]["reader"].startswith("st_") for i in its)


def test_post_kind_wrapper():
    pk = _st_ape.post_kind
    assert pk("Addl. Chief Secretary to Chief Minister") == "acs"
    assert pk("Spl. Chief Secretary to Govt.") == "acs"
    assert pk("Secretary to Chief Minister") == "secretary"
    assert pk("A.D.C to Governor") == "other"
    assert pk("Prl. Secretary to Government (FAC)") == "principal_secretary"


def test_tg_secretariat():
    html = (DATA / "st_tg_secretariat.html").read_text()
    r = by_id(st_tg_portal.parse(html, st_tg_portal.PAGES["secretariat"], "secretariat"))
    assert len(r) == 57
    d = r["dept:st_tg_portal:secretariat:1:2"]
    assert d["name"] == "Sri K. Surendra Mohan, IAS" and d["post"] == "Secretary to Government" and d["level"] == "state"
    assert d["department"] == "Agriculture and Co-operation" and d["dept"] == "agriculture" and d["state_code"] == "36"
    assert d["phone"] == "040-23453269, 040-23451086" and d["email"] == "secy-agri@telangana.gov.in"
    assert d["src_pos"] == {"table": 1, "row": 2}
    cs = [x for x in r.values() if x.get("post_kind") == "chief_secretary"]
    assert len(cs) == 1 and cs[0]["name"].startswith("Sri Sanjay Jaju")
    gov = [x for x in r.values() if x["body_kind"] == "governor"]
    assert len(gov) == 6


def test_tg_district_officials():
    html = (DATA / "st_tg_district_officials.html").read_text()
    r = st_tg_portal.parse(html, st_tg_portal.PAGES["district-officials"], "district-officials")
    assert len(r) == 96 and all(d["level"] == "district" and d.get("district_code") for _, d in r)
    d = dict(r)["dept:st_tg_portal:district-officials:1:2"]
    assert d["district_code"] == "501" and d["post"] == "Collector" and d["email"] == "collector_adbd@telangana.gov.in"


def test_od_whoswho_and_lists():
    h = (DATA / "st_od_whoswho_p0.html").read_text()
    assert st_od_portal.last_page(h) == 78
    r = by_id(st_od_portal.parse(h, st_od_portal.WHOSWHO + "?page=0", "whoswho-0"))
    assert len(r) == 20
    d = r["dept:st_od_portal:whoswho-0:1:3"]
    assert d["name"] == "Shri Sanjay Kumar Singh, IAS" and d["post_kind"] == "principal_secretary"
    assert d["dept"] == "food_supplies" and d["email"] == "fcswsc@nic.in" and d["list_no"] == "2"
    s = st_od_portal.parse((DATA / "st_od_secretariat.html").read_text(), st_od_portal.SECRETARIAT, "secretariat")
    assert len(s) == 39 and dict(s)["dept:st_od_portal:secretariat:1:2"]["phone"] == "0674-2323049, 0674-2391325"
    c = by_id(st_od_portal.parse((DATA / "st_od_cmo.html").read_text(), st_od_portal.CMO, "cmo"))
    assert len(c) == 16 and c["dept:st_od_portal:cmo:1:3"]["post_kind"] == "acs"


def test_od_fetch_flags_new_pages():
    h = (DATA / "st_od_whoswho_p0.html").read_text().replace('href="?page=78" title="Go to last page"',
                                                            'href="?page=80" title="Go to last page"')
    recs, files, why = st_od_portal.fetch({"url": "u", "page": "whoswho-0"}, lambda *a, **k: Resp(h.encode()))
    assert why == "" and len(files) == 1 and recs[-1][1]["last_page"] == 80


def test_wb_ias_excerpt():
    text = _field.pdf_text((DATA / "st_wb_ias_excerpt.pdf").read_bytes())
    r = by_id(st_wb_par.parse_ias(text, st_wb_par.IAS_PDF))
    cs = r["dept:st_wb_par:ias:1"]
    assert cs["name"] == "Sh. Manoj Kr. Agarwal" and cs["post_kind"] == "chief_secretary" and cs["batch"] == "1990"
    assert cs["src_pos"]["page"] == 1 and cs["src_pos"]["line_text"].lstrip().startswith("1.")
    k = r["dept:st_wb_par:ias:10"]
    assert k["post"].startswith("Additional Chief Secretary, Fire and Emergency Services") and k["post_kind"] == "acs"
    jd = r["dept:st_wb_par:ias:10:div:jalpaiguri"]
    assert jd["level"] == "division" and jd["area"] == "Jalpaiguri" and jd["districts"] == ["314", "309", "702", "664", "308"]
    assert r["dept:st_wb_par:ias:20"]["posted_outside"] is True
    dc = [d for d in r.values() if d["level"] == "division" and d.get("charge") != "additional"]
    assert dc and all(d["post_kind"] in ("divisional_commissioner", "other") for d in dc)


def test_wb_district_posts():
    assert st_wb_par.district_kind("DM-cum-DEO, Nadia") == "district_magistrate"
    assert st_wb_par.district_kind("D.M. cum D.E.O., Alipurduar") == "district_magistrate"
    assert st_wb_par.district_kind("ADM(LR), Nadia") == "adm"
    assert st_wb_par.district_kind("SDO, Kalna, Purba Bardhaman") == "sdo"
    assert st_wb_par.district_kind("Principal Secretary, Transport Department") == ""
    assert st_wb_par.district_in("SDO, Bongaon, North 24 Paraganas") == ("303", "North 24 Parganas")
    assert st_wb_par.divisions_in("Divisional Commissioner, Bardhaman Division and Secretary") == ["Burdwan"]


def test_wb_key_people():
    h = (DATA / "st_wb_key_people.html").read_text()
    r = st_wb_par.parse_key(h, st_wb_par.KEY_PEOPLE)
    assert len(r) == 21
    d = dict(r)["dept:st_wb_par:key:1:2"]
    assert d["name"] == "Shri Surendra Gupta, IAS" and d["post_kind"] == "principal_secretary" and d["email"] == "secy.par-wb@nic.in"


def test_wb_iframe():
    assert st_wb_par.iframe_pdf('<iframe src = "writereaddata/WBCSdirectory/Posting of IAS.pdf" width=1>',
                                st_wb_par.IAS_PAGE) == "https://par.wb.gov.in/writereaddata/WBCSdirectory/Posting%20of%20IAS.pdf"


def test_wb_wbcs_excerpt():
    text = _field.pdf_text((DATA / "st_wb_wbcs_excerpt.pdf").read_bytes())
    r = by_id(st_wb_wbcs.parse(text, st_wb_wbcs.PDF))
    assert len(r) == 60
    d = r["dept:st_wb_wbcs:CS1993080"]
    assert d["name"] == "PAPIA GHOSH (ROYCHOUDHURY)" and d["post"] == "SPECIAL SECRETARY" and d["dob"] == "07-07-1967"
    assert d["posting_office"] == "URBAN DEVELOPMENT AND MUNICIPAL AFFAIRS DEPTT." and d["dept"] == "town_body"
    assert d["level"] == "state" and d["batch"] == "1993" and d["src_pos"]["page"] == 1
    m = r["dept:st_wb_wbcs:sl1668"]
    assert m["level"] == "district" and m["district_code"] == "316" and m["name"] == "ARNAB BISWAS"
    assert m["address"] == "OFFICE OF THE DISTRICT MAGISTRATE, DIST- MALDA"
