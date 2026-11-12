"""Jharkhand Police: www.jhpolice.gov.in/police-station (Drupal view; India only). One <table> per district with a <caption>
(the district) and columns views-field-title (station, linked to /police-station/<slug>) / -field-thana-code (STD code) /
-field-thana-office-no / -field-thana-resi-no / -field-thana-mobile-no. No officer names. The whole list is ~640 rows in one
big page, so one queue item = one district through the view's own filter ?field_thana_district_nid=<nid> (26 districts incl.
Rail Dhanbad and Rail Jamshedpur); items(get) lists them from the filter's <select>. Record id dept:police_jh:<nid>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms import _civic
from dforms._police import clean, gz, phones, rec, slug, uniq

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police_jh"
URL = "https://www.jhpolice.gov.in/police-station"


def district_url(nid):
    return f"{URL}?field_thana_district_nid={nid}"


def items(get):
    r = get(URL)
    if r is None:
        return []
    soup = BeautifulSoup(r.text, "lxml")
    sel = soup.find("select", attrs={"name": "field_thana_district_nid"})
    return [{"key": f"{M}:{o['value']}-{slug(o.get_text())}",
             "payload": {"reader": M, "url": district_url(o["value"]), "state": "JH", "nid": o["value"], "district": clean(o.get_text()),
                         "india_only": True}}
            for o in (sel.find_all("option") if sel else []) if (o.get("value") or "").isdigit()]


def _cell(tr, field):
    td = tr.find("td", class_=f"views-field-{field}")
    return clean(td.get_text(" ", strip=True)) if td else None


def landline(std, num):
    """'0651' + '2242132' -> '0651-2242132'. Placeholders ('0', '0, 0', '--') give None; an STD code without its 0 ('6542')
    gets it back. A cell with several numbers ('253290, 86339') gives the first; see landlines() for all of them."""
    nums, _ = landlines(std, num)
    return nums[0] if nums else None


def landlines(std, cell):
    """(phones, short numbers) of one cell: each number of 6+ digits with the STD code; parts of 1-5 digits that are not
    placeholders ('86339', '7265': short police exchange numbers, not dialable alone) are given apart."""
    std = re.sub(r"\D", "", std or "")
    if set(std) <= {"0"}:
        std = ""
    elif not std.startswith("0"):
        std = "0" + std
    out, short = [], []
    for part in re.split(r"[,;/&]|\bor\b", cell or ""):
        num = re.sub(r"\D", "", part)
        if not num or set(num) == {"0"}:
            continue
        if len(num) < 6:
            short.append(num)
        elif len(num) == 10 and num[0] in "6789":
            out.append(num)
        elif num.startswith("0") and len(num) >= 10:
            out.append(num)
        else:
            out.append(f"{std}-{num}" if std else num)
    return out, short


def parse(html, nid, district=None, url=URL):
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for t in soup.find_all("table"):
        cap = t.find("caption")
        dist = clean(cap.get_text(" ", strip=True)) if cap else district
        for tr in t.find_all("tr"):
            st = _cell(tr, "title")
            if not st or not tr.find("td"):
                continue
            a = tr.find("td", class_="views-field-title").find("a", href=True)
            std = _cell(tr, "field-thana-code")
            office, short = landlines(std, _cell(tr, "field-thana-office-no"))
            resi, short2 = landlines(std, _cell(tr, "field-thana-resi-no"))
            mob = [n for n in (phones(_cell(tr, "field-thana-mobile-no")) or "").split(", ") if n and set(re.sub(r"\D", "", n)) != {"0"}]
            allp = mob + office + resi                                                      # landlines kept as built: phones()
            allp = [n for i, n in enumerate(allp) if n and n not in allp[:i]]               # misreads '06542-222222'
            recs.append(rec(M, f"{nid}:{slug(st)}", area=st, post="Officer in charge (station mobile)", phone=", ".join(allp) or None,
                            short_numbers=", ".join(short + short2) or None,
                            state="JH", district=dist, office_id=a["href"].rsplit("/", 1)[-1] if a else None, source=url,
                            src_pos=_civic.tr_pos(tr)))
    return uniq(recs)


def fetch(p, get):
    nid = str(p["nid"])
    url = p.get("url") or district_url(nid)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, nid, p.get("district"), url)
    return recs, [gz(M, f"district-{nid}.html", r.content)], "" if recs else "no stations"
