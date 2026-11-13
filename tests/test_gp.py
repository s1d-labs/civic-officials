"""Offline tests of the gram panchayat secretary readers (dforms/gp_*.py) on saved pages in tests/data/gp/."""
import json
import re

from esw_common import DATA, ROOT, check_records, fake_get, mod  # noqa: F401


def _gj(label):
    m = mod("gp_gj_tcm")
    return m, next(i["payload"] for i in m.items() if i["key"] == f"gp_gj_tcm:{label}")


def _common(recs):
    check_records(recs, "gp_gj_tcm", "rural_development")
    for rid, d in recs:
        assert d["level"] == "gram_panchayat" and d["state"] == "GJ" and d.get("district") and d.get("area"), d
        assert d["src_pos"]["table"] >= 1 and d["src_pos"]["row"] >= 2 and d["src_url"] == d["source"], d
        assert d.get("cells"), d


def test_gp_gj_tcm_seeds():
    m = mod("gp_gj_tcm")
    seeds = json.loads((ROOT / "seeds" / "dept_gp_gj_tcm.json").read_text())
    assert seeds == m.items() and len(seeds) == 33 and len({s["key"] for s in seeds}) == 33
    assert {s["payload"]["district"] for s in seeds} >= {"Kheda", "Dangs", "Banas Kantha", "Panch Mahals", "Kachchh"}
    assert m.METHOD


def test_gp_gj_tcm_district_flow_tapi():
    m, p = _gj("tapidp")
    get = fake_get({p["url"]: "gp/gj_tapi_home.html",
                    "https://tapidp.gujarat.gov.in/gu/taluka/Vyara/home": "gp/gj_tapi_vyara_home.html",
                    "https://tapidp.gujarat.gov.in/gu/taluka/Vyara/tcm-list": "gp/gj_tapi_vyara_tcm.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 30
    _common(recs)
    urls = [u for _, u, _ in get.calls]
    assert len(urls) == 10 and urls.count("https://tapidp.gujarat.gov.in/gu/Tcm-List") == 1   # 7 taluka homes + 2 lists
    d = dict(recs)
    r = d["dept:gp_gj_tcm:tapi:vyara:1-2"]
    assert r["name"] == "ચૌધરી હર્ષાબેન એન." and r["phone"] == "6352348836" and r["sejo"] == "કરંજવેલ"
    assert r["villages"] == "કરંજવેલ, કાટકુઈ, કપડવણ" and r["taluka"] == "Vyara" and r["district"] == "Tapi"
    assert r["post"] == "Talati-cum-Mantri (Panchayat Secretary)" and "extra_charge" not in r      # "-" = none
    assert r["cells"]["સોમવાર"] == "કરંજવેલ"                                                     # visiting days kept
    assert files and files[0][0] == "depts/gp_gj_tcm/tapi/gu-taluka-vyara-tcm-list.html.gz"


def test_gp_gj_tcm_sarpanch_and_tcm_in_one_table():
    m, p = _gj("botaddp")
    url = "https://botaddp.gujarat.gov.in/gu/taluka/Botad/Botad-Elected-Sarpanch-TCM-Details"
    recs = m.records((DATA / "gp/gj_botad_sarpanch_tcm.html").read_text(), url, p, "Botad")
    _common(recs)
    assert len(recs) == 51
    r = dict(recs)["dept:gp_gj_tcm:botad:botad:1-2"]
    assert r["name"] == "શ્રી એ.એન.ચૌહાણ" and r["phone"] == "9904457087" and r["area"] == "ઢાંકણીયા"
    assert r["sarpanch_name"] == "જોગરાણા જાનાબેન નગાભાઇ" and r["sarpanch_phone"] == "9824450598"
    assert r["src_pos"] == {"table": 1, "row": 2}


def test_gp_gj_tcm_employee_list_with_designation():
    m, p = _gj("mahisagardp")
    url = "https://mahisagardp.gujarat.gov.in/gu/taluka/Balasinor/TCM-Details"
    recs = m.records((DATA / "gp/gj_mahisagar_balasinor_tcm.html").read_text(), url, p, "Balasinor")
    _common(recs)
    r = dict(recs)["dept:gp_gj_tcm:mahisagar:balasinor:1-3"]
    assert r["name"] == "શ્રીમતિ.પી.જે.અમીન" and r["phone"] == "9978415701" and r["designation"] == "ત.ક મંત્રી"


def test_gp_gj_tcm_ditto_taluka():
    m, p = _gj("ahmedabaddp")
    url = "https://ahmedabaddp.gujarat.gov.in/gu/taluka/Sanand/Talati-cum-Ministers-Info"
    recs = m.records((DATA / "gp/gj_ahmedabad_sanand_tcm.html").read_text(), url, p, "Sanand")
    _common(recs)
    d = dict(recs)
    r = d["dept:gp_gj_tcm:ahmedabad:sanand:1-3"]
    assert r["taluka_regional"] == "સાણંદ" and r["area"] == "હિરાપુર" and r["phone"] == "9724788595"     # " = the cell above
    assert all(x.get("name") for _, x in recs)


# ---- Karnataka: Zilla Panchayat gram panchayat pages ----
def _ka(label):
    m = mod("gp_ka_zp")
    return m, next(i["payload"] for i in m.items() if i["key"] == f"gp_ka_zp:{label}")


def test_gp_ka_zp_seeds():
    m = mod("gp_ka_zp")
    seeds = json.loads((ROOT / "seeds" / "dept_gp_ka_zp.json").read_text())
    assert seeds == m.items() and len(seeds) == 28 and all(s["payload"]["state"] == "KA" for s in seeds)
    assert m.METHOD


def test_gp_ka_zp_tumakuru_table():
    m, p = _ka("zptumakuru")
    gp = "https://zptumakuru.karnataka.gov.in/46/gram-panchayat/en"
    assert p["pages"] == [gp]
    get = fake_get({p["url"]: "gp/ka_tumakuru_home.html", gp: "gp/ka_tumakuru_gp.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 327 and len(get.calls) == 2       # the menu link is the known page: read once
    check_records(recs, "gp_ka_zp", "rural_development")
    d = dict(recs)
    r = d["dept:gp_ka_zp:tumakuru:46:3-2"]
    assert r["area"] == "BARAKANALU" and r["block"] == "Chikkanayakanahalli" and r["phone"] == "9480877201"
    assert r["post"] == "Panchayat Development Officer (PDO)" and r["designation"] == "PDO/Secretary"
    assert r["src_pos"] == {"table": 3, "row": 2} and r["src_url"] == gp and r["level"] == "gram_panchayat"
    assert d["dept:gp_ka_zp:tumakuru:46:3-330"]["area"] == "VADAVANAGHATTA"


def test_gp_ka_zp_names_only_page_gives_nothing():
    m, p = _ka("zpkalaburagi")
    recs, files, why = m.fetch(p, fake_get({p["pages"][0]: "gp/ka_kalaburagi_gps.html"}))
    assert recs == [] and why == "no PDO table"


# ---- Maharashtra, Palghar: panchayat samiti office cards ----
def test_gp_mh_palghar_cards_and_pages():
    m = mod("gp_mh_palghar")
    seeds = json.loads((ROOT / "seeds" / "dept_gp_mh_palghar.json").read_text())
    assert seeds == m.items() and len(seeds) == 8 and m.METHOD
    p = next(s["payload"] for s in seeds if s["key"] == "gp_mh_palghar:vikramgad")
    get = fake_get({p["url"]: "gp/mh_palghar_vikramgad_p1.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 12 and len(get.calls) == 2      # page 2 is linked, not saved here: the item stops there
    check_records(recs, "gp_mh_palghar", "rural_development")
    r = dict(recs)["dept:gp_mh_palghar:vikramgad:wedhi-chari"]
    assert r["name"] == "Umesh Ladakya Guhe" and r["phone"] == "8830083988" and r["email"] == "vpzpvikramgadvedhe@gmail.com"
    assert r["post"] == "Gram Panchayat Adhikari (Panchayat Secretary)" and r["block"] == "Vikramgad" and r["district"] == "Palghar"
    assert (r["lat"], r["lon"]) == (19.79327, 72.995973) and r["src_pos"] == {"page": 1, "card": 1}
    four = m.records((DATA / "gp/mh_palghar_vikramgad_p4.html").read_text(), p["url"] + "page/4/", p, 4, set())
    assert len(four) == 6 and all(d["src_pos"]["page"] == 4 for _, d in four)


def _gz(name):
    import gzip
    return gzip.decompress((DATA / "gp_gj_tcm" / f"{name}_full.html.gz").read_bytes())


def test_gp_gj_tcm_two_lists_of_one_taluka_keep_all_rows():
    """Sailla (Surendranagar), full saved pages (bucket copies bd60fb97..., a27a8ee3...): Information-Talati has 46 TCM rows,
    information-sarpanches 12 rows. Both give ids 1-2 ...; before, the second page replaced 12 of the first page's records
    (34 of 46 left). Now: 46 + 12 = 58 records, unique ids."""
    m, p = _gj("surendranagardp")
    base = "https://surendranagardp.gujarat.gov.in/gu/taluka/Sailla/"

    class A:
        def __init__(self, b, url):
            self.content, self.url, self.status_code = b, url, 200
            self.text = b.decode("utf-8")
    pages = {p["url"]: b'<select id="ddtaluka"><option value="7||Sailla">Sailla</option></select>',
             base + "home": ('<a href="/gu/taluka/Sailla/Information-Talati">તલાટી કમ મંત્રી</a>'
                             '<a href="/gu/taluka/Sailla/information-sarpanches">સરપંચશ્રીઓ</a>').encode("utf-8"),
             base + "Information-Talati": _gz("sailla_talati"), base + "information-sarpanches": _gz("sailla_sarpanches")}

    def get(url, method="GET", data=None, headers=None):
        return A(pages[url], url) if url in pages else None
    recs, files, why = m.fetch(p, get)
    _common(recs)
    talati = [d for _, d in recs if d["src_url"].endswith("Information-Talati")]
    sar = [r for r, d in recs if d["src_url"].endswith("information-sarpanches")]
    assert why == "" and len(talati) == 46 and len(sar) == 12 and len(recs) == 58
    assert all(":information-sarpanches:" in r for r in sar)
    assert dict(recs)["dept:gp_gj_tcm:surendranagar:sailla:1-2"]["src_url"].endswith("Information-Talati")


def test_gp_gj_tcm_administrator_column():
    """Rapar (Kutch) sarpanch list, full saved page (bucket copy a43e451c...): 82 rows; 53 name a sarpanch, 29 have no sarpanch
    ("-") and name the administrator (વહીવટદાર) with the one mobile. Before, the 29 administrator rows were dropped."""
    m, p = _gj("kutchdp")
    recs = m.records(_gz("rapar_sarpanch").decode("utf-8"), "https://kutchdp.gujarat.gov.in/gu/taluka/Rapar/sarpanch-list", p, "Rapar")
    _common(recs)
    kinds = [d["kind"] for _, d in recs]
    assert len(recs) == 82 and kinds.count("sarpanch") == 53 and kinds.count("administrator") == 29
    assert all(d.get("phone") for _, d in recs)
    a = next(d for r, d in recs if r.endswith(":a"))
    assert a["name"] == "જે.વી.પ્રજાપતિ" and a["phone"] == "9879670950" and a["post_regional"] == "વહીવટદાર"


def test_gp_gj_tcm_deputy_age_and_name_phone_columns():
    """Full saved pages (2026-11-12/13). Sanand: sarpanch and deputy sarpanch columns -> 69 + 69 records (before: 69 records with
    both names in one). Detroj: a page of deputies keeps its ids (":s") with post Deputy Sarpanch. Bavala: the name column is
    "હરીફ ઉમેદવાર"; the age and "first term?" columns are not names (before: 48 records named "હા | 35"). Bardoli: TCM name and
    mobile in one cell -> name and phone apart (57 of 65 rows have a mobile)."""
    def run(name, url, taluka):
        recs = mod("gp_gj_tcm").records(_gz(name).decode("utf-8"), url, {"district": "Ahmedabad", "host": "x", "state": "GJ"}, taluka)
        _common(recs)
        return recs, dict(recs)
    recs, d = run("sanand_sarpanch_deputy", "https://ahmedabaddp.gujarat.gov.in/gu/taluka/Sanand/Sarpanch-Deputy-Superintendent-List", "Sanand")
    assert len(recs) == 138 and sum(1 for r in d if r.endswith(":d")) == 69
    assert d["dept:gp_gj_tcm:ahmedabad:sanand:1-2:s"]["name"] == "ઝુબેદાબેન હબીબભાઇ કુરેશી"
    assert d["dept:gp_gj_tcm:ahmedabad:sanand:1-2:d"]["name"] == "ઇમરાનભાઇ એહમદભાઇ વાઘેલા"
    assert d["dept:gp_gj_tcm:ahmedabad:sanand:1-2:d"]["phone"] == "8866688828"
    recs, d = run("detroj_upsarpanch", "https://ahmedabaddp.gujarat.gov.in/gu/taluka/Detroj/Upsarpanch-details", "Detroj")
    assert len(recs) == 33 and all(r.endswith(":s") and x["post"] == "Deputy Sarpanch" for r, x in recs)
    recs, d = run("bavala_sarpanch", "https://ahmedabaddp.gujarat.gov.in/gu/taluka/Bavala/Sarpanch-list", "Bavala")
    assert len(recs) == 48 and d["dept:gp_gj_tcm:ahmedabad:bavala:1-2:s"]["name"] == "પૃથ્વીપાલસિંહપ્રતાપસિંહ રાઠોડ"
    assert not any("|" in x["name"] for _, x in recs)
    recs, d = run("bardoli_tcm", "https://suratdp.gujarat.gov.in/gu/taluka/Bardoli/Tcm-list", "Bardoli")
    assert len(recs) == 65 and sum(1 for _, x in recs if x.get("phone")) == 57
    assert not any(re.search(r"[0-9]{6}", x.get("name") or "") for _, x in recs)
