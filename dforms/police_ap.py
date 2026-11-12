"""Andhra Pradesh Police citizen portal: citizen.appolice.gov.in (India only). GET /public/session/init first (it sets the
'visitor' cookie; without it the API answers 'Please reload the browser!'), then GET
/public/organization/police-station-table?offset=N&limit=M -> {"data": [...], "totalCount": 999}: district, sdpoOffice,
circleOffice, stationName, address, phone (the station / SHO CUG mobile, 9440xxxxxx), latitude, longitude, updatedAt.
No officer names. One queue item = the whole table (2-3 requests). Record id dept:police_ap:<district>:<station>."""
import json

from dforms._police import gz, phones, rec, slug, uniq

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

M = "police_ap"
BASE = "https://citizen.appolice.gov.in"
URL = BASE + "/our-organization/police-stations"
PAGE = 1000


def parse(rows, url=URL):
    recs = []
    for x in rows:
        st = x.get("stationName")
        if not st:
            continue
        lat, lon = x.get("latitude"), x.get("longitude")
        ok = isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and 12 < lat < 20 and 76 < lon < 85
        recs.append(rec(M, f"{slug(x.get('district'))}:{slug(st)}", area=st, post="SHO (station CUG)", phone=phones(str(x.get("phone") or "")),
                        address=x.get("address"), state="AP", district=x.get("district"), subdivision=x.get("sdpoOffice"),
                        circle=x.get("circleOffice"), office_id=x.get("stationTableId"),
                        last_updated=(x.get("updatedAt") or "")[:10] or None, lat=lat if ok else None, lon=lon if ok else None,
                        source=url))
    return uniq(recs)


def fetch(p, get):
    base = p.get("base", BASE)
    if get(base + "/public/session/init") is None:
        return [], [], "session/init did not answer"
    rows, files, total, off = [], [], None, 0
    while total is None or off < total:
        r = get(f"{base}/public/organization/police-station-table?offset={off}&limit={PAGE}")
        if r is None:
            return [], files, f"no answer at offset {off}"
        files.append(gz(M, f"police-station-table-{off}.json", r.content))
        try:
            js = r.json()
        except (ValueError, json.JSONDecodeError):
            return [], files, "not json: " + r.text[:80]
        data = js.get("data") or []
        rows += data
        total = int(js.get("totalCount") or len(rows))
        if not data:
            break
        off += len(data)
    if len(rows) < total:
        return [], files, f"only {len(rows)} of {total} rows"
    recs = parse(rows, p.get("url", URL))
    return recs, files, "" if recs else "no rows"
