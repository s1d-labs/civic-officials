"""Odisha: officers of every Collectorate, Sub-Collector office, Tahasil office and Panchayat Samiti (block) office, with mobiles, from
the RTI Central Monitoring Mechanism of the Government of Odisha (rtiodisha.gov.in, run by the I&PR Department). Answers only from India
(this box in Germany times out).

Each district page /Districts/<n> (n = 1..30, about 800 KB) lists every public authority of the district in four tabs (District,
Sub-divisional, Block, Panchayat): "<office name> ( <RTI code> )", a link /pa/<base64 "OTH/<dept>/<office>/<district>"> and the office
address. Each office's proactive disclosure manual answers one POST per section:
  /Pages/getDisclouser/department_id:<dept>/office_id:<office>/district_id:<n>/section_id:<s>/language:en
Section 10 = "Directory of Officers & Employees" (Sl. No, Name, Designation, Mobile No), section 7 = PIOs Details (APIO, PIO and
1st Appellate Authority tables: Name, Designation, Mobile No., E-Mail ID, Address). Both end with "last updated on dd/mm/yyyy".
The reader asks section 10 and keeps the officer posts (Tahasildar, Additional Tahasildar, Revenue Inspector, BDO, Collector, ADM,
Sub-Collector, extension officers ...; clerks, peons and drivers are left out); if that gives no officer, it asks section 7.

One queue item per district: 1 GET + about 25-40 POSTs (Collectorate, Zilla Parishad / DRDA, each Sub-Collector office, each Tahasil
office, each Panchayat Samiti office). Area = the office's place as the site spells it ("Baliapal", "Balasore Sadar").
Record ids: dept:sub_od_rti:OD-<RTI code>:<slug of post>[:n].
"""
import base64
import re

from dforms import _esw

MODULE = "sub_od_rti"
BASE = "https://rtiodisha.gov.in"
SECTION = BASE + "/Pages/getDisclouser/department_id:{dept}/office_id:{office}/district_id:{dist}/section_id:{sec}/language:en"
# rtiodisha.gov.in district id -> LGD district (code, name as in lgd.districts)
DISTRICTS = {1: ("344", "Anugola"), 2: ("346", "Baleshwar"), 3: ("347", "Baragada"), 4: ("348", "Bhadrak"), 5: ("345", "Balangir"),
             6: ("349", "Boudh"), 7: ("350", "Kataka"), 8: ("351", "Debagada"), 9: ("352", "Dhenkanal"), 10: ("353", "Gajapati"),
             11: ("354", "Ganjam"), 12: ("355", "Jagatsinghapur"), 13: ("356", "Jajpur"), 14: ("357", "Jharsuguda"),
             15: ("358", "Kalahandi"), 16: ("359", "Kandhamala"), 17: ("360", "Kendrapada"), 18: ("361", "Kendujhar"),
             19: ("362", "Khordha"), 20: ("363", "Koraput"), 21: ("364", "Malkangiri"), 22: ("365", "Mayurbhanj"),
             23: ("366", "Nabarangpur"), 24: ("367", "Nayagada"), 25: ("368", "Nuapada"), 26: ("369", "Puri"), 27: ("370", "Rayagada"),
             28: ("371", "Sambalpur"), 29: ("372", "Subarnapur"), 30: ("373", "Sundaragada")}
# (office name pattern, tab, dept, level, prefix to strip for the area)
KINDS = [
    (re.compile(r"^\s*collectorate\b", re.I), "district", "administration", "district", None),
    (re.compile(r"zilla\s+parishad|district\s+rural\s+development\s+agency|\bDRDA\b", re.I), "district", "rural_development", "district", None),
    (re.compile(r"sub[\s-]*collector", re.I), "subdivisoonal", "administration", "subdivision",
     re.compile(r"^(office\s+of\s+the\s+)?sub[\s-]*collector('?s)?\s*(office)?\s*[,:-]?\s*", re.I)),
    (re.compile(r"^\s*(office\s+of\s+the\s+)?tahas[ie]l", re.I), "block", "revenue", "subdistrict",
     re.compile(r"^(office\s+of\s+the\s+)?tahas[ie]l(dar)?('?s)?\s*(office)?\s*[,:-]?\s*", re.I)),
    (re.compile(r"panchayat\s+samiti|block\s+(development\s+)?office|\bB\.?\s?D\.?\s?O\b", re.I), "block", "rural_development", "block",
     re.compile(r"^(office\s+of\s+the\s+)?(panchayat\s+samiti|block\s+(development\s+)?(office(r)?)?|B\.?\s?D\.?\s?O\.?)\s*(office)?\s*"
                r"[,:-]?\s*", re.I)),
]
OFFICER = re.compile(r"officer|collector|magistrate|tahas|\bB\.?\s?D\.?\s?O\b|\bA\.?\s?B\.?\s?D\.?\s?O\b|\bR\.?\s?I\b|inspector|supervisor|"
                     r"engineer|\bJ\.?E\b|\bA\.?E\.?E\b|commissioner|secretary|superintendent|\bP\.?D\b|\bC\.?D\.?O\b|\bA\.?D\.?M\b|"
                     r"project director|\bS\.?D\.?M\b|\bP\.?E\.?O\b|\bS\.?E\.?O\b|\bW\.?E\.?O\b|\bG\.?P\.?E\.?O\b|\bP\.?I\.?O\b", re.I)
CLERICAL = re.compile(r"peon|driver|attendant|clerk|typist|steno|watch|sweeper|chowkidar|chaukidar|daftry|dafadar|data\s*entry|computer|"
                      r"\bamin\b|orderly|messenger|night guard|\bD\.?E\.?O\b|cook|mali|gardener|\bM\.?T\.?S\b|helper|assistant(?!\s+(block|"
                      r"engineer|executive|director|collector|commissioner|secretary|tahas|sub|district|public information|project))", re.I)
UPDATED = re.compile(r"last\s+updated\s+on\s*(\d{1,2})/(\d{1,2})/(\d{4})", re.I)


def items(get=None):
    return [{"key": f"sub_od_rti_{n}", "payload": {"reader": MODULE, "url": f"{BASE}/Districts/{n}", "district_id": n, "district": name,
                                                    "district_code": code, "state": "OD", "india_only": True}}
            for n, (code, name) in DISTRICTS.items()]


def area_of(name, strip, district=""):
    """'Tahasil Office, Khaira, Soro, Balasore' -> 'Khaira'; 'Panchayat Samiti Office, Balasore Sadar, Balasore' -> 'Balasore Sadar'."""
    s = _esw.clean(re.sub(r"\(\s*\d+\s*\)\s*$", "", name))
    if strip:
        s = strip.sub("", s)
    parts = [p.strip(" .,-") for p in re.split(r",", s) if p.strip(" .,-")]
    a = parts[0] if parts else s
    a = re.sub(r"(?i)\s*(tahas[ie]l|block|panchayat samiti|sub[\s-]*division)\s*$", "", a).strip(" .,-")
    return a or district


def offices(html):
    """[{name, code, dept_id, office_id, dist_id, url, address, tab}] for the offices of one district page."""
    soup = _esw.soup(html)
    out = []
    for tab in ("district", "subdivisoonal", "block"):
        div = soup.find(id=tab)
        if div is None:
            continue
        for li in div.find_all("li"):
            a = li.find("a", href=re.compile(r"/pa/"))
            if a is None:
                continue
            href = a["href"].strip()
            try:
                kind, dept, office, dist = base64.b64decode(href.split("/pa/")[1] + "==").decode().split("/")[:4]
            except (ValueError, UnicodeDecodeError):
                continue
            label = _esw.clean(a.get_text(" "))
            m = re.search(r"\(\s*(\d+)\s*\)\s*$", label)
            p = li.find("p")
            out.append({"name": _esw.clean(re.sub(r"\(\s*\d+\s*\)\s*$", "", label)), "code": m.group(1) if m else office,
                        "kind": kind, "dept_id": dept, "office_id": office, "dist_id": dist, "url": href, "tab": tab,
                        "address": _esw.clean(p.get_text(" ")) if p else ""})
    return out


NOT_OFFICE = re.compile(r"college|maha[bv]idyalaya|vidyalaya|school|hospital|\bitc\b|\biti\b", re.I)


def wanted(offs):
    """The offices this reader reads, each with its (dept, level, area strip pattern)."""
    out, seen = [], set()
    for o in offs:
        if NOT_OFFICE.search(o["name"]):
            continue
        for pat, tab, dept, level, strip in KINDS:
            if o["tab"] == tab and pat.search(o["name"]) and o["office_id"] not in seen:
                seen.add(o["office_id"])
                out.append({**o, "dept": dept, "level": level, "strip": strip})
                break
    return out


def staff(html):
    """(rows [{name, post, phone, email, role}], last_updated ISO date or '') from one disclosure section answer."""
    soup = _esw.soup(html)
    rows = []
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if not g:
            continue
        head = [h.lower() for h in g[0]]
        col = {}
        for i, h in enumerate(head):
            if "name" in h and "name" not in col:
                col["name"] = i
            elif "designation" in h:
                col["post"] = i
            elif "mobile" in h or "phone" in h:
                col["phone"] = i
            elif "mail" in h:
                col["email"] = i
        if "name" not in col or "post" not in col:
            continue
        prev = t.find_previous(string=re.compile(r"Public Information Officer|Appellate Authority", re.I))
        role = _esw.clean(prev) if prev else ""
        for r in g[1:]:
            r = r + [""] * (len(head) - len(r))
            name = _esw.clean(r[col["name"]])
            if not name or name.lower() == "name":
                continue
            rows.append({"name": name, "post": _esw.clean(r[col["post"]]), "phone": _esw.phones(r[col["phone"]]) if "phone" in col else "",
                         "email": _esw.emails(r[col["email"]]) if "email" in col else "", "role": role})
    m = UPDATED.search(soup.get_text(" "))
    upd = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else ""
    return rows, upd


def is_officer(post):
    return bool(OFFICER.search(post or "")) and not CLERICAL.search(post or "")


def build(o, rows, upd, district, seen):
    recs = []
    area = district if o["level"] == "district" else area_of(o["name"], o["strip"], district)
    done = set()
    for r in rows:
        if not r["role"] and not is_officer(r["post"]):
            continue
        k = (r["name"].lower(), r["post"].lower())
        if k in done:
            continue
        done.add(k)
        base = f"OD-{o['code']}:{_esw.slug(r['post']) or _esw.slug(r['name'])}"
        key, i = base, 2
        while key in seen:
            key, i = f"{base}:{i}", i + 1
        seen.add(key)
        rec = _esw.record(MODULE, key, dept=o["dept"], level=o["level"], area=area, post=r["post"], name=r["name"], phone=r["phone"],
                          email=r["email"], address=o["address"], district=district, state="OD", office_id=f"OD-RTI-{o['code']}",
                          office=o["name"], rti_role=r["role"], source=o["url"], last_updated=upd)
        if rec[1].get("name") and (rec[1].get("phone") or rec[1].get("email") or rec[1].get("post")):
            recs.append(rec)
    return recs


def fetch(p, get):
    url = p.get("url") or f"{BASE}/Districts/{p['district_id']}"
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"district-{p.get('district_id')}", r.content)]
    district = p.get("district") or DISTRICTS.get(int(p.get("district_id", 0)), ("", ""))[1]
    recs, seen, missing = [], set(), 0
    for o in wanted(offices(r.text)):
        got = []
        for sec in (10, 7):
            a = get(SECTION.format(dept=o["dept_id"], office=o["office_id"], dist=o["dist_id"], sec=sec), method="POST", data={})
            if a is None:
                continue
            files.append(_esw.keep(MODULE, f"office-{o['office_id']}-s{sec}", a.content))
            rows, upd = staff(a.text)
            if sec == 7:
                rows = [dict(x, role=x["role"] or "PIO") for x in rows]
            got = build(o, rows, upd, district, seen)
            if got:
                break
        if not got:
            missing += 1
        recs += got
    return recs, files, "" if recs else "no rows"
