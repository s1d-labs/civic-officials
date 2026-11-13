"""Shared parsing for the north-east state-level readers (dforms/st_<as|ar|mn|ml|mz|nl|sk|tr>_*.py, 2026-11-13).

table_rows(html): every HTML table with a header row that names a person column, as dicts of the cells the header names
  (name, post, department, contact, phone, email, district, place, remarks, address) + the raw cells + src_pos {table,row},
  and the heading text above the table ("section"). Tables without such a header are left out.
label_lists(html): "Name: X / Official Contact No.: Y / Departments: Z" lists (Sikkim portal), one dict per <tr> or card.
pdf_blocks(text): rows of a Word-made telephone list PDF (Tripura department lists), from layout text: a row starts at a line
  with a serial number or a titled name ("Shri", "Smt", "Dr" ...) in the name column; the following lines up to the next row
  start are joined column by column (text cells by their start offset), so a wrapped designation or phone stays whole.
contact(text): (phones, emails, address) of a "Contact Details" cell ("Phone : 0364-2226043 Email ID : a[at]b[dot]in").
"""
import re

from dforms import _esw
import provenance

HEAD = [
    ("name", r"^(name|name of the officer|officer'?s? name|name of officer|name\s*(?:&|and)\s*designation|officer)\b"),
    ("post", r"designation|^post\b|position|present post|current posting|post\s*(?:&|and)\s*dep"),
    ("department", r"department|deptt|organi[sz]ation|office\b"),
    ("email", r"e-?\s?mail"),
    ("phone", r"phone|mobile|tel\b|telephone|contact no|fax"),
    ("contact", r"contact"),
    ("district", r"^district"),
    ("place", r"place of posting|location|station"),
    ("remarks", r"remark|service|cadre|batch|recruitment"),
    ("address", r"address|room|block"),
]
TITLE = re.compile(r"(?i)^(shri|smt|smti|sri|dr|mr|mrs|ms|miss|prof|kumari|km|er|lt|col|capt|md\.?)\b\.?\s")


def head_keys(cells):
    out, used = [], set()
    for c in cells:
        t = _esw.clean(c).lower()
        k = next((k for k, rx in HEAD if re.search(rx, t) and (k not in used or k == "phone")), "")
        if k:
            used.add(k)
        out.append(k)
    return out


def heading(table):
    h = table.find_previous(["h1", "h2", "h3", "h4", "h5", "h6", "caption", "strong", "b", "button"])
    return _esw.clean(h.get_text(" ")) if h else ""


def table_rows(html):
    s = _esw.soup(html)
    out = []
    for t in s.find_all("table"):
        pos = []
        g = _esw.grid(t, pos=pos)
        if len(g) < 2:
            continue
        hi = next((i for i, r in enumerate(g[:3]) if "name" in head_keys(r)), None)
        if hi is None:
            continue
        keys = head_keys(g[hi])
        sec = heading(t)
        cap = t.find("caption")
        if cap:
            sec = _esw.clean(cap.get_text(" "))
        for r, p in zip(g[hi + 1:], pos[hi + 1:]):
            if len(set(r)) == 1 and len(r) > 1:       # a full-width section row
                sec = r[0]
                continue
            d = {"cells": r, "section": sec, "src_pos": p}
            for k, v in zip(keys, r):
                if k and v:
                    d[k] = (d[k] + " | " + v) if k in d and d[k] != v else v
            if d.get("name") or d.get("post"):
                out.append(d)
    return out


def label_lists(html):
    """Lists of "<strong>Label:</strong> value" items (one person per <tr>, or per <ul> when no table), with the heading
    above the table (the tab's link text on the Sikkim portal) and src_pos {table,row} / {list}."""
    from dforms import _trail
    s = _esw.soup(html)
    out = []
    for n, ul in enumerate(s.find_all("ul"), 1):
        items = {}
        for li in ul.find_all("li", recursive=False):
            st = li.find("strong")
            if not st:
                continue
            lab = _esw.clean(st.get_text(" ")).rstrip(":").strip().lower()
            st.extract()
            items[lab] = _esw.clean(li.get_text(" "))
        if "name" not in items:
            continue
        tr = ul.find_parent("tr")
        pos = _trail.tr_pos(tr) if tr is not None else {"list": n}
        t = ul.find_parent("table")
        sec = ""
        if t is not None:
            pane = t.find_parent(id=True, class_=re.compile("tab-pane|collapse"))
            h = None
            if pane is not None:
                h = s.find(attrs={"href": "#" + pane["id"]}) or s.find(attrs={"data-bs-target": "#" + pane["id"]}) or \
                    s.find(attrs={"data-target": "#" + pane["id"]}) or s.find(attrs={"aria-controls": pane["id"]})
            if h is None:
                h = t.find_previous("a", href=re.compile("^#"))
            sec = _esw.clean(h.get_text(" ")) if h else heading(t)
        out.append({"labels": items, "section": sec, "src_pos": pos})
    return out


def contact(text):
    t = _esw.clean(text)
    addr = ""
    m = re.search(r"(?i)address\s*:\s*(.*?)(?=\b(phone|mobile|fax|e-?mail(?: id)?)\s*:|$)", t)
    if m:
        addr = m.group(1).strip(" ,")
    rest = t.replace(m.group(0), " ") if m else t
    em = _esw.emails(rest)
    ph = _esw.phones(re.sub(r"\S+@\S+|\S+\[at\]\S+", " ", _esw.deob(rest)))
    return ph, em, addr


SNO = re.compile(r"^\s{0,12}(\d{1,3})[.)]?(\s{2,}|\s*$)")
CHUNK = re.compile(r"\S+(?: \S+)*")
HEADER = re.compile(r"(?i)\b(sl\.?\s*no|s\.?\s*no|name\s*(?:&|and)\s*designation|designation)\b.*\b(contact|phone|e-?mail|designation)\b")


def chunks(line):
    return [(m.start(), m.group(0)) for m in CHUNK.finditer(line)]


def _kind(c):
    t = re.sub(r"(?i)e-?mail\s*(id)?\s*:?", " ", c)
    if re.search(r"@|\[at\]", t):
        return "email"
    if re.fullmatch(r"\s*\(?\d{3,5}\)?\s*", t):
        return "phone"
    if len(re.sub(r"\D", "", t)) >= 5 and len(re.sub(r"[\d\s()+/,.:-]|(?i:office|fax|mobile|res|tel|ph|o|r|m|cug|pbx|ext|epabx)", "", t)) <= 3:
        return "phone"
    if re.fullmatch(r"\d{1,3}[.)]?", t.strip()):
        return "sno"
    return "text"


def pdf_blocks(text):
    """People of a telephone-list PDF from its layout text (Word tables, rows often centred vertically: the serial number
    and the phones can stand above or below the name line). Each titled name ("Shri", "Smt", "Dr" ...) is one person; a line
    with a post and a phone but no name, after a person who already has a phone, is a post of its own. Every other text cell
    goes to the nearest person on the page (text in the name column only to the person above it: the designation under the
    name). Returns dicts {"name_cell", "post_cells", "phones", "emails", "page", "line", "line_text", "section"}."""
    out = []
    for pg, ptext in enumerate(text.split("\f"), 1):
        lines = [(ln, raw, chunks(raw)) for ln, raw in enumerate(ptext.split("\n"), 1) if raw.strip()]
        people, pend, sec = [], [], ""
        # a name without a title opens a person too when its line starts with a serial number and the name stands in the
        # column of the titled names ("3   Kabita Debbarma, TCS, Gr-II   Deputy Director ...": Tripura, 2026-11-13 audit)
        name_cols = [s0 for _, _, cs in lines for s0, c in cs if TITLE.match(c)]
        untitled = set()
        for ln, raw, cs in lines:
            if len(cs) >= 2 and _kind(cs[0][1]) == "sno" and _kind(cs[1][1]) == "text" and not TITLE.match(cs[1][1]) and \
                    any(abs(cs[1][0] - x) <= 2 for x in name_cols) and not _field_post(cs[1][1]) and \
                    not re.search(r"(?i)\b(division|district|office|sub|block|circle|department|section|branch|unit|cell|"
                                  r"cent(re|er)|icat|tehsil|zone|tripura|police|station|hospital|school|college)\b", cs[1][1]) and \
                    re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,40}(,\s*[A-Za-z][\w .()-]{1,25}){0,3}", cs[1][1]):
                untitled.add((ln, cs[1][0]))
        TITLED = lambda ln, s0, c: TITLE.match(c) or (ln, s0) in untitled
        for ln, raw, cs in lines:
            if HEADER.search(raw) and not any(TITLED(ln, s0, c) for s0, c in cs):
                provenance.skip_line(ln, 'skip: HEADER.search(raw) and not any(TITLE.match(c) for _, c in cs)')
                continue
            for s0, c in cs:
                if TITLED(ln, s0, c):
                    if pend:
                        sec, pend = _esw.clean(" ".join(pend)), []
                    people.append({"name_cell": c, "col": s0, "post_cells": [], "phones": [], "emails": [], "page": pg,
                                   "line": ln, "line_text": raw, "section": sec, "other": []})
            kinds = [_kind(c) for _, c in cs]
            if people and "phone" in kinds and not any(TITLED(ln, s0, c) for s0, c in cs) and people[-1]["line"] < ln:
                people[-1]["seen_phone"] = True
            elif people and "phone" in kinds and people[-1]["line"] == ln:
                people[-1]["seen_phone"] = True
            texts = [(s0, c) for (s0, c), k in zip(cs, kinds) if k == "text" and not TITLED(ln, s0, c)]
            if (not any(TITLED(ln, s0, c) for s0, c in cs) and people and "phone" in kinds and texts
                    and people[-1].get("seen_phone") and _field_post(texts[0][1]) and abs(texts[0][0] - people[-1]["col"]) <= 4):
                people.append({"name_cell": "", "col": texts[0][0], "post_cells": [], "phones": [], "emails": [], "page": pg,
                               "line": ln, "line_text": raw, "section": sec, "other": []})
            if not people and not any(k in ("phone", "email") for k in kinds):
                pend.append(raw.strip())
        if not people:
            provenance.skipped('skip: not people')
            continue
        pend_cells = []
        for ln, raw, cs in lines:
            if HEADER.search(raw) and not any(TITLED(ln, s0, c) for s0, c in cs):
                provenance.skip_line(ln, 'skip: HEADER.search(raw) and not any(TITLE.match(c) for _, c in cs)')
                continue
            for s0, c in cs:
                if TITLED(ln, s0, c):
                    continue
                k = _kind(c)
                if k == "sno":
                    continue
                if k == "text":
                    above = [p for p in people if p["line"] <= ln]
                    p = above[-1] if above else None
                    if p is None:
                        continue
                    if abs(s0 - p["col"]) <= 4 or s0 > p["col"]:
                        if ln - p["line"] <= 6:
                            p["post_cells"].append(c)
                            p["end"] = max(p.get("end", p["line"]), ln)
                        else:
                            p["other"].append(c)
                    continue
                pend_cells.append((ln, k, c))
        for ln, k, c in pend_cells:
            def dist(q):
                a, b = q["line"], q.get("end", q["line"])
                return (0 if a <= ln <= b else min(abs(ln - a), abs(ln - b)), a > ln)
            p = min(people, key=dist)
            p["phones" if k == "phone" else "emails"].append((ln, c))
        out.extend(people)
    return out


def _field_post(t):
    return bool(re.search(r"(?i)secretary|officer|director|commissioner|minister|police|p\.?p\.?s|p\.?s\.?|p\.?a\.?|o\.?s\.?d|"
                          r"superintendent|engineer|controller|registrar|chairman|member|inspector|deputy|assistant|joint|"
                          r"addl|additional|section|head|in-?charge|chief", t))


PHONE_ONLY = re.compile(r"^[\d\s()+/,.-]*(\((o|r|off|res|fax|m)\)|office|fax|mobile|res)?[\d\s()+/,.:-]*$", re.I)


def block_fields(b):
    """(name, post, phones, emails, rest) of a pdf_blocks person: the name up to its service tag ("Shri X, IAS"), the post from
    the text after it and the cells under it."""
    t = _esw.clean(b["name_cell"])
    name, post = t, ""
    m = re.match(r"(.+?(?:,?\s*\(?\b(?:IAS|IPS|IFS|IRS|TCS|TPS|TFS|MCS|MPS|APCS|NCS|SCS|ACS)\b(?:\s*Gr\.?-?\s*I+)?\)?))[\s,]*(.*)$", t)
    if m:
        name, post = m.group(1), m.group(2)
    post = _esw.clean(" ".join([post] + b["post_cells"]))
    post = re.sub(r"(?i)\s*\bname\s*(?:&|and)\s*designation\b.*$", "", post).strip(" ,")
    frags = []
    for _, c in sorted(b["phones"], key=lambda x: x[0]):
        d = len(re.sub(r"\D", "", c))
        if frags and (d < 6 or frags[-1][1] < 6) and frags[-1][1] + d <= 12:
            frags[-1] = (frags[-1][0] + " " + c, frags[-1][1] + d)
        else:
            frags.append((c, d))
    ph = _esw.phones(" , ".join(f for f, _ in frags))
    em = _esw.emails(" ".join(c for _, c in b["emails"]))
    return name.strip(" ,"), post, ph, em, b.get("other", [])


# keys that _state.DEPTS tries too late for these names ("Agriculture and Farmers' Welfare" hit social_welfare by "welfare",
# "Women & Child Welfare" the same); tried first here (reported to the parent for _state.py)
FIRST = [("agriculture", r"\b(agricultur|horticultur|farmer|animal husbandry|veterinar|fisher|sericultur|dairy)"),
         ("women_child", r"\b(women|child)"), ("police", r"\b(police|home \(police|prisons?)\b"),
         ("health", r"\b(health|medical)"), ("education", r"\beducation")]


def dept(*texts):
    from dforms import _state
    t = " ".join(_esw.clean(x) for x in texts if x)
    for k, rx in FIRST:
        if re.search(rx, t, re.I):
            return k
    return _state.dept_key(*texts)


def post_kind(post):
    """_state.post_kind with the north-east abbreviations ("DS(Budget)", "US (Home)", "PPS to HCM") and with "Secretary to
    Hon'ble Chief Minister" read as a secretary (the _state pattern for "minister" runs first; reported to the parent)."""
    from dforms import _state
    t = _esw.clean(post)
    if re.match(r"(?i)^(DS|Dy\.?\s*Secy)\b", t):
        return "deputy_secretary"
    if re.search(r"(?i)\b(addl\.?|additional|spl\.?|special)\s+director general\b", t):
        return "adgp" if re.search(r"(?i)police|\bIPS\b", t) else "head_of_department"
    if re.search(r"(?i)\bvice[- ]?chair", t):
        return "vice_chairperson"
    if re.match(r"(?i)^(i/c\s+)?DIGP?\b", t):
        return "dig"
    if re.match(r"(?i)^US\b", t):
        return "under_secretary"
    if re.match(r"(?i)^(P\.?P\.?S|Sr\.?\s*P\.?S|P\.?S|P\.?A|O\.?S\.?D)\b\.?\s*(to|-|$)", t):
        return "personal_staff"
    if re.search(r"(?i)secretary\b.{0,40}\bminister", t):
        return _state.post_kind(re.sub(r"(?i)\bto\b.{0,40}\bminister.*", "", t)) or "secretary"
    return _state.post_kind(t)
