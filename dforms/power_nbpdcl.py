"""NBPDCL (North Bihar Power Distribution): telephone directory https://nbpdcl.co.in/frmHelplineNumbers.aspx. Answers from Germany.

One page, one queue item (~260 KB). The tree and its office codes are read by dforms/_power_bihar.py: Headquarter (officer
names), Area Board (DGM cum ESE: Tirhut, Mithila, Kosi = zone), 9 circles (ESE), 46 divisions (EEE, ESD), sub-divisions (AEE,
E/S/S/Divn or ESSD), sections (JEE, ESS), 250 SBO phones of 33/11 kV sub-stations, fuse call centres / control rooms.
Cell order is place, designation (a few blocks swap it). Names only in the headquarters block and a few circle rows.
About 1,415 rows: ~570 JEE, ~250 SBO, ~200 AEE, ~80 EEE, 9 ESE.
After the shared parse: dedupe() drops a row the page lists twice (the same office, post and phone, sometimes with the cells
in the other order: "JEE | ESS, Line Bazar" and "Line Bazar | JEE"; before, the second copy became "...~2"), and split_post()
moves the officer's post out of the name cell ("Sri Santosh Kumar,JEE (S)" + "ESS Patori" -> name "Sri Santosh Kumar",
post "JEE (S), ESS Patori").
"""
import re

from dforms._power import raw, slug
from dforms._power_bihar import parse

METHOD = "html table (office tree)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://nbpdcl.co.in/frmHelplineNumbers.aspx"
MOD = "power_nbpdcl"


TITLE_TAIL = re.compile(r"^(IAS|IPS|BAS|BPS|IRS|IFS)\b", re.I)


def dedupe(recs):
    """Drop a record that repeats an earlier one: the same level, place, post (letters only) and phone, and the same name
    when both have one (a row without a phone: also the same circle). Different people on one post keep their own rows."""
    seen, out = set(), []
    for rid, d in recs:
        ph = re.sub(r"\D", "", d.get("phone") or "")
        key = (d.get("level"), slug(d.get("area")).replace("-", ""), re.sub(r"[^a-z]", "", (d.get("post") or "").lower()), ph,
               slug(d.get("name")), "" if ph else (d.get("parents") or {}).get("circle"))
        if key in seen:
            continue
        seen.add(key)
        out.append((rid, d))
    return out


def split_post(recs):
    """'Sri Santosh Kumar,JEE (S)' in the name cell: the part after the comma is the officer's post."""
    for _, d in recs:
        m = re.match(r"^(.*?\S)\s*,\s*(\S.*)$", d.get("name") or "")
        if m and not TITLE_TAIL.match(m.group(2)):
            d["name"] = m.group(1)
            d["post"] = f"{m.group(2)}, {d['post']}" if d.get("post") else m.group(2)
    return recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = split_post(dedupe(parse(r.text, MOD, "BR", "NBPDCL", url, desig_first=False)))
    return recs, [raw(MOD, "frmHelplineNumbers", r.content, "html")], "" if recs else "no rows"
