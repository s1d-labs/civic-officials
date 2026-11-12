"""Fire stations listed on S3WaaS district portals, "Public Utilities -> Fire Station / Fire Service / Fire Brigade / Fire" pages
(Howrah, Jalpaiguri, Kalimpong, Malda, Jagtial, Nizamabad, Krishnagiri, North Tripura, Palamu, Tuensang, Wayanad): one card per
station (heading, address, "Phone :", "Email :", "Pincode :"; Jalpaiguri writes more numbers in the address after "All Contact
No:"), read with dforms/police_s3waas.cards() (imported, not changed), paged with /page/N/. No officer names.
Seed: seeds/dept_civic_fire_s3waas.json (11 pages that archive.s1d.me holds, scan of
2026-11-11). Record ids: dept:civic_fire_s3waas:<host>:<slug of station>.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import cards, last_updated

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_fire_s3waas"


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def records(pages, p):
    host = urlparse(p["url"]).netloc
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        for c in cards(html):
            station = _esw.clean(c.get("title"))
            if not station:
                continue
            key = _civic.unique(f"{host}:{_esw.slug(station)}", seen)
            adr = _esw.clean(c.get("address"))
            m = re.search(r"(?i)(?:contact|phone|mob(?:ile)?|tel)[^:\d]{0,12}:?\s*((?:\+?\d[\d -]{5,}\d[,/ ]*)+)", adr)
            recs.append(_civic.record(
                MODULE, key, "fire", dept="fire", level="facility", area=station, post="Station Officer",
                phone=_esw.phones(c.get("phone") or "", m.group(1) if m else ""), email=_esw.emails(c.get("email") or ""),
                address=adr,
                pincode=re.sub(r"\D", "", c.get("pincode") or "")[:6], district=p.get("district"), state=p.get("state"),
                office_id=key, source=url, last_updated=lu))
    return recs


def fetch(p, get):
    pages, files = _civic.s3waas_pages(p, get, MODULE)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
