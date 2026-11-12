"""Nagar Palik Nigam Bhilai (bhilainagarnigam.com): the officers in charge of its 5 zones (1 Nehru Nagar, 2 Vaishali Nagar,
3 Mother Teresa Nagar, 4 Shivaji Nagar, 5 Sector 6). One PDF, the duty list of the officers ("नगर पालिक निगम भिलाई के अधिकारियों
के प्रभार", /officersno.pdf; answers from Germany; live sample 2026-11-11, not in archive.s1d.me), 10 pages, set in Kruti Dev
(converted with dforms/_ward_kd.py; in this file the curly quotes stand for ' and ", so they are made straight first). Columns:
क्र | officer name and post | the numbered duties ("1. जोन आयुक्त, जोन 1-नेहरू नगर"). The PDF gives no phones and no ward lists.
A row = one serial number; its duties run from the "1." line at or above the serial line to the next row's duties. Each duty that
names a zone gives one record for that zone: post = the charge the duty names ("प्रभारी कार्यपालन अभियंता" -> Executive Engineer
(in charge)), else the officer's own post (Zone Commissioner, Executive / Assistant / Sub Engineer, Assistant Revenue Officer,
Revenue Inspector, Zone Assistant Health Officer, zone office clerks). Names and posts are Hindi: name and name_regional carry the
same text, post is English, post_regional as written. Records: level "zone". Ids: dept:ward2n_bhilai:zone-<n>:<post slug>:<n>.
"""
import re

import provenance
from dforms import _esw, _ward, _ward_kd as kd

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_bhilai"
BODY, LGD, STATE, DISTRICT = "Nagar Palik Nigam Bhilai", "250639", "CG", "Durg"
URL = "https://bhilainagarnigam.com/officersno.pdf"
ZONES = {"1": "Zone 1 Nehru Nagar", "2": "Zone 2 Vaishali Nagar", "3": "Zone 3 Mother Teresa Nagar", "4": "Zone 4 Shivaji Nagar",
         "5": "Zone 5 Sector 6"}
POSTS = (("जोन सहायक स्वास्थ्य अधिकारी", "Zone Assistant Health Officer"), ("सहायक स्वास्थ्य अधिकारी", "Assistant Health Officer"),
         ("जोन आयुक्त", "Zone Commissioner"), ("अधीक्षण अभियंता", "Superintending Engineer"),
         ("कार्यपालन अभियंता", "Executive Engineer"), ("सहायक अभियंता", "Assistant Engineer"), ("उप अभियंता", "Sub Engineer"),
         ("सहायक राजस्व अधिकारी", "Assistant Revenue Officer"), ("राजस्व अधिकारी", "Revenue Officer"),
         ("सहायक राजस्व निरीक्षक", "Assistant Revenue Inspector"), ("राजस्व उप निरीक्षक", "Revenue Sub Inspector"),
         ("राजस्व निरीक्षक", "Revenue Inspector"), ("सहायक अधीक्षक सह लेखापाल", "Assistant Superintendent and Accountant"),
         ("सहायक अधीक्षक", "Assistant Superintendent"), ("लेखापाल", "Accountant"), ("स्वच्छता निरीक्षक", "Sanitary Inspector"),
         ("स्वच्छता पर्यवेक्षक", "Sanitation Supervisor"), ("मानचित्रकार", "Draughtsman"), ("सहायक ग्रेड-2", "Assistant Grade 2"),
         ("तकनीकी सहायक", "Technical Assistant"), ("डाटा एंट्री", "Data Entry Operator"), ("समयपाल", "Timekeeper"))
HONOR = re.compile(r"^(श्रीमती|श्री|सुश्री|मो\.|डॉ\.?|डा\.)\s")
ITEM = re.compile(r"^(\d{1,2})\s*[-.]\s")      # Kruti Dev "1-" and "1." are the duty numbers
ZONE_REF = re.compile(r"जोन\s*(?:क्रमांक|क्र\.)?\s*-?\s*0?([1-5])(?:\s*(?:,|एवं|व)\s*0?([1-5]))?(?:\s*(?:,|एवं|व)\s*0?([1-5]))?")


def items(get=None):
    return [{"key": f"{MODULE}-officers", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def hi(raw):
    t = raw.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'}))
    t = kd.convert(t).replace("]", ",").replace("¼", "(").replace("½", ")")
    return _esw.clean(t)


def lines_of(pages):
    """[(serial, left text, right raw text, src_pos)] of every line (page heads and page numbers left out). Columns by start position."""
    out = []
    for pn, lno, ln in _ward.pdf_lines(pages):
        if re.search(r"Page \d+ of|vf/kdkjh@deZpkjh|^\s*Ø\s|¼1½", ln):
            continue
        serial, left, right = None, [], []
        for m in re.finditer(r"\S+(?: \S+)*", ln):
            s, t = m.start(), m.group(0)
            if s < 4 and re.fullmatch(r"\d{1,2}", t) and serial is None and not right:
                serial = t
            elif s < 22 and not right:
                left.append(t)
            else:
                right.append(t)
        if serial or left or right:
            out.append((serial, " ".join(left), " ".join(right), provenance.line_pos(pn, lno, ln)))
    return out


def post_en(text):
    t = _esw.clean(text).replace("ष", "श")
    for hi_, en in POSTS:
        if hi_.replace("ष", "श") in t:
            return en + (" (in charge)" if "प्रभारी" in t else "")
    return ""


def rows(lines):
    """[(serial, name, own post, [duty texts], src_pos)]; src_pos = the serial number's line, "to" = the last line of the row."""
    serials = [i for i, (s, *_) in enumerate(lines) if s]
    starts = []
    for i, (_, _, r, *_) in enumerate(lines):
        m = ITEM.match(r)
        if not (m and m.group(1) == "1"):
            continue
        # a short unnumbered heading right above item 1 ("प्रभारी अधीक्षण अभियंता", "नोडल अधिकारी,") opens the same list
        if i and lines[i - 1][2] and not ITEM.match(lines[i - 1][2]) and len(lines[i - 1][2].split()) <= 8 \
                and re.match(r"(प्रभारी|नोडल|जोन आयुक्त)", hi(lines[i - 1][2])) and post_en(hi(lines[i - 1][2])):
            i -= 1
        starts.append(i)
    spans, prev = [], -1
    for i in serials:
        st = max([g for g in starts if prev < g <= i] or [i])
        spans.append(st)
        prev = i
    out = []
    for k, i in enumerate(serials):
        st, end = spans[k], (spans[k + 1] if k + 1 < len(spans) else len(lines))
        lo = max(st - 2, spans[k - 1] + 1 if k else 0)
        lefts = [(j, hi(lines[j][1])) for j in range(lo, end) if lines[j][1]]
        names = [(abs(j - i), t) for j, t in lefts if HONOR.match(t) and j <= i]
        posts = [(abs(j - i), t) for j, t in lefts if not HONOR.match(t) and j >= i]
        name = re.sub(r"[,\s]+[\u093e-\u094d]*$", "", min(names)[1]) if names else ""
        own = min(posts)[1].strip(" ,") if posts else ""
        duties, cur = [], ""
        head = not ITEM.match(lines[st][2])          # the list opens with an unnumbered heading line
        for j in range(st, end):
            r = lines[j][2]
            if not r:
                continue
            if ITEM.match(r) and cur and not (head and j == st + 1):
                duties.append(cur)
                cur = ""
            cur += " " + ITEM.sub("", r)
        if cur:
            duties.append(cur)
        pos = dict(lines[i][3]) if len(lines[i]) > 3 else None
        if pos and end - 1 > i:
            pos["to"] = {"page": lines[end - 1][3]["page"], "line": lines[end - 1][3]["line"]}
        out.append((lines[i][0], name, own, [hi(d) for d in duties], pos))
    return out


def parse(pages, p):
    seen, recs, n = set(), [], {}
    for serial, name, own, duties, pos in rows(lines_of(pages)):
        done = set()
        for d in duties:
            t = d.replace("ष", "श")
            zs = []
            for m in ZONE_REF.finditer(t):
                zs += [z for z in m.groups() if z and z not in zs]
            if not zs:
                continue
            charge = t[:ZONE_REF.search(t).start()].strip(" ,")
            rest = ZONE_REF.sub(" ", t)
            for zn in ("नेहरू नगर", "वैशाली नगर", "मदर टेरेसा नगर", "मदरटेरेसा नगर", "शिवाजी नगर", "सेक्टर 06", "सेक्टर 6", "नगर"):
                rest = rest.replace(zn, " ")
            en = post_en(charge) or (post_en(rest.split("हेतु")[-1]) if "हेतु" in rest else "")
            if not en and len(re.findall(r"[\u0900-\u097F]+", rest)) > 3:
                continue          # a duty that only mentions a zone (an upload, a file register), not a charge
            post_hi = (charge if post_en(charge) else "") or own
            en = en or post_en(own) or _ward.hi_post(own)
            for z in zs:
                if (z, en) in done:
                    continue
                done.add((z, en))
                key = f"zone-{z}:{_esw.slug(en)}"
                n[key] = n.get(key, 0) + 1
                recs.append(_ward.record(MODULE, f"{key}:{n[key]}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                         level="zone", area=ZONES[z], zone=ZONES[z], post=en, post_regional=post_hi or None,
                                         name=name, name_regional=name or None, own_post=own or None, duty=_esw.clean(d),
                                         serial=serial, source=p["url"], src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "officers", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no zone duties (pdftotext missing?)"
