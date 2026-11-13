"""cforms/pri_ap.py: Andhra Pradesh SEC results files 2021 (pdftotext -layout text saved from the files of 2026-11-13)."""
import shutil
from pathlib import Path

import pytest

from cforms import _pri, pri_ap

DATA = Path(__file__).parent / "data" / "pri_ap"
LGD = _pri.Lgd("AP")


def txt(name):
    return (DATA / name).read_text(encoding="utf-8")


def test_gp_rows_division_split_and_wrapped_name():
    zp = pri_ap.lgd_zp("YSR Kadapa")
    mandals = frozenset(pri_ap.norm(r[2]) for r in LGD.rows if r[1] == "ps" and LGD.by_code.get(r[4], [0, 0, ""])[2] == zp)
    rows = pri_ap.parse_gp(txt("gp_kadapa.txt"), mandals)
    first = rows[0]
    # "Jammalamadugu Chapad" has one space only between division and mandal
    assert (first["division"], first["mandal"], first["gp"], first["post"]) == ("Jammalamadugu", "Chapad", "ALLADUPALLE", "S")
    assert first["name"] == "Gosula MunaiahgariKishore Kumar Reddy" and first["education"] == "Post-Graduation"
    wrapped = [r for r in rows if r["wrapped"]]
    assert wrapped and wrapped[0]["name"] == "SIDDAMREDDYSIDDAMREDDY SANDEEP KUMAR REDDY" and wrapped[0]["ward"] == "7"
    recs = pri_ap.gp_records(rows, {"url": "https://sec.ap.gov.in/x.pdf", "district": "YSR Kadapa", "file": "gp"}, LGD)
    heads = [(rid, d) for rid, d in recs if d.get("head_rank") == 1]
    rid, d = heads[0]
    assert d["type"] == "pri_member" and d["level"] == "gp" and d["post"] == "Sarpanch" and rid.endswith(":head")
    assert d["lgd_code"] and rid == f"pri:AP:gp:{d['lgd_code']}:head" and d["src_pos"]["page"] == 1
    vice = [d for _, d in recs if d.get("post") == "Upa-Sarpanch"][0]
    assert vice["ward_no"] == "3" and vice["head_rank"] == 2
    assert any(r.endswith(":w9") for r, _ in recs)


def test_mptc_rows_reservation_in_words_and_wrapped():
    rows = pri_ap.parse_table(txt("mptc_p64_p88.txt"), "mptc")
    recs = pri_ap.pz_records(rows, {"url": "u", "file": "mptc"}, LGD)
    by = {d["serial"]: d for _, d in recs}
    assert by["399"]["name"] == "Setti Padmavathi" and by["399"]["reservation"] == "GENERAL(W)"
    assert by["399"]["block"] == "Kurupam" and by["399"]["ward_no"] == "Kitchada" and by["399"]["party"] == "YSRCP"
    assert by["239"]["name"] == "BUDIREDDI APPADU ALIAS NAIDU" and by["239"]["district"] == "Visakhapatnam"
    assert all(d["level"] == "ps" and d["post"] == "MPTC Member" for d in by.values())


def test_zptc_and_mpp():
    recs = pri_ap.pz_records(pri_ap.parse_table(txt("zptc_p1.txt"), "zptc"), {"url": "u", "file": "zptc"}, LGD)
    rid, d = recs[0]
    assert rid == "pri:AP:zp:474:wAmadalavalasa" and d["name"] == "Bendi Govinda Rao" and d["gender"] == "Male"
    assert [d for _, d in recs if d["serial"] == "9"][0]["name"] == "Dharmana Krishna Chaitanya"
    recs = pri_ap.pz_records(pri_ap.parse_table(txt("mpp_p1.txt"), "mpp"), {"url": "u", "file": "mpp"}, LGD)
    agali = {rid.rsplit(":", 1)[1]: d for rid, d in recs if d["block"] == "Agali"}
    assert agali["head"]["name"] == "B.K. Renuka" and agali["head"]["post"] == "Mandal Parishad President"
    assert agali["vice"]["name"] == "Gayatri" and agali["vice-2"]["name"] == "Vimala" and agali["coopted"]["name"] == "A. Nasir Sab"
    bram = [d for _, d in recs if d["block"] == "Bramhasamudram" and d["post"] == "Mandal Parishad President"][0]
    assert bram["name"] == "Kambam Chandra Sekhar Reddy"


def test_zpp_heads():
    """The whole ZPP file (tests/data/pri_ap/zpp.pdf = the bucket copy 6d6b0b159d21...): 13 chairpersons, 26 vice-chairpersons
    and 26 co-opted members. Before 2026-11-13 the vice-chairpersons and co-opted members were lines on the head record only
    (13 records): the reader audit found 13 records for 38 person rows."""
    recs = pri_ap.pz_records(pri_ap.parse_table(txt("zpp.txt"), "zpp"), {"url": "u", "file": "zpp"}, LGD)
    assert len(recs) == 65 and all(d["lgd_code"] for _, d in recs)
    posts = {}
    for _, d in recs:
        posts[d["post"]] = posts.get(d["post"], 0) + 1
    assert posts == {"Zilla Praja Parishad Chairperson": 13, "Zilla Praja Parishad Vice-Chairperson": 26, "Co-opted Member": 26}
    d = dict(recs)
    assert d["pri:AP:zp:474:vice-2"]["name"] == "Siripurapu Jaganmohanarao"          # wrapped around its party line
    assert d["pri:AP:zp:475:coopted-1"]["name"] == "Petakamsetti Siva Satyanaraya Joseph"
    assert d["pri:AP:zp:465:coopted-1"]["name"] == "Md. Gouse"                        # stood in the party column
    assert d["pri:AP:zp:459:coopted-1"]["name"] == "M. Ameen" and d["pri:AP:zp:459:vice"]["party"] == "YSRCP"
    recs = [(rid, d) for rid, d in recs if rid.endswith(":head")]
    by = {d["serial"]: d for _, d in recs}
    assert by["4"]["name"] == "Vipparthi Venugopal Rao" and by["4"]["vice_chairpersons_lines"][:1] == ["Burra Anubabu"]
    assert by["7"]["district"] == "Guntur" and by["7"]["name"] == "Kattera Heny Christina"
    assert by["1"]["coopted_members_lines"] == ["Savara Lakshmi", "Shaik Babji"]


@pytest.mark.skipif(not shutil.which("pdftotext"), reason="pdftotext not installed")
def test_fetch_from_pdf():
    class R:
        content = (DATA / "zpp.pdf").read_bytes()
    p = pri_ap.items()[-1]["payload"]
    assert p["file"] == "zpp"
    recs, files, why = pri_ap.fetch(p, lambda url, **k: R())
    assert why == "" and len(recs) == 65 and files[0][0] == "pri/AP/zpp-state-2021.pdf"


def test_items():
    items = pri_ap.items()
    assert len(items) == 17 and len({i["key"] for i in items}) == 17
    assert all(i["payload"]["kind"] == "form-pri_ap" and i["payload"]["url"].startswith("https://sec.ap.gov.in/") for i in items)
