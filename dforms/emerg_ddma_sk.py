"""Sikkim: Sikkim State Disaster Management Authority "Who is Who" (ssdma.nic.in/whoiswho.html, no login, no date): one table for
the SSDMA officials and one per district authority, captioned "DDMA (Gangtok)", "DDMA (Namchi)", "DDMA (Pakyong)", "DDMA
(Gyalshing)", "DDMA (Mangan)", "DDMA (Soreng)". Columns: Sl. No. | Name | Designation | Email Id | Contact Number | Department.
Every row names the officer (DC, ADC, SDMs, District Project Officer ...). Tables are read with the generic table reader of
dforms/emerg_ddma_s3waas.py; this module sets district (from the caption) and level (SSDMA officials: state). 55 rows on 2026-11-11.
Record ids: dept:emerg_ddma_sk:<slug of table>:<slug of post>.
"""
import re

from dforms import _emerg, emerg_ddma_s3waas

METHOD = "json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_ddma_sk"
URL = "https://ssdma.nic.in/whoiswho.html"


def records(html, url=URL):
    out = []
    for rid, d in emerg_ddma_s3waas.records(html, {"url": url, "state": "SK"}):
        m = re.search(r"(?i)ddma\s*\(\s*([^)]+?)\s*\)", d.get("section", ""))
        d = dict(d)
        if m:
            d["district"] = d["area"] = m.group(1).title()
        else:
            d["level"], d["area"] = "state", "Sikkim"
        key = rid.split(":", 3)[-1]
        out.append((f"dept:{MODULE}:{key}", {**d, "office_id": key}))
    return out


def items(get=None):
    return _emerg.seed(MODULE)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = records(r.text, url)
    return recs, [_emerg.keep(MODULE, "whoiswho", r.content)], "" if recs else "no rows"
