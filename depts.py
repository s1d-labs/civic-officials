"""Task `depts`: department offices and their officers (police stations, power offices, EROs, sub-registrars, water offices ...),
the bengawalk / Vonter layers for all of India. One queue item = one source page, file or API call. Payload:
{"reader": "<module>", "url", ...}: dforms/<module>.py fetch(payload, get) returns (records, files, why), with
get(url, method="GET", data=None, headers=None) on one requests session (the same contract as cforms/ in councillors.py).
{"kind": "seed", "module": "<module>"}: dforms/<module>.py items(get) lists the queue items; one record "seed_items".
Records: "dept:<module>:<office key>" = {"type": "dept_office", "dept", "level", "area", "area_regional", "post", "name",
"name_regional", "phone", "email", "address", "state", "district", "office_id", "source", "last_updated", "lat", "lon"}
(dept / level keys: civic-india/TAGGING.md; leave a field out when the source does not give it).
`python depts.py --local '<payload json>'` runs one item without the hub.
"""
import importlib
import sys

import councillors


def run(item, get):
    p = item["payload"]
    if p.get("kind") == "seed":
        items = importlib.import_module("dforms." + p["module"]).items(get)
        return ([(f"seed:dept:{p['module']}", {"type": "seed_items", "module": p["module"], "items": items, "url": p.get("url", "")})],
                [], "" if items else "no items")
    return importlib.import_module("dforms." + p["reader"]).fetch(p, get)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--local":
        councillors.local(sys.argv[2], run)
    else:
        sys.exit(councillors.main(run, "depts"))
