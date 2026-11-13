"""Bareilly Nagar Nigam (nagarnigambareilly.com): the sanitation inspector and the sanitation supervisors (safai nayak) of each of
its 10 sanitation wards, from "Cleaning inspector list of cleaning works" (/Download/WorkPlanSafai/SafaiNayak.pdf, linked from the
home page; live copy 2026-11-13 from Mumbai, 29.7 MB, 11 pages, sha256 e0a6185e...; not in archive.s1d.me). The file is a scan
(doPDF, no text layer). Each page: "सफाई अभियान का कार्यक्रम / सफाई वार्ड नं0 NN / सफाई निरीक्षक का नाम : श्री <name> (मोबाइल नं0 <mobile>)",
then a table: क्र0 सं0 | सफाई नायक का नाम व मोबाइल नं0 | सम्मिलित मोहल्ले (localities) | the day-wise work plan (Monday ...
Saturday). Page 4 repeats page 3 (both headed "सफाई वार्ड नं0 03"; its rows are the same five names): read once.
The names and mobiles were read BY EYE from the rendered pages (no OCR on this server; rows below, with page and row); this
reader fetches the file (the source trail copies it), checks that it is the file the rows were read from (sha256) and gives the
records. The localities and the work plan are not read (still in the saved file). A "sanitation ward" (सफाई वार्ड) is a group
of council wards and mohallas, not a council ward: records are at level "zone", area "Sanitation Ward NN", wards_note says so.
Records: the inspector of each sanitation ward (wing sanitation, role head; one inspector serves two sanitation wards: one record
with both in sanitation_wards) and each safai nayak (one record per mobile; a row with two persons gives two records; a person
whose row has no mobile gets the row number in the id). Names and posts are Hindi: name / name_regional, post_regional.
Record ids: dept:ward3_bareilly:<inspector|supervisor>:<mobile or sw<NN>-row<n>>. All rows unchecked against a second reading.
"""
import io
import re

import provenance
from dforms import _esw, _ward

METHOD = "scanned PDF: inspector and safai nayak rows read by eye from the rendered pages (page + row), file checked by sha256"

MODULE = "ward3_bareilly"
BODY, LGD, STATE, DISTRICT = "Bareilly Nagar Nigam", "249149", "UP", "Bareilly"
URL = "https://nagarnigambareilly.com/Download/WorkPlanSafai/SafaiNayak.pdf"
SHA256 = "e0a6185e8b19e73638227cc1edd98a9d4db7e6c5c44d340dbaeb2199eb4627c1"
NOTE = ("sanitation ward of Bareilly Nagar Nigam (a group of mohallas, not a council ward); localities and the day-wise plan are "
        "in the source file")

# page -> (sanitation ward as printed, inspector name, inspector mobile)
HEADS = {1: ("01", "श्री संजीव कुमार", "7055519621"), 2: ("02", "श्री संजीव कुमार", "7055519621"),
         3: ("03", "श्री राकेश गंगवार", "7055519619"), 5: ("04", "श्री राकेश गंगवार", "7055519619"),
         6: ("05", "श्री एम0सी0 राना", "7055519620"), 7: ("06", "श्री एम0सी0 राना", "7055519620"),
         8: ("07", "श्री दीपक कुमार", "7055519618"), 9: ("08", "श्री दीपक कुमार", "7055519618"),
         10: ("09", "श्री साविर अली", "7055519615"), 11: ("10", "श्री साविर अली", "7055519615")}
# (page, row, name, mobile or "")
ROWS = (
    (1, 1, "श्री दीपक", "9259612086"), (1, 2, "श्री सागर", "9267009754"), (1, 3, "श्री कमल", "9634258580"),
    (1, 3, "श्री ओमकार", "9897830885"), (1, 4, "श्री प्रदीप", "8937049770"), (1, 4, "श्री सुरेन्द्र", "9759704314"),
    (1, 5, "श्री राजेन्द्र", "9627603738"), (1, 6, "श्री राकेश कठेरिया", "9897608166"), (1, 7, "श्री सुधीर", ""),
    (1, 8, "श्री पंकज", "9997606600"), (1, 9, "श्री संजय", "9457381847"),
    (2, 1, "श्री राकेश ऋषिवाल", "9917531464"), (2, 2, "श्री राम किशोर", "9634442662"), (2, 3, "श्री जितेन्द्र", "7534870255"),
    (2, 4, "श्री हसनैन", "8923932601"), (2, 5, "श्री सत्य प्रकाश", "9027585568"), (2, 6, "श्री राजू गौर्या", "9675919510"),
    (2, 7, "श्री शिव कुमार", ""), (2, 8, "श्री मनोज", "7669620514"), (2, 9, "श्री मुनीष आनन्द", "9639721372"),
    (3, 1, "श्री सुशील", "9286703794"), (3, 2, "श्री शिव कुमार", "7669528475"), (3, 3, "श्री हवासिंह", "8979628883"),
    (3, 4, "श्री मनोहर लाल", "8755251537"), (3, 5, "श्री गोपाल", "8273128190"),
    (5, 1, "श्री सुरेन्द्र", "9557095044"), (5, 2, "श्री संतोष", "8006089918"), (5, 3, "श्री ज्ञान चन्द्र", "9319067309"),
    (5, 4, "श्री राजेश कुमार", "9837250168"), (5, 5, "श्री राजेश मसीह", "9259479473"), (5, 6, "श्री भगवत सरन", "8077931884"),
    (5, 7, "श्री विष्णु आनन्द", "9897293297"), (5, 8, "श्री किशन लाल", "9411221471"), (5, 9, "श्री राम गोपाल", "8899585565"),
    (6, 1, "श्री महक सिंह", "9720776026"), (6, 1, "श्री राकेश", "8057115573"), (6, 2, "श्री हशमत खां", "9639900307"),
    (6, 3, "श्री रामगुलाम", "8755508184"), (6, 4, "श्री राकेश चौधरी", "9359506614, 8126693187"), (6, 5, "श्री अशोक", "9456624982"),
    (6, 6, "श्री कमल", "8171749700"), (6, 7, "श्री संजय", "9634801468"), (6, 8, "श्री महेश चन्द्र", "9759390863"),
    (6, 9, "श्री अमर दीप", "7599062137"), (6, 10, "श्री सुरेश", "9045783870"),
    (7, 1, "श्री घनश्याम", "9897855570"), (7, 2, "श्री सुबोध", "9368641849"), (7, 3, "श्री राजकुमार", "9897608224"),
    (7, 4, "श्रीमती सुरजीत प्रेमी", "9412428226"), (7, 5, "श्री सुरेश शिन्दे", "9319382960"), (7, 6, "श्री धर्मवीर", "8791803086"),
    (7, 7, "श्री अनिल", ""), (7, 8, "श्री राज कुमार", "9897608224"),
    (8, 1, "श्री इम्तियाज", "9528744323"), (8, 2, "श्री राजेश कश्यप", "9058124441"), (8, 3, "श्री सोमपाल", "8273104850"),
    (8, 4, "श्री कमल", "7351060130"), (8, 5, "श्री राजकुमार", "9897830358"), (8, 6, "श्री राज कुमार आनन्द", "9219748761"),
    (8, 7, "श्री विशेष गौरव", "9219710100"),
    (9, 1, "श्री रवि कुमार", "8445117365"), (9, 2, "श्री सुनील", "9557055195"), (9, 3, "श्री मनोज", "8439417964"),
    (9, 4, "श्री प्रमोद", "7310941600"), (9, 5, "श्री अंगूर मोहम्मद", "9696060843"), (9, 5, "श्री कृष्ण गोपाल", "8273011030"),
    (9, 6, "श्री राजीव कुमार सिंह", "9358577025"), (9, 7, "श्री मयंक", "9675137563"),
    (10, 1, "श्री राजेश", "9368956951"), (10, 2, "श्री राजेन्द्र समदर्शी", "9696998395"), (10, 3, "श्रीमती सुनीता", "8192970922"),
    (10, 4, "श्री मो0 सद्दीक", "9634172551"), (10, 5, "श्री सोनू", ""),
    (11, 1, "श्री दीप कुमार", "8445425419"), (11, 2, "श्री राकेश भारती", "7500024193"), (11, 3, "श्री रंजीत सिंह", "9917391688"),
    (11, 4, "श्री सुरेश", "9012013196"), (11, 5, "सुरेश पाल", ""),
)


def items(get=None):
    return [{"key": f"{MODULE}-safai-nayak", "payload": {"reader": MODULE, "url": URL, "state": STATE, "sha256": SHA256,
                                                         "pages": 11}}]


def area(sw):
    return f"Sanitation Ward {sw}"


def records(p, src):
    seen, recs = set(), []
    insp = {}
    for page, (sw, name, mob) in sorted(HEADS.items()):
        g = insp.setdefault(mob, {"name": name, "sws": [], "pos": []})
        g["sws"].append(sw)
        g["pos"].append({"page": page, "line": "header", "read": "by eye from the rendered scan"})
    for mob, g in insp.items():
        recs.append(_ward.record(MODULE, f"inspector:{mob}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=" & ".join(area(s) for s in g["sws"]), zone=area(g["sws"][0]),
                                 sanitation_wards=g["sws"], post="Sanitary Inspector", post_regional="सफाई निरीक्षक",
                                 name=g["name"], name_regional=g["name"], phone=mob, wing="sanitation", role="head",
                                 wards_note=NOTE, source=URL, src_pos=g["pos"][0] if len(g["pos"]) == 1 else
                                 {"rows": g["pos"], "note": "one inspector over these sanitation wards"}, **src))
    nayak = {}
    for page, row, name, mob in ROWS:
        sw = HEADS[page][0]
        k = mob or f"sw{sw}-row{row}"
        g = nayak.setdefault(k, {"name": name, "phone": mob, "sws": [], "pos": []})
        if sw not in g["sws"]:
            g["sws"].append(sw)
        g["pos"].append({"page": page, "row": row, "read": "by eye from the rendered scan"})
    for k, g in nayak.items():
        insp_name, insp_mob = next((n, m) for s, n, m in HEADS.values() if s == g["sws"][0])
        recs.append(_ward.record(MODULE, f"supervisor:{re.sub(r'[^0-9a-z-]', '', k.split(',')[0])}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="zone", area=" & ".join(area(s) for s in g["sws"]),
                                 zone=area(g["sws"][0]), sanitation_wards=g["sws"], post="Sanitation Supervisor (Safai Nayak)",
                                 post_regional="सफाई नायक", name=g["name"], name_regional=g["name"], phone=g["phone"],
                                 wing="sanitation", role="staff", reports_to=f"{insp_name} ({insp_mob})", wards_note=NOTE,
                                 source=URL, src_pos=g["pos"][0] if len(g["pos"]) == 1 else
                                 {"rows": g["pos"], "note": "same mobile on these rows"}, **src))
    return recs


def pages_of(content):
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:
        return None


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    body = r.content or b""
    if not body.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [(f"depts/{MODULE}/SafaiNayak.pdf", body, "application/pdf")]
    src = provenance.at(r, p["url"])
    if p.get("sha256") and src.get("src_sha256") != p["sha256"]:
        # the rows were read from another file: do not put them on this one
        return [], files, f"file changed (sha256 {src.get('src_sha256', '')[:12]}, rows read from {p['sha256'][:12]}): read the rows again"
    n = pages_of(body) if p.get("pages") else None
    if n is not None and n < p["pages"]:
        return [], files, f"file has {n} pages, rows name page {p['pages']}"
    recs = records(p, src)
    for _, d in recs:
        d["method"] = METHOD
    return recs, files, ""
