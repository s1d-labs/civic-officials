"""Sikkim: members elected in the Panchayat General Election 2022 (poll 10 Nov 2022, count 12 Nov 2022; party-less), from
text PDFs (exported from Excel; no OCR needed):
  1. State Election Commission notifications of 13-11-2022 under Rule 84 of the Sikkim Panchayat (Conduct of Election) Rules
     1997, as published on namchi.nic.in "Panchayati Raj Institutions":
       No. 20/SEC/2022 "candidates declared elected to the Gram Panchayats" (16 pages, all 6 districts) and
       No. 21/SEC/2022 "... to the Territorial Constituency" (zilla panchayat members, 4 pages, with the allotted symbol).
     They list the wards that went to the poll; wards won unopposed are not in them.
  2. District lists that also cover the uncontested wards: Soreng "Newly Elected Gram Panchayats" (every ward of 36 GPUs) and
     "Newly Elected Zilla Panchayats" (soreng.nic.in, posted 2022-12).
Columns (header words): GPU / Zilla Panchayat, ward / territorial constituency (TC) with the seat's category in brackets
("Lower Sribadam(ST)", "[SC (W)]", "(OBC(C)W)", "(BL-ST (W))"), SN / SL, candidate, symbol. In the district lists the GPU cell
is merged over its wards, so its words sit on lines between the ward rows: they are joined to the GPU whose ward rows
(ward numbers 1, 2, ... restart per GPU) surround them.
Heads (zilla adhyaksha, up-adhyaksha, gram panchayat president / vice president) are chosen later by the members and are not
in these lists.

Records: level gp (ward member of a gram panchayat unit) or zp (zilla panchayat member of a territorial constituency), role
member, body_name = the GPU name (gp) or the zilla panchayat (zp: the district), ward / ward_no / category, symbol (zp, SEC list).
Record ids: pri:pri_sk:2022:<list>:<district>:<gpu no or zp>:<ward no> with list = sec (SEC notification) or dist (district
list); the same seat may come from both lists (the loader keeps one).
"""
import re

from dforms import _pri
from dforms._esw import pdf_pages
import provenance

METHOD = "pdf text (pypdf layout; header words -> columns; merged GPU cells joined by ward-number groups)"
MODULE = "pri_sk"
ELECTION = "Sikkim Panchayat General Election 2022"
CDN_NAMCHI = "https://cdn.s3waas.gov.in/s38757150decbd89b0f5442ca3db4d0e0e/uploads/2022/11/"
CDN_SORENG = "https://cdn.s3waas.gov.in/s3f457c545a9ded88f18ecee47145a72c0/uploads/2022/12/"
SEEDS = [
    ("sec-gp", CDN_NAMCHI + "2022111630.pdf", "gp", "sec", "", "https://namchi.nic.in/panchayati-raj-institutions/"),
    ("sec-zp", CDN_NAMCHI + "2022111619.pdf", "zp", "sec", "", "https://namchi.nic.in/panchayati-raj-institutions/"),
    ("soreng-gp", CDN_SORENG + "2022121341.pdf", "gp", "dist", "Soreng", "https://soreng.nic.in/?p=2796"),
    ("soreng-zp", CDN_SORENG + "2022121365.pdf", "zp", "dist", "Soreng", "https://soreng.nic.in/?p=2796"),
]
CAT = re.compile(r"(?:[\(\[\)]\s*|\s+(?=(?:BL-)?(?:OBC|ST|SC|UR|GEN)\b))((?:BL\s*-\s*)?(?:OBC|ST|SC|UR|GEN|BL)\b.*)$")
NUM = re.compile(r"^(\d+)\s*\.\s*(.*)$")


def items(get=None):
    return [{"key": f"pri_sk:{k}", "payload": {"reader": MODULE, "url": u, "level": lv, "list": ls, "district": d, "page": pg,
                                               "state": "SK", "india_only": False, "route": "abroad"}}
            for k, u, lv, ls, d, pg in SEEDS]


def segs(line):
    """[(start column, text)] of the parts of a layout line split at 2+ spaces."""
    return [(m.start(), m.group(0).strip()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def split_cat(s):
    """'Lower Sribadam(ST)' -> ('Lower Sribadam', 'ST'); 'Soreng Mangsari(ST(W)' -> ('Soreng Mangsari', 'ST(W)')."""
    s = _pri.clean(s)
    m = CAT.search(s)
    if not m:
        return s, ""
    cat = re.sub(r"\s+", "", m.group(1)).rstrip(")]")
    if cat.count("(") > cat.count(")"):
        cat += ")" * (cat.count("(") - cat.count(")"))
    return s[:m.start()].strip(" -"), cat


def header_cols(line):
    """{role: start column} from a header line, or None."""
    if not re.search(r"(?i)candidate", line):
        return None
    cols = {}
    for x, t in segs(line):
        tl = t.lower()
        if re.search(r"gpu|zilla", tl):
            cols["body"] = x
        elif re.search(r"ward|territorial|\btc\b", tl):
            cols["ward"] = x
        elif re.match(r"^(sn|sl\.?)\b", tl):
            cols["sn"] = x
        elif "candidate" in tl:
            cols["name"] = x
        elif "symbol" in tl:
            cols["symbol"] = x
    return cols if "ward" in cols and "name" in cols else None


def rows(pages):
    """Rows {district, gpu (text or None), gpu_parts [(page, line, text)], ward, sn, name, symbol, page, line, line_text}."""
    out, district, cols, prev = [], "", None, None
    for pi, text in enumerate(pages, 1):
        for li, line in enumerate(text.split("\n"), 1):
            m = re.search(r"DISTRICT\s*:\s*([A-Za-z][A-Za-z ]*?)(?:\s*-|\s{2,}|$)", line)
            if m:
                district, prev = m.group(1).strip().title(), None
                continue
            h = header_cols(line)
            if h:
                cols, prev = h, None
                continue
            if re.search(r"(?i)^\s*(by order|copy for)", line):
                cols, prev = None, None          # end of the list: the copy-to lines follow
                continue
            if not cols or not line.strip() or re.search(r"(?i)^\s*page \d", line) or \
                    all(re.fullmatch(r"(?i)no\.?|panchayat|constituency|sl\.?|no\.", t) for _, t in segs(line)):
                continue
            ss = segs(line)
            mid = (cols.get("body", 0) + cols["ward"]) / 2 if "body" in cols else cols["ward"] - 6
            lead_sl = "sn" in cols and cols["sn"] < cols["ward"]          # district lists: SL. NO. first
            sl = None
            if lead_sl and ss and ss[0][1].isdigit() and ss[0][0] < mid:
                sl, ss = ss[0][1], ss[1:]
            body = [t for x, t in ss if x < mid and "body" in cols]
            rest = [(x, t) for x, t in ss if not (x < mid and "body" in cols)]
            ward_i = next((i for i, (x, t) in enumerate(rest) if NUM.match(t)), None)
            if ward_i is None and body:
                # the GPU cell and the ward cell came out with one space between them: "24. Lower Timburbong 3. Banpala ..."
                m2 = re.match(r"^(\d+\s*\.\s*.*?\S)\s+(\d+\s*\.\s*\S.*)$", body[-1])
                if m2:
                    body[-1] = m2.group(1)
                    rest = [(int(mid), m2.group(2))] + rest
                    ward_i = 0
            sn, name, symbol, ward = None, "", "", ""
            if ward_i is not None:
                after = rest[ward_i + 1:]
                if not lead_sl:
                    k = next((i for i, (x, t) in enumerate(after) if t.isdigit()), None)
                    if k is not None:
                        sn = after[k][1]
                        ward = " ".join([rest[ward_i][1]] + [t for _, t in after[:k]])
                        tail = [t for _, t in after[k + 1:]]
                        name = tail[0] if tail else ""
                        symbol = " ".join(tail[1:]) if "symbol" in cols else ""
                else:
                    tail = [t for _, t in after]
                    if tail and not re.match(r"^[\(\[]", tail[-1]):
                        name = tail[-1]
                        ward = " ".join([rest[ward_i][1]] + tail[:-1])
                    sn = sl
            r = {"district": district, "page": pi, "line": li, "line_text": line}
            if ward and name and sn:
                r.update(ward=ward, sn=sn, name=name, symbol=symbol, gpu_parts=[(pi, li, t) for t in body])
                out.append(r)
                prev = r
            else:
                for t in body:
                    out.append({**r, "frag": t})
                if prev is not None and not body and rest and prev.get("district") == district:
                    prev["ward"] += " " + " ".join(t for _, t in rest)     # a ward name broken over two lines
    return out


def group_gpus(rs, merged):
    """Give each ward row its GPU name. SEC lists: the GPU is on the first row of its group (continuation lines join it).
    District lists (merged cells): ward numbers restart per GPU; fragments go to the group whose lines surround them."""
    groups, cur, last_no = [], None, None
    for r in rs:
        if "frag" in r:
            continue
        no = int(NUM.match(r["ward"]).group(1))
        new = cur is None or r["district"] != cur["district"] or (r["gpu_parts"] if not merged else (last_no is not None and no <= last_no))
        if new:
            cur = {"district": r["district"], "rows": [], "parts": []}
            groups.append(cur)
        cur["rows"].append(r)
        cur["parts"] += r["gpu_parts"]
        last_no = no
    frags = [r for r in rs if "frag" in r]
    for f in frags:
        cands = [g for g in groups if g["district"] == f["district"]]
        if not cands:
            continue
        pos = (f["page"], f["line"])

        def dist(g):
            a = (g["rows"][0]["page"], g["rows"][0]["line"])
            b = (g["rows"][-1]["page"], g["rows"][-1]["line"])
            if a <= pos <= b:
                return (0, 0)
            if pos < a:
                return (1, (a[0] - pos[0]) * 1000 + a[1] - pos[1])
            return (1, (pos[0] - b[0]) * 1000 + pos[1] - b[1])
        if merged:
            g = min(cands, key=dist)
        else:       # SEC lists: a GPU name broken over lines continues the group that started above it
            before = [g for g in cands if (g["rows"][0]["page"], g["rows"][0]["line"]) <= pos]
            g = before[-1] if before else cands[0]
        g["parts"].append((f["page"], f["line"], f["frag"]))
    for g in groups:
        g["gpu"] = _pri.clean(" ".join(t for _, _, t in sorted(g["parts"])))
    return groups


def records(pages, p, url):
    level, lst = p["level"], p["list"]
    merged = lst == "dist"
    out = []
    for g in group_gpus(rows(pages), merged):
        gm = NUM.match(g["gpu"] or "")
        gno, gname = (gm.group(1), gm.group(2).strip()) if gm else ("", g["gpu"])
        district = g["district"] or p.get("district", "")
        for r in g["rows"]:
            wm = NUM.match(r["ward"])
            wno, wname = wm.group(1), wm.group(2)
            ward, cat = split_cat(wname)
            if level == "zp":
                body = gname or district
                key = f"2022:{lst}:{_pri.slug(district)}:zp:{wno}"
                post = "Zilla Panchayat Member"
            else:
                body = re.sub(r"(?i)\s*\bGP\b\.?$", "", gname).strip()
                key = f"2022:{lst}:{_pri.slug(district)}:{gno or _pri.slug(body)}:{wno}"
                post = "Gram Panchayat Member (Panchayat Ward)"
            out.append(_pri.record(
                MODULE, key, state="SK", level=level, role="member", post=post, name=r["name"], symbol=r.get("symbol"),
                body_name=body, body_no=gno if level == "gp" else (gno or None), district=district,
                ward=ward, ward_no=wno, category=cat, constituency=f"{wno}. {wname}" if level == "zp" else None,
                election=ELECTION, election_year=2022, status="won" if lst == "sec" else "elected",
                list=("SEC notification " + ("20/SEC/2022" if level == "gp" else "21/SEC/2022") + " dated 13-11-2022") if lst == "sec"
                else f"{district} district list of newly elected members",
                sn=r["sn"], source=url, src_url=url,
                src_pos=provenance.line_pos(r["page"], r["line"], r["line_text"],
                                            gpu_lines=[[a, b] for a, b, _ in sorted(g["parts"])] or None)))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    pages = pdf_pages(r.content)
    if not pages:
        return [], [], "not a readable pdf"
    recs = records(pages, p, p["url"])
    return recs, [], "" if recs else "no rows"
