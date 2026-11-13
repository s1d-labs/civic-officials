"""Bank branches of India with IFSC, address, phone and district: the public IFSC list of github.com/razorpay/ifsc (release
asset IFSC.csv, MIT licence, built from RBI's "List of NEFT enabled bank branches" (rbi.org.in Scripts/bs_viewcontent.aspx?Id=2009,
235 bank xlsx files on rbidocs.rbi.org.in, updated monthly) and the NPCI lists). Columns: BANK, IFSC, BRANCH, CENTRE, DISTRICT,
STATE, ADDRESS, CONTACT, IMPS, RTGS, CITY, ISO3166, NEFT, MICR, UPI, SWIFT.

Why not the RBI files directly: rbidocs.rbi.org.in gave an empty reply to plain clients from Germany and from India (2026-11-11,
3 requests); the reader would need faked browser headers. The CSV carries the same rows plus the district.

One queue item = one state or UT: fetch() reads the whole CSV (about 40 MB; it is kept in the bucket once per item) and keeps
the rows of payload "state". Payload: url, state (two-letter code). One record per branch: dept "banking", level "facility",
area = branch, post "Branch Manager" (the list gives the branch phone, no officer names), bank, ifsc, micr, swift, centre, city,
district, address, phone. Record id dept:central_banking:<IFSC>. Seed: seeds/dept_central_banking.json.
"""
import csv
import io
import json
from pathlib import Path

from dforms import _civic, _esw
import provenance

METHOD = "csv file (RBI IFSC list)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "central_banking"
ISO = {"IN-AN": "AN", "IN-AP": "AP", "IN-AR": "AR", "IN-AS": "AS", "IN-BR": "BR", "IN-CH": "CH", "IN-CT": "CG", "IN-CG": "CG",
       "IN-DN": "DH", "IN-DD": "DH", "IN-DH": "DH", "IN-DL": "DL", "IN-GA": "GA", "IN-GJ": "GJ", "IN-HR": "HR", "IN-HP": "HP",
       "IN-JK": "JK", "IN-JH": "JH", "IN-KA": "KA", "IN-KL": "KL", "IN-LA": "LA", "IN-LD": "LD", "IN-MP": "MP", "IN-MH": "MH",
       "IN-MN": "MN", "IN-ML": "ML", "IN-MZ": "MZ", "IN-NL": "NL", "IN-OR": "OD", "IN-OD": "OD", "IN-PY": "PY", "IN-PB": "PB",
       "IN-RJ": "RJ", "IN-SK": "SK", "IN-TN": "TN", "IN-TG": "TG", "IN-TS": "TG", "IN-TR": "TR", "IN-UP": "UP", "IN-UT": "UK",
       "IN-UK": "UK", "IN-WB": "WB"}


def items(get=None):
    return json.loads((Path(__file__).resolve().parent.parent / "seeds" / f"dept_{MODULE}.json").read_text())


def state_of(row):
    """Two-letter code from ISO3166 ('IN-GJ'), else from the STATE name."""
    return ISO.get((row.get("ISO3166") or "").strip().upper()) or _civic.state_code(row.get("STATE"))


def phone(v):
    """'+912612536772' as written; the list writes '0' or 'NA' when it has no number."""
    v = _esw.clean(v)
    return v if sum(c.isdigit() for c in v) >= 6 else None


def records(text, p, url):
    out = []
    dr = csv.DictReader(io.StringIO(text))
    for n, row in enumerate(dr, 1):
        if state_of(row) != p["state"]:
            provenance.filtered("other state")
            continue
        ifsc = _esw.clean(row.get("IFSC")).upper()
        if len(ifsc) != 11:
            provenance.skipped("no 11-character IFSC")
            continue
        out.append(_esw.record(
            MODULE, ifsc, dept="banking", level="facility", area=row.get("BRANCH"), post="Branch Manager",
            bank=row.get("BANK") or None, bank_code=ifsc[:4], ifsc=ifsc, micr=row.get("MICR") or None,
            swift=row.get("SWIFT") or None, centre=row.get("CENTRE"), city=row.get("CITY"), district=row.get("DISTRICT"),
            address=row.get("ADDRESS"), phone=phone(row.get("CONTACT")), state=p["state"], office_id=ifsc,
            source=url, last_updated=p.get("last_updated"),
            src_pos={"row": n, "line": dr.line_num}))     # row: data row (header not counted); line: file line where it ends
    return out


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    raw = r.content
    text = raw.decode("utf-8-sig", "replace")
    if not text.startswith("BANK,IFSC"):
        return [], [_esw.keep(MODULE, f"{p['state']}-bad", raw, "csv")], "not the IFSC CSV"
    recs = records(text, p, url)
    buf = io.StringIO()
    rd = csv.reader(io.StringIO(text))
    head = next(rd)
    w = csv.writer(buf)
    w.writerow(head)
    for row in rd:
        if state_of(dict(zip(head, row))) == p["state"]:
            w.writerow(row)
    files = [_esw.keep(MODULE, f"IFSC-{p['state']}", buf.getvalue(), "csv")]
    return recs, files, "" if recs else "no rows for the state"
