"""Delhi Police: Special and Joint Commissioners of Police (delhipolice.gov.in "Important Contact", 2026-11-13).

Source: https://delhipolice.gov.in/important-contact.html (HTML, 73 KB; archive copy of 2026-11-07). Two tables under the
headings "Special Commissioners of Police" (20 rows) and "Joint Commissioners of Police" (22 rows): S.No. | Designation |
e-Mail ([at]/[dot] written out) | Contact No. The page names posts, not persons (no names): records without a name.
A Joint CP of a Range (Northern, Southern, Western, Central, Eastern, New Delhi) and a Special CP of a Law & Order Zone get
level division (area = the range or zone; "covers" = the police districts in brackets as the page writes them); the others
(HQ, Crime, Traffic, Special Cell ...) level state.
Route: answered dev-vps-3 (Mumbai) in the archive; abroad unchecked -> proxy.
Ids: dept:st_dl_police:<spl|jt>:<S.No.>.
"""
import re

from dforms import _esw, _state

METHOD = "html table"
MODULE = "st_dl_police"
URL = "https://delhipolice.gov.in/important-contact.html"
BODY = "Delhi Police Headquarters"


def heading_of(table):
    for el in table.find_all_previous(string=True, limit=60):
        t = _esw.clean(el)
        if re.search(r"(?i)commissioners of police", t):
            return t
    return ""


def parse(html, url=URL):
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        head = heading_of(t)
        kind = "spl" if re.search(r"(?i)special", head) else "jt" if re.search(r"(?i)joint", head) else ""
        if not kind:
            continue
        pos = []
        for row, p in zip(_esw.grid(t, pos=pos), pos):
            if len(row) < 4 or not re.fullmatch(r"\d{1,3}", row[0].strip()):
                continue
            sn, post, mail, phone = (_esw.clean(c) for c in row[:4])
            unit = re.sub(r"(?i)^(spl\.?|jt\.?)\s*cp\s*/?\s*", "", post).strip()
            covers = re.findall(r"\(([^)]*)\)", unit)
            area = ""
            m = re.search(r"(?i)\b([A-Za-z ]+?)\s+range\b", unit)
            if kind == "jt" and m and not re.search(r"(?i)transport", m.group(1)):
                area = _esw.clean(m.group(1)).title() + " Range"
            m = re.search(r"(?i)\bzone\s*(\d)", unit)
            if kind == "spl" and m:
                area = f"Law & Order Zone {m.group(1)}"
            out.append(_state.rec(
                MODULE, f"{kind}:{sn}", state="DL", level="division" if area else "state", post=post, body=BODY,
                body_kind="police", department="Delhi Police", division=area, dept="police",
                post_kind="special_cp" if kind == "spl" else "joint_cp", unit=unit, covers=", ".join(covers) or None,
                email=_esw.emails(mail), phone=_esw.phones(phone), section=head, list_no=sn, cells=row, src_url=url,
                src_pos=p))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:important-contact", "payload": {"reader": MODULE, "url": URL, "state": "DL",
                                                               "india_only": True, "route": "proxy"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    recs = parse(r.text, p["url"])
    return recs, [_esw.keep(MODULE, "important-contact", r.content)], "" if recs else "no rows"
