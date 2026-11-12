"""Build seeds/tngis_services.json: Tamil Nadu public-service and boundary layers on the TNGIS public GeoServer WFS
(https://tngis.tn.gov.in/tngismaps/wfs, no login, no token), one queue item per layer for dforms/wm2_wfs.py (payload "kind").

Checked 2026-11-12 from dev-vps-3 (one resultType=hits + one DescribeFeatureType per layer): every layer below answered.
"expect" = numberMatched that day. Layers in the workspaces `tngis:` and `TNGIS_V2:` (e_sevai, sp_post_office, PHC, uphc,
Anganwadi, ICDS_Points, sp_fair_price_shop, RevenueOffices, sp_govt_alloffices, TalukOffices, ...) answer HTTP 500
("database tnega / hillaris does not exist") and are not seeded. Mirror layers with the same rows in another workspace
(e.g. Police_Jurisdiction:Data_Sharing_Police_Locations = generic_viewer:police_stations) are left out.

The owner's shapefile download (~/data/civic-india/tngis-2026-11-12/TNGIS_all_layers, 657 layers OK) has every layer below
with the same feature counts, but GeoServer wrote its DBFs as ISO-8859-1 (Tamil text became "?"), with 10-character field
names and 254-character text: these GeoJSON copies are the lossless ones.

    python seeds/build_tngis_services.py      (writes seeds/tngis_services.json)
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
URL = "https://tngis.tn.gov.in/tngismaps/wfs"

# (kind, layer, expect, district attribute, page size). Sort: object_id where the layer has it (GeoServer's own id column).
LAYERS = [
    ("police_station", "generic_viewer:police_stations", 1315, "", 2000),
    ("police_jurisdiction", "generic_viewer:police_jurisdiction_boundary", 1333, "district_name", 200),
    ("traffic_police_jurisdiction", "generic_viewer:traffic police jurisdiction", 1139, "district_name", 200),
    ("police_place", "generic_viewer:police_point_of_interest", 55913, "district_name", 5000),
    ("pds_shop", "generic_viewer:public_distribution_system_shop", 34719, "district", 5000),
    ("health_facility", "generic_viewer:all_health_facilities", 11289, "district_name", 5000),
    ("phc", "generic_viewer:tn_phc", 2262, "district_name", 5000),
    ("veterinary_hospital", "generic_viewer:vertinary_hospital", 143, "district_name", 2000),
    ("school", "generic_viewer:schools", 58519, "district", 5000),
    ("school_gcc", "generic_viewer:gcc_schools", 392, "", 2000),
    ("anganwadi", "generic_viewer:anganwadi_centres", 54436, "district", 5000),
    ("csc", "generic_viewer:csc_updated", 44101, "district", 5000),
    ("aadhaar_centre", "generic_viewer:aadhar_enrollment_center", 977, "district", 2000),
    ("govt_office", "generic_viewer:government_offices_location", 2317, "distname1", 5000),
    ("govt_office_tanfinet", "generic_viewer:government_office_tanfinet_pop", 164814, "district", 5000),
    ("district_hq", "generic_viewer:district_headquarters", 38, "district", 2000),
    ("rdo_office", "generic_viewer:revenue_divisional_office", 14, "district_name", 2000),
    ("taluk_office", "generic_viewer:taluk_office", 288, "district_name", 2000),
    ("block_hq", "tngis_basemap:basemap_blocks_headquarters", 278, "district_name", 2000),
    ("block_office_tanfinet", "generic_viewer:block_office_tanfinet", 388, "district", 2000),
    ("panchayat_hq", "tngis_basemap:basemap_panchayat_headquarters", 12328, "district_name", 5000),
    ("village_panchayat_office", "generic_viewer:village_panchayat_office", 12525, "district", 5000),
    ("gram_panchayat_office_tanfinet", "generic_viewer:gram_panchayat_office_tanfinet", 12525, "district", 5000),
    ("registration_office", "generic_viewer:registration_office", 699, "district_name", 2000),
    ("gcc_region_office", "generic_viewer:gcc_region_office", 3, "", 2000),
    ("gcc_zone_office", "generic_viewer:gcc_zone_office", 12, "", 2000),
    ("gcc_ward_office", "generic_viewer:gcc_ward_office", 148, "", 2000),
    ("eb_section_office", "generic_viewer:tneb_section_office_gis", 2812, "", 5000),
    ("fire_station", "generic_viewer:fire_stations", 407, "", 2000),
    ("postal_boundary", "generic_viewer:postal_boundary", 2044, "district", 200),
    ("district_boundary", "admin_master:administrative_boundary_district_updated", 38, "district_name", 100),
    ("taluk_boundary", "admin_master:administrative_boundary_taluk", 313, "district_name", 400),
    ("taluk_boundary_gv", "generic_viewer:taluk_boundary", 315, "district_name", 400),
    ("block_boundary", "admin_master:administrative_boundary_block", 389, "district_name", 400),
    ("revenue_village", "generic_viewer:revenue_villages", 21510, "district_name", 500),
    ("revenue_village_basemap", "tngis_basemap:basemap_revenue_village", 18143, "dist_name", 500),
    ("village_panchayat_boundary", "generic_viewer:tn_village_panchayat_boundary", 12525, "district_name", 1000),
    ("town_panchayat_boundary", "generic_viewer:town_Panchayat", 496, "dist_name", 500),
    ("municipality_boundary", "generic_viewer:municipalities", 139, "dist_name", 200),
    ("corporation_boundary", "generic_viewer:corporation_boundary", 21, "district", 100),
    ("ulb_ward", "generic_viewer:urban_local_bodies", 3271, "district_name", 500),
    ("assembly_constituency", "generic_viewer:assembly_constituency", 234, "district_name", 300),
    ("parliament_constituency", "generic_viewer:parliament_constituency", 39, "", 100),
]
# Layers without an object_id column: small enough for one page, no sortBy
NO_OBJECT_ID = {"admin_master:administrative_boundary_district_updated", "admin_master:administrative_boundary_taluk",
                "admin_master:administrative_boundary_block"}


def items():
    out = []
    for kind, layer, expect, district, page in LAYERS:
        chunk = layer.split(":", 1)[1].replace(" ", "_").lower()
        if chunk.startswith("basemap_"):
            chunk = chunk.removeprefix("basemap_") + "_basemap"
        p = {"reader": "wm2_wfs", "url": URL, "layer": layer, "kind": kind.removesuffix("_gv").removesuffix("_basemap"),
             "state": "33", "india_only": False, "source": "tngis", "chunk": chunk, "page": page, "expect": expect,
             "vintage": "live 2026-11"}
        if layer not in NO_OBJECT_ID:
            p["sort"] = "object_id"
        if district:
            p["district"] = district
        out.append({"key": f"tngis-{chunk}", "payload": p})
    assert len({i["key"] for i in out}) == len(out)
    return out


if __name__ == "__main__":
    (HERE / "tngis_services.json").write_text(json.dumps(items(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(len(LAYERS), "layers")
