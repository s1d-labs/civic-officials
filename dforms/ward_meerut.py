"""Meerut Nagar Nigam (meerutnagarnigam.com): the sanitation officers of every ward. One PDF, "Wardwise Sanitary Inspector and Safai
Supervisor List" (/downloads/Wardwise-Sanitary-Inspector-And-Safai-Supervisor-List.pdf, linked from the home page; answers from
Germany; live sample 2026-11-11, not in archive.s1d.me). Set in Kruti Dev (legacy Hindi font): the text is converted with
dforms/_ward_kd.py.
  pages 1-6  one row per ward (1-90): ward no | पार्षद (councillor) name + mobile | सफाई एवं खाद्य निरीक्षक (sanitary and food
             inspector) name + mobile | सफाई नायक / कार्यवाहक सफाई नायक (sanitation supervisor) name + mobile | मोहल्ले (localities).
             Columns are found per page from the start positions of the text runs (five peaks).
  page 7     "सफाई एवं खाद्य निरीक्षको को आंवटित वार्डो का विवरण": the city health officer, the zonal sanitary officer and the chief
             inspectors (each in charge of a vehicle depot), then each inspector with mobile and the wards allotted.
Records: inspectors and supervisors at level "ward" (one per person, wards = the wards in their charge, area_regional = the
localities of a one-ward record); the page-7 heads at level "body". The councillors are not read here (the councillors task has
them). Names are Hindi: name and name_regional carry the same text. Record ids: dept:ward_meerut:<post slug>:<mobile or n>.
"""
import collections
import re

import provenance
from dforms import _esw, _ward, _ward_kd as kd

METHOD = "pdf text (pypdf) + Kruti Dev map"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward_meerut"
BODY, LGD, STATE, DISTRICT = "Meerut Nagar Nigam", "248964", "UP", "Meerut"
URL = "https://meerutnagarnigam.com/downloads/Wardwise-Sanitary-Inspector-And-Safai-Supervisor-List.pdf"
PHONE = re.compile(r"(?<!\d)(\d[\d ]{8,11}\d)(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-sanitation", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _runs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def ward_rows(page, at=None):
    """[(ward, [text of column 1..4])] of one ward-table page, or [] when the page is not one. at: a list; when given, it gets
    each row's first line (1-based in page.splitlines())."""
    lines = page.splitlines()
    starts = [ln for ln in lines if re.match(r"\s*\d{1,3}\s{2,}\S", ln)]
    c = collections.Counter(x for ln in lines for x, _ in _runs(ln))
    peaks = []
    for x, n in sorted(c.items()):
        if n >= max(3, len(starts) * 0.4):
            if peaks and x - peaks[-1] <= 3:
                continue
            peaks.append(x)
    if len(peaks) != 5 or len(starts) < 3:
        return []
    out, cur = [], None
    for lno, ln in enumerate(lines, 1):
        m = re.match(r"\s*(\d{1,3})\s{2,}\S", ln)
        if m and abs(m.start(1) - peaks[0]) <= 3:
            cur = (m.group(1), [[] for _ in range(4)])
            out.append(cur)
            if at is not None:
                at.append(lno)
            ln = ln[:m.start(1)] + " " * len(m.group(1)) + ln[m.end(1):]
        if cur is None:
            provenance.skip_line(ln, 'skip: cur is None')
            continue
        for x, t in _runs(ln):
            col = max(i for i, p in enumerate(peaks) if p <= x + 2) if x + 2 >= peaks[0] else 0
            if col >= 1:
                cur[1][col - 1].append(t)
    return [(w, [" ".join(c) for c in cols]) for w, cols in out]


def person(text):
    """(name, post, phone) from one cell's Kruti Dev text: the phone numbers, the post words, the rest is the name."""
    phones = [p.replace(" ", "") for p in PHONE.findall(text)]
    t = PHONE.sub(" ", text)
    u = _esw.clean(kd.convert(t))
    post = None
    for w in ("कार्यवाहक सफाई नायक", "सफाई नायक"):
        if w in u:
            post, u = w, u.replace(w, " ")
    return _esw.clean(u).strip(" -,]"), post, ", ".join(phones)


def allotment(page):
    """Page 7: [(name, post, phone, wards, note, line no)] of the heads and the inspectors' ward allotments (line no 1-based in
    the page text)."""
    u = kd.convert(page)
    out = []
    for lno, ln in enumerate(u.splitlines(), 1):
        ln = _esw.clean(ln)
        m = re.match(r"(?:\d+\s*-\s*)?(श्री[^\]]+|डा\S*\s*[^\]]+)\]\s*([^-\d]+?)\s*-+\s*(\d{10})\s*-?\s*(.*)$", ln)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip(), m.group(3), [], m.group(4).strip(" -"), lno))
            continue
        m = re.match(r"\d+\s+(श्री.+?)\s+(\d{10})\s+(.+)$", ln)
        if m:
            out.append((m.group(1).strip(), "सफाई एवं खाद्य निरीक्षक", m.group(2), _ward.wards_of(m.group(3).replace("]", ",")), "",
                        lno))
    return out


POSTS = {"सफाई एवं खाद्य निरीक्षक": "Sanitary and Food Inspector", "सफाई नायक": "Sanitation Supervisor (Safai Nayak)",
         "कार्यवाहक सफाई नायक": "Acting Sanitation Supervisor (Safai Nayak)", "नगर स्वास्थ्य अधिकारी": "City Health Officer",
         "जोनल सेनटरी अधिकारी": "Zonal Sanitary Officer", "मुख्य सफाई एंव खाद्य निरीक्षक": "Chief Sanitary and Food Inspector",
         "मुख्य सफाई एवं खाद्य निरीक्षक": "Chief Sanitary and Food Inspector"}


def parse(pages, p):
    people = {}  # (post, phone or name) -> {...}
    localities = {}
    for pn, pg in enumerate(pages, 1):
        at = []
        for (ward, cols), lno in zip(ward_rows(pg, at), at):
            w = str(int(ward))
            localities[w] = _esw.clean(kd.convert(cols[3]))
            for ci, default in ((1, "सफाई एवं खाद्य निरीक्षक"), (2, "सफाई नायक")):
                name, post, phone = person(cols[ci])
                if not (name or phone):
                    continue
                post = post or default
                g = people.setdefault((post, phone or name), {"name": name, "post": post, "phone": phone, "wards": [], "at": []})
                if w not in g["wards"]:
                    g["wards"].append(w)
                g["at"].append({"page": pn, "line": lno, "col": ci + 1})
    heads = []
    for pn, pg in enumerate(pages, 1):
        raw = pg.splitlines()
        for name, post, phone, wards, note, lno in allotment(pg):
            pos = provenance.line_pos(pn, lno, raw[lno - 1] if lno <= len(raw) else "")
            if wards:
                g = people.setdefault(("सफाई एवं खाद्य निरीक्षक", phone), {"name": name, "post": "सफाई एवं खाद्य निरीक्षक",
                                                                           "phone": phone, "wards": [], "at": []})
                g["wards"] += [x for x in wards if x not in g["wards"]]
                g["at"].append({"page": pn, "line": lno})
            else:
                heads.append((name, post, phone, note, pos))
    seen, recs = set(), []
    for g in people.values():
        g["wards"].sort(key=lambda x: int(re.match(r"\d+", x).group(0)))
        en = POSTS.get(g["post"], g["post"])
        area = ("Ward " if len(g["wards"]) == 1 else "Wards ") + ", ".join(g["wards"])
        recs.append(_ward.record(MODULE, f"{_esw.slug(en)}:{g['phone'].split(',')[0] or len(recs)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area=area,
                                 area_regional=localities.get(g["wards"][0]) if len(g["wards"]) == 1 else None, post=en,
                                 post_regional=g["post"], name=g["name"], name_regional=g["name"], phone=g["phone"],
                                 wards=g["wards"], wing="sanitation", source=p["url"],
                                 src_pos={"rows": g["at"], "note": "one person summed over these ward rows (col: table column)"}))
    for name, post, phone, note, pos in heads:
        en = POSTS.get(post, post)
        recs.append(_ward.record(MODULE, f"{_esw.slug(en)}:{phone}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT,
                                 level="body", area=BODY, post=en, post_regional=post, name=name, name_regional=name, phone=phone,
                                 wing="health" if "स्वास्थ्य" in post else "sanitation", note=note or None, source=p["url"],
                                 src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "wardwise-sanitation", r.content, "pdf")]
    pages = _esw.pdf_pages(r.content)
    if not pages:
        return [], files, "not a readable pdf"
    recs = parse(pages, p)
    return recs, files, "" if recs else "no ward table"
