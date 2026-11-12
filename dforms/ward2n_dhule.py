"""Dhule Mahanagarpalika (dhulecorporation.org): its 4 kshetriya (zone) offices, the prabhag (election wards) of each, the office
address and the ward officer (prabhag adhikari) with his mobile. One page, /dmc/ward-committee-office-1 (Marathi; in
archive.s1d.me, saved 2026-11-11; the page shows "Last Updated"), two tables:
  "अ .क्र. | क्षेत्रीय कार्यालय | प्रभाग क्र . | एकूण लोकसंख्या": office no. + address, its prabhag, population;
  "क्षेत्रीय कार्यालय | प्रभाग अधिकारी | कार्यक्षेत्र ( प्रभाग) | संपर्क क्रमांक": the ward officer of each office.
(/dmc/ward-committee-office carries the same 4 officers as text.) Records: level "zone", area "Kshetriya Karyalay <n>",
wards = its prabhag, one record per office (the officer, with the office address and population). Record ids:
dept:ward2n_dhule:kk<n>:ward-officer.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_dhule"
BODY, LGD, STATE, DISTRICT = "Dhule Mahanagarpalika", "251282", "MH", "Dhule"
URL = "https://dhulecorporation.org/dmc/ward-committee-office-1"


def items(get=None):
    return [{"key": f"{MODULE}-ward-committee-office", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def num(s):
    m = re.search(r"\d+", _ward.hi_norm(s))
    return int(m.group(0)) if m else None


def parse(html, p):
    soup = _esw.soup(html)
    m = re.search(r"Last Updated\s*([\d/]+)", _esw.clean(soup.get_text(" ")))
    last = m.group(1) if m else None
    offices, officers = {}, {}
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        head = None
        for r in g:
            low = " ".join(r)
            if "क्षेत्रीय कार्यालय" in low and ("प्रभाग अधिकारी" in low or "लोकसंख्या" in low):
                head = "officer" if "प्रभाग अधिकारी" in low else "office"
                continue
            if not head or len(r) < 4:
                continue
            r = [_ward.hi_norm(c) for c in r]
            if head == "office":
                n = num(r[1])
                addr = re.split(r"पत्ता\s*[-–:]\s*", r[1], maxsplit=1)
                offices[n] = {"address": _esw.clean(addr[1]) if len(addr) > 1 else "", "wards": _ward.wards_of(r[2]),
                              "population": re.sub(r"\D", "", r[3]) or None}
            else:
                officers[num(r[0])] = {"name": r[1], "wards": _ward.wards_of(r[2]), "phone": r[3]}
    seen, recs = set(), []
    for n in sorted(set(offices) | set(officers), key=lambda x: x or 0):
        if not n:
            continue
        o, f = offices.get(n, {}), officers.get(n, {})
        area = f"Kshetriya Karyalay {n}"
        recs.append(_ward.record(MODULE, f"kk{n}:ward-officer", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="zone", area=area, zone=area, post="Ward Officer", post_regional=f"प्रभाग अधिकारी क्र. {n}",
                                 name=f.get("name", ""), name_regional=f.get("name") or None, phone=f.get("phone", ""),
                                 address=o.get("address"), wards=f.get("wards") or o.get("wards"),
                                 population=int(o["population"]) if o.get("population") else None,
                                 vacant=None if f.get("name") else True, wing="administration", last_updated=last,
                                 source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "ward-committee-office", r.content)], "" if recs else "no office tables"
