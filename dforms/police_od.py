"""Odisha: district portal police pages, <district>.odisha.gov.in/en/administartive-setup/distrcit-police (the site's spelling).
Jharsuguda's page is an RTI table: Sphere (the police station or office) | P.I.O. (the IIC: "Inspector S.Bala,IIC, Jharsuguda
P.S. Contact No.- 06645-272736") | A.P.I.O. (a sub-inspector) | Appellate Authority. Other districts use the same path but
show no table (Sambalpur, 2026-11-11). Answers only from India. One queue item = one district page.
Record id dept:police_od:<district>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, rec, slug, uniq
from dforms.police_s3waas import fix_phone, grid, level_of

M = "police_od"
CONTACT = re.compile(r"Contact\s*No\.?\s*[-:.]?\s*(.*)$", re.I)
OFFICER = re.compile(r"^(?:Shri\.?\s+|Smt\.?\s+)?(Inspector|Inspr\.?|S\.?I\.?|Sub[- ]Inspector)?\s*\.?\s*([^,]+?)\s*,?\s*(IIC|OIC|SDPO|DSP)\b", re.I)


def officer(cell):
    """'Inspector S.Bala,IIC, Jharsuguda P.S. Contact No.- 06645- 272736' -> (name, rank, post, phone)."""
    cell = clean(cell) or ""
    m = CONTACT.search(cell)
    phone = fix_phone(re.sub(r"(\d{4,5})-\s+(\d)", r"\1-\2", m.group(1))) if m else None   # 06645-..: not _police.phones()
    head = cell[:m.start()] if m else cell
    o = OFFICER.search(head)
    if o:
        return clean(o.group(2)).strip(" .,"), clean(o.group(1)), o.group(3).upper(), phone
    parts = [x.strip() for x in head.split(",") if x.strip()]
    return (parts[0] if parts else None), None, None, phone


def parse(html, district, url):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        rows = grid(t)
        if not rows or not any("sphere" in (c or "").lower() for c in rows[0]):
            continue
        for r in rows[1:]:
            if len(r) < 3 or not r[1]:
                continue
            sphere = clean(r[1])
            name, rank, post, phone = officer(r[2])
            level, otype = level_of(sphere, "", "district")
            if post == "IIC":
                level, otype = "police_station", "police station"
            recs.append(rec(M, f"{slug(district)}:{slug(sphere)}", level=level, office_type=otype, area=sphere,
                            post=post or "PIO", name=name, rank=rank, phone=phone, state="OD", district=district,
                            deputy=clean(r[3]) if len(r) > 3 and r[3] else None, source=url))
    return uniq(recs)


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p.get("district") or "", url)
    m = re.search(r'Updated\s*:?\s*<time datetime="(\d{4}-\d{2}-\d{2})', r.text)
    for _, d in recs:
        if m:
            d["last_updated"] = m.group(1)
    return recs, [gz(M, f"{slug(p.get('district') or url)}-police.html", r.content)], "" if recs else "no police table"
