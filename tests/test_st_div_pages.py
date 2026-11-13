"""dforms/st_div_pages.py on saved pages (tests/data/st_div_pages/, tables cut from the live pages of 2026-11-13)."""
import json
from pathlib import Path

from dforms import st_div_pages as M

D = Path(__file__).resolve().parent / "data" / "st_div_pages"


def page(name):
    return (D / name).read_text(encoding="utf-8")


def by_post(recs):
    return {d["post"]: d for _, d in recs}


def test_karnataka_regional_commissioner_table():
    p = {"key": "ka-kalaburagi", "state": "KA", "division": "Kalaburagi"}
    recs = M.parse_page(p, page("ka_kalaburagi.html"), "https://rckalaburagi.karnataka.gov.in/107/officers-details/en")
    assert len(recs) == 2                                   # the accessibility / file-format tables are not read
    rc = by_post(recs)["Regional Commissioner"]
    assert rc["level"] == "division" and rc["division"] == "Kalaburagi" and rc["post_kind"] == "divisional_commissioner"
    assert rc["email"] == "rcgulb@gmail.com" and rc["dept"] == "revenue" and rc["state_code"] == "29"
    assert rc["name"].startswith("Smt. Zehera Naseem") and rc["service"] == "IAS"
    assert rc["districts"]                                   # from dforms/st_div_ka.json
    assert by_post(recs)["Additional Regional Commissioner"]["post_kind"] != "divisional_commissioner"
    rid = recs[0][0]
    assert rid.startswith("dept:st_div_pages:ka-kalaburagi:107-officers-details-en:")
    assert recs[0][1]["src_pos"]["table"] >= 1 and "cells" in recs[0][1]


def test_office_contact_block():
    p = {"key": "ka-belagavi", "state": "KA", "division": "Belagavi"}
    recs = M.office_record(p, page("ka_belagavi_contact.html"), "https://rcbelagavi.karnataka.gov.in/34/contact-us/en", 0,
                           {"post": "Regional Commissioner"})
    assert len(recs) == 1
    rid, d = recs[0]
    assert rid == "dept:st_div_pages:ka-belagavi:office:0"
    assert d["phone"].startswith("0831-2404007") and d["email"] == "rcbelagavi@gmail.com"
    assert d["level"] == "division" and d["division"] == "Belagavi" and d["post_kind"] == "divisional_commissioner"
    assert "Besides Court Compound" in d["address"] and "Share" not in d["address"]


def test_magadh_commissioner_named_after_division():
    p = {"key": "br-magadh", "state": "BR", "division": "Magadh"}
    recs = M.parse_page(p, page("br_magadh.html"), "https://magadhdivision.bihar.gov.in/whoiswho.php")
    posts = by_post(recs)
    assert posts["Magadh Commissioner"]["post_kind"] == "divisional_commissioner"
    assert posts["Magadh Commissioner"]["phone"] == "0631-2225821, 0631-2229002"
    assert posts["Secretary To Commissioner"]["post_kind"] != "divisional_commissioner"
    assert posts["Secretary To Commissioner"]["phone"].startswith("0631-2226337")


KONKAN = {"482": ["Mumbai", "मुंबई शहर"], "483": ["Mumbai Suburban", "मुंबई उपनगर"], "497": ["Thane", "ठाणे"],
          "665": ["Palghar", "पालघर"], "491": ["Raigad", "रायगड"], "492": ["Ratnagiri", "रत्नागिरी"], "495": ["Sindhudurg", "सिंधुदुर्ग"]}


def test_marathi_headers_and_district_heads():
    p = {"key": "mh-konkan", "state": "MH", "division": "Konkan", "district_names": KONKAN}
    recs = M.parse_page(p, page("mh_konkan.html"), "https://divcomkonkan.gov.in/directory-mr/")
    assert len(recs) == 56
    d = dict(recs)
    head = [x for x in d.values() if x.get("post_kind") == "divisional_commissioner"]
    assert head and head[0]["post"] == "विभागीय आयुक्त" and head[0]["level"] == "division"
    coll = [x for x in d.values() if x["post"].startswith("जिल्हाधिकारी")]
    assert len(coll) == 7 and all(x["level"] == "district" for x in coll)
    assert {x["district_code"] for x in coll} == set(KONKAN)
    suburban = next(x for x in coll if "उपनगर" in x["post"])
    assert suburban["district_code"] == "483"               # the longer name wins
    sp = [x for x in d.values() if x["post"].startswith("पोलीस अधीक्षक")]
    assert sp and all(x["dept"] == "police" and x["level"] == "district" for x in sp)
    mc = [x for x in d.values() if x["post"].startswith("महानगरपालिका आयुक्त")]
    assert mc and all(x["dept"] == "town_body" for x in mc)
    addl = [x for x in d.values() if x["post"].startswith("अपर आयुक्त")]
    assert addl and all(x["level"] == "division" and x["dept"] == "revenue" for x in addl)


def test_haryana_police_range_page():
    names = {"72": ["Hisar"], "71": ["Fatehabad"], "84": ["Sirsa"], "73": ["Jind"]}
    p = {"key": "hr-police-hisar", "state": "HR", "division": "Hisar Range", "kind": "police",
         "body": "Hisar Range, Haryana Police", "district_names": names}
    recs = M.parse_page(p, page("hr_police_hisar.html"), "https://haryanapolice.gov.in/static/TelephoneDirectory_hisar.aspx")
    posts = by_post(recs)
    assert not any(k in ("Office", "Residence") for k in posts)          # the second header row is skipped
    ig = posts["IGP/Hisar Range, Hisar"]
    assert ig["level"] == "division" and ig["division"] == "Hisar Range" and ig["post_kind"] == "igp"
    assert ig["dept"] == "police" and ig["body"] == "Hisar Range, Haryana Police" and ig["email"] == "ighsr@hry.nic.in"
    assert "8814011000" in ig["phone"]
    sp = posts["SP/Sirsa"]
    assert sp["level"] == "district" and sp["district_code"] == "84" and sp["division"] == "Hisar Range"
    assert posts["SP/Dabwali"]["level"] == "division"    # a police district that is not an LGD district stays with the range


def test_fetch_with_fake_get():
    class R:
        def __init__(self, text):
            self.text, self.content, self.status_code, self.encoding, self.url = text, text.encode(), 200, "utf-8", ""

    pages = {"https://x/officers": page("ka_kalaburagi.html"), "https://x/contact": page("ka_belagavi_contact.html")}
    p = {"key": "ka-test", "state": "KA", "division": "Belagavi", "urls": ["https://x/officers"],
         "office": [{"url": "https://x/contact", "post": "Regional Commissioner"}]}
    recs, files, why = M.fetch(p, lambda url, *a, **k: R(pages[url]))
    assert why == "" and len(recs) == 3 and len(files) == 2
    json.dumps(recs)


def test_seeds_are_well_formed():
    root = Path(__file__).resolve().parent.parent / "seeds"
    for f in sorted(root.glob("dept_div_*.json")):
        items = json.loads(f.read_text())
        keys = [i["key"] for i in items]
        assert len(keys) == len(set(keys)), f
        for i in items:
            pl = i["payload"]
            assert pl["reader"] in ("st_div_pages", "st_div_s3waas") and pl["state"] and pl["division"]
            assert pl.get("route") in ("abroad", "direct") and isinstance(pl.get("india_only"), bool)
            if pl["reader"] == "st_div_pages":
                assert pl["urls"] or pl.get("office")


def test_jk_police_zone_cards_and_range_tables():
    p = {"key": "jk-police", "state": "JK", "division": "Jammu", "kind": "police", "body": "Jammu and Kashmir Police",
         "table_divisions": {"1": "Jammu", "2": "Kashmir"}, "police_unit_rx": r"(?i)\b[\w -]+\b(range|zone)\b|\b(NKR|SKR|CKR)\b"}
    html = page("jk_police_zones.html")
    url = "https://jkpolice.gov.in/Zonal-Range-Hqrs"
    recs = M.parse_page(p, html, url)
    assert len(recs) == 7
    d = by_post(recs)
    dig = next(v for k, v in d.items() if "Rajouri Poonch" in k)
    assert dig["division"] == "Jammu" and dig["post_kind"] == "dig" and dig["dept"] == "police"
    assert dig["name"].startswith("Sh. Sandeep Wazir") and dig["email"] == "digrajourioff@jkpolice.gov.in"
    assert sum(1 for v in d.values() if v["division"] == "Kashmir") == 3
    ig = M.office_record(p, html, url, 9, {"post": "IGP Kashmir Zone", "anchor": r"Kashmir Zone\nJ&K", "division": "Kashmir",
                                           "police_unit": "Kashmir Zone"})
    assert len(ig) == 1
    rid, v = ig[0]
    assert v["division"] == "Kashmir" and v["post"].startswith("IGP") and v["name"].startswith("Sh. Sujit Kumar")
    assert v["email"] == "igkmr@jkpolice.gov.in" and v["phone"].startswith("0194-2458735") and v["post_kind"] == "igp"
