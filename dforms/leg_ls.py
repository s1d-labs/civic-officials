"""Lok Sabha: every sitting MP with phones, email, Delhi and home address, from sansad.in's member API
(https://sansad.in/api_ls/member?loksabha=18&sitting=1&size=600: the list behind sansad.in/ls/members, one JSON answer, ~600 KB).
Answers from outside India too (checked 2026-11-11 from Germany).

Fields used per member (membersDtoList[]): mpsno, mpFirstLastName, partyFname/partySname, stateName, constName, categoryCode,
presentFaddr + presentLaddr (Delhi address + PIN), permanentFaddr + permanentLaddr (home address in the state + PIN),
personalPhone (mobile), delhiPhone, phone (HTML snippets "Tels : (011) ... <br> ... (M)<br>Fax : ..."), email (list), updatedAt.
The API gives no constituency number: the name goes to the site's PC number (dforms/leg_pc_no.json). Assam's 2023 seats and
Anantnag-Rajouri map to the older seat of the same area (ALIAS, with seat_note). The API also gives family details, date of birth
and education; the reader keeps only the contact fields, the party and the photo link.
Record ids: dept:leg_ls:<ST>-PC-<no>.
"""
import re

from dforms import _leg

MODULE = "leg_ls"
URL = "https://sansad.in/api_ls/member?loksabha=18&page=1&size=600&locale=en&sitting=1"
ALIAS = {   # sansad name (normalised) -> the name in the site's PC layer, for seats renamed by a delimitation
    ("AS", "guwahati"): "gauhati", ("AS", "sonitpur"): "tezpur", ("AS", "darrangudalguri"): "mangaldoi",
    ("AS", "nagaon"): "nowgong", ("AS", "kaziranga"): "kaliabor", ("AS", "diphu"): "autonomousdistrict",
    ("JK", "anantnagrajouri"): "anantnag",
}
NOTE = "seat from the 2023 delimitation (2022 for J&K); the site's PC layer has the older seat of the same area"


def items(get=None):
    return [{"key": f"{MODULE}-18", "payload": {"reader": MODULE, "url": URL, "state": "IN", "loksabha": 18, "india_only": False}}]


def _text(v):
    """A field that may be a string, a list of strings or HTML snippets -> one clean line."""
    if isinstance(v, list):
        v = " | ".join(str(x) for x in v if x)
    v = re.sub(r"(?i)<br\s*/?>", " | ", str(v or ""))
    return _leg.clean(re.sub(r"<[^>]+>", " ", v))


def _addr(street, pin):
    street, pin = _leg.clean(street), _leg.clean(pin)
    if pin and pin not in street:
        street = f"{street} - {pin}" if street else pin
    return street


def _split_fax(s):
    """("phones", "fax numbers") from text like "Tels : (011) 23782786 | 09013180072 (M) | Fax : (011) 23782779"."""
    fax = []
    def cut(m):
        fax.append(m.group(1))
        return " "
    s = re.sub(r"(?i)\bfax\s*[:.-]?\s*([\d()\s,-]{6,}?)(?=\||$|[a-z])", cut, s or "")
    return s, _leg.phones(*fax)


def seat(state, const):
    k = _leg.norm(const)
    no = _leg.pc_no(state, ALIAS.get((state, k), k))
    return no, (NOTE if (state, k) in ALIAS else "")


def parse(doc, url):
    recs = []
    for m in (doc or {}).get("membersDtoList") or []:
        if _leg.clean(m.get("status")) not in ("", "Sitting"):
            continue
        state_name, const = _leg.clean(m.get("stateName")), _leg.clean(m.get("constName"))
        st = _leg.state_code(state_name)
        if st == "" and "dadra" in state_name.lower():          # Dadra and Nagar Haveli and Daman and Diu: one UT, two seats
            st = "DD" if "daman" in const.lower() else "DN"
        if not st:
            continue
        no, note = seat(st, const)
        delhi, fax = _split_fax(" | ".join(x for x in (_text(m.get("delhiPhone")), _text(m.get("phone"))) if x))
        cat = _leg.clean(m.get("categoryCode")).strip("() ")
        recs.append(_leg.member(
            MODULE, st, "PC", no, m.get("mpFirstLastName") or m.get("name"), constituency=const + (f" ({cat})" if cat else ""),
            party=m.get("partyFname"), party_short=_leg.clean(m.get("partySname")), source=url, email=_text(m.get("email")),
            mobile=_text(m.get("personalPhone")), phone_delhi=delhi, fax=fax,
            residence_address=_addr(m.get("permanentFaddr"), m.get("permanentLaddr")),
            delhi_address=_addr(m.get("presentFaddr"), m.get("presentLaddr")), house="Lok Sabha", term="18th Lok Sabha",
            member_id=str(m.get("mpsno") or ""), photo=_leg.clean(m.get("imageUrl")), note=note,
            last_updated=_leg.clean(m.get("updatedAt"))[:10] or None))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"ls-{p.get('loksabha', 18)}", r.content, "json")]
    try:
        doc = r.json()
    except ValueError:
        return [], files, "not json"
    recs = parse(doc, p["url"])
    return recs, files, "" if recs else "no sitting members"
