"""Offline tests of dforms/vil_s3waas_staff.py (AP / TG district portal village staff lists) on saved answers in tests/data/vil/."""
import json

from esw_common import ROOT, check_records, fake_get, mod

M = "vil_s3waas_staff"
PDF = "https://cdn.s3waas.gov.in/s3e00da03b685a0dd18fb6a08af0923de0/uploads/2018/03/2018031521.pdf"


def _payload(d):
    return next(i["payload"] for i in mod(M).items() if i["key"] == f"{M}:{d}")


def test_seeds():
    m = mod(M)
    seeds = json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())
    assert seeds == m.items() and len(seeds) == 58 and len({s["key"] for s in seeds}) == 58
    assert sum(s["payload"]["state"] == "TG" for s in seeds) == 33 and m.METHOD
    assert all(s["payload"]["route"] == "abroad" and not s["payload"]["india_only"] for s in seeds)


def test_menu_links_mahabubnagar():
    m = mod(M)
    p = _payload("mahabubnagar")
    links = [u for u, _ in m.menu_links((ROOT / "tests/data/vil/tg_mahabubnagar_home.html").read_text(), p["url"])]
    assert "https://mahabubnagar.telangana.gov.in/panchayat/" in links[:3] and len(links) <= m.MAX_PAGES
    assert not any("tender" in u or "/te/" in u for u in links)


def test_flow_mahabubnagar_ps_list():
    m = mod(M)
    p = _payload("mahabubnagar")
    get = fake_get({p["url"]: "vil/tg_mahabubnagar_home.html",
                    "https://mahabubnagar.telangana.gov.in/panchayat/": "vil/tg_mahabubnagar_panchayat.html",
                    PDF: "vil/tg_mahabubnagar_ps_nagarkurnool.pdf"})
    recs, files, why = m.fetch(p, get)
    staff = [(r, d) for r, d in recs if d["type"] == "dept_office"]
    src = [d for r, d in recs if d["type"] == "source_file"]
    assert why == "" and len(staff) == 86 and len(src) == 1 and len(files) == 1
    check_records(staff, M, "rural_development")
    assert sum(1 for _, d in staff if d.get("name")) == 65 and sum(1 for _, d in staff if d.get("phone")) == 83
    assert src[0]["rows"] == 86 and src[0]["src_sha256"] and "NAGARKURNOOL" in src[0]["title"]
    d = dict(staff)
    r = next(v for v in d.values() if v.get("name") == "V.Venkateswarlu")
    assert r["phone"] == "9640754909" and r["area"] == "Rangapur" and r["mandal"] == "Achampet" and r["cadre"] == "V.D.O.Gr.I"
    assert r["level"] == "gram_panchayat" and r["post"] == "Panchayat Secretary" and r["state"] == "TG"
    assert r["gps_listed_before"] == ["Singaram", "Devla Thanda", "Inole", "Puljala", "Chennaram"]
    assert r["src_url"] == PDF and r["src_pos"]["page"] == 1 and "V.Venkateswarlu" in r["src_pos"]["line_text"]
    a = next(v for v in d.values() if v.get("phone") == "9493320213")
    assert a["mandal"] == "Amrabad" and not a.get("gps_listed_before")      # a new mandal starts a new cluster
    assert all(k.startswith(f"dept:{M}:mahabubnagar.telangana.gov.in:") for k in d)


def test_no_list():
    m = mod(M)
    p = _payload("mahabubnagar")
    recs, files, why = m.fetch(p, fake_get({p["url"]: "vil/tg_mahabubnagar_home.html"}))
    assert recs == [] and files == [] and why.startswith("no staff list")
