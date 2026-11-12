"""Tamil Nadu: ward members elected in the casual (bye-) elections of 2022 to urban bodies, and the late general poll of
Kadambur town panchayat (Thoothukudi), from tnsec.tn.gov.in (answers only from India).

Pages (tnsec_static/election_results/): rulbe2022/rulbe2022.php "ஊரக மற்றும் நகர்ப்புற உள்ளாட்சி (தற்செயல்) தேர்தல் முடிவுகள் - 2022"
(rural and urban casual elections 2022) and ulbetp2022/ulbetp2022.php (Kadambur, 12 wards). Each page is a district form:
POST cmb_district=<code> (37 districts on the casual page; no Chennai) gives the district's files, opened by
window.open('<file>.pdf'). Urban files: corp_<d>.pdf (corporation), mun_<d>.pdf (municipality), tp_<d>.pdf (town panchayat);
rural files (vpp_, vpwm_, puwm_, dpwm_) are not urban bodies and are not read. The PDFs are the same mPDF layout as the 2022
general results, so cforms/tn_text.py reads them.
TNSEC lists no casual elections after 2022 on its results page (checked 2026-11-12).

seed: items(get) posts the district form of the casual page once per district and lists one form-tn_casual item per urban file.
form-tn_casual: reads the PDF with tn_text; a casual-election winner gets bye_election = true, "replaces" = the record id of the
2022 general-election winner of the same ward (councillor:TN:tx:<type>-<district>:<body>:<ward>), and its own id with the suffix
":bye2022". The loader marks the replaced record stale (seat filled again).
"""
import re

from cforms import tn_text

METHOD = tn_text.METHOD

BASE = "https://tnsec.tn.gov.in/tnsec_static/election_results/"
CASUAL = BASE + "rulbe2022/rulbe2022.php"
KADAMBUR = BASE + "ulbetp2022/ulbetp2022.php"
ELECTION_CASUAL = "Tamil Nadu urban local bodies casual election 2022 (TNSEC, தற்செயல் தேர்தல்)"
ELECTION_KADAMBUR = "Tamil Nadu 2022 (Kadambur town panchayat, poll held apart from the general poll)"
URBAN = re.compile(r"^(corp|mun|tp)_([a-z]{3})\.pdf$")
DISTRICTS = re.compile(r'<option value="([a-z]{3})">\s*([^<]+?)\s*</option>')
FILE = re.compile(r"window\.open\('([^']+\.pdf)'")


def districts(html):
    return DISTRICTS.findall(html or "")


def files(html):
    """Urban result files on a district answer: [(type, district code, file name)]."""
    out = []
    for f in FILE.findall(html or ""):
        m = URBAN.match(f)
        if m and (m.group(1), m.group(2), f) not in out:
            out.append((m.group(1), m.group(2), f))
    return out


def item(page, kind, dist_code, dist_name, f, casual):
    url = page.rsplit("/", 1)[0] + "/" + f
    p = {"kind": "form-tn_casual", "state": "TN", "url": url, "type": kind, "district_code": dist_code, "district": dist_name,
         "election": ELECTION_CASUAL if casual else ELECTION_KADAMBUR, "list_url": page}
    if casual:
        p.update({"bye_election": True, "id_suffix": ":bye2022"})
    return {"key": f"tn-casual-{'2022' if casual else 'kadambur'}-{kind}-{dist_code}", "payload": p}


def items(get):
    out = []
    for page, casual in ((CASUAL, True), (KADAMBUR, False)):
        r = get(page)
        if r is None:
            continue
        for code, name in districts(r.text):
            a = get(page, method="POST", data={"cmb_district": code})
            if a is None:
                continue
            for kind, dc, f in files(a.text):
                out.append(item(page, kind, dc, name, f, casual))
    return out


def fetch(p, get):
    recs, fl, why = tn_text.fetch(p, get)
    for _, d in recs:
        d["list_url"] = p.get("list_url")
    return recs, fl, why
