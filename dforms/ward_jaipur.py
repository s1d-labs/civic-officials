"""Nagar Nigam Jaipur (jaipurmc.org): the zone officers of its zones (Deputy Commissioner, Executive Engineer, Revenue Officer of
each zone: Malviya Nagar, Sanganer, Adarsh Nagar, Muralipura, Jagatpura, Jhalana, Kishanpole, Vidhyadhar Nagar, Mansarovar,
Jhotwara, Vaishali Nagar, Civil Lines, Hawamahal-Amer ...). One PDF, the "Administrative Directory" (/PDF/Others/jp_AdminContList.pdf,
shown on the site through MstPdfViewer.aspx; answers from Germany; live sample 2026-11-11, not in archive.s1d.me), 6 pages, set in
Kruti Dev (converted with dforms/_ward_kd.py). Columns: क्रमांक | नाम | पद नाम | पी.बी.एक्स | कार्यालय | निवास | मोबाइल-1 | मोबाइल-2;
one row = one block of lines between blank lines (cells wrap above and below the row number); in a block the post that names a
zone ("उपायुक्त मालवीय नगर जोन") and the name (श्री / श्रीमती / सुश्री + up to 4 words) are found by their words, the phones by
their digits. Only posts that name a zone (जोन) are read. The PDF does not list the 150 wards of
each zone (no "wards" key). Names and posts are Hindi: name and name_regional carry the same text; post is English, post_regional
as written. Reads pdftotext (poppler) text, else pypdf. Record ids: dept:ward_jaipur:<zone slug>:<post slug>:<n>.
"""
import re

from dforms import _esw, _ward, _ward_kd as kd

MODULE = "ward_jaipur"
BODY, LGD, STATE, DISTRICT = "Nagar Nigam Jaipur", "303088", "RJ", "Jaipur"
URL = "https://jaipurmc.org/PDF/Others/jp_AdminContList.pdf"
ZONES = {"मालवीय नगर": "Malviya Nagar", "सांगानेर": "Sanganer", "आदर्श नगर": "Adarsh Nagar", "मुरलीपुरा": "Muralipura",
         "जगतपुरा": "Jagatpura", "झालाना": "Jhalana", "किशनपोल": "Kishanpole", "विघाधर नगर": "Vidhyadhar Nagar",
         "विद्याधर नगर": "Vidhyadhar Nagar", "मानसरोवर": "Mansarovar", "झोटवाडा": "Jhotwara", "वैशाली नगर": "Vaishali Nagar",
         "सिविल लाईन": "Civil Lines", "हवामहल-आमेर": "Hawamahal-Amer", "हवामहल": "Hawamahal", "आमेर": "Amer"}
POSTS = (("उपायु", "Deputy Commissioner"), ("अधिशाषी अभियं", "Executive Engineer"), ("सहायक अभियं", "Assistant Engineer"),
         ("कनिष्ठ अभियं", "Junior Engineer"), ("राजस्व अधिकारी", "Revenue Officer"), ("स्वास्थ्य निरीक्षक", "Health Inspector"))
PHONE = re.compile(r"(?<![\d/])([6-9]\d{9}|0141[-\s]?\d{7}|2\d{6})(?![\d/])")


def items(get=None):
    return [{"key": f"{MODULE}-admin-directory", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def _runs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def blocks(page):
    """[(Kruti Dev text of the block, [phones])] of one page: one row = the lines between blank lines (after the heading line)."""
    lines = page.splitlines()
    hi = next((i for i, ln in enumerate(lines) if re.search(r"\bin uke\b", ln)), None)
    if hi is None:
        return []
    out, cur = [], []
    for ln in lines[hi + 1:] + [""]:
        if not ln.strip() or re.search(r"\bin uke\b", ln):
            if cur:
                out.append(cur)
            cur = []
            continue
        cur.append(ln)
    rows = []
    for b in out:
        phones = [x for ln in b for x in PHONE.findall(ln)]
        text = " ".join(t for ln in b for _, t in _runs(ln)
                        if not (re.fullmatch(r"[\d\s/@,.-]+", t) or "@" in t or re.search(r"\.(GOV|IN)\b|RAJASTHAN|^\.?IN$|^N,?$", t)))
        rows.append((text, phones))
    return rows


NAME = re.compile(r"(?:श्रीमती|श्री|सुश्री|डॉ0?|डा0)\s+(?:(?!उपायु|अधिशाषी|राजस्व|सहायक|कनिष्ठ|आर\.|आई\.)[^\s]+\s*){1,4}")


def parse(pages, p):
    seen, recs, n = set(), [], {}
    for pg in pages:
        for text_kd, phones in blocks(pg):
            text = _ward.hi_norm(kd.convert(text_kd)).replace("ुु", "ु").replace("ु ु", "ु")
            m = re.search(r"(उपायु\S*(?:\s+त(?=\s))?|अधिशाषी\s+अभियं?\S*|सहायक\s+अभियं?\S*|कनिष्ठ\s+अभियं?\S*|राजस्व\s+अधिकारी)\s+([^\s].{1,20}?)\s+जोन", text)
            if not m:
                continue
            post = _esw.clean(m.group(0))
            zone = next((en for hi, en in sorted(ZONES.items(), key=lambda kv: -len(kv[0])) if hi in m.group(2)), None)
            if not zone:
                continue
            nm = NAME.search(text)
            name = _esw.clean(re.sub(r"[\d½¼]+", " ", nm.group(0))) if nm else ""
            en = next((e for k, e in POSTS if k in post), None) or _ward.hi_post(post)
            key = f"{_esw.slug(zone)}:{_esw.slug(en)}"
            n[key] = n.get(key, 0) + 1
            recs.append(_ward.record(MODULE, f"{key}:{n[key]}", seen, body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="zone",
                                     area=f"{zone} Zone", zone=f"{zone} Zone", post=en, post_regional=post, name=name,
                                     name_regional=name or None, phone=", ".join(dict.fromkeys(phones)),
                                     vacant=None if name else True, source=p["url"]))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "admin-directory", r.content, "pdf")]
    recs = parse(_ward.layout_pages(r.content), p)
    return recs, files, "" if recs else "no zone posts (pdftotext missing?)"
