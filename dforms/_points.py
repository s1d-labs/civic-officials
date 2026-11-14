"""Shared reader for the national point layers (owner 2026-11-14, "cover everything like points"): GeoParquet files of public
service points with a location, as compiled by github.com/ramSeraph/indian_facilities (release assets; the data comes from
government map servers: Bharatmaps (NIC), PM GatiShakti, DFS; the compilation is CC0, the source GIS states no licence, so the
civic-india map shows the points and links the source, it does not offer the files for download).

One queue item = one slice of one row group of one file. Payload: reader (the dforms/points_<kind>_<src>.py module), url (release
asset), rg (row group), lo / hi (rows of the FILE, lo included, hi not), n_file (rows of the whole file when the seed was made),
expected (hi - lo), open true (GitHub, no geoblock). fetch() reads the whole file with one GET (7-90 MB; the source trail keeps one
copy per sha256), checks that it still has n_file rows (else no records and why "file changed"), reads row group rg and keeps rows
lo..hi. Coordinates come from the GeoParquet bbox covering columns (xmin = xmax, ymin = ymax for a point); a point outside India's
box (lat 6-37.6, lon 68-97.5) is kept without lat/lon and counted ("no location in India"). Each record has src_pos {"row": row
number in the file, 1-based, "rg": row group}. Seeds: seeds/dept_points_<kind>_all.json (seeds/build_dept_points.py).
Needs pyarrow (requirements.txt).
"""
import io

from dforms import _civic, _esw
import provenance

METHOD = "geoparquet file (row group slice)"
# Census 2011 / LGD state codes (they agree for the states and UTs of 2011; 37 Ladakh, 38 DNH and DD) -> two-letter codes
STATE = {"01": "JK", "02": "HP", "03": "PB", "04": "CH", "05": "UK", "06": "HR", "07": "DL", "08": "RJ", "09": "UP", "10": "BR",
         "11": "SK", "12": "AR", "13": "NL", "14": "MN", "15": "MZ", "16": "TR", "17": "ML", "18": "AS", "19": "WB", "20": "JH",
         "21": "OD", "22": "CG", "23": "MP", "24": "GJ", "25": "DH", "26": "DH", "27": "MH", "28": "AP", "29": "KA", "30": "GA",
         "31": "LD", "32": "KL", "33": "TN", "34": "PY", "35": "AN", "36": "TG", "37": "LA", "38": "DH"}
NONE = {"", "na", "n/a", "nil", "null", "none", "\\n", "0", "-", "--", "not available"}


def val(v):
    """A cell as clean text, None for the placeholders these files use (' ', 'NA', '\\N', '0')."""
    if v is None:
        return None
    if isinstance(v, float):
        if v != v:
            return None
        v = int(v) if v.is_integer() else v
    s = _esw.clean(str(v))
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return None if s.lower() in NONE else s


def state_of(*codes_or_names):
    """Two-letter code from the first census / LGD state code ('9', '09') or state name that gives one, else ''."""
    for v in codes_or_names:
        v = val(v)
        if not v:
            continue
        if v.isdigit():
            st = STATE.get(v.zfill(2), "")
        else:
            st = _civic.state_code(v)
        if st:
            return st
    return ""


def point(row):
    """(lat, lon) of a point row from the bbox covering column, or (None, None) when it is not a point inside India's box."""
    b = row.get("bbox") or {}
    x, y = b.get("xmin"), b.get("ymin")
    if x is None or y is None or b.get("xmax") != x or b.get("ymax") != y:
        return None, None
    la, lo = _civic.lat(y), _civic.lon(x)
    return (la, lo) if la is not None and lo is not None else (None, None)


def rows(content, p, columns):
    """[(row number in the file, 1-based, row dict)] for rows p["lo"]..p["hi"] of row group p["rg"]; raises ValueError when the
    file is not the seeded one (not Parquet, other row count, the slice outside the row group)."""
    import pyarrow.parquet as pq
    if content[:4] != b"PAR1":
        raise ValueError("not a Parquet file")
    pf = pq.ParquetFile(io.BytesIO(content))
    md = pf.metadata
    if md.num_rows != p["n_file"]:
        raise ValueError(f"file changed: {md.num_rows} rows, seeded {p['n_file']}")
    start = sum(md.row_group(i).num_rows for i in range(p["rg"]))
    end = start + md.row_group(p["rg"]).num_rows
    if not start <= p["lo"] < p["hi"] <= end:
        raise ValueError(f"rows {p['lo']}-{p['hi']} are not in row group {p['rg']} ({start}-{end})")
    names = set(pf.schema_arrow.names)
    t = pf.read_row_group(p["rg"], columns=[c for c in columns + ["bbox"] if c in names])
    t = t.slice(p["lo"] - start, p["hi"] - p["lo"])
    return [(p["lo"] + i + 1, r) for i, r in enumerate(t.to_pylist())]


def fetch(p, get, module, make, columns):
    """The item: GET the file, read the slice, make(row, n, p) -> (key, fields) or (None, skip reason) for each row."""
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    try:
        got = rows(r.content, p, columns)
    except ValueError as e:
        return [], [], str(e)
    out, seen = [], set()
    for n, row in got:
        key, f = make(row, n, p)
        if key is None:
            provenance.skipped(f)
            continue
        la, lo = point(row)
        if la is None:
            f["no_location"] = True      # the row is kept (name, codes); the map leaves it out
        else:
            f["lat"], f["lon"] = la, lo
        out.append(_civic.record(module, _civic.unique(key, seen), f.pop("layer"), level="facility", source=p["url"],
                                 src_url=p["url"], src_pos={"row": n, "rg": p["rg"]}, **f))
        provenance.used()
    return out, [], "" if out else "no rows"
