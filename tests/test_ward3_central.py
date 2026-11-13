"""Offline tests of the helpers of the ward3 readers of branch ward-staff-central (dforms/_ward3_central.py, dforms/ward3_kota.py)
that the case files of tests/test_ward3.py do not reach."""
from esw_common import mod


def test_zones_of():
    c3 = mod("_ward3_central")
    assert c3.zones_of("जोनल अधिकारी जोन क्र.02 एवं 05") == ["2", "5"]
    assert c3.zones_of("ज़ोनल अधिकारी जोन क्रमांक 1, 3 एवं 4 / प्रभारी योजना शाखा") == ["1", "3", "4"]
    assert c3.zones_of("उपयंत्री (विद्युत)") == []


def test_strip_title_keeps_names_that_start_like_a_title():
    c3 = mod("_ward3_central")
    assert c3.strip_title("श्री कुलदीप करोसिया") == "कुलदीप करोसिया"
    assert c3.strip_title("कु. बरखा गोहर") == "बरखा गोहर"
    assert c3.strip_title("डाॅ. शेर सिंह मीना") == "शेर सिंह मीना"


def test_post_en():
    c3 = mod("_ward3_central")
    assert c3.post_en("प्र.कार्यपालन यंत्री") == "Executive Engineer (in charge)"
    assert c3.post_en("उपयंत्री जोन क्र.01") == "Sub Engineer"
    assert c3.post_en("अति. आयुक्त/उपायुक्त") == "Additional Commissioner"
    assert c3.wing("उपयंत्री (विद्युत)", "Sub Engineer") == "electrical"


def test_kota_picks_the_newest_kota_pdf():
    k = mod("ward3_kota")
    rows = [{"Id": 15314, "DepartmentTitle": "Municipal Corporation, Kota", "IsActive": True, "AttachmentUrl": "https://x/a.pdf"},
            {"Id": 15999, "DepartmentTitle": "Municipal Corporation, Kota", "IsActive": False, "AttachmentUrl": "https://x/off.pdf"},
            {"Id": 15562, "DepartmentTitle": "Municipal Corporation, Kota", "IsActive": True, "AttachmentUrl": None},
            {"Id": 16000, "DepartmentTitle": "Municipal Corporation, Ajmer", "IsActive": True, "AttachmentUrl": "https://x/b.pdf"},
            {"Id": 15400, "DepartmentTitle": "Municipal Corporation, Kota", "IsActive": True, "AttachmentUrl": "https://x/c.pdf"}]
    assert k.pick({"Data": rows}) == "https://x/c.pdf"
    assert k.pick({"Data": {"Data": rows[:1]}}) == "https://x/a.pdf"
    assert k.pick({"Data": []}) is None
    assert k.sectors("का.वा. मुख्य स्वास्थ्य निरीक्षक से. नं. 01,02,03, व 07") == ["1", "2", "3", "7"]
    assert k.sectors("कार्य0 स्वा. निरी. (से.न. 9)") == ["9"]
