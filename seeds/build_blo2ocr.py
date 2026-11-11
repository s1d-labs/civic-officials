"""Make seeds/blo2ocr.json: the BLO list PDFs that forms/blo2_ocr.py reads by OCR (project civic-officials-blo2-ocr).

The items come from the blo2 seeds (same key, same payload) with kind "form-blo2_ocr" and "stored" = where the first fetch
saved the PDF: civic-officials-blo2/blo2/<state>/<sha1(url)[:12]>.pdf (forms/blo2_pdf.py) or, for the Manipur kind "pdf"
items, civic-officials-blo2-in/blo/MN/<sha1(payload)[:16]>.pdf (blo.py). The OCR task also looks in its own project and
fetches the file once when no copy is saved.
KEYS: the files measured or checked on 2026-11-11 (see the list below). Files that are not BLO lists or that have no part
numbers are left out (NOT_BLO).
Run: python seeds/build_blo2ocr.py
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent

KEYS = [
    # Uttar Pradesh, Farrukhabad: scans (no text layer), Hindi; measured on blo2-up-farrukhabad-a881b1c2c0
    "blo2-up-farrukhabad-a881b1c2c0", "blo2-up-farrukhabad-0f76ba2308", "blo2-up-farrukhabad-2b1cbdc9d8",
    "blo2-up-farrukhabad-e9f30e7369",
    # Bihar, Rohtas: Kruti Dev text layer that pypdf cannot lay out (drawn pages, OCR reads them well)
    "blo2-br-rohtas-b9b2567f0a", "blo2-br-rohtas-8cee7b9727", "blo2-br-rohtas-fad3b6d8ad", "blo2-br-rohtas-062e297c0d",
    # Uttar Pradesh, Hardoi: Type 3 fonts (garbled text layer), English
    "blo2-up-hardoi-f30e1d48ab",
    # Uttar Pradesh, Lucknow: Kruti Dev and Mangal text layer that pypdf cannot lay out
    "blo2-up-lucknow-565c1a2922", "blo2-up-lucknow-490ab60414", "blo2-up-lucknow-5ff6fdf93a", "blo2-up-lucknow-6c8cbb5152",
]
MANIPUR = True          # every Imphal West list in seeds/blo2_mn.json (English scans)
NOT_BLO = {
    "blo2-up-ghaziabad-e115152cda": "a list of the 5 Returning Officers of the district, not of BLOs",
    "blo2-up-shamli-cf73acaebd": "ERO, AERO, supervisor and BLO names without part numbers",
}


def item(it):
    p = dict(it["payload"])
    if p["kind"] == "pdf":
        stored = f"civic-officials-blo2-in/blo/{p['state']}/" + \
            hashlib.sha1(json.dumps(it["payload"], sort_keys=True).encode()).hexdigest()[:16] + ".pdf"
    else:
        stored = f"civic-officials-blo2/blo2/{p['state']}/{hashlib.sha1(p['url'].encode()).hexdigest()[:12]}.pdf"
    p["kind"] = "form-blo2_ocr"
    p["stored"] = [stored]
    return {"key": it["key"], "payload": p}


def main():
    seeds = {i["key"]: i for f in sorted(HERE.glob("blo2_*.json")) for i in json.loads(f.read_text())}
    out = [item(seeds[k]) for k in KEYS]
    if MANIPUR:
        out += [item(i) for i in json.loads((HERE / "blo2_mn.json").read_text())]
    assert not {i["key"] for i in out} & set(NOT_BLO)
    (HERE / "blo2ocr.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(len(out), "items")


if __name__ == "__main__":
    main()
