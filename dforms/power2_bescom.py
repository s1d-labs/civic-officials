"""Karnataka: BESCOM (Bengaluru) "Field Officers Contact Details", bescom.karnataka.gov.in (India only: the site does not answer
from Germany; sample fetched from India 2026-11-11, Last-Modified 2025-09-11; the archive copy of the workbook is not readable).
One workbook: /uploads/media_to_upload1757575623.xlsx ("Details of Respective area engineers of BESCOM"), linked from the home page
menu "Field Officers Contact Details". 7 sheets, one per district group (Bengaluru urban, Bengaluru rural, Ramanagar, Kolar &
Chikkaballapura, Tumakuru, Davanagere & Chitradurga; Table 7 continues Table 6 without a header). One row per O&M unit (section),
the upper offices repeated on every row:
  B zone | C Chief Engineer | D circle | E Superintending Engineer | F division | G Executive Engineer | H sub-division |
  I Assistant Executive Engineer | J O&M unit | K Assistant Engineer / Junior Engineer(s) | (L service station number) | areas.
Each officer cell is free text "Sri. Name 9449844643 mail@bescom.co.in" (numbers and e-mails are sometimes broken over lines);
the K cell holds one or more people ("AE Sri. X 94... JE Sri. Y 94..."): one record per person. About 536 sections, ~170
sub-divisions, ~55 divisions, ~15 circles, 4 zones (BMAZ North, BMAZ South, BRAZ, CTAZ). Names and phones on every level.
Records: dept:power2_bescom:<level>:<path>[:<post>:<name>]; the section record keeps the areas it serves ("areas").
"""
import re
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from dforms._power import Out, clean, email, phone, raw

MODULE = "power2_bescom"
URL = "https://bescom.karnataka.gov.in/uploads/media_to_upload1757575623.xlsx"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
DESIG = re.compile(r"\(?\b(Assistant Executive Engineer|Assistant Engineer|Junior Engineer|Executive Engineer|AEE|EE|AE|JE|"
                   r"A\.E\.?|J\.E\.?|SO|inch|I/?C)\b\)?/?", re.I)
EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def sheets(content):
    """[(sheet name, [{column letter: text}])] of every sheet, read with the standard library."""
    z = zipfile.ZipFile(BytesIO(content))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = ["".join(t.text or "" for t in si.iter(NS + "t")) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si")]
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    out = []
    for sh in ET.fromstring(z.read("xl/workbook.xml")).iter(NS + "sheet"):
        t = rels[sh.get(RNS + "id")].lstrip("/")
        t = t if t.startswith("xl/") else "xl/" + t
        rows = []
        for r in ET.fromstring(z.read(t)).find(NS + "sheetData"):
            d = {}
            for c in r.findall(NS + "c"):
                col = re.match(r"[A-Z]+", c.get("r", "")).group()
                if c.get("t") == "inlineStr":
                    d[col] = "".join(x.text or "" for x in c.iter(NS + "t"))
                    continue
                v = c.find(NS + "v")
                if v is not None and v.text is not None:
                    d[col] = ss[int(v.text)] if c.get("t") == "s" else v.text
            rows.append({k: v for k, v in d.items() if v and v.strip()})
        out.append((sh.get("name"), rows))
    return out


def _emails(text):
    """E-mails and the text without them. Mends addresses the sheet breaks over lines ("bescom.co\\n.in", "besc\\nom.co.in",
    "work @gmail.com", "bescom.co/.in")."""
    t = re.sub(r"\s*@\s*", "@", text.replace("/.", "."))
    found, rest, last = [], [], 0
    for m in re.finditer(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)(?=(\s+\.?[a-z]+(?:\.[a-z]+)*(?![\w@.]))?)", t):
        dom, end = m.group(2), m.end(2)
        nxt = (m.group(3) or "").strip()
        if nxt and (nxt.startswith(".") or not re.search(r"\.(in|com|org|net)$", dom)):
            dom, end = dom + nxt, m.end(2) + len(m.group(3))
        a = (m.group(1) + "@" + dom.strip(".")).lower()
        if EMAIL_RX.fullmatch(a):
            found.append(a)
            rest.append(t[last:m.start()])
            last = end
    rest.append(t[last:])
    return list(dict.fromkeys(found)), " ".join(rest)


def _phones(text):
    """Phone numbers and the text without them. Joins a mobile broken over a line ("94498\\n44988")."""
    t = re.sub(r"(\d)(?=[A-Za-z])", r"\1 ", text)
    toks = re.findall(r"\d[\d-]*\d|\d|[^\d]+", t)
    nums, rest, i = [], [], 0
    while i < len(toks):
        tok = toks[i]
        if re.fullmatch(r"\d[\d-]*", tok):
            digits = tok.replace("-", "")
            # glue "94482 79094" / "94498\n44988" (a 10-digit mobile in two parts) and "08193 229533" (STD code + number)
            if i + 2 < len(toks) and re.fullmatch(r"\s+", toks[i + 1]) and re.fullmatch(r"\d+", toks[i + 2]):
                nxt = toks[i + 2]
                if (len(digits) < 10 and len(digits + nxt) == 10 and digits[0] in "6789") or \
                        (digits.startswith("0") and 3 <= len(digits) <= 5 and len(digits + nxt) in (10, 11, 12)):
                    tok = f"{tok}-{nxt}" if digits.startswith("0") else digits + nxt
                    digits = tok.replace("-", "")
                    i += 2
            if len(digits) >= 6:
                nums.append(tok)
                rest.append(" ")
            else:
                rest.append(tok)
        else:
            rest.append(tok)
        i += 1
    return list(dict.fromkeys(nums)), "".join(rest)


def _name(text):
    t = DESIG.sub(" ", text)
    t = re.sub(r"[()/|:,]+", " ", t)
    t = re.sub(r"\b(Sri|Smt|Shri)\b\.?", lambda m: m.group(1) + ".", t, flags=re.I)
    t = clean(re.sub(r"\s+", " ", t).strip(" .-"))
    # a piece of a broken e-mail address left before the title ("aeaero Sri. Jayaram")
    t = re.sub(r"^(?:[a-z0-9_.]+\s+)+(?=(Sri|Smt|Shri)\.)", "", t or "") or None
    if not t or not re.search(r"[A-Za-z]{2,}", t) or re.fullmatch(r"(Sri|Smt|Shri)\.?", t, re.I):
        return None
    return t


def people(cell):
    """[(post or None, name, phones, emails)] of one cell. A person ends after their numbers and e-mails, when the next word
    starts (so "AE Sri. A 94... a@b.in JE Sri. B 94..." gives two people)."""
    if not clean(cell):
        return []
    mails, t = _emails(cell)
    t = re.sub(r"(\d)(?=[A-Za-z])", r"\1 ", t)
    # split into chunks: text up to and including a run of numbers
    chunks = re.findall(r"(.*?(?:\d[\d\s/,-]{4,}\d)+[\s/,;-]*|.+$)", t, re.S)
    out = []
    for ch in chunks:
        if not ch.strip():
            continue
        nums, rest = _phones(ch)
        m = re.search(r"\b(AEE|AE|JE|EE|SO)\b", rest)
        post = m.group(1).upper() if m else None
        nm = _name(rest)
        if not nm and not nums:
            continue
        if not nm and out:
            out[-1][2].extend(nums)
            continue
        out.append([post, nm, nums, []])
    if not out:
        return []
    # e-mails: give each to the person whose post or name its local part names, else to the first person
    for a in mails:
        local = a.split("@")[0].lower()
        who = next((p for p in out if p[0] and local.startswith(p[0].lower())), out[0])
        who[3].append(a)
    return [(p, n, nums, ms) for p, n, nums, ms in out]


def _area(s):
    return clean(re.sub(r"\s+", " ", s or "")) or None


def parse(content, url=URL):
    out = Out(MODULE, "KA", url, discom="BESCOM", last_updated="2025-09-11")
    seen = set()
    head = None
    district = None
    for sname, rows in sheets(content):
        for r in rows:
            a = (r.get("A") or "").strip()
            if a.lower().startswith("district"):
                district = clean(a.split(":", 1)[-1])
                continue
            if r.get("J") == "O&M Unit" or r.get("M") == "Areas" or r.get("L") == "Areas":
                head = {v.strip().lower(): k for k, v in r.items()}
                continue
            if not re.fullmatch(r"\d+", a) or not r.get("J") or r.get("B", "").strip() == "2":
                continue
            zone, circle, div, sub, unit = (_area(r.get(c)) for c in "BDFHJ")
            if not unit:
                continue
            area_col = (head or {}).get("areas", "L")
            ss_col = (head or {}).get("service station number")
            par = {"zone": zone}
            levels = (("zone", zone, "C", "Chief Engineer", {}),
                      ("circle", circle, "E", "Superintending Engineer", {"zone": zone}),
                      ("division", div, "G", "Executive Engineer", {"zone": zone, "circle": circle}),
                      ("subdivision", sub, "I", "Assistant Executive Engineer", {"zone": zone, "circle": circle, "division": div}))
            path = []
            for lvl, name, col, post, parents in levels:
                path.append(name or "")
                key = (lvl, tuple(path))
                if not name or key in seen:
                    continue
                seen.add(key)
                ppl = people(r.get(col, "")) or [(None, None, [], [])]
                p0 = ppl[0]
                out.add(f"{lvl}:{':'.join(path)}", lvl, name, post=post, name=p0[1], phone_=phone(*p0[2]),
                        email_=email(" ".join(p0[3])), parents=parents, district=district)
            par = {"zone": zone, "circle": circle, "division": div, "subdivision": sub}
            ss = phone(r.get(ss_col)) if ss_col and ss_col != area_col else None
            areas = clean(r.get(area_col)) if area_col not in "BCDEFGHIJK" else None
            ppl = people(r.get("K", "")) or [(None, None, [], [])]
            for post, nm, nums, mails in ppl:
                post = {"AE": "Assistant Engineer", "JE": "Junior Engineer", "SO": "Section Officer"}.get(post or "",
                                                                                                          "Assistant Engineer / Junior Engineer")
                out.add(f"section:{':'.join(path)}:{unit}:{post}:{nm or ''}", "section", unit, post=post, name=nm,
                        phone_=phone(*nums), email_=email(" ".join(mails)), parents=par, district=district,
                        areas=areas, service_station_phone=ss)
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw(MODULE, "field-officers", r.content, "xlsx")]
    try:
        recs = parse(r.content, url)
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        return [], files, f"not a readable xlsx: {type(e).__name__}"
    return recs, files, "" if recs else "no rows"
