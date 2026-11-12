"""SEC heads and new results, west / central states (worktree sec-new-west, 2026-11-12)."""
import gzip
import json
from pathlib import Path

from cforms import rj_chair

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def _html(name):
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8")


def test_rj_chair_winners():
    url = rj_chair.BASE_URL + rj_chair.PAGES["chair"]
    recs = rj_chair.parse(_html("rj_chair_winner.html.gz"), "chair", url)
    assert len(recs) == 309 and len(dict(recs)) == 309
    d = dict(recs)["councillor:RJ:ajmer-nagar-nigam:chair"]
    assert d["name"] == "अनामिका शर्मा" and d["position"] == "Mayor" and d["position_local"] == "महापौर"
    assert d["party"] == "भारतीय जनता पार्टी" and d["votes"] == "43" and d["electorate"] == "80" and d["unopposed"] is False
    assert d["src_pos"] == {"table": "#tabs-5 (Winner)", "row": 2} and d["ward_no"] == "chair"
    k = dict(recs)["councillor:RJ:kekri-nagar-palika:chair"]
    assert k["position"] == "Chairperson" and k["position_local"] == "अध्यक्ष"
    pos = {d["position"] for _, d in recs}
    assert pos == {"Mayor", "Chairperson"} and sum(d["position"] == "Mayor" for _, d in recs) == 10
    # the head ids use the ward reader's body slugs (cforms/rj.py; Laxmangarh and Rajgarh carry the district)
    seeds = {i["payload"]["slug"] for i in json.loads((SEEDS / "councillors_rj.json").read_text())}
    assert {r.split(":")[2] for r, _ in recs} == seeds


def test_rj_vice_winners():
    url = rj_chair.BASE_URL + rj_chair.PAGES["vice"]
    recs = rj_chair.parse(_html("rj_dychair_winner.html.gz"), "vice", url)
    assert len(recs) == 309
    d = dict(recs)["councillor:RJ:ajmer-nagar-nigam:vice"]
    assert d["name"] == "हेमन्त सांखला" and d["position"] == "Deputy Mayor" and d["votes"] == "40" and "party" not in d
    assert rj_chair.METHOD


def test_rj_chair_fetch_postbacks():
    pages = {"chair": _html("rj_chair_winner.html.gz")}
    calls = []

    class R:
        def __init__(self, t):
            self.text, self.content, self.url, self.status_code = t, t.encode(), "", 200

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, (data or {}).get("__EVENTTARGET"), (data or {}).get(rj_chair.P + "btnSubmit")))
        return R(pages["chair"])
    recs, files, why = rj_chair.fetch({"post": "chair", "period": "61"}, get)
    assert why == "" and len(recs) == 309 and len(files) == 1
    assert calls == [("GET", None, None), ("POST", rj_chair.P + "Election", None), ("POST", rj_chair.P + "Period", None),
                     ("POST", "", "Submit")]
    assert recs[0][1]["src_sha256"]
    seeds = json.loads((SEEDS / "councillors_rj_heads.json").read_text())
    assert [s["payload"]["post"] for s in seeds] == ["chair", "vice"]


# Chhattisgarh 2025 heads (cforms/cw_cg_heads.py): page 1 of the SEC's "Mayor-president 2025.pdf" (10 mayors, 22 chairpersons),
# read without OCR (names come from Tesseract on the runners).
def test_cg_heads_text_layer():
    from cforms import cw_cg_heads
    recs = cw_cg_heads.parse(str(DATA / "cw_cg_heads_p1.pdf"), {}, use_ocr=False)
    assert len(recs) == 32
    d = dict(recs)
    assert sum(r["position"] == "Mayor" for r in d.values()) == 10
    b = d["councillor:CG:2025:bilaspur:chair"]
    assert b["lgd_code"] == "250616" and b["party"] == "BJP" and b["position_local"] == "महापौर" and b["src_pos"]["serial"] == "1"
    assert b["ward_no"] == "chair" and b["src_pos"]["page"] == 1
    t = d["councillor:CG:2025:takhatpur:chair"]
    assert t["position"] == "Chairperson" and t["party"] == "INC" and t["lgd_code"] == "250615"
    assert all("lgd_code" in r and "body_read_by_ocr" not in r for r in d.values())
    seeds = json.loads((SEEDS / "ocr_councillors_cw_cg_heads.json").read_text())
    assert seeds[0]["payload"]["kind"] == "form-cw_cg_heads" and seeds[0]["payload"]["expected"] == 173


# Punjab heads of the 2026 poll (cforms/cr_pb.py, payload heads_only): only the post cards, ids chair / vice, member pages read.
def test_pb_heads_only():
    from cforms import cr_pb
    home = (DATA / "cr_pb_talwara_home.html").read_text(encoding="utf-8")
    det = (DATA / "cr_pb_patiala_687.html").read_text(encoding="utf-8")
    asked = []

    class R:
        def __init__(self, t):
            self.text, self.content = t, t.encode()

    def get(url, method="GET", data=None, headers=None):
        asked.append(url)
        return R(home if "Home/Index" in url else det)
    p = {"heads_only": True, "mcid": 1094, "body": "Talwara", "slug": "talwara", "lgd_code": "248301"}
    recs, files, why = cr_pb.fetch(p, get)
    d = dict(recs)
    assert why == "" and set(d) == {"councillor:PB:talwara:chair", "councillor:PB:talwara:vice"} and len(asked) == 3
    assert d["councillor:PB:talwara:chair"]["position"] == "President" and d["councillor:PB:talwara:vice"]["seat_ward"] == "7"
    assert d["councillor:PB:talwara:chair"]["src_pos"] == {"selector": ".card-body .row"}
    items = json.loads((SEEDS / "councillors_cr_pb_heads.json").read_text())
    assert len(items) == 90 and all(i["payload"]["heads_only"] and i["payload"]["slug"] for i in items)
    old = {i["payload"]["mcid"] for i in json.loads((SEEDS / "councillors_cr_pb.json").read_text())}
    assert not old & {i["payload"]["mcid"] for i in items}


# Chhattisgarh June 2026 general and bye-elections (cforms/cw_cg26.py): files without a text layer; the grid is checked here with
# a stand-in for Tesseract (cells answer with their column number, or the ward numbers of the page), the OCR runs on runners.
def _cg26_seed(post):
    return next(i["payload"] for i in json.loads((SEEDS / "ocr_councillors_cw_cg26.json").read_text()) if i["payload"]["post"] == post)


def test_cg26_heads_grid():
    from cforms import cw_cg26
    seen = []

    def ocr(pdf, pg, boxes):
        seen.append(len(boxes))
        return ["राम कुमार" if i % 5 == 3 else "भारतीय जनता पाट" if i % 5 == 4 else "" for i in range(len(boxes))]
    recs = cw_cg26.parse(str(DATA / "cw_cg26_heads.pdf"), _cg26_seed("chair"), ocr=ocr)
    d = dict(recs)
    assert seen == [25] and len(recs) == 5
    assert list(d) == ["councillor:CG:2026:bamhanidih:chair", "councillor:CG:2026:shivnandanpur:chair",
                       "councillor:CG:2026:palari-balod:chair", "councillor:CG:2026:ghumka:chair",
                       "councillor:CG:2026:sahaspur-lohara:chair"]
    s = d["councillor:CG:2026:sahaspur-lohara:chair"]
    assert s["bye_election"] is True and s["replaces"] == "councillor:CG:2025:sahaspur-lohara:chair" and s["lgd_code"] == "273468"
    g = d["councillor:CG:2026:ghumka:chair"]
    assert g["party"] == "BJP" and g["name"] == "राम कुमार" and "bye_election" not in g or g["bye_election"] is False
    assert g["src_pos"]["part"] == "general" and g["src_pos"]["page"] == 1


def test_cg26_bye_members_grid():
    from cforms import cw_cg26
    wards = ["16", "29", "15", "8", "14", "6", "7", "1", "12", "13", "9"]
    boxes_seen = []

    def ocr(pdf, pg, boxes):
        boxes_seen.extend(boxes)
        return [wards[i // 7] if i % 7 == 3 else "" for i in range(len(boxes))]
    p = {**_cg26_seed("member"), "first_part": "bye"}
    recs = cw_cg26.parse(str(DATA / "cw_cg26_members_p3.pdf"), p, ocr=ocr)
    ids = [r for r, _ in recs]
    assert len(recs) == 11 and ids[0] == "councillor:CG:2026:jagdalpur:16" and ids[4] == "councillor:CG:2026:jashpur-nagar:14"
    assert ids[-1] == "councillor:CG:2026:pakhajur:9"
    d = dict(recs)
    assert d["councillor:CG:2026:farasgaon:12"]["replaces"] == "councillor:CG:2025:farasgaon:12"
    assert all(x["bye_election"] and x["election"] == cw_cg26.BYE for x in d.values())
    # Jashpur Nagar: district and body cells merged over its two rows, cut once from the top of the merge
    assert boxes_seen[3 * 7 + 1] == boxes_seen[4 * 7 + 1] and boxes_seen[3 * 7 + 5] != boxes_seen[4 * 7 + 5]
    # Kanker: the district merged over two bodies, the body cells not
    assert boxes_seen[9 * 7 + 1] == boxes_seen[10 * 7 + 1] and boxes_seen[9 * 7 + 2] != boxes_seen[10 * 7 + 2]
