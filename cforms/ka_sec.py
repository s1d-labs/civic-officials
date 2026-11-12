"""Karnataka State Election Commission (karsec.karnataka.gov.in): which urban local bodies elected their council in which round
since 2021, from the SEC's press notes. The SEC publishes no ward-wise winner names (its Results / Elected grids and press notes
give party-wise totals per body), and the notes are scans without a text layer. So the body rows of each note were read by eye
from the rendered pages and are carried in the seed payload (seeds/build_ka_sec.py), with their page and row; this reader
fetches the note (the source trail copies it), checks that it is the same file the rows were read from (sha256) and has the
pages named, and gives one record per body. No OCR.
One queue item = one press note: payload {"kind": "form-ka_sec", "state": "KA", "url", "round", "election", "poll_date",
"result_date", "doc", "sha256", "pages", "rows": [{"page", "row", "body", "body_kn", "body_type", "district", "lgd_code", "wards"}]}.
Record id body_election:KA:<round>:<LGD code, else body slug>, type "body_election": the council of that body was elected in
that round; members are not named. Term: five years from the council's first meeting (Karnataka Municipalities Act 1964 s.18,
KMC Act 1976 s.8; the Karnataka High Court held in Pavankumar v. State of Karnataka, 2026, that the five years run from the first
meeting without pause), so it ends no earlier than five years after the poll / result date ("term_ends_not_before").
India only? The SEC site answers dev-vps-3 (Mumbai); not tested from abroad."""
import io
import re

import provenance

METHOD = "scanned SEC press note: body rows read by eye from the rendered page (page + row in the seed), file checked by sha256"

NOTE = "council elected in this round; the SEC file gives party-wise totals only, not the members' names"
TERM = "five years from the council's first meeting (KM Act 1964 s.18 / KMC Act 1976 s.8)"


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def plus5(d):
    """'2021-12-30' -> '2026-12-30'; None for a missing or odd date."""
    if not d or not re.fullmatch(r"\d{4}-\d\d-\d\d", d):
        return None
    y, rest = d[:4], d[4:]
    return f"{int(y) + 5}{rest}" if rest != "-02-29" else f"{int(y) + 5}-02-28"


def pages_of(content):
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:
        return None


def records(p, r):
    """Records of one press note from its payload rows; r = the response (source trail)."""
    out = []
    end = plus5(p.get("result_date") or p.get("poll_date"))
    for row in p["rows"]:
        key = row.get("lgd_code") or slug(row["body"])
        rec = {"type": "body_election", "state": "KA", "body": row["body"], "body_local": row.get("body_kn"), "body_type": row.get("body_type"),
               "district": row.get("district"), "lgd_code": row.get("lgd_code"), "election": p["election"], "round": p["round"],
               "poll_date": p.get("poll_date"), "result_date": p.get("result_date"), "wards": row.get("wards"),
               "term": TERM, "term_ends_not_before": end, "note": NOTE, "doc": p.get("doc"), "url": p["url"],
               **provenance.at(r, p["url"]), "src_pos": {"page": row["page"], "row": row["row"], "read": "by eye from the rendered scan"},
               "method": METHOD}
        out.append((f"body_election:KA:{p['round']}:{key}", {k: v for k, v in rec.items() if v not in (None, "")}))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "press note did not answer"
    body = r.content or b""
    if not body.startswith(b"%PDF"):
        return [], [], "not a PDF"
    files = [(f"councillors/KA/sec/{p['round']}.pdf", body, "application/pdf")]
    sha = provenance.at(r, p["url"]).get("src_sha256")
    if p.get("sha256") and sha != p["sha256"]:
        # the rows were read from another file: do not put them on this one
        return [], files, f"file changed (sha256 {sha[:12]}, rows read from {p['sha256'][:12]}): read the rows again"
    n = pages_of(body)
    if n is not None and n < max(row["page"] for row in p["rows"]):
        return [], files, f"file has {n} pages, rows name page {max(row['page'] for row in p['rows'])}"
    return records(p, r), files, ""
