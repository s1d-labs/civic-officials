"""Gujarat (leg_gj) and Punjab (leg_pb) MLAs from their NeVA member directories (shared reader dforms/_leg_neva.py), on
trimmed copies of the lists fetched 2026-11-12 (8 of 182 Gujarat cards, 13 of 117 Punjab cards; regional list + English list)."""
import json

from esw_common import ROOT, check_records, mod
from test_leg_more import neva_get


def _run(m):
    items = json.loads((ROOT / "seeds" / f"dept_{m}.json").read_text())
    assert items == mod(m).items() and len(items) == 1
    p = items[0]["payload"]
    get = neva_get(p, f"neva_{m[4:]}_list.html", f"neva_{m[4:]}_list_en.html")
    recs, files, why = mod(m).fetch(p, get)
    assert why == "" and [f[0] for f in files] == [f"depts/{m}/list.html.gz", f"depts/{m}/list-en.html.gz"]
    check_records(recs, m, "elected")
    return p, dict(recs)


def test_leg_gj():
    p, r = _run("leg_gj")
    assert p["host"] == "gujarat.neva.gov.in" and p["house"] == 15 and p["india_only"] is False and len(r) == 8
    a = r["dept:leg_gj:GJ-AC-77"]                                    # Jamnagar Rural = the layer's "Jamnagar" (ALIAS)
    assert (a["name"], a["phone"], a["email"], a["district"]) == ("Raghavjibhai Hansrajbhai Patel", "9825213302",
                                                                  "mlajamnagarrural@gujarat.gov.in", "Jamnagar")
    assert a["name_regional"] == "શ્રી રાઘવજીભાઈ હંસરાજભાઈ પટેલ"
    assert r["dept:leg_gj:GJ-AC-117"]["name"] == "Arjunsinh Udesinh Chauhan"      # Mahemdabad -> Mehmedabad (ALIAS)
    assert r["dept:leg_gj:GJ-AC-157"]["area"] == "157 - Mandvi (ST)"               # Surat's Mandvi: district settles it
    x = r["dept:leg_gj:GJ-AC-x-maninagar"]                           # Ahmedabad seats are not in the site's AC layer
    assert x["name"] == "Amul Bhatt" and "office_id" not in x


def test_leg_pb():
    p, r = _run("leg_pb")
    assert p["host"] == "pvs.neva.gov.in" and p["house"] == 16 and len(r) == 13
    assert all(d.get("office_id") for d in r.values())
    cm = r["dept:leg_pb:PB-AC-107"]
    assert (cm["name"], cm["area"], cm["email"], cm["district"]) == ("Bhagwant Mann", "107 - Dhuri", "cmo@punjab.gov.in", "Sangrur")
    assert r["dept:leg_pb:PB-AC-20"]["name_regional"] == "ਏ.ਡੀ.ਸੀ. ਜਸਵਿੰਦਰ ਸਿੰਘ ਰਮਦਾਸ"
