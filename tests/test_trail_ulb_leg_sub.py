"""Source trail of the town body (ulb_*, ulb2_*), legislator (leg_*) and sub-division (sub_*, sub2_*, sub3_*) readers: every
record that these readers make in their own offline tests (tests/test_ulb*.py, test_leg*.py, test_sub*.py, on the saved answers in
tests/data/) carries a position in its source ("src_pos"), and the module has a METHOD.
The check runs those tests again with dforms._esw.record watched: every reader record goes through it (_ulb.record and
_leg.member call it)."""
import importlib
import inspect
import pkgutil
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))

MINE = re.compile(r"^(ulb|ulb2|leg|sub|sub2|sub3)_")
NOT_MINE = {"sub2_rj_bdo", "sub2_gj", "sub3_mh_aero"}
TESTS = ["test_ulb_ap", "test_ulb_ar", "test_ulb_as", "test_ulb_ga", "test_ulb_gj", "test_ulb_hr", "test_ulb_jh", "test_ulb_jk",
         "test_ulb_kl", "test_ulb_mh", "test_ulb_pb", "test_ulb_py", "test_ulb_rj", "test_ulb_tn", "test_ulb_uk",
         "test_ulb_up", "test_ulb2", "test_leg", "test_leg_more", "test_leg_nw", "test_leg_se", "test_sub", "test_sub_ar",
         "test_sub_as", "test_sub_la", "test_sub_ml", "test_sub_od", "test_sub2", "test_sub3"]


def readers():
    import dforms
    return sorted(m.name for m in pkgutil.iter_modules(dforms.__path__) if MINE.match(m.name) and m.name not in NOT_MINE)


def test_every_reader_has_a_method():
    for name in readers():
        m = importlib.import_module("dforms." + name)
        if hasattr(m, "fetch") or hasattr(m, "read"):
            assert getattr(m, "METHOD", ""), name


@pytest.fixture(scope="module")
def made():
    return collect()


def collect():
    """(module, record) for every record the readers' own tests make."""
    from dforms import _esw
    seen = []
    orig = _esw.record

    def spy(module, key, **f):
        rid, d = orig(module, key, **f)
        seen.append((module, d))
        return rid, d
    _esw.record = spy
    try:
        for t in TESTS:
            try:
                tm = importlib.import_module(t)
            except ImportError:
                continue
            for n, fn in vars(tm).items():
                if n.startswith("test_") and callable(fn) and not inspect.signature(fn).parameters:
                    try:
                        fn()
                    except Exception:        # a test of another fork's work in progress: its records still count
                        pass
    finally:
        _esw.record = orig
    return seen


def test_records_carry_src_pos(made):
    # records that a test builds with a helper and a made-up source ("u", "https://x") are not reader output
    mine = [(m, d) for m, d in made if MINE.match(m) and m not in NOT_MINE and str(d.get("source", "")).startswith("http")
            and d.get("source") not in ("https://x", "http://x")]
    assert len(mine) > 1000
    missing = {}
    for m, d in mine:
        if not d.get("src_pos"):
            missing[m] = missing.get(m, 0) + 1
    assert not missing, sorted(missing.items())


def test_pdf_positions_are_pages_and_lines(made):
    by = {}
    for m, d in made:
        by.setdefault(m, []).append(d)
    for m in ("ulb_up", "ulb_jk", "ulb2_br", "ulb2_mp", "leg_dl", "leg_mp", "sub_ar"):
        pdf = [d["src_pos"] for d in by.get(m, []) if "page" in (d.get("src_pos") or {})]
        if not pdf:
            continue
        assert all(isinstance(p["page"], int) and p["page"] >= 1 and p["line"] >= 1 and p["line_text"].strip() for p in pdf), m


def test_items_with_several_answers_name_the_answer(made):
    """Readers whose item reads more than one answer say which one each record came from: src_url, and src_sha256 where one url
    gives several answers (ASP.NET GET + POST)."""
    by = {}
    for m, d in made:
        by.setdefault(m, []).append(d)
    fetched = 0
    for m in ("sub2_mp_ero", "sub2_cg", "sub2_up_prd", "ulb2_jh"):           # GET then POST of the same url
        got = [d for d in by.get(m, []) if d.get("src_url")]           # made by fetch() (tests that call parse() give no src)
        fetched += len(got)
        assert all(len(d.get("src_sha256", "")) == 64 for d in got), m
    assert fetched
    gj = {d["src_url"] for d in by.get("ulb_gj", []) if d.get("src_url")}
    if gj:
        assert {"https://communi.gujarat.gov.in/Home/listofmunicipalities", "https://communi.gujarat.gov.in/Home/pramukhlist"} <= gj
    bdo = [d for d in by.get("sub3_br", []) if d.get("level") == "block" and str(d.get("source", "")).endswith(".pdf")
           and d.get("src_url")]
    assert all(d["src_url"] == d["source"] and d["src_pos"]["page"] >= 1 for d in bdo)


def test_provenance_finish_uses_the_hash():
    """A record with src_sha256 gets the src of exactly that answer, though the url gave two (GET form, POST list)."""
    import hashlib
    import provenance
    import requests

    def resp(body):
        r = requests.Response()
        r.status_code, r._content, r.url = 200, body, "https://a.gov.in/ero.aspx"
        r.headers["Content-Type"] = "text/html"
        return r
    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "dforms.sub2_mp_ero")
    form, answer = resp(b"<form>"), resp(b"<table id='Grid_ERO'>")
    t.note(form, "https://a.gov.in/ero.aspx")
    t.note(answer, "https://a.gov.in/ero.aspx", "POST", {"__EVENTTARGET": "x"})
    recs, _ = t.finish([("dept:sub2_mp_ero:MP-AC-1", {**provenance.at(answer, "https://a.gov.in/ero.aspx"),
                                                       "src_pos": {"table": 1, "row": 2}})], [])
    assert recs[0][1]["src"]["sha256"] == hashlib.sha256(b"<table id='Grid_ERO'>").hexdigest()
