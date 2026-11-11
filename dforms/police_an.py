"""Andaman and Nicobar Islands Police: the RTI suo motu manual on the UT portal (andamannicobar.gov.in/pdf/Police Suo Motu.pdf,
222 pages, 21 MB; the police site's own hosts do not answer). Works from outside India. The block "Police Stations with
Landline Phone Numbers" (25 PS) and the next one, "Out Posts with Landline Phone Numbers" (7 OP): "N. PS <name> <phone>".
No officer names. The next block (fire stations) ends the read. Record id dept:police_an:<station>."""
import io
import re

from dforms._police import clean, phones, rec, slug, uniq

M = "police_an"
URL = "https://andamannicobar.gov.in/pdf/Police%20Suo%20Motu.pdf"
ROW = re.compile(r"^\s*\d+\.\s+((?:PS|OP)\s.+?)\s+((?:\+?\d[\d\s,/-]{5,})+)$")


def parse(texts, url=URL):
    recs, mode = [], None
    for t in texts:
        lines = (t or "").splitlines()
        i = 0
        while i < len(lines):
            ln = clean(lines[i]) or ""
            i += 1
            if "Police Stations with Landline Phone Numbers" in ln:
                mode = "police station"
                continue
            if "Out Posts with Landline Phone Numbers" in ln:
                mode = "out post"
                continue
            if mode and re.search(r"with Landline Phone Numbers", ln):
                return uniq(recs)
            m = ROW.match(ln) if mode else None
            if not m:
                continue
            num = m.group(2)
            while num.rstrip().endswith(",") and i < len(lines) and re.fullmatch(r"[\d\s,-]+", lines[i].strip() or "x"):
                num += " " + lines[i].strip()
                i += 1
            area = m.group(1)
            recs.append(rec(M, slug(area), area=area, office_type=mode, post="Station (landline)", phone=phones(num),
                            state="AN", source=url))
    return uniq(recs)


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [(f"depts/police/{M}/police-suo-motu.pdf", r.content, "application/pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    from pypdf import PdfReader
    texts = []
    try:
        for page in PdfReader(io.BytesIO(r.content)).pages:
            t = page.extract_text() or ""
            if texts or "Police Stations with Landline Phone Numbers" in t:
                texts.append(t)
            if texts and "Fire Stations with Landline" in t:
                break
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = parse(texts, url)
    return recs, files, "" if recs else "no rows"
