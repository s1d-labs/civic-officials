"""Jammu and Kashmir: the officers and field staff of every panchayat halqa, from the "Panchayat Secretary" directory of the
Department of Rural Development and Panchayati Raj (jkpanchayat.jk.gov.in/officersdirectory.php; open, no login, no captcha;
answers from abroad and from Mumbai, 2026-11-13).

Structure (measured 2026-11-13): the home page chains three selects through ajaxData.php (POST, answers <option> lists):
division=<Kashmir|Jammu> -> districts; district=<District> -> blocks; block=<Block> -> panchayats (values = names as written,
e.g. "Baramulla", "Behrampora A"). officersdirectory.php?panchayat=<P>&block=<B> (GET) gives one HTML table for that halqa:
Sno | Panchayat (District, Block) ("Chanum (District : Baramulla, Block : Rafiabad)") | Name | Mobile No | Aadhar Card No |
Designation | Department. Without a panchayat the page shows only the first 50 rows of the whole state.
Each halqa lists the BDO of its block, the Secretary Panchayat / VLW / MPW / GRS / Panchayat Inspector, the Patwari (revenue),
and line staff of other departments (PHE / Jal Shakti, PDD, health ASHA, Anganwadi workers, agriculture, REW engineers, NRLM).

Records: one per row, dept from the Department column (DEPTS), level gram_panchayat, area = the panchayat halqa, block, district
(LGD); post = the designation as written. Rows whose designation is the BDO give ONE record per block and person instead (level
block, area = block, post "Block Development Officer", panchayats = the halqas that list that person). Rows of a halqa page that
name another block or district are dropped (the page filter is by name). The "Aadhar Card No" column is not copied into the
records (an Aadhaar number is an identity number, not a contact; the column is empty on most rows; the trail keeps the page as
answered): records note aadhaar_column_filled=true when the source cell was not empty.
One queue item per district: 1 POST (blocks) + 1 POST per block (panchayats) + 1 GET per panchayat (about 100-500 requests).
Record ids: dept:sub4_jk_rdd:<district>:<block>:<panchayat>:<row> and dept:sub4_jk_rdd:<district>:<block>:bdo:<name>.
"""
import re
from urllib.parse import quote

from dforms import _esw, _trail
import provenance

METHOD = "html table (halqa pages of the RD&PR directory; selects from ajaxData.php)"     # source trail (provenance.py)

MODULE = "sub4_jk_rdd"
BASE = "https://jkpanchayat.jk.gov.in/"
AJAX = BASE + "ajaxData.php"
# division -> district values of the select (2026-11-13), and LGD district codes (lgd.districts, state 1)
DIVISIONS = {"Kashmir": ["ANANTNAG", "Bandipora", "Baramulla", "BUDGAM", "GANDERBAL", "KULGAM", "KUPWARA", "PULWAMA", "SHOPIAN",
                         "SRINAGAR"],
             "Jammu": ["Doda", "JAMMU", "Kathua", "Kishtwar", "Poonch", "Rajouri", "Ramban", "Reasi", "Samba", "Udhampur"]}
LGD = {"anantnag": ("1", "Anantnag"), "bandipora": ("623", "Bandipora"), "baramulla": ("3", "Baramulla"), "budgam": ("2", "Budgam"),
       "doda": ("4", "Doda"), "ganderbal": ("626", "Ganderbal"), "jammu": ("5", "Jammu"), "kathua": ("7", "Kathua"),
       "kishtwar": ("620", "Kishtwar"), "kulgam": ("622", "Kulgam"), "kupwara": ("8", "Kupwara"), "poonch": ("10", "Poonch"),
       "pulwama": ("11", "Pulwama"), "rajouri": ("12", "Rajouri"), "ramban": ("621", "Ramban"), "reasi": ("627", "Reasi"),
       "samba": ("624", "Samba"), "shopian": ("625", "Shopian"), "srinagar": ("13", "Srinagar"), "udhampur": ("14", "Udhampur"),
       "badgam": ("2", "Budgam")}
# Department column (lower case, first match) -> dept key (civic-india TAGGING.md)
DEPTS = ((r"rural|rdd|panchayati|nrlm|rew", "rural_development"), (r"revenue", "revenue"), (r"\bpdd\b|power", "electricity"),
         (r"jal\s*shakti|\bphe\b|water", "water"), (r"health", "health"), (r"social\s*welfare|icds", "women_child"),
         (r"educat|school", "education"), (r"agricult|horticult|farmer|animal|sheep|fisher", "agriculture"),
         (r"forest", "forest"), (r"food|fcs", "food_supplies"))
BDO = re.compile(r"(?i)^\s*(b\.?\s*d\.?\s*o\.?|block\s+development\s+officer)\b")
HALQA = re.compile(r"^(.*?)\s*\(\s*District\s*:\s*(.*?)\s*,\s*Block\s*:\s*(.*?)\s*\)\s*$", re.I)


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def district_of(name):
    return LGD.get(key(name), ("", _esw.clean(name).title()))


def items(get=None):
    return [{"key": f"sub4_jk_rdd-{key(d)}", "payload": {"reader": MODULE, "division": div, "district": d, "state": "JK",
                                                         "india_only": False, "route": "abroad"}}
            for div, ds in DIVISIONS.items() for d in ds]


def options(html):
    """<option> values of an ajaxData.php answer, without the "Select ..." entry."""
    out = []
    for m in re.finditer(r"<option[^>]*value=\"([^\"]*)\"", html or "", re.I):
        v = _esw.clean(m.group(1).replace("&amp;", "&"))
        if v and v not in out:
            out.append(v)
    return out


def dept_of(text):
    t = (text or "").lower()
    for pat, d in DEPTS:
        if re.search(pat, t):
            return d
    return "other"


def phone(s):
    d = re.sub(r"[\s-]", "", s or "")
    return d if re.fullmatch(r"\+?\d{6,13}", d) else _esw.clean(s)


def page_rows(html):
    """[(cells, src_pos)] of the halqa table: cells = [sno, halqa, name, mobile, aadhaar, designation, department]."""
    sp = _esw.soup(html)
    out = []
    for t in sp.find_all("table"):
        head = [_esw.clean(c.get_text(" ")) for c in (t.find("tr").find_all(["th", "td"]) if t.find("tr") else [])]
        if not any("Designation" in h for h in head) or not any("Panchayat" in h for h in head):
            continue
        for tr in t.find_all("tr")[1:]:
            cells = [_esw.clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if len(cells) >= 7 and any(cells[1:4]):
                out.append((cells[:7], _trail.tr_pos(tr)))
            else:
                provenance.skip_row(tr, 'skip: not (len(cells) >= 7 and any(cells[1:4]))')
    return out


def build(district, block, pages):
    """pages: [(panchayat, url, html)] of one block -> records."""
    code, dname = district_of(district)
    recs, bdos = [], {}
    for gp, url, html in pages:
        for cells, pos in page_rows(html):
            sno, halqa, name, mobile, aadhaar, desig, dept_txt = cells
            m = HALQA.match(halqa)
            h_gp, h_dist, h_block = (m.group(1), m.group(2), m.group(3)) if m else (halqa, district, block)
            if key(h_block) != key(block) or key(h_dist) != key(district):
                provenance.skip_row(cells, 'skip: key(h_block) != key(block) or key(h_dist) != key(district)')
                continue
            if not name and not mobile:
                provenance.skip_row(cells, 'skip: not name and not mobile')
                continue
            extra = {"aadhaar_column_filled": True} if re.search(r"\d", aadhaar or "") else {}
            if BDO.match(desig):
                k = (key(name), re.sub(r"\D", "", mobile))
                if k in bdos:
                    bdos[k][1]["panchayats"].append(h_gp or gp)
                    continue
                rid, d = _esw.record(MODULE, f"{_esw.slug(dname)}:{_esw.slug(block)}:bdo:{_esw.slug(name) or k[1]}",
                                     dept="rural_development", level="block", area=block, block=block, district=dname,
                                     district_code=code, state="JK", name=name, post="Block Development Officer",
                                     designation=desig, department=dept_txt, phone=phone(mobile), source=url, src_url=url,
                                     src_pos=pos, **extra)
                d["panchayats"] = [h_gp or gp]
                bdos[k] = (rid, d)
                continue
            recs.append(_esw.record(MODULE, f"{_esw.slug(dname)}:{_esw.slug(block)}:{_esw.slug(h_gp or gp)}:{sno or pos.get('row')}",
                                    dept=dept_of(dept_txt), level="gram_panchayat", area=h_gp or gp, block=block, district=dname,
                                    district_code=code, state="JK", name=name, post=desig, department=dept_txt,
                                    phone=phone(mobile), list_no=sno, source=url, src_url=url, src_pos=pos, **extra))
    # two people listed as BDO of one block (halqa pages not all updated): keep both, say how many halqas name each
    for rid, d in bdos.values():
        d["listed_by_panchayats"] = len(d["panchayats"])
        recs.append((rid, d))
    seen, out = set(), []
    for rid, d in recs:
        r, i = rid, 2
        while r in seen:
            r, i = f"{rid}:{i}", i + 1
        seen.add(r)
        out.append((r, d))
    return out


def gp_url(gp, block):
    return f"{BASE}officersdirectory.php?panchayat={quote(gp)}&block={quote(block)}"


def fetch(p, get):
    district = p["district"]
    r = get(AJAX, method="POST", data={"district": district})
    blocks = options(r.text) if r is not None else []
    if not blocks:
        return [], [], "no blocks"
    recs, failed = [], 0
    for block in blocks:
        r = get(AJAX, method="POST", data={"block": block})
        gps = options(r.text) if r is not None else []
        pages = []
        for gp in gps:
            url = gp_url(gp, block)
            a = get(url)
            if a is None:
                failed += 1
                continue
            pages.append((gp, url, a.text))
        recs += build(district, block, pages)
    return recs, [], "" if recs else (f"no rows ({failed} halqa pages did not answer)" if failed else "no rows")
