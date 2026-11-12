"""Sikkim: ward councillors of the 9 urban bodies elected in the General Municipal Elections 2026 (poll 24.04.2026, count
25.04.2026), from the Urban Development Department notifications under Rule 118 of the Sikkim Municipalities (Conduct of
Election) Rules 2007, printed in the Sikkim Government Gazette Extraordinary:
- No. 236 (07/UDD/2026, 25.04.2026): candidates elected uncontested, 62 wards in 9 bodies;
- No. 237 (08/UDD/2026, 25.04.2026): the one contested ward (Gangtok ward 10, Diesel Power House).
Files: sikkim.gov.in/uploads//Notifications/Gazette_Num_<no>_74_20260502.pdf (listed at sikkim.gov.in/media/notifications,
department 74 = Urban Development). PageMaker text layer, read with pdftotext -layout. The files answer outside India.

Each table line is "<ward no>  <ward name>  <NAME>"; the body name stands in the left column, broken over the lines of its
block ("Gangtok / Municipal / Corporation"). A new body starts where the ward number falls back. The mayor / chairperson and
deputies are chosen later by the councillors; the gazette does not name them (not read here).
One queue item = one gazette. Record id councillor:SK:<LGD code>:<ward no>.
"""
import re
import subprocess
import tempfile

METHOD = "pdf text (pdftotext -layout)"
ELECTION = "Sikkim General Municipal Elections 2026 (poll 24.04.2026, count 25.04.2026)"
GAZETTES = {
    236: ("https://sikkim.gov.in/uploads//Notifications/Gazette_Num_236_74_20260502.pdf",
          "Sikkim Government Gazette Extraordinary No. 236 of 25.04.2026, notification 07/UDD/2026 (elected uncontested)", True),
    237: ("https://sikkim.gov.in/uploads//Notifications/Gazette_Num_237_74_20260502.pdf",
          "Sikkim Government Gazette Extraordinary No. 237 of 25.04.2026, notification 08/UDD/2026 (contested ward)", False),
}
# first word of the body column -> (LGD code, body name)
BODIES = {"gangtok": ("249694", "Gangtok Municipal Corporation"), "namchi": ("249692", "Namchi Municipal Council"),
          "rangpo": ("290460", "Rangpo Nagar Panchayat"), "singtam": ("249695", "Singtam Nagar Panchayat"),
          "mangan": ("249689", "Mangan Nagar Panchayat"), "gyalshing": ("249690", "Gyalshing Nagar Panchayat"),
          "nayabazaar": ("249693", "Nayabazar Jorethang Nagar Panchayat"), "nayabazar": ("249693", "Nayabazar Jorethang Nagar Panchayat"),
          "soreng": ("306274", "Soreng Nagar Panchayat"), "pakyong": ("306273", "Pakyong Nagar Panchayat")}
ROW = re.compile(r"^(?P<left>.*?)\s(?P<ward>\d{1,2})\s{2,}(?P<wname>\S.*?)\s{2,}(?P<name>[A-Z][A-Z .'()-]*[A-Z.)])\s*$")
HEADLINE = re.compile(r"Name of|Municipality|elected|Ward\s+Name|^\s*No\.", re.I)


def lines(text):
    """pdftotext -layout text -> [(page, line no in page, line)]."""
    out = []
    for pi, page in enumerate(text.split("\f"), 1):
        for li, ln in enumerate(page.splitlines(), 1):
            out.append((pi, li, ln))
    return out


def parse(text, p):
    rows, frags = [], []                         # rows: (index, page, line, raw, match); frags: (index, text)
    started = False
    for i, (pg, li, ln) in enumerate(lines(text)):
        if re.search(r"Name of\s+Ward|Name of\s*$", ln):
            started = True
            continue
        if not started or not ln.strip() or re.search(r"By Order|S\.G\.P\.G|^\s*-\d+-\s*$", ln):
            if re.search(r"By Order", ln):
                started = False
            continue
        m = ROW.match(ln)
        if m:
            rows.append((i, pg, li, ln, m))
            if m.group("left").strip():
                frags.append((i, m.group("left").strip()))
        elif not HEADLINE.search(ln) and re.fullmatch(r"\s*[A-Za-z][A-Za-z .]*", ln):
            frags.append((i, ln.strip()))
    blocks, last = [], None
    for r in rows:
        w = int(r[4].group("ward"))
        if last is None or w <= last:
            blocks.append([])
        blocks[-1].append(r)
        last = w
    recs = []
    for bi, b in enumerate(blocks):
        start = b[0][0] if bi else -1
        end = blocks[bi + 1][0][0] if bi + 1 < len(blocks) else 10 ** 9
        words = [t for i, t in frags if start <= i < end]
        body_text = " ".join(words)
        key = next((k for k in BODIES if re.search(rf"\b{k}", body_text, re.I)), None)
        code, body = BODIES[key] if key else (None, body_text or None)
        for i, pg, li, ln, m in b:
            ward = str(int(m.group("ward")))
            d = {"type": "councillor", "state": "SK", "body": body, "lgd_code": code, "body_local": body_text or None,
                 "ward_no": ward, "ward_name": m.group("wname").strip(), "name": " ".join(m.group("name").split()),
                 "position": "Councillor", "unopposed": True if p.get("uncontested") else None,
                 "election": ELECTION, "source": p.get("label"), "url": p["url"],
                 "src_pos": {"page": pg, "line": li, "line_text": ln.rstrip()}}
            recs.append((f"councillor:SK:{code or re.sub(r'[^a-z0-9]+', '-', (body or '').lower())}:{ward}",
                         {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    if not r.content.startswith(b"%PDF"):
        return [], [], "not a PDF"
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content)
        f.flush()
        text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
    no = p.get("gazette")
    files = [(f"councillors/SK/gazette-{no}.pdf", r.content, "application/pdf")]
    recs = parse(text, p)
    return recs, files, "" if recs else "no members read"


def seed_items():
    return [{"key": f"ce-sk-2026-gazette-{no}",
             "payload": {"kind": "form-ce_sk", "state": "SK", "url": url, "gazette": no, "label": label, "uncontested": unc,
                         "election": ELECTION}} for no, (url, label, unc) in GAZETTES.items()]
