"""cforms/pri_mh.py: Maharashtra ZP office bearers, ZP members and panchayat samiti chairpersons from Zilla Parishad websites
(fixtures: www.punezp.gov.in, zpnagpur.maharashtra.gov.in, zpkolhapur.gov.in, fetched 2026-11-13)."""
import json
from pathlib import Path

import councillors
from cforms import pri_mh

D = Path(__file__).parent / "data" / "pri_mh"
P = {"kind": "form-pri_mh", "state": "MH", "district": "Pune", "lgd_code": "446", "url": "https://www.punezp.gov.in/", "pages": []}


def page(name):
    return (D / name).read_text(encoding="utf-8")


def test_links_on_pune_home():
    kinds = [k for k, _, _ in pri_mh.links(page("pune_home.html"), "https://www.punezp.gov.in/")]
    assert kinds == ["bearers", "members", "ps_heads"]


def test_bearers():
    recs = dict(pri_mh.records(page("pune_bearers.html"), "u", "bearers", P))
    assert len(recs) == 6
    d = recs["pri:MH:zp:446:head"]
    assert d["type"] == "pri_member" and d["post"] == "President" and d["name"] == "विरधवल जगदाळे" and d["head_rank"] == 1
    assert d["name_as_written"].startswith("श्री.") and d["page_updated"] == "29.04.2026" and d["src_pos"]["row"] >= 2
    assert recs["pri:MH:zp:446:vice"]["post_regional"].startswith("उपाध्यक्ष")
    assert sum(1 for k in recs if ":chair-" in k) == 4


def test_members_taluka_filled_down():
    recs = dict(pri_mh.records(page("pune_members.html"), "u", "members", P))
    assert len(recs) == 73 and all(d["level"] == "zp" and d["lgd_code"] == "446" for d in recs.values())
    d = recs["pri:MH:zp:446:w2"]
    assert d["block"] == "जुन्नर" and d["ward_no"] == "2" and d["ward_name"] == "ओतूर" and d["name"] == "छाया अतुल तांबे"
    assert recs["pri:MH:zp:446:w73"]["block"] == "इंदापूर"


def test_ps_heads_matched_to_lgd():
    recs = dict(pri_mh.records(page("pune_ps_heads.html"), "u", "ps_heads", P))
    assert len(recs) == 13 and all(d["level"] == "ps" and d["head"] for d in recs.values())
    assert recs["pri:MH:ps:4872:head"]["block"] == "जुन्नर"          # Junnar
    assert "pri:MH:ps:4874:head" in recs                              # मावळ = LGD मवाळ (Maval)


def test_whoswho_officers_dropped_and_pdf_links():
    assert pri_mh.records(page("nagpur_whoswho.html"), "u", "whoswho", {"district": "Nagpur", "lgd_code": "440"}) == []
    pdfs = pri_mh.pdf_links(page("kolhapur_home.html"), "https://zpkolhapur.gov.in/")
    assert len(pdfs) == 1 and "राजपत्र" in pdfs[0][1]


def test_fetch_and_dispatch():
    pages = {"https://www.punezp.gov.in/": "pune_home.html"}
    for k, u, _ in pri_mh.links(page("pune_home.html"), "https://www.punezp.gov.in/"):
        pages[u] = {"bearers": "pune_bearers.html", "members": "pune_members.html", "ps_heads": "pune_ps_heads.html"}[k]

    class R:
        def __init__(self, url):
            self.url, self.text = url, page(pages[url])
            self.content = self.text.encode()

    recs, files, why = councillors.run({"key": "k", "payload": P}, lambda u, **kw: R(u) if u in pages else None)
    assert why == "" and files == [] and len(recs) == 6 + 73 + 13


def test_seeds():
    items = json.loads((Path(__file__).parents[1] / "seeds" / "pri_mh.json").read_text())
    assert len(items) == 34 and len({i["key"] for i in items}) == 34
    assert all(i["payload"]["kind"] == "form-pri_mh" and i["payload"]["lgd_code"] for i in items)
