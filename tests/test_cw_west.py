"""Elected ward councillors of West and Central India (prefix cw_): Maharashtra (cforms/cw_mh*.py), Madhya Pradesh
(cforms/cw_mp.py), Chhattisgarh 2025 (cforms/cw_cg.py), Gujarat (cforms/cw_gj.py), Goa (cforms/cw_ga.py) and Dadra and
Nagar Haveli and Daman and Diu (cforms/cw_dd.py). Offline: saved samples in tests/data/cw_* only, no network, no Tesseract."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = Path(__file__).parent / "data"


# ---- Maharashtra ----
# Maharashtra councillor readers (cforms/cw_mh*.py) on saved samples (tests/data/cw_mh_*): no network.
import gzip
import json
import sys
from pathlib import Path



def sec_page(name, doc):
    """One page of the SEC Maharashtra statistical reports, saved as text-layer words and drawn lines."""
    from cforms import cw_mh
    d = json.loads(gzip.decompress((DATA / f"cw_mh_sec_{name}.json.gz").read_bytes()))
    ws = [tuple(w) for w in d["words"]]
    hs = [tuple(h) for h in d["h"]]
    vs = [tuple(v) for v in d["v"]]
    return dict(cw_mh.parse_page(ws, hs, vs, {"doc": doc}, d["page"], []))


def test_sec_members_page():
    recs = sec_page("members_p64", "members")
    hm = {k: r for k, r in recs.items() if r["body_sec"] == "Himayatnagar"}
    assert len(hm) >= 10
    r = hm["councillor:MH:276606:9-1"]
    assert r["name"] == "Rathod Suchita Kunal" and r["party"] == "SS(UBT)" and r["votes"] == 442
    assert r["runner_up"] == "Mudholkar Inidira Pankaj" and r["runner_up_party"] == "BJP" and r["margin"] == "258"
    assert r["reservation"] == "BCC W" and r["gender"] == "Female"
    assert r["body"] == "Himayatnagar Nagarpanchayat" and r["lgd_code"] == "276606" and r["body_type"] == "Nagar Panchayat"
    assert r["district"] == "Nanded" and r["state"] == "MH" and r["type"] == "councillor"
    # ward 10: the second runner-up with the same votes is its own row, without a winner
    w10 = hm["councillor:MH:276606:10-1"]
    assert w10["name"] == "Sakwan Ashish Baburao" and w10["runner_up_tied"] == ["Palajkar Gajanan Dattatray"]
    assert not any(r["name"] == "" for r in recs.values())


def test_sec_presidents_page():
    recs = sec_page("presidents_p26", "presidents")
    by_body = {r["body_sec"]: r for r in recs.values()}
    m = by_body["Mangalwedha"]                       # "MANGALWEDH A": a word the printout broke inside the cell
    assert m["position"] == "President" and m["name"] == "Avatade Sunanda Baban" and m["votes"] == 9850
    assert m["body"] == "Mangalvedhe" and m["lgd_code"] == "251580"
    a = by_body["Angar"]                              # "UNOPP OSED"
    assert a["unopposed"] and a["votes"] is None and a["party"] == "BJP" and a["runner_up"] == ""
    assert by_body["Kurduwadi"]["party"] == "SS(UBT)"
    assert "councillor:MH:251580:president" in recs


def test_party_names():
    from cforms import cw_mh
    assert cw_mh.party_of("BHARTIY JANTA PARTY") == "BJP"
    assert cw_mh.party_of("भारतीय जनता पाटी") == "BJP"
    assert cw_mh.party_of("SHIVSENA (EKNATH SHINDE)") == "SHS"
    assert cw_mh.party_of("SHIV SENA (UDDHAV BALASAHEB THACKREY)") == "SS(UBT)"
    assert cw_mh.party_of("NATIONALIST CONGRESS PARTY - SHARADCHAN DRA PAWAR") == "NCP(SP)"
    assert cw_mh.party_of("NCP (AJIT PAWAR)") == "NCP"
    assert cw_mh.party_of("INDEPENDANT") == "Independent"
    assert cw_mh.party_of("JAN SURAJYA SHAKTI") == "Jan Surajya Shakti"


def test_sec_items():
    from cforms import cw_mh
    it = cw_mh.items()
    assert len(it) == 13 and len({i["key"] for i in it}) == 13
    first = [i for i in it if i["payload"]["first"] == 1]
    assert len(first) == 2 and not any("stored" in i["payload"] for i in first)
    assert all(i["payload"]["stored"].startswith("civic-officials-councillors-ocr/councillors/MH/") for i in it if i not in first)
    pages = sorted((i["payload"]["first"], i["payload"]["last"]) for i in it if i["payload"]["doc"] == "members")
    assert pages[0] == (1, 46) and pages[-1][1] == 552


class _Answer:
    def __init__(self, path):
        self.content = (DATA / path).read_bytes()
        self.text = self.content.decode("utf-8")
        self.status_code = 200


def _get(routes):
    def get(url, method="GET", data=None, headers=None):
        return _Answer(routes[url]) if url in routes else None             # pages not saved: as get() answers on an error
    return get


def test_pcmc_corporators():
    from cforms import cw_mh_city
    get = _get({"https://www.pcmcindia.gov.in/corporator-details?Id=288": "cw_mh_pcmc_288.html",
                "https://www.pcmcindia.gov.in/corporator": "cw_mh_pcmc_list.html"})
    recs, files, why = cw_mh_city.fetch({"site": "pcmc", "url": cw_mh_city.SITES["pcmc"]["url"]}, get)
    recs = dict(recs)
    assert why == "" and len(recs) == 12 and files[0][0] == "councillors/MH/pcmc-corporators.html.gz"
    r = recs["councillor:MH:pimpri-chinchwad-mc:2-अ"]
    assert r["name"] == "सुजाता निलेश बोराटे" and r["phone"] == "9096330431" and r["party"] == "BJP"
    assert r["email"] == "2a@pcmcindia.gov.in" and "बोऱ्हाडेवाडी" in r["address"]
    assert r["body"] == "Pimpri Chinchwad" and r["body_type"] == "Municipal Corporation" and r["district"] == "Pune"
    leader = recs["councillor:MH:pimpri-chinchwad-mc:32-ड"]
    assert leader["name"] == "प्रशांत शितोळे" and leader["post"] == "सभागृह नेता" and leader["phone"] == "9922501688"
    assert "party" not in leader            # its detail page did not answer


def test_amravati_corporators():
    from cforms import cw_mh_city
    get = _get({"https://amravaticorporation.in/en/elected-members/": "cw_mh_amravati.html"})
    recs, files, why = cw_mh_city.fetch({"site": "amravati"}, get)
    recs = dict(recs)
    assert why == "" and len(recs) == 11
    r = recs["councillor:MH:amravati-mc:7-1"]
    assert r["name"] == "श्री. श्रीचंद लक्ष्मणदास तेजवानी" and r["post"] == "मा. महापौर" and r["party"] == "BJP"
    assert r["phone"] == "9405379594"
    assert recs["councillor:MH:amravati-mc:1-2"]["name"] == "सौ.वंदना प्रदीप मडघे"
    assert recs["councillor:MH:amravati-mc:16-1"]["party"] == "VBA"


def test_csmc_rows():
    """Chhatrapati Sambhajinagar corporator list, last page: rows, prabhag (merged cell), seat, phone from the text layer."""
    from cforms import cw_mh_csmc
    d = json.loads(gzip.decompress((DATA / "cw_mh_csmc_p8.json.gz").read_bytes()))
    ws, hs, vs = [tuple(w) for w in d["words"]], [tuple(h) for h in d["h"]], [tuple(v) for v in d["v"]]
    rows, last = cw_mh_csmc.parse_page(ws, hs, vs, None, "29")
    assert [(s, w, seat) for s, w, seat, _, _ in rows][:3] == [("113", "29", "अ"), ("114", "29", "ब"), ("115", "29", "क")]
    assert rows[0][4] == ["8793877777"] and rows[2][4] == ["7470723374"]
    # names come from OCR in the pool; the OCR cell text is split at the first comma
    texts = ["श्री.सिध्दांत संजय सिरसाट, लिंकरोड, गोलवाडी", "श्रीमती अनिता नंदकुमार घोडेले, मातोश्री", "श्रीमती श्वेता सुमित त्रिवेदी, संताजी"]
    rows, _ = cw_mh_csmc.parse_page(ws, hs, vs, texts, "29")
    assert cw_mh_csmc.split_name(rows[0][3]) == ("श्री", "सिध्दांत संजय सिरसाट", "लिंकरोड, गोलवाडी")
    assert cw_mh_csmc.split_name(rows[1][3])[:2] == ("श्रीमती", "अनिता नंदकुमार घोडेले")


# ---- Madhya Pradesh ----
# Madhya Pradesh 2022 elected councillors (cforms/cw_mp.py): Gazette Extraordinary notices of the State Election Commission,
# scans read by OCR. Samples: the cell texts that Tesseract read from pages 9 and 10 of issue No. 411 of 26 July 2022 (two
# Betul district notices), and a gazette search answer. The answer's markup is the site's own (an empty answer of 2026-11-11);
# its two rows carry the number, date and subject of real notices, but their file links are made up for the test (no live
# answer with rows was saved). The grid test draws its own small image, so no PDF and no Tesseract are needed here.
import io
import json
import pathlib

from pypdf import PdfWriter

from cforms import cw_mp



def test_preamble_body():
    b = cw_mp.body_from("यह अधिसूचित किया जाता है कि राज्य में नगर परिषद् धोडाडौंगरी जिला बैतूल के माह जुलाई वर्ष--2022 में कराये गये")
    assert (b["body_local"], b["district_local"], b["body_type"], b["year"]) == ("धोडाडौंगरी", "बैतूल", "Nagar Parishad", "2022")
    b = cw_mp.body_from("कि राज्य में नगरपालिका परिषद् शाजापुर जिला शाजापुर के माह-जुलाई 2022 में")
    assert (b["body_local"], b["body_type"]) == ("शाजापुर", "Municipality")
    b = cw_mp.body_from("राज्य में नगरपालिक निगम भोपाल के माह जुलाई 2022 में")
    assert (b["body_local"], b["district_local"], b["body_type"]) == ("भोपाल", "भोपाल", "Municipal Corporation")
    assert cw_mp.body_from("822 मध्यप्रदेश राजपत्र, दिनांक 26 जुलाई 2022") is None


def test_party_and_numbers():
    assert cw_mp.party_of("मारतीय जनता पार्दी") == "BJP"
    assert cw_mp.party_of("इंडियन नेशनल कॉँग्रेस") == "INC"
    assert cw_mp.party_of("निर्दलीय") == "Independent"
    assert cw_mp.party_of("आम आदमी पार्टी") == "AAP"
    assert cw_mp.word_num("पच्चीस") == "25" and cw_mp.word_num("छः") == "6"
    assert cw_mp.num("| 6") == "6" and cw_mp.num("१२") == "12"


def test_sequence_fixes_misread_ward_numbers():
    body = {"body_local": "क", "district_local": "ख"}
    rows = [{"position": "Councillor", "ward_no": w, "ward_read": r, "ward_words": ww, "name": n}
            for w, r, ww, n in (("13", "13", "13", "a"), ("", "", "", "b"), ("45", "45", "", "c"), ("16", "16", "16", "d"))]
    rows[0]["ward_no"] = "13"
    out = cw_mp.sequence([(body, {**rows[0], "ward_no": str(i)}, 1) for i in range(1, 13)] + [(body, m, 1) for m in rows])
    assert [m["ward_no"] for _, m, _ in out][-4:] == ["13", "14", "15", "16"]


def test_read_pages_sample():
    blocks = json.loads((DATA / "cw_mp_blocks_p9_p10.json").read_text())
    found = cw_mp.read_pages(blocks)
    bodies = {}
    for b, m, _ in found:
        bodies.setdefault(b["body_local"], []).append(m)
    assert set(bodies) == {"धोडाडौंगरी", "भैंसदेही"}
    bh = {m["ward_no"]: m for m in bodies["भैंसदेही"]}
    assert len(bh) >= 14
    assert bh["2"]["name"] == "कुसुम सिंह राजा ठाकुर" and bh["2"]["party"] == "BJP"
    assert bh["7"]["name"] == "सुषमा प्रजापति" and bh["7"]["party"] == "INC"
    assert all(not cw_mp.HEADER.search(m["name"]) for ms in bodies.values() for m in ms)
    rid, d = cw_mp.record({"url": "https://govtpress.mp.gov.in/x.pdf", "gazette_no": "411", "gazette_date": "26-07-2022"},
                          found[0][0], found[0][1], 9)
    assert rid.startswith("councillor:MP:") and d["state"] == "MP" and d["type"] == "councillor"
    assert d["body_local"] == "धोडाडौंगरी" and (d["body"], d["district"], d["lgd_code"]) == ("Ghodadongri", "Betul", "298919")


def test_lgd_match_survives_ocr_slips():
    assert cw_mp.lgd_match("विरसिंल्युर", "सतना", "Nagar Parishad")[1] == "Birsinghpur"     # बिरसिंहपुर as Tesseract read it
    assert cw_mp.lgd_match("खण्डवा", "खण्डवा", "Municipal Corporation")[:2] == ["250923", "Khandwa"]   # LGD: Khandwa (East Nimar)
    assert cw_mp.lgd_match("न्यू रामनगर", "सतना", "Nagar Parishad")[1] == "New Ramnagar"       # now in Maihar district
    assert cw_mp.lgd_match("बैतूल बाजार", "बैतूल", "Nagar Parishad")[1] == "Betul Bazar"


def test_grid_on_drawn_table():
    w, h = 400, 300
    img = bytearray([255]) * (w * h)

    def dot(x, y):
        if 0 <= x < w and 0 <= y < h:
            img[y * w + x] = 0
    ys = [60 + 25 * i for i in range(9)]
    xs = [40, 70, 150, 230, 360]
    for i, y in enumerate(ys):                      # rows a little skewed, as in a scan
        for x in range(40, 361):
            dot(x, y + x // 200)
    for x in xs:
        for y in range(ys[0], ys[-1] + 3):
            dot(x + y // 150, y)
    for y in range(20, 30):                         # a text line above the table: words with spaces
        for x in range(40, 360):
            if (x // 30) % 2 == 0:
                dot(x, y)
    hs, vs, table = cw_mp.grid(w, h, bytes(img))
    assert len(hs) == 9 and all(abs(a - b) <= 3 for a, b in zip(hs, ys))
    assert len(vs) == 5 and all(abs(a - b) <= 4 for a, b in zip(vs, xs))
    assert len(table) == 8


def test_listing_and_items():
    html = (DATA / "cw_mp_listing.html").read_text()
    rows, offsets = cw_mp.listing(html)
    assert [r["no"] for r in rows] == ["411", "316"] and offsets == [10]
    assert [cw_mp.wanted(r) for r in rows] == [True, False]
    assert rows[0]["url"] == "https://govtpress.mp.gov.in/uploads/gazette/test-411.pdf"
    assert cw_mp.slug_of(rows[0]) == "mp-gz-26072022-411"

    buf = io.BytesIO()
    pdf = PdfWriter()
    for _ in range(6):
        pdf.add_blank_page(595, 842)
    pdf.write(buf)

    class Resp:
        def __init__(self, text="", content=b""):
            self.text, self.content = text, content

    class Hub:
        saved = []

        def upload_many(self, files):
            self.saved += [f[0] for f in files]

    def get(url, method="GET", data=None, headers=None):
        if url.endswith(".pdf"):
            return Resp(content=buf.getvalue())
        if method == "POST":
            return Resp(text=html if data["year"] == "2022" and data["page"] == 0 else "")
        return Resp(text="")
    get.hub = Hub()
    its = cw_mp.items(get)
    assert [i["key"] for i in its] == ["mp-gz-26072022-411-p1", "mp-gz-26072022-411-p5"]
    assert its[1]["payload"]["first"] == 5 and its[1]["payload"]["last"] == 6
    assert its[0]["payload"]["stored"].endswith("councillors/MP/mp-gz-26072022-411.pdf")
    assert get.hub.saved == ["councillors/MP/mp-gz-26072022-411.pdf"]


# ---- Chhattisgarh ----
# Chhattisgarh 2025 elected councillors (cforms/cw_cg.py): the SEC's statewide PDF, text layer + OCR. The sample is a cut of
# page 2 (drawn borders, text layer words, and the OCR of its name cells as Tesseract read them), so no PDF and no Tesseract
# are needed here.
import json
import pathlib

from cforms import cw_cg, gj



def test_keys_and_party():
    assert cw_cg.body_key("नगरपािलका प रषद तखतप र ु") == ("नगर पालिका परिषद", "तखतपर")
    assert cw_cg.body_key("नगर प च ं ायत कोटा") == cw_cg.body_key("नगर पंचायत कोटा") == ("नगर पंचायत", "कट")
    assert cw_cg.body_key("नगरपािलक िनगम िबलासप र ु")[0] == "नगर पालिक निगम"
    assert cw_cg.dist_key("म ंग ु ेली") == cw_cg.dist_key("म ग ं ु ेली")
    assert cw_cg.party_of("भारतीय जनता पाट") == "BJP"
    assert cw_cg.party_of("इि डयन नेशनल कां ेस") == "INC"
    assert cw_cg.party_of("िनदलीय") == "Independent"
    assert cw_cg.party_of("बहजन समाज पाट") == "BSP"
    assert cw_cg.party_of("आम आदमी पाट") == "AAP"
    assert cw_cg.party_of("क य ि ु न ट पाट ऑफ (मा इि डया सिस ट)") == "CPI(M)"
    assert cw_cg.party_of("क य ि ु न ट पाट ऑफ इ ि ं डया") == "CPI"


def test_fix_name():
    assert cw_cg.fix_name("स रेश कुमार केंवट") == "सुरेश कुमार केंवट"
    assert cw_cg.fix_name("श्याम कुमार साह्") == "श्याम कुमार साहू"
    assert cw_cg.fix_name("बिलासप्र") == "बिलासपुर"
    assert cw_cg.fix_name("बी. वल्लभ राव") == "बी. वल्लभ राव"
    assert cw_cg.subseq(cw_cg.key("िदलीप कुमार कोरी"), cw_cg.key("दिलीप कुमार कोरी"))


def test_page_sample(monkeypatch):
    s = json.loads((DATA / "cw_cg_page2.json").read_text())
    monkeypatch.setattr(gj, "drawn_lines", lambda reader, i: ([tuple(h) for h in s["hs"]], [tuple(v) for v in s["vs"]]))
    monkeypatch.setattr(gj, "words", lambda pdf, pg: [tuple(w) for w in s["words"]])
    monkeypatch.setattr(cw_cg, "ocr_cells", lambda pdf, pg, boxes, tmp, dpi=400: s["ocr"][:len(boxes)])

    class Reader:
        def __init__(self, *a):
            self.pages = [None] * 55
    monkeypatch.setattr("pypdf.PdfReader", Reader)
    seed = json.loads((pathlib.Path(__file__).parent.parent / "seeds" / "ocr_councillors_cw_cg.json").read_text())
    p = dict(seed[0]["payload"], first=2, last=2)
    recs = dict(cw_cg.page_records("x.pdf", p, 2))
    assert len(recs) == 8
    r = recs["councillor:CG:2025:bilaspur:69"]
    assert (r["name"], r["ward_name"], r["party"]) == ("प्रकाश यादव (बन्टी)", "बिलासा दाई केंवटिन नगर", "BJP")
    assert (r["body"], r["body_en"], r["body_type"], r["district"], r["local_body_code"]) == \
        ("बिलासपुर", "Bilaspur", "नगर पालिक निगम", "Bilaspur", "250616")
    assert "2025" in r["election"] and r["state"] == "CG"
    t = recs["councillor:CG:2025:takhatpur:1"]
    assert (t["name"], t["ward_no"], t["party"], t["body_en"]) == ("गौरी अजय देवांगन", "1", "INC", "Takhatpur")
    assert recs["councillor:CG:2025:takhatpur:3"]["name"] == "कोमल सिंह"


def test_seed():
    seed = json.loads((pathlib.Path(__file__).parent.parent / "seeds" / "ocr_councillors_cw_cg.json").read_text())
    assert [i["payload"]["first"] for i in seed] == list(range(1, 56, 5))
    assert "stored" not in seed[0]["payload"] and all(i["payload"]["stored"].endswith(".pdf") for i in seed[1:])
    lgd = {b["lgd"] for i in seed for b in i["payload"]["bodies"].values()}
    assert len(lgd) == 173


# ---- Gujarat (cforms/cw_gj.py), Goa (cforms/cw_ga.py), Dadra and Nagar Haveli and Daman and Diu (cforms/cw_dd.py) ----
# Samples: cw_gj_index_links.html (the links of sec.gujarat.gov.in/index.htm, 2026-11-11), cw_ga_previous.html (the main part of
# sec.goa.gov.in/elections/previous/, 2026-11-11), cw_dd_listing.html (5 rows of ddd.gov.in latest-updates page 40, 2026-11-11),
# cw_dd_daman_2016.txt (pdftotext of the Feb 2016 Daman council gazette, the same notice the 2025 gazettes repeat) and
# cw_ga_winners_sample.txt (made by hand from the SEC's 2023 Ponda winners file as search engines show it: no copy reached).
import datetime as _dt
import io as _io

from cforms import cw_dd, cw_ga, cw_gj


class _Resp:
    def __init__(self, text="", content=None):
        self.text, self.content = text, content if content is not None else text.encode()


def test_dd_members_from_gazette_text():
    rows = cw_dd.members((DATA / "cw_dd_daman_2016.txt").read_text())
    assert len(rows) == 15 and {r[0] for r in rows} == {"Daman"}
    assert rows[0] == ("Daman", "1", "Shri Mario Francisco Lopes", "Indian National Congress")
    assert rows[3][2] == "Smt. Tandel Lata Devjibhai" and rows[11][1:] == ("12", "Shri Jaiantilal Mital", "Bharatiya Janata Party")
    recs = cw_dd.records((DATA / "cw_dd_daman_2016.txt").read_text(), {"url": "u", "election": "x"})
    assert recs[0][0] == "councillor:DD:daman:1" and recs[0][1]["party"] == "INC" and recs[1][1]["party"] == "Independent"
    assert recs[0][1]["body"] == "Daman Municipal Council" and recs[0][1]["district"] == "Daman"


def test_dd_listing_and_items():
    rows = cw_dd.listing((DATA / "cw_dd_listing.html").read_text())
    assert rows[0][0] == "OFFICIAL GAZETTE : Extra Ordinary No. 115" and rows[0][1] == _dt.date(2025, 9, 3)
    assert rows[0][2].endswith(".pdf")
    assert cw_dd.window(_dt.date(2025, 11, 12)) and cw_dd.window(_dt.date(2023, 3, 1)) and not cw_dd.window(_dt.date(2025, 9, 3))
    page1 = '<table><tr><td>OFFICIAL GAZETTE : Extra Ordinary No. 160</td><td>12/11/2025</td><td><a href="https://x/a.pdf">View</a></td></tr>' \
            '<tr><td>Tender notice</td><td>13/11/2025</td><td><a href="https://x/t.pdf">View</a></td></tr></table>'
    old = '<table><tr><td>OFFICIAL GAZETTE : Extra Ordinary No. 3</td><td>02/01/2023</td><td><a href="https://x/o.pdf">View</a></td></tr></table>'
    pages = {cw_dd.LIST.format(1): page1, cw_dd.LIST.format(2): old}
    got = cw_dd.items(lambda u, **k: _Resp(pages[u]) if u in pages else None)
    assert [i["payload"]["url"] for i in got] == ["https://x/a.pdf"]
    assert got[0]["payload"]["kind"] == "form-cw_dd" and got[0]["payload"]["election"].startswith("DNH&DD")


def test_dd_other_gazette_keeps_nothing(monkeypatch):
    monkeypatch.setattr(cw_dd, "text_of", lambda c, pages=None: ("NOTIFICATION about a tender", "text layer"))
    assert cw_dd.fetch({"url": "u"}, lambda u, **k: _Resp(content=b"%PDF-1.4 x")) == ([], [], "no member list")


def test_ga_pages_and_parse():
    html = (DATA / "cw_ga_previous.html").read_text()
    assert cw_ga.election_pages(html, cw_ga.BASE + "elections/previous/") == [
        ("https://sec.goa.gov.in/elections/previous/municipal-council/", "Municipal Council")]
    assert cw_ga.roman("XII") == 12 and cw_ga.roman("IX") == 9 and cw_ga.roman("4") == 4
    recs = cw_ga.parse((DATA / "cw_ga_winners_sample.txt").read_text(), {"url": "u"})
    assert [r[0] for r in recs] == [f"councillor:GA:ponda:{i}" for i in range(1, 5)]
    d = dict(recs)["councillor:GA:ponda:2"]
    assert d["name"] == "PUNALEKAR VIDHYA SADASHIV" and d["unopposed"] and d["reservation"] == "Women"
    assert d["election"] == "Goa municipal councils 2023" and d["district"] == "South Goa"


def test_ga_items_skip_2021_councils():
    b = cw_ga.BASE
    pages = {b + "elections/previous/municipal-council/":
             '<base href="https://sec.goa.gov.in/"><a href="elections/previous/municipal-council/general-election-2021/">2021</a>'
             '<a href="elections/previous/municipal-council/ponda-sanquelim-2023/">Ponda and Sanquelim 2023</a>',
             b + "elections/ongoing/": "",
             b + "elections/previous/municipal-council/ponda-sanquelim-2023/":
             '<a href="https://sec.goa.gov.in/assets/media/docs/ponda-2023/winning-candidates-ponda.pdf">Winning candidates</a>'
             '<a href="https://sec.goa.gov.in/assets/media/docs/ponda-2023/result-sheet-ponda.pdf">Result sheet</a>'}
    asked = []

    def get(u, **k):
        asked.append(u)
        return _Resp(pages[u]) if u in pages else None
    got = cw_ga.items(get)
    assert [i["payload"]["url"] for i in got] == ["https://sec.goa.gov.in/assets/media/docs/ponda-2023/winning-candidates-ponda.pdf"]
    assert not any("2021" in u for u in asked)


def test_gj_discovery():
    html = (DATA / "cw_gj_index_links.html").read_text()
    pages = cw_gj.result_pages(html, cw_gj.BASE + "index.htm")
    assert "https://sec.gujarat.gov.in/election-oct-2026" in pages and "https://sec.gujarat.gov.in/election-results.htm" in pages
    assert cw_gj.result_pdfs(html, cw_gj.BASE + "index.htm") == []          # the counting press note is not a result file
    assert cw_gj.year_of("નગરપાલિકાની સામાન્ય ચૂંટણી-૨૦૨૫") == 2025 and cw_gj.year_of("2026") == 2026
    assert "https://sec.gujarat.gov.in/images/ahmedabad-corpo.pdf" in cw_gj.known()


def test_gj_items_split_and_store():
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(8):
        w.add_blank_page(100, 100)
    buf = _io.BytesIO()
    w.write(buf)
    old = "https://sec.gujarat.gov.in/images/ahmedabad-corpo.pdf"
    new = "https://sec.gujarat.gov.in/images/pdf/gandhinagar-corpo-2026.pdf"
    page = f'<a href="{old}">Ahmedabad</a><a href="{new}">ગાંધીનગર મહાનગરપાલિકા પરિણામ</a>' \
           '<a href="Portal/News/1_Result Akhbari yadi.pdf">અખબારી યાદી</a>'

    def get(u, **k):
        if u == cw_gj.BASE + "election-oct-2026":
            return _Resp(page)
        if u == new:
            return _Resp(content=buf.getvalue())
        return None
    got = cw_gj.items(get)
    assert [i["payload"]["first"] for i in got] == [1, 7] and got[1]["payload"]["last"] == 8
    assert got[0]["payload"]["election"] == "Gujarat 2026" and got[0]["payload"]["body_type"] == "Municipal Corporation"
    assert "stored" not in got[0]["payload"] and got[1]["payload"]["stored"].startswith("civic-officials-councillors-ocr/councillors/GJ/")


# Real SEC Goa winners files (fetched from dev-vps-3, Mumbai, 2026-11-12): Ponda 2023 and Sanquelim 2023 (ward | name | address in
# columns, names and addresses over 2-3 lines; Sanquelim writes "WARD I (ONE)"), and the Sanquelim ward IX bye-election (mixed case).
def _ga_pdf(name, p):
    from pypdf import PdfReader
    pages = [pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(DATA / name).pages]
    return cw_ga.parse("\n".join(pages), p, pages)


def test_ga_real_files_by_column():
    recs = dict(_ga_pdf("cw_ga_ponda_2023.pdf", {"url": "u"}))
    assert len(recs) == 15
    assert recs["councillor:GA:ponda:2"]["name"] == "DHAVALIKAR VIRENDRA TIMA"
    assert recs["councillor:GA:ponda:14"]["name"] == "NAIK ANAND PANDURANG" and recs["councillor:GA:ponda:14"]["reservation"] == "General"
    assert recs["councillor:GA:ponda:15"]["name"] == "SINAI TALAULICAR GEETALI RAJESH"
    recs = dict(_ga_pdf("cw_ga_sanquelim_2023.pdf", {"url": "u"}))
    assert sorted(int(k.rsplit(":", 1)[1]) for k in recs) == list(range(1, 13))
    d = recs["councillor:GA:sanquelim:5"]
    assert d["name"] == "BLAGGAN PRAVEEN DWARKANATH" and d["unopposed"] and d["reservation"] == "General"
    assert recs["councillor:GA:sanquelim:12"]["reservation"] == "Women"            # not the number word "(TWELEVE)"
    assert recs["councillor:GA:sanquelim:11"]["name"] == "JALMI DEEPA NILESH" and d["district"] == "North Goa"
    assert all(r["src_pos"]["page"] >= 1 and r["src_pos"]["line_text"] for r in recs.values())
    recs = _ga_pdf("cw_ga_sanquelim_bye_ix.pdf", {"url": "u", "title": "Winning Candidates for Ward No.IX of Sanquelim Municipal Council"})
    assert [(k, d["name"], d["reservation"]) for k, d in recs] == [("councillor:GA:sanquelim:9", "Ameshkar Rajendra Ramesh", "OBC")]


def test_ga_orders_are_not_winners():
    html = ('<a href="https://sec.goa.gov.in/assets/media/docs/x/no-of-councilors.pdf">Order regarding Number of Councillors to be elected</a>'
            '<a href="https://sec.goa.gov.in/assets/media/docs/x/DMA-WARD-COUNCILOR.pdf">Order</a>'
            '<a href="https://sec.goa.gov.in/assets/media/docs/x/winning-candidates-ponda.pdf">Winning Candidates Ponda</a>')
    assert [u for u, _ in cw_ga.winners_pdfs(html, cw_ga.BASE)] == ["https://sec.goa.gov.in/assets/media/docs/x/winning-candidates-ponda.pdf"]


def test_mp_gap_preamble_cuts():
    """The 18 OCR'd preamble names without an LGD code in civic.councillor on 2026-11-14 (352 members): 16 now tie;
    पांडल्थाखुर्द (Khargone) stays open (no LGD body is close)."""
    from cforms import cw_mp
    cases = {("आगरमालवा जिला आगर मालवा", "आगरमालवा जिला आगर मालवा", "Municipality"): "250858",
             ("बड़नगर जिला उज्जैन", "बड़नगर जिला उज्जैन", "Municipality"): "250852",
             ("बड़ौद जिला आगर मालवा", "बड़ौद जिला आगर मालवा", "Nagar Parishad"): "250857",      # not Bairad (Shivpuri)
             ("बरेलीं जिंला रायसेन", "बरेलीं जिंला रायसेन", "Nagar Parishad"): "250962",
             ("गाशसिवनी", "बालाघाट", "Municipality"): "251037", ("ह॒ गरप़ालिका परिषद गाडरवाड़ा", "नरसिंहपुर", ""): "250999",
             ("जुन्नारदेव", "छिंदवाड़ा", "Municipality"): "251010", ("कैंटनी", "कटनी", "Municipal Corporation"): "250979",
             ("कानड़ जिला आगर मालवा", "कानड़ जिला आगर मालवा", "Nagar Parishad"): "250859",
             ("क् नगर परिषद मालथान जिला", "क् नगर परिषद मालथान जिला", ""): "297116",
             ("मिहाना जिंलाँ मिण्ड", "मिहाना जिंलाँ मिण्ड", "Nagar Parishad"): "250690",         # not Mandla
             ("नगर-परिषद बड़ागांव जिला आगर मालवा", "नगर-परिषद बड़ागांव जिला आगर मालवा", ""): "250733",
             ("नलखेडा जिला आगर मालवा", "नलखेडा जिला आगर मालवा", "Nagar Parishad"): "250855",
             ("पंरिषद् करेली ह", "नरसिंहपुर", "Municipality"): "251002", ("फूप", "मिंण्ड", "Nagar Parishad"): "250683",
             ("सोयतकलां जिला आगर मालवा", "सोयतकलां जिला आगर मालवा", "Nagar Parishad"): "250853",
             ("पांडल्थाखुर्द", "खरगौन", "Nagar Parishad"): None}
    got = {c: (cw_mp.lgd_of_split(*c) or [None])[0] for c in cases}
    assert got == cases
    assert cw_mp.split_body("बड़ौद जिला आगर मालवा", "बड़ौद जिला आगर मालवा") == ("बड़ौद", "आगर मालवा")
