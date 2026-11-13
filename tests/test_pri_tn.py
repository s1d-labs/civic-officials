"""cforms/pri_tn.py: Tamil Nadu rural local body results (tnsec.tn.gov.in rlbe2019), text layer of the mPDF files.
Fixtures: first 3 pages of pdftotext -layout output of 4 Ariyalur 2019 files (fetched 2026-11-13), and the district page."""
import json
from pathlib import Path

from cforms import pri_tn

DATA = Path(__file__).parent / "data" / "pri_tn"
SEEDS = Path(__file__).parents[1] / "seeds"


def recs(name):
    raw = (DATA / f"{name}.txt").read_text()
    p = pri_tn.item("2019", "ari", f"{name}.pdf")["payload"]
    return pri_tn.parse_text(raw), pri_tn.records(pri_tn.parse_text(raw), p)


def test_district_panchayat_members():
    cs, r = recs("dpwm_ari")
    assert len(cs) == 12 and all(c["ctx"]["district"] == "அரியலூர்" for c in cs)
    rid, d = r[0]
    assert rid == "pri:TN:zp:560:w1" and d["type"] == "pri_member" and d["level"] == "zp" and d["lgd_code"] == "560"
    assert d["name"] == "அம்பிகா.ச" and d["party"] == "AIADMK" and d["votes"] == 22975 and d["ward_no"] == "1"
    assert d["reservation"] == "ஆதி திராவிடர் (பெண்கள்)" and d["post"] == "District Panchayat Ward Member"
    assert d["src_pos"]["page"] == 1 and "22975" in d["src_pos"]["line_text"] and d["src_url"].endswith("rlbe2019/dpwm_ari.pdf")
    assert len(d["candidates"]) == 3 and d["electors"] == 48907


def test_union_members_and_page_numbers():
    cs, r = recs("puwm_ari")
    rid, d = r[0]
    assert rid == "pri:TN:ps:6561:w1" and d["body"] == "Ariyalur" and d["name"] == "வெள்ளைச்சாமி.மு" and d["party"] == "AIADMK"
    assert all(" " not in c["ctx"]["union"] for c in cs)      # page numbers do not join the union name


def test_village_presidents_wrapped_label():
    cs, r = recs("vpp_ari")
    by = {d["body_local"]: (rid, d) for rid, d in r}
    rid, d = by["அருங்கால்"]
    assert rid == "pri:TN:gp:226364:head" and d["head"] is True and d["name"] == "கண்ணகி.சி" and d["votes"] == 745
    assert d["block"] == "Ariyalur" and d["block_lgd"] == "6561" and "ward_no" not in d and not d.get("party")
    # label line wrapped over 3 lines: "கிராம ஊராட்சி : ஆண்டிப்பட்டாகாடு [ஆதி திராவிடர்" / union line / "(பெண்கள்)]"
    w = next(c for c in cs if c["ctx"].get("gp", "").startswith("ஆண்டிப்பட்டாகாடு"))
    assert w["ctx"]["gp"] == "ஆண்டிப்பட்டாகாடு" and w["reservation"] == "ஆதி திராவிடர் (பெண்கள்)"
    assert all(len(c["winners"]) == 1 for c in cs[:-1])      # the last contest goes on past the 3 saved pages


def test_village_ward_members_unopposed():
    cs, r = recs("vpwm_ari_ariyal")
    rid, d = r[0]
    assert rid == "pri:TN:gp:226364:w1" and d["unopposed"] is True and d["name"] == "சசிகலா.பா" and d["block"] == "Ariyalur"
    assert d["post"] == "Village Panchayat Ward Member" and "term_note" in d


def test_links_and_seeds():
    names = pri_tn.links((DATA / "rlbe2019_ari.html").read_text())
    assert names[:3] == ["dpwm_ari.pdf", "puwm_ari.pdf", "vpp_ari.pdf"] and len(names) == 9
    items = json.loads((SEEDS / "pri_tn.json").read_text())
    keys = [i["key"] for i in items]
    assert len(keys) == len(set(keys)) == 115 and items[0]["payload"]["kind"] == "seed"
    for i in items[1:]:
        p = i["payload"]
        assert p["kind"] == "form-pri_tn" and p["zp_lgd"] and p["route"] == "proxy" and p["url"].endswith(".pdf")
    assert pri_tn.item("2021", "slm", "vpwm_slm_omalur.pdf")["payload"]["bye_election"] is True
    assert pri_tn.item("2021", "kki", "vpp_kki.pdf")["payload"]["bye_election"] is False
