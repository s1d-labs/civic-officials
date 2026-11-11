"""DVVNL (Dakshinanchal Vidyut Vitran Nigam, south-west Uttar Pradesh: Agra, Aligarh, Kanpur, Jhansi, Banda zones): the contact
list of www.dvvnl.org/ContactListNew1.aspx, exported as one CSV (Outlook columns) by the page's own "Download" link. Works from
Germany. One queue item: GET the page (session cookie, __VIEWSTATE), then POST it back with __EVENTTARGET
ctl00$ContentPlaceHolder1$lnkDownload -> ContactList.csv (about 1,466 rows: 965 JE, 241 AE, 121 EE, 37 SE, 8 CE).
Columns used: First Name = officer, Job Title = designation (CE zone, SE circle, EE division, AE sub-division, JE sub-station
/ section), Business Street + Business Street 2 = office type and place ("EDSD" + "Dibiyapur"), Mobile Phone, Business Phone,
E-mail Address. No district column. Rows of the M.D. office are level "state".
Record id dept:power_dvvnl:<designation>:<office>.
"""
import csv
import io
import re

from dforms._power import Out, clean, email, phone, raw
from forms.aspnet import hidden

MOD = "power_dvvnl"
URL = "https://www.dvvnl.org/ContactListNew1.aspx"
LEVEL = {"CE": "zone", "SE": "circle", "EE": "division", "AE": "subdivision", "JE": "section"}


def level(post, office):
    m = re.match(r"(CE|SE|EE|AE|JE)\b", (post or "").upper())
    if (office or "").lower().startswith("m.d. office") or re.match(r"(?i)(md|dir)", post or ""):
        return "state"
    return LEVEL.get(m.group(1)) if m else None


def parse_csv(text, url=URL):
    out = Out(MOD, "UP", url, discom="DVVNL")
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        post = clean(row.get("Job Title"))
        a, b = clean(row.get("Business Street")), clean(row.get("Business Street 2"))
        office = " ".join(x for x in (a, b) if x) or None
        lvl = level(post, office)
        if not lvl or not office:
            continue
        out.add(f"{post}:{office}", lvl, office, post=post, name=row.get("First Name"),
                phone_=phone(row.get("Mobile Phone"), row.get("Business Phone"), row.get("Primary Phone")),
                email_=email(row.get("E-mail Address")), address=clean(row.get("Business City")))
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    form = hidden(r.text)
    if "__VIEWSTATE" not in form:
        return [], [raw(MOD, "page", r.content, "html")], "no form on the page"
    form.update({"__EVENTTARGET": "ctl00$ContentPlaceHolder1$lnkDownload", "__EVENTARGUMENT": ""})
    c = get(url, method="POST", data=form)
    if c is None:
        return [], [], "csv export did not answer"
    files = [raw(MOD, "ContactList", c.content, "csv")]
    text = c.content.decode("utf-8-sig", "replace")
    if not text.startswith("Title,") and "First Name" not in text[:500]:
        return [], files, "answer is not the csv"
    recs = parse_csv(text, url)
    return recs, files, "" if recs else "no rows"
