"""Jammu and Kashmir: District Development Council (DDC) members, DDC General Election 2020 (Nov-Dec 2020, 280 constituencies,
20 districts), from the State Election Commission's final result print: https://secjk.nic.in/ResultDDC_ms/DDC_2020_Result_final.pdf
(linked from secjk.nic.in/DDC_Result_2020.html; 10 pages, a browser print of ceojk.nic.in/panchayater/ dated 13-09-2022; text PDF).

Table: Sr No, District, Constituency ("1-Achabal"), Winner "Name (Party, Symbol - X), Votes Polled - N", Runner Up (same form),
Vote Margin. Cells wrap over 2-3 lines; pypdf layout text keeps the columns apart: the row's first line holds Sr, district,
constituency, the first part of both cells and the margin; the next lines hold the rest of each cell. A chunk (text between 2+
spaces) goes to the winner when it ends before the "Runner Up" header column (page 1 header; later pages have none), else to the runner up; a chunk that ends before
the "Winner" header column continues the constituency.
Checks: winner votes - runner-up votes = margin (vote_check "ok" / "differs"). Full file 2026-11-13: 278 rows, 264 read (263
checks ok, 1 without runner-up); 14 rows whose winner cell does not parse are left out (cells split oddly across lines).
Terms: DDCs met first in Feb 2021 for five years, so these terms have ended or end in 2026 (status says so). Panches and
sarpanches (2018, term ended 9 Jan 2024) and BDC chairpersons (Oct 2019, term ended 2024) are not read here: the BDC winner
list (ceojk.nic.in/pdf/BDC_2019/winner.pdf) is a Xerox scan (OCR on the runners), the 2018 panchayat results are press notes.
LGD: J&K ZP level = "District Planning & Development Board" (20 bodies): the loader matches the district name.
One queue item (1 GET, 1.3 MB). Records: pri:pri_jk:ddc2020:<sr no>.
"""
import re

import provenance
from dforms import _pri
from dforms._esw import pdf_pages

METHOD = "pdf text (pypdf layout; columns split at the header positions)"     # source trail (provenance.py)
MODULE = "pri_jk"
URL = "https://secjk.nic.in/ResultDDC_ms/DDC_2020_Result_final.pdf"
ELECTION = "Jammu and Kashmir DDC General Election 2020"
ROW = re.compile(r"^\s*(\d{1,3})\s{2,}([A-Z][A-Za-z .]+?)\s{2,}")
PERSON = re.compile(r"^(?P<name>.*?)\s*\((?P<party>[^,()]*?),\s*Symbol\s*-\s*(?P<symbol>.*?)\)\s*,?\s*Votes\s*Polled\s*-\s*(?P<votes>\d+)\s*$")


def items(get=None):
    return [{"key": f"{MODULE}:ddc2020", "payload": {"reader": MODULE, "url": URL, "state": "JK", "india_only": True,
                                                     "route": "direct", "expected": 278}}]


def chunks(line):
    """[(start, end, text)] of the runs of text separated by 2+ spaces."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def split(line, wcol, rcol):
    """One continuation line -> {"cons", "win", "run"} chunk lists by the column each chunk ends in."""
    parts = {"cons": [], "win": [], "run": []}
    for _a, b, t in chunks(line):
        parts["cons" if b < wcol else "win" if b <= rcol + 2 else "run"].append(t)
    return parts


def complete(row):
    """A row is complete when its winner cell ends with the vote count and its runner-up cell does too (or is empty)."""
    done = re.compile(r"Votes\s*Polled\s*-\s*\d+\s*$")
    w, r = " ".join(row["win"]), " ".join(row["run"])
    return bool(done.search(w)) and (not r or bool(done.search(r)))


def person(text):
    t = _pri.clean(text)
    m = PERSON.match(t)
    if not m:
        return {"raw": t}
    return {"name": _pri.clean(m["name"]), "party": _pri.clean(m["party"]), "symbol": _pri.clean(m["symbol"]),
            "votes": _pri.int_or_none(m["votes"]), "raw": t}


def parse(pages):
    """[(page, line, fields)] for every result row of the PDF text pages."""
    out, wcol, rcol = [], None, None
    for pn, text in enumerate(pages, 1):
        lines = text.split("\n")
        hi = next((i for i, ln in enumerate(lines) if "Runner Up" in ln and "Winner" in ln), None)
        if hi is not None:
            wcol, rcol = lines[hi].index("Winner"), lines[hi].index("Runner Up")
        elif wcol is None:
            continue        # pages after the first carry no header: the first page's columns are used
        else:
            hi = -1
        carry = []          # lines after a complete row: the first part of the next row's cells (printed above its Sr line)
        for i in range(hi + 1, len(lines)):
            ln = lines[i]
            if not ln.strip() or "Disclaimer" in ln or "http" in ln or re.match(r"^\s*No\s+Margin\s*$", ln):
                continue
            m = ROW.match(ln)
            if not m:
                row = out[-1][2] if out and out[-1][0] == pn and not out[-1][2]["done"] else None
                parts = split(ln, wcol, rcol)
                if row is not None:
                    for k in ("cons", "win", "run"):
                        row[k] += parts[k]
                    row["lines"].append(ln)
                    row["done"] = complete(row)
                else:
                    carry.append((ln, parts))
                continue
            row = {"sr": m.group(1), "district": m.group(2).strip(), "cons": [], "win": [], "run": [], "margin": "",
                   "lines": [c[0] for c in carry] + [ln]}
            for _, parts in carry:
                for k in ("cons", "win", "run"):
                    row[k] += parts[k]
            carry = []
            first = chunks(ln[m.end():])
            off = m.end()
            if first and first[-1][2].isdigit() and first[-1][0] + off > rcol:
                row["margin"] = first.pop()[2]
            for n, (a0, b0, t) in enumerate(first):
                b0 = b0 + off
                k = "cons" if (n == 0 and b0 < wcol + 2 and not re.search(r"[(),]", t)) else "win" if b0 <= rcol + 2 else "run"
                row[k].append(t)
            row["done"] = complete(row)
            out.append((pn, i + 1, row))
    for _, _, row in out:
        row["constituency"] = "".join(c if c.endswith("-") else c + " " for c in row.pop("cons")).strip()
        row["winner"], row["runner"] = " ".join(row.pop("win")), " ".join(row.pop("run"))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    pages = pdf_pages(r.content)
    if not pages:
        return [], [], "not a readable pdf"
    recs = []
    for pn, ln, v in parse(pages):
        w, ru = person(v["winner"]), person(v["runner"])
        if not w.get("name"):
            continue
        mg = _pri.int_or_none(v["margin"])
        check = None
        if mg is not None and w.get("votes") is not None and ru.get("votes") is not None:
            check = "ok" if w["votes"] - ru["votes"] == mg else "differs"
        cm = re.match(r"^(\d+)\s*-\s*(.+)$", v["constituency"])
        recs.append(_pri.record(
            MODULE, f"ddc2020:{v['sr']}", state="JK", level="zp", role="member", post="DDC Member",
            post_regional="District Development Council Member", name=w["name"], party=w.get("party"), symbol=w.get("symbol"),
            votes=w.get("votes"), runner_up=ru.get("name") or ru.get("raw"), runner_up_party=ru.get("party"),
            runner_up_votes=ru.get("votes"), margin=mg, vote_check=check, district=v["district"], body_name=v["district"],
            constituency=v["constituency"], ward_no=cm.group(1) if cm else None, ward=v["constituency"],
            election=ELECTION, election_year=2020, status="term ended or ending (elected Dec 2020; five-year term from Feb 2021)",
            source=p["url"], **provenance.at(r, p["url"]),
            src_pos=provenance.line_pos(pn, ln, v["lines"][0], lines=v["lines"]),
            cells={"Sr No": v["sr"], "District": v["district"], "Constituency": v["constituency"], "Winner": w["raw"],
                   "Runner Up": ru["raw"], "Vote Margin": v["margin"]}))
    return recs, [], "" if recs else "no rows"
