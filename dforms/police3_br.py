"""Bihar Police: field officers, police.bihar.gov.in/FieldOfficerHandler.ashx?action=getall&lang=en&page=1&pageSize=100 (the JSON
behind the site's "Field Officers" page; the SPA's own call uses pageSize=20, the handler gives all 76 rows in one page).
data[] {sl_no, range, designation, std_code, office_no, residence, fax, mobile, email, full_office_number, full_residence_number}:
range IG / DIG, every district SP / SSP ("SP, Aurangabad", "SSP, Patna", "SP, West Champaran, Bettiah", "SP, Bagaha"), city /
rural / traffic SPs and the rail SRPs. No officer names (posts only). The mobile is the post's CUG number.
Kept: one record per row. District rows: level district, district from the post (LGD spelling: West Champaran -> Pashchim
Champaran, East Champaran -> Purbi Champaran, Bagaha -> Pashchim Champaran, Naugachhia -> Bhagalpur, Purnea -> Purnia); range rows:
level division; rail rows: level district with office_type railway, no district. Office / residence numbers keep the STD code.
India only (police_br, same host). One queue item = the call. Record id dept:police3_br:<sl_no>-<post>."""
import json
import re

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "json api"

M = "police3_br"
URL = "https://police.bihar.gov.in/FieldOfficerHandler.ashx?action=getall&lang=en&page=1&pageSize=100"
SOURCE = "https://police.bihar.gov.in/"
DISTRICT = {
    "west champaran": "Pashchim Champaran", "bagaha": "Pashchim Champaran", "bettiah": "Pashchim Champaran",
    "east champaran": "Purbi Champaran", "motihari": "Purbi Champaran", "naugachhia": "Bhagalpur", "purnea": "Purnia",
    "patna": "Patna", "nalanda": "Nalanda", "gaya": "Gaya", "nawada": "Nawada", "aurangabad": "Aurangabad", "jehanabad": "Jehanabad",
    "arwal": "Arwal", "rohtas": "Rohtas", "bhojpur": "Bhojpur", "kaimur": "Kaimur (Bhabua)", "buxar": "Buxar",
    "muzaffarpur": "Muzaffarpur", "sitamarhi": "Sitamarhi", "vaishali": "Vaishali", "sheohar": "Sheohar", "saran": "Saran",
    "siwan": "Siwan", "gopalganj": "Gopalganj", "darbhanga": "Darbhanga", "madhubani": "Madhubani", "samastipur": "Samastipur",
    "araria": "Araria", "kishanganj": "Kishanganj", "katihar": "Katihar", "saharsa": "Saharsa", "supaul": "Supaul",
    "madhepura": "Madhepura", "bhagalpur": "Bhagalpur", "banka": "Banka", "munger": "Munger", "jamui": "Jamui",
    "lakhisarai": "Lakhisarai", "sheikhpura": "Sheikhpura", "begusarai": "Begusarai", "khagaria": "Khagaria",
}
RANGE_TOWN = {"chhapra": "Saran"}


def district_of(text):
    t = (clean(text) or "").lower()
    best = None
    for k, v in DISTRICT.items():
        m = re.search(r"\b" + k + r"\b", t)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), v)
    return best[1] if best else None


def num(std, cell):
    std = re.sub(r"\D", "", std or "")
    out = []
    for p in re.split(r"\s*[/,]\s*", clean(cell) or ""):
        d = re.sub(r"\D", "", p)
        if 5 <= len(d) <= 8 and std:
            out.append(f"{std}-{d}")
        elif len(d) >= 10:
            out.append(d)
    return out


def parse(text, url=URL, state="BR"):
    data = json.loads(text).get("data") or []
    recs = []
    for i, x in enumerate(data):
        post = clean(x.get("designation"))
        if not post:
            provenance.skip_row(x, 'skip: not post')
            continue
        rng = clean(x.get("range"))
        std = x.get("std_code")
        dist = None
        if re.search(r"\b(?:IG|DIG|ADG|AIG)\b", post) or re.search(r"control room", post, re.I):
            level, otype = ("division", "office") if not re.search(r"rail", post, re.I) else ("state", "railway")
            if re.search(r"control room", post, re.I):
                otype = "control room"
        elif re.search(r"\bSRP\b|rail", post, re.I):
            level, otype = "district", "railway"
        else:
            level = "district"
            otype = "traffic" if re.search(r"traffic", post, re.I) else "office"
            dist = district_of(post) or district_of(re.sub(r"\.", " ", rng or "")) or RANGE_TOWN.get(
                (re.search(r",\s*(\w+)", rng or "") or [None, ""])[1].lower())
        d = dict(level=level, office_type=otype, area=dist or post, post=post, range=rng,
                 phone=phones(*(([x["mobile"]] if x.get("mobile") else []) + num(std, x.get("office_no")) + num(std, x.get("residence")))),
                 office_phone=", ".join(num(std, x.get("office_no"))) or None, residence_phone=", ".join(num(std, x.get("residence"))) or None,
                 fax=", ".join(num(std, x.get("fax"))) or None, email=email(x.get("email")), std=clean(std), state=state,
                 district=dist, list_no=x.get("sl_no"), source=SOURCE, src_url=url, src_pos={"index": i, "id": x.get("sl_no")})
        recs.append(rec(M, f"{x.get('sl_no') or i}-{slug(post)[:50]}", **d))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    try:
        recs = parse(r.text, url, p.get("state", "BR"))
    except ValueError:
        return [], [gz(M, "field-officers", r.content)], "not json"
    return recs, [gz(M, "field-officers", r.content)], "" if recs else "no rows"
