"""District disaster management pages on S3WaaS sites (district portals' "Directory / Departments -> Disaster Management" page, the
template page ?p=2778 at /disaster-management/, and S3WaaS state authority pages such as usdma.uk.gov.in/eocs-contact/). The page
names the District Disaster Management Authority (DDMA) members, the District Disaster Management Officer (DDMO), the District
Emergency Operation Centre (DEOC) / control room numbers, toll free 1077, and on some pages the taluk / block control rooms.

Two forms on one page, both read:
- HTML tables inside the page body (div#post-NNNN): the header row names the columns (Name, Designation, Contact / Phone / Mobile
  / Telephone / Fax, E-mail, District / Taluka / Block / Centre ...). A table without a header row is read cell by cell (a cell
  with "Shri / Smt / Dr / Mr" is the name, a cell with an e-mail is the e-mail, a cell with numbers is a phone, the rest is the post).
  Tables of documents (Download / Link / File) and hazard profiles (no phone, no e-mail) give no rows.
- Plain text outside tables: "Name: ... | Designation: ... | Phone: ..." blocks (one officer each) and labelled numbers
  ("District Emergency Operation Centre : 06189-222080", "District Control Room Numbers: | Landline: ... | Mobile: ...").
Every record: dept disaster, layer emerg_ddma, level district (taluk / tehsil / block / mandal columns: subdistrict; sub-division:
subdivision), area = the row's place or the district, section = table caption or the heading before the table, post, name, phone,
fax, email, helpline (short codes 1077 / 1070 / 112 ... in the row). The DDMA lists often hold the other members too (SP, EE PWD,
CMO ...): they are kept, with their posts, because the page lists them as the district's disaster contacts.
The same table reader also reads plain (non-S3WaaS) state pages: payload "level": "state" (no district) gives level state and
area = payload "area"; with "area_is_district": true a row's place column is the district (USDMA's EOC and DM lists).
Seed: seeds/dept_emerg_ddma_s3waas.json (district portals of sites.csv + pages found by archive search; saved = archive.s1d.me
holds a copy with contacts on 2026-11-11). Record ids: dept:emerg_ddma_s3waas:<host>:<slug of section>:<slug of post / place>.
"""
import re
from urllib.parse import urlparse

from dforms import _emerg
from dforms.police_s3waas import last_updated

METHOD = "html table + html text (label lines)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "emerg_ddma_s3waas"

HEAD_WORDS = re.compile(r"(?i)\b(name|designation|post|contact|phone|mobile|tel|telephone|landline|e-?mail|mail id|officer|"
                        r"district|taluka?|tehsil|block|centre|center|address|fax|office|number|no\.?)\b")
DOC_HEAD = re.compile(r"(?i)\b(download|link|file|view|click|maps?|hazard|severity|damages|working hours|description|title)\b")
NAME_HINT = re.compile(r"(?i)^(shri|sri|sh|smt|smti|sushri|ms|mrs|mr|dr|er|km|kumari|miss|capt|col|lt|pu|pi|thiru|tmt|selvi|"
                       r"श्रीमती|श्री|सुश्री|डॉ[0०]?|कु[0०]|मो[0०])(?=[\s.,०0]|$)")
SERVICE = re.compile(r",?\s*\(?\b(IAS|IPS|IFS|MCS|PCS|HCS|RAS|WBCS|KAS|NCS|JCS|TCS|ACS|OCS|BAS|MPS|HPAS|PPS|IRS)\)?\.?$")
FIRE = re.compile(r"(?i)\bfire\b(?!.*\bdisaster\b)|अग्निशमन|दमकल")
YEARS = re.compile(r"^(19|20)\d\d\s*[-–/]\s*(19|20)?\d\d$")
SUBDIST = re.compile(r"(?i)\b(taluka?|tehsil|tahsil|block|mandal|circle|anchal)\b")
SUBDIV = re.compile(r"(?i)\b(sub-?division|subdivision)\b")


def col_kind(h):
    """What one header cell holds: name, post, namepost, phone, fax, email, area, address, serial, or '' (unknown)."""
    h = _emerg.clean(h).lower()
    if not h:
        return ""
    if re.fullmatch(r"(s\.?\s*no\.?|sl\.?\s*no\.?|sr\.?\s*no\.?|sno|serial.*|#|क्र.*|क्रम.*)", h):
        return "serial"
    if "name" in h and re.search(r"designation|post|officer", h) and not re.search(r"name of (the )?(office\b|centre|center|taluk|block)", h):
        return "namepost"
    if re.search(r"e-?\s?mail|mail id|ई-?मेल", h):
        return "email"
    if "fax" in h and not re.search(r"phone|tel|contact|mobile", h):
        return "fax"
    if re.fullmatch(r"(department|dept\.?|organi[sz]ation|agency)", h):
        return "org"
    if re.search(r"area to be covered|areas? covered|cover area|jurisdiction", h):
        return "covers"
    if re.search(r"name of (the )?(office\b|centre|center|taluka?|tehsil|block|department|agenc)|office name|center name|centre name|"
                 r"district|taluka?|tehsil|block|nagarpalika|zone|agencies|place|location|department|station|"
                 r"control room$|^centre$|^center$", h) and not re.search(r"number|no\.|phone|contact", h):
        return "area"
    if re.search(r"पदनाम|पद$", h):
        return "post"
    if re.search(r"name|नाम", h):
        return "name"
    if re.search(r"designation|post|position|role|officer|पद", h):
        return "post"
    if re.search(r"phone|mobile|contact|tel|landline|number|no\.|residence|office|helpline|मोबाइल|फोन|दूरभाष", h):
        return "phone"
    if "address" in h or "पता" in h:
        return "address"
    return ""


def is_header(row):
    kinds = [col_kind(c) for c in row]
    return sum(1 for k in kinds if k and k != "serial") >= 2 and not any(re.search(r"\d{6,}", c) for c in row)


def guess(cell):
    """Kind of a cell in a table without a header row."""
    c = _emerg.clean(cell)
    if not c or re.fullmatch(r"\d{1,3}\.?", c):
        return "serial"
    if _emerg.emails(c):
        return "email"
    if re.search(r"\d{5,}|\d{3,5}[- ]\d{5,8}", c) and len(re.sub(r"[\d\s,/()+-]", "", c)) < len(c) / 2:
        return "phone"
    if NAME_HINT.match(c):
        return "name"
    return "post"


def level_of(text):
    if SUBDIV.search(text or ""):
        return "subdivision"
    if SUBDIST.search(text or ""):
        return "subdistrict"
    return "district"


def section_of(table):
    cap = table.find("caption")
    if cap and _emerg.clean(cap.get_text(" ")):
        return _emerg.clean(cap.get_text(" "))[:150]
    prev = table.find_previous(["h1", "h2", "h3", "h4", "h5", "h6", "p", "strong", "b"])
    if prev and not prev.find_parent("table") and prev.name != "h1":
        t = _emerg.clean(prev.get_text(" "))
        if 3 <= len(t) <= 150 and not re.search(r"\d{6,}", t):
            return t
    return ""


def table_rows(table, where=None):
    """[{kind: text}] for each data row of one table (kinds from col_kind / guess). where (a list) gets each row's src_pos."""
    from dforms import _esw
    gp = []
    g = _esw.grid(table, pos=gp)
    if not g:
        return []
    hi = next((i for i, r in enumerate(g[:3]) if is_header(r)), None)
    if hi is not None:
        heads = g[hi]
        if any(DOC_HEAD.search(h) for h in heads) and not any(col_kind(h) in ("phone", "email") for h in heads):
            return []
        kinds = [col_kind(h) for h in heads]
        body, bpos = g[hi + 1:], gp[hi + 1:]
        heads_l = [_emerg.clean(h) for h in heads]
    else:
        kinds, body, heads_l, bpos = None, g, None, gp
    out = []
    for r, rp in zip(body, bpos):
        if heads_l and [_emerg.clean(c) for c in r] == heads_l:
            continue
        ks = kinds or [guess(c) for c in r]
        d = {}
        for i, c in enumerate(r):
            k = ks[i] if i < len(ks) else ""
            c = _emerg.clean(c)
            if not c or k == "serial":
                continue
            if not k:
                k = guess(c)
                if k == "post" and kinds:
                    k = "extra"
            if heads_l and k in ("phone", "fax", "extra", "area") and i < len(heads_l):
                # keep the column label for phone kinds (Office / Residence / Mobile)
                d.setdefault(k + "_labels", []).append(heads_l[i])
            if c not in d.get(k, []):
                d.setdefault(k, []).append(c)
        out.append(d)
        if where is not None:
            where.append(rp)
    return out


def split_namepost(v):
    """'Shri Gaurav Kumar, District Magistrate' / 'Shri X (DDMO)' / 'DDMO - Shri X' -> (name, post)."""
    v = _emerg.clean(v)
    m = re.match(r"^(.*?)\s*[,(|/-]\s*(.+?)\)?$", v)
    if m and NAME_HINT.match(m.group(1)):
        return m.group(1).strip(" ,"), m.group(2).strip(" ,()")
    if m and NAME_HINT.match(m.group(2)):
        return m.group(2).strip(" ,"), m.group(1).strip(" ,")
    return (v, "") if NAME_HINT.match(v) else ("", v)


def is_name(x):
    return bool(NAME_HINT.match(x) or SERVICE.search(x))


def people(d):
    """(name, post) of one table row: name / post / name-and-post cells, split where a cell holds both ("Pu X, MCS | SDO (Civil)",
    "Shri X, District Magistrate")."""
    names, posts = [], []
    for k in ("name", "namepost", "post"):
        for v in d.get(k, []):
            parts = [x for x in re.split(r"\s*\|\s*", v) if x]
            if len(parts) > 1 and any(is_name(x) for x in parts):
                for x in parts:
                    (names if is_name(x) else posts).append(x)
            elif k == "namepost" or (k == "post" and NAME_HINT.match(v)):
                n2, p2 = split_namepost(v)
                names += [n2] if n2 else []
                posts += [p2] if p2 else []
            else:
                (names if k == "name" else posts).append(v)
    name, post = " ".join(names), " ".join(posts)
    if name and not post and not NAME_HINT.match(name) and not d.get("area"):
        post, name = name, ""
    return name, post


def text_blocks(post):
    """Records from plain text outside tables: [(label, name, post, phones, emails, text)]."""
    for t in post.find_all("table"):
        t.decompose()
    from dforms import _esw
    lines = [_emerg.clean(x) for x in re.split(r"\s*\|\s*", _esw.cell_text(post))]
    lines = [x for x in lines if x]
    out, person, label, lastplain = [], None, "", ""

    def flush():
        nonlocal person
        if person and (person.get("phone") or person.get("email")):
            out.append(person)
        person = None

    for ln in lines:
        m = re.match(r"(?i)^(name|designation|phone|mobile|contact(?: no\.?)?|tel(?:ephone)?|e-?mail)\s*[:\-]\s*(.*)$", ln)
        if m and (person is not None or m.group(1).lower() in ("name", "designation")):
            k = m.group(1).lower()
            if k == "name":
                flush()
                person = {"name": m.group(2), "label": label}
            else:
                person = person or {"label": label}
                if k == "designation":
                    person["post"] = m.group(2)
                elif k.startswith("e"):
                    person["email"] = _emerg.emails(m.group(2))
                else:
                    person["phone"] = ", ".join(x for x in (person.get("phone"), _emerg.phones(m.group(2))) if x)
            continue
        ph, em = _emerg.phones(ln), _emerg.emails(ln)
        sc = _emerg.short_codes(ln)
        lab = _emerg.clean(re.split(r"\s*[:：]\s*|\s+(?=\+?\d[\d -]{5,})", ln)[0]) if (ph or em or sc) else ""
        if ph or em:
            if person is not None and not re.search(r"(?i)control|emergency|eoc|helpline|toll|room|office", lab):
                person["phone"] = ", ".join(x for x in (person.get("phone"), ph) if x)
                person["email"] = person.get("email") or em
                continue
            flush()
            generic = re.fullmatch(r"(?i)(landline|mobile|phone|tel(ephone)?|fax|e-?mail|contact( no\.?)?|\d.*)", lab or "x")
            head = label or lastplain
            post_l = head if (generic or not lab) and head else lab
            if generic and head and out and out[-1].get("post") == head:
                last = out[-1]
                last["phone"] = ", ".join(x for x in (last.get("phone"), ph) if x)
                last["email"] = last.get("email") or em
                continue
            if not re.search(r"(?i)control|emergency|eoc|disaster|helpline|toll|room|office|officer|authority|cell|centre|center|"
                             r"आपदा|नियंत्रण|कंट्रोल", post_l + " " + label):
                continue
            out.append({"post": post_l, "phone": ph, "email": em, "label": label, "helpline": sc})
        elif re.search(r"[:：]\s*$", ln) and len(ln) < 100:
            flush()
            label = ln.rstrip(" :：")
        elif len(ln) < 80 and not re.search(r"\d", ln):
            lastplain = ln
        elif sc and re.search(r"(?i)toll|helpline|control|emergency", ln):
            flush()
            out.append({"post": lab or ln[:80], "helpline": sc, "label": label})
    flush()
    return out


def records(html, p):
    url = p["url"]
    host = urlparse(url).netloc
    district, state = p.get("district"), p.get("state")
    soup = _emerg_soup(html)
    post = soup.find("div", id=re.compile(r"^post-\d+")) or soup.find("main") or soup
    lu = last_updated(html)
    recs, seen = [], set()

    def add(section, area, post_, name, phone, fax, email, address, helpline, covers, org, labels, pos=None, method=None):
        phone = ", ".join(x for x in (phone or "").split(", ") if x and not YEARS.match(x))
        name = name if re.search(r"[^\W\d_]", name or "") else ""
        if not (phone or email or helpline):
            return
        lvl = level_of(" ".join(x for x in (section, labels or "") if x)) if area and area != district else "district"
        if re.match(r"(?i)state\b", post_ or "") and not name:
            lvl = "state"
        dist = district
        if not district and p.get("level") == "state":
            lvl = "district" if area and lvl == "district" and p.get("area_is_district") else "state"
            dist = area if lvl == "district" else None
        key = _emerg.unique(f"{host}:{_emerg.slug(section)[:40] or 'page'}:{_emerg.slug(post_ or area or name)[:60] or 'row'}", seen)
        recs.append(_emerg.record(
            MODULE, key, "ddma", dept="fire" if FIRE.search(f"{area} {post_}") else "disaster", level=lvl,
            area=area or district or p.get("area"), post=post_, name=name, phone=phone, fax=fax, email=email, address=address,
            helpline=helpline, covers=covers, org=org, section=section, district=dist, state=state, office_id=key, source=url,
            last_updated=lu, src_pos=pos, method=method))

    for t in post.find_all("table"):
        if t.find_parent("table"):
            continue
        sec = section_of(t)
        tw = []
        for di, d in enumerate(table_rows(t, tw)):
            name, post_ = people(d)
            area = " ".join(d.get("area", []))
            extra = " ".join(d.get("extra", []))
            phone = _emerg.phones(*d.get("phone", []), extra if re.search(r"\d{6,}", extra) else "")
            alltext = " ".join(sum((v for k, v in d.items() if not k.endswith("_labels")), []))
            email = _emerg.emails(alltext)
            fax = _emerg.phones(*d.get("fax", []))
            helpline = _emerg.short_codes(" ".join(d.get("phone", []) + d.get("extra", [])))
            if not post_ and (name or area):
                post_ = sec or ("" if name else "Control Room")
            add(sec, area, post_, name, phone, fax, email, " ".join(d.get("address", [])), helpline, " ".join(d.get("covers", [])),
                " ".join(d.get("org", [])),
                " ".join(d.get("area_labels", [])) + " " + sec, tw[di], "html table")
    for bi, b in enumerate(text_blocks(post), 1):
        add(b.get("label", ""), "", b.get("post", ""), b.get("name", ""), b.get("phone", ""), "", b.get("email", ""), "",
            b.get("helpline", ""), "", "", "", {"selector": "page text outside tables", "block": bi}, "html text (label lines)")
    return recs


def _emerg_soup(html):
    from dforms import _esw
    return _esw.soup(html)


def items(get=None):
    return _emerg.seed(MODULE)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    host = urlparse(p["url"]).netloc
    tag = _emerg.slug(urlparse(p["url"]).path)[-50:] or "page"
    files = [_emerg.keep(MODULE, f"{host}-{tag}", r.content)]
    recs = records(r.text, p)
    return recs, files, "" if recs else "no contacts"
