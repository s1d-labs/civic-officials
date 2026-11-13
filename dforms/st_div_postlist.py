"""Division-level officers from a state's own list of officer postings (2026-11-13), for divisions whose own pages and
headquarters district pages name nobody: one PDF that lists every officer of a service with the post the officer holds.
  - West Bengal, Personnel & Administrative Reforms: "Posting of IAS Officers as on DD.MM.YYYY" (par.wb.gov.in, link on
    wbcsdirectory.php; the file name changes with each update). Columns No. | Year | Name | Designation. The five Divisional
    Commissioners (Presidency, Bardhaman, Medinipur, Jalpaiguri, Malda) are in the Designation text, often as "additional
    charge of Divisional Commissioner, Malda Division". No phone numbers.
  - Gujarat Police: "List of members of the Indian Police Service (Gujarat cadre) as on 1st January 2026, updated up to 26th
    January 2026" (police.gujarat.gov.in/upload/IPS_Civil_List-2026_Web18022026.pdf). One entry per officer: name, mobile,
    e-mail, office / residence / fax phone, "Present Post" ("Inspector General of Police, Rajkot Range, Rajkot."). The nine
    range IGs / DIGs.
  - Maharashtra Police: "Quarterly list of Officers of the Indian Police Service and State Police Service as on 06/08/2026"
    (mahapolice.gov.in/uploads/posting_details/<hash>.pdf), one block per range ("AMRAVATI RANGE"), columns Sr No | Designation |
    Name | Office / No ("O: 0721/2663226"). The range IG.

Method: layout text of the PDF (pdftotext -layout, else pypdf layout; dforms/_pdftext.layout_pages). A line that matches the
payload's "first_rx" (named groups "name" and "post", optional "sno") opens an entry; the entry runs to the next such line. The
post column starts where the "post" group starts on the opening line; on the entry's other lines the text chunks (split at 2+
spaces) that start within a few columns of it continue the post. Each payload "posts" rule {"rx", "division"} is searched in
the joined post text: its match is the post of one record (the whole post text is kept in "designation_full"). Phones and
e-mail come from the whole entry text: "(0281) 2477511 (O)" office, "(R)" residence, "(F)" fax, "99784 05368 (M)" mobile.
Entries that name no division of the payload are counted as skipped (provenance.skipped).

Payload: {"reader": "st_div_postlist", "key", "state", "url", "kind": "revenue" | "police", "as_on" (the list's own date),
"body", "first_rx", "break_rx" (a line that opens an entry even when first_rx does not match it), "posts": [{"rx",
"division"}], "col_slack" (default 6), "phone_rx" (office phones written without "(O)")}.
Records (_state.rec, type dept_office): level division, division = the rule's division (as dforms/st_div_<st>.json writes it),
post, name, phone, email, fax, as_on, list_title, src_pos = provenance.line_pos(page, line, opening line) + "entry" (the
serial number). Ids: dept:st_div_postlist:<key>:<serial>:<division>.
"""
import re

import provenance
from dforms import _esw, _state
from dforms._pdftext import layout_pages

METHOD = "pdf text (pdftotext -layout, else pypdf layout): officer posting list, one entry per officer; post column from the opening line"
MODULE = "st_div_postlist"

CHUNK = re.compile(r"\S+(?: \S+)*")
PHONE = re.compile(r"\(?(0\d{2,4})\)?[\s-]*(\d[\d ]{5,9}\d)\s*\((O|R|F)\)")
MOBILE = re.compile(r"\b(\d{5}\s?\d{5})\s*\(M\)")


def entries(pages, first_rx, break_rx=None):
    """[{"sno", "name", "post_col", "page", "line", "head", "lines": [line text, ...]}] in file order. A line that matches
    break_rx but not first_rx also ends the entry before it: when that line laid over the next line matches first_rx (a name cut
    by the PDF: "45  Shri M" + "      akrand Govindbhai Chauhan  IPS/RR ..."), the two make the opening line; else the entry is
    kept with "unread" true (its text is not given to the entry before it)."""
    rx, brk = re.compile(first_rx), re.compile(break_rx) if break_rx else None
    out, cur = [], None
    for pno, text in enumerate(pages, 1):
        lines = text.split("\n")
        skip = False
        for i, ln in enumerate(lines):
            if skip:
                skip = False
                continue
            lno = i + 1
            m = rx.match(ln)
            if not m and brk is not None and brk.match(ln):
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                head = ln.rstrip()
                rest = re.sub(r"^[\s\x00-\x1f]+", "", nxt[len(head):])          # pdftotext puts a \x07 before the cut part
                over = head + rest if rest and not re.sub(r"[\s\x00-\x1f]", "", nxt[:len(head)]) else ""
                m = rx.match(over) if over else None
                if m:
                    ln, skip = over, True
                else:
                    cur = {"sno": "", "name": "", "post_col": 0, "page": pno, "line": lno, "head": ln, "lines": [ln], "unread": True}
                    out.append(cur)
                    continue
            if m:
                cur = {"sno": (m.groupdict().get("sno") or str(len(out) + 1)), "name": _esw.clean(m.group("name")),
                       "post_col": m.start("post"), "page": pno, "line": lno, "head": ln, "lines": [ln]}
                out.append(cur)
            elif cur is not None:
                cur["lines"].append(ln)
    return out


def post_text(e, slack=6):
    """The entry's post: the "post" chunk of the opening line plus the chunks of later lines that start near its column."""
    col = e["post_col"]
    parts = []
    for i, ln in enumerate(e["lines"]):
        for m in CHUNK.finditer(ln):
            if (i == 0 and m.start() == col) or (i > 0 and col - slack <= m.start() <= col + slack):
                parts.append(m.group())
                break
    return _esw.clean(" ".join(parts))


def contacts(e, phone_rx=None):
    """({"O": [...], "R": [...], "F": [...]}, [mobiles], e-mails) of one entry. phone_rx (payload): a regex with groups (std code,
    number) for lists that write office phones without "(O)" ("O: 0721/2663226"); its numbers count as office phones."""
    text = "\n".join(e["lines"])
    ph = {"O": [], "R": [], "F": []}
    for m in PHONE.finditer(text):
        ph[m.group(3)].append(m.group(1) + "-" + re.sub(r"\s", "", m.group(2)))
    if phone_rx:
        for m in re.finditer(phone_rx, text):
            n = m.group(1) + "-" + re.sub(r"\s", "", m.group(2))
            if n not in ph["O"] + ph["R"] + ph["F"]:
                ph["O"].append(n)
    mob = [re.sub(r"\s", "", m.group(1)) for m in MOBILE.finditer(text)]
    return ph, mob, _esw.emails(text)


def parse_pages(p, pages):
    recs = []
    slack = int(p.get("col_slack", 6))
    rules = [(re.compile(r["rx"]), r["division"]) for r in p["posts"]]
    for e in entries(pages, p["first_rx"], p.get("break_rx")):
        if e.get("unread"):
            provenance.skipped("skip: entry opening line not read (break_rx)")
            continue
        full = post_text(e, slack)
        hits = [(m, div) for rx, div in rules for m in [rx.search(full)] if m]
        if not hits:
            provenance.skipped("skip: entry names no division of the payload")
            continue
        ph, mob, email = contacts(e, p.get("phone_rx"))
        police = p.get("kind") == "police"
        for m, div in hits:
            post = re.sub(r"\s+,", ",", _esw.clean(m.group(0))).strip(" ,.")
            pk = _state.post_kind(post) or None
            if re.match(r"(?i)(additional|addl|assistant|asst|joint|jt|deputy|dy|special)\b", post) and pk == "divisional_commissioner":
                pk = "officer"                          # "Assistant Commissioner, Presidency Division": not the head
            elif not police and re.search(r"(?i)^(divisional\s+)?commissioner\b", post):
                pk = "divisional_commissioner"
            phone = ", ".join(ph["O"] + ph["R"] + mob)
            recs.append(_state.rec(
                MODULE, f"{p['key']}:{e['sno']}:{re.sub(r'[^a-z0-9]+', '-', div.lower()).strip('-')}", state=p["state"],
                level="division", post=post, post_kind=pk, name=e["name"],
                body=p.get("body") or (f"{div}, {p['state']} Police" if police else f"Office of the Divisional Commissioner, {div}"),
                body_kind="police" if police else "division", dept="police" if police else "revenue", division=div,
                division_kind=p.get("kind") or "revenue", phone=phone, office_phone=", ".join(ph["O"]) or None,
                residence_phone=", ".join(ph["R"]) or None, mobile=", ".join(mob) or None, fax=", ".join(ph["F"]) or None,
                email=email, designation_full=full, as_on=p.get("as_on"), list_title=p.get("list_title"),
                source=p["url"], src_url=p["url"],
                src_pos=provenance.line_pos(e["page"], e["line"], e["head"], entry=e["sno"])))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or getattr(r, "status_code", 200) >= 400 or r.content[:5] != b"%PDF-":
        return [], [], "the list did not load (no pdf)"
    pages, engine = layout_pages(r.content)
    recs = parse_pages(p, pages)
    for _, d in recs:
        d["method"] = METHOD.replace("pdftotext -layout, else pypdf layout", engine)
        d.update(provenance.at(r, p["url"]))
    note = "" if recs else ("no text layer (scan): needs OCR" if not "".join(pages).strip() else "no entry names a division")
    return recs, [], note
