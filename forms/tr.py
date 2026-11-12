"""Tripura BLO list: erms.tripura.gov.in viewBLO.aspx (ASP.NET WebForms). Answers only from India.

Press the per-AC button; the server redirects (302) to viewBLOMain.aspx?<token>, which needs the
session cookie. One table (ContentPlaceHolder2_dgshow) holds all parts of the AC.
"""
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import provenance
from forms.aspnet import keep_trail

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

URL = "https://erms.tripura.gov.in/encoretripura/outviews/viewBLO.aspx"
UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
GRID_ID = "ContentPlaceHolder2_dgshow"
BTN_RE = re.compile(r"\$Button(\d+)$")
PAUSE = 1.0
MAX_PAGES = 50


def _session(session=None):
    s = session or requests.Session()
    s.headers["User-Agent"] = UA
    return s


def _form(soup):
    """Fields a browser sends: hidden inputs + the selected value of each select."""
    d = {i["name"]: i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}
    for sel in soup.select("select[name]"):
        o = sel.find("option", selected=True) or sel.find("option")
        if o is not None:
            d[sel["name"]] = o.get("value", o.get_text(strip=True))
    return d


def _get(s):
    r = s.get(URL, timeout=90)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")


def items(session=None):
    s = _session(session)
    soup = _get(s)
    out = []
    for b in soup.select("input[type=submit][name]"):
        m = BTN_RE.search(b["name"])
        if not m:
            continue
        label = b.get("value", "").strip()
        lm = re.match(r"\s*(\d+)\s*-\s*(.+)$", label)
        ac_no = int(lm.group(1)) if lm else int(m.group(1))
        ac_name = lm.group(2).strip() if lm else label
        out.append({"key": f"tr-ac-{ac_no}",
                    "payload": {"kind": "form-tr", "state": "TR", "ac_no": ac_no, "ac_name": ac_name,
                                "button": b["name"], "button_value": label}})
    out.sort(key=lambda x: x["payload"]["ac_no"])
    return out


def _cell(td, base):
    img = td.find("img")
    if img is not None and img.get("src"):
        return urljoin(base, img["src"])
    return td.get_text(" ", strip=True)


def _rows(soup, base, ac_no, ac_name):
    g = soup.find(id=GRID_ID)
    if g is None:
        return [], None
    head, rows, pager = None, [], None
    for n, tr in enumerate(g.find_all("tr", recursive=False), 1):
        cells = tr.find_all(["td", "th"], recursive=False)
        if tr.find("a", href=re.compile(r"__doPostBack")) is not None and len(cells) <= 2:
            pager = tr
            continue
        if head is None:
            head = [c.get_text(" ", strip=True) for c in cells]
            continue
        vals = [_cell(c, base) for c in cells]
        if len(vals) < 3:
            continue
        raw = {head[i] if i < len(head) and head[i] else f"col{i}": v for i, v in enumerate(vals)}
        part = raw.get("Part No", "")
        rows.append({
            "ac_no": ac_no, "ac_name": ac_name,
            "part_no": int(part) if part.isdigit() else part,
            "station": raw.get("Polling Station Name", ""),
            "blo_name": raw.get("B.L.O Name", ""),
            "blo_phone": raw.get("Mobile No", ""),
            "designation": raw.get("Designation", ""),
            "office": raw.get("Office Address", ""),
            "address": raw.get("Residential Address", ""),
            "last_updated": raw.get("Last Updated On", ""),
            "cells": raw,
            "src_pos": {"selector": "#" + GRID_ID, "row": n},
        })
    return rows, pager


def fetch(session, payload):
    ac_no, ac_name = int(payload["ac_no"]), payload.get("ac_name", "")
    s = keep_trail(_session(requests.Session()), session)  # one session per AC: the result URL token rides on its cookie
    soup = _get(s)
    data = _form(soup)
    btn = payload.get("button") or f"ctl00$ContentPlaceHolder2$Button{ac_no}"
    data[btn] = payload.get("button_value") or soup.find("input", attrs={"name": btn}).get("value", "")
    time.sleep(PAUSE)
    r = s.post(URL, data=data, timeout=120)  # 302 -> viewBLOMain.aspx?<token>
    r.raise_for_status()
    base, soup = r.url, BeautifulSoup(r.text, "lxml")
    lbl = soup.find(id="ContentPlaceHolder1_lblAcNoName")
    if lbl is not None:
        m = re.match(r"\s*(\d+)", lbl.get_text())
        if m and int(m.group(1)) != ac_no:
            raise RuntimeError(f"tr: asked AC {ac_no}, page shows {lbl.get_text(strip=True)}")
    all_rows, cur = [], 1
    for _ in range(MAX_PAGES):
        rows, pager = _rows(soup, base, ac_no, ac_name)
        src = provenance.at(r)          # the answer the rows came from (postbacks share one url: its hash names it)
        for row in rows:
            row.update(src)
            row["src_pos"]["grid_page"] = cur
        all_rows.extend(rows)
        if pager is None:
            break
        nxt = None  # GridView-style pager, only if it ever appears
        for a in pager.find_all("a", href=True):
            m = re.search(r"__doPostBack\('([^']+)','Page\$(\d+)'\)", a["href"].replace("&#39;", "'"))
            if m and int(m.group(2)) == cur + 1:
                nxt = m
        if nxt is None:
            break
        data = _form(soup)
        data["__EVENTTARGET"], data["__EVENTARGUMENT"] = nxt.group(1), f"Page${cur + 1}"
        time.sleep(PAUSE)
        r = s.post(base, data=data, timeout=120)
        r.raise_for_status()
        soup, cur = BeautifulSoup(r.text, "lxml"), cur + 1
    return all_rows
