"""District emergency and helpline numbers on S3WaaS district portals: the "Helpline" page (https://<host>/helpline/, menu
Directory -> Helpline). The district writes one or more tables of (service / office, number), sometimes with a heading above each
table ("Police Stations", "Fire Stations"). Many rows are national short codes (100, 101, 108, 1098, 181, 1077); the rows that this
layer keeps are the district's own numbers: police control room, police stations, women and child helpline units, fire stations,
district control room / DEOC, hospitals and ambulances, with the local landline or mobile.

Rows: a row is kept when its label (or the heading above its table) names a police, fire, disaster, women / child or health
service, and it carries at least one number of 6 or more digits (a short code alone is the same in every district; it goes to
short_codes on the rows that have a local number too). Toll-free 1800 numbers of state schemes (MGNREGA, PMAY ...) name no
emergency service and are left out.
dept: police (control room, police station, traffic, cyber, women police station), fire, disaster (district control room,
emergency operation centre, flood control, collectorate control room), women_child (women helpline, one stop centre, child
helpline, child protection), health (hospital, ambulance, blood bank, health control room).
level: police_station / facility (a named station or hospital), subdivision (SDPO, sub-divisional control room), district.
Officers: a label or cell that names a person ("Shri ...", "Smt ...", "Dr ...") goes to name; posts such as SP, DSP, SDPO,
SHO / OC, CMO, DDMO go to post when the row writes them. Most rows name nobody.

Pages without a table (about half, mostly short-code lists in paragraphs) give no rows. Not India-only.
Seed: seeds/dept_emerg_help_s3waas.json, the helpline pages of the district portals in sites.csv that archive.s1d.me saved and
that give at least one row (scan of 2026-11-11): 111 pages of 338 saved (651 district portals), 548 rows on the saved copies:
police 174, disaster 150, health 110, fire 80, women_child 34; 35 rows name a person, 62 give a post.
Record ids: dept:emerg_help_s3waas:<host>:<slug of heading and label>.
"""
import re
from urllib.parse import urlparse

from dforms import _emerg, _esw
from dforms.police_s3waas import last_updated

MODULE = "emerg_help_s3waas"

DEPTS = [  # (dept, pattern) in order: the first match wins
    ("women_child", r"women|woman|mahila|\bchild|childline|one stop|sakhi|\bOSC\b|\bDCPU\b|\bCWC\b|1098|\b181\b|1091|anti.?human"),
    ("fire", r"\bfire"),
    ("disaster", r"disaster|\bDEOC\b|\bEOC\b|emergency operation|\bDDMA\b|flood|cyclone|1077|1070|collectorate control|"
                 r"district control room|\bDCR\b|control room.{0,20}collector|district emergency|relief"),
    ("police", r"police|thana|\bP\.?S\.?\b|\bS\.?P\.?\b|\bD\.?S\.?P\b|\bSDPO\b|\bSHO\b|\bO\.?C\.?\b|traffic|cyber|outpost|"
               r"\bchowki\b|crime|\b100\b|\b112\b|ERSS|vigilance"),
    ("health", r"hospital|ambulance|\bhealth|medical|blood|\bPHC\b|\bCHC\b|\bCMO\b|\bCMHO\b|doctor|\b108\b|\b102\b|trauma|covid"),
    ("disaster", r"control room"),   # a control room that names no other service: the district's own
]
OTHER = re.compile(r"(?i)municipal|nagar (nigam|palika)|electric|power|energy|engg|engineering|harbour|bsnl|telephone|railway|"
                   r"water|\bgas\b|bank|airline|air ?port|"
                   r"\bbus\b|transport|tourism|tourist|election|ration|consumer|grievance|pension|scheme|mgnrega|pmay|kisan|"
                   r"agricultur|education|school|vigilance|anti.?corruption|income tax|revenue")
NOT_PERSON = re.compile(r"(?i)hospital|memorial|nagar|marg|road|college|school|clinic|nursing|trust|chowk|bhawan|institute")
STD = re.compile(r"(?i)std\.?\s*code\s*[-:]?\s*\(?(0\d{2,4})")
STATION = {"police": r"police station|\bP\.?S\.?\b|thana|outpost|chowki|\bO\.?P\.?\b",
           "fire": r"fire station|fire (and|&) (rescue|emergency) (services? )?station|\bF\.?S\.?\b",
           "health": r"hospital|\bPHC\b|\bCHC\b|dispensary|health cent|medical college"}
POSTS = r"\b(Superintendent of Police|Medical (?:Supdt|Superintendent)|Chief Medical Officer|District Disaster Management " \
    r"Officer|District Child Protection Officer|Station (?:Fire )?Officer|Officer[- ]in[- ]charge|S\.?P\.?|Addl\.? ?S\.?P\.?|" \
    r"D\.?S\.?P\.?|SDPO|S\.?H\.?O\.?|O\.?C\.?|I\.?C\.?|CMO|CMHO|CMS|DDMO|DPO|DCPO|ADM|SDM|DM)\b"
PERSON = re.compile(r"\b(?:Shri|Sri|Smt|Kum|Dr|Mr|Ms|Mrs)\.?\s+[A-Z][\w.]*(?:\s+[A-Z][\w.]*){0,4}")


def items(get=None):
    return _emerg.seed(MODULE)


def dept_of(text):
    if OTHER.search(text or "") and not re.search(r"(?i)police|fire|disaster|hospital|ambulance|women|child|emergency", text or ""):
        return None
    for d, pat in DEPTS:
        if re.search(pat, text or "", re.I):
            return d
    return None


def heading_before(table, content):
    """The nearest heading text above a table inside the page content (h2-h6, a bold paragraph or a caption), else ''."""
    cap = table.find("caption")
    if cap and _esw.clean(cap.get_text(" ")):
        return _esw.clean(cap.get_text(" "))
    for el in table.find_all_previous(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "p"], limit=4):
        if content not in el.parents:
            break
        t = _esw.clean(el.get_text(" "))
        if t and len(t) < 90 and not re.search(r"\d{6,}", t):
            if el.name in ("h2", "h3", "h4", "h5", "h6", "strong", "b") or el.find(["strong", "b"]):
                return t
    return ""


def is_number_cell(t):
    t = t or ""
    d = len(re.sub(r"\D", "", t))
    return d >= 3 and d >= len(re.sub(r"[\d\s()+,/.:-]|or|and|tel|ph|mob|fax|landline", "", t, flags=re.I))


def split_row(cells):
    """(label, number text, extra labels) of one table row; S.No. cells and header-like rows give ("", "", [])."""
    labels, nums = [], []
    for c in cells:
        c = _esw.clean(c) or ""
        if not c or re.fullmatch(r"\d{1,3}\.?", c):
            continue
        (nums if is_number_cell(c) else labels).append(c)
    return labels, " , ".join(nums)


def main_of(soup):
    m = soup.select_one("#SkipContent") or soup.select_one("main") or soup
    for t in m.select(".breadcrumb-outer, .printShare, #breadcam, script, style"):
        t.decompose()
    return m


def records(url, html, p):
    host = urlparse(url).netloc
    lu = last_updated(html)
    soup = _esw.soup(html)
    m = main_of(soup)
    content = m.select_one(".bodyWrapper") or m
    recs, seen = [], set()
    for table in content.find_all("table"):
        head = heading_before(table, content)
        for cells in _esw.grid(table):
            labels, numtext = split_row(cells)
            if not labels:
                continue
            label = " - ".join(dict.fromkeys(labels))
            if re.fullmatch(r"(?i)(s\.?\s*no\.?|sl\.?\s*no\.?|name|services?|department|contact.*|helpline.*|designation|"
                            r"office|particulars|service\s*/\s*\w+|.*number.*|.*details.*)( - .*)?", label) and not numtext:
                continue
            nums = _emerg.phones(numtext, *[x for x in labels if re.search(r"\d{6,}", x)])
            if not nums:
                continue
            ctx = f"{head} {label}"
            dept = dept_of(label) or dept_of(head)
            if not dept:
                continue
            station = STATION.get(dept)
            level = ("police_station" if dept == "police" else "facility") if station and re.search(station, ctx, re.I) \
                else "district"
            post = re.search(POSTS, label)
            if post and re.fullmatch(r"SDPO|SDM|Sub.?Divisional.*", post.group(0)) or re.search(r"(?i)sub.?division", ctx):
                level = "subdivision"
            person = PERSON.search(label)
            if person and NOT_PERSON.search(label[person.end():person.end() + 30]):
                person = None
            std = STD.search(head) or STD.search(label)
            area = label if level != "district" else (p.get("district") or label)
            if head and level == "district" and re.fullmatch(r"(?i)(the )?(page|helpline|helpline numbers?|important.*|emergency.*|"
                                                             r"useful.*|contact.*)", head):
                head = ""
            key = _emerg.unique(f"{host}:{_emerg.slug((head + ' ' + label) if head else label)[:90]}", seen)
            recs.append(_emerg.record(
                MODULE, key, "help", dept=dept, level=level, area=area, service=label, heading=head or None,
                post=post.group(0) if post else None, name=person.group(0) if person else None,
                phone=nums, std_code=std.group(1) if std else None, short_codes=_emerg.short_codes(numtext) or None,
                email=_emerg.emails(" ".join(cells)) or None,
                district=p.get("district"), state=p.get("state"), office_id=key, source=url, last_updated=lu))
    return recs


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    host = urlparse(url).netloc
    files = [_emerg.keep(MODULE, f"{host}-helpline", r.content)]
    recs = records(url, r.text, p)
    return recs, files, "" if recs else "no rows"
