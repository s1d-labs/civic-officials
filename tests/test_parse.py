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


def test_candidate_links_town_site():
    html = '<a href="/en/Engwardstaffs">Wardwise Staff Details</a><a href="/en/BLO">Booth Level Officers</a><a href="/en/tenders">Tenders</a>'
    links = candidate_links(html, "http://www.harohallitown.mrc.gov.in/", "harohallitown.mrc.gov.in")
    assert links == ["http://www.harohallitown.mrc.gov.in/en/Engwardstaffs", "http://www.harohallitown.mrc.gov.in/en/BLO"]


def test_pubutility():
    from officials import pubutility
    t = pubutility(read("patna_pubutility_municipality.html"))
    assert t and t[0]["rows"][0]["Office"] == "Patna Municipal Corporation"
    assert normalise(t[0]["rows"][0])["phone"].startswith("+91")


def test_text_people_cards():
    from officials import text_people
    rows = text_people(read("tezpur_members.html"))[0]["rows"]
    assert len(rows) >= 15
    assert rows[0] == {"Name": "Prajanoo Bhatacharjyya", "Designation": "Chairman", "Phone": "9435080593"}


def test_json_with_embedded_table():
    import json as _j
    import directory

    class R:
        status_code = 200
        content = _j.dumps({"data": [{"menuName": "<table><tr><th>Name</th><th>Mobile</th></tr><tr><td>A B</td><td>9999999999</td></tr></table>"}]}).encode()

        def json(self):
            return _j.loads(self.content)
    recs, _, _ = directory.run({"key": "k", "payload": {"url": "u", "fmt": "json"}}, lambda m, u, d: R())
    rows = [d for _, d in recs if d["type"] == "row"]
    assert rows[0]["name"] == "A B" and rows[0]["phone"] == "9999999999"


def test_rows_keep_names_and_phones_the_headers_do_not_name():
    """Full saved pages the reader audit flagged (2026-11-13). Balrampur directory: police station tables whose first row is a data
    row ("01 | Shri. Rajkumar Lehre | Inspector, SHO, Basantpur | 94791-93816") lost that row and had no fields: rows 136 -> 140,
    named 117 -> 140, with phone 104 -> 137. Bengaluru Rural police: "NAME (SRIYUTHS)" and a second phone column "DEPT ISSUED MOB
    NO.": named 0 -> 107, with phone 36 -> 84."""
    import gzip
    h = gzip.decompress((PAGES / "balrampur_directory_full.html.gz").read_bytes()).decode("utf-8")
    rows = [normalise(r) for t in tables(h) for r in t["rows"]]
    assert (len(rows), sum(1 for r in rows if r.get("name")), sum(1 for r in rows if r.get("phone"))) == (140, 140, 137)
    assert {"name": "Shri. Rajkumar Lehre", "phone": "94791-93816"}.items() <= next(
        r for r in rows if r.get("name") == "Shri. Rajkumar Lehre").items()
    h = gzip.decompress((PAGES / "bangaloreruralpolice_contact_full.html.gz").read_bytes()).decode("utf-8")
    rows = [normalise(r) for t in tables(h) for r in t["rows"]]
    assert (len(rows), sum(1 for r in rows if r.get("name")), sum(1 for r in rows if r.get("phone"))) == (131, 107, 84)
    assert rows[1]["name"] == "SRI CHANDRAKANTH.M.V - I.P.S." and rows[1]["phone"].endswith("9480802401")
