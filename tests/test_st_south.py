"""State-level readers of fork SOUTH (TN, KL, KA, PY, LD): saved pages only, no network."""
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from dforms import _state, st_ka_gokdir, st_kl_secretaries, st_ld_portal, st_py_portal, st_tn_contacts  # noqa: E402

DATA = Path(__file__).parent / "data"
MODS = [st_tn_contacts, st_kl_secretaries, st_ka_gokdir, st_py_portal, st_ld_portal]


def page(name):
    return (DATA / name).read_text(encoding="utf-8")


class Resp:
    def __init__(self, text, status=200):
        self.text, self.status_code, self.content, self.url = text, status, text.encode(), ""


def trail_ok(recs):
    for rid, d in recs:
        assert d["type"] == "dept_office" and d["level"] in ("state", "division", "district")
        assert d.get("src_pos") and d.get("src_url"), rid
        assert d.get("state_code")


def test_methods_and_seeds():
    for m in MODS:
        assert m.METHOD
    for st in ("tn", "kl", "ka", "py", "ld"):
        seeds = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert seeds and len({s["key"] for s in seeds}) == len(seeds)
        for s in seeds:
            p = s["payload"]
            assert p["route"] in ("abroad", "proxy", "direct") and isinstance(p["india_only"], bool)
            assert hasattr(__import__(f"dforms.{p['reader']}", fromlist=["fetch"]), "fetch")
    tn = json.loads((ROOT / "seeds" / "dept_st_tn.json").read_text())
    assert len(tn) == 460 and sum(1 for s in tn if s["payload"]["kind"] == "hod") == 242


def test_tn_secretaries_cards():
    recs = st_tn_contacts.parse_cards(page("st_tn_secretaries.html"), "https://www.tn.gov.in/secret_to_govt.php")
    assert len(recs) == 40
    d = dict(recs)["dept:st_tn_contacts:secy:2"]
    assert d["name"] == "Tmt Anu George, IAS" and d["post"] == "Secretary to Government" and d["email"] == "ahsec@tn.gov.in"
    assert d["body"].startswith("Animal Husbandry") and d["src_pos"] == {"card": 2, "selector": "div.data1"}
    trail_ok(recs)


def test_tn_office_tables():
    recs = st_tn_contacts.parse_table(page("st_tn_hod.html"), "https://www.tn.gov.in/detail_contact_hod.php?org_name=ODY3&category_value=NA==",
                                      {"kind": "hod", "label": "Agricultural Engineering", "body_kind": "directorate"})
    assert [d["post"] for _, d in recs] == ["CE (Agrl.Engg)", "CE (River Valley Project)"]
    assert recs[0][1]["phone"] == "24350154" and recs[0][1]["email"] == "aedce@tn.nic.in"
    assert recs[0][1]["office_phone"] == "24352622, 24352686, 24351492" and recs[0][1]["src_pos"] == {"table": 1, "row": 2}
    cs = st_tn_contacts.parse_table(page("st_tn_cs.html"), "u", {"kind": "cs", "label": "Chief Secretary to Government",
                                                                 "body_kind": "secretariat"})
    assert cs[0][1]["post_kind"] == "chief_secretary" and cs[0][1]["name"] == "Dr. M. Sai Kumar, IAS.," and cs[0][1]["email"] == "cs@tn.gov.in"
    dept = st_tn_contacts.parse_table(page("st_tn_dept.html"), "u", {"kind": "dept", "label": "Agriculture", "body_kind": "department"})
    assert [d["post_kind"] for _, d in dept] == ["secretary", "joint_secretary"]
    trail_ok(recs + cs + dept)


def test_tn_list_items():
    it = st_tn_contacts.list_items(page("st_tn_und_list.html"), "und", st_tn_contacts.LISTS[2][2], "other")
    assert len(it) == 172 and all(i["payload"]["url"].startswith("https://www.tn.gov.in/detail_contact.php?") for i in it)
    assert any(i["payload"]["body_kind"] == "commission" for i in it)


def test_tn_fetch_keeps_page():
    p = {"reader": "st_tn_contacts", "url": "https://www.tn.gov.in/cont_cheif_secret_to_govt.php?id=Nw==", "page": "table",
         "kind": "cs", "label": "Chief Secretary to Government", "body_kind": "secretariat"}
    recs, files, why = st_tn_contacts.fetch(p, lambda url, **k: Resp(page("st_tn_cs.html")))
    assert len(recs) == 1 and files[0][0] == "depts/st_tn_contacts/cs-Nw.html.gz" and why == ""
    assert recs[0][1]["src_sha256"]


def test_kl_secretaries_english_and_malayalam():
    en = st_kl_secretaries.parse(page("st_kl_secretaries_en.html"))
    assert len(en) == 46
    d = en[0][1]
    assert d["name"] == "Shri. Bishwanath Sinha IAS" and d["post"] == "Chief Secretary" and d["post_kind"] == "chief_secretary"
    assert d["email"] == "chiefsecy@kerala.gov.in" and d["phone"].startswith("0471-2333147")
    j = en[2][1]
    assert j["post"] == "Additional Chief Secretary" and j["department"] == "Home Department & Vigilance Department"
    assert j["src_pos"]["table"] == 2
    ml = st_kl_secretaries.parse(page("st_kl_secretaries_ml.html"))
    assert len(ml) == 46 and ml[0][1]["name_regional"].startswith("ശ്രീ") and ml[0][1]["post_kind"] == "chief_secretary"
    assert sum(1 for _, x in ml if x.get("post_kind") == "acs") == 4
    trail_ok(en + ml)


def test_kl_fetch_switches_language_first():
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((url, headers))
        return Resp('{"success":"successfully set"}') if "setbilingualval" in url else Resp(page("st_kl_secretaries_en.html"))
    recs, files, why = st_kl_secretaries.fetch(st_kl_secretaries.items()[0]["payload"], get)
    assert calls[0][0].endswith("/setbilingualval") and calls[0][1]["X-Requested-With"] == "XMLHttpRequest"
    assert len(recs) == 46 and why == ""


def test_ka_contact_directory():
    recs = st_ka_gokdir.parse(page("st_ka_gokdir.html"))
    assert len(recs) == 253
    by = {}
    for _, d in recs:
        by.setdefault(d["section"], []).append(d)
    assert len(by["Principal Secretaries / Secretaries"]) == 43 and len(by["Deputy Commissioners"]) == 31
    cs = by["Chief Secretary"][0]
    assert cs["name"] == "Dr. Shalini Rajneesh, IAS" and cs["post_kind"] == "chief_secretary" and cs["intercom"] == "3476"
    dc = by["Deputy Commissioners"][0]
    assert dc["level"] == "district" and dc["district"] == "Bagalkote" and dc["phone"] == "08354-235091"
    sp = by["Superintendent of Police"][0]
    assert sp["dept"] == "police" and sp["email"] == "spbgk@ksp.gov.in"
    hod = by["Head of Departments"][0]
    assert hod["post"] == "Commissioner" and hod["department"] == "Department of Social Welfare" and "name" not in hod
    assert by["Ministers"][0]["post"].startswith("Hon'ble Minister")
    trail_ok(recs)


def test_ka_divisions():
    name, codes = _state.districts_of("KA", "Kalaburagi Division")
    assert name == "Kalaburagi" and "738" in codes and len(codes) == 7
    assert sum(len(v) for v in _state.divisions("KA").values()) == 31


def test_py_pages():
    it = {i["payload"]["name"]: i["payload"] for i in st_py_portal.items()}
    cards = st_py_portal.parse_cards(page("st_py_secretaries.html"), it["secretaries"]["url"], it["secretaries"])
    assert len(cards) == 16 and cards[0][1]["post_kind"] == "chief_secretary" and cards[0][1]["email"] == "cs@py.gov.in"
    assert cards[0][1]["batch"] == "AGMU:1994" and cards[0][1]["dept"] == "administration"
    pol = st_py_portal.parse_table(page("st_py_police.html"), it["police"]["url"], it["police"])
    assert len(pol) == 66 and pol[0][1]["post_kind"] == "dgp" and pol[0][1]["email"] == "dgp@py.gov.in"
    assert pol[1][1].get("vacant") is True and pol[0][1]["section"].startswith("Director General")
    kkl = st_py_portal.parse_table(page("st_py_karaikal.html"), it["karaikal"]["url"], it["karaikal"])
    assert len(kkl) == 61 and kkl[0][1]["level"] == "district" and kkl[0][1]["district_code"] == "598"
    dc = st_py_portal.parse_table(page("st_py_dept_contacts.html"), it["dept-contacts"]["url"], it["dept-contacts"])
    assert len(dc) == 49 and dc[0][1]["post"] == "Director" and dc[0][1]["department"] == "Accounts and Treasuries"
    trail_ok(cards + pol + kkl + dc)


def test_ld_pages():
    it = {i["payload"]["name"]: i["payload"] for i in st_ld_portal.items()}
    ww = st_ld_portal.parse(page("st_ld_whoswho.html"), it["whos-who"]["url"], it["whos-who"])
    assert len(ww) == 5 and ww[0][1]["name"] == "Shri. Praful Patel" and ww[0][1]["email"] == "lk-admin@nic.in"
    assert ww[0][0] == "dept:st_ld_portal:whos-who:1" and ww[0][1]["state_code"] == "31"
    dr = st_ld_portal.parse(page("st_ld_directory.html"), it["directory"]["url"], it["directory"])
    assert len(dr) == 37 and dr[1][1]["department"] == "General Administration & Protocol" and dr[1][1]["email"] == "cs-lak@nic.in"
    trail_ok(ww + dr)
