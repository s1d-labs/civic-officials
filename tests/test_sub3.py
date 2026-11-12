"""Offline tests of the sub3 sub-district officer readers (dforms/sub3_*.py) on small saved answers in tests/data/sub3/.
Bihar: RDD BDO mobile list (PDF, merged district cells) and LRC circle officer list (HTML). Haryana: Who's Who District page
(Next.js flight data). Maharashtra: CEO AERO notification (scan) read from saved OCR text; no OCR runs in the tests."""
import json

from esw_common import *  # noqa: F401,F403


def _seeds(name, n):
    seeds = json.loads((ROOT / "seeds" / f"dept_sub3_{name}.json").read_text())
    assert len(seeds) == n and len({s["key"] for s in seeds}) == n
    assert all(s["key"].startswith("sub3_") for s in seeds)
    return seeds


# ---------- Bihar ----------

def test_sub3_br_seeds():
    m = mod("sub3_br")
    seeds = _seeds("br", 3)
    assert seeds == m.items()
    assert all(s["payload"]["india_only"] is True and s["payload"]["state"] == "BR" for s in seeds)
    assert {s["payload"]["kind"] for s in seeds} == {"bdo", "co", "dclr"}


def test_sub3_br_bdo_pdf_merged_districts():
    m = mod("sub3_br")
    rows = m.pdf_rows((DATA / "sub3" / "br_bdo_pages.pdf").read_bytes())   # pages 1, 5, 12, 13 of the 13-page list
    by = {r["mobile"]: r for r in rows}
    assert len(rows) == 156 and all(r["district"] and r["area"] and r["post"] == "BDO" for r in rows)
    # Excel overflow: "SONBHADRA BANSI" / "SURYAPUR" runs over the next row (Aurangabad)
    assert by["9031071341"]["area"] == "SONBHADRA BANSI SURYAPUR" and by["9031071341"]["district"] == "ARWAL"
    assert by["9031071345"]["area"] == "AURANGABAD" and by["9031071345"]["district"] == "AURANAGABAD"
    # page 5: no rule between the Katihar and Khagaria cells
    assert by["9031071561"]["district"] == "KATIHAR" and by["9031071567"]["district"] == "KHAGARIA"
    # page 13: the last Siwan rows sit above the Supaul cell, the Siwan label is on page 12
    assert by["9031071993"]["district"] == "SIWAN" and by["9031071996"]["district"] == "SUPAUL"
    recs = dict(m.build("bdo", rows, "https://x/bdo.pdf"))
    d = recs["dept:sub3_br:bdo:aurangabad:aurangabad"]
    assert (d["dept"], d["level"], d["post"], d["phone"], d["district_code"]) == \
        ("rural_development", "block", "Block Development Officer", "9031071345", "189")


def test_sub3_br_bdo_fetch():
    m = mod("sub3_br")
    p = {s["payload"]["kind"]: s["payload"] for s in m.items()}["bdo"]
    pdf = "https://betastate.bihar.gov.in/file_2/FileUpload/2026/Oct/09-Oct-2026/9/DyPage/ab30439c-3747-483f-84f5-4ad0cb714f82.pdf"
    get = fake_get({p["url"]: "sub3/br_rdd_bdo_page.html", pdf: "sub3/br_bdo_pages.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and [u for _, u, _ in get.calls] == [p["url"], pdf]
    assert [f[0] for f in files] == ["depts/sub3_br/bdo.html.gz", "depts/sub3_br/bdo.pdf"]
    check_records(recs, "sub3_br", "rural_development")
    assert len(recs) == 156 and all(d["source"] == pdf and d["state"] == "BR" for _, d in recs)


def test_sub3_br_circle_officers():
    m = mod("sub3_br")
    p = {s["payload"]["kind"]: s["payload"] for s in m.items()}["co"]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "sub3/br_co_list.html"}))
    assert why == "" and len(files) == 1
    check_records(recs, "sub3_br", "revenue")
    d = dict(recs)
    a = d["dept:sub3_br:co:araria:araria-sadar"]
    assert (a["area"], a["post"], a["phone"], a["level"], a["district_code"]) == \
        ("Araria Sadar", "Circle Officer", "9031672256", "subdistrict", "188")
    assert d["dept:sub3_br:co:pashchim-champaran:chanpatia"]["area"] == "Chanpatia"      # "Circle Officer,Chanpatia"
    assert len(recs) == 7


def test_sub3_br_names_and_no_answer():
    m = mod("sub3_br")
    assert m.district("AURANAGABAD") == ("Aurangabad", "189") and m.district("East Champaran") == ("Purbi Champaran", "213")
    assert m.district("KAIMUR (BHABUA)") == ("Kaimur (Bhabua)", "200") and m.district("Purnea") == ("Purnia", "214")
    assert m.split_post("Circle Officer, Araria Sadar", "") == "Araria Sadar" and m.split_post("DCLR,Sadar Araria", "") == "Sadar Araria"
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


# ---------- Haryana ----------

def test_sub3_hr_flight_data():
    m = mod("sub3_hr")
    assert _seeds("hr", 1) == m.items() and m.items()[0]["payload"]["india_only"] is True
    # the decoder on the state Who's Who page (same site, same flight data, filled)
    lists = m.initial_data((DATA / "sub3" / "hr_state_whoiswho.html").read_text())
    assert [len(x) for x in lists] == [4] and lists[0][0]["name"] == "Dr. Sumita Misra, IAS"
    assert lists[0][0]["phone"] == "\t0172-2711925"
    # the district page on 2026-11-11: the list is empty
    p = m.items()[0]["payload"]
    recs, files, why = m.fetch(p, fake_get({p["url"]: "sub3/hr_district_whoiswho.html"}))
    assert recs == [] and len(files) == 1 and why == "the page lists no officers (initialData is empty)"


def test_sub3_hr_posts():
    m = mod("sub3_hr")
    # entries in the shape the page's component reads (officerId, officer_Name, designationName, email, district_Name)
    entries = [{"officerId": 1, "officer_Name": "A B", "designationName": "Tehsildar, Panipat", "email": "thpnp[at]hry[dot]nic[dot]in",
                "district_Name": "PANIPAT"},
               {"officerId": 2, "officer_Name": "C D", "designationName": "Naib Tehsildar Israna", "district_Name": "Panipat"},
               {"officerId": 3, "officer_Name": "E F", "designationName": "SDO(C) Gohana", "district_Name": "Sonepat"},
               {"officerId": 4, "officer_Name": "G H", "designationName": "District Revenue Officer", "district_Name": "Mewat"},
               {"officerId": 5, "officer_Name": "I J", "designationName": "Naib Tehsildar (Election)", "district_Name": "Mewat"}]
    d = dict(m.build(entries, "u"))
    assert sorted(d) == ["dept:sub3_hr:nuh:naib-tehsildar:nuh", "dept:sub3_hr:panipat:naib-tehsildar:israna",
                         "dept:sub3_hr:panipat:tehsildar:panipat", "dept:sub3_hr:sonipat:sdm:gohana"]
    t = d["dept:sub3_hr:panipat:tehsildar:panipat"]
    assert (t["email"], t["district_code"], t["level"], t["dept"]) == ("thpnp@hry.nic.in", "71", "subdistrict", "revenue")
    s = d["dept:sub3_hr:sonipat:sdm:gohana"]
    assert (s["level"], s["dept"], s["post"]) == ("subdivision", "administration", "Sub Divisional Officer (Civil)")
    assert m.fetch(m.items()[0]["payload"], fake_get({})) == ([], [], "no answer")


# ---------- Maharashtra ----------

def _mh_pages():
    return [(2, (DATA / "sub3" / "mh_aero_p002.ocr.txt").read_text()), (40, (DATA / "sub3" / "mh_aero_p040.ocr.txt").read_text())]


def test_sub3_mh_seeds():
    m = mod("sub3_mh_aero")
    seeds = _seeds("mh", 17)                       # 7 ten-page items + 10 three-page retries of pages 10-30
    assert seeds == m.items()
    for s in seeds:
        p = s["payload"]
        assert p["open"] is True and not p.get("india_only") and p["stored"] == "civic-officials-depts-open/depts/sub3_mh_aero/aero.pdf"
    assert [(s["payload"]["first"], s["payload"]["last"]) for s in seeds][6] == (61, 70)
    assert [(s["payload"]["first"], s["payload"]["last"]) for s in seeds][7:9] == [(10, 12), (12, 14)]


def test_sub3_mh_ocr_page_timeout_falls_back(monkeypatch, tmp_path):
    """A page that runs past the limit is read again at 200 dpi / psm 6, single-threaded; a second timeout gives ""."""
    import subprocess
    m = mod("sub3_mh_aero")
    calls = []

    def run(cmd, **kw):
        calls.append((cmd[0], cmd[cmd.index("--psm") + 1] if "--psm" in cmd else cmd[2], kw.get("env", {}).get("OMP_THREAD_LIMIT")))
        if cmd[0] == "tesseract" and cmd[cmd.index("--psm") + 1] == "4":
            raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
        return subprocess.CompletedProcess(cmd, 0, "47 - Nashik", "")
    monkeypatch.setattr(m.subprocess, "run", run)
    assert m.ocr_page("a.pdf", 12, str(tmp_path)) == "47 - Nashik"
    assert calls == [("pdftoppm", "300", None), ("tesseract", "4", "1"), ("pdftoppm", "200", None), ("tesseract", "6", "1")]


def test_sub3_mh_parse_ocr():
    m = mod("sub3_mh_aero")
    rows = m.parse(_mh_pages())
    assert [r["ac_no"] for r in rows if r["serial"] == 1] == [2, 3, 4, 5, 6, 160, 161, 162, 163]
    assert len([r for r in rows if r["ac_no"] == 2]) == 12
    four = next(r for r in rows if r["ac_no"] == 3 and r["serial"] == 4)
    assert four["cell"] == "Naib Tahsildar (Election), Tahsildar Office, Nandurbar"          # wrapped cell joined
    last = next(r for r in rows if r["ac_no"] == 6 and r["serial"] == 5)
    assert last["cell"].endswith("Dhule Rural")                       # the next page's running head is not joined
    d = dict(m.build(rows, "u"))
    t = d["dept:sub3_mh_aero:AC-5:1"]                                   # OCR "Tabsildar, Sakri"
    assert (t["post"], t["area"], t["dept"], t["level"], t["ac_name"]) == ("Tahsildar", "Sakri", "revenue", "subdistrict", "Sakri")
    assert d["dept:sub3_mh_aero:AC-2:8"]["post"] == "Block Development Officer" and d["dept:sub3_mh_aero:AC-2:8"]["area"] == "Shahada"
    assert d["dept:sub3_mh_aero:AC-6:3"]["area"] == "Dhule"            # "Block Development Officer, Panchayat Samiti, Dhule"
    assert d["dept:sub3_mh_aero:AC-5:5"]["post"] == "Additional Tahsildar" and d["dept:sub3_mh_aero:AC-5:5"]["area"] == "Pimpalner"
    assert d["dept:sub3_mh_aero:AC-161:1"]["area"] == "Charkop"        # "Tahsildar, (Land and Estate Branch), M.M.R.D.A." -> AC name
    assert "dept:sub3_mh_aero:AC-2:2" not in d                         # municipal chief officers are left out
    assert len(d) == 34 and all(v["ocr"] is True and v["state"] == "MH" for v in d.values())


def test_sub3_mh_saved_ocr_text():
    m = mod("sub3_mh_aero")
    raw = "".join(f"\f### page {pg}\n{t}" for pg, t in _mh_pages())
    assert m.pages_of(raw) == _mh_pages()
