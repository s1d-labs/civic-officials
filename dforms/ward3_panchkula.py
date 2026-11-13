"""Municipal Corporation Panchkula (mcpanchkula.in): the sanitation staff of every ward, from the PDF "Details of ASI, Safai Daroga
and Supervisors" (/PDF/Sanitation.pdf, linked from the site; 1 page, 37 rows, 20 wards; in archive.s1d.me, saved by the pool
(abroad) on 2026-11-06; on 2026-11-13 the live site answered HTTP 999 to curl from Mumbai: the archive copy is the source).
Table: Sr. No. | Ward No. | Sector/Area | Name of SD/Supervisor (Sh.) | Contact No | ASI (Sh.). The Ward and ASI cells are merged
over several rows, with the text in the middle of the merged cell, so a line reader cannot tell which rows a ward holds. This
reader takes the position of every text run (pypdf text visitor, PDF points), cuts the page into rows at the midpoints between
the serial numbers, and shares the rows out to the ward labels (and to the ASI labels) so that each label sits in the middle
of its rows (the split with the least squared distance; rows stay in order).
Records: one per row (level "ward", wards = [the ward], area_regional = the sectors): the Safai Daroga / supervisor with the
phone(s) of the row; one per ASI (Assistant Sanitary Inspector) block (level "ward", wards = the wards of the rows under him).
The sector text of a row is the Sector/Area runs nearest to its serial number: in wrapped cells (rows 27-28, "Sec-20 (Fathepur,
Anaj Mandi)" / "Sec-20 (Kundi, Anaj Mandi)") a line can go to the next row.
Route: the archive copy (archive-first) or abroad; the live host answered HTTP 999 to a plain curl from Mumbai (unchecked).
Record ids: dept:ward3_panchkula:<row n | asi-name>:<mobile>.
"""
import io
import re

from dforms import _esw, _ward

METHOD = "pdf text runs with positions (pypdf visitor), merged cells shared out by position"

MODULE = "ward3_panchkula"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Panchkula", "248489", "HR", "Panchkula"
URL = "https://mcpanchkula.in/PDF/Sanitation.pdf"
X_WARD, X_AREA, X_NAME, X_PHONE, X_ASI = 75, 105, 240, 390, 470   # column starts (PDF points), from the heading runs
MOB = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-sanitation", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def runs_of(content):
    """[[page, y, x, text]] of every non-blank text run of the PDF (y up from the page bottom)."""
    from pypdf import PdfReader
    out = []
    for pn, pg in enumerate(PdfReader(io.BytesIO(content)).pages, 1):
        def v(text, cm, tm, fd, fs, pn=pn):
            if text.strip():
                x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
                y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
                out.append([pn, round(y, 1), round(x, 1), text])
        pg.extract_text(visitor_text=v)
    return out


def share(row_y, labels):
    """Contiguous split of the rows (y top-down) among the labels (y top-down): [label index of each row]. Row bands end at the
    midpoints between rows; the cost of a block is (centre of its band - label y)^2; every label gets at least one row."""
    n, k = len(row_y), len(labels)
    if not n or not k or k > n:
        return [None] * n
    bounds = [row_y[0] + (row_y[0] - row_y[1]) / 2 if n > 1 else row_y[0] + 8]
    bounds += [(row_y[i] + row_y[i + 1]) / 2 for i in range(n - 1)]
    bounds += [row_y[-1] - (row_y[-2] - row_y[-1]) / 2 if n > 1 else row_y[-1] - 8]
    inf = float("inf")
    best = [[inf] * (n + 1) for _ in range(k + 1)]
    back = [[0] * (n + 1) for _ in range(k + 1)]
    best[0][0] = 0.0
    for j in range(1, k + 1):
        for e in range(j, n + 1):
            for s in range(j - 1, e):
                if best[j - 1][s] == inf:
                    continue
                c = best[j - 1][s] + ((bounds[s] + bounds[e]) / 2 - labels[j - 1]) ** 2
                if c < best[j][e]:
                    best[j][e], back[j][e] = c, s
    out, e = [None] * n, n
    for j in range(k, 0, -1):
        s = back[j][e]
        for i in range(s, e):
            out[i] = j - 1
        e = s
    return out


def parse(runs, p):
    rows, wards, asis = [], [], []
    for pn, y, x, t in runs:
        t2 = _esw.clean(t)
        if pn != 1 and not rows:
            continue
        m = re.fullmatch(r"(\d{1,3})(?:\s+(\d{1,3}))?", t2)
        if m and x < X_WARD:
            rows.append({"sr": m.group(1), "y": y, "x": x, "text": t, "page": pn, "area": [], "name": [], "phone": []})
            if m.group(2):
                wards.append((y, m.group(2)))
        elif m and x < X_AREA:
            wards.append((y, m.group(1)))
    rows.sort(key=lambda r: -r["y"])
    if len(rows) < 3:
        return []
    row_y = [r["y"] for r in rows]

    def nearest(y):
        return min(range(len(rows)), key=lambda i: abs(rows[i]["y"] - y))
    asi_runs = []
    for pn, y, x, t in runs:
        t2 = _esw.clean(t)
        if not t2 or y >= rows[0]["y"] + 20 or re.search(r"(?i)^(sr\.?|no\.?|ward|sector/area|name of sd/?|supervisor \(sh\.\)|"
                                                          r"contact no|asi \(sh\.\))$", t2):
            continue
        if X_AREA <= x < X_NAME:
            rows[nearest(y)]["area"].append((-y, t2))
        elif X_NAME <= x < X_PHONE:
            rows[nearest(y)]["name"].append((-y, t2))
        elif X_PHONE <= x < X_ASI:
            rows[nearest(y)]["phone"].append((-y, t2))
        elif x >= X_ASI:
            asi_runs.append((y, x, t2))
    wards.sort(key=lambda w: -w[0])
    w_of = share(row_y, [w[0] for w in wards])
    # ASI labels: a name run, then its mobile run(s) under it; the label sits between them
    asi_runs.sort(key=lambda a: -a[0])
    asi = []
    for y, x, t in asi_runs:
        if MOB.search(t) and asi and not asi[-1]["phone"]:
            asi[-1]["phone"] = MOB.search(t).group(0)
            asi[-1]["y2"] = y
        elif not MOB.search(t):
            if asi and not asi[-1]["phone"] and abs(asi[-1]["y"] - y) < 18:
                asi[-1]["name"] += " " + t            # "Ajay Kumar" / "Sood"
                asi[-1]["y_last"] = y
            else:
                asi.append({"name": t, "y": y, "y_last": y, "phone": "", "y2": None})
    a_of = share(row_y, [(a["y"] + (a["y2"] if a["y2"] is not None else a["y_last"])) / 2 for a in asi])
    seen, recs = set(), []
    for i, r in enumerate(rows):
        ward = wards[w_of[i]][1] if w_of[i] is not None else None
        name = " ".join(t for _, t in sorted(r["name"]))
        phones = MOB.findall(name) + [m for _, t in sorted(r["phone"]) for m in MOB.findall(t)]
        name = _esw.clean(MOB.sub(" ", name)).strip(" -")
        sd = "(SD)" in name
        name = _esw.clean(name.replace("(SD)", ""))
        area = _esw.clean(" ".join(t for _, t in sorted(r["area"])))
        if not (name or phones):
            continue
        a = asi[a_of[i]] if a_of[i] is not None else None
        recs.append(_ward.record(MODULE, f"row-{r['sr']}:{phones[0] if phones else _esw.slug(name)}", seen, body=BODY, lgd=LGD,
                                 state=STATE, district=DISTRICT, level="ward", area=f"Ward {ward}" if ward else BODY,
                                 area_regional=area or None, post="Safai Daroga" if sd else "Safai Daroga / Supervisor",
                                 name=name, phone=", ".join(phones), wards=[ward] if ward else None,
                                 wards_note=None if ward else "ward cell not found", wing="sanitation", role="staff",
                                 asi=a["name"] if a else None, source=p.get("url") or URL,
                                 src_pos={"page": r["page"], "row": int(r["sr"]), "y": r["y"], "x": r["x"], "text": r["text"],
                                          "note": "PDF points; ward from the merged Ward cell by position"}))
    for j, a in enumerate(asi):
        ws = sorted({wards[w_of[i]][1] for i in range(len(rows)) if a_of[i] == j and w_of[i] is not None}, key=int)
        recs.append(_ward.record(MODULE, f"asi-{_esw.slug(a['name'])}:{a['phone'] or j}", seen, body=BODY, lgd=LGD, state=STATE,
                                 district=DISTRICT, level="ward", area=("Ward " if len(ws) == 1 else "Wards ") + ", ".join(ws),
                                 post="Assistant Sanitary Inspector", name=a["name"], phone=a["phone"], wards=ws or None,
                                 wards_note=None if ws else "no rows", wing="sanitation", role="head",
                                 rows=[int(rows[i]["sr"]) for i in range(len(rows)) if a_of[i] == j],
                                 source=p.get("url") or URL,
                                 src_pos={"page": 1, "y": a["y"], "text": a["name"],
                                          "note": "PDF points; rows from the merged ASI cell by position"}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or not r.content.startswith(b"%PDF"):
        return [], [], "no answer" if r is None else "not a pdf"
    files = [_esw.keep(MODULE, "sanitation", r.content, "pdf")]
    try:
        runs = runs_of(r.content)
    except Exception as e:      # a broken PDF: say so
        return [], files, f"pdf not readable: {type(e).__name__}"
    recs = parse(runs, p)
    return recs, files, "" if recs else "no rows"
