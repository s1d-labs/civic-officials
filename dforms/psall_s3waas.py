"""Police station lists on S3WaaS district portals that no other police item reads (2026-11-14, owner: "I hope all the police
stations are loaded"): <district>.nic.in / .gov.in / .telangana.gov.in pages /police/, /police-stations/,
/public-utility-category/police-station(s)/, read with the S3WaaS table and card parser and the officer clean-up of
police2n_dir (police_s3waas.records + police2n_dir.clean_records), then cleaned for station lists:
- a phone written in the station name ("Poonch [+91-01965-220225]") goes to the phone field (when the row has none) and out of
  the name;
- rows at level police_station whose name is a sub-division office, a superintendent, a SHE team or a district office are
  left out (counted in the source trail: provenance.skipped).
Payload: url, state, district (as police2n_dir). Seeds: seeds/dept_psall_<st>.json (pages found in the archive that no seed
had, states with the largest gap to the BPR&D station count). Record id dept:psall_s3waas:<district>:<station>.
Records: type dept_office, dept police, level police_station (or subdivision / circle / district as police2n_dir decides),
area (station name), post, name, phone, email, address, pincode, state, district, source, src_url, src_pos, method."""
import re

from dforms import police2n_dir
from dforms._police import slug
import provenance

METHOD = police2n_dir.METHOD     # source trail (provenance.py): how this reader reads its sources

M = "psall_s3waas"

PHONE_IN_NAME = re.compile(r"\s*[\[(]\s*((?:\+91[-\s]?)?0?\d[\d\s-]{6,}\d)\s*[\])]\s*")
NOT_STATION = re.compile(r"sub[- ]?divi|supdt|superintendent|she\s*teams?|\bdistrict\s+office\b|\boffice$|^\s*(?:addl|dy)\.", re.I)


def clean_stations(recs):
    out = []
    for rid, d in recs:
        if d.get("level") == "police_station":
            area = d.get("area") or ""
            m = PHONE_IN_NAME.search(area)
            if m:
                d = dict(d)
                d["area"] = PHONE_IN_NAME.sub(" ", area).strip(" ,-")
                if not d.get("phone"):
                    d["phone"] = re.sub(r"^\+91[-\s]?", "", m.group(1)).replace(" ", "")
                rid = f"dept:{rid.split(':')[1]}:{slug(d.get('district') or '')}:{slug(d['area'])}"
            if NOT_STATION.search(d.get("area") or ""):
                provenance.skipped("not a station: sub-division, superintendent, SHE team or office")
                continue
        out.append((rid, d))
    return out


def fetch(p, get, module=M):
    recs, files, why = police2n_dir.fetch(p, get, module)
    if not recs:
        return recs, files, why
    recs = clean_stations(recs)
    return recs, files, "" if recs else "no station rows"
