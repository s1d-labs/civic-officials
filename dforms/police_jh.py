"""Jharkhand Police: www.jhpolice.gov.in/police-station (Drupal view; India only). One <table> per district with a <caption>
(the district) and columns views-field-title (station, linked to /police-station/<slug>) / -field-thana-code (STD code) /
-field-thana-office-no / -field-thana-resi-no / -field-thana-mobile-no. No officer names. The whole list is ~640 rows in one
big page, so one queue item = one district through the view's own filter ?field_thana_district_nid=<nid> (26 districts incl.
Rail Dhanbad and Rail Jamshedpur); items(get) lists them from the filter's <select>. Record id dept:police_jh:<nid>:<station>."""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, gz, phones, rec, slug, uniq

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
    num = re.sub(r"\D", "", num or "")
    if not num:
        return None
    std = re.sub(r"\D", "", std or "")
    if len(num) == 10 and num[0] in "6789":
        return num
    return f"{std}-{num}" if std else num


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
            nums = [landline(std, _cell(tr, "field-thana-office-no")), landline(std, _cell(tr, "field-thana-resi-no"))]
            allp = (phones(_cell(tr, "field-thana-mobile-no")) or "").split(", ") + nums   # landlines kept as built: phones()
            allp = [n for i, n in enumerate(allp) if n and n not in allp[:i]]               # misreads '06542-222222'
            recs.append(rec(M, f"{nid}:{slug(st)}", area=st, post="Officer in charge (station mobile)", phone=", ".join(allp) or None,
                            state="JH", district=dist, office_id=a["href"].rsplit("/", 1)[-1] if a else None, source=url))
    return uniq(recs)


def fetch(p, get):
    nid = str(p["nid"])
    url = p.get("url") or district_url(nid)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, nid, p.get("district"), url)
    return recs, [gz(M, f"district-{nid}.html", r.content)], "" if recs else "no stations"
