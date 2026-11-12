"""Mizoram: https://ceo.mizoram.gov.in/officer-contacts?officer_type=blo&blo_page=N (Laravel page, 15 cards per page, 87 pages,
about 1,300 BLOs in Nov 2026). Answers from abroad. Each card in the "blo" tab: name (h5), designation (h6), district, assembly
constituency, part (the part NAME, e.g. "KHATLA V"; the page gives no part number and no phone).

Records: part_no = the part name as published (the number comes later from ECI 2017 geo.eci_pollingstations_2017, AC + name).
One queue item = one page.
"""
import re

from bs4 import BeautifulSoup

from forms.aspnet import session

METHOD = "html page"     # source trail (provenance.py): how this reader reads its sources

URL = "https://ceo.mizoram.gov.in/officer-contacts?officer_type=blo&blo_page={}"

# ECI assembly constituency numbers (2008 delimitation); keys are lower-case letters and digits only, "(ST)" removed
ACS = {"hachhek": 1, "dampa": 2, "mamit": 3, "tuirial": 4, "kolasib": 5, "serlui": 6, "tuivawl": 7, "chalfilh": 8, "tawi": 9,
       "aizawlnorthi": 10, "aizawlnorthii": 11, "aizawlnorthiii": 12, "aizawleasti": 13, "aizawleastii": 14, "aizawlwesti": 15,
       "aizawlwestii": 16, "aizawlwestiii": 17, "aizawlsouthi": 18, "aizawlsouthii": 19, "aizawlsouthiii": 20, "lengteng": 21,
       "tuichang": 22, "champhainorth": 23, "champhaisouth": 24, "easttuipui": 25, "serchhip": 26, "tuikum": 27, "hrangturzo": 28,
       "southtuipui": 29, "lungleinorth": 30, "lungleieast": 31, "lungleiwest": 32, "lungleisouth": 33, "thorang": 34,
       "westtuipui": 35, "tuichawng": 36, "lawngtlaiwest": 37, "lawngtlaieast": 38, "saiha": 39, "siaha": 39, "palak": 40}


def new_session():
    return session()


def ac_key(name):
    name = re.sub(r"\((sc|st)\)", "", name or "", flags=re.I)
    return re.sub(r"[^a-z0-9]", "", name.lower())


def last_page(html):
    soup = BeautifulSoup(html, "lxml")
    nums = [int(m.group(1)) for a in soup.select("a[href*='blo_page=']") if (m := re.search(r"blo_page=(\d+)", a.get("href", "")))]
    return max(nums or [1])


def items(s):
    n = last_page(s.get(URL.format(1), timeout=60).text)
    return [{"key": f"blo2-mz-p{i}", "payload": {"kind": "form-blo2_mz", "state": "MZ", "url": URL.format(i), "page": i}}
            for i in range(1, n + 1)]


def parse(html, url=""):
    soup = BeautifulSoup(html, "lxml")
    pane = soup.select_one("#blo") or soup
    rows = []
    for card in pane.select("div.media.p-3"):
        name = card.find("h5")
        desig = card.find("h6")
        cells = {"Name": name.get_text(" ", strip=True) if name else "", "Designation": desig.get_text(" ", strip=True) if desig else ""}
        for body in card.select("div.media.mt-2 > div.media-body"):
            t = " ".join(body.get_text(" ", strip=True).split())
            if t.startswith("Assembly Constituency:"):
                cells["Assembly Constituency"] = t.split(":", 1)[1].strip()
            elif t.startswith("Part:"):
                cells["Part"] = t.split(":", 1)[1].strip()
            elif "District" not in cells:
                cells["District"] = t
        if "Part" not in cells:          # DEO / ERO / AERO cards on other tabs carry no part
            continue
        ac = cells.get("Assembly Constituency", "")
        rows.append({"ac_no": ACS.get(ac_key(ac)), "ac_name": ac, "district": cells.get("District"), "part_no": cells["Part"],
                     "station": cells["Part"], "blo_name": cells["Name"], "blo_phone": "", "designation": cells["Designation"],
                     "cells": cells})
    return rows


def fetch(s, p):
    r = s.get(p["url"], timeout=60)
    r.raise_for_status()
    return parse(r.text, p["url"])
