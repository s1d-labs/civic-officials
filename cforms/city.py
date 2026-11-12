"""Single-city councillor sources: one queue item = one city (seeds/councillors_city.json, keys "city-<slug>").
Payload: {"kind": "form-city", "state", "source", "slug", "body", "district", "election", "url", ...}; fetch(p, get) dispatches on
p["source"] to one small reader per source:
- "opencity": OpenCity CKAN dataset (data.opencity.in): package_show, then the CSV resource (Mumbai, Pune 2026).
- "kolhapur": Kolhapur MC member list, one div.card per prabhag (Devanagari number), one div.profile-card per seat (letter).
- "indore": Indore MC Next.js page, <script id=__NEXT_DATA__> details[].otherContent (ward, name, phone, address).
- "bbsr": Bhubaneswar MC zones and wards page, ul.wardbrief per zone tab: ward no, area, "Name 10-digit-phone".
- "agartala": Agartala MC councillor table (SL, ward, name with "(MAYOR IN COUNCIL)", phone). India only.
- "gangtok": Gangtok MC SPA; the councillors are a literal array in /assets/index-*.js ({name, designation, ward, contact}).
- "itanagar": Itanagar MC committee member cards: name, role, "Ward No. NN".
- "panaji": Goa SEC "elected members" PDF (ward in Roman numerals, category, name; India only) plus ccpgoa.com elected members
  (ward, name, address). Either one alone is enough; nominated councillors (no ward) are left out.
- "wikipedia": English Wikipedia election article (p["title"]), via the parse API; the ward table with a Winner group or a
  Councillor column. The page URL with the revision id is the record's url.
Record id councillor:<XX>:<slug>:<ward no>[-<seat>]. p["note"], when present, is copied into every record.
"""
import csv
import gzip
import io
import json
import re
from urllib.parse import quote

from bs4 import BeautifulSoup

METHOD = "pdf text (pypdf) + json api + html table + csv file"     # source trail (provenance.py): how this reader reads its sources

DEVA = str.maketrans("०१२३४५६७८९", "0123456789")
SEATS = str.maketrans({"अ": "a", "ब": "b", "क": "c", "ड": "d", "इ": "e"})   # Kolhapur seat letters in record ids
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def clean(s):
    return " ".join((s or "").replace("‬", " ").replace("‭", " ").split())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def gz(p, name, content):
    if isinstance(content, str):
        content = content.encode()
    return (f"councillors/{p['state']}/city-{p['slug']}-{name}.gz", gzip.compress(content), "application/gzip")


def roman(s):
    n, prev = 0, 0
    for ch in reversed(s.upper()):
        v = ROMAN.get(ch, 0)
        n, prev = (n - v, prev) if v < prev else (n + v, v)
    return n


def phones(s):
    """'+91 94250 51166' / '79994 64751 / 98266 55578' -> '9425051166' / '7999464751, 9826655578'."""
    out = []
    for part in re.split(r"[/,]", s or ""):
        d = re.sub(r"\D", "", part)
        if len(d) == 12 and d.startswith("91"):
            d = d[2:]
        if d:
            out.append(d)
    return ", ".join(out) or None


# --- readers: each returns (rows, files, why); a row is a dict with at least ward_no or ward_name, and name ---------------------

def opencity(p, get):
    api = f"https://data.opencity.in/api/3/action/package_show?id={p['dataset']}"
    r = get(api)
    if r is None:
        return [], [], "package_show did not answer"
    files = [gz(p, "package.json", r.content)]
    res = [x for x in r.json()["result"]["resources"] if (x.get("format") or "").upper() == "CSV"]
    if not res:
        return [], files, "no CSV resource"
    c = get(res[0]["url"])
    if c is None:
        return [], files, "CSV did not answer"
    files.append(gz(p, "results.csv", c.content))
    rows, ward_name = [], {}
    for x in csv.DictReader(io.StringIO(c.content.decode("utf-8-sig"))):
        x = {clean(k): clean(v) for k, v in x.items() if k}
        w = x.get("Ward No.")
        if not w or not x.get("Elected Candidate Name"):
            continue
        if x.get("Ward Name"):
            ward_name[w] = x["Ward Name"]
        rows.append({"ward_no": w, "ward_name": x.get("Ward Name") or ward_name.get(w), "seat": x.get("Seat"),
                     "reservation": x.get("Reservation"), "name": x["Elected Candidate Name"], "party": x.get("Party"),
                     "votes": x.get("Valid Votes Received"), "file_url": res[0]["url"]})
    return rows, files, ""


def kolhapur(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "list.html", r.content)]
    rows = []
    for h in BeautifulSoup(r.text, "lxml").select("h4.card-title"):
        m = re.search(r"(\d+)", clean(h.get_text()).translate(DEVA))
        card = h.find_parent(class_="card")
        if not m or card is None:
            continue
        for pc in card.select("div.profile-card"):
            name = clean(pc.select_one(".name").get_text() if pc.select_one(".name") else "")
            name = re.sub(r"^मा\.\s*", "", name)
            seat = clean(pc.select_one(".designation").get_text() if pc.select_one(".designation") else "")
            if name:
                rows.append({"ward_no": m.group(1), "seat": seat or None, "name": name})
    return rows, files, ""


def indore(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "councillors.html", r.content)]
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return [], files, "no __NEXT_DATA__"
    attrs = json.loads(m.group(1))["props"]["pageProps"]["data"]["data"]["attributes"]
    rows = []
    for x in attrs.get("details") or []:
        o = x.get("otherContent") or {}
        no = re.search(r"(\d+)", o.get("wardNumber") or "")
        wname = clean(re.sub(r"^Ward Name\s*:?-?\s*", "", clean(o.get("wardName")), flags=re.I))
        des, web = clean(o.get("designation")), clean(o.get("website"))
        position = des if re.search(r"councillor|chairman|mayor", des, re.I) else None
        address = web if position else (des or web)          # the address sits in "designation", or in "website" when that holds a post
        rows.append({"ward_no": no.group(1) if no else None, "ward_name": wname or None, "name": clean(o.get("title")),
                     "phone": phones(o.get("phoneNumber")), "position": position, "address": address or None})
    return rows, files, "" if rows else "no details"


def bbsr(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "zones-wards.html", r.content)]
    soup = BeautifulSoup(r.text, "lxml")
    zones = {a["href"].lstrip("#"): clean(a.get_text()) for a in soup.select("ul.zonetab a[href^='#']")}
    rows = []
    for pane in soup.select("div.tab-pane"):
        zone = zones.get(pane.get("id"))
        for li in pane.select("ul.wardbrief > li"):
            no, who = li.select_one("span.wardno"), li.select_one("div.block3")
            if not no or not who:
                continue
            area = li.select_one("div.block2")
            area_t = clean(area.get_text()) if area else ""
            who_t = clean(who.get_text())
            if area_t.endswith(who_t):              # block2 left open in the source: block3 sits inside it
                area_t = clean(area_t[: -len(who_t)])
            m = re.match(r"^(.*?)\s*((?:\d[\d\s]{8,}\d)?)$", who_t)
            rows.append({"ward_no": clean(no.get_text()), "ward_area": area_t or None, "zone": zone,
                         "name": clean(m.group(1)) if m else who_t, "phone": phones(m.group(2)) if m else None})
    return rows, files, ""


def agartala(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "councilor-list.html", r.content)]
    rows = []
    for t in BeautifulSoup(r.text, "lxml").find_all("table"):
        trs = t.find_all("tr")
        head = [clean(c.get_text()) for c in trs[0].find_all(["th", "td"])] if trs else []
        if not any("Ward" in h for h in head):
            continue
        for tr in trs[1:]:
            c = dict(zip(head, (clean(td.get_text(" ")) for td in tr.find_all(["td", "th"]))))
            name = c.get("Name of Corporator") or ""
            m = re.match(r"^(.*?)\s*\(([^)]*)\)\s*$", name)
            if not c.get("Ward No.") or not name:
                continue
            rows.append({"ward_no": c["Ward No."], "name": m.group(1) if m else name, "position": m.group(2).title() if m else None,
                         "phone": phones(c.get("Contact Number"))})
    return rows, files, ""


def gangtok(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    js = re.search(r'src="(/assets/index-[^"]+\.js)"', r.text)
    if not js:
        return [], [gz(p, "home.html", r.content)], "no JS bundle in the page"
    b = get(p["url"].rstrip("/") + js.group(1))
    if b is None:
        return [], [], "bundle did not answer"
    files = [gz(p, js.group(1).rsplit("/", 1)[1], b.content)]
    rows = []
    for m in re.finditer(r'\{name:"([^"]+)",designation:"([^"]*)",ward:"([^"]*)",contact:"([^"]*)"', b.text):
        rows.append({"ward_name": clean(m.group(3)), "name": clean(m.group(1)), "position": clean(m.group(2)) or None,
                     "phone": phones(m.group(4))})
    return rows, files, ""


def itanagar(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "committeemember.html", r.content)]
    soup = BeautifulSoup(r.text, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    tok = [clean(s) for s in soup.stripped_strings]
    rows, seen = [], set()
    for i, t in enumerate(tok):
        if t != "account_circle" or i + 5 >= len(tok):
            continue
        name, role, ward = tok[i + 1], tok[i + 3] if tok[i + 2] == "local_offer" else None, tok[i + 5]
        m = re.match(r"Ward No\.?\s*0*(\d+)", ward)
        if not m or (name, m.group(1)) in seen:     # the page repeats one card (ward 20)
            continue
        seen.add((name, m.group(1)))
        rows.append({"ward_no": m.group(1), "name": name, "position": role})
    return rows, files, ""


def panaji(p, get):
    files, sec, ccp = [], {}, {}
    r = get(p["pdf_url"])
    if r is not None:
        files.append((f"councillors/{p['state']}/city-{p['slug']}-elected-members.pdf", r.content, "application/pdf"))
        from pypdf import PdfReader
        text = "\n".join(pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(r.content)).pages)
        marks = list(re.finditer(r"Ward No\.\s*([IVXLC]+)\b", text))
        for k, m in enumerate(marks):
            block = text[m.end(): marks[k + 1].start() if k + 1 < len(marks) else len(text)]
            cat = re.search(r"\(([^)]+)\)", block)
            block = re.sub(r"\([^)]*\)|Corporation of|the City of|Panaji", " ", block)
            sec[str(roman(m.group(1)))] = {"name": clean(block), "reservation": cat.group(1) if cat else None}
    r = get(p["url"])
    if r is not None:
        files.append(gz(p, "elected-members.html", r.content))
        t = next((t for t in BeautifulSoup(r.content, "lxml").find_all("table") if "WARD NO" in t.get_text()), None)
        for tr in t.find_all("tr") if t else []:
            tds = tr.find_all("td")
            if len(tds) < 2 or not clean(tds[0].get_text()).isdigit():
                continue
            lines = [clean(s) for s in tds[-1].stripped_strings]
            if not lines or any("NOMINATED" in x.upper() for x in lines):
                continue
            addr = re.sub(r"^COUNCILLOR,?\s*WARD\s*NO\.?\s*\d+,?\s*", "", " ".join(lines[1:]), flags=re.I)
            ccp[clean(tds[0].get_text())] = {"name": lines[0], "address": clean(addr) or None}
    if not sec and not ccp:
        return [], files, "neither the SEC PDF nor ccpgoa.com answered"
    rows = []
    for w in sorted(set(sec) | set(ccp), key=int):
        s, c = sec.get(w, {}), ccp.get(w, {})
        rows.append({"ward_no": w, "name": s.get("name") or c.get("name"), "reservation": s.get("reservation"),
                     "name_ccp": c.get("name") if s else None, "address": c.get("address"),
                     "url": p["pdf_url"] if s else p["url"], "site_url": p["url"] if c and s else None})
    return rows, files, ""


def grid(table):
    """A wikitable as a list of rows of (text, is_header) with rowspan/colspan filled out."""
    out, carry = [], {}
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["th", "td"], recursive=False)
        for cell in cells + [None]:
            while col in carry:
                text, hd, left = carry[col]
                row.append((text, hd))
                carry[col] = (text, hd, left - 1)
                if left - 1 == 0:
                    del carry[col]
                col += 1
            if cell is None:
                break
            for s in cell.select("sup.reference"):
                s.decompose()
            text, hd = clean(cell.get_text(" ")), cell.name == "th"
            span = int(re.sub(r"\D", "", cell.get("colspan", "1")) or 1)
            down = int(re.sub(r"\D", "", cell.get("rowspan", "1")) or 1)
            for _ in range(span):
                row.append((text, hd))
                if down > 1:
                    carry[col] = (text, hd, down - 1)
                col += 1
        out.append(row)
    return out


def wikipedia(p, get):
    api = ("https://en.wikipedia.org/w/api.php?action=parse&prop=text%7Crevid&format=json&formatversion=2&redirects=1&page="
           + quote(p["title"]))
    r = get(api)
    if r is None:
        return [], [], "no answer"
    files = [gz(p, "parse.json", r.content)]
    d = r.json().get("parse") or {}
    if not d.get("text"):
        return [], files, "no such article"
    page_url = f"https://en.wikipedia.org/w/index.php?title={quote(d.get('title', p['title']).replace(' ', '_'))}&oldid={d.get('revid')}"
    for t in BeautifulSoup(d["text"], "lxml").select("table.wikitable"):
        g = grid(t)
        heads = [row for row in g if row and all(h for _, h in row)]
        if not heads:
            continue
        width = max(len(row) for row in heads)
        label = [" | ".join(dict.fromkeys(row[i][0] for row in heads if i < len(row) and row[i][0])) for i in range(width)]
        winner = any("Winner" in x for x in label)
        if not (winner or any(re.search(r"Councillor", x) for x in label)):
            continue

        def col(*need, avoid=None):
            return [i for i, x in enumerate(label) if all(n.lower() in x.lower() for n in need) and not (avoid and avoid in x)]
        wcol = next(iter(col("Ward")), None)
        if wcol is None:
            continue
        side = "Winner" if winner else ""
        name_c = (col(side, "Candidate") if winner else col("Councillor"))[:1]
        party_c = col(side, "Party") if winner else col("Party")
        votes_c = col(side, "Votes")[:1] if winner else []
        ru_name, ru_party, ru_votes = col("Runner", "Candidate")[:1], col("Runner", "Party"), col("Runner", "Votes")[:1]
        margin_c, borough_c = col("Margin")[:1], col("Borough")[:1]

        def val(row, cs):
            vals = [row[i][0] for i in cs if i < len(row) and row[i][0]]
            return vals[-1] if vals else None
        rows = []
        for row in g:
            if not row or all(h for _, h in row) or wcol >= len(row):
                continue
            m = re.search(r"(\d+)", row[wcol][0])
            name = val(row, name_c)
            if not m or not name:
                continue
            rows.append({"ward_no": m.group(1), "name": name, "party": val(row, party_c), "votes": val(row, votes_c),
                         "runner_up": val(row, ru_name), "runner_up_party": val(row, ru_party), "runner_up_votes": val(row, ru_votes),
                         "margin": val(row, margin_c), "borough": val(row, borough_c), "url": page_url,
                         "wikipedia_revision": d.get("revid")})
        if rows:
            return rows, files, ""
    return [], files, "no ward result table"


READERS = {"opencity": opencity, "kolhapur": kolhapur, "indore": indore, "bbsr": bbsr, "agartala": agartala, "gangtok": gangtok,
           "itanagar": itanagar, "panaji": panaji, "wikipedia": wikipedia}


def fetch(p, get):
    rows, files, why = READERS[p["source"]](p, get)
    recs, seen = [], {}
    for x in rows:
        if not x.get("name"):
            continue
        ward = x.get("ward_no") or slug(x.get("ward_name") or "") or str(len(recs) + 1)
        key = ward + (f"-{slug(x['seat'].translate(SEATS))}" if x.get("seat") and slug(x["seat"].translate(SEATS)) else "")
        seen[key] = seen.get(key, 0) + 1
        rid = f"councillor:{p['state']}:{p['slug']}:{key}" + (f"-{seen[key]}" if seen[key] > 1 else "")
        d = {"type": "councillor", "state": p["state"], "body": p["body"], "district": p.get("district"), "election": p.get("election"),
             "url": p.get("url"), "source": p["source"], "note": p.get("note"), **{k: v for k, v in x.items() if v not in (None, "")}}
        recs.append((rid, {k: v for k, v in d.items() if v not in (None, "")}))
    return recs, files, why or ("" if recs else "no members")
