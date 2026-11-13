"""Offline tests of the town-heads readers for the North (dforms/th_jk.py, th_pb.py, th_up_cug.py), 2026-11-13."""
import re

from esw_common import *  # noqa: F401,F403


def _seed(name):
    return json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text())


# ---- th_jk ----
def test_th_jk_items_match_seed():
    s = _seed("th_jk")
    assert mod("th_jk").items() == s and [i["payload"]["part"] for i in s] == ["jammu", "kashmir"]


def test_th_jk_jammu():
    m = mod("th_jk")
    p = m.items()[0]["payload"]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "th_jk_jammu_whoswho.html"}))
    assert why == "" and files[0][0] == "depts/th_jk/jammu-whoswho.html.gz"
    check_records(recs, "th_jk", "town_body")
    d = dict(recs)
    heads = [v for v in d.values() if v["level"] == "body"]
    assert len(heads) == 36 and len({v["lgd_code"] for v in heads}) == 36
    doda = d["dept:th_jk:JK-doda-doda-executive-officer"]
    assert doda["name"] == "Sh.Ravi Saini" and doda["phone"] == "9906078844" and doda["email"] == "eododa-jk@nic.in"
    assert doda["charge"] == "additional" and doda["own_post"] == "BDO Doda" and doda["lgd_code"] == "248038"
    assert doda["src_pos"] == {"table": 1, "row": 2} and doda["role"] == "head"
    kathua = [v for v in heads if v["area"] == "Kathua"][0]
    assert kathua["post"] == "Chief Executive Officer" and kathua["lgd_code"] == "276581"
    lak = [v for v in heads if v["area"] == "Lakhanpur"][0]       # "-" as the name: the mailbox stays
    assert "name" not in lak and lak["email"] == "eolakhanpur-jk@nic.in"
    assert [v for v in heads if v["area"] == "Basholi"][0]["lgd_code"] == "276585"
    staff = [v for v in d.values() if v["level"] == "state"]
    assert staff[0]["name"] == "Sh. Kapil Sharma" and staff[0]["post"] == "Director"


def test_th_jk_kashmir_codes():
    m = mod("th_jk")
    recs = m.parse_kashmir((DATA / "ulb_jk_key_contacts.txt").read_text())
    check_records(recs, "th_jk", "town_body")
    assert all(v.get("lgd_code") for _, v in recs)
    a = dict(recs)["dept:th_jk:JK--achabal-executive-officer"]
    assert a["lgd_code"] == "248172" and a["district"] == "Anantnag" and a["name"] == "Mirza Asif Ali"
    assert len(set(m.LGD["rows"].values())) == 76 and m.LGD["rows"]["tangmarg"] == "248154"


# ---- th_pb ----
def test_th_pb_items_match_seed():
    s = _seed("th_pb")
    assert mod("th_pb").items() == s and len(s) == 114 and all(i["payload"]["lgd_code"] for i in s)


def test_th_pb_cards():
    m = mod("th_pb")
    it = {i["payload"]["mcid"]: i["payload"] for i in m.items()}
    p = it[1009]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "th_pb_phagwara.html"}))
    assert why == "" and files[0][0] == "depts/th_pb/enigam-1009.html.gz"
    check_records(recs, "th_pb", "town_body")
    d = dict(recs)
    c = d["dept:th_pb:PB-kapurthala-phagwara-commissioner"]
    assert c["name"] == "S. Randeep Singh Heer, P.C.S." and c["role"] == "head" and c["lgd_code"] == "248286"
    assert c["photo_uploaded"] == "2026-11-11" and c["src_pos"] == {"selector": ".massage-card .name_overlay", "card": 2}
    assert d["dept:th_pb:PB-kapurthala-phagwara-mayor"]["role"] == "chair"
    # empty cards (Talwara) and a post typed as the name (Tapa) give nothing
    assert m.parse((DATA / "th_pb_talwara.html").read_text(), it[1094]) == []
    assert m.parse((DATA / "th_pb_tapa.html").read_text(), it[1104]) == []


# ---- th_up_cug ----
def _pages():
    raw = (DATA / "th_up_cug_p01_p02.txt").read_text()
    return [(int(a), b) for a, b in re.findall(r"### page (\d+)\n(.*?)(?=### page |\Z)", raw, re.S)]


def test_th_up_cug_items_match_seed():
    s = _seed("th_up_cug")
    assert mod("th_up_cug").items() == s and len(s) == 4 and s[-1]["payload"]["last"] == 16


def test_th_up_cug_rows():
    m = mod("th_up_cug")
    rows = m.parse(_pages())
    assert len(rows) == 17
    assert rows[0]["kind"] == "commissioner" and rows[0]["code"] == "249062" and rows[0]["cug"] == "8189077813"
    by = {r["body"]: r for r in rows}
    assert by["नकुड़"]["code"] == "248876" and by["नकुड़"]["body_type"] == "नगर पालिका परिषद"
    assert by["गढ़ीपुख्ता"]["code"] == "248890" and by["गढ़ीपुख्ता"]["body_type"] == "नगर पंचायत"
    assert by["मवाना"]["district"] == "मेरठ" and by["मवाना"]["code"] == "248961"       # division word skipped
    assert by["सरधना"]["cug"] == "8189077872"                                          # cell bars
    recs = m.build(rows)
    check_records(recs, "th_up_cug", "town_body")
    d = [v for _, v in recs if v["area"] == "स्याना"][0]
    assert d["post"] == "Executive Officer" and d["phone"] == "8189077917" and d["role"] == "head" and d["cug"] is True
    assert d["src_pos"]["page"] == 2 and d["src_pos"]["line_text"].endswith("8189077917")
