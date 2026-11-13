"""seeds/directories_missing2.json: district portals that no project had as a district site (block-district, 2026-11-13).

These LGD districts had no row in civic.official. Their S3WaaS portals were not in sites.csv (the igod list leaves them out),
so no project read them. The archive (DB archive, vantage "pool" = GitHub runners abroad) holds 200 answers from every host
below, dated 2026-11-05 to 2026-11-11, and the Who's Who / directory pages listed here: route "abroad" (project dm-abroad).
Items: one per portal (whoswho.py finds the Who's Who and directory links), plus one item per officials page that the
portal's menu may not link (read_start: the start address is itself an officials page).
Run: python seeds/build_dm_gap.py (writes seeds/directories_missing2.json).
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
# (host, LGD name, state abbr, state name, LGD district code, extra officials pages seen in the archive)
PORTALS = [
    ("ahmedabad.nic.in", "Ahmedabad", "GJ", "Gujarat", "438", ["/about-district/whos-who/", "/directory/"]),
    ("amreli.nic.in", "Amreli", "GJ", "Gujarat", "439", ["/about-district/whos-who/", "/directory/"]),
    ("anand.nic.in", "Anand", "GJ", "Gujarat", "440", ["/about-district/whos-who/", "/directory/"]),
    ("akola.gov.in", "Akola", "MH", "Maharashtra", "467", ["/en/about-district/whos-who/"]),
    ("amravati.gov.in", "Amravati", "MH", "Maharashtra", "468", ["/en/about-district/whos-who/", "/en/district-telephone-directory-2/"]),
    ("kolhapur.gov.in", "Kolhapur", "MH", "Maharashtra", "480", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("agarmalwa.nic.in", "Agar-Malwa", "MP", "Madhya Pradesh", "667", ["/en/about-district/whos-who/", "/en/district-officers-directory/"]),
    ("alirajpur.nic.in", "Alirajpur", "MP", "Madhya Pradesh", "639", ["/en/whos-who/", "/en/department-directory/", "/en/collectors-contact/"]),
    ("anuppur.nic.in", "Anuppur", "MP", "Madhya Pradesh", "390", ["/en/about-district/whos-who/"]),
    ("maihar.nic.in", "Maihar", "MP", "Madhya Pradesh", "784", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("pandhurna.nic.in", "Pandhurna", "MP", "Madhya Pradesh", "785", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("balod.gov.in", "Balod", "CG", "Chhattisgarh", "646", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("balodabazar.gov.in", "Balodabazar-Bhatapara", "CG", "Chhattisgarh", "644", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("balrampur.gov.in", "Balrampur-Ramanujganj", "CG", "Chhattisgarh", "649", ["/en/about-district/whos-who/", "/en/directory/"]),
    ("sarangarh-bilaigarh.cg.gov.in", "Sarangarh-Bilaigarh", "CG", "Chhattisgarh", "763", ["/en/about-district/whos-who/", "/directory/"]),
]
# (host, ...) that failed on the runners and the proxies but answered dev-vps-3 on 2026-11-13: route "direct"
DIRECT = [
    ("aurangabad.bih.nic.in", "Aurangabad", "BR", "Bihar", "189", ["/directory/"]),
    ("markapuram.ap.gov.in", "Markapuram", "AP", "Andhra Pradesh", "790", []),
]


def items():
    out = []
    for route, rows in (("abroad", PORTALS), ("direct", DIRECT)):
        for host, name, st, state, dc, pages in rows:
            base = {"name": name, "kind": "District administration", "state": st, "jurisdiction": state, "district_code": dc,
                    "route": route}
            out.append({"key": f"dm2:{host}", "payload": {"url": f"https://{host}", **base}})
            for p in pages:
                out.append({"key": f"dm2:{host}{p.rstrip('/')}", "payload": {"url": f"https://{host}{p}", **base, "read_start": "1"}})
    return out


if __name__ == "__main__":
    (HERE / "directories_missing2.json").write_text(json.dumps(items(), indent=1, ensure_ascii=False) + "\n")
