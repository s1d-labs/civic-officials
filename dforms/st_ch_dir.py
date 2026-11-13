"""Chandigarh: the Chandigarh Administration Telephone Directory 2026 (Department of Public Relations, chdpr.gov.in).

Source: https://chdpr.gov.in/cadmin/uploads/filemanagers/Main_Directory_2026_-_Print_Ready_file_(1).pdf (129 pages A4
landscape, Google Sheets export with a text layer, 676 KB; archive copy of 2026-11-06, sha256 68b8e311...). Linked from
chandigarh.gov.in/telephone-directory. Sections (a centred heading in capitals per office: "CHIEF SECRETARY'S OFFICE",
"HOME SECRETARY'S OFFICE", "OFFICERS OF CHANDIGARH ADMINISTRATION", each department, board, corporation, the Municipal
Corporation, Police ...). Under a heading, one block per person: the first line holds the name (with service: "H. Rajesh
Prasad, IAS"), office phone, residence / mobile, centrex and the residence address in columns; the lines below hold the posts
(one per line; an officer with several charges has several lines) and e-mail addresses. A block may start with a post and no
name ("Secretary Health   2740008"): then the record has no name.
Records: level state (the UT is one district: district "Chandigarh", district_code 4... LGD district code of Chandigarh is
given by the loader, not here), body = the section heading, post = the first post line, posts = every post line,
phone = the numbers of the block outside the address column, email, address (residence address as printed).
Text: pdftotext -layout (the runner has poppler; else pypdf layout). Heuristic block reader: check with the fixture pages.
Route: chdpr.gov.in answered from India in the archive; abroad unchecked -> proxy.
Ids: dept:st_ch_dir:<page>:<line of the block's first line>.
"""
import re

import provenance
from dforms import _esw, _field, _state

METHOD = "pdf text (pdftotext -layout, else pypdf layout), blocks per person under centred headings"
MODULE = "st_ch_dir"
URL = "https://chdpr.gov.in/cadmin/uploads/filemanagers/Main_Directory_2026_-_Print_Ready_file_(1).pdf"

HONOR = re.compile(r"(?i)^(dr|sh|shri|smt|sri|mr|mrs|ms|miss|kumari|km|er|prof|professor|col|capt|maj|lt|brig|gen|justice|"
                   r"hon'?ble|s\.)\b\.?")
SERVICE = re.compile(r",\s*(IAS|IPS|IFS|PCS|HCS|DANICS|DANIPS|IRS|ITS|IRTS|IDAS|IAAS|IES|HPS|PPS|CSS)\b")
POSTW = re.compile(r"(?i)\b(officer|commissioner|collector|magistrate|superintendent|supdt|director|dir\.|secretary|secy|"
                   r"inspector|supervisor|in-?charge|registrar|dean|adviser|advisor|engineer|manager|chairman|chairperson|"
                   r"chairman|member|president|clerk|assistant|asstt|osd|adc|ps to|pa to|p\.a\.|p\.s\.|librarian|accountant|"
                   r"controller|head|principal|professor|lecturer|counsellor|warden|curator|executive|administrator|governor|"
                   r"mayor|councillor|deputy|addl|additional|joint|chief|senior|junior|section|nodal|cpio|sdm|sp\b|dsp|"
                   r"estate|treasury|architect|planner|draftsman|steno|stenographer|operator|reader|attendant|medical|doctor|"
                   r"surgeon|technician|pharmacist|editor|tehsildar|kanungo|patwari|naib|consultant|coordinator|incharge|"
                   r"cell|wing|branch|office|division|circle|unit|board|centre|center|department|dept|control room|"
                   r"enquiry|reception|exchange|helpline|fax|administration|society|corporation|authority|council|"
                   r"committee|limited|ltd|institute|hospital|college|university|commission|government|govt)\b")
HEADER = re.compile(r"(?i)^\s*name\s*&\s*designation|^\s*(off\.|telephone|centrex|residence)\b")
NUM = re.compile(r"(?<![\w/#-])(?:\+?91[\s-]?)?(?:0\d{2,4}[\s-]?)?\d{5,10}(?![\w/])")


def chunks(line):
    """[(start column, text)] of a layout line, cells two or more spaces apart."""
    return [(m.start(), m.group()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def is_heading(line):
    t = line.strip()
    if not t or len(line) - len(line.lstrip()) < 8 or re.search(r"\d|@", t):
        return False
    letters = re.sub(r"[^A-Za-z]", "", t)
    return len(letters) >= 4 and letters.upper() == letters and len(chunks(line)) <= 2


def is_name(text):
    t = text.strip()
    if SERVICE.search(t) or HONOR.match(t):
        return True
    if POSTW.search(t) or re.search(r"\d|@|#", t):
        return False
    words = t.replace(".", ". ").split()
    return 1 <= len(words) <= 6 and all(w[:1].isupper() for w in words if w[:1].isalpha())


def address_col(lines):
    """Start column of the address cells of a page: the left edge of cells that begin with "#" or "House" (or None)."""
    cols = [c for ln in lines for c, t in chunks(ln) if c > 30 and re.match(r"(?i)#|house|h\.?\s*no|flat|tower|kothi", t)]
    return min(cols) - 2 if cols else None


def parse_text(text, url=URL):
    """Records of the layout text (pages split by form feeds)."""
    out, section, block = [], "", None

    def close():
        if block and (block["posts"] or block["name"]):
            out.append(build(block, section, url))

    for pg, ptext in enumerate(text.split("\f"), 1):
        lines = ptext.split("\n")
        acol = address_col(lines)
        for n, raw in enumerate(lines, 1):
            if not raw.strip() or HEADER.match(raw) or re.match(r"(?i)\s*(epabx|email i\.?d|fax)", raw.strip()):
                provenance.skip_line(raw, 'skip: not raw.strip() or HEADER.match(raw) or re.match(r"(?i)\\s*(epabx|em...')
                continue
            if is_heading(raw):
                close()
                block, section = None, _esw.clean(raw)
                continue
            cs = chunks(raw)
            left = [t for c, t in cs if c < 25]
            right = [(c, t) for c, t in cs if c >= 25]
            addr = [t for c, t in right if acol is not None and c >= acol and not re.fullmatch(r"[-\d\s,/]+", t)]
            nums = [t for c, t in right if not (acol is not None and c >= acol and not re.fullmatch(r"[-\d\s,/]+", t))]
            lead = left[0] if left else ""
            cont = block is not None and block["posts"] and re.search(r"[,&(/-]$|\b(of|and|for|to|the)$", block["posts"][-1])
            if lead and "@" not in lead and cont:
                block["posts"][-1] = block["posts"][-1] + " " + lead
            elif lead and "@" not in lead and is_name(lead):
                close()
                block = {"name": lead, "posts": [], "nums": [], "emails": [], "addr": [],
                         "pos": provenance.line_pos(pg, n, raw), "key": f"{pg}:{n}"}
            elif lead and "@" not in lead and block is None:
                block = {"name": "", "posts": [lead], "nums": [], "emails": [], "addr": [],
                         "pos": provenance.line_pos(pg, n, raw), "key": f"{pg}:{n}"}
            elif lead and "@" not in lead and block is not None:
                block["posts"].append(lead)
            if block is None:
                provenance.skip_line(raw, 'skip: block is None')
                continue
            for t in [x for x in left if "@" in x] + [t for _, t in right if "@" in t]:
                block["emails"].append(t)
            block["nums"] += [t for t in nums if "@" not in t]
            block["addr"] += addr
    close()
    seen = set()
    res = []
    for rid, d in out:
        if rid in seen:
            continue
        seen.add(rid)
        res.append((rid, d))
    return res


def build(b, section, url):
    posts = [_esw.clean(p) for p in b["posts"] if not re.fullmatch(r"[-\s]+", p)]
    phones = _esw.phones(" , ".join(x for x in b["nums"] if not re.fullmatch(r"[-\s]+", x)))
    return _state.rec(
        MODULE, b["key"], state="CH", level="state", district="Chandigarh", post=posts[0] if posts else "",
        posts=posts or None, name=b["name"], body=section, body_kind="department", department=section or None,
        phone=phones, email=_esw.emails(" ".join(b["emails"])), address=_esw.clean(" ".join(b["addr"])),
        section=section, src_url=url, src_pos=b["pos"])


def items(get=None):
    return [{"key": f"{MODULE}:main-directory-2026", "payload": {"reader": MODULE, "url": URL, "state": "CH",
                                                                 "india_only": True, "route": "proxy"}}]


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    text, engine = _field.pdf_text_engine(r.content)
    recs = parse_text(text, p["url"])
    for _, d in recs:
        d["method"] = f"pdf text ({engine}), blocks per person under centred headings"
    return recs, [(f"depts/{MODULE}/main-directory-2026.pdf", r.content, "application/pdf")], "" if recs else "no rows"
