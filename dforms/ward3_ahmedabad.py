"""Amdavad Municipal Corporation: "AMC Contact Directory" (21 pages, created 2025-07-05), the PDF that the Ahmedabad district site
publishes (ahmedabad.gujarat.gov.in/assets/downloads/AMC_Contact_Directory_.pdf; the corporation's own host ahmedabadcity.gov.in
did not answer from dev-vps-3 on 2026-11-13). Live sample from dev-vps-3 (Mumbai) 2026-11-13; the archive holds the district
site only from Indian vantages (IN, IN-proxy).
Columns: SR. | OFFICERS NAME | DESIGNATION | OFFICE PHONE NO | MOBILE NO. | EMAIL ADDRESS; a block starts at a line with a serial
number, the name and the designation wrap onto the lines below it, the email wraps in its own column, and the lines below a
deputy commissioner list his portfolio (kept in "portfolio"). Centred lines without a serial are section titles ("Assistant
Municipal Commissioner", "Zonal Assistant Municipal Commissioner (Senior)/H.O.D.", ...): kept in "section".
Levels: an assistant municipal commissioner of named wards ("Assistant Municipal Commissioner W Z - 4 Ranip & Nava Vadaj Ward")
-> level "ward" (ward_names = the ward names as written; AMC wards are known by name, so wards = [] and wards_note says so);
a post that names a zone (Dy. MC- WEST ZONE, Addl. MOH West Zone, Collector East Zone, ...) -> level "zone"; the rest -> "body".
Ids: dept:ward3_ahmedabad:<level>:<email local part or mobile or page-serial>.
"""
import re

import provenance
from dforms import _esw, _ward

METHOD = "pdf text (pypdf layout), blocks by serial number and column position"

MODULE = "ward3_ahmedabad"
BODY, LGD, STATE, DISTRICT = "Amdavad Municipal Corporation", "251096", "GJ", "Ahmedabad"
URL = "https://ahmedabad.gujarat.gov.in/assets/downloads/AMC_Contact_Directory_.pdf"
START = re.compile(r"^(\s*)(\d{1,3})\s{2,}(\S.*)$")
NUM = re.compile(r"^(?:[\d][\d ,/()-]{6,}|[-–])$")       # a phone, or "-" for none
POST_WORD = re.compile(r"\s(?=(?:Assistant|Asst\.?|Deputy|Dy\.|I/[cC]\.?|HOD|H\.O\.D|GM|Executive|Establishment|Municipal|Addl\.?|"
                       r"Additional|Chief|City|Medical|Zonal|Collector|Superintendent|Director|Secretary|Town|Fire|Engineer|"
                       r"Officer|Manager|Health|Estate|Tax|Sr\.|Jr\.|Joint|Project|Principal|Dean|Registrar|Accounts?|Audit|"
                       r"Garden|Legal|Security|Head|In[- ]?charge|CEO|CFO|Admin|North|South|East|West|Central)\b)")
ZONES = {"WZ": "West Zone", "SZ": "South Zone", "EZ": "East Zone", "NZ": "North Zone", "CZ": "Central Zone",
         "NWZ": "North West Zone", "SWZ": "South West Zone"}


def items(get=None):
    return [{"key": f"{MODULE}-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True,
                                                       "route": "proxy"}}]


def runs(line):
    return [(m.start(), m.group(0).replace("\u00a0", " ")) for m in re.finditer(r"\S+(?:\s\S+)*", line)]


def blocks(pages):
    """[{serial, page, line, raw, start: [(x, text)], cont: [(line_no, [(x, text)])], section}] in page order."""
    out, section = [], ""
    for pn, pg in enumerate(pages, 1):
        cur = None
        for ln, raw in enumerate(pg.splitlines(), 1):
            m = START.match(raw)
            if m and not NUM.match(m.group(3).split("  ")[0]):
                cur = {"serial": m.group(2), "page": pn, "line": ln, "raw": raw, "name_x": m.start(3),
                       "start": runs(raw[m.start(3):]), "cont": [], "section": section}
                cur["start"] = [(x + cur["name_x"], t) for x, t in cur["start"]]
                out.append(cur)
                continue
            rs = runs(raw)
            if not rs:
                continue
            if cur is None or (len(rs) == 1 and rs[0][1].isupper() and len(rs[0][1]) > 25):
                if len(rs) == 1 and "@" not in rs[0][1]:
                    section = _esw.clean(rs[0][1])
                    if cur is not None:
                        cur = None
                continue
            cur["cont"].append((ln, rs))
    return out


def split_start(start):
    """(name, designation, numbers, email head, email x) of a block's first line."""
    email_x, email, nums, mid = None, "", [], []
    for x, t in start:
        if "@" in t:
            email_x, email = x, t
        elif NUM.match(t) and email_x is None:
            nums.append(t)
        elif email_x is None:
            mid.append((x, t))
    if not mid:
        return "", "", nums, email, email_x
    if len(mid) >= 2:
        return mid[0][1], " ".join(t for _, t in mid[1:]), nums, email, email_x
    t = mid[0][1]
    parts = POST_WORD.split(t, maxsplit=1)
    words = t.split()
    if len(parts) == 2 and len(parts[0].split()) >= 2:
        return parts[0], parts[1], nums, email, email_x
    return " ".join(words[:3]), " ".join(words[3:]), nums, email, email_x


def person(b):
    name, post, nums, email, email_x = split_start(b["start"])
    desig_x = min([x for _, rs in b["cont"] for x, t in rs if x > b["name_x"] + 6 and (email_x is None or x < email_x - 2)
                   and not NUM.match(t)] or [10 ** 6])
    post_lines, portfolio, name_more = [post] if post else [], [], []
    in_post = True
    for _, rs in b["cont"]:
        for x, t in rs:
            if email_x is not None and x >= email_x - 3 and not NUM.match(t):
                email += t.strip()
            elif NUM.match(t):
                nums.append(t)
            elif x < desig_x - 2:
                name_more.append(t)
            elif x > desig_x + 6:
                continue
            elif in_post and continues(post_lines, t):
                post_lines.append(t)
            else:
                in_post = False
                portfolio.append(t)
    full_name = _esw.clean(" ".join([name] + name_more))
    post_lines = [t for t in post_lines if t not in ("-", "–")]
    m = re.search(r"\s(\d{8,10})$", post_lines[0]) if post_lines else None
    if m:                       # "Addl. MOH West Zone 27553661": the office phone ran into the designation
        nums.insert(0, m.group(1))
        post_lines[0] = post_lines[0][:m.start()]
    return full_name, _esw.clean(" ".join(post_lines)), [n for n in nums if n not in ("-", "–")], email.rstrip(","), portfolio


CONT = re.compile(r"^(Commissioner|Officer|Engineer|ZONE|Zone|Ward|WARD|[,&(\-\d]|[a-z])|\bZ\s*[-–]|(?i:\bzone\b|\bward\b)|^Dy\.?\s*MC")


def continues(post_lines, t):
    """True when line t still belongs to the designation (not to the portfolio list below it)."""
    last = " ".join(post_lines)
    if re.search(r"\bZ\s*[-–]", last) and not re.search(r"(?i)\bward\s*$", last):
        return True                 # "... W Z - 4" / "Ranip & Nava Vadaj" / "Ward": the ward names run until "Ward"
    if last and re.search(r"(?i)\bward\s*$", last):
        return bool(re.match(r"(?i)(I/C\s+)?Assistant\s+Municipal|Commissioner", t))      # a second ward charge
    return bool(CONT.search(t)) or bool(re.search(r"(?i)(assistant|deputy|dy\.|addl\.?|municipal|health|city)\s*$", last))


def zone_of(post):
    p = post.upper()
    m = re.search(r"\b(N\s*W|S\s*W|[NSEWC])\s*Z\s*[-–]\s*(\d+)", p)
    if m:
        z = ZONES.get(m.group(1).replace(" ", "") + "Z", m.group(1))
        return z, f"{z} - {m.group(2)}"
    m = re.search(r"\b(NWZ|SWZ|EZ|WZ|NZ|SZ|CZ)\b", p)
    if m:
        return ZONES[m.group(1)], ZONES[m.group(1)]
    m = re.search(r"(NORTH\s*WEST|SOUTH\s*WEST|NORTH|SOUTH|EAST|WEST|CENTRAL)\s*ZONE", p)
    if m and not re.search(r"ALL\s*ZONE", p):
        z = m.group(1).title().replace("  ", " ") + " Zone"
        return z, z
    return None, None


def parse(pages, p):
    seen, recs = set(), []
    for b in blocks(pages):
        name, post, nums, email, portfolio = person(b)
        if not (name or post):
            continue
        zone, sub = zone_of(post)
        wards = re.findall(r"([A-Za-z][A-Za-z .&,]+?)\s+Ward\b", post)
        ward_names = None
        level = "body"
        if zone and re.search(r"(?i)assistant\s+municipal\s+commissioner", post) and re.search(r"(?i)\bward\b", post):
            level = "ward"
            names = re.findall(r"(?i)z\s*[-–]\s*\d+\s*,?\s*([^,]*?)\s*ward", post)
            ward_names = "; ".join(_esw.clean(n).strip(" ,") for n in names if n.strip(" ,")) or None
        elif zone:
            level = "zone"
        phones = ", ".join(_esw.clean(n) for n in nums)
        mob = re.search(r"[6-9]\d{9}", phones.replace(" ", ""))
        key = (email.split("@")[0] if "@" in email else "") or (mob.group(0) if mob else f"{b['page']}-{b['serial']}")
        extra = {}
        if level == "ward":
            extra.update(ward_names=ward_names, wards_note="the source names the wards (AMC wards have names), not their numbers")
        recs.append(_ward.record(MODULE, f"{level}:{_esw.slug(key)}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level=level, area=(sub if level == "ward" and sub else zone) or BODY, zone=zone, post=post or "-",
                                 name=name, phone=phones, email=email, section=b["section"] or None,
                                 portfolio="; ".join(portfolio) or None, source=p["url"],
                                 src_pos=provenance.line_pos(b["page"], b["line"], b["raw"]), **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "amc-contact-directory", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p)
    return recs, files, "" if recs else "no officer blocks"
