"""Jharkhand CEO: BLO contacts (https://ceojh.jharkhand.gov.in/linkinfo/BLOcontacts.aspx).

The page has one AC dropdown (DropDownList1, 81 AC names, no numbers) and a GridView
(5 columns: Constituency Name, Part No, BLO Name, Designation, Mb No), 600 rows per page.
A form post with a new DropDownList1 value filters the grid to that AC (the page has no
button: the server applies the filter on any postback that changes the value).
The unfiltered first view lists ACs in an odd order, so work goes per AC.

Answers only from India. Read-only: GET + one dropdown postback (+ pager postbacks if an AC
ever has more than 600 parts).
"""
import re
import time

import requests
from bs4 import BeautifulSoup

URL = "https://ceojh.jharkhand.gov.in/linkinfo/BLOcontacts.aspx"
UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"
SLEEP = 1.0
TIMEOUT = 90

# AC numbers (Delimitation 2008, ECI). The site gives names only; keys are normalised names
# as the dropdown spells them.
AC_NO = {
    "rajmahal": 1, "borio": 2, "barhait": 3, "littipara": 4, "pakur": 5, "maheshpur": 6,
    "shikaripara": 7, "nala": 8, "jamtara": 9, "dumka": 10, "jama": 11, "jarmundi": 12,
    "madhupur": 13, "sarath": 14, "deoghar": 15, "poreyahat": 16, "godda": 17, "mahagama": 18,
    "kodarma": 19, "barkattha": 20, "barhi": 21, "barkagaon": 22, "ramgarh": 23, "mandhu": 24,
    "hazaribagh": 25, "simaria": 26, "chatra": 27, "dhanwar": 28, "bagodar": 29, "jamua": 30,
    "gandey": 31, "giridih": 32, "dumri": 33, "gomia": 34, "bermo": 35, "bokaro": 36,
    "chandankyari": 37, "sindri": 38, "nirsa": 39, "dhanbad": 40, "jharia": 41, "tundi": 42,
    "baghmara": 43, "baharagora": 44, "ghatshila": 45, "potka": 46, "jugsalai": 47,
    "jamshedpur east": 48, "jamshedpur west": 49, "ichagarh": 50, "saraikella": 51,
    "chaibasa": 52, "majhganon": 53, "jaganathpur": 54, "manoharpur": 55, "chakradharpur": 56,
    "kharasawan": 57, "tamar": 58, "torpa": 59, "khunti": 60, "silli": 61, "khijri": 62,
    "ranchi": 63, "hatia": 64, "kanke": 65, "mandar": 66, "sisai": 67, "gumla": 68,
    "bishunpur": 69, "simdega": 70, "kolebira": 71, "lohardaga": 72, "manika": 73,
    "latehar": 74, "panki": 75, "daltonganj": 76, "bishrampur": 77, "chattarpur": 78,
    "hussainabad": 79, "garhwa": 80, "bhawanathpur": 81,
}
COLS = ["Constituency Name", "Part No", "BLO Name", "Designation", "Mb No"]


def _norm(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _session(session=None):
    s = requests.Session()
    s.headers["User-Agent"] = UA
    if session is not None:  # keep caller's proxies / CA bundle, never its cookies
        s.proxies.update(getattr(session, "proxies", {}) or {})
        s.verify = getattr(session, "verify", True)
    return s


def _soup(resp):
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def _hidden(soup):
    return {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}


def _selected(soup):
    sel = soup.find("select", id="DropDownList1")
    if not sel:
        return None
    for o in sel.find_all("option"):
        if o.has_attr("selected"):
            return o.get("value")
    return None


def _grid_rows(soup):
    g = soup.find("table", id="GridView1")
    out = []
    if not g:
        return out
    for tr in g.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) != 5:
            continue
        cells = [td.get_text(" ", strip=True) for td in tds]
        if not any(cells):  # blank spacer row before the pager
            continue
        out.append(cells)
    return out


def _pages(soup):
    g = soup.find("table", id="GridView1")
    return sorted({int(n) for n in re.findall(r"Page\$(\d+)", str(g))}) if g else []


def _row(cells):
    ac_name, part, name, desig, phone = (re.sub(r"\s+", " ", c).strip() for c in cells)
    return {
        "ac_no": AC_NO.get(_norm(ac_name)),
        "ac_name": ac_name,
        "part_no": int(part) if part.isdigit() else part,
        "blo_name": name,
        "blo_phone": phone,
        "designation": desig,
        "cells": dict(zip(COLS, cells)),
    }


def items(session):
    s = _session(session)
    soup = _soup(s.get(URL, timeout=TIMEOUT))
    out = []
    for o in soup.find("select", id="DropDownList1").find_all("option"):
        ac = o.get("value")
        no = AC_NO.get(_norm(ac))
        key = "jh-ac-%03d" % no if no else "jh-ac-" + re.sub(r"[^a-z0-9]+", "-", _norm(ac))
        out.append({"key": key, "payload": {"kind": "form-jh", "state": "JH", "ac": ac, "ac_no": no}})
    return out


def fetch(session, payload):
    ac = payload["ac"]
    s = _session(session)
    soup = _soup(s.get(URL, timeout=TIMEOUT))
    time.sleep(SLEEP)
    data = _hidden(soup)
    data.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", "DropDownList1": ac})
    if _selected(soup) == ac:
        # The first view already has this value selected (Rajmahal): the server sees no
        # change and would not filter, so choose another value first, as a visitor would.
        other = next(o.get("value") for o in soup.find("select", id="DropDownList1").find_all("option")
                     if o.get("value") != ac)
        d2 = dict(data, DropDownList1=other)
        soup = _soup(s.post(URL, data=d2, timeout=TIMEOUT))
        time.sleep(SLEEP)
        data = _hidden(soup)
        data.update({"__EVENTTARGET": "", "__EVENTARGUMENT": "", "DropDownList1": ac})
    soup = _soup(s.post(URL, data=data, timeout=TIMEOUT))
    if _selected(soup) != ac:
        raise RuntimeError("JH: filter to %r did not apply" % ac)
    rows = _grid_rows(soup)
    seen, todo = {1}, [p for p in _pages(soup) if p != 1]
    while todo:  # only if an AC has more than 600 parts
        p = todo.pop(0)
        if p in seen:
            continue
        seen.add(p)
        time.sleep(SLEEP)
        data = _hidden(soup)
        data.update({"__EVENTTARGET": "GridView1", "__EVENTARGUMENT": "Page$%d" % p, "DropDownList1": ac})
        soup = _soup(s.post(URL, data=data, timeout=TIMEOUT))
        rows += _grid_rows(soup)
        todo += [q for q in _pages(soup) if q not in seen and q not in todo]
    out = [_row(c) for c in rows]
    bad = [r for r in out if _norm(r["ac_name"]) != _norm(ac)]
    if bad:
        raise RuntimeError("JH: %d rows of another AC in %r (pager kept no filter)" % (len(bad), ac))
    return out
