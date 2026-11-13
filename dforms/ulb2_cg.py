"""Chhattisgarh: the Urban Administration & Development Department's lists of the heads and the elected heads of all urban bodies.

Two server-rendered pages, two queue items (payload "kind"):
- "contacts": uad.cg.gov.in/ContactUAD/ContactReport.aspx, table id "gdviewnikay" (194 rows on 2026-11-11, one per body):
  संभाग (division), जिला (district), निकाय (body), निकाय का प्रकार (Nagar Nigam / Nagar Palika Parishad / Nagar Panchayat),
  पद नाम (आयुक्त = Commissioner of a corporation, सी.एम.ओ. = Chief Municipal Officer), नाम, office phone (STD), mobile, email,
  the body's engineer and the engineer's mobile. No page date. India only (no answer from Germany on 2026-11-11; vpsin got it).
  Records: the head (post "Commissioner" or "Chief Municipal Officer", role head; the Hindi post in post_regional) and the
  engineer (post "Engineer", role staff) when the row names one. The other tables of the page (minister, secretariat,
  directorate, regional joint directors, SUDA) are state officers, not body officers: left out.
- "elected": cguadestablishment.in/electionresult (the department's establishment wing; answers from Germany): two tables,
  "S.no, निकाय का नाम, नाम, पार्टी, कुल वार्ड की संख्या". Table 1 = the 14 municipal corporations (the mayor), table 2 = the
  other bodies (the chairperson, अध्यक्ष; 163 rows on 2026-11-11). No district, no phone. Records: post "Mayor" or
  "Chairperson" (role chair), party, wards. 17 bodies of the contacts list have no row (new bodies without an election yet).

Both lists write the body in Hindi only. dforms/ulb2_cg_lgd.json ties each row to its LGD local body code (lgd_code in the
record): "contacts" by district + body as the page writes them, "elected" by body, and for the five names that two bodies share
(Kusmi, Bhatgaon, Navagarh, Palari) by body + the body of the row before (the list keeps the district order). The table was
made on 2026-11-11 from the saved pages by a Devanagari/Latin name match in the district, every weak match checked by hand: all
194 contact rows tie to the 194 LGD bodies of the state, one to one. A row that is not in the table (a new body, a new spelling)
gets no lgd_code; civic-india sql/87 then ties it by name, if it can. area = the body as the list writes it; area_latin = the LGD
name (also used for the record ids).
"""
import json
import re
import unicodedata
from pathlib import Path

from dforms._trail import tr_pos
from dforms import _esw, _ulb
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_cg"
STATE = "CG"
CONTACTS = "https://uad.cg.gov.in/ContactUAD/ContactReport.aspx"
ELECTED = "https://cguadestablishment.in/electionresult"
LGD = json.loads((Path(__file__).with_name("ulb2_cg_lgd.json")).read_text())


def items(get=None):
    return [{"key": f"{MODULE}-contacts", "payload": {"reader": MODULE, "kind": "contacts", "url": CONTACTS, "state": STATE,
                                                       "india_only": True}},
            {"key": f"{MODULE}-elected", "payload": {"reader": MODULE, "kind": "elected", "url": ELECTED, "state": STATE}}]


def norm(s):
    """The key form of a Hindi cell: no zero-width characters, NFC, single spaces."""
    return " ".join(unicodedata.normalize("NFC", re.sub("[​-‍﻿]", "", s or "")).split())


def cell(td):
    """Cell text without the zero-width joiners the page puts after a virama (_esw.clean would turn them into spaces)."""
    return _esw.clean(re.sub("[\u200b-\u200d\ufeff]", "", td.get_text(" ")))


def head_post(p):
    return "Commissioner" if "आयुक्त" in norm(p) else "Chief Municipal Officer"


def tie(code):
    """(lgd_code, LGD name, district as the contacts list writes it) or (None, None, None)."""
    if not code:
        return None, None, None
    d = LGD["lgd"].get(code, {})
    return code, d.get("name"), d.get("district")


def parse_contacts(html, url=CONTACTS):
    soup = _esw.soup(html)
    t = soup.find("table", id="gdviewnikay")
    recs, seen = [], set()
    if not t:
        return recs
    for tr in t.find_all("tr")[1:]:
        c = [cell(td) for td in tr.find_all("td")]
        if len(c) < 11 or not c[2]:
            provenance.skip_row(tr, 'skip: len(c) < 11 or not c[2]')
            continue
        div, dist, body, btype, post, name, office, mobile, email, eng, engmob = c[:11]
        code, latin, _ = tie(LGD["contacts"].get(norm(dist) + "|" + norm(body)))
        common = {"district": dist, "body_type": btype, "division": div, "lgd_code": code, "area_latin": latin}
        recs.append(_ulb.record(MODULE, STATE, body, head_post(post), seen, name=name, phone=mobile, email=email, source=url,
                                latin=latin, post_regional=post, office_phone=_esw.phones(office) or None,
                                src_pos=tr_pos(tr), **common))
        if eng:
            recs.append(_ulb.record(MODULE, STATE, body, "Engineer", seen, name=eng, phone=engmob, source=url, latin=latin,
                                    post_regional="इंजीनियर", src_pos={**tr_pos(tr), "cells": "engineer columns"}, **common))
    return recs


def parse_elected(html, url=ELECTED):
    soup = _esw.soup(html)
    recs, seen = [], set()
    prev = ""
    for ti, t in enumerate(soup.find_all("table")):
        post, preg = ("Mayor", "महापौर") if ti == 0 else ("Chairperson", "अध्यक्ष")
        for tr in t.find_all("tr")[1:]:
            c = [cell(td) for td in tr.find_all("td")]
            if len(c) < 4 or not c[1]:
                provenance.skip_row(tr, 'skip: len(c) < 4 or not c[1]')
                continue
            body = c[1]
            b = norm(body)
            code = LGD["elected"].get(b) or LGD["elected"].get(b + "|" + prev)
            prev = b
            code, latin, dist = tie(code)
            recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=c[2], district=dist, source=url, latin=latin,
                                    post_regional=preg, party=c[3] or None, wards=c[4] if len(c) > 4 and c[4] else None,
                                    lgd_code=code, area_latin=latin, src_pos=tr_pos(tr)))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    kind = p.get("kind", "contacts")
    recs = parse_contacts(r.text, p["url"]) if kind == "contacts" else parse_elected(r.text, p["url"])
    return recs, [_esw.keep(MODULE, kind, r.content)], "" if recs else "no rows"
