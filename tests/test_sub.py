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


def test_discover_fallback_portal_pages_chandauli():
    # Chandauli's home page links no tehsil / block category; the fallback reads the portal's own /tehsil/ page (archive copy
    # 2026-11-05): "Tehsil | Sub Divisional Magistrate | Teshildar", one phone column per post -> two records per tehsil
    home = "https://chandauli.nic.in/"
    m = mod("sub_s3waas")
    html = (DATA / "sub/s3waas_chandauli_home.html").read_text()
    assert m.categories(html, home) == []
    assert "https://chandauli.nic.in/tehsil/" in m.page_links(html, home)
    p = {"reader": "sub_s3waas", "url": home, "discover": True, "state": "UP", "district": "Chandauli"}
    get = fake_get({home: "sub/s3waas_chandauli_home.html", "https://chandauli.nic.in/tehsil/": "sub/s3waas_chandauli_tehsil_page.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and [f[0] for f in files] == ["depts/sub_s3waas/chandauli.nic.in-home.html.gz",
                                                   "depts/sub_s3waas/chandauli.nic.in-tehsil.html.gz"] and len(recs) == 10
    d = dict(recs)
    s = d["dept:sub_s3waas:chandauli.nic.in:page:subdivision:sakaldiha"]
    assert s["post"] == "Sub-Divisional Magistrate" and s["phone"] == "9454417060" and s["level"] == "subdivision"
    t = d["dept:sub_s3waas:chandauli.nic.in:page:tehsil:sakaldiha"]
    assert t["post"] == "Tahsildar" and t["phone"] == "9454417064" and t["dept"] == "revenue" and t["level"] == "subdistrict"
    assert t["src_url"] == "https://chandauli.nic.in/tehsil/" and set(t["src_pos"]) == {"table", "row"}
    for _, r in recs:
        assert r["state"] == "UP" and r["district"] == "Chandauli" and r["source"] and r["method"]
    # no tehsil page answers: the old reason, with the number of pages read
    get = fake_get({home: "sub/s3waas_chandauli_home.html"})
    assert m.fetch(p, get)[2] == "no tehsil or block categories"


def _tab(name, url, state):
    return mod("sub_s3waas").table_records((DATA / f"sub/{name}").read_text(), url, {"state": state, "district": "X"})


def test_table_layouts():
    # headerless "post - place | phone, email" rows (Sheikhpura, archive copy 2026-11-05)
    d = dict(_tab("s3waas_sheikhpura_subdivision_block.html", "https://sheikhpura.nic.in/sub-division-block/", "BR"))
    b = d["dept:sub_s3waas:sheikhpura.nic.in:page:block:barbigha"]
    assert b["post"] == "Block Development Officer" and b["phone"] == "9431818578" and b["email"] == "bdo.bar-sp-bih@nic.in"
    assert len(d) == 6 and d["dept:sub_s3waas:sheikhpura.nic.in:page:block:ghatkusumbha"]["phone"] == "7549346830, 9431818264"
    # "Block Name | Email Id | No. of Panchayat ..." (Hazaribag): email only, counts left out
    recs = _tab("s3waas_hazaribag_blocks.html", "https://hazaribag.nic.in/blocks/", "JH")
    check_records(recs, "sub_s3waas", "rural_development")
    h = dict(recs)["dept:sub_s3waas:hazaribag.nic.in:page:block:barhi"]
    assert h["email"] == "bdobarhi@gmail.com" and h["post"] == "Block Development Officer" and "phone" not in h
    # "Office | Contact No | EMail | Office Address" (Navsari): Prant office = sub-division, Mamlatdar office = taluka
    d = dict(_tab("s3waas_navsari_subdivision_blocks.html", "https://navsari.nic.in/subdivision-blocks/", "GJ"))
    n = d["dept:sub_s3waas:navsari.nic.in:page:subdivision:chikhali"]
    assert n["post"] == "Prant Officer" and n["phone"] == "02637233544" and n["office"] == "Prant,Chikhali"
    assert any(r["post"] == "Mamlatdar" and r["level"] == "subdistrict" for r in d.values())
    # a bare "Name" column of one-word places (Ayodhya): the place, not a person
    d = dict(_tab("s3waas_ayodhya_subdivision_blocks.html", "https://ayodhya.nic.in/subdivision-blocks/", "UP"))
    a = d["dept:sub_s3waas:ayodhya.nic.in:page:block:masodha"]
    assert "name" not in a and a["area"] == "Masodha" and a["email"] == "bdo.msd@gmail.com"


def test_gadwal_mandal_table_ids_do_not_meet_the_card_ids():
    """Gadwal /mandals/ (the full saved copy, 2026-11-13): 14 mandal tahsildars with name and mobile. Their ids are not those of the
    /tehsil/ category cards (dept:sub_s3waas:gadwal.telangana.gov.in:tehsil:gadwal ...), which overwrote 7 of them before."""
    import gzip
    html = gzip.decompress((DATA / "sub/s3waas_gadwal_mandals_full.html.gz").read_bytes()).decode("utf-8")
    recs = mod("sub_s3waas").table_records(html, "https://gadwal.telangana.gov.in/mandals/", {"state": "TG", "district": "Gadwal"})
    d = dict(recs)
    assert len(recs) == 14 and all(k.startswith("dept:sub_s3waas:gadwal.telangana.gov.in:page:tehsil:") for k in d)
    assert sum(1 for r in d.values() if r.get("name")) == 14 and sum(1 for r in d.values() if r.get("phone")) == 13
    g = d["dept:sub_s3waas:gadwal.telangana.gov.in:page:tehsil:gadwal"]
    assert (g["name"], g["phone"], g["post"]) == ("Sri Mallikarjun", "9000101492", "Tahsildar")
