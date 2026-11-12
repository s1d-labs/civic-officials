"""Karnataka: the home page of each urban body's own site, www.<label>.mrc.gov.in/en (Municipal Reforms Cell, one Drupal template
"great_zymphonies" for every City Corporation, City / Town Municipal Council and Town Panchayath). Answers only from India (no
answer from Germany on 2026-11-11; vpsin got the pages). archive.s1d.me holds no copy of these sites (2026-11-11).

The home page has four or five "flip cards" (Drupal blocks): Chief Minister, Municipal / UD Minister, then the body's own
"presidentmessage" or "mayorsmessage" card and its "commissionersmessage" card. The front side of each card holds the name, the post
and the body ("Sri.Shivaleela Sadashiv Butali / Hon'ble President, / Athani TMC"; "Chief Officer,Athani / smt.Daya k Joshi";
"Shri. Kartik M (Senior Scale) / Commissioner, / Belagavi City Corporation"). Ministers' cards are left out. A card whose name is a
blank ("Sri. ___________") is left out. A card that names another body is left out: some new sites still carry the template's text
(huttitown shows "Hon'ble Administrator, / Bogadi TP." with blank names, 2026-11-11). Records: "President" / "Mayor" / "Administrator"
(role chair, chair, head) and "Chief Officer" / "Commissioner" (role head), dept town_body, level body. The card does not show a date,
a phone or an email.

The site list (dforms/ulb2_ka_sites.json) = the 308 mrc.gov.in sites of sites.csv (minus www.mrc.gov.in and the Kodagu DUDC site)
plus 11 sites found by DNS on 2026-11-11 for bodies with no official in DB civic (aminagadtown, benakanahallitown, ...). Each entry
has the body name (the site title; LGD name + type when the title is Kannada or a block page) and the LGD local body code, matched by
name (letters only, then consonant skeleton), checked by hand for the doubtful ones: the site names differ from LGD
(Athani / Athni, Bantwal / Bantval, Hospet / Hosapete, H.D.Kote / Heggadadevankote, Kaup / Kapu, T.Narasipura / Tirumakudal -
Narsipur, kamalapura-kbg = Kamalapura of Kalaburagi, vijayapuracity = Vijayapura City Corporation, vijayapuratown = Vijayapura of
Bengaluru Rural). jalitown has no LGD body (Jali of Bhatkal is not in LGD as an urban body): no lgd_code.
"""
import json
import re
from pathlib import Path

from dforms import _esw, _ulb

METHOD = "html cards (flip cards div#block-*, .frontside)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ulb2_ka"
STATE = "KA"
SITES = json.loads((Path(__file__).with_name("ulb2_ka_sites.json")).read_text())
TYPE = re.compile(r"(?i)\s+(city\s+corporation|city\s+municipal\s+council|town\s+municipal\s+council|town\s+panchaya?th?|"
                  r"notified\s+area\s+committee)$")
# a post on the card ("Hon'ble President,", "Chief Officer,Athani", "Cheif Officer,")
POST = re.compile(r"(?i)\b(president|vice\s*president|mayor|deputy\s*mayor|administrator|ch(ie|ei)f\s*officer|commissioner|"
                  r"adhyaksha|upadhyaksha)\b|ಅಧ್ಯಕ್ಷ|ಮಹಾಪೌರ|ಆಯುಕ್ತ|ಮುಖ್ಯಾಧಿಕಾರಿ|ಆಡಳಿತಾಧಿಕಾರಿ")
SKIP = re.compile(r"(?i)minister|govt\.?\s*of\s*karnataka|government\s+of\s+karnataka|ಸಚಿವ|ಮುಖ್ಯಮಂತ್ರಿ")
BODYWORD = re.compile(r"(?i)\b(tmc|cmc|tp|cc|town|city|corporation|council|panchaya?th?|municipal(ity)?|palike|nac)\b\.?|"
                      r"ಪಟ್ಟಣ|ನಗರಸಭೆ|ಪುರಸಭೆ|ಪಾಲಿಕೆ")
HONOUR = re.compile(r"(?i)^(hon'?\s*ble|honourable)\s+")


def items(get=None):
    out = []
    for s in SITES:
        p = {"reader": MODULE, "url": f"http://www.{s['site']}.mrc.gov.in/en", "site": s["site"], "body": s["body"], "state": STATE,
             "india_only": True}
        for k in ("lgd_code", "district"):
            if s.get(k):
                p[k] = s[k]
        out.append({"key": f"{MODULE}-{s['site']}", "payload": p})
    return out


def split_type(name):
    """'Athani Town Municipal Council' -> ('Athani', 'Town Municipal Council'); 'ALMEL TOWN PANCHAYATH' -> ('ALMEL', 'TOWN PANCHAYATH')."""
    name = _esw.clean(name)
    m = TYPE.search(name)
    return (name[:m.start()].strip(), m.group(1)) if m else (name, None)


def _skel(s):
    k = re.sub(r"[^a-z]", "", (s or "").lower())
    for a, b in (("th", "t"), ("dh", "d"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("sh", "s"), ("w", "v")):
        k = k.replace(a, b)
    k = re.sub(r"(.)\1+", r"\1", k)
    return k[:1] + re.sub("[aeiouy]", "", k[1:])


def _same_body(text, area, site):
    """True when the card's body text names this body (or names none). 'Athani TMC' for Athani -> True; 'Bogadi TP.' on huttitown -> False."""
    rest = _esw.clean(BODYWORD.sub(" ", text or "")).strip(" .,")
    if not re.search(r"[A-Za-z]{3}", rest):
        return True
    k = _skel(rest)
    return any(k and (k in _skel(x) or _skel(x) in k) for x in (area, re.sub(r"(town|city|tp|tmc|cmc)$", "", site)) if _skel(x))


def _name_ok(name):
    letters = re.sub(r"(?i)\b(sri|smt|shri|shrimati|kum|dr|mr|mrs|ms)\b\.?|[^A-Za-zಀ-೿]", "", name)
    return len(letters) >= 3


def cards(html):
    """[(lines)] of the front side of each flip card, innermost block only."""
    soup = _esw.soup(html)
    out = []
    for b in soup.find_all("div", id=re.compile("^block-")):
        fr = b.find("div", class_="frontside")
        if not fr or b.find("div", id=re.compile("^block-")):
            continue
        lines = [_esw.clean(x) for x in fr.get_text("\n").split("\n")]
        out.append((b["id"], [x for x in lines if x]))
    return out


def parse(html, body, site, url="", district=None, lgd_code=None):
    area, btype = split_type(body)
    recs, seen, why = [], set(), []
    for bid, lines in cards(html):
        if any(SKIP.search(x) for x in lines):
            continue
        i = next((n for n, x in enumerate(lines) if POST.search(x)), None)
        if i is None:
            continue
        post, _, after = lines[i].partition(",")
        post = HONOUR.sub("", _esw.clean(post)).strip(" .,:")
        post = re.sub(r"(?i)\bcheif\b", "Chief", post)
        rest = [x for n, x in enumerate(lines) if n != i]
        bodyl = [x for x in rest if BODYWORD.search(x)] + ([after] if after.strip() else [])
        name = _esw.clean(" ".join(x for x in rest if not BODYWORD.search(x))).strip(" ,")
        if not all(_same_body(x, area, site) for x in bodyl):
            why.append(f"{bid}: card names another body ({'; '.join(bodyl)})")
            continue
        if not _name_ok(name):
            why.append(f"{bid}: no name")
            continue
        extra = {"lgd_code": lgd_code} if lgd_code else {}
        recs.append(_ulb.record(MODULE, STATE, area, post, seen, name=name, district=district, body_type=btype, source=url,
                                list_name=body, card=bid.replace("block-", ""), src_pos={"selector": f"div#{bid} .frontside"},
                                **extra))
    return recs, why


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, p["site"], r.content)]
    recs, why = parse(r.text, p["body"], p["site"], p["url"], p.get("district"), p.get("lgd_code"))
    return recs, files, "" if recs else ("no named card" + (": " + " | ".join(why) if why else ""))
