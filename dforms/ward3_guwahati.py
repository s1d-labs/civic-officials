"""Guwahati Municipal Corporation (gmc.assam.gov.in, Assam Standardized Website Framework 2.0, Drupal): the heads of its 6 zones and
its 6 public works divisions, each with the wards it covers (wards 1-60 of the 2022 delimitation). Two pages (live sample
2026-11-13 from Mumbai; archive.s1d.me has only failed captures from the GitHub runners and from an India server on 2026-11-11):
  /about-us/our-zones      "the corporation area is divided into 6 zones. Each zone is headed by a Deputy Commissioner": per zone
       zone name, old wards (31-ward layout), new wards, name, designation, phone, address, email.
  /about-us/our-divisions  per public works division (I-VI): wards covered, "Name, Executive Engineer, (i/c) Div I, place", phone,
       email.
The pages are not tables: <p> blocks with <br> line breaks, and one block can run over several <p>. The reader flattens the content
(div#block-swf-content) to lines and starts a block at a zone name or a roman numeral that is followed by a ward list line.
Records: level "zone" (zones: the zone; divisions: area "Public Works Division I", zone = the zone with the same wards, if any);
wards = the new wards; zones also keep old_wards. Record ids: dept:ward3_guwahati:<zone|division>-<name>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html text lines (bs4): <p>/<br> blocks"     # source trail (provenance.py)

MODULE = "ward3_guwahati"
BODY, LGD, STATE, DISTRICT = "Guwahati Municipal Corporation", "249854", "AS", "Kamrup Metro"
BASE = "https://gmc.assam.gov.in/about-us/"
PAGES = (("zones", BASE + "our-zones"), ("divisions", BASE + "our-divisions"))
WARDS = re.compile(r"^\d{1,2}(?:\s*(?:,|&|and)\s*\d{1,2})+$")
PHONE = re.compile(r"^(?:\+?91[\s-]*)?[\d][\d\s-]{6,}\d$")


def items(get=None):
    return [{"key": f"{MODULE}-{k}", "payload": {"reader": MODULE, "url": u, "state": STATE, "kind": k, "india_only": True,
                                                 "route": "direct", "route_note": "route unchecked: GitHub runners and an "
                                                 "India server failed on 2026-11-11 (archive), Mumbai answered 2026-11-13"}}
            for k, u in PAGES]


def lines_of(html):
    """The content lines of the page (div#block-swf-content), <p> and <br> as line ends, after the 'Last Updated' line."""
    soup = _esw.soup(html)
    div = soup.find("div", id="block-swf-content") or soup.body or soup
    for br in div.find_all("br"):
        br.replace_with("\n")
    for p in div.find_all(["p", "li", "h3", "tr"]):
        p.insert_after("\n")
    out = [_esw.clean(x) for x in div.get_text().split("\n")]
    out = [x for x in out if x]
    i = next((k for k, x in enumerate(out) if x.lower().startswith("last updated")), -1)
    return out[i + 1:]


def blocks(lines):
    """[(start line index, [lines])]: a block starts at a short name line (zone name or roman numeral) followed by a ward list."""
    out = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if re.fullmatch(r"[IVX]{1,4}|[A-Z][a-z]{2,15}", ln) and WARDS.match(nxt):
            out.append((i, [ln]))
        elif out:
            out[-1][1].append(ln)
    return out


def parse(html, p):
    lines = lines_of(html)
    kind = p.get("kind") or ("divisions" if "division" in p["url"] else "zones")
    seen, recs = set(), []
    for start, b in blocks(lines):
        head, rest = b[0], b[1:]
        wl = [x for x in rest if WARDS.match(x)]
        phones = [x for x in rest if PHONE.match(x)]
        mails = [x for x in rest if "@" in x]
        other = [x for x in rest if x not in wl and x not in phones and x not in mails]
        new = _ward.wards_of(wl[-1]) if wl else []
        pos = {"line": start + 1, "line_text": head, "lines": len(b), "note": "line in the flattened text of div#block-swf-content"}
        if kind == "zones":
            name = other[0] if other else ""
            desig = next((x for x in other[1:] if re.search(r"(?i)commissioner|officer", x)), "Deputy Commissioner")
            addr = ", ".join(x for x in other[1:] if x != desig) or None
            area = f"{head} Zone"
            recs.append(_ward.record(MODULE, f"zone-{_esw.slug(head)}:{_esw.slug(desig)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=area, zone=area, post=f"{desig}, {area}",
                                     name=re.sub(r"^(Sri|Smti?|Shri)\.?\s+", "", name), phone=" ".join(phones),
                                     email=" ".join(mails), address=addr, wards=new,
                                     old_wards=_ward.wards_of(wl[0]) if len(wl) > 1 else None, wing="revenue", role="head",
                                     duties="trade licence, property tax and assessment", source=p["url"], src_pos=pos))
        else:
            text = " ".join(other)
            m = re.match(r"\s*([^,]+?)\s*,\s*((?:Spl\.?\s*)?Executive\s+Engineer)\s*,?\s*(.*)$", text, re.I)
            name, desig, place = (m.group(1), m.group(2), m.group(3)) if m else (text, "Executive Engineer", "")
            area = f"Public Works Division {head}"
            recs.append(_ward.record(MODULE, f"division-{head.lower()}:{_esw.slug(desig)}", seen, body=BODY, lgd=LGD, state=STATE,
                                     district=DISTRICT, level="zone", area=area, post=f"{desig}, {area}", name=name,
                                     phone=" ".join(phones), email=" ".join(mails), wards=new, wing="engineering", role="head",
                                     office=_esw.clean(place).strip(" .,") or None,
                                     duties="development and maintenance of roads and drains", source=p["url"], src_pos=pos))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, p.get("kind") or "page", r.content)], "" if recs else "no zone or division blocks"
