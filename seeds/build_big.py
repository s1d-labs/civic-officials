"""Big-city officer pages found by the targeted search (seeds/raw/search/out_big_*.csv): HTML pages that answered from India go to
big_sites.csv (the whoswho task reads the start page itself); PDF and JSON lists go to directories.json. Every item keeps the LGD code."""
import csv
import glob
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).parent
OUT = HERE.parent / "big_sites.csv"
DIRS = HERE.parent / "directories.json"
FAR = HERE.parent / "directories_abroad.json"


def main():
    sites, pdfs, far, seen = [], [], [], set()
    for f in sorted(glob.glob(str(HERE / "raw/search/out_big_*.csv"))):
        for r in csv.DictReader(open(f, newline="", encoding="utf-8")):
            url, fmt, ok = (r.get("url") or "").strip(), (r.get("fmt") or "").strip().lower(), (r.get("verified") or "").strip()
            abroad = "mcdonline.nic.in" in url and ok.startswith("000")     # MCD's portal times out from India, answers from abroad
            if not url.startswith("http") or not (ok.startswith(("200", "406")) or abroad) or fmt == "js" or url in seen:
                continue
            if abroad:
                seen.add(url)
                far.append({"key": "big-" + hashlib.sha1(url.encode()).hexdigest()[:12],
                            "payload": {"url": url, "method": "GET", "data": None, "fmt": fmt if fmt in ("json", "pdf") else "html",
                                        "state": "DL", "source": r["city"], "label": f"{r['city']}: {r.get('what', '')}",
                                        "lgd_code": r["local_body_code"]}})
                continue
            seen.add(url)
            if fmt in ("pdf", "json"):
                pdfs.append({"key": "big-" + hashlib.sha1(url.encode()).hexdigest()[:12],
                             "payload": {"url": url, "method": "GET", "data": None, "fmt": fmt, "state": "", "source": r["city"],
                                         "label": f"{r['city']}: {r.get('what', '')}", "lgd_code": r["local_body_code"]}})
            else:
                u = urlsplit(url)
                sites.append({"domain": (u.netloc + u.path + ("?" + u.query if u.query else "")).rstrip("/").lower(), "url": url,
                              "name": r["city"], "kind": "Urban local body (big city)", "state_code": "", "jurisdiction": "",
                              "lgd_code": r["local_body_code"], "read_start": "1"})
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["domain", "url", "name", "kind", "state_code", "jurisdiction", "lgd_code", "read_start"])
        w.writeheader()
        w.writerows(sites)
    d = json.loads(DIRS.read_text())
    have = {i["key"] for i in d}
    new = [x for x in pdfs if x["key"] not in have]
    DIRS.write_text(json.dumps(d + new, indent=1, ensure_ascii=False))
    FAR.write_text(json.dumps(far, indent=1, ensure_ascii=False))
    print(len(sites), "pages;", len(new), "new PDF/JSON lists;", len(far), "sources that answer only from abroad")


if __name__ == "__main__":
    main()
