"""Offline tests of the sub4 block / sub-district readers for central India (dforms/sub4_mp_*, sub4_mh_*, sub4_goa_*) on saved
answers in tests/data/sub4/. No test touches the network."""
import json

from esw_common import *  # noqa: F401,F403


# ---------- Madhya Pradesh: CEO Janpad Panchayat (Panchayat Darpan) ----------

def test_sub4_mp_seeds():
    m = mod("sub4_mp_jp")
    seeds = json.loads((ROOT / "seeds" / "dept_sub4_mp.json").read_text())
    assert seeds == m.items() and len(seeds) == 52 and len({s["key"] for s in seeds}) == 52
    assert {m.DISTRICTS[s["payload"]["district_id"]][0] for s in seeds} >= {"667", "639", "390", "426", "399", "424"}


def test_sub4_mp_page():
    m = mod("sub4_mp_jp")
    info = m.page((DATA / "sub4" / "mp_jp_agar.html").read_text())
    assert info == {"name": "ANJALI BADOLE", "designation": "मुख्य कार्यपालन आधिकारी जनपद पंचायत", "body": "जनपद पंचायत, AGAR",
                    "address": "chhawani naka narwal road agar zila agar malwa"}


def test_sub4_mp_new_districts():
    m = mod("sub4_mp_jp")
    assert m.lgd_block("Maihar", "426") == ("784", "3975")
    assert m.lgd_block("Sausar", "399") == ("785", "3798")
    assert m.lgd_block("Hanumana", "424") == ("766", "3955")
    assert m.lgd_block("Agar", "667") == ("667", "4000")


def test_sub4_mp_fetch():
    m = mod("sub4_mp_jp")
    p = m.items()[0]["payload"]                      # district 51 Agar-Malwa
    get = fake_get({("GET", m.SEARCH): "sub4/mp_search.html", m.LIST.format("51"): "sub4/mp_jp_list_51.json",
                    ("POST", m.SEARCH): "sub4/mp_jp_agar.html"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 4 and len(files) == 5
    posts = [c for c in get.calls if c[0] == "POST"]
    assert [c[2]["ctl00$ContentPlaceHolder1$hdnLBID"] for c in posts] == ["24150", "24151", "24152", "24157"]
    assert all(c[2]["__EVENTTARGET"] == "ctl00$ContentPlaceHolder1$btnView" and c[2]["__VIEWSTATE"] for c in posts)
    check_records(recs, "sub4_mp_jp", "rural_development")
    d = dict(recs)["dept:sub4_mp_jp:51:24157"]
    assert (d["level"], d["area"], d["district"], d["district_code"], d["lgd_block_code"], d["name"], d["post"]) == \
        ("block", "Agar", "Agar-Malwa", "667", "4000", "ANJALI BADOLE", "Chief Executive Officer, Janpad Panchayat")
    assert d["src_pos"]["janpad"] == "24157" and d["src_url"] and d["src_sha256"]
