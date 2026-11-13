"""Hospitals listed on S3WaaS district portals, "Public Utilities -> Hospitals" pages (also "Hospital", "Govt Hospitals", "Private
Hospitals", "Ambulance"): one card per hospital (heading, address, "Phone :", "Email :", "Pincode :", "Category/Type :",
"Website Link :"), read with dforms/police_s3waas.cards() (imported, not changed) and paged with /page/N/ by
dforms/_civic.s3waas_pages(). The district administration writes the cards; most give the hospital's main phone (often the
casualty / emergency desk of a government hospital), few say which desk the number is. A number that the card labels
"casualty", "emergency", "trauma" or "ambulance" also goes to emergency_phone (no card on the 2026-11-11 copies does this).
Buldhana writes ambulance counts in the address ("Government Ambulance : 7 MEMS 108 Ambulance : 1"): ambulances_govt, ambulances_108.

The cards name nobody (no medical superintendent): post is left out. Most cards have no type; the district's own words are kept
in facility_type. Public-utility pages are not India-only (archive.s1d.me saved them from Germany).
Seed: seeds/dept_emerg_hosp_s3waas.json, 471 category pages of 461 district portals that archive.s1d.me saved with at least
one card (scan of ~/data/civic-india/pu_all.tsv, 2026-11-11): 2,574 cards on the first pages, 1,463 with a phone; 131 pages
have more pages. Record ids: dept:emerg_hosp_s3waas:<host>:<slug of hospital>.
"""
import re
from urllib.parse import urlparse

from dforms import _civic, _emerg
from dforms.police_s3waas import cards, last_updated
import provenance

METHOD = "html cards (S3WaaS public utility, paged /page/N/)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_hosp_s3waas"
# reader audit (audit.py): no drop (2026-11-13: 372 cards on the saved pages, 372 records, one per card). A card with no phone
# or e-mail names no person, so it is a record but not a "person" record. On pages without tables the audit counts page furniture
# as blocks: the S3WaaS accessibility widget, the state banner, the site menus and footer, and on a page of 1-2 cards the lines of
# a card ("Email : | x"; the card is the block). They hold no other person.
AUDIT_LEAVES_OUT = (r"^(हिन्दी \| )?(Accessibility Links|Accessibility Tools|High Contrast|Font Size Increase|Big Cursor|Skip to|"
                    r"Home \| About District|Useful Links \| Website Policies|Email :|Website Link :|Category/Type :|Phone :|"
                    r"Pincode :)|(सरकार|शासन|அரசு|ସରକାର|সরকার|ಸರ್ಕಾರ|સરકાર) \| (?i:gov)")
EMERG = re.compile(r"(?i)\b(casualty|emergency|trauma|ambulance)\b[^:\d|]{0,15}:?\s*((?:\+?\d[\d -]{6,}\d[,/ ]*)+)")
CONTACT = re.compile(r"(?i)(?:contact|phone|ph|mob(?:ile)?|tel|landline)[^:\d]{0,12}:?\s*((?:\+?\d[\d -]{5,}\d[,/ ]*)+)")


def items(get=None):
    return _emerg.seed(MODULE)


def kind_of(c, page_url):
    """The district's own type word, or the category of the page ("Private Hospitals", "Ambulance") when the card has none."""
    t = _emerg.clean(c.get("type"))
    if t:
        return t
    cat = urlparse(page_url).path.split("/public-utility-category/")[-1].split("/")[0]
    cat = re.sub(r"-(en|rang)$", "", cat)
    return {"private-hospital": "Private Hospital", "private-hospitals": "Private Hospital", "govt-hospitals": "Government Hospital",
            "government-hospitals": "Government Hospital", "ambulance": "Ambulance", "ambulance-services": "Ambulance"}.get(cat)


def count(label, text):
    """A count the card writes after a label ("Government Ambulance : 7"), as int, else None."""
    m = re.search(rf"(?i){label}\s*:\s*(\d+)\b", text or "")
    return int(m.group(1)) if m else None


def records(pages, p):
    host = urlparse(p["url"]).netloc
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        cw = []
        for ci, c in enumerate(cards(html, cw)):
            name = _emerg.clean(c.get("title"))
            if not name:
                provenance.skip_row(c, 'skip: not name')
                continue
            key = _emerg.unique(f"{host}:{_emerg.slug(name)}", seen)
            adr = _emerg.clean(c.get("address"))
            text = " | ".join(_emerg.clean(c.get(k)) or "" for k in ("title", "address", "phone"))
            em = [m.group(2) for m in EMERG.finditer(text)]
            m = CONTACT.search(adr)
            kind = kind_of(c, url)
            recs.append(_emerg.record(
                MODULE, key, "hosp", dept="health", level="facility", area=name,
                phone=_emerg.phones(c.get("phone") or "", m.group(1) if m else "", *em),
                emergency_phone=_emerg.phones(*em) if em else None,
                email=_emerg.emails(c.get("email") or ""), address=adr,
                pincode=re.sub(r"\D", "", c.get("pincode") or c.get("pin code") or "")[:6] or None,
                facility_type=kind, website=_emerg.clean(c.get("website")),
                ambulances_govt=count(r"government ambulance", adr), ambulances_108=count(r"(?:mems\s*)?108 ambulance", adr),
                district=p.get("district"), state=p.get("state"), office_id=key, source=url, last_updated=lu,
                src_url=url, src_pos=cw[ci]))
    return recs


def fetch(p, get):
    pages, files = _civic.s3waas_pages(p, get, MODULE)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
