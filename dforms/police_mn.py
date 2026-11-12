"""Manipur. Two forms (payload "form"), both work from outside India:
- "helpline": S3WaaS district helpline page (imphaleast.nic.in/?p=2780): rows "Police Station – OC <station>" with the station
  landline; parsed by police_nl.records.
- "controlrooms": manipurpolice.gov.in/?page_id=3257, one table "Sl. No. | Office's | Telephone No. | Fax No." with the 17
  district police control rooms (district level; no station rows). Manipur has about 93 police stations; no statewide list of
  station numbers was found.
Record id dept:police_mn:<district>:<station> or dept:police_mn:control-room:<district>."""
import re

from bs4 import BeautifulSoup

from dforms import police_nl
from dforms import _civic
from dforms._police import clean, gz, phones, rec, slug

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_mn"


def control_rooms(html, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        for tr in t.find_all("tr"):
            c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
            if len(c) < 3 or not re.search(r"control room", c[1], re.I):
                continue
            office = c[1]
            district = re.sub(r"\s*Control Room\s*$", "", office, flags=re.I)
            ph = phones(c[2])
            if not ph:
                continue
            state_level = district.upper().startswith("DG")
            recs.append(rec(M, f"control-room:{slug(district)}", level="state" if state_level else "district",
                            area="Manipur" if state_level else district, post="Police control room", office_type="control room",
                            phone=ph, fax=phones(c[3]) if len(c) > 3 else None, state="MN",
                            district=None if state_level else district, source=url))
            recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
    return recs


def fetch(p, get):
    if p.get("form") == "controlrooms":
        r = get(p["url"])
        if r is None:
            return [], [], "no answer"
        recs = control_rooms(r.text, p["url"])
        return recs, [gz(M, "control-rooms.html", r.content)], "" if recs else "no control rooms"
    return police_nl.fetch({"state": "MN", **p}, get, M)
