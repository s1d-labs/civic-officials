"""Pune City Police (commissionerate, 45 stations): the public JSON API behind the punepolice.gov.in site.
GET admin.punepolice.gov.in/api/ps -> {"ps": [...]} (id, Marathi name, address, phone as HTML-entity Devanagari digits, email,
map link); GET /api/ps?ps=<id> -> [one object] with English and Marathi names, address, phone, the officer in charge (oname,
oname_mr, opost, omobile), zone (name_zo), division (name_di, phone_div) and up to 8 police chowkis (chname/chowkiN + chphoneN).
Works from outside India. One queue item = the whole list (46 requests). Records: one per station
(dept:police_pune:<id>) and one per chowki (dept:police_pune:<id>:chowki-<n>, office_type "police chowki")."""
import html as htmlmod
import json
import re

from dforms._police import ascii_digits, email, gz, phones, rec, uniq

METHOD = "json api"     # source trail (provenance.py): how this reader reads its sources

M = "police_pune"
API = "https://admin.punepolice.gov.in/api/ps"
SITE = "https://punepolice.gov.in/"


def latlon(map_link):
    m = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", map_link or "")
    return (float(m.group(2)), float(m.group(1))) if m else (None, None)


def ph(s):
    return phones(ascii_digits(htmlmod.unescape(s or ""))) if s else None


def station(base, d):
    """base: the row of the list; d: the detail object (may be {})."""
    # the API gives some phone numbers as JSON numbers: text for the phone and email helpers
    base, d = ({k: str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for k, v in x.items()} for x in (base, d))
    sid = base.get("id") or d.get("id")
    lat, lon = latlon(d.get("map_link") or base.get("map_link"))
    name_en, name_mr = d.get("name"), d.get("name_mr") or base.get("name")
    out = [rec(M, str(sid), area=name_en or name_mr, area_regional=name_mr if name_en else None,
               post=d.get("opost") or "Police station in-charge", post_regional=d.get("opost_mr"),
               name=d.get("oname"), name_regional=d.get("oname_mr"),
               phone=phones(d.get("omobile"), ph(d.get("phone") or base.get("phone")), ph(d.get("phone2"))),
               mobile=phones(d.get("omobile")), landline=phones(ph(d.get("phone") or base.get("phone")), ph(d.get("phone2"))),
               email=email(d.get("email") or base.get("email") or ""),
               email_2=email(d.get("email_2") or ""), address=d.get("address") or base.get("address"),
               address_regional=d.get("address_mr") if d.get("address") else None, zone=d.get("name_zo"),
               division=d.get("name_di"), division_phone=phones(d.get("phone_div")), state="MH", district="Pune",
               office_id=str(sid), lat=lat, lon=lon, source=f"{API}?ps={sid}", last_updated=(d.get("updated_at") or "")[:10] or None)]
    for n in range(1, 9):
        cn = d.get("chname" if n == 1 else f"chowki{n}")
        if not cn:
            continue
        cmr = d.get("chname_mr" if n == 1 else f"chowki{n}_mr")
        out.append(rec(M, f"{sid}:chowki-{n}", area=cn, area_regional=cmr, office_type="police chowki",
                       post="Police chowki", phone=ph(d.get("chphone" if n == 1 else f"chphone{n}")), parent=name_en or name_mr,
                       state="MH", district="Pune", office_id=f"{sid}:{n}", source=f"{API}?ps={sid}"))
    return out


def fetch(p, get):
    url = p.get("url", API)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, "ps.json", r.content)]
    try:
        rows = r.json().get("ps") or []
    except ValueError:
        return [], files, "list not json"
    recs = []
    for base in rows:
        d = {}
        x = get(f"{API}?ps={base['id']}")
        if x is not None:
            files.append(gz(M, f"ps-{base['id']}.json", x.content))
            try:
                js = x.json()
                d = js[0] if isinstance(js, list) and js and isinstance(js[0], dict) else {}
            except (ValueError, json.JSONDecodeError):
                d = {}
        recs += station(base, d)
    why = "" if recs else "no stations"
    return uniq(recs), files, why
