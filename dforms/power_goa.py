"""Goa: Electricity Department official telephone directory 2026-27 (one text PDF, 37 pages),
www.goaelectricity.gov.in/wp-content/uploads/2026/06/Telephone-Directory-2026-27-1.pdf. India only (403 from Germany). One item.

The PDF is one table (Sr. No, Name of Officers/Officials & Designation, Mobile, Office Landline, Fax, E-mail) in office blocks
headed "Head Office ...", "Office of the Superintending Engineer, Elect. Circle-I(S), Margao", "Office of the Executive Engineer,
Elect. Div- I, Panaji", "Office of the Sub-Divisional Engineer, Sub-Div-I, Corlim". The plain text (not layout) keeps each cell
together: "N." starts an entry, then the name/designation lines, then phones, then e-mails (wrapped: "...gov.i" + "n").
Records: one per entry (about 620): the block's level (circle / division / subdivision), and level section for Junior Engineers,
"Section Office <place>" (complaint centres) and "Sub-Station <place>" in a sub-division block. Name = text before the first comma
when it is a person; "Shri. X (Jr. Engineer), Navelim Section Office" keeps the bracketed post whole in the post. PBX lines
"(0832)2426022" + "ext. 115" are phones, not post text. Record id dept:power_goa:<block>-<entry no>.
"""
import re

from dforms._power import Out, clean, email, raw, slug

METHOD = "pdf text (pypdf, plain)"     # source trail (provenance.py): how this reader reads its sources

URL = "https://www.goaelectricity.gov.in/wp-content/uploads/2026/06/Telephone-Directory-2026-27-1.pdf"
HEAD = re.compile(r"^\s*(Office of the .*Engineer.*|Head Office.*)$")
NUM = re.compile(r"^\s*(\d{1,3})(?:\.\s*|\s+|$)(.*)$")
PHONE = re.compile(r"^(?:\+?91[- ]?)?(\d{10}|\d{7}|0\d{2,4}[- ]?\d{6,7})/?$")
DESIG = re.compile(r"(?<![A-Za-z])(Chief|Superintending|Exe\w*\.?\s*Eng\w*|Asst+\.?\s*Eng\w*|Assistant|Junior|Jr\.|Dy\.|Director|"
                   r"Joint|Jt\.|J\.?E\b|A\.?E\b|J/E|A/E|Accounts|Section Office|Sub\s*-?\s*Station|Technical|Office)", re.I)
MAILPART = re.compile(r"^[\w.-]*(gov\.in?|nic\.in|\.com|co\.in|\.in|electricit\w*|\.goa)$|^[a-z]{1,2}$", re.I)
SECTION = re.compile(r"(Section\s+Office|Secton\s+Office|Sub\s*-?\s*Station)\s+(.+?)(?:\s*\(?Complaint.*)?$", re.I)
SUBONLY = re.compile(r"^(?i:Sub)[\s.-]*(?i:Div)\S*?\s*[-–]?\s*[IVX]+\s*(\([A-Z ]*\))?\.?$")
PLACE_FIRST = re.compile(r"(?<![\w/])((?!(?:JE|AE|HT|KV|Office|New|Sub|Div|Technical)\b)[A-Z][\w'-]+(?:\s(?:[A-Z][\w'-]+))?)\s*,?\s*"
                         r"(?i:Sec?ti?on\s+off\w*\.?|Sub\s*-?\s*Station)")
JE = re.compile(r"\b(Junior\s+Eng|Jr\.?\s*Eng|J\.?E\b|J/E)", re.I)


def block_of(h):
    """(level, area) of an office heading."""
    h = " ".join(h.split())
    tail = clean(h.rsplit(",", 1)[-1].strip(" .")) if "," in h else h
    if tail:
        tail = clean(re.sub(r"^(?i:Sub)[\s.-]*(?i:Div)\S*?[-–\s]*[IVX]+[-–\s]+(?=[A-Z][a-z])", "", tail)) or tail
    if re.search(r"Head Office|Chief Electrical", h, re.I):
        return "state", "Head Office, Panaji"
    m = re.search(r"Circle\s*-?\s*([IVX]+\s*\(?[A-Z]?\)?)", h, re.I)
    if "Superintending" in h and m:
        return "circle", f"{tail} (Circle-{m.group(1).replace(' ', '')})"
    m = re.search(r"(?i:Sub[ .-]*Div(?:ision)?)\.?\s*[-–]?\s*([IVX]+\s*(?:\([A-Z ]+\))?)", h)
    if "Sub-Divisional" in h or "Sub Divisional" in h:
        return "subdivision", f"{tail} (Sub-Div-{m.group(1).replace(' ', '')})" if m else tail
    m = re.search(r"(?i:Div)\.?\s*-?\s*([IVX]+(?:\s*\([A-Z&]+\))?)", h)
    if "Executive Engineer" in h:
        return "division", f"{tail} (Div-{m.group(1).replace(' ', '')})" if m else tail
    return "other", tail


def entries(pages, pos=None):
    """[(heading, number, text lines, phones, email parts)] from the PDF's plain text, one string per page.
    pos: a list; when given, it gets for each entry its source trail position ({"page", "line", "line_text", "lines"})."""
    lines, where = [], []
    for pn, t in enumerate(pages, 1):
        ls = [(i, x) for i, x in enumerate(t.splitlines(), 1) if x.strip()]
        if ls and re.fullmatch(r"\s*\d{1,2}\s*", ls[0][1]):          # page number
            ls = ls[1:]
        lines += [x for _, x in ls]
        where += [(pn, i) for i, _ in ls]
    out, head, cur, open_head = [], None, None, False
    at = []
    for li, line in enumerate(lines):
        s = line.strip()
        h = HEAD.match(s)
        m = NUM.match(s)
        if h and not m:
            head, cur = " ".join(h.group(1).split()), None
            tail = head.rsplit(",", 1)[-1].strip() if "," in head else ""
            open_head = not tail or bool(SUBONLY.match(tail))
            continue
        if open_head and head and not m:                     # the heading wraps: "Sub Div-I," + "(U), Vasco"
            head = f"{head} {s}"
            open_head = False
            continue
        open_head = False
        nxt = cur[1] + 1 if cur else 1
        if m and head and (int(m.group(1)) == nxt or (cur is None or nxt < int(m.group(1)) <= nxt + 2)
                           and re.match(r"[A-Z]", m.group(2))):
            # (a number may be missing: "2 Accounts Section" is followed by "4 Establishment Section"; a block may go on with
            # the numbers of the block before it: "Sub Div-II, Cuncolim" starts at 12)
            cur = [head, int(m.group(1)), [], [], []]
            out.append(cur)
            at.append([li])                              # the numbered line (its number may stand alone)
            s = m.group(2).strip()
            if not s:
                continue
        if cur is None:
            continue
        if at[-1][-1] != li:
            at[-1].append(li)
        rest, ext = [], False
        for tok in re.split(r"\s+", s):
            t = tok.strip(",;")
            if ext and re.fullmatch(r"\d{2,4}", t) and cur[3]:
                cur[3][-1] += f" ext. {t}"           # a PBX line: "(0832)2426022" + "ext. 115"
                ext = False
                continue
            ext = False
            if re.fullmatch(r"(?i)ext\.?", t):
                ext = True
            elif re.fullmatch(r"\(0\d{2,4}\)\s?\d{6,8}", t):
                cur[3].append(t)
            elif PHONE.match(t):
                cur[3].append(PHONE.match(t).group(1))
            elif "@" in t:
                cur[4].append(t)
            elif cur[4] and MAILPART.match(t):
                cur[4][-1] += t                   # the wrapped end of the last address
            elif t in ("--", "_", "-", "—", "/"):
                continue
            else:
                rest.append(tok)
        if rest:
            cur[2].append(" ".join(rest))
    if pos is not None:
        for lis in at:
            pg = where[lis[0]][0] if lis else None
            nos = [where[i][1] for i in lis if where[i][0] == pg]
            pos.append({"page": pg, "line": nos[0], "line_text": "\n".join(lines[i] for i in lis if where[i][0] == pg),
                        **({"lines": nos} if len(nos) > 1 else {}),
                        **({"to_page": where[lis[-1]][0]} if lis and where[lis[-1]][0] != pg else {})} if lis else {})
    return out


NOT_PLACE = re.compile(r"(?i)\b(Junior|Engi?n\w*|Engr|JE|AE|Jr|Asst\w*|Shri|Smt|Office|Technical|Complaint\w*|Centre|Center|HT|KV)\b|^[IVX]+$")


def place_ok(cand, name):
    cand = (cand or "").strip(" ,.()")
    if len(cand) < 3 or NOT_PLACE.search(cand) or re.match(r"(?i)S/?D\b|Sub\b", cand):
        return False
    return not (name and any(w in name.split() for w in cand.split()))


def split_name(txt):
    """(name, designation): the person is the text before the designation words."""
    m = DESIG.search(txt)
    if not m or m.start() == 0:
        return None, txt
    name = txt[:m.start()].strip(" ,")
    des = txt[m.start():].strip(" ,")
    if name.endswith("("):                     # "Shri. X (Jr. Engineer), Navelim Section Office": the post is in brackets
        name = name.rstrip(" ,(")
        des = unbracket(des)
    q = re.search(r"\s*\(([A-Za-z&. ]{2,8})\)$", name)
    if q and not re.match(r"(?i)(Shri|Smt|Kum|Mr|Ms|Dr)\.?$", q.group(1)):
        name = name[:q.start()].strip(" ,")    # "Bhanudas Kerkar (COM)" + "Asst. Engineer": the bracket belongs to the post
        des = f"{des} ({q.group(1)})"
    if (re.search(r"Section|Station|Office|Complaint", name, re.I) or len(name) < 3
            or re.match(r"(?i)(Section|Secton|Sub\s*-?\s*Station|Sub\s*-?\s*Store|Office|Technical)", txt[m.start():])
            and not re.match(r"(?i)(Shri|Smt|Kum|Mr|Ms|Dr)\b", name)):
        return None, txt
    return name, des


def unbracket(des):
    """Drop the first ")" that has no "(" before it: "Jr. Engineer), Navelim Section Office" -> "Jr. Engineer, Navelim ..."."""
    depth = 0
    for i, c in enumerate(des):
        depth += {"(": 1, ")": -1}.get(c, 0)
        if depth < 0:
            des = des[:i] + des[i + 1:]
            break
    des = re.sub(r"(\w)\(", r"\1 (", re.sub(r"\)\(", ") (", des))
    return " ".join(des.split()).strip(" ,")


def parse_pages(pages, source=URL):
    out = Out("power_goa", "GA", source, discom="Electricity Department, Goa")
    circle = division = None
    keys, last, key = set(), None, None
    pos = []
    for (head, n, lines, phones, mails), sp in zip(entries(pages, pos), pos):
        lvl, area = block_of(head)
        if head != last:                         # a new block; two blocks may have one heading ("Sub Div-I," with no place,
            last, key = head, slug(head)         # in Div-XIII and in Div-XV): the second one's key names its division
            if key in keys:
                key = slug(f"{division or circle or ''} {head}")
            keys.add(key)
        if lvl == "other":
            continue
        if lvl == "circle":
            circle = area
        elif lvl == "division":
            division = area
        txt = " ".join(" ".join(lines).split())
        if not txt and not phones:
            continue
        name, des = split_name(txt)
        elvl, earea = lvl, area
        sm = SECTION.search(txt)
        pm = next((x for x in PLACE_FIRST.finditer(txt) if place_ok(x.group(1), name)), None)
        if lvl == "subdivision" and (sm or pm or JE.search(txt)):
            elvl = "section"
            if pm:
                earea = clean(pm.group(1).strip(" ,.()")) or area
            elif sm and place_ok(sm.group(2).split(",")[0].split("(")[0].strip(), name):
                earea = clean(re.sub(r"\(.*$|,.*$", "", sm.group(2)).strip(" ,.()")) or area
        par = {"circle": circle if elvl in ("division", "subdivision", "section") else None,
               "division": division if elvl in ("subdivision", "section") else None,
               "subdivision": area if elvl == "section" else None}
        mail = email(" ".join(mails).replace("/", " ")) if mails else None
        rid = f"{key}-{n}"
        if len(rid) > 80:                         # Out.add cuts a key at 80 characters: keep the entry number on the end
            rid = f"{key[:79 - len(str(n))].rstrip('-')}-{n}"
        out.add(rid, elvl, earea, post=des, name=name, phone_=", ".join(dict.fromkeys(phones)) or None,
                email_=mail, parents=par, office=head, entry=n, src_pos=sp)
    return out.recs


def fetch(p, get):
    url = p.get("url", URL)
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [raw("power_goa", "telephone-directory-2026-27", r.content, "pdf")]
    if r.content[:5] != b"%PDF-":
        return [], files, "not a pdf"
    from pypdf import PdfReader
    import io
    try:
        pages = [(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(r.content)).pages]
    except Exception as e:
        return [], files, f"pdf: {type(e).__name__}"
    recs = parse_pages(pages, url)
    return recs, files, "" if recs else "no entries"
