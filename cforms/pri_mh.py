"""Maharashtra Panchayati Raj elected representatives from the 34 Zilla Parishad websites (NIC template, Marathi pages):
ZP office bearers (अध्यक्ष President, उपाध्यक्ष Vice President, सभापती chairs of subject committees), ZP members (one per
electoral division / गट, with the taluka) and the Panchayat Samiti chairpersons (सभापती, one per panchayat samiti).

Why these pages: the State Election Commission (mahasec.maharashtra.gov.in) publishes only election programmes and party-wise
totals for ZP / PS / GP polls; its candidate search (mahasecelec.in/MasterSearch.aspx) lists contesting candidates, not winners.
The ZP sites list the elected people (measured 2026-11-13 on www.punezp.gov.in, last updated 29.04.2026 after the poll of
February 2026): "जि.प. पदाधिकारी" table नाव | पदनाम (6 rows); "मा. जिल्हा परिषद सदस्य" table अ.क्र. | तालुका |
मतदार गटाचा क्रमांक व गटाचे नाव | सदस्याचे नाव (taluka cells span rows; "1. डिंगोरे" = division 1); "पंचायत समिती सभापती" table
अ.क्र | तालुका | गण क्रमांक व गणाचे नाव | सदस्याचे नाव (13 rows, one per samiti).
A ZP whose council has not been elected (administrator period) may show an old council or none: every record carries the page's
own "last updated" date (page_updated) so the loader can judge.

One queue item = one ZP: payload {"kind": "form-pri_mh", "state": "MH", "url": ZP home, "district", "lgd_code" (LGD ZP code),
"pages": [known page urls]}. 1 GET of the home + at most 6 linked pages of the same host whose link text names office bearers,
members or panchayat samiti chairpersons. Records: type pri_member (cforms/_pri.py).
"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

from cforms import _pri
from dforms import _esw
import provenance

METHOD = "html table (Zilla Parishad website: office bearer, member and panchayat samiti chairperson pages; header words -> columns)"
# reader audit (audit.py): the site's menus (about the ZP, departments, the list of panchayat samiti chair pages, RTI, schemes,
# circulars, gallery) are lists of links, not people. The office bearers stand in a 2-column table (name | post) that the audit
# does not count; the Pune page (2026-11-13) has 6 office bearers and the reader makes 6 records
AUDIT_LEAVES_OUT = (r"^(जिल्हा परिषद विषयी|सामान्य प्रशासन विभाग|पंचायत समिती सभापती \||तक्रार निवारण|राज्य सरकार \||"
                    r"परिपत्रके|छायाचित्र दालन|माहितीचा अधिकार)")

ELECTION = "Maharashtra Zilla Parishad / Panchayat Samiti, as listed on the Zilla Parishad website"
L_BEARERS = re.compile(r"पदाधिकारी|office\s*bearer|elected\s*representative|लोकप्रतिनिधी")
L_MEMBERS = re.compile(r"(जिल्हा\s*परिषद|जि\.\s*प\.?)\s*सदस्य|^\s*(मा\.\s*)?सदस्य\s*$|zp\s*members|zilla\s*parishad\s*members|^\s*members\s*$", re.I)
L_PSHEADS = re.compile(r"(पंचायत\s*समिती\s*)?सभापती|sabhapati|chairm[ae]n.*panchayat\s*samiti", re.I)
L_WHOSWHO = re.compile(r"कोणाचे\s*कोण|who'?s\s*who", re.I)
OFFICER = re.compile(r"अधिकारी|officer|सचिव|secretary|अभियंता|engineer|लेखा|प्रशासक|administrator", re.I)
NOT_LINK = re.compile(r"\.pdf$|facebook|twitter|linkedin|#", re.I)
H_NAME = re.compile(r"नाव|name", re.I)
H_POST = re.compile(r"पदनाम|^पद$|designation|post", re.I)
H_TALUKA = re.compile(r"तालुका|taluka|block|पंचायत\s*समिती$", re.I)
H_DIV = re.compile(r"गट|गण|मतदार|division|constituency|ward", re.I)
H_PARTY = re.compile(r"पक्ष|party", re.I)
H_PHONE = re.compile(r"मोबा|mobile|phone|संपर्क|contact|दूरध्वनी", re.I)
H_SNO = re.compile(r"^(अ\.?\s*क्र|क्र|sr|s\.?\s*no|no\.?$)", re.I)
UPDATED = re.compile(r"(?:शेवटचे\s*अद्यावत|Last\s*Updated)\s*:?\s*(?:<[^>]+>\s*)*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})", re.I)
POSTS = [  # (pattern on the post text, level, key, English post, head rank)
    (re.compile(r"उपाध्यक्ष|vice\s*-?\s*president", re.I), "zp", "vice", "Vice President", 2),
    (re.compile(r"अध्यक्ष|president", re.I), "zp", "head", "President", 1),
]


def roles(header):
    out = {}
    for i, h in enumerate(header):
        h = h.strip()
        if not h or i in out:
            continue
        if H_SNO.match(h):
            out[i] = "sno"
        elif H_PHONE.search(h):
            out[i] = "phone"
        elif H_PARTY.search(h):
            out[i] = "party"
        elif H_POST.search(h):
            out[i] = "post"
        elif H_DIV.search(h) and "div" not in out.values():
            out[i] = "div"
        elif H_TALUKA.search(h) and "taluka" not in out.values():
            out[i] = "taluka"
        elif H_NAME.search(h) and "name" not in out.values():
            out[i] = "name"
    return out


def plain_name(s):
    """The name without the honorifics मा. / श्री. / श्रीम. / Shri / Smt (the written form stays in name_as_written)."""
    t = " ".join((s or "").split())
    for _ in range(3):
        t = re.sub(r"^(मा\.|मा\s|श्रीमती|श्रीम\.|श्री\.|सौ\.|डॉ\.|कु\.|shri\.?|smt\.?|mr\.?|mrs\.?|ms\.?)\s*", "", t, flags=re.I)
    return t.strip()


def division(s):
    """("12", "पारगाव त.अवसरी बु") from "12. पारगाव त.अवसरी बु"; the number only when it is all digits."""
    t = " ".join((s or "").replace("‍", "").split())
    m = re.match(r"^([0-9०-९]+)\s*[.)-]?\s*(.*)$", t)
    if not m:
        return "", t
    num = m.group(1).translate(str.maketrans("०१२३४५६७८९", "0123456789"))
    return _pri.digits(num), m.group(2).strip()


def page_kind(link_text, url):
    t = " ".join((link_text or "").split())
    if L_PSHEADS.search(t) and not L_BEARERS.search(t):
        return "ps_heads"
    if L_BEARERS.search(t):
        return "bearers"
    if L_MEMBERS.search(t):
        return "members"
    if L_WHOSWHO.search(t):
        return "whoswho"
    return ""


def links(html, base):
    """[(kind, url, link text)] of the home page's links to the pages read here (same host, first link of each url)."""
    host = urlparse(base).hostname
    out, seen = [], set()
    for a in _esw.soup(html).find_all("a", href=True):
        t = " ".join(a.get_text(" ", strip=True).split())
        u = urljoin(base, a["href"])
        if urlparse(u).hostname != host or NOT_LINK.search(a["href"]) or u in seen:
            continue
        k = page_kind(t, u)
        if k:
            seen.add(u)
            out.append((k, u, t))
    return out


def post_of(text):
    t = " ".join((text or "").split())
    if re.search(r"सभापती|chair", t, re.I):
        if re.search(r"पंचायत\s*समिती", t) and not re.search(r"समिती\s*,?\s*जि", t):
            return "ps", "head", "Chairperson (Sabhapati), Panchayat Samiti", 1
        return "zp", "chair-" + hashlib.sha1(t.encode()).hexdigest()[:8], "Chairperson, subject committee", 0
    for rx, lev, key, en, rank in POSTS:
        if rx.search(t):
            return lev, key, en, rank
    if re.search(r"सदस्य|member", t, re.I):
        return "zp", "", "Member", 0
    return "zp", "post-" + hashlib.sha1(t.encode()).hexdigest()[:8], t, 0


_SIGNS = re.compile(r"[\u093c\u093e-\u094d\u0900-\u0903\u0962\u0963\u200c\u200d]")


def mr_key(s):
    """Loose key for a Marathi or English place name: Devanagari consonant skeleton (vowel signs, anusvara, virama removed:
    शिरुर = शिरूर, मावळ = मवाळ), else the Latin key of _pri.norm."""
    t = " ".join((s or "").split())
    if re.search(r"[\u0900-\u097f]", t):
        t = re.sub(r"पंचायत\s*समिती|तालुका|ता\.", " ", t)
        return re.sub(r"[^\u0900-\u097f]", "", _SIGNS.sub("", t))
    return _pri.norm(t)


def ps_code(lgd, name, zp_code):
    """LGD code of the panchayat samiti `name` (Marathi or English) under ZP zp_code; "" when not exactly one."""
    k = mr_key(name)
    if not k or not zp_code:
        return ""
    hits = {r[0] for r in lgd.rows if r[1] == "ps" and r[4] == zp_code and k in (mr_key(r[2]), mr_key(r[3]))}
    return next(iter(hits)) if len(hits) == 1 else ""


def records(html, url, kind, p, lgd=None):
    lgd = lgd or _pri.Lgd("MH")
    soup = _esw.soup(html)
    m = UPDATED.search(html)
    updated = m.group(1) if m else ""
    district, zp_code = p.get("district", ""), p.get("lgd_code", "")
    recs = []
    for table in soup.find_all("table"):
        pos = []
        rows = _esw.grid(table, pos=pos)
        hdr_i = next((i for i, r in enumerate(rows[:3]) if "name" in roles(r).values()), None)
        if hdr_i is None:
            continue
        ro = roles(rows[hdr_i])
        col = {v: k for k, v in ro.items()}
        last_taluka = ""
        for row, sp in zip(rows[hdr_i + 1:], pos[hdr_i + 1:]):
            if len(row) <= col["name"] or row == rows[hdr_i]:
                provenance.skip_row(row, 'skip: len(row) <= col["name"] or row == rows[hdr_i]')
                continue
            cell = {k: (row[i] if i < len(row) else "") for k, i in col.items()}
            written = cell["name"]
            name = plain_name(written)
            if not name or H_NAME.search(written) and len(written) < 25:
                provenance.skip_row(row, 'skip: not name or H_NAME.search(written) and len(written) < 25')
                continue
            ward_no, ward_name = division(cell.get("div", ""))
            taluka = cell.get("taluka", "") or last_taluka     # the taluka cell is written once per taluka, then left empty
            last_taluka = taluka
            if kind == "ps_heads":
                level, key, post_en, rank = "ps", "head", "Chairperson (Sabhapati), Panchayat Samiti", 1
            elif "post" in cell and cell["post"]:
                level, key, post_en, rank = post_of(cell["post"])
                if kind == "whoswho" and (OFFICER.search(cell["post"]) or key.startswith("post-")):
                    provenance.skip_row(row, 'skip: kind == "whoswho" and (OFFICER.search(cell["post"]) or key.startswi...')
                    continue        # Who's Who pages mostly list officers: keep elected posts only
            elif kind == "whoswho":
                provenance.skip_row(row, 'skip: kind == "whoswho"')
                continue
            else:
                level, key, post_en, rank = "zp", "", "Member", 0
            d = {"post": post_en, "post_regional": cell.get("post") or None, "name": name, "name_as_written": written,
                 "district": district, "block": taluka or None, "ward_no": ward_no or None,
                 "ward_name": ward_name or None, "party": cell.get("party") or None,
                 "phone": _pri.phone(cell["phone"]) if cell.get("phone") else None, "election": ELECTION,
                 "page_updated": updated or None, "url": url, "src_url": url, "page_kind": kind,
                 "src_pos": {**sp, "cells": row}, "cells": dict(zip(rows[hdr_i], row))}
            if rank:
                d["head"], d["head_rank"] = True, rank
            if level == "ps":
                body = taluka or (cell.get("post", "") and re.sub(r"(?i)सभापती|पंचायत\s*समिती|,|chairperson", " ", cell["post"]).strip())
                code = ps_code(lgd, body, zp_code) if body else ""
                bkey = code or f"{zp_code or _esw.slug(district)}~" + hashlib.sha1(mr_key(body).encode()).hexdigest()[:10]
                rid, data = _pri.record("MH", "ps", lgd_code=code, body=f"Panchayat Samiti {body}".strip(), body_key=bkey,
                                        pkey=key, **d)
            else:
                pkey = key or (_pri.post_key(ward_no=ward_no) if ward_no else f"m{sp['table']}-{sp['row']}")
                rid, data = _pri.record("MH", "zp", lgd_code=zp_code, body=f"Zilla Parishad {district}".strip(), pkey=pkey, **d)
            recs.append((rid, data))
    return recs


L_FILE = re.compile(r"सदस्य|निकाल|पदाधिकारी|सभापती|member|result|office\s*bearer", re.I)   # "राजपत्र" (gazette) alone: other acts too
MAX_FILES = 3


def pdf_links(html, base):
    """[(url, link text)] of PDF links whose text names members, the gazette list of elected members (राजपत्र), results or
    office bearers (any host: NIC sites keep uploads on cdnbbsr.s3waas.gov.in)."""
    out, seen = [], set()
    for a in _esw.soup(html).find_all("a", href=True):
        u = urljoin(base, a["href"])
        t = " ".join(a.get_text(" ", strip=True).split()) or " ".join((a.get("title") or "").split())
        if re.search(r"\.pdf($|\?)", u, re.I) and L_FILE.search(t) and u not in seen:
            seen.add(u)
            out.append((u, t))
    return out


def text_layer(content):
    """True when the PDF's first page has a text layer (else it is a scan: OCR on the runners)."""
    try:
        import io
        from pypdf import PdfReader
        pg = PdfReader(io.BytesIO(content)).pages
        return len((pg[0].extract_text() or "").strip()) > 40 if len(pg) else False
    except Exception:
        return False


def fetch(p, get):
    """Records from the ZP pages; PDFs linked as member / gazette / result lists are saved to the bucket and noted as
    source_file records (scans: an OCR item reads them later on the runners)."""
    r = get(p["url"])
    if r is None:
        return [], [], "ZP home did not answer"
    base = r.url or p["url"]
    found = links(r.text, base)
    for u in p.get("pages", []):
        if u not in [x[1] for x in found]:
            found.append((page_kind(u, u) or "members", u, ""))
    found = found[:6]
    pdfs = [(u, t, "home") for u, t in pdf_links(r.text, base)]
    lgd = _pri.Lgd("MH")
    recs, empty = {}, []
    for kind, u, _ in found:
        pr = get(u)
        if pr is None:
            continue
        got = records(pr.text, u, kind, p, lgd)
        for rid, d in got:
            recs.setdefault(rid, d)      # first page wins (office bearer page before the member list)
        if not got:
            empty.append(u)
            pdfs += [(x, t, kind) for x, t in pdf_links(pr.text, u)]
    files, slug = [], _esw.slug(p.get("district", "")) or "zp"
    seen = set()
    for u, t, where in pdfs:
        if u in seen or len(seen) >= MAX_FILES:
            continue
        seen.add(u)
        f = get(u)
        ok = f is not None and f.content[:4] == b"%PDF"
        sha = hashlib.sha1(u.encode()).hexdigest()[:12]
        path = f"pri/MH/{slug}/{sha}.pdf"
        if ok:
            files.append((path, f.content, "application/pdf"))
        recs[f"pri_file:MH:{slug}:{sha}"] = {
            "type": "source_file", "state": "MH", "district": p.get("district"), "lgd_code": p.get("lgd_code", ""), "url": u,
            "link_text": t, "found_on": where, "stored": path if ok else None, "bytes": len(f.content) if ok else None,
            "fetched": ok, "text_layer": text_layer(f.content) if ok else None, "purpose": "pri_member list (ZP / PS)",
            **({"src_url": u, "method": "file saved to the bucket (pdf)"} if ok else {})}
    out = list(recs.items())
    n_people = sum(1 for _, d in out if d.get("type") == "pri_member")
    why = "" if out else ("no office bearer / member pages linked on the ZP home" if not found
                          else "linked pages have no name tables (" + ", ".join(empty[:3]) + ")")
    if out and not n_people:
        why = "only files saved (no name tables)"
    return out, files, why


def items(get=None):
    """One item per ZP site (hosts as dforms/sub2_mh_zp.py)."""
    from dforms.sub2_mh_zp import ZP
    lgd = _pri.Lgd("MH")
    out = []
    for host, (_code, name) in sorted(ZP.items(), key=lambda x: x[1][1]):
        out.append({"key": f"pri_mh_zp:{_esw.slug(name)}",
                    "payload": {"kind": "form-pri_mh", "state": "MH", "level": "zp", "url": f"https://{host}/",
                                "host": host, "district": name, "lgd_code": lgd.match("zp", name), "election": ELECTION,
                                "pages": [], "route": "abroad", "expected": 60}})
    return out
