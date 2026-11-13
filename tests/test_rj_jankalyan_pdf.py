"""Offline tests of dforms/rj_jankalyan_pdf.py: officer lists in the Rajasthan Jankalyan portal PDFs, read from the bucket copies
that dforms/rj_jankalyan.py saved (fixtures: four of those copies, downloaded once from bucket project civic-officials-depts-direct,
2026-11-13). No test touches the network."""
import json

from esw_common import DATA, check_records, mod

R = DATA / "rjpdf"


def _p(code, eid, cat, district, dept="administration"):
    return {"reader": "rj_jankalyan_pdf", "code": code, "entry_id": eid, "category": cat, "district": district, "dept": dept,
            "url": f"https://jankalyanfile.rajasthan.gov.in/x/{eid}.pdf", "source": "https://x.rajasthan.gov.in/contact-directory",
            "portal": "x.rajasthan.gov.in", "stored": f"civic-officials-depts-direct/depts/rj_jankalyan/x/{eid}.pdf", "state": "RJ"}


def _parse(name, p):
    m = mod("rj_jankalyan_pdf")
    recs, engine, has_text = m.parse((R / name).read_bytes(), p)
    assert has_text
    return recs


def _trail(recs):
    for _, d in recs:
        pos = d["src_pos"]
        assert pos["page"] >= 1 and pos["line"] >= 1 and pos["line_text"].strip() and pos["mode"] in ("table", "loose")
        assert d["method"].startswith("pdf text")


def test_kruti_dev_words():
    m = mod("rj_jankalyan_pdf")
    assert m.kd_chunk("Jh ih;w\"k lekfj;k I.A.S.") == "श्री पीयूष समारिया I.A.S."
    assert m.kd_chunk("dqekj RAS") == "कुमार RAS"
    assert m.kd_chunk("sdm.kota@rajasthan.gov.in") == "sdm.kota@rajasthan.gov.in"
    assert m.head_en("नाम अधिकारी") == "Name of Officer" and m.head_en("पद नाम") == "Designation"
    assert m.relayout("1     abc     def", str.upper) == "1     ABC     DEF"


def test_jodhpur_sdm_list():
    recs = _parse("jodhpur_573.pdf", _p("42", "573", "Other Officers", "Jodhpur"))
    check_records(recs, "rj_jankalyan_pdf", "administration")
    _trail(recs)
    assert len(recs) == 14 and all(d["level"] == "subdivision" for _, d in recs)
    d = dict(recs)["dept:rj_jankalyan_pdf:42:573:3"]
    assert (d["post"], d["name"], d["phone"], d["district"]) == ("SDM Jodhpur South", "Smt. Apoorva Parwal", "9983318037", "Jodhpur")
    assert d["src_pos"]["page"] == 1 and "Apoorva Parwal" in d["src_pos"]["line_text"]


def test_kota_dlo_kruti_dev():
    recs = _parse("kota_1920.pdf", _p("44", "1920", "DLO(PDF)", "Kota"))
    _trail(recs)
    assert len(recs) >= 240
    by = dict(recs)
    dm = by["dept:rj_jankalyan_pdf:44:1920:3"]
    assert dm["name"] == "श्री पीयूष समारिया I.A.S." and dm["post"] == "जिला कलक्टर एवं जिला मजिस्ट्रेट कोटा"
    assert dm["phone"] == "2451200, 9982910228" and dm["src_pos"]["line_text"].lstrip().startswith("3")
    sp = by["dept:rj_jankalyan_pdf:44:1920:6"]
    assert sp["dept"] == "police" and "9871064211" in sp["phone"]
    assert max(d["src_pos"]["page"] for d in by.values()) == 9


def test_nagaur_dlo_multiline_rows():
    recs = _parse("nagaur_1963.pdf", _p("45", "1963", "DLO(PDF)", "Nagaur"))
    _trail(recs)
    by = dict(recs)
    phed = by["dept:rj_jankalyan_pdf:45:1963:3"]
    assert (phed["dept"], phed["name"], phed["email"]) == ("water", "Sharwan singh khiriya", "secircle.nag.phed@rajasthan.gov.in")
    assert "9314874645" in phed["phone"] and phed["cells"]["Designation"] == "Superintendent Engineer"
    assert phed["src_pos"]["line_start"] < phed["src_pos"]["line"] < phed["src_pos"]["line_end"]
    assert by["dept:rj_jankalyan_pdf:45:1963:4"]["dept"] == "public_works"


def test_jhalawar_bdo_list():
    recs = _parse("jhalawar_529.pdf", _p("40", "529", "Other Officers", "Jhalawar"))
    check_records(recs, "rj_jankalyan_pdf", "rural_development")
    assert len(recs) == 8 and all(d["level"] == "block" for _, d in recs)
    d = dict(recs)["dept:rj_jankalyan_pdf:40:529:1"]
    assert (d["post"], d["name"], d["phone"]) == ("BDO- Dag", "Sh. Bhanupratap Singh", "07435-283324, 283325, 9540940471")


class _Hub:
    def read_urls(self, project, keys):
        return {k: "https://bucket.example/" + k for k in keys}


def test_fetch_reads_stored_copy(monkeypatch):
    m = mod("rj_jankalyan_pdf")
    body = (R / "jhalawar_529.pdf").read_bytes()

    class A:
        status_code, content = 200, body
    import requests
    monkeypatch.setattr(requests, "get", lambda url, timeout=None: A())
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        return None
    get.hub = _Hub()
    p = _p("40", "529", "Other Officers", "Jhalawar")
    recs, files, why = m.fetch(p, get)
    assert not why and not calls and not files and len(recs) == 8
    src = recs[0][1]["src"]
    assert src["file"] == p["stored"] and src["url"] == p["url"] and len(src["sha256"]) == 64
    assert recs[0][1]["method"].startswith("pdf text (pdftotext -layout)") or recs[0][1]["method"].startswith("pdf text (pypdf")


def test_fetch_scan_note():
    m = mod("rj_jankalyan_pdf")
    tiny = (DATA / "gaps2" / "tiny.pdf").read_bytes()

    class A:
        content = tiny
    recs, files, why = m.fetch(_p("22", "9", "DLO(PDF)", "Ajmer"), lambda url, **k: A())
    assert not why and len(recs) == 1 and recs[0][1]["type"] == "note" and recs[0][0] == "dept:rj_jankalyan_pdf:22:9:note"


def test_items_from_file_records():
    m = mod("rj_jankalyan_pdf")
    recs = [("dept:rj_jankalyan:44:file:1920", {"type": "source_file", "category": "DLO(PDF)", "fetched": True, "url": "u1",
                                                "stored": "depts/rj_jankalyan/kota/1920.pdf", "portal": "kota.rajasthan.gov.in",
                                                "district": "Kota", "dept": "administration", "source": "s"}),
            ("dept:rj_jankalyan:44:file:7", {"category": "Bus Time Table", "fetched": True, "stored": "a.pdf", "url": "u"}),
            ("dept:rj_jankalyan:44:file:8", {"category": "CHC", "fetched": False, "stored": None, "url": "u"})]
    its = m.items_from(recs)
    assert [i["key"] for i in its] == ["rj_jankalyan_pdf:kota:1920"]
    p = its[0]["payload"]
    assert p["stored"] == "civic-officials-depts-direct/depts/rj_jankalyan/kota/1920.pdf" and p["code"] == "44"
    seeds = m.items()
    assert len(seeds) == len({i["key"] for i in seeds}) >= 250
    assert all(i["payload"]["stored"].startswith("civic-officials-depts-direct/depts/rj_jankalyan/") for i in seeds)
    json.dumps(seeds)


def test_rows_with_a_phone_and_no_name_column_are_kept():
    """The reader audit (2026-11-13) found rows with a phone that were dropped because no name or post column was known. Full saved
    files, records before -> after: Pratapgarh sarpanch list (loose rows, Kruti Dev titles "Jhefr") 21 -> 101, Jaipur BDO list (names
    without a title) 1 -> 16, Jaisalmer officers (name in the column after the post) 106 -> 168 (named 14 -> 162)."""
    m = mod("rj_jankalyan_pdf")
    p = {"code": "t", "entry_id": "1"}
    recs = dict(m.parse((R / "pratapgarh_loose_full.pdf").read_bytes(), p)[0])
    assert len(recs) == 101 and all(d.get("name") and d.get("phone") for d in recs.values())
    assert sum(d["name"].startswith(("श्री", "सुश्री")) for d in recs.values()) == 56
    assert not any(d["name"].startswith(("Jh", "Jefr")) or any(ch.isdigit() for ch in d["name"]) for d in recs.values())
    recs = dict(m.parse((R / "jaipur_bdo_untitled_full.pdf").read_bytes(), p)[0])
    assert len(recs) == 16 and all(d.get("name") and d.get("email") for d in recs.values())
    assert sum(d.get("post") == "बी० डी०" for d in recs.values()) == 14
    recs = dict(m.parse((R / "jaisalmer_name_after_post_full.pdf").read_bytes(), p)[0])
    assert len(recs) == 168 and sum(1 for d in recs.values() if d.get("name")) == 162
    assert any(d.get("name") == "Radhey Shyam Narwal" and d["post"] == "Dy Dir Agriculture" and d["phone"] == "9414773880"
               for d in recs.values())
