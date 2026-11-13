"""Police contact pages on S3WaaS district portals (<district>.gov.in, <district>.nic.in, <district>.telangana.gov.in ...):
tables ("Police Station | CUG | Landline | Email", "Office Name | Phone | CUG", "Rank | Place of posting | Cell") and
public-utility cards (title, address, "Phone :", "Email :", "Pincode :"), paged with /page/N/.

Shared by police_cg, police_up and police_tg (and usable on its own): fetch(p, get, module) reads one district page (and its
/page/N/ pages), keeps every answer, and returns one record per station or office. Payload: url, state, district, and optional
std (STD code for landlines written without it), std_prefix (10-digit "landlines" that start with the STD code without its 0,
e.g. Raipur 771...), police_only (a general directory page: keep only police rows), max_pages.
Record id dept:<module>:<district slug>:<station slug>.
"""
import re

from bs4 import BeautifulSoup

from dforms._police import clean, email, gz, phones, rec, slug, uniq
import provenance

METHOD = "html table + html cards (S3WaaS public utility), paged /page/N/"     # source trail (provenance.py): how this reader reads its sources

M = "police_s3waas"

KIND = [   # (field, header pattern), first match wins
    ("sno", r"^(s\.?\s*no|sr\.?\s*no|sl\.?\s*no|sn|s\. no|serial|#)\.?$|^s\.?no\.?$|^sl\.? ?no\.?$|^si\.? ?no$"),
    ("email", r"e-?\s?mail|nic_mail"),
    ("std", r"^std"),
    ("pincode", r"pin ?code"),
    ("address", r"address"),
    ("mobile", r"mobile|cug|cell|mo\. ?no"),
    ("phone", r"phone|tele|land ?line|land no|pnt|contact|office no|office number|resi|fax|number$|\bno\.?$"),
    ("circle", r"circle name|^circle$|sub ?division"),
    ("name", r"^name$|name of (the )?officer|officer'?s? name|name of sho|^officer name"),
    ("rank", r"^rank$|officer/ ?rank|designation|^post$|^rank & designation"),
    ("station", r"police station|thana|station|office|location|place of posting|post held|unit|sphere|police post|chauki|"
                r"circle officer|^officer$|name of the office"),
]
STATION_HEAD = re.compile(r"police station|thana|station|location|sphere|police post|chauki", re.I)

POST = re.compile(r"\b(chowki|chauki|out ?post|police post|O\.?P\.?|PP|TOP|outpost)\b", re.I)
STATION = re.compile(r"police station|\bP\.?\s?S\b\.?|\bthana\b|kotwali|\bS\.?H\.?O\b|station house|\bAJK\b|ajak", re.I)
DISTRICT = re.compile(r"\b(SP|S\.P|SSP|ASP|Addl\.?\s?S\.?P|Additional S\.?P|Superintendent|Commissioner|C\.P\.?|CP|DCP|ADCP|"
                      r"Addl\.?\s?DCP|DIG|IGP?|DPO)\b", re.I)
CIRCLE = re.compile(r"\b(CO|C\.O\.?|ACP|A\.C\.P\.?|Circle|CI|C\.I\.?|CIP)\b", re.I)
SUBDIV = re.compile(r"\b(CSP|SDOP|SDPO|DSP|Dy\.?\s?SP|Sub[- ]?Divisional|Deputy Superintendent)\b", re.I)
ACP = re.compile(r"Assistant Commissioner|\bA\.?C\.?P\b", re.I)
SHO_SI = re.compile(r"^(S\.?\s?I\.?|SHO)\s|,?\s+(S\.?\s?I|Insp\.?|Inspr\.?)$|\bW?PS\b", re.I)    # Telangana: "S.I. Indalwai", "Town-II, S I"
UNIT = re.compile(r"control room|cont\.? room|police line|reserve inspector|\bR\.?I\.?\b|\bcell\b|\bsel\b|DCRB|PCR|home guard|"
                  r"hqrs|naxal|\bCAR\b|\bDSB\b|\bCSB\b|\bNIB\b|\bCCS\b|\bIT\b", re.I)
RANKS = re.compile(r"^(?:(?:W/|Women\s+|S\.)?(?:Inspr|Insp|Inspector|Sub[- ]?Inspector|S\.?\s?I|A\.?S\.?I|Asst\.? Sub[- ]?Inspector|"
                   r"Circle Inspector|Head Constable|HC)\.?(?:\s+of\s+Police)?)$", re.I)
POLICE = re.compile(r"police|thana|\bS\.?H\.?O\b|chowki|chauki|station house|out ?post|\bS\.?P\b|SDOP|CSP|DSP|\bP\.?S\b", re.I)
GENERIC = re.compile(r"^(SHO|POLICE STATION|OFFICE|CIP|SI|S\.I\.|INSPR?\.?|INSPECTOR)$", re.I)


def kind(h):
    h = (clean(h) or "").lower().strip(" :.")
    for k, pat in KIND:
        if re.search(pat, h, re.I):
            return k
    return None


def grid(table):
    """Rows of cell texts with rowspan / colspan filled in."""
    out, carry = [], {}
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["td", "th"], recursive=False) or tr.find_all(["td", "th"])
        for td in cells:
            while col in carry:
                text, left = carry[col]
                row.append(text)
                left -= 1
                if left:
                    carry[col] = (text, left)
                else:
                    del carry[col]
                col += 1
            text = clean(td.get_text(" ", strip=True)) or ""
            span = int(re.sub(r"\D", "", td.get("colspan") or "1") or 1)
            rows = int(re.sub(r"\D", "", td.get("rowspan") or "1") or 1)
            for _ in range(min(span, 10)):
                row.append(text)
                if rows > 1:
                    carry[col] = (text, rows - 1)
                col += 1
        while col in carry:
            text, left = carry[col]
            row.append(text)
            left -= 1
            if left:
                carry[col] = (text, left)
            else:
                del carry[col]
            col += 1
        out.append(row)
    return out


def header_of(row):
    ks = [kind(c) for c in row]
    named = [k for k in ks if k]
    if len(named) >= 2 and not any(re.search(r"\d{4,}|\[\s*at\s*\]|@", c or "") for c in row):
        return ks
    return None


def level_of(label, post="", default="police_station"):
    t = f"{label} {post}"
    if POST.search(t):
        return "police_station", "police post"
    if SUBDIV.search(t):
        return "subdivision", "office"
    if ACP.search(t):
        return "circle", "office"
    if DISTRICT.search(t):
        return "district", "office"
    if SHO_SI.search(label or ""):
        return "police_station", "police station"
    if CIRCLE.search(t):
        return "circle", "office"
    if STATION.search(t):
        return "police_station", "police station"
    if UNIT.search(t):
        return "district", "unit"
    return (default, "police station") if default == "police_station" else (default, "unit")


def split_designation(s):
    """'Inspector, Station House Officer, Basantpur' -> (rank, post, area); 'Sub-Inspector of Police, Toopran PS' -> (rank, rank, area)."""
    parts = [x.strip() for x in re.split(r"\s*,\s*", s or "") if x.strip()]
    if len(parts) >= 2 and RANKS.match(parts[0]):
        rank = parts[0]
        rest = parts[1:]
        area = rest[-1]
        post = " ".join(rest[:-1]) or None
        m = re.match(r"^(Station House Officer|SHO|Incharge|In-?charge|Chowki Incharge|Outpost Incharge|Officer In-?charge)\s+(.+)$",
                     area, re.I)
        if m:
            post, area = m.group(1), m.group(2)
        return rank, post or rank, area
    return None, None, s


LANDLINE = re.compile(r"(?<![\d-])\(?(0\d{2,4})\)?\s*-\s*(\d[\d ]{4,9}\d)(?![\d-])")


def fix_phone(raw, std=None, std_prefix=None):
    """Numbers of one or more cells. Landlines with an STD code are taken first: _police.phones() reads '07727-223339'
    (a 4-digit STD code that starts with 7, 8 or 9) as a mobile number with a leading 0."""
    raw = re.sub(r"\s*[\u2013\u2014\u2212]\s*", "-", clean(raw) or "")
    if raw in ("", "-", "--", "NA", "N/A"):
        return None
    raw = re.sub(r"(?i)-?\s*fax\b", "", raw)
    out, rest = [], raw
    for m in LANDLINE.finditer(raw):
        num = m.group(2).replace(" ", "")
        if len(num) >= 5 and len(m.group(1)) + len(num) in (10, 11):
            out.append(f"{m.group(1)}-{num}")
            rest = rest.replace(m.group(0), " , ")
    for n in (phones(rest) or "").split(", "):
        if not n:
            continue
        d = n.replace("-", "")
        if std_prefix and len(d) == 10 and d.startswith(std_prefix):
            n = f"0{std_prefix}-{d[len(std_prefix):]}"
        elif std and "-" not in n and 5 <= len(d) <= 8 and not d.startswith("0"):
            n = f"0{str(std).lstrip('0')}-{d}"
        if n not in out:
            out.append(n)
    mobiles = [n for n in out if "-" not in n and len(n) == 10]
    return ", ".join(mobiles + [n for n in out if n not in mobiles]) or None


def table_rows(html):
    """Yield (fields, context) for every data row of every table: fields = {kind: text}."""
    soup = BeautifulSoup(html, "lxml")
    last_head = None
    for ti, t in enumerate(soup.find_all("table"), 1):
        cap = t.find("caption")
        h = t.find_previous(["h1", "h2", "h3", "h4", "h5", "strong"])
        context = clean(cap.get_text(" ", strip=True)) if cap else None
        head, section = None, None
        rows = grid(t)
        for ri, r in enumerate(rows, 1):
            if not any(r):
                provenance.skip_row(r, 'skip: not any(r)')
                continue
            hk = header_of(r)
            if hk:
                head = hk
                continue
            if len(set(x for x in r if x)) == 1 and not re.search(r"\d{6,}", r[0]):
                section = r[0]       # a heading row inside the table ("SIDDIPET DIVISION", "STD CODE-03823")
                continue
            use = head or (last_head if last_head and len(last_head) == len(r) else None)
            if not use:
                provenance.skip_row(r, 'skip: not use')
                continue
            f = {}
            for k, v in zip(use, r):
                if k and v and k not in f:
                    f[k] = v
                elif k and v and k in ("phone", "mobile") and v != f[k]:
                    f[k] += ", " + v
            if not f:
                provenance.skip_row(r, 'skip: not f')
                continue
            yield f, {"caption": context, "section": section, "heading": clean(h.get_text(" ", strip=True)) if h else None,
                      "station_head": bool(use and any(k == "station" for k in use)) and any(
                          STATION_HEAD.search(x or "") for x, k in zip(rows[0], use) if k == "station"),
                      "pos": {"table": ti, "row": ri}}
        if head:
            last_head = head


def cards(html, where=None):
    """S3WaaS public-utility cards: {title, address, phone, email, pincode, website, type}. where (a list) gets each card's
    src_pos {"selector": ".public-utlty-catg", "card": n} (1-based among the page's cards). The "district-theme-5" template
    (Kolasib, 2026-11) writes the cards as "ul.pub-ut-container > li.box" (h2.heading3, ul.pubutility-list): read the same way,
    selector ".pub-ut-container > li"."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    sel = ".public-utlty-catg"
    found = soup.select(sel)
    if not found:
        sel = ".pub-ut-container > li"
        found = soup.select(sel)
    for n, c in enumerate(found, 1):
        h = c.select_one(".heading4, h2, h3")
        d = {"title": clean(h.get_text(" ", strip=True)) if h else None}
        for li in c.select("li"):
            st = li.find("strong")
            txt = clean(li.get_text(" ", strip=True)) or ""
            if st:
                lab = (clean(st.get_text(" ", strip=True)) or "").rstrip(" :").lower()
                val = txt[len(clean(st.get_text(" ", strip=True)) or ""):].strip(" :")
                key = {"phone": "phone", "email": "email", "pincode": "pincode", "website link": "website", "address": "address",
                       "category/type": "type", "mobile": "phone"}.get(lab, lab)
                d[key] = val
            elif txt and "address" not in d:
                d["address"] = txt
        if d.get("title"):
            out.append(d)
            if where is not None:
                where.append({"selector": sel, "card": n})
    return out


def next_pages(html, url):
    base = re.sub(r"page/\d+/?$", "", url.rstrip("/") + "/")
    found = set()
    for m in re.finditer(r'href="([^"]+/page/(\d+)/?)"', html):
        if m.group(1).startswith(base) or m.group(1).startswith("/"):
            found.add(int(m.group(2)))
    return base, found


def last_updated(html):
    m = re.search(r"Last Updated:?\s*(?:<[^>]+>\s*)*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", html)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None


def records(module, pages, p):
    """pages: [(url, html)]. One record per row / card."""
    state, district = p.get("state"), p.get("district")
    std, std_prefix = p.get("std"), p.get("std_prefix")
    out = []
    lu = next((last_updated(h) for _, h in pages if last_updated(h)), None)
    for url, html in pages:
        for f, ctx in table_rows(html):
            label, post, rank, name = f.get("station"), None, f.get("rank"), f.get("name")
            if label and rank and GENERIC.match(label) and not GENERIC.match(rank):
                label, rank = rank, label                # Siddipet: the columns are swapped in places
            if not label:
                label, rank = rank, None
            if rank and GENERIC.match(rank):
                post, rank = rank, None          # "SHO", "POLICE STATION": the post, not a rank
            if not label:
                provenance.skip_row(f, 'skip: not label')
                continue
            original = label
            if label and not f.get("station") or (label and "," in label and RANKS.match(label.split(",")[0].strip())):
                r2, p2, a2 = split_designation(label)
                if r2:
                    rank, post, label = r2, p2, a2
            text = " ".join(x for x in (original, rank or "", post or "", ctx.get("caption") or "") if x)
            if p.get("police_only") and not POLICE.search(text):
                provenance.skip_row(f, 'skip: p.get("police_only") and not POLICE.search(text)')
                continue
            if not re.search(r"[A-Za-zऀ-ൿ]", label) or label.lower().startswith(("total", "read more")):
                provenance.skip_row(f, 'skip: not re.search(r"[A-Za-zऀ-ൿ]", label) or label.lower().startswith(("...')
                continue
            row_std = std
            sec = ctx.get("section") or ""
            m = re.search(r"STD\s*CODE\s*[-:]?\s*(0\d{2,4})", sec, re.I)
            if m:
                row_std = m.group(1)
            if f.get("std") and re.fullmatch(r"0?\d{2,4}", f["std"]):
                row_std = f["std"]
            ph = fix_phone(", ".join(x for x in (f.get("mobile"), f.get("phone")) if x), row_std, std_prefix)
            mail = None
            for part in re.split(r"[\s,;/]+(?=\S+(?:\[at\]|@))", f.get("email") or ""):
                mail = mail or email(part)
            level, otype = level_of(label, " ".join(x for x in (rank, post) if x), "police_station" if ctx.get("station_head") else "district")
            sub = None
            for c in (ctx.get("caption"), sec):
                if c and re.search(r"sub[- ]?divi|division|circle", c, re.I) and not re.search(r"STD", c):
                    sub = c
            if not post or GENERIC.match(post):
                post = ("SHO" if otype == "police station" else "Officer in charge" if otype == "police post" else rank or label)
            key = f"{slug(district or '')}:{slug(label)}"
            out.append(rec(module, key, level=level, office_type=otype, area=label, post=post, name=name,
                           rank=rank if rank != post else None, phone=ph, email=mail, address=f.get("address"),
                           pincode=f.get("pincode"), circle=f.get("circle"), subdivision=sub, state=state, district=district,
                           source=url, last_updated=lu, src_url=url, src_pos=ctx.get("pos"), method="html table"))
        cw = []
        for ci, c in enumerate(cards(html, cw)):
            label = c["title"]
            if p.get("police_only") and not POLICE.search(f"{label} {c.get('type') or ''}"):
                provenance.skip_row(c, 'skip: p.get("police_only") and not POLICE.search(f"{label} {c.get(\'type\')...')
                continue
            level, otype = level_of(label, c.get("type") or "", "police_station")
            if otype == "unit":
                otype = "police station"
                level = "police_station"
            out.append(rec(module, f"{slug(district or '')}:{slug(label)}", level=level, office_type=otype, area=label,
                           post="SHO" if otype == "police station" else "Officer in charge" if otype == "police post" else label,
                           phone=fix_phone(c.get("phone"), std, std_prefix), email=email(c.get("email")),
                           address=c.get("address"), pincode=c.get("pincode"), state=state, district=district, source=url,
                           last_updated=lu, src_url=url, src_pos=cw[ci], method="html cards (S3WaaS public utility)"))
    return merge(out)


def merge(recs):
    """The same office twice on one page (Siddipet lists the SHO and then the station's own number): one record, phones joined."""
    by, order = {}, []
    for rid, d in recs:
        if rid in by:
            o = by[rid]
            if d.get("phone"):
                ph = [x for x in (o.get("phone") or "").split(", ") if x]
                ph += [x for x in d["phone"].split(", ") if x not in ph]
                o["phone"] = ", ".join(ph)
            for k, v in d.items():
                o.setdefault(k, v)
        else:
            by[rid] = d
            order.append(rid)
    return [(rid, by[rid]) for rid in order]


def fetch(p, get, module=M):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    name = slug(re.sub(r"^https?://", "", url))[:80]
    files = [gz(module, f"{name}.html", r.content)]
    pages = [(url, r.text)]
    base, nums = next_pages(r.text, url)
    seen, n = {1}, 2
    while n in nums and n not in seen and n <= int(p.get("max_pages", 30)):
        seen.add(n)
        u = f"{base}page/{n}/"
        r2 = get(u)
        if r2 is None:
            break
        files.append(gz(module, f"{name}-page-{n}.html", r2.content))
        pages.append((u, r2.text))
        nums |= next_pages(r2.text, u)[1]
        n += 1
    recs = uniq(records(module, pages, p))
    return recs, files, "" if recs else "no rows"
