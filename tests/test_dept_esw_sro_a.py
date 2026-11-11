from esw_common import *  # noqa: F401,F403


# ---- Sub-registrars: Karnataka, Kerala, Andhra Pradesh, Odisha, Delhi, Uttarakhand, Jammu and Kashmir, Puducherry, Goa (dforms/sro_*)

def _sro(module, sample, check=True):
    p = json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())[0]["payload"]
    get = fake_get({p["url"]: sample})
    recs, files, why = mod(module).fetch(p, get)
    assert why == "" and files and files[0][0].startswith(f"depts/{module}/") and get.calls[0][1] == p["url"]
    if check:
        check_records(recs, module, "registration")
    return dict(recs)


def test_sro_ka():
    recs = _sro("sro_ka", "sro_ka.html")
    d = recs["dept:sro_ka:KA-SRO-malleshwaram"]
    assert d["name"] == "Prakash Nayak" and d["designation"] == "FDA, Sub registrar (I/C)" and d["phone"] == "8050479342"
    assert d["email"] == "sr.malleswaram@karnataka.gov.in" and d["registration_district"] == "Gandhinagar"
    assert "designation" not in recs["dept:sro_ka:KA-SRO-gandhinagara"]


def test_sro_kl():
    recs = _sro("sro_kl", "sro_kl.html")
    d = recs["dept:sro_kl:KL-SRO-trivandrum-amaravila"]
    assert d["post"] == "Sub Registrar" and d["phone"] == "0471-2234399" and d["email"] == "sroamvla.regn@kerala.gov.in"
    assert recs["dept:sro_kl:KL-DR-trivandrum-audit"]["level"] == "district"
    assert recs["dept:sro_kl:KL-DIG-south-zone"]["level"] == "zone"


def test_sro_ap():
    recs = _sro("sro_ap", "sro_ap.pdf")
    d = recs["dept:sro_ap:AP-SRO-101"]
    assert d["area"] == "Amadalavalasa" and d["district"] == "Srikakulam" and d["phone"] == "7093921337"
    assert d["email"] == "sr.sklm.amadalavalasa@igrs.ap.gov.in" and d["last_updated"] == "2025-09-22"
    assert recs["dept:sro_ap:AP-SRO-115"]["area"] == "Srikakulam"                     # "SRIKAKULAM(R.O)"
    assert "phone" not in recs["dept:sro_ap:AP-SRO-209"]                             # mobile "0" on the list
    assert recs["dept:sro_ap:AP-DR-srikakalum"]["level"] == "district"


def test_sro_ap_lines():
    lines = ["   3       DR.Eluru (Audit)                     draudit.eluru @igrs.ap.gov.in                            7093921455",
             "                                                SPS NELLORE DISTRICT",
             "   1       KAVALI                                    701        sr.nlr.kavali@igrs.ap.gov.in             7093921590"]
    recs = dict(mod("sro_ap").parse(["\n".join(lines)]))
    assert recs["dept:sro_ap:AP-DR-AUDIT-eluru"]["email"] == "draudit.eluru@igrs.ap.gov.in"
    assert recs["dept:sro_ap:AP-SRO-701"]["district"] == "SPS Nellore"


def test_sro_od():
    recs = _sro("sro_od", "sro_od.html")
    d = recs["dept:sro_od:OD-SRO-anugola-athamallik"]
    assert d["name"] == "PRASANA TETE" and d["phone"] == "9668418493" and d["district"] == "Anugola"
    dr = recs["dept:sro_od:OD-DR-anugola"]
    assert dr["level"] == "district" and dr["phone"] == "9437529295, 06764-230491"


def test_sro_dl():
    recs = _sro("sro_dl", "sro_dl.html", check=False)      # the page gives no name, phone or email: office + address only
    d = recs["dept:sro_dl:DL-SRO-jangpura"]
    assert d["district"] == "South East" and d["level"] == "subdistrict" and d["address"].endswith("New Delhi-110024")
    assert recs["dept:sro_dl:DL-SRO-badarpur"]["district"] == "South East"           # rowspan carried down
    assert all(r.startswith("dept:sro_dl:") and v["dept"] == "registration" for r, v in recs.items())


def test_sro_uk():
    recs = _sro("sro_uk", "sro_uk.html")
    d = recs["dept:sro_uk:UK-SRO-dehradun-i"]
    assert d["name"] == "Smt. Pushpa Negi (RC Incharge)" and d["email"] == "sr1deh-sro-uk@nic.in" and d["phone"] == "9760252257"
    assert recs["dept:sro_uk:UK-DR-dehradun"]["level"] == "district"
    assert recs["dept:sro_uk:UK-SRO-chakrata"]["designation"] == "Incharge Sub Registrar"
    assert "name" not in recs["dept:sro_uk:UK-HQ-addl-inspector-general"]               # "—-" on the page


def test_sro_jk():
    recs = _sro("sro_jk", "sro_jk.html")
    d = recs["dept:sro_jk:JK-SRO-r-s-pura"]
    assert d["name"] == "Mehmood Riaz,JKAS" and d["phone"] == "9419172154" and d["division"] == "Jammu Division"
    assert recs["dept:sro_jk:JK-SRO-budgam"]["division"] == "Kashmir Division"


def test_sro_py():
    recs = _sro("sro_py", "sro_py.html")
    d = recs["dept:sro_py:PY-SRO-bahour"]
    assert d["name"] == "N.Rajan" and d["phone"] == "0413-2634243" and d["email"] == "srobah.pon@nic.in"
    assert recs["dept:sro_py:PY-SRO-mahe"]["district"] == "Mahe"


def test_sro_ga():
    recs = _sro("sro_ga", "sro_ga.html")
    assert recs["dept:sro_ga:GA-SRO-tiswadi"]["phone"] == "9405864319"                # office at Panaji
    assert recs["dept:sro_ga:GA-SRO-bardez"]["town"] == "Mapusa"
    st = recs["dept:sro_ga:GA-SR-state"]
    assert st["email"] == "srhns-rd.goa@nic.in" and st["phone"] == "+91 832 2437136" and st["level"] == "state"
