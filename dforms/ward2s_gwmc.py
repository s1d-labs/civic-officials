"""Greater Warangal Municipal Corporation (gwmc.gov.in): the officers who serve each election ward, section by section.
Source: the public form "Know Your Service Person with House No." (/KnowUrAreaServicePerson.aspx; ASP.NET, no captcha; India only:
no TCP answer from Germany on 2026-11-11; one answer read from India the same day; the empty form is in archive.s1d.me,
2026-11-05). The form takes a house number in three boxes (ward - block - door, "11-25-462") and answers with "Election Ward
Number : 23" and one table per section: Tax Section (Deputy Commissioner, Taxation Officer, Revenue Officer, Revenue Inspector,
Ward Officer, Bill Collector), Town Planning Section (City Planner, Asst City Planner, TPBO/TPS), Public Health Section (Municipal
Health Officer, Sanitary Supervisor, Sanitary Inspector), Engineering Section and Engineering Section (Electrical) (SE, EE, DEE,
AE), Urban Maleria Section, Birth and Death Section, Horticulture Section, MEPMA Section: Name | Designation | Cellno.
The second form, "with Election Ward", needs a captcha: it is not used. There is no list of house numbers, so one queue item is
one house-number ward W and asks door "1" of blocks 1, 2, 3 ... (POST with the form's own hidden fields); it stops after
MISS_AFTER blocks in a row without an answer (or FIRST_TRY blocks with none at all). Every answer gives the officers of one
election ward. The page shows no "last updated" date.
Records: level "ward", wards = [the election ward], area "Election Ward <n>"; extra keys section, house_blocks (the
"W-B" blocks that pointed to that ward in this item). Officers who serve many wards (Deputy Commissioner, City Planner, SE) appear
once per ward. "VACANT" posts are kept with vacant = true. Record ids: dept:ward2s_gwmc:w<ward>:<section slug>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_gwmc"
BODY, LGD, STATE, DISTRICT = "Greater Warangal Municipal Corporation", "251691", "TG", "Hanumakonda"
URL = "https://gwmc.gov.in/KnowUrAreaServicePerson.aspx"
WARDS = 66            # house-number wards to try (GWMC has 66 election wards; house-number wards are fewer)
BLOCKS = 60           # highest block number asked in one ward
MISS_AFTER, FIRST_TRY = 6, 12
F = "ctl00$ContentPlaceHolder1$"
SECTION_WING = ((r"tax", "revenue"), (r"town\s*planning", "planning"), (r"electrical", "electrical"), (r"engineering", "engineering"),
                (r"maleria|malaria|birth", "health"), (r"horticulture", "horticulture"))


def wing(section, post):
    for rx, w in SECTION_WING:
        if re.search(rx, section, re.I):
            return w
    return _ward.wing_of(post)


def items(get=None):
    return [{"key": f"{MODULE}-hno-w{w}", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True,
                                                    "house_ward": w}} for w in range(1, WARDS + 1)]


def hidden(html):
    return {m.group(1): m.group(2) for m in re.finditer(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html)}


def answer(html):
    """(election ward, [(section, name, post, phone)]) of one form answer; (None, []) when the house number is not known."""
    m = re.search(r"Election\s+Ward\s+Number\s*:\s*(\d+)", html)
    if not m:
        return None, []
    rows, section = [], ""
    i = html.find("filldata")
    for tr in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", html[i:]):
        cells = [_esw.clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", tr.group(1))]
        if len(cells) == 1:
            if not re.match(r"(?i)election\s+ward", cells[0]):
                section = cells[0]
        elif len(cells) >= 3 and cells[:2] != ["Name", "Designation"]:
            rows.append((section, cells[0], cells[1], cells[2]))
    return m.group(1), rows


def parse(html, p, block=None, seen=None, recs=None, blocks=None):
    seen = set() if seen is None else seen
    recs = [] if recs is None else recs
    blocks = {} if blocks is None else blocks
    ward, rows = answer(html)
    if not ward:
        return recs
    ward = str(int(ward))
    if block:
        blocks.setdefault(ward, []).append(block)
    for section, name, post, phone in rows:
        if not post:
            provenance.skipped('skip: not post')
            continue
        key = f"w{ward}:{_esw.slug(section)}:{_esw.slug(post)}:{_esw.slug(name) or 'post'}"
        if f"dept:{MODULE}:{key}" in {r for r, _ in recs}:
            provenance.skipped("repeated (same post in an earlier answer)")
            continue
        recs.append(_ward.record(MODULE, key, seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="ward",
                                 area=f"Election Ward {ward}", post=post, name=name, phone=phone, wards=[ward],
                                 source=p["url"], section=section, wing=wing(section, post), house_blocks=blocks.get(ward)))
    return recs


def fetch(p, get):
    w = p["house_ward"]
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    form = hidden(r.text)
    if "__VIEWSTATE" not in form:
        return [], [_esw.keep(MODULE, f"form-w{w}", r.content)], "no form"
    seen, recs, blocks, files, miss, hits = set(), [], {}, [], 0, 0
    for b in range(1, BLOCKS + 1):
        data = dict(form, **{F + "txtward": str(w), F + "txtBlock": str(b), F + "txthno": "1", F + "btnshow": "Show"})
        a = get(p["url"], method="POST", data=data)
        if a is None:
            miss += 1
        else:
            n = len(recs)
            parse(a.text, p, f"{w}-{b}", seen, recs, blocks)
            if answer(a.text)[0]:
                hits += 1
                miss = 0
                if len(recs) > n:
                    files.append(_esw.keep(MODULE, f"hno-{w}-{b}-1", a.content))
                form = hidden(a.text) or form
            else:
                miss += 1
        if (hits and miss >= MISS_AFTER) or (not hits and b >= FIRST_TRY):
            break
    # the blocks list of each ward is final only now: write it into every record of that ward
    for _, d in recs:
        d["house_blocks"] = blocks.get(d["wards"][0])
    return recs, files, "" if recs else f"no house number of ward {w} answered"
