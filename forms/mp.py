"""Madhya Pradesh: https://ceoelection.mp.gov.in/BLO_Details.aspx: District -> AC by postback; one table of parts per AC
(part, polling station, BLO name, mobile). 55 districts, 230 ACs. The server needs TLS legacy renegotiation."""
import time

from bs4 import BeautifulSoup

from forms.aspnet import hidden, options, session

U = "https://ceoelection.mp.gov.in/BLO_Details.aspx"
HOST = "ceoelection.mp.gov.in"
P = "ctl00$ContentPlaceHolder1$"


def new_session():
    return session(legacy_host=HOST)


def _post(s, html, target, fields):
    d = hidden(html)
    d.update({"__EVENTTARGET": P + target, "__EVENTARGUMENT": "", **{P + k: v for k, v in fields.items()}})
    time.sleep(1)
    return s.post(U, data=d, timeout=60).text


def items(s):
    out = []
    h = s.get(U, timeout=60).text
    for dv, dname in options(h, "ddlDist"):
        h2 = _post(s, h, "ddlDist", {"ddlDist": dv})
        for av, aname in options(h2, "ddlAC"):
            no = int("".join(c for c in aname.split("-")[0] if c.isdigit()) or 0) or None
            out.append({"key": f"mp-ac-{av}", "payload": {"kind": "form-mp", "state": "MP", "url": U, "district_value": dv, "district": dname,
                                                         "ac_value": av, "ac_name": aname, "ac_no": no}})
    return out


def fetch(s, p):
    h = s.get(U, timeout=60).text
    h = _post(s, h, "ddlDist", {"ddlDist": p["district_value"]})
    h = _post(s, h, "ddlAC", {"ddlDist": p["district_value"], "ddlAC": p["ac_value"]})
    soup = BeautifulSoup(h, "lxml")
    rows = []
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if len(trs) < 2:
            continue
        head = [" ".join(c.get_text(" ", strip=True).split()) for c in trs[0].find_all(["th", "td"])]
        if not any("blo" in x.lower() or "मतदान" in x or "booth" in x.lower() for x in head):
            continue
        for tr in trs[1:]:
            cells = [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["td", "th"])]
            if not any(cells):
                continue
            c = {head[i] if i < len(head) else f"col{i}": v for i, v in enumerate(cells)}
            rows.append({"ac_no": p.get("ac_no"), "ac_name": p.get("ac_name"), "district": p.get("district"), "cells": c})
    return rows
