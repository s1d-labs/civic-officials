"""Andhra Pradesh: Mayors and Chairpersons of the urban bodies, 2nd ordinary elections 2026 (poll 01.11.2026, count 03.11.2026).
In 2026 the heads were elected DIRECTLY by the voters (one ballot per body), so the SEC prints them like ward results.

Sources (sec.ap.gov.in, a React site; the file list is in its JS bundle, section "Results"):
- Uploads/Doc26/Rsls/Mayors - Results 2026.pdf (7 pages, 13 corporations of phase I)
- Uploads/Doc26/Rsls/Chairpersons - Results, 2026.pdf (23 pages, municipalities and nagar panchayats of phase I)
"PROFORMA - X (Report on votes secured by each contesting candidate for Mayor / Chairperson)", dated 04.11.2026. Columns:
Sl. No. | District | Urban Local Body | Office reserved for | Date of Poll | Total voters | Polled | Invalid | Valid | candidate no. |
Name | Votes secured | Party | Elected (E) / Defeated (D) | Remarks. The body cells stand on the body's first candidate row only.
A long name wraps onto the lines above and below its row (the row line then has no name). Text layer, no OCR.
Later bodies (phase II, 23 ULBs; Mydukur postponed) and the indirect deputy-mayor / vice-chairperson elections of 03-04.11.2026
are not in these files.
One queue item = one file. Payload {"kind": "form-ap_heads", "state": "AP", "url", "post" ("Mayor" | "Chairperson")}.
One record per body: the elected candidate, with every candidate of the body in "candidates". Record id
councillor:AP:head:<district>:<body>. Answers from India (sec.ap.gov.in did not answer the pool runners in the archive).
"""
import re
import subprocess
import tempfile

import provenance

METHOD = "pdf text (pdftotext -layout)"     # source trail (provenance.py): how this reader reads its sources

BASE = "https://sec.ap.gov.in/Uploads/Doc26/Rsls/"
FILES = {"Mayor": BASE + "Mayors%20-%20Results%202026.pdf", "Chairperson": BASE + "Chairpersons%20-%20Results,%202026.pdf"}
ELECTION = "Andhra Pradesh urban local bodies 2026 (poll 01.11.2026, direct election of the {post})"
N = r"(?:\d+|-)"
ROW = re.compile(r"^\s*(?:(?P<sl>\d+)\s+)?(?:(?P<pre>[^\d\s-].*?)\s+(?:(?P<date>\d{2}\.\d{2}\.\d{4}\S*(?:\s*&)?|-)\s+)?"
                 r"(?P<total>" + N + r")\s+(?P<polled>" + N + r")\s+(?P<invalid>" + N + r")\s+(?P<valid>" + N + r")\s+)?"
                 r"(?P<cno>\d+|-)\s+(?P<name>\S.*?)??\s*(?P<votes>\d+|-)\s+"
                 r"(?:(?P<party>\S.*?)\s+)?(?P<res>Elected|Defeated)\b\s*(?P<rem>.*)$", re.I)
# a row whose votes, party and result stand on the next line (a long name filled the name column)
HALF = re.compile(r"^\s*(?:(?P<sl>\d+)\s+)?(?:(?P<pre>[^\d\s-].*?)\s+(?:(?P<date>\d{2}\.\d{2}\.\d{4}\S*(?:\s*&)?)\s+)?"
                  r"(?P<total>\d+)\s+(?P<polled>\d+)\s+(?P<invalid>\d+)\s+(?P<valid>\d+)\s+)?(?P<cno>\d+)\s+(?P<name>[A-Za-z].*?)\s*$")
TAIL = re.compile(r"^\s+(?P<votes>\d+)\s+(?:(?P<party>\S.*?)\s+)?(?P<res>Elected|Defeated)\b\s*(?P<rem>.*)$", re.I)
START = re.compile(r"^\s*1\s+2\s+3\s+4\s+5\s+6")
DATE = re.compile(r"\d{2}\.\d{2}\.\d{4}")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


class Row:
    def __init__(self, i, m, raw, tail=None):
        self.i, self.m, self.raw, self.tail = i, m, raw, tail
        self.name = [m.group("name")] if m.group("name") else []
        self.pre, self.post, self.left = [], [], []

    def g(self, k):
        if self.tail is not None and k in ("votes", "party", "res", "rem"):
            return self.tail.group(k)
        return self.m.group(k)


def cols_of(m):
    """Start offsets of the district, body and reserved cells of a full body row (pre split on 2+ spaces)."""
    out, base = [], m.start("pre")
    for x in re.finditer(r"\S+(?: \S+)*", m.group("pre")):
        out.append((base + x.start(), x.group(0)))
    return out


def parse_text(raw, post):
    """pdftotext -layout text -> bodies [{district, body, reserved, date, totals, candidates, elected, page}]."""
    bodies, cols = [], None
    for pno, page in enumerate(raw.split("\f"), 1):
        lines = page.split("\n")
        started, rows, extra, skip = False, [], [], set()
        for i, line in enumerate(lines):
            if not started:
                started = bool(START.match(line))
                continue
            if not line.strip() or i in skip:
                continue
            m = ROW.match(line)
            if m:
                rows.append(Row(i, m, line))
                continue
            h = HALF.match(line)
            nx = next((j for j in range(i + 1, min(i + 3, len(lines))) if lines[j].strip()), None)
            t2 = TAIL.match(lines[nx]) if h and nx is not None else None
            if h and t2:
                rows.append(Row(i, h, line, t2))
                skip.add(nx)
                continue
            extra.append((i, line))
        for r in rows:
            if r.m.group("total") and r.m.group("pre") and len(cols_of(r.m)) >= 3:
                cols = [c[0] for c in cols_of(r.m)][:3]
        name_lo = lambda r: r.m.end("cno")
        for i, line in extra:
            nxt = next((r for r in rows if r.i > i), None)
            prv = next((r for r in reversed(rows) if r.i < i), None)
            ref = nxt or prv
            if ref is None:
                continue
            lo = name_lo(ref)
            seg = line[lo:].strip() if len(line) > lo else ""
            seg = re.sub(r"\s{2,}.*$", "", seg)
            left = [(x.start(), x.group(0)) for x in re.finditer(r"\S+(?: \S+)*", line[:lo]) if x.start() < lo - 2]
            if seg and not re.fullmatch(r"[\d\s-]+", seg):
                if nxt is not None and not nxt.name and (prv is None or nxt.i - i <= i - prv.i or prv.name):
                    nxt.pre.append(seg)
                elif prv is not None:
                    prv.post.append(seg)
            if re.match(r"^\s*\d+\s{2,}[A-Za-z]", line) and not seg:
                continue           # a numbered body row without candidates (Chirala: counting postponed): not a wrapped cell
            if left:
                # body cells that wrap: to the nearest body row (above or below)
                near = sorted((r for r in rows if r.m.group("total")), key=lambda r: abs(r.i - i))
                if near and abs(near[0].i - i) <= 3:
                    near[0].left.extend((x, s, i < near[0].i) for x, s in left)
        cur = bodies[-1] if bodies else None
        for r in rows:
            m = r.m
            if m.group("total"):
                cells = {"district": [], "body": [], "reserved": [], "date": []}
                parts = [(x, s, None) for x, s in cols_of(m)] + r.left
                for x, s, above in sorted(parts, key=lambda q: (q[2] is False, q[0])):
                    if DATE.search(s) or s in ("&", "-"):
                        cells["date"].append(s)
                        continue
                    c = cols or [0, 20, 40]
                    k = "district" if x < c[1] - 2 else "body" if x < c[2] - 2 else "reserved"
                    cells[k].append(s)
                if m.group("date"):
                    cells["date"].insert(0, m.group("date"))
                num = lambda k: int(m.group(k)) if m.group(k).isdigit() else None
                cur = {"district": " ".join(cells["district"]) or (cur or {}).get("district"),
                       "body": " ".join(cells["body"]).replace("- ", "-"), "reserved": " ".join(cells["reserved"]) or None,
                       "date": " ".join(cells["date"]) or None, "total_voters": num("total"), "polled": num("polled"),
                       "invalid": num("invalid"), "valid": num("valid"), "candidates": [], "page": pno}
                bodies.append(cur)
            if cur is None:
                continue
            name = re.sub(r"^[`'\s.,-]+", "", " ".join(r.pre + r.name + r.post)).strip()
            party = (r.g("party") or "").strip()
            votes = r.g("votes")
            cur["candidates"].append({"serial": int(m.group("cno")) if m.group("cno").isdigit() else None, "name": name,
                                      "votes": int(votes) if votes.isdigit() else None,
                                      "party": None if party in ("", "-", "NOTA") and name.upper() != "NOTA" else party or None,
                                      "result": r.g("res").title(), "remarks": (r.g("rem") or "").strip(" -") or None,
                                      "src_pos": provenance.line_pos(pno, r.i + 1, r.raw,
                                                                     row=int(m.group("sl")) if m.group("sl") else None)})
    for b in bodies:
        won = [c for c in b["candidates"] if c["result"] == "Elected"]
        b["elected"] = won[0] if len(won) == 1 else None
        b["unopposed"] = bool(b["elected"] and b["elected"]["remarks"] and re.match(r"(?i)unani|unopp", b["elected"]["remarks"]))
        vs = [c["votes"] for c in b["candidates"]]
        b["votes_check"] = (sum(vs) == b["valid"]) if b["valid"] is not None and None not in vs else None
    return bodies


def records(bodies, p):
    post = p.get("post", "Chairperson")
    out = []
    for b in bodies:
        w = b["elected"]
        if not w:
            continue
        d = {"type": "councillor", "state": "AP", "body": b["body"], "district": b["district"], "ward_no": "chair",
             "position": post, "name": w["name"], "party": w["party"], "votes": w["votes"], "reservation": b["reserved"],
             "poll_date": b["date"], "total_voters": b["total_voters"], "polled": b["polled"], "invalid": b["invalid"],
             "valid": b["valid"], "remarks": w["remarks"], "direct": True, "unopposed": b["unopposed"] or None,
             "votes_check": b["votes_check"],
             "candidates": [{k: v for k, v in c.items() if k != "src_pos"} for c in b["candidates"]],
             "election": ELECTION.format(post=post.lower() + "s"), "url": p.get("url"), "page": b["page"],
             "src_pos": w["src_pos"]}
        out.append((f"councillor:AP:head:{slug(b['district'])}:{slug(b['body'])}", {k: v for k, v in d.items() if v not in (None, "")}))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.content[:5] != b"%PDF-":
        return [], [], "no answer"
    files = [(f"councillors/AP/heads-{slug(p.get('post'))}-2026.pdf", r.content, "application/pdf")]
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content)
        f.flush()
        raw = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    bodies = parse_text(raw, p.get("post"))
    recs = records(bodies, p)
    return recs, files, "" if recs else f"no elected head read ({len(bodies)} bodies)"


def items(get=None):
    return [{"key": f"ap-heads-2026-{slug(post)}", "payload": {"kind": "form-ap_heads", "state": "AP", "url": url, "post": post}}
            for post, url in FILES.items()]
