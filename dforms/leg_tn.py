"""Tamil Nadu: members of the 17th Legislative Assembly (2026-) with their residence address, residence phones and official email,
from the assembly's alphabetical member list (www.assembly.tn.gov.in/17thassembly/members.php, 234 rows, one page).
Answers only from India (Germany gets no connection).

Each row: serial no, "Name Hon. Thiru. (PARTY) (Minister) | (Constituency)", address, TEL NO.(R) (one or more), email, photo.
The photo file is the ECI AC number (members/014.jpg = 14 Villivakkam); the reader uses it when it agrees with the name,
else the name decides. Address and phones are the member's residence ("TEL NO.(R)"). No office address, no constituency office.
One queue item = the whole list. Record ids: dept:leg_tn:TN-AC-<no>.
"""
import re

from dforms import _esw, _leg, _leg_se

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "leg_tn"
URL = "https://www.assembly.tn.gov.in/17thassembly/members.php"
PARTY = re.compile(r"^[A-Z][A-Z.]{1,9}(?:\s?\(M\))?$")
ALIAS = {"palacodu": "palacode", "thiyagarayanagar": "thiyagarayanagar"}


def items(get=None):
    return [{"key": f"{MODULE}-list", "payload": {"reader": MODULE, "url": URL, "state": "TN", "india_only": True}}]


def _parens(s):
    """Top-level (...) groups of a text, nested ones kept inside: 'X (DMK) (Vandavasi (SC))' -> ['DMK', 'Vandavasi (SC)']."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            if depth:
                cur += ch
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth:
                cur += ch
            else:
                out.append(_esw.clean(cur))
                cur = ""
        elif depth:
            cur += ch
    return out


def parse(html, url):
    recs = []
    for tr in _esw.soup(html).find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 5 or not _esw.clean(tds[0].get_text()).isdigit():
            continue
        who = _esw.clean(tds[1].get_text(" "))
        lines = [x for x in _esw.cell_text(tds[1]).split(" | ") if x]
        if "vacant" in who.lower():
            continue
        text = re.sub(r"\((?:Tmt|Thiru|Selvi)\.?\)\.?", " ", " | ".join(lines)).replace("(@)", "@")
        groups = _parens(text)
        if len(groups) < 2:
            continue
        constituency = groups[-1]
        party = next((g for g in groups[:-1] if PARTY.match(g)), "")
        roles = [g for g in groups[:-1] if g != party and len(g) > 2]
        initials = [g for g in groups[:-1] if len(g) <= 2]          # "Vijayakumar (A)": an initial in brackets
        nm = _esw.clean(re.sub(r"\b(?:Hon|Thiru|Tmt|Selvi)\b\.?", " ", text.split("(")[0]) + " " + " ".join(initials))
        if not nm:
            continue
        img = tr.find("img")
        m = re.search(r"/(\d{1,3})\.jpe?g", img.get("src", "")) if img else None
        photo_no = int(m.group(1)) if m and int(m.group(1)) else None
        address = re.sub(r",(\s*,)+", ",", _esw.cell_text(tds[2]).replace(" | ", ", "))
        by_name, _ = _leg_se.seat("TN", None, constituency, alias=ALIAS)
        if not by_name and not photo_no:      # two seats share a name (Tiruppattur): the district in the address decides
            by_name = next((n for d in re.split(r"[,\-–]", address) if (n := _esw.ac_no("TN", constituency, re.sub(r"[\d.]", "", d).strip()))), None)
        no = photo_no if photo_no and (not by_name or by_name == photo_no) else (by_name or photo_no)
        recs.append(_leg.member(MODULE, "TN", "AC", no, nm, constituency=constituency, party=party, source=url,
                                email=_esw.clean(tds[4].get_text(" ")), residence_address=address,
                                phone_residence=_esw.cell_text(tds[3]).replace(" | ", ", "), role=", ".join(roles),
                                seat_no=photo_no, house="Tamil Nadu Legislative Assembly (17th)"))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "members", r.content)]
    recs = parse(r.text, p["url"])
    return recs, files, "" if recs else "no members in the page"
