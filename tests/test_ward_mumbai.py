"""Offline tests of the Mumbai (BMC / MCGM) ward readers dforms/ward2n_mumbai.py and dforms/ward2n_mumbai_water.py, on small saved
answers in tests/data/ward_mumbai/:
  ac_list.html       portal.mcgm.gov.in qlListofAsstMC, the officer table only (live answer 2026-11-11, "Last updated on 03/07/2026")
  docs_d.html        portal.mcgm.gov.in qlwrdd (D ward documents page), only its content iframe (live answer 2026-11-11)
  d_water.pdf        portal.mcgm.gov.in .../D Ward/Water Dept.pdf without font programs and tags (same text and positions)
  water_t_*         T ward (2026-11-13): page iframe only, KM frame, WebDAV PROPFIND listing, "MCGM employee email id" PDF
  prabhag_topo.json  Vonter/city-officials mumbai/boundaries_bmc_prabhag.json, properties ward + prabhag_no only
"""
import json
from pathlib import Path

from esw_common import ROOT, mod

D = Path(__file__).parent / "data" / "ward_mumbai"


class Answer:
    def __init__(self, content, url):
        self.content, self.url, self.status_code, self.encoding = content, url, 200, "utf-8"

    @property
    def text(self):
        return self.content.decode("utf-8", "replace")


def fake_get(routes):
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((url, headers))
        return Answer((D / routes[url]).read_bytes(), url) if url in routes else None
    get.calls = calls
    return get


def by_id(recs):
    return {r: d for r, d in recs}


def test_ac_list():
    m = mod("ward2n_mumbai")
    p = m.items()[0]["payload"]
    get = fake_get({m.AC_URL: "ac_list.html", m.AREAS_URL: "prabhag_topo.json"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 32 and files
    # the portal gets a browser User-Agent; GitHub gets the session's own
    for url, headers in get.calls:
        if "portal.mcgm.gov.in" in url:
            assert headers and headers["User-Agent"].startswith("Mozilla/5.0 (Windows NT 10.0")
        else:
            assert not headers
    r = by_id(recs)
    d = r["dept:ward2n_mumbai:ac:d"]
    assert d["name"] == "Santosh G. Salunke" and d["name_regional"] == "संतोष गो.साळुंके" and d["level"] == "ward"
    assert d["area"] == "D Ward" and d["admin_ward"] == "D" and d["wards"] == ["214", "215", "216", "217", "218", "219"]
    assert d["since"] == "2025-10-03" and d["last_updated"] == "2026-07-03" and d["local_body_code"] == "251488"
    assert d["role"] == "head" and d["post"] == "Assistant Municipal Commissioner"
    b = r["dept:ward2n_mumbai:ac:b"]
    assert b["name"] == "Jitendra Ghorade" and b["holder_post"] == "Executive Engineer" and b["in_charge"] is True
    assert r["dept:ward2n_mumbai:ac:a"]["name"] == "गजानन बेल्लोळे"          # the page gives only the Marathi name
    assert r["dept:ward2n_mumbai:ac:ps"]["vacant"] is True and "name" not in r["dept:ward2n_mumbai:ac:ps"]
    kn = r["dept:ward2n_mumbai:ac:kn"]
    assert kn["area"] == "K/North Ward" and not kn.get("wards") and "K/E" in kn["wards_note"]
    assert kn["charge"] == "Additional charge with effect from 21.05.2026" and kn["since"] == "2026-05-21"
    assert r["dept:ward2n_mumbai:ac:rs"]["wards"][0] == "19" and r["dept:ward2n_mumbai:ac:rs"]["wards"][-1] == "31"
    assert r["dept:ward2n_mumbai:ac:a"]["wards"] == ["225", "226", "227"]
    enc = r["dept:ward2n_mumbai:ac:removal-of-encroachment-ws"]
    assert enc["level"] == "body" and enc["name"] == "Mridula Ande" and enc["acting"] and enc["post_vacant"] and "vacant" not in enc
    assert r["dept:ward2n_mumbai:ac:hospitals"]["area"] == "Hospitals" and r["dept:ward2n_mumbai:ac:hospitals"]["vacant"]
    wards = [d for d in r.values() if d["level"] == "ward"]
    assert len(wards) == 26 and sum(1 for d in wards if d.get("wards")) == 24   # K/North, P/East: no published prabhags
    assert len({w for d in wards for w in d.get("wards") or []}) == 227


def test_ac_without_layer_and_error_page():
    m = mod("ward2n_mumbai")
    recs, _, why = m.fetch(m.items()[0]["payload"], fake_get({m.AC_URL: "ac_list.html"}))
    assert len(recs) == 32 and why.startswith("no prabhag layer")
    assert all(not d.get("wards") for _, d in recs)

    def err(url, method="GET", data=None, headers=None):
        return Answer(b"<html>Could not open iView. The iView is not compatible with your browser</html>", url)
    assert m.fetch(m.items()[0]["payload"], err)[2] == "portal error page (browser check)"


def test_dmc_helpers():
    m = mod("ward2n_mumbai")
    assert m.zone_of("परिमंडळ-३Zone-III") == "Zone 3" and m.zone_of("परिमंडळ ५") == "Zone 5" and m.zone_of("Solid Waste") is None
    assert m.ward_codes_in("A, B, C, D and E wards") == ["A", "B", "C", "D", "E"]
    assert m.ward_codes_in("F/South, F/North, G/S") == ["F/S", "F/N", "G/S"]
    assert m.ward_code("F/North Ward") == "F/N" and m.ward_code("R/South") == "R/S" and m.ward_code("Estate") is None
    assert m.split_lang("मालमत्ताEstate") == ("मालमत्ता", "Estate")


def test_water_d_ward():
    m = mod("ward2n_mumbai_water")
    p = next(i["payload"] for i in m.items() if i["payload"]["ward"] == "D")
    pdf = "https://portal.mcgm.gov.in/irj/go/km/docs/documents/D%20Ward/Water%20Dept.pdf"
    get = fake_get({p["url"]: "docs_d.html", pdf: "d_water.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and len(recs) == 7
    urls = [u for u, _ in get.calls]
    assert urls[0] == p["url"] and "com.mcgm.WardD" in urls[1] and urls[2] == pdf     # page, its KM frame, then the D-ward file
    assert all(h and h["User-Agent"].startswith("Mozilla/5.0") for _, h in get.calls)
    r = by_id(recs)
    ae = r["dept:ward2n_mumbai_water:d:1"]
    assert ae["post"] == "Assistant Engineer (Water Works)" and ae["post_abbr"] == "A.E. (W)" and ae["name"] == "Prashant V. Bagwe"
    assert ae["phone"] == "9930260470, 9819292591" and ae["email"] == "aeww.d@mcgm.gov.in" and ae["role"] == "head"
    assert ae["wards"] == ["214", "215", "216", "217", "218", "219"] and ae["beats"][0]["whole_ward"] is True
    assert ae["file_created"] == "2022-12-14" and ae["wing"] == "water" and ae["dept"] == "town_body"
    se = r["dept:ward2n_mumbai_water:d:2"]
    assert se["name"] == "Sandesh D. Khedkar" and se["phone"] == "7718825596" and se["email"] == "seww04.d@mcgm.gov.in"
    assert se["wards"] == ["215", "216", "217", "218", "219"] and se["part_wards"] == ["217", "218", "219"]
    assert se["beat_area"].startswith("Mumbai Central, Khetwadi, Part Tardeo")
    je3 = r["dept:ward2n_mumbai_water:d:3"]
    assert je3["maintenance"] is True and len(je3["beats"]) == 2 and je3["beats"][1]["area"] == "Water Maintenance"
    assert je3["beats"][0]["wards"] == ["214", "217", "218", "219"]
    je6 = r["dept:ward2n_mumbai_water:d:6"]          # its "Water Maintenance" beat continues on page 2
    assert je6["name"] == "Apurva R. Chimalwar" and je6["maintenance"] is True and je6["beats"][1]["area"] == "Water Maintenance"
    je7 = r["dept:ward2n_mumbai_water:d:7"]
    assert je7["name"] == "Madhur M. Sagar" and je7["phone"] == "7887434851" and je7["wards"] == ["216", "217", "218"]
    assert "maintenance" not in je7


def test_water_links_and_guesses():
    m = mod("ward2n_mumbai_water")
    html = ('<a href="/irj/go/km/docs/documents/A%20Ward/Water%20Dept.pdf">Water</a>'
            '<a href="&#x2f;irj&#x2f;go&#x2f;km&#x2f;docs&#x2f;documents&#x2f;A Ward&#x2f;Licence.pdf">Licence</a>')
    assert m.water_links(html) == ["https://portal.mcgm.gov.in/irj/go/km/docs/documents/A%20Ward/Water%20Dept.pdf"]
    assert m.guesses("F/N") == ["https://portal.mcgm.gov.in/irj/go/km/docs/documents/FN%20Ward/Water%20Dept.pdf",
                                "https://portal.mcgm.gov.in/irj/go/km/docs/documents/F%20North%20Ward/Water%20Dept.pdf"]
    recs, files, why = m.fetch({"reader": "ward2n_mumbai_water", "url": "x", "ward": "A", "state": "MH"}, fake_get({}))
    assert recs == [] and why.startswith("no water PDF found")


def test_seeds_match_items():
    for name in ("ward2n_mumbai", "ward2n_mumbai_water"):
        seed = json.loads((ROOT / "seeds" / f"dept_{name}.json").read_text())
        assert seed == mod(name).items()
    keys = [i["key"] for i in json.loads((ROOT / "seeds" / "dept_ward2n_mumbai_water.json").read_text())]
    assert len(keys) == 24 and "ward2n_mumbai_water-gs" in keys and "ward2n_mumbai_water-kn" not in keys


def test_water_t_ward_dav_and_maillist():
    """T ward (2026-11-13): no water PDF; the frame names its KM folder, a WebDAV listing (saved: water_t_dav.xml, 21 files) shows
    "MCGM employee email id for Ward T.pdf" (Excel 2013, 2015): its Water Works rows give post-mailbox records."""
    import re
    m = mod("ward2n_mumbai_water")
    p = next(i["payload"] for i in m.items() if i["payload"]["ward"] == "T")
    page = (D / "water_t_page.html").read_text()
    frame = "https://portal.mcgm.gov.in" + m.km_frame(page)
    fr = (D / "water_t_frame.html").read_text(encoding="utf-8", errors="replace")
    assert m.folder_uri(fr) == "/documents/WardWiseInformation/WardT/"
    dav = m.km_url("/irj/go/km/docs/documents/WardWiseInformation/WardT/")
    ents = m.dav_entries((D / "water_t_dav.xml").read_text())
    assert len(ents) == 21 and ("Solid Waste Management", ents[-1][1], True) == ents[-1]
    mail = next(u for n, u, d in ents if "email" in n)
    assert mail.endswith("/WardT/MCGM%20employee%20email%20id%20for%20Ward%20T.pdf")
    get = fake_get({p["url"]: "water_t_page.html", frame: "water_t_frame.html", dav: "water_t_dav.xml", mail: "water_t_maillist.pdf"})
    recs, files, why = m.fetch(p, get)
    assert why == "" and [u for u, _ in get.calls] == [p["url"], frame, dav, mail]
    assert get.calls[2][1]["Depth"] == "1"
    r = by_id(recs)
    assert len(recs) == 5 and all(d["mailbox_list"] and d["wing"] == "water" and not d.get("name") for d in r.values())
    ae = r["dept:ward2n_mumbai_water:t:mail:aeww.t"]
    assert ae["post"] == "Assistant Engineer (Water Works)" and ae["email"] == "aeww.t@mcgm.gov.in" and ae["role"] == "head"
    assert ae["file_created"] == "2015-09-29" and ae["area"] == "T Ward" and ae["src_pos"]["page"] == 1 and ae["src_url"] == mail
    assert {d["email"] for d in r.values()} == {"aeww.t@mcgm.gov.in", "seww01.t@mcgm.gov.in", "seww02.t@mcgm.gov.in",
                                                 "jeww01.t@mcgm.gov.in", "jeww02.t@mcgm.gov.in"}
    # no folder listing (PROPFIND failed): the old "<X> Ward/Water Dept.pdf" guess is tried
    assert re.search(r"no water PDF found: .*/T%20Ward/Water%20Dept.pdf",
                     m.fetch(p, fake_get({p["url"]: "water_t_page.html", frame: "water_t_frame.html"}))[2])
