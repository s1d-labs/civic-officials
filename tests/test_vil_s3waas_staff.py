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
    assert why == "" and len(staff) == 88 and len(src) == 1 and len(files) == 1
    check_records(staff, M, "rural_development")
    assert sum(1 for _, d in staff if d.get("name")) == 87 and sum(1 for _, d in staff if d.get("phone")) == 83
    assert sum(1 for _, d in staff if d.get("lgd_gp_code")) == 81
    assert src[0]["rows"] == 88 and src[0]["src_sha256"] and "NAGARKURNOOL" in src[0]["title"]
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


def _file(name):
    m = mod(M)
    return m, [d for _, d in m.file_records((ROOT / f"tests/data/vil/tg_mahabubnagar_ps_{name}.pdf").read_bytes(), PDF,
                                            _payload("mahabubnagar"), "t", "PS list")]


def test_gp_and_name_in_one_cell_nagarkurnool():
    """The G.P. cell holds the secretary's name too ("13 Remaddula   P.Bal Raj" with the page shifted left): split at the LGD
    G.P. name of the mandal (Pangal: Remuddula), so the G.P. ties (2026-11-14)."""
    m, r = _file("nagarkurnool")
    d = next(x for x in r if "Remaddula" in x["src_pos"]["line_text"])
    assert (d["area"], d["name"], d["cadre"], d["lgd_gp_code"], d["lgd_block_code"]) == \
        ("Remaddula", "P.Bal Raj", "Contract", "205808", "5586")
    d = next(x for x in r if "Adula" in x["src_pos"]["line_text"])
    assert (d["area"], d["name"], d["mandal"]) == ("Adula", "M.Hanmanthu", "Gopalpet")
    assert m.gp_of("TG", {"5586"}, "Peddagudem Tanda")[0] == ""
    assert m.skel("Alampoor") == m.skel("Alampur") and m.skel("Achampet") == m.skel("Achampeta")


def test_three_line_header_mahabubnagar():
    """Header "Name of the Mandal / Name of the Panchayat Secretary / Designation / Name of the Regular G.P. / Name of the
    Incharge Gram Panchayats / Cell Number": the header-word reader took the incharge G.P.s as names (104 rows)."""
    m, r = _file("mahabubnagar")
    assert len(r) == 151 and sum(1 for d in r if d.get("name")) == 151 and sum(1 for d in r if d.get("phone")) == 146
    assert sum(1 for d in r if d.get("lgd_gp_code")) == 120 and sum(len(d.get("gps_additional") or []) for d in r) == 267
    d = r[0]
    assert (d["name"], d["area"], d["mandal"], d["cadre"], d["phone"], d["gps_additional"]) == \
        ("Smt.Thirupathamma", "Dasarpally", "Addakal", "Contract", "9603307065", ["Vemula", "Rachala"])
    assert r[1]["lgd_gp_code"] == "204769" and r[1]["lgd_gp_how"].startswith("G.P. name in the LGD districts")


def test_additional_gps_lines_gadwal_narayanpet():
    """"Additional G.P.s allotted" on own lines (Gadwal: same phone on each line; Narayanpet: lines above and below the
    secretary's line) go to the secretary, not to new records."""
    m, r = _file("gadwal")
    assert len(r) == 99 and sum(1 for d in r if d.get("name")) == 96 and sum(1 for d in r if d.get("lgd_gp_code")) == 70
    assert sum(len(d.get("gps_additional") or []) for d in r) == 203
    assert r[1]["name"] == "M.Dastagiri" and r[1]["gps_additional"] == ["Sulthanpur", "Konair", "Bukkapur", "Imampur"]
    m, r = _file("narayanpet")
    assert len(r) == 85 and sum(1 for d in r if d.get("name")) == 84 and sum(1 for d in r if d.get("lgd_gp_code")) == 59
    assert sum(len(d.get("gps_additional") or []) for d in r) == 240
    d = r[3]
    assert (d["name"], d["area"], d["cadre"], d["gps_additional"]) == \
        ("Sri.Shyam Sunder Reddy", "Khanapur", "Rediployeement", ["Amarachintha", "Nandimalla'X'Road", "Pinnamcherla"])
