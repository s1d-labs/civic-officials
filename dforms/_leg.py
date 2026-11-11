"""Shared helpers for the legislator readers (dforms/leg_*.py): MLAs, Lok Sabha MPs, Rajya Sabha MPs with their contact details.

One record per sitting member, type "dept_office" (depts.py fields), dept "elected":
  level "ac"     MLA of an assembly constituency     office_id "<ST>-AC-<no>"   record "dept:leg_<house>:<ST>-AC-<no>"
  level "pc"     Lok Sabha MP of a constituency      office_id "<ST>-PC-<no>"   record "dept:leg_<house>:<ST>-PC-<no>"
  level "state"  Rajya Sabha MP or nominated member  office_id "<ST>-RS-<slug>" record "dept:leg_<house>:<ST>-RS-<slug>"
  level "state"  MLC (member of a Legislative Council) office_id "<ST>-LC-<slug>" record "dept:leg_<house>:<ST>-LC-<slug>"
                 (area = the council constituency: "Agra Division Teachers", "Pratapgarh Local Authorities", "Nominated")
Common fields: name, party, phone (every number, joined by ", "), email (every address), address (the address in the state:
constituency office, else residence, else office), source. Extra keys when the source gives them: house, constituency, seat_no
(the number the source gives), office_address, residence_address, constituency_office, delhi_address, phone_office,
phone_residence, mobile, fax, website, term, name_regional.

Seat numbers follow the site's layers (civic.seat_member, geo.lgd_assembly_constituencies, geo.lgd_parliament_constituencies):
  - PC: the number of the name in dforms/leg_pc_no.json (built from geo.lgd_parliament_constituencies; AP is 18-42 there).
  - AC: the source's ECI number, except Andhra Pradesh: the site keeps the united-AP numbers (ECI no + 119), and Jammu and Kashmir
    and Assam: the site has the seats from before the 2022/2023 delimitation, so the name decides (_esw.ac_no); when the name is
    not in the old layer, the seat gets no number (record "<ST>-AC-x-<name>", no office_id) and "seat_note" gives the ECI number.
"""
import json
import re
from pathlib import Path

from dforms import _esw

clean, slug, phones, emails = _esw.clean, _esw.slug, _esw.phones, _esw.emails
_PC = None

# state names as the sources write them -> the two-letter codes of civic-india sql/86_dept_office.sql
STATES = {
    "andaman and nicobar islands": "AN", "andhra pradesh": "AP", "arunachal pradesh": "AR", "assam": "AS", "bihar": "BR",
    "chandigarh": "CH", "chhattisgarh": "CG", "dadra and nagar haveli": "DN", "daman and diu": "DD", "delhi": "DL",
    "nct of delhi": "DL", "national capital territory of delhi": "DL", "goa": "GA", "gujarat": "GJ", "haryana": "HR",
    "himachal pradesh": "HP", "jammu and kashmir": "JK", "jharkhand": "JH", "karnataka": "KA", "kerala": "KL", "keralam": "KL",
    "ladakh": "LA", "lakshadweep": "LD", "madhya pradesh": "MP", "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML",
    "mizoram": "MZ", "nagaland": "NL", "odisha": "OD", "orissa": "OD", "puducherry": "PY", "pondicherry": "PY", "punjab": "PB",
    "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN", "telangana": "TS", "tripura": "TR", "uttar pradesh": "UP",
    "uttarakhand": "UK", "uttaranchal": "UK", "west bengal": "WB", "nominated": "NM",
}
POST = {"AC": "Member of Legislative Assembly", "PC": "Member of Parliament, Lok Sabha", "RS": "Member of Parliament, Rajya Sabha",
        "LC": "Member of Legislative Council"}
LEVEL = {"AC": "ac", "PC": "pc", "RS": "state", "LC": "state"}
ADDR_ORDER = ("constituency_office", "residence_address", "permanent_address", "office_address", "delhi_address")
PHONE_KEYS = ("mobile", "phone_office", "phone_residence", "phone_constituency", "phone_delhi")


def state_code(name):
    k = re.sub(r"[^a-z ]", " ", clean(name).lower().replace("&", " and "))
    return STATES.get(" ".join(k.split()), "")


def norm(s):
    return _esw.norm_ac(re.sub(r"\((sc|st|gen|bl)\)|\b(sc|st)\b\s*$", "", clean(s), flags=re.I))


def pc_no(state, name):
    """Site PC number for a constituency name, or None."""
    global _PC
    if _PC is None:
        _PC = json.loads((Path(__file__).parent / "leg_pc_no.json").read_text())
    d, k = _PC.get(state, {}), norm(name)
    if k in d:
        return d[k]
    if len(d) == 1:                       # one-seat states and UTs
        return next(iter(d.values()))
    return None


def ac_seat(state, no, name=None, district=None):
    """(site AC number, note) for a source AC number + name."""
    no = int(no) if str(no or "").strip().isdigit() else None
    if state == "AP" and no and no <= 175:
        return no + 119, ""
    if state in ("JK", "AS"):
        old = _esw.ac_no(state, name or "", district) if name else None
        if old:
            return old, ""
        if no:   # the ECI number can be another seat's old number (ECI 5 Parbatjhora, old 5 Badarpur): key by name instead
            return None, f"ECI seat {no} after the 2022/2023 delimitation; the site's AC layer has the older seats"
    if not no and name:
        return _esw.ac_no(state, name, district), ""
    return no, ""


def _key(x):
    """Phone numbers compare by their digits without the leading 0 / +91 (09999864553 = 9999864553); other values as written."""
    d = re.sub(r"\D", "", x)
    return re.sub(r"^(91(?=\d{10}$)|0+)", "", d) if len(d) >= 6 and not re.search(r"[a-z@]", x, re.I) else x.lower()


def _join(*vals):
    out, seen = [], set()
    for v in vals:
        for x in re.split(r"\s*,\s*", v or ""):
            if x and _key(x) not in seen:
                seen.add(_key(x))
                out.append(x)
    return ", ".join(out)


def member(module, state, kind, no, name, *, constituency="", party="", source="", phone="", email="", address="", post=None,
           note="", **extra):
    """(record id, data) for one sitting member. kind: AC, PC, RS or LC. no: the seat number on the site (None if unknown).
    phone / email may be given whole; the mobile, phone_* and *_address extras are also folded into phone / address."""
    extra = {k: clean(v) if isinstance(v, str) else v for k, v in extra.items()}
    for k in PHONE_KEYS:
        if extra.get(k):
            extra[k] = _join(phones(extra[k]) or extra[k])
    phone = _join(phones(phone) or clean(phone), *[extra.get(k, "") for k in PHONE_KEYS])
    email = _join(emails(email), *[emails(extra.get(k, "")) for k in ("email_office", "email_personal")])
    address = clean(address) or next((extra[k] for k in ADDR_ORDER if extra.get(k)), "")
    constituency = clean(constituency)
    if kind in ("RS", "LC"):
        key = f"{state}-{kind}-{slug(name)}"
        area = constituency if kind == "LC" else ""
    else:
        key = f"{state}-{kind}-{no}" if no else f"{state}-{kind}-x-{slug(constituency or name)}"
        area = f"{no} - {constituency}" if no and constituency else constituency
    return _esw.record(module, key, dept="elected", level=LEVEL[kind], area=area, post=post or POST[kind], name=clean(name),
                       party=clean(party), phone=phone, email=email, address=address, state=state,
                       office_id=key if (no or kind in ("RS", "LC")) else "", source=source, constituency=constituency,
                       seat_note=note, **extra)


def keep(module, name, content, ext="html"):
    return _esw.keep(module, name, content, ext)
