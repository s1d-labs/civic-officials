"""Tripura Fire & Emergency Services: the "Contact Us" page fireservice.tripura.gov.in/contact-us (saved on archive.s1d.me
2026-11-05). One two-column table "Name & Designation | Office Address & Phone No.": headquarters officers first, then four
fire divisions (West, Gomati, Unakoti, Dhalai; a row that repeats the division name in both cells), each with its I/C
Divisional Fire Officer (named, mobile and phone) and one row per fire station or fire post: "<Station> Fire Station" |
"(0381) 232-5630 /101/(M)6033231202" (landline, the 101 line, the station's own mobile). Station officers are not named.
The page shows no date. Record ids: dept:emerg_fire_tr:st-<station>, div-<division>, hq-<name or office>.
"""
import re

from dforms import _emerg, _esw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_fire_tr"
URL = "https://fireservice.tripura.gov.in/contact-us"


def items(get=None):
    return _emerg.seed(MODULE)


def split_phones(text):
    """'(0381) 232-5630 /101/(M)6033231202' -> (landline, mobiles): the short code 101 is left out."""
    t = re.split(r"(?i)\bfax\b", _emerg.clean(text))[0]
    mob = re.findall(r"(?<!\d)[6-9]\d{9}(?!\d)", re.sub(r"\(M\)\s*", " ", t))
    land = re.sub(r"\(M\)\s*\d+|(?<!\d)[6-9]\d{9}(?!\d)|/\s*101\s*/|IP\s*Phone\s*\d+", " ", t)
    land = [x.strip(" /-") for x in re.findall(r"\(0\d{3,4}\)\s*[\d-]{5,9}", land)]
    return ", ".join(land), ", ".join(mob)


def records(html, url):
    s = _esw.soup(html)
    recs, seen, division = [], set(), None
    for t in s.find_all("table"):
        for row in _esw.grid(t):
            if len(row) < 2 or re.match(r"(?i)name\s*&\s*designation|postal address", row[0]):
                continue
            left, right = row[0], row[1]
            lc = _emerg.clean(left.replace(" | ", " "))
            if left == right and re.search(r"(?i)division", left):
                division = re.sub(r"(?i)\s*fire\s+division", "", lc).strip()
                continue
            m = re.match(r"(?i)^(.+?)\s+fire\s+(station|post)\b(.*)$", lc)
            if m and not re.search(r"\d", lc):
                land, mob = split_phones(right)
                area = _emerg.clean(f"{m.group(1)} Fire {m.group(2).title()}{m.group(3)}")
                key = _emerg.unique(f"st-{_emerg.slug(m.group(1))}", seen)
                recs.append(_emerg.record(
                    MODULE, key, "fire", dept="fire", level="facility", area=area, post="Station Officer",
                    phone=", ".join(x for x in (land, mob) if x), landline=land, mobile=mob, has_101="/101" in right.replace(" ", ""),
                    division=division, state="TR", office_id=key, source=url))
                continue
            parts = [_emerg.clean(x) for x in left.split("|") if _emerg.clean(x)]
            land, mob = split_phones(right)
            email = _emerg.emails(_esw.deob(right))
            adr = _emerg.clean(re.split(r"(?i)\bphone|\bmobile|\be-?mail", right.replace(" | ", ", "))[0]).strip(" ,.-")
            adr = re.sub(r"\s*,(\s*,)+", ",", re.sub(r"\s+,", ",", adr))
            named = re.match(r"(?i)^(dr\.?|shri|sh\.?|smt\.?|er\.?|sri)\s", parts[0]) if parts else None
            if named:
                bits = [x.strip(" ,.") for x in re.split(r",\s*", " ".join(parts)) if x.strip(" ,.")]
                name = bits[0]
                post = re.sub(r"^(IAS|IPS)\s+", "", ", ".join(bits[1:])) or None
            else:
                name, post = None, " ".join(parts)
            is_div = bool(division) and post and re.search(r"(?i)divisional fire officer", post) and re.search(r"(?i)division", post)
            key = _emerg.unique(f"div-{_emerg.slug(division)}" if is_div else f"hq-{_emerg.slug(name or post or 'office')}", seen)
            recs.append(_emerg.record(
                MODULE, key, "fire", dept="fire", level="division" if is_div else "state",
                area=f"{division} Fire Division" if is_div else "Tripura Fire & Emergency Services", post=post, name=name,
                phone=", ".join(x for x in (land, mob) if x), landline=land, mobile=mob, email=email, address=adr,
                division=division if is_div else None, state="TR", office_id=key, source=url))
    return recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = records(r.text, url)
    return recs, [_emerg.keep(MODULE, "contact-us", r.content)], "" if recs else "no rows"
