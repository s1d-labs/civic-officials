"""Build seeds/dept_div4.json (2026-11-15): division heads for divisions of DB civic that still had no official after the
div3 seeds (civic.division without a civic.state_official row). Run anywhere:  python seeds/build_dept_div4.py
(district names are copied from seeds/dept_div_hr.json and seeds/dept_div_ka.json; no database needed).

Items (each source answered dev-vps-3, OVH Mumbai, 2026-11-15; abroad unchecked, so route "direct", india_only):
  - Haryana Police, Rohtak Range: the range telephone page moved from /static/TelephoneDirectory_rtk.aspx (now a 301 to the
    name without ".aspx"; the old item st_div_pages:hr-police-rtk gave up on 2026-11-13) to
    https://haryanapolice.gov.in/static/TelephoneDirectory_rtk ("Updated on 21.10.2026": IGP Rohtak Range and the SPs of
    Charkhi Dadri, Rohtak, Bhiwani). The other four range pages redirect the same way; their records of 2026-11-13 are kept
    (a new url gives new record ids), so only Rohtak is queued here.
  - Karnataka, Regional Commissioner Bengaluru Division: https://rcb.karnataka.gov.in/20/Officers%20Details/en (the
    karnataka.gov.in CMS, as rckalaburagi; "/info-1/Officers+Details/en" answers 307 to it). "About Us" (/26/About%20Us/en)
    lists the 9 districts of dforms/st_div_ka.json "Bengaluru" (Ramanagara = Bengaluru South).
  - Chhattisgarh GAD, "Civil List of IAS Officers 2026, as on 02nd November, 2026" (made 2026-11-11):
    https://gad.cg.gov.in/ias/view_preview.aspx?fn=CL/2026/11/0483, read by dforms/st_div_postlist.py with "post_end_rx" and
    "name_rx": Commissioner, Bastar Division (entry 59) and Commissioner, Bilaspur Division (entry 58). The other three CG
    divisions already have a commissioner from district pages, so only these two rules.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKED = "answered dev-vps-3 (Mumbai) 2026-11-15; abroad unchecked"
DIRECT = {"india_only": True, "route": "direct", "route_note": CHECKED}


def names(seed):
    return json.loads((HERE / seed).read_text())[0]["payload"]["district_names"]


def items():
    hr = names("dept_div_hr.json")
    ka = names("dept_div_ka.json")
    out = [
        {"key": "st_div_pages:div4-hr-rohtak-range", "payload": {
            "reader": "st_div_pages", "state": "HR", "key": "div4-hr-rohtak-range", "division": "Rohtak Range", "kind": "police",
            "body": "Rohtak Range, Haryana Police", "urls": ["https://haryanapolice.gov.in/static/TelephoneDirectory_rtk"],
            "districts": ["701", "73", "59"], **DIRECT, "district_names": hr}},
        {"key": "st_div_pages:div4-ka-bengaluru", "payload": {
            "reader": "st_div_pages", "state": "KA", "key": "div4-ka-bengaluru", "division": "Bengaluru",
            "urls": ["https://rcb.karnataka.gov.in/20/Officers%20Details/en"], **DIRECT, "district_names": ka}},
        {"key": "st_div_postlist:div4-cg-ias-civil-list", "payload": {
            "reader": "st_div_postlist", "state": "CG", "key": "div4-cg-ias-civil-list", "kind": "revenue",
            "as_on": "02.11.2026", "list_title": "Civil List of IAS Officers 2026, as on 02nd November, 2026",
            "url": "https://gad.cg.gov.in/ias/view_preview.aspx?fn=CL/2026/11/0483",
            "first_rx": r"^\s{0,3}(?P<sno>\d{1,3})\s{3,}(?P<name>\S.*?)\s{2,}(?:\S.*?\s{2,})?\d\d\s?/\s?\d\d\s?/\s?\d{4}\s+"
                        r"(?P<post>\S.*?)(?:\s{3,}|$)",
            "post_end_rx": r"\s{2,}Level\s+\d|\s{2,}\d\d-\s*$",
            "name_rx": r"^\s{3,}(?P<name>(?:Dr\.\s|Smt\.\s|Shri\s)?[A-Z][A-Za-z.]*(?:\s[A-Z][A-Za-z.]*)+)\s{2,}",
            "posts": [{"rx": r"(?i)\bcommissioner,\s*bastar\s+division", "division": "Bastar"},
                      {"rx": r"(?i)\bcommissioner,\s*bilaspur\s+division", "division": "Bilaspur"}],
            **DIRECT}},
    ]
    return out


if __name__ == "__main__":
    (HERE / "dept_div4.json").write_text(json.dumps(items(), ensure_ascii=False, indent=1) + "\n")
    print("seeds/dept_div4.json:", len(items()), "items")
