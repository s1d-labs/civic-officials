"""Offline tests of the PRI elected-member readers for Rajasthan, Haryana and Punjab (dforms/pri_rj.py, pri_hr.py, pri_pb.py) on
saved answers in tests/data/pri/ (no network; no OCR: the Punjab test reads OCR-like text transcribed from page 2 of the Ludhiana PS
gazette image)."""
import json

from pri_common import DATA, ROOT, check_pri, fake_get, mod


# ---------------------------------------------------------------- Rajasthan

RJ_P = {"reader": "pri_rj", "url": "https://sec.rajasthan.gov.in/GramPanchayatDetails.aspx", "state": "RJ", "period": "64",
        "district_value": "5", "district": "BARMER", "samiti_value": "39", "samiti": "BARMER PANCHAYAT SAMITI"}


def _rj_get():
    steps = {"DropDownListPeriod": "pri/rj_period.html", "DistrictDropDownList": "pri/rj_district.html",
             "PanchayatSamitiDropDownList": "pri/rj_samiti.html"}

    def target(name):
        return lambda url, method, data: method == "POST" and data and data.get("__EVENTTARGET", "").endswith(name)
    routes = {("GET", RJ_P["url"]): "pri/rj_get.html",
              (lambda url, method, data: method == "POST" and data and data.get("ctl00$ContentPlaceHolder1$btnSubmit")):
              "pri/rj_barmer_submit.html"}
    routes.update({target(k): v for k, v in steps.items()})
    return fake_get(routes)


def test_pri_rj_flow_barmer():
    m = mod("pri_rj")
    get = _rj_get()
    recs, files, why = m.fetch(RJ_P, get)
    assert why == "" and len(get.calls) == 5
    check_pri(recs, "pri_rj", "RJ")
    heads = [d for _, d in recs if d["role"] == "head"]
    members = [d for _, d in recs if d["role"] == "member"]
    assert len(heads) == 4 and len(members) == 32
    d = dict(recs)
    h = d["pri:pri_rj:64-39:aadrsh-dundha:sarpanch"]
    assert h["name"] == "MAGI" and h["phone"] == "9460538939" and h["father_name"] == "RAMESH KUMAR" and h["votes"] == 1330
    assert h["post"] == "Sarpanch" and h["level"] == "gp" and h["block"] == "BARMER" and h["district"] == "BARMER"
    assert h["election"] == "Rajasthan PRI General Election OCT-NOV 2026" and h["runner_up"] == "JASHODA KANWAR"
    assert h["src_pos"]["table"].startswith("#tabs-4") and h["src_pos"]["candidate_row"] >= 2 and h["src_sha256"]
    assert all(x.get("phone") for x in heads)
    w = d["pri:pri_rj:64-39:aadrsh-dundha:w8"]
    assert w["name"] == "BHURCHAND" and w["ward_no"] == "8" and w["votes"] == 301 and w["unopposed"] is False
    assert files and files[0][0].startswith("pri/RJ/64-39-")


def test_pri_rj_wrong_samiti():
    m = mod("pri_rj")
    recs, files, why = m.fetch({**RJ_P, "samiti": "BAYTOO PANCHAYAT SAMITI"}, _rj_get())
    assert recs == [] and "not BAYTOO" in why


def test_pri_rj_seeds():
    seeds = json.loads((ROOT / "seeds" / "dept_pri_rj.json").read_text())
    assert len(seeds) == 457 and len({s["key"] for s in seeds}) == 457
    assert {s["payload"]["route"] for s in seeds} == {"direct"} and len({s["payload"]["district"] for s in seeds}) == 41
    assert mod("pri_rj").METHOD


# ---------------------------------------------------------------- Haryana

def _hr(name, p):
    m = mod("pri_hr")
    pages = (DATA / "pri" / name).read_text().split("\f")
    return m, pages, m.build(m.parse(pages, p), p, pages, p["url"])


def test_pri_hr_block_sarpanch_panch():
    p = {"kind": "gp", "district": "Ambala", "block": "Barara", "url": "https://example/2022120212.pdf"}
    m, pages, recs = _hr("hr_barara_p1-2_p24.txt", p)
    check_pri(recs, "pri_hr", "HR")
    d = dict(recs)
    h = d["pri:pri_hr:ambala:barara:g1:sarpanch"]
    assert h["name"] == "कुलवन्त सिंह" and h["body_name"] == "अब्दुलागढ" and h["post"] == "Sarpanch" and h["role"] == "head"
    assert h["seat_category"] == "महिला के सिवाय" and h["lang"] == "hi" and h["cells_raw"]["post"] == "ljiap"
    w = d["pri:pri_hr:ambala:barara:g1:w2"]
    assert w["name"] == "संदीप" and w["father_name"] == "श्री परमजीत सिंह" and w["unopposed"] is True
    assert w["seat_category"] == "अनुसूचित जाति महिला के सिवाय"          # wrapped on the next line
    e = d["pri:pri_hr:ambala:barara:g1:sarpanch:en"]
    assert e["name"] == "Kulwant Singh" and e["body_name"] == "Abdulagarh" and e["seat_category"] == "Other than Women"
    assert d["pri:pri_hr:ambala:barara:g1:w2:en"]["father_name"] == "Sh. Paramjeet Singh"
    assert d["pri:pri_hr:ambala:barara:g3:sarpanch"]["body_name"] == "अधोया एम0"
    assert all(r["src_pos"]["page"] in (1, 2, 3) and r["src_pos"]["line_text"] for _, r in recs)


def test_pri_hr_zp():
    p = {"kind": "zp", "district": "Ambala", "url": "https://example/2022120248.pdf"}
    m, pages, recs = _hr("hr_ambala_zp.txt", p)
    check_pri(recs, "pri_hr", "HR")
    hi = {d["ward_no"]: d for _, d in recs if d["lang"] == "hi"}
    assert sorted(hi, key=int) == [str(i) for i in range(1, 16)]
    assert hi["1"]["name"] == "राजेश कुमार" and hi["1"]["party"] == "निर्दलीय" and hi["1"]["level"] == "zp"
    assert hi["11"]["seat_category"] == "अनुसूचित जाति महिला के सिवाय" and hi["11"]["party"] == "बहुजन समाज पार्टी"
    en = dict(recs)["pri:pri_hr:ambala:zp:w15:en"]
    assert en["name"] == "Deepika" and en["father_name"] == "Mohit Sharma" and en["party"] == "Independent"


def test_pri_hr_garbled_ps():
    m = mod("pri_hr")
    assert m.garbled([(DATA / "pri" / "hr_ambala_ps_p1.txt").read_text()])
    assert not m.garbled([(DATA / "pri" / "hr_ambala_zp.txt").read_text()])


def test_pri_hr_seeds():
    seeds = json.loads((ROOT / "seeds" / "dept_pri_hr.json").read_text())
    kinds = [s["payload"]["kind"] for s in seeds]
    assert len(seeds) == 187 and kinds.count("gp") == 143 and kinds.count("zp") == 22 and kinds.count("ps") == 22
    assert len({s["key"] for s in seeds}) == 187 and len({s["payload"]["district"] for s in seeds}) == 22
    assert {s["payload"]["route"] for s in seeds} == {"abroad"}


# ---------------------------------------------------------------- Punjab

def test_pri_pb_parse_ps_rows():
    m = mod("pri_pb")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_pb_ocr.json").read_text())
    p = next(s["payload"] for s in seeds if s["key"] == "pri_pb:ps-ludhiana:ocr")
    text = (DATA / "pri" / "pb_ludhiana_ps_p2_ocr.txt").read_text()
    recs = m.build(m.parse([(2, text)], p), p, p["url"])
    check_pri(recs, "pri_pb", "PB")
    assert len(recs) == 7
    d = dict(recs)
    r = d["pri:pri_pb:ludhiana:ps-doraha:1-dhamot-kalan"]
    assert r["name"] == "KIRANPREET KAUR" and r["party"] == "AAP" and r["seat_category"] == "SC (W)" and r["block"] == "Doraha"
    assert r["level"] == "ps" and r["ward_no"] == "1" and r["src_pos"]["page"] == 2
    assert d["pri:pri_pb:ludhiana:ps-jagraon:10-kaunke-kalan"]["name"] == "SUKHDEV SINGH S/O JEET SINGH"
    assert d["pri:pri_pb:ludhiana:ps-jagraon:13-agwar-gujjran"]["party"] == "IND"     # a line without the | borders


def test_pri_pb_save_step():
    m = mod("pri_pb")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_pb_save.json").read_text())
    p = next(s["payload"] for s in seeds if s["key"] == "pri_pb:zp-mansa:save")
    get = fake_get({p["url"]: "pri/pb_tiny.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files[0][0] == "pri/PB/Final_Gazette_Report-ZP_Mansa.pdf" and recs[0][1]["ocr_needed"] is True


def test_pri_pb_seeds():
    save = json.loads((ROOT / "seeds" / "dept_pri_pb_save.json").read_text())
    ocr = json.loads((ROOT / "seeds" / "dept_pri_pb_ocr.json").read_text())
    assert len(save) == len(ocr) == 44 and {s["payload"]["route"] for s in save} == {"direct"}
    assert {s["payload"]["route"] for s in ocr} == {"abroad"}
    assert all(s["payload"]["stored"].endswith(s["payload"]["url"].rsplit("/", 1)[-1]) for s in ocr)
    assert all(s["payload"]["samitis"] for s in ocr if s["payload"]["level"] == "ps")
