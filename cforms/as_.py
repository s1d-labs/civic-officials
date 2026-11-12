"""Assam: ward commissioners/councillors from the State Election Commission's 2022 election reports (sec.assam.gov.in, India only).
Payload: {"kind": "form-as_", "state": "AS", "url", "layout", "election", ...}. Layouts:
- "gazette": Municipal Board Election 2022 report. Its section 18 holds the gazette notifications of winners, per district:
  "... Municipal Boards of <District> District.", then "1. <Name> Municipal Board" and rows "Ward No. <n> <category> <name> <party>".
  Ward numbers can carry a letter ("Ward No. 2(A)"). The report's font prints some capitals as small letters ("chabua"):
  the first letter of each word of a board name is set back to a capital.
- "gmc": Guwahati Municipal Corporation report. "List of Winning Candidates" (ward, name, party) plus votes and reservation
  from the "Contesting Candidate wise vote share" table. Payload also has "body" and "district".
"""
import hashlib
import io
import re

from pypdf import PdfReader

METHOD = "pdf text (pypdf, plain mode)"     # source trail (provenance.py): how this reader reads its sources

DISTRICT = re.compile(r"Municipal\s+Boards\s+of\s+([A-Za-z() ]+?)\s+District", re.I)
BOARD = re.compile(r"^\d+\.\s+(.+?Municipal\s+Board)$", re.I)
CATEGORY = r"(Unreserved|Unserved|Women|SC|ST|OBC)\s*(\(\s*Women\s*\))?"
MB_ROW = re.compile(r"^(?:Ward\s*No\.?\s*)?(\d+)\s*(?:\(\s*([A-D])\s*\))?\s+" + CATEGORY + r"\s+(.+?)\s+([A-Z]{2,}(?:\s*\(\s*M\s*\))?)$", re.I)
GMC_ROW = re.compile(r"^\d+\.?\s+Ward\s*No\.?\s*(\d+)\s+(.+?)\s+([A-Z]{2,}(?:\s*\(\s*M\s*\))?)$")
CAND = re.compile(r"([A-Za-z.]+(?: [A-Za-z.]+)*) ([A-Z]{2,}(?:\(M\))?) (\d+|Uncontested)")
GMC_WARD = re.compile(r"(?<!\d)(\d{1,2}) (Open|Women|SC ?\( ?Women ?\)|ST ?\( ?Women ?\)|SC|ST|OBC) \d{1,3} ")


def slug(body):
    return re.sub(r"[^a-z0-9]+", "-", body.lower()).strip("-")


def cap(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def category(c, women):
    c = {"unserved": "Unreserved", "unreserved": "Unreserved", "women": "Women"}.get(c.lower(), c.upper())
    return f"{c} (Women)" if women else c


def gazette_rows(pages, p):
    start = next((i for i, t in enumerate(pages) if "duly elected from the Wards" in t), None)
    if start is None:
        return []
    recs, district, board, tail = [], None, None, ""
    for pno in range(start, len(pages)):
        if "Political party wise Result of MB" in pages[pno]:
            break
        for li, raw in enumerate(pages[pno].splitlines(), 1):
            line = " ".join(raw.split())
            tail = (tail + " " + line)[-300:]
            m = DISTRICT.search(tail)
            if m:
                district, tail = cap(m.group(1)), ""
                continue
            m = BOARD.match(line)
            if m:
                board = cap(m.group(1))
                continue
            m = MB_ROW.match(line)
            if m and board:
                ward = m.group(1) + (m.group(2) or "").upper()
                recs.append((board, ward, {"district": district, "body": board, "ward_no": ward,
                                           "reservation": category(m.group(3), m.group(4)), "name": m.group(5),
                                           "party": re.sub(r"\s+", "", m.group(6)), "page": pno + 1,
                                           "src_pos": {"page": pno + 1, "line": li, "line_text": raw}}))
    return recs


def gmc_rows(pages, p):
    text = "\n".join(pages)
    a, b = text.find("Contesting Candidate wise vote share"), text.find("List of Winning Candidates")
    if b < 0:
        return []
    votes = " ".join(text[a:b].split()) if a >= 0 else ""
    marks = list(GMC_WARD.finditer(votes))
    seg = {m.group(1): (m.group(2), votes[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(votes)])
           for i, m in enumerate(marks)}
    recs, first = [], next(i for i, t in enumerate(pages) if "List of Winning Candidates" in t)
    for pno in range(first, len(pages)):
        for li, raw in enumerate(pages[pno].splitlines(), 1):
            m = GMC_ROW.match(" ".join(raw.split()))
            if not m:
                continue
            ward, name, party = m.groups()
            party = {"BJO": "BJP"}.get(party, party)    # one typo in the list (ward 38); the count and the tally say BJP
            d = {"district": p.get("district"), "body": p["body"], "ward_no": ward, "name": name, "party": party, "page": pno + 1,
                 "src_pos": {"page": pno + 1, "line": li, "line_text": raw}}
            if ward in seg:
                res, part = seg[ward]
                d["reservation"] = re.sub(r"\s*\(\s*", " (", res).replace(" )", ")")
                v = re.search(r"\s+".join(map(re.escape, name.split())) + r"\s+[A-Z()]+\s+(\d+|Uncontested)", part, re.I)
                v = v.group(1) if v else None
                if v is None:   # name spelt otherwise in the count ("Satapa"/"Sutapa"): the top vote, if its party is the winner's
                    top = max(((int(n) if n.isdigit() else 10 ** 9, pt) for _, pt, n in CAND.findall(part)), default=None)
                    v = (str(top[0]) if top[0] < 10 ** 9 else "Uncontested") if top and top[1] == party else None
                if v:
                    d["votes"] = int(v) if v.isdigit() else None
                    d["uncontested"] = True if not v.isdigit() else None
            recs.append((p["body"], ward, d))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    key = hashlib.sha1(p["url"].encode()).hexdigest()[:16]
    files = [(f"councillors/AS/{key}.pdf", r.content, "application/pdf")]
    try:
        pages = [pg.extract_text() or "" for pg in PdfReader(io.BytesIO(r.content)).pages]
        rows = (gmc_rows if p.get("layout") == "gmc" else gazette_rows)(pages, p)
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    seen = {}
    for body, ward, d in rows:
        seen.setdefault(body, set()).add(d.get("district"))
    recs = {}
    for body, ward, d in rows:
        if len(seen[body]) > 1:     # two boards of one name (Lakhipur in Cachar and in Goalpara): the id carries the district
            body = f"{body} {d.get('district')}"
        d.update({"type": "councillor", "state": "AS", "election": p.get("election", "Assam 2022"), "url": p["url"],
                  "file": files[0][0]})
        recs[f"councillor:AS:{slug(body)}:{ward}"] = {k: v for k, v in d.items() if v not in (None, "")}
    return list(recs.items()), files, "" if recs else "no winners found in the pdf"
