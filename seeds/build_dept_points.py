"""Build seeds/dept_points_<kind>_all.json: the queue items of the national point readers (dforms/points_*.py, dforms/_points.py).
Reads only the Parquet footer of each release asset (HTTP range requests, about 3 x 64 KB per file): rows of the file and of each
row group. One item = rows lo..hi of one row group, at most SLICE rows. Run anywhere with pyarrow (2026-11-14 on dev-vps-3):
    python seeds/build_dept_points.py
The files are on GitHub (github.com/ramSeraph/indian_facilities releases; answer from anywhere): payload open true (project
civic-officials-depts-open, plain GitHub runners).
"""
import io
import json
import struct
import urllib.request
from pathlib import Path

import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
REL = "https://github.com/ramSeraph/indian_facilities/releases/download"
SLICE = 50_000
# kind -> (reader module, release tag, asset); rows on 2026-11-14 in the comment
FILES = {
    "school": ("points_school_bm", "education", "Bharatmaps_Schooldata.parquet"),                 # 1,466,160
    "awc": ("points_awc_gs", "health", "GatiShakti_ICDS_Anganvadis.parquet"),                     # 1,224,038
    "fps": ("points_fps_dofd", "govt-services", "Bharatmaps_DoFD_PDS_2023.parquet"),             # 423,738
    "csc": ("points_csc_meity", "govt-services", "Bharatmaps_MeitY_CSCs_2022.parquet"),          # 401,268
    "bank": ("points_bank_dfs", "banking", "Bharatmaps_DFS_Bank_Branches_2022.parquet"),         # 168,955
    "atm": ("points_atm_dfs", "banking", "Bharatmaps_DFS_Bank_ATMs_2022.parquet"),               # 196,360
    "aadhaar": ("points_aadhaar_gm", "govt-services", "Bharatmaps_Grammanchitra_Aadhar_Centers.parquet"),   # 79,023
}


def _range(url, a, b):
    req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}", "User-Agent": "civic-officials seeds"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Range", "")


def footer(url):
    """pyarrow FileMetaData of a remote Parquet file from its last bytes only."""
    _, cr = _range(url, 0, 0)
    size = int(cr.split("/")[1])
    tail, _ = _range(url, size - 8, size - 1)
    if tail[4:] != b"PAR1":
        raise ValueError(f"{url}: not Parquet")
    flen = struct.unpack("<I", tail[:4])[0]
    foot, _ = _range(url, size - 8 - flen, size - 1)
    buf = bytearray(size)          # a sparse stand-in: pyarrow reads only the footer for the metadata
    buf[:4] = b"PAR1"
    buf[size - 8 - flen:] = foot
    return pq.ParquetFile(io.BytesIO(bytes(buf))).metadata


def items(module, url, groups):
    """groups: rows per row group -> items of at most SLICE rows inside one row group."""
    out, start, n_file = [], 0, sum(groups)
    for rg, n in enumerate(groups):
        for lo in range(start, start + n, SLICE):
            hi = min(lo + SLICE, start + n)
            out.append({"key": f"{module}-{lo:07d}", "payload": {"reader": module, "url": url, "state": "IN", "rg": rg, "lo": lo,
                        "hi": hi, "n_file": n_file, "expected": hi - lo, "open": True, "india_only": False, "route": "abroad"}})
        start += n
    return out


def main():
    for kind, (module, tag, asset) in FILES.items():
        url = f"{REL}/{tag}/{asset}"
        md = footer(url)
        groups = [md.row_group(i).num_rows for i in range(md.num_row_groups)]
        its = items(module, url, groups)
        (HERE / f"dept_points_{kind}_all.json").write_text(json.dumps(its, indent=1, ensure_ascii=False) + "\n")
        print(kind, md.num_rows, "rows", len(groups), "row groups", len(its), "items")


if __name__ == "__main__":
    main()
