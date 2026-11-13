"""Madhya Pradesh district police sites (<district>.mppolice.gov.in, WordPress, one theme for all 55 units): the page
/officers-list/ is a TablePress table of officers with names (SP, ASP, CSP / SDOP, thana prabhari, chowki prabhari, branch
heads) and, on most districts, CUG and mobile numbers; /contact/ is a second table on some units (Bhopal, Indore: names on
officers-list, numbers on contact). Columns differ by district and are in Hindi or English ("नाम अधिकारी | पद / थाना | कार्यालय |
सीयूजी नम्बर | मोबाइल नम्बर", "पद | अधिकारी का नाम | सीयूजी | मोबाइल नं", or no header: post | name). Columns are typed by
their content: number columns are phones (all numbers kept: office, CUG, mobile), the column with most honorifics (श्री, निरी.,
उनि., Shri, Smt ...) is the name, the other text column is the post / office. Rows with one text cell are section headings
(अनुभाग, ZONE - I) and become the subdivision / zone of the rows below. Some units show "[table “1” not found /]" (no data).
The police_mp reader (station KML, no names) stays; this one adds the officers. Works from outside India.
One queue item = one page. Record id dept:police2s_mp:<district>:<slug of post>."""
import re

from bs4 import BeautifulSoup

from dforms._police import ascii_digits, clean, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

M = "police2s_mp"
DEV = re.compile(r"[ऀ-ॿ]")
HONOR = re.compile(r"^(?:श्री|श्रीमती|श्रीमति|सुश्री|कु\.|डॉ|निरी|उनि|सउनि|प्र\.?\s?आर|आर\.|उ\.?पु\.?अ|Shri|Smt|Mrs|Ms|Mr|Dr|Kum|Insp|SI\b|ASI\b)", re.I)
NUMCELL = re.compile(r"\d[\d\s–—-]{5,}\d")
CHOWKI = re.compile(r"चौकी|chowki|chauki|police post|\bPP\b", re.I)
SUBDIV = re.compile(r"अनु\s*0?\.?\s*अधी|अनु\.?\s*अधिकारी|अ0\s*अ0\s*पु0|अ\.\s?अ\.\s?पु|उपुअ|एसडीओपी|एस\.?डी\.?ओ\.?पी|अनुविभागीय|न\.?\s?पु\.?\s?अ|नगर पुलिस अधीक्षक|उ\.?\s?पु\.?\s?अ|उप पुलिस अधीक्षक|सी\.?\s?एस\.?\s?पी|"
                    r"सहायक पुलिस आयुक्त|\bSDOP\b|\bCSP\b|\bDSP\b|\bACP\b|ASST\.?\s?CP|Assistant Commissioner", re.I)
STATION = re.compile(r"थाना|था\.?\s?प्र|कोतवाली|POLICE STATION|\bP\.?S\.?\b|\bT\.?I\.?\b|Thana", re.I)
DISTRICT = re.compile(r"पुलिस अधीक्षक|पुलिस महानिरीक्षक|पुलिस उप ?महानिरीक्षक|पुलिस आयुक्त|उपायुक्त|COMMISSIONER|\bS\.?P\b|\bA\.?S\.?P\b|"
                      r"\bDIG\b|\bIGP?\b|\bDCP\b|Superintendent", re.I)
UNIT = re.compile(r"यातायात|शाखा|सेल|रेडियो|फिंगर|लाइन|कंट्रोल|नियंत्रण|रक्षित|विशेष|अपराध|FSL|Cyber|Traffic|Branch|Cell|Line|Control|"
                  r"Crime|Radio|Reserve|Special|HQ|मुख्यालय|OSD|कार्यालय", re.I)
STRIP_ST = re.compile(r"^(?:थाना\s*प्रभारी|था\.?\s?प्र\.?|थाना|POLICE\s+STATION|P\.?S\.?|T\.?I\.?)\s*[-–:,.]*\s*", re.I)
STRIP_CH = re.compile(r"^(?:चौकी\s*प्रभारी|चौकी)\s*[-–:,.]*\s*", re.I)


def grid(t):
    rows = []
    for tr in t.find_all("tr"):
        rows.append([re.sub(r"\s*[\u2013\u2014]\s*", "-", clean(ascii_digits(td.get_text(" ", strip=True))) or "")
                     for td in tr.find_all(["td", "th"])])
    return [r for r in rows if any(r)]


POSTWORD = re.compile(r"थाना|था\.?\s?प्र|प्रभारी|निरीक्षक|निरी\.?$|अधीक्षक|पुलिस|चौकी|अनु\.?\s?अधिकारी|उ\.?\s?पु\.?\s?अ|न\.?\s?पु\.?\s?अ|अ0|"
                      r"\bCSP\b|\bSDOP\b|\bDSP\b|\bSP\b|\bTI\b|POLICE|STATION|COMMISSIONER|ACP|DCP|सी\.?एस\.?पी|एस\.?डी\.?ओ\.?पी|शाखा|सेल|रक्षित|"
                      r"कंट्रोल|यातायात|अजाक|महिला|सायबर|साइबर", re.I)
NAME_HEAD = re.compile(r"नाम|Name", re.I)
POST_HEAD = re.compile(r"पद|थाना|कार्यालय|Designation|Post|Office|Unit", re.I)
PLACE_HEAD = re.compile(r"पदस्थापना|तैनात|थाना\s*/\s*कार्यालय|कार्यालय\s*/\s*थाना|posting|place", re.I)
SECTION_HEAD = re.compile(r"^अनुभाग$|sub ?division", re.I)
RANK_HEAD = re.compile(r"^(?:पद|पदनाम|Designation|Rank)$", re.I)
INSPECTOR = re.compile(r"निरीक्षक|निरी\b|निरी\.|उनि|सउनि|Inspector|\bS\.?I\b|\bTI\b", re.I)


def head_cols(head):
    """{"place": i, "rank": i, "section": i} from a header row whose columns name a posting place and a rank."""
    out = {}
    for i, h in enumerate(head or []):
        h = clean(h) or ""
        if PLACE_HEAD.search(h) and "place" not in out:
            out["place"] = i
        elif SECTION_HEAD.search(h) and "section" not in out:
            out["section"] = i
        elif RANK_HEAD.search(h) and "rank" not in out:
            out["rank"] = i
    return out if "place" in out else {}


def col_types(rows, head=None):
    """(name column, post column, phone columns): from the header when it names them, else from the cells."""
    n = max(len(r) for r in rows)
    num, hon, post, txt = [0] * n, [0] * n, [0] * n, [0] * n
    for r in rows:
        for i, c in enumerate(r):
            if not c or c in ("-", "--"):
                continue
            if NUMCELL.search(c) and not re.search(r"[A-Za-z\u0900-\u097f]{3,}", c):
                num[i] += 1
            elif re.fullmatch(r"[\d\s.)]{1,4}", c):
                continue                                  # serial numbers
            else:
                txt[i] += 1
                hon[i] += bool(HONOR.match(c))
                post[i] += bool(POSTWORD.search(c))
    phone_cols = [i for i in range(n) if num[i] and num[i] >= txt[i]]
    text_cols = [i for i in range(n) if i not in phone_cols and txt[i]]
    if not text_cols:
        return None, None, phone_cols
    name_col = post_col = None
    if head:
        for i, h in enumerate(head[:n]):
            if i not in text_cols:
                continue
            if NAME_HEAD.search(h) and not re.search(r"थाना|चौकी|कार्यालय|Office|पद", h) and name_col is None:
                name_col = i
            elif POST_HEAD.search(h) and post_col is None:
                post_col = i
    if name_col is None:
        cand = [i for i in text_cols if i != post_col]
        if cand:
            best = max(cand, key=lambda i: (hon[i] - post[i], -i))
            name_col = best if (hon[best] - post[best]) > 0 or len(cand) > 1 or post_col is not None else None
    if post_col is None:
        cand = [i for i in text_cols if i != name_col]
        post_col = max(cand, key=lambda i: (post[i] - hon[i], -i)) if cand else None
    return name_col, post_col, phone_cols


def is_header(r):
    j = " ".join(r)
    return bool(re.search(r"नाम|पद|मोबाइल|मोबाईल|सीयूजी|CUG|Designation|Name|Mobile", j)) and not NUMCELL.search(j)


def level_of(post):
    p = post or ""
    if SUBDIV.search(p):
        return "subdivision", "office"
    if CHOWKI.search(p):
        return "police_station", "police post"
    if STATION.search(p) and not re.search(r"मुंशी", p):
        return "police_station", "police station"
    if DISTRICT.search(p):
        return ("district", "unit") if UNIT.search(p) and not re.search(r"^(?:अति\.?\s*)?पुलिस अधीक्षक", p) else ("district", "office")
    return "district", "unit"


def area_of(level, otype, post):
    p = clean(post) or ""
    if otype == "police post":
        p = STRIP_CH.sub("", p)
    elif level == "police_station":
        p = STRIP_ST.sub("", p)
    return p.strip(" ,.-–") or post


def records(html, url, p):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t in soup.select("table"):
        rows = grid(t)
        if len(rows) < 2:
            continue
        head = next((r for r in rows[:4] if is_header(r)), None)
        body = [r for r in rows if not is_header(r)]
        if not body:
            continue
        name_col, post_col, phone_cols = col_types(body, head)
        if post_col is None:
            continue
        section = None
        for r in body:
            cells = [c for c in r if c]
            if len(set(cells)) == 1 and not NUMCELL.search(cells[0]):
                section = cells[0]                     # "शहर अनुभाग", "ZONE - I"
                continue
            g = lambda i: r[i] if i is not None and i < len(r) else ""  # noqa: E731
            post, name = g(post_col), g(name_col)
            hc = head_cols(head)
            place = rank = None
            if hc:
                place, rank = g(hc["place"]), g(hc.get("rank"))
                if hc.get("section") is not None and g(hc["section"]):
                    section = g(hc["section"])
                post = " ".join(x for x in (rank, place) if x) if rank and place and rank != place else (place or rank or post)
            if not post and name:
                post, name = name, ""
            if not post or re.fullmatch(r"[.\s]*", post):
                provenance.skip_row(r, 'skip: not post or re.fullmatch(r"[.\\s]*", post)')
                continue
            if name and re.fullmatch(r"[.\s-]*", name):
                name = ""
            level, otype = level_of(place or post) if place else level_of(post)
            if place and level == "district" and otype == "unit" and not UNIT.search(f"{place} {rank or ''}") and (
                    INSPECTOR.search(rank or "") or INSPECTOR.search(name or "")):
                level, otype = "police_station", "police station"     # an inspector posted at a place = its thana prabhari
            if place and level == "district" and SUBDIV.search(rank or ""):
                level, otype = "subdivision", "office"
            area = area_of(level, otype, place if place else post)
            ph = phones(*[g(i) for i in phone_cols])
            zone = section if section and re.search(r"zone|जोन", section, re.I) else None
            sub = section if section and not zone else None
            page = "contact:" if "/contact" in url else ""
            out.append(rec(M, f"{slug(p.get('district') or '')}:{page}{slug(post)}", level=level, office_type=otype, area=area,
                           area_regional=area if DEV.search(area or "") else None, post=post,
                           name=name or None, name_regional=name if DEV.search(name or "") else None, phone=ph,
                           subdivision=sub if level == "police_station" else None, zone=zone, state="MP",
                           district=p.get("district"), source=url))
    return out


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [gz(M, f"{slug(re.sub(r'^https?://', '', url))[:80]}.html", r.content)]
    if "not found /]" in r.text and "<table" not in r.text.split("entry-content", 1)[-1][:20000]:
        return [], files, "the page shows no table ([table not found])"
    recs = uniq(records(r.text, url, p))
    return recs, files, "" if recs else "no officer rows"
