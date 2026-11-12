"""Ward map files (GeoPDFs and other PDF maps of ward boundaries): download each file ONCE into the bucket.

Fetch once, process anywhere: this reader only downloads and stores. The ward polygons are made later from the saved copy by
civic-india/wm_geopdf.py (GDAL), on any machine. So the items need an Indian IP only when the source site needs one
(payload "india_only"); GitHub (Git LFS) files run on plain GitHub runners.

Payload (seeds/wm_*.json):
  {"reader": "wm_geopdf", "url": "<file url>", "state": "MH", "body": "<LGD local_body_code>", "body_name": "...",
   "ward": "<ward number for a one-ward map, or empty>", "all": <true when the file maps every ward>, "stage": "final|draft|",
   "source": "okeskar | <site>", "path": "<path in the source>", optional "sha256" + "size" (Git LFS: checked; on a
   short or wrong answer the LFS batch API gives a fresh download link), optional "lfs_repo": "owner/name"}
Record "wm_file:<sha256[:16]>" = {"type": "wm_file", "url", "file" (bucket path, relative to the project), "bytes", "sha256",
  "pages", "geo" (true: the PDF carries a geospatial measure dictionary; false: none found; null: not a PDF or unreadable),
  "body", "body_name", "state", "ward", "all", "stage", "source", "path"}.
Stored file: wardmaps/<state>/<body>/<sha256[:16]>.<ext>.
"""
import hashlib
import io
import json
import re

import provenance

METHOD = "file saved to the bucket (GeoPDF, read later)"     # source trail (provenance.py): how this reader reads its sources

ACCEPT = (b"%PDF-", b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*")
EXT = {b"%PDF-": "pdf", b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"II*\x00": "tif", b"MM\x00*": "tif"}


def lfs_link(get, repo, oid, size):
    """A fresh download link for one Git LFS object (GitHub's public LFS batch API, no login)."""
    body = json.dumps({"operation": "download", "transfers": ["basic"], "objects": [{"oid": oid, "size": int(size)}]})
    r = get(f"https://github.com/{repo}.git/info/lfs/objects/batch", method="POST", data=body,
            headers={"Accept": "application/vnd.git-lfs+json", "Content-Type": "application/vnd.git-lfs+json"})
    if r is None:
        return None
    try:
        return r.json()["objects"][0]["actions"]["download"]["href"]
    except (KeyError, IndexError, ValueError):
        return None


def geo_flag(content):
    """True when a page of the PDF has a geospatial viewport or LGIDict (ISO 32000 / OGC GeoPDF); False when none; None if unreadable."""
    if not content.startswith(b"%PDF-"):
        return None
    if any(k in content for k in (b"/LGIDict", b"/GPTS")):
        return True
    try:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(content))
        for pg in rd.pages[:3]:
            if "/LGIDict" in pg or "/VP" in pg:
                vp = pg.get("/VP")
                vps = vp if isinstance(vp, list) else [vp] if vp is not None else []
                for v in vps:
                    v = v.get_object() if hasattr(v, "get_object") else v
                    if v is not None and "/Measure" in v:
                        return True
                if "/LGIDict" in pg:
                    return True
        return False
    except Exception:  # noqa: BLE001 - damaged or encrypted: the converter decides later
        return None


def pages(content):
    if not content.startswith(b"%PDF-"):
        return 1
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:  # noqa: BLE001
        return len(re.findall(rb"/Type\s*/Page[^s]", content)) or None


def ok(content, p):
    if not content or not content.startswith(ACCEPT):
        return False
    if p.get("sha256") and hashlib.sha256(content).hexdigest() != p["sha256"]:
        return False
    return not (p.get("size") and len(content) != int(p["size"]))


def fetch(p, get):
    r = get(p["url"])
    content = r.content if r is not None else b""
    if not ok(content, p) and p.get("lfs_repo") and p.get("sha256"):
        href = lfs_link(get, p["lfs_repo"], p["sha256"], p.get("size") or 0)
        if href:
            r = get(href)
            content = r.content if r is not None else b""
    if not content:
        return [], [], "no answer"
    if not content.startswith(ACCEPT):
        return [], [], "not a PDF or image" + (" (an LFS pointer)" if content.startswith(b"version https://git-lfs") else "")
    if not ok(content, p):
        return [], [], f"short or changed file ({len(content)} bytes, want {p.get('size')})"
    sha = hashlib.sha256(content).hexdigest()
    ext = next(v for k, v in EXT.items() if content.startswith(k))
    body = re.sub(r"[^A-Za-z0-9._-]+", "-", str(p.get("body") or "unknown"))
    path = f"wardmaps/{p.get('state', 'XX')}/{body}/{sha[:16]}.{ext}"
    rec = {"type": "wm_file", "url": p["url"], "file": path, "bytes": len(content), "sha256": sha, "pages": pages(content),
           **provenance.at(r),          # the answer the file came from (the LFS link when the first url gave a pointer)
           "geo": geo_flag(content), **{k: p[k] for k in ("body", "body_name", "state", "ward", "all", "stage", "source", "path")
                                          if k in p}}
    return [(f"wm_file:{sha[:16]}", rec)], [(path, content, "application/pdf" if ext == "pdf" else f"image/{ext}")], ""
