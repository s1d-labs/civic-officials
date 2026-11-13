"""Offline tests of dforms/vil_tn_ddmp.py (Tamil Nadu VAO lists in the District Disaster Management Plans 2024, TNSDMA).
Samples in tests/data/vil_tn_ddmp_*.txt: pdftotext -layout pages (form feed between pages) of the archive.s1d.me copies of
2026-11-07 (Trichy pp. 111-113, Namakkal pp. 199-203, Ariyalur pp. 76-77, Coimbatore p. 424, Nagapattinam pp. 202-203).
No test touches the network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

M = mod("vil_tn_ddmp")


def recs(name, district):
    text = (DATA / f"vil_tn_ddmp_{name}.txt").read_text()
    out = M.records(text, {"district": district}, f"http://tnsdma.tn.gov.in/img/document/DDMPPDF/{name}.pdf")
    check_records([r for r in out if r[1]["dept"] == "revenue"], "vil_tn_ddmp", "revenue")
    return out


def by_area(out, post=M.POST):
    return {d["area"]: d for _, d in out if d["post"] == post}


def test_trichy_firka_and_wrapped_cells():
    out = recs("trichy", "Tiruchirappalli")
    v = by_area(out)
    assert len(v) >= 60
    d = v["Varaganeri Tharanallur"]          # the second village of the cell is on the next line
    assert (d["name"], d["phone"], d["taluk"], d["level"], d["post_regional"]) == (
        "Jaiganesh", "8675219390", "Tiruchirappalli East", "village", "கிராம நிர்வாக அலுவலர்")
    assert v["Ariyamangalam"]["in_charge"] is True
    d = v["Thorakkudi"]
    assert (d["name"], d["firka"], d["taluk"]) == ("Sankar", "Manikandam", "Srirangam")
    assert d["src_pos"]["page"] == 3 and "Thorakkudi" in d["src_pos"]["line_text"]
    assert d["table_row"]["VAO’s Name"] == "Sankar"


def test_namakkal_cug_and_personal_mobile():
    v = by_area(recs("namakkal", "Namakkal"))
    d = v["Namakkal"]
    assert (d["name"], d["phone"], d["phone_cug"], d["firka"]) == ("K.Anand", "9384830562, 7092706704", "9384830562", "Namakkal")
    assert "K.Kokila" in [x["name"] for x in v.values()]      # village cell wrapped above and below the serial line
    assert not any("Surveyor" in (x.get("name") or "") for x in v.values())     # the survey staff table above is not a VAO list


def test_ariyalur_ri_vao_secretary():
    out = recs("ariyalur", "Ariyalur")
    d = by_area(out)["Sempiyakkudi"]
    assert (d["name"], d["phone"]) == ("K.Kanagaraj", "9786738882")
    ps = by_area(out, "Village Panchayat Secretary")["Sempiyakkudi"]
    assert (ps["name"], ps["phone"], ps["dept"], ps["level"]) == ("S.Balamurugan", "9894567284", "rural_development", "gram_panchayat")
    assert len(by_area(out, "Village Panchayat Secretary")) >= 10


def test_coimbatore_village_and_number_only():
    v = by_area(recs("coimbatore", "Coimbatore"))
    assert len(v) >= 40
    d = v["Naickenpalayam"]
    assert (d.get("name"), d["phone"], d["taluk"]) == (None, "9486932846", "COIMBATORE NORTH")


def test_nagapattinam_continuation_page():
    v = by_area(recs("nagapattinam", "Nagapattinam"))
    assert v["Anthanapettai"]["name"] == "Pakkiyarani"
    d = v["Porakudi"]                       # page after the header: columns at other x, read by order
    assert (d["name"], d["phone"], d["firka"]) == ("A.Manipal", "9597410293", "Thirukannapuram")


def test_fetch_refuses_non_pdf():
    url = "http://tnsdma.tn.gov.in/img/document/DDMPPDF/x.pdf"
    r, files, why = M.fetch({"url": url, "district": "Karur"}, fake_get({url: "vil_tn_ddmp_coimbatore.txt"}))
    assert (r, files, why) == ([], [], "not a PDF")


def test_seed():
    items = json.loads((ROOT / "seeds" / "dept_vil_tn_ddmp.json").read_text())
    assert len(items) == 38 and len({i["key"] for i in items}) == 38
    for i in items:
        p = i["payload"]
        assert p["reader"] == "vil_tn_ddmp" and p["state"] == "TN" and p["district"] and p["url"].endswith(".pdf")
        assert p["india_only"] is True and p["route"] in ("proxy", "direct")
