"""Parsing tests on saved pages (tests/pages): S3WaaS Who's Who tables, the pager's inputs, and one ww_pages answer."""
from pathlib import Path

from officials import ajax_rows, candidate_links, deobfuscate, normalise, pager_blocks, tables

PAGES = Path(__file__).parent / "pages"


def read(name):
    return (PAGES / name).read_text(encoding="utf-8", errors="replace")


def test_deobfuscate():
    assert deobfuscate("dcurban[at]nic[dot]in") == "dcurban@nic.in"
    assert deobfuscate("deo[dot]bangaloreu[at]gmail[dot]com") == "deo.bangaloreu@gmail.com"
    assert deobfuscate("so[hyphen]holagarh[dot]ah[at]nic[dot]in") == "so-holagarh.ah@nic.in"


def test_tables_bengaluru():
    ts = tables(read("bengaluruurban_whoswho.html"))
    assert ts[0]["caption"] == "Deputy Commissioner"
    row = normalise(ts[0]["rows"][0])
    assert row["name"].startswith("Shri. P.S.Kantharaju")
    assert row["designation"].startswith("Deputy Commissioner")
    assert row["email"] == "dcurban@nic.in"
    assert row["phone"] == "080-22211292"


def test_pager_patna():
    pg = pager_blocks(read("patna_whoswho.html"), "ww")
    assert pg["action"] == "ww_pages" and pg["nonce"] and pg["ajaxurl"].endswith("admin-ajax.php")
    names = [b["name"] for b in pg["blocks"]]
    assert "District Administration" in names
    assert max(b["pages"] for b in pg["blocks"]) > 1
    assert pager_blocks(read("patna_whoswho.html"), "dir") is None


def test_ajax_rows():
    rows = ajax_rows(read("patna_ww_pages.json"))
    assert rows and all(normalise(r).get("designation") for r in rows)
    assert any(normalise(r).get("email", "").endswith("@nic.in") for r in rows)


def test_candidate_links():
    links = candidate_links(read("patna_whoswho.html"), "https://patna.nic.in/", "patna.nic.in")
    assert any("whos-who" in u for u in links)
