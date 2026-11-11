"""Offline tests of the North India councillor readers (cforms/cn_*.py) on small saved samples in tests/data/cn_*."""
import gzip
import json
from pathlib import Path

from cforms import cn_dl, cn_hr, cn_pb, cn_uk, cn_up
from cforms.cn_krutidev import convert

DATA = Path(__file__).parent / "data"
SEEDS = Path(__file__).parent.parent / "seeds"


def read(name):
    return (DATA / name).read_text(encoding="utf-8")


# ---- Haryana 2022 (grid rows of page 7 of the SEC notification, saved from cforms/hr.py table())

def test_hr_2022_page7():
    rows = json.loads(read("cn_hr_2022_p7_rows.json"))
    state = {"district": "Hisar", "body": "Hansi", "body_type": "Municipal Council", "last": 19}
    recs = dict(cn_hr.records({"url": cn_hr.URL, "election": cn_hr.ELECTION}, cn_hr.page_rows(rows, state), 7))
    # the body carried in from page 6 continues with ward 20
    assert recs["councillor:HR:hansi-municipal-council:20"]["name"] == "Subhash Chander"
    assert recs["councillor:HR:hansi-municipal-council:21"]["party"] == "Bharatiya Janata Party"
    chair = recs["councillor:HR:safidon-municipal-committee:chair"]
    assert chair["name"] == "Anita Rani" and chair["position"] == "President" and chair["district"] == "Jind"
    assert chair["body_en"] == "Safidon" and chair["body_type"] == "Municipal Committee"
    assert recs["councillor:HR:safidon-municipal-committee:17"]["name"] == "Sonika"
    assert recs["councillor:HR:uchana-municipal-committee:4"]["unopposed"] is True
    assert len([k for k in recs if k.startswith("councillor:HR:uchana")]) == 13


def test_hr_party_and_seed():
    assert cn_hr.party("Aam Adami Party") == "Aam Aadmi Party"
    assert cn_hr.party("Indian National Lokdal") == "Indian National Lok Dal"
    assert cn_hr.party("Jannayak Janta Party") == "Jannayak Janta Party"
    items = json.loads((SEEDS / "ocr_councillors_cn_hr.json").read_text())
    assert [i["payload"]["first"] for i in items] == [1, 7, 13, 19] and items[-1]["payload"]["last"] == 24
    assert all(i["payload"].get("stored") for i in items[1:]) and "carry" in items[1]["payload"]


# ---- Punjab 2024 corporations

def test_pb_amritsar():
    recs = dict(cn_pb.amritsar_page(read("cn_pb_amritsar.htm"), "https://www.amritsarcorp.com/council.htm"))
    r1 = recs["councillor:PB:amritsar:1"]
    assert r1["name"] == "Smt. Kuljit Kaur" and r1["party"] == "Aam Aadmi Party" and r1["phone"] == "9867100007"
    assert recs["councillor:PB:amritsar:3"]["party"] == "Indian National Congress"
    assert recs["councillor:PB:amritsar:11"]["position"] == "Senior Deputy Mayor"
    assert recs["councillor:PB:amritsar:11"]["name"] == "Smt. Priyanka Sharma"


def test_pb_jalandhar():
    links = cn_pb.jalandhar_links(read("cn_pb_jalandhar_list.html"), "https://mcjalandhar.in/elected-authorities/")
    assert len(links) == 85 and links[10] == ("11", "https://mcjalandhar.in/smt-karamjit-kaur-ward-11/")
    rid, d = cn_pb.jalandhar_ward(read("cn_pb_jalandhar_w34.html"), "https://mcjalandhar.in/sh-davinder-sood-ward-34/", "34")
    assert rid == "councillor:PB:jalandhar:34"
    assert d["name"] == "Sh. Davinder Sood" and d["party"] == "Bahujan Samaj Party" and d["reservation"] == "SC"
    assert d["phone"] == "9878324440, 7973285433" and d["email"] == "gloss.dsp@gmail.com"
    assert "Abadpura" in d["areas"]


# ---- Uttarakhand 2025 (pages 2-3 of the UDD list, pdftotext -bbox)

def test_uk_members():
    p = json.loads((SEEDS / "councillors_cn_uk.json").read_text())[0]["payload"]
    recs = dict(cn_uk.parse_bbox(gzip.open(DATA / "cn_uk_p2-3.bbox.html.gz", "rt", encoding="utf-8").read(), p))
    d = recs["councillor:UK:dehradun:45"]
    assert d["name"] == "मीनाक्षी मौर्य" and d["ward_name"] == "गांधीग्राम" and d["phone"] == "7500141649"
    assert d["body_en"] == "Dehradun" and d["district"] == "Dehradun" and d["body_type"] == "Municipal Corporation"
    chair = recs["councillor:UK:rishikesh:chair"]
    assert chair["name"] == "शम्भू पासवान" and chair["position"] == "Mayor"
    assert not any("कु " in x["name"] for x in recs.values())       # Chrome's false spaces closed ("कु मार" -> "कुमार")
    assert len(p["bodies"]) == 103


def test_uk_join():
    # a true space is 0.209 x the word height; any other small gap is a split inside a word
    ws = [(100, 0, 110, 15.36, "कु"), (113.9, 0, 130, 15.36, "मार"), (133.21, 0, 150, 15.36, "सिंह")]
    assert cn_uk.join(ws) == "कुमार सिंह"


# ---- Uttar Pradesh 2023 corporations

def test_up_lucknow():
    assert convert("vEcsMdj uxj okMZ") == "अम्बेडकर नगर वार्ड"
    recs = dict(cn_up.lucknow(read("cn_up_lucknow_layout.txt"), cn_up.SOURCES["lucknow"]["url"]))
    assert recs["councillor:UP:lucknow:chair"]["name"] == "सुषमा खर्कवाल"
    r2 = recs["councillor:UP:lucknow:2"]
    assert r2["name"] == "द्रोपदी रावत" and r2["party"] == "Bharatiya Janata Party" and r2["phone"] == "9648965050"
    assert r2["ward_name"] == "शारदा नगर- द्वितीय वार्ड" and r2["father_or_husband"] == "श्री मनोज कुमार"
    r110 = recs["councillor:UP:lucknow:110"]
    assert r110["name"] == "मुसब्बोर अली मंशु" and r110["father_or_husband"] == "मो0 अज्जम अली"
    assert r110["party"] == "Samajwadi Party"


def test_up_kanpur_gorakhpur():
    k = dict(cn_up.kanpur(read("cn_up_kanpur.html"), cn_up.SOURCES["kanpur"]["url"]))
    assert k["councillor:UP:kanpur:chair"]["name"] == "श्रीमती प्रमिला पांडे"
    assert k["councillor:UP:kanpur:1"]["phone"] == "9956600372, 9696419696"
    g = dict(cn_up.gorakhpur(read("cn_up_gorakhpur.html"), cn_up.SOURCES["gorakhpur"]["url"]))
    assert g["councillor:UP:gorakhpur:2"]["name"] == "श्रीमती बाला" and g["councillor:UP:gorakhpur:2"]["ward_name"] == "बाबाराघवदासनगर"
    assert all(d["body_en"] in ("Kanpur", "Gorakhpur") for d in list(k.values()) + list(g.values()))


# ---- Delhi: NDMC council (appointed and ex-officio members)

def test_dl_ndmc():
    recs = [d for _, d in cn_dl.members(read("cn_dl_ndmc.html"))]
    assert recs[0]["name"] == "Sh. Manoj Kumar Dwivedi, IAS" and recs[0]["position"] == "Chairperson (appointed)"
    assert recs[1]["position"] == "Vice Chairperson"
    ex = {d["name"]: d for d in recs if d["position"].startswith("Member (ex officio")}
    assert ex["Ms. Bansuri Swaraj"]["position"] == "Member (ex officio, MP (LS))"
    assert ex["Mr. Virender Singh Kadian"]["email"] == "virendersinghkadian@gmail.com"
