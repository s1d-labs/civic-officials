"""Madhya Pradesh gap round (2026-11-14): ward councillors of towns that the Gazette OCR reader (cforms/cw_mp.py) did not reach,
from the towns' own files.

- "ratlam": Ratlam Municipal Corporation, "-जनप्रतिनिधियों की सूची-" (rmcratlam.in/assets/uploads/Janpratinidhi_List.pdf,
  Microsoft Word 2010, 27.01.2023, 3 pages; copy in archive.s1d.me 2026-11-06). Text layer in Kruti Dev 010 (cforms/cn_krutidev.py).
  Columns: serial | ward | name | post (महापौर, अध्यक्ष, पार्षद) | mobile (one to three numbers, one per line) | address. A long name or
  address wraps onto the next lines; "MIC Member" (member of the Mayor-in-Council) stands under the name in Latin letters.
  The file lists the mayor, the council chair (अध्यक्ष, no ward) and 48 ward councillors (wards 1-49 except 12) = 50 rows.
Payload: {"kind": "form-cgap_mp", "state": "MP", "layout", "url", "body", "lgd_code", "district", "election"}.
Record id councillor:MP:<lgd code>:<ward no | "mayor" | "chair">.
"""
import gzip
import re
import subprocess
import tempfile

import provenance
from cforms.cn_krutidev import convert

METHOD = "pdf text (pdftotext -layout) + Kruti Dev map"

ROW = re.compile(r"^\s*(?P<sl>\d{1,2})\s+(?:(?P<ward>\d{1,2})\s+)?(?P<name>\S.*?)\s{2,}(?P<post>ek0|ik\"kZn)\s+(?P<phone>\d{10})\s*(?P<addr>.*)$")
POSTS = {"egkikSj": ("Mayor", "mayor"), "v/;{k": ("Chairperson", "chair")}     # second line of "ek0" (मा0 = honourable)
PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")


def pdf_lines(body):
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(body)
        f.flush()
        out = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=120)
    return [(pg, ln, t) for pg, page in enumerate(out.stdout.decode("utf-8", "replace").split("\f"), 1)
            for ln, t in enumerate(page.splitlines(), 1)]


def ratlam_rows(lines):
    """Rows of the Ratlam list (lines: [(page, line, text)] of pdf_lines): dicts {sl, ward, name, post, phones, address, mic,
    _pos}; raw Kruti Dev text per cell, converted at the end (the column positions hold in the raw text only)."""
    rows, cur = [], None
    for page, ln, raw in lines:
        m = ROW.match(raw)
        if m:
            cur = {"sl": m["sl"], "ward": m["ward"], "name": [m["name"]], "post": [m["post"]], "phones": [m["phone"]],
                   "address": [m["addr"]] if m["addr"].strip() else [], "mic": False,
                   "_pos": provenance.line_pos(page, ln, raw), "_cut": raw.index(m["phone"])}
            rows.append(cur)
            continue
        if cur is None or not raw.strip():
            if not raw.strip():
                provenance.skipped("empty")
            else:
                provenance.skipped("header")
            continue
        if "MIC Member" in raw:
            cur["mic"] = True
            raw = raw.replace("MIC Member", " " * 10)
        for ph in PHONE.finditer(raw):
            cur["phones"].append(ph.group(0))
        raw = PHONE.sub(lambda m: " " * len(m.group(0)), raw)     # a shifted phone column must not cut into the name
        left, right = raw[:cur["_cut"]], raw[cur["_cut"] + 10:]
        for chunk in re.split(r"\s{2,}", left.strip()):
            if not chunk:
                continue
            if chunk in POSTS:
                cur["post"].append(chunk)
            else:
                cur["name"].append(chunk)
        if right.strip():
            cur["address"].append(right.strip())
        provenance.skipped("text line")      # a wrapped line of the row above (not data on its own)
    out = []
    for r in rows:
        name = convert(" ".join(" ".join(r["name"]).split()))
        name = re.sub(r"^(मा0\s*)", "", name).replace("¼", "(").replace("½", ")")
        post = next((POSTS[p] for p in r["post"] if p in POSTS), None)
        out.append({"sl": r["sl"], "ward": r["ward"], "name": " ".join(name.split()), "post": post, "phones": r["phones"],
                    "address": convert(" ".join(" ".join(r["address"]).split())).replace("]", ","), "mic": r["mic"],
                    "_pos": r["_pos"]})
    return out


def records(rows, p, r=None):
    recs = []
    for x in rows:
        post = x["post"]
        if x["ward"]:
            ward, position = str(int(x["ward"])), None
        elif post:
            ward, position = post[1], post[0]
        else:
            provenance.skipped("no ward and no post")
            continue
        d = {"type": "councillor", "state": "MP", "body": p["body"], "body_type": "Municipal Corporation", "district": p.get("district"),
             "lgd_code": p.get("lgd_code"), "ward_no": ward if x["ward"] else None, "name": x["name"], "position": position,
             "phone": ", ".join(x["phones"]), "address": x["address"], "mic_member": True if x["mic"] else None,
             "election": p.get("election"), "url": p["url"], "src_pos": x["_pos"], **(provenance.at(r, p["url"]) if r is not None else {})}
        provenance.used()
        recs.append((f"councillor:MP:{p['lgd_code']}:{ward}", {k: v for k, v in d.items() if v not in (None, "")}))
    return recs


def fetch(p, get):
    if p.get("layout") != "ratlam":
        return [], [], f"unknown layout {p.get('layout')}"
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    files = [(f"councillors/MP/{p['lgd_code']}-janpratinidhi.pdf.gz", gzip.compress(r.content), "application/gzip")]
    recs = records(ratlam_rows(pdf_lines(r.content)), p, r)
    return recs, files, "" if recs else "no member rows"
