"""Madhya Pradesh: education officers of every division, district and block, from the "Who is Who" page of the Directorate of
Public Instruction's Vimarsh portal (vimarsh.mp.gov.in/whoiswho.aspx, public, no login, no captcha; "संभाग, जिला, विकासखंड
स्तरीय अधिकारियों एवं प्राचार्य की जानकारी").

The page is an ASP.NET form. The first GET is redirected to a cookieless session path (/(S(<id>))/whoiswho.aspx). A postback
with __EVENTTARGET = DropDownList1 and DropDownList1 = <designation> answers the table GridView1 for the whole state:
Division | District | Block | Designation | Name | Phone (office) | Mobile No. | Email ID (no pager). Measured 2026-11-12 from
Mumbai (dev-vps-3): DEO 46 rows, BEO 235 rows. The archive saved the page from an Indian IP only (unchecked from abroad).

One queue item = one designation (1 GET + 1 POST). Records: dept education; level division (JD, DD), block (BEO; area = the
block), else district; post = the designation as the list names it, with its long form; name, phone (office phone and mobile;
"0" dropped), email, division, district (LGD name), block. Ids dept:edu_mp_vimarsh:<designation slug>:<district slug>[:<block
slug>][:n].
"""
import re

import provenance
from dforms import _esw
from dforms import sub2_mp_ero

METHOD = "html table (ASP.NET postback answer, table#GridView1)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "edu_mp_vimarsh"
URL = "https://vimarsh.mp.gov.in/whoiswho.aspx"
# designation (the site's option value) -> (long form, level)
POSTS = {
    "JD": ("Joint Director, School Education (division)", "division"),
    "DD (JD Office)": ("Deputy Director, Joint Director's office", "division"),
    "DEO": ("District Education Officer", "district"),
    "AD (DEO Office)": ("Assistant Director, District Education Office", "district"),
    "PO (DEO OFFICE)": ("Programme Officer, District Education Office", "district"),
    "DIET Principal": ("Principal, District Institute of Education and Training", "district"),
    "APC": ("Assistant Project Coordinator (Samagra Shiksha)", "district"),
    "ADPC": ("Additional District Project Coordinator (Samagra Shiksha)", "district"),
    "Sports Officer": ("District Sports Officer (education)", "district"),
    "BEO": ("Block Education Officer", "block"),
}
ALIAS = {"NARSINGHPUR": "NARSINGPUR", "NIWARI": "Niwari"}


def district_of(s):
    """(LGD name, LGD code) for the site's spelling (sub2_mp_ero's table + this site's own spellings)."""
    s = _esw.clean(s)
    return sub2_mp_ero.district_of(ALIAS.get(s.upper(), s))


EXPECT = {"DEO": 46, "BEO": 235}


def items(get=None):
    return [{"key": f"{MODULE}:{_esw.slug(d)}", "payload": {"reader": MODULE, "url": URL, "designation": d, "state": "MP",
                                                           "india_only": True, "expected": EXPECT.get(d, 0)}}
            for d in POSTS]


def hidden(html):
    return {i["name"]: i.get("value", "") for i in _esw.soup(html).find_all("input", type="hidden") if i.get("name")}


def parse(html, p, src=None):
    t = _esw.soup(html).find("table", id="GridView1")
    if t is None:
        return []
    tp = []
    g = _esw.grid(t, pos=tp)
    if not g:
        return []
    head = [_esw.clean(h).lower() for h in g[0]]

    def col(row, word):
        k = next((i for i, h in enumerate(head) if word in h), None)
        return _esw.clean(row[k]) if k is not None and k < len(row) else ""

    recs, seen = [], set()
    for row, pos in zip(g[1:], tp[1:]):
        name, desig = col(row, "name"), col(row, "designation") or p.get("designation", "")
        dist_s, block = col(row, "district"), col(row, "block")
        phone = _esw.phones(*(x for x in (col(row, "phone"), col(row, "mobile")) if re.sub(r"\D", "", x).strip("0")))
        email = _esw.emails(col(row, "email"))
        if not (name or phone or email):
            continue
        long, level = POSTS.get(desig, POSTS.get(p.get("designation"), (desig, "district")))
        district, dc = district_of(dist_s) if dist_s else (None, "")
        if level == "block" and not block:
            level = "district"
        area = block.title() if level == "block" else (col(row, "division").title() if level == "division" else district)
        base = ":".join(x for x in (_esw.slug(desig), _esw.slug(dist_s or col(row, "division")), _esw.slug(block)) if x)
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        recs.append(_esw.record(MODULE, key, dept="education", level=level, area=area or district or "Madhya Pradesh",
                                post=f"{desig} ({long})" if long != desig else desig, designation=desig, name=name,
                                phone=phone, email=email, division=col(row, "division").title() or None, district=district,
                                district_code=dc or None, block=block.title() or None, state="MP", source=p.get("url") or URL,
                                src_pos=pos, **(src or {})))
    return recs


def fetch(p, get):
    r = get(p.get("url") or URL)
    if r is None:
        return [], [], "no answer"
    page = getattr(r, "url", None) or URL          # the cookieless session path the site redirected to
    files = [_esw.keep(MODULE, "home", r.content)]
    d = p.get("designation", "DEO")
    a = get(page, method="POST", data={**hidden(r.text), "__EVENTTARGET": "DropDownList1", "__EVENTARGUMENT": "",
                                       "__LASTFOCUS": "", "DropDownList1": d})
    if a is None:
        return [], files, "no answer to the designation postback"
    files.append(_esw.keep(MODULE, _esw.slug(d), a.content))
    recs = parse(a.text, p, provenance.at(a, page))
    return recs, files, "" if recs else "no rows"
