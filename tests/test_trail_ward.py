"""Source trail of the ward / zone office readers (dforms/ward_*.py, ward2n_*.py, ward2s_*.py): every reader names its METHOD, and
the readers that give positions put a src_pos on every record that points at the real line of the PDF text or the real <tr> of the
saved page (the same cases as test_ward_cities.py, test_ward2n.py, test_ward2s.py)."""
import json
import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from esw_common import DATA, ROOT, fake_get, mod

import provenance

DIRS = ("ward", "ward2n", "ward2s")
CASES = [p for d in DIRS for p in sorted((DATA / d).glob("*.json"))]
MODULES = sorted(p.stem for p in (ROOT / "dforms").glob("ward*.py"))


def run(path):
    case = json.loads(path.read_text())
    m = mod(case["module"])
    d = path.parent.name
    if case.get("pages"):
        pages = json.loads((path.parent / case["pages"]).read_text())
        return case, m, m.parse(pages, case["payload"]), pages, {}
    routes = {}
    for k, v in case.get("routes", {}).items():
        routes[("POST", k[5:]) if k.startswith("POST ") else k] = f"{d}/{v}"
    recs, _, _ = m.fetch(case["payload"], fake_get(routes))
    return case, m, recs, None, routes


def test_every_ward_reader_has_a_method():
    for name in MODULES:
        if name.startswith("_"):
            continue
        assert getattr(mod(name), "METHOD", ""), name


def tr_text(html, table, row):
    t = BeautifulSoup(html, "lxml").find_all("table")[table - 1]
    trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
    return " ".join(trs[row - 1].get_text(" ").split())


def positions(d):
    p = d.get("src_pos") or {}
    return p.get("rows") or [p]


@pytest.mark.parametrize("path", CASES, ids=[f"{p.parent.name}/{p.stem}" for p in CASES])
def test_positions_point_at_the_source(path):
    if any(not (DATA / f).exists() for f in json.loads(path.read_text()).get("routes", {}).values()
           if not (DATA / path.parent.name / f).exists()):
        pytest.skip("fixture not in this checkout")
    case, m, recs, pages, routes = run(path)
    if "src_pos" not in Path(m.__file__).read_text():
        pytest.skip(f"{case['module']}: no positions yet")
    assert recs
    missing = [rid for rid, d in recs if not d.get("src_pos")]
    assert not missing, missing[:5]
    htmls = [(DATA / f).read_text("utf-8", "replace") for f in routes.values()] if routes else []
    named = hit = 0
    for rid, d in recs:
        for pos in positions(d):
            if pages is not None and "line" in pos and isinstance(pos.get("page"), int):
                sets = list(pages.values()) if isinstance(pages, dict) else [pages]     # bikaner: {"list": [...], "contacts": [...]}
                ok = []
                for pg in sets:
                    lines = pg[pos["page"] - 1].replace("\f", "\n").split("\n") if pos["page"] <= len(pg) else []
                    ok.append(1 <= pos["line"] <= len(lines) and ("line_text" not in pos or
                                                                  lines[pos["line"] - 1].strip() == pos["line_text"].strip()))
                assert any(ok), (rid, pos)
            if "table" in pos and "row" in pos and isinstance(pos["row"], int) and htmls:
                texts = []
                for h in htmls:
                    try:
                        texts.append(tr_text(h, pos["table"], pos["row"]))
                    except IndexError:
                        pass
                assert texts, (rid, pos)
                if d.get("name") and len(positions(d)) == 1:
                    named += 1
                    first = re.split(r"[\s,.]+", d["name"].strip())[0]
                    hit += any(first.lower() in t.lower() for t in texts)
    if named:
        assert hit / named >= 0.7, (hit, named)


def test_multi_source_items_name_their_source():
    """ward2n_bikaner reads two PDFs, ward2n_faridabad a home page and a script bundle: each record says which one (src_url +
    src_sha256), and the trail resolves it to that answer."""
    from dforms import ward2n_faridabad as fb

    home = b'<html><script type="module" src="/assets/index-abc.js"></script></html>'
    js = (b'zone1:{name:"Zone 1",officer:"A Kumar",mobile:"9876543210"},zone1:{name:"\xe0\xa4\x9c\xe0\xa5\x8b\xe0\xa4\xa8 1",'
          b'officer:"\xe0\xa4\x8f",mobile:"9876543210"}')

    class R:
        def __init__(self, b, u):
            self.content, self.url, self.status_code, self.encoding = b, u, 200, "utf-8"
            self.headers = {"Content-Type": "text/javascript" if u.endswith(".js") else "text/html"}

        @property
        def text(self):
            return self.content.decode()

    t = provenance.Trail("depts", "p")
    t.begin({"key": "k", "payload": {}}, "dforms.ward2n_faridabad")

    def get(u, method="GET", data=None, headers=None):
        r = R(js if u.endswith(".js") else home, u)
        t.note(r, u)
        return r
    recs, _, why = fb.fetch({"url": fb.URL, "state": "HR"}, get)
    assert recs, why
    d = recs[0][1]
    assert d["src_url"] == "https://mcfaridabad.in/assets/index-abc.js" and d["src_pos"]["object"] == "zone1"
    out, _ = t.finish(recs, [], fb.METHOD)
    assert out[0][1]["src"]["sha256"] == provenance.hashlib.sha256(js).hexdigest() and out[0][1]["method"].startswith("js bundle")
