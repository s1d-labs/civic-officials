"""Offline tests of the north-state education / health readers (officials-3-north) on saved answers in tests/data/north/."""
import hashlib
import json

from esw_common import DATA, ROOT, check_records, fake_get, mod


def test_edu_mp_vimarsh_deo_beo():
    m = mod("edu_mp_vimarsh")
    seeds = json.loads((ROOT / "seeds" / "dept_edu_mp_vimarsh.json").read_text())
    assert [i["key"] for i in seeds] == [i["key"] for i in m.items()]
    for d, n, fixture in (("DEO", 46, "north/vimarsh_deo.html"), ("BEO", 232, "north/vimarsh_beo.html")):
        p = next(i["payload"] for i in seeds if i["payload"]["designation"] == d)
        get = fake_get({("GET", m.URL): "north/vimarsh_home.html",
                        lambda u, mm, dd, d=d: mm == "POST" and dd and dd.get("DropDownList1") == d: fixture})
        recs, files, why = m.fetch(p, get)
        assert why == "" and len(recs) == n and len(files) == 2
        check_records(recs, "edu_mp_vimarsh", "education")
        assert all(r["district_code"] for _, r in recs)
        r = recs[0][1]
        assert r["src_sha256"] == hashlib.sha256((DATA / fixture).read_bytes()).hexdigest()
        assert r["src_pos"] == {"table": 2, "row": 2}
    agar = dict(recs)["dept:edu_mp_vimarsh:beo:agar-malwa:susner"]
    assert agar["level"] == "block" and agar["name"] == "MUKESH TIWARI" and agar["phone"] == "9425979565"
