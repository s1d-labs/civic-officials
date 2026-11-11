"""forms/blo2_ocr.py (scanned BLO lists by OCR) and the PDF saving of forms/blo2_pdf.py, on saved OCR results in
tests/data/blo2/ocr_*.json (page_table output of real pages): no network, no Tesseract."""
import gzip
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import blo  # noqa: E402
from forms import blo2_ocr, blo2_pdf  # noqa: E402

DATA = Path(__file__).parent / "data" / "blo2"


def ocr(name):
    d = json.loads((DATA / name).read_text(encoding="utf-8"))
    return d["pages"], d["payload"]


def by_part(rows):
    return {r["part_no"]: r for r in rows}


def test_manipur_english_scan():
    pages, p = ocr("ocr_mn_thangmeiband.json")
    rows = blo2_ocr.parse(pages, p)
    assert [r["part_no"] for r in rows] == list(range(1, 43))     # "9/ 1" read as "9/4", "97", "9112": all fixed by order
    r = by_part(rows)
    assert (r[1]["blo_name"], r[1]["blo_phone"]) == ("Thingom lboyaima Singh", "9862014812")
    assert r[1]["station"].startswith("Sinam Nodiya Upper Primary School") and r[1]["designation"] == "Primary Teacher"
    assert r[11]["cells"]["_part_inferred"] is True and r[11]["blo_name"] == "N. Basanta Singh"
    assert r[27]["blo_phone"] == ""          # "§774678307": 9 digits, not taken
    assert all(x["ocr"] and x["ac_no"] == 9 and x["district"] == "Imphal West" for x in rows)
    assert sum(1 for x in rows if x["blo_phone"]) == 41


def test_up_hindi_scan_names_and_two_readings_of_mobiles():
    pages, p = ocr("ocr_up_farrukhabad_193_p1.json")
    r = by_part(blo2_ocr.parse(pages, p))
    assert sorted(r) == list(range(1, 24))
    assert (r[1]["blo_name"], r[1]["blo_phone"]) == ("मंजू सिंह", "7985745141")
    assert r[2]["blo_phone"] == "9793125695"          # only the digits-only reading has it
    assert r[9]["blo_phone"] == ""                    # the two readings disagree (9793328386 / 9793328336): left empty
    assert r[5]["blo_name"] == "" and r[5]["cells"]["_name_incomplete"] == "पालीवाल"   # a word was not read
    assert r[7]["blo_name"] == "पप्पू उर्फ शिशुपाल सिंह" and r[7]["designation"] == "शिक्षा मित्र"
    assert r[1]["station"].startswith("प्राइमरी पाठशाला")


def test_bihar_drawn_page_name_and_post_in_one_cell():
    pages, p = ocr("ocr_br_rohtas_213_p1.json")
    r = by_part(blo2_ocr.parse(pages, p))
    assert sorted(r) == list(range(1, 9))
    assert [r[k]["blo_phone"] for k in (1, 5, 8)] == ["7870179940", "9572225930", "9801427881"]
    assert (r[1]["blo_name"], r[1]["designation"]) == ("शान्ति देवी", "सेविका")
    assert (r[2]["blo_name"], r[2]["designation"]) == ("शुभद्रा देवी", "सेविका")     # no comma: the post word ends the cell
    assert r[4]["blo_name"] == "राकेश कुमार"


def test_two_rows_in_one_cell_are_dropped():
    pages, p = ocr("ocr_mn_naoriya_p1_merged_row.json")
    rows = blo2_ocr.parse(pages, p)
    assert 12 not in by_part(rows) and 13 not in by_part(rows)
    assert by_part(rows)[14]["blo_name"] == "Sagolsem Asha Devi"


def test_rules():
    assert blo2_ocr.phone_pick("9793125695", "") == "9793125695"
    assert blo2_ocr.phone_pick("9793328336", "9793328386") == ""
    assert blo2_ocr.phone_pick("3129298035", "") == ""
    assert blo2_ocr.phone_pick("", "+91 98620 14812") == "9862014812"
    assert blo2_ocr.phone_pick("930522897]", "") == "9305228971"
    assert blo2_ocr.part_cands("9/ 12", 9) == [12]
    assert blo2_ocr.part_cands("9112", 9) == [12, 112, 9112]
    assert blo2_ocr.part_cands("gf 22", 9) == [22]
    assert blo2_ocr.part_cands("21/13", None) == [13]
    assert blo2_ocr.clean_name("var पालीवाल") == ("पालीवाल", False)
    assert blo2_ocr.clean_name("Th. Geetabali Devi") == ("Th. Geetabali Devi", True)
    vals, inf = blo2_ocr.pick_parts([{4: 2, 1: 2}, {2: 3, 6: 1}, {3: 2}, {14: 1, 41: 2}, {5: 2}])
    assert vals == [1, 2, 3, 4, 5] and inf == [False, False, False, True, False]
    assert blo2_ocr.labels(["Sl. No", "Part No.", "Building in which Polling Station will be located", "Name of the BLO",
                            "Designation", "Mobile No."]) == {0: "serial", 1: "part_no", 2: "station", 3: "blo_name",
                                                               4: "designation", 5: "blo_phone"}
    assert blo2_ocr.labels(["बुध संख्या", "बूथ का नाम", "बूथ लेबिल अधिकारी का नाम", "बूथ लेबिल अधिकारी का पद नाम", "मोबाइल"]) == \
        {0: "part_no", 1: "station", 2: "blo_name", 3: "designation", 4: "blo_phone"}
    assert blo2_ocr.lang_of({"state": "UP"}) == "hin+eng" and blo2_ocr.lang_of({"state": "MN"}) == "eng"
    assert blo2_ocr.lang_of({"state": "UP", "lang": "hin"}) == "hin"


def test_straighten_a_tilted_line():
    w, h = 400, 200
    img = bytearray(b"\xff" * (w * h))
    for x in range(20, 380):                       # a rule with slope 0.02 (about 1.1 degrees)
        y = int(100 + 0.02 * (x - 200))
        for t in range(2):
            img[(y + t) * w + x] = 0
    s = blo2_ocr.skew(w, h, bytes(img), step=1)
    assert abs(s - 0.02) < 0.003
    out = blo2_ocr.straighten(w, h, bytes(img), s)
    ys = {y for y in range(h) for x in (40, 360) if out[y * w + x] < 128}
    assert max(ys) - min(ys) <= 3


class Hub:
    def __init__(self, files):
        self.files, self.asked = files, []

    def read_urls(self, target, keys):
        self.asked.append((target, list(keys)))
        return {k: "https://bucket/" + k for k in keys if k in self.files}


class Resp:
    def __init__(self, content, status=200):
        self.content, self.status_code = content, status

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(self.status_code)


PDF = b"%PDF-1.4 scanned"


def test_read_uses_the_saved_copy_and_keeps_the_ocr_text(monkeypatch):
    pages, p = ocr("ocr_mn_thangmeiband.json")
    p = {**p, "kind": "form-blo2_ocr", "stored": ["civic-officials-blo2-in/blo/MN/abc.pdf"]}
    monkeypatch.setattr(blo2_ocr, "tools", lambda lang: True)
    monkeypatch.setattr(blo2_ocr, "ocr_pages", lambda content, lang, first=1, last=None: pages)
    monkeypatch.setattr(blo2_ocr.requests, "get", lambda url, timeout=None: Resp(PDF))
    monkeypatch.delenv("SCRAPE_POOL_PROJECT", raising=False)

    class Site:
        def get(self, url, timeout=None):
            raise AssertionError("the site must not be asked when a saved copy exists")
    hub = Hub({"civic-officials-blo2-in/blo/MN/abc.pdf"})
    rows, files, why = blo2_ocr.read(Site(), p, hub)
    assert why == "" and len(rows) == 42 and hub.asked[0] == ("civic-officials-blo2-in", ["civic-officials-blo2-in/blo/MN/abc.pdf"])
    assert [f[0] for f in files] == [blo2_pdf.store_path(p)[:-4] + ".ocr.json.gz"]       # no second copy of the PDF
    raw = json.loads(gzip.decompress(files[0][1]))
    assert raw["lang"] == "eng" and raw["pages"][0]["rows"][1][3] == "Thingom lboyaima Singh"


def test_read_fetches_once_when_nothing_is_saved(monkeypatch):
    pages, p = ocr("ocr_up_farrukhabad_193_p1.json")
    p = {**p, "kind": "form-blo2_ocr", "stored": ["civic-officials-blo2/blo2/UP/x.pdf"]}
    monkeypatch.setattr(blo2_ocr, "tools", lambda lang: True)
    monkeypatch.setattr(blo2_ocr, "ocr_pages", lambda content, lang, first=1, last=None: pages)
    monkeypatch.setenv("SCRAPE_POOL_PROJECT", "civic-officials-blo2-ocr")
    hub = Hub(set())

    class Site:
        n = 0

        def get(self, url, timeout=None):
            Site.n += 1
            return Resp(PDF)
    rows, files, why = blo2_ocr.read(Site(), p, hub)
    assert Site.n == 1 and why == "" and len(rows) == 23
    assert [k for _, ks in hub.asked for k in ks] == ["civic-officials-blo2/blo2/UP/x.pdf",
                                                       "civic-officials-blo2-ocr/" + blo2_pdf.store_path(p)]
    assert files[0] == (blo2_pdf.store_path(p), PDF, "application/pdf") and files[1][0].endswith(".ocr.json.gz")


def test_blo_dispatch_carries_ocr_flag_and_files(monkeypatch):
    pages, p = ocr("ocr_mn_thangmeiband.json")
    monkeypatch.setattr(blo2_ocr, "tools", lambda lang: True)
    monkeypatch.setattr(blo2_ocr, "ocr_pages", lambda content, lang, first=1, last=None: pages)
    monkeypatch.setattr(blo2_ocr.requests, "get", lambda url, timeout=None: Resp(PDF))

    def get(m, u, d):
        raise AssertionError("no site request")
    get.hub = Hub({"civic-officials-blo2-in/blo/MN/abc.pdf"})
    item = {"key": "k", "payload": {**p, "kind": "form-blo2_ocr", "stored": "civic-officials-blo2-in/blo/MN/abc.pdf"}}
    recs, files, why = blo.run(item, get)
    assert why == "" and len(recs) == 42 and len(files) == 1
    rid, d = recs[0]
    assert rid == "blo:MN:9:1" and d["ocr"] is True and d["page"] == 1 and d["blo_phone"] == "9862014812"


def test_blo2_pdf_saves_every_pdf_and_names_scans():
    from pypdf import PdfWriter
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)

    class S:
        def get(self, url, timeout=None):
            return Resp(buf.getvalue())
    p = {"url": "https://cdn.s3waas.gov.in/x.pdf", "state": "UP", "kind": "form-blo2_pdf"}
    rows, files, why = blo2_pdf.read(S(), p)
    assert rows == [] and why.startswith("scanned") and files == [(blo2_pdf.store_path(p), buf.getvalue(), "application/pdf")]
    assert blo2_pdf.store_path(p).startswith("blo2/UP/") and blo2_pdf.store_path(p).endswith(".pdf")


def test_seed_and_project():
    import family
    items = json.loads((ROOT / "seeds" / "blo2ocr.json").read_text(encoding="utf-8"))
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) and items
    for i in items:
        pl = i["payload"]
        assert pl["kind"] == "form-blo2_ocr" and pl["url"].startswith("https://cdn.s3waas.gov.in/")
        assert pl["stored"][0].startswith(("civic-officials-blo2/blo2/", "civic-officials-blo2-in/blo/MN/"))
    pj = [x for x in family.PROJECTS if x["name"] == "civic-officials-blo2-ocr"][0]
    assert pj["task"] == "blo2-ocr" and not pj.get("geo") and not pj.get("proxy") and len(pj["items"]) == len(items)
    assert json.loads((ROOT / "scrape.json").read_text())["tasks"]["blo2-ocr"] == ["python", "blo.py"]
