"""Build seeds/tngis_all.json and seeds/tngis_all_big.json: every other TNGIS layer of the owner's 2026-11-12 download that the
public WFS still answers, one queue item per layer for dforms/wm2_wfs.py (layer mode, payload "kind").
  tngis_all.json      layers up to BIG_MB of GeoJSON (estimate): project civic-officials-tngis (with tngis_services.json)
  tngis_all_big.json  the larger ones (parcel analyses, master plans, land use, Chennai buildings, road networks; about 20 M
                      features, 36 GB of GeoJSON by the estimate): project civic-officials-tngis-big, queued on its own

Source list: seeds/tngis_all.tsv (one row per layer), made from civic-india wardmap/tngis_inventory.tsv:
  - the owner's download (~/data/civic-india/tngis-2026-11-12/TNGIS_all_layers: _download_log.tsv, 677 layers, 657 saved as
    shapefiles) read from the log, the zip listings and the .dbf / .shp headers only;
  - left out: the 43 layers of seeds/tngis_services.json, and mirrors (same feature count + same fields + same bounding box in
    another workspace; column "mirrors" names them); workspaces tngis: and TNGIS_V2: (HTTP 500, database missing) are not in it;
  - "expect" = numberMatched of one resultType=hits request per layer from dev-vps-3, 2026-11-13 (2 s apart);
  - "sort" = object_id (or objectid / ogc_fid / gid / fid / id) when the layer has it, else attributes picked from the layer's
    DescribeFeatureType (GeoServer refuses a paged request on a table without a primary key unless sortBy is given);
    "page" = about 5 MB of GeoJSON per request (estimate from the shapefile: min(unzipped size, 10 x zip size)), 100 to 4,000
    features; "district" = the district attribute for the record's by_district count; "est_json_mb" = that estimate.
The shapefiles are not the source: GeoServer wrote their DBFs as ISO-8859-1 (Tamil text became "?"), with 10-character field
names and 254-character text. The GeoJSON copies keep every attribute in UTF-8.

    python seeds/build_tngis_all.py      (writes seeds/tngis_all.json)
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
URL = "https://tngis.tn.gov.in/tngismaps/wfs"
BIG_MB = 200


def rows():
    with open(HERE / "tngis_all.tsv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def items(big=False):
    out = []
    for r in rows():
        if (float(r["est_json_mb"]) > BIG_MB) != big:
            continue
        expect = int(r["expect"]) if r["expect"].isdigit() else None
        p = {"reader": "wm2_wfs", "url": URL, "layer": r["layer"], "kind": r["chunk"], "category": r["category"], "state": "33",
             "india_only": False, "source": "tngis", "chunk": r["chunk"], "page": int(r["page"]), "expect": expect,
             "vintage": "live 2026-11"}
        if r["sort"]:
            p["sort"] = r["sort"]
        if r["district"]:
            p["district"] = r["district"]
        out.append({"key": f"tngis-{r['chunk']}", "payload": p})
    assert len({i["key"] for i in out}) == len(out)
    return out


if __name__ == "__main__":
    for name, big in (("tngis_all.json", False), ("tngis_all_big.json", True)):
        it = items(big)
        (HERE / name).write_text(json.dumps(it, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(name, len(it), "layers")
