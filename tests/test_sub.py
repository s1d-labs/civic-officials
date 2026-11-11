"""Offline tests of the sub-district / block office readers (dforms/sub_*.py) on small saved answers in tests/data/sub/.
State readers by other agents have their own files tests/test_sub_<xx>.py."""
import json

from esw_common import ROOT, Answer, DATA, check_records, fake_get, mod  # noqa: F401


def _s3(url, sample, kind, state, district):
    p = {"reader": "sub_s3waas", "url": url, "kind": kind, "state": state, "district": district}
    get = fake_get({url: f"sub/{sample}"})
    recs, files, why = mod("sub_s3waas").fetch(p, get)
    assert why == "" and files and files[0][0].startswith("depts/sub_s3waas/")
    return recs


def test_area_words():
    area = mod("sub_s3waas").area
    assert area("Chail Tehsil") == "Chail"
    assert area("SIRATHU TEHSIL") == "Sirathu"
    assert area("Block – Andana at Moonak") == "Andana at Moonak"
    assert area("SDM GHAGWAL") == "Ghagwal"
    assert area("Alibag Tahasil Office") == "Alibag"
    assert area("विकास खण्ड मंझनपुर") == "मंझनपुर"


def test_tehsil_kaushambi():
    recs = _s3("https://kaushambi.nic.in/public-utility-category/tehsil/", "s3waas_kaushambi_tehsil.html", "tehsil", "UP", "Kaushambi")
    check_records(recs, "sub_s3waas", "revenue")
    d = dict(recs)
    r = d["dept:sub_s3waas:kaushambi.nic.in:tehsil:chail"]
    assert r["area"] == "Chail" and r["level"] == "subdistrict" and r["phone"] == "9454417879"
    # the SDM heads the tehsil in Uttar Pradesh: the email says so
    assert r["email"] == "sdmkos-chail@nic.in" and r["post"] == "Sub-Divisional Magistrate"
    assert r["last_updated"] == "2026-10-28" and r["district"] == "Kaushambi" and len(recs) == 3


def test_blocks_sangrur():
    recs = _s3("https://sangrur.nic.in/public-utility-category/blocks/", "s3waas_sangrur_blocks.html", "block", "PB", "Sangrur")
    check_records(recs, "sub_s3waas", "rural_development")
    d = dict(recs)
    assert len(recs) == 8
    r = d["dept:sub_s3waas:sangrur.nic.in:block:andana-at-moonak"]
    assert r["area"] == "Andana at Moonak" and r["level"] == "block" and r["post"] == "Block Development Officer"
    assert r["phone"] == "01676276342" and r["pincode"] == "148033"


def test_sdm_samba():
    recs = _s3("https://samba.gov.in/public-utility-category/sdm/", "s3waas_samba_sdm.html", "subdivision", "JK", "Samba")
    check_records(recs, "sub_s3waas", "administration")
    d = dict(recs)
    r = d["dept:sub_s3waas:samba.gov.in:subdivision:ghagwal"]
    assert r["email"] == "sdm-ghagwal@jk.gov.in" and r["level"] == "subdivision" and r["address"] == "SDM Office, Ghagwal"


def test_seed_file():
    items = json.loads((ROOT / "seeds" / "dept_sub_s3waas.json").read_text())
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and all(k.startswith("sub_s3waas-") for k in keys)
    for i in items:
        p = i["payload"]
        assert p["reader"] == "sub_s3waas" and p["state"] and p["district"]
        if p.get("discover"):
            assert p["url"].endswith("/") and "public-utility" not in p["url"]
        else:
            assert p["kind"] in ("tehsil", "block", "subdivision", "circle") and "/public-utility-category/" in p["url"]
    assert sum(1 for i in items if not i["payload"].get("discover")) >= 25 and len(items) > 700


def test_discover_kaushambi():
    # one item per district portal: the home page links the tehsil and block categories; banks, police stations ... are skipped
    home = "https://kaushambi.nic.in/"
    p = {"reader": "sub_s3waas", "url": home, "discover": True, "state": "UP", "district": "Kaushambi"}
    get = fake_get({home: "sub/s3waas_kaushambi_home.html",
                    "https://kaushambi.nic.in/public-utility-category/tehsil/": "sub/s3waas_kaushambi_tehsil.html",
                    "https://kaushambi.nic.in/public-utility-category/block/": "sub/s3waas_kaushambi_block.html"})
    m = mod("sub_s3waas")
    assert m.categories((DATA / "sub/s3waas_kaushambi_home.html").read_text(), home) == [
        ("block", "https://kaushambi.nic.in/public-utility-category/block/"),
        ("tehsil", "https://kaushambi.nic.in/public-utility-category/tehsil/")]
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(files) == 2
    d = dict(recs)
    assert len([r for r in d.values() if r["level"] == "block"]) == 8 and len([r for r in d.values() if r["level"] == "subdistrict"]) == 3
    b = d["dept:sub_s3waas:kaushambi.nic.in:block:chail"]
    assert b["dept"] == "rural_development" and b["phone"] == "9454464582" and b["post"] == "Block Development Officer"
    assert m.fetch({**p, "url": "https://example.nic.in/"}, fake_get({}))[2] == "no answer"
