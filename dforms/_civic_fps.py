"""Shared code of the fair price shop readers (dforms/civic_fps_<xx>.py): the two ePoS platforms that the state food departments use.

1. SMART-PDS (NIC React app, 17 states and UTs: AP, AR, AS, BR, CG, DL, GA, HR, JH, JK, LA, MZ, NL, SK, TR, UK, DH). Public JSON
   endpoints that the site's own report pages call without a login:
   - GET  /Epos_Spring/api/getSearchDetailsDistrict                       -> [{dist_code, dist_name_en}]
   - POST /Epos_Spring/api/fpsdevicemapping/device  (dist_code=<code>)   -> {"list": [{fps_id, del_name, del_mob, terminal_id,
     nom_1_name, nom_1_mob, nom_2_name, nom_2_mob}]}   ("FPS Dealer & Device Details"; the dealer mobile is masked: XXXXX-X9494)
   - GET  /Epos_Spring/api/getSearchDetailsBlock?dist_code=<code>         -> [{afso_code, afso_name_en}]  (supply office: block / circle)
   - GET  /Epos_Spring/api/getSearchDetailsFps?dist_code=&office_code=&month=&year= -> [{fps_id, ownername}]  ("Search" side menu)
   The device list gives the dealer of every shop of a district; the search list ties each shop to its supply office (the area).
2. AePDS (older JSP sites: KL, MP, MH, CH): FPS_Device_Mapping.jsp has a district <select name="dist_code">; the page POSTs
   dist_code to fps_device.action and shows an HTML table: Sl.No, FPS / ARD number, terminal id, dealer name, nominee I, nominee II
   (the "Dealer Mobile" column is commented out in the page source: the department does not publish it).

One queue item = one state (all districts) or one district ("dist_code" in the payload). Record ids: dept:<module>:<fps_id>.
Shops with ids that start with 123456789 are the vendor's test shops ("srinivas", "Harish Sharma") and are left out.
Name cells are cleaned (name_of / split_name): a mobile written in the name ("FPS QUMROO(Zahida Akhter)9906625865", JK and MH)
moves to the phone; labels and codes that are not names ("PACX", "PACS", "FPS", "---", a longitude "77.539566" (MP), a shop id
"130900220142") give no name; a shop id or in-charge note after the name ("... FPS ID 131300300154 IS ALSO TAGGE" (AS),
"... IC 39", "... Ic No.0781159 dealer" (AP)) and a trailing comma are cut. A 10-digit number that is not a mobile (first digit
0-5: "3090090924") or one digit ten times ("9999999999") is no phone (BR). A shop with no name but a phone is kept.
"""
import datetime
import json
import re

from dforms import _esw

POST = "FPS dealer"
TEST_ID = re.compile(r"^123456789")
MASKED = re.compile(r"[Xx*]{2,}")


MOBILE = re.compile(r"(?<![\d])(?:\+?91[\s-]?)?([6-9]\d{4}\s?\d{5})(?![\d])")
LABEL = re.compile(r"(?i)(-+|\.+|fps|pac[sx]|-?na-?|n/a|null|nil|[\d\s.,:/-]+|(?=[a-z]*\d)(?=\d*[a-z])[a-z\d]{8,})")
SHOP_NOTE = re.compile(r"(?i)\s+fps\s+(id|is)\b.*$|[\s,]+ic\b(\s*(no|shop)\b)?[\s.]*\d[\d.]*(\s+(dealer|incharge\w*))?\s*$")


def unmasked(v):
    """A phone value that the source shows in full; '' for masked (XXXXX-X9494), '-NA-' or empty values, and for 10-digit
    numbers that cannot be a mobile (first digit 0-5) or are one digit repeated (9999999999)."""
    v = _esw.clean(v)
    d = re.sub(r"\D", "", v)
    if not v or MASKED.search(v) or len(d) < 10:
        return ""
    if len(d) == 10 and (d[0] not in "6789" or len(set(d)) == 1):
        return ""
    return v


def split_name(v, numbers=None):
    """(name, mobile) from a name cell: a mobile written in the name moves out; labels and codes give no name. Other digit
    runs of 7 to 12 digits (mistyped or cut mobiles: "990623760", "94699679061") also leave the name; they go to the list
    `numbers` when one is given (the record keeps them as name_number, as written)."""
    v = SHOP_NOTE.sub("", _esw.clean(v))
    phones = [re.sub(r"\s", "", m.group(1)) for m in MOBILE.finditer(v)]
    v = MOBILE.sub(" ", v)
    other = re.findall(r"(?<![^\W_])(?<!\d\.)\d{7,12}(?![^\W_])(?!\.\d)", v) if re.search(r"[^\W\d_]", v) else []
    if numbers is not None:
        numbers += other
    if phones or other:
        v = re.sub(r"(?<![^\W_])(?<!\d\.)\d{7,12}(?![^\W_])(?!\.\d)", " ", v)
        v = re.sub(r"[\s,.:-]*\(\s*[\s,.:-]*\)", "", v)                  # "( )" and "(, )" left by the number
        v = re.sub(r"[\s,.:-]+\)", ")", v)                               # "(MUSHTAQ AHMAD )" -> "(MUSHTAQ AHMAD)"
        v = re.sub(r"[\s,.:-]+(\]|$)", r"\1", _esw.clean(re.sub(r"-\s+-", "-", v)))
    v = _esw.clean(re.sub(r"[\s,;]+$", "", v))
    if not v or LABEL.fullmatch(v):
        v = ""
    ph = ", ".join(x for x in dict.fromkeys(p for p in phones if unmasked(p)))
    return v, ph


def name_of(v):
    return split_name(v)[0]


def _json(r):
    if r is None:
        return None
    try:
        return r.json()
    except ValueError:
        try:
            return json.loads(r.content)
        except ValueError:
            return None


# ---------------------------------------------------------------- SMART-PDS

def sp_base(p):
    return p["url"].rstrip("/")


def sp_districts(get, base):
    d = _json(get(f"{base}/Epos_Spring/api/getSearchDetailsDistrict"))
    return [(str(x["dist_code"]), _esw.clean(x.get("dist_name_en"))) for x in (d or []) if x.get("dist_code")]


def sp_items(module, state, base, india_only=False, districts=None):
    """One item for the whole state, or one per district when the district list is given."""
    pay = {"reader": module, "url": base, "state": state}
    if india_only:
        pay["india_only"] = True
    if not districts:
        return [{"key": module, "payload": pay}]
    return [{"key": f"{module}-{c}", "payload": dict(pay, dist_code=c, district=n)} for c, n in districts]


def sp_offices(get, base, dist_code):
    """{fps_id: (afso_code, afso_name, ownername)} from the Search menu, and the raw answers."""
    out, raw = {}, []
    blocks = _json(get(f"{base}/Epos_Spring/api/getSearchDetailsBlock?dist_code={dist_code}")) or []
    raw.append({"blocks": blocks})
    today = datetime.date.today()
    for b in blocks:
        code = b.get("afso_code")
        if code is None:
            continue
        fps = _json(get(f"{base}/Epos_Spring/api/getSearchDetailsFps?dist_code={dist_code}&office_code={code}"
                        f"&month={today.month}&year={today.year}")) or []
        raw.append({"afso_code": code, "fps": fps})
        for f in fps:
            if f.get("fps_id"):
                out[str(f["fps_id"])] = (str(code), _esw.clean(b.get("afso_name_en")), name_of(f.get("ownername")))
    return out, raw


def sp_parse(device, offices, module, state, base, dist_code="", district=""):
    """Records from one district's device list (dict) joined with the {fps_id: office} map."""
    recs, seen = [], set()
    district = _esw.clean(device.get("dist_name_en")) or district
    src = f"{base}/FPS_Device_Mapping"
    for x in device.get("list") or []:
        fid = _esw.clean(x.get("fps_id"))
        if not fid or TEST_ID.match(fid) or fid in seen:
            continue
        seen.add(fid)
        afso_code, afso, owner = offices.get(fid, ("", "", ""))
        nums = []
        name, name_ph = split_name(x.get("del_name"), nums)
        if not name:
            name, name_ph = split_name(owner, nums)
        (n1, n1_ph), (n2, n2_ph) = split_name(x.get("nom_1_name")), split_name(x.get("nom_2_name"))
        post, phone = POST, unmasked(x.get("del_mob")) or name_ph
        if not name and n1 and not phone:            # a dealer with a phone but only a label ("PACX") stays the dealer
            name, post, phone = n1, "FPS nominee", unmasked(x.get("nom_1_mob")) or n1_ph
        if not name and not phone:
            continue
        recs.append(_esw.record(
            module, fid, dept="food_supplies", level="facility", layer="fps", area=afso or district, post=post, name=name,
            phone=phone, state=state, district=district, subdistrict=afso, block=afso, afso_code=afso_code,
            fps_id=fid, office_id=fid, terminal_id=_esw.clean(x.get("terminal_id")), dist_code=dist_code or x.get("dist_code"),
            nominee_1=n1, nominee_1_phone=unmasked(x.get("nom_1_mob")) or n1_ph, nominee_2=n2,
            nominee_2_phone=unmasked(x.get("nom_2_mob")) or n2_ph, name_number=", ".join(nums),
            source=src))
    return recs


def sp_fetch(p, get, module, state):
    base = sp_base(p)
    dists = [(str(p["dist_code"]), p.get("district", ""))] if p.get("dist_code") else sp_districts(get, base)
    if not dists:
        return [], [], "no district list"
    recs, files = [], []
    for code, dname in dists:
        r = get(f"{base}/Epos_Spring/api/fpsdevicemapping/device", method="POST", data={"dist_code": code},
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        device = _json(r)
        if not isinstance(device, dict):
            continue
        offices, raw = sp_offices(get, base, code)
        files.append(_esw.keep(module, f"device-{code}", r.content, "json"))
        files.append(_esw.keep(module, f"search-{code}", json.dumps(raw, ensure_ascii=False), "json"))
        recs += sp_parse(device, offices, module, state, base, code, dname)
    return recs, files, "" if recs else "no rows"


# ---------------------------------------------------------------- AePDS (JSP)

def jsp_districts(html):
    sel = _esw.soup(html).find("select", attrs={"name": "dist_code"})
    return [(o.get("value"), _esw.clean(o.get_text())) for o in (sel.find_all("option") if sel else []) if (o.get("value") or "").strip()]


def jsp_items(module, state, base, districts, india_only=False):
    pay = {"reader": module, "url": base, "state": state}
    if india_only:
        pay["india_only"] = True
    return [{"key": f"{module}-{c}", "payload": dict(pay, dist_code=c, district=n)} for c, n in districts]


def jsp_parse(html, module, state, base, dist_code="", district=""):
    soup = _esw.soup(html)
    u = soup.find("u")
    district = _esw.clean(u.get_text()) if u and _esw.clean(u.get_text()) else district
    table = soup.find("table", id="Report") or soup.find("table")
    recs, seen = [], set()
    if table is None:
        return recs
    src = f"{base}/FPS_Device_Mapping.jsp"
    for tr in table.find_all("tr"):
        tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(tds) < 4 or not re.fullmatch(r"\d{4,15}", tds[1]):
            continue
        fid, term, rest = tds[1], tds[2], tds[3:]
        if TEST_ID.match(fid) or fid in seen:
            continue
        seen.add(fid)
        names, phone_after, nums = [], {}, []
        for c in rest:                       # a mobile column may follow a name when a state shows it
            if re.fullmatch(r"[\dXx*+\- ]{8,}", c) and re.search(r"\d", c):
                if names:
                    phone_after.setdefault(len(names) - 1, unmasked(c))
            else:
                n, ph = split_name(c, nums if not names else None)   # a mobile in the name cell (MH): that person's phone
                names.append(n)
                if ph:
                    phone_after.setdefault(len(names) - 1, ph)
        names += [""] * 3
        dealer, n1, n2 = names[0], names[1], names[2]
        dealer_phone = phone_after.get(0, "")
        post = POST
        if not dealer and n1 and not dealer_phone:
            dealer, post, dealer_phone = n1, "FPS nominee", phone_after.get(1, "")
        if not dealer and not dealer_phone:
            continue
        recs.append(_esw.record(
            module, fid, dept="food_supplies", level="facility", layer="fps", area=district, post=post, name=dealer,
            phone=dealer_phone, state=state, district=district, fps_id=fid, office_id=fid, terminal_id=term,
            dist_code=dist_code, nominee_1=n1, nominee_2=n2, name_number=", ".join(nums), source=src))
    return recs


def jsp_fetch(p, get, module, state):
    base = p["url"].rstrip("/")
    if p.get("dist_code"):
        dists = [(str(p["dist_code"]), p.get("district", ""))]
    else:
        page = get(f"{base}/FPS_Device_Mapping.jsp")
        dists = jsp_districts(page.text) if page is not None else []
    if not dists:
        return [], [], "no district list"
    recs, files = [], []
    for code, dname in dists:
        r = get(f"{base}/fps_device.action", method="POST", data={"dist_code": code},
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        if r is None:
            continue
        files.append(_esw.keep(module, f"device-{code}", r.content))
        recs += jsp_parse(r.text, module, state, base, code, dname)
    return recs, files, "" if recs else "no rows"
