"""State-level readers, north group (PB, HR, DL, LA, CH, JK, UK): saved archive copies (tests/data/st_*), no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import (_state, st_ch_dir, st_dl_police, st_hr_cs, st_jk_gad, st_la_dir, st_nt_commission,  # noqa: E402
                    st_pb_whoswho, st_uk_sad)

DATA = Path(__file__).parent / "data"
MODS = (st_pb_whoswho, st_hr_cs, st_dl_police, st_la_dir, st_ch_dir, st_jk_gad, st_uk_sad, st_nt_commission)


def txt(name):
    return (DATA / name).read_text(encoding="utf-8")


def check_trail(recs):
    assert recs
    for rid, d in recs:
        assert rid.startswith("dept:") and d["type"] == "dept_office"
        assert d["level"] in ("state", "division", "district", "subdivision", "subdistrict")
        assert d.get("src_url") and d.get("src_pos"), rid
        assert d.get("state_code"), rid
    assert len({r for r, _ in recs}) == len(recs)


class Resp:
    def __init__(self, content, status=200, url=""):
        self.content = content if isinstance(content, bytes) else content.encode("utf-8")
        self.status_code, self.url = status, url

    @property
    def text(self):
        return self.content.decode("utf-8", "replace")


def test_methods_and_seeds():
    for m in MODS:
        assert m.METHOD
    keys = []
    for f in sorted((ROOT / "seeds").glob("dept_st_*.json")):
        for it in json.loads(f.read_text()):
            p = it["payload"]
            assert p["route"] in ("abroad", "proxy", "direct") and (p["reader"].startswith("st_") or p["reader"] == "rj_jankalyan")
            assert hasattr(__import__("dforms." + p["reader"], fromlist=["fetch"]), "fetch")
            keys.append(it["key"])
    assert len(keys) == len(set(keys)) >= 11


def test_division_files():
    for st, n in (("PB", 23), ("HR", 23), ("HP", 12), ("UK", 13), ("JK", 20)):
        codes = [c for v in _state.divisions(st).values() for c in v]
        assert len(codes) == len(set(codes)) == n, st


def test_pb_whoswho():
    cs = st_pb_whoswho.parse_cs(txt("st_pb_chief_secretary.html"))
    assert cs == {"phone": "0172-2740860, 0172-2740156", "email": "cs@punjab.gov.in"}
    recs = st_pb_whoswho.parse(txt("st_pb_admin_secretaries.html"), cs=cs)
    check_trail(recs)
    d = dict(recs)
    c = d["dept:st_pb_whoswho:kap-sinha:1"]
    assert c["post_kind"] == "chief_secretary" and c["phone"].startswith("0172-2740860") and c["service"] == "IAS"
    assert c["batch"] == "RR: 1992" and c["main_charge"] is True
    j = d["dept:st_pb_whoswho:ramvir:1"]
    assert j["level"] == "division" and j["division"] == "Jalandhar" and "34" in j["districts"]
    r = d["dept:st_pb_whoswho:manvesh-singh-sidhu:3"]
    assert r["division"] == "Rupnagar" and r["post_kind"] == "divisional_commissioner"
    assert d["dept:st_pb_whoswho:krishan-kumar:1"]["department"] == "Water Resources"
    assert d["dept:st_pb_whoswho:krishan-kumar:1"]["dept"] == "water"
    assert sum(1 for _, x in recs if x["level"] == "division") == 2 and len(recs) == 66


def test_hr_cs():
    recs = st_hr_cs.parse(txt("st_hr_cs_contact_us.html"))
    check_trail(recs)
    assert len(recs) == 64
    d = dict(recs)
    assert d["dept:st_hr_cs:1"]["post_kind"] == "chief_secretary" and d["dept:st_hr_cs:1"]["name"] == "Anurag Rastogi, IAS"
    assert d["dept:st_hr_cs:11"]["phone"] == "9814969609" and d["dept:st_hr_cs:11"]["intercom"] == "5535"
    assert d["dept:st_hr_cs:1"]["src_pos"] == {"table": 1, "row": 3}


def test_dl_police():
    recs = st_dl_police.parse(txt("st_dl_police_important_contact.html"))
    check_trail(recs)
    assert len(recs) == 42 and sum(1 for _, x in recs if x["level"] == "division") == 8
    d = dict(recs)
    n = d["dept:st_dl_police:jt:3"]
    assert n["area"] == "Northern Range" and n["email"] == "jtcp-nr-dl@nic.in" and n["phone"] == "011-27048007"
    assert d["dept:st_dl_police:spl:3"]["area"] == "Law & Order Zone 1"


def test_la_dir():
    recs = st_la_dir.parse(txt("st_la_directory.html"))
    check_trail(recs)
    assert len(recs) == 81
    d = dict(recs)
    assert d["dept:st_la_dir:249:2"]["post_kind"] == "chief_secretary"
    assert d["dept:st_la_dir:249:2"]["email"] == "chiefsecretary@ladakh.gov.in"
    assert d["dept:st_la_dir:786:1"]["post_kind"] == "dgp" and d["dept:st_la_dir:786:1"]["dept"] == "police"
    assert d["dept:st_la_dir:953:1"]["level"] == "district" and d["dept:st_la_dir:953:1"]["district"] == "Drass"


def test_ch_dir():
    recs = st_ch_dir.parse_text(txt("st_ch_dir_p9_10_60.txt"))
    check_trail(recs)
    d = {x["name"]: x for _, x in recs if x.get("name")}
    cs = d["H. Rajesh Prasad, IAS"]
    assert cs["post"] == "Chief Secretary" and cs["email"] == "cs-chd@chd.gov.in" and cs["phone"] == "2740154"
    assert cs["section"] == "CHIEF SECRETARY'S OFFICE" and cs["src_pos"]["page"] == 2
    assert dict(recs)["dept:st_ch_dir:3:1"]["post"].endswith("Chandigarh Administration")
    assert "Chandigarh Administration" not in d
    assert d["Professor Vivek Lal"]["email"] == "dpgi@pgimer.edu.in"
    assert any(not x.get("name") and x["post"] == "Secretary Health" for _, x in recs)


def test_jk_gad():
    h = txt("st_jk_kas_p100.html")
    assert st_jk_gad.n_pages(h) == 8
    recs = st_jk_gad.officer_records("kas", "all", st_jk_gad.grid_rows(h), st_jk_gad.PAGES["kas"])
    check_trail(recs)
    assert len(recs) == 100
    d = dict(recs)
    assert d["dept:st_jk_gad:kas:all:43"]["level"] == "district" and d["dept:st_jk_gad:kas:all:43"]["district"] == "Bandipora"
    ias = dict(st_jk_gad.officer_records("ias", "A", st_jk_gad.grid_rows(txt("st_jk_ias_p1.html")), st_jk_gad.PAGES["ias"]))
    assert ias["dept:st_jk_gad:ias:A:3"]["post_kind"] == "chief_secretary" and ias["dept:st_jk_gad:ias:A:3"]["cadre"] == "AGMUT"
    em = st_jk_gad.email_records(txt("st_jk_email.html"), st_jk_gad.PAGES["email"])
    check_trail(em)
    assert len(em) == 96 and dict(em)["dept:st_jk_gad:email:3:2"]["email"] == "agri-jk@nic.in"


def test_jk_gad_postbacks():
    """fetch() for the KAS list: GET, POST page size 100, then POST each further page (the fixture stands for every page)."""
    calls = []
    h = txt("st_jk_kas_p100.html")

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, (data or {}).get("__EVENTTARGET"), (data or {}).get("ctl00$conPage$ddlPageNumb")))
        return Resp(h, url=url)

    recs, files, why = st_jk_gad.fetch({"url": st_jk_gad.PAGES["kas"], "list": "kas"}, get)
    assert why == "" and len(recs) == 100
    assert calls[0][0] == "GET" and calls[1] == ("POST", "ctl00$conPage$ddlPageSize", "0")
    assert calls[-1] == ("POST", "ctl00$conPage$ddlPageNumb", "7") and len(calls) == 9


def test_uk_sad():
    lst = st_uk_sad.parse_list(txt("st_uk_sad_officers.html"))
    assert len(lst) == 83 and lst[0][3] == "https://sad.uk.gov.in/shri-anand-bardhan/"
    det = st_uk_sad.parse_detail(txt("st_uk_sad_officer_cs.html"))
    assert det["email"] == "cs-uttarakhand@nic.in" and det["departments"] == ["CHIEF SECRETARY"] and len(det["staff"]) == 2
    recs = st_uk_sad.records(*lst[0], det)
    check_trail(recs)
    d = dict(recs)
    assert d["dept:st_uk_sad:1"]["post_kind"] == "chief_secretary" and "0135-2712100" in d["dept:st_uk_sad:1"]["phone"]
    assert d["dept:st_uk_sad:1:staff:1"]["post_kind"] == "personal_staff"
    assert d["dept:st_uk_sad:1:staff:1"]["src_url"] == "https://sad.uk.gov.in/shri-anand-bardhan/"


def test_commissions():
    p = st_nt_commission.SOURCES[0]
    recs = st_nt_commission.parse(txt("st_hr_sec_whos_who.html"), p["url"], p)
    check_trail(recs)
    d = dict(recs)
    k = "dept:st_nt_commission:hr-state-election-commission-haryana:1:"
    assert d[k + "2"]["post_kind"] == "state_election_commissioner" and d[k + "2"]["email"] == "sec@hry.nic.in"
    assert d[k + "3"]["vacant"] is True and "name" not in d[k + "3"]
    p = st_nt_commission.SOURCES[1]
    recs = st_nt_commission.parse(txt("st_uk_sec_whos_who.html"), p["url"], p)
    assert len(recs) == 12 and all(x["body_kind"] == "commission" and x["dept"] == "elections" for _, x in recs)
