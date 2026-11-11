"""Ladakh: the two municipal committees (Leh, Kargil) from the district portals' directories, leh.nic.in/directory/ and
kargil.nic.in/directory/ (S3WaaS, server-rendered; saved in archive.s1d.me 2026-11-05). Each directory has one table with the
caption "Municipal Committee" (Leh: Name | Designation | Email | Mobile No | Landline No | Fax No | Address; Kargil: Name |
Designation | Place of Posting | Phone Number (STD code 01985) | E-Mail | Mobile). It names the Executive Officer, the head of the
committee. No date on the page. Both rows are in civic.official already, as district rows (kind "District administration",
no local_body_code); these records tie them to the body by LGD code.
The directories name no President of either committee, and leh.nic.in "Municipal Election" shows only the result of the
2018 election (saved 2026-11-05), so no record of a chairperson is made.
"""
import re

from dforms import _esw, _ulb2_nw

MODULE = "ulb2_la"
STATE = "LA"
PAGES = [("https://leh.nic.in/directory/", "248177", "Leh Ladakh", "Leh"),
         ("https://kargil.nic.in/directory/", "248178", "Kargil", "Kargil")]
CAPTION = re.compile(r"(?i)^\W*municipal\s+committee\W*$")


def items(get=None):
    return [{"key": f"{MODULE}-{_esw.slug(body)}",
             "payload": {"reader": MODULE, "url": url, "state": STATE, "body": body, "district": district, "lgd_code": lgd,
                         "body_type": "Municipal Committee", "india_only": False}}
            for url, lgd, district, body in PAGES]


def parse(html, p):
    people = []
    for t in _esw.soup(html).find_all("table"):
        cap = t.find("caption")
        if cap and CAPTION.match(_esw.clean(cap.get_text(" "))):
            people += table_rows_la(t)
    return _ulb2_nw.records(MODULE, STATE, p, people, set(), source=p["url"])


def table_rows_la(t):
    rows = _ulb2_nw.table_rows(t)
    for x in rows:                                   # "Executive Officer, Municipal Committee" -> "Executive Officer"
        x["post"] = re.sub(r"(?i),?\s*municipal\s+committee\s*$", "", x["post"]).strip() or x["post"]
    return rows


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, _esw.slug(p["body"]), r.content)], "" if recs else "no rows"
