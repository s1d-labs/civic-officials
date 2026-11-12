"""Offline tests of the ulb2 readers (dforms/ulb2_*.py): heads and chairpersons of the towns that had no official in DB civic
(2026-11-11). One section per reader group; each section's helpers carry the group suffix."""
from esw_common import *  # noqa: F401,F403

# ---- ulb2_br_jh ----
def test_ulb2_br_items_match_seed():
    seed = json.loads((ROOT / "seeds" / "dept_ulb2_br.json").read_text())
    assert mod("ulb2_br").items() == seed and len(seed) == 1 and seed[0]["key"].startswith("ulb2_")
    assert seed[0]["payload"]["india_only"]


def test_ulb2_br_rows():
    m = mod("ulb2_br")
    p = m.items()[0]["payload"]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "ulb2_br_udhd.txt"}))
    assert why == "" and files[0][0] == "depts/ulb2_br/udhd-contacts.txt.gz"
    check_records(recs, "ulb2_br", "town_body")
    d = dict(recs)
    ara = d["dept:ulb2_br:BR-bhojpur-ara-municipal-commissioner"]
    assert ara["name"] == "Smt Anju Kumari" and ara["phone"] == "9472677217" and ara["role"] == "head" and ara["lgd_code"] == "249659"
    # several officers in one cell: phones follow the names in order
    beg = [v for k, v in recs if v["area"] == "Begusarai" and v["role"] == "deputy"]
    assert [(v["name"], v["phone"]) for v in beg] == [("Sri Shiv Shakti Kumar", "7488529677"), ("Md. Osama Ibn Manshur", "9234057860")]
    patna = [v for k, v in recs if v["area"] == "Patna" and v["role"] == "deputy"]
    assert len(patna) == 6 and patna[0]["name"] == "Smt. Jaya" and patna[0]["phone"] == "8252252477"
    # counts do not agree: no personal phone, the row's phones kept
    pur = [v for k, v in recs if v["area"] == "Purnea"]
    assert all("phone" not in v and v["row_phones"] == "9899492016, 9900101628, 9529234541" for v in pur)
    kh = [v for k, v in recs if v["area"] == "Khagaul"]
    assert kh[0]["role"] == "head" and kh[0]["name"] == "Sri Abhinav Kumar" and kh[0]["lgd_code"] == "249649"
    assert kh[1]["post"] == "Executive Officer (Urban Administration)" and kh[1]["role"] == "staff"
    # circle officers of Patna are staff of the corporation
    az = d["dept:ulb2_br:BR-patna-patna-executive-officer-azimabad-circle"]
    assert az["role"] == "staff" and az["phone"] == "9264447415"
    # spellings tied by the LGD table; split phones joined; a row across a page break
    assert d["dept:ulb2_br:BR-aurangabad-daudnagar-executive-officer"]["phone"] == "7763004227"
    assert d["dept:ulb2_br:BR-saharsa-simari-bakhtiyarpur-executive-officer"]["phone"] == "7352595363, 7739058178"
    assert d["dept:ulb2_br:BR-saharsa-simari-bakhtiyarpur-executive-officer"]["lgd_code"] == "299164"
    assert d["dept:ulb2_br:BR-pashchim-champaran-machchhargawan-executive-officer"]["lgd_code"] == "300556"
    ak = d["dept:ulb2_br:BR-bhagalpur-akbarnagar-executive-officer-urban-administration"]
    assert ak["role"] == "head" and ak["name"] == "Sri Nishant kumar"
    assert not any(v["area"] == "Motihari" for k, v in recs)          # a row with no officer gives no record


def test_ulb2_jh_items_match_seed():
    seed = json.loads((ROOT / "seeds" / "dept_ulb2_jh.json").read_text())
    assert mod("ulb2_jh").items() == seed and len(seed) == 50
    assert all(i["key"].startswith("ulb2_jh-") and i["payload"]["india_only"] for i in seed)


def test_ulb2_jh_giridih():
    m = mod("ulb2_jh")
    p = next(i["payload"] for i in m.items() if i["key"] == "ulb2_jh-giridih-municipal-corporation")
    get = fake_get({("GET", p["url"]): "ulb2_jh_get.html", ("POST", p["url"]): "ulb2_jh_giridih.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and files[0][0] == "depts/ulb2_jh/giridih-municipal-corporation.html.gz"
    method, url, data = get.calls[1]
    assert method == "POST" and data["ctl00$ContentPlaceHolderBody$ddlULB"] == "19" and data["__VIEWSTATE"]
    check_records(recs, "ulb2_jh", "town_body")
    (rid, d), = recs
    assert rid == "dept:ulb2_jh:JH-giridih-giridih-executive-officer"
    assert d["name"] == "Vijya Yadav" and d["phone"] == "9431978557" and d["role"] == "head" and d["lgd_code"] == "250349"
    assert d["office_phone"] == "06532250279" and d["office_email"] == "giridihmunicipalcorporation@gmail.com"
    assert d["area"] == "Giridih" and d["body_type"] == "Municipal Corporation" and d["address"].startswith("J.P. Chowk")


def test_ulb2_jh_empty_officer_gives_office():
    html = (DATA / "ulb2_jh_giridih.html").read_text().replace("Vijya Yadav", "").replace("9431978557", "0")
    (rid, d), = mod("ulb2_jh").parse(html, "Giridih Municipal Corporation", "Giridih", "250349")
    assert d["post"] == "Office" and d["role"] == "staff" and d["phone"] == "06532250279"


# ---- ulb2_gj ----
M_GJ = "ulb2_gj"
SEED_GJ = json.loads((ROOT / "seeds" / f"dept_{M_GJ}.json").read_text())


def test_ulb2_gj_items_match_seed():
    assert mod(M_GJ).items() == SEED_GJ and len(SEED_GJ) == 1 and SEED_GJ[0]["key"].startswith("ulb2_")


def test_ulb2_gj_corporations():
    p = SEED_GJ[0]["payload"]
    recs, files, why = mod(M_GJ).fetch(p, fake_get({p["url"]: "ulb2_gj_corporations.html"}))
    assert why == "" and files[0][0] == f"depts/{M_GJ}/corporations.html.gz"
    check_records(recs, M_GJ, "town_body")
    d = dict(recs)
    assert len(d) == 3                                  # the first row has no <tr> and is still read
    a = d["dept:ulb2_gj:GJ-ahmedabad-ahmedabad-municipal-commissioner"]
    assert a["name"] == "Shri. Banchhanidhi Pani, IAS" and a["email"] == "mc@ahmedabadcity.gov.in" and a["lgd_code"] == "251096"
    assert a["role"] == "head" and a["website"] == "https://ahmedabadcity.gov.in/"
    m = d["dept:ulb2_gj:GJ-mahesana-mehsana-municipal-commissioner"]
    assert m["area"] == "Mehsana" and m["lgd_code"] == "251068" and m["district"] == "Mahesana" and "website" not in m
    assert m["body_type"] == "Municipal Corporation" and m["email"] == "commissioner-mmc@gujarat.gov.in"


def test_ulb2_gj_unknown_city_has_no_code():
    html = (DATA / "ulb2_gj_corporations.html").read_text().replace(">Surat<", ">Bharuch<")
    d = dict(mod(M_GJ).parse(html))
    b = next(v for v in d.values() if v["area"] == "Bharuch")
    assert "lgd_code" not in b and b["name"] == "Smt.Shalini Agrawal, IAS"


# ---- ulb2_ka ----
M_KA = "ulb2_ka"
SEED_KA = json.loads((ROOT / "seeds" / f"dept_{M_KA}.json").read_text())


def _p_KA(site):
    return next(i["payload"] for i in SEED_KA if i["payload"]["site"] == site)


def test_ulb2_ka_items_match_seed():
    assert mod(M_KA).items() == SEED_KA and len(SEED_KA) == 319
    assert all(i["key"].startswith("ulb2_") and i["payload"]["india_only"] for i in SEED_KA)
    codes = [i["payload"]["lgd_code"] for i in SEED_KA if i["payload"].get("lgd_code")]
    assert len(codes) == len(set(codes)) == 318                           # one site per body; only jalitown has no LGD body
    assert _p_KA("athanitown")["lgd_code"] == "251812" and _p_KA("kamalapura-kbgtown")["lgd_code"] == "301080"
    assert _p_KA("vijayapuracity")["lgd_code"] == "251993" and _p_KA("vijayapuratown")["lgd_code"] == "251842"
    assert _p_KA("aminagadtown")["url"] == "http://www.aminagadtown.mrc.gov.in/en"


def test_ulb2_ka_athani():
    p = _p_KA("athanitown")
    recs, files, why = mod(M_KA).fetch(p, fake_get({p["url"]: "ulb2_ka_athani.html"}))
    assert why == "" and files[0][0] == f"depts/{M_KA}/athanitown.html.gz"
    check_records(recs, M_KA, "town_body")
    d = dict(recs)
    chair, head = d["dept:ulb2_ka:KA-belagavi-athani-president"], d["dept:ulb2_ka:KA-belagavi-athani-chief-officer"]
    assert chair["name"] == "Sri.Shivaleela Sadashiv Butali" and chair["role"] == "chair" and chair["area"] == "Athani"
    assert head["name"] == "smt.Daya k Joshi" and head["role"] == "head" and head["lgd_code"] == "251812"
    assert head["body_type"] == "Town Municipal Council" and head["district"] == "Belagavi"
    assert len(recs) == 2                                                  # the Chief Minister and Minister cards are left out


def test_ulb2_ka_belagavi_city_corporation():
    p = _p_KA("belagavicity")
    recs, _, why = mod(M_KA).fetch(p, fake_get({p["url"]: "ulb2_ka_belagavi.html"}))
    d = {v["post"]: v for _, v in recs}
    assert why == "" and set(d) == {"Mayor", "Commissioner"}
    assert d["Commissioner"]["name"] == "Shri. Kartik M (Senior Scale)" and d["Commissioner"]["role"] == "head"
    assert d["Mayor"]["role"] == "chair" and d["Mayor"]["area"] == "Belagavi" and d["Mayor"]["lgd_code"] == "251824"


def test_ulb2_ka_template_card_left_out():
    p = _p_KA("huttitown")
    recs, _, why = mod(M_KA).fetch(p, fake_get({p["url"]: "ulb2_ka_hutti.html"}))
    assert recs == [] and "another body (Bogadi TP.)" in why                 # the new site still shows the template's blanks


def test_ulb2_ka_names_and_bodies():
    m = mod(M_KA)
    assert m.split_type("ALMEL TOWN PANCHAYATH") == ("ALMEL", "TOWN PANCHAYATH")
    assert m._same_body("Athani TMC", "Athani", "athanitown") and m._same_body("Belagavi City Corporation", "Belagavi", "belagavicity")
    assert not m._same_body("Bogadi TP.", "HUTTI", "huttitown")
    assert not m._name_ok("Sri.  ___________") and m._name_ok("Sri. M P Ramesh")
    html = (DATA / "ulb2_ka_athani.html").read_text().replace("Chief Officer,Athani", "Cheif Officer,")
    recs, _ = m.parse(html, "Athani Town Municipal Council", "athanitown", "u")
    assert {v["post"]: v["role"] for _, v in recs} == {"President": "chair", "Chief Officer": "head"}


# ---- ulb2_mh ----
MH, GA, DD = "ulb2_mh", "ulb2_ga", "ulb2_dd"


def seed_MH(m):
    return json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())


def test_ulb2_mh_ga_dd_items_match_seed():
    for m in (MH, GA, DD):
        assert mod(m).items() == seed_MH(m)
        assert all(i["key"].startswith("ulb2_") and i["payload"]["reader"] == m for i in seed_MH(m))
    assert all(i["payload"]["india_only"] for i in seed_MH(GA))
    assert not any(i["payload"]["india_only"] for i in seed_MH(MH) + seed_MH(DD))


def test_ulb2_mh_sec_president_rows():
    m = mod(MH)
    text = (DATA / "ulb2_mh_president.txt").read_text()
    rows = m.sec_rows(text)
    assert [r["sr"] for r in rows] == list(range(1, 10))
    assert rows[0] == {"sr": 1, "division": "AMRAVATI", "district": "AKOLA", "body": "AKOT", "reservation": "BCC W",
                       "name": "DHULE MAYA VIVEKRAO", "gender": "F", "votes": "15928"}
    assert rows[5]["body"] == "BARSHI TAKLI" and rows[5]["reservation"] == "GEN W" and rows[5]["name"] == "AKHTAR KHATUN ALIMODDIN"
    recs = m.parse_sec_text(text, "2026-04-16")
    check_records(recs, MH, "town_body")
    d = dict(recs)["dept:ulb2_mh:MH-akola-akot-president"]
    assert d["role"] == "chair" and d["post"] == "President" and d["district"] == "Akola" and d["lgd_code"] == "251310"
    assert d["last_updated"] == "2026-04-16" and d["reservation"] == "BCC W" and d["sec_sr"] == 1
    assert dict(recs)["dept:ulb2_mh:MH-akola-murtizapur-president"]["lgd_code"] == "251315"     # Murtijapur in LGD: hand tie


def test_ulb2_mh_sec_president_district_words_and_unopposed():
    m = mod(MH)
    b = m.sec_rows((DATA / "ulb2_mh_president_b.txt").read_text(), first=80)
    assert [(r["district"], r["body"]) for r in b] == [("BEED", "MAJALGAON"), ("CHH. SAMBHAJI NAGAR", "VAIJAPUR"),
                                                        ("CHH. SAMBHAJI NAGAR", "SILLOD")]
    assert b[0]["name"] == "चाऊस मिरीन शशफा बिलाल"                      # the list writes this name in Devanagari: kept as written
    c = m.sec_rows((DATA / "ulb2_mh_president_c.txt").read_text(), first=284)
    assert c[0]["body"] == "MANGALWEDH A" and c[-1]["votes"] == "unopposed" and c[-1]["body"] == "ANGAR"
    assert m.LGD[m.lgd_key("SOLAPUR", "MANGALWEDH A")] == "251580" and m.LGD[m.lgd_key("CHH. SAMBHAJI NAGAR", "SILLOD")] == "297092"


def test_ulb2_mh_fetch_not_pdf():
    p = seed_MH(MH)[0]["payload"]
    recs, files, why = mod(MH).fetch(p, fake_get({p["url"]: "ulb2_mh_nashik_mc.html"}))
    assert recs == [] and why == "not a PDF" and files[0][0] == "depts/ulb2_mh/president.pdf.gz"


def test_ulb2_mh_nashik_office_lists():
    items = {i["key"]: i["payload"] for i in seed_MH(MH)}
    p = items["ulb2_mh-nashik-mc"]
    recs, files, why = mod(MH).fetch(p, fake_get({p["url"]: "ulb2_mh_nashik_mc.html"}))
    assert why == "" and files[0][0] == "depts/ulb2_mh/municipal-council.html.gz"
    check_records(recs, MH, "town_body")
    d = dict(recs)
    assert len(d) == 4
    man = d["dept:ulb2_mh:MH-nashik-manmad-office"]
    assert man["phone"] == "02591-222328" and man["email"] == "co.manmad@gmail.com" and man["mailbox"] == "chief officer"
    assert man["role"] == "staff" and man["lgd_code"] == "251440" and man["body_type"] == "Municipal Council"
    assert "mailbox" not in d["dept:ulb2_mh:MH-nashik-nandgaon-office"]
    p = items["ulb2_mh-nashik-np"]
    recs, _, why = mod(MH).fetch(p, fake_get({p["url"]: "ulb2_mh_nashik_np.html"}))
    d = dict(recs)
    assert why == "" and d["dept:ulb2_mh:MH-nashik-kalvan-office"]["lgd_code"] == "276278"
    assert d["dept:ulb2_mh:MH-nashik-dindori-office"]["body_type"] == "Nagar Panchayat"


def test_ulb2_ga_charge_orders():
    ga = mod(GA)
    v = dict(ga.parse((DATA / "ulb2_ga_valpoi.txt").read_text(), "u"))["dept:ulb2_ga:GA-north-goa-valpoi-chief-officer"]
    assert v["name"] == "Shri Rajeskr Arlekar" and v["role"] == "head" and v["lgd_code"] == "252079"
    assert v["last_updated"] == "2026-10-21" and v["own_post"].startswith("Assistant Director of Civil Supplies, Sattari")
    p = dict(ga.parse((DATA / "ulb2_ga_pernem.txt").read_text(), "u"))["dept:ulb2_ga:GA-north-goa-pernem-chief-officer"]
    assert p["name"] == "Smt. Mecksha Omkar Manjrekar" and p["own_post"] == "BD0, Pernem" and p["last_updated"] == "2026-02-04"
    assert p["charge"] == "additional charge" and p["lgd_code"] == "252057"


def test_ulb2_dd_diu_office():
    p = seed_MH(DD)[0]["payload"]
    recs, files, why = mod(DD).fetch(p, fake_get({p["url"]: "ulb2_dd_diu.html"}))
    assert why == "" and files[0][0] == "depts/ulb2_dd/diu-municipal-council.html.gz"
    check_records(recs, DD, "town_body")
    d = dict(recs)["dept:ulb2_dd:DD-diu-diu-office"]
    assert d["phone"] == "02875-252126" and d["email"] == "dmc-diu-dd@nic.in" and d["lgd_code"] == "251271"
    assert d["last_updated"] == "2022-10-18" and d["address"].startswith("Fort Road, Diu")


# ---- ulb2_mp_cg ----
def seed_MP_CG(m):
    return json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())


def test_ulb2_cg_items_match_seed():
    s = seed_MP_CG("ulb2_cg")
    assert mod("ulb2_cg").items() == s and [i["key"] for i in s] == ["ulb2_cg-contacts", "ulb2_cg-elected"]
    assert s[0]["payload"]["india_only"] and not s[1]["payload"].get("india_only")


def test_ulb2_cg_contacts():
    p = seed_MP_CG("ulb2_cg")[0]["payload"]
    recs, files, why = mod("ulb2_cg").fetch(p, fake_get({p["url"]: "ulb2_cg_contacts.html"}))
    assert why == "" and files[0][0] == "depts/ulb2_cg/contacts.html.gz"
    check_records(recs, "ulb2_cg", "town_body")
    d = dict(recs)
    assert len(recs) == 9                                           # 5 heads + 4 engineers; state officers' tables left out
    b = d["dept:ulb2_cg:CG--bodla-chief-municipal-officer"]
    assert b["role"] == "head" and b["name"] == "श्री प्रणव प्रवेश प्रधान" and b["phone"] == "8269994337"
    assert b["email"] == "cmobodla@rediffmail.com" and b["office_phone"] == "7740253505" and b["post_regional"] == "सी. एम.ओ."
    assert b["lgd_code"] == "273466" and b["area"] == "बोड़ला" and b["area_latin"] == "Bodla" and b["district"] == "कबीरधाम"
    assert d["dept:ulb2_cg:CG--bodla-engineer"]["role"] == "staff"
    assert d["dept:ulb2_cg:CG--raipur-commissioner"]["role"] == "head"
    # the zero-width joiner after a virama is dropped, not turned into a space; the row still ties
    bs = d["dept:ulb2_cg:CG--bastar-chief-municipal-officer"]
    assert bs["area"] == "बस्तर" and bs["lgd_code"] == "248143"
    t = d["dept:ulb2_cg:CG--takhatpur-chief-municipal-officer"]  # the row names no CMO: the post with the office mailbox stays
    assert "name" not in t and t["email"] == "nptkp2013@gmail.com"
    assert d["dept:ulb2_cg:CG--shivnandanpur-chief-municipal-officer"]["lgd_code"] == "301867"


def test_ulb2_cg_elected():
    p = seed_MP_CG("ulb2_cg")[1]["payload"]
    recs, files, why = mod("ulb2_cg").fetch(p, fake_get({p["url"]: "ulb2_cg_elected.html"}))
    assert why == ""
    check_records(recs, "ulb2_cg", "town_body")
    d = dict(recs)
    m = d["dept:ulb2_cg:CG--ambikapur-mayor"]
    assert m["post"] == "Mayor" and m["role"] == "chair" and m["party"] == "भाजपा" and m["wards"] == "48" and m["lgd_code"] == "250588"
    c = d["dept:ulb2_cg:CG--bodla-chairperson"]
    assert c["post_regional"] == "अध्यक्ष" and c["role"] == "chair" and c["lgd_code"] == "273466" and c["district"] == "कबीरधाम"
    # "कुसमी" after "लखनपुर" is Kusmi of Balrampur; "कुसमी ( बे)" is Kusmi of Bemetara; "पटना" is Patna of Korea
    assert d["dept:ulb2_cg:CG--kusmi-chairperson"]["lgd_code"] == "253118"
    assert d["dept:ulb2_cg:CG--kusmi-chairperson:2"]["lgd_code"] == "301834"
    assert d["dept:ulb2_cg:CG--patna-chairperson"]["lgd_code"] == "301809"
    # a shared name (भटगांव) whose row before is not the one the table knows gets no lgd_code (sql/87 may tie it, or not)
    assert sum(1 for _, x in recs if not x.get("lgd_code")) == 1


def test_ulb2_mp_items_match_seed():
    s = seed_MP_CG("ulb2_mp")
    assert mod("ulb2_mp").items() == s and s[0]["payload"]["india_only"]


def test_ulb2_mp_directory():
    m = mod("ulb2_mp")
    recs = m.parse((DATA / "ulb2_mp_directory.txt").read_text())
    check_records(recs, "ulb2_mp", "town_body")
    d = dict(recs)
    assert len(recs) == 17                                          # the second print of the Morena rows is skipped
    b = d["dept:ulb2_mp:MP--bhopal-commissioner"]
    assert b["role"] == "head" and b["area"] == "भोपाल" and b["body_type"] == "नगर निगम" and b["lgd_code"] == "250946"
    assert b["email"] == "commbhopal@mpurban.gov.in, commissioner@bmconline.gov.in" and b["phone"] == "0755-2701222"
    s = d["dept:ulb2_mp:MP--sehore-chief-municipal-officer"]
    assert s["district"] == "सीहोर" and s["lgd_code"] == "250947" and s["post_from"] == "directory" and "name" not in s
    assert d["dept:ulb2_mp:MP--rajgarh-chief-municipal-officer"]["lgd_code"] == "250931"   # Rajgarh of Dhar, shared mailbox
    assert d["dept:ulb2_mp:MP--porsa-chief-municipal-officer"]["district"] == "मुरैना"
    assert d["dept:ulb2_mp:MP--berasia-chief-municipal-officer"]["division"] == "भोपाल संभाग"


def test_ulb2_mp_fetch(monkeypatch):
    m = mod("ulb2_mp")
    p = seed_MP_CG("ulb2_mp")[0]["payload"]
    txt = (DATA / "ulb2_mp_directory.txt").read_text()
    monkeypatch.setattr(m, "layout_pages", lambda content: (txt.split("\f"), "pdftotext"))
    get = lambda url, **k: Answer(b"%PDF-1.4 sample", url)          # noqa: E731
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 17 and files[0][0] == "depts/ulb2_mp/directory.pdf.gz"
    assert m.fetch(p, lambda url, **k: Answer(b"<html>", url))[2] == "not a pdf"


# ---- ulb2_ne ----
def seed_NE(m):
    return json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())


def test_ulb2_ne_items_match_seeds():
    for m, n in (("ulb2_as", 41), ("ulb2_mn", 1), ("ulb2_sk", 2), ("ulb2_nl", 1)):
        s = seed_NE(m)
        assert mod(m).items() == s and len(s) == n
        assert all(i["key"].startswith("ulb2_") and i["payload"]["reader"] == m for i in s)


def test_ulb2_as_same_bodies_as_ulb_as():
    base = {i["key"].split("-", 1)[1]: i["payload"] for i in mod("ulb_as").items()}
    for i in seed_NE("ulb2_as"):
        p, b = i["payload"], base[i["key"].split("-", 1)[1]]
        assert (p["url"], p["members"], p["body"], p["district"]) == (b["url"], b["members"], b["body"], b["district"])
    assert sum(1 for i in seed_NE("ulb2_as") if i["payload"].get("lgd_code")) == 40       # Fakiragram has no LGD code


def test_ulb2_as_bongaigaon():
    p = next(i["payload"] for i in seed_NE("ulb2_as") if i["key"] == "ulb2_as-bongaigaon")
    get = fake_get({p["url"]: "ulb2_as_bongaigaon_staff.html", p["members"]: "ulb2_as_bongaigaon_members.html"})
    recs, files, why = mod("ulb2_as").fetch(p, get)
    assert why == "" and len(files) == 2
    check_records(recs, "ulb2_as", "town_body")
    d = dict(recs)
    eo = d["dept:ulb2_as:AS-bongaigaon-bongaigaon-executive-officer"]
    assert eo["name"] == "Prashanti Bhattacharyya" and eo["phone"] == "9365917801" and eo["role"] == "head"
    assert eo["lgd_code"] == "249836" and eo["office_phone"] == "03664-230450" and eo["office_email"] == "municipality.bngn@gmail.com"
    ch = d["dept:ulb2_as:AS-bongaigaon-bongaigaon-chairman"]
    assert ch["name"] == "Subodh Chandra Das" and ch["role"] == "chair" and ch["ward"] == "16" and ch["lgd_code"] == "249836"
    assert not any("Abhijit Ray" == x.get("name") for x in d.values())                  # ward commissioners are not kept


def test_ulb2_mn_bishnupur():
    p = seed_NE("ulb2_mn")[0]["payload"]
    recs, files, why = mod("ulb2_mn").fetch(p, fake_get({p["url"]: "ulb2_mn_bishnupur_dlos.html"}))
    assert why == ""
    check_records(recs, "ulb2_mn", "town_body")
    d = {x["lgd_code"]: x for _, x in recs}
    assert len(d) == 7 and all(x["role"] == "head" for x in d.values())
    assert d["276506"]["name"] == d["276525"]["name"] == "Kh. Kanta Singh"              # "EO, Oinam & Kwakta": two councils
    assert d["276506"]["area"] == "Oinam" and d["276525"]["area"] == "Kwakta" and d["276525"]["post"] == "EO, Oinam & Kwakta"
    assert d["276501"]["name"] == "Samuel, MMAS" and d["276501"]["district"] == "Bishnupur"
    assert d["276501"]["last_updated"] == "2026-10-13"


def test_ulb2_sk_gangtok_and_namchi():
    s = seed_NE("ulb2_sk")
    p = s[0]["payload"]
    recs, _, why = mod("ulb2_sk").fetch(p, fake_get({p["url"]: "ulb2_sk_gangtok_officers.html"}))
    assert why == ""
    check_records(recs, "ulb2_sk", "town_body")
    d = dict(recs)
    mc = d["dept:ulb2_sk:SK-gangtok-gangtok-municipal-commissiner-gmc"]                   # one record, though two ACs list him
    assert mc["name"] == "R.B BHANDARI" and mc["phone"] == "9832014743" and mc["role"] == "head" and mc["role_from"] == "rule"
    assert mc["lgd_code"] == "249694" and mc["body_type"] == "Municipal Corporation"
    meo = d["dept:ulb2_sk:SK-gangtok-singtam-meo-singtam"]                               # a short (row-spanned) table row
    assert meo["name"] == "UJJWAL PANDEY" and meo["role"] == "head" and meo["lgd_code"] == "249695"
    assert d["dept:ulb2_sk:SK-gangtok-gangtok-deputy-commissioner-gmc"]["role"] == "deputy"
    assert len(recs) == 5 and not any("ADC" in x["post"] or "COLLECTOR" in x["post"] for x in d.values())
    p = s[1]["payload"]
    recs, _, why = mod("ulb2_sk").fetch(p, fake_get({p["url"]: "ulb2_sk_namchi_directory.html"}))
    (rid, n), = recs
    assert n["name"] == "Ms. Yogen Syanden" and n["phone"] == "257157, 9593375861" and n["lgd_code"] == "249692" and n["role"] == "head"


def test_ulb2_nl_mokokchung():
    p = seed_NE("ulb2_nl")[0]["payload"]
    recs, _, why = mod("ulb2_nl").fetch(p, fake_get({p["url"]: "ulb2_nl_mokokchung_contacts.html"}))
    (rid, d), = recs
    assert d["name"] == "Atsungba Walling" and d["phone"] == "8415059304" and d["role"] == "head" and d["lgd_code"] == "249717"


def test_ulb2_ne_no_rows_and_no_answer():
    p = seed_NE("ulb2_nl")[0]["payload"]
    assert mod("ulb2_nl").fetch(p, fake_get({}))[2] == "no answer"
    assert mod("ulb2_nl").fetch(p, fake_get({p["url"]: "ulb2_mn_bishnupur_dlos.html"}))[2] == "no rows"


# ---- ulb2_nw ----
def seed_NW(m):
    return json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())


def test_ulb2_nw_items_match_seeds():
    for m, n in (("ulb2_hp", 20), ("ulb2_hr", 4), ("ulb2_la", 2), ("ulb2_dl", 1)):
        assert mod(m).items() == seed_NW(m) and len(seed_NW(m)) == n, m
        assert all(i["key"].startswith("ulb2_") for i in seed_NW(m))
    assert all(i["payload"]["lgd_code"] for m in ("ulb2_hp", "ulb2_hr", "ulb2_la") for i in seed_NW(m))


def payload_NW(m, body):
    return next(i["payload"] for i in seed_NW(m) if i["payload"].get("body") == body)


def test_ulb2_hp_amb_site():
    p = payload_NW("ulb2_hp", "Amb")
    get = fake_get({"https://npamb.in/": "ulb2_hp_amb_officers.html", "https://npamb.in/Web/Officers": "ulb2_hp_amb_officers.html",
                    "https://npamb.in/Web/ElectedOfficers": "ulb2_hp_amb_elected.html",
                    "https://npamb.in/Web/Contact": "ulb2_hp_amb_contact.html"})
    recs, files, why = mod("ulb2_hp").fetch(p, get)
    assert why == "" and "https://npamb.in/Web/ElectedOfficers" in [c[1] for c in get.calls]
    check_records(recs, "ulb2_hp", "town_body")
    d = dict(recs)
    head = d["dept:ulb2_hp:HP-una-amb-secretary-np-amb"]
    assert head["name"] == "Raman Kumar" and head["phone"] == "9418503512" and head["role"] == "head"
    assert head["lgd_code"] == "297009" and head["area"] == "Amb" and head["body_type"] == "Nagar Panchayat"
    assert len(recs) == 6 and d["dept:ulb2_hp:HP-una-amb-clerk"]["role"] == "staff"     # the empty elected table gives nothing


def test_ulb2_hp_office_only_and_parked():
    p = payload_NW("ulb2_hp", "Hamirpur")
    recs, _, why = mod("ulb2_hp").fetch(p, fake_get({"https://mchamirpur.com/": "ulb2_hp_hamirpur_contact.html"}))
    assert why == "" and [r for r, _ in recs] == ["dept:ulb2_hp:HP-hamirpur-hamirpur-office"]
    assert recs[0][1]["email"] == "m.corphamirpur@gmail.com" and recs[0][1]["phone"] == "+91-1792-223657"
    nw = mod("_ulb2_nw")
    assert not nw.is_body_page("<title>npnarkanda.in</title>Narkanda Nagar Panchayat. This domain may be for sale!", "Narkanda")
    assert not nw.is_body_page("<p>Welcome to Shimla</p>", "Rampur")
    assert nw.is_body_page("<p>Municipal Council Joginder Nagar</p>", "Jogindarnagar|Joginder Nagar")


def test_ulb2_hr_palwal_post_mailbox():
    p = payload_NW("ulb2_hr", "Palwal")
    recs, _, why = mod("ulb2_hr").fetch(p, fake_get({"https://mcpalwal.in/": "ulb2_hr_palwal_home.html"}))
    assert why == "" and len(recs) == 1
    d = recs[0][1]
    assert d["post"] == "Executive Officer" and d["post_from"] == "email" and d["role"] == "head"
    assert d["email"] == "eo-palwal@ulbharyana.gov.in" and d["phone"] == "01275252526" and d["lgd_code"] == "248586"


def test_ulb2_la_directories():
    out = {}
    for body, f in (("Leh", "ulb2_la_leh.html"), ("Kargil", "ulb2_la_kargil.html")):
        p = payload_NW("ulb2_la", body)
        recs, files, why = mod("ulb2_la").fetch(p, fake_get({p["url"]: f}))
        assert why == "" and len(recs) == 1                      # the Police Department table is not read
        check_records(recs, "ulb2_la", "town_body")
        out[body] = recs[0][1]
    assert out["Leh"]["name"] == "Sh. Atul Singh Mankotia, JKAS" and out["Leh"]["email"] == "adm.mcleh@gmail.com"
    assert out["Kargil"]["post"] == "Executive Officer" and out["Kargil"]["phone"] == "232176, 946-9707-220"
    assert out["Kargil"]["role"] == "head" and out["Kargil"]["lgd_code"] == "248178"


def test_ulb2_dl_ndmc():
    p = seed_NW("ulb2_dl")[0]["payload"]
    recs, _, why = mod("ulb2_dl").fetch(p, fake_get({p["url"]: "ulb2_dl_ndmc.html"}))
    assert why == "" and len(recs) == 9                          # the ex-officio table is left out
    check_records(recs, "ulb2_dl", "town_body")
    roles = [d["role"] for _, d in recs]
    assert roles.count("head") == 1 and roles.count("deputy") == 1 and roles.count("member") == 7
    chair = recs[0][1]
    assert chair["name"] == "Sh. Manoj Kumar Dwivedi, IAS" and chair["email"] == "chairperson@ndmc.gov.in"
    assert chair["lgd_code"] == "276447" and chair["post"] == "Chairperson & Member"
    assert dict(recs)["dept:ulb2_dl:DL-new-delhi-new-delhi-municipal-council-secretary-d-member"]["role"] == "member"


def test_ulb2_nw_table_rows_phone_columns():
    html = ("<table><tr><th>Name</th><th>Designation</th><th>Phone</th><th>Mobile</th><th>Ward No.</th></tr>"
            "<tr><td>A B</td><td>President</td><td>01972-222222</td><td>9418000000</td><td>--</td></tr>"
            "<tr><td>C D</td><td></td><td></td><td>9418111111</td><td>3</td></tr>"
            "<tr><td>Vacant</td><td></td><td></td><td></td><td></td></tr></table>")
    rows = mod("_ulb2_nw").table_rows(mod("_esw").soup(html).table)
    assert rows[0]["phone"] == "01972-222222, 9418000000" and rows[0]["post"] == "President"
    assert rows[1]["post"] == "Ward Member" and rows[1]["ward"] == "3" and len(rows) == 2


# ---- ulb2_py ----
M_PY = "ulb2_py"
SEED_PY = json.loads((ROOT / "seeds" / f"dept_{M_PY}.json").read_text())


def test_ulb2_py_items_match_seed():
    assert mod(M_PY).items() == SEED_PY and [i["key"] for i in SEED_PY] == ["ulb2_py-yanam", "ulb2_py-oulgaret"]


def test_ulb2_py_yanam():
    p = SEED_PY[0]["payload"]
    recs, files, why = mod(M_PY).fetch(p, fake_get({p["url"]: "ulb2_py_yanam.html"}))
    assert why == "" and files[0][0] == f"depts/{M_PY}/yanam.html.gz"
    check_records(recs, M_PY, "town_body")
    assert len(recs) == 1                               # the Regional Administrator and the hospital are not body officials
    d = recs[0][1]
    assert d["area"] == "Yanam" and d["lgd_code"] == "253092" and d["name"] == "Shri. Raghavan. I" and d["role"] == "head"
    assert d["phone"] == "+91-9345429499" and d["office_phone"] == "+91-884-2951005" and d["email"] == "munci.yanam@py.gov.in"


def test_ulb2_py_oulgaret():
    p = SEED_PY[1]["payload"]
    recs, files, why = mod(M_PY).fetch(p, fake_get({p["url"]: "ulb2_py_oulgaret.html"}))
    assert why == ""
    check_records(recs, M_PY, "town_body")
    d = dict(recs)
    assert list(d) == ["dept:ulb2_py:PY-puducherry-oulgaret-commissioner"]   # Lt. Governor, CM, Secretary, Director left out
    c = d["dept:ulb2_py:PY-puducherry-oulgaret-commissioner"]
    assert c["name"] == "Thiru. M.M Vinayaraj" and c["lgd_code"] == "253093" and c["last_updated"] == "2026-11-11" and c["role"] == "head"


# ---- ulb2_rj_od ----
M_RJ_OD = "ulb2_rj"
SEED_RJ_OD = json.loads((ROOT / "seeds" / f"dept_{M_RJ_OD}.json").read_text())


def test_ulb2_rj_items_match_seed():
    assert mod(M_RJ_OD).items() == SEED_RJ_OD and len(SEED_RJ_OD) == 1
    p = SEED_RJ_OD[0]["payload"]
    assert SEED_RJ_OD[0]["key"].startswith("ulb2_") and p["reader"] == M_RJ_OD and p["india_only"] is False


def test_ulb2_rj_parse_sample():
    p = SEED_RJ_OD[0]["payload"]
    get = fake_get({("POST", p["url"]): "ulb2_rj_nodal.json"})
    recs, files, why = mod(M_RJ_OD).fetch(p, get)
    assert why == "" and files[0][0] == f"depts/{M_RJ_OD}/nodal-officers.json.gz"
    assert get.calls[0][0] == "POST" and json.loads(get.calls[0][2])["UserType"] == "DPTO,DLO"
    check_records(recs, M_RJ_OD, "town_body")
    d = dict(recs)
    # regional commissioners (Kherthal, Chomu rows) and a non-town office are left out
    assert len(recs) == 3 and not any("regional" in r["post"].lower() for r in d.values())
    bs = d["dept:ulb2_rj:RJ-chittorgarh-badi-sadri-executive-officer"]
    assert bs["role"] == "head" and bs["lgd_code"] == "248843" and bs["area"] == "BADI SADRI" and bs["area_latin"] == "Bari Sadri"
    assert bs["phone"] == "9660045191" and not bs.get("email")                  # "abcd@rajasthan.gov.in" is a filler
    assert bs["row_modified"] == "2023-01-30" and bs["body_type"] == "Nagar Palika" and not bs.get("name")
    bh = next(r for r in d.values() if r["area"] == "Bharatpur")
    assert bh["post"] == "Commissioner Nagar Nigam" and bh["role"] == "head" and bh["lgd_code"] == "248708"
    jn = next(r for r in d.values() if r["area"] == "Jodhpur North")
    assert "lgd_code" not in jn and jn["role"] == "staff"                        # merged corporation: no LGD body
    assert all("SSOID" not in r and "UserName" not in r for r in d.values())


def test_ulb2_rj_lgd_table():
    t = mod(M_RJ_OD).LGD
    assert len(t) >= 200
    assert t["NAGAR PALIKA, KHERTHAL"]["lgd_code"] == "248698" and t["NAGAR PALIKA, LAXMANGARH"]["lgd_code"] == "248740"
    assert "NAGAR PALIKA, KAITHOON" not in t and mod(M_RJ_OD).okey(" Nagar Palika,\xa0 BADI  SADRI ") == "NAGAR PALIKA, BADI SADRI"


# ---- ulb2_s3waas ----
M_S3WAAS = "ulb2_s3waas"
SEED_S3WAAS = json.loads((ROOT / "seeds" / f"dept_{M_S3WAAS}.json").read_text())


def item_S3WAAS(key):
    return next(i["payload"] for i in SEED_S3WAAS if i["key"] == key)


def test_ulb2_s3waas_seed():
    assert mod(M_S3WAAS).items() == SEED_S3WAAS and len(SEED_S3WAAS) > 400
    keys = [i["key"] for i in SEED_S3WAAS]
    assert len(keys) == len(set(keys)) and all(k.startswith("ulb2_s3waas-") for k in keys)
    assert all(i["payload"]["reader"] == M_S3WAAS and i["payload"]["state"] and i["payload"]["district"] for i in SEED_S3WAAS)
    assert not any("satara" in i["payload"]["url"] for i in SEED_S3WAAS)          # dforms/ulb_mh.py reads Satara


def test_ulb2_s3waas_kaimur_name_and_post_in_address():
    p = item_S3WAAS("ulb2_s3waas-kaimur.nic.in-municipality")
    get = fake_get({p["url"]: "ulb2_s3waas_kaimur.html", p["url"] + "page/2/": "ulb2_s3waas_kaimur_p2.html"})
    recs, files, why = mod(M_S3WAAS).fetch(p, get)
    assert why == "" and len(files) == 2 and len(get.calls) == 2
    check_records(recs, M_S3WAAS, "town_body")
    d = dict(recs)
    hata = d["dept:ulb2_s3waas:BR-kaimur-bhabua-nagar-panchayat-hata-executive-officer"]
    assert hata["name"] == "Pratiksha Prajapati" and hata["post"] == "Executive Officer" and hata["role"] == "head"
    assert hata["phone"] == "8448579813" and hata["lgd_code"] == "299203" and hata["post_from"] == "address"
    assert hata["last_updated"] == "2026-11-03" and hata["pincode"] == "821106" and hata["body_type"] == "Nagar Panchayat"
    moh = d["dept:ulb2_s3waas:BR-kaimur-bhabua-nagar-panchayat-mohania-executive-officer"]
    assert moh["name"] == "Sudhanshu Kumar" and moh["source"].endswith("/page/2/") and moh["lgd_code"] == "276648"


def test_ulb2_s3waas_wardha_person_in_heading():
    html = (DATA / "ulb2_s3waas_wardha.html").read_text()
    p = {"url": "https://wardha.gov.in/public-utility-category/x/", "state": "MH", "district": "Wardha"}
    d = {r[1]["area"]: r[1] for r in mod(M_S3WAAS).records([(p["url"], html)], p)}
    assert d["नगर परिषद वर्धा"]["post"] == "मुख्याधिकारी" and d["नगर परिषद वर्धा"]["name"] == "श्री राजेश भगत"
    arvi = d["नगर परिषद आर्वी"]
    assert arvi["name"] == "श्री किरण सुकलवाड" and arvi["post"] == "Chief Officer" and arvi["post_from"] == "title-name"
    assert arvi["role"] == "head" and arvi["email"] == "arvinagarparishad@gmail.com" and arvi["phone"] == "07157-224251"
    assert d["सिंदि रेल्वे"]["notes"] == "additional charge" and d["सिंदि रेल्वे"]["area_latin"] == "sindi relve"


def test_ulb2_s3waas_katni_hindi_labels_and_mailbox():
    html = (DATA / "ulb2_s3waas_katni.html").read_text()
    p = {"url": "https://katni.nic.in/public-utility-category/x/", "state": "MP", "district": "Katni"}
    d = {r[1]["area"]: r[1] for r in mod(M_S3WAAS).records([(p["url"], html)], p)}
    nn = d["नगर निगम कटनी"]                      # labels "फोन" / "ईमेल" folded; post from the mailbox commkatni@
    assert nn["phone"] == "7622-230120" and nn["email"] == "commkatni@mpurban.gov.in"
    assert nn["post"] == "Commissioner" and nn["post_from"] == "email" and nn["role"] == "head"
    km = d["नगर परिषद कैमोर"]
    assert km["post"] == "मुख्य नगर पालिका अधिकारी" and km["post_from"] == "address" and km["role"] == "head"


def test_ulb2_s3waas_posts_and_keys():
    m = mod(M_S3WAAS)
    assert m.post_of_text("Near Commissioner Office, Bhagalpur") is None
    assert m.post_of_text("Office of The Chief Municipal Officer, Nagar Panchayat Aamdi") == ("Chief Municipal Officer", "")
    assert m.post_of_text("Smt. Ranjeeta Kumari Nisad, Chairman") == ("Chairman", "Smt. Ranjeeta Kumari Nisad")
    assert m.post_of_text("श्रीमती अर्चना कुमारी, चेयरमैन") == ("चेयरमैन", "श्रीमती अर्चना कुमारी")
    assert m.post_of_email("eonpbakhira@gmail.com") == "Executive Officer" and m.post_of_email("itstaff_ulb_bannur@yahoo.com") is None
    assert m.role("ಪೌರ ಆಯುಕ್ತರು") == "head" and m.role("ஆணையர்") == "head" and m.role("Office") == "staff"
    assert m.name_key("नगर पंचायत रामगढ़") == "raamagarha" and m.skel("raamagarha") == m.skel("ramgarh")
    assert m.name_key("ಗಂಗಾವತಿ ನಗರಸಭೆ") == "gangaavati" and m.skel("gangaavati") == m.skel("gangawati")
    assert m.name_key("NAYAKANHATTI Town Panchayath") == "nayakanhatti" and m.name_key("Devanahalli TMC") == "devanahalli"
    seen = set()
    r = m.record_of({"title": "Sri Muktsar Sahib Municipal Council", "address": ""}, {"state": "PB"}, "u", "h", seen)[1]
    assert r["post"] == "Office" and "name" not in r                    # "Sri" in a town name is no person
    r = m.record_of({"title": "Commissioner, Pollachi", "address": ""}, {"state": "TN"}, "u", "h", seen)[1]
    assert r["area"] == "Pollachi" and r["post"] == "Commissioner" and r["post_from"] == "title"


# ---- ulb2_tg ----
M_TG = "ulb2_tg"
SEED_TG = json.loads((ROOT / "seeds" / f"dept_{M_TG}.json").read_text())


def _p_TG(key):
    return next(i["payload"] for i in SEED_TG if i["key"] == key)


def test_ulb2_tg_items_match_seed():
    assert mod(M_TG).items() == SEED_TG and len(SEED_TG) == 38
    assert all(i["key"].startswith("ulb2_") and i["payload"]["india_only"] for i in SEED_TG)
    assert all(i["payload"].get("lgd_code") or i["payload"]["kind"] == "ghmc" for i in SEED_TG)


def test_ulb2_tg_cdma_chair_and_staff():
    p = _p_TG("ulb2_tg-jangaon-chairman-details")
    recs, files, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_cdma_chair.html"}))
    assert why == "" and files[0][0] == f"depts/{M_TG}/jangaon-chairman-details.html.gz"
    check_records(recs, M_TG, "town_body")
    d = dict(recs)
    c = d["dept:ulb2_tg:TG-jangoan-jangaon-chairman"]
    assert c["name"] == "SmtKadakanchiBalamani" and c["phone"] == "9100173333" and c["role"] == "chair" and c["lgd_code"] == "251690"
    assert d["dept:ulb2_tg:TG-jangoan-jangaon-vice-chairman"]["role"] == "deputy"
    p = _p_TG("ulb2_tg-jangaon-staff-directory")
    recs, _, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_cdma_staff.html"}))
    h = dict(recs)["dept:ulb2_tg:TG-jangoan-jangaon-commissioner"]
    assert h["name"] == "Ch. Rajashekar" and h["phone"] == "9703020342" and h["role"] == "head" and len(recs) == 4


def test_ulb2_tg_cdma_office_contact():
    p = dict(_p_TG("ulb2_tg-sircilla-office-contact"))
    recs = mod(M_TG).parse_cdma((DATA / "ulb2_tg_cdma_office.html").read_text(), p)
    assert len(recs) == 1
    d = recs[0][1]
    assert d["post"] == "Manager" and d["role"] == "staff" and d["office_phone"] == "6300487155"
    assert d["office_email"] == "alairmunicipality@gmail.com" and d["address"].startswith("Beside ROB Bridge")


def test_ulb2_tg_new_platform():
    p = _p_TG("ulb2_tg-asifabad")
    base = p["url"] + "asifabad/"
    recs, files, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_new_home.html", base + "chairperson": "ulb2_tg_new_chair.html",
                                                 base + "contact": "ulb2_tg_new_contact.html"}))
    assert why == "" and len(files) == 2
    check_records(recs, M_TG, "town_body")
    d = dict(recs)
    c = d["dept:ulb2_tg:TG-kumuram-bheem-asifabad-asifabad-chairperson"]
    assert c["name"] == "Akash Mengre" and c["phone"] == "9949227151" and c["role"] == "chair" and c["lgd_code"] == "301596"
    assert c["office_email"] == "mc.asifabad2024@gmail.com" and c["office_phone"] == "9550034564"
    v = d["dept:ulb2_tg:TG-kumuram-bheem-asifabad-asifabad-vice-chairperson"]
    assert v["name"] == "MD Ahmed" and v["role"] == "deputy"


def test_ulb2_tg_new_platform_no_slug():
    p = _p_TG("ulb2_tg-mulugu")
    recs, files, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_cdma_chair.html"}))
    assert recs == [] and why == "no town slug" and len(files) == 1


def test_ulb2_tg_gwmc_commissioner():
    p = _p_TG("ulb2_tg-warangal-commissioner")
    recs, _, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_gwmc_comm.html"}))
    assert why == "" and len(recs) == 1
    d = recs[0][1]
    assert d["name"] == "Sri T VENKANNA" and d["role"] == "head" and d["phone"] == "9701999645" and d["email"] == "ourwmc@gmail.com"
    assert d["lgd_code"] == "251691" and d["area"] == "Warangal"


def test_ulb2_tg_ghmc_circles():
    p = _p_TG("ulb2_tg-ghmc-circles")
    recs, _, why = mod(M_TG).fetch(p, fake_get({p["url"]: "ulb2_tg_ghmc.html"}))
    assert why == ""
    check_records(recs, M_TG, "town_body")
    d = {v["area"]: v for _, v in recs}
    assert set(d) == {"Badangpet", "Shamshabad", "Jalapally", "Adibatla"}                 # Charminar is not a gap body
    assert d["Jalapally"]["name"] == "B.Venkat Ram" and d["Jalapally"]["lgd_code"] == "276409" and d["Jalapally"]["ghmc_circle"] == "Jalpally"
    assert d["Badangpet"]["email"] == "dccircle16badangpet@gmail.com" and d["Badangpet"]["merged_into"] == "GHMC"
    assert all(v["role"] == "deputy" for v in d.values())


# ---- ulb2_up ----
M_UP = "ulb2_up"
SEED_UP = json.loads((ROOT / "seeds" / f"dept_{M_UP}.json").read_text())


def test_ulb2_up_items_match_seed():
    assert mod(M_UP).items() == SEED_UP and SEED_UP[0]["key"] == "ulb2_up-yeida"


def test_ulb2_up_yeida():
    p = SEED_UP[0]["payload"]
    recs, files, why = mod(M_UP).fetch(p, fake_get({p["url"]: "ulb2_up_yeida.html"}))
    assert why == "" and files[0][0] == f"depts/{M_UP}/yeida.html.gz"
    check_records(recs, M_UP, "town_body")
    d = dict(recs)["dept:ulb2_up:UP-gautam-buddha-nagar-yeida-chief-executive-officer"]
    assert d["name"] == "Shri Rakesh Kumar Singh (IAS)" and d["role"] == "head" and d["lgd_code"] == "274822"
    assert d["office_phone"] == "0120-2395152, 0120-2395157" and d["body_type"] == "Notified Area Council"


def test_ulb2_hp_nerwa_misspelt_header():
    """Nerwa's employee table heads its post column "Desiganation" (2026-11-12): the rows are read."""
    p = payload_NW("ulb2_hp", "Nerwa")
    get = fake_get({"https://npnerwa.com/": "ulb2_hp_nerwa_start.html",
                    "https://www.npnerwa.com/Web/employee": "ulb2_hp_nerwa_employee.html"})
    recs, files, why = mod("ulb2_hp").fetch(p, get)
    assert why == ""
    check_records(recs, "ulb2_hp", "town_body")
    by = {d["post"]: d for _, d in recs}
    assert len(recs) == 3 and by["Secretary"]["name"] == "Mr. Ram Karan" and by["JE"]["phone"] == "9805162675"
    assert by["Secretary"]["phone"] == "9418681728" and by["Secretary"]["lgd_code"] == "297014"
    assert by["Secretary"]["src_url"] == "https://www.npnerwa.com/Web/employee" and by["Secretary"]["src_pos"]
