"""Delhi: MLAs of the 8th Delhi Legislative Assembly (2025-) from the assembly's "List of Members" PDF
(delhiassembly.delhi.gov.in/sites/default/files/2026-09/list_of_member.pdf, 4 pages, created 2026-09-15). Answers from
Germany too. The home page links the newest list ("List of Members"); items(get) reads that link when get is given.

Table columns: AC No., Constituency Name, Hon'ble Member, Address, Number (one to three phones), Email ID, Party Name. Cells
wrap over several lines, and emails break anywhere ("rajkarankhatri19" / "65@gmail.com"). The reader reads pypdf's layout text
(pdftotext mixes name and address words more often here), cuts each page at the column starts it finds in the data (the x of the phone numbers, the x where
address lines continue) and joins the wrapped parts. Address = the member's address as printed (no separate office or
residence). One queue item = the whole PDF.
"""
import re
from collections import Counter

from dforms import _leg

MODULE = "leg_dl"
HOME = "https://delhiassembly.delhi.gov.in/"
URL = "https://delhiassembly.delhi.gov.in/sites/default/files/2026-09/list_of_member.pdf"
PARTIES = ("BJP", "AAP", "INC", "IND")
ROW = re.compile(r"^\s{0,3}(\d{1,2})\s{2,}\S")
SEG = re.compile(r"\S+(?: \S+)*")


def items(get=None):
    url = URL
    if get is not None:
        r = get(HOME)
        m = re.search(r'href="([^"]*list_of_member[^"]*\.pdf)"', r.text if r is not None else "")
        if m:
            url = m.group(1) if m.group(1).startswith("http") else HOME.rstrip("/") + m.group(1)
    return [{"key": "leg_dl-list", "payload": {"reader": MODULE, "url": url, "state": "DL", "india_only": False}}]


def _segs(line):
    return [(m.start(), m.group()) for m in SEG.finditer(line)]


def _blocks(lines):
    out, cur = [], None
    for ln in lines:
        m = ROW.match(ln)
        if m and 1 <= int(m.group(1)) <= 70:
            cur = [int(m.group(1)), [ln]]
            out.append(cur)
        elif cur is not None and ln.strip() and not re.search(r"Delhi Legislative Assembly|Constituency|Hon'ble", ln):
            cur[1].append(ln)
    return out


ADDR_START = re.compile(r"^(\d|[A-Z]{1,3}-?\d|[A-Z]-\d|H\.?\s?No|House|Plot|Flat|Khasra|Bungalow|Village|Vill|Gali|Pocket|Quarter)", re.I)


def _phone_x(lines):
    for ln in lines:
        for m in re.finditer(r"(?<!\S)\d{8,12}(?!\S)", ln):
            return m.start()
    return None


def _addr_x(blocks):
    """x where the address cells continue on a page: the most common start of continuation cells with a digit or comma."""
    xs = Counter()
    for _, ls in blocks:
        px = _phone_x(ls) or 10 ** 6
        for ln in ls[1:]:
            for x, s in _segs(ln):
                if 15 <= x < px - 4 and re.search(r"[\d,]", s):
                    xs[x] += 1
    return xs.most_common(1)[0][0] if xs else None


def _left(ln, i, addr_x, cons, name, addr):
    """Sort the text left of the phone column into constituency, name and address words."""
    if i == 0:                                           # constituency, name and the address start share the first line
        words = ln.split()
        j = 0
        while j < len(words) and (words[j].isupper() or re.fullmatch(r"\(S\.?C\.?\)", words[j])) and not ADDR_START.match(words[j]):
            j += 1
        k = j
        while k < len(words) and not ADDR_START.match(words[k]):
            k += 1
        cons += words[:j]
        name += words[j:k]
        addr += words[k:]
        return
    ax = addr_x or 10 ** 6
    for x, sg in _segs(ln):
        if x < 15:
            cons.append(sg)
        elif x >= ax - 3:
            addr.append(sg)
        else:
            rest, cut = "", ax - x
            if len(sg) > cut:                            # a name cell and an address cell joined by one space
                while 0 < cut < len(sg) and sg[cut - 1] != " ":
                    cut += 1
                sg, rest = sg[:cut].strip(), sg[cut:].strip()
            if re.search(r"[\d,]", sg):                 # an address line that starts left of the address column
                addr.append((sg + " " + rest).strip())
            else:
                (cons if sg.isupper() else name).append(sg)
                if rest:
                    addr.append(rest)


def _member(no, lines, addr_x, url, prev_mail="", tail=""):
    """(record, orphan): orphan = an email tail printed on this row's first line that belongs to the row above ("com").
    prev_mail: the row above's email; a fragment that repeats its start is the row above's second, hidden email
    (the PDF prints it under this row's cell) and is left out."""
    phone_x = _phone_x(lines) or max(len(ln) for ln in lines)
    cons, name, addr, phones, email, party, orphan = [], [], [], [], [], "", ""
    for i, ln in enumerate(lines):
        right = ln[phone_x - 1:] if len(ln) >= phone_x else ""
        left = ln[:phone_x - 1]
        if i == 0:
            left = re.sub(r"^\s*\d{1,2}", lambda m: " " * len(m.group()), left)
        _left(left, i, addr_x, cons, name, addr)
        for t in re.split(r"[\s,]+", right):
            if not t:
                continue
            if t in PARTIES:
                party = t
            elif re.fullmatch(r"\(?\d[\d()-]{6,}\d", t):
                phones.append(t)
            elif i == 0 and not phones and re.fullmatch(r"(co\.)?(com|in|org)", t):
                orphan = t
            else:
                email.append(t)
    local, cut_off = prev_mail.split("@")[0].lower(), []
    for n, f in enumerate(email):
        for i in range(1, len(f) - 6) if local and n < len(email) - 1 else ():
            if re.fullmatch(r"[a-z0-9]{7}", f[i:i + 7].lower()) and f[i:i + 7].lower() in local:
                cut_off.append(f[i:])
                email[n] = f[:i]
                break
    mail = "".join(email) + tail
    cons_s = " ".join(cons)
    seat, note = _leg.ac_seat("DL", no, cons_s)
    ok = _leg.emails(mail) == mail.lower()
    return _leg.member(MODULE, "DL", "AC", seat, " ".join(name), constituency=cons_s.title(), party=party, source=url,
                       phone=", ".join(phones), email=mail if ok else "", address=" ".join(addr), seat_no=no, note=note,
                       email_raw="" if ok else mail, email_overlap=", ".join(cut_off)), orphan


def parse(pages, url=URL):
    rows = []
    for page in pages:
        blocks = _blocks(page.splitlines())
        addr_x = _addr_x(blocks)
        rows += [[no, lines, addr_x] for no, lines in blocks]
    # an email that ends in "." continues in the next row: as a lone "com" on its first line, or glued into its email ("@gcom")
    tails = [""] * len(rows)
    for n in range(len(rows) - 1):
        (_, d), _ = _member(*rows[n], url)
        if d.get("email_raw", "").endswith("."):
            (_, _), orphan = _member(*rows[n + 1], url)
            if orphan:
                tails[n] = orphan
            elif any(re.search(r"@gcom", ln) for ln in rows[n + 1][1]):
                rows[n + 1][1] = [ln.replace("@gcom", "@g", 1) for ln in rows[n + 1][1]]
                tails[n] = "com"
    recs, prev = {}, ""
    for n, row in enumerate(rows):
        (rid, d), _ = _member(*row, url, prev_mail=prev, tail=tails[n])
        prev = d.get("email") or d.get("email_raw", "")
        recs.setdefault(rid, (rid, d))
    return list(recs.values())


def fetch(p, get):
    from dforms._power import pdf_pages
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [_leg.keep(MODULE, "list_of_member", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    pages = pdf_pages(r.content, layout=True)        # pypdf: here it keeps the columns better than pdftotext
    recs = parse(pages, p["url"])
    return recs, files, "" if recs else "no members"
