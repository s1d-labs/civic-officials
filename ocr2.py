"""Task `councillors-ocr2`: a second, independent OCR read of the saved page images behind the OCR'd councillor rows (owner,
2026-11-15: verification pass). One queue item = one saved PDF in the family bucket and up to 4 of its pages.

The first reads used Tesseract (tessdata hin / mar / guj / tam, per cell or per line). This task reads each page again, whole, with
a different engine, and stores what it read with the position of every text segment. It does not see the first read: the comparison
(name and ward per row) is done afterwards on the box (investigations civic-india/ocr2_compare.py).
  - Devanagari (hi, mr), English (en): EasyOCR (CRAFT text detector + CRNN recogniser; PyTorch CPU), page at 300 dpi.
  - Gujarati and Tamil (EasyOCR has no Gujarati model, and its Tamil model does not load: size mismatch, 2026-11-15): Tesseract
    with the tessdata_best script model "Gujarati" / "Tamil" (a different, float LSTM network from the tessdata "guj" / "tam" of
    the first read), page binarised (Otsu) with the ruled lines removed, psm 4, word boxes.
Payload: {"doc": "<project>/<key>.pdf[.gz]", "pages": [n, ...], "engine": "easyocr" | "tess-best", "langs": ["hi", "en"] |
"Gujarati" | "Tamil", "sha256": "<sha256 of the PDF>"}.
Record per page: "ocr2:<sha256[:16]>:p<page>" = {"type": "ocr_second_read", "doc", "sha256", "page", "engine", "langs", "dpi",
"size_pt": [w, h], "segs": [[x0, y0, x1, y1, text, conf], ...]} with boxes in PDF points (origin top left, as box_pt of the first
reads). `python ocr2.py --local '<payload json>' FILE.pdf` reads a local file without the hub.
"""
import gzip
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import requests

DPI = 300
stop = False
_reader = {}
BEST = "https://github.com/tesseract-ocr/tessdata_best/raw/main/script/{}.traineddata"


def on_signal(*_):
    global stop
    stop = True


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def need_poppler():
    if not shutil.which("pdftoppm") or not shutil.which("tesseract"):
        sh("sudo -n apt-get update -q && sudo -n apt-get install -y -q poppler-utils tesseract-ocr")
    return bool(shutil.which("pdftoppm"))


def need_easyocr():
    try:
        import easyocr  # noqa: F401
        return True
    except ImportError:
        pass
    py = sys.executable
    # the CPU build of PyTorch (the default wheel pulls ~3 GB of CUDA libraries the runner cannot use)
    sh(f"{py} -m pip install -q --index-url https://download.pytorch.org/whl/cpu torch torchvision")
    sh(f"{py} -m pip install -q easyocr opencv-python-headless")
    try:
        import easyocr  # noqa: F401
        return True
    except ImportError:
        return False


def need_best(script, d):
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, script + ".traineddata")
    if not os.path.exists(p):
        r = requests.get(BEST.format(script), timeout=(20, 300))
        r.raise_for_status()
        with open(p, "wb") as f:
            f.write(r.content)
    return d


def render(pdf, page, tmp):
    base = os.path.join(tmp, f"p{page}")
    subprocess.run(["pdftoppm", "-r", str(DPI), "-gray", "-png", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True, timeout=600)
    return base + ".png" if os.path.exists(base + ".png") else None


def page_size_pt(png):
    import cv2
    im = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    return im.shape[1] * 72 / DPI, im.shape[0] * 72 / DPI


def read_easyocr(png, langs):
    import easyocr
    k = tuple(langs)
    if k not in _reader:
        _reader.clear()          # one model set in memory at a time
        _reader[k] = easyocr.Reader(list(langs), gpu=False, verbose=False)
    out = []
    for box, text, conf in _reader[k].readtext(png, paragraph=False):
        xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
        out.append([round(min(xs) * 72 / DPI, 1), round(min(ys) * 72 / DPI, 1), round(max(xs) * 72 / DPI, 1),
                    round(max(ys) * 72 / DPI, 1), text, round(float(conf), 3)])
    return out


def unruled(png, tmp):
    """Otsu binarisation, then long horizontal and vertical runs (ruled lines) whitened."""
    import cv2
    im = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    _, bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inv = 255 - bw
    h = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (DPI // 2, 1)))
    v = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, DPI // 2)))
    clean = 255 - cv2.subtract(inv, cv2.bitwise_or(h, v))
    out = os.path.join(tmp, "u_" + os.path.basename(png))
    cv2.imwrite(out, clean)
    return out


def read_tess_best(png, script, tmp):
    d = need_best(script, os.path.join(tempfile.gettempdir(), "tessdata_best"))
    img = unruled(png, tmp)
    r = subprocess.run(["tesseract", img, "-", "--tessdata-dir", d, "-l", script, "--psm", "4", "--dpi", str(DPI),
                        "-c", "tessedit_create_tsv=1"],
                       capture_output=True, text=True, timeout=900)
    out = []
    for ln in r.stdout.splitlines()[1:]:
        p = ln.split("\t")
        if len(p) < 12 or p[0] != "5" or not p[11].strip():
            continue
        x, y, w, h = (int(v) for v in p[6:10])
        out.append([round(x * 72 / DPI, 1), round(y * 72 / DPI, 1), round((x + w) * 72 / DPI, 1), round((y + h) * 72 / DPI, 1),
                    p[11], round(float(p[10]) / 100, 3)])
    return out


def read_item(p, pdf_bytes):
    """-> [(record id, data)], why"""
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    if p.get("sha256") and p["sha256"] != sha:
        # the bucket copy is not the file the first read used: nothing to compare
        return [], f"sha256 differs: {sha[:16]}"
    if not need_poppler():
        return [], "poppler not available"
    if p["engine"] == "easyocr" and not need_easyocr():
        return [], "easyocr not available"
    recs = []
    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "doc.pdf")
        with open(pdf, "wb") as f:
            f.write(pdf_bytes)
        for page in p["pages"]:
            if stop:
                break
            png = render(pdf, page, tmp)
            if not png:
                continue
            t = time.time()
            if p["engine"] == "easyocr":
                segs = read_easyocr(png, p["langs"])
            else:
                need_easyocr()           # opencv for the line removal
                segs = read_tess_best(png, p["langs"], tmp)
            recs.append((f"ocr2:{sha[:16]}:p{page}", {
                "type": "ocr_second_read", "doc": p["doc"], "sha256": sha, "page": page, "engine": p["engine"],
                "langs": p["langs"], "dpi": DPI, "size_pt": [round(v, 1) for v in page_size_pt(png)], "segs": segs,
                "seconds": round(time.time() - t, 1),
                "method": ("ocr easyocr " + "+".join(p["langs"]) + " (whole page, 300 dpi)") if p["engine"] == "easyocr" else
                          f"ocr tesseract tessdata_best script/{p['langs']} (whole page, 300 dpi, Otsu, ruled lines removed, psm 4)"}))
            os.remove(png)
    return recs, "" if recs else "no page rendered"


def fetch_doc(hub, key):
    url = hub.read_urls(key.split("/", 1)[0], [key])[key]
    r = requests.get(url, timeout=(20, 300))
    r.raise_for_status()
    b = r.content
    if key.endswith(".gz") and b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b


def main():
    from scrape_hub_client import HubClient
    project = os.environ["SCRAPE_POOL_PROJECT"]
    deadline = time.time() + float(os.environ.get("SCRAPE_MAX_HOURS", "1")) * 3600 - 600
    hub = HubClient(project, job_index=int(os.environ.get("SCRAPE_JOB_INDEX", 0)), total_jobs=int(os.environ.get("SCRAPE_TOTAL_JOBS", 1)))
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    try:
        while time.time() < deadline and not stop:
            if hub.settings.get("paused"):
                time.sleep(30)
                continue
            try:
                items = hub.claim(1, steal=True, retry_failed=True)
            except requests.RequestException:
                time.sleep(30)
                continue
            if not items:
                break
            item = items[0]
            p = item["payload"]
            if item.get("attempts", 0) > 3:
                hub.failure("ocr2", item["key"], "gave up after 3 attempts", doc=p.get("doc"))
                hub.complete([item["key"]], "done", fetched=0)
                continue
            try:
                t = time.time()
                b = fetch_doc(hub, p["doc"])
                hub.metric("n_http")
                hub.metric("t_http_s", time.time() - t)
                recs, why = read_item(p, b)
            except Exception as e:  # noqa: BLE001
                recs, why = [], f"{type(e).__name__}: {e}"[:200]
            hub.metric("pages_read", len(recs))
            for attempt in range(5):
                try:
                    for rid, data in recs:
                        hub.record(rid, data)
                    if not recs or (why and stop):
                        hub.failure("ocr2", item["key"], why or "stopped", doc=p.get("doc"))
                        hub.complete([item["key"]], "failed", error=(why or "stopped")[:200])
                    elif len(recs) < len(p["pages"]):
                        hub.complete([item["key"]], "failed", error="stopped before the last page")
                    else:
                        hub.complete([item["key"]], "done", fetched=len(recs))
                    break
                except requests.RequestException:
                    time.sleep(30 * (attempt + 1))
        hub.close("finished" if not stop else "failed", "" if not stop else "stopped by signal")
    except BaseException as e:
        hub.close("failed", f"{type(e).__name__}: {e}"[:200])
        raise


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--local":
        with open(sys.argv[3], "rb") as f:
            recs, why = read_item(json.loads(sys.argv[2]), f.read())
        print(json.dumps({"why": why, "pages": len(recs)}))
        for rid, d in recs:
            print(rid, d["seconds"], "s", len(d["segs"]), "segs")
            for s in d["segs"][:400]:
                print("  ", s)
    else:
        sys.exit(main())
