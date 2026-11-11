"""Maharashtra: BLO lists that district collectorates publish (the CEO site ceoelection.maharashtra.gov.in has no BLO list).

Text PDFs without rules on cdn.s3waas.gov.in; read with pypdf layout mode (forms/blo2_in.layout_lines).
- layout "raigad": raigad.gov.in notice "Contact numbers of Booth Level Officers and Booth Level Supervisors" (2026-07),
  one PDF per AC (188 Panvel ... 194 Mahad): Sr.No | Part Number | Name of BLO | Designation of BLO | Office Name |
  Mobile Number, then the same six columns for the BLO Supervisor on the same line.
- layout "satara": satara.gov.in notice "BLO details Satara district SIR 2026" (2026-10), one PDF for all 8 ACs (255-262):
  Sr. No | Assembly | Part No. | Part Name | Name | Officer Type | AC No | Mobile No.
The pages answer from Germany (cdn.s3waas.gov.in). Seed: seeds/blo2_mh.json (links from the archived notice pages).
"""
from forms.blo2_in import cells, download, layout_lines, mobiles, part_of

RAIGAD_SUP = ["Supervisor Sr.No.", "Supervisor Part Number", "Name of BLO Supervisor", "Designation of BLO Supervisor",
              "Supervisor Office Name", "Supervisor Mobile Number"]


def _mid(mid):
    """Designation + office cells between the name and the mobile; an office name sometimes spills into 2 cells."""
    if not mid:
        return "", ""
    if len(mid) == 1:
        return "", mid[0]
    return mid[0], " ".join(mid[1:])


def parse_raigad(lines, p):
    out = []
    for page, ln in lines:
        c = cells(ln)
        if len(c) < 5 or not (part_of(c[0]) and part_of(c[1])):
            continue
        i = next((k for k, v in enumerate(c) if mobiles(v)), None)
        if i is None or i < 3:
            continue
        desig, office = _mid(c[3:i])
        raw = {"page": page, "Sr.No.": c[0], "Part Number": c[1], "Name of BLO": c[2], "Designation of BLO": desig,
               "Office Name": office, "Mobile Number": c[i]}
        right = c[i + 1:]
        if len(right) >= 3 and part_of(right[0]) and part_of(right[1]):
            j = next((k for k, v in enumerate(right) if mobiles(v)), len(right))
            sd, so = _mid(right[3:j])
            vals = [right[0], right[1], right[2], sd, so, right[j] if j < len(right) else ""]
            raw.update(dict(zip(RAIGAD_SUP, vals)))
        elif right:
            raw["after_mobile"] = " | ".join(right)
        out.append({"ac_no": p.get("ac_no"), "ac_name": p.get("ac_name"), "district": p.get("district"), "part_no": c[1],
                    "blo_name": c[2], "blo_phone": mobiles(c[i])[0], "designation": desig, "cells": raw})
    return out


def parse_satara(lines, p):
    out = []
    for page, ln in lines:
        c = cells(ln)
        if len(c) < 6 or not part_of(c[0]) or not mobiles(c[-1]):
            continue
        raw = {"page": page, "Sr. No": c[0], "Assembly": c[1], "Part No.": c[2], "Officer Type": c[-3], "AC No": c[-2],
               "Mobile No.": c[-1]}
        mid = c[3:-3]
        if len(mid) == 2:
            raw["Part Name"], raw["Name"] = mid
        else:                                   # columns ran together: keep the text, no name guess
            raw["Part Name and Name"] = " ".join(mid)
        ac = c[-2] if part_of(c[-2]) else p.get("ac_no")
        out.append({"ac_no": int(ac) if ac and str(ac).isdigit() else ac, "ac_name": c[1], "district": p.get("district"),
                    "part_no": c[2], "station": raw.get("Part Name", ""), "blo_name": raw.get("Name", ""),
                    "blo_phone": mobiles(c[-1])[0], "designation": c[-3], "cells": raw})
    return out


PARSERS = {"raigad": parse_raigad, "satara": parse_satara}


def fetch(s, p):
    return PARSERS[p["layout"]](layout_lines(download(s, p["url"])), p)


RAIGAD = "https://cdn.s3waas.gov.in/s344c4c17332cace2124a1a836d9fc4b6f/uploads/2026/07/"
SOURCES = [  # raigad.gov.in/en/notice/contact-numbers-of-booth-level-officers-and-booth-level-supervisors/ (archived 2026-11-10)
    ("raigad", 188, "Panvel", RAIGAD + "17829950235803.pdf"), ("raigad", 189, "Karjat", RAIGAD + "17829950242988.pdf"),
    ("raigad", 190, "Uran", RAIGAD + "17829950257145.pdf"), ("raigad", 191, "Pen", RAIGAD + "17829950279595.pdf"),
    ("raigad", 192, "Alibag", RAIGAD + "17829950289678.pdf"), ("raigad", 193, "Shrivardhan", RAIGAD + "17829952272487.pdf"),
    ("raigad", 194, "Mahad", RAIGAD + "17829950294369.pdf"),
    # satara.gov.in/en/notice/blo-details-satara-district-sir-2026/ (archived 2026-11-10): ACs 255-262 in one file
    ("satara", None, None, "https://cdn.s3waas.gov.in/s33493894fa4ea036cfc6433c3e2ee63b0/uploads/2026/10/17911762766301.pdf"),
]


def items(s=None):
    out = []
    for lay, ac, name, url in SOURCES:
        key = f"blo2-mh-{lay}-{ac}" if ac else f"blo2-mh-{lay}"
        out.append({"key": key, "payload": {"kind": "form-blo2_mh", "state": "MH", "url": url, "layout": lay, "ac_no": ac,
                                             "ac_name": name, "district": lay.capitalize(), "india_only": False}})
    return out
