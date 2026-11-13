"""State-level readers of fork WEST (Goa, Gujarat, Maharashtra): saved pages and files only, no network."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import _field, st_ga_portal, st_ga_teldir, st_gj_police_hq, st_mh_divcom, st_mh_police_emails  # noqa: E402
from dforms.police_gj import contact, orgchart  # noqa: E402

DATA = Path(__file__).parent / "data"


def html(name):
    return (DATA / name).read_text(encoding="utf-8")


class Resp:
    def __init__(self, content, url=""):
        self.content, self.url, self.status_code = content, url, 200
        self.text = content.decode("utf-8", "replace")


def by_id(recs):
    return {k: d for k, d in recs}


def test_ga_secretaries_cards():
    recs = by_id(st_ga_portal.parse(html("st_ga_secretaries.html"), "secretaries", st_ga_portal.URLS["secretaries"]))
    assert len(recs) == 16
    cs = recs["dept:st_ga_portal:secretaries:1"]
    assert cs["post_kind"] == "chief_secretary" and cs["level"] == "state" and cs["state_code"] == "30"
    assert cs["name"] == "Dr. V. Candavelou, IAS (1997)" and cs["service"] == "IAS"
    assert "cs-goa@nic.in" in cs["email"] and "0832-2419401" in cs["phone"]
    assert cs["portfolios"][:2] == ["Vigilance/ Chief Vigilance Officer", "Home"]
    assert cs["src_pos"] == {"card": 1} and cs["src_url"] == st_ga_portal.URLS["secretaries"]
    rev = recs["dept:st_ga_portal:secretaries:2"]
    assert rev["department"] == "Revenue" and rev["dept"] == "revenue" and rev["post_kind"] == "secretary"


def test_ga_deptdir_cards():
    recs = st_ga_portal.parse(html("st_ga_deptdir_excerpt.html"), "deptdir", st_ga_portal.URLS["deptdir"])
    assert len(recs) == 7
    first = recs[0][1]
    assert first["name"] == "Shri. Puneet Kumar Goel, IAS" and first["department"] == "Administrative Reforms Department"
    assert first["email"] == "cs-goa@nic.in" and first["phone"] == "08322419659" and first.get("fax")
    us = recs[2][1]
    assert us["post_kind"] == "under_secretary" and "9767240186" in us["phone"]


def test_ga_hod_table():
    recs = st_ga_portal.parse(html("st_ga_hod.html"), "hod", st_ga_portal.URLS["hod"])
    assert len(recs) == 193
    d = by_id(recs)["dept:st_ga_portal:hod:4"]
    assert d["body"] == "Bal Bhavan" and d["post"] == "Director" and d["email"] == "goabalbhavan@yahoo.in"
    assert d["src_pos"] == {"table": 1, "row": 4} and len(d["cells"]) == 4
    assert any(x["district_code"] == "551" for _, x in recs if x.get("district_code"))


def test_ga_teldir_saves_file_once():
    recs, files, why = st_ga_teldir.fetch({"url": st_ga_teldir.URL, "pages": 278}, lambda u, **k: Resp(b"%PDF-1.6 x", u))
    assert why == "" and files[0][0] == "depts/st_ga_teldir/teldir2023.pdf"
    assert recs[0][1]["type"] == "source_file" and recs[0][1]["ocr_needed"] is True


def test_gj_police_hq_chart():
    chart = orgchart(html("st_gj_dgp_orgchart.html"))
    pages = {d: ("u" + d, contact(html(f"st_gj_dgp_{d}.html"))) for d in ("636", "733")}
    recs = by_id(st_gj_police_hq.build(chart, pages))
    assert len(recs) == 79
    dgp = recs["dept:st_gj_police_hq:636"]
    assert dgp["level"] == "state" and dgp["post_kind"] == "dgp" and dgp["email"] == "dgp-gs@gujarat.gov.in"
    assert "9978406277" in dgp["phone"] and dgp["service"] == "IPS"
    ahd = recs["dept:st_gj_police_hq:733"]
    assert ahd["level"] == "division" and ahd["division"] == "Ahmedabad Range" and ahd["districts"] == ["438", "440", "450"]
    assert ahd["post_kind"] == "igp" and ahd["name"] == "શ્રી રાઘવેન્દ્ર વત્સ"
    assert recs["dept:st_gj_police_hq:734"]["post_kind"] == "dig"
    sp = recs["dept:st_gj_police_hq:3189"]
    assert sp["level"] == "district" and sp["district_code"] == "675" and sp["division"] == "Junagadh Range" and "districts" not in sp
    assert recs["dept:st_gj_police_hq:729"]["post_kind"] == "cp" and recs["dept:st_gj_police_hq:729"]["district_code"] == "438"
    assert recs["dept:st_gj_police_hq:114489"]["level"] == "state"      # SP technical services, Gandhinagar: a HQ post
    assert recs["dept:st_gj_police_hq:13707"]["districts"] == ["454", "445", "669"]   # from st_div_gj.json (SPs not nested)


def test_mh_divcom_tables():
    url = "https://divcomnashik.maharashtra.gov.in/en/directory/"
    recs = st_mh_divcom.parse(html("st_mh_divcom_nashik_directory.html"), "Nashik", url)
    div = [d for _, d in recs if d["level"] == "division"]
    dist = [d for _, d in recs if d["level"] == "district"]
    assert len(div) == 22 and len(dist) == 15
    assert div[0]["post_kind"] == "divisional_commissioner" and div[0]["districts"] == ["487", "474", "486", "478", "466"]
    assert div[0]["email"] == "divcom.nashik@maharashtra.gov.in" and div[0]["src_pos"] == {"table": 1, "row": 2}
    col = next(d for d in dist if d["post"] == "Collector, Ahilyanagar")
    assert col["district_code"] == "466" and col["dept"] == "administration" and col["division"] == "Nashik"
    pune = st_mh_divcom.parse(html("st_mh_divcom_pune_whoswho.html"), "Pune",
                              "https://divcompune.maharashtra.gov.in/en/whos-who/")
    assert len(pune) == 28 and sum(1 for _, d in pune if d.get("district_code") == "494") == 2   # Satara collector + ZP CEO
    csn = st_mh_divcom.parse(html("st_mh_divcom_csn_whoswho.html"), "Chhatrapati Sambhajinagar",
                             "https://divcomcsn.maharashtra.gov.in/whos-who/")
    assert len(csn) == 12 and len(csn[0][1]["districts"]) == 8


def test_mh_police_email_lists():
    ig = st_mh_police_emails.parse(_field.pdf_text((DATA / "st_mh_police_igcontact3.pdf").read_bytes()),
                                   st_mh_police_emails.BASE + "igcontact3.pdf")
    assert len(ig) == 8
    aur = by_id(ig)["dept:st_mh_police_emails:igcontact3:2"]
    assert aur["post"] == "IG, AURANGABAD RANGE, AURANGABAD" and aur["level"] == "division"
    assert aur["districts"] == ["469", "479", "470"] and aur["email"] == "ig.aurangabadrange@mahapolice.gov.in"
    assert aur["src_pos"]["page"] == 1 and "AURANGABAD" in aur["src_pos"]["line_text"]
    dgp = st_mh_police_emails.parse(_field.pdf_text((DATA / "st_mh_police_dgp_office.pdf").read_bytes()),
                                    st_mh_police_emails.BASE + st_mh_police_emails.FILES[0])
    d = by_id(dgp)
    assert len(dgp) == 93 and d["dept:st_mh_police_emails:68668baee3e1:1"]["post_kind"] == "dgp"
    assert d["dept:st_mh_police_emails:68668baee3e1:10"]["email"].count("@") == 3
    assert d["dept:st_mh_police_emails:68668baee3e1:23"]["level"] == "state"
    assert d["dept:st_mh_police_emails:68668baee3e1:s2:10"]["post"] == "Desk - 1A"


def test_seeds_name_readers_and_routes():
    for st in ("ga", "gj", "mh"):
        items = json.loads((ROOT / "seeds" / f"dept_st_{st}.json").read_text())
        assert items and len({i["key"] for i in items}) == len(items)
        for i in items:
            p = i["payload"]
            assert (ROOT / "dforms" / f"{p['reader']}.py").exists() and p["route"] in ("abroad", "proxy", "direct")
            assert p["state"] == st.upper()
    for m in (st_ga_portal, st_ga_teldir, st_gj_police_hq, st_mh_divcom, st_mh_police_emails):
        assert m.METHOD
