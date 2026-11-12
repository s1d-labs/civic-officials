"""DVVNL (Dakshinanchal Vidyut Vitran Nigam, south-west Uttar Pradesh: Agra, Aligarh, Kanpur, Jhansi, Banda zones): the contact
list of www.dvvnl.org/ContactListNew1.aspx, exported as one CSV (Outlook columns) by the page's own "Download" link. Works from
Germany. One queue item: GET the page (session cookie, __VIEWSTATE), then POST it back with __EVENTTARGET
ctl00$ContentPlaceHolder1$lnkDownload -> ContactList.csv (about 1,466 rows: 965 JE, 241 AE, 121 EE, 37 SE, 8 CE).
Columns used: First Name = officer, Job Title = designation (CE zone, SE circle, EE division, AE sub-division, JE sub-station
/ section), Business Street + Business Street 2 = office type and place ("EDSD" + "Dibiyapur"), Mobile Phone, Business Phone,
E-mail Address. No district column. Rows of the M.D. office are level "state".
The CSV repeats some contacts with the office or name in other letter case or spacing ("ACHALDA" / "Achalda", "prabhu park" /
"Prabhupark", "Shivnath Sharma" / "Shiv Nath Sharma"): a row with the same designation, office, phone and name (letters only)
as a row before is skipped (before, it became "...~2" or a second id). Other people on one post or one phone keep their rows. A phone number written
into the name cell ("Ramesh Kumar Maurya  8004933068") is taken out of the name.
Record id dept:power_dvvnl:<designation>:<office>.
"""
import csv
import io
import re

import provenance
from dforms._power import Out, clean, email, phone, raw
from forms.aspnet import hidden

METHOD = "csv file"     # source trail (provenance.py): how this reader reads its sources

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
    seen = set()
    for rn, row in enumerate(csv.DictReader(io.StringIO(text.lstrip("﻿"))), 2):
        out.src = {"src_pos": {"csv_record": rn - 1, "line": rn}}    # line = after the header line, when no field holds a newline
        post = clean(row.get("Job Title"))
        a, b = clean(row.get("Business Street")), clean(row.get("Business Street 2"))
        office = " ".join(x for x in (a, b) if x) or None
        lvl = level(post, office)
        if not lvl or not office:
            continue
        name = clean(re.sub(r"\s*\+?\d[\d -]{5,}\d\s*", " ", row.get("First Name") or ""))
        ph = phone(row.get("Mobile Phone"), row.get("Business Phone"), row.get("Primary Phone"))
        key = (re.sub(r"[^a-z]", "", post.lower()), re.sub(r"[^a-z0-9]", "", office.lower()), re.sub(r"\D", "", ph or ""),
               re.sub(r"[^a-z]", "", re.sub(r"(?i)^(er|shri|sri)\.?\s+", "", name or "").lower()))
        if key in seen:
            continue
        seen.add(key)
        out.add(f"{post}:{office}", lvl, office, post=post, name=name, phone_=ph,
                email_=email(row.get("E-mail Address")), address=clean(row.get("Business City")))
    out.src = {}
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
    for _, d in recs:                     # the item read the form page and the csv export (POST to the same url)
        d.update(provenance.at(c, url))
    return recs, files, "" if recs else "no rows"
