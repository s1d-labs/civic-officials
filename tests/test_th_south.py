"""Offline tests of the town-heads South readers (dforms/th_tn.py, th_kl.py): commissioners, secretaries and staff of the town
bodies of Tamil Nadu and Kerala, from saved answers of the bodies' own sites."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod


def load_seed(name):
    return json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text(encoding="utf-8"))


# ---- th_tn ----
def tn_item(site):
    return next(i["payload"] for i in mod("th_tn").items() if i["payload"]["site"] == site)


def tn_run(site, en, ta=None):
    m = mod("th_tn")
    p = tn_item(site)
    routes = {m.search_url(site, "commissioner"): en}
    if ta:
        routes[m.search_url(site, "ஆணையாளர்")] = ta
    return m.fetch(p, fake_get(routes))


def test_th_tn_items_match_seed():
    s = load_seed("th_tn")
    assert mod("th_tn").items() == s and len(s) == 154
    assert sum(1 for i in s if i["payload"]["lgd_code"]) == 153 and not s[0]["payload"]["india_only"]


def test_th_tn_ambur_head_and_staff():
    recs, files, why = tn_run("ambur", "th_tn_ambur_en.json", "th_tn_ambur_ta.json")
    assert why == "" and len(files) == 2
    check_records(recs, "th_tn", "town_body")
    d = dict(recs)
    h = d["dept:th_tn:TN--ambur-commissioner"]
    # the newest Commissioner page wins (the Tamil one, 2025-10-24 12:40, after the English one of 12:22)
    assert h["role"] == "head" and h["phone"] == "7397392691" and h["email"] == "commr.ambur@tn.gov.in"
    assert h["lgd_code"] == "252391" and h["src_pos"]["id"] == 1733 and h["src_url"].endswith("&per_page=50")
    assert h["src_sha256"] and h["page_modified"].startswith("2025-10-24")
    # staff table (2026-07): named rows, no second commissioner record
    st = [v for v in d.values() if v["role"] != "head"]
    assert d["dept:th_tn:TN--ambur-manager"]["name"] == "Damodharan" and d["dept:th_tn:TN--ambur-manager"]["grade"] == "C"
    assert d["dept:th_tn:TN--ambur-manager"]["src_pos"]["row"] == 4 and len(st) > 50
    assert not any(v["post"] == "Commissioner" and v["role"] != "head" for v in d.values())
    # the office's posts with mobiles (Officers Details), only the body's own rows
    eng = [v for v in d.values() if v.get("post_from") == "directory"]
    assert eng and all(v["office"] == eng[0]["office"] for v in eng)
    assert not any("காவல்" in v["office"] for v in eng)


def test_th_tn_copied_pages_dropped():
    # Erode's Tamil Commissioner page is Tiruvannamalai's (commr.thiruvannamalai@): dropped; the English page names the head
    recs, files, why = tn_run("erode", "th_tn_erode_en.json", "th_tn_erode_ta.json")
    h = dict(recs)["dept:th_tn:TN--erode-commissioner"]
    assert h["name"] == "THIRU . ARPIT JAIN" and h["qualification"].startswith("I.A.S.") and h["in_charge"] is True
    assert h["email"] == "commr.erode@tn.gov.in"
    assert not any("Baskar" in (v.get("name") or "") for _, v in recs)       # Who's Who copies are not read


def test_th_tn_degree_cut():
    recs, _, _ = tn_run("arakkonam", "th_tn_arakkonam_en.json")
    h = dict(recs)["dept:th_tn:TN--arakkonam-commissioner"]
    assert h["name"] == "Thiru. J. VEERAVANJINATHAN" and h["qualification"] == "B.Sc." and h["phone"] == "04177 -237430"


def test_th_tn_no_answer():
    assert mod("th_tn").fetch(tn_item("ambur"), fake_get({}))[2] == "no answer"


# ---- th_kl ----
def kl_item(host):
    return next(i["payload"] for i in mod("th_kl").items() if f"//{host}." in i["payload"]["url"])


def kl_run(host, f):
    p = kl_item(host)
    return mod("th_kl").fetch(p, fake_get({p["url"]: f}))


def test_th_kl_items_match_seed():
    s = load_seed("th_kl")
    assert mod("th_kl").items() == s and len(s) == 93 and all(i["payload"]["url"].endswith("/en/officials") for i in s)


def test_th_kl_table_with_mobiles():
    recs, files, why = kl_run("koduvallymunicipality", "th_kl_koduvally.html")
    assert why == "" and files[0][0].startswith("depts/th_kl/m") and files[0][0].endswith(".html.gz")
    check_records(recs, "th_kl", "town_body")
    d = dict(recs)
    s = d["dept:th_kl:KL-kozhikode-koduvally-secretary"]
    assert s["name"] == "Sugadhakumar M" and s["phone"] == "9188955279" and s["role"] == "head" and s["src_pos"] == {"table": 1, "row": 2}
    off = d["dept:th_kl:KL-kozhikode-koduvally-office"]
    assert off["email"] == "koduvallymunicipality@gmail.com" and off["last_updated"].startswith("03-Nov-2026")
    assert all(v["lgd_code"] == s["lgd_code"] for v in d.values()) and s["lgd_code"]


def test_th_kl_header_under_title_and_sections():
    recs, _, why = kl_run("thodupuzhamunicipality", "th_kl_thodupuzha.html")
    d = dict(recs)
    s = d["dept:th_kl:KL-idukki-thodupuzha-secretary"]
    assert s["name"] == "Ansal Issac" and s["phone"] == "9916407067" and s["section"] == "General Section"
    assert sum(1 for v in d.values() if v.get("name")) == 59


def test_th_kl_two_scripts_and_malayalam_headers():
    recs, _, _ = kl_run("mukkammunicipality", "th_kl_mukkam.html")
    s = next(v for _, v in recs if v.get("name") == "Krishnagopal A")
    assert s["name_regional"] == "കൃഷ്ണഗോപാൽ എ" and s["post"] == "Secretary" and s["post_regional"] == "സെക്രട്ടറി"
    recs, _, _ = kl_run("kondottymunicipality", "th_kl_kondotty.html")
    assert sum(1 for _, v in recs if v.get("name")) == 25
    assert any(v["post"] == "റവന്യൂ ഇന്സ്പെക്ടര്" for _, v in recs)


def test_th_kl_chart_page_gives_office_only():
    recs, _, why = kl_run("panoormunicipality", "th_kl_panoor.html")
    assert [v["post"] for _, v in recs] == ["Office"] and recs[0][1]["phone"] == "0490-2311340"


def test_th_kl_plain_table():
    recs, _, _ = kl_run("ettumanoormunicipality", "th_kl_ettumanoor.html")
    d = dict(recs)
    eng = [v for v in d.values() if v.get("section") == "Engineering Department"]
    assert len(eng) == 3 and d["dept:th_kl:KL-kottayam-ettumanoor-municipal-secretary"]["name"] == "Shri Shibu C K"


def test_th_tn_officers_with_names_poonamallee():
    # Officers Details with a name column (S.No | name | designation | mobile | e-mail | work), full search answer 2026-11-13:
    # the reader used to keep the first row only (2 of the 8 data rows). Now every row: 6 officers, 2 vacant posts.
    recs, files, why = tn_run("poonamallee", "th_tn_poonamallee_en.json")
    assert why == ""
    d = {v["post"]: v for _, v in recs if v.get("post_from") == "directory"}
    assert set(d) == {"ASSISTANT EXECUTIVE ENGINEER (I/C)", "ASSISTANT REVENUE OFFICER", "TOWN PLANNING OFFICER", "MANAGER",
                      "ACCOUNTANT", "SANITARY OFFICER", "SANITARY INSPECTOR"}      # the commissioner row: the head record has it
    assert len(recs) == 8 and dict(recs)["dept:th_tn:TN--poonamallee-commissioner"]["name"] == "M. SARAVANAKUMAR"
    assert d["ASSISTANT REVENUE OFFICER"]["name"] == "R.S. RAJAN" and d["ASSISTANT REVENUE OFFICER"]["phone"] == "8939403799"
    assert d["ASSISTANT REVENUE OFFICER"]["email"] == "commr.poonamallee@tn.gov.in"       # ",," repeats the row above
    assert d["SANITARY INSPECTOR"]["work"] == "BIRTH, DEATH AND SANITATION"
    assert d["MANAGER"]["vacant"] is True and not d["MANAGER"].get("name")


def test_th_kl_seat_name_column_is_the_post():
    """Shornur officials page, the full saved page (bucket copy c4a31ccf..., 2026-11-12): header "Sl No | Saet Name | Emp. Name |
    Emp. PEN". Before, "Saet Name" was taken as the name column, no post column was found and the 36 officials were dropped
    (1 office record). Now 36 officials + the office."""
    import gzip
    p = kl_item("shornurmunicipality")
    html = gzip.decompress((DATA / "th_kl" / "shornur_officials_full.html.gz").read_bytes()).decode("utf-8")
    recs = mod("th_kl").parse(html, p)[0]
    people = [d for _, d in recs if d.get("name")]
    assert len(recs) == 37 and len(people) == 36
    assert people[0]["name"] == "RAJESH P S" and people[0]["post"] == "Secretary, Local Self Government Institution"
    assert people[-1]["name"] == "MANEESHA M"
