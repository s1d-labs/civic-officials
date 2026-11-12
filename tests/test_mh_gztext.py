"""Maharashtra corporation results from divisional e-Gazette notices with a text layer (cforms/mh_gztext.py): saved word boxes
(pdftotext -bbox) of the first two pages of Nagpur A-2530, Chandrapur A-2529 and Akola A-2531 (19 Jan 2026). No network."""
import gzip
import json
from pathlib import Path

from cforms import mh_gztext as g

DATA = Path(__file__).parent / "data"
WORDS = json.loads(gzip.decompress((DATA / "mh_gztext_words.json.gz").read_bytes()))


def recs(name, cols):
    pages = [(pg, [tuple(w) for w in ws]) for pg, ws in WORDS[name]]
    return dict(g.records(g.rows_of(pages, cols), {"cols": cols, "url": "u", "slug": name, "body": name, "lgd_code": "1"}))


def test_fix_doubled_marks():
    assert g.fix("महाारााष्ट्र शाासन") == "महाराष्ट्र शासन"
    assert g.fix("साार्ववत्रि�क नि�वडणूूक") == "सार्वत्रिक निवडणूक"
    assert g.fix("वर्षष") == "वर्ष"


def test_nagpur():
    r = recs("nagpur", ["ward", "seat", "name", "address", "party"])
    assert len(r) >= 15
    d = r["councillor:MH:nagpur:1-अ"]
    assert d["name"] == "धनविजय महेंद्रप्रसाद रमेश"
    assert d["party"] == "BJP" and d["address"].startswith("७३-अ, नागसेन नगर")
    assert r["councillor:MH:nagpur:3-ब"]["party"] == "AIMIM"
    assert r["councillor:MH:nagpur:2-अ"]["party"] == "INC"


def test_chandrapur_columns_differ():
    r = recs("chandrapur", ["serial", "name", "ward", "seat", "reservation"])
    d = r["councillor:MH:chandrapur:1-अ"]
    assert d["name"] == "सरलादेवी जनार्धन गेडाम" and d["ward_name"] == "दे.गो. तूकूम"
    assert d["reservation_local"] == "अ.ज. (महिला)"
    assert r["councillor:MH:chandrapur:2-ब"]["name"] == "डिलन शैलेश केळझरकर"


def test_akola_ward_name_and_wraps():
    r = recs("akola", ["ward", "seat", "name", "address", "party"])
    assert r["councillor:MH:akola:1-अ"]["name"] == "शेख अब्दुल्लाह शेख सलीम"
    assert r["councillor:MH:akola:1-अ"]["ward_name"] == "नायगांव"
    assert r["councillor:MH:akola:1-ड"]["name"] == "अब्दुल सलाम खान अब्दुल करीम खान"
    assert r["councillor:MH:akola:2-अ"]["party"] == "AIMIM"


def test_mh_div_seeds():
    import importlib
    seeds = json.loads((Path(__file__).parent.parent / "seeds" / "ocr_councillors_mh_div.json").read_text())
    assert len({s["key"] for s in seeds}) == len(seeds) == 20
    for s in seeds:
        p = s["payload"]
        mod = importlib.import_module("cforms." + p["kind"].split("-", 1)[1])
        assert hasattr(mod, "fetch") and p["lgd_code"].isdigit() and p["match"]
        assert int(p.get("last", 99)) - int(p.get("first", 0)) <= 6 or p["kind"] == "form-mh_gztext"
