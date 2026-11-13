"""Tripura: the telephone lists of every department, linked on tripura.gov.in/contact-directory (checked 2026-11-13 from
dev-vps-3, Mumbai: HTTP 200, no captcha). The index has three tables: "Secretariats" (Governor, Chief Minister, Chief
Secretary), "District administration" (District Magistrates, SDMs, BDOs) and departments / organisations (about 50: GA
branches, Home (Police), Home (Prisons), Finance, Health, Education ...). Each list is one Word-made PDF (1-10 pages, text
layer, 80-400 KB, the date in the file name). Layouts differ (Sl No | Name and Designation | Contact | Email; Name |
Designation | Contact No | Email; rows centred vertically): dforms/st_ne.pdf_blocks reads every titled name as one person
and gives each phone / e-mail cell to the nearest person (source trail: page + line of the name line).
Seed: items(get) reads the index (one item per PDF; payload "org" = the index row, "group"). The heavy part is small (a
few pages of pdftotext per item): it runs in the depts task.
Levels: the Secretariats and departments lists -> level state; District Magistrates / SDMs / BDOs lists -> level district
(their area is in the post: "District Magistrate & Collector, West Tripura"; the reader keeps it in the post).
Record ids: dept:st_tr_dirs:<file slug>:<n>.
"""
import re
from urllib.parse import urljoin

from dforms import _esw, _field, _state, st_ne

METHOD = "pdf text (pdftotext -layout) + person blocks (st_ne.pdf_blocks)"
MODULE = "st_tr_dirs"
INDEX = "https://tripura.gov.in/contact-directory"
GROUPS = ["secretariat", "district", "department"]


def index_items(html, url=INDEX):
    s = _esw.soup(html)
    out = []
    for gi, t in enumerate(s.find_all("table")):
        for tr in t.find_all("tr")[1:]:
            a = tr.find("a", href=True)
            tds = [_esw.clean(td.get_text(" ")) for td in tr.find_all("td")]
            if not a or len(tds) < 2:
                continue
            u = urljoin(url, a["href"])
            f = re.sub(r"\.pdf$", "", u.rsplit("/", 1)[-1], flags=re.I)
            out.append({"key": f"{MODULE}:{_esw.slug(f)[:120]}",
                        "payload": {"reader": MODULE, "url": u, "org": tds[1], "group": GROUPS[min(gi, 2)], "state": "TR",
                                    "india_only": False, "route": "direct", "index": url}})
    return out


def parse(text, p):
    org, group = p.get("org", ""), p.get("group", "department")
    level = "district" if group == "district" else "state"
    bk = "secretariat" if group == "secretariat" else "police" if re.search(r"(?i)police", org) else \
        "commission" if re.search(r"(?i)commission", org) else "department"
    slug = _esw.slug(re.sub(r"\.pdf$", "", p["url"].rsplit("/", 1)[-1], flags=re.I))[:80]
    out = []
    for n, b in enumerate(st_ne.pdf_blocks(text), 1):
        name, post, ph, em, rest = st_ne.block_fields(b)
        if not (name or post):
            continue
        dist = ""
        if level == "district":
            m = re.search(r"(?i)\b(west|south|north|dhalai|gomati|khowai|sepahijala|unakoti)\b(\s+tripura)?", post)
            dist = {"west": "West Tripura", "south": "South Tripura", "north": "North Tripura"}.get(m.group(1).lower(), m.group(1).title()) \
                if m else ""
        out.append(_state.rec(MODULE, f"{slug}:{n}", state="TR", level=level if (level == "state" or dist) else "state",
                              district=dist, post=post, post_kind=st_ne.post_kind(post), name=name, body=org, body_kind=bk, department=org,
                              dept=st_ne.dept(org, post), phone=ph, email=em, section=b.get("section") or None,
                              notes=" | ".join(rest) or None, list_group=group,
                              src_url=p["url"], src_pos={"page": b["page"], "line": b["line"], "line_text": b["line_text"]}))
    return out


def items(get):
    r = get(INDEX)
    if r is None or r.status_code != 200:
        return []
    return index_items(r.text, INDEX)


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if r.content[:5] != b"%PDF-":
        return [], [], "not a pdf"
    text, engine = _field.pdf_text_engine(r.content)
    recs = parse(text, p)
    for _, d in recs:
        d["method"] = f"pdf text ({engine}) + person blocks (st_ne.pdf_blocks)"
    return recs, [(f"depts/{MODULE}/{p['url'].rsplit('/', 1)[-1]}", r.content, "application/pdf")], "" if recs else "no rows"
