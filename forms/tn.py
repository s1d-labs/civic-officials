"""Tamil Nadu CEO BLO list: https://www.erolls.tn.gov.in/blo/

ASP.NET WebForms page: District -> Assembly (AC) -> Part. The part list has
"Select All", which returns every part of one AC in one table.
The dropdowns have no client-side autopostback script; the server still
accepts a postback with __EVENTTARGET set to the dropdown (as the browser
would send), and fills the next dropdown. The page has no __EVENTVALIDATION.
The site answers only from India.

Read-only. Only GET + postbacks that choose dropdown values.
"""
import re
import time

import requests
from bs4 import BeautifulSoup

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.erolls.tn.gov.in/blo/"
UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
P = "ctl00$ContentPlaceHolder1$"
DIST, AC, PART, SUBMIT = P + "ddl_District", P + "ddl_Assembly", P + "ddl_Part", P + "btn_submit"
DELAY = 1.0
TIMEOUT = 120
HIDDEN = ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION", "__VIEWSTATEENCRYPTED")


def new_session():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    return s


def _soup(text):
    return BeautifulSoup(text, "lxml")


def _hidden(soup):
    out = {}
    for i in soup.select("input[type=hidden]"):
        name = i.get("name")
        if name and (name in HIDDEN or name.startswith("__")):
            out[name] = i.get("value", "")
    return out


def _options(soup, name):
    sel = soup.find("select", attrs={"name": name})
    if sel is None:
        return []
    return [(o.get("value", "").strip(), o.get_text(" ", strip=True)) for o in sel.find_all("option")]


def _check(r):
    r.raise_for_status()
    if "ddl_District" not in r.text:
        raise RuntimeError("unexpected page (no district dropdown), status %s, %d bytes" % (r.status_code, len(r.text)))
    return _soup(r.text)


def _get(session):
    r = session.get(URL, timeout=TIMEOUT)
    time.sleep(DELAY)
    return _check(r)


def _post(session, soup, target, values, submit=False):
    data = _hidden(soup)
    data["__EVENTTARGET"] = "" if submit else target
    data["__EVENTARGUMENT"] = ""
    data.update(values)
    if submit:
        data[SUBMIT] = "Submit"
    r = session.post(URL, data=data, headers={"Referer": URL}, timeout=TIMEOUT)
    time.sleep(DELAY)
    return _check(r)


def _real(opts):
    return [(v, t) for v, t in opts if v and v not in ("Select", "Select All", "0", "-1")]


def items(session=None):
    """One work item per AC. Walks the district dropdown (one postback per district)."""
    session = session or new_session()
    soup = _get(session)
    out = []
    for dval, dname in _real(_options(soup, DIST)):
        s2 = _post(session, soup, DIST, {DIST: dval, AC: "Select", PART: "Select"})
        for aval, aname in _real(_options(s2, AC)):
            ac_no = int(aval) if aval.isdigit() else int(re.match(r"\d+", aname).group())
            out.append({
                "key": "tn-ac-%d" % ac_no,
                "payload": {
                    "kind": "form-tn", "state": "TN",
                    "district_value": dval, "ac_value": aval,
                    "ac_no": ac_no, "ac_name": aname, "district": dname,
                },
            })
    return out


def _split_no(text):
    """'12-Some School' -> ('12', 'Some School')."""
    m = re.match(r"\s*(\d+)\s*-\s*(.*)$", text, re.S)
    return (m.group(1), m.group(2).strip()) if m else ("", text.strip())


def parse(soup):
    """Rows of the result table. Returns (rows as header->text dicts, total from the label or None)."""
    total = None
    lab = soup.select_one("#ContentPlaceHolder1_lb_Page")
    if lab:
        m = re.search(r"Total Records\s*:\s*(\d+)", lab.get_text(" ", strip=True))
        if m:
            total = int(m.group(1))
    box = soup.select_one("#ContentPlaceHolder1_namedetails") or soup
    tab = box.find("table")
    if tab is None:
        return [], total
    heads = [th.get_text(" ", strip=True) for th in tab.find_all("th")]
    rows = []
    for tr in tab.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        vals = [" ".join(td.get_text(" ", strip=True).split()) for td in tds]
        keys = heads if len(heads) == len(vals) else ["col%d" % i for i in range(len(vals))]
        rows.append(dict(zip(keys, vals)))
    return rows, total


def fetch(session, payload):
    """All BLO rows of one AC: GET, district postback, AC postback, submit with part = Select All."""
    session = session or new_session()
    dval, aval = payload["district_value"], payload["ac_value"]
    soup = _get(session)
    soup = _post(session, soup, DIST, {DIST: dval, AC: "Select", PART: "Select"})
    soup = _post(session, soup, AC, {DIST: dval, AC: aval, PART: "Select"})
    parts = [v for v, _ in _options(soup, PART)]
    if "Select All" not in parts:
        raise RuntimeError("no 'Select All' part option for AC %s" % aval)
    soup = _post(session, soup, None, {DIST: dval, AC: aval, PART: "Select All"}, submit=True)
    raw, total = parse(soup)
    if total is not None and total != len(raw):
        raise RuntimeError("AC %s: label says %d records, table has %d" % (aval, total, len(raw)))
    out = []
    for c in raw:
        part_no, station = _split_no(c.get("Part Name", ""))
        out.append({
            "ac_no": payload["ac_no"],
            "ac_name": payload["ac_name"],
            "district": payload["district"],
            "part_no": int(part_no) if part_no.isdigit() else part_no,
            "station": station,
            "blo_name": c.get("BLO Name", ""),
            "blo_phone": c.get("Mobile No", ""),
            "address": c.get("Office Address", ""),
            "cells": c,
        })
    return out


if __name__ == "__main__":
    import json
    import sys
    s = new_session()
    if len(sys.argv) > 1 and sys.argv[1] == "items":
        print(json.dumps(items(s), ensure_ascii=False))
    else:
        print(json.dumps(fetch(s, json.loads(sys.argv[1])), ensure_ascii=False))
