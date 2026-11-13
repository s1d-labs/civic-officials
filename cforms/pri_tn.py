"""Tamil Nadu rural local bodies (Panchayati Raj): elected members from the State Election Commission results files,
tnsec.tn.gov.in/tnsec_static/election_results/rlbe<year>/ (year 2019: ordinary election of December 2019 in 27 districts;
year 2021: ordinary election of October 2021 in the 9 new or re-formed districts, plus casual (bye-) elections elsewhere).

Each district page (POST cmb_district=<code> to rlbe<year>.php) links four kinds of PDF (made by mPDF with its Tamil font; the text
layer is complete once the glyphs are mapped back, cforms/cn_mpdf_ta.py, as in cforms/tn_text.py):
  dpwm_<d>.pdf           District Panchayat ward members         -> level zp, post "District Panchayat Ward Member"
  puwm_<d>.pdf           Panchayat Union ward members            -> level ps, post "Panchayat Union Ward Member"
  vpp_<d>.pdf            Village Panchayat presidents            -> level gp, post "Village Panchayat President" (head)
  vpwm_<d>_<union>.pdf   Village Panchayat ward members, per union -> level gp, post "Village Panchayat Ward Member"
Each contest: label lines ("மாவட்டம் : <district>", "ஊராட்சி ஒன்றியம் : <union>", "கிராம ஊராட்சி : <village panchayat>",
"வார்டு எண்: <n> [<reservation>]"; page captions repeat the district / union), a totals line, then one row per candidate
(serial, name, gender, father's / husband's name, party (not in village panchayat files: no party symbols), votes, %, result).
A label line may wrap: its pieces are joined by column position. The winner is the row with "வெற்றி" (won) or
"போட்டியின்றி தேர்வு" (elected unopposed).
Not in these files: the indirectly elected chairpersons / vice chairpersons of district panchayats and panchayat unions, and the
vice presidents of village panchayats (no SEC page lists them).

One queue item = one PDF. Payload: {"kind": "form-pri_tn", "state": "TN", "url", "file" (dpwm|puwm|vpp|vpwm), "year",
"district_code", "district" (English, LGD), "zp_lgd" (LGD code of the district panchayat), "election", "bye_election" (bool),
optional "stored" (bucket key of a saved copy: then the site is not asked)}.
The seed item {"kind": "seed", "module": "pri_tn"} lists the PDFs of every district page of both years (items(get)).
Records: type pri_member (cforms/_pri.py), one per winner, with every candidate of the contest in "candidates".
Record id pri:TN:<level>:<LGD code or names>:<head | w<ward>>, with suffix ":<year>-bye" for casual elections.
"""
import difflib
import hashlib
import os
import re
import subprocess
import tempfile

import provenance
from cforms import _pri
from cforms.cn_mpdf_ta import convert
from cforms.tn_text import NUM, chunks, party_en, row_of, totals, ward_of

METHOD = "pdf text (pdftotext -layout) + Tamil font map (mPDF glyphs); label lines joined by column"

BASE = "https://tnsec.tn.gov.in/tnsec_static/election_results/rlbe{year}/"
# district option codes of the results pages -> LGD district (panchayat) names
DISTRICTS = {
    "ari": "Ariyalur", "rmd": "Ramanathapuram", "erd": "Erode", "cud": "Cuddalore", "kar": "Karur", "kki": "Kallakurichi",
    "kkm": "Kanniyakumari", "kpm": "Kancheepuram", "kgi": "Krishnagiri", "cbe": "Coimbatore", "svg": "Sivagangai",
    "cpt": "Chengalpattu", "slm": "Salem", "tnj": "Thanjavur", "dpi": "Dharmapuri", "dgl": "Dindigul", "try": "Tiruchirappalli",
    "tnv": "Tirunelveli", "tpt": "Tirupathur", "tpr": "Tiruppur", "tvm": "Tiruvannamalai", "tlr": "Tiruvallur",
    "tvr": "Tiruvarur", "tut": "Thoothukkudi", "tki": "Tenkasi", "thn": "Theni", "ngp": "Nagapattinam", "nmk": "Namakkal",
    "nlg": "The Nilgiris", "pdk": "Pudukkottai", "pmb": "Perambalur", "mdu": "Madurai", "myl": "Mayiladuthurai",
    "rpt": "Ranipet", "vnr": "Virudhunagar", "vpm": "Villupuram", "vlr": "Vellore",
}
# the 9 districts of the ordinary election of October 2021 (all other 2021 files are casual elections)
NEW_2021 = {"kki", "kpm", "cpt", "tnv", "tpt", "tki", "rpt", "vpm", "vlr"}
FILES = {"dpwm": ("zp", "District Panchayat Ward Member"), "puwm": ("ps", "Panchayat Union Ward Member"),
         "vpp": ("gp", "Village Panchayat President"), "vpwm": ("gp", "Village Panchayat Ward Member")}
# terms run 5 years from the first meeting (2019 poll: January 2020; 2021 poll: October 2021); not checked against a later
# notification: an indicator only
TERM = {"2019": "elected Dec 2019; 5-year term from Jan 2020, so it ended about Jan 2025 (indicator, not checked)",
        "2021": "elected Oct 2021; 5-year term from Oct 2021, so it ended about Oct 2026 (indicator, not checked)"}
LABELS = (("district", "மாவட்டம்"), ("union", "ஊராட்சி ஒன்றியம்"), ("gp", "கிராம ஊராட்சி"), ("ward", "வார்டு எண்"))
ORDER = ["district", "union", "gp", "ward"]
LABEL = re.compile(r"(மாவட்டம்|ஊராட்சி ஒன்றியம்|கிராம ஊராட்சி|வார்டு எண்)\s*:\s*")
WON = ("வெற்றி", "போட்டியின்றி")
# reader audit (audit.py): the files list every candidate of each contest; the reader keeps the winner. Checked on the 2 saved
# files (2026-11-13): 127 and 98 result lines "won / unopposed" = 127 and 98 contests = 127 and 98 records. The raw text layer
# (mPDF glyphs before convert()) does not hold the names as the records write them, so the audit's names_found stays low
AUDIT_RESULTS = True


def tkey(s):
    """Tamil name key: letters and digits only (spaces, dots, brackets dropped)."""
    return re.sub(r"[\s.,()\-\[\]'`]+", "", s or "")


class Block:
    """One contest (the shape cforms/tn_text.ward_of reads)."""

    def __init__(self, ctx, page):
        self.ctx = dict(ctx)
        self.body_type, self.body = "", ctx.get("gp") or ctx.get("union") or ctx.get("district") or ""
        self.ward, self.reservation = ctx.get("ward") or "", ctx.get("reservation") or ""
        self.page, self.totals, self.cols, self.rows, self.extra = page, {}, {}, [], []

    def col_of(self, x):
        c = self.cols
        g, f, p, v, r = c.get("gender"), c.get("father"), c.get("party"), c.get("votes"), c.get("result")
        if g is not None and x < g - 2:
            return "name"
        if f is not None and p is not None and x < (f + p) / 2:
            return "father"
        if p is None and v is not None and x < v - 4:
            return "father"
        if v is not None and x < v - 4:
            return "party"
        if r is not None and x >= r - 12:
            return "result"
        return "numbers"


def head_fields(lines):
    """[(raw line chunks)] of one label group -> {"district"|"union"|"gp"|"ward": value, "reservation": text}."""
    fields = []          # [x, key, [texts]]
    for ch in lines:
        for x, t in ch:
            parts = list(LABEL.finditer(t))
            if not parts:
                if fields:   # a wrapped piece: the field whose label starts nearest to the left of it
                    left = [f for f in fields if f[0] <= x + 4] or fields
                    min(left, key=lambda f: abs(x - f[0]))[2].append(t)
                continue
            for k, m in enumerate(parts):
                end = parts[k + 1].start() if k + 1 < len(parts) else len(t)
                key = next(n for n, lab in LABELS if lab == m.group(1))
                fields.append([x + m.start(), key, [t[m.end():end].strip()]])
    out = {}
    for _, key, texts in fields:
        v = " ".join(x for x in texts if x).strip()
        m = re.search(r"\[(.*?)\]?\s*$", v) if "[" in v else None
        if m:
            out["reservation"] = m.group(1).strip()
            v = v[:m.start()].strip()
        out[key] = v
    return out


def update(ctx, f):
    """Labels change the context; a changed higher label clears the lower ones."""
    for key in ORDER:
        if key in f and f[key] != ctx.get(key):
            for low in ORDER[ORDER.index(key) + 1:]:
                ctx.pop(low, None)
            ctx[key] = f[key]
    if "reservation" in f:
        ctx["reservation"] = f["reservation"]
    elif any(k in f for k in ("gp", "ward")):
        ctx.pop("reservation", None)


def parse_text(raw):
    """pdftotext -layout output (pages split by form feed) -> [contest dict] (tn_text.ward_of + "ctx")."""
    blocks, cur, ctx, head = [], None, {}, None
    for page_no, page in enumerate(raw.split("\f"), 1):
        for i, rl in enumerate(page.splitlines()):
            line = convert(rl)
            if not line.strip():
                provenance.skipped("empty")
                continue
            if re.fullmatch(r"\s*(page\s*)?\d+\s*(/\s*\d+)?\s*", line, re.I):
                provenance.skipped('skip: re.fullmatch(r"\\s*(page\\s*)?\\d+\\s*(/\\s*\\d+)?\\s*", line, re.I)')
                continue      # page numbers
            ch = chunks(rl)
            if LABEL.search(line):
                head = (head or []) + [ch]
                continue
            if "வாக்காளர்கள்" in line and "வாக்குகள்" in line:
                update(ctx, head_fields(head or []))
                head = None
                cur = Block(ctx, page_no)
                cur.totals = totals(line)
                blocks.append(cur)
                continue
            if "தேர்தல்" in line and not NUM.match(ch[0][1]):
                provenance.skipped('skip: "தேர்தல்" in line and not NUM.match(ch[0][1])')
                continue      # page titles
            if any("பாலினம்" in t or t.startswith(("தந்தை", "பெற்ற", "சதவீதம்", "முடிவு")) for _, t in ch):
                if cur is not None:
                    for x, t in ch:
                        if "பாலினம்" in t:
                            cur.cols["gender"] = x
                        if "தந்தை" in t:
                            cur.cols["father"] = x + t.index("தந்தை")
                        if t.startswith("கட்சி"):
                            cur.cols["party"] = x
                        if "பெற்ற" in t:
                            cur.cols["votes"] = x + t.index("பெற்ற")
                        if t.startswith("முடிவு"):
                            cur.cols["result"] = x
                continue
            if ch and ch[0][1].startswith(("வ.", "எண்.")):
                provenance.skipped('skip: ch and ch[0][1].startswith(("வ.", "எண்."))')
                continue
            r = row_of(ch)
            if head is not None and r is None:
                head.append(ch)           # a wrapped piece of a label line
                continue
            if head is not None:          # page caption over a contest that goes on from the page before
                update(ctx, head_fields(head))
                head = None
            if cur is None:
                provenance.skipped('skip: cur is None')
                continue
            if r:
                r["line"], r["page"], r["raw"] = (page_no, i), page_no, rl
                r["cells"] = {"name": [], "father": [], "party": [], "result": []}
                for x, t in r.pop("mid"):
                    col = cur.col_of(x)
                    r["cells"]["party" if col in ("party", "numbers", "result") else "father"].append(t)
                if r["result"]:
                    r["cells"]["result"].append(r["result"])
                cur.rows.append(r)
            else:
                cur.extra.append(((page_no, i), ch))
    out = []
    for b in blocks:
        w = ward_of(b, {})
        w["winners"] = [c for c in w["candidates"] if any(x in c["result"] for x in WON)] or \
            (w["candidates"] if len(w["candidates"]) == 1 else [])
        w["ctx"] = b.ctx
        out.append(w)
    return out


class Matcher:
    """LGD codes by Tamil names: district panchayat from the payload, union under it, village panchayat under the union."""

    def __init__(self):
        self.lgd = _pri.Lgd("TN")
        self.kids = {}
        for code, lev, name, local, parent in self.lgd.rows:
            self.kids.setdefault(parent, []).append((code, lev, name, local))

    def find(self, parent, level, tamil):
        k = tkey(tamil)
        if not k:
            return None
        kids = [r for r in self.kids.get(parent, []) if r[1] == level]
        c = [r for r in kids if tkey(r[3]) == k]
        if len(c) == 1:
            return c[0]
        if c:
            return None
        # spelling differs (அன்னிமங்கலம் / அண்ணிமங்கலம்): the one close name under the same parent (ratio >= 0.85, next best
        # at least 0.1 lower); "fuzzy" match, marked on the record
        sc = sorted(((difflib.SequenceMatcher(None, k, tkey(r[3])).ratio(), r) for r in kids), key=lambda x: -x[0])
        if sc and sc[0][0] >= 0.85 and (len(sc) == 1 or sc[0][0] - sc[1][0] >= 0.1):
            return sc[0][1] + ("fuzzy",)
        return None

    def anywhere(self, level, tamil, under=None):
        k = tkey(tamil)
        c = [r for r in self.lgd.rows if r[1] == level and tkey(r[3]) == k and (under is None or under in self.lgd.chain(r[0]))]
        return tuple(c[0][:4]) if len(c) == 1 else None

    def union(self, zp, tamil):
        return self.find(zp, "ps", tamil) or self.anywhere("ps", tamil)

    def gp(self, ps, zp, tamil):
        return (self.find(ps, "gp", tamil) if ps else None) or (self.anywhere("gp", tamil, under=zp) if zp else None)


_M = None


def matcher():
    global _M
    if _M is None:
        _M = Matcher()
    return _M


def records(contests, p):
    level, post = FILES[p["file"]]
    m = matcher()
    zp = p.get("zp_lgd") or ""
    recs, seen = [], {}
    for w in contests:
        cx = w["ctx"]
        ps = m.union(zp, cx.get("union")) if cx.get("union") else None
        gp = m.gp(ps[0] if ps else None, zp, cx.get("gp")) if cx.get("gp") else None
        if level == "zp":
            code, body, body_local = zp, f"{p.get('district')} District Panchayat", cx.get("district")
        elif level == "ps":
            code, body, body_local = (ps[0] if ps else ""), (ps[2] if ps else cx.get("union")), cx.get("union")
        else:
            code, body, body_local = (gp[0] if gp else ""), (gp[2] if gp else cx.get("gp")), cx.get("gp")
        head = p["file"] == "vpp"
        for k, c in enumerate(w["winners"]):
            d = {"lgd_code": code, "body": body, "body_local": body_local, "district": p.get("district"),
                 "district_local": cx.get("district"), "block": ps[2] if ps else cx.get("union"), "block_local": cx.get("union"),
                 "block_lgd": ps[0] if ps else "", "zp_lgd": zp, "post": post, "name": c["name"], "gender": c["gender"],
                 "father_or_husband": c["father_or_husband"], "party_local": c["party_local"],
                 "party": c["party"] if c["party_local"] else "", "votes": c["votes"], "vote_pct": c["vote_pct"],
                 "result": c["result"], "unopposed": "போட்டியின்றி" in c["result"], "reservation": w["reservation"],
                 **{x: w[x] for x in ("electors", "polled", "valid", "invalid", "poll_pct") if x in w},
                 "candidates": w["candidates"], "election": p.get("election"), "year": p.get("year"),
                 "bye_election": bool(p.get("bye_election")), "url": p.get("url"), "src_url": p.get("url"),
                 "file_kind": p["file"], "page": w["page"]}
            fuzzy = [x for x, r in (("block", ps), ("body", gp)) if r and len(r) > 4]
            if fuzzy:
                d["lgd_match"] = "fuzzy name: " + ", ".join(fuzzy)
            d["term_note"] = TERM.get(p.get("year"), "")
            if not head:
                d["ward_no"] = w["ward_no"]
            else:
                d["head"], d["head_rank"] = True, 1
            if k < len(w.get("winner_pos") or []):
                d["src_pos"] = w["winner_pos"][k]
            if p.get("_src"):
                d["src"] = dict(p["_src"])
                d.pop("src_url")
            bkey = code or "~".join(_pri.norm(x) or tkey(x) for x in (p.get("district") or "", cx.get("union") or "",
                                                                       cx.get("gp") or "" if level == "gp" else ""))
            pkey = _pri.post_key(head=head, ward_no=None if head else w["ward_no"])
            if p.get("bye_election"):
                pkey += f":{p.get('year')}-bye"
            rid, data = _pri.record("TN", level, body_key=bkey, pkey=pkey, **d)
            n = seen.get(rid, 0)
            seen[rid] = n + 1
            recs.append((rid if n == 0 else f"{rid}:{n + 1}", data))
    return recs


def fetch(p, get):
    from cforms.tn import stored
    from cforms.tn_text import pdftotext
    if not pdftotext():
        return [], [], "pdftotext not available"
    content, files, src = stored(p, get), [], None
    if content is not None:
        src = provenance.file_src(content, p.get("url"), p.get("stored"))
    else:
        r = get(p["url"])
        if r is None or r.content[:5] != b"%PDF-":
            return [], [], "no answer"
        content = r.content
        files = [(f"pri/TN/{p.get('year')}/{p['url'].rsplit('/', 1)[-1]}", content, "application/pdf")]
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "r.pdf")
        with open(pdf, "wb") as f:
            f.write(content)
        raw = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    contests = parse_text(raw)
    recs = records(contests, dict(p, _src=src) if src else p)
    if recs:
        return recs, files, ""
    return [], files, f"no winners read ({len(contests)} contests)"


def links(html):
    """PDF names of one district results page (window.open('<name>.pdf'))."""
    return list(dict.fromkeys(re.findall(r"window\.open\('([a-z0-9_]+\.pdf)'", html or "")))


def item(year, code, name):
    kind = name.split("_", 1)[0]
    if kind not in FILES:
        return None
    lgd = _pri.Lgd("TN")
    dist = DISTRICTS.get(code, code)
    bye = year == "2021" and code not in NEW_2021
    union = name[:-4].split("_", 2)[2] if kind == "vpwm" and name.count("_") >= 2 else None
    key = f"pri_tn:{year}:{name[:-4]}"
    return {"key": key, "payload": {
        "kind": "form-pri_tn", "state": "TN", "url": BASE.format(year=year) + name, "file": kind, "level": FILES[kind][0],
        "year": year, "district_code": code, "district": dist, "zp_lgd": lgd.match("zp", dist), "union_code": union,
        "election": (f"Tamil Nadu rural local bodies {year}" + (" (casual election)" if bye else "")),
        "bye_election": bye, "route": "proxy", "india_only": True}}


def items(get):
    """Every PDF of every district page of 2019 and 2021 (POST cmb_district=<code>): one queue item each."""
    out = []
    for year in ("2019", "2021"):
        page = BASE.format(year=year) + f"rlbe{year}.php"
        for code in DISTRICTS:
            r = get(page, method="POST", data={"cmb_district": code})
            if r is None:
                continue
            for name in links(r.text):
                it = item(year, code, name)
                if it:
                    out.append(it)
    return out


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:12]
