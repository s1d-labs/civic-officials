"""Offline tests of the sub4 sub-district officer readers for the east and northeast (dforms/sub4_*.py) on saved answers in
tests/data/sub4/. Tripura: state contact directory PDFs (SDMs, BDOs)."""
import json

from esw_common import *  # noqa: F401,F403


def _seeds(st, n):
    seeds = json.loads((ROOT / "seeds" / f"dept_sub4_{st}.json").read_text())
    assert len(seeds) == n and len({s["key"] for s in seeds}) == n
    return seeds


# ---------- Tripura ----------

def test_sub4_tr_seeds():
    m = mod("sub4_tr")
    assert _seeds("tr", 2) == m.items()


def test_sub4_tr_sdm():
    m = mod("sub4_tr")
    p = {s["payload"]["kind"]: s["payload"] for s in m.items()}["sdm"]
    pdf = "https://tripura.gov.in/sites/default/files/2026-11/Sub_Divisional_Magistrates_05_11_2026.pdf"
    get = fake_get({m.PAGE: "sub4/tr_contact_directory.html", pdf: "sub4/tr_sdm.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and [u for _, u, _ in get.calls] == [m.PAGE, pdf]
    assert [f[0] for f in files] == ["depts/sub4_tr/contact-directory.html.gz", "depts/sub4_tr/sdm.pdf"]
    check_records(recs, "sub4_tr", "administration")
    assert len(recs) == 23 and all(d["level"] == "subdivision" and d["subdistrict_code"] and d["district_code"] for _, d in recs)
    d = dict(recs)["dept:sub4_tr:sdm:kanchanpur"]
    assert (d["name"], d["cadre"], d["email"], d["phone"], d["district_code"], d["subdistrict_code"]) == \
        ("Thite Shubham Bhagvan", "IAS", "sdmkcp-tr@nic.in", "03824-265211", "270", "6685")
    d = dict(recs)["dept:sub4_tr:sdm:sonamura"]
    assert d["email"] == "sdmofficesonamura@gmail.com" and d["phone"] == "0381-2750222, 9436454678"
    assert d["src_pos"] == {"page": 2, "row": 8, "sn": "21"} and d["src_url"] == pdf and d["last_updated"] == "2026-11-05"


def test_sub4_tr_bdo():
    m = mod("sub4_tr")
    p = {s["payload"]["kind"]: s["payload"] for s in m.items()}["bdo"]
    pdf = "https://tripura.gov.in/sites/default/files/2026-10/Block_Development_Officers_27_10_2026.pdf"
    recs, files, why = m.fetch(p, fake_get({m.PAGE: "sub4/tr_contact_directory.html", pdf: "sub4/tr_bdo.pdf"}))
    assert why == ""
    check_records(recs, "sub4_tr", "rural_development")
    assert len(recs) == 58 and len({d["lgd_block_code"] for _, d in recs}) == 58
    d = dict(recs)["dept:sub4_tr:bdo:ambassa"]
    assert (d["name"], d["email"], d["phone"], d["lgd_block_code"], d["district_code"]) == \
        ("Barnita Biswas", "po_abs@yahoo.co.in", "03826-222360", "2410", "269")      # the fax number is left out
    assert dict(recs)["dept:sub4_tr:bdo:pecharthal"]["district_code"] == "655"         # "Unokoti District"


def test_sub4_tr_page_down_uses_payload_url():
    m = mod("sub4_tr")
    p = {s["payload"]["kind"]: s["payload"] for s in m.items()}["bdo"]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "sub4/tr_bdo.pdf"}))
    assert why == "" and len(recs) == 58 and [f[0] for f in files] == ["depts/sub4_tr/bdo.pdf"]


# ---------- Nagaland ----------

def test_sub4_nl_row():
    m = mod("sub4_nl_row")
    assert _seeds("nl", 1) == m.items()
    recs, files, why = m.fetch(m.items()[0]["payload"], fake_get({m.URL: "sub4/nl_row.html"}))
    assert why == "" and files[0][0] == "depts/sub4_nl_row/public-entities.html.gz"
    check_records(recs, "sub4_nl_row", "administration")
    by = dict(recs)
    assert len(recs) == 32 and all(d["district_code"] for _, d in recs)
    assert sum(d["level"] == "district" for _, d in recs) == 16 and sum(d["level"] == "subdivision" for _, d in recs) == 16
    d = by["dept:sub4_nl_row:dc:kohima"]
    assert (d["name"], d["cadre"], d["phone"], d["email"], d["district_code"]) == \
        ("Henok Buchem", "NCS", "8787679448", "dckma-ngl@nic.in", "245")
    d = by["dept:sub4_nl_row:eac:dimapur"]
    assert (d["name"], d["post"], d["phone"], d["src_pos"]) == ("Imlijungla", "Extra Assistant Commissioner", "7982588143",
                                                              {"table": 1, "row": 19})
    assert "name" not in by["dept:sub4_nl_row:sdo:noklak"]          # "Noklak SDO": a post without a person


# ---------- Meghalaya ----------

def test_sub4_ml_mcs():
    m = mod("sub4_ml_mcs")
    assert _seeds("ml", 1) == m.items()
    routes = {m.URL: "sub4/ml_mcs.html"}
    routes.update({f"{m.URL}?page={n}": f"sub4/ml_mcs_{n}.html" for n in (1, 2, 3, 4)})
    get = fake_get(routes)
    recs, files, why = m.fetch(m.items()[0]["payload"], get)
    assert why == "" and len(get.calls) == 5 and len(files) == 4          # page 4 has no officers: the reader stops there
    check_records([r for r in recs if r[1]["level"] == "block"], "sub4_ml_mcs", "rural_development")
    by = dict(recs)
    bdo = [d for _, d in recs if d["level"] == "block"]
    assert len(recs) == 68 and len(bdo) == 45 and all(d["lgd_block_code"] and d["district_code"] for d in bdo)
    assert all(d["district_code"] for _, d in recs)
    d = by["dept:sub4_ml_mcs:bdo:umsning"]
    assert (d["name"], d["charge_date"], d["lgd_block_code"], d["district_code"], d["post"]) == \
        ("Andrew L. Myrthong", "2024-06-27", "2470", "276", "Block Development Officer")
    d = by["dept:sub4_ml_mcs:bdo:mawlai"]
    assert d["charge_report_pending"] is True and "charge_date" not in d and d["src_url"].endswith("?page=1")
    d = by["dept:sub4_ml_mcs:sdo:ranikor"]
    assert d["in_charge"] is True and d["district_code"] == "658" and d["level"] == "subdivision"
    assert by["dept:sub4_ml_mcs:bdo:selsella"]["lgd_block_code"] == "2480"          # "Selsella" in the list
