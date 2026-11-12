"""Common Service Centres and state service centres listed on S3WaaS district portals, "Public Utilities" pages: CSC (Manipur,
Nuh, Palamu, Nadia), Atal Seva Kendra rural / urban (Haryana: Kaithal, Panipat, Rohtak, Palwal, Karnal, Nuh), Antyodaya SARAL
Kendra (Haryana), Lok Sewa Kendra (Chhattisgarh, MP), Sewa Setu Kendra (Chhattisgarh), Sewa Kendra (Punjab), Saanjh Kendra
(Punjab), Jana Snehi Kendra (Karnataka), MeeSeva centres (Hyderabad), Bangla Sahayata Kendra (Malda) ...; cards read with
dforms/police_s3waas.cards() (imported, not changed), paged with /page/N/.
Atal Seva Kendra cards name the village level entrepreneur first in the address ("Hira Lal, Panchayat Office, Bhuna Road, Ram Nagar,
Guhla"): items with "operator_first": true take that first part as the name when it looks like a person's name (2 to 5 words of
letters, no place or office word); "S/O <father>" is cut. Other cards name only the centre.
Seed: seeds/dept_civic_csc_s3waas.json (category pages that archive.s1d.me holds, scan of 2026-11-11; English pages first, a Hindi
page only when the site has no English one). Record ids: dept:civic_csc_s3waas:<host>:<category>:<slug of centre>-<n>.
"""
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import cards, last_updated

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

MODULE = "civic_csc_s3waas"
PLACE = re.compile(r"(?i)\b(village|vill|vpo|v\.?p\.?o|office|road|near|opp|sector|sec|chowk|panchayat|tehsil|block|market|bazar|"
                   r"ward|colony|nagar|street|complex|building|bhawan|kendra|centre|center|bank|kiosk|shop|plot|house|gali|mandir|"
                   r"school|stand|distt|district|p\.?o|h\.?no|no\.)\b|\d")


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def operator(address):
    """'Subhash Sharma S/O Sadhu Ram Vill. Bad Seekri Kalan, Kalayat' -> 'Subhash Sharma'; '' when the first part is a place."""
    first = re.split(r",|\bS/O\b|\bD/O\b|\bW/O\b", address or "", maxsplit=1, flags=re.I)[0].strip(" .-")
    words = first.split()
    if not 2 <= len(words) <= 5 or PLACE.search(first) or not re.fullmatch(r"[A-Za-z. ]+", first):
        return ""
    return first


def kind(url):
    return unquote(urlparse(url).path.rstrip("/").split("/")[-1])


def records(pages, p):
    host = urlparse(p["url"]).netloc
    cat = kind(p["url"])
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    recs, seen = [], set()
    for url, html in pages:
        for c in cards(html):
            centre = _esw.clean(c.get("title"))
            if not centre:
                continue
            adr = _esw.clean(c.get("address"))
            name = operator(adr) if p.get("operator_first") else ""
            key = _civic.unique(f"{host}:{_esw.slug(cat) or 'csc'}:{_esw.slug(centre)}", seen)
            pin = re.sub(r"\D", "", c.get("pincode") or "")[:6]
            recs.append(_civic.record(
                MODULE, key, "csc", dept="digital_services", level="facility", area=centre, post="Operator" if name else None,
                name=name, phone=_esw.phones(c.get("phone") or ""), email=_esw.emails(c.get("email") or ""), address=adr,
                pincode=pin, centre_type=p.get("centre_type") or cat, district=p.get("district"), state=p.get("state"),
                office_id=key, website=c.get("website"), source=url, last_updated=lu))
    return recs


def fetch(p, get):
    pages, files = _civic.s3waas_pages(p, get, MODULE)
    if pages is None:
        return [], [], "no answer"
    recs = records(pages, p)
    return recs, files, "" if recs else "no cards"
