"""cforms/pri_ga.py: Goa village panchayat ward members and Zilla Panchayat members from the Goa SEC winners PDFs
(fixtures saved 2026-11-13 from sec.goa.gov.in). Puducherry has no elected panchayats (no reader: see seeds/pri_py.json)."""
import json
from pathlib import Path

from cforms import pri_ga

DATA = Path(__file__).parent / "data" / "pri_ga"
SEEDS = Path(__file__).parent.parent / "seeds"
B = "https://sec.goa.gov.in/elections/previous/"


class R:
    def __init__(self, content=b"", text=""):
        self.content, self.text = content, text


def run(name, **p):
    body = (DATA / name).read_bytes()
    return pri_ga.fetch({"kind": "form-pri_ga", "state": "GA", "url": "https://sec.goa.gov.in/x/" + name, **p},
                        lambda url, **k: R(body))


def test_vp_taluka_file():
    recs, files, why = run("TISWADIWC.pdf", level="gp", taluka="Tiswadi", district="North Goa", election="Goa SEC 2022",
                           poll_year="2022")
    assert why == "" and len(recs) == 153 and len({r for r, _ in recs}) == 153
    rid, d = recs[0]
    assert rid == "pri:GA:gp:254363:w1" and d["type"] == "pri_member" and d["body"] == "Azossim-Mandur"
    assert d["name"] == "TEJASWI CHADRAKANT NAIK" and d["category"] == "Women" and d["votes"] == "144"
    assert d["votes_pct"] == "34.53%" and d["district"] == "North Goa" and d["block"] == "Tiswadi" and d["post"] == "Panch"
    assert d["src_pos"]["page"] == 1 and d["src_url"].endswith("TISWADIWC.pdf")
    bodies = {d["body"] for _, d in recs}
    assert len(bodies) == 18 and all(d["lgd_code"] for _, d in recs)       # aliases cover Siridao-Palem, St.Andre ...


def test_vp_unopposed_and_groups():
    recs, _, _ = run("pernem3.pdf", level="gp", taluka="Pernem", poll_year="2022")
    by = {(d["body"], d["ward_no"]): d for _, d in recs}
    assert len(recs) == 17 and by[("Alorna", "1")]["unopposed"] is True and by[("Alorna", "1")]["name"] == "VINOD YESHWANT HARIJAN"
    assert by[("Chandel-Hassapur", "3")]["name"] == "TULSIDAS VASUDEV GAWAS" and by[("Chandel-Hassapur", "3")]["lgd_code"] == "254386"
    recs, _, _ = run("taleigao.pdf", level="gp", poll_year="2024")
    assert len(recs) == 11 and recs[0][1]["name"] == "Siddhi Rajendra Kerkar" and recs[0][1]["unopposed"] is True
    assert recs[1][1]["name"] == "Agnelo Cirilo Santana Da Cunha" and recs[1][1]["votes"] == "1403"


def test_bye_election_id():
    recs, _, _ = run("taleigao.pdf", level="gp", poll_year="2026", bye=True)
    assert recs[0][0].endswith(":w1-bye2026") and recs[0][1]["bye_election"] is True


def test_zp_file():
    recs, _, why = run("winning-north.pdf", level="zp", district="North Goa", poll_year="2025")
    assert why == "" and len(recs) == 25
    by = {d["ward_no"]: d for _, d in recs}
    assert recs[0][0] == "pri:GA:zp:506:w1" and by["1"]["name"] == "RADHIKA UDAY PALYEKAR" and by["1"]["party"] == "Independent"
    assert by["2"]["party"] == "Maharashtrawadi Gomantak" and by["3"]["name"] == "SHRIKRISHNA RAVINDRA HARMALKAR"
    assert by["13"]["constituency"] == "Penha-de-Franca" and by["13"]["votes"] == "7511"
    assert by["14"]["party"] == "Revolutionary Goans Party" and by["14"]["category"] == "OBC Women"


def test_items_from_pages():
    pages = {B + "village-panchayat/": "prev_vp.html", B + "zilla-panchayat/": "prev_zp.html",
             B + "village-panchayat/general-election-to-186-village-panchayat-2022/": "vp2022.html",
             B + "village-panchayat/general-election-to-three-village-panchayats-of-pernem-taluka/": "vp_pernem3.html",
             B + "zilla-panchayat/general-election-to-zilla-panchayat-2025/": "zp2025.html"}
    asked = []

    def get(url, **k):
        asked.append(url)
        return R(text=(DATA / pages[url]).read_text(encoding="utf-8")) if url in pages else None
    it = pri_ga.items(get)
    urls = [i["payload"]["url"] for i in it]
    assert "https://sec.goa.gov.in/assets/media/docs/general-election-to-186-village-panchayat-2022/TISWADIWC.pdf" in urls
    assert len([u for u in urls if u.endswith("WC.pdf")]) == 12 and sum(i["payload"]["level"] == "zp" for i in it) == 2
    assert any(u.endswith("three-village-panchayats-of-pernem-taluka/winning-candidates.pdf") for u in urls)
    assert not any("2017-vp" in a or "zp-2020" in a for a in asked)        # rounds replaced by later polls are not read


def test_seeds():
    items = json.loads((SEEDS / "pri_ga.json").read_text())
    assert items[0]["payload"]["kind"] == "seed" and len({i["key"] for i in items}) == len(items)
    for i in items[1:]:
        p = i["payload"]
        assert p["kind"] == "form-pri_ga" and p["state"] == "GA" and p["url"].startswith("https://sec.goa.gov.in/assets/")
        assert p["level"] in ("gp", "zp") and p["route"] == "direct" and p["poll_year"]
    py = json.loads((SEEDS / "pri_py.json").read_text())
    assert py == []
