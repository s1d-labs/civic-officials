"""Chhattisgarh district portals (S3WaaS, <district>.gov.in, <district>.cg.gov.in): police pages that seeds/dept_police_cg.json
does not list yet. Two passes on one page (and its /page/N/ pages):
1. police_s3waas (tables with "Police Station | CUG ..." heads and public-utility cards), records renamed to police3_cg;
2. if that gives nothing, the plain tables these pages use instead:
   - "Sr. No | Details | Contact Number" with section rows "Sub-Division <name>" / "Other's" (Mahasamund): Thana / Chauki /
     Traffic / Ajaak / Control Room rows, the sub-division kept as subdivision;
   - "sno | PS Name | Pin Code | Gram Panchayat | Block | Landline No. of Site" (Janjgir-Champa, Sakti);
   - "S.No. | Name of PS | Landline and DSPT Number | CUG Number | Email ID" (Bijapur);
   - "Label | Value" (Sukma: SP, ASP = names; counts such as "No. of Thanas" are left out).
CUG numbers (94791-9xxxx) belong to the post, not to a person; most pages give no officer names.
Station rows: level police_station (office_type police station, police post for Chauki / outpost, women for AJK / Ajaak /
mahila, traffic, control_room, cyber, unit for branches such as Special Branch, Crime Branch, Reserve Centre, Arms).
Hosts answer from India (Mumbai, 2026-11-13); copies were saved by archive.s1d.me. Record id dept:police3_cg:<district>:<slug>.
"""
import re

from bs4 import BeautifulSoup

from dforms import police_s3waas
from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table (S3WaaS police page)"     # source trail (provenance.py): how this reader reads its sources
# reader audit (audit.py): no drop (2026-11-13: 14 cards on the saved pages, 14 records, one per card). A card with no phone
# or e-mail names no person, so it is a record but not a "person" record. On pages without tables the audit counts page furniture
# as blocks: the S3WaaS accessibility widget, the state banner, the site menus and footer, and on a page of 1-2 cards the lines of
# a card ("Email : | x"; the card is the block). They hold no other person.
AUDIT_LEAVES_OUT = (r"^(हिन्दी \| )?(Accessibility Links|Accessibility Tools|High Contrast|Font Size Increase|Big Cursor|Skip to|"
                    r"Home \| About District|Useful Links \| Website Policies|Email :|Website Link :|Category/Type :|Phone :|"
                    r"Pincode :)|(सरकार|शासन|அரசு|ସରକାର|সরকার|ಸರ್ಕಾರ|સરકાર) \| (?i:gov)")

M = "police3_cg"

STATION_H = re.compile(r"^(details|ps name|name of ps|name of police station|police station|thana|station name)$", re.I)
PHONE_H = re.compile(r"contact|landline|phone|cug|mobile|dspt", re.I)
SKIP_LABEL = re.compile(r"^no\.? ?of\b|number of", re.I)


def unit_type(name):
    n = name.lower()
    if re.search(r"\bajaak\b|\bajak\b|\bajk\b|mahila|women", n):
        return "women"
    if "traffic" in n:
        return "traffic"
    if "control room" in n:
        return "control_room"
    if "cyber" in n:
        return "cyber"
    if re.search(r"chauki|chowki|out ?post|police post", n):
        return "police post"
    if re.search(r"branch|squad|reserve|arms|\batm\b|line|cell|\bdsb\b|\bdcb\b", n):
        return "unit"
    return "police station"


def _cells(tr):
    return [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all(["td", "th"])]


def tables(html, url, district, state="CG"):
    soup = BeautifulSoup(html, "lxml")
    d = slug(district)
    out = []
    for ti, t in enumerate(soup.find_all("table")):
        rows = t.find_all("tr")
        if not rows:
            continue
        head = [h.lower().strip(" .:") for h in _cells(rows[0])]
        if head[:2] == ["label", "value"]:
            for ri, tr in enumerate(rows[1:], 1):
                c = _cells(tr)
                if len(c) < 2 or not c[1] or SKIP_LABEL.search(c[0]) or not re.search(r"[A-Za-zऀ-ॿ]", c[1]):
                    provenance.skip_row(tr, 'skip: len(c) < 2 or not c[1] or SKIP_LABEL.search(c[0]) or not re.search(...')
                    continue
                post = c[0]
                level, otype = police_s3waas.level_of(post, post, default="district")
                out.append(rec(M, f"{d}:{slug(post)}", level=level, office_type=otype, area=district, post=post, name=c[1],
                               state=state, district=district, source=url, src_url=url, src_pos={"table": ti, "row": ri}))
            continue
        si = next((i for i, h in enumerate(head) if STATION_H.match(h)), None)
        if si is None:
            continue
        pcols = [i for i, h in enumerate(head) if PHONE_H.search(h)]
        ecol = next((i for i, h in enumerate(head) if re.search(r"e-?mail", h)), None)
        extra = {h: i for i, h in enumerate(head) if re.search(r"pin ?code|gram panchayat|block", h)}
        sub = None
        for ri, tr in enumerate(rows[1:], 1):
            c = _cells(tr)
            if len(c) == 1:          # section row: "Sub-Division Mahasamund", "Other's"
                m = re.match(r"^sub[- ]?division\s+(.+)$", c[0], re.I)
                sub = clean(m.group(1)) if m else None
                continue
            if len(c) <= si or not c[si]:
                provenance.skip_row(tr, 'skip: len(c) <= si or not c[si]')
                continue
            name = c[si]
            ph = phones(*(c[i] for i in pcols if i < len(c) and c[i].strip("–—- ")))
            ut = unit_type(name)
            f = dict(area=name, post="SHO" if ut in ("police station", "women", "cyber") else "In-charge", phone=ph,
                     email=email(c[ecol]) if ecol is not None and ecol < len(c) else None, office_type=ut,
                     subdivision=sub, state=state, district=district, source=url, src_url=url, src_pos={"table": ti, "row": ri})
            for h, i in extra.items():
                if i < len(c) and c[i].strip("–—- "):
                    f[re.sub(r"\W+", "_", h).strip("_")] = c[i]
            level = "police_station" if ut in ("police station", "police post", "women", "cyber") else "district"
            out.append(rec(M, f"{d}:{slug(name)}", level=level, **f))
    return uniq(out)


def fetch(p, get):
    p = {"state": "CG", **p}
    recs, files, why = police_s3waas.fetch(p, get, M)
    if recs:
        return recs, files, why
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = tables(r.text, url, p["district"], p["state"])
    return recs, [gz(M, slug(p["district"]), r.content)], "" if recs else "no rows"
