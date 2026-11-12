"""Punjab: BLO lists that district sites publish (ceopunjab.gov.in itself lists no BLOs; it links voters.eci.gov.in "Book a
call with BLO", which needs a login, so we do not use it).

- layout "ludhiana": ludhiana.nic.in/know-blo/ (2026-09), one PDF per AC on cdn.s3waas.gov.in, 13 of the district's 14 ACs
  (57 Khanna ... 70 Jagraon; 65 Ludhiana North is not on the page). Title "AC 58 — Samrala : BLO list, Part-wise",
  "230 parts · source: Know your BLO Ludhiana, 20-08-2026", then Part No. | BLO Name | Mobile Number.
Text PDF without rules; read with pypdf layout mode. Answers from Germany. Seed: seeds/blo2_pb.json.
"""
import re

from forms.blo2_in import cells, download, layout_lines, mobiles, part_of

METHOD = "pdf text (pypdf) + html table"     # source trail (provenance.py): how this reader reads its sources

TITLE = re.compile(r"AC\s+(\d+)\s*[—–-]\s*(.+?)\s*:\s*BLO list", re.I)
SOURCE = re.compile(r"source:\s*(.+)$", re.I)


def parse_ludhiana(lines, p):
    out, ac_no, ac_name, source = [], p.get("ac_no"), p.get("ac_name"), ""
    for page, ln in lines:
        m = TITLE.search(ln)
        if m:
            ac_no, ac_name = int(m.group(1)), m.group(2).strip()
            continue
        m = SOURCE.search(ln)
        if m:
            source = m.group(1).strip()
            continue
        c = cells(ln)
        if len(c) < 2 or not part_of(c[0]) or not mobiles(c[-1]):
            continue
        name = " ".join(c[1:-1])
        raw = {"page": page, "Part No.": c[0], "BLO Name": name, "Mobile Number": c[-1]}
        if source:
            raw["source_note"] = source
        out.append({"ac_no": ac_no, "ac_name": ac_name, "district": p.get("district", "Ludhiana"), "part_no": c[0],
                    "blo_name": name, "blo_phone": mobiles(c[-1])[0], "cells": raw})
    return out


PARSERS = {"ludhiana": parse_ludhiana}


def fetch(s, p):
    return PARSERS[p.get("layout", "ludhiana")](layout_lines(download(s, p["url"])), p)


LUDHIANA = "https://cdn.s3waas.gov.in/s363923f49e5241343aa7acb6a06a751e7/uploads/2026/09/"
SOURCES = [  # ludhiana.nic.in/know-blo/ (archived 2026-11-10); 65 Ludhiana North is not on the page
    (57, "Khanna", "17891228286554"), (58, "Samrala", "17891228549558"), (59, "Sahnewal", "17891228688825"),
    (60, "Ludhiana East", "17891229358342"), (61, "Ludhiana South", "17891229492322"), (62, "Atam Nagar", "17891229698476"),
    (63, "Ludhiana Central", "17891229886268"), (64, "Ludhiana West", "17891230023627"), (66, "Gill", "17891230188664"),
    (67, "Payal", "17891230377924"), (68, "Dakha", "17891231452328"), (69, "Raikot", "17891231601804"),
    (70, "Jagraon", "17891231781152"),
]


def items(s=None):
    return [{"key": f"blo2-pb-ludhiana-{ac}", "payload": {"kind": "form-blo2_pb", "state": "PB", "url": f"{LUDHIANA}{f}.pdf",
                                                          "layout": "ludhiana", "ac_no": ac, "ac_name": name,
                                                          "district": "Ludhiana", "india_only": False}}
            for ac, name, f in SOURCES]
