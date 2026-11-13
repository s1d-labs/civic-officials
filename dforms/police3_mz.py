"""Mizoram Police senior officers: police.mizoram.gov.in/page/senior-police-officers (India only, like police_mz: 403 from
outside India; answers from Mumbai). One table "Designation | Name | Office": DGP, IGPs, DIGPs, AIGPs, the SPs of the 11
districts ("SP  Aizawl" ... "SP  Hnahthial"), SPs of units (CID, security, traffic, cyber crime, narcotics, ANTF, F&ES), the
battalion commandants and ex-cadre posts. The page carries inline base64 images (about 1.4 MB): the kept copy has them cut out.
Kept: every row with a name or a number (vacant posts with neither are left out). "SP <district>" -> level district,
office_type office; others -> level state (office_type unit; battalion for "CO ... Bn", traffic / cyber by keyword).
One queue item = the page. Record id dept:police3_mz:<district or post slug>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py)

M = "police3_mz"
URL = "https://police.mizoram.gov.in/page/senior-police-officers"
DISTRICTS = ["Aizawl", "Champhai", "Kolasib", "Lawngtlai", "Lunglei", "Mamit", "Siaha", "Serchhip", "Hnahthial", "Saitual",
             "Khawzawl"]


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for ti, t in enumerate(soup.find_all("table")):
        for ri, tr in enumerate(t.find_all("tr")):
            c = [clean(x.get_text(" ", strip=True)) or "" for x in tr.find_all(["td", "th"])]
            if len(c) < 2 or c[0].lower() == "designation":
                continue
            c += [""] * (3 - len(c))
            post, name, office = c[0], c[1], c[2]
            ph = phones(office)
            if not name and not ph:
                continue
            common = dict(name=name or None, phone=ph, office_phone=office or None, state="MZ", source=url,
                          src_pos={"table": ti, "row": ri})
            m = re.match(r"^S\.?P\.?\s+(\w+)$", post)
            d = next((x for x in DISTRICTS if m and m.group(1).lower() == x.lower()), None)
            if d:
                recs.append(rec(M, slug(d), level="district", office_type="office", area=d, post=post, district=d, **common))
                continue
            ot = ("battalion" if re.search(r"\bBn\b|battalion", post, re.I) else "traffic" if re.search(r"traffic", post, re.I)
                  else "cyber" if re.search(r"cyber", post, re.I) else "unit")
            recs.append(rec(M, slug(post), level="state", office_type=ot, area="Mizoram", post=post, **common))
    return uniq(recs)


def items(get=None):
    return [{"key": f"{M}:senior-police-officers", "payload": {"reader": M, "url": URL, "state": "MZ"}}]


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, url)
    content = re.sub(rb"data:[a-z/+]+;base64,[A-Za-z0-9+/=]+", b"data:,", r.content)
    return recs, [gz(M, "senior-police-officers", content)], "" if recs else "no rows"
