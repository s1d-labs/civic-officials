"""Rajya Sabha: every sitting member with phones, email, Delhi and home address, from sansad.in's member API
(https://sansad.in/api_rs/member/sitting-members?page=N&size=300: despite the name, all 2,548 past and present members; the
reader keeps mpFlag 1 / status "Sitting"). 9 pages of 300. Answers from outside India too (checked 2026-11-11).

Fields used per member (records[]): mpsno, firstName/lastName/initial/name, hname (Hindi name), party/partyCode, state,
emailID ("x[dot]y[at]sansad[dot]nic[dot]in"), localAdd + localTele (Delhi), permanentAdd + permanentTele (home), term,
expirationDate, imageUrl, updatedAt. Rajya Sabha members have no constituency: level "state", office_id "<ST>-RS-<slug>";
nominated members have state "NM".
Record ids: dept:leg_rs:<ST>-RS-<slug of name>.
"""
from dforms import _leg
from dforms.leg_ls import _split_fax

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_rs"
URL = "https://sansad.in/api_rs/member/sitting-members?page={}&size=300&locale=en"
PAGES = range(1, 10)


def items(get=None):
    return [{"key": f"{MODULE}-p{n}", "payload": {"reader": MODULE, "url": URL.format(n), "state": "IN", "page": n,
                                                   "india_only": False}} for n in PAGES]


def parse(doc, url):
    recs = []
    for m in (doc or {}).get("records") or []:
        if str(m.get("mpFlag")) != "1" and _leg.clean(m.get("status")) != "Sitting":
            continue
        st = _leg.state_code(m.get("state")) or "NM"
        first, last = _leg.clean(m.get("firstName")), _leg.clean(m.get("lastName"))
        name = f"{first} {last}".strip() or _leg.clean(m.get("name")).strip(", ")
        local, fax1 = _split_fax(m.get("localTele"))
        perm, fax2 = _split_fax(m.get("permanentTele"))
        recs.append(_leg.member(
            MODULE, st, "RS", None, name, party=m.get("party"), party_short=_leg.clean(m.get("partyCode")), source=url,
            email=_leg.clean(m.get("emailID")), phone_delhi=local, phone_residence=perm, fax=", ".join(x for x in (fax1, fax2) if x),
            residence_address=_leg.clean(m.get("permanentAdd")).strip(". ") or "", delhi_address=_leg.clean(m.get("localAdd")),
            house="Rajya Sabha", term=_leg.clean(m.get("term")), term_ends=_leg.clean(m.get("expirationDate")),
            name_regional=_leg.clean(m.get("hname")).strip(", "), member_id=str(m.get("mpsno") or ""),
            title=_leg.clean(m.get("initial")), nominated="yes" if st == "NM" else "", photo=_leg.clean(m.get("imageUrl")),
            last_updated=_leg.clean(m.get("updatedAt"))[:10] or None))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, f"rs-p{p.get('page', 'x')}", r.content, "json")]
    try:
        doc = r.json()
    except ValueError:
        return [], files, "not json"
    if not (doc or {}).get("records"):
        return [], files, "empty page"
    recs = parse(doc, p["url"])
    return recs, files, "" if recs else "no sitting members on this page"
