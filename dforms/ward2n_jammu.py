"""Jammu Municipal Corporation (jmc.jk.gov.in): ward and zone staff from the four "Contact Us" pages
(/contactus.aspx?type=<Sanitation | Works | Officers | Enforcement>; ASP.NET; in archive.s1d.me, saved 2026-11-06; the pages show
no date). One queue item per page:
  - Sanitation: "Zonewise Name & Contact Nos. of Sanitation Supervisory": S. No. | Ward No. ("7-A", "20-A") | Contact no. of
    Supervisor | of S/I | of ASO | of SO | of Zone officer; each cell "Name 9xxxxxxxxx". Records: the supervisor of each ward
    (level "ward"), and one record per sanitary inspector, assistant sanitation officer, sanitation officer and zone officer with
    the wards of their rows (level "ward").
  - Works: one table per Executive Engineer division (caption or a full-width row "OFFICE OF THE EXECUTIVE ENGINEER
    DIVISION - I, JMC"): S.No | Name of the
    officer/official | Designation | Contact No. | Jurisdiction ("Ward Nos. 1 to 11, 13, 14, 15, 19 & 71"). Records: level "ward"
    when the jurisdiction names wards, else level "division" (division = the EE division).
  - Officers: S. No. | Name | Designation | Phone No | Mobile No | Email ID (Commissioner, Joint and Deputy Commissioners, XENs,
    Health Officer, Senior Town Planner ...): level "body"; Deputy Commissioner (North / South): level "zone".
  - Enforcement: S.No. | Name of Officers (Deputy Commissioner of the zone) | I/c Chief Revenue Officer / Enforcement Officer |
    Enforcement Inspector with contact | Zone | Wards ("1, Panjtirthi | 2, Jullaka Mohalla | ..."). Records: one per enforcement
    inspector (level "ward") and one per enforcement officer (level "zone", wards = all wards of their rows).
Record ids: dept:ward2n_jammu:<page>:<wards or division or zone>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_jammu"
BODY, LGD, STATE, DISTRICT = "Jammu Municipal Corporation", "248194", "JK", "Jammu"
BASE = "https://jmc.jk.gov.in/contactus.aspx?type="
PAGES = ("Sanitation", "Works", "Officers", "Enforcement")
PH = re.compile(r"(?<!\d)(?:[6-9]\d{4}-?\d{5}|0?191-?\d{7}|25\d{5})(?!\d)")
SAN_POSTS = (("supervisor", "Sanitation Supervisor"), ("s/i", "Sanitary Inspector"), ("aso", "Assistant Sanitation Officer"),
             ("so", "Sanitation Officer"), ("zone officer", "Zone Officer"))


def items(get=None):
    return [{"key": f"{MODULE}-{t.lower()}", "payload": {"reader": MODULE, "url": BASE + t, "page": t, "state": STATE}} for t in PAGES]


def name_phone(cell):
    """("Gulshan", "9086055589") from "Gulshan 9086055589" / "Philips Sotra7006730647" / "S. Joginder Singh | 9906335876"."""
    t = _esw.clean(cell.replace("|", " "))
    phones = PH.findall(t)
    name = _esw.clean(PH.sub(" ", t)).strip(" ,-(")
    name = re.sub(r"\(\s*(E\.?O\.?)?\s*\)?\s*$", "", name).strip(" ,")
    return name, ", ".join(phones)


def ward_of(cell):
    w = re.sub(r"\s+", "", _esw.clean(cell)).strip(".").upper()
    m = re.fullmatch(r"(\d{1,3})(?:-?([A-Z]))?", w)
    return (str(int(m.group(1))) + (f"-{m.group(2)}" if m.group(2) else "")) if m else None


def div_name(text):
    """"DIVISION - II" / "DIVISION-V" / "PROJECTS DIVISION" -> "Division II" / "Division V" / "Projects Division"."""
    m = re.search(r"(?i)(PROJECTS\s+)?DIVISION(?:\s*[-–]\s*([IVX]+))?", text)
    return _esw.clean(("Projects " if m.group(1) else "") + "Division" + (f" {m.group(2).upper()}" if m.group(2) else ""))


def tables(html, *words):
    soup = _esw.soup(html)
    for t in soup.find_all("table"):
        g = _esw.grid(t)
        if g and all(any(w in c.lower() for c in g[0]) for w in words):
            yield t, [c.lower() for c in g[0]], g[1:]


def parse(html, p):
    page = p.get("page") or p["url"].rsplit("=", 1)[-1]
    seen, recs = set(), []
    kw = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=p["url"])
    pg = _esw.slug(page)

    def add(key, **f):
        recs.append(_ward.record(MODULE, f"{pg}:{key}", seen, **kw, **f))

    if page == "Sanitation":
        groups = {}
        for _, head, rows in tables(html, "ward", "supervisor"):
            idx = {post: next((i for i, h in enumerate(head) if re.search(rf"\bof\s+{re.escape(k)}\b", h)), None) for k, post in SAN_POSTS}
            wi = next(i for i, h in enumerate(head) if "ward" in h)
            for r in rows:
                w = ward_of(r[wi]) if wi < len(r) else None
                if not w:
                    continue
                for post, i in idx.items():
                    if i is None or i >= len(r) or not r[i].strip():
                        continue
                    name, phone = name_phone(r[i])
                    if not (name or phone):
                        continue
                    if post == "Sanitation Supervisor":
                        add(f"ward-{w}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", level="ward", area=f"Ward {w}", post=post,
                            name=name, phone=phone, wards=[w], wing="sanitation")
                    else:
                        g = groups.setdefault((post, name, phone), [])
                        if w not in g:
                            g.append(w)
        for (post, name, phone), ws in groups.items():
            wing = "health" if re.search(r"(?i)^dr\.", name) and post == "Zone Officer" else "sanitation"
            add(f"{_esw.slug(post)}:{_esw.slug(name) or 'n'}", level="ward", area="Wards " + ", ".join(ws), post=post, name=name,
                phone=phone, wards=ws, wing=wing)
    elif page == "Works":
        for t, head, rows in tables(html, "name", "designation"):
            cap = _esw.clean(t.caption.get_text()) if t.caption else ""
            m = re.search(r"(?i)(PROJECTS\s+)?DIVISION(\s*[-–]\s*[IVX]+)?", cap)
            div = div_name(m.group(0)) if m else ""
            for r in rows:
                if len(set(r)) == 1:
                    m = re.search(r"(?i)(PROJECTS\s+)?DIVISION(\s*[-–]\s*[IVX]+)?", r[0])
                    div = div_name(m.group(0)) if m else div
                    continue
                d = dict(zip(head, r))
                name, post = _ward.col(d, "name"), _ward.col(d, "designation")
                phone, jur = _ward.col(d, "contact"), _ward.col(d, "jurisdiction")
                if not post or not (name or phone) or post.lower() == "designation":
                    continue
                ws = _ward.wards_of(jur) if re.search(r"(?i)ward", jur) else []
                area = ("Ward " + ", ".join(ws)) if ws else (f"Executive Engineer {div}" if div else BODY)
                level = "ward" if ws else ("division" if div else "body")
                add(f"{_esw.slug(div) or 'hq'}:{_esw.slug(post)}:{_esw.slug(name) or 'n'}", level=level, area=area, post=post,
                    name=name, phone=_esw.phones(phone), wards=ws or None, division=div or None, jurisdiction=jur or None,
                    wing=_ward.wing_of(post) if _ward.wing_of(post) != "other" else "engineering")
    elif page == "Officers":
        for _, head, rows in tables(html, "name", "designation"):
            for r in rows:
                d = dict(zip(head, r))
                name, post = _ward.col(d, "name"), _ward.col(d, "designation")
                if not post or not name or not re.search(r"[A-Za-z]", post):
                    continue
                z = re.search(r"\((North|South)\)", post)
                add(f"{_esw.slug(post)}:{_esw.slug(name)}", level="zone" if z else "body", area=f"{z.group(1)} Zone" if z else BODY,
                    zone=f"{z.group(1)} Zone" if z else None, post=post, name=name,
                    phone=_esw.phones(_ward.col(d, "phone"), _ward.col(d, "mobile")), email=_ward.col(d, "email"))
    elif page == "Enforcement":
        eos = {}
        for _, head, rows in tables(html, "inspector", "wards"):
            for r in rows:
                d = dict(zip(head, r))
                zone = _esw.clean(_ward.col(d, "zone").replace("|", " "))
                wtxt = _ward.col(d, "wards")
                ws = []
                for part in re.split(r"\s*\|\s*", wtxt):
                    m = re.match(r"\s*(\d{1,3})\s*(?:-?\s*([A-Z])\b)?", part)
                    if m and str(int(m.group(1))) not in ws:
                        ws.append(str(int(m.group(1))))
                ins, iph = name_phone(_ward.col(d, "inspector"))
                eo, eph = name_phone(_ward.col(d, "enforcement officer", "revenue officer"))
                eo = re.sub(r"[,\s]*\(?E\.?O\.?\)?$", "", eo).strip(" ,")
                if ins and ws:
                    add(f"ward-{'-'.join(ws)}:enforcement-inspector:{_esw.slug(ins)}", level="ward", area="Ward " + ", ".join(ws),
                        zone=zone or None, post="Enforcement Inspector", name=ins, phone=iph, wards=ws, ward_names=wtxt,
                        wing="planning")
                if eo:
                    g = eos.setdefault((eo, eph, zone), [])
                    g += [w for w in ws if w not in g]
        for (eo, eph, zone), ws in eos.items():
            add(f"{_esw.slug(zone) or 'zone'}:enforcement-officer:{_esw.slug(eo)}", level="zone", area=zone or BODY, zone=zone or None,
                post="Enforcement Officer", name=eo, phone=eph, wards=ws or None, wing="planning")
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, _esw.slug(p.get("page") or "page"), r.content)], "" if recs else "no contact table"
