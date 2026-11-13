"""Build seeds/dept_pri_hr.json from the Haryana SEC index PDF "Result sheet for Elected Members of Zila Parishads and Members
Panchayat Samitis and Elected Sarpanches and Panches for PRI General Elections - 2022" (notification of 02.12.2022 on
https://secharyana.gov.in/orders-notifications-related-to-panchayat-elections-2021/). The PDF links one gazette PDF per district
(Members ZP, Members PS) and per block (Sarpanch and Panches). Local tool (needs pymupdf, not a runner dependency):
  python seeds/build_pri_hr.py INDEX.pdf > seeds/dept_pri_hr.json"""
import json
import re
import sys

import pymupdf

FULL = {"Charkhi": "Charkhi Dadri", "M/garh": "Mahendragarh"}     # the index wraps / shortens these
INDEX = "https://cdnbbsr.s3waas.gov.in/s31c6a0198177bfcc9bd93f6aab94aad3c/uploads/2022/12/2022121338.pdf"


def main(path):
    d = pymupdf.open(path)
    out, district = [], None
    for p in d:
        words = p.get_text("words")
        for ln in p.get_links():
            if not ln.get("uri"):
                continue
            r = ln["from"]
            label = " ".join(p.get_textbox(r).split())
            mid = (r.y0 + r.y1) / 2
            if re.search(r"(?i)member", label) and "ZP" in label:
                row = [w for w in words if abs((w[1] + w[3]) / 2 - mid) < 6 and 60 < w[0] < 200]
                district = " ".join(w[4] for w in sorted(row, key=lambda w: w[0]))
                district = FULL.get(re.sub(r"^\d+\.?\s*", "", district), re.sub(r"^\d+\.?\s*", "", district))
            if "ZP" in label:
                kind, block = "zp", ""
            elif "PS" in label:
                kind, block = "ps", ""
            else:
                kind, block = "gp", label
            sl = re.sub(r"[^a-z0-9]+", "-", f"{district} {block or kind}".lower()).strip("-")
            out.append({"key": f"pri_hr:{sl}", "payload": {
                "reader": "pri_hr", "url": ln["uri"], "kind": kind, "state": "HR", "district": district, "block": block,
                "index_pdf": INDEX, "route": "abroad"}})
    keys = [o["key"] for o in out]
    for o in out:
        if keys.count(o["key"]) > 1:
            o["key"] += "-" + re.sub(r"\W", "", o["payload"]["url"].rsplit("/", 1)[-1].split(".")[0])
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
