"""Madhya Pradesh: Chief Executive Officer of every Janpad Panchayat (CEO JP, मुख्य कार्यपालन अधिकारी जनपद पंचायत: the head of the
block panchayat = the block development officer of MP), from the Janpad pages of Panchayat Darpan (mppanchayatdarpan.gov.in, Panchayat
and Rural Development Department, run by NIC Bhopal). The department site prd.mp.gov.in (Who Is Who) did not answer dev-vps-3 on
2026-11-13, and the archive copy (2026-11-05) has no rows.

Panchayat Darpan "Panchayat Website" search (/panchayat/Search.aspx) is an ASP.NET page: district list (52 site ids, the districts
before Maihar, Pandhurna and Mauganj were made) -> the page's own handler /Handlers/localbodies.ashx?DistrictID=<id>&LBTypeID=6
(JSON {"columns": ["LBID", "LBName"], "rows": [[24157, " AGAR"], ...]}: the janpads) -> postback of "View Details"
(ctl00$ContentPlaceHolder1$btnView with hdnDistrict and hdnLBID) -> redirect to the janpad page
/Panchayat/Default.aspx?QS=..&ID=... The janpad page names the CEO (span lblCEO_Name, Latin capitals), the post
(lblCEO_Designation, Hindi), the janpad (lbl_Panchayat_Name "जनपद पंचायत, AGAR") and the office address (profile "पता :"). It gives
no phone or email. The president box (lbl_President) said "जानकारी उपलब्ध नहीं" (no information) on the checked page; not read.

One queue item per site district: 1 GET (search page) + 1 GET (janpad list) + 1 POST per janpad (about 6 per district, 313 in
all; each answer about 100 kB). Answered dev-vps-3 (Mumbai) on 2026-11-13; abroad not checked.
Records (dept rural_development, level block): area = the janpad name (title case, as LGD writes blocks), district = LGD district
(janpads of the new districts Maihar, Pandhurna, Mauganj go there by the LGD block list, dforms/sub4_mp_blocks.json from
lgd.blocks), lgd_block_code when the name matches an LGD block of that district, office_id = the site's LBID, address.
Record ids: dept:sub4_mp_jp:<site district id>:<LBID>.
"""
import json
import re
from pathlib import Path

import provenance
from dforms import _esw

METHOD = "html (ASP.NET postback answers: janpad page spans lblCEO_Name / lblCEO_Designation) + json (localbodies.ashx janpad list)"

MODULE = "sub4_mp_jp"
BASE = "https://mppanchayatdarpan.gov.in"
SEARCH = BASE + "/panchayat/Search.aspx"
LIST = BASE + "/Handlers/localbodies.ashx?DistrictID={}&LBTypeID=6"
POST = "Chief Executive Officer, Janpad Panchayat"
# site district id -> (LGD district code, LGD name); from the search page's district list, 2026-11-13
DISTRICTS = {
    "51": ("667", "Agar-Malwa"), "49": ("639", "Alirajpur"), "47": ("390", "Anuppur"), "46": ("391", "Ashoknagar"),
    "45": ("392", "Balaghat"), "28": ("393", "Barwani"), "35": ("394", "Betul"), "3": ("395", "Bhind"), "32": ("396", "Bhopal"),
    "48": ("397", "Burhanpur"), "9": ("398", "Chhatarpur"), "43": ("399", "Chhindwara"), "12": ("400", "Damoh"), "5": ("401", "Datia"),
    "23": ("402", "Dewas"), "25": ("403", "Dhar"), "41": ("404", "Dindori"), "7": ("406", "Guna"), "4": ("407", "Gwalior"),
    "36": ("408", "Harda"), "26": ("410", "Indore"), "39": ("411", "Jabalpur"), "24": ("412", "Jhabua"), "38": ("413", "Katni"),
    "29": ("405", "Khandwa (East Nimar)"), "27": ("414", "Khargone (West Nimar)"), "42": ("415", "Mandla"), "19": ("416", "Mandsaur"),
    "2": ("417", "Morena"), "37": ("409", "Narmadapuram"), "40": ("418", "Narsimhapur"), "18": ("419", "Neemuch"), "52": ("722", "Niwari"),
    "10": ("420", "Panna"), "34": ("421", "Raisen"), "30": ("422", "Rajgarh"), "20": ("423", "Ratlam"), "14": ("424", "Rewa"),
    "11": ("425", "Sagar"), "13": ("426", "Satna"), "33": ("427", "Sehore"), "44": ("428", "Seoni"), "16": ("429", "Shahdol"),
    "22": ("430", "Shajapur"), "1": ("431", "Sheopur"), "6": ("432", "Shivpuri"), "17": ("433", "Sidhi"), "50": ("638", "Singrauli"),
    "8": ("434", "Tikamgarh"), "21": ("435", "Ujjain"), "15": ("436", "Umaria"), "31": ("437", "Vidisha")}
NEW = {"784": "Maihar", "785": "Pandhurna", "766": "MAUGANJ"}   # LGD districts made after the site's list
BLOCKS = json.loads((Path(__file__).parent / "sub4_mp_blocks.json").read_text())   # LGD district code -> {block name: block code}


def items(get=None):
    return [{"key": f"{MODULE}-{i}", "payload": {"reader": MODULE, "url": SEARCH, "district_id": i, "state": "MP",
                                                  "india_only": False}} for i in DISTRICTS]


def key(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def lgd_block(name, dc):
    """(LGD district code, block code) for a janpad: first in its site district, then in the new districts."""
    k = key(name)
    for d in [dc] + list(NEW):
        for b, code in BLOCKS.get(d, {}).items():
            if key(b) == k:
                return d, code
    return dc, ""


def hidden(html):
    s = _esw.soup(html)
    return {i["name"]: i.get("value", "") for i in s.find_all("input", attrs={"type": "hidden"}) if i.get("name")}


def janpads(text):
    try:
        d = json.loads(text)
    except ValueError:
        return []
    out = []
    for i, row in enumerate(d.get("rows") or []):
        if len(row) >= 2 and str(row[0]).strip().isdigit():
            out.append((str(row[0]).strip(), _esw.clean(str(row[1]))))
    return out


def span(s, sid):
    e = s.find(id="ctl00_ContentPlaceHolder1_" + sid)
    return _esw.clean(e.get_text(" ")) if e else ""


NONE = re.compile(r"जानकारी\s*उपलब्ध\s*नहीं")


def page(html):
    """{name, designation, body, address} of one janpad page."""
    s = _esw.soup(html)
    out = {"name": span(s, "lblCEO_Name"), "designation": span(s, "lblCEO_Designation"), "body": span(s, "lbl_Panchayat_Name")}
    t = _esw.clean(s.get_text(" "))
    m = re.search(r"पता\s*:\s*(.+?)\s*(?:Information about|ग्राम पंचायत|$)", t)
    out["address"] = m.group(1).strip() if m else ""
    if NONE.search(out["name"]):
        out["name"] = ""
    return out


def title(s):
    return " ".join(w.capitalize() for w in s.split())


def record(did, lbid, lbname, info, url, r=None):
    dc, dname = DISTRICTS[did]
    area = title(lbname)
    dc2, code = lgd_block(area, dc)
    if dc2 != dc:
        dname = NEW[dc2].title() if NEW[dc2].isupper() else NEW[dc2]
    rid, d = _esw.record(MODULE, f"{did}:{lbid}", dept="rural_development", level="block", area=area,
                         area_regional=info.get("body"), district=dname, district_code=dc2, state="MP", name=info.get("name"),
                         post=POST, designation=info.get("designation"), address=info.get("address"), office_id=lbid,
                         lgd_block_code=code or None, source=url, vacant=None if info.get("name") else True,
                         src_pos={"element": "span#ctl00_ContentPlaceHolder1_lblCEO_Name", "janpad": lbid})
    d.update(provenance.at(r, url) if r is not None else {"src_url": url})
    return rid, d


def fetch(p, get):
    did = str(p.get("district_id") or "")
    if did not in DISTRICTS:
        return [], [], "unknown district id"
    r = get(SEARCH)
    if r is None:
        return [], [], "no answer (search page)"
    form = hidden(r.text)
    lr = get(LIST.format(did))
    if lr is None:
        return [], [], "no answer (janpad list)"
    jps = janpads(lr.text)
    if not jps:
        return [], [], "no janpads"
    recs, files, fails = [], [_esw.keep(MODULE, f"{did}-list", lr.content, "json")], 0
    for lbid, name in jps:
        data = dict(form)
        data.update({"__EVENTTARGET": "ctl00$ContentPlaceHolder1$btnView", "__EVENTARGUMENT": "",
                     "ctl00$ContentPlaceHolder1$ddlDistrict_DD": did, "ctl00$ContentPlaceHolder1$hdnDistrict": did,
                     "ctl00$ContentPlaceHolder1$hdnLBID": lbid, "ctl00$ContentPlaceHolder1$hdnGp": "0",
                     "ctl00$ContentPlaceHolder1$hdntypeID": "0"})
        jr = get(SEARCH, method="POST", data=data)
        if jr is None or "lblCEO_Name" not in (jr.text or ""):
            fails += 1
            continue
        url = getattr(jr, "url", "") or SEARCH
        files.append(_esw.keep(MODULE, f"{did}-{lbid}", jr.content))
        recs.append(record(did, lbid, name, page(jr.text), url, jr))
    why = "" if recs else "no janpad pages"
    if recs and fails:
        why = ""   # partial: the records name what was read
    return recs, files, why
