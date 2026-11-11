"""NBPDCL (North Bihar Power Distribution): telephone directory https://nbpdcl.co.in/frmHelplineNumbers.aspx. Answers from Germany.

One page, one queue item (~260 KB). The tree and its office codes are read by dforms/_power_bihar.py: Headquarter (officer
names), Area Board (DGM cum ESE: Tirhut, Mithila, Kosi = zone), 9 circles (ESE), 46 divisions (EEE, ESD), sub-divisions (AEE,
E/S/S/Divn or ESSD), sections (JEE, ESS), 250 SBO phones of 33/11 kV sub-stations, fuse call centres / control rooms.
Cell order is place, designation (a few blocks swap it). Names only in the headquarters block and a few circle rows.
About 1,425 rows: ~570 JEE, ~250 SBO, ~200 AEE, ~80 EEE, 9 ESE.
"""
from dforms._power import raw
from dforms._power_bihar import parse

URL = "https://nbpdcl.co.in/frmHelplineNumbers.aspx"
MOD = "power_nbpdcl"


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, MOD, "BR", "NBPDCL", url, desig_first=False)
    return recs, [raw(MOD, "frmHelplineNumbers", r.content, "html")], "" if recs else "no rows"
