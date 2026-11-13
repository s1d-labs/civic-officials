"""Jharkhand Panchayat General Election 2022 (dforms/pri_jh.py): the SEC results list, the constituency cell and the
Prapatra-23 rows. The OCR itself runs on the runners; the rows here were typed by eye from Koderma pages 3 and 50."""
import json

from pri_common import DATA, check_pri, mod

from esw_common import Answer

M = mod("pri_jh")
P = next(i["payload"] for i in M.items() if i["payload"]["district"] == "Koderma")


def test_items_match_the_sec_list():
    got = M.listing((DATA / "pri/jh_sec_results_2022_p1.html").read_text()) + \
        M.listing((DATA / "pri/jh_sec_results_2022_p2.html").read_text())
    assert len(got) == 24 == len(M.items())
    assert [u for _, u in got] == [i["payload"]["url"] for i in M.items()]
    assert got[5][0].startswith("Koderma") and P["no"] == 6 and P["route"] == "abroad" and M.METHOD


def test_constituency_cell():
    c = M.constituency("VI कोडरमा/6/08/कादोडीह– (3)")
    assert c["district"] == "कोडरमा" and c["block_no"] == "6" and c["gp_no"] == "08" and c["gp"] == "कादोडीह" and c["no"] == "3"
    assert M.constituency("VI कोडरमा-(1)")["no"] == "1" and "gp" not in M.constituency("VI कोडरमा-(1)")
    assert M.constituency("VI कोडरमा/1/14/अम्बाबाद - 4")["no"] == "4"


def test_rows_to_records():
    rows = json.loads((DATA / "pri/jh_koderma_rows.json").read_text())
    found = M.page_records(rows["3"], P, 3) + M.page_records(rows["50"], P, 50)
    recs = M.build(found)
    check_pri(recs, "pri_jh", "JH")
    d = dict(recs)
    assert len(recs) == 6
    zp = d["pri:pri_jh:koderma:zp:1"]
    assert zp["name"] == "श्रीमती नीतू कुमारी" and zp["level"] == "zp" and zp["post"] == "Zila Parishad Member"
    assert zp["gender"] == "female" and zp["src_pos"]["page"] == 3 and zp["src_pos"]["row"] == 4 and zp["src_pos"]["conf"] == 77
    assert d["pri:pri_jh:koderma:zp:3"]["category"].startswith("खुली") and "gender" not in d["pri:pri_jh:koderma:zp:3"]
    w = d["pri:pri_jh:koderma:gp:6-08:w3"]
    assert w["name"] == "विजय साव" and w["body_name_regional"] == "कादोडीह" and w["ward_no"] == "3" and w["role"] == "member"
    assert d["pri:pri_jh:koderma:gp:6-10:w1"]["body_name_regional"] == "मरकच्चो उत्तरी"


def test_post_words():
    assert M.post_of("मुखिया") == ("gp", "head", "Mukhiya")
    assert M.post_of("पंचायत समिति सदस्य")[0] == "ps" and M.post_of("जिला परिषद सदस्य")[0] == "zp"
    assert M.post_of("ग्राम पंचायत सदस्य") == ("gp", "member", "Gram Panchayat Member (ward)")


def test_file_item_lists_ocr_items():
    pdf = b"%PDF-1.4\n<< /Type /Pages /Kids [] /Count 23 >>\n%%EOF"
    recs, files, why = M.fetch(P, lambda url, **k: Answer(pdf, url))
    assert why == "" and files[0][0] == "depts/pri_jh/6_koderma.pdf"
    seed = recs[0][1]
    assert recs[0][0] == "seed:dept:pri_jh:6" and seed["type"] == "seed_items" and seed["pages"] == 23
    assert [i["payload"]["pages"] for i in seed["items"]] == [[1, 10], [11, 20], [21, 23]]
    assert all(i["payload"]["stored"].endswith("/depts/pri_jh/6_koderma.pdf") for i in seed["items"])


def test_seed_file():
    from pri_common import ROOT
    assert json.loads((ROOT / "seeds/dept_pri_jh.json").read_text()) == M.items()
