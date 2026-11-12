"""SBPDCL (South Bihar Power Distribution): telephone directory https://www.sbpdcl.co.in/frmHelplineNumbers.aspx. Answers from
Germany.

One page, one queue item (~225 KB), read by dforms/_power_bihar.py: Headquarter (officer names), 11 circles (ESE; PESU(E),
PESU(W) = Patna city), 47 divisions (EEE, ESD), sub-divisions (AEE(Supply), JEE(Revenue), ESSD), sections (JEE, ESS), ~300
PSS sub-station phones, and the "Fuse Call Center" block (division, locality, mobile; Patna PESU localities). Cell order is
designation, office. frmFuseCallDetails.aspx (a separate fuse call centre page) is not read: this block already has them.
About 1,510 rows: ~380 ESS, ~300 PSS, ~250 ESSD, ~185 ESD rows.
After the shared parse: power_nbpdcl.dedupe() drops rows the page lists twice (before: "...~2" copies), rows "PSS | PSS" with
no place and no phone are left out (nothing to show), and swap() puts name and post right on the headquarters rows whose cells
are in the other order ("SRI AJAY YADAV, IAS | CHAIRMAN-CUM- MD, BSPHCL"; the record id stays as it was).
"""
import re

from dforms._power import raw
from dforms._power_bihar import DES, parse
from dforms.power_nbpdcl import dedupe

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + html table"     # source trail (provenance.py): how this reader reads its sources

TITLE = re.compile(r"(?i)\b(CHAIRMAN|SECRETARY|DIRECTOR|PRIVATE|GENERAL MANAGER|ENGINEER|MANAGER|OFFICER|ASSISTANT|CONTROL)\b"
                   r"|CUM-?\s*MD\b|\bMD\s*-|\bTO\s+C?MD\b|^(OSD|HC|DIR|PS|OS|CMD)\b|-")
PERSON = re.compile(r"(?i)((SRI|SMT|SHRI|MD\.?|MISS|KUMARI)\s+)?[A-Z][A-Za-z.]*( [A-Z][A-Za-z.]*){1,4}(\s*,\s*(IAS|IPS|BAS))?")


def swap(recs):
    """Headquarters rows with the officer's name in the post and the post in the name ("CHAIRMAN-CUM- MD, BSPHCL" |
    "SRI AJAY YADAV, IAS", "OSD TO CMD" | "BHUPENDRA UMRAO"): put them back."""
    for _, d in recs:
        n, p = d.get("name") or "", d.get("post") or ""
        if d.get("level") == "state" and (TITLE.search(n) or DES.search(n)) and PERSON.fullmatch(p) and not TITLE.search(p) \
                and not DES.search(p):
            d["name"], d["post"] = p, n
    return recs


def empty(d):
    return not d.get("phone") and not d.get("name") and (d.get("area") or "").upper() == (d.get("post") or "").upper()

URL = "https://www.sbpdcl.co.in/frmHelplineNumbers.aspx"
MOD = "power_sbpdcl"


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = swap([(i, d) for i, d in dedupe(parse(r.text, MOD, "BR", "SBPDCL", url, desig_first=True)) if not empty(d)])
    return recs, [raw(MOD, "frmHelplineNumbers", r.content, "html")], "" if recs else "no rows"
