"""Offline tests of the north / west / central MLA readers (dforms/leg_br, leg_ga, leg_rj, leg_mp, leg_dl) on small saved samples
in tests/data/leg/. The lead merges this file into tests/test_leg.py."""
from esw_common import *  # noqa: F401,F403

LEG = DATA / "leg"


def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def _fetch(module, sample, payload=None):
    p = payload or _seed(module)[0]["payload"]
    get = fake_get({p["url"]: "leg/" + sample})
    recs, files, why = mod(module).fetch(p, get)
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/")
    check_records(recs, module, "elected")
    return dict(recs)


def test_seeds_match_items():
    for st in ("br", "ga", "rj", "mp", "dl"):
        m = mod("leg_" + st)
        assert _seed("leg_" + st) == m.items(), st
        assert all(i["key"].startswith("leg_") and i["payload"]["state"] == st.upper() for i in m.items())


def test_leg_br():
    recs = _fetch("leg_br", "br_list.html")
    m = recs["dept:leg_br:BR-AC-1"]
    assert m["name"] == "SURENDRA PRASAD" and m["party"] == "INC" and m["phone"] == "9307811777"
    assert m["email"] == "mla-vnagar-bih@nic.in" and m["office_id"] == "BR-AC-1" and m["area"] == "1 - Valmiki Nagar"
    assert m["level"] == "ac" and m["post"] == "Member of Legislative Assembly" and m["email_note"]
    assert recs["dept:leg_br:BR-AC-16"]["name"] == "SACHINDRA PRASAD SINGH"
    assert _seed("leg_br")[0]["payload"]["india_only"] is True


def test_leg_ga_list():
    ga = mod("leg_ga")
    assert ga.list_ids((LEG / "ga_list.html").read_text()) == [250, 251]      # the "Expired" member is left out
    assert len(_seed("leg_ga")) == 38
    get = fake_get({ga.LIST: "leg/ga_list.html"})
    assert [i["payload"]["mem_id"] for i in ga.items(get)] == [250, 251]


def test_leg_ga_member():
    url = "https://www.goavidhansabha.gov.in/member_detail.php?mem_id=253"
    recs = _fetch("leg_ga", "ga_mem_253.html", {"reader": "leg_ga", "url": url, "state": "GA", "india_only": False, "mem_id": 253})
    m = recs["dept:leg_ga:GA-AC-6"]
    assert m["name"] == "Smt. Delilah Lobo" and m["party"] == "Bharatiya Janata Party" and m["area"] == "6 - Siolim"
    assert m["mobile"] == "9822127754" and m["phone_office"] == "9022443114" and m["phone_residence"] == "08322952272"
    assert m["residence_address"] == "H.No.181/15,Bhatti-vaddo,Parra-Bardez-Goa 403510" and "email" not in m


def test_leg_ga_cm():
    url = "https://www.goavidhansabha.gov.in/member_detail.php?dflag=CM"
    recs = _fetch("leg_ga", "ga_mem_cm.html", {"reader": "leg_ga", "url": url, "state": "GA", "india_only": False})
    m = recs["dept:leg_ga:GA-AC-17"]
    assert m["name"] == "Shri. Pramod Sawant" and m["designation"] == "Chief Minister" and m["constituency"] == "Sanquelim"
    assert m["fax"] == "(0832)2419840" and m["office_address"].startswith("Office of the Chief Minister")
    assert m["email_images"].endswith("Email_ID54_2.png")       # the email is shown only as an image


def test_leg_rj():
    recs = _fetch("leg_rj", "rj_contacts.html")
    m = recs["dept:leg_rj:RJ-AC-40"]
    assert m["name"] == "Sh. Hansraj Patel" and m["party"] == "BJP" and m["district"] == "Jaipur"
    assert m["email"] == "hansrajpatel001@gmail.com" and m["mobile"] == "9414209502" and m["phone_constituency"] == "9710000017"
    assert m["permanent_address"] == "हंसा मोती पैलेस, बस स्टेण्ड के सामने, कोटपुतली"      # ZWJ kept out, no broken words
    m = recs["dept:leg_rj:RJ-AC-38"]                                # "Neem ka thana" -> neemakathana via ALIAS
    assert m["name"] == "Sh. Suresh Modi" and m["email"] == "sureshmodi0019@gmail.com"
    assert m["residence_address"].startswith("ए-2/803, विधायक आवास") and m["terms"] == "15, 16"
    assert mod("leg_rj").ALIAS["raysinghnagar"] == "raisinghnagar"


def test_leg_mp():
    mp = mod("leg_mp")
    recs = mp.parse((LEG / "mp_suchi_layout.txt").read_text().split("\f"))
    check_records(recs, "leg_mp", "elected")
    recs = dict(recs)
    m = recs["dept:leg_mp:MP-AC-1"]
    assert m["name"] == "श्री बाबू जन्डे ल" and m["party"] == "INC" and m["party_regional"] == "इं.ने.कां."
    assert m["mobile"] == "7067689008, 9425128072" and m["email"] == "babu.jandel@mpvidhansabha.nic.in"
    assert m["residence_address"].endswith("भोपाल.") and m["permanent_address"].startswith("ग्राम सोंठवा")
    assert m["office_id"] == "MP-AC-1" and m["district"] == "श्योपुर"
    assert recs["dept:leg_mp:MP-AC-12"]["designation"] == "मंत्री"
    m = recs["dept:leg_mp:MP-AC-230"]
    assert m["phone_residence"] == "(0755) 2441462, 2441672" and m["phone_constituency"] == "(07420) 232595"
    p = _seed("leg_mp")[0]["payload"]
    assert p["india_only"] is True


def test_leg_mp_needs_pdftotext(monkeypatch):
    from dforms import _pdftext
    monkeypatch.setattr(_pdftext, "layout_pages", lambda c: (["x"], "pypdf"))
    p = _seed("leg_mp")[0]["payload"]
    get = lambda url, **k: Answer(b"%PDF-1.4 x", url)            # noqa: E731
    recs, files, why = mod("leg_mp").fetch(p, get)
    assert recs == [] and files and "pdftotext" in why


def test_leg_dl():
    recs = mod("leg_dl").parse((LEG / "dl_list_layout.txt").read_text().split("\f"))
    check_records(recs, "leg_dl", "elected")
    recs = dict(recs)
    m = recs["dept:leg_dl:DL-AC-1"]
    assert m["name"] == "Raj Karan Khatri" and m["party"] == "BJP" and m["constituency"] == "Narela"
    assert m["phone"] == "9212049876, 9310049876" and m["email"] == "rajkarankhatri1965@gmail.com"
    assert m["address"] == "1100, Pana Paposian, Mata Mansa Devi Marg, , Narela, Delhi-110040"
    assert recs["dept:leg_dl:DL-AC-4"]["name"] == "Raj Kumar Bhatia" and recs["dept:leg_dl:DL-AC-4"]["constituency"] == "Adarsh Nagar"
    assert recs["dept:leg_dl:DL-AC-49"]["email"] == "chandankrchoudharymla@gmail.com"     # "com" printed in the next row
    assert recs["dept:leg_dl:DL-AC-50"]["email"] == "shikharai.bjp@gmail.com"
    m = recs["dept:leg_dl:DL-AC-67"]                               # row 66's hidden second email overlaps row 67's cell
    assert m["email"] == "gopalrai1975@gmail.com" and m["email_overlap"] == "ajaymahawar20"


def test_leg_dl_items_follow_home_link():
    dl = mod("leg_dl")
    get = lambda url, **k: Answer(b'<a href="/sites/default/files/2027-01/list_of_member.pdf">List of Members</a>', url)  # noqa: E731
    assert dl.items(get)[0]["payload"]["url"] == "https://delhiassembly.delhi.gov.in/sites/default/files/2027-01/list_of_member.pdf"
