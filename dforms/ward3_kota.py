"""Nagar Nigam Kota (one body since the 2025 merger of Kota North and Kota South, LGD 303090): the officer and staff list that the
corporation's Jankalyan site gives as a contact PDF, with the health inspectors of each sanitation sector. The Rajasthan contact
service (lsg.rajasthan.gov.in .../GetDepartmentContactDetail, the source of dforms/ulb_rj.py, which leaves PDF-only rows out) has a
row "Municipal Corporation, Kota", category "Help Line", IsPDF, whose AttachmentUrl is the list (on 2026-11-13:
jankalyanfile.rajasthan.gov.in .../DEPTContactDetail/2026/May/DEPTContactDetaild02bc063-....pdf, 5 pages, 182 rows, "Microsoft:
Print To PDF", set in Kruti Dev). Live sample from Mumbai on 2026-11-13, not in archive.s1d.me; the contact service answered from
Germany on 2026-11-11 (ulb_rj), the file host is unchecked from abroad.
fetch(): asks the contact service for the newest such Kota PDF row (highest Id); when the service gives none, it reads payload
"url". The rows are read with dforms/ward2n_kota.rows() (same Kruti Dev list layout: क्र.सं. | नाम | पदनाम | मो0 नं0).
Columns: commissioner, additional / deputy commissioners, engineers (superintending, executive, assistant, junior), town planners,
revenue, accounts, legal, fire, programmers, clerks, and the health staff: "का.वा. मुख्य स्वास्थ्य निरीक्षक से. नं. 01, 02, 03 व 07",
"का.वा. स्वास्थ्य निरीक्षक से. नं. 01" ... 07 and "कार्य0 स्वा. निरी. (से.न. 1)" ... 9. "से. नं." = सेक्टर नंबर, the sanitation
sector. The list has two sector series (01-07 with "का.वा.", 1-9 with "कार्य0") and does not say which part of the city each covers
or which wards a sector holds.
Records: a row whose post names sectors -> one record per sector, level "zone" (area "Sector <n> (series A|B)", zone the same,
wards_note); every other row -> level "body". Names and posts are Hindi: name = the name without श्री / श्रीमती and without the
service tag that the font map garbles ("(RAS)" -> "( द्ध"), name_regional as converted, post English (_ward3_central.post_en_known, else
ward2n_kota.post_en; "का.वा." / "कार्य0" = कार्यवाहक adds " (acting)"), post_regional as converted ("]" of the font = ","). Record ids: dept:ward3_kota:<row n>[:sector-<s>].
"""
import json
import re

from dforms import _esw, _ward, _ward3_central as c3, ward2n_kota as k2
import provenance

METHOD = "contact service json + pdf text (pdftotext -layout) + Kruti Dev map"     # source trail (provenance.py)

MODULE = "ward3_kota"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Kota", "303090", "RJ", "Kota"
SERVICE = "https://lsg.rajasthan.gov.in/webapi/PublicPortal/DepartmentWebsite/GetDepartmentContactDetail"
TITLE = "Municipal Corporation, Kota"
URL = ("https://jankalyanfile.rajasthan.gov.in/WebMyWayFiles/Department/PDF/DEPTContactDetail/2026/May/"
       "DEPTContactDetaild02bc063-71e1-4099-a578-fcaedce98a7e.pdf")


def items(get=None):
    return [{"key": f"{MODULE}-staff-list", "payload": {"reader": MODULE, "url": URL, "service": SERVICE, "state": STATE,
                                                       "route": "abroad"}}]


def pick(data):
    """AttachmentUrl of the newest (highest Id) active PDF row of the Kota corporation in a contact-service answer, or None."""
    rows = data.get("Data") or []
    if isinstance(rows, dict):
        rows = rows.get("Data") or []
    best = None
    for x in rows:
        if _esw.clean(x.get("DepartmentTitle")) != TITLE or not x.get("IsActive", True):
            provenance.skip_row(x, 'skip: _esw.clean(x.get("DepartmentTitle")) != TITLE or not x.get("IsActiv...')
            continue
        u = _esw.clean(x.get("AttachmentUrl"))
        if not u.lower().endswith(".pdf"):
            provenance.skip_row(x, 'skip: not u.lower().endswith(".pdf")')
            continue
        if best is None or int(x.get("Id") or 0) > int(best.get("Id") or 0):
            best = x
    return _esw.clean(best["AttachmentUrl"]) if best else None


SECTOR = re.compile(r"से\s*\.?\s*0?\s*न\s*[ं0]?\s*\.?\s*0?\s*([\d\s,\]व]+)")


def sectors(post):
    """Sector numbers a post names: "स्वास्थ्य निरीक्षक से. नं. 01]02]03] व 07" -> ["1", "2", "3", "7"]."""
    m = SECTOR.search(post)
    if not m:
        return []
    return list(dict.fromkeys(str(int(n)) for n in re.findall(r"\d{1,2}", m.group(1))))


def clean_name(name):
    n = re.sub(r"\(\s*[^()]*द्ध\s*\)?|\(\s*\)", " ", name)
    n = re.sub(r"से\s*0?\s*नं\s*0?", " ", n)
    return _esw.clean(n).strip(" ]-,")


def parse(pages, p):
    seen, recs = set(), []
    for r in k2.rows(pages):
        post = _esw.clean(r["post"].replace("]", ","))
        name_hi = clean_name(r["name"])
        if not (name_hi or r["phones"]) or not post:
            continue
        en = c3.post_en_known(post) or k2.post_en(post)
        if en == _esw.clean(post):
            en = c3.post_en(post)
        if re.match(r"(का\s*\.?\s*वा|कार्य\s*0)", post) and "acting" not in en and en != _esw.clean(post):
            en += " (acting)"
        phone = ", ".join(r["phones"])
        secs = sectors(post)
        series = "A" if re.search(r"का\s*\.?\s*वा", post) else "B"
        base = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, post=en, post_regional=post, name=c3.strip_title(name_hi),
                    name_regional=name_hi, phone=phone, wing=c3.wing(post, en), note=r["note"] or None, source=p["url"],
                    src_pos=r["pos"])
        if secs:
            for s in secs:
                area = f"Sector {s} (series {series})"
                recs.append(_ward.record(MODULE, f"{r['n']}:sector-{s}", seen, level="zone", area=area, zone=area,
                                         wards_note="the list names the sanitation sector, not its wards; two sector series "
                                                    "(A: का.वा. 01-07, B: कार्य0 1-9)", **base))
        else:
            recs.append(_ward.record(MODULE, r["n"], seen, level="body", area=BODY, **base))
    return recs


def fetch(p, get):
    files, url = [], p["url"]
    s = get(p.get("service", SERVICE), method="POST", data="{}", headers={"Content-Type": "application/json"})
    if s is not None:
        try:
            url = pick(json.loads(s.content)) or url
        except ValueError:
            pass
    r = get(url)
    if r is None:
        return [], files, "no answer"
    files.append(_esw.keep(MODULE, "staff-list", r.content, "pdf"))
    pages = _ward.layout_pages(r.content)
    recs = parse(pages, {**p, "url": url})
    _ward.tag(recs, r, url, METHOD)
    return recs, files, "" if recs else "no rows (pdftotext missing?)"
