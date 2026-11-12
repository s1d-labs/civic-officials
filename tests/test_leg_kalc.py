"""Karnataka Legislative Council members (dforms/leg_kalc.py) from the Council's contact directory of 18-08-2026, a PDF in
the legacy Nudi font (cforms/cn_nudi.py). The fixture is the PDF's pdftotext -raw text (archive.s1d.me copy of 2026-11-08,
kla.kar.nic.in/council/members/mcontact/mcontact18082026.pdf) and the list page that links it."""
import json

from esw_common import DATA, ROOT, Answer, check_records, mod

D = DATA / "leg_kalc"


def _recs():
    m = mod("leg_kalc")
    return dict(m.parse_text((D / "mcontact18082026_raw.txt").read_text(encoding="utf-8"),
                             "https://kla.kar.nic.in/council/members/mcontact/mcontact18082026.pdf", "18-08-2026"))


def test_leg_kalc_seed_and_link():
    m = mod("leg_kalc")
    assert json.loads((ROOT / "seeds" / "dept_leg_kalc.json").read_text()) == m.items()
    assert m.latest_pdf((D / "memberslist.htm").read_text()) == \
        "https://kla.kar.nic.in/council/members/mcontact/mcontact18082026.pdf"
    assert m.latest_pdf('<a href="mcontact/mcontact07082026.pdf"> <a href="mcontact/mcontact25112025.pdf">').endswith(
        "mcontact07082026.pdf")
    assert m.latin("ವಿಜಯ್ ಕುಮಾರ್") == "vijay kumaar"


def test_leg_kalc_members():
    r = _recs()
    assert len(r) == 70 and all(d.get("mobile") and d.get("address") for d in r.values())
    check_records(list(r.items()), "leg_kalc", "elected")
    ch = r["dept:leg_kalc:KA-LC-saliim-ahmad"]                       # the Chairman
    assert ch["name"] == "ಸಲೀಂ ಅಹ್ಮದ್" and ch["name_regional"] == "ಶ್ರೀ ಸಲೀಂ ಅಹ್ಮದ್" and ch["level"] == "state"
    assert ch["designation"] == "ಮಾನ್ಯ ಸಭಾಪತಿಯವರು, ಕರ್ನಾಟಕ ವಿಧಾನ ಪರಿಷತ್ತು"
    assert ch["mobile"] == "9845061890" and ch["phone_office"] == "080-22258575, 22259112, 22284547"
    assert ch["fax"] == "080 22252068" and ch["second_address"].endswith("ವೆಸ್ಟ್ ಆಫ್ ಕಾರ್ಡ್ ರೋಡ್, ರಾಜಾಜಿನಗರ, ಬೆಂಗಳೂರು- 560086.")
    u = r["dept:leg_kalc:KA-LC-umaashrii"]                           # "ಡಾ:" taken off the name; page title not in the address
    assert u["name"] == "ಉಮಾಶ್ರೀ" and u["mobile"] == "9448852737, 9945409523"
    assert u["second_address"] == "ನಂ.49/38, 39ನೇ ‘ಎ’ ಕ್ರಾಸ್, 11ನೇ ಮುಖ್ಯರಸ್ತೆ, 4ನೇ ಟಿ ಬ್ಲಾಕ್, ಜಯನಗರ, ಬೆಂಗಳೂರು – 560 041."
    v = r["dept:leg_kalc:KA-LC-ke-viveekaanmda"]
    assert (v["name"], v["phone"], v["last_updated"]) == ("ಕೆ. ವಿವೇಕಾನಂದ", "9916106055", "18-08-2026")
    assert v["address"] == "ನಂ.3869, “ಮಡಿಲು ನಿಲಯ”, ಹಂಪಿ ವೃತ್ತದ ಹತ್ತಿರ, ವಿಜಯನಗರ 2ನೇ ಹಂತ, ಮೈಸೂರು-17."


def test_leg_kalc_fetch_follows_latest_link(monkeypatch):
    m = mod("leg_kalc")
    monkeypatch.setattr(m._pdfcells, "ensure_poppler", lambda: True)
    monkeypatch.setattr(m, "raw_text", lambda content: (D / "mcontact18082026_raw.txt").read_text(encoding="utf-8"))
    p = m.items()[0]["payload"]
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append(url)
        if url == p["url"]:
            return Answer((D / "memberslist.htm").read_bytes(), url)
        return Answer(b"%PDF-1.7 stand-in", url)
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 70 and calls[1].endswith("mcontact18082026.pdf")
    assert [f[0] for f in files] == ["depts/leg_kalc/memberslist.html.gz", "depts/leg_kalc/mcontact18082026.pdf.gz"]
