"""District courts on the eCourts S3WaaS sites (<district>.dcourts.gov.in, 731 sites listed on ecourts.gov.in "District Courts"):
the judges of every court establishment and the court offices on the "Contact Us" page.

One queue item = one site. fetch() reads two pages of it:
- /list-of-judges/: one table per court establishment (caption "PATNA SADAR, CIVIL COURT", "SUB DIVISIONAL COURT BARH"),
  columns Name | Designation | Room Number | Location (the photo column and the column order differ between sites).
  One record per judge: post = designation, name, area = establishment, room, location, profile (the judge's own page).
- /contact-us/: free text or a table. Text: one record per block that has a phone or an email (the office line, the
  officer's name when the block gives one, the address); a table: one record per row.
Payload: url (site root), state, district. Record ids: dept:court_dcourts:<host>:j:<establishment>:<name> (judges) and
dept:court_dcourts:<host>:c:<n> (contact blocks). dept "courts", level "district" for the district seat, "subdivision" for
sub-divisional / taluk / outlying courts. Seed: seeds/dept_court_dcourts.json (ecourts.gov.in state lists, archive copy
2026-11-06). No masking: names, phones and emails are kept as the page writes them.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from dforms import _civic, _esw
from dforms.police_s3waas import last_updated

MODULE = "court_dcourts"
SUB = re.compile(r"sub[- ]?divisional|\bsdjm\b|\bsdm\b|outlying|taluk|taluka|tehsil|tahsil|munsif|munsiff|gram nyayalaya|"
                 r"link court|\bbranch\b|camp court|civil court (?:jr|junior)", re.I)
TITLE = r"(?:hon'?ble\s+)?(?:shri|smt|sri|smti|kumari|km|mr|mrs|ms|miss|dr|thiru|tmt|selvi|kum|sh|janab)(?:\.\s*|\s+)"
HONOR = re.compile(rf"^(?:{TITLE})+", re.I)
GENERIC_CAP = re.compile(r"(?i)^(list of judges|judges|judicial officers|list of judicial officers|profile|name|)$")
PLACEWORD = re.compile(r"(?i)court|judge|magistrate|sessions|civil|criminal|special|spl|addl|additional|principal|division|act|"
                       r"cases|incharge|i/c|tribunal|family|labour|small|cause|chief|judicial|junior|senior|exclusive|fast|track|"
                       r"\bcum\b|pocso|ndps|\bsc\b|\bst\b|mact|\bjm\b|cjm|acjm|\bsd\b|\bjd\b|\bno\b|\d|floor|block|building|wing|complex|"
                       r"campus|hall|annex|dlsa|\bdivn?\b|\bdn\b|\bftc\b|jjb|\blok\b|adalat|secretary|room|\bpin\b|p\.o|\bps\b|"
                       r"\bsr\b|\bjr\b|vacant|leave|authority|services|india|district|board|juvenile|justice|crime|women|metropolitan")
SEAT = re.compile(r"(?i)^(?:(?:sub[- ]?divisional|civil|district|munsif|munsiff|outlying|taluka?|tehsil|link|camp)\s+)+"
                  r"(?:court|courts|court complex)\s+(?:at\s+)?([A-Za-z][A-Za-z .-]+)$")
LATLON = re.compile(r"(?i)\b(lat|long)\w*\s*[:.-]*\s*(\d{1,2}\.\d{3,})")
HEAD = re.compile(r"court|office|judge|registrar|officer|magistrate|nazir|tribunal|complex|establishment|sewa|seva|legal services|"
                  r"\bdlsa\b|\btlsc\b|adalat|registry|superintendent|clerk|sheristadar|administrative|\bsystem\b|e-?courts|"
                  r"copying|record room|central project|\bcpc\b|mediation|nyayalaya", re.I)
COLS = [("designation", r"designation|^post$|court name|name of (the )?(court|office|establishment)|^court$|^office"),
        ("name", r"^name|judge|officer'?s? name|name of (the )?(judge|officer|presiding)"),
        ("room", r"room"), ("location", r"location|place|station|^at$"), ("email", r"e-?\s?mail"),
        ("phone", r"phone|mobile|contact|tele|landline|fax|cug"), ("address", r"address")]


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def level_of(*texts):
    return "subdivision" if any(t and SUB.search(t) for t in texts) else "district"


def town_of(district, *texts):
    """The town a court sits in when the post or location names one that is not the district: 'Civil Judge [Junior Division],
    Darsi' (district Prakasam) -> 'Darsi'. None when the text names only the district or no place."""
    dn = re.sub(r"[^a-z]", "", (district or "").lower())
    for t in texts:
        if not t:
            continue
        for seg in reversed(re.split(r"[,(]", t.rstrip(" .)"))):
            seg = _esw.clean(seg).strip(" .-")
            m = SEAT.match(seg)
            seg = m.group(1) if m else seg
            k = re.sub(r"[^a-z]", "", seg.lower())
            if seg.lower() in _civic.STATES:
                continue
            if dn and k and (dn in k or k in dn) and not PLACEWORD.search(seg):
                continue                                  # the district itself: look one part further left
            if not seg or len(seg) > 30 or len(k) < 3 or PLACEWORD.search(seg) or re.match(TITLE, seg + " ", re.I) or not re.fullmatch(r"[A-Za-z][A-Za-z .-]+", seg):
                break
            return seg.title() if seg.isupper() else seg
    return None


def person(s):
    """'MS. ANAMIKA T.' -> 'ANAMIKA T.'; 'Smt. A. S. Shende' -> 'A. S. Shende' (the honorific is a title, not part of the name)."""
    s = _esw.clean(s)
    return HONOR.sub("", s).strip(" ,-") or s


def col_kinds(head):
    out = []
    for h in head:
        h = _esw.clean(h).lower()
        k = next((k for k, pat in COLS if re.search(pat, h)), None)
        out.append(k if k not in out else None)
    return out


def judges(html, url, p):
    """One record per row of every /list-of-judges/ table."""
    host = urlparse(url).netloc
    lu = last_updated(html)
    soup = _esw.soup(html)
    recs, seen = [], set()
    for t in soup.select("table"):
        cap = t.find("caption")
        est = _esw.clean(cap.get_text(" ")) if cap else ""
        est = "" if GENERIC_CAP.match(est) else est
        head = [th.get_text(" ") for th in t.select("thead th")]
        rows = t.select("tbody tr") or t.find_all("tr")[1:]
        if not head:
            first = t.find("tr")
            head = [c.get_text(" ") for c in first.find_all(["th", "td"])] if first else []
        kinds = col_kinds(head)
        if "name" not in kinds:
            continue
        for tr in rows:
            tds = tr.find_all(["td", "th"], recursive=False)
            if len(tds) < 2:
                continue
            f, prof = {}, None
            for k, td in zip(kinds, tds):
                if k:
                    f[k] = _esw.cell_text(td).replace(" | ", ", ")
                if k == "name" and td.find("a", href=True):
                    prof = td.find("a", href=True)["href"]
            name = person(f.get("name"))
            vac = bool(re.search(r"(?i)\bvacant\b", f.get("name") or ""))
            name = None if vac else name
            if (not name or name.lower() in ("name", "-", "--")) and not vac:
                if not f.get("designation"):
                    continue
                name = None
            key = _esw.slug(f"{host}:j:{est[:60]}:{name or f.get('designation')}")[:180]
            key = unique(key, seen)
            town = town_of(p.get("district"), f.get("location"), f.get("designation"), est)
            recs.append(_esw.record(
                MODULE, key, dept="courts", level="subdivision" if town else level_of(est, f.get("location")),
                area=est or f.get("location") or p.get("district"), town=town,
                post=f.get("designation"), name=name, vacant=vac or None,
                establishment=est, room=f.get("room"), location=f.get("location"), profile=prof,
                phone=_esw.phones(f.get("phone") or ""), email=_esw.emails(f.get("email") or ""),
                state=p.get("state"), district=p.get("district"), office_id=key, source=url, last_updated=lu, kind="judge"))
    return recs


def unique(key, seen):
    k, n = key, 1
    while k in seen:
        n += 1
        k = f"{key}-{n}"
    seen.add(k)
    return k


def lines_of(node):
    """Text lines of a content node: <br>, paragraphs, list items and headings each end a line."""
    for br in node.find_all("br"):
        br.replace_with("\n")
    for b in node.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"]):
        b.insert_after("\n")
    out = []
    for ln in node.get_text("").split("\n"):
        ln = _esw.clean(ln)
        if ln and not re.match(r"(?i)^(contact us|share on .*|share of x.*|home|about court)$", ln):
            out.append(ln)
    return out


def contact_tables(node, url, p, lu, host, seen):
    recs = []
    for t in node.find_all("table"):
        g = _esw.grid(t)
        if len(g) < 2:
            continue
        hi = next((i for i, r in enumerate(g[:3]) if {"email", "phone"} & set(col_kinds(r))
                   and sum(1 for k in col_kinds(r) if k) >= 2), None)
        if hi is None:
            continue
        kinds = col_kinds(g[hi])
        for row in g[hi + 1:]:
            f = {k: v for k, v in zip(kinds, row) if k}
            ph, em = _esw.phones(f.get("phone", "")), _esw.emails(" ".join(row))
            if not (ph or em):
                continue
            office = f.get("designation") or f.get("location") or f.get("name") or next(
                (c for c in row if c and not re.fullmatch(r"[\d. ]+", c) and "@" not in c and "[at]" not in c), "")
            key = unique(_esw.slug(f"{host}:c:{office[:80]}") or f"{host}:c", seen)
            name = person(f.get("name")) if f.get("name") and f.get("designation") else None
            town = town_of(p.get("district"), office)
            recs.append(_esw.record(
                MODULE, key, dept="courts", level="subdivision" if town else level_of(office, f.get("address")), area=office,
                post=office, name=name, town=town,
                phone=ph, email=em, address=f.get("address"), state=p.get("state"), district=p.get("district"), office_id=key,
                source=url, last_updated=lu, kind="office"))
        t.decompose()
    return recs


NAME_LINE = re.compile(rf"^(?:{TITLE})+([A-Za-z][A-Za-z. ]{{2,60}}?)(?:\s*[,(-]\s*(.+?))?\)?$", re.I)
CONTACT = re.compile(r"(?i)e-?\s?mail|phone|mob|tel|fax|contact no|ph\.|cell|landline|@|\[at\]")


def contacts(html, url, p):
    """Contact Us: one record per office block (text) or table row with a phone or an email."""
    host = urlparse(url).netloc
    lu = last_updated(html)
    soup = _esw.soup(html)
    node = soup.select_one("#row-content") or soup.find("main") or soup.body
    if node is None:
        return []
    for x in node(["script", "style", "nav", "form", "img"]):
        x.decompose()
    for x in node.select(".switchViewHead, .share-links, .social-share, .socialShare, .breadcrumb"):
        x.decompose()
    seen = set()
    recs = contact_tables(node, url, p, lu, host, seen)
    blocks, cur = [], []
    for ln in lines_of(node):
        has = any(CONTACT.search(x) for x in cur)
        if cur and has and HEAD.search(ln) and not CONTACT.search(ln) and len(ln) < 160:
            blocks.append(cur)
            cur = []
        cur.append(ln)
    if cur:
        blocks.append(cur)
    for b in blocks:
        text = " | ".join(b)
        ll = [float(m.group(2)) for m in LATLON.finditer(text)]
        b = [LATLON.sub(" ", x) for x in b]
        ph, em = _esw.phones(*[x for x in b if not re.search(r"(?i)pin|^\s*\d{6}\s*$", x) or re.search(r"(?i)ph|mob|tel", x)]), \
            _esw.emails(text)
        if not (ph or em):
            continue
        office = next((x for x in b if HEAD.search(x) and not CONTACT.search(x) and not NAME_LINE.match(x)), b[0])
        name, post = None, None
        for x in b:
            m = NAME_LINE.match(x)
            if m and not CONTACT.search(x):
                name, post = _esw.clean(m.group(1)).strip(" ,."), _esw.clean(m.group(2) or "") or None
                break
        if NAME_LINE.match(office):
            office = f"District Court {p.get('district')}" if p.get("district") else ""
        adr = ", ".join(x for x in b if x is not office and not CONTACT.search(x) and not NAME_LINE.match(x))
        key = unique(_esw.slug(f"{host}:c:{office[:80]}") or f"{host}:c", seen)
        town = town_of(p.get("district"), office)
        recs.append(_esw.record(
            MODULE, key, dept="courts", level="subdivision" if town else level_of(office), area=office, town=town,
            lat=next((x for x in ll if 6 < x < 37.6), None), lon=next((x for x in ll if 68 < x < 97.5), None),
            post=post or office, name=name, phone=ph, email=em,
            address=adr[:400], text=text[:1000], state=p.get("state"), district=p.get("district"), office_id=key, source=url,
            last_updated=lu, kind="office"))
    return recs


def fetch(p, get):
    base = p["url"].rstrip("/")
    host = urlparse(base).netloc
    recs, files, why = [], [], []
    for path, parse in (("/list-of-judges/", judges), ("/contact-us/", contacts)):
        u = base + path
        r = get(u)
        if r is None:
            why.append(f"no answer {path}")
            continue
        files.append(_esw.keep(MODULE, f"{host}-{path.strip('/')}", r.content))
        got = parse(r.text, u, p)
        if not got:
            why.append(f"no rows {path}")
        recs += got
    return recs, files, "" if recs else "; ".join(why) or "no rows"
