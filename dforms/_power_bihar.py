"""Shared reading of the Bihar discoms' telephone directory (NBPDCL and SBPDCL, frmHelplineNumbers.aspx): one page, a collapsible
tree of <li><span class="caret">Heading</span><ul class="nested"><table>...; headings are "Headquarter", "Area Board",
"Circle-<name>", "Division-<name>" (nested in its circle), "Fuse Call Center", "Customer Care Number", "Switch Board Operator".
Rows have 3-4 cells: two text cells (place or officer name, and designation, in either order) and mobile / phone.
Offices: ESD = electric supply division (EEE), ESSD = electric supply sub-division (AEE), ESS = electric supply section (JEE),
PSS = 33/11 kV power sub-station (SBO / PSS phone). ESE = circle head; "DGM cum ESE <x> Area" = area board (zone).
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, clean, phone

DES = re.compile(r"^\s*(E\.?\s?E\.?\s?E|EEE|AEE|JEE|ESE|SBO|PSS|EE|AE|JE|AA|RO|AO|A\.O|AITM|ITM|ASSISTANT|MANAGER|"
                 r"REVENUE|DGM|GM|CE|CHIEF|SR\.?|SENIOR|DEPUTY|UNDER|FUSE|CGRF|SECTION|LAND|LAW|DLA|PROJECT|DIRECTOR|"
                 r"CONTROL|ACCOUNTS?|JUNIOR|EXECUTIVE)\b", re.I)
OFFICE = re.compile(r"\b(E\.?\s?S\.?\s?S\.?\s?D|E\.?\s?S\.?\s?D|E\.?\s?S\.?\s?S|EES|PSS|E/S/S/Divn)\b", re.I)
PERSON = re.compile(r"^(SRI|SMT|SHRI|MD\.?|MISS\.?|MR\.?|MRS\.?|DR\.?|KUMARI|MS\.?)\s", re.I)
FUNC = re.compile(r"\b(PROJECT|REVENUE|MRT|TRW|T\.R\.W|CIVIL|IT|F\s*&\s*A|RMR|METERING|PLANNING|CGRF|ITM|AITM|STF|SLDC|"
                  r"RO|AO|A\.O|ACCOUNTS?|IPDS|DDUGJY|RE|S\s*&\s*P|EA|ENERGY|MANAGER)\b", re.I)


def office_level(text):
    t = (text or "").upper().replace(" ", "")
    if re.search(r"E\.?S\.?S\.?D|E/S/S/DIVN", t):
        return "subdivision"
    if re.search(r"E\.?S\.?D\b|E\.?S\.?D[,.]", t) or re.search(r"\bE\.?S\.?D\b", (text or "").upper()):
        return "division"
    if re.search(r"\b(E\.?S\.?S|EES|PSS)\b", (text or "").upper()):
        return "section"
    return None


def post_level(post):
    p = re.sub(r"[^A-Z]", " ", (post or "").upper()).split()
    head = "".join(p[:3]) if p[:3] == ["E", "E", "E"] else (p[0] if p else "")
    if "CUM" in p and "ESE" in p and "AREA" in p:
        return "zone"
    return {"ESE": "circle", "EEE": "division", "AEE": "subdivision", "JEE": "section", "SBO": "section",
            "PSS": "section"}.get(head)


def area_of(office):
    """'ESSD, MeenaBazar' -> 'MeenaBazar'; 'PSS - GAIGHAT' -> 'GAIGHAT'; 'EEE, ESD, Barauni' -> 'Barauni'."""
    a = re.sub(r"(?i)^.*?\b(E\.?\s?S\.?\s?S\.?\s?D|E\.?\s?S\.?\s?D|E\.?\s?S\.?\s?S|EES|PSS|33/11\s*KV\s*PSS)\b\.?\s*[,:-]?\s*", "", office or "")
    return clean(a.strip(" ,-")) or clean(office)


def parse(html, module, state, discom, url, desig_first):
    """desig_first: the source's usual cell order (SBPDCL designation first, NBPDCL place first); swapped per row when the
    other cell is the one that looks like a designation."""
    out = Out(module, state, url, discom=discom)
    soup = BeautifulSoup(html, "lxml")
    head = circle = division = None
    for el in soup.find_all(["span", "tr"]):
        if el.name == "span":
            if "caret" in (el.get("class") or []):
                head = clean(el.get_text(" ", strip=True))
                if head and head.lower().startswith("circle"):
                    circle, division = clean(re.sub(r"(?i)^circle\s*-\s*", "", head)), None
                elif head and head.lower().startswith("division"):
                    division = clean(re.sub(r"(?i)^division\s*-\s*", "", head))
                elif head and not head.lower().startswith("division"):
                    circle = division = None
            continue
        tds = el.find_all("td", recursive=False)
        if len(tds) < 3 or head is None:
            continue
        c = [clean(td.get_text(" ", strip=True)) for td in tds]
        a, b = c[0], c[1]
        if not (a or b):
            continue
        d, other = (a, b) if desig_first else (b, a)
        if not (d and DES.search(d)) and other and DES.search(other):
            d, other = other, d
        nums = phone(*c[2:4])
        h = (head or "").lower()
        name = None
        if other and (PERSON.search(other) or h.startswith("headquarter")) and not OFFICE.search(other):
            name, other = other, None
        blob = " ".join(x for x in (d, other) if x)
        if h.startswith("headquarter"):
            level, area = "state", f"{discom} Headquarters"
        elif h.startswith("area"):
            level, area = "zone", other
            m = re.search(r"(?i)ESE\s+(.*?)\s+Area", d or "")
            area = clean(m.group(1)) + " Area" if m else other
        elif h.startswith("customer"):                       # toll-free 1912 only: not an office
            continue
        elif h.startswith("fuse"):
            level, area, d = "section", b, "Fuse Call Centre"
            if not desig_first:                              # NBPDCL: control room name, then its place
                level, d, area = "division", a, b
            elif h.startswith("fuse"):                       # SBPDCL: division, then the fuse call centre's locality
                division = a
        elif h.startswith("switch"):
            level, area = "section", area_of(a if OFFICE.search(a or "") else b)
        else:
            staff = bool(FUNC.search(d or "")) and post_level(d) not in ("section",)
            lv_off = office_level(blob)
            lv_post = post_level(d)
            level = lv_off or lv_post or ("division" if division else "circle")
            if staff and not lv_off:
                level = "division" if division else "circle"
            if other and OFFICE.search(other):
                area = area_of(other)
            elif other and not desig_first:                  # NBPDCL: the place of posting
                area = other
            elif OFFICE.search(d or ""):
                area = area_of(d)
            elif level == "division" and division:
                area = other or division
            elif level == "circle":
                area = circle
            else:
                area = other or division or circle
        parents = {}
        if circle and level not in ("circle", "zone", "state"):
            parents["circle"] = circle
        if division and level in ("subdivision", "section"):
            parents["division"] = division
        if level == "circle" and circle and area != circle:
            parents["circle"] = circle
        key = f"{division or circle or head}:{area}:{d}"
        if h.startswith("fuse"):
            parents = {"division": division} if division else {}
            division = None
        out.add(key, level, area, post=d, name=name, phone_=nums, parents=parents, block=head, src_pos=tr_pos(el))
    return out.recs
