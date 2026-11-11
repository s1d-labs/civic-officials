"""SBPDCL (South Bihar Power Distribution): telephone directory https://www.sbpdcl.co.in/frmHelplineNumbers.aspx. Answers from
Germany.

One page, one queue item (~225 KB), read by dforms/_power_bihar.py: Headquarter (officer names), 11 circles (ESE; PESU(E),
PESU(W) = Patna city), 47 divisions (EEE, ESD), sub-divisions (AEE(Supply), JEE(Revenue), ESSD), sections (JEE, ESS), ~300
PSS sub-station phones, and the "Fuse Call Center" block (division, locality, mobile; Patna PESU localities). Cell order is
designation, office. frmFuseCallDetails.aspx (a separate fuse call centre page) is not read: this block already has them.
About 1,520 rows: ~380 ESS, ~300 PSS, ~250 ESSD, ~185 ESD rows.
"""
from dforms._power import raw
from dforms._power_bihar import parse

URL = "https://www.sbpdcl.co.in/frmHelplineNumbers.aspx"
MOD = "power_sbpdcl"


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, MOD, "BR", "SBPDCL", url, desig_first=True)
    return recs, [raw(MOD, "frmHelplineNumbers", r.content, "html")], "" if recs else "no rows"
