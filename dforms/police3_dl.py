"""Delhi Police telephone directory: delhipolice.gov.in/telephonedirectory (ASP.NET WebForms; no login, no captcha). The page
has one select "District/Unit" (60 values: the 15 police districts, Traffic, Cyber Cell, Police Control Room, SPUWAC, Special
Cell, DAP battalions, Helpline ...). Choosing one posts the form back (__doPostBack on ddldistrict, the page's own view state)
and the answer lists every row of that unit in one table (grddata): S.No. | Office/Police Station | Telephone No. |
Mobile No. | Fax No. | District/Unit | Email ID. No officer names; the mobile is the post's CUG. Answered from Mumbai and from
the GitHub runners (archive vantage pool, 2026-11-07).

Rows (district pages):
- "SHO/Karol Bagh", "SHO Nabi Karim", "PS ANAND PARBAT" -> level police_station, post SHO, area = the station;
- "L&O/Patel Nagar-Central", "Inv./Ranjeet Nagar-Central", "INSPR L&O Anand Parbhat-Central" -> level police_station, post
  Inspector (Law & Order) / Inspector (Investigation), area = the station;
- "ACP/Karol Bagh" -> level subdivision (Delhi's ACP sub-divisions), area Karol Bagh; "ACP/HQ, PG CELL & MACT" -> unit;
- "DCP/South East", "Addl. DCP-I" -> level district, post as written;
- "Central District, Daryaganj" (the DCP office) -> level district; the post from the e-mail (dcp.* -> DCP, adcp1.* ->
  Addl. DCP-I), else "District office";
- anything else (RI, cells, PG cell, ...) -> level district, office_type unit.
Units that are not police districts (Traffic, Cyber Cell, PCR, SPUWAC, Special Cell, battalions ...) -> level state with
office_type traffic / cyber / control_room / women / helpline / unit; their stations ("Traffic Inspector X", "Cyber PS X")
keep the area as published.
District: police district -> LGD district where the names are the same (Central, East, New Delhi, North, North East, North
West, Outer North, South, South East, South West, West); Dwarka, Rohini, Outer, Shahdara, IGI Airport, Metro and Railways are
police districts without an LGD district of that name: kept as published (police_district always set).
items(get) reads the select. One queue item = one unit. Record id dept:police3_dl:<unit slug>:<row slug>."""
import re

from bs4 import BeautifulSoup

import provenance
from dforms._police import clean, email, gz, phones, rec, slug, uniq
from forms.aspnet import hidden, options

METHOD = "html table (ASP.NET postback of the page's own District/Unit select)"     # source trail (provenance.py)

M = "police3_dl"
URL = "https://delhipolice.gov.in/telephonedirectory"
SELECT = "ctl00$MainContent$ddldistrict"

LGD = {"CENTRAL": "Central", "EAST": "East", "NEW DELHI": "New Delhi", "NORTH": "North", "NORTH-EAST": "North East",
       "NORTH EAST": "North East", "NORTH-WEST": "North West", "NORTH WEST": "North West", "OUTER NORTH": "Outer North",
       "SOUTH": "South", "SOUTH-EAST": "South East", "SOUTH EAST": "South East", "SOUTH-WEST": "South West",
       "SOUTH WEST": "South West", "WEST": "West"}
POLICE_DISTRICTS = set(LGD) | {"DWARKA", "ROHINI", "OUTER", "SHAHDARA", "IGI AIRPORT", "METRO", "RAILWAYS"}
UNIT_TYPE = [(r"TRAFFIC", "traffic"), (r"CYBER|IFSO", "cyber"), (r"CONTROL ROOM|OPERATIONS & COMM", "control_room"),
             (r"WOMEN|SPUWAC", "women"), (r"HELPLINE", "helpline")]
SHO = re.compile(r"^(?:SHO|PS|P\.S\.)\s*[/.:\-]?\s*(.+)$", re.I)
INSP = re.compile(r"^(?:INSPR\.?\s+)?(L\s*&\s*O|Inv\.?|ATO|Inspr?\.?\s*Inv\.?)\s*[/.:\-]?\s*(.+?)(?:\s*-\s*[A-Za-z .]+)?$", re.I)
ACP = re.compile(r"^ACP\s*[/.:\-]?\s*(.+)$", re.I)
ACP_UNIT = re.compile(r"\bHQ\b|PG CELL|MACT|CELL|CRIME|OPS|LINES|SECURITY|TRAFFIC|CAW|SJPU|AATS|SPECIAL STAFF|NARCOTIC", re.I)


def unit_name(u):
    """'CENTRAL DISTRICT' -> 'CENTRAL'; 'OUTER NORTH DISTT' -> 'OUTER NORTH'; 'NORTH-WEST DISTRICT' -> 'NORTH-WEST'."""
    return re.sub(r"\s+(DISTRICT|DISTT\.?)$", "", clean(u).upper()).strip()


def is_district(u):
    return unit_name(u) in POLICE_DISTRICTS


def district_of(u):
    n = unit_name(u)
    return LGD.get(n) or n.title().replace("Igi", "IGI")


def unit_type(u):
    for pat, t in UNIT_TYPE:
        if re.search(pat, u, re.I):
            return t
    return "unit"


def items(get):
    r = get(URL)
    if r is None:
        return []
    out = []
    for value, label in options(r.text, "ddldistrict"):
        out.append({"key": f"{M}:{slug(label)}", "payload": {"reader": M, "url": URL, "state": "DL", "unit": value}})
    return out


def rows(html):
    soup = BeautifulSoup(html, "lxml")
    t = soup.find("table", id=re.compile("grddata", re.I)) or soup.find("table")
    if t is None:
        return []
    out = []
    for i, tr in enumerate(t.find_all("tr")):
        c = [clean(td.get_text(" ", strip=True)) or "" for td in tr.find_all("td")]
        if len(c) < 7 or not re.fullmatch(r"\d+", c[0]):
            provenance.skip_row(tr, 'skip: len(c) < 7 or not re.fullmatch(r"\\d+", c[0])')
            continue
        out.append({"row": i, "sno": c[0], "office": c[1], "tel": c[2], "mobile": c[3], "fax": c[4], "unit": c[5],
                    "email": c[6]})
    return out


def std(tel):
    """Delhi landlines as published: '91-11- 25873401' / '1125751048' -> '011-25873401' / '011-25751048' (STD code 011)."""
    t = re.sub(r"(?<![\d])(?:\+?91[\s-]*)?11[\s-]+(?=\d{8}\b)", "011-", tel or "")
    return re.sub(r"(?<![\d-])11(\d{8})(?!\d)", r"011-\1", t)


def station_area(s):
    """'Ranjeet Nagar-Central' -> 'Ranjeet Nagar'; 'Karol Bagh' -> 'Karol Bagh'."""
    s = re.sub(r"\s*-\s*(Central|East|West|North|South|New Delhi|Outer|Shahdara|Dwarka|Rohini|North[- ]?East|North[- ]?West|"
               r"South[- ]?East|South[- ]?West|Outer North|Metro|IGI|Railways?)\s*$", "", clean(s) or "", flags=re.I)
    s = re.sub(r"^(?:PS|P\.S\.?)\s*[/.:\-]?\s*", "", s.strip(" /-."), flags=re.I)
    return s.strip(" /-.")


def classify(office, unit):
    """(level, post, area, office_type) of one row."""
    o = clean(office) or ""
    dist = is_district(unit)
    m = INSP.match(o)
    if m and not o.upper().startswith("SHO"):
        kind = "Inspector (Law & Order)" if re.match(r"L\s*&\s*O|ATO", m.group(1), re.I) else "Inspector (Investigation)"
        return "police_station", kind, station_area(m.group(2)), "police station"
    m = SHO.match(o)
    if m:
        return "police_station", "SHO", station_area(m.group(1)), "police station"
    m = ACP.match(o)
    if m and dist:
        area = station_area(m.group(1))
        if ACP_UNIT.search(area):
            return "district", o, district_of(unit), "unit"
        return "subdivision", "ACP", area, "subdivision"
    if dist and re.match(r"(?:Addl\.?\s*|Additional\s+)?D\.?C\.?P\b", o, re.I):
        return "district", o, district_of(unit), "office"
    if dist and re.search(r"\bDistrict\b", o, re.I) and "," in o:
        return "district", None, district_of(unit), "office"
    if dist:
        return "district", o, district_of(unit), "unit"
    return "state", o, o, unit_type(unit)


def dcp_post(mail):
    m = re.match(r"(addl?\.?dcp|adcp|dcp)[\-.]?(\d*)", mail or "", re.I)
    if not m:
        return None
    base = "DCP" if m.group(1).lower() == "dcp" else "Addl. DCP"
    return base + (f"-{['', 'I', 'II', 'III', 'IV'][int(m.group(2))]}" if m.group(2) and int(m.group(2)) < 5 else "")


def parse(html, unit, url=URL, src=None):
    recs = []
    u = slug(unit_name(unit))
    for r in rows(html):
        level, post, area, otype = classify(r["office"], r["unit"] or unit)
        mails = [e for e in (email(x) for x in re.split(r"[,;\s]+", r["email"].replace("[at]", "@").replace("[dot]", "."))) if e]
        if level == "district" and post is None:
            post = dcp_post(mails[0] if mails else "") or "District office"
        tel = std(r["tel"])
        ph = phones(r["mobile"], tel)
        if not ph and not mails:
            provenance.skip_row(r, 'skip: not ph and not mails')
            continue
        fields = dict(level=level, office_type=otype, post=post, area=area, office=r["office"], phone=ph,
                      mobile=phones(r["mobile"]), telephone=r["tel"] or None, telephone_std=tel if tel != r["tel"] else None, fax=r["fax"] if r["fax"].strip("- ") else None,
                      email=", ".join(mails) or None, state="DL", police_district=unit_name(r["unit"] or unit).title(),
                      unit=r["unit"] or unit, list_no=r["sno"], source=url, src_pos={"table": 0, "row": r["row"]},
                      **(src or {}))
        if is_district(r["unit"] or unit):
            fields["district"] = district_of(r["unit"] or unit)
        key = f"{u}:{slug(post)}-{slug(area)}" if level in ("police_station", "subdivision") else \
            f"{u}:{slug(post)}" if (level, otype) == ("district", "office") else f"{u}:{slug(r['office'])}"
        recs.append(rec(M, key, **fields))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url") or URL
    unit = p["unit"]
    r = get(url)
    if r is None:
        return [], [], "no answer (form page)"
    data = hidden(r.text)
    data.update({"__EVENTTARGET": SELECT, "__EVENTARGUMENT": "", SELECT: unit, "ctl00$MainContent$ddlrecord": "25",
                 "ctl00$MainContent$txtsearch": ""})
    r2 = get(url, method="POST", data=data)
    if r2 is None:
        return [], [gz(M, slug(unit) + "-form", r.content)], "no answer (postback)"
    recs = parse(r2.text, unit, url, provenance.at(r2, url))
    return recs, [gz(M, slug(unit), r2.content)], "" if recs else "no rows"
