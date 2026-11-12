"""cforms/mh_np_ocr.py: Maharashtra nagar panchayat notices 2021-22 read from Tesseract word boxes (TSV).

Saved fixtures (tests/data/mh_np_ocr/): the word boxes of the text layer of two notices, written as Tesseract TSV at 300 dpi
(pdftotext -bbox-layout): Kudal (Konkan notice 12, 27 Jan 2022, pages 1-2; Unicode text that drops conjuncts, much like
OCR slips) and Shahapur (Konkan notice 11, 25 Jan 2022, page 3, the English order). The other tests build small TSV pages
in code, laid out like the scans: Gondia (several bodies in one notice, a table continued on the next page), a Konkan group
register, and Raigad (the Marathi list and the English list of the same body).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cforms import mh_np_ocr as m  # noqa: E402

HERE = os.path.dirname(__file__)
LGD = json.load(open(os.path.join(HERE, "..", "cforms", "mh_np_lgd.json")))


def bodies(*codes):
    return [{"lgd_code": k, **LGD[k]} for k in codes]


def data(name):
    return open(os.path.join(HERE, "data", "mh_np_ocr", name)).read()


def tsv(lines, conf=91.0):
    """[(y, [(x, text), ...]), ...] -> Tesseract TSV (one Tesseract line per entry, words 18 px per letter, 40 px high)."""
    out = ["level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]
    for li, (y, ws) in enumerate(lines, 1):
        k = 0
        for x, text in ws:
            for t in text.split():
                k += 1
                out.append(f"5\t1\t1\t1\t{li}\t{k}\t{x}\t{y}\t{18 * len(t)}\t40\t{conf}\t{t}")
                x += 18 * len(t) + 20
    return "\n".join(out)


def test_kudal_two_pages():
    p = {"bodies": bodies("251612"), "url": "u", "notice": "031"}
    recs, why = m.parse_tsv([(1, data("n031-p1.tsv")), (2, data("n031-p2.tsv"))], p)
    d = dict(recs)
    assert len(recs) == 17 and why == ""
    assert [d[f"councillor:MH:251612:{w}"]["ward_no"] for w in range(1, 18)] == [str(w) for w in range(1, 18)]
    r = d["councillor:MH:251612:1"]
    assert r["name"] == "जळवी योती जय" and r["reservation_text"].startswith("सवसाधारण")
    assert r["src_pos"]["page"] == 1 and r["src_pos"]["row"] == 1 and r["src_pos"]["conf"] == 90.0 and r["method"] == m.METHOD
    assert d["councillor:MH:251612:9"]["name"] == "गवंड ेया शेखर"          # the page number "(१)" below is not part of it
    assert d["councillor:MH:251612:10"]["src_pos"]["page"] == 2
    assert r["body_type"] == "Nagar Panchayat" and r["election"] == m.ELECTION and r["lgd_code"] == "251612"


def test_shahapur_english():
    p = {"bodies": bodies("276333", "251487"), "url": "u", "notice": "032"}
    recs, why = m.parse_tsv([(3, data("n032-p3.tsv"))], p)
    d = dict(recs)
    assert len(recs) == 17 and why == "251487: nothing read"     # Murbad is in another notice
    r = d["councillor:MH:276333:5"]
    assert r["name"] == "Bhangare Gayatri Yogesh" and r["reservation"] == "ST woman" and r["body_from"] == "notice text"
    assert d["councillor:MH:276333:12"]["reservation"] == "SC" and r["lang"] == "en"


HEAD_MR = [(1000, [(150, "अ.क्र."), (450, "नगरपंचायतीचे नाव"), (950, "प्रभाग क्रमांक"),
                   (1350, "निवडून आलेल्या सदस्याचे नाव"), (2000, "शेरा")]),
           (1100, [(150, "(१)"), (550, "(२)"), (1000, "(३)"), (1500, "(४)"), (2050, "(५)")])]


def row(y, serial, body, ward, name, resv):
    return (y, [(160, serial)] + ([(500, body)] if body else []) + [(1010, ward), (1400, name), (1950, resv)])


def test_gondia_bodies_and_continued_table():
    p1 = [(300, [(700, "आदेश")]),
          (400, [(150, "मा. राज्य निवडणूक आयोग यांचे आदेशानुसार अर्जुनी मोरगाव नगरपंचायतीच्या सार्वत्रिक निवडणुकीमध्ये")]),
          (460, [(150, "निवडून आलेले सदस्य खालीलप्रमाणे आहेत")])] + HEAD_MR + [
          row(1200, "१", "अर्जुनी", "१", "उईके शिला सुरेश", "अनुसूचित जमाती (महिला)"),
          row(1300, "२", "", "२", "उपवंशी सपना सेवकराम", "अनुसूचित जमाती"),
          row(1400, "३", "", "३", "दामले सुषमा नानाजी", "अनुसूचित जाती (महिला)"),
          (3300, [(1100, "(१)")])]
    p2 = [(150, [(300, "महाराष्ट्र शासन राजपत्र असाधारण भाग एक-अ-नागपूर विभागीय पुरवणी")]),
          (300, [(1000, "अनुसूची—चालू")]),
          (400, [(150, "(१)"), (550, "(२)"), (1000, "(३)"), (1500, "(४)"), (2050, "(५)")]),
          row(500, "४", "अर्जुनी", "४", "भेंडारकर राधेश्याम गजानन", "सर्वसाधारण"),
          row(600, "५", "", "५", "शहारे यशकुमार ज्ञानदेव", "अनुसूचित जाती"),
          (900, [(700, "आदेश")]),
          (1000, [(150, "मा. राज्य निवडणूक आयोग यांचे आदेशानुसार सडक अर्जुनी नगरपंचायतीच्या सार्वत्रिक निवडणुकीमध्ये")])] + \
        [(y + 200, ws) for y, ws in HEAD_MR] + [
          row(1400, "१", "सडक अर्जुनी", "१", "कापगते रेखा मनोहर", "सर्वसाधारण (महिला)"),
          row(1500, "२", "", "२", "भेंडारकर अनिल गोविंदा", "नागरिकांचा मागास प्रवर्ग"),
          (2000, [(150, "गोंदिया,"), (1800, "नयना गुंडे,")]),
          (2060, [(1800, "जिल्हाधिकारी, गोंदिया.")])]
    p = {"bodies": bodies("276366", "276363", "276368"), "url": "u", "notice": "110"}
    recs, why = m.parse_tsv([(1, tsv(p1)), (2, tsv(p2))], p)
    d = dict(recs)
    assert sorted(k for k in d if ":276366:" in k) == [f"councillor:MH:276366:{w}" for w in "12345"]
    assert sorted(k for k in d if ":276368:" in k) == ["councillor:MH:276368:1", "councillor:MH:276368:2"]
    assert d["councillor:MH:276366:4"]["name"] == "भेंडारकर राधेश्याम गजानन" and d["councillor:MH:276366:4"]["page"] == 2
    assert d["councillor:MH:276366:1"]["reservation"] == "ST woman" and d["councillor:MH:276366:1"]["body_from"] == "body"
    assert d["councillor:MH:276368:2"]["reservation"] == "OBC"
    assert d["councillor:MH:276368:1"]["src_pos"]["block"] == 2
    assert "276363: nothing read" in why and "276366: 5 of 17 wards read" in why


def test_group_register():
    pg = [(300, [(700, "अधिसूचना")]),
          (400, [(150, "वाभवे-वैभववाडी नगरपंचायतीमधील नगरविकास आघाडी गटाची नोंद")]),
          (1000, [(150, "अ.क्र."), (450, "नगरपंचायतीचे नाव"), (1000, "नगरसेवकाचे नाव"), (1700, "नगरपंचायत गटाचे नाव")]),
          (1100, [(150, "(१)"), (550, "(२)"), (1150, "(३)"), (1850, "(४)")]),
          (1200, [(160, "१"), (420, "वाभवे-वैभववाडी नगरपंचायत"), (1000, "माईणकर नेहा दिपक"), (1600, "वाभवे-वैभववाडी नगरविकास आघाडी")]),
          (1300, [(160, "२"), (1000, "बावदाणे रेवा रामचंद्र")]),
          (1400, [(160, "३"), (1000, "चव्हाण संगिता बजरंग")]),
          (1700, [(150, "सिंधुदुर्गनगरी,"), (1700, "के. मंजुलक्ष्मी,")])]
    p = {"bodies": bodies("263834"), "url": "u", "notice": "026"}
    recs, why = m.parse_tsv([(1, tsv(pg))], p)
    d = dict(recs)
    assert sorted(d) == [f"councillor:MH:263834:grp-026-1-{i}" for i in (1, 2, 3)]
    r = d["councillor:MH:263834:grp-026-1-1"]
    assert r["name"] == "माईणकर नेहा दिपक" and r["group"] == "वाभवे-वैभववाडी नगरविकास आघाडी"
    assert r["list"] == "group register (no ward)" and "ward_no" not in r and why == ""


def test_marathi_and_english_lists_merge():
    mr = [(300, [(700, "आदेश")]), (400, [(150, "पाली नगरपंचायतीच्या सार्वत्रिक निवडणुकीमध्ये")]),
          (1000, [(150, "अ.क्र."), (450, "निवडून आलेल्या सदस्याचे नाव"), (1150, "प्रभाग क्र."), (1600, "शेरा")]),
          (1100, [(150, "(१)"), (550, "(२)"), (1200, "(३)"), (1750, "(४)")]),
          (1200, [(160, "१"), (450, "ठोंबरे जुईली श्रीकांत"), (1210, "१"), (1600, "सर्वसाधारण (महिला)")]),
          (1300, [(160, "२"), (450, "कल्याणी संदीप डाकी"), (1210, "२"), (1600, "सर्वसाधारण (महिला)")]),
          (1600, [(150, "अलिबाग,"), (1700, "जिल्हाधिकारी, रायगड.")])]
    en = [(200, [(700, "BY THE COLLECTOR OF RAIGAD")]), (300, [(800, "Order")]),
          (400, [(150, "the names of person who have been declared elected as Councillors of the Nagar Panchayat Pali")]),
          (1000, [(150, "Sr. No."), (400, "Name of the Councillor Elected"), (1150, "Ward No."), (1600, "Remark")]),
          (1100, [(150, "(1)"), (550, "(2)"), (1200, "(3)"), (1750, "(4)")]),
          (1200, [(160, "1"), (400, "Thombare Juili Shrikant"), (1210, "1"), (1600, "General (Women)")]),
          (1300, [(160, "2"), (400, "Kalyani Sandeep Dapke"), (1210, "2"), (1600, "General (Women)")]),
          (1600, [(150, "Alibag,"), (1700, "Collector, Raigad.")])]
    p = {"bodies": bodies("300027", "276270"), "url": "u", "notice": "034"}
    recs, why = m.parse_tsv([(1, tsv(mr)), (3, tsv(en))], p)
    d = dict(recs)
    assert sorted(d) == ["councillor:MH:300027:1", "councillor:MH:300027:2"]
    r = d["councillor:MH:300027:1"]
    assert r["name"] == "Thombare Juili Shrikant" and r["name_local"] == "ठोंबरे जुईली श्रीकांत"
    assert r["reservation"] == "General woman" and r["src_pos"]["page"] == 3 and r["src_pos_local"]["page"] == 1


def test_body_names_longest_first():
    b = bodies("276366", "276368")
    assert m.body_in("सडक अर्जुनी नगरपंचायत", b)["lgd_code"] == "276368"
    assert m.body_in("अर्जुनी मोरगाव नगरपंचायत", b)["lgd_code"] == "276366"
    assert m.body_in("Lonand Nagarpanchayat Prabhag No. 4", bodies("276414", "276381"))["lgd_code"] == "276414"
    assert m.ward_of("Lonand Nagarpanchayat Prabhag No. 10.") == "10" and m.ward_of("प्रभाग क्रमांक ७") == "7"


def test_col_row():
    line = {"words": [{"text": t, "x0": i * 300, "x1": i * 300 + 60} for i, t in enumerate(["(१)", "(२)", "(३)", "(४)"])]}
    assert m.col_row(line) == [30.0, 330.0, 630.0, 930.0]
    line["words"][1]["text"] = "उईके"
    line["words"][2]["text"] = "शिला"
    assert m.col_row(line) is None


def test_rotation_pages():
    p = {"rotate": 90, "rotate_pages": [2, 13]}
    assert m.rotation(p, 1) == 0 and m.rotation(p, 2) == 90 and m.rotation({"rotate": 270}, 5) == 270


def test_satara_form_iv_rows_by_gap():
    """English Form IV (Satara, scanned sideways): no serial column, cells wrap over several lines, the ward is in the
    constituency cell, rows are apart by a blank gap."""
    head = [(800, [(100, "Name of the"), (450, "Father's/"), (700, "Name of the"), (1100, "Name of")]),
            (850, [(100, "Councillor/"), (450, "Husband's"), (700, "Constituency"), (1100, "Political Party")]),
            (900, [(100, "Member"), (450, "Name"), (700, "from which"), (1100, "or Aghadi")]),
            (950, [(100, "1"), (480, "2"), (760, "3"), (1150, "4")])]
    rows = [(1050, [(100, "SHELKE"), (450, "Nanaji"), (700, "Lonand"), (1100, "Nationalist")]),
            (1100, [(100, "SACHIN"), (700, "Nagarpanchayat"), (1100, "Congress")]),
            (1150, [(700, "Prabhag No. 4")]),
            (1300, [(100, "KHARAT"), (450, "Vaibhav"), (700, "Lonand"), (1100, "Nationalist")]),
            (1350, [(100, "SEEMA"), (700, "Nagarpanchayat"), (1100, "Congress")]),
            (1400, [(700, "Prabhag No.10.")])]
    p = {"bodies": bodies("276414", "276383"), "url": "u", "notice": "060"}
    recs, why = m.parse_tsv([(2, tsv(head + rows))], p)
    d = dict(recs)
    assert sorted(d) == ["councillor:MH:276414:10", "councillor:MH:276414:4"]
    r = d["councillor:MH:276414:4"]
    assert r["name"] == "SHELKE SACHIN" and r["father_or_husband"] == "Nanaji" and r["party"] == "NCP"
    assert r["body_from"] == "ward"


def test_name_next_to_nagar_panchayat_wins():
    b = bodies("276414", "276383")
    assert m.body_in("नगरपंचायतीचे नाव : लोणंद नगरपंचायत, लोणंद, तालुका खंडाळा, जिल्हा सातारा", b)["lgd_code"] == "276414"
