"""Punjab: councillors of the municipal corporations elected on 21.12.2024, from the corporations' own sites.

cforms/pb.py reads the LBPAMS 2026 result API, which has no 2024 bodies; sec.punjab.gov.in lists only the 2026 gazettes.
- "amritsar": Municipal Corporation Amritsar, "Your Councillors" (amritsarcorp.com/council.htm, council1.htm, council2.htm,
  council3.htm; 85 wards). One table row per ward: "Smt. Name ( Ward No.N) Address : ... Mobile No. : ... Party : AAP"; the
  Mayor and Deputy Mayors are marked in brackets after the name.
- "jalandhar": Municipal Corporation Jalandhar, "Elected Authorities" (mcjalandhar.in/elected-authorities/, links "Ward 1" ..
  "Ward 85"), one page per ward: Name, Father/Husband Name, Address, Mobile, Email, Party, Category, Areas/ Locality.
Both sites answer outside India. One queue item = one corporation (payload "source"). Record id councillor:PB:<body slug>:<ward>
(the scheme of cforms/pb.py).
"""
import gzip
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

PARTIES = {"AAP": "Aam Aadmi Party", "INC": "Indian National Congress", "BJP": "Bharatiya Janata Party", "BSP": "Bahujan Samaj Party",
           "SAD": "Shiromani Akali Dal", "IND": "Independent", "INDEPENDENT": "Independent", "CONGRESS": "Indian National Congress"}
SOURCES = {"amritsar": {"body": "Amritsar", "district": "Amritsar",
                        "urls": [f"https://www.amritsarcorp.com/{p}.htm" for p in ("council", "council1", "council2", "council3")]},
           "jalandhar": {"body": "Jalandhar", "district": "Jalandhar", "urls": ["https://mcjalandhar.in/elected-authorities/"]}}
ELECTION = "Punjab municipal corporations 2024 (poll 21.12.2024)"
POSTS = re.compile(r"\((Mayor|Senior Deputy Mayor|Sr\.? Deputy Mayor|Deputy Mayor)\)", re.I)


def norm(s):
    return " ".join((s or "").replace("\xa0", " ").split()).strip(" :,-")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def party(s):
    s = norm(s)
    return PARTIES.get(re.sub(r"[^A-Z]", "", s.upper()), s) if s else None


def phones(s):
    out = []
    for m in re.finditer(r"\d[\d\s-]{8,}\d", s or ""):
        d = re.sub(r"\D", "", m.group(0))
        if len(d) == 10:
            out.append(d)
    return ", ".join(out) or None


def base(src, body_type="Municipal Corporation"):
    s = SOURCES[src]
    return {"type": "councillor", "state": "PB", "body": f"Municipal Corporation {s['body']}", "body_en": s["body"],
            "body_type": body_type, "district": s["district"], "election": ELECTION}


def amritsar_page(html, url):
    """council*.htm -> records (one table row per ward)."""
    soup = BeautifulSoup(html, "lxml")
    recs = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3 or tr.find("tr"):
            continue
        text = norm(" ".join(td.get_text(" ", strip=True) for td in tds[2:3]))
        m = re.search(r"\(\s*Ward\s*No\.?\s*(\d+)\s*\)", text)
        if not m:
            continue
        name = norm(text[:m.start()])
        post = POSTS.search(name)
        name = norm(POSTS.sub("", name))
        addr = re.search(r"Address\s*:?\s*(.*?)\s*(Mobile|Party|$)", text)
        mob = re.search(r"Mobile\s*No\.?\s*:?\s*(.*?)\s*(Party|$)", text)
        pty = re.search(r"Party\s*:?\s*(.*)$", text)
        d = {**base("amritsar"), "ward_no": m.group(1), "name": name, "position": post.group(1).title() if post else "Member",
             "address": norm(addr.group(1)) if addr else None, "phone": phones(mob.group(1)) if mob else None,
             "party": party(pty.group(1)) if pty else None, "url": url}
        recs.append((f"councillor:PB:amritsar:{m.group(1)}", {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def jalandhar_links(html, url):
    """elected-authorities page -> [(ward no, page url)] from the "Ward N" links."""
    soup = BeautifulSoup(html, "lxml")
    out = {}
    for a in soup.find_all("a", href=True):
        m = re.fullmatch(r"(?:W?ard)\s*(\d+)", norm(a.get_text())) or re.search(r"-ward-(\d+)/?$", a["href"])
        if m and m.group(1) not in out:
            out[m.group(1)] = urljoin(url, a["href"])
    return sorted(out.items(), key=lambda x: int(x[0]))


def jalandhar_ward(html, url, ward):
    soup = BeautifulSoup(html, "lxml")
    art = soup.find("article") or soup
    p = next((p for p in art.find_all("p") if "Name" in p.get_text() and "Party" in p.get_text()), None)
    if p is None:
        return None
    f = {}
    for part in re.split(r"<br\s*/?>", str(p)):
        t = norm(BeautifulSoup(part, "lxml").get_text(" "))
        m = re.match(r"([A-Za-z/ ]+?)\s*:\s*(.*)$", t)
        if m:
            f[m.group(1).strip().lower()] = norm(m.group(2))
    areas = [norm(li.get_text()) for li in art.select("ul li") if norm(li.get_text())]
    d = {**base("jalandhar"), "ward_no": str(int(ward)), "name": f.get("name"), "father_or_husband": f.get("father/husband name"),
         "address": f.get("address"), "phone": phones(f.get("mobile")), "email": f.get("email") or None,
         "party": party(f.get("party")), "reservation": f.get("category"), "position": "Member",
         "ward_name": ", ".join(areas)[:300] or None, "areas": areas or None, "url": url}
    return f"councillor:PB:jalandhar:{d['ward_no']}", {k: v for k, v in d.items() if v not in (None, "", [])}


def fetch(p, get):
    src = p["source"]
    recs, files = [], []
    if src == "amritsar":
        for url in p.get("urls") or SOURCES[src]["urls"]:
            r = get(url)
            if r is None:
                continue
            files.append((f"councillors/PB/amritsar-{url.rsplit('/', 1)[1]}.gz", gzip.compress(r.content), "application/gzip"))
            recs += amritsar_page(r.text, url)
        seen, out = set(), []
        for rid, d in recs:               # the pages overlap by one ward
            if rid not in seen:
                seen.add(rid)
                out.append((rid, d))
        return out, files, "" if out else "no councillors read"
    if src == "jalandhar":
        url = p.get("url") or SOURCES[src]["urls"][0]
        r = get(url)
        if r is None:
            return [], [], "no answer"
        files.append(("councillors/PB/jalandhar-elected-authorities.html.gz", gzip.compress(r.content), "application/gzip"))
        for ward, wurl in jalandhar_links(r.text, url):
            w = get(wurl)
            if w is None:
                continue
            files.append((f"councillors/PB/jalandhar-ward-{ward}.html.gz", gzip.compress(w.content), "application/gzip"))
            rec = jalandhar_ward(w.text, wurl, ward)
            if rec and rec[1].get("name"):
                recs.append(rec)
        return recs, files, "" if recs else "no councillors read"
    return [], [], f"unknown source {src}"
