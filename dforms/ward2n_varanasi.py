"""Varanasi Nagar Nigam (nnvns.org.in): the sanitation supervisors and sanitary and food inspectors of its 100 wards, with the zone
and sub-zone of each ward. One PDF, the "Sanitary Beat List" (/nnvns/attachments/article/84/All_100_Ward_Beat_List.pdf, linked
from the home page; 75 pages, made 2025-04-15; not in archive.s1d.me; live sample 2026-11-11 from this box). One row per sweeping
beat: B_W_No ("<ward>-<beat>") | Zone | Sub_Zone | Ward_No | Ward_Name | Work_Area | Beat_Length | sweeper names | SUP1_Name |
SUP1_MOB | SFI_Name | SFI_MOB | Remarks. The ward number is read from B_W_No (the Sub_Zone / Ward_No cells are empty in some rows,
so the columns shift); zone names are written in several spellings ("Rishi Mandavi", "Rishimandawi") and are mapped to one.
Long cells wrap, so a row is read by its end: "<supervisor> <mobile> <SFI> <mobile>"; a name missing from a row is taken from the
other rows with the same mobile. The sweepers are not read (workers, not officers). The officers' telephone list on the same site
(/nnvns/attachments/article/218/Officers_Telephone1.pdf) is a scanned image: not read.
Records: one per person and post, level "ward", wards = every ward where the beat list names them, zone = the zone of those wards
("Sarnath Zone"), sub_zones = their sub-zones. A person = one name (Dr / Shri left out); mobiles seen in one row only are Excel fill-down slips and are left out;
a name seen in one row only is left out (a sweeper name that wrapped into the column). beats = the number of beat rows.
Record ids: dept:ward2n_varanasi:<sup|sfi>:<name slug>.
"""
import collections
import re

from dforms import _esw, _ward

MODULE = "ward2n_varanasi"
BODY, LGD, STATE, DISTRICT = "Varanasi Nagar Nigam", "249531", "UP", "Varanasi"
URL = "https://nnvns.org.in/nnvns/attachments/article/84/All_100_Ward_Beat_List.pdf"
ZONES = (("varunapar", "Varunapar"), ("sarnath", "Sarnath"), ("bhelup", "Bhelupur"), ("adampur", "Adampur"), ("ramnagar", "Ramnagar"),
         ("dashasw", "Dashaswamedh"), ("rishi", "Rishi Mandvi"), ("kotwali", "Kotwali"))
NAME = r"(?:[A-Za-z][A-Za-z.()/]*(?: [A-Za-z.()/]+)*)"
POSTS = {"sup": ("Sanitation Supervisor", "sanitation"), "sfi": ("Sanitary and Food Inspector", "sanitation")}


def items(get=None):
    return [{"key": f"{MODULE}-beat-list", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def zone_of(s):
    k = re.sub(r"[^a-z]", "", s.lower())
    return next((v for p, v in ZONES if k.startswith(p)), None)


MOB = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def _runs(line):
    """Text runs (words joined by single spaces) with their start; a mobile inside a run is cut out as a run of its own."""
    out = []
    for m in re.finditer(r"\S+(?: \S+)*", line):
        x, t, last = m.start(), m.group(0), 0
        for mm in MOB.finditer(t):
            if t[last:mm.start()].strip():
                out.append((x + last, t[last:mm.start()].strip()))
            out.append((x + mm.start(), mm.group(0)))
            last = mm.end()
        if t[last:].strip():
            out.append((x + last + len(t[last:]) - len(t[last:].lstrip()), t[last:].strip()))
    return out


def beats(pages):
    """[(ward, zone or None, sub zone or None, sup name, sup mobile, sfi name, sfi mobile)] of the beat rows. The two mobile
    columns are found per page from the start positions of the mobiles (the two most common ones: left = supervisor, right =
    SFI); a row with one mobile gives it to the nearer column. The name is the text run just before the mobile."""
    out = []
    for pg in pages:
        lines = [ln for ln in pg.splitlines() if re.match(r"\s*\d{1,3}-\d{2,3}\s{2,}", ln)]
        pos = collections.Counter(m.start() for ln in lines for m in MOB.finditer(ln))
        cols = sorted(x for x, _ in pos.most_common(2))
        if len(cols) == 2 and cols[1] - cols[0] < 12:
            cols = sorted(x for x, _ in pos.most_common(3))[:2]
        if len(cols) < 2:
            continue
        for ln in lines:
            m = re.match(r"\s*(\d{1,3})-\d{2,3}\s{2,}(.*)", ln)
            cells = re.split(r"\s{2,}", m.group(2).strip())
            z = zone_of(cells[0]) if cells else None
            sub = cells[1] if z and len(cells) > 2 and not re.fullmatch(r"\d+", cells[1]) else None
            got = {}
            runs = _runs(ln)
            for k, (x, t) in enumerate(runs):
                if not MOB.fullmatch(t):
                    continue
                col = min(range(2), key=lambda c: abs(cols[c] - x))
                prev = runs[k - 1][1] if k else ""
                name = prev if re.fullmatch(NAME, prev) and not re.search(r"(?i)\b[sdw]/o\b|^\d", prev) else ""
                got[col] = (name, t)
            if got:
                (sn, sm), (fn, fm) = got.get(0, ("", "")), got.get(1, ("", ""))
                out.append((str(int(m.group(1))), z, sub, sn, sm, fn, fm))
    return out


def parse(pages, p):
    rows = beats(pages)
    by_mob = collections.defaultdict(collections.Counter)
    for _, _, _, sn, sm, fn, fm in rows:
        for nm, mob in ((sn, sm), (fn, fm)):
            if nm:
                by_mob[mob][nm] += 1
    # a mobile seen in one row only is an Excel fill-down slip (9452709492, ...93, ...94) when the same first letter of the name has
    # a mobile seen in more rows: the row is counted under that mobile
    mob_rows = collections.Counter(m for r in rows for m in (r[4], r[6]) if m)
    main = {}
    for _, _, _, sn, sm, fn, fm in rows:
        for nm, mob in ((sn, sm), (fn, fm)):
            if nm and mob and mob_rows[mob] >= 2:
                f = re.sub(r"(?i)^(dr|shri|smt)\.?\s+", "", nm)[:1].lower()
                main.setdefault((_esw.slug(nm), f), collections.Counter())[mob] += 1
    canon = {}
    for _, _, _, sn, sm, fn, fm in rows:
        for nm, mob in ((sn, sm), (fn, fm)):
            if nm and mob and mob_rows[mob] == 1:
                f = re.sub(r"(?i)^(dr|shri|smt)\.?\s+", "", nm)[:1].lower()
                if (_esw.slug(nm), f) in main:
                    canon[(mob, f)] = main[(_esw.slug(nm), f)].most_common(1)[0][0]
    # a row with one mobile can put it in the wrong column: a mobile takes the column it has in most rows
    col_of = collections.defaultdict(collections.Counter)
    for _, _, _, sn, sm, fn, fm in rows:
        col_of[sm]["sup"] += 1
        col_of[fm]["sfi"] += 1
    people = {}
    for ward, z, sub, sn, sm, fn, fm in rows:
        for kind, nm, mob in (("sup", sn, sm), ("sfi", fn, fm)):
            kind = col_of[mob].most_common(1)[0][0] if mob else kind
            nm = nm or (by_mob[mob].most_common(1)[0][0] if by_mob[mob] else "")
            if not nm or re.match(r"(?i)^[sdw]/o\b", nm):
                continue
            if not mob:
                continue
            first = re.sub(r"(?i)^(dr|shri|smt)\.?\s+", "", nm)[:1].lower()
            d = people.setdefault((kind, canon.get((mob, first), mob), first),
                                  {"names": collections.Counter(), "mobs": collections.Counter(), "wards": [],
                                   "zones": collections.Counter(), "subs": [], "rows": 0})
            d["names"][nm] += 1
            d["mobs"][mob] += 1
            d["rows"] += 1
            if ward not in d["wards"]:
                d["wards"].append(ward)
            if z:
                d["zones"][z] += 1
            if sub and sub not in d["subs"]:
                d["subs"].append(sub)
    seen, recs = set(), []
    for (kind, key, first), d in people.items():
        if d["rows"] < 2:
            continue
        post, wing = POSTS[kind]
        # mobiles that occur once only are Excel fill-down slips (9452709492, ...93, ...94): the main mobile stands for them
        mobs = [key]
        zones = [z for z, _ in d["zones"].most_common()]
        wards = sorted(d["wards"], key=int)
        recs.append(_ward.record(MODULE, f"{kind}:{key}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="ward",
                                 area="Ward " + ", ".join(wards) if len(wards) < 6 else f"{len(wards)} wards", post=post,
                                 name=d["names"].most_common(1)[0][0], phone=key, wards=wards,
                                 other_names=[n for n in d["names"] if n != d["names"].most_common(1)[0][0]] or None,
                                 zone=f"{zones[0]} Zone" if zones else None,
                                 zones=[f"{z} Zone" for z in zones] if len(zones) > 1 else None, sub_zones=d["subs"] or None,
                                 beats=d["rows"], wing=wing, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "beat-list", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no beat rows (pdftotext missing?)"
