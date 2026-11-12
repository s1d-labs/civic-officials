"""North-East councillor sources that cforms/city.py does not read. One queue item = one body (seeds/councillors_ce_mz.json).
Payload: {"kind": "form-ce_ne", "state", "source", "body", "body_en", "lgd_code", "district", "election", "url", "slug"};
fetch(p, get) dispatches on p["source"]:
- "amc-table": Aizawl Municipal Corporation, amcmizoram.com/page/list-of-councillors. One table "LIST OF ELECTED CORPORATORS":
  serial, photo, name, designation (Corporator / Executive Corporator / Mayor / Deputy Mayor), ward number in Roman numerals,
  party. The ward number is converted to an integer; the Roman form is kept in ward_roman.
Record id councillor:<XX>:<slug>:<ward no>. Every answer is kept in the bucket under councillors/<XX>/.
"""
import gzip
import re

from bs4 import BeautifulSoup

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(s):
    """'XIV' -> 14; None when s is not a Roman numeral."""
    s = (s or "").strip().upper().rstrip(".")
    if not s or not re.fullmatch(r"[IVXLC]+", s):
        return None
    total = 0
    for i, ch in enumerate(s):
        v = ROMAN[ch]
        total += -v if i + 1 < len(s) and ROMAN[s[i + 1]] > v else v
    return total


def cell(td):
    return " ".join(td.get_text(" ", strip=True).split())


def amc_rows(html, pos=None):
    """Rows of the corporators table: dicts with name, position, ward_no, ward_roman, party. pos: a list that gets each row's
    src_pos {"table", "row"} (source trail)."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for ti, table in enumerate(soup.find_all("table"), 1):
        head = None
        for ri, tr in enumerate(table.find_all("tr"), 1):
            tds = [cell(td) for td in tr.find_all(["td", "th"])]
            low = [t.lower() for t in tds]
            if head is None:
                if any("name" in t for t in low) and any("ward" in t for t in low):
                    head = {"name": next(i for i, t in enumerate(low) if "name" in t),
                            "ward": next(i for i, t in enumerate(low) if "ward" in t),
                            "post": next((i for i, t in enumerate(low) if "designation" in t), None),
                            "party": next((i for i, t in enumerate(low) if "party" in t), None)}
                continue
            if len(tds) <= max(v for v in head.values() if v is not None):
                continue
            name, ward = tds[head["name"]], tds[head["ward"]]
            n = roman(ward) or (int(ward) if ward.isdigit() else None)
            if not name or n is None:
                continue
            out.append({"name": name, "ward_no": str(n), "ward_roman": ward if roman(ward) else None,
                        "position": tds[head["post"]] if head["post"] is not None else None,
                        "party": tds[head["party"]] if head["party"] is not None else None})
            if pos is not None:
                pos.append({"table": ti, "row": ri})
        if out:
            break
    return out


def amc_table(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    st = p["state"]
    files = [(f"councillors/{st}/{p['slug']}.html.gz", gzip.compress(r.content), "application/gzip")]
    recs = []
    pos = []
    for d, sp in zip(amc_rows(r.text, pos), pos):
        d.update({"src_pos": sp, "type": "councillor", "state": st, "body": p["body"], "body_en": p.get("body_en") or p["body"],
                  "body_type": p.get("body_type"), "district": p.get("district"), "lgd_code": p.get("lgd_code"),
                  "election": p.get("election"), "url": p["url"]})
        recs.append((f"councillor:{st}:{p['slug']}:{d['ward_no']}", d))
    return recs, files, "" if recs else "no corporators table"


SOURCES = {"amc-table": amc_table}


def fetch(p, get):
    return SOURCES[p["source"]](p, get)
