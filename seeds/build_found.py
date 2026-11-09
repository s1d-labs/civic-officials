"""Build found_sites.csv from the search agents' results (seeds/raw/search/out_g*.csv): bodies whose site or officials page answered
from India (HTTP 200). The start address is the officials page when there is one, else the site. Each row keeps its LGD code.
Rajasthan's lsg.rajasthan.gov.in/<vdir> shell answers 200 for any address (an Angular app): those rows are left out here."""
import csv
import glob
import re
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).parent
OUT = HERE.parent / "found_sites.csv"


def ok(code_text, which):
    m = re.search(rf"{which}:(\d+)", code_text or "")
    return bool(m and m.group(1) == "200")


def main():
    out, seen = [], set()
    for f in sorted(glob.glob(str(HERE / "raw/search/out_g*.csv"))):
        group = Path(f).stem.removeprefix("out_")
        for r in csv.DictReader(open(f, newline="", encoding="utf-8")):
            v = r.get("verified_from_india", "")
            if "(sh" in v or "lsg.rajasthan.gov.in" in (r.get("website") or ""):
                continue
            start, read_start = "", False
            if r.get("officials_url") and ok(v, "offi"):
                start, read_start = r["officials_url"], True
            elif r.get("website") and ok(v, "webs"):
                start = r["website"]
            if not start or not start.startswith("http"):
                continue
            u = urlsplit(start)
            key = (u.netloc + u.path).rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"domain": key, "url": start, "name": r["name"], "kind": "Urban local body (search)", "state_code": group,
                        "jurisdiction": "", "lgd_code": r["local_body_code"], "read_start": "1" if read_start else ""})
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["domain", "url", "name", "kind", "state_code", "jurisdiction", "lgd_code", "read_start"])
        w.writeheader()
        w.writerows(out)
    print(len(out), "sites;", sum(1 for x in out if x["read_start"]), "start at an officials page")


if __name__ == "__main__":
    main()
