"""Maharashtra: members of the 15th Maharashtra Legislative Assembly (2024-) from the Election Commission's notification of the
elected members, as printed in the Maharashtra Government Gazette of 24 November 2024
(mls.org.in/PDF2025/15-Assembly-24-11-2024.pdf, 19 pages; the legislature's "list of MLA" page links this file). Answers from
Germany. The legislature's NeVA site (mhla.neva.gov.in) lists only 4 members (2026-11-11).

Names only: AC number and name, member's name, party (pages 2-9 in English; pages 10-19 repeat the schedule in Marathi, which
the reader skips). No phone, no email, no address. Columns: the reader takes each row's own column starts and adds the wrapped
lines below it (name and party often take two lines). The notification is from the general election: a later by-election is not
in it. The reader needs poppler's pdftotext (the India pool servers have it): pypdf's layout puts one space between a long
name and its party, so the columns run together (2026-11-11: 214 of 288 rows wrong). On a GitHub runner the item fails and
goes back to the queue (as dforms/leg_mp.py). One queue item = the PDF. Record ids: dept:leg_mh:MH-AC-<no>.
"""
import re

from dforms import _leg

MODULE = "leg_mh"
URL = "https://mls.org.in/PDF2025/15-Assembly-24-11-2024.pdf"
SEATS = 288
ROW = re.compile(r"^\s{0,12}(\d{1,3})\s+(\S.*?)\s{2,}(\S.*?)\s{2,}(\S.*?)\s*$")
SHORT = re.compile(r"^\s{0,12}(\d{1,3})\s+(\S.*?)\s{2,}(\S.*?)\s*$")       # no party on the row's first line
PARTY_START = ("Bharatiya Janata Party", "Indian National Congress", "Shiv Sena", "Nationalist Congress Party", "Samajwadi Party",
               "Independent", "Jan Surajya Shakti", "Communist Party", "All India Majlis", "Rashtriya ", "Peasants And Workers")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def items(get=None):
    return [{"key": f"{MODULE}-gazette", "payload": {"reader": MODULE, "url": URL, "state": "MH", "india_only": True}}]     # pdftotext: the India servers have it, the GitHub runners do not


def rows(pages):
    """[(AC no, constituency, name, party)] from the English schedule. Two pdftotext quirks: a long name runs into the party
    with one space ("... Wooike Bharatiya Janata Party": the known party names split it), and a row's first line can carry
    only the last word of the row above ("113 Nandgaon   Nanasaheb": that word is the end of 112's name)."""
    out, cur, cols = {}, None, None
    split_party = re.compile(r"^(.*\S)\s+((?:" + "|".join(re.escape(p) for p in PARTY_START) + r").*)$")
    for page in pages:
        for line in page.splitlines():
            if not line.strip() or DEVANAGARI.search(line):
                cur = None
                continue
            m = ROW.match(line)
            s = None if m else SHORT.match(line)
            if m and re.search("[A-Za-z]", m.group(2)) and 1 <= int(m.group(1)) <= SEATS and int(m.group(1)) not in out:
                no, cons, name, party = int(m.group(1)), m.group(2), m.group(3), m.group(4)
                cols = (m.start(2), m.start(3), m.start(4))
                cur = out[no] = {"cons": [cons], "name": [name], "party": [party], "cols": cols}
                continue
            if s and cols and re.search("[A-Za-z]", s.group(2)) and 1 <= int(s.group(1)) <= SEATS and int(s.group(1)) not in out:
                k = split_party.match(s.group(3))
                no = int(s.group(1))
                if k:                                            # name and party with one space between them
                    cur = out[no] = {"cons": [s.group(2)], "name": [k.group(1)], "party": [k.group(2)], "cols": cols}
                else:                                            # the word belongs to the row above; this row's name follows
                    if no - 1 in out:
                        out[no - 1]["name"].append(s.group(3))
                    cur = out[no] = {"cons": [s.group(2)], "name": [], "party": [], "cols": cols}
                continue
            if cur is None or re.match(r"^\s*\d", line):
                cur = None
                continue
            c, n, p = cur["cols"]
            for key, a, b in (("cons", c, n), ("name", n, p), ("party", p, None)):
                part = line[max(a - 2, 0):(b - 2) if b else None].strip()
                if part:
                    cur[key].append(part)
    return [(no, " ".join(d["cons"]), " ".join(d["name"]), re.sub(r"\s*[–-]\s*$", "", " ".join(d["party"])).replace(" – ", " - "))
            for no, d in sorted(out.items())]


def parse(pages, url=URL):
    recs = []
    for no, cons, name, party in rows(pages):
        seat, note = _leg.ac_seat("MH", no, cons)
        recs.append(_leg.member(MODULE, "MH", "AC", seat, re.sub(r"\s+", " ", name), constituency=re.sub(r"\s+", " ", cons),
                                party=re.sub(r"\s+", " ", party), source=url, seat_no=no, note=note,
                                house="Maharashtra Legislative Assembly (15th)",
                                source_note="ECI notification No. 308/MH-LA/2024 of 24 November 2024 (names and parties only)"))
    return recs


def fetch(p, get):
    from dforms import _pdftext
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "15-Assembly-24-11-2024", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    pages, engine = _pdftext.layout_pages(r.content)
    if engine != "pdftotext":
        return [], files, "needs pdftotext: pypdf joins the name and party columns of this PDF"
    recs = parse(pages, p["url"])
    return recs, files, "" if len(recs) > SEATS // 2 else f"only {len(recs)} members read"
