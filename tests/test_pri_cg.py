"""Offline tests of the Chhattisgarh PRI reader (dforms/pri_cg.py, SEC 2025 ZP / JP member PDFs saved 2026-11-13).
The reader needs poppler's pdftotext; the tests skip when it is missing."""
import json
import shutil

import pytest

from pri_common import DATA, ROOT, check_pri, fake_get, mod

pytestmark = pytest.mark.skipif(not shutil.which("pdftotext"), reason="needs pdftotext (poppler)")


def test_pri_cg_seeds():
    m = mod("pri_cg")
    seeds = json.loads((ROOT / "seeds" / "dept_pri_cg.json").read_text())
    assert seeds == m.items() and len(seeds) == 2 and m.METHOD
    assert {s["payload"]["level"] for s in seeds} == {"zp", "ps"}


def test_pri_cg_zila_members():
    m = mod("pri_cg")
    p = next(i["payload"] for i in m.items() if i["payload"]["level"] == "zp")
    recs, files, why = m.fetch(p, fake_get({p["url"]: "pri/cg_zp_2025.pdf"}))
    check_pri(recs, "pri_cg", "CG")
    assert why == "" and len(recs) == 433
    assert {r["serial"] for _, r in recs} == set(range(1, 434))
    d = dict(recs)
    r = d["pri:pri_cg:2025:zp:1"]
    assert r["name"] == "अनुसुईया जागेन्द्र कश्यप" and r["father_name"] == "जागेन्द्र कुमार कश्यप"     # "कु मार" joined
    assert r["district"] == "बिलासपुर" and r["block"] == "बिल्हा" and r["constituency_no"] == 1 and r["lgd_code"]
    assert r["address"] == "मुकाम व पोस्ट- गढ़वट, व्हाया रतनपुर जिला बिलासपुर" and r["src_pos"]["page"] == 1
    r = d["pri:pri_cg:2025:zp:394"]                       # constituency cell on three lines ("05 अनारक्षित महिला")
    assert r["name"] == "तिजेश्वरी सिन्हा" and r["constituency_no"] == 5 and r["constituency"] == "05 अनारक्षित महिला"
    assert len({r["district"] for _, r in recs}) == 33
    assert sum(1 for _, r in recs if r.get("lgd_code")) == 433


def test_pri_cg_janpad_members():
    m = mod("pri_cg")
    p = next(i["payload"] for i in m.items() if i["payload"]["level"] == "ps")
    recs, files, why = m.fetch(p, fake_get({p["url"]: "pri/cg_ps_2025.pdf"}))
    check_pri(recs, "pri_cg", "CG")
    assert len(recs) == 2973 and {r["serial"] for _, r in recs} == set(range(1, 2974))
    d = dict(recs)
    r = d["pri:pri_cg:2025:ps:2287"]                      # long district name over the column border
    assert r["district"] == "मोहला मानपुर अंबागढ़ चौकी" and r["block"] == "अम्बागढ़ चौकी"
    assert r["name"] == "लक्ष्मी ललित कोसारे" and r["constituency"] == "1-लाताकोड़ो" and r["constituency_no"] == 1
    assert all(r["level"] == "ps" and r["role"] == "member" for _, r in recs)
    share = sum(1 for _, r in recs if r.get("lgd_code")) / len(recs)
    assert share > 0.8, share
