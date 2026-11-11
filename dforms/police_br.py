"""Bihar Police: police.bihar.gov.in/PoliceStationHandler.ashx (the JSON behind the site's SPA; India only).
?action=getalldistricts&lang=en -> 44 police districts {id, name, name_hi, station_count} (1,380 stations incl. rail, cyber,
traffic and women thanas); ?action=search&districtId=<id>&lang=en -> data[] {ps_id, ps_name_en, ps_name_hi, district_name,
email, mobile}. The mobile is the SHO CUG number (9031xxxxxx); no SHO names. One queue item = one district (payload
district_id, district, expected); items(get) lists them. Record id dept:police_br:<ps_id>."""
import json

from dforms._police import email, gz, phones, rec, slug

M = "police_br"
BASE = "https://police.bihar.gov.in/PoliceStationHandler.ashx"
SOURCE = "https://police.bihar.gov.in/"


def items(get):
    r = get(BASE + "?action=getalldistricts&lang=en")
    if r is None:
        return []
    return [{"key": f"{M}:{x['id']}-{slug(x.get('name_en') or x['name'])}",
             "payload": {"reader": M, "url": f"{BASE}?action=search&districtId={x['id']}&lang=en", "state": "BR",
                         "district_id": x["id"], "district": x.get("name_en") or x["name"], "expected": x.get("station_count"),
                         "india_only": True}}
            for x in r.json().get("districts") or []]


def parse(rows, url=SOURCE):
    recs = []
    for x in rows:
        st = x.get("ps_name_en") or x.get("ps_name")
        if not st:
            continue
        key = str(x["ps_id"]) if x.get("ps_id") is not None else f"{slug(x.get('district_name'))}:{slug(st)}"
        recs.append(rec(M, key, area=st, area_regional=x.get("ps_name_hi"), post="SHO (station CUG)", phone=phones(x.get("mobile")),
                        email=email(x.get("email")), state="BR", district=x.get("district_name"),
                        office_id=str(x["ps_id"]) if x.get("ps_id") is not None else None, source=url))
    return recs


def fetch(p, get):
    url = p.get("url") or f"{BASE}?action=search&districtId={p['district_id']}&lang=en"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"district-{p['district_id']}.json", r.content)]
    try:
        js = r.json()
    except (ValueError, json.JSONDecodeError):
        return [], files, "not json"
    recs = parse(js.get("data") or [], url)
    return recs, files, "" if recs else "no stations"
