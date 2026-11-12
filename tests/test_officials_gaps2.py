"""Offline tests of the readers added for the second gaps round of 2026-11-12 (district health, education, rural development
officers): pages saved once from archive.s1d.me or fetched once by hand, in tests/data/gaps2/. No test touches the network."""
import gzip
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

G = DATA / "gaps2"


def _text(name):
    b = (G / name).read_bytes()
    return (gzip.decompress(b) if name.endswith(".gz") else b).decode("utf-8")


# ---- Andhra Pradesh: hmfw.ap.gov.in (DMHOs, state officers, CHC / area hospital superintendents) ----
def test_ap_hmfw_contact():
    m = mod("health_ap_hmfw")
    recs = m.parse_contact(_text("ap_hmfw_contact.html"))
    check_records(recs, "health_ap_hmfw", "health")
    by = dict(recs)
    dmho = [d for d in by.values() if d["level"] == "district"]
    assert len(dmho) == 28 and len({d["district"] for d in dmho}) == 28
    d = by["dept:health_ap_hmfw:dmho:vizianagaram"]
    assert (d["name"], d["phone"], d["email"]) == ("Dr.S.V.Ramana Kumari", "9849902278", "dmhovzm@gmail.com")
    assert d["post"] == "District Medical & Health Officer"
    st = [d for d in by.values() if d["level"] == "state"]
    assert len(st) == 11 and all("|" not in d["post"] for d in st)


def test_ap_hmfw_csms():
    m = mod("health_ap_hmfw")
    recs = m.parse_csms(_text("ap_hmfw_csms.html"))
    check_records(recs, "health_ap_hmfw", "health")
    assert len(recs) == 115 and len({d["district"] for _, d in recs}) == 13
    d = dict(recs)["dept:health_ap_hmfw:hospital:srikakulam:chc-pathapatnam"]
    assert (d["name"], d["phone"], d["email"], d["level"]) == ("Dr. L. Ram Mohan", "800-855-3372", "chcpathapatnam@gmail.com", "facility")
    ic = dict(recs)["dept:health_ap_hmfw:hospital:srikakulam:chc-kotturu"]
    assert ic["post"] == "Medical Superintendent (in charge)" and ic["name"] == "Dr. J. Krishna Mohan"


def test_ap_hmfw_fetch():
    m = mod("health_ap_hmfw")
    get = fake_get({m.CONTACT: "gaps2/ap_hmfw_contact.html", m.CSMS: "gaps2/ap_hmfw_csms.html"})
    recs, files, why = m.fetch(m.items()[0]["payload"], get)
    assert not why and len(recs) == 154 and len(files) == 2


# ---- Rajasthan: Jankalyan portals (districtfrontwebapi GetDepartmentContactDetail, answers saved 2026-11-12) ----
def _rj_payload(label):
    m = mod("rj_jankalyan")
    return next(i["payload"] for i in m.items() if i["key"] == f"rj_jankalyan:{label}")


def test_rj_jankalyan_items():
    m = mod("rj_jankalyan")
    its = m.items()
    assert len(its) == len({i["key"] for i in its}) == 94
    p = _rj_payload("jaipur")
    assert (p["code"], p["district"], p["dept"], p["india_only"]) == ("37", "Jaipur", "administration", True)
    assert _rj_payload("nhm")["level"] == "state" and _rj_payload("jaipurruralpolice")["dept"] == "police"
    assert json.dumps(m.body("37"))[:60].startswith('{"Page": 1, "PageSize": 10000')


def test_rj_jankalyan_parse_kota():
    m = mod("rj_jankalyan")
    recs, files = m.parse(json.loads((G / "rj_jankalyan_kota.json").read_text()), _rj_payload("kota"))
    by = dict(recs)
    d = by[next(r for r, x in recs if x.get("post") == "DISTRICT COLLECTOR")]
    assert (d["name"], d["dept"], d["level"], d["district"]) == ("SHRI PIYUSH SAMARIYA", "administration", "district", "Kota")
    assert d["phone"] == "9982910228, 0744-2451200"
    sdm = [x for x in by.values() if x["level"] == "subdivision"]
    assert len(sdm) == 6 and all(x["dept"] == "administration" for x in sdm)
    assert len([x for x in by.values() if x.get("category") == "Pradhan" and x["level"] == "block"]) == 5
    assert len(files) == 17 and all(u.startswith("https://jankalyanfile.rajasthan.gov.in/") for _, u, _ in files)
    assert len(recs) == 41 and len(by) == 41


def test_rj_jankalyan_parse_barmer():
    m = mod("rj_jankalyan")
    recs, files = m.parse(json.loads((G / "rj_jankalyan_barmer.json").read_text()), _rj_payload("barmer"))
    by = dict(recs)
    dso = [x for x in by.values() if x["dept"] == "food_supplies"]
    assert len(dso) == 1 and dso[0]["email"] == "dsofood-bar-rj@nic.in" and dso[0]["phone"] == "02982 220164"
    sp = [x for x in by.values() if x["dept"] == "police"]
    assert sp and sp[0]["post"].startswith("SUPERINTENDENT OF POLICE")
    rti = [x for x in by.values() if x.get("category") == "Right to Information"]
    assert rti and all(x["dept"] == "administration" for x in rti)
    assert all("DateOfBirth" not in json.dumps(x) for x in by.values())


def test_rj_jankalyan_fetch():
    m = mod("rj_jankalyan")
    p = _rj_payload("kota")
    get = fake_get({("POST", m.API): "gaps2/rj_jankalyan_kota.json",
                    (lambda u, meth, d: u.startswith("https://jankalyanfile.rajasthan.gov.in/")): "gaps2/tiny.pdf"})
    recs, files, why = m.fetch(p, get)
    assert not why
    srcs = [d for _, d in recs if d["type"] == "source_file"]
    assert len(srcs) == 17 and all(d["fetched"] and d["stored"].startswith("depts/rj_jankalyan/kota/") for d in srcs)
    assert len(files) == 18 and files[0][0] == "depts/rj_jankalyan/kota/contact-detail.json.gz"
    post = [c for c in get.calls if c[0] == "POST"][0]
    assert json.loads(post[2])["AdvanceSearchModel"]["DepartmentCode"] == 44
    check_records([r for r in recs if r[1]["type"] == "dept_office" and r[1]["dept"] == "administration"], "rj_jankalyan",
                  "administration")
