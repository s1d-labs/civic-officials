"""Bihar: the four staff of every gram panchayat (Panchayat Secretary, Executive Assistant, Technical Assistant, Accountant-cum-IT
Assistant) with their mobile numbers, from the Panchayati Raj Department's "District Officer Phone Directory" page
(betastate.bihar.gov.in/biharprd/DyPageView.aspx?PageTitleID=3111), row "Panchayat Secretary_Ex Asst_TA_Acc-cum-ITAsst Contact
Detail": one PDF (2026-11-13: /file_2/FileUpload/2024/May/07-May-2024/44/DyPage/787de287-....pdf, 7.9 MB, 257 pages, iLovePDF
merge of the 38 districts' own sheets, modified 2023-03-02). Checked 2026-11-13 from dev-vps-3 (Mumbai): page and PDF answer.

The column heading of the first sheet (Araria) is an image of Hindi words: क्र0 सं0 | BLOCK | ग्राम पंचायत का नाम | पंचायत सचिव
(नाम, मोबाईल नं0) | कार्यपालक सहायक | तकनीकी सहायक | लेखापाल सह आईटी सहायक; the PDF title gives the same order. The districts
filled the sheet in their own way: with or without the BLOCK column, English or Hindi (some Hindi in legacy fonts that extract as
Latin letters, e.g. Kruti Dev "flaguku"), the block in a heading line ("District…Araria  Block…Araria  BPRO Name & Mobile No ..",
"ARWAL  KURTHA  BPRO  NAME, 9199806401", "जिला ... प्रखंड ... BPRO का नाम ...") or not at all. About 39 pages have no text
layer (scans: no rows; an OCR task can read the stored copy).

How a row is read (pdftotext -layout, else pypdf layout): a line that starts with a serial number and has letters. The line is cut
into cells at gaps of 2+ spaces, and every phone number (6-12 digits) is cut out as a cell of its own. The text cells before the
first phone are [block,] gram panchayat, secretary (3+ cells: the first is the block; 2: no block). After that, each name cell and
the phone after it belong to the next post in the order above. A post without a phone keeps its name; a phone without a name
keeps the phone. Rows with no name at all (phones only: the names stand on other lines in a few sheets) are counted, not kept.
A heading line is a line that is not a row and has "BPRO" in it: it starts a section; its text before "BPRO" gives district and
block when it has two cells ("District…Araria", "Block…Araria", "जिला-SUPAUL", "प्रखंड - Raghopur"); the 10-digit number after
"BPRO" is the BPRO's mobile (kept on each record of the section as bpro_phone, with the heading text).

LGD: dforms/vil_br_lgd.json (lgd.pri_local_bodies of Bihar: 8,051 gram panchayats with their Panchayat Samiti and Zila
Parishad). The GP name (letters only, upper case) is looked up in the block when the block is known (row cell or heading),
else in the whole state; a name that is unique gives the LGD code, block and district. A section without a known block takes
the block / district that most of its unique matches give.

Records (dept rural_development, level gram_panchayat): one per post per row: post (English), post_regional (Hindi), name as
written, phone, area = the gram panchayat as written, block, district, lgd_gp_code, lgd_block (name), lgd_how, bpro_phone,
section_head, and the raw cells. src_pos = page + line + line text. Nothing is masked.
One queue item = page + PDF (2 GETs). The PDF is kept in the bucket (depts/vil_br_prd/ps_ea_ta_acc.pdf).
Record ids: dept:vil_br_prd:p<page>-l<line>:<post key>.
"""
import difflib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

from dforms import _esw, _field
import provenance

METHOD = "pdf text (pdftotext -layout, else pypdf layout); cells at 2+ space gaps and phone numbers; posts in sheet order"

MODULE = "vil_br_prd"
PAGE = "https://betastate.bihar.gov.in/biharprd/DyPageView.aspx?PageTitleID=3111"
SUBJECT = re.compile(r"(?i)panchayat\s*secretary")
POSTS = [("ps", "Panchayat Secretary", "पंचायत सचिव"), ("ea", "Executive Assistant (Gram Panchayat)", "कार्यपालक सहायक"),
         ("ta", "Technical Assistant (Gram Panchayat)", "तकनीकी सहायक"),
         ("acc", "Accountant-cum-IT Assistant (Gram Panchayat)", "लेखापाल सह आईटी सहायक")]
PHONE = re.compile(r"(?<!\d)(\d{6,12})(?!\d)")
ROW = re.compile(r"^\s*(\d{1,3})[.)]?\s+(.*\S)\s*$")
LETTER = re.compile(r"[A-Za-zऀ-ॿ]")
HEAD_LABEL = re.compile(r"(?i)^(district|distric|dist|block|जि[लऱ]ा|जजरा|जजऱा|क्षजऱा|प्रख[ंॊि]*ड|प्रखॊड्)\s*[:.…\-–_\s]*")

LEGACY = re.compile(r"[\[\]{}~&;]|[a-z][A-Z]")
_LGD = None
_IN_BLOCK = {}


def key(s):
    """Letters only, upper case (Latin) / as written (Devanagari): "Araria Basti" = "ARARIA BASTI" = "ARARIA-BASTI"."""
    return re.sub(r"[^A-Zऀ-ॿ]", "", (s or "").upper())


def lgd():
    """(by_block {(block key, gp key): [rows]}, by_gp {gp key: [rows]}, blocks {block key: (block, district)})."""
    global _LGD
    if _LGD is None:
        rows = json.loads((Path(__file__).with_name("vil_br_lgd.json")).read_text())["rows"]
        by_block, by_gp, blocks = {}, {}, {}
        for code, gp, block, dist in rows:
            by_block.setdefault((key(block), gkey(gp)), []).append((code, gp, block, dist))
            by_gp.setdefault(gkey(gp), []).append((code, gp, block, dist))
            blocks.setdefault(key(block), (block, dist))
        _LGD = (by_block, by_gp, blocks)
    return _LGD


def cells_of(text):
    """Cells of a row (after the serial): text cells at 2+ space gaps, each phone number a cell of its own (("p", "9801...")
    or ("t", "NAME"))."""
    out = []
    for chunk in re.split(r"\s{2,}", text.strip()):
        pos = 0
        for m in PHONE.finditer(chunk):
            t = chunk[pos:m.start()].strip(" ,;-–")
            if t:
                out.append(("t", _esw.clean(t)))
            out.append(("p", m.group(1)))
            pos = m.end()
        t = chunk[pos:].strip(" ,;-–")
        if t:
            out.append(("t", _esw.clean(t)))
    return [c for c in out if c[0] == "p" or LETTER.search(c[1])]


def split_row(text):
    """{"block", "gp", "posts": {post key: {"name", "phone"}}} of one row, or None (no name at all)."""
    cells = cells_of(text)
    if not any(k == "t" for k, _ in cells):
        return None
    first_p = next((i for i, (k, _) in enumerate(cells) if k == "p"), len(cells))
    lead = [v for _, v in cells[:first_p]]
    row = {"block": "", "gp": "", "posts": {}}
    if len(lead) >= 3:
        row["block"], row["gp"], name0 = lead[0], lead[1], " ".join(lead[2:])
    elif len(lead) == 2:
        row["gp"], name0 = lead
    else:
        row["gp"], name0 = (lead[0] if lead else ""), ""
    i, cur = 0, {"name": name0, "phone": ""}
    for k, v in cells[first_p:]:
        if k == "p":
            if cur["phone"]:                      # a second phone with no name between: the next post, phone only
                row["posts"][POSTS[i][0]] = cur
                i, cur = i + 1, {"name": "", "phone": ""}
                if i >= len(POSTS):
                    break
            cur["phone"] = v
        else:
            if cur["name"] or cur["phone"]:
                row["posts"][POSTS[i][0]] = cur
                i, cur = i + 1, {"name": "", "phone": ""}
                if i >= len(POSTS):
                    break
            cur["name"] = v
    if i < len(POSTS) and (cur["name"] or cur["phone"]):
        row["posts"][POSTS[i][0]] = cur
    if not row["gp"] and not row["posts"]:
        return None
    return row


def heading(line):
    """(district, block, bpro_phone) of a section heading line (a line with "BPRO" that is not a row)."""
    m = re.search(r"(?i)bpro", line)
    before, after = line[:m.start()], line[m.end():]
    parts = [HEAD_LABEL.sub("", p).strip(" .…:-–_,]") for p in re.split(r"\s{2,}|\|\|", before.strip())]
    parts = [p for p in parts if p and LETTER.search(p)]
    dist = blk = ""
    if len(parts) >= 2:
        dist, blk = parts[0], parts[1]
    elif len(parts) == 1:
        blk = parts[0]
    ph = re.search(r"(?<!\d)([6-9]\d{9})(?!\d)", after)
    return dist, blk, ph.group(1) if ph else ""


def gkey(s):
    """GP key: key() without a trailing "Panchayat" / "Gram Panchayat" / "GP" (LGD writes "Sakri Panchayat" for some GPs)."""
    return re.sub(r"(GRAMPANCHAYAT|PANCHAYAT|GP|ग्रामपंचायत|पंचायत)$", "", key(s)) or key(s)


def match(gp, block_hint, state_wide=True):
    """(lgd row, how) for a GP name: in the block (row cell / heading), else unique in the state."""
    by_block, by_gp, blocks = lgd()
    g = gkey(gp)
    if not g:
        return None, ""
    if block_hint:
        hit = by_block.get((key(block_hint), g))
        if hit and len(hit) == 1:
            return hit[0], "block+name"
    hit = by_gp.get(g) if state_wide else None
    if hit and len(hit) == 1:
        return hit[0], "unique name"
    if block_hint:                                # spelling variants inside the block ("LAKSHMIPUR" / "LAXMIPUR")
        b = key(block_hint)
        if not _IN_BLOCK:
            for (bk, gk), rows in by_block.items():
                _IN_BLOCK.setdefault(bk, []).append((gk, rows))
        cands = [(difflib.SequenceMatcher(None, g, gk).ratio(), rows) for gk, rows in _IN_BLOCK.get(b, [])]
        cands.sort(key=lambda x: -x[0])
        if cands and cands[0][0] >= 0.8 and len(cands[0][1]) == 1 and (len(cands) == 1 or cands[1][0] < cands[0][0] - 0.05):
            return cands[0][1][0], "block+similar name"
    return None, ""


def parse(text, url=""):
    """Records of the PDF layout text (pages split by form feeds). Returns (records, stats)."""
    blocks = lgd()[2]
    sections, cur = [], {"head": "", "dist": "", "block": "", "bpro": "", "rows": []}
    stats = Counter()
    for pg, ptext in enumerate(text.split("\f"), 1):
        for ln, raw in enumerate(ptext.split("\n"), 1):
            m = ROW.match(raw)
            if m and LETTER.search(m.group(2)):
                row = split_row(m.group(2))
                if row is None:
                    stats["rows_without_names"] += 1
                    continue
                row.update(page=pg, line=ln, raw=raw, serial=m.group(1))
                cur["rows"].append(row)
            elif m:
                stats["rows_without_names"] += 1
            elif re.search(r"(?i)bpro", raw):
                d, b, ph = heading(raw)
                sections.append(cur)
                cur = {"head": _esw.clean(raw), "dist": d, "block": b, "bpro": ph, "rows": []}
    sections.append(cur)
    out = []
    for sec in sections:
        hint = sec["block"] if key(sec["block"]) in blocks else ""
        found = [(row, *match(row["gp"], row["block"] if key(row["block"]) in blocks else hint)) for row in sec["rows"]]
        common = Counter((h[2], h[3]) for _, h, _ in found if h)
        sec_block, sec_dist = common.most_common(1)[0][0] if common else ("", "")
        dists = Counter(h[3] for _, h, _ in found if h)
        top = blocks[key(hint)][1] if hint else (dists.most_common(1)[0][0] if dists and dists.most_common(1)[0][1] >= 3 else "")
        if top:          # a unique name in another district than the section's is another GP of the same name
            found = [(row, h, how) if not h or how != "unique name" or h[3] == top else (row, None, "") for row, h, how in found]
        for row, hit, how in found:
            if hit is None and sec_block:          # second try in the section's block
                hit, how = match(row["gp"], sec_block, state_wide=False)
            blk = hit[2] if hit else (blocks.get(key(row["block"]), ("", ""))[0] or blocks.get(key(sec["block"]), ("", ""))[0]
                                      or sec_block)
            dist = hit[3] if hit else (blocks.get(key(blk), ("", ""))[1] or sec_dist)
            stats["rows"] += 1
            stats["rows_lgd"] += bool(hit)
            for pk, post, post_hi in POSTS:
                p = row["posts"].get(pk)
                if not p or not (p["name"] or p["phone"]):
                    continue
                if re.fullmatch(r"(?i)(vacant|रिक्त|-+|na|n/a|nil)", p["name"] or "") and not p["phone"]:
                    p = {"name": "", "phone": "", "vacant": True}
                data = {"type": "dept_office", "dept": "rural_development", "level": "gram_panchayat", "state": "BR",
                        "post": post, "post_regional": post_hi, "name": p["name"], "phone": p["phone"],
                        "area": row["gp"], "block": blk, "block_as_written": row["block"] or sec["block"],
                        "district": dist, "district_as_written": sec["dist"],
                        "lgd_gp_code": hit[0] if hit else "", "lgd_gp_name": hit[1] if hit else "", "lgd_how": how,
                        "bpro_phone": sec["bpro"], "section_head": sec["head"][:300], "serial": row["serial"],
                        "source": url, "src_url": url,
                        "src_pos": provenance.line_pos(row["page"], row["line"], row["raw"])}
                if p.get("vacant"):
                    data["vacant"] = True
                if LEGACY.search(p["name"] or "") or LEGACY.search(row["gp"] or ""):
                    data["legacy_font_suspect"] = True     # Hindi in a legacy font (Kruti Dev) read as Latin letters
                out.append((f"dept:{MODULE}:p{row['page']}-l{row['line']}:{pk}", {k: v for k, v in data.items() if v != ""}))
    stats["records"] = len(out)
    return out, stats


def file_link(html, page_url=PAGE):
    """Address of the PDF in the directory row whose subject names the Panchayat Secretary."""
    for tr in re.findall(r"<tr[^>]*grid-row.*?</tr>", html, re.S):
        if SUBJECT.search(re.sub(r"<[^>]+>", " ", tr)):
            m = re.search(r"href='([^']+\.pdf)'|href=\"([^\"]+\.pdf)\"|data-id=\"([^\"]+\.pdf)\"", tr)
            if m:
                return urljoin(page_url, next(g for g in m.groups() if g))
    return ""


def fetch(p, get):
    page = p.get("url") or PAGE
    r = get(page)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, "page", r.content)]
    link = file_link(r.text, page) or p.get("file_url", "")
    if not link:
        return [], files, "no Panchayat Secretary row on the page"
    f = get(link)
    if f is None:
        return [], files, "no answer for the PDF"
    if f.content[:5] != b"%PDF-":
        return [], files, "the list file is not a PDF"
    files.append((f"depts/{MODULE}/ps_ea_ta_acc.pdf", f.content, "application/pdf"))
    recs, stats = parse(_field.pdf_text(f.content), link)
    src = provenance.at(f, link)
    for _, d in recs:
        d.update(src)
        d["page_url"] = page
    return recs, files, "" if recs else "no rows"
