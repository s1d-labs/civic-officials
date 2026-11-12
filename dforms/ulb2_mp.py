"""Madhya Pradesh: the Urban Administration & Development Department's directory of urban body offices, "नगरीय निकायों की
दूरभाष एवं ई-मेल", www.mpurban.gov.in/Uploaded Document/ULBs Telephone and emails/Directory (3).pdf (linked from the page
"नगरीय निकायों की दूरभाष एवं ई-मेल" of mpurban.gov.in; PDF made 2024-11-06, 10 pages, about 135 KB). India only (no answer
from Germany on 2026-11-11; vpsin got it).

The PDF is set in Kruti Dev: pdftotext gives Latin letters ("u-ik- lhgksj" = "न.पा. सीहोर"); dforms/ulb_uk_krutidev.convert
turns them back. Layout: division headings ("Hkksiky laHkkx"), district headings ("ftyk lhgksj" = "जिला सीहोर"), then one line per
body: the type ("u-fu-" नगर निगम, "u-ik-" / "uik-" नगर पालिका, "u-ifj-" नगर परिषद), the name, the office phone (STD) and the
mailbox (cmo<town>@mpurban.gov.in, comm<city>@mpurban.gov.in for a corporation); a line with only a phone or a mailbox adds to
the body above. Page 7 is printed twice and its second print puts the Morena rows under the Damoh heading: a row that came
before (same name, phone and mailbox) is skipped, so the first print, under the right heading, is kept. 376 bodies; MP has 413
in LGD (the 37 others, mostly nagar parishads made in 2021-2022, are not in this PDF). No officer names, no page date.

Records (one per body): post "Commissioner" (u-fu-) or "Chief Municipal Officer", role head, name empty, phone = the office
phone, email = the post's mailbox (the mailbox belongs to the post, so it reaches the officer in charge whoever it is),
post_from = "directory" (the PDF names the office of the post, not a person). area = the body in Hindi as the PDF writes it,
body_type = नगर निगम / नगर पालिका / नगर परिषद, district = the PDF's heading (the district of 2024: Maihar, Mauganj and
Pandhurna bodies stand under Satna, Rewa and Chhindwara).
dforms/ulb2_mp_lgd.json ties each row to its LGD local body code (lgd_code), by the mailbox (or district + name + mailbox where
two bodies share a mailbox: Rajgarh of Rajgarh and of Dhar, Tendukheda of Narsinghpur and of Damoh). The table was made on
2026-11-11 by a match of the mailbox name and the Hindi name against the LGD names in the district, each weak match checked by
hand: 376 rows -> 376 different bodies. area_latin = the LGD name.
This is the same PDF as the "KD: UADD MP" rows of civic-india's directories (civic.official_dir), which lost the district and
the mailbox, so 38 of those rows were not tied to a body (2026-11-11).
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb
import provenance
from dforms._pdftext import layout_pages
from dforms.ulb_uk_krutidev import convert

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_mp"
STATE = "MP"
URL = "https://www.mpurban.gov.in/Uploaded%20Document/ULBs%20Telephone%20and%20emails/Directory%20(3).pdf"
PAGE = "https://www.mpurban.gov.in/?page=7HRZoU6F4ZQQb0k3xdV0HA%3D%3D"
LGD = json.loads((Path(__file__).with_name("ulb2_mp_lgd.json")).read_text())
PFX = re.compile(r"^\s*(u-\s?fu-|u-\s?ik-|uik-|u-\s?ifj-)\s*(.*)$")
PH = re.compile(r"\d{3,5}\s*-\s*\d{5,8}")
EM = re.compile(r"[\w.\-]+@[\w.\-]+")
TYPES = {"u-fu-": "नगर निगम", "u-ik-": "नगर पालिका", "uik-": "नगर पालिका", "u-ifj-": "नगर परिषद"}


def items(get=None):
    return [{"key": f"{MODULE}-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True}}]


def rows(text, where=None):
    """[{kind, name, district, division, phones, emails}] from the layout text (form feeds between pages). where: a list; when
    given, it gets provenance.line_pos(page, line, raw line) of each row's first line."""
    div = dist = None
    out, seen, at = [], set(), []
    lines = [(pno, lno, ln) for pno, pg in enumerate(text.split("\f"), 1) for lno, ln in enumerate(pg.split("\n"), 1)]
    for pno, lno, line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("ftyk "):
            dist = convert(re.split(r"\s{2,}", s[5:])[0].strip())
            continue
        m = PFX.match(line)
        if not m and re.search(r"la+Hkkx\s*$", s):
            div = convert(s.replace("laaHkkx", "laHkkx"))
            continue
        if m:
            rest = m.group(2)
            cut = min([x.start() for x in (PH.search(rest), EM.search(rest)) if x] or [len(rest)])
            name = rest[:cut].strip()
            row = {"kind": m.group(1).replace(" ", ""), "name": convert(name), "district": dist, "division": div,
                   "phones": PH.findall(rest), "emails": EM.findall(rest)}
            k = (name, tuple(row["phones"][:1]), tuple(row["emails"][:1]))
            if k in seen:                       # the second print of page 7
                out.append(None)
                at.append(None)
                continue
            seen.add(k)
            out.append(row)
            at.append(provenance.line_pos(pno, lno, line))
        elif out and out[-1] and (PH.search(s) or EM.search(s)):
            out[-1]["phones"] += PH.findall(s)
            out[-1]["emails"] += EM.findall(s)
    if where is not None:
        where.extend(a for a in at if a)
    return [r for r in out if r]


def name_of(n):
    """The converted name without the stray marks of the PDF ("मेघनगर            ." -> "मेघनगर", "भाण्डेर 07523..242242")."""
    n = re.sub(r"[\d.\-]+$", "", re.sub(r"\s+\.$", "", n)).strip(" .-")
    return _esw.clean(n)


def lgd_of(r):
    e = r["emails"][0] if r["emails"] else ""
    return LGD["rows"].get(e) or LGD["rows"].get(f"{r['district'] or ''}|{r['name']}|{e}")


def parse(text, url=URL):
    recs, seen = [], set()
    where = []
    for r, pos in zip(rows(text, where), where):
        code = lgd_of(r)
        latin = LGD["lgd"].get(code, {}).get("name") if code else None
        post = "Commissioner" if r["kind"] == "u-fu-" else "Chief Municipal Officer"
        recs.append(_ulb.record(MODULE, STATE, name_of(r["name"]), post, seen, phone=" ".join(r["phones"]),
                                email=" ".join(r["emails"]), district=r["district"], body_type=TYPES[r["kind"]], source=url,
                                latin=latin, lgd_code=code, area_latin=latin, division=r["division"], post_from="directory",
                                page=PAGE, src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    pages, _ = layout_pages(r.content)
    recs = parse("\f".join(pages), p["url"])
    return recs, [_esw.keep(MODULE, "directory", r.content, "pdf")], "" if recs else "no rows"
