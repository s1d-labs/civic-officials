"""Offline tests of the disaster management and home guard readers (dforms/emerg_ddma_*.py, dforms/emerg_hg_*.py) and their seeds
(seeds/dept_emerg_ddma_*.json, seeds/dept_emerg_hg_*.json). Small samples in tests/data/emerg_ddma_* / emerg_hg_*; no network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod  # noqa: F401


def by_id(recs):
    return dict(recs)


def check_emerg(recs, module, dept, layer):
    check_records(recs, module, dept)
    for rid, d in recs:
        assert d["layer"] == layer and d["level"] in ("state", "division", "district", "subdistrict", "subdivision", "facility"), d
        assert d.get("area") and d.get("post"), d


# ---- S3WaaS district disaster management pages ----
def s3(name, url, district, state):
    m = mod("emerg_ddma_s3waas")
    p = {"reader": "emerg_ddma_s3waas", "url": url, "district": district, "state": state}
    return m.fetch(p, fake_get({url: f"emerg_ddma_s3waas_{name}.html"}))


def test_s3waas_table_with_header():
    recs, files, why = s3("chamoli", "https://chamoli.gov.in/disaster-management/", "Chamoli", "UK")
    assert why == "" and len(recs) == 2 and files[0][0] == "depts/emerg_ddma_s3waas/chamoli.gov.in-disaster-management.html.gz"
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    d = by_id(recs)["dept:emerg_ddma_s3waas:chamoli.gov.in:page:disaster-management-officer"]
    assert (d["name"], d["post"], d["area"]) == ("Shri Nand Kishore Joshi", "Disaster Management Officer", "Chamoli")
    assert d["phone"] == "01372-251437, 9411352136" and d["fax"] == "01372-252203"
    assert d["email"] == "ddmachamoli1077@gmail.com" and d["last_updated"] == "2025-10-27" and d["state"] == "UK"


def test_s3waas_name_and_post_in_one_cell():
    recs, _, why = s3("serchhip", "https://serchhip.nic.in/disaster-management/", "Serchhip", "MZ")
    assert why == "" and len(recs) == 4
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    d = recs[0][1]
    assert (d["name"], d["post"]) == ("Pi Rebecca Laldinmawii Hrahsel, MCS", "SDO (Sadar) Serchhip")
    assert d["covers"].startswith("New Serchhip North") and d["phone"] == "03838-222285, 8974736278"


def test_s3waas_plain_text():
    recs, _, why = s3("lakhisarai", "https://lakhisarai.nic.in/disaster-management/", "Lakhisarai", "BR")
    assert why == "" and len(recs) == 2
    check_emerg(recs, "emerg_ddma_s3waas", "disaster", "emerg_ddma")
    a, b = recs[0][1], recs[1][1]
    assert (a["post"], a["phone"], a["level"]) == ("State Control Room", "0612-2217305", "state")
    assert (b["post"], b["phone"]) == ("District Control Room Numbers", "06346-232124, 232190, 9431071977")   # Landline + Mobile lines


def test_s3waas_name_designation_lines():
    recs, _, _ = s3("namsai", "https://namsai.nic.in/disaster-management/", "Namsai", "AR")
    assert len(recs) == 1
    d = recs[0][1]
    assert (d["name"], d["post"], d["phone"]) == ("Mrs. Thongchin", "District Disaster Management Officer", "8259003656")


def test_s3waas_no_answer_and_seed():
    m = mod("emerg_ddma_s3waas")
    assert m.fetch({"url": "https://x.nic.in/disaster-management/"}, fake_get({})) == ([], [], "no answer")
    items = m.items()
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and all(k.startswith("emerg_ddma_s3waas-") for k in keys)
    assert all(i["payload"]["reader"] == "emerg_ddma_s3waas" and i["payload"]["state"] for i in items)
    assert sum(1 for i in items if i["payload"].get("saved")) >= 150


# ---- Kerala DM Directory 2025 ----
def test_kl_directory():
    m = mod("emerg_ddma_kl")
    pages = (DATA / "emerg_ddma_kl_layout.txt").read_text().split("\f")
    recs = m.records(pages)
    assert len(recs) == 21
    ids = by_id(recs)
    for rid, d in recs:
        assert rid.startswith("dept:emerg_ddma_kl:") and d["layer"] == "emerg_ddma" and d["state"] == "KL" and d["phone"], d
    d = ids["dept:emerg_ddma_kl:helplines:state:state-emergency-helpline"]
    assert d["helpline"] == "1070" and d["level"] == "state"
    d = ids["dept:emerg_ddma_kl:deoc:kollam:district-emergency-operations-centre"]
    assert (d["district"], d["phone"], d["dept"]) == ("Kollam", "0474-2794002, 9447677800, 2794004", "disaster")
    d = ids["dept:emerg_ddma_kl:teoc:thiruvananthapuram:kattakada"]
    assert (d["area"], d["level"], d["phone"]) == ("Kattakada", "subdistrict", "0471 2291414, 9497711284")
    d = ids["dept:emerg_ddma_kl:district:thiruvananthapuram:district-police-chief"]
    assert (d["dept"], d["section"], d["phone"]) == ("police", "Police", "9497996991, 0471-2320579, 0471-2320486")
    d = ids["dept:emerg_ddma_kl:district:thiruvananthapuram:fire-and-rescue-station-thiruvananthapuram"]
    assert (d["dept"], d["level"]) == ("fire", "facility")   # the station name on the next line is not a district heading
    assert len(m.items()) == 1


def test_kl_not_pdf():
    m = mod("emerg_ddma_kl")
    assert m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_ddma_sk.html"}))[2] == "not a PDF"


# ---- Sikkim SSDMA who is who ----
def test_sk_whoiswho():
    m = mod("emerg_ddma_sk")
    recs, files, why = m.fetch({"url": m.URL}, fake_get({m.URL: "emerg_ddma_sk.html"}))
    assert why == "" and len(recs) == 9 and files[0][0] == "depts/emerg_ddma_sk/whoiswho.html.gz"
    check_emerg(recs, "emerg_ddma_sk", "disaster", "emerg_ddma")
    ids = by_id(recs)
    d = ids["dept:emerg_ddma_sk:ssdma-officials:director"]
    assert (d["level"], d["name"], d["phone"], d["email"]) == ("state", "Shri. Prabhakar Rai", "9434179141, 03592-201145",
                                                                "directorssdma@gmail.com")
    d = ids["dept:emerg_ddma_sk:ddma-gyalshing:adc-gyalshing"]
    assert (d["district"], d["level"], d["name"], d["org"]) == ("Gyalshing", "district", "Mr. Suresh Rai",
                                                               "Land Revenue and Disaster Management Department")


# ---- Uttar Pradesh Home Guards officials ----
def test_hg_up():
    m = mod("emerg_hg_up")
    recs = m.records([(DATA / "emerg_hg_up_layout.txt").read_text()])
    assert len(recs) == 16
    check_emerg(recs, "emerg_hg_up", "police", "emerg_hg")
    ids = by_id(recs)
    d = ids["dept:emerg_hg_up:cghg-up"]
    assert (d["post"], d["level"], d["phone"], d["email"]) == ("Commandant General, Home Guards", "state", "8005194100", "cghg-up@nic.in")
    d = ids["dept:emerg_hg_up:cmdhgrb-up"]
    assert (d["post"], d["district"], d["phone"]) == ("District Commandant, Home Guards", "Rae Bareli", "8005194068")
    d = ids["dept:emerg_hg_up:dtc-hg.lu"]
    assert d["level"] == "division" and d["area"] == "Lucknow" and d["email"] == "dtc-hg.lu@up.gov.in"
    assert m.unit("cmdhgpr-up")[2] == "pr" and m.CODES["pr"] == "Pratapgarh" and m.TRAINING["pr"] == "Prayagraj"
    assert len(m.CODES) == 75 and len(m.items()) == 1


def test_seed_keys():
    for f in ROOT.glob("seeds/dept_emerg_ddma_*.json"):
        for it in json.loads(f.read_text()):
            assert it["key"].startswith("emerg_ddma_") and it["payload"]["reader"] in f.stem, (f, it["key"])
    for f in ROOT.glob("seeds/dept_emerg_hg_*.json"):
        for it in json.loads(f.read_text()):
            assert it["key"].startswith("emerg_hg_") and it["payload"]["reader"] in f.stem, (f, it["key"])
