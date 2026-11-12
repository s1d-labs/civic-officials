"""Offline tests of the south readers of 2026-11-12 (district health and education officers in Karnataka, Tamil Nadu,
Telangana): files saved once from archive.s1d.me or fetched once by hand, in tests/data/south3/. No test touches the network."""
import gzip
import re

import provenance  # noqa: F401  (the readers import it)
from esw_common import DATA, check_records, fake_get, mod

D = DATA / "south3"


def _gz(name):
    return gzip.decompress((D / name).read_bytes()).decode("utf-8")


# ---- Karnataka: RTI list of PIOs, Nodal Officers and FAAs of the Health & FW Department (pages 2, 10, 16, 40, 120, 200) ----
def test_ka_rti_parse():
    m = mod("health_ka_rti")
    text = _gz("ka_rti_pages.txt.gz")
    recs = m.parse(text)
    check_records(recs, "health_ka_rti", "health")
    by = dict(recs)
    d = by["dept:health_ka_rti:p2-1"]
    assert (d["name"], d["phone"], d["email"], d["level"]) == ("Kuppurulingaiah B", "9449843141", "caofa.healthkar.in@gmail.com", "state")
    d = by["dept:health_ka_rti:p40-54"]           # e-mail cut by the column ("phcimangala@gmail.co" + "m"), no person name
    assert d["email"] == "phcimangala@gmail.com" and d["district"] == "Chitradurga" and d["level"] == "facility"
    assert "Aimangala" in d["post"] and not d.get("name")
    d = by["dept:health_ka_rti:p120-93"]          # Mandya has no heading: the district comes from the row text
    assert (d["name"], d["email"], d["district"]) == ("Dr.Veerabhadrappa.P", "ictckirugavalu@gmail.com", "Mandya")
    d = by["dept:health_ka_rti:p120-94"]
    assert d["name"] == "Dr Ravishankar C" and d["level"] == "subdistrict" and d["email"] == "thomaddur@gmail.com"
    d = by["dept:health_ka_rti:p200-1"]
    assert d["district"] == "Vijayanagara" and d["name"] == "B G Giridhara"
    dho = [d for d in by.values() if d["rti_role"] == "First Appellate Authority" and d.get("district") == "Vijayanagara"
           and re.search("District Health", d.get("post") or "")]
    assert dho and dho[0]["email"] == "dhovijayanagara21@gmail.com" and dho[0]["phone"] == "9449842080"
    for rid, d in recs:                           # the trail: page + line of the serial number, and the line itself
        pos = d["src_pos"]
        page = text.split("\f")[pos["page"] - 1].split("\n")
        assert page[pos["line"] - 1] == pos["line_text"] and pos["line_text"].strip().startswith(pos["serial"])


def test_ka_rti_fetch_discovers_the_list():
    m = mod("health_ka_rti")
    get = fake_get({m.HOME: "south3/ka_hfw_home_rti_menu.html"})
    assert m.current_url(get) == m.URL
    p = m.items()[0]["payload"]
    assert p["india_only"] and p["discover"]
    recs, files, why = m.fetch(p, get)            # the PDF itself is not saved here (13.6 MB): no answer -> no records
    assert recs == [] and why == "no answer"


# ---- Tamil Nadu: Deputy Directors of Health Services of the 45 health unit districts (DPH&PM, Dec 2021) ----
def test_tn_dph_ddhs():
    m = mod("health_tn_dph")
    get = fake_get({m.URL: "south3/tn_dph_ddhs_dec2021.pdf"})
    recs, files, why = m.fetch(m.items()[0]["payload"], get)
    assert not why and len(recs) == 45 and len(files) == 1
    check_records(recs, "health_tn_dph", "health")
    by = dict(recs)
    assert all(d.get("district") for d in by.values())
    assert len({d["district"] for d in by.values()}) == 37      # 45 HUDs in 37 revenue districts (Chennai has none)
    d = by["dept:health_tn_dph:ddhs:aranthangi"]
    assert (d["name"], d["district"], d["phone"], d["fax"]) == ("Dr.B.Kalaivani", "Pudukkottai", "9788855481, 04371-220501", "04371-220501")
    d = by["dept:health_tn_dph:ddhs:coimbatore"]                 # phones on the lines above and below the serial line
    assert d["name"] == "Dr.P.Aruna" and "0422-2220351" in d["phone"] and "8248411359" in d["phone"]
    assert by["dept:health_tn_dph:ddhs:tenkasi"]["vacant"] is True
    assert by["dept:health_tn_dph:ddhs:mayiladuthurai"]["name"] == "Dr.P.Prathap kumar (MHO Kumbakonam)(i/c)"
    assert all(d["src_pos"]["line_text"].lstrip().startswith(d["list_no"]) for d in by.values())


# ---- Telangana: contact page of the Director of School Education (33 DEOs, 2 RJDs, state officers) ----
def test_tg_dse_contact():
    m = mod("edu_tg_dse")
    recs = m.parse(_gz("tg_dse_contact.html.gz"))
    check_records(recs, "edu_tg_dse", "education")
    by = dict(recs)
    deo = [d for d in by.values() if d["level"] == "district"]
    assert len(deo) == 33 and len({d["district"] for d in deo}) == 33 and all(d["district"] for d in deo)
    d = by["dept:edu_tg_dse:deo:yadadri-bhongiri"]
    assert (d["name"], d["phone"], d["email"], d["district"]) == ("A. Bixapathi (FAC)", "7995087630", "deo_ydd@yahoo.com", "Yadadri Bhuvanagiri")
    assert by["dept:edu_tg_dse:deo:medchal"]["district"] == "Medchal Malkajgiri"
    assert len([d for d in by.values() if d["level"] == "region"]) == 2
    assert all(isinstance(d["src_pos"]["row"], int) for d in by.values())
