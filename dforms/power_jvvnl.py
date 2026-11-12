"""Rajasthan: JVVNL telephone directory, energy.rajasthan.gov.in/webapi/api/JankalyanHome/GetTelephoneDirectory (the JSON behind
the Jankalyan energy portal). India only (times out from Germany). One plain GET returns the whole list (about 3,370 rows);
one queue item.

Rows: S.No., Name, Designation, Office Name, Mobile No., Landline No., Email (space-padded, email as x[at]y[dot]z). Rows come in
office blocks ("Office Name"): government and headquarters cells first, then JVVNL zones (ZCE), circles (SE (O&M) <town>,
SE (JCC North/South), SE (JPDC North/South)) that list their XEN divisions, AEN sub-divisions and JEN sections in order, then one
block per AEN sub-division whose rows are its 33/11 kV GSS phones (Name = the GSS place). After the first "Managing Director"
block follow AVVNL (Ajmer), JdVVNL (Jodhpur), RVPN and RVUN headquarters; only their zone (ZCE) and O&M circle (SE (O&M)) heads
are kept, with discom set to AVVNL / JdVVNL. Kept: field posts ZCE/CE (zone), SE (circle), XEN (division), AEN (sub-division),
JEN (section) of distribution offices, their control rooms, and the GSS phones (level section). Not kept: headquarters,
metering (M&P, HTM, MST), vigilance, civil, IT and accounts posts.
Record id dept:power_jvvnl:<designation> (JVVNL's own post names are unique, e.g. "AEN (O&M) Bassi"); a repeat gets ~2.
"""
import json
import re

from dforms._power import Out, clean, email, phone, raw

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

URL = "https://energy.rajasthan.gov.in/webapi/api/JankalyanHome/GetTelephoneDirectory"
LEVEL = {"ZCE": "zone", "CE": "zone", "SE": "circle", "XEN": "division", "AEN": "subdivision", "JEN": "section"}
POST = re.compile(r"^(ZCE|CE|SE|XEN|AEN|JEN)\b\.?\s*(?:\(([^)]*)\))?\s*(.*)$")
# distribution tags inside the bracket: O&M, urban/rural, the Jaipur city sub-divisions (A-I .. H-IV), zone codes (JZ, KZ, BZ ...)
DIST = re.compile(r"^(O&M(-[A-Z]+)?|O&M-R|U|R|U/R|CD(-[IVX]+)?|DD|[A-H]-[IVX]+|[A-Z]{1,3}/?Z|JCC.*|JPDC.*)$", re.I)
BLOCK = re.compile(r"^(SE \((O&M|JCC|JPDC)|ZCE \([A-Z/]+Z\)|XEN \(O&M|AEN \()", re.I)
OTHERS = ["AVVNL", "JdVVNL"]          # the 1st and 2nd "Managing Director" blocks; after them: RVPN, RVUN (not kept)


def _c(s):
    return clean(s) or ""


def parse(rows, source=URL):
    out = Out("power_jvvnl", "RJ", source, discom="JVVNL")
    discom, md = "JVVNL", 0
    prev_office, zone, circle, division, sub, sub_town = None, None, None, None, None, None
    seen, under, block_repeat = set(), {}, False                       # blocks seen; AEN/XEN post -> its parents (for the GSS blocks)
    for x in rows:
        name, des, office = _c(x.get("Name")), _c(x.get("Designation")), _c(x.get("Office Name"))
        ph = phone(x.get("Mobile No."), x.get("Landline No."))
        em = email(x.get("Email"))
        if office == "Managing Director" and office != prev_office:
            md += 1
            discom = OTHERS[md - 1] if md <= len(OTHERS) else None
        if office != prev_office:
            division = sub = sub_town = None
            repeat = office in seen
            seen.add(office)
            if office.startswith("SE ") and not repeat:
                circle = office
            prev_office = office
            block_repeat = repeat
        if discom is None:
            continue
        m = POST.match(des)
        if discom != "JVVNL":                     # AVVNL / JdVVNL: only zone and O&M circle heads
            if m and m.group(1) in ("ZCE", "SE") and (m.group(1) == "ZCE" or (m.group(2) or "").upper() == "O&M"):
                lvl = LEVEL[m.group(1)]
                out.add(des, lvl, clean(m.group(3)) or des, post=des, name=name, phone_=ph, email_=em, discom=discom)
            continue
        if not BLOCK.match(office):
            continue
        om = POST.match(office)
        if om and om.group(1) == "ZCE":
            zone = clean(om.group(3)) or office
        if (des == office and om and name and name != "Control Room"
                and (om.group(1) in ("AEN", "XEN") or (om.group(1) == "SE" and block_repeat))):
            # a GSS phone of this office: Name is the place
            par = dict(under.get(office) or {"circle": office if om.group(1) == "SE" else None})
            par[{"AEN": "subdivision", "XEN": "division", "SE": "circle"}[om.group(1)]] = office
            out.add(f"{office}:gss:{name}", "section", name, post="33/11 kV GSS", phone_=ph, email_=em, parents=par)
            continue
        if name == "Control Room" or des == "Control Room":
            lvl = LEVEL.get(om.group(1)) if om else None
            out.add(f"{office}:control-room", lvl or "circle", clean(om.group(3)) if om else office, post="Control Room",
                    phone_=ph, email_=em, parents={"zone": zone, "circle": circle if lvl != "circle" else None})
            continue
        if not m:
            continue
        kind, tag, town = m.group(1), (m.group(2) or "").strip(), clean(m.group(3))
        if tag and not DIST.match(tag):
            continue
        lvl = LEVEL[kind]
        area = town or (f"{sub_town} ({tag})" if kind == "JEN" and sub_town and tag else sub_town if kind == "JEN" else None) or tag or des
        par = {"zone": zone if lvl != "zone" else None, "circle": circle if lvl not in ("zone", "circle") else None,
               "division": division if lvl in ("subdivision", "section") else None, "subdivision": sub if lvl == "section" else None}
        out.add(des, lvl, area, post=des, name=name, phone_=ph, email_=em, parents=par)
        if kind in ("XEN", "AEN"):
            under.setdefault(des, {k: v for k, v in par.items() if v})
        if kind == "XEN":
            division, sub, sub_town = des, None, None
        elif kind == "AEN":
            sub, sub_town = des, town or tag
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_jvvnl", "telephone-directory", r.content, "json")]
    try:
        rows = json.loads(r.content)
    except ValueError:
        return [], files, "not json"
    recs = parse(rows, url)
    return recs, files, "" if recs else "no offices"
