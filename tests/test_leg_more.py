"""Offline tests of the MLA / MLC readers added on 2026-11-11: the NeVA member directories (dforms/_leg_neva.py with leg_jk,
leg_hr, leg_hp, leg_jh, leg_ar, leg_wb, leg_uplc), Chhattisgarh (leg_cg) and Maharashtra (leg_mh), on small saved answers in
tests/data/leg/ (2-5 members each). No test touches the network."""
import json
import unicodedata

from esw_common import DATA, ROOT, Answer, check_records, fake_get, mod

def nfc(s):
    return unicodedata.normalize("NFC", s)


NEVA = ("leg_jk", "leg_hr", "leg_hp", "leg_jh", "leg_ar", "leg_wb", "leg_uplc")


def _seed(module):
    items = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())
    assert items == mod(module).items() and all(i["key"].startswith("leg_") for i in items)
    return items


def neva_get(p, default, english=None):
    """A NeVA host in one session: '/' answers, the list answers `default` until the English switch, then `english`."""
    calls, state = [], {"en": False}

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, url, headers))
        if url == f"https://{p['host']}/":
            return Answer(b"<html>home</html>", url)
        if "/Home/ChangeInEngCulture" in url:
            state["en"] = True
            return Answer(b"<html>switched</html>", url)
        if url == p["url"]:
            name = english if state["en"] else default
            return Answer((DATA / "leg" / name).read_bytes(), url) if name else None
        return None
    get.calls = calls
    return get


def test_seeds_match_items():
    for m in NEVA + ("leg_cg", "leg_mh"):
        items = _seed(m)
        assert len(items) == 1 and items[0]["payload"]["reader"] == m
    for m in NEVA:
        p = _seed(m)[0]["payload"]
        assert p["url"] == f"https://{p['host']}/ContactDirectory/FetchMembersList?MLT=16&MSLT={p['house']}&Assemblyid={p['house']}"
        assert p["host"].endswith(".neva.gov.in") and p["india_only"] is False
    assert _seed("leg_uplc")[0]["payload"]["kind"] == "LC" and _seed("leg_wb")[0]["payload"]["house"] == 18


def test_neva_constituency_and_name():
    n = mod("_leg_neva")
    assert n.constituency("Anantnag West -Anantnag (Jammu and Kashmir )") == (None, "Anantnag West", "Anantnag")
    assert n.constituency("Chrar- i - sharief -Budgam (Jammu and Kashmir )") == (None, "Chrar- i - sharief", "Budgam")
    assert n.constituency("76 - डाल्टनगंज -पलामू (Jharkhand)") == (76, "डाल्टनगंज", "पलामू")
    assert n.constituency("Tuting-Yingkiong") == (None, "Tuting-Yingkiong", "")
    assert n.name("Sh.  Bamang Felix") == "Bamang Felix" and n.name("Adv. Abdul Rahim Rather") == "Abdul Rahim Rather"
    assert n.name("श्रीमती रेणुका सिंह सरूता") == "रेणुका सिंह सरूता" and n.name("Dr. Akash Agarwal") == "Dr. Akash Agarwal"
    assert n.near("AR", "Pongchau-Wakka") == (60, "pongchouwakka")             # a spelling the ALIAS does not need to list
    assert n.near("JK", "Budgam") == (None, "")                  # JK: new seats look like other old seats, so no near match
    assert n.near("AR", "Aalo East") == (None, "")               # 0.82 to alongeast: not clear enough


def test_leg_jk_english_list():
    p = _seed("leg_jk")[0]["payload"]
    get = neva_get(p, "neva_jk_list.html")
    recs, files, why = mod("leg_jk").fetch(p, get)
    assert why == "" and [f[0] for f in files] == ["depts/leg_jk/list.html.gz"]
    assert [c[1] for c in get.calls] == [f"https://{p['host']}/", p["url"]]        # English already: no switch
    check_records(recs, "leg_jk", "elected")
    recs = dict(recs)
    r = recs["dept:leg_jk:JK-AC-30"]                                 # Chrar-i-Sharief -> the old layer's Chrar-e-Sharief (ALIAS)
    assert r["name"] == "Abdul Rahim Rather" and r["phone"] == "9697000001" and r["fax"] == "2546531"
    assert r["office_id"] == "JK-AC-30" and r["email"] == "arrather.speaker@jk.gov.in" and r["district"] == "Budgam"
    assert r["party"] == "Jammu And Kashmir National Conference"
    assert r["member_page"] == "https://jkla.neva.gov.in/Member/Details/1?AssemblyID=1"
    x = recs["dept:leg_jk:JK-AC-x-anantnag-west"]                    # a seat made in the 2022 delimitation: no number
    assert x["name"] == "Abdul Majid Bhat (Larmi)" and "office_id" not in x and x["address"].startswith("Larm Bazar")
    assert recs["dept:leg_jk:JK-AC-27"]["name"] == "Aga Syed Muntazir Mehdi"   # Budgam = the old layer's Badgam (ALIAS)


def test_leg_ar_shared_seat_and_placeholders():
    p = _seed("leg_ar")[0]["payload"]
    recs, _, why = mod("leg_ar").fetch(p, neva_get(p, "neva_ar_list.html"))
    assert why == ""
    check_records(recs, "leg_ar", "elected")
    recs = dict(recs)
    t = recs["dept:leg_ar:AR-AC-34"]                                 # Tuting-Yingkiong -> layer "Tuting Yinkgkiong" (ALIAS)
    assert t["name"] == "Alo Libang" and t["email"] == "alo.libang@nic.in" and "address" not in t     # "-" = no address
    f = [d for d in recs.values() if d["name"] == "Bamang Felix"][0]
    assert f["address"] == "ITANAGAR" and "fax" not in f and f["phone"] == "9436040028"
    shared = sorted(k for k in recs if k.startswith("dept:leg_ar:AR-AC-x-khonsa-east-"))
    assert shared == ["dept:leg_ar:AR-AC-x-khonsa-east-chakat-aboh", "dept:leg_ar:AR-AC-x-khonsa-east-wanglam-sawin"]
    assert all("2 members" in recs[k]["seat_note"] and "office_id" not in recs[k] for k in shared)


def test_leg_uplc_hindi_then_english():
    p = _seed("leg_uplc")[0]["payload"]
    get = neva_get(p, "neva_uplc_hi.html", "neva_uplc_en.html")
    recs, files, why = mod("leg_uplc").fetch(p, get)
    assert why == "" and [f[0] for f in files] == ["depts/leg_uplc/list.html.gz", "depts/leg_uplc/list-en.html.gz"]
    assert "ChangeInEngCulture" in get.calls[2][1] and "langCulCode=en-US" in get.calls[2][1] and get.calls[3][1] == p["url"]
    check_records(recs, "leg_uplc", "elected")
    recs = dict(recs)
    a = recs["dept:leg_uplc:UP-LC-dr-akash-agarwal"]
    assert a["level"] == "state" and a["post"] == "Member of Legislative Council" and a["office_id"] == "UP-LC-dr-akash-agarwal"
    assert a["area"] == "Agra Division Teachers" and a["district"] == "Teachers’ Constituency" and a["party"] == "INDEPENDENT"
    assert a["name_regional"] == "आकाश अग्रवाल" and a["area_regional"] == "आगरा खण्ड शिक्षक" and a["party_regional"] == "निर्दलीय"
    assert a["phone"] == "8193849760" and a["email"] == "bsslucknow1@gmail.com" and a["address"].startswith("बी-62")
    assert recs["dept:leg_uplc:UP-LC-akshay-pratap-singh"]["area"] == "Pratapgrah Local Authorities"


def test_leg_neva_english_list_missing():
    p = _seed("leg_hr")[0]["payload"]
    recs, files, why = mod("leg_hr").fetch(p, neva_get(p, "neva_uplc_hi.html", None))
    assert recs == [] and "English" in why and len(files) == 1
    recs, files, why = mod("leg_hr").fetch(p, lambda url, **k: None)
    assert recs == [] and files == [] and why == "no answer"


def test_leg_cg():
    p = _seed("leg_cg")[0]["payload"]
    recs, files, why = mod("leg_cg").fetch(p, fake_get({p["url"]: "leg/cg_mla_current.html"}))
    assert why == "" and files[0][0] == "depts/leg_cg/mla_current.html.gz"
    check_records(recs, "leg_cg", "elected")
    recs = dict(recs)
    assert sorted(recs) == ["dept:leg_cg:CG-AC-1", "dept:leg_cg:CG-AC-19", "dept:leg_cg:CG-AC-2", "dept:leg_cg:CG-AC-7"]  # 67 vacant
    a = recs["dept:leg_cg:CG-AC-2"]
    assert a["name"] == "श्याम बिहारी जायसवाल" and a["party"] == "BJP" and a["party_regional"] == "भारतीय जनता पार्टी"
    assert a["phone"] == "97544 28962" and a["email"] == "shyambiharijaiswalmla@gmail.com"
    assert nfc(a["area"]) == nfc("2 - मनेन्द्रगढ़")
    assert a["permanent_address"].endswith("पिन- 497 449") and a["residence_address"].startswith("सी-1, सी-2")
    assert a["address"] == a["residence_address"]
    r = recs["dept:leg_cg:CG-AC-7"]
    assert r["phone"] == "0771-3583041, 9425256555" and nfc(r["constituency"]) == nfc("रामानुजगंज (अ.ज.जा.)")
    assert recs["dept:leg_cg:CG-AC-19"]["party"] == "INC"


def test_leg_mh():
    mh = mod("leg_mh")
    recs = mh.parse((DATA / "leg" / "mh_gazette_layout.txt").read_text().split("\f"))
    check_records(recs, "leg_mh", "elected")
    recs = dict(recs)
    assert len(recs) == 22                                           # the Marathi schedule is left out
    assert recs["dept:leg_mh:MH-AC-6"]["name"] == "Raghavendra (Ramdada) Manohar Patil"
    assert recs["dept:leg_mh:MH-AC-7"]["name"] == "Agrawal Anupbhaiyya Omprakash"
    assert recs["dept:leg_mh:MH-AC-77"]["name"] == "Prof. Dr. Ashok Ramaji Wooike"           # name and party with one space
    assert recs["dept:leg_mh:MH-AC-78"]["party"] == "Indian National Congress"
    assert recs["dept:leg_mh:MH-AC-112"]["name"] == "Bornare (Sir) Ramesh Nanasaheb"          # last word on 113's line
    assert recs["dept:leg_mh:MH-AC-113"]["name"] == "Suhas (Aanna) Dwarkanath Kande"
    j = recs["dept:leg_mh:MH-AC-287"]
    assert j["constituency"] == "Tasgaon-Kavathe Mahankal" and j["party"] == "Nationalist Congress Party - Sharadchandra Pawar"
    assert j["office_id"] == "MH-AC-287" and j["area"] == "287 - Tasgaon-Kavathe Mahankal" and "phone" not in j


def test_leg_mh_needs_pdftotext(monkeypatch):
    from dforms import _pdftext
    monkeypatch.setattr(_pdftext, "layout_pages", lambda c: (["x"], "pypdf"))
    p = _seed("leg_mh")[0]["payload"]
    recs, files, why = mod("leg_mh").fetch(p, lambda url, **k: Answer(b"%PDF-1.4 x", url))
    assert recs == [] and files and "pdftotext" in why


def test_neva_spellings_and_brackets():
    """2026-11-12 load: 9 MLA records without a seat (HR 5, WB 2, HP 1, OD 1); each now gets its ECI number."""
    n, se, esw = mod("_leg_neva"), mod("_leg_se"), mod("_esw")
    assert n.constituency("Nuh -Mewat(Nuh) (Haryana)") == (None, "Nuh", "Mewat(Nuh)")
    assert n.constituency("Ferozepur Jhirka -Mewat(Nuh)") == (None, "Ferozepur Jhirka", "Mewat")
    assert n.constituency("Kinnaur -KINNAUR (ST)*") == (None, "Kinnaur", "KINNAUR")
    assert n.near("HR", "Ferozepur Jhirka")[0] == 80 and n.near("HR", "Nuh")[0] == 79 and n.near("HP", "Kinnaur")[0] == 68
    hr, wb = mod("leg_hr").ALIAS, mod("leg_wb").ALIAS
    assert [se.seat("HR", None, c, d, hr)[0] for c, d in (("Mehem", "Rohtak"), ("Punhana", "Mewat"), ("Kharkhoda", "Sonipat"))] == [60, 81, 30]
    assert se.seat("WB", None, "Nawda", "Murshidabad", wb)[0] == 74
    assert esw.ac_no("WB", "Bishnupur", "South 24 Parganas") == 146 and esw.ac_no("WB", "Bishnupur", "Bankura") == 255
