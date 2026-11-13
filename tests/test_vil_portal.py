"""Offline tests of dforms/vil_portal.py (finder of village official lists on district portals). Samples: the archive.s1d.me
copies of ahilyanagar.maharashtra.gov.in/en/ and /en/circle-officer-and-talathi/ (saved 2026-11-12) and the Jamkhed tahsil PDF
(tests/data/vil_mh_talathi_jamkhed.pdf) standing in for every tahsil PDF. No test touches the network."""
import json

from esw_common import ROOT, fake_get, mod

M = "vil_portal"
HOME = "https://ahilyanagar.maharashtra.gov.in/en/"
PAGE = "https://ahilyanagar.maharashtra.gov.in/en/circle-officer-and-talathi/"


def test_links():
    html = (ROOT / "tests" / "data" / "vil_portal_ahilyanagar_home.html").read_text()
    off, teh = mod(M).links(html, HOME)
    assert off == [PAGE]
    assert all("seniority" not in u and "recruit" not in u for u in off + teh)


def test_portal_reads_found_lists():
    get = fake_get({HOME: "vil_portal_ahilyanagar_home.html", PAGE: "vil_portal_ahilyanagar_talathi.html",
                    (lambda u, m, d: u.startswith("https://cdn.s3waas.gov.in/") and u.endswith(".pdf")): "vil_mh_talathi_jamkhed.pdf"})
    recs, files, why = mod(M).fetch({"url": HOME, "state": "MH", "district": "Ahilyanagar"}, get)
    assert why == "", why
    pdf_calls = [u for _, u, _ in get.calls if u.endswith(".pdf")]
    assert len(pdf_calls) == mod(M).MAX_PDFS        # 14 tahsil PDFs linked, the cap holds
    sajas = [d for _, d in recs if d.get("level") == "village"]
    assert len(sajas) == 33 * len(pdf_calls) and all(d["post"].startswith("Talathi") for d in sajas)
    assert all(r.startswith("dept:vil_portal:") for r, _ in recs) and len({r for r, _ in recs}) == len(recs)
    assert all(d["src_url"] in pdf_calls for d in sajas)
    assert files[0][0] == "depts/vil_portal/ahilyanagar.maharashtra.gov.in-home.html.gz"


def test_html_patwari_table():
    html = """<table><tr><th>क्र.</th><th>राजस्व निरीक्षक मंडल</th><th>पटवारी हल्का क्रमांक/नाम</th><th>पटवारी का नाम</th>
    <th>मोबाइल नंबर</th><th>शामिल ग्राम</th></tr><tr><td>1</td><td>बरगी</td><td>12 - बरगी</td><td>रामलाल पटेल</td>
    <td>9425012345</td><td>बरगी, खमरिया</td></tr></table>"""
    recs = mod("vil_mh_talathi").parse_html(html, {"state": "MP", "district": "Jabalpur"}, "https://x.nic.in/p/", module=M)
    s = [d for _, d in recs if d["level"] == "village"]
    assert len(s) == 1 and s[0]["post"] == "Patwari" and s[0]["area"] == "12 - बरगी" and s[0]["name"] == "रामलाल पटेल"
    assert s[0]["phone"] == "9425012345" and s[0]["villages"] == ["बरगी", "खमरिया"] and s[0]["state"] == "MP"


def test_seeds():
    seeds = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())
    assert len(seeds) == 141 and len({s["key"] for s in seeds}) == len(seeds)
    assert {s["payload"]["state"] for s in seeds} == {"MH", "MP", "CG", "GJ", "GA"}
