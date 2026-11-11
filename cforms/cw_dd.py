"""Dadra and Nagar Haveli and Daman and Diu: municipal councillors of Daman, Silvassa and Diu from the UT Official Gazette
(Extraordinary), listed on ddd.gov.in/document-category/latest-updates/ (title "OFFICIAL GAZETTE : Extra Ordinary No. N", date,
link to cdnbbsr.s3waas.gov.in/.../<file>.pdf).

The Election Commission for UTs notifies "Names of the persons elected to the <name> Municipal Council" after each general
election, with a table: council, ward ("7/15" or "7"), name of the person declared elected, party affiliation. Elections:
Daman and Silvassa Municipal Councils on 5 Nov 2025 (15 wards each); Diu Municipal Council in 2023 (13 wards). The listing gives
no subject, so every gazette dated inside an election window is one queue item; fetch() reads its text and keeps only the
members list ("no member list" for the others). The 2025 gazettes are made with Word (text layer); a scanned gazette falls back
to Tesseract (eng).
items(get) pages through the listing (newest first) and stops below the earliest window. One request per listing page.
Record id councillor:DD:<council slug>:<ward>.
"""
import datetime
import hashlib
import io
import re
import shutil
import subprocess
import tempfile

from bs4 import BeautifulSoup

LIST = "https://ddd.gov.in/document-category/latest-updates/page/{}/"
WINDOWS = ((datetime.date(2025, 11, 1), datetime.date(2026, 1, 31), "DNH&DD Municipal Councils 2025"),
           (datetime.date(2023, 2, 1), datetime.date(2023, 6, 30), "Diu Municipal Council 2023"))
HEAD = re.compile(r"Names\s+of\s+the\s+persons?\s+(?:declared\s+)?elected\s+to\s+the\s+([A-Za-z ]+?)\s+Municipal\s+Council", re.I)
HONOR = r"(?:Shri|Smt|Sh|Ms|Mr|Mrs|Kum|Km|Kumari|Dr)\b[.,]?"
ROW = re.compile(r"(?:^|[\s|])(\d{1,2})\s*(?:/\s*\d{1,2})?\s*[_|.]*\s*[|]?\s+(" + HONOR + r"\s*\S.*)$")
PARTY = (("bharatiya janata", "BJP"), ("indian national congress", "INC"), ("independent", "Independent"),
         ("janata dal (united)", "JD(U)"), ("janata dal(united)", "JD(U)"), ("janata dal (u)", "JD(U)"),
         ("shiv sena", "SHS"), ("nationalist congress", "NCP"), ("aam aadmi", "AAP"), ("bahujan samaj", "BSP"))
SLUG = {"daman": ("daman", "Daman", "Daman Municipal Council"), "silvassa": ("silvassa", "Dadra And Nagar Haveli",
        "Silvassa Municipal Council"), "diu": ("diu", "Diu", "Diu Municipal Council")}


def window(day):
    for a, b, label in WINDOWS:
        if a <= day <= b:
            return label
    return None


def listing(html, base="https://ddd.gov.in/"):
    """Rows of one listing page: [(title, date, pdf url)]."""
    out = []
    for tr in BeautifulSoup(html, "lxml").select("table tr"):
        tds = tr.find_all("td")
        a = tr.find("a", href=re.compile(r"\.pdf$", re.I))
        if len(tds) < 2 or not a:
            continue
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", tds[1].get_text())
        if not m:
            continue
        day = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        out.append((" ".join(tds[0].get_text(" ", strip=True).split()), day, a["href"]))
    return out


def items(get):
    seen, out = set(), []
    oldest = min(a for a, _, _ in WINDOWS)
    for n in range(1, 400):
        r = get(LIST.format(n))
        if r is None:
            break
        rows = listing(r.text)
        if not rows:
            break
        for title, day, url in rows:
            label = window(day)
            if label and url not in seen and re.search(r"gazette|notification|election", title, re.I):
                seen.add(url)
                out.append({"key": "dd-" + hashlib.sha1(url.encode()).hexdigest()[:10],
                            "payload": {"kind": "form-cw_dd", "state": "DD", "url": url, "title": title,
                                        "date": day.isoformat(), "election": label}})
        if max(d for _, d, _ in rows) < oldest:
            break
    return out


def party_of(t):
    low = " ".join((t or "").lower().split())
    for k, v in PARTY:
        if k in low:
            return v
    return t or None


def split_name_party(rest):
    """'Shri Mario Francisco Lopes      Indian National Congress' -> (name, party): columns are 2+ spaces or a bar apart."""
    parts = [x.strip(" _|") for x in re.split(r"\s{2,}|\s*\|\s*", rest.strip()) if x.strip(" _|")]
    if not parts:
        return None, None
    if len(parts) == 1:          # no gap: the party is the known tail of the line
        low = parts[0].lower()
        for k, _ in PARTY:
            i = low.find(k)
            if i > 0:
                return parts[0][:i].strip(" ,"), parts[0][i:].strip()
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def members(text):
    """[(council, ward, name, party text)] from a gazette's text; each heading starts one council's table."""
    heads = list(HEAD.finditer(text))
    out = []
    for k, h in enumerate(heads):
        council = " ".join(h.group(1).split())
        block = text[h.end(): heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        seen = set()
        for line in block.splitlines():
            m = ROW.search(line)
            if not m:
                continue
            ward = str(int(m.group(1)))
            name, party = split_name_party(m.group(2))
            if not name or ward in seen:
                continue
            seen.add(ward)
            name = re.sub(r"^(Shri|Smt|Sh|Ms|Mr|Mrs|Kum|Km|Kumari|Dr),", r"\1.", name)     # OCR reads "Smt." as "Smt,"
            out.append((council, ward, " ".join(name.split()), party))
    return out


def text_of(content):
    from pypdf import PdfReader
    try:
        t = "\n".join(pg.extract_text(extraction_mode="layout") or "" for pg in PdfReader(io.BytesIO(content)).pages)
    except Exception:  # noqa: BLE001 - a broken file reads as nothing
        t = ""
    if len(t.strip()) > 200 or not (shutil.which("tesseract") and shutil.which("pdftoppm")):
        return t, "text layer"
    with tempfile.TemporaryDirectory() as tmp:          # a scanned gazette (the 2016 ones are): OCR in English
        open(f"{tmp}/g.pdf", "wb").write(content)
        subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", f"{tmp}/g.pdf", f"{tmp}/p"], capture_output=True, timeout=600)
        pages = sorted(__import__("glob").glob(f"{tmp}/p*.png"))
        t = "\n".join(subprocess.run(["tesseract", p, "-", "--psm", "6", "-l", "eng"], capture_output=True, text=True,
                                     timeout=300).stdout for p in pages)
    return t, "ocr"


def records(text, p, read="text layer"):
    recs = []
    for council, ward, name, party in members(text):
        slug, district, body = SLUG.get(council.lower().split()[0], (re.sub(r"[^a-z0-9]+", "-", council.lower()), "",
                                                                    council + " Municipal Council"))
        recs.append((f"councillor:DD:{slug}:{ward}",
                     {"type": "councillor", "state": "DD", "body": body, "body_en": body, "body_type": "Municipal Council",
                      "district": district, "ward_no": ward, "name": name, "party": party_of(party), "party_full": party,
                      "election": p.get("election"), "gazette": p.get("title"), "gazette_date": p.get("date"),
                      "url": p["url"], "read": read}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a pdf"
    text, read = text_of(r.content)
    recs = records(text, p, read)
    if not recs:
        return [], [], "no member list"           # most gazettes in the window are other notices: nothing kept
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:12]
    return recs, [(f"councillors/DD/{key}.pdf", r.content, "application/pdf")], ""
