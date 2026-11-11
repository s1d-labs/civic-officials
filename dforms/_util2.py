"""Shared parts of the second-round utility readers (dforms/power2_*.py, dforms/water2_*.py).

office_level(text) gives the level of an office from its own name ("Harda North D/c" -> section, "Timarni S/D" -> subdivision,
"(O&M) Dn. Harda South" -> division, "O&M Circle Guna" -> circle, "Bhopal Region" -> zone); post_level(post) gives it from the
post (Assistant Engineer / JE / Asst. Manager -> section, AEE / SDO / AEN / Manager -> subdivision, EE / XEN / DGM -> division, SE / GM
-> circle, CE / ED / CGM -> zone). person(name) strips honorifics. updated(text) finds the page's own "as on" / "updated" date.
"""
import re

from dforms import _power

OFFICE_RULES = (
    ("section", r"\bD/?\s?C\b|\bDC\b|DISTRIBUTION\s+CENT|\bZONE\b|\bSECTION\b|\bCCC\b|SUB-?\s?STATION|\bS/S\b|\bJEN\b|SERVICE\s+STATION"),
    ("subdivision", r"S/\s?D(N|IV)?\b|\bSUB[\s.-]*D(IV|N)|\bSUBDIV|\bSUB\.?\s|\bSDO\b|SUB\s*-?\s*DIVISION"),
    ("division", r"\bDN\b\.?|\bDIVISION\b|\bDIV\b\.?|\bDIVN\b"),
    ("circle", r"\bCIRCLE\b"),
    ("zone", r"\bREGION\b|\bZONAL\b"),
)
POST_RULES = (
    ("section", r"\bJ\.?\s?E\b|\bJEN\b|JUNIOR\s+ENG|\bA\.?\s?E\b(?!\s*\()|ASSISTANT\s+ENGINEER|ASST\.?\s*ENGINEER|ASS(T|TT|ISTANT)\.?\s*MANAGER|\bLINE\s*MAN"),
    ("subdivision", r"\bA\.?\s?E\.?\s?E\b|\bA\.?\s?EN\b|\bS\.?\s?D\.?\s?[OE]\b|ASS(T|ISTANT)\.?\s*EXEC|\bADE\b|DY\.?\s*EXEC|^\s*MANAGER\b|\bMANAGER\s*\((O|D|O&M|T)\)|\bAE\s*\(|\bDY\.?\s*MANAGER"),
    ("division", r"\bE\.?\s?E\b|\bXEN\b|EXECUTIVE\s+ENG|\bD\.?\s?G\.?\s?M\b|DY\.?\s*G(ENERAL)?\.?\s*M(ANAGER)?|DEPUTY\s+GENERAL|SR\.?\s*MANAGER|SENIOR\s+MANAGER"),
    ("circle", r"\bS\.?\s?E\b|SUPERINTEND|\bG\.?\s?M\b|GENERAL\s+MANAGER|\bA\.?\s?G\.?\s?M\b"),
    ("zone", r"\bC\.?\s?E\b|CHIEF\s+ENG|\bC\.?\s?G\.?\s?M\b|CHIEF\s+GENERAL|\bE\.?\s?D\b|EXECUTIVE\s+DIRECTOR|ADDL\.?\s*C"),
    ("state", r"MANAGING\s+DIRECTOR|\bM\.?\s?D\b|\bDIRECTOR\b|CHAIRMAN|SECRETARY|ENGINEER[\s-]+IN[\s-]+CHIEF|\bCMD\b"),
)
HONORIFIC = re.compile(r"^\s*((sh|shri|shree|smt|mr|mrs|ms|ku|kum|km|kumari|sri|smt\.|thiru|tmt|selvi)\.?\s+|(sh|shri|smt|mr|mrs|ms)\.(?=\S))+",
                       re.I)
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


def office_level(text):
    t = " " + (text or "").upper() + " "
    for level, rx in OFFICE_RULES:
        if re.search(rx, t):
            return level
    return None


def post_level(post, default=None):
    t = (post or "").upper()
    for level, rx in POST_RULES:
        if re.search(rx, t):
            return level
    return default


def person(name):
    n = _power.clean(name)
    if not n:
        return None
    n = HONORIFIC.sub("", n).strip(" .,")
    return _power.clean(n) if not re.fullmatch(r"[\d\s.]*", n) else None


def updated(text):
    """The first date after 'as on', 'updated', 'updation', 'Dt.' or a list title: ISO yyyy-mm-dd, or None."""
    m = re.search(r"(?:as\s+on|updat\w*|dt\.?|dated|date)\s*[:\-]?\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", text or "", re.I) or \
        re.search(r"-\s*(\d{1,2})-(\d{1,2})-(\d{4})\b", text or "")
    if m:
        d, mo, y = (int(x) for x in m.groups())
        y = y + 2000 if y < 100 else y
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(?:as\s+on|updat\w*)\s*[:\-]?\s*(\d{1,2})\s*([A-Za-z]{3})[a-z]*['’ ,.-]*(\d{2,4})", text or "", re.I)
    if m and m.group(2).lower() in MONTHS:
        y = int(m.group(3))
        y = y + 2000 if y < 100 else y
        return f"{y:04d}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    return None


def area_name(text):
    """'(O&M) Dn. Harda North' -> 'Harda North'; 'Harda North D/c' -> 'Harda North'; 'Timarni S/D' -> 'Timarni'."""
    t = _power.clean(text) or ""
    t = re.sub(r"^\(?\s*O\s*&\s*M\s*\)?\s*", "", t, flags=re.I)
    t = re.sub(r"^(Dn|Divn|Division|Circle|S/Dn|S/D|Sub[- ]?Division|DC|D/C)\.?[\s-]+", "", t, flags=re.I)
    t = re.sub(r"[\s-]+(D/?c|DC|S/?Dn?|Sub[- ]?Div(ision|n)?\.?|Subdivision|Division|Dn|Circle|Zone)\.?$", "", t, flags=re.I)
    return _power.clean(t.strip(" -,")) or _power.clean(text)


def tel(*parts):
    """_power.phone(), else the cleaned text when it holds 7 or more digits ("(033)2262-2641/40" has no 5-digit run)."""
    p = _power.phone(*parts)
    if p:
        return p
    keep = [_power.clean(x) for x in parts if x and len(re.sub(r"\D", "", x)) >= 7]
    return ", ".join(x for x in keep if x) or None
