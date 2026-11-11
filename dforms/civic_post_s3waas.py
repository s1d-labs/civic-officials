"""Post offices with phone numbers from the "Public Utilities -> Postal" pages of S3WaaS district portals (<district>.nic.in,
<district>.gov.in, <district>.ap.gov.in ...): /public-utility-category/postal/ (also post, post-office, post-offices, postoffice,
and the Hindi slugs डाक / डाकघर / डाक-घर), 10 cards a page, paged with /page/N/. A card has the office as its heading
("ASHOKNAGAR HO", "Greamspet Post Office", "Head Post Office") and lines "Phone :", "Email :", "Pincode :", "Website Link :" and an
address. Some districts list every office of the district (Ashoknagar: 2 pages), most list the head office and a few sub offices.
The pages carry no postmaster names (a card that says "Postmaster, Post Office AKOLA (HEAD OFFICE)" names the post, not a person).
The cards are read with dforms/police_s3waas.cards() and .next_pages() (imported, not changed).

Seed: seeds/dept_civic_post_s3waas.json, one item per district page, built from the district sites in sites.csv whose
public-utility postal pages archive.s1d.me holds (scan of 2026-11-11). Payload: url, state, district, max_pages.
Record ids: dept:civic_post_s3waas:<host>:<pincode>-<slug of office>.
"""
import re
from urllib.parse import urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import cards, last_updated

MODULE = "civic_post_s3waas"
MAX_PAGES = 30


def items(get=None):
    """The seed file is the list (it is built from archive.s1d.me, not from a request)."""
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def post_of(title):
    t = title.upper()
    if re.search(r"\bH\.?\s?O\b|HEAD (POST )?OFFICE|\bGPO\b|GENERAL POST OFFICE", t):
        return "HO", "Postmaster"
    if re.search(r"\bB\.?\s?O\b|BRANCH", t):
        return "BO", "Branch Postmaster"
    if re.search(r"\bS\.?\s?O\b|SUB (POST )?OFFICE|SUB-POST", t):
        return "SO", "Sub Postmaster"
    return None, "Postmaster"


def records(pages, p):
    host = urlparse(p["url"]).netloc
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        for c in cards(html):
            office = _esw.clean(c.get("title"))
            if not office:
                continue
            pin = re.sub(r"\D", "", c.get("pincode") or "")[:6]
            if not pin:
                m = re.search(r"\b(\d{3})\s?(\d{3})\b", c.get("address") or "")
                pin = m.group(1) + m.group(2) if m else ""
            typ, post = post_of(office)
            key = _civic.unique(f"{host}:{pin + '-' if pin else ''}{_esw.slug(office)}", seen)
            recs.append(_civic.record(
                MODULE, key, "post", dept="postal", level="facility", area=office, post=post, office_type=typ,
                phone=_esw.phones(c.get("phone") or ""), email=_esw.emails(c.get("email") or ""), address=c.get("address"),
                pincode=pin, district=p.get("district"), state=p.get("state"), office_id=key, website=c.get("website"),
                source=url, last_updated=lu))
    return recs


def fetch(p, get):
    pages, files = _civic.s3waas_pages(p, get, MODULE, MAX_PAGES)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
