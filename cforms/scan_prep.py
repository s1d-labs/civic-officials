"""Scan clean-up before OCR (last-gaps round, 2026-11-15): a scanned page turned straight (deskew) and its faint text made darker
(contrast), saved as a one-page PDF of the same size, so a reader reads it like the original page. Used by cforms/cw_mp.py when
the payload has "prep" (pages whose ruled grid is tilted, Kotma Ex-550 p. 3, or whose text is faint, Nayagaon Ex-411 p. 27).

prep = {"deskew": true, "max_angle": 3.0, "contrast": 1.0 .. 3.0, "dpi": 300}. The angle is the one (step 0.05 degree) at which
the dark pixels of the page fall into the sharpest rows (the projection profile); the page is turned by it (when it is 0.1 degree or more) around its centre,
white fills the corners. Contrast: the grey levels are stretched (autocontrast, 1 % cut) and darkened (each level v becomes 255 * (v / 255) ** contrast)."""
import os
import subprocess

METHOD = "page image deskewed (projection profile) and contrast stretched before OCR"


def skew_angle(img, max_angle=3.0, step=0.05):
    """The angle in degrees (counter-clockwise positive, PIL rotate) that makes the text rows of a grey image level."""
    from PIL import Image, ImageOps
    small = ImageOps.autocontrast(img.convert("L"), cutoff=1)      # faint ink counts too
    w = 1000
    if small.width > w:
        small = small.resize((w, round(small.height * w / small.width)))
    bw = small.point(lambda v: 255 if v < 140 else 0)       # dark ink = 255
    if not bw.getbbox():
        return 0.0
    best, best_a = -1.0, 0.0
    n = int(round(max_angle / step))
    for i in range(-n, n + 1):
        a = i * step
        r = bw.rotate(a, resample=Image.NEAREST, fillcolor=0)
        h = r.height
        data = r.tobytes()
        sums = [sum(data[y * r.width:(y + 1) * r.width]) for y in range(h)]
        mean = sum(sums) / h
        score = sum((s - mean) ** 2 for s in sums)
        if score > best:
            best, best_a = score, a
    return best_a


def prep_page(pdf, page, tmp, prep):
    """Path of a one-page PDF with the cleaned page, and the angle used. (None, 0) when the page cannot be rendered."""
    from PIL import Image, ImageOps
    dpi = int(prep.get("dpi", 300))
    base = os.path.join(tmp, f"prep{page}")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-f", str(page), "-l", str(page), "-singlefile", pdf, base],
                   capture_output=True)
    if not os.path.exists(base + ".pgm"):
        return None, 0.0
    img = Image.open(base + ".pgm").convert("L")
    angle = 0.0
    if prep.get("deskew"):
        angle = skew_angle(img, float(prep.get("max_angle", 3.0)))
        if abs(angle) >= 0.1:              # smaller turns blur more than they straighten
            img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=255, expand=False)
    c = float(prep.get("contrast", 1.0) or 1.0)
    if c != 1.0:
        img = ImageOps.autocontrast(img, cutoff=1)
        img = img.point([round(255 * (v / 255) ** c) for v in range(256)])
    out = base + ".pdf"
    img.save(out, "PDF", resolution=dpi)
    os.remove(base + ".pgm")
    return out, angle
