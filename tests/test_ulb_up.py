"""Offline tests of dforms/ulb_up.py (Uttar Pradesh, Directorate of Local Bodies) on small saved answers in tests/data/:
ulb_up_listnn.htm (header + 3 of the 17 nagar nigam rows), ulb_up_elected-npp.pdf (page 1 of 6) and ulb_up_elected-np.pdf
(page 3 of 16), both cut with pypdf and without their embedded font files (text extraction does not need them)."""
from esw_common import *  # noqa: F401,F403

M = "ulb_up"


def _run(kind, sample):
    p = next(i["payload"] for i in json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text()) if i["payload"]["kind"] == kind)
    recs, files, why = mod(M).fetch(p, fake_get({p["url"]: sample}))
    assert why == "" and files and files[0][0].startswith(f"depts/{M}/")
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_up_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_up_fix():
    fix = mod(M).fix
    assert fix("Ůवीण कु मार") == "प्रवीण कुमार"              # conjunct glyph, gap after कु
    assert fix("अɊ िपछड़ा वगŊ") == mod(M).nfc("अन्य पिछड़ा वर्ग")   # i-sign before its consonant, reph after its syllable
    assert fix("खुशŎद जहाँ") == "खुर्शीद जहाँ"                # ी + reph in one glyph
    assert fix("चȾ Ůकाश वमाŊ") == "चन्द्र प्रकाश वर्मा"


def test_ulb_up_nagar_nigam():
    recs = _run("nn", "ulb_up_listnn.htm")
    assert len(recs) == 6
    mayor = recs["dept:ulb_up:UP-nn-ayodhy-ayodhy-mayor"]
    assert mayor["area"] == "अयोध्या" and mayor["post"] == "महापौर" and mayor["role"] == "chair"
    assert mayor["name"] == "गिरीश पति त्रिपाठी" and mayor["phone"] == "9415140105" and mayor["level"] == "body"
    ayukt = recs["dept:ulb_up:UP-nn-ayodhy-ayodhy-nagar-ayukt"]
    assert ayukt["role"] == "head" and ayukt["name"] == "विशाल सिंह" and ayukt["phone"] == "05278-233093, 8189077815"
    assert ayukt["email"] == "nagarnigamayodhya@gmail.com" and ayukt["district"] == "अयोध्या" and ayukt["body_type"] == "नगर निगम"
    assert ayukt["lgd_code"] == "249391" and ayukt["office_id"] == mayor["office_id"] == "UP-NN-ayodhy-ayodhy"
    prayag = recs["dept:ulb_up:UP-nn-prayagaraj-prayagaraj-nagar-ayukt"]          # body cell "प्रयागराजhttp://..." (no break)
    assert prayag["area"] == "प्रयागराज" and prayag["website"] == "http://allahabadmc.gov.in" and prayag["name"] == "चन्द्र मोहन गर्ग"


def test_ulb_up_npp_chairs():
    recs = _run("npp", "ulb_up_elected-npp.pdf")
    assert len(recs) == 35 and {d["serial"] for d in recs.values()} == set(range(1, 36))
    assert all(d["post"] == "अध्यक्ष" and d["role"] == "chair" and d["body_type"] == "नगर पालिका परिषद" for d in recs.values())
    d = recs["dept:ulb_up:UP-npp-amaroh-dhanaur-chairperson"]
    assert (d["area"], d["district"], d["name"], d["phone"]) == ("धनौरा", "अमरोहा", "प्रवीण कुमार", "9837067731")
    assert d["relative"] == "कृष्ण कुमार" and d["reservation"] == "अनारक्षित"
    d = recs["dept:ulb_up:UP-npp-amaroh-gajaraul-chairperson"]          # three cells wrap onto the line below
    assert d["name"] == "राजेंद्री उर्फ उमा देवी" and d["reservation"] == "अनुसूचित जाति महिला" and d["phone"] == "9897898539"
    d = next(d for d in recs.values() if d["area"] == "जलालपुर")        # district "अम्बेडकर नगर" over two lines
    assert d["district"] == "अम्बेडकर नगर" and d["name"] == "खुर्शीद जहाँ" and d["reservation"] == "अन्य पिछड़ा वर्ग महिला"
    d = next(d for d in recs.values() if d["area"] == "गंगाघाट")          # relative wraps
    assert d["name"] == "कौमुदी पाण्डेय" and d["relative"] == "संदीप कुमार पाण्डेय"


def test_ulb_up_np_chairs():
    recs = _run("np", "ulb_up_elected-np.pdf")
    assert len(recs) == 31 and {d["serial"] for d in recs.values()} == set(range(71, 102))
    d = recs["dept:ulb_up:UP-np-et-raj-k-ramapur-chairperson"]
    assert (d["area"], d["district"], d["name"], d["phone"]) == ("राजा का रामपुर", "एटा", "सुनीता", "7627117304")
    assert d["body_type"] == "नगर पंचायत" and d["area_latin"] == "Raj K Ramapur"
