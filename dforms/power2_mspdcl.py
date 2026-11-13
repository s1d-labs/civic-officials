"""Manipur: Manipur State Power Distribution Company Ltd (MSPDCL). The company site is now mspdcl.in; the old domain mspdcl.com
serves an unrelated betting page (seen 2026-11-11), so never read it. One queue item:
- mspdcl.in/about/who-is-who, "Officers up to DGM Level": one table; a one-cell row names the block ("Corporate Office",
  "Electrical Division-I" .. "-IV" = the four Electrical Circles EC-I..IV, "Other Offices"), then Sl. No. | DESIGNATION | NAME |
  EMAIL ID. The circle blocks list the Deputy General Manager of each distribution division (IED-I..IV in Imphal, Bishnupur,
  Thoubal, Kakching, Ukhrul, ... Tengnoupal: 18 divisions). Names and e-mails; no phones. About 36 rows.
  Levels: division for the circle blocks (parent circle "Electrical Circle-<n>"), state for Corporate Office / Other Offices.
The organisation page (/about/organisation) lists the 53 sub-divisions under each division but no officers. The RTI Annexure-III
"Directory of MSPDCL Officers" (mspdcl.in/uploads/rti/files/01KW9HTPSR6WDH30F2F3DY88RB.pdf, "as on 29th June 2026") has the same
officers plus the MD, EDs and GMs, also without phones.
Answers from Germany (2026-11-11). No page date. Records "dept:power2_mspdcl:<block>:<post>".
"""
import re

from bs4 import BeautifulSoup

from dforms import _power, _util2_east
from dforms._power import tr_pos
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_mspdcl"
URL = "https://mspdcl.in/about/who-is-who"
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}


def items(get=None):
    return [{"key": f"{MODULE}:who-is-who", "payload": {"reader": MODULE, "url": URL, "state": "MN", "india_only": False}}]


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    out = _power.Out(MODULE, "MN", url, discom="MSPDCL")
    for tb in soup.find_all("table"):
        block, head = None, None
        for tr in tb.find_all("tr"):
            out.src = {"src_pos": tr_pos(tr)}
            c = _power.cells(tr)
            if len(c) == 1:
                block, head = _power.clean(c[0]), None
                continue
            if any(re.fullmatch(r"designation", x, re.I) for x in c):
                head = _util2_east.head_map(c, {"post": r"designation", "name": r"^name", "email": r"e-?mail"})
                continue
            if not head or not block:
                provenance.skip_row(tr, 'skip: not head or not block')
                continue
            g = {k: c[i] if i < len(c) else "" for k, i in head.items()}
            post = _power.clean(g.get("post"))
            m = re.search(r"Electrical Division-([IV]+)", block)
            unit = re.search(r"\(([^)]+)\)|-\s*(IED-[IV]+)$", post or "")
            unit = _power.clean((unit.group(1) or unit.group(2)).title() if unit else None)
            if unit and unit.upper().startswith("IED"):
                unit = "Imphal Electrical Division-" + unit.split("-")[-1].upper()
            if m and unit:
                circle = f"Electrical Circle-{m.group(1)}"
                out.add(f"{block}:{post}", "division", unit, post=post, name=_util2_east.person(g.get("name")),
                        email_=_power.email(g.get("email")), parents={"circle": circle}, office_id=f"EC-{m.group(1)}")
            else:
                out.add(f"{block}:{post}", "state", block if block != "Other Offices" else (unit or block), post=post,
                        name=_util2_east.person(g.get("name")), email_=_power.email(g.get("email")))
    out.src = {}
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    return recs, [_power.raw(MODULE, "who-is-who", r.content, "html")], "" if recs else "no rows"
