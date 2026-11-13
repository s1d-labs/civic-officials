"""Andaman and Nicobar Islands: ward councillors of Sri Vijaya Puram (Port Blair) Municipal Council, the only urban body of
the islands (24 wards, 3 nominated members), from the council's RTI section 4(1)(b) disclosure.

pbmc.gov.in/files?id=1023&websection=RTI is a 27-page PDF with a text layer (PDF24, 28.02.2025). Item (viii) lists the
Chairperson, Sr Vice Chairperson and Junior Vice Chairperson, five sub-committees, then "Ward Councillors": a table
S No | Name of Elected Representatives | Ward No | Designation, one line per ward (24). The text is read with pdftotext
-layout (poppler; installed on a GitHub runner when missing). The posts of the chair and the vice chairs go to the
councillor of that name. The site answers from outside India (archive.s1d.me pool copies).
One queue item = the file. Record id councillor:AN:sri-vijaya-puram-mc:<ward no>.
The same file lists the council's officers and staff; they are kept too, as dept_office records (depts.py contract, dept
town_body; reader audit 2026-11-13: 24 records for 286 person rows): item (ix) "directory of its officers and employees"
(Name | Designation | Division | Office phone, 28 rows, cells wrap) -> dept:ce_an:svpmc:dir-<sl>; item (x) "monthly
remuneration" (Sl | Code | Employee Name | Designation | Pay Level, 155 rows) -> dept:ce_an:svpmc:emp-<code>; item (xvi) the
appellate authority, the RTI nodal officer, the PIOs and APIOs (posts with e-mail and phone, no names) -> dept:ce_an:svpmc:
rti-<table>-<sl>. Item (ii) (work allocation) names the same officers as (ix): not read again.
"""
import re
import shutil
import subprocess
import tempfile

from dforms import _esw

METHOD = 'pdf text (pdftotext -layout)'     # source trail (provenance.py): how this reader reads its sources

URL = "https://pbmc.gov.in/files?id=1023&websection=RTI"
BODY, LGD = "Sri Vijaya Puram (Port Blair) Municipal Council", "253098"
ELECTION = "Sri Vijaya Puram Municipal Council (as listed in its RTI 4(1)(b) disclosure of 28.02.2025)"
POSTS = ("Chairperson", "Sr Vice Chairperson", "Junior Vice Chairperson")


def tools():
    if shutil.which("pdftotext"):
        return True
    cmd = "sudo -n apt-get update -q && sudo -n apt-get install -y -q poppler-utils"
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0 and bool(shutil.which("pdftotext"))


def bare(name):
    return re.sub(r"^(Shri|Smti|Smt|Sri|Mr|Mrs|Ms|Dr)\.?\s+", "", name.strip(), flags=re.I).lower()


def parse(text, url=URL):
    posts, cur = {}, None
    head = text.split("Ward Councillors", 1)
    if len(head) < 2:
        return []
    for ln in head[0].splitlines()[-200:]:
        t = ln.strip()
        if t in POSTS:
            cur = t
            continue
        m = re.match(r"\d+\.\s+(.+?)\s*$", t)
        if cur and m:
            posts[bare(m.group(1))] = cur
            cur = None
    recs = []
    for ln in head[1].splitlines():
        m = re.match(r"\s*(\d+)\.?\s+(.+?)\s{2,}(\d{1,2})\s+(Councillor|Member)\b", ln)
        if not m:
            if recs and re.search(r"\(ix\)|directory of its officers", ln):
                break
            continue
        ward = str(int(m.group(3)))
        name = " ".join(m.group(2).split())
        d = {"type": "councillor", "state": "AN", "body": BODY, "lgd_code": LGD, "ward_no": ward, "name": name,
             "position": posts.get(bare(name), "Councillor"), "election": ELECTION, "url": url}
        recs.append((f"councillor:AN:sri-vijaya-puram-mc:{ward}", d))
    return recs


SECTION = re.compile(r"^\s*\((ix|x|xi|xvi)\)\s")
RTI = (("appellate", r"APPELLATE AUTHORITY"), ("nodal", r"NODAL OFFICER FOR RTI"), ("pio", r"PUBLIC INFORMATION OFFICER \(PIO\)"),
       ("apio", r"ASSISTANT PUBLIC INFORMATION OFFICER"))


def sections(text):
    """{roman numeral: text} of the items (ix), (x), (xvi) (the first item (xvi) is empty: ":-")."""
    out, cur = {}, None
    for ln in text.splitlines():
        m = SECTION.match(ln)
        if m:
            cur = m.group(1)
            out[cur] = out.get(cur, "")
        if cur:
            out[cur] += ln + "\n"
    return out


def join(a, b, glue):
    if not a:
        return b
    if not glue or (a[-1].islower() and b[:1].islower()):      # a word or an e-mail / phone cut by the narrow column
        return a + b
    return a + " " + b


def rows(block, serial=r"\d+\.?", glue=None):
    """Rows of a pdftotext -layout table: a row starts on a line whose first run is a serial number; the runs of the lines
    below it (wrapped cells) join the column whose start on the row line is nearest. glue: {column index: ""} for columns whose
    pieces join without a space (e-mail, phone)."""
    out, starts = [], None
    for ln in block.splitlines():
        runs = [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", ln)]
        if not runs:
            continue
        if re.fullmatch(serial, runs[0][1]) and len(runs) >= 3:
            starts = [x for x, _ in runs]
            out.append([t for _, t in runs])
            continue
        if not out or starts is None:
            continue
        for x, t in runs:
            k = min(range(len(starts)), key=lambda i: abs(starts[i] - x))
            if k == 0:
                continue
            out[-1][k] = join(out[-1][k], t, (glue or {}).get(k, " "))
    return out


HEAD = (("sl", r"\bSl\b"), ("department", r"\bName\b"), ("authority", r"\bPublic\b"), ("designation", r"\bDesignat"),
        ("division", r"(?<=\S)\s+(Name|Division)\b|^(?!.*\bDesignat).{0}$"), ("email", r"\bEmail"), ("phone", r"\bPhon"),
        ("address", r"\bOfficial\b"))


def rti_rows(block):
    """[(sl, {column: text})] of one RTI officers table (item xvi). The header line ("Sl  Name of  Designation Name of
    Email-ID  Phone  Official") gives the column starts; every word of every line goes to the column it starts in (cells are
    narrow and touch: "Administrati Administrati santhi.pbmc@pbmc.g"); a row starts with "1." and its wrapped lines follow.
    E-mail and phone pieces join without a space ("prkaruppaiah.pbmc@pbm" + "c.gov.in", "9679" "5087" "64")."""
    starts, out = None, []
    for ln in block.splitlines():
        if starts is None:
            if re.match(r"\s*Sl\b", ln) and "Email" in ln:
                starts = []
                for name, rx in HEAD:
                    if name == "division":
                        m = re.search(r"\bDesignat\S*\s+(Name|Division)\b", ln)
                        if m:
                            starts.append((m.start(1), name))
                        continue
                    m = re.search(rx, ln)
                    if m and not (name == "department" and m.start() > 15):
                        starts.append((m.start(), name))
                starts.sort()
            continue
        words = [(m.start(), m.group(0)) for m in re.finditer(r"\S+", ln)]
        if not words:
            continue
        if re.fullmatch(r"\d+\.", words[0][1]) and words[0][0] < starts[1][0] - 1:
            out.append((words[0][1].rstrip("."), {}))
            words = words[1:]
        if not out:
            continue
        cells, line = out[-1][1], {}
        for x, w in words:
            if "@" in w and not any(n == "email" and s <= x + 1 for s, n in starts):
                # an e-mail that starts left of its head word (Administrative Officer row): the column starts there
                starts = sorted((x if n == "email" else s, n) for s, n in starts)
            col = [n for s, n in starts if s <= x + 1][-1] if any(s <= x + 1 for s, _ in starts) else starts[0][1]
            line[col] = (line.get(col, "") + " " + w).strip()
        for col, t in line.items():
            cells[col] = join(cells.get(col, ""), t, "" if col in ("email", "phone") else " ")
    return out


def staff(text, url=URL):
    """dept_office records of items (ix), (x) and (xvi)."""
    sec = sections(text)
    recs = []
    base = {"dept": "town_body", "level": "body", "area": BODY, "state": "AN", "district": "South Andaman", "lgd_code": LGD,
            "source": url, "src_url": url}
    for r in rows(sec.get("ix", ""), r"\d+"):
        r += [""] * (5 - len(r))
        phone = re.sub(r"\D", "", r[4])
        rid, d = _esw.record("ce_an", f"svpmc:dir-{r[0]}", **base, name=r[1], post=r[2], division=r[3],
                             phone=("03192-" + phone) if len(phone) == 6 else None, list="directory of officers (RTI 4(1)(b) ix)")
        recs.append((rid, d))
    for ln in sec.get("x", "").splitlines():
        m = re.match(r"\s*(\d+)\.\s+(R\d+)\s{2,}(\S.*?)\s{2,}(\S.*?)\s{2,}(\d+)\s*$", ln)
        if m:
            rid, d = _esw.record("ce_an", f"svpmc:emp-{m.group(2)}", **base, name=m.group(3), post=m.group(4),
                                 employee_code=m.group(2), pay_level=m.group(5), serial=m.group(1),
                                 list="officers and employees, monthly remuneration (RTI 4(1)(b) x)")
            recs.append((rid, d))
    xvi = sec.get("xvi", "")
    parts = re.split(r"(?m)^.*(" + "|".join(rx for _, rx in RTI) + r").*$", xvi)
    for i in range(1, len(parts) - 1, 2):
        kind = next(k for k, rx in reversed(RTI) if re.search(rx, parts[i]))
        for sl, c in rti_rows(parts[i + 1]):
            post = c.get("authority") or c.get("designation") or ""
            if c.get("division"):
                post += ", " + c["division"]
            phone = re.sub(r"\D", "", c.get("phone", ""))
            phone = (phone[:5] + "-" + phone[5:]) if phone.startswith("03192") else phone
            rid, d = _esw.record("ce_an", f"svpmc:rti-{kind}-{sl}", **base,
                                 post={"appellate": "Appellate Authority (RTI): ", "nodal": "Nodal Officer, RTI portal: ",
                                       "pio": "Public Information Officer: ", "apio": "Assistant Public Information Officer: "}[kind] + post,
                                 email=c.get("email") or None, phone=phone or None, list="RTI officers (RTI 4(1)(b) xvi)")
            recs.append((rid, d))
    return recs


def fetch(p, get):
    if not tools():
        return [], [], "poppler not available"
    r = get(p.get("url", URL))
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [("councillors/AN/svpmc-rti-4-1-b.pdf", r.content, "application/pdf")]
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content)
        f.flush()
        text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    recs = parse(text, p.get("url", URL))
    ok = bool(recs)
    recs += staff(text, p.get("url", URL))
    return recs, files, "" if ok else "no councillor table"
