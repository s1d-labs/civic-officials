"""Source trail of the councillor readers in cforms/ (provenance.py): METHOD, src_pos and src on saved fixtures."""
import gzip
import hashlib
import json
from pathlib import Path

import provenance
from cforms import cn_hr, cw_mp, dl, gj, hr, mh, tn, tn_text, upch

DATA = Path(__file__).parent / "data"


def test_methods_name_the_engine():
    assert "Tamil font map" in tn_text.METHOD and "pdftotext" in tn_text.METHOD
    assert tn.METHOD.startswith("ocr tesseract tam")
    assert "ocr tesseract hin" in cw_mp.METHOD and "ocr tesseract hin" in upch.METHOD and "eng" in cn_hr.METHOD
    assert "guj" in gj.METHOD and "mar" in mh.METHOD


def test_tn_text_winner_line_and_bucket_copy():
    raw = gzip.decompress((DATA / "tn_text_tp_ari.txt.gz").read_bytes()).decode("utf-8")
    p = {"url": "https://tnsec.tn.gov.in/x.pdf", "type": "tp", "district_code": "1",
         "_src": provenance.file_src(b"%PDF-1", "https://tnsec.tn.gov.in/x.pdf", "proj/councillors/TN/abc.pdf")}
    recs = tn_text.records(tn_text.parse_text(raw), p)
    pages = raw.split("\f")
    for _, d in recs:
        sp = d["src_pos"]
        assert sp["page"] == d["page"] or sp["page"] >= d["page"]
        assert pages[sp["page"] - 1].splitlines()[sp["line"] - 1] == sp["line_text"]
        assert sp["line_text"].strip().startswith(sp["serial"])
        assert d["src"] == {"sha256": hashlib.sha256(b"%PDF-1").hexdigest(), "url": p["url"], "file": "proj/councillors/TN/abc.pdf"}


def test_hr_text_rows_and_grid_rows():
    text = ("   Sr. District  Name of Council   W. No  Name of Elected   Father's Name   Name of Office  Category  Political Party\n"
            "   1   Hisar     Hansi             3      Suman Bala        Ram Lal         Member          BCA       BJP\n")
    rows = hr.body_fill(hr.text_rows(text), {})
    assert rows[0]["_pos"] == {"line": 2, "line_text": text.splitlines()[1]}
    rid, d = hr.record({"url": "https://x/1.pdf"}, {}, rows[0], 4, "text layer")
    assert d["src_pos"]["page"] == 4 and d["src_pos"]["line"] == 2 and d["method"] == "pdf text (pdftotext -layout)"
    assert "_pos" not in d
    assert hr.row_pos({"row": 3, "y": 410, "conf": [88, None, 61]}) == {"row": 3, "y": 410, "conf": 61}
    rid, d = hr.record({"url": "u"}, {}, {"body": "Hansi", "ward": "3", "name": "A", "_pos": {"row": 3}}, 2, "ocr")
    assert d["src_pos"] == {"page": 2, "row": 3} and d["method"].startswith("ocr tesseract")


def test_dl_text_rows_positions():
    text = ("Sr. Ward No  Ward Name     Reservation   Name of the Councillor   Party\n"
            "1.  12       MALKA GANJ    SC WOMAN      REKHA                    BHARATIYA JANATA PARTY\n"
            "\fSr. Ward No  Ward Name     Reservation   Name of the Councillor   Party\n"
            "2.  13       SADAR         GENERAL       RAM                      AAM AADMI PARTY\n")
    pos = []
    rows = dl.text_rows(text, 1, pos)
    assert [r[-1] for r in rows] == [1, 2] and [x["line"] for x in pos] == [2, 2]
    rid, d = dl.record({"url": "u", "source": "bye2025"}, *rows[1], "text layer", pos[1])
    assert d["src_pos"] == {"page": 2, "line": 2, "line_text": text.split("\n")[3]} and d["method"] == "pdf text (pdftotext -layout)"


def test_cw_mp_table_row_positions():
    blocks = json.loads((DATA / "cw_mp_blocks_p9_p10.json").read_text())
    found = cw_mp.read_pages(blocks)
    b, m, page = found[3]
    rid, d = cw_mp.record({"url": "https://govtpress.mp.gov.in/x.pdf"}, b, m, page)
    assert d["src_pos"]["page"] == page and d["src_pos"]["table"] >= 1 and d["src_pos"]["row"] >= 1
    kinds = [kind for kind, _ in dict(blocks)[page]]
    rows = [v for kind, v in dict(blocks)[page] if kind == "rows"][d["src_pos"]["table"] - 1]
    assert m["name"].split()[0] in " ".join(rows[d["src_pos"]["row"] - 1]) and "rows" in kinds


def test_cw_dd_line_of_each_member():
    from cforms import cw_dd
    text = (DATA / "cw_dd_daman_2016.txt").read_text()
    recs = cw_dd.records(text, {"url": "u", "election": "x"}, "text layer", [text])
    lines = text.split("\n")
    for _, d in recs:
        sp = d["src_pos"]
        assert sp["page"] == 1 and lines[sp["line"] - 1] == sp["line_text"] and d["name"].split()[-1] in sp["line_text"]
        assert d["method"] == "pdf text (pypdf layout)"


def test_cw_ga_ward_heading_line():
    from cforms import cw_ga
    text = (DATA / "cw_ga_winners_sample.txt").read_text()
    recs = cw_ga.parse(text, {"url": "u"}, [text])
    assert recs and all(d["src_pos"]["page"] == 1 and text.split("\n")[d["src_pos"]["line"] - 1] == d["src_pos"]["line_text"]
                        for _, d in recs)


def test_cw_mh_sec_and_csmc_grid_rows():
    from cforms import cw_mh, cw_mh_csmc
    d = json.loads(gzip.decompress((DATA / "cw_mh_sec_members_p64.json.gz").read_bytes())) \
        if (DATA / "cw_mh_sec_members_p64.json.gz").exists() else None
    if d:
        ws, hs, vs = [tuple(w) for w in d["words"]], [tuple(h) for h in d["h"]], [tuple(v) for v in d["v"]]
        recs = cw_mh.parse_page(ws, hs, vs, {"doc": "members"}, d["page"], [])
        assert recs and all(r["src_pos"]["page"] == d["page"] and r["src_pos"]["row"] >= 1 for _, r in recs)
    d = json.loads(gzip.decompress((DATA / "cw_mh_csmc_p8.json.gz").read_bytes()))
    ws, hs, vs = [tuple(w) for w in d["words"]], [tuple(h) for h in d["h"]], [tuple(v) for v in d["v"]]
    pos = []
    rows, _ = cw_mh_csmc.parse_page(ws, hs, vs, None, "29", pos)
    assert len(pos) == len(rows) and pos[0]["row"] < pos[1]["row"] and len(pos[0]["box_pt"]) == 4


def test_cw_wb_answer_hash_and_index():
    from cforms import cw_wb
    raw = gzip.decompress((DATA / "cw_wb_res220.json.gz").read_bytes())
    prd = gzip.decompress((DATA / "cw_wb_prd220.json.gz").read_bytes())

    class R:
        def __init__(self, b):
            self.content, self.text = b, b.decode("utf-8")

    def get(url, method="GET", data=None, headers=None):
        return R(prd if url.endswith("PollResultDate") else raw)
    recs, _, _ = cw_wb.fetch({"wbme_id": 220, "lgd_code": "249958"}, get)
    d = dict(recs)["councillor:WB:249958:1"]
    assert d["src_sha256"] == hashlib.sha256(raw).hexdigest() and d["src_url"].endswith("SelectCandidateVotesinFavourPortalList")
    cands = json.loads(json.loads(raw)["d"])
    assert cands[d["src_pos"]["index"]]["CandidateName"].strip() == d["name"]


def _get(pages):
    class Resp:
        def __init__(self, text):
            self.text, self.content, self.url = text, text.encode(), ""

    def get(url, method="GET", data=None, headers=None):
        return Resp(pages[url]) if url in pages else None
    return get


def test_cp_table_rows_positions():
    from bs4 import BeautifulSoup
    from cforms import cp_common as cp, cp_od, cp_tg
    html = (DATA / "cp" / "cp_tg_dubbaka.html").read_text(encoding="utf-8")
    p = {"url": "https://dubbakamunicipality.telangana.gov.in/pages/council-page", "body": "Dubbaka", "slug": "dubbaka"}
    recs = dict(cp_tg.fetch(p, _get({p["url"]: html}))[0])
    d = recs["cp:TG:dubbaka:1"]
    tables = BeautifulSoup(html, "lxml").find_all("table")
    tr = tables[d["src_pos"]["table"] - 1].find_all("tr")[d["src_pos"]["row"] - 1]
    assert "Mallaipally" in tr.get_text(" ") and d["src_url"] == p["url"] and cp_tg.METHOD == "html table"
    assert cp.tr_pos(tr) == d["src_pos"]
    seed = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_cp_od.json").read_text())[0]["payload"]
    recs, _, _ = cp_od.fetch(seed, _get({seed["url"]: (DATA / "cp" / "cp_od_jharsuguda.html").read_text(encoding="utf-8")}))
    assert all(d["src_pos"]["selector"] == ".author-text" or "table" in d["src_pos"] for _, d in recs)


def test_cp_gj_vadodara_lines():
    from cforms import cp_gj
    text = (DATA / "cp" / "cp_gj_vmc_p1_layout.txt").read_text(encoding="utf-8")
    pos = []
    e = cp_gj.vmc_entries(text, pos)
    assert len(pos) == len(e) and pos[0][1].strip().startswith("1")
    assert cp_gj.page_line([text], pos[1][0], pos[1][1]) == {"page": 1, "line": pos[1][0], "line_text": pos[1][1]}
    assert cp_gj.page_line(["a\nb", "c"], 3, "c")["page"] == 2


def test_city_records_name_source_and_place():
    from cforms import city
    html = ("<table><tr><td>menu</td></tr></table><table><tr><th>Ward No.</th><th>Name of Corporator</th><th>Contact Number</th></tr>"
            "<tr><td>1</td><td>A B (Mayor)</td><td>9436123456</td></tr><tr><td>2</td><td>C D</td><td>9436000111</td></tr></table>")
    p = {"source": "agartala", "url": "https://amc.tripura.gov.in/c", "state": "TR", "slug": "agartala", "body": "Agartala MC"}
    recs = dict(city.fetch(p, _get({p["url"]: html}))[0])
    d = recs["councillor:TR:agartala:2"]
    assert d["src_pos"] == {"table": 2, "row": 3} and d["method"] == "html table"
    wiki = json.dumps({"parse": {"title": "X", "revid": 7, "text": "<table class='wikitable'><tr><th>Ward</th><th>Councillor</th>"
                                 "<th>Party</th></tr><tr><td>Ward 4</td><td>E F</td><td>INC</td></tr></table>"}})
    p = {"source": "wikipedia", "title": "X", "state": "XX", "slug": "x", "body": "X"}
    api = "https://en.wikipedia.org/w/api.php?action=parse&prop=text%7Crevid&format=json&formatversion=2&redirects=1&page=X"

    class R:
        def __init__(self, t):
            self.text, self.content = t, t.encode()

        def json(self):
            return json.loads(self.text)
    recs = dict(city.fetch(p, lambda url, *a, **k: R(wiki) if url == api else None)[0])
    d = recs["councillor:XX:x:4"]
    assert d["src_url"] == api and d["src_pos"] == {"selector": "table.wikitable", "table": 1, "row": 2}


def test_as_od_line_positions():
    from cforms import as_, od
    pages = ["Municipal Boards of Cachar District\n1. Lakhipur Municipal Board\n3 Unreserved Abc Def BJP\n"]
    rows = as_.gazette_rows(["duly elected from the Wards"] + pages, {})
    assert rows[0][2]["src_pos"] == {"page": 2, "line": 3, "line_text": "3 Unreserved Abc Def BJP"}

    class Page:
        def extract_text(self, **k):
            return "x\n12 KHORDHA JATNI WARD 3 Unreserved Ram Das Biju Janata Dal\n"

    class Reader:
        pages = [Page()]
    rows = od.list_rows(Reader(), {})
    assert rows[0][2]["src_pos"]["line"] == 2 and rows[0][2]["name"] == "Ram Das"


def test_cr_up_rows_and_page_answer():
    from cforms import cr_up
    html = (DATA / "cr_up_sec_winners.html").read_text(encoding="utf-8")
    rows = cr_up.winners(html)
    recs = dict(cr_up.records(rows, "8"))
    d = recs["councillor:UP:249062:7"]
    assert d["src_pos"]["table_id"] == "ctl00_ContentPlaceHolder1_winnerdetail" and d["src_pos"]["row"] >= 2
    assert "_pos" not in d and "html table" in cr_up.METHOD


def test_cr_body_and_ce_ne_table_rows():
    from bs4 import BeautifulSoup
    from cforms import ce_ne, cr_body
    html = (DATA / "cr_body_gj_chanasma.html").read_text(encoding="utf-8")
    p = {"state": "GJ", "slug": "chanasma", "body": "Chanasma", "url": "https://chanasmanagarpalika.org/Members_List.html"}
    d = dict(cr_body.records(html, p))["councillor:GJ:chanasma:6"]
    tr = BeautifulSoup(html, "lxml").find_all("table")[d["src_pos"]["table"] - 1].find_all("tr")[d["src_pos"]["row"] - 1]
    assert "પ્રતીક્ષાબેન" in tr.get_text(" ")
    html = (DATA / "ce_mz_aizawl.html").read_text(encoding="utf-8")
    pos = []
    rows = ce_ne.amc_rows(html, pos)
    assert len(pos) == len(rows) and pos[0]["row"] < pos[1]["row"]


def test_cw_mh_city_list_cell_and_detail():
    from cforms import cw_mh_city
    routes = {"https://www.pcmcindia.gov.in/corporator-details?Id=288": "cw_mh_pcmc_288.html",
              "https://www.pcmcindia.gov.in/corporator": "cw_mh_pcmc_list.html"}

    class A:
        def __init__(self, path):
            self.content = (DATA / path).read_bytes()
            self.text = self.content.decode("utf-8")
    recs = dict(cw_mh_city.fetch({"site": "pcmc"}, lambda url, *a, **k: A(routes[url]) if url in routes else None)[0])
    r = recs["councillor:MH:pimpri-chinchwad-mc:2-अ"]
    assert r["src_url"] == cw_mh_city.SITES["pcmc"]["url"] and r["src_pos"]["col"] == 2
    assert r["src_pos"]["detail_page"].endswith("Id=288")
    assert "detail_page" not in recs["councillor:MH:pimpri-chinchwad-mc:32-ड"]["src_pos"]


def test_aspnet_readers_name_the_answer_by_hash():
    from cforms import tg
    a = ("<table id='GridView1'><tr><td>WARD Name : 1, Reserved for : GEN</td></tr>"
         "<tr><td>1</td><td>A</td><td>INC</td><td>10</td><td>Won</td></tr><tr><td>2</td><td>B</td><td>BJP</td><td>5</td><td></td></tr></table>")

    class R:
        def __init__(self, t):
            self.text, self.content = t, t.encode()
    tok = '<input name="org.apache.struts.taglib.html.TOKEN" value="t1">'

    def get(url, method="GET", data=None, headers=None):
        return R(tok if method == "GET" else a)
    recs, _, why = tg.fetch({"district_id": "1", "ulb_id": "2", "ulb": "X"}, get)
    if recs:
        d = recs[0][1]
        assert d["src_pos"] == {"table_id": "GridView1", "row": 2} and d["src_sha256"] == hashlib.sha256(a.encode()).hexdigest()
