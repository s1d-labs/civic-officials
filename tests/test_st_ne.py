"""North-east state-level readers (dforms/st_ne.py, st_sk_portal, st_tr_portal, st_tr_dirs, st_ml_keycontacts, st_ar_whoswho,
st_as_secretaries, st_mn_police) on pages and PDFs saved 2026-11-13. No network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import (_field, _state, st_ar_whoswho, st_as_secretaries, st_ml_keycontacts, st_mn_police, st_ne, st_ne_page,  # noqa: E402
                    st_sk_portal, st_tr_dirs, st_tr_portal)

DATA = Path(__file__).parent / "data"
MODULES = [st_ne_page, st_sk_portal, st_tr_portal, st_tr_dirs, st_ml_keycontacts, st_ar_whoswho, st_as_secretaries, st_mn_police]


def page(name):
    return (DATA / name).read_text(encoding="utf-8")


def by_name(recs, part):
    return [d for _, d in recs if part.lower() in d.get("name", "").lower()]


def trail_ok(recs):
    for rid, d in recs:
        assert d["type"] == "dept_office" and d["level"] in ("state", "division", "district"), rid
        assert d["src_url"].startswith("http") and d["src_pos"], rid
        assert d["state_code"] and d["dept"], rid
    assert len({rid for rid, _ in recs}) == len(recs)


def test_methods_and_seeds():
    for m in MODULES:
        assert m.METHOD
    for st in ("sk", "tr", "ml", "ar", "as", "mn", "mz"):
        items = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert items and all(i["payload"]["reader"].startswith("st_") and i["payload"]["route"] in ("abroad", "proxy", "direct")
                             and "india_only" in i["payload"] for i in items)


def test_sikkim():
    phones, ministers = st_sk_portal.parse_tel(page("st_sk_tel.html"))
    assert len(ministers) == 12 and ministers[0][1]["post_kind"] == "minister"
    hod = st_sk_portal.parse_hod(page("st_sk_hod.html"), phones=phones)
    assert len(hod) == 70
    cs = [d for _, d in hod if d["post"] == "Chief Secretary"][0]
    assert cs["name"] == "Mr. Ravindra Telang, IAS" and cs["post_kind"] == "chief_secretary" and cs["phone"].startswith("204884")
    dgp = by_name(hod, "Akshay Sachdeva")[0]
    assert dgp["post_kind"] == "dgp" and dgp["dept"] == "police" and dgp["body_kind"] == "police"
    assert sum(1 for _, d in hod if d.get("phone")) >= 30
    dc = st_sk_portal.parse_dc(page("st_sk_dc.html"))
    assert len(dc) == 6 and dc[0][1]["level"] == "district" and dc[0][1]["district"] == "Pakyong" and dc[0][1]["phone"] == "8824132808"
    emp = st_sk_portal.parse_emp(page("st_sk_emp_p6.html"), "https://www.sikkim.gov.in/x")
    assert len(emp) == 4 and emp[0][1]["place_of_posting"] == "Gangtok"
    trail_ok(hod + ministers + dc + emp)


def test_sikkim_fetch_pages():
    class R:
        def __init__(self, text):
            self.text, self.content, self.status_code = text, text.encode(), 200
    first = page("st_sk_emp_p6.html").replace('id="totalRec" type="hidden" value="', 'id="totalRec" type="hidden" value="2')
    pages = {st_sk_portal.TEL: page("st_sk_tel.html"), st_sk_portal.HOD: page("st_sk_hod.html"), st_sk_portal.DC: page("st_sk_dc.html"),
             st_sk_portal.EMP_FIRST: first, st_sk_portal.EMP.format(n=2): page("st_sk_emp_p6.html")}
    asked = []

    def get(u, **k):
        asked.append(u)
        return R(pages[u]) if u in pages else None
    recs, files, why = st_sk_portal.fetch(st_sk_portal.items()[0]["payload"], get)
    assert not why and len(files) >= 5 and st_sk_portal.EMP.format(n=3) in asked
    assert len(recs) == 70 + 12 + 6 + 4 + 4


def test_tripura_portal():
    r = st_tr_portal.parse(page("st_tr_senior.html"))
    assert len(r) == 20
    cs = r[0][1]
    assert cs["post_kind"] == "chief_secretary" and "cs-tripura@nic.in" in cs["email"] and "09402182582" in cs["phone"]
    assert r[0][1]["src_pos"] == {"table": 1, "row": 2}
    trail_ok(r)


def test_tripura_index_and_pdfs():
    items = st_tr_dirs.index_items(page("st_tr_index.html"))
    assert len(items) == 56 and items[0]["payload"]["group"] == "secretariat" and items[3]["payload"]["group"] == "district"
    pdf = lambda n: _field.pdf_text((DATA / f"st_tr_{n}.pdf").read_bytes())   # noqa: E731
    cs = st_tr_dirs.parse(pdf("cs"), {"url": "https://tripura.gov.in/f/Chief_Secretary_Office_18_06_2024.pdf", "org": "Chief Secretary Office",
                                      "group": "secretariat"})
    assert [(d.get("name"), d["post"], d["phone"]) for _, d in cs] == [
        ("Shri Jitendra Kumar Sinha", "Chief Secretary", "0381 241 4392"), (None, "P.P.S. to the Chief Secretary", "0381 2413200")]
    assert cs[0][1]["email"] == "cs-tripura@nic.in" and cs[0][1]["src_pos"]["page"] == 1
    pol = st_tr_dirs.parse(pdf("police"), {"url": "https://tripura.gov.in/f/Home_Police.pdf", "org": "Home (Police)", "group": "department"})
    dgp = by_name(pol, "G.S. Rao")[0]
    assert dgp["post"].startswith("Director General of Police") and dgp["post_kind"] == "dgp" and dgp["email"] == "dgp@tripurapolice.nic.in"
    assert "0381-232-3291" in dgp["phone"] and dgp["dept"] == "police"
    assert by_name(pol, "Avula Ramesh Reddy")[0]["phone"] == "0381-230-5604"
    food = st_tr_dirs.parse(pdf("food"), {"url": "https://tripura.gov.in/f/Food.pdf", "org": "Food, Civil Supplies Consumer Affairs",
                                          "group": "department"})
    assert [(d["post"], d["phone"]) for _, d in food][:2] == [("Hon'ble Minister, FCS & CA", "0381 241 4007"),
                                                               ("Principal Secretary", "0381 241 5712")]
    trail_ok(cs + pol + food)


def test_meghalaya():
    items = st_ml_keycontacts.index_items(page("st_ml_index.html"))
    assert len(items) == 71 and any(i["payload"]["org"] == "Commissioner of Division, Shillong" for i in items)
    secy = st_ml_keycontacts.parse(page("st_ml_secretaries.html"), {"url": "https://meghalaya.gov.in/key-contacts/secretaries",
                                                                    "page": "secretaries"})
    assert len(secy) == 336
    d = secy[0][1]
    assert d["department"] == "Agriculture and Farmers' Welfare Department" and d["dept"] == "agriculture"
    assert d["email"] == "dvijaykumar@ias.nic.in" and d["phone"] == "0364-2226043" and d["post_kind"] == "secretary"
    div = st_ml_keycontacts.parse(page("st_ml_org.html"), {"url": "https://meghalaya.gov.in/key-contacts/organisation/35298",
                                                           "page": "organisation/35298", "org": "Commissioner of Division, Shillong"})
    assert div[0][1]["level"] == "division" and div[0][1]["division"] == "Shillong" and "274" in div[0][1]["districts"]
    trail_ok(secy + div)


def test_arunachal():
    r = st_ar_whoswho.parse(page("st_ar_whoswho.html"))
    assert len(r) >= 150
    cs = by_name(r, "Manish Gupta")[0]
    assert cs["post_kind"] == "chief_secretary" and cs["email"] == "cs-arunachal@nic.in" and "2212444" in cs["phone"]
    assert by_name(r, "Kaling Tayeng")[0]["also_divisional_commissioner"] == "West"
    assert by_name(r, "Mabi Taipodia")[0]["post_kind"] == "deputy_secretary"
    trail_ok(r)


def test_assam():
    r = st_as_secretaries.parse(page("st_as_secretaries.html"))
    assert len(r) == 119
    assert r[0][1]["name"] == "Dr. Ravi Kota, IAS" and r[0][1]["post_kind"] == "chief_secretary" and r[0][1]["recruitment"] == "RR-1993"
    assert sum(1 for _, d in r if d.get("on_central_deputation")) >= 19
    cm = [d for _, d in r if d["post"].startswith("Secretary to Hon")][0]
    assert cm["post_kind"] == "secretary"
    trail_ok(r)
    assert _state.districts_of("AS", "Barak Valley Division")[1] == ["282", "289", "293"]
    assert sum(len(v) for v in _state.divisions("AS").values()) == 35


def test_manipur_police():
    r = st_mn_police.parse(page("st_mn_police_senior.html"))
    assert len(r) == 15
    assert r[0][1]["post_kind"] == "dgp" and r[0][1]["email"] == "dgp-mnp@nic.in" and r[0][1]["phone_residence"] == "0385-2445062"
    z = by_name(r, "Themthing")[0]
    assert z["level"] == "division" and z["division"] == "Zone I" and z["post_kind"] == "igp"
    trail_ok(r)


def test_pdf_blocks_phone_fragments():
    text = "Sl. Name            Designation   Contact No\n1   Shri A B, IAS   Director      0381 241\n                                  4007\n"
    b = st_ne.pdf_blocks(text)
    assert st_ne.block_fields(b[0])[:3] == ("Shri A B, IAS", "Director", "0381 241 4007")


def test_generic_pages():
    from dforms import st_ne_page
    seeds = {i["payload"]["page_key"]: i["payload"] for st in ("ml", "tr", "ar", "mz")
             for i in json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text()) if i["payload"]["reader"] == "st_ne_page"}
    fx = {"ml-police-tel": "st_ml_police_tel.html", "tr-tcw": "st_tr_tcw.html", "ar-sec": "st_ar_secap.html",
          "mz-sec": "st_mz_sec_table.html", "ml-labour": "st_ml_meglc.html"}
    got = {k: st_ne_page.parse((DATA / f).read_text(errors="replace"), seeds[k]) for k, f in fx.items()}
    assert {k: len(v) for k, v in got.items()} == {"ml-police-tel": 63, "tr-tcw": 5, "ar-sec": 5, "mz-sec": 29, "ml-labour": 65}
    pol = got["ml-police-tel"]
    assert pol[0][1]["post_kind"] == "dgp" and pol[0][1]["name"] == "Smti. I. Nongrang, IPS" and pol[1][1]["post_kind"] == "adgp"
    assert got["tr-tcw"][1][1]["post_kind"] == "vice_chairperson" and got["tr-tcw"][0][1]["email"] == "tripuracommissionforwomen@gmail.com"
    sec = got["ar-sec"][1][1]
    assert "name" not in sec and sec["post"] == "Secretary to the Commission" and sec["phone"] == "0360-2290621"
    mz = got["mz-sec"][0][1]
    assert mz["post_kind"] == "state_election_commissioner" and mz["dept"] == "elections" and "9436154739" in mz["phone"]
    lab = got["ml-labour"][0][1]
    assert "name" not in lab and lab["office"].startswith("Office of the Labour Commissioner")
    for v in got.values():
        trail_ok(v)


def test_tripura_untitled_name_with_serial_is_a_person():
    """Welfare for Minorities list (the full saved file, 2026-11-13 audit): "3  Kabita Debbarma, TCS, Gr-II  Deputy Director" has
    no title; she was not read and her phone went to row 2. Records 2 -> 3."""
    t = _field.pdf_text((DATA / "st_tr_minorities.pdf").read_bytes())
    r = st_tr_dirs.parse(t, {"url": "https://tripura.gov.in/f/Welfare_for_Minorities.pdf", "org": "Welfare for Minorities",
                             "group": "department"})
    assert [(d.get("name"), d["phone"]) for _, d in r] == [("Shri Sukla Charan Noatia", "0381-241-3388"),
                                                          ("Shri. Nirmal Adhikari, IAS", "9436540890"),
                                                          ("Kabita Debbarma, TCS", "+91-9366113876")]
    assert r[2][1]["email"] == "mwtripura@gmail.com"
