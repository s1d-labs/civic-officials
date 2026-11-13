"""Offline tests of dforms/vil_mh_talathi.py (Maharashtra Talathi / Gram Mahsul Adhikari per saja and Circle Officers).
Samples: tests/data/vil_mh_talathi_jamkhed.pdf (Ahilyanagar collectorate, Jamkhed tahsil list, fetched once 2026-11-13 from
cdn.s3waas.gov.in) and vil_mh_talathi_jalna_partur.html (the table of the archive.s1d.me copy of jalna.gov.in/en/partur-taluka/,
saved 2026-11-06). No test touches the network."""
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod

M = "vil_mh_talathi"
PDF = "https://cdn.s3waas.gov.in/s345fbc6d3e05ebd93369ce542e8f2322d/uploads/2023/06/2023063036.pdf"
JALNA = "https://jalna.gov.in/en/partur-taluka/"


def run(url, sample, **p):
    recs, files, why = mod(M).fetch(dict(url=url, state="MH", **p), fake_get({url: sample}))
    assert why == "" and files and files[0][0].startswith(f"depts/{M}/"), why
    check_records(recs, M, "revenue")
    return recs


def test_jamkhed_pdf():
    recs = run(PDF, "vil_mh_talathi_jamkhed.pdf", district="Ahilyanagar", tehsil="Jamkhed", tag="ahilyanagar-jamkhed")
    sajas = [d for _, d in recs if d["level"] == "village"]
    circles = [d for _, d in recs if d["level"] == "circle"]
    assert len(circles) == 5 and len(sajas) == 33
    # every village of the list (serials 1-86) sits in one saja, in order
    serials = [int(x) for d in sajas for x in d["village_serials"]]
    assert serials == list(range(1, 87))
    assert all(d["email"].startswith("tal.") and d["email"].endswith("@mah.gov.in") for d in sajas)
    s = sajas[0]
    assert (s["area"], s["name"], s["phone"], s["email"]) == ("Jamakhed", "VISHWAJIT CHOUGALE", "9850716710",
                                                              "tal.jamkhed-jam@mah.gov.in")
    assert s["villages"] == ["Jamakhed", "Dhotri", "Batewadi", "Chumbhali", "Jamadarawadi"]
    assert s["circle"] == "Jamkhed" and s["circle_officer"] == "Nandkumar Gavhane" and s["tehsil"] == "Jamkhed"
    assert s["post"].startswith("Talathi") and s["post_regional"].startswith("ग्राम महसूल अधिकारी")
    assert s["src_pos"]["page"] == 1 and "9850716710" in s["src_pos"]["line_text"]
    c = circles[0]
    assert (c["area"], c["name"], c["phone"], c["email"]) == ("Jamkhed", "Nandkumar Gavhane", "9764815549",
                                                              "co-jamkhed-jam@mah.gov.in")
    assert [d["area"] for d in circles] == ["Jamkhed", "Aranagaon", "Nannaj", "Nayagaon", "Kharda"]


def test_jalna_html():
    recs = run(JALNA, "vil_mh_talathi_jalna_partur.html", district="Jalna", tehsil="Partur")
    sajas = [d for _, d in recs if d["level"] == "village"]
    circles = [d for _, d in recs if d["level"] == "circle"]
    assert len(sajas) == 35 and len(circles) == 6
    s = sajas[1]
    assert (s["area"], s["name"], s["phone"], s["charge"]) == ("Amba", "Shri.G.R.Kute", "9823224723", "Additional")
    assert s["villages"] == ["Amba", "Masla"] and s["circle"] == "Partur" and s["circle_officer"] == "Shri.N.N. Pathan"
    assert circles[0]["phone"] == "9823182567" and circles[0]["name"] == "Shri.N.N. Pathan"
    # the Marathi headers of the same table (jalna.gov.in/?p=35999) give the same roles
    assert mod(M).roles(["अ.क्र.", "मंडळ विभाग", "मंडळ अधिकारी यांचे नांव", "ग्राम महसूल अधिकारी यांचे नांव", "मोबाईल क्रमांक",
                         "मुळ/अति", "तलाठी सजा", "सजातर्गत असलेली गावे"]) == {
        0: "sno", 1: "circle", 2: "co_name", 3: "talathi", 4: "phone", 5: "charge", 6: "saja", 7: "villages"}
    assert s["src_pos"]["table"] == 1


def test_seeds():
    seeds = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())
    assert len(seeds) == 15 and len({s["key"] for s in seeds}) == 15
    assert all(s["payload"]["reader"] == M and s["payload"]["state"] == "MH" and s["payload"].get("route") for s in seeds)
    assert mod(M).items() == seeds
