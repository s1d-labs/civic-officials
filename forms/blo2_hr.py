"""Haryana district "find my booth" pages (s3waas WordPress): one table per assembly constituency (caption "079 - Nuh"), columns
Polling Station | Polling Station Name | BLO Name | Designation | Mobile No | Location. The mobile is only in the link
(<a href="tel:98...">Dial</a>) and the location only in a Google Maps link (maps?q=LAT,LON), so blo.py's html-table kind loses
both: this reader keeps them. Nuh (nuh.gov.in/find-my-booth/, 640 parts: Nuh 200, Ferozepur Jhirka 245, Punhana 195) is the only
Haryana district with the page (2026-11-11: the other 21 district sites answer 404). Answers from abroad.
The same layout works for any s3waas page of this kind (payload "url", "state", "district").
"""
import re

from bs4 import BeautifulSoup

from forms.aspnet import session

TEL = re.compile(r"tel:\+?(?:91)?[\s-]*([0-9][0-9\s-]{6,})")
LATLON = re.compile(r"[?&](?:q|query|ll)=(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)")


def new_session():
    return session()


def _text(td):
    return " ".join(td.get_text(" ", strip=True).replace("\xa0", " ").split())


def parse(html, district=None):
    soup = BeautifulSoup(html, "lxml")
    rows, seen = [], set()
    for t in soup.find_all("table"):
        cap = _text(t.caption) if t.caption else ""
        m = re.match(r"0*(\d+)\s*-\s*(.+)", cap)
        ac_no, ac_name = (int(m.group(1)), m.group(2).strip()) if m else (None, cap or None)
        trs = t.find_all("tr")
        head = None
        for tr in trs:
            tds = tr.find_all(["td", "th"])
            vals = [_text(td) for td in tds]
            if any(re.search(r"blo\s*name", v, re.I) for v in vals):
                head = vals                      # header row (also repeated inside tbody in one copy of the table)
                continue
            if not head or not any(vals):
                continue
            cells = {head[i] if i < len(head) else f"col{i}": v for i, v in enumerate(vals)}
            for td in tds:
                for a in td.find_all("a", href=True):
                    if (tm := TEL.search(a["href"])):
                        cells["mobile"] = re.sub(r"\D", "", tm.group(1))
                    elif (lm := LATLON.search(a["href"])):
                        cells["lat"], cells["lon"] = lm.group(1), lm.group(2)
            part = next((cells[k] for k in cells if re.search(r"polling station$|booth no|part", k, re.I) and cells[k].isdigit()), vals[0])
            if (ac_no, part) in seen:
                continue
            seen.add((ac_no, part))
            name_k = next((k for k in cells if re.search(r"blo\s*name", k, re.I)), None)
            stn_k = next((k for k in cells if re.search(r"station name|booth name", k, re.I)), None)
            rows.append({"ac_no": ac_no, "ac_name": ac_name, "district": district, "part_no": part,
                         "station": cells.get(stn_k, ""), "blo_name": cells.get(name_k, ""), "blo_phone": cells.get("mobile", ""),
                         **({"designation": cells["Designation"]} if cells.get("Designation") else {}), "cells": cells})
    return rows


def fetch(s, p):
    r = s.get(p["url"], timeout=90)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = "utf-8"
    return parse(r.text, p.get("district"))
