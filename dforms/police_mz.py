"""Mizoram Police: police.mizoram.gov.in/page/contact-numbers-of-police-stations-and-outposts. India only (403 from outside).
One table: District (rowspan) | Police Stations / Outposts | PS/OC Number. The numbers are the officer-in-charge CUGs
(690931xxxx); no names. About 45 PS and 16 OP. One queue item = the page. Record id dept:police_mz:<district>:<station>."""
from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import clean, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_mz"
URL = "https://police.mizoram.gov.in/page/contact-numbers-of-police-stations-and-outposts"


def parse(html, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        district, left = None, 0
        for tr in t.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                provenance.skip_row(tr, 'skip: not cells')
                continue
            c = [clean(x.get_text(" ", strip=True)) for x in cells]
            if left > 0 and len(c) == 2:
                left -= 1
            elif len(c) >= 3:
                district = c[0]
                left = int(cells[0].get("rowspan") or 1) - 1
                c = c[1:]
            else:
                continue
            station, num = c[0], c[1]
            if not station or station.lower().startswith("police station"):
                provenance.skip_row(tr, 'skip: not station or station.lower().startswith("police station")')
                continue
            kind = "out post" if station.upper().endswith(" OP") else "police station"
            recs.append(rec(M, f"{slug(district or '')}:{slug(station)}", area=station, office_type=kind, post="Officer in charge",
                            phone=phones(num), state="MZ", source=url,
                            **({"unit": district} if "special" in (district or "").lower() else {"district": district})))
            recs[-1][1]["src_pos"] = _civic.tr_pos(tr)
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    soup = BeautifulSoup(r.text, "lxml")
    tables = "".join(str(t) for t in soup.find_all("table"))
    files = [gz(M, "contact-numbers.html", r.content)]
    recs = parse(tables or r.text, url)
    return recs, files, "" if recs else "no rows"
