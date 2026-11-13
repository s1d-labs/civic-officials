"""State-level readers for MP, CG, RJ (fork MPCGRJ, 2026-11-13): st_mp_diary, st_div_s3waas, st_html_tables, the division
files and the seeds. Saved fixtures only; no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import _state, st_div_s3waas, st_html_tables, st_mp_diary  # noqa: E402

DATA = Path(__file__).parent / "data"


def read(name):
    return (DATA / name).read_text(encoding="utf-8", errors="replace")


def by_id(recs):
    return dict(recs)


def test_division_files_cover_every_district_once():
    for st, n_div, n_dist in (("MP", 10, 55), ("CG", 5, 33), ("RJ", 7, 41)):
        d = _state.divisions(st)
        codes = [c for v in d.values() for c in v]
        assert len(d) == n_div and len(codes) == n_dist == len(set(codes))
    assert _state.districts_of("MP", "Narmadapuram Division")[1] == ["409", "408", "394"]


def test_mp_diary_mantralaya():
    url = st_mp_diary.BASE + "9"
    r = by_id(st_mp_diary.parse(read("st_mp_diary_9.html"), 9, url))
    assert len(r) == 140
    cs = r["dept:st_mp_diary:9:1"]
    assert cs["post"] == "मुख्य सचिव" and cs["post_kind"] == "chief_secretary" and cs["name"] == "श्री अनुराग जैन"
    assert cs["phone"] == "2441848, 2441370" and cs["email"] == "cs@mp.nic.in" and cs["level"] == "state"
    assert cs["department"] == "मुख्य सचिव कार्यालय" and cs["src_pos"] == {"table": 1, "row": 3} and cs["src_url"] == url
    assert cs["residence_address"] == "बी-18, चार इमली" and cs["state_code"] == "23"
    home = [d for d in r.values() if d.get("department") == "गृह विभाग"]
    assert home[0]["post_kind"] == "acs" and home[0]["dept"] == "police"
    kinds = {d.get("post_kind") for d in r.values()}
    assert {"acs", "principal_secretary", "secretary", "additional_secretary"} <= kinds


def test_mp_diary_division_and_district_grids():
    r = by_id(st_mp_diary.parse(read("st_mp_diary_46.html"), 46, st_mp_diary.BASE + "46"))
    dc = r["dept:st_mp_diary:46:1:3"]
    assert dc["level"] == "division" and dc["division"] == "Chambal" and dc["districts"] == ["417", "395", "431"]
    assert dc["post_kind"] == "divisional_commissioner" and dc["phone"] == "232900" and dc["phone_residence"] == "232660"
    assert dc["std_code"] == "07532" and dc["src_pos"] == {"table": 1, "row": 2, "col": 4}
    assert {d["division"] for d in r.values()} == set(_state.divisions("MP"))
    g = by_id(st_mp_diary.parse(read("st_mp_diary_48.html"), 48, st_mp_diary.BASE + "48"))
    col = g["dept:st_mp_diary:48:1:3"]
    assert col["post"] == "Collector" and col["email"] == "dmsheopur@nic.in" and col["district_code"] == "431"
    sp = g["dept:st_mp_diary:48:1:4"]
    assert sp["dept"] == "police" and sp["phone"] == "222400" and sp["phone_residence"] == "222401"
    codes = {d.get("district_code") for d in g.values()}
    assert len(codes) == 53 and None not in codes     # the page lists 53 of the 55 districts (2026-11-06 copy)


def test_mp_diary_stacked_zp_and_mayors():
    r = by_id(st_mp_diary.parse(read("st_mp_diary_20.html"), 20, st_mp_diary.BASE + "20"))
    a, c = r["dept:st_mp_diary:20:2:1"], r["dept:st_mp_diary:20:2:2"]
    assert a["name"] == "श्रीमती आरती आकाश गुर्जर" and a["post"] == "अध्यक्ष" and a["district_code"] == "417"
    assert a["email"] == "adhyakshzmpmorena118@gmail.com" and a["phone_residence"] == "9340350428, 9425433055"
    assert c["name"] == "श्री कमलेश कुमार भार्गव" and c["email"] == "ceozpmor@mp.gov.in" and c["src_pos"]["person"] == 2
    m = by_id(st_mp_diary.parse(read("st_mp_diary_21.html"), 21, st_mp_diary.BASE + "21"))
    g = [d for d in m.values() if d["district"] == "Gwalior"]
    assert [d["post"] for d in g] == ["महापौर", "आयुक्त"] and g[0]["name"] == "डॉ. शोभा सतीश सिकरवार"
    assert g[1]["email"] == "nn.gwalior@mpurban.gov.in"


def test_mp_diary_commissions_and_boards():
    r = by_id(st_mp_diary.parse(read("st_mp_diary_23.html"), 23, st_mp_diary.BASE + "23"))
    psc = r["dept:st_mp_diary:23:1"]
    assert psc["body"].startswith("मध्यप्रदेश लोक सेवा आयोग") and psc["post_kind"] == "chairperson"
    assert "secretarypsc-mp@nic.in" in psc["email"] and psc["body_kind"] == "commission"
    b = by_id(st_mp_diary.parse(read("st_mp_diary_10.html"), 10, st_mp_diary.BASE + "10"))
    x = b["dept:st_mp_diary:10:2"]
    assert x["department"] == "गृह विभाग" and x["body"] == "मध्यप्रदेश पुलिस आवास एवं अधोसंरचना विकास निगम"
    h = by_id(st_mp_diary.parse(read("st_mp_diary_16.html"), 16, st_mp_diary.BASE + "16"))
    assert h["dept:st_mp_diary:16:1"]["body"] == "आरसीव्हीपी नरोन्हा प्रशासन एवं प्रबन्धकीय अकादमी"
    assert len(by_id(st_mp_diary.parse(read("st_mp_diary_7.html"), 7, st_mp_diary.BASE + "7"))) == 24


def test_div_s3waas():
    p = {"state": "MP", "division": "Bhopal", "host": "bhopaldivisionmp.nic.in"}
    url = "https://bhopaldivisionmp.nic.in/en/about-division/whos-who/"
    r = st_div_s3waas.parse_page(p, read("st_div_s3waas_bhopal_whoswho.html"), url)
    d = dict(r)["dept:st_div_s3waas:bhopaldivisionmp.nic.in:en-about-division-whos-who:1:2"]
    assert d["name"] == "Shri Karmveer Sharma (IAS)" and d["post_kind"] == "divisional_commissioner"
    assert d["email"] == "commbho@nic.in" and d["phone"] == "0755-2540399" and d["level"] == "division"
    assert d["districts"] == ["396", "421", "422", "427", "437"] and d["src_pos"] == {"table": 1, "row": 2}
    assert dict(r)["dept:st_div_s3waas:bhopaldivisionmp.nic.in:en-about-division-whos-who:1:3"]["post_kind"] != "divisional_commissioner"
    c = st_div_s3waas.parse_page({"state": "MP", "division": "Chambal", "host": "c"}, read("st_div_s3waas_chambal_contact.html"),
                                 "https://c/en/contact-directory/")
    cols = [d for _, d in c if d["level"] == "district"]
    assert {d["district_code"] for d in cols} == {"417", "395", "431"} and all(len(d["districts"]) == 1 for d in cols)
    s = st_div_s3waas.parse_page({"state": "CG", "division": "Surguja", "host": "s"}, read("st_div_s3waas_surguja_directory.html"),
                                 "https://s/directory/")
    assert len(s) == 3 and s[0][1]["email"] == "comm-ambikapur.cg@gov.in" and s[0][1]["districts"][0] == "389"


def test_html_tables():
    p = {"key": "rj-sec", "state": "RJ", "body": "State Election Commission, Rajasthan", "body_kind": "commission", "dept": "elections",
         "post_kinds": {"Commissioner": "state_election_commissioner"}}
    r = st_html_tables.parse(read("st_rj_sec_office.html"), p, "https://sec.rajasthan.gov.in/officecontacts.aspx")
    assert len(r) == 12
    d = r[0][1]
    assert d["name"] == "Shri Rajeshwar Singh" and d["post"] == "Commissioner" and d["post_kind"] == "state_election_commissioner"
    assert d["phone"] == "(0141)-2227621, (0141)-2926021" and d["dept"] == "elections" and d["src_pos"] == {"table": 1, "row": 2}
    assert r[1][1]["service"] == "IAS"
    h = st_html_tables.parse(read("st_rj_rshrc_dir.html"), {"key": "x", "state": "RJ", "body": "RSHRC"}, "https://x/")
    assert len(h) == 9 and h[0][1]["post_kind"] == "chairperson" and h[0][1]["email"] == "rshrc@rajasthan.gov.in"
    assert h[0][1]["fax"] == "2227738" and h[0][1]["ip"] == "26623"
    c = st_html_tables.parse(read("st_cg_psc_dir.html"), {"key": "y", "state": "CG", "body": "CGPSC"}, "https://y/")
    assert len(c) == 9 and c[0][1]["post_kind"] == "chairperson" and c[4][1]["phone"] == "0771-2439564, 2331525"


def test_seeds():
    for st, n in (("mp", 33), ("cg", 2), ("rj", 53)):
        items = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert len(items) == n and len({i["key"] for i in items}) == n
        for i in items:
            p = i["payload"]
            assert p["state"] == st.upper() and p["route"] in ("abroad", "proxy", "direct") and "reader" in p
            assert isinstance(p["india_only"], bool)
    for m in (st_mp_diary, st_div_s3waas, st_html_tables):
        assert m.METHOD
