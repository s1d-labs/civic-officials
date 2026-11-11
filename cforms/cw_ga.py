"""Goa municipal councils: elected councillors from the Goa State Election Commission (sec.goa.gov.in), "winning candidates" /
"elected members" PDFs of each general election (India only).

State in 2026-11: the 11 councils elected in 2021 (Mapusa, Margao, Mormugao, Bicholim, Canacona, Curchorem-Cacora, Cuncolim,
Pernem, Quepem, Sanguem, Valpoi) have no elected council: their term ended on 25-26 May 2026, the government appointed
administrators, and the SEC notified the draft ward division for their next poll in Nov 2026. Ponda (15 wards) and Sanquelim
(12 wards) were elected on 5 May 2023 and are the only councils in office. Panaji (CCP 2026) is read by cforms/city.py.
items(get) reads the SEC's previous and ongoing election pages, finds the municipal council elections of 2023 or later, and
lists their winners PDFs. So a new general election of the 11 councils is found when its results are on the site.
fetch(p, get) reads the PDF's text layer: one block per "Ward No. <roman or digits>" (the SEC's layout, as in the CCP file),
the name in capitals, the seat category in brackets, "Unopposed" when no poll was held.
Record id councillor:GA:<council slug>:<ward>.
"""
import hashlib
import io
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

BASE = "https://sec.goa.gov.in/"
START = ("elections/previous/municipal-council/", "elections/ongoing/")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
WARD = re.compile(r"Ward\s*No\.?\s*[:\-]?\s*([IVXLC]+|\d{1,2})\b")
COUNCIL = re.compile(r"(?:General|Bye)[\s-]*Election\s+to\s+(?:the\s+)?([A-Z][A-Za-z\- ]+?)\s+Municipal\s+Council\s*[-–,]?\s*(20\d\d)?", re.I)
DISTRICT = {"ponda": "South Goa", "sanquelim": "North Goa", "mapusa": "North Goa", "bicholim": "North Goa", "pernem": "North Goa",
            "valpoi": "North Goa", "margao": "South Goa", "mormugao": "South Goa", "cuncolim": "South Goa", "canacona": "Kushavati",
            "curchorem": "Kushavati", "quepem": "Kushavati", "sanguem": "Kushavati"}


def roman(s):
    if s.isdigit():
        return int(s)
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMAN[a]
        total += -v if b != " " and ROMAN.get(b, 0) > v else v
    return total


def clean(s):
    return " ".join((s or "").split())


def links(html, url):
    """(absolute url, text) of every link on a page of the site."""
    soup = BeautifulSoup(html, "lxml")
    b = soup.find("base", href=True)              # the site's pages carry <base href="../../">: links are relative to it
    base = urljoin(url, b["href"]) if b else url
    return [(urljoin(base, a["href"]), clean(a.get_text(" "))) for a in soup.find_all("a", href=True)]


def year_of(*texts):
    ys = [int(y) for t in texts for y in re.findall(r"(20\d\d)", t or "")]
    return max(ys) if ys else None


def election_pages(html, url):
    """Pages of single municipal council elections linked from a list page (deeper than the list itself)."""
    out = []
    for u, t in links(html, url):
        if u.startswith(BASE) and "/elections/" in u and "municipal" in (u + " " + t).lower() and not u.lower().endswith(".pdf") \
                and u.rstrip("/").count("/") > url.rstrip("/").count("/") and "panaji" not in u.lower():
            out.append((u, t))
    return list({u: (u, t) for u, t in reversed(out)}.values())[::-1]      # one entry per url (first text wins)


def winners_pdfs(html, url):
    return [(u, t) for u, t in links(html, url) if u.lower().endswith(".pdf")
            and re.search(r"winning|elected|winner|result", (u + " " + t).lower()) and not re.search(r"sheet|panaji|ccp", u.lower())]


def items(get):
    """Winners PDFs of municipal council elections of 2023 or later; a page without PDFs is followed one level deeper."""
    todo = []
    for s in START:
        r = get(urljoin(BASE, s))
        if r is not None:
            todo += [(u, t, 0) for u, t in election_pages(r.text, urljoin(BASE, s))]
    out, seen, visited = [], set(), set()
    while todo:
        u, t, depth = todo.pop(0)
        y = year_of(u, t)
        if u in visited or (y is not None and y < 2023):    # 2021 councils: term over (May 2026), not in office
            continue
        visited.add(u)
        r = get(u)
        if r is None:
            continue
        pdfs = winners_pdfs(r.text, u)
        if not pdfs and depth < 1:
            todo += [(v, vt, depth + 1) for v, vt in election_pages(r.text, u)]
        for pdf, pt in pdfs:
            y2 = year_of(pdf, pt) or y
            if pdf in seen or (y2 is not None and y2 < 2023):
                continue
            seen.add(pdf)
            out.append({"key": "ga-" + hashlib.sha1(pdf.encode()).hexdigest()[:10],
                        "payload": {"kind": "form-cw_ga", "state": "GA", "url": pdf, "page": u, "title": pt or t,
                                    "year": y2}})
    return out


def parse(text, p):
    """[(record id, record)] from the text of one winners PDF."""
    m = COUNCIL.search(text) or COUNCIL.search(p.get("title") or "")
    council = clean(m.group(1)).title() if m else (p.get("body") or "")
    year = (m.group(2) if m and m.group(2) else None) or p.get("year")
    slug = re.sub(r"[^a-z0-9]+", "-", council.lower()).strip("-") or "x"
    marks = list(WARD.finditer(text))
    recs, seen = [], set()
    for k, w in enumerate(marks):
        block = text[w.end(): marks[k + 1].start() if k + 1 < len(marks) else len(text)]
        block = COUNCIL.sub(" ", block)
        cat = re.search(r"\(([^)]{2,40})\)", block)
        unopposed = bool(re.search(r"unopposed", block, re.I))
        rest = re.sub(r"\([^)]*\)|[-–]\s*unopposed|unopposed|Elected Candidates?( for)?|Sr\.?\s*No\.?|Name of (the )?(elected )?candidate"
                      r"|Category|Ward|Party|\b\d+\b", " ", block, flags=re.I)
        caps = re.findall(r"[A-Z][A-Z.'\-]+(?:\s+[A-Z][A-Z.'\-]+)+", rest)
        name = clean(max(caps, key=len)) if caps else clean(rest)
        ward = str(roman(w.group(1)))
        if not name or ward in seen or len(name) > 80:
            continue
        seen.add(ward)
        recs.append((f"councillor:GA:{slug}:{ward}",
                     {"type": "councillor", "state": "GA", "body": f"{council} Municipal Council", "body_en": council,
                      "body_type": "Municipality", "district": DISTRICT.get(slug.split("-")[0], ""), "ward_no": ward,
                      "ward_roman": w.group(1), "name": name, "reservation": clean(cat.group(1)) if cat else None,
                      "unopposed": unopposed or None, "election": f"Goa municipal councils {year}" if year else None,
                      "url": p["url"], "page_url": p.get("page")}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    from pypdf import PdfReader
    try:
        text = "\n".join(pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(r.content)).pages)
    except Exception as e:  # noqa: BLE001
        return [], [], f"pdf: {type(e).__name__}"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    files = [(f"councillors/GA/{key}.pdf", r.content, "application/pdf")]
    recs = parse(text, p)
    return recs, files, "" if recs else ("no text layer" if len(text.strip()) < 50 else "no wards read")
