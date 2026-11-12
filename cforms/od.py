"""Odisha: ward councillors from the State Election Commission's PDFs (sec.odisha.gov.in, India only).
Payload: {"kind": "form-od", "state": "OD", "url", "layout", "election", ...}. Layouts:
- "list": "Name of Elected Councillors (ward wise)" / "Name of Elected Corporators" (general election 2022). One text line per
  ward: "<sl> <DISTRICT> <body> WARD <n> <reservation> <name> <party>". The PDF breaks some party names with stray spaces.
- "votes": one NAC's full count (2023: Hindol, Attabira). Every candidate with votes; the ward number sits in a merged cell, so
  rows are placed by their position on the page. The winner is the top vote of the ward. Payload also has "body" and "district".
"""
import hashlib
import io
import re

from pypdf import PdfReader

METHOD = "pdf text (pypdf)"     # source trail (provenance.py): how this reader reads its sources

RESERVATIONS = ["Reserved For Woman", "Unreserved", "Scheduled Caste Woman", "Scheduled Caste", "Scheduled Tribe Woman",
                "Scheduled Tribe", "Backward Class Woman", "Backward Class"]
PARTIES = ["Biju Janata Dal", "Bharatiya Janata Party", "Indian National Congress", "Independent", "Communist Party of India (Marxist)",
           "Communist Party of India", "Bahujan Samaj Party", "Aam Aadmi Party", "Jharkhand Mukti Morcha"]
CAND = re.compile(r"^(\d+) (.+?) ([A-Z]{2,}) (\d+)$")   # "<sl> <name> <party> <votes>" in a "votes" file
ROW = re.compile(r"^(\d+)\s+([A-Z]{3,}(?:\s[A-Z]{3,})*)\s+(.+?)\s+WARD\s*(\d+)\s+(" + "|".join(RESERVATIONS) + r")\s+(.+)$")


def slug(body):
    s = re.sub(r"[^a-z0-9]+", "-", body.lower()).strip("-")
    return re.sub(r"(^|-)n-a-c$", r"\1nac", s)


def split_party(rest):
    """'Mamata Xalxo Bharatiya Jan ata Party' -> ('Mamata Xalxo', 'Bharatiya Janata Party'): compare without spaces."""
    flat = rest.replace(" ", "")
    for party in PARTIES:
        pf = party.replace(" ", "")
        if flat.endswith(pf):
            n, i = 0, len(rest)
            while n < len(pf):
                i -= 1
                if rest[i] != " ":
                    n += 1
            return rest[:i].strip(), party
    return rest, None


def list_rows(reader, p):
    recs = []
    for pno, page in enumerate(reader.pages, 1):
        for line in (page.extract_text() or "").splitlines():
            m = ROW.match(" ".join(line.split()))
            if not m:
                continue
            sl, district, body, ward, reservation, rest = m.groups()
            name, party = split_party(rest)
            recs.append((body, ward, {"district": district.title(), "body": body, "ward_no": ward, "reservation": reservation,
                                      "name": name, "party": party, "sl_no": int(sl), "page": pno}))
    return recs


def page_lines(page):
    """Text pieces of a page grouped into lines by height: [(y, [(x, text), ...]), ...], top first."""
    bits = []
    page.extract_text(visitor_text=lambda t, cm, tm, fd, fs: t.strip() and bits.append((tm[5], tm[4], t.strip())))
    lines = []
    for y, x, t in sorted(bits, key=lambda b: -b[0]):
        if lines and abs(lines[-1][0] - y) < 3:
            lines[-1][1].append((x, t))
        else:
            lines.append((y, [(x, t)]))
    return lines


def vote_rows(reader, p):
    """Blocks of candidates end at a TOTAL line; the ward label (a number in the ward column) lies inside the block's height."""
    recs = []
    for pno, page in enumerate(reader.pages, 1):
        lines = page_lines(page)
        labels = [(y, t) for y, bits in lines for x, t in bits if 100 < x < 150 and t.isdigit()]
        block, top = [], None
        for y, bits in lines:
            bits.sort()
            if any(t.startswith("TOTAL") and 200 < x < 260 for x, t in bits):
                ward = [t for ly, t in labels if top is not None and y < ly <= top + 3]
                if block and len(ward) == 1:
                    votes, name, party = max(block)
                    recs.append((p["body"], ward[0], {"district": p.get("district"), "body": p["body"], "ward_no": ward[0],
                                                      "name": name, "party": party, "votes": votes, "page": pno}))
                block, top = [], None
                continue
            text = " ".join(" ".join(t for x, t in bits if not (100 < x < 150 and t.isdigit())).split())
            m = CAND.match(text)
            if m and m.group(2) != "NOTA":
                block.append((int(m.group(4)), m.group(2).rstrip(","), m.group(3)))
                top = y if top is None else top
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:16]
    files = [(f"councillors/OD/{key}.pdf", r.content, "application/pdf")]
    try:
        reader = PdfReader(io.BytesIO(r.content))
        rows = (vote_rows if p.get("layout") == "votes" else list_rows)(reader, p)
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = {}
    for body, ward, d in rows:
        d.update({"type": "councillor", "state": "OD", "election": p.get("election", "Odisha 2022"), "url": p["url"],
                  "file": files[0][0]})
        recs[f"councillor:OD:{slug(body)}:{ward}"] = {k: v for k, v in d.items() if v not in (None, "")}
    return list(recs.items()), files, "" if recs else "no winners found in the pdf"
