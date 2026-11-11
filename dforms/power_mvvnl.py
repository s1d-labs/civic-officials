"""MVVNL (Madhyanchal Vidyut Vitran Nigam, central Uttar Pradesh). Works from Germany. Two queue items (payload "part"):
- "directory": mvvnl.in/post/en/directory?cd=NQA2AA%3d%3d, one HTML page with one table per zone (Sitapur, Raebareli, Ayodhya,
  Bareilly 1 and 2, Devipatan, store and workshop circles). Header rows name the zone and the circle ("ELECTRICITY DISTRIBUTION
  CIRCLE - X"); rows = S.No, title, name, designation, district, area, phone, email. Chief Engineer = zone, Superintending
  Engineer = circle, Executive Engineer = division: about 140 rows. The Head Quarter, store and workshop tables are left out. The page also holds about
  360 sub-division rows (Assistant Engineer, EDSD) inside HTML comments: public page source, so they are read too.
- "lesa": the Lucknow (LESA) telephone directory PDF (50 pages, Dec 2025): zone officer tables (CE, SE, EE with office
  address and mobile), the AE of each sub-division under its EE division, and the JE (33 kV / 11 kV and LT) offices with the
  33/11 kV sub-stations they look after. No names. About 50 zone officers, 60 AE and 150 JE rows.
Record ids dept:power_mvvnl:<zone>:<designation>:<area> (directory) and dept:power_mvvnl:lesa:<zone>:<designation> (PDF).
"""
import re

from bs4 import BeautifulSoup

from dforms._pdftext import cut, layout_pages
from dforms._power import Out, cells, clean, email, phone, raw

MOD = "power_mvvnl"
DIR_URL = "https://mvvnl.in/post/en/directory?cd=NQA2AA%3d%3d"
LESA_URL = "https://mvvnl.in/site/writereaddata/siteContent/202512061655264596Lesa-Direcotary_061225.pdf"
MOBILE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def level(post):
    p = (post or "").lower().replace(" ", "")
    if p.startswith("chiefengineer") or p.startswith("ce("):
        return "zone"
    if p.startswith("superintending") or p.startswith("se("):
        return "circle"
    if p.startswith("executiveengineer") or p.startswith("execu") or p.startswith("ee("):
        return "division"
    if p.startswith("assistantengineer") or p.startswith("ae("):
        return "subdivision"
    if p.startswith("je(") or p.startswith("juniorengineer"):
        return "section"
    return None


def parse_directory(html, url=DIR_URL):
    out = Out(MOD, "UP", url, discom="MVVNL")
    # rows inside HTML comments (about 360 sub-divisions) are part of the public page source: read them too (owner 2026-11-11)
    soup = BeautifulSoup(re.sub(r"(?s)<!--(.*?)-->", r"\1", html), "lxml")
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if not trs or len(trs) < 3:
            continue
        zone = clean(cells(trs[0])[0]) if len(cells(trs[0])) == 1 else None
        if not zone or re.search(r"(?i)head quarter|work allotment|store|workshop", zone):
            continue
        circle = cdist = None
        for tr in trs[1:]:
            c = cells(tr)
            if len(c) == 1:
                circle = clean(re.sub(r"(?i)^ELECTRICITY DISTRIBUTION CIRCLE\s*-\s*", "EDC ", c[0]))
                cdist = None
                continue
            if len(c) < 8 or not c[0].isdigit():
                continue
            title, name, post, dist, area, tel, mail = c[1], c[2], clean(c[3]), clean(c[4]), clean(c[5]), c[6], c[7]
            lvl = level(post)
            if not lvl:
                continue
            if dist and lvl in ("zone", "circle"):
                cdist = dist                     # the district is printed once, on the zone or circle row
            dist = dist or cdist
            nm = clean(name)
            if nm and title and not nm.lower().startswith(title.lower()):
                nm = f"{title} {nm}"
            par = {"zone": zone if lvl != "zone" else None, "circle": circle if lvl in ("division", "subdivision") else None}
            out.add(f"{zone}:{post}:{area}", lvl, area, post=post, name=nm, phone_=phone(tel), email_=email(mail),
                    district=dist.title() if dist else None, parents=par)
    return out.recs


def _hdr_pos(line, *words):
    for w in words:
        i = line.find(w)
        if i >= 0:
            return i
    return -1


def parse_lesa(pages, url=LESA_URL):
    """Zone officer tables, AE rows and JE blocks of the LESA directory (page text from pdftotext -layout or pypdf)."""
    out = Out(MOD, "UP", url, discom="MVVNL", last_updated="2025-12-06")
    zone = division = None
    for text in pages:
        lines = [ln.replace(" ", " ") for ln in text.splitlines()]
        mode, je, cols = None, None, None
        i = 0
        while i < len(lines):
            ln = lines[i]
            s = ln.strip()
            u = " ".join(s.split())
            m = re.fullmatch(r"([A-Z][A-Z .]+ ZONE)", u)
            if m:
                zone, mode = _fix(m.group(1).title()), None
                i += 1
                continue
            m = re.fullmatch(r"(.+?) Zone O\S*cers", u)
            if m:
                zone, mode = _fix(m.group(1).strip().title()) + " Zone", "officers"
                i += 1
                continue
            if re.fullmatch(r"EE\s*\(.*?\)\s*.+", u) and not MOBILE.search(u):
                division = _fix(u)
                i += 1
                continue
            if "Helpdesk" in u and "S.No" in u:
                mode = None
            if re.search(r"Helpdesk Name|Zone Helpdesk", u):
                mode = None
            if "JE Mobile" in ln or ("JE O" in ln and "Mobile" in ln):
                if je:
                    _je_flush(out, je, zone, division)
                je = None
                xo, xm, xs = _hdr_pos(ln, "JE O"), _hdr_pos(ln, "JE Mobile", "Mobile"), _hdr_pos(ln, "Name of")
                # the sub-station names often start a few characters left of their header; the JE mobile ends before them
                cols = [0, xo - 1, xm - 1, max(xm + 11, xs - 6)] if min(xo, xm, xs) > 0 else None
                mode = "je" if cols else None
                i += 1
                continue
            if re.search(r"O\S*cer Designa", u) and "Address" in u and mode != "officers":
                mode = "ae"
                i += 1
                continue
            if mode == "officers":
                m = re.match(r"\s*(\d{1,2})\s{2,}(\S.*)", ln)
                if m:
                    # "N  Chief Engineer   Indralok Hydel Colony,   9415901415": the designation wraps onto the next line
                    nxt = lines[i + 1] if i + 1 < len(lines) else ""
                    parts = [p for p in re.split(r"\s{2,}", m.group(2).strip()) if p]
                    nparts = [p for p in re.split(r"\s{2,}", nxt.strip()) if p] if not re.match(r"\s*\d{1,2}\s", nxt) else []
                    tels = MOBILE.findall(ln + " " + nxt)
                    post = " ".join([parts[0]] + ([nparts[0]] if nparts and not MOBILE.fullmatch(nparts[0]) else []))
                    post = _fix(post)
                    addr = " ".join([p for p in parts[1:] if not MOBILE.fullmatch(p)] +
                                    [p for p in nparts[1:] if not MOBILE.fullmatch(p)])
                    lvl = level(post)
                    if lvl:
                        out.add(f"lesa:{zone}:{post}", lvl, f"{post} ({zone})" if lvl != "zone" else zone, post=post,
                                phone_=", ".join(dict.fromkeys(tels)) or None, address=addr, district="Lucknow",
                                parents={"zone": zone if lvl != "zone" else None})
                    i += 2 if nparts else 1
                    continue
            if mode in ("ae", "je", None) and re.match(r"\s*\d{1,2}\s+AE\s*\(", ln) or re.match(r"\s{4,}AE\s*\(.*\d{10}", ln):
                post = _fix(" ".join(re.match(r"\s*(?:\d{1,2}\s+)?(AE\s*\(.*?\)\s*.*?)(?:\s{2,}|$)", ln).group(1).split()))
                tel = MOBILE.findall(ln) or (MOBILE.findall(lines[i + 1]) if i + 1 < len(lines) else [])
                rest = re.split(r"\s{2,}", ln.strip())
                addr = " ".join(p for p in rest[1:] if not MOBILE.fullmatch(p) and not p.startswith("AE"))
                out.add(f"lesa:{zone}:{post}", "subdivision", post, post=post, phone_=", ".join(tel) or None, address=addr,
                        district="Lucknow", parents={"zone": zone, "division": division})
                i += 1
                continue
            if mode == "ae" and re.match(r"\s*\d{1,2}\s*$", ln):
                # serial on its own line, the AE row follows
                i += 1
                continue
            if mode == "ae" and re.match(r"\s{4,}AE\s*\(", ln):
                post = _fix(" ".join(re.match(r"\s*(AE\s*\(.*?\)\s*.*?)(?:\s{2,}|$)", ln).group(1).split()))
                tel = MOBILE.findall(ln)
                out.add(f"lesa:{zone}:{post}", "subdivision", post, post=post, phone_=", ".join(tel) or None, district="Lucknow",
                        parents={"zone": zone, "division": division})
                i += 1
                continue
            if mode == "je" and cols and s:
                if re.match(r"\s{0,3}\d{1,2}(\s|$)", ln):
                    if je:
                        _je_flush(out, je, zone, division)
                    je = {"des": [], "addr": [], "mob": [], "ss": []}
                    ln = re.sub(r"^(\s{0,3})\d{1,2}", lambda mm: " " * len(mm.group(0)), ln, count=1)
                if je is not None:
                    a, b, c, d = cut(ln, cols)
                    je["des"].append(a)
                    je["addr"].append(b)
                    je["mob"].append(c)
                    je["ss"].append(d)
            i += 1
        if je:
            _je_flush(out, je, zone, division)
    return out.recs


def _fix(s):
    """pdf ligature gaps: "Execu ve" -> "Executive", "O cer" -> "Officer"."""
    s = re.sub(r"Execu\s*ve", "Executive", s)
    s = re.sub(r"Collec\s*on", "Collection", s)
    s = re.sub(r"Sta\s*on", "Station", s)
    s = re.sub(r"Administra\s*on", "Administration", s)
    s = re.sub(r"\bGom(\s+[Nn]agar)", r"Gomti\1", s)
    return " ".join(s.split())


def _je_flush(out, je, zone, division):
    des = _fix(" ".join(x for x in je["des"] if x))
    if not des.upper().startswith("JE"):
        return
    mob = MOBILE.findall(" ".join(je["des"] + je["addr"] + je["mob"]))
    ss = []
    for m_, x in zip(je["mob"], je["ss"]):
        x = (MOBILE.sub(" ", m_) + " " + x).strip()     # a sub-station name may start inside the mobile column
        for nm, tel in re.findall(r"([A-Za-z][A-Za-z0-9 .\-/()&]*?)\s+((?<!\d)[6-9]\d{9})", x):
            ss.append({"name": " ".join(nm.split()), "phone": tel})
    addr = _fix(MOBILE.sub(" ", " ".join(x for x in je["addr"] if x)))
    out.add(f"lesa:{zone}:{des}", "section", des, post="JE", phone_=", ".join(dict.fromkeys(mob)) or None, address=addr or None,
            district="Lucknow", parents={"zone": zone, "division": division}, substations=ss or None)


def fetch(p, get):
    url = p.get("url") or (LESA_URL if p.get("part") == "lesa" else DIR_URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    if p.get("part") == "lesa":
        files = [raw(MOD, "lesa-directory", r.content, "pdf")]
        if r.content[:5] != b"%PDF-":
            return [], files, "not a pdf"
        pages, _ = layout_pages(r.content)
        recs = parse_lesa(pages, url)
    else:
        files = [raw(MOD, "directory", r.content, "html")]
        recs = parse_directory(r.text, url)
    return recs, files, "" if recs else "no rows"
