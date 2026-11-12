"""Odisha: phones of ward members from municipalities' own sites. Jharsuguda: jharsugudamunicipality.in/about-us/elected-
representatives/ (WordPress, one card per member: name, post, "Contact No.: +91 ...", "Location : Ward No. - 2 (Jharsuguda)";
the 2022 council, the same members as cforms/od.py). Other Odisha bodies checked in archive.s1d.me (2026-11-11): Berhampur
(www.berhampur.gov.in/corporators.php) lists names and wards only; Cuttack, Rourkela, Sambalpur have no saved member page.
One queue item = one body: payload {"kind": "form-cp_od", "state": "OD", "url", "body" (the name cforms/od.py gives), "lgd_code",
"slug" (cforms/od.py's body slug, for record_for)}. Seeds: seeds/councillors_cp_od.json."""
import gzip
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from cforms import cp_common as cp

METHOD = "html cards (.author-text), else html table"     # source trail (provenance.py): how this reader reads its sources


def cards(html, p, url):
    recs = []
    for k, card in enumerate(BeautifulSoup(html, "lxml").select(".author-text"), 1):
        name = card.select_one(".author-name")
        if not name:
            continue
        post = card.select_one(".deg")
        conts = {}
        for c in card.select(".cont"):
            t = " ".join(c.get_text(" ", strip=True).split())
            k, _, v = t.partition(":")
            conts[k.strip().lower()] = v.strip()
        loc = conts.get("location", "")
        m = re.search(r"Ward\s*No\.?\s*-?\s*(\d+)\s*(?:\((.*?)\))?", loc, re.I)
        ward = str(int(m.group(1))) if m else None
        nm = re.sub(r"^(Sri|Smt|Shri|Dr)\.?\s+", "", name.get_text(" ", strip=True))
        recs.append(cp.record("OD", p["body"], ward, nm, url, phone=cp.phones(conts.get("contact no.") or conts.get("contact no")),
                              position=post.get_text(" ", strip=True) if post else None, ward_label=loc or None,
                              lgd_code=p.get("lgd_code"), record_for=f"councillor:OD:{p['slug']}:{ward}" if ward else None,
                              extra={"ward_name": m.group(2)} if m and m.group(2) else None,
                              pos={"selector": ".author-text", "card": k}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/OD/cp/{urlsplit(p['url']).hostname}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = cards(r.text, p, p["url"]) or cp.table_members(r.text, "OD", p["body"], p["url"], lgd_code=p.get("lgd_code"),
                                                          record_prefix=f"councillor:OD:{p['slug']}")
    good = cp.useful(recs)
    return cp.keyed("OD", p["slug"], good), files, "" if good else ("no members listed" if not recs else "no contacts listed")
