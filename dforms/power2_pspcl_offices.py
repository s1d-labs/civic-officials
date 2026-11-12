"""Punjab: PSPCL (Punjab State Power Corporation Ltd) distribution offices down to the sub-division, three public sources (three
queue items). Not India-only (all three answered from Germany on 2026-11-11; plain TLS). No officer names in any of them: PSPCL
publishes posts and office phones only. (power2_pspcl reads the heads-of-offices page Contact-Hods.aspx: zones and circles.)

- "pio": www.pspcl.in/pdfs/twenty-twentytwo/06/Recent_Updated_PIO_List10092025.pdf, "LIST OF APPELLATE AUTHORITIES / PIO'S /
  APIO'S UNDER PSPCL PATIALA" (37 pages, PDF dated 2025-09-11). One numbered row per office post: S.No. | Name of the Present Post
  (e.g. "AEE/OP.S/d. Sanour") | Designated (Appellate Authority / PIO / APIO) | Office Address | Office Phone No. (landline and
  CUG mobile) | Fax | E-mail. A post cell and a phone cell often wrap over 2-3 lines. Rows 1-174 are head-office cells, then the
  five distribution zones in order: CE/South (175), CE/DS Central (320), CE/DS North (425), CE/DS Border (555), CE/DS West (695),
  then thermal plants, transmission and P&M (825+). Kept: the five zone blocks (about 650 posts): CE (zone), Dy.CE/DS circle heads
  and circle staff (circle), Addl.SE / Sr.Xen DS divisions (division), AEE / AE operation, technical and commercial
  sub-divisions (subdivision). Parents (zone, circle, division) follow the order of the rows. "-do-" in the address column repeats
  the address above. Record id dept:power2_pspcl_offices:pio:<e-mail local part, else post>.
- "hierarchy": pspcl.in/admin/Hierarchies20261201302.pdf (14 pages, PDF dated 2026-02-13; page 1 is a scanned covering letter).
  Six zone tables (Border, Central, North, South, West, East) with one row per sub-division: S.No. | zone code + name | circle code +
  name | division code + name | UBS (sub-division) code + RSG name | legacy code | SAP / Non-SAP | postal code | ME lab ... About
  512 sub-divisions. Records: one per zone, circle, division and sub-division (office_id = the PSPCL code, the PIN as "pincode",
  parents by name). Record id dept:power2_pspcl_offices:h:<code>.
- "ncc": www.pspcl.in/Otherlinks/nodal-complaint-centres.aspx: one table, a one-cell row per circle ("Tarantaran Circle/Border
  Zone"), then Sr. No. | Division | Nodal Complaint Centre (NCC) Number | Addl. SE/Sr. Xen Contact Number. About 120 divisions; one
  record per division (level division, post "Addl. SE / Sr. Xen", phone = the Xen's number, "complaint_phone" = the NCC numbers).
  The site footer "Updated on: DD-MM-YYYY" is the last_updated. Record id dept:power2_pspcl_offices:ncc:<circle>:<division>.
"""
import io
import re

from bs4 import BeautifulSoup

from dforms._power import Out, cells, clean, email, pdf_pages, phone, raw, slug

METHOD = "pdf text (pypdf) + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "power2_pspcl_offices"
URLS = {"pio": "https://www.pspcl.in/pdfs/twenty-twentytwo/06/Recent_Updated_PIO_List10092025.pdf",
        "hierarchy": "https://pspcl.in/admin/Hierarchies20261201302.pdf",
        "ncc": "https://www.pspcl.in/Otherlinks/nodal-complaint-centres.aspx"}
ZONE_HEAD = re.compile(r"(?i)^C\.?\s?E\.?\s*/\s*(?:DS\b)?\s*[,-]?\s*(South|Central|North|Border|West|East)\b")
ROLE = re.compile(r"^(Appellate|PIO|APIO)\b")
RANK = re.compile(r"(?i)^(A\.?\s?E\.?\s?E|A\.?\s?E|S\s*r[,.\s]*xen|Addl?\.?\s*S\.?\s?E\.?|ASE|Dy\.?\s*C\.?\s?E\.?"
                  r"|C\.?\s?E\.?|S\.?\s?E\.?|XEN)\s*/?\s*")
DIVN = re.compile(r"(?i)DIV(N|ISION)?\b|Di\s?v\b|\bDn\b|/\s*DS\b")
XEN = re.compile(r"(?i)^(S\s*r[,.\s]*xen|Addl?\.?\s*S\.?\s?E|ASE|XEN)")
CIRCLE_HEAD = re.compile(r"(?i)^(Dy\.?\s*C\.?\s?E\.?|S\.?\s?E)\b.*circle|^Dy\.?\s*C\.?\s?E\.?\s*/?\s*(DS|OP)\b")


def items(get=None):
    return [{"key": f"{MODULE}:{k}", "payload": {"reader": MODULE, "page": k, "url": u, "state": "PB", "india_only": False}}
            for k, u in URLS.items()]


def pdf_date(content):
    """The PDF's own modification (or creation) date, YYYY-MM-DD."""
    try:
        from pypdf import PdfReader
        m = PdfReader(io.BytesIO(content)).metadata or {}
        for k in ("/ModDate", "/CreationDate"):
            d = re.search(r"(\d{4})(\d{2})(\d{2})", str(m.get(k) or ""))
            if d:
                return f"{d.group(1)}-{d.group(2)}-{d.group(3)}"
    except Exception:
        pass
    return None


# ---- PIO list

def chunks(line):
    """[(start column, text)] of the parts of a layout line that are 2+ spaces apart."""
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def is_phone(t):
    return bool(re.fullmatch(r"[\d\s()+,/-]*\d{5,}[\d\s()+,/-]*|\d{4,6}[- ]?\d{5,}", t.replace(" ", ""))) or \
        bool(re.fullmatch(r"\d{2,5}\s?-\s?\d{5,8}", t))


def pio_rows(pages):
    """One dict per numbered row: sno, post, role, address, phones, email."""
    rows, cur = [], None
    for page in pages:
        for line in page.splitlines():
            cs = chunks(line)
            if not cs:
                continue
            ri = next((i for i, (_, t) in enumerate(cs) if ROLE.match(t) and re.fullmatch(r"(Appellate|PIO|APIO)\b.*", t)), None)
            if ri is None and len(cs) >= 2 and re.match(r"^\S+\s+(Appellate|PIO|APIO)\b", cs[1][1]):
                # "Sr.XEN/Technical West APIO": post and role in one chunk
                t = cs[1][1]
                m = re.match(r"^(.*\S)\s+((?:Appellate|PIO|APIO)\b.*)$", t)
                cs = [cs[0], (cs[1][0], m.group(1)), (cs[1][0] + len(m.group(1)) + 1, m.group(2))] + cs[2:]
                ri = 2
            if ri is not None:
                head = cs[:ri]
                sno = head[0][1].rstrip(".") if head and re.fullmatch(r"\d{1,3}\.?\s*[A-Z]?\.?", head[0][1]) else None
                post_parts = [t for _, t in (head[1:] if sno else head)]
                role_t = cs[ri][1]
                role = ROLE.match(role_t).group(1)
                rest = cs[ri + 1:]
                extra = role_t[len(role):].strip()          # "Appellate Autho Shakti Vihar": address glued to the role
                if extra and not re.match(r"(?i)autho", extra):
                    rest = [(cs[ri][0] + len(role) + 1, extra)] + rest
                cur = {"sno": sno, "post": post_parts, "role": role, "address": [], "phones": [], "email": "",
                       "rc": cs[ri][0], "pc": None}
                rows.append(cur)
                for pos, t in rest:
                    _cell(cur, pos, t, first=True)
                continue
            if cur is None:
                continue
            if re.match(r"(?i)^note\b", cs[0][1]):
                cur = None
                continue
            for pos, t in cs:
                if pos < cur["rc"] - 1:
                    if re.fullmatch(r"\d{1,3}\.?", t) and not cur["sno"]:
                        cur["sno"] = t.rstrip(".")
                    elif not re.fullmatch(r"\d{1,3}\.?", t):
                        cur["post"].append(t)
                else:
                    _cell(cur, pos, t)
    return rows


def _cell(cur, pos, t, first=False):
    if "@" in t or re.fullmatch(r"[a-z0-9._]+(-[a-z0-9._]+)*-", t) or (cur["email"].endswith("-") and re.fullmatch(r"[\w.@-]+", t)):
        cur["email"] += t.replace(" ", "")
        return
    if re.fullmatch(r"(?i)authority|autho\w*", t):
        return
    if is_phone(t) or re.fullmatch(r"\d{6,8}", t):
        if cur["pc"] is None:
            cur["pc"] = pos
        if cur["pc"] is not None and pos > cur["pc"] + 12 and not first:
            return                                          # the fax column
        if first and len(cur["phones"]) >= 1:
            return                                          # fax on the first line
        cur["phones"].append(t)
        return
    if t in ("-", "--") or re.fullmatch(r"0\d{2,4}\s?-?", t):
        return                                              # empty fax, or a fax code cut by the line end
    if cur["pc"] is not None and pos >= cur["pc"] - 2:
        return
    cur["address"].append(t)


def pio_level(post, ctx):
    """zone / circle / division / subdivision from the post; ctx (the block's circle or zone) for staff posts like "Addl.SE/Tech"."""
    if ZONE_HEAD.match(post):
        return "zone"
    if re.match(r"(?i)^A\.?\s?E\.?\s?E|^A\.?\s?E\b|^AEE?(?=[A-Z])", post):
        return "subdivision"
    if re.search(r"(?i)/\s*HQ\b", post):
        return ctx if ctx == "zone" else "circle"
    if CIRCLE_HEAD.search(post):
        return "circle"
    if XEN.match(post) and DIVN.search(post):
        return "division"
    return ctx


def parse_pio(pages, url=URLS["pio"], last_updated=None):
    out = Out(MODULE, "PB", url, discom="PSPCL", last_updated=last_updated)
    keep, zone, circle, division, prev_addr = False, None, None, None, None
    for r in pio_rows(pages):
        post = clean(" ".join(r["post"]).replace(" /", "/").replace("/ ", "/"))
        if not post:
            continue
        addr = clean(" ".join(r["address"]))
        if addr and re.fullmatch(r"(?i)-?\s*do\s*-?", addr):
            addr = prev_addr
        prev_addr = addr or prev_addr
        if r["role"] == "Appellate":
            m = ZONE_HEAD.match(post)
            keep = bool(m)
            if m:
                zone, circle, division = f"{m.group(1).title()} Zone", None, None
        if not keep:
            continue
        ctx = "circle" if circle else "zone"
        lvl = "zone" if r["role"] == "Appellate" else pio_level(post, ctx)
        area = clean(RANK.sub("", post, count=1)) or post
        if lvl == "zone":
            area = zone if r["role"] == "Appellate" else area
        if lvl == "circle" and CIRCLE_HEAD.search(post):
            circle, division = area, None
        if lvl == "division":
            division = area
        par = {"zone": zone if lvl != "zone" else None, "circle": circle if lvl in ("division", "subdivision") else None,
               "division": division if lvl == "subdivision" else None}
        em = email(r["email"])
        key = "pio:" + (em.split("@")[0] if em else slug(post))
        out.add(key, lvl, area, post=post, phone_=phone(*r["phones"]), email_=em, address=addr, parents=par,
                pio_role=r["role"], list_no=r["sno"])
    return out.recs


# ---- hierarchy

HROW = re.compile(r"^\s*\d+\s+([1-6])\s+([A-Za-z]+)\s+(\d{2})\s+(\S.*?)\s+(\d{3})\s+(\S.*?)\s+(\d{4})\s+(\S.*?)(?=\s{2,}|$)(.*)$")


def parse_hierarchy(pages, url=URLS["hierarchy"], last_updated=None):
    out = Out(MODULE, "PB", url, discom="PSPCL", last_updated=last_updated)
    seen = set()
    for line in "\n".join(pages).splitlines():
        m = HROW.match(line)
        if not m:
            continue
        zc, zn, cc, cn, dc, dn, sc, sn, rest = m.groups()
        if not (cc.startswith(zc) and dc.startswith(cc) and sc.startswith(dc)):
            continue
        zn = f"{zn.title()} Zone"
        cn, dn, sn = (clean(x) for x in (cn, dn, sn))
        pin = re.search(r"\b(1[4-6]\d{4})\b", rest or "")
        for code, lvl, name, par in ((zc, "zone", zn, {}), (cc, "circle", cn, {"zone": zn}),
                                     (dc, "division", dn, {"zone": zn, "circle": cn})):
            if code not in seen:
                seen.add(code)
                out.add(f"h:{code}", lvl, name, post={"zone": "Chief Engineer / DS", "circle": "Dy. CE / DS (circle head)",
                                                      "division": "Addl. SE / Sr. Xen (DS)"}[lvl], office_id=code, parents=par or None)
        if sc in seen:
            continue
        seen.add(sc)
        lvl = "section" if re.match(r"(?i)sub\s*office", sn) else "subdivision"
        out.add(f"h:{sc}", lvl, sn, post="AEE / AE (sub-division)" if lvl == "subdivision" else "Sub office",
                office_id=sc, parents={"zone": zn, "circle": cn, "division": dn}, pincode=pin.group(1) if pin else None)
    return out.recs


# ---- nodal complaint centres

def parse_ncc(html, url=URLS["ncc"]):
    soup = BeautifulSoup(html, "lxml")
    m = re.search(r"Updated on:\s*(?:<[^>]+>)?\s*(\d{2})-(\d{2})-(\d{4})", html)
    out = Out(MODULE, "PB", url, discom="PSPCL", last_updated=f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None)
    circle, zone = None, None
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr"):
            c = cells(tr)
            if len(c) == 1 and c[0]:
                parts = [clean(x) for x in c[0].split("/")]
                circle, zone = parts[0], (parts[1] if len(parts) > 1 else None)
                continue
            if len(c) < 4 or not re.match(r"^\d+\.?$", c[0]) or not circle:
                continue
            div = clean(c[1])
            if not div:
                continue
            out.add(f"ncc:{circle}:{div}", "division", div, post="Addl. SE / Sr. Xen", phone_=phone(*re.split(r"\s+(?=\d)", c[3])),
                    parents={"zone": zone, "circle": circle},
                    complaint_phone=phone(*re.split(r"\s+(?=\d)", c[2])))
    return out.recs


def fetch(p, get):
    page = p.get("page", "pio")
    url = p.get("url") or URLS[page]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if page == "ncc":
        recs = parse_ncc(r.text, url)
        return recs, [raw(MODULE, "ncc", r.content, "html")], "" if recs else "no rows"
    if not r.content.startswith(b"%PDF"):
        return [], [raw(MODULE, page, r.content, "html")], "not a pdf"
    files = [raw(MODULE, page, r.content, "pdf")]
    pages, upd = pdf_pages(r.content), pdf_date(r.content)
    recs = parse_pio(pages, url, upd) if page == "pio" else parse_hierarchy(pages, url, upd)
    return recs, files, "" if recs else "no rows"
