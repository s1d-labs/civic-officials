"""Jammu and Kashmir: the executive heads (CEO / EO, or the officer who holds the post as additional charge) of every urban local
body except the two corporations, with mobile and mailbox, tied to LGD codes.

Two items:
- "jammu": Directorate of Urban Local Bodies Jammu, "Who's Who" page, https://ulbjammu.jk.gov.in/ulb%20AboUsWhoSWho.html (static
  HTML, about 40 KB, no date). Table 1 = the directorate's own officers (Director, Dy. Directors, AO ...; level state, area
  "Jammu division"). Table 2 = "Contact details of CEOs and EOs of ULBs in Jammu Division": S.No. | Name of ULB ("Doda (Addl)") |
  Name of CEO/EOs ("Sh.Ravi Saini (Addl)") | Designation (the officer's own post: "Executive Officer", "BDO Doda", "JKAS
  Tehsildar Jourian") | Office Name ("Municipal Council Doda") | Mobile Nos. | E-Mail IDs. 36 bodies on 2026-11-05 (archive copy,
  vantage IN-proxy); the live page answered dev-vps-3 (Mumbai) on 2026-11-13. Rows with "-" as the name (Lakhanpur, Parole on
  2026-11-05) keep the post's mailbox with no name. "(Addl)" = additional charge: charge "additional", and the officer's own
  post goes to own_post; post is "Executive Officer" (or "Chief Executive Officer" where the list says so).
  The directory task already reads this page (directories.json "jk-jammu-whoswho"), but civic-india ties all its 64 rows to one
  body (LGD 248038, Doda): this reader gives each row its own body.
- "kashmir": the Kashmir division key contacts PDF that dforms/ulb_jk.py reads (same rows, same parser), here with the LGD code
  of each body (ulb_jk records carry none and civic-india tied none of its 40 rows to a body). India only.

dforms/th_jk_lgd.json: body name (type words cut, a-z only) -> LGD local_body_code, matched once (2026-11-13) by name in the
state, every match checked by eye (Basholi = Basohli, Thannamandi = Thanamandi, Chararisharief = Chrari Sharief, Tangmarg =
Gulmarg Tangmarg). 76 of the state's 78 bodies; Jammu and Srinagar corporations are in neither list.
"""
import json
import re
from pathlib import Path

import provenance
from dforms import _esw, _ulb, ulb_jk

METHOD = "html table (who's who, table/row) | pdf text (pypdf, kashmir via ulb_jk.rows)"

MODULE = "th_jk"
STATE = "JK"
JAMMU = "https://ulbjammu.jk.gov.in/ulb%20AboUsWhoSWho.html"
KASHMIR = ulb_jk.URL
LGD = json.loads(Path(__file__).with_name("th_jk_lgd.json").read_text())
ADDL = re.compile(r"\(\s*addl\.?\s*\)", re.I)
TYPE = re.compile(r"(?i)^(mun\w*\s+(?:committee|council|corporation))\s+(.+)$")


def items(get=None):
    return [{"key": f"{MODULE}-jammu", "payload": {"reader": MODULE, "part": "jammu", "url": JAMMU, "state": STATE,
                                                  "india_only": True}},
            {"key": f"{MODULE}-kashmir", "payload": {"reader": MODULE, "part": "kashmir", "url": KASHMIR, "state": STATE,
                                                    "india_only": True}}]


def key_of(name):
    n = re.sub(r"(?i)^mun\w*\s+(committee|council|corporation)\s+", "", _esw.clean(name))
    return re.sub(r"[^a-z]", "", n.lower())


def lgd_of(office):
    code = LGD["rows"].get(key_of(office))
    return code, (LGD["lgd"].get(code) or {}) if code else {}


def nil(s):
    s = _esw.clean(s)
    return "" if re.fullmatch(r"[-–—\s.]*", s) else s


def parse_jammu(html, url=JAMMU):
    soup = _esw.soup(html)
    recs, seen = [], set()
    tables = soup.find_all("table")
    for ti, t in enumerate(tables):
        rows = t.find_all("tr")
        head = " ".join(c.get_text(" ", strip=True) for c in rows[0].find_all(["td", "th"])).lower() if rows else ""
        for ri, tr in enumerate(rows[1:], 1):
            c = [_esw.cell_text(td) for td in tr.find_all("td")]
            pos = {"table": ti, "row": ri}
            if "name of ulb" in head and len(c) >= 7:
                ulb, officer, own, office, mobile, mail = c[1], c[2], c[3], c[4], c[5], c[6]
                m = TYPE.match(_esw.clean(office))
                body, btype = (m.group(2), m.group(1)) if m else (re.sub(ADDL, "", ulb).strip(), None)
                addl = bool(ADDL.search(ulb) or ADDL.search(officer))
                name = nil(re.sub(ADDL, "", officer))
                post = "Chief Executive Officer" if re.search(r"(?i)chief\s*executive", own) else "Executive Officer"
                code, l = lgd_of(office)
                recs.append(_ulb.record(MODULE, STATE, body, post, seen, name=name, phone=nil(mobile), email=nil(mail),
                                        district=l.get("district"), body_type=btype, source=url, lgd_code=code,
                                        area_latin=l.get("name"), charge="additional" if addl else None,
                                        own_post=None if own.lower() == post.lower() else nil(own), list_name=_esw.clean(office),
                                        list_ulb=_esw.clean(ulb), page=url, src_pos=pos))
            elif "designation" in head and len(c) >= 7 and nil(c[1]):
                rid, d = _esw.record(MODULE, f"{STATE}-dulb-jammu-{_esw.slug(c[2])}-{ri}", dept="town_body", level="state",
                                     area="Jammu division", post=c[2], name=c[1], phone=_esw.phones(c[3], c[4]),
                                     email=_esw.emails(c[5]), address=c[6], state=STATE, role="staff",
                                     office_id=f"{STATE}-DULB-JAMMU", source=url, page=url, src_pos=pos,
                                     office="Directorate of Urban Local Bodies Jammu")
                recs.append((rid, d))
    return recs


def parse_kashmir(content, url=KASHMIR):
    out = []
    for rid, d in ulb_jk.parse(content, url):
        code, l = lgd_of(d.get("list_name") or d.get("area", ""))
        d = dict(d, lgd_code=code, area_latin=l.get("name"), district=l.get("district"), page=url)
        out.append((rid.replace("dept:ulb_jk:", f"dept:{MODULE}:", 1), d))
    return out


def fetch(p, get):
    part = p.get("part", "jammu")
    r = get(p.get("url") or (JAMMU if part == "jammu" else KASHMIR))
    if r is None:
        return [], [], "no answer"
    if part == "kashmir":
        if not r.content.startswith(b"%PDF"):
            return [], [], "not a PDF"
        recs = parse_kashmir(r.content, p.get("url") or KASHMIR)
        return recs, [_esw.keep(MODULE, "kashmir-key-contacts", r.content, "pdf")], "" if recs else "no rows"
    recs = parse_jammu(r.text, p.get("url") or JAMMU)
    return recs, [_esw.keep(MODULE, "jammu-whoswho", r.content)], "" if recs else "no rows"
