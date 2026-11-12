"""Maharashtra nagar panchayat results 2021-22 from the English orders in the divisional e-Gazette notices (cforms/mh_np.py):
saved word boxes (pdftotext -bbox) of pages of the Gadchiroli (25 Jan 2022), Solapur (28 Jan), Osmanabad (1 Feb), Nashik
(27 Jan, ordinary), Amravati (21 Jan) and Jalna (25 Jan) notices. No network."""
import gzip
import json
from pathlib import Path

from cforms import mh_np as m

DATA = Path(__file__).parent / "data"
WORDS = json.loads(gzip.decompress((DATA / "mh_np_words.json.gz").read_bytes()))
LGD = json.loads((Path(m.__file__).parent / "mh_np_lgd.json").read_text(encoding="utf-8"))


def bodies(*codes):
    return [{"lgd_code": c, **LGD[c]} for c in codes]


def recs(name, *codes):
    pages = [(pg, [tuple(w) for w in ws]) for pg, ws in WORDS[name]]
    return dict(m.records(m.rows_of(pages), {"url": "u", "bodies": bodies(*codes), "match": "x", "gazette_date": "25/01/2022"}))


def test_gadchiroli_two_bodies_in_one_notice():
    r = recs("gadchiroli", "276327", "276288")
    assert sum(k.startswith("councillor:MH:276327:") for k in r) == 17          # Aheri
    assert sum(k.startswith("councillor:MH:276288:") for k in r) == 17          # Sironcha
    d = r["councillor:MH:276327:1"]
    assert d["name"] == "Uikey Vikas Ashok" and d["reservation"] == "General" and d["address"] == "At Post Tah. Aheri, Distt. Gadchiroli"
    assert r["councillor:MH:276327:17"]["address"] == "At Post Tah. Aheri, Distt. Gadchiroli"     # the signature is not address
    assert r["councillor:MH:276288:17"]["reservation"] == "SC woman"
    assert d["src_pos"]["page"] == 3 and d["src_pos"]["line_text"].startswith("1 Ward No. 1 General Uikey")
    assert d["body_type"] == "Nagar Panchayat" and d["lgd_code"] == "276327"


def test_solapur_body_column_is_not_the_name():
    r = recs("solapur", "276302")
    assert len(r) == 17
    assert r["councillor:MH:276302:1"]["name"] == "Mali Ajinath Bhagavat"
    assert r["councillor:MH:276302:2"]["reservation"] == "SC"


def test_osmanabad_ward_number_next_to_name():
    r = recs("osmanabad", "276312")
    assert len(r) == 17
    assert r["councillor:MH:276312:1"]["name"] == "Gaikwad Smita Amol"
    assert r["councillor:MH:276312:1"]["reservation"] == "SC woman"


def test_nashik_address_and_party():
    r = recs("nashik", "251434")
    assert len(r) == 17
    d = r["councillor:MH:251434:4"]
    assert d["name"] == "Pawar Yogita Vijay" and d["party"] == "CPI(M)" and d["reservation"] == "ST woman"
    assert r["councillor:MH:251434:1"]["party"] == "SHS"
    assert "Surgana" in r["councillor:MH:251434:2"]["address"]


def test_amravati_reservation_beside_ward():
    r = recs("amravati", "276289")
    assert len(r) == 17
    assert r["councillor:MH:276289:2"]["reservation"] == "General woman"


def test_jalna_and_body_choice():
    r = recs("jalna", "276372", "276371")         # the Jafrabad order: Mantha is not named in it
    assert len(r) == 17 and all(k.startswith("councillor:MH:276372:") for k in r)
    assert r["councillor:MH:276372:1"]["name"] == "DIVTE SURESH TRAMBAK"


def test_reservation_words():
    assert m.reservation("S.T. (W.)") == "ST woman"
    assert m.reservation("Backward Class of Citizens (Women)") == "OBC woman"
    assert m.reservation("Scheduled Castes") == "SC"
    assert m.reservation("Open (Women)") == "General woman"
    assert m.party_of("Nationalist Congress Party.") == "NCP"


def test_ward_formation_block_is_not_read():
    blocks = [{"text": "the extent of the Wards ... Draft Order", "rows": [{"page": 1, "line": 1, "line_text": "1 x", "serial": "1",
                                                                          "name": "Abc Def", "ward": "1"}]}]
    assert m.records(blocks, {"url": "u", "bodies": bodies("276312"), "match": ""}) == []


def test_seeds():
    items = json.loads((Path(__file__).parent.parent / "seeds" / "councillors_mh_np.json").read_text(encoding="utf-8"))
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys))
    codes = [b["lgd_code"] for i in items if not i["payload"].get("save_only") for b in i["payload"]["bodies"]]
    assert len(codes) == len(set(codes)) >= 59 and all(c in LGD for c in codes)
    assert all(i["payload"]["kind"] == "form-mh_np" for i in items)
