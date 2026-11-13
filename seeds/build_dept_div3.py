"""Build seeds/dept_div3_<st>.json (2026-11-13): division-level officers for divisions that had none in DB civic.
Run on the server (reads district names from DB civic, schema lgd):  python seeds/build_dept_div3.py

Sources, found in archive.s1d.me first, then live from dev-vps-3 (OVH Mumbai, at most 3 GETs per host):
  - the headquarters district's S3WaaS Who's Who / directory, which also lists the Divisional Commissioner, the zone IG and the
    range DIG (dforms/st_div_pages.py with "sections" / "keep": only those rows are read);
  - state pages that list every division (Assam GAD "Divisions", HP revenue courts list: st_div_pages "division_col");
  - state lists of officer postings (dforms/st_div_postlist.py): West Bengal IAS postings as on 06.11.2026, Gujarat IPS civil
    list as on 01.01.2026 (range IGs), Maharashtra IPS/SPS quarterly list as on 06.08.2026 (Amravati Range IG).
Routes: S3WaaS hosts "abroad" (other S3WaaS portals answer GitHub runners; unchecked for these), the other hosts "direct" with
india_only true. "checked" says where each page was seen.
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_CODE = {"AS": "18", "BR": "10", "CG": "22", "GJ": "24", "HP": "2", "HR": "6", "JH": "20", "MH": "27", "ML": "17", "OD": "21",
              "PB": "3", "WB": "19"}
ALIASES = {"69": ["Mahendergarh", "Narnaul"], "62": ["Gurgaon"], "604": ["Mewat"]}
ARCH = "archive.s1d.me copy 2026-11-05..11 (saved from India)"
LIVE = "answered dev-vps-3 (Mumbai) 2026-11-13"


def abroad(checked):
    return {"india_only": False, "route": "abroad", "route_note": f"{checked}; abroad unchecked (S3WaaS)"}


def direct(checked):
    return {"india_only": True, "route": "direct", "route_note": f"{checked}; abroad unchecked"}


PAGES = {
    "JH": [
        {"key": "div3-jh-santhal-pargana", "division": "Santhal Pargana", "urls": ["https://dumka.nic.in/about-district/whos-who/"],
         "sections": r"(?i)division", "note": "Dumka who's who, table 'Divisional Level Officer': Commissioner, IG, DIG",
         **abroad(ARCH)},
        {"key": "div3-jh-north-chotanagpur", "division": "North Chotanagpur", "urls": ["https://hazaribag.nic.in/whos-who/"],
         "sections": r"(?i)commissioner officials", **abroad(ARCH)},
        {"key": "div3-jh-palamu", "division": "Palamu", "urls": ["https://palamu.nic.in/directory/"],
         "keep": r"(?i)^commissioner palamu|to commissioner\b|\bI\.?G\.? palamu|D\.I\.G\.? palamu|palamu (zone|range)",
         "header_kinds": {r"(?i)^office$": "phone"}, **abroad(ARCH)},
        {"key": "div3-jh-south-chotanagpur", "division": "South Chotanagpur", "urls": ["https://ranchi.nic.in/whos-who/"],
         "keep": r"(?i)^divisional commissioner", **abroad(ARCH)},
    ],
    "BR": [
        {"key": "div3-br-bhagalpur", "division": "Bhagalpur", "urls": ["https://bhagalpur.nic.in/directory/"],
         "sections": r"(?i)bhagalpur division", **abroad(ARCH)},
    ],
    "CG": [
        {"key": "div3-cg-durg", "division": "Durg", "urls": ["https://durg.gov.in/en/about-district/whos-who/"],
         "sections": r"(?i)commissioner durg division", **abroad(ARCH)},
        {"key": "div3-cg-raipur", "division": "Raipur", "urls": ["https://raipur.gov.in/en/directory/"],
         "keep": r"(?i)^commissioner raipur", **abroad(ARCH)},
    ],
    "PB": [
        {"key": "div3-pb-ferozepur", "division": "Ferozepur", "urls": ["https://ferozepur.nic.in/contact-directory/"],
         "keep": r"(?i)^divisional commissioner|ferozepur range", **abroad(ARCH)},
        {"key": "div3-pb-jalandhar", "division": "Jalandhar", "urls": ["https://jalandhar.nic.in/about-district/whos-who/"],
         "sections": r"(?i)commissioner jalandhar division", **abroad(ARCH)},
        {"key": "div3-pb-jalandhar-range", "division": "Jalandhar", "urls": ["https://jalandhar.nic.in/keycontacts/"],
         "header_kinds": {r"(?i)office name": "post"}, "keep": r"(?i)^DIG Jalandhar Range", **abroad(ARCH)},
        {"key": "div3-pb-faridkot", "division": "Faridkot", "urls": ["https://faridkot.nic.in/commissioner-faridkot-division-faridkot/"],
         **abroad(ARCH)},
    ],
    "HR": [
        {"key": "div3-hr-ambala", "division": "Ambala", "urls": ["https://ambala.gov.in/whos-who/"],
         "sections": r"(?i)^commissioner ambala division", **abroad(ARCH)},
        {"key": "div3-hr-faridabad", "division": "Faridabad", "urls": ["https://faridabad.nic.in/whos-who/"],
         "keep": r"(?i)^commissioner faridabad division", **abroad(ARCH)},
        {"key": "div3-hr-karnal", "division": "Karnal", "urls": ["https://karnal.gov.in/whos-who/"],
         "note": "the who's who under 'Divisional Commissioner Karnal': the Commissioner and the office staff", **abroad(ARCH)},
        {"key": "div3-hr-rohtak", "division": "Rohtak", "urls": ["https://rohtak.gov.in/whos-who/"],
         "sections": r"(?i)commissioner rohtak division", **abroad(ARCH)},
        {"key": "div3-hr-gurugram", "division": "Gurugram", "urls": ["https://rewari.gov.in/whos-who/"],
         "sections": r"(?i)gurugram division", "note": "Rewari who's who (Gurugram division)", **abroad(ARCH)},
    ],
    "ML": [
        {"key": "div3-ml-tura", "division": "Tura", "kind": "police", "body": "Western Range, Meghalaya Police",
         "urls": ["https://westgarohills.gov.in/directory/"], "sections": r"(?i)\bDIG\b",
         "note": "DIG Western Range, Tura: the range covers the Garo Hills districts (= Tura division)", **abroad(ARCH)},
    ],
    "WB": [
        {"key": "div3-wb-burdwan", "division": "Burdwan", "urls": ["https://hooghly.nic.in/important-telephone-number/"],
         "header_kinds": {r"(?i)name of the offices": "post"}, "keep": r"(?i)divisional commissioner",
         "note": "office phones of the Divisional Commissioner, Burdwan Division (Chinsurah); no name", **abroad(ARCH)},
    ],
    "OD": [
        {"key": "div3-od-southern", "division": "Southern", "urls": ["https://rdcsdbmp.nic.in/whos-who/"], **abroad(LIVE)},
        {"key": "div3-od-southern-rdc", "division": "Southern", "urls": ["https://rdcsdbmp.nic.in/department/department-1/"],
         "keep": r"(?i)^revenue divisional commissioner \|",
         "note": "the S3WaaS 'Department 1' list: only the RDC row (office phone); its other rows are template text", **abroad(LIVE)},
    ],
    "AS": [
        {"key": "div3-as-divisions", "division": "Lower Assam", "urls": ["https://gad.assam.gov.in/divisions"],
         "default_post": "Commissioner", "division_col": r"(?i)division name", "header_kinds": {r"(?i)divisional office": "address"},
         "note": "GAD 'Divisions': the five Commissioners with phones (the Central Assam row repeats the Lower Assam phones)",
         **direct(LIVE)},
    ],
    "HP": [
        {"key": "div3-hp-courts", "division": "Shimla", "urls": ["https://rms.hp.gov.in/CourtsList.aspx"],
         "header_kinds": {r"(?i)^court$": "post", r"(?i)office address": "address"}, "keep": r"(?i)^divisional commissioner-",
         "division_col": r"(?i)^court$", "division_rx": r"(?i)divisional commissioner-\s*(\w+)",
         "note": "Revenue court list: the three Divisional Commissioner offices with address only (no name, no phone)",
         **direct(ARCH)},
    ],
}

WB_DIV = [("Presidency", r"presidency\s+division"), ("Burdwan", r"(?:bardhaman|burdwan)(?:\s+division)?"),
          ("Medinipur", r"medinipur(?:\s+division)?"), ("Jalpaiguri", r"jalpaiguri(?:\s+division)?"), ("Malda", r"malda(?:\s+division)?")]
GJ_DIV = [("Ahmedabad Range", "Ahmedabad"), ("Gandhinagar Range", "Gandhinagar"), ("Vadodara Range", "Vadodara"),
          ("Surat Range", "Surat"), ("Junagadh Range", "Junagadh"), ("Rajkot Range", "Rajkot"), ("Border Range", "Border"),
          ("Bhavnagar Range", "Bhavnagar"), ("Panchmahal-Godhra Range", r"Panchmahal[-, ]*Godha?ra")]
LISTS = {
    "WB": [{"key": "div3-wb-ias-postings", "kind": "revenue", "as_on": "06.11.2026",
            "list_title": "Posting of IAS Officers as on 06.11.2026 (Personnel & Administrative Reforms Department)",
            "url": "https://par.wb.gov.in/writereaddata/WBCSdirectory/Posting%20of%20IAS%20Officers%20as%20on%2006112026.pdf",
            "first_rx": r"^\s*(?P<sno>\d{1,3})\.\s+\d{4}\s+(?P<name>\S.*?)\s{2,}(?P<post>\S.*?)\s*$",
            "posts": [{"rx": r"(?i)(?:(?:additional|addl\.?|assistant|asst\.?|joint|deputy|special)\s+)?(?:divisional\s+)?commissioner,\s*" + rx,
                       "division": d} for d, rx in WB_DIV],
            "note": "the file name changes with each update: par.wb.gov.in/wbcsdirectory.php names the newest", **direct(LIVE)}],
    "GJ": [{"key": "div3-gj-ips-civil-list", "kind": "police", "as_on": "01.01.2026 (updated up to 26.01.2026)",
            "list_title": "List of members of the Indian Police Service (Gujarat cadre) as on 1st January 2026",
            "url": "https://www.police.gujarat.gov.in/upload/IPS_Civil_List-2026_Web18022026.pdf",
            "first_rx": r"^\s{0,3}(?P<sno>\d{1,3})\s{3,}(?P<name>\S.*?)\s+IPS/\S+\s+(?:\d{4}\s+)?\d\d/\d\d/\d{4}\s+\d\d/\d\d/\d{4}\s+(?P<post>\S.*?)(?:\s{2,}|$)",
            "break_rx": r"^\s{0,3}\d{1,3}\s{3,}(?:Shri|Smt|Dr|Ms|Kum|Miss|Mr)\b",
            "posts": [{"rx": r"(?i)(?:(?:special|addl\.?|additional|deputy)\s+)?inspector\s+general\s+of\s+police,?\s*(?:[\w.-]+\s+)?" + w + r"\s+range",
                       "division": d} for d, w in GJ_DIV], **direct(ARCH)}],
    "MH": [{"key": "div3-mh-ips-sps-quarterly", "kind": "police", "as_on": "06.08.2026",
            "list_title": "Quarterly list of Officers of the Indian Police Service and State Police Service as on 06/08/2026",
            "url": "https://www.mahapolice.gov.in/uploads/posting_details/be63db846f01fbde3fef5066673080ef.pdf",
            "first_rx": r"^\s{0,8}(?P<sno>\d{1,3})\.?\s{2,}(?P<post>\S.*?)\s{2,}(?P<name>\(?(?:Shri|Smt|Dr|Ms|Kum|Miss|Vacant)\b.*?)(?:\s{2,}|$)",
            "phone_rx": r"\b(0\d{2,4})\s*[/-]\s*(\d{6,8})\b",
            "posts": [{"rx": r"(?i)(?:spl\.?\s*|special\s+)?(?:I\.?\s?G\.?\s?P|inspector general of police)\s*,\s*amravati range",
                       "division": "Amravati Range"}], **direct(ARCH)}],
}


def district_names(code):
    out = subprocess.run(["psql", "-d", "civic", "-At", "-F", "\t", "-c",
                          f"select district_code, district_name from lgd.districts where state_code = '{code}'"],
                         capture_output=True, text=True, check=True).stdout
    names = {}
    for line in out.splitlines():
        c, n = line.split("\t")
        names[c] = [n] + ALIASES.get(c, [])
    return names


def main():
    for st in sorted(set(PAGES) | set(LISTS)):
        out = []
        if st in PAGES:
            names = district_names(STATE_CODE[st])
            out += [{"key": f"st_div_pages:{it['key']}",
                     "payload": {"reader": "st_div_pages", "state": st, "all_division": True, **it, "district_names": names}}
                    for it in PAGES[st]]
        out += [{"key": f"st_div_postlist:{it['key']}", "payload": {"reader": "st_div_postlist", "state": st, **it}}
                for it in LISTS.get(st, [])]
        (HERE / f"dept_div3_{st.lower()}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print(st, len(out))


if __name__ == "__main__":
    main()
