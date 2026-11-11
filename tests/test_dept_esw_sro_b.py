from esw_common import *  # noqa: F401,F403

# ---- Sub-registrars: Tamil Nadu, Gujarat, Maharashtra, Uttar Pradesh (dforms/sro_tn, sro_gj, sro_mh, sro_up)

def _seed(module):
    return json.loads((ROOT / "seeds" / f"dept_{module}.json").read_text())


def test_sro_tn():
    """GET portal (csrf), POST English, POST the list, GET page 2 from the pager link. sro_tn_list_p2.html is a stand-in page made
    of two rows of the real page 1."""
    p = _seed("sro_tn")[0]["payload"]
    get = fake_get({
        "https://tnreginet.gov.in/portal/": "sro_tn_portal.html",
        (lambda u, m, d: m == "POST" and "actionVal=homePage" in u): "sro_tn_portal.html",
        (lambda u, m, d: m == "POST" and "actionVal=sroList" in u and "_csrf=bd81dca9" in u): "sro_tn_list_p1.html",
        (lambda u, m, d: m == "GET" and u.endswith("d-4033352-p=2")): "sro_tn_list_p2.html",
    })
    recs, files, why = mod("sro_tn").fetch(p, get)
    check_records(recs, "sro_tn", "registration")
    d = dict(recs)
    assert len(d) == 5 and why == "only 5 of 595 offices"           # the other 58 pages are not in the fake
    a = d["dept:sro_tn:TN-SRO-aathur-dindugal"]
    assert a["area"] == "Aathur" and a["district"] == "Dindugul" and a["phone"] == "0451 -2556987"
    assert a["email"] == "sroattur_dindugal@tnreginet.net" and a["level"] == "subdistrict" and a["state"] == "TN"
    assert d["dept:sro_tn:TN-SRO-acchirapakkam"]["phone"] == "044-27522833"            # from page 2
    assert [f[0] for f in files] == ["depts/sro_tn/sro-list-p1.html.gz", "depts/sro_tn/sro-list-p2.html.gz"]
    sent = [c for c in get.calls if c[0] == "POST" and "homePage" in c[1]]
    assert sent and "UserLocaleID=en_US" in sent[0][1] and sent[0][2]["_csrf"] == "bd81dca9-6e21-44b5-93a1-98c524cc4502"


def test_sro_tn_no_token():
    get = fake_get({"https://tnreginet.gov.in/portal/": "sro_tn_list_p2.html"})
    recs, files, why = mod("sro_tn").fetch(_seed("sro_tn")[0]["payload"], get)
    assert recs == [] and why == "no csrf token on the portal page"


def test_sro_gj():
    p = _seed("sro_gj")[0]["payload"]
    assert p["india_only"] is True
    recs, files, why = mod("sro_gj").fetch(p, fake_get({p["url"]: "sro_gj_offices.xlsx"}))
    assert why == "" and files[0][0] == "depts/sro_gj/gARVI_SRO_Office_list.xlsx.gz"
    assert len(recs) == 2
    godhra, ghoghamba = (d for _, d in recs)
    assert godhra["area"] == "ગોધરા" and godhra["district"] == "Panchmahal" and godhra["address"] == "mamlatdar office compund Godhra"
    assert godhra["villages"] == [{"en": "ACHALA", "gu": "અછાલા"}, {"en": "AGARVADA", "gu": "આગરવાડા"}]
    assert ghoghamba["village_count"] == 3 and ghoghamba["office_id"].startswith("GJ-SRO-panchmahal-")
    assert all(d["type"] == "dept_office" and d["dept"] == "registration" and d["level"] == "subdistrict" for _, d in recs)


def test_sro_gj_names():
    m = mod("sro_gj")
    assert m.short("સ.ર.કચેરી \nઅંકલેશ્વર") == "અંકલેશ્વર" and m.short("S.R.O - KALYANPUR") == "KALYANPUR"
    assert m.short("સબ-રજીસ્ટ્રાર અમદાવાદ-14 (દશક્રોઇ)") == "અમદાવાદ-14 (દશક્રોઇ)"
    assert m.district("સુ.નગર") == "Surendranagar" and m.district("DEV BHUMI-DWARKA") == "Devbhumi Dwarka"


def _pdf_text(monkeypatch, module, name):
    """The runner reads PDFs with pypdf (_esw.pdf_pages); the test gives it the layout text pypdf made of the real file."""
    pages = (DATA / name).read_text(encoding="utf-8").split("\f")
    monkeypatch.setattr(mod(module)._esw, "pdf_pages", lambda content: pages if content.startswith(b"%PDF") else [])
    return pages


def _pdf_get(url):
    return lambda u, method="GET", data=None, headers=None: Answer(b"%PDF-1.4 stand-in", u) if u == url else None


def test_sro_mh(monkeypatch):
    items = _seed("sro_mh")
    assert len(items) == 9 and all(i["payload"]["india_only"] for i in items)
    p = next(i["payload"] for i in items if i["payload"]["division"] == "pune")
    assert p["url"] == "https://igrmaharashtra.gov.in/pdf/documents/offices/Pune%20Div.pdf"
    _pdf_text(monkeypatch, "sro_mh", "sro_mh_pune_div.txt")
    recs, files, why = mod("sro_mh").fetch(p, _pdf_get(p["url"]))
    check_records(recs, "sro_mh", "registration")
    d = {v["sr_no"]: v for _, v in recs}
    assert sorted(d) == [1, 2, 3, 62, 63, 64, 65, 66, 67, 115, 116, 117]
    h = d[3]
    assert h["area"] == "Haveli 1" and h["district"] == "Pune City" and h["phone"] == "020-24487353"
    assert h["email"] == "jsr.haveli1@igrmaharashtra.gov.in" and h["pincode"] == "411002" and h["post"] == "Joint Sub Registrar"
    assert h["lat"] == 18.522778 and h["lon"] == 73.24
    assert d[1]["post"] == "DIG of Registration" and d[1]["level"] == "division" and d[1]["email"] == "dig.pune@igrmaharashtra.gov.in"
    assert d[2]["level"] == "district" and d[2]["pincode"] == "411001" and d[2]["email"] == "jdr.punecity@igrmaharashtra.gov.in"
    assert d[64]["area"] == "Mahabaleshwar" and d[65]["area"] == "Khandala"          # a name broken over two rows' lines
    assert "phone" not in d[62]                                                        # "2.17E+09" in the sheet: dropped
    assert d[116]["area"] == "Mangalwedha" and d[116]["district"] == "Solapur" and d[116]["lon"] == 75.45393


def test_sro_mh_coord():
    c = mod("sro_mh").coord
    assert c("18.52258") == 18.52258 and c("18°31'22\"") == round(18 + 31 / 60 + 22 / 3600, 6) and c("NA") is None


def test_sro_up_legacy():
    fix = mod("sro_up").legacy
    assert fix("महाǓनरȣ¢क") == "महानिरीक्षक" and fix("काया[लय") == "कार्यालय" and fix("Įीवाèतव") == "श्रीवास्तव"
    assert fix("Ǒɮतीय") == "द्वितीय" and fix("ǐरजवȶशन") == "रिजर्वेशन" and fix("मुजÝफरनगर") == "मुजफ्फरनगर"


def test_sro_up(monkeypatch):
    p = _seed("sro_up")[0]["payload"]
    assert not p.get("india_only")
    _pdf_text(monkeypatch, "sro_up", "sro_up_officers.txt")
    recs, files, why = mod("sro_up").fetch(p, _pdf_get(p["url"]))
    assert why == "" and files[0][0] == "depts/sro_up/officers_Name_No.pdf.gz"
    check_records(recs, "sro_up", "registration")
    d = dict(recs)
    s1 = d["dept:sro_up:UP-SRO-1"]
    assert s1["area"].startswith("अली") and s1["area"].endswith("(कोल) सदर - 1")       # the file writes ढ़ as one code point
    assert s1["name"] == "अरुण प्रकाश" and s1["phone"] == "9235930102"
    assert s1["address"] == "उपनिबन्धक प्रथम कोल, अलीगढ (तहसील परिसर कोल अलीगढ)" and s1["aig"] == "बृजेश कुमार"
    assert d["dept:sro_up:UP-SRO-5"]["in_charge"] is True and "name" not in d["dept:sro_up:UP-SRO-5"]
    assert d["dept:sro_up:UP-SRO-8"]["district"] == "एटा" and d["dept:sro_up:UP-SRO-8"]["name"] == "धीरज सिंह"
    assert d["dept:sro_up:UP-DIG-9235930501"]["name"] == "पुष्पेन्द्र कुमार" and d["dept:sro_up:UP-DIG-9235930501"]["level"] == "division"
    assert d["dept:sro_up:UP-AIG-9235930522"]["area"] == "एटा"
    assert len([1 for k in d if k.startswith("dept:sro_up:UP-SRO-")]) == 9
