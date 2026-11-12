"""Maharashtra municipal corporation results, January 2026 (Government e-Gazette, egazzete.mahaonline.gov.in), read by OCR.

Each corporation's commissioner published the ward winners as a Part-II extraordinary notice (Central Section, 19 Jan 2026).
The e-Gazette has no file links: the search page (ASP.NET) lists notices, and "View" posts the form back and answers with the
PDF. So a queue item names the notice (gazette date, its listed text) and a page range; fetch() searches that one day, finds
the row, posts it back and reads the pages.
The PDFs have a text layer whose Devanagari breaks (vowel signs doubled or dropped, conjuncts lost), and every corporation's
table has its own columns (ward, seat, reservation, name, address, party, votes, in varying order). The grid comes from the
drawn cell borders (cforms/gj.py), every cell is read by Tesseract (mar), and each column's role is found from what its
cells hold (seat letters, reservation words, party names, vote counts). Ward and vote numbers come from the text layer when
it has them (digits survive), else from OCR.
One queue item = one notice and up to 6 pages. The site answers only from India.
The other corporations published in their division's "Part -1 A" extraordinary supplement of 19 Jan 2026 (payload division
3 Pune, 4 Nashik, 7 Aurangabad; section "3"), several corporations in one notice: payload "first"/"last" give the pages of
one corporation and "lgd_code" its LGD body; "store" keeps the file in the bucket when the item does not start at page 1.
Notices of Nagpur and Amravati divisions have no ruled table: cforms/mh_gztext.py reads them from the text layer.
"""
import collections
import hashlib
import os
import re
import shutil
import tempfile

from cforms import gj

SEARCH = "https://egazzete.mahaonline.gov.in/Forms/GazetteSearch.aspx"
DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
PARTY = ((r"उद्ध?व|ठाकरे", "SS(UBT)"), (r"शरद", "NCP(SP)"), (r"राष्ट्रवादी|राष्ट्रवादि", "NCP"),
         (r"जनता\s*पा", "BJP"), (r"भारतीय\s*जनता", "BJP"), (r"शिवसेना|शिवसेन", "SHS"), (r"नवनिर्माण|मनसे", "MNS"),
         (r"काँग्रेस|कॉंग्रेस|कॉग्रेस|काॅंग्रेस|काँग्रस", "INC"), (r"मजलिस|मजलीस|एमआयएम|इत्तेहाद", "AIMIM"),
         (r"वंचित", "VBA"), (r"समाजवादी", "SP"), (r"बहुजन\s*समाज", "BSP"), (r"अपक्ष", "Independent"))
RESV = re.compile(r"सर्वसाधारण|सर्व\s*साधारण|अनुसूचित|अनुसुचित|मागास|महिला|प्रवर्ग|स्त्री")
SEAT = re.compile(r"^\(?\s*[0-9०-९]*\s*[-.]?\s*([अबकडइ])\s*\)?$")
SHORT = re.compile(r"[\s()0-9०-९.,\-–अबकडइ]*[0-9०-९अबकडइ][\s()0-9०-९.,\-–अबकडइ]*")
HEAD = re.compile(r"नाव|सदस्य|उमेदवार|क्रमांक|पक्ष|आरक्षण|मते$")


def tools():
    return gj.tools("mar")


def num(t):
    m = re.search(r"\d+", (t or "").translate(DIGITS))
    return str(int(m.group(0))) if m else ""


def party_of(t):
    for k, v in PARTY:
        if re.search(k, t or ""):
            return v
    return ""


def reservation(t):
    t = t or ""
    if "अनुसूचित" in t or "अनुसुचित" in t:
        cat = "ST" if re.search(r"जमात", t) else "SC"
    elif "मागास" in t or "प्रवर्ग" in t:
        cat = "OBC"
    elif "सर्व" in t or "साधारण" in t:
        cat = "General"
    else:
        cat = ""
    woman = "महिला" in t or "स्त्री" in t
    return (cat + " woman") if (cat and woman) else (cat or ("Woman" if woman else ""))


def table(hs, vs):
    """Rows of the page's main table: the most common number of columns among the bands between horizontal borders."""
    ys = sorted({round(h[0], 1) for h in hs})
    counts = collections.Counter()
    for a, b in zip(ys, ys[1:]):
        if b - a < 5:
            continue
        xs = []
        for x in sorted(v[0] for v in vs if v[1] - 1 <= (a + b) / 2 <= v[2] + 1):
            if not xs or x - xs[-1] > 3:
                xs.append(x)
        if len(xs) >= 4:
            counts[len(xs) - 1] += 1
    if not counts:
        return []
    n = counts.most_common(1)[0][0]
    rows, _ = gj.grid_rows(hs, vs, n, n)        # cut at borders across the last column (votes or party: never merged)
    return rows


def roles(cells):
    """Column roles from the read cells of all rows: {role: column}. cells = [{col: text}]."""
    ncol = max((max(c) for c in cells if c), default=0)
    score = {}
    for c in range(1, ncol + 1):
        vals = [r.get(c, "") for r in cells]
        filled = [v for v in vals if v.strip()] or [""]
        k = len(filled)
        nums = [int(num(v)) for v in filled if re.fullmatch(r"[\s(]*[0-9०-९,]+[\s.)]*", v)]
        score[c] = {
            "seat": sum(bool(SEAT.match(v.strip())) or bool(re.fullmatch(r"[0-9०-९]+\s*-\s*[अबकडइ]", v.strip()))
                        for v in filled) / k,
            "reservation": sum(bool(RESV.search(v)) for v in filled) / k,
            "party": sum(bool(party_of(v)) for v in filled) / k,
            "number": len(nums) / k,
            "big": (sorted(nums)[len(nums) // 2] if nums else 0),
            "digits": sum(bool(re.search(r"[0-9०-९]", v)) for v in filled) / k,
            "len": sum(len(v.split()) for v in filled) / k,
            "fill": len([v for v in vals if v.strip()]) / max(1, len(vals)),
        }
    out = {}

    def take(role, key, cond):
        best = [c for c in score if c not in out.values() and cond(score[c])]
        if best:
            out[role] = max(best, key=lambda c: score[c][key])
    take("votes", "big", lambda s: s["number"] > 0.6 and s["big"] >= 200)
    take("party", "party", lambda s: s["party"] > 0.4)
    take("seat", "seat", lambda s: s["seat"] > 0.5)
    take("reservation", "reservation", lambda s: s["reservation"] > 0.4)
    nums = [c for c in score if c not in out.values() and score[c]["number"] > 0.6]
    if nums:                                  # serial first, ward next (the ward cell spans its seats: fewer filled)
        nums.sort()
        if len(nums) >= 2:
            out["serial"], out["ward"] = nums[0], nums[1]
        else:       # one number column: the ward, unless the seat cells carry the ward ("6-अ")
            seat_has_ward = "seat" in out and score[out["seat"]]["digits"] > 0.5
            out["serial" if seat_has_ward else "ward"] = nums[0]
    rest = [c for c in score if c not in out.values() and score[c]["len"] >= 1.5]
    if rest:
        addr = [c for c in rest if score[c]["digits"] > 0.4 and score[c]["len"] > 3]
        if addr:
            out["address"] = max(addr, key=lambda c: score[c]["len"])
        names = [c for c in rest if c != out.get("address")]
        if names:
            out["name"] = min(names, key=lambda c: (score[c]["digits"], c))
    return out


def get_pdf(p, get):
    """Search the gazette's day, find the notice by its listed text, post its "View" back: the PDF bytes or None."""
    from bs4 import BeautifulSoup

    def form(html):
        soup = BeautifulSoup(html, "lxml")
        data = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
        return soup, data
    r = get(SEARCH)
    if r is None:
        return None, "no answer"
    soup, data = form(r.text)
    day = p["gazette_date"]
    data.update({"ctl00$CPH$ddldivision": p.get("division", "1"), "ctl00$CPH$ddlSection": p.get("section", "17"),
                 "ctl00$CPH$ddlGazetteType": p.get("gazette_type", "1"), "ctl00$CPH$txtfromDate": day,
                 "ctl00$CPH$txtToDate": day, "ctl00$CPH$btnSearch": "Search"})
    r = get(SEARCH, "POST", data)
    if r is None:
        return None, "search did not answer"
    soup, data = form(r.text)
    want = gj.norm(p["match"])
    target, nth = None, int(p.get("nth", 0) or 0)      # nth: the day lists the same text more than once
    for tr in soup.find_all("tr"):
        a = tr.find("a", href=re.compile("doPostBack"))
        tds = [gj.norm(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if a and len(tds) > 6 and (tds[6] == want or tds[6].startswith(want[:80])):
            if nth == 0:
                target = a["href"].split("'")[1]
                break
            nth -= 1
    if not target:
        return None, "notice not in the search result"
    data.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
    for sel in soup.find_all("select"):
        o = sel.find("option", selected=True)
        data[sel["name"]] = o.get("value") if o else ""
    for inp in soup.find_all("input", type="text"):
        data[inp["name"]] = inp.get("value", "")
    r = get(SEARCH, "POST", data)
    if r is None or not r.content.startswith(b"%PDF"):
        return None, "no pdf"
    return r.content, ""


def parse(pdf, p, use_ocr=True):
    from pypdf import PdfReader
    import concurrent.futures
    reader = PdfReader(pdf)
    first, last = int(p.get("first", 1)), min(int(p.get("last", 1)), len(reader.pages))
    tmp = tempfile.mkdtemp()
    pages = {}
    for pg in range(first, last + 1):
        ws = gj.words(pdf, pg)
        hs, vs = gj.drawn_lines(reader, pg - 1)
        pages[pg] = (ws, hs, table(hs, vs))

    def read(pg):
        ws, hs, rows = pages[pg]
        boxes = [(c[0] + 1.2, a + 1.2, c[1] - 1.2, b - 1.2) for cols, a, b in rows for _, c in sorted(cols.items())]
        texts = gj.ocr_boxes(pdf, pg, boxes, tmp, "mar") if use_ocr else [gj.box_text(ws, *b) for b in boxes]
        out, i = [], 0
        for cols, a, b in rows:
            row = {}
            for j, c in enumerate(sorted(cols)):
                lay = gj.norm(gj.box_text(ws, *boxes[i + j]))
                # numbers and seat codes: the text layer (OCR misreads lone digits and letters); words: OCR
                row[c] = lay if SHORT.fullmatch(lay) else gj.clean_cell(texts[i + j])
            out.append(row)
            i += len(cols)
        return out
    with concurrent.futures.ThreadPoolExecutor(max(1, min(len(pages), os.cpu_count() or 1))) as ex:
        cells = dict(zip(sorted(pages), ex.map(read, sorted(pages))))
    data = [(pg, k, row) for pg in sorted(pages) for k, row in enumerate(cells[pg])
            if row and not any(HEAD.search(v) for v in row.values()) and not all(re.fullmatch(r"\W*[0-9०-९]*\W*", v) for v in row.values())]
    role = roles([row for _, _, row in data])
    recs = []
    if "name" not in role:
        shutil.rmtree(tmp, ignore_errors=True)
        return recs
    last_ward, ward_n = "", 0
    for pg, k, row in data:
        ws, hs, rows = pages[pg]
        cols, a, b = rows[k]

        def layer(r, merged=False):
            if r not in role:
                return ""
            c = cols[role[r]]
            band = gj.cell_of(role[r], hs, (a + b) / 2, cols) if merged else (a, b)
            return gj.box_text(ws, c[0], band[0], c[1], band[1])
        name = row.get(role["name"], "")
        if not name or len(name) < 3:
            continue
        seat_t = row.get(role.get("seat"), "") if "seat" in role else ""
        m = re.search(r"([अबकडइ])\s*\)?\s*$", seat_t) or re.search(r"([अबकडइ])\s*\)?\s*$", gj.norm(layer("seat")))
        seat = m.group(1) if m else ""
        if not re.search(r"[0-9०-९]", seat_t):
            seat_t = gj.norm(layer("seat")) or seat_t
        ward = num(layer("ward", merged=True)) or num(row.get(role.get("ward"), "")) if "ward" in role else ""
        if not ward and re.search(r"[0-9०-९]", seat_t):
            ward = num(seat_t)
        ward = ward or last_ward
        if ward in (p.get("skip_wards") or []):
            last_ward = ward
            continue
        ward_n = ward_n + 1 if ward == last_ward else 1
        last_ward = ward
        seat_by_order = not seat and "seat" in role and bool(ward)
        if seat_by_order:
            seat = "अबकडइ"[min(ward_n, 5) - 1]       # seats are listed अ, ब, क, ड within a ward
        votes = num(layer("votes")) or num(row.get(role.get("votes"), "")) if "votes" in role else ""
        party_local = row.get(role.get("party"), "") if "party" in role else ""
        resv_t = row.get(role.get("reservation"), "") if "reservation" in role else ""
        alias = ""
        mm = re.match(r"^(.*?)\s*\(([^()]+)\)?\s*$", name)
        if mm and mm.group(1) and not mm.group(2).startswith(("उद्ध", "शरद")):
            name, alias = mm.group(1).strip(" -–"), mm.group(2).strip()
        rec = {"type": "councillor", "state": "MH", "body": p.get("body_local") or p.get("body", ""),
               "body_local": p.get("body_local", ""), "body_en": p.get("body", ""), "body_type": "Municipal Corporation",
               "district": p.get("district", ""), "ward_no": ward, "seat": seat, "reservation": reservation(resv_t),
               "reservation_local": resv_t, "name": name, "party": party_of(party_local) or party_local,
               "party_local": party_local, "votes": int(votes) if votes else None,
               "address": row.get(role.get("address"), "") if "address" in role else "",
               "election": "Maharashtra 2026", "url": p["url"], "gazette": p.get("match", ""), "page": pg,
               "read": "ocr+text layer" if use_ocr else "text layer"}
        if seat_by_order:
            rec["seat_from"] = "row order"
        if p.get("lgd_code"):
            rec["lgd_code"] = p["lgd_code"]
        if p.get("corrigendum"):
            rec["corrigendum"] = True
        if alias:
            rec["name_alias"] = alias
        serial = num(row.get(role.get("serial"), "")) if "serial" in role else ""
        recs.append((f"councillor:MH:{p.get('slug', 'x')}:{ward or 'x'}" + (f"-{seat}" if seat else (f"-s{serial}" if not ward else "")), rec))
    shutil.rmtree(tmp, ignore_errors=True)
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "tesseract not available"
    content, why = get_pdf(p, get)
    if content is None:
        return [], [], why
    key = hashlib.sha1((p["gazette_date"] + p["match"]).encode()).hexdigest()[:12]
    files = [(f"councillors/MH/{key}.pdf", content, "application/pdf")] if int(p.get("first", 1)) == 1 or p.get("store") else []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        recs = parse(pdf, p)
    return recs, files, "" if recs else "no members read"
