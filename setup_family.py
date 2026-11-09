"""Put this family's projects in the pool. Run by the Setup workflow (GitHub Actions; the hub trusts s1d-labs/<family> through its
OIDC token). Safe to run again: queue items that exist are kept."""
from scrape_hub_client import register_project, seed_queue, set_pool, set_probes

from family import FAMILY, PROBES, PROJECTS

print("health checks:", set_probes(FAMILY, PROBES))
for p in PROJECTS:
    register_project(p["name"], title=p["title"], unit_label=p["unit_label"], record_label=p["record_label"],
                     expected_units=len(p["items"]), expected_records=0)
    set_pool(p["name"], FAMILY, p["task"], target=p["target"], env=p["env"], probe=p["probe"], max_workers=p["workers"],
             threads=p["threads"], delay_ms=p["delay_ms"], **{k: p[k] for k in ("proxy", "geo") if p.get(k)})
    if p["items"]:
        print(p["name"], "queue:", seed_queue(p["name"], p["items"]))
