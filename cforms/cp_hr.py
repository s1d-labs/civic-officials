"""Haryana councillor contacts from the bodies' own sites (records "councillor_contact", see cforms/cp_common.py).
One queue item = one body. Payload: "layout", "body" (as the SEC record cforms/cn_hr.py gives it), "lgd_code", "sec_slug"
(the body part of the SEC record id), "ward_pad" (2 when the SEC ids write ward 1 as "01", Panipat). Layouts:
- "table": one member per row, header row in English: ward no., name of councilor / candidate / elected representative,
  designation, address, mobile no., e-mail (Panchkula, Sirsa: Elected_Representative.aspx; Yamunanagar:
  mcynr.com/elected-members-0). The Mayor / President row has no ward number (or "President" in the ward cell, or ", Mayor"
  after the name): it gets record_for <sec id>:chair. E-mail addresses that Cloudflare hides on the page (data-cfemail, a
  plain XOR of the bytes) are written back as text. A table with ID numbers in it (Yamunanagar's second table: "family id",
  "aadhaar") is not read: it holds nominated members, not the elected council, and these readers take contact fields only.
- "blocks": Panipat (nagarnigampanipat.in/municipal-councillors/, WordPress): one small table per member, "Name <name>",
  "Ward <n>", "Mobile <98123-20895>".
Names lose the title (Sh., Smt.) and the relation part (W/o, S/o, D/o ...), which goes to "relation".
Record id cp:HR:<sec slug>:<ward> (chair for the Mayor / President)."""
import gzip
import re

from bs4 import BeautifulSoup

from cforms.cp_common import clean, column, emails, keyed, phones, record, table_rows, useful, ward_no

METHOD = "html table (else page text blocks)"     # source trail (provenance.py): how this reader reads its sources

TITLE = re.compile(r"^(sh|shri|sri|smt|mr|mrs|ms|dr|km|kumari)\.?\s+", re.I)
RELATION = re.compile(r"\s+([wsd]\s*/\s*[ok]|[wsd]o\s*/|wife of|son of|daughter of)\.?\s*(.*)$", re.I)
CHAIR = re.compile(r"\b(mayor|president|chair\s*(person|man)?)\b", re.I)
SKIP_TABLE = re.compile(r"aadhaa?r|family id", re.I)
NAME = (r"name of (the )?(councill?or|candidate|elected representative|member)", r"^name\b")
WARD = (r"^ward",)
PHONE = (r"mobile|contact|phone",)
ADDR = (r"address",)
EMAIL = (r"e-?\s*mail",)
POST = (r"designation|post\b",)


def cf_emails(html):
    """Cloudflare's hidden e-mail links -> the address as text (key = first byte, each next byte XOR key)."""
    def dec(m):
        b = bytes.fromhex(m.group(2))
        return m.group(1) + "".join(chr(c ^ b[0]) for c in b[1:]) + "</a>"
    return re.sub(r'(<a[^>]*data-cfemail="([0-9a-fA-F]+)"[^>]*>).*?</a>', dec, html, flags=re.S)


def phones10(s):
    """cp_common.phones() with a comma put between two 10-digit numbers that only a space (a <br> on the page) separates."""
    return phones(re.sub(r"(\d{10})\s+(?=\d)", r"\1, ", s or ""))


def split_name(s):
    s = clean(s) or ""
    for _ in range(2):
        s = TITLE.sub("", s).strip()
    post = None
    m = re.search(r",\s*(mayor|president|chair\w*)\s*$", s, re.I)
    if m:
        post, s = m.group(1).title(), s[:m.start()].strip()
    rel = None
    m = RELATION.search(s)
    if m:
        rel, s = clean(m.group(0)), s[:m.start()].strip()
    return s or None, post, rel


def rid_for(p, ward, chair):
    if not p.get("sec_slug"):
        return None
    if chair:
        return f"councillor:HR:{p['sec_slug']}:chair"
    return f"councillor:HR:{p['sec_slug']}:{ward.zfill(p.get('ward_pad', 1))}" if ward else None


def table_layout(html, p):
    recs, skip = [], set()
    for head, cells in table_rows(cf_emails(html)):
        if not head or SKIP_TABLE.search(" ".join(head)):
            continue
        ni, wi = column(head, *NAME), column(head, *WARD)
        pi, ai, ei, di = column(head, *PHONE), column(head, *ADDR), column(head, *EMAIL), column(head, *POST)
        if ni is None or pi is None or ni >= len(cells):
            continue
        cell = lambda i: cells[i] if i is not None and i < len(cells) else None
        name, post, rel = split_name(cell(ni))
        if not name:
            continue
        post = post or cell(di)
        label = cell(wi)
        chair = bool(CHAIR.search(post or "") or CHAIR.search(label or ""))
        ward = None if chair else ward_no(label)
        recs.append(record("HR", p["body"], ward, name, p["url"], phone=phones10(cell(pi)), email=emails(cell(ei)) if ei is not None else None,
                           address=cell(ai), position=post if post and post.lower() != "member" else ("Mayor/President" if chair else None),
                           ward_label=label, lgd_code=p.get("lgd_code"), record_for=rid_for(p, ward, chair),
                           extra={"relation": rel} if rel else None, pos=cells.pos))
    return recs


def blocks_layout(html, p):
    t = " ".join(BeautifulSoup(html, "lxml").get_text(" ").split())
    recs = []
    for k, m in enumerate(re.finditer(r"\bName\s+(.+?)\s+Ward\s+(\d+)\s+Mobile\s+([\d\s,/-]+?)(?=\s+Name\b|\s+[A-Za-z]|$)", t), 1):
        name, _, rel = split_name(m.group(1))
        ward = ward_no(m.group(2))
        recs.append(record("HR", p["body"], ward, name, p["url"], phone=phones10(m.group(3)), ward_label=m.group(2),
                           lgd_code=p.get("lgd_code"), record_for=rid_for(p, ward, False), extra={"relation": rel} if rel else None,
                           # source trail: the k-th "Name ... Ward ... Mobile ..." block of the page text, its text as matched
                           pos={"selector": "page text", "block": k, "text": m.group(0)}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/HR/cp-{p['sec_slug']}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = useful((blocks_layout if p["layout"] == "blocks" else table_layout)(r.text, p))
    chair = [d for d in recs if d.get("record_for", "").endswith(":chair")]
    out = [(f"cp:HR:{p['sec_slug']}:chair" + (f"-{i}" if i > 1 else ""), d) for i, d in enumerate(chair, 1)]
    out += keyed("HR", p["sec_slug"], [d for d in recs if d not in chair])
    return out, files, "" if recs else "no members with contacts"
