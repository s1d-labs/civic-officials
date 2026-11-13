"""Build seeds/dept_div_<st>.json: division-level pages that dforms/st_div_pages.py (and, for S3WaaS English pages,
dforms/st_div_s3waas.py) read (2026-11-13). Run on the server (reads district names from DB civic, schema lgd):
    python seeds/build_dept_div.py
Every page below answered dev-vps-3 (OVH Mumbai) on 2026-11-13 with one GET. Abroad was not checked: S3WaaS hosts are seeded
"abroad" (other S3WaaS portals answer GitHub runners), the other hosts "direct" with india_only true.
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_CODE = {"BR": "10", "HR": "6", "JK": "1", "KA": "29", "MH": "27", "OD": "21"}
ALIASES = {"69": ["Mahendergarh", "Narnaul"], "200": ["Kaimur", "Bhabua"], "211": ["West Champaran", "Bettiah"],
           "213": ["East Champaran", "Motihari"], "482": ["मुंबई शहर", "Mumbai City"], "483": ["मुंबई उपनगर"], "497": ["ठाणे"],
           "665": ["पालघर"], "491": ["रायगड"], "492": ["रत्नागिरी"], "495": ["सिंधुदुर्ग"], "538": ["Kalburgi", "Gulbarga"],
           "527": ["Belgaum"], "530": ["Vijayapur", "Bijapur"], "62": ["Gurgaon"], "604": ["Mewat"]}
DIRECT = {"india_only": True, "route": "direct", "route_note": "answered dev-vps-3 (Mumbai) 2026-11-13; abroad unchecked"}
ABROAD = {"india_only": False, "route": "abroad", "route_note": "answered dev-vps-3 (Mumbai) 2026-11-13; abroad unchecked (S3WaaS)"}
HRP = "https://haryanapolice.gov.in/static/TelephoneDirectory_{}.aspx"
# Haryana Police ranges: the SPs each range page lists (2026-11-13); the same lists go to dforms/st_div_hr.json "police_ranges"
HR_RANGES = {"Ambala Range": ("ambala", ["58", "76", "68"]), "Hisar Range": ("hisar", ["63", "74", "65", "792", "61"]),
             "Karnal Range": ("karnal", ["66", "67", "71"]), "Rohtak Range": ("rtk", ["701", "73", "59"]),
             "South Range": ("southrange", ["72", "619", "69", "604"])}

ITEMS = {
    "KA": [
        {"key": "ka-kalaburagi", "division": "Kalaburagi", "urls": ["https://rckalaburagi.karnataka.gov.in/107/officers-details/en"],
         "office": [{"url": "https://rckalaburagi.karnataka.gov.in/18/contact-us/en", "post": "Regional Commissioner"}], **DIRECT},
        {"key": "ka-belagavi", "division": "Belagavi", "urls": [],
         "office": [{"url": "https://rcbelagavi.karnataka.gov.in/34/contact-us/en", "post": "Regional Commissioner"}], **DIRECT},
    ],
    "BR": [
        {"key": "br-magadh", "division": "Magadh", "urls": ["https://magadhdivision.bihar.gov.in/whoiswho.php",
                                                           "https://magadhdivision.bihar.gov.in/contact_commissioner.php"], **DIRECT},
    ],
    "MH": [
        {"key": "mh-konkan", "division": "Konkan",
         "urls": ["https://divcomkonkan.gov.in/e0-a4-a8-e0-a4-bf-e0-a4-b0-e0-a5-8d-e0-a4-a6-e0-a5-87-e0-a4-b6-e0-a4-bf-e0-a4-95-e0-a4-be-mr/"],
         **ABROAD},
    ],
    "JK": [
        {"key": "jk-police-zones", "division": "Jammu", "kind": "police", "body": "Jammu and Kashmir Police",
         "urls": ["https://jkpolice.gov.in/Zonal-Range-Hqrs"], "table_divisions": {"1": "Jammu", "2": "Kashmir"},
         "police_unit_rx": r"(?i)\b(rajouri|doda|jammu|udhampur)[\w -]*range\b|\b(NKR|SKR|CKR)\b[\w ]*",
         "office": [{"url": "https://jkpolice.gov.in/Zonal-Range-Hqrs", "post": "IGP Jammu Zone", "anchor": r"Jammu Zone\nJ&K",
                     "division": "Jammu", "police_unit": "Jammu Zone"},
                    {"url": "https://jkpolice.gov.in/Zonal-Range-Hqrs", "post": "IGP Kashmir Zone", "anchor": r"Kashmir Zone\nJ&K",
                     "division": "Kashmir", "police_unit": "Kashmir Zone"}],
         "note": "the Jammu and Kashmir police zones cover the same districts as the two revenue divisions", **DIRECT},
    ],
    "HR": [
        {"key": f"hr-police-{slug}", "division": rng, "kind": "police", "body": f"{rng}, Haryana Police", "urls": [HRP.format(slug)],
         "districts": codes, **DIRECT} for rng, (slug, codes) in HR_RANGES.items()
    ],
}
S3WAAS = {}
ITEMS["OD"] = [{"key": "od-northern", "division": "Northern", "urls": ["https://rdcsambalpur.nic.in/whos-who/"],
                "office": [{"url": "https://rdcsambalpur.nic.in/contact-us/", "post": "Revenue Divisional Commissioner",
                            "anchor": r"Postal Address"}], **ABROAD}]


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
    for st in sorted(set(ITEMS) | set(S3WAAS)):
        names = district_names(STATE_CODE[st]) if st in ITEMS else {}
        out = []
        for it in ITEMS.get(st, []):
            p = {"reader": "st_div_pages", "state": st, **it, "district_names": names}
            out.append({"key": f"st_div_pages:{it['key']}", "payload": p})
        out += S3WAAS.get(st, [])
        (HERE / f"dept_div_{st.lower()}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
        print(st, len(out))


if __name__ == "__main__":
    main()
