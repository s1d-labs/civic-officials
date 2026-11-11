"""Offline tests of the councillor contact readers (cforms/cp_*.py) on small saved samples in tests/data/cp/."""
import json
from pathlib import Path

from cforms import cp_common as cp
from cforms import cp_as, cp_br, cp_gj, cp_hr, cp_tg, cp_tn

DATA = Path(__file__).parent / "data" / "cp"
SEEDS = Path(__file__).parent.parent / "seeds"


def read(name):
    return (DATA / name).read_text(encoding="utf-8")


class Resp:
    def __init__(self, text):
        self.text = text
        self.content = text.encode()


def getter(pages):
    """A get() that answers from saved pages by url (None for any other url), and remembers the urls asked."""
    asked = []

    def get(url, method="GET", data=None, headers=None):
        asked.append(url)
        return Resp(pages[url]) if url in pages else None
    get.asked = asked
    return get


# ---- shared helpers

def test_phones():
    assert cp.phones("9398256470") == "9398256470"
    assert cp.phones("+91 98155 17018") == "9815517018"
    assert cp.phones("0278-2424801") == "02782424801"
    assert cp.phones("98765 43210 / 0294-2410323") == "9876543210, 02942410323"
    assert cp.phones("00 00 00 00") is None and cp.phones(". .. .") is None and cp.phones("9999999999") is None
    assert cp.phones("२४१०३२३") is None                         # too short: a landline without its STD code


def test_ward_no_and_emails():
    assert cp.ward_no("1ST WARD / Mallaipally") == "1"
    assert cp.ward_no("Div.NO.4") == "4" and cp.ward_no("Ward No. 01") == "1" and cp.ward_no("वार्ड १२") == "12"
    assert cp.ward_no("") is None
    assert cp.emails("Mail: Abc.Def@Gmail.com, x@y.in.") == "abc.def@gmail.com, x@y.in"


def test_keyed_repeats():
    recs = [{"ward_no": "3"}, {"ward_no": "3"}, {}]
    assert [k for k, _ in cp.keyed("TG", "x", recs)] == ["cp:TG:x:3", "cp:TG:x:3-2", "cp:TG:x:sl-3"]


# ---- Telangana: municipality sites, /pages/council-page and the older /<code>/council page

TG = {"kind": "form-cp_tg", "state": "TG", "url": "https://adilabadmunicipality.telangana.gov.in/pages/council-page",
      "body": "Adilabad", "lgd_code": "251651", "slug": "adilabad"}


def test_tg_council_page():
    get = getter({TG["url"]: read("cp_tg_adilabad.html")})
    recs, files, why = cp_tg.fetch(TG, get)
    assert why == "" and len(recs) == 6 and len(files) == 1
    rid, d = recs[0]
    assert rid == "cp:TG:adilabad:1" and d["type"] == "councillor_contact"
    assert d["name"] == "MEERABAI KOTEKAR" and d["phone"] == "9398256470" and d["ward_no"] == "1"
    assert d["record_for"] == "councillor:TG:adilabad:1" and d["body"] == "Adilabad" and d["lgd_code"] == "251651"
    assert d["source"] == "adilabadmunicipality.telangana.gov.in"


def test_tg_ward_labels():
    p = {**TG, "url": "https://dubbakamunicipality.telangana.gov.in/pages/council-page", "body": "Dubbaka", "slug": "dubbaka"}
    recs = dict(cp_tg.fetch(p, getter({p["url"]: read("cp_tg_dubbaka.html")}))[0])
    d = recs["cp:TG:dubbaka:1"]
    assert d["ward_label"] == "1ST WARD / Mallaipally" and d["phone"] == "8008487466"
    # member rows with no ward and no phone give no records
    p = {**TG, "url": "https://maripedamunicipality.telangana.gov.in/pages/council-page", "body": "Maripeda", "slug": "maripeda"}
    recs, files, why = cp_tg.fetch(p, getter({p["url"]: read("cp_tg_maripeda.html")}))
    assert recs == [] and why == "no phones listed"


def test_tg_older_page_and_empty():
    older = "https://adilabadmunicipality.telangana.gov.in/001/council"
    empty = read("cp_tg_atchampet_empty.html").replace("atchampetmunicipality", "adilabadmunicipality").replace(
        "//pages/council-page", "/001/council")
    get = getter({TG["url"]: empty, older: read("cp_tg_adilabad_001.html")})
    recs, files, why = cp_tg.fetch(TG, get)
    assert get.asked == [TG["url"], older] and len(files) == 2
    d = dict(recs)["cp:TG:adilabad:2"]
    assert d["name"] == "SHAIK NAHIMATULLAH" and d["phone"] == "7013638787" and d["url"] == older
    p = {**TG, "url": "https://atchampetmunicipality.telangana.gov.in/pages/council-page"}
    recs, files, why = cp_tg.fetch(p, getter({p["url"]: read("cp_tg_atchampet_empty.html")}))
    assert recs == [] and why == "council page lists no members"
    assert cp_tg.fetch({**p, "guessed": True}, getter({}))[2] == "no answer (guessed host)"


def test_tg_seeds():
    items = json.loads((SEEDS / "councillors_cp_tg.json").read_text())
    assert len(items) == len({i["key"] for i in items}) and all(i["key"].startswith("cp-tg-") for i in items)
    assert all(i["payload"]["kind"] == "form-cp_tg" and i["payload"]["url"].endswith("/pages/council-page") for i in items)
    adi = next(i["payload"] for i in items if i["payload"]["body"] == "Adilabad")
    assert adi["slug"] == "adilabad" and adi["url"].startswith("https://adilabadmunicipality.telangana.gov.in/")


# ---- Punjab: Bathinda's own councillor table (generic table reader)

def test_pb_bathinda():
    from cforms import cp_pb
    p = json.loads((SEEDS / "councillors_cp_pb.json").read_text())[0]["payload"]
    recs, files, why = cp_pb.fetch(p, getter({p["url"]: read("cp_pb_bathinda.html")}))
    recs = dict(recs)
    assert why == "" and len(recs) == 7
    d = recs["cp:PB:bathinda:1"]
    assert d["name"] == "Amandeep Kaur" and d["phone"] == "9855584085" and d["address"] == "#14842 St No 10 Goniana Road"
    assert d["position"] == "Councillor" and d["record_for"] == "councillor:PB:bathinda:1" and d["lgd_code"] == "248367"
    assert recs["cp:PB:bathinda:50"]["name"] == "Sukhdev Singh"


# ---- Odisha: Jharsuguda's member cards

def test_od_jharsuguda_cards():
    from cforms import cp_od
    p = json.loads((SEEDS / "councillors_cp_od.json").read_text())[0]["payload"]
    recs, files, why = cp_od.fetch(p, getter({p["url"]: read("cp_od_jharsuguda.html")}))
    recs = dict(recs)
    assert why == "" and len(recs) == 4
    d = recs["cp:OD:jharsuguda-municipality:2"]
    assert d["name"] == "Benugopal Panigrahi" and d["position"] == "Vice-Chairperson" and d["phone"] == "9439533286"
    assert d["ward_name"] == "Jharsuguda" and d["record_for"] == "councillor:OD:jharsuguda-municipality:2"
    assert recs["cp:OD:jharsuguda-municipality:1"]["name"] == "Geetanjali Panda"


# ---- Assam: <town>.assamurban.in/members

AS_P = {"kind": "form-cp_as", "state": "AS", "url": "https://tezpur.assamurban.in/members", "body": "Tezpur Municipal Board",
        "lgd_code": "249877", "record_slug": "tezpur-municipal-board"}


def test_as_cards():
    recs = dict(cp_as.keyed("AS", AS_P["record_slug"], cp_as.parse(read("cp_as_tezpur.html"), AS_P)))
    w2 = recs["cp:AS:tezpur-municipal-board:2"]
    assert w2["name"] == "Dr. Joysankar Hazarika" and w2["phone"] == "9435183772" and w2["position"] == "Ward Commissioner"
    assert w2["record_for"] == "councillor:AS:tezpur-municipal-board:2" and w2["type"] == "councillor_contact"
    assert w2["body"] == "Tezpur Municipal Board" and w2["lgd_code"] == "249877" and w2["source"] == "tezpur.assamurban.in"
    # a bare number under the phone is the ward (Sangita Ghosh Bose, ward 12)
    assert recs["cp:AS:tezpur-municipal-board:12"]["phone"] == "6001147148"
    # the chairman's card has no ward: kept without one, for the name match
    chair = recs["cp:AS:tezpur-municipal-board:sl-1"]
    assert chair["position"] == "Chairman" and "ward_no" not in chair and "record_for" not in chair
    # "Sher Alam (Expired)" carries the chairman's office phone: no record for ward 1
    assert "cp:AS:tezpur-municipal-board:1" not in recs
    assert len(recs) == 18


def test_as_fetch_and_seeds():
    class R:
        text = read("cp_as_tezpur.html")
        content = text.encode()
    recs, files, why = cp_as.fetch(AS_P, lambda url, **kw: R())
    assert why == "" and len(recs) == 18 and files[0][0] == "councillors/AS/cp-tezpur.assamurban.in.html.gz"
    assert cp_as.fetch(AS_P, lambda url, **kw: None) == ([], [], "no answer")
    items = json.loads((SEEDS / "councillors_cp_as.json").read_text())
    assert all(i["key"].startswith("cp-as-") and i["payload"]["kind"] == "form-cp_as" for i in items)
    assert len({i["key"] for i in items}) == len(items) >= 80
    assert all(i["payload"]["url"].endswith(".assamurban.in/members") and i["payload"]["record_slug"] for i in items)


# ---- Tamil Nadu: www.tnurbantree.tn.gov.in/<site>/ councillor pages

def tn_p(site, body="X"):
    return {"kind": "form-cp_tn", "state": "TN", "url": cp_tn.search_url(site), "site": site, "body": body, "lgd_code": "1",
            "record_prefix": f"councillor:TN:mun-x:{body}"}


def test_tn_tables():
    avadi = cp_tn.parse(read("cp_tn_avadi.html"), tn_p("avadi", "ஆவடி"), "u")
    assert [r["ward_no"] for r in avadi] == ["1", "2", "3", "4"]
    a1 = avadi[0]
    assert a1["name"] == "Prakash A" and a1["phone"] == "9840664495" and "Avadi IAF" in a1["address"]
    assert a1["record_for"] == "councillor:TN:mun-x:ஆவடி:1" and a1["body"] == "ஆவடி"
    dh = cp_tn.parse(read("cp_tn_dharapuram.html"), tn_p("dharapuram"), "u")
    assert dh[1]["name"] == "Pappukanan" and dh[1]["phone"] == "9843284567"        # "(Chairman)" and "Thiru." dropped
    kk = cp_tn.parse(read("cp_tn_kallakurichi.html"), tn_p("kallakurichi"), "u")
    assert kk[0]["name"] == "A.K.Ramesh" and kk[0]["ward_no"] == "1"               # "S/o Kupusamy" dropped
    arani = cp_tn.parse(read("cp_tn_arani.html"), tn_p("arani"), "u")           # address only, no phone column
    assert arani[0]["ward_no"] == "1" and "phone" not in arani[0] and arani[0]["address"].startswith("57, Pillaiyar")


def test_tn_search_answer():
    table = read("cp_tn_dharapuram.html")
    pages = json.loads(read("cp_tn_vellore_search.json"))
    (link, recs), pdfs = cp_tn.best_page(pages, tn_p("vellore"))
    assert recs == [] and pdfs[0].endswith("COUNCILLORS-LIST-WITH-PHOTO.pdf")
    pages.append({"link": "https://www.tnurbantree.tn.gov.in/x/municipal-councillors/", "title": {"rendered": "Councillors"},
                  "content": {"rendered": table}})
    (link, recs), _ = cp_tn.best_page(pages, tn_p("x"))
    assert link.endswith("/municipal-councillors/") and len(recs) == 3

    class R:
        def __init__(self, body):
            self.text, self.content = body, body.encode()
    answers = {cp_tn.search_url("x"): R(json.dumps(pages))}
    recs, files, why = cp_tn.fetch(tn_p("x"), lambda url, **kw: answers.get(url))
    assert why == "" and [k for k, _ in recs][:2] == ["cp:TN:x:1", "cp:TN:x:2"] and files[0][0] == "councillors/TN/cp-x.json.gz"


def test_tn_seeds():
    items = json.loads((SEEDS / "councillors_cp_tn.json").read_text())
    assert all(i["key"].startswith("cp-tn-") and i["payload"]["kind"] == "form-cp_tn" for i in items)
    assert len({i["key"] for i in items}) == len(items) >= 40
    assert all("wp-json" in i["payload"]["url"] and i["payload"]["record_prefix"].startswith("councillor:TN:") for i in items)


# ---- Gujarat: Bhavnagar, Surat, Rajkot, Vadodara (cforms/cp_gj.py)

def test_gj_bhavnagar_pages():
    pages = {1: read("cp_gj_bmc_p1.html"), 2: read("cp_gj_bmc_p5.html"), 3: read("cp_gj_bmc_p5.html")}

    def get(url, method="GET", data=None, headers=None):
        return Resp(pages.get(int(url.rsplit("=", 1)[1]), "<html></html>"))
    p = json.loads((SEEDS / "councillors_cp_gj.json").read_text())[0]["payload"]
    recs, files, why = cp_gj.fetch(p, get)
    d = dict(recs)
    assert why == "" and len(recs) == 16 and len(files) == 2          # page 3 repeats page 2: the loop stops
    r = d["cp:GJ:bhavnagar-municipal-corporation:1-1"]
    assert r["name"] == "Niralben Manishbhai Siddhpura" and r["phone"] == "9426590643" and r["lgd_code"] == "251165"
    assert r["type"] == "councillor_contact" and r["address"].startswith("Gayatri Villa")


def test_gj_surat_chain():
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, url.rsplit("/", 1)[1]))
        if url.endswith("Corp_list"):
            return Resp(read("cp_gj_smc_list.html"))
        if url.endswith("Navigate"):
            assert data["target"] == "CorpDetail" and data["__RequestVerificationToken"]
            return Resp(read("cp_gj_smc_nav.html"))
        return Resp(read("cp_gj_smc_detail.html"))
    p = json.loads((SEEDS / "councillors_cp_gj.json").read_text())[1]["payload"]
    recs, files, why = cp_gj.fetch(p, get)
    assert calls[:3] == [("GET", "Corp_list"), ("POST", "Navigate"), ("POST", "CorpDetail")]
    r = dict(recs)["cp:GJ:surat-municipal-corporation:1-1"]
    assert r["name"] == "NAYNABEN SURESHBHAI DOBARIYA" and r["phone"] == "8306670003" and r["ward_no"] == "1"
    assert r["address"] == "L-404, Radhika Residency, Tadwadi , Variav , Surat"


def test_gj_rajkot_cards():
    p = json.loads((SEEDS / "councillors_cp_gj.json").read_text())[2]["payload"]
    recs, files, why = cp_gj.fetch(p, lambda url, **k: Resp(read("cp_gj_rmc.html")))
    d = dict(recs)
    assert len(recs) == 5
    r = d["cp:GJ:rajkot-municipal-corporation:1-1"]
    assert r["name"] == "ભાનુબેન મનોહરભાઇ બાબરીયા" and r["phone"] == "9904343321" and "અનામિકા સોસાયટી" in r["address"]
    assert d["cp:GJ:rajkot-municipal-corporation:1-3"]["name"] == "અલ્પેશભાઇ મનસુખભાઇ મોરજરીયા"     # titles "શ્રી ર્ડો." dropped
    assert d["cp:GJ:rajkot-municipal-corporation:2-1"]["ward_no"] == "2"


def test_gj_vadodara_pdf_entries():
    text = read("cp_gj_vmc_p1_layout.txt")          # pypdf layout text of page 1 (entries 1-4), saved from the 2026 list
    e = cp_gj.vmc_entries(text)
    assert [x[:2] for x in e] == [("1", "1"), ("2", "1"), ("3", "1"), ("4", "1")]
    assert e[0][3] == "9016446621, 8460505675"            # the second mobile sits on the address line
    assert e[1][3] == "9925003720" and e[3][3] == "9033222278"
    assert e[0][4] and "9016446621" not in e[0][4]


# ---- Bihar: Patna (cforms/cp_br.py)

def test_br_patna():
    p = json.loads((SEEDS / "councillors_cp_br.json").read_text())[0]["payload"]
    html = read("cp_br_patna.html")
    recs, files, why = cp_br.fetch(p, lambda url, **k: Resp(html))
    d = dict(recs)
    assert why == "" and len(recs) == 5
    r = d["cp:BR:nagar-nigam-patna:2"]
    assert r["name"] == "Babita Kumari" and r["phone"] == "9471422265, 9931000117"
    assert r["record_for"] == "councillor:BR:nagar-nigam-patna:2" and r["body"] == "नगर निगम, पटना" and r["lgd_code"] == "249650"
    assert d["cp:BR:nagar-nigam-patna:16"]["name"] == "Jay Prakash Singh"       # "Sri" dropped


# ---- Haryana: Panchkula, Sirsa, Yamunanagar, Panipat (cforms/cp_hr.py)

HR_SEEDS = {s["key"]: s["payload"] for s in json.loads((SEEDS / "councillors_cp_hr.json").read_text())}


def hr_run(key, sample):
    html = read(sample)
    recs, files, why = cp_hr.fetch(HR_SEEDS[key], lambda url, **k: Resp(html))
    assert why == "" and files
    return dict(recs)


def test_hr_panchkula_mayor_relation_two_phones():
    d = hr_run("cp-hr-panchkula", "cp_hr_panchkula.html")
    mayor = d["cp:HR:pankchkula-municipal-corporation:chair"]
    assert mayor["name"] == "Sham Lal" and mayor["position"] == "Mayor" and mayor["phone"] == "9216505596"
    assert mayor["record_for"] == "councillor:HR:pankchkula-municipal-corporation:chair"
    w1 = d["cp:HR:pankchkula-municipal-corporation:1"]
    assert w1["name"] == "Paramjeet Kaur" and w1["relation"].startswith("W/o") and w1["phone"] == "9988755533, 7889267809"
    assert d["cp:HR:pankchkula-municipal-corporation:7"]["name"] == "Jyoti Parsad"          # "S/k Sh. Krishan Lal" dropped


def test_hr_sirsa_president():
    d = hr_run("cp-hr-sirsa", "cp_hr_sirsa.html")
    assert d["cp:HR:sirsa-municipal-council:chair"]["name"] == "SHANTI SAWROOP"
    assert d["cp:HR:sirsa-municipal-council:1"]["record_for"] == "councillor:HR:sirsa-municipal-council:1"
    assert len(d) == 3


def test_hr_yamunanagar_cf_email_and_id_table_skipped():
    d = hr_run("cp-hr-yamunanagar", "cp_hr_ynr.html")
    assert d["cp:HR:yamuna-nagar-municipal-corporation:chair"]["email"] == "sumanbahmani1970@gmail.com"
    assert d["cp:HR:yamuna-nagar-municipal-corporation:1"]["name"] == "Reena"
    assert len(d) == 2                     # the second table (family id / aadhaar columns) is not read
    assert not any("aadhaar" in json.dumps(r).lower() for r in d.values())


def test_hr_panipat_blocks_ward_pad():
    d = hr_run("cp-hr-panipat", "cp_hr_panipat.html")
    r = d["cp:HR:panipat-municipal-corporation:2"]
    assert r["name"] == "Kajal Sharma" and r["phone"] == "8607663520"
    assert r["record_for"] == "councillor:HR:panipat-municipal-corporation:02"


def test_phones_two_mobiles_one_space():
    assert cp.phones("9988755533 7889267809") == "9988755533, 7889267809"
    assert cp.phones("98155 17018") == "9815517018"


def test_table_members_ward_column():
    html = ("<table><tr><th>Sr. No.</th><th>Ward No.</th><th>Name</th><th>Mobile</th></tr>"
            "<tr><td>1</td><td>7</td><td>A B</td><td>9876543210</td></tr></table>")
    d = cp.table_members(html, "HR", "X", "https://x/", record_prefix="councillor:HR:x")[0]
    assert d["ward_no"] == "7" and d["record_for"] == "councillor:HR:x:7"
