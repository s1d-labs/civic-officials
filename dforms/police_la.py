"""Ladakh Police: police.ladakh.gov.in/pages/policestations.html. One page, four tables (police stations and police posts of
Leh and of Kargil): Name of Police Station / Name of SHO / Rank / Contact Details. Works from outside India.
One queue item = the page. Record id dept:police_la:<district>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import clean, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_la"
URL = "https://police.ladakh.gov.in/pages/policestations.html"


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        h = t.find_previous(["h", "h1", "h2", "h3", "h4", "h5"])
        label = clean(h.get_text(" ", strip=True)) if h else ""
        m = re.search(r"District\s+(\w+)", label)
        district = m.group(1) if m else None
        post_kind = "police post" if "Post" in label else "police station"
        for tr in t.find_all("tr"):
            c = [clean(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if len(c) < 4 or not c[0] or c[0].lower().startswith("name of"):
                provenance.skip_row(tr, 'skip: len(c) < 4 or not c[0] or c[0].lower().startswith("name of")')
                continue
            station, name, rank, contact = c[:4]
            recs.append(rec(M, f"{slug(district or '')}:{slug(station)}", area=station, office_type=post_kind,
                            post="SHO" if post_kind == "police station" else "Officer in charge", name=name, rank=rank,
                            phone=phones(contact), state="LA", district=district, source=url))
            recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
    return uniq(recs)


def fetch(p, get):
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "policestations.html", r.content)]
    recs = parse(r.text, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
