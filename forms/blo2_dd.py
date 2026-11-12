"""Dadra and Nagar Haveli and Daman and Diu (state DD): BLO lists of the CEO, ceodaman.nic.in/Document-2023/{DNHBLO,DMNBLO,DIUBLO}.pdf.

Text PDFs with ruled tables; a cell often wraps over 2-4 lines, so the rows come from the rules (forms/blo2_in.ruled_tables),
not from the page text. The kind "pdf" pages of blo.py lose the part number in Diu ("1. 94." = serial, PS no) and many
names in Daman; this reader keeps every column.
- DNH: PS No | Polling Station Name | BLO Name | Posted at | Residential Address | BLO Phone Number (PS 1-306, 21-10-2023).
- Daman: PS No | Polling Station Name | BLO name, designation, office | BLO resident address | phone (PS 1-93).
  A few rows print the PS no and the station in one cell ("13 Panchayat Ghar, Marwad").
- Diu: Sr. No | PS no | BLO name, designation, office | building | "Mo.<mobile>" (PS 94-140). The file lists Diu twice:
  pages 1-2 with the building, pages 3-4 with the BLO's resident address; one record per PS keeps both.
The UT has no assembly: ac_no is the Lok Sabha seat from the payload (1 Dadra and Nagar Haveli, 2 Daman and Diu).
The files answered from Germany for the archive (2026-11-11); the 2024 copies (Document-2024/DNHBLO.pdf) answer 404.
"""
import re

from forms.blo2_in import MOBILE, download, mobiles, part_of, ruled_tables, split_name

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

COLS = {
    "dnh": ["station", "blo_name", "posted_at", "address"],
    "daman": ["station", "blo", "address"],
    "diu": ["blo", "building"],
}
MERGED = re.compile(r"^(\d{1,4})\.?\s+(\D.+)$")


def rows_from_tables(tables, p):
    layout = p["layout"]
    cols = list(COLS[layout])
    out, by_part = [], {}
    for page, rows in tables:
        for row in rows:
            joined = " ".join(row)
            if layout == "diu" and "RESIDENT ADDRESS" in joined.upper():
                cols = ["blo", "resident_address"]
            phones = mobiles(joined)
            if not phones:
                continue
            vals = []
            for v in row:
                if v and mobiles(v):     # "Kala Sheri Vanakbara Mo.8530558419": text and mobile in one cell
                    v = re.sub(r"\bMo(?:b(?:ile)?)?\.?\s*(?:No\.?)?\s*$", "", MOBILE.sub("", v).replace("/", " ").strip()).strip(" ,.-:")
                    v = v if re.search(r"[A-Za-z]", v) else ""
                if v:
                    vals.append(v)
            phone_cell = next(v for v in row if mobiles(v))
            nums = [i for i, v in enumerate(vals) if part_of(v)]
            station = None
            if layout == "diu" and len(nums) >= 2:
                part, rest = part_of(vals[nums[1]]), vals[nums[1] + 1:]
                serial = part_of(vals[nums[0]])
            elif nums and nums[0] == 0:
                part, rest, serial = part_of(vals[0]), vals[1:], None
            elif vals and MERGED.match(vals[0]):
                m = MERGED.match(vals[0])
                part, station, rest, serial = m.group(1), m.group(2), vals[1:], None
            else:
                continue
            c = {"page": page, "ps_no": part, "phone_cell": phone_cell}
            if serial:
                c["sr_no"] = serial
            names = cols[1:] if station is not None else cols
            if station is not None:
                c["station"] = station
            for k, v in zip(names, rest):
                c[k] = v
            if len(rest) > len(names):
                c["extra"] = " | ".join(rest[len(names):])
            if "blo" in c:
                name, desig = split_name(c["blo"])
            else:
                name, desig = c.get("blo_name", ""), ""
            if part in by_part:          # Diu second list: same PS, add what is new
                old = by_part[part]
                for k, v in c.items():
                    old["cells"].setdefault(k, v)
                if phones[0] != old["blo_phone"]:
                    old["cells"]["phone_other_list"] = phones[0]
                continue
            rec = {"ac_no": p.get("ac_no"), "ac_name": p.get("ac_name"), "district": p.get("district"), "part_no": part,
                   "station": c.get("station") or c.get("building") or "", "blo_name": name, "blo_phone": phones[0],
                   "designation": desig or c.get("posted_at", ""), "cells": c}
            if len(phones) > 1:
                c["phones"] = phones
            by_part[part] = rec
            out.append(rec)
    return out


def fetch(s, p):
    return rows_from_tables(ruled_tables(download(s, p["url"])), p)


BASE = "https://ceodaman.nic.in/Document-2023/"
SOURCES = [("dnh", "DNHBLO.pdf", 1, "Dadra and Nagar Haveli", "Dadra and Nagar Haveli"),
           ("daman", "DMNBLO.pdf", 2, "Daman and Diu", "Daman"),
           ("diu", "DIUBLO.pdf", 2, "Daman and Diu", "Diu")]


def items(s=None):
    """Queue items (static: the CEO's three files)."""
    return [{"key": f"blo2-dd-{lay}", "payload": {"kind": "form-blo2_dd", "state": "DD", "url": BASE + f, "layout": lay,
                                                  "ac_no": ac, "ac_name": acn, "district": d, "india_only": False}}
            for lay, f, ac, acn, d in SOURCES]
