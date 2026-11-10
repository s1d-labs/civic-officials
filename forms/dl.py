"""Delhi BLO list: ceodelhinet.nic.in BloUpdateDetails.aspx (ASP.NET WebForms).

Choose an AC in ddlACNO (postback), then turn the GridView pager (Page$N) as a visitor does.
"""
import re
import time

import requests
from bs4 import BeautifulSoup

URL = "https://ceodelhinet.nic.in/ceodelhiweb/BloUpdateDetails.aspx"
UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
DDL = "ctl00$ContentPlaceHolder1$ddlACNO"
GRID = "ctl00$ContentPlaceHolder1$gvBloUpdateSearchPage"
GRID_ID = "ctl00_ContentPlaceHolder1_gvBloUpdateSearchPage"
PAUSE = 1.0
MAX_PAGES = 200


def _session(session=None):
    s = session or requests.Session()
    s.headers["User-Agent"] = UA
    return s


def _hidden(soup):
    return {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}


def _get(s):
    r = s.get(URL, timeout=90)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def _post(s, soup, target, arg, ac_no):
    data = _hidden(soup)
    data["__EVENTTARGET"] = target
    data["__EVENTARGUMENT"] = arg
    data[DDL] = str(ac_no)
    time.sleep(PAUSE)
    r = s.post(URL, data=data, timeout=90)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def items(session=None):
    s = _session(session)
    soup = _get(s)
    out = []
    for o in soup.select(f"select[name='{DDL}'] option"):
        v = (o.get("value") or "").strip()
        if not v.isdigit() or int(v) < 1:
            continue
        name = re.sub(r"^\s*\d+\s*-\s*", "", o.get_text(strip=True))
        out.append({"key": f"dl-ac-{int(v)}",
                    "payload": {"kind": "form-dl", "state": "DL", "ac_no": int(v), "ac_name": name}})
    return out


def _rows(soup, ac_no, ac_name):
    g = soup.find(id=GRID_ID)
    if g is None:
        return [], None
    trs = g.find_all("tr", recursive=False) or g.select("tr")
    head, rows, pager = None, [], None
    for tr in trs:
        cells = tr.find_all(["td", "th"], recursive=False)
        if tr.find("table") is not None or (len(cells) == 1 and tr.find("a", href=re.compile("Page\\$"))):
            pager = tr
            continue
        txt = [c.get_text(" ", strip=True) for c in cells]
        if head is None and tr.find("th") is not None:
            head = txt
            continue
        if not txt or len(txt) < 3:
            continue
        hdr = head or ["AC No", "Part No", "BLO Name", "Designation", "Mobile"]
        raw = {hdr[i] if i < len(hdr) else f"col{i}": t for i, t in enumerate(txt)}
        part = raw.get("Part No", "")
        rows.append({
            "ac_no": ac_no, "ac_name": ac_name,
            "part_no": int(part) if part.isdigit() else part,
            "station": None,
            "blo_name": raw.get("BLO Name", ""),
            "blo_phone": raw.get("Mobile", ""),
            "designation": raw.get("Designation", ""),
            "cells": raw,
        })
    return rows, pager


def _current_page(pager):
    if pager is None:
        return 1
    for sp in pager.find_all("span"):
        t = sp.get_text(strip=True)
        if t.isdigit():
            return int(t)
    return 1


def fetch(session, payload):
    ac_no, ac_name = int(payload["ac_no"]), payload.get("ac_name", "")
    s = _session(requests.Session())  # one session per AC
    soup = _post(s, _get(s), DDL, "", ac_no)
    all_rows, seen_pages = [], set()
    for _ in range(MAX_PAGES):
        rows, pager = _rows(soup, ac_no, ac_name)
        cur = _current_page(pager)
        if cur in seen_pages:
            break
        seen_pages.add(cur)
        all_rows.extend(rows)
        nxt = f"Page${cur + 1}"
        if pager is None or not pager.find("a", href=lambda h: h and f"'{nxt}'" in h.replace("&#39;", "'")):
            break
        soup = _post(s, soup, GRID, nxt, ac_no)
    return all_rows
