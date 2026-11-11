"""Offline tests of dforms/ulb_uk.py (Uttarakhand, Urban Development Directorate) on small saved answers in tests/data/:
ulb_uk_list-of-ulb-eo.html (the document table of the page), ulb_uk_eo.pdf (page 1 of 4 of the EO list) and ulb_uk_email.pdf
(page 1 of 3 of the email list), both cut with pypdf and without their embedded font files."""
from esw_common import *  # noqa: F401,F403

M = "ulb_uk"
EO = "https://cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/08/202609211745084968.pdf"
EMAIL = "https://cdnbbsr.s3waas.gov.in/s38208974663db80265e9bfe7b222dcb18/uploads/2026/08/202608051632633803.pdf"


def _recs():
    p = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())[0]["payload"]
    get = fake_get({p["url"]: "ulb_uk_list-of-ulb-eo.html", EO: "ulb_uk_eo.pdf", EMAIL: "ulb_uk_email.pdf"})
    recs, files, why = mod(M).fetch(p, get)
    assert why == "" and len(files) == 3 and all(f[0].startswith(f"depts/{M}/") for f in files)
    check_records(recs, M, "town_body")
    return dict(recs)


def test_ulb_uk_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())


def test_ulb_uk_links():
    found = mod(M).links((DATA / "ulb_uk_list-of-ulb-eo.html").read_text())
    assert found["eo"] == (EO, "2026-09-21") and found["email"][0] == EMAIL


def test_ulb_uk_eo_list():
    recs = _recs()
    assert len(recs) == 32
    d = recs["dept:ulb_uk:UK-nn-deharadun-deharadun-nagar-ayukt"]
    assert (d["area"], d["district"], d["body_type"], d["name"], d["post"]) == ("देहरादून", "देहरादून", "नगर निगम", "आलोक कुमार पाण्डेय", "नगर आयुक्त")
    assert d["role"] == "head" and "phone" not in d and d["email"] == "nagarnigam.ddn@gmail.com" and d["lgd_code"] == "248430"
    assert d["last_updated"] == "2026-09-21" and d["level"] == "body"
    d = recs["dept:ulb_uk:UK-nn-deharadun-rishikesh-up-nagar-ayukt-adhishasi-adhikari-shreni-1"]     # 4th officer line of a body
    assert d["name"] == "अंकिता जोशी" and d["phone"] == "9958523095" and d["role"] == "deputy"
    d = recs["dept:ulb_uk:UK-npp-deharadun-harabartapur-pradhan-sahayak-prabhari-adhishasi-adhikari"]
    assert d["name"] == "विरेन्द्र पंवार" and d["phone"] == "9411145838" and d["email"] == "eoher-mb-uk@nic.in, nppherbertpur84@gmail.com"
    d = recs["dept:ulb_uk:UK-np-haridvar-piran-kaliyar-varishth-sahayak-prabhari-adhishasi-adhikari"]
    assert d["name"] == "कुलदीप चौहान" and d["district"] == "हरिद्वार" and d["phone"] == "8057875754"
    assert {d["district"] for d in recs.values()} == {"देहरादून", "हरिद्वार"}    # one district cell over many bodies


def test_ulb_uk_officer_without_comma():
    assert mod(M).officer("Jh lquhy iqjksfgr izHkkjh vf/k'kklh vf/kdkjh") == ("सुनील पुरोहित", "प्रभारी अधिशासी अधिकारी")
