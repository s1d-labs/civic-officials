"""Greater Chennai Corporation (chennaicorporation.gov.in): the ward staff that the corporation puts in charge of its monsoon relief
centres, ward by ward, and the senior officers (SRO) over groups of wards. Source: one PDF, "Details of Relief Centres in GCC - 2025",
/gcc/pdf/Relief_Center_details.pdf (18 pages, made from "Relief_Center_details (1) UPDATED 2025.xlsx" on 2025-10-28; the PDF shows
no "last updated" date). Saved in archive.s1d.me 2026-11-11; the live file answers from Germany (same bytes on 2026-11-11).
Columns: S.No | Zone | Ward | Name of the Relief Centre | Capacity | Name of the Officials Incharge | Officials Incharge (mobile) |
SRO Name | SRO Contact No; 215 relief centres in the 15 zones, about 170 of the 200 wards. The official in charge is a ward-level revenue
or licence officer, written as "DHARANIRAJ-TAX COLLECTOR", "P.SIVANESAN , Assessor", "Durairaj- LI", "Sathyabalan -TC": name and post.
Other GCC staff pages were checked and give no ward officers (2026-11-11): /gcc/department/zonal-details/ is a map image,
/gcc/who-is-who/ lists only the heads; "CDMP DIRECTORY 2026.pdf" (the disaster management directory, 183 pages, 113 MB) is cut off
in the archive (52 MB saved) and has no text layer.
The PDF is read with pdftotext -layout (_ward.layout_pages). A row is one line that starts "S.No Zone Ward"; names and posts that
wrap onto the lines above or below are taken from the same columns (the blank-line-separated block of that row).
Records (level "ward", wards = every ward where that person holds a relief centre, zone = "Zone N (Name)"):
  one per official in charge (post as the page writes it, expanded: TC -> Tax Collector, LI -> Licence Inspector; extra key
  "duty": "relief centre in charge", "relief_centres": the centre names), and one per SRO (post "SRO (relief centres)").
Record ids: dept:ward2s_chennai:z<zone>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

MODULE = "ward2s_chennai"
BODY, LGD, STATE, DISTRICT = "Greater Chennai Corporation", "252294", "TN", "Chennai"
URL = "https://chennaicorporation.gov.in/gcc/pdf/Relief_Center_details.pdf"
ZONES = {1: "Thiruvottiyur", 2: "Manali", 3: "Madhavaram", 4: "Tondiarpet", 5: "Royapuram", 6: "Thiru. Vi. Ka. Nagar", 7: "Ambattur",
         8: "Anna Nagar", 9: "Teynampet", 10: "Kodambakkam", 11: "Valasaravakkam", 12: "Alandur", 13: "Adyar", 14: "Perungudi",
         15: "Sholinganallur"}
ROW = re.compile(r"^\s*(\d{1,3})\s+(\d{1,2})\s+(\d{1,3})\s+\S")
PHONE = re.compile(r"(?<![\d,(])(?:\d{10,11}|\d(?:,\d{1,3}){3,5})(?!\d)")
HEADER = re.compile(r"(?i)(name of the|officials|incharge|capacity|sro\s+(name|contact)|details of relief|^\s*no\s*$|s\.no\s+zone)")
POSTS = (
    (r"tax\s*collec[td]?[eo]r|t\.?\s?c\.?", "Tax Collector"), (r"licen[cs]e\s*inspector|l\.?\s?i\.?", "Licence Inspector"),
    (r"assessor", "Assessor"), (r"revenue\s*inspector|r\.?\s?i\.?", "Revenue Inspector"), (r"bill\s*collector|b\.?\s?c\.?", "Bill Collector"),
    (r"assistant\s*revenue\s*officer|a\.?r\.?o\.?", "Assistant Revenue Officer"), (r"assistant\s*engineer|a\.?\s?e\.?", "Assistant Engineer"),
    (r"junior\s*engineer|j\.?\s?e\.?", "Junior Engineer"), (r"sanitary\s*inspector|s\.?\s?i\.?", "Sanitary Inspector"),
    (r"conservancy\s*inspector|c\.?\s?i\.?", "Conservancy Inspector"), (r"r\.?\s?w\.?", "RW"),
    (r"(?:[a-z]+\s+)?(?:officer|inspector|engineer|superintendent|assistant|clerk|collector|supervisor)", None),
)


def items(get=None):
    return [{"key": f"{MODULE}-relief-centres", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def phone_of(s):
    """A 10-digit mobile, also when the spreadsheet wrote it as a number with thousands commas ("9,17,60,84,284")."""
    d = re.sub(r"\D", "", s or "")
    return d if len(d) >= 10 else _esw.clean(s)


def name_post(text):
    """("DHARANIRAJ-TAX COLLECTOR") -> ("DHARANIRAJ", "Tax Collector"); ("M.P.KUMAR Tax collector") -> ("M.P.KUMAR", "Tax Collector");
    a text without a post -> (text, "")."""
    t = _esw.clean(text).strip(" ,-")
    for rx, post in POSTS:
        m = re.search(r"(?i)(?:\s*[-,–]\s*|\s+)(" + rx + r")\s*$", t)
        if m and m.start() > 0:
            name = t[:m.start()].strip(" ,-")
            if name:
                return name, post or _esw.clean(m.group(1)).title()
    return t, ""


def rows(pages):
    """[(zone, ward, centre, capacity, official text, official phone, sro text, sro phone)] from the page texts."""
    out = []
    for page in pages:
        lines = [ln for ln in page.split("\n") if not HEADER.search(ln)]
        blocks, cur = [], []
        for ln in lines + [""]:
            if ln.strip():
                cur.append(ln)
            elif cur:
                blocks.append(cur)
                cur = []
        for b in blocks:
            mains = [i for i, ln in enumerate(b) if ROW.match(ln)]
            for k, i in enumerate(mains):
                # lines between two rows with no blank line between them: the upper half wraps the upper row, the lower half the
                # lower row (wrapped cells are centred on their row's line)
                lo = (mains[k - 1] + 1 + (i - mains[k - 1]) // 2) if k else 0  # a line half-way goes to the upper row
                hi = (i + 1 + (mains[k + 1] - i) // 2) if k + 1 < len(mains) else len(b)
                out.append(_row(b[i], b[lo:i], b[i + 1:hi]))
    return [r for r in out if r]


def _seg(lines, lo, hi, slack=3):
    """The text of each line between columns lo and hi (a little wider on the left: wrapped cells are centred), phones left out."""
    out = []
    for ln in lines:
        seg = re.sub(r"(?<=\s),(?=\s|$)", " ", PHONE.sub(" ", ln[max(lo - slack, 0):hi])).strip()
        if seg and not re.fullmatch(r"[\d\s,.-]+", seg):
            out.append(seg)
    return out


def _row(main, above, below):
    """One relief centre: the main line holds S.No, zone, ward, the capacity and (mostly) the SRO's name and mobile at the right end.
    The officials' mobiles are on the main line, or, where two officials share the cell (Zone 9), on the lines above and below."""
    m = ROW.match(main)
    zone, ward = int(m.group(2)), m.group(3)
    cap = re.search(r"(?<=\s\s)(\d{1,4})(?=\s{2,})", main[m.end(3):])
    if cap is None:
        return None
    cap_start, cap_end = m.end(3) + cap.start(), m.end(3) + cap.end()
    on_main = [x for x in PHONE.finditer(main) if x.start() > cap_end]
    off_ph = [(x.start(), x.group(0)) for ln in above + below for x in PHONE.finditer(ln) if x.start() > cap_end]
    sro_ph, sro_lo, sro_name = None, len(main), ""
    if len(on_main) >= 2 or (on_main and off_ph and min(x for x, _ in off_ph) < on_main[-1].start() - 10):
        sro_ph = on_main[-1]
        on_main = on_main[:-1]
        nm = re.search(r"(\S+(?: \S+)*)\s*$", main[:sro_ph.start()].rstrip())
        sro_lo, sro_name = nm.start(1), nm.group(1)
    elif on_main and main[on_main[-1].end():].strip():  # a mobile, then a name with no mobile: an SRO without a number
        sro_lo = on_main[-1].end() + 1
        sro_name = main[sro_lo:].strip()
    off_ph = sorted(off_ph + [(x.start(), x.group(0)) for x in on_main])
    if sro_ph is None and not on_main and not off_ph:
        return None
    hi = min([x for x, _ in off_ph] + [sro_lo])
    mid = PHONE.sub(" ", main[cap_end + 1:hi]).strip(" ,")
    off = _esw.clean(" ".join(_seg(above, cap_end + 1, hi) + ([mid] if mid else []) + _seg(below, cap_end + 1, hi)))
    # the phones in page order: above the main line first
    phones = [phone_of(t) for _, t in [(x.start(), x.group(0)) for ln in above for x in PHONE.finditer(ln) if x.start() > cap_end]
              + [(x.start(), x.group(0)) for x in on_main]
              + [(x.start(), x.group(0)) for ln in below for x in PHONE.finditer(ln) if x.start() > cap_end and x.start() < sro_lo]]
    centre = _esw.clean(" ".join([ln[:cap_start] for ln in above] + [main[m.end(3):cap_start]] + [ln[:cap_start] for ln in below]))
    return (zone, ward, centre, cap.group(1), off, phones, _esw.clean(PHONE.sub(" ", sro_name)), phone_of(sro_ph.group(0)) if sro_ph else "")


def people_of(off, phones):
    """[(name, post, phone)] of one "Officials Incharge" cell: "Deepika ,Sanitary Inspector, Narenthiran Babu,Conservancy Inspector"
    with two mobiles -> two people, each with the mobile in the same order. A mobile is given to a person only when the counts match
    (or there is one person)."""
    out, cur = [], ""
    off = re.sub(r"\(\s*\d{10}\s*\)", " ", off)
    for part in off.split(","):
        cur = f"{cur}, {part}" if cur else part
        name, post = name_post(cur)
        if post and re.fullmatch(r"[\d\s,.-]*", name):  # "9445190614-Ci": a mobile written where the name should be
            out.append(("", post))
            cur = ""
        elif post and name.strip(" .,"):
            out.append((name.strip(" .,"), post))
            cur = ""
    if cur.strip(" .,") and not re.fullmatch(r"[\d\s,.-]*", cur):  # a name with no post after it
        out.append((cur.strip(" .,"), ""))
    if len(out) == len(phones):
        return [(n, p, ph) for (n, p), ph in zip(out, phones)]
    if len(out) <= 1:
        return [(n, p, ", ".join(phones)) for n, p in out] or [("", "", ", ".join(phones))]
    return [(n, p, "") for n, p in out]


def parse(pages, p):
    people, sros = {}, {}
    for zone, ward, centre, cap, off, phones, sro, sph in rows(pages):
        for name, post, ph in people_of(off, phones):
            if not (name or ph):
                continue
            k = (zone, name.upper().replace(" ", ""), post, ph)
            d = people.setdefault(k, {"name": name, "post": post or "Official in charge", "phone": ph, "wards": [], "centres": []})
            d["wards"].append(ward)
            d["centres"].append(centre)
        if sro or sph:
            k = (zone, sro.upper().replace(" ", ""), sph)
            d = sros.setdefault(k, {"name": sro, "phone": sph, "wards": []})
            d["wards"].append(ward)
    seen, recs = set(), []
    for (zone, *_), d in list(people.items()) + list(sros.items()):
        zn = f"Zone {zone} ({ZONES[zone]})" if zone in ZONES else f"Zone {zone}"
        wards = sorted(dict.fromkeys(d["wards"]), key=lambda w: int(re.match(r"\d+", w).group()))
        is_sro = "centres" not in d
        post = "SRO (relief centres)" if is_sro else d["post"]
        extra = {} if is_sro else {"duty": "relief centre in charge", "relief_centres": list(dict.fromkeys(d["centres"]))}
        recs.append(_ward.record(MODULE, f"z{zone}:{_esw.slug(post)}:{_esw.slug(d['name']) or 'post'}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area="Ward " + ", ".join(wards), zone=zn,
                                 post=post, name=d["name"], phone=d["phone"], wards=wards,
                                 wing=None if is_sro else _ward.wing_of(post), source=p["url"], **extra))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a PDF"
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, [_esw.keep(MODULE, "relief-centres", r.content, "pdf")], "" if recs else "no rows"
