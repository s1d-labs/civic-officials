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
