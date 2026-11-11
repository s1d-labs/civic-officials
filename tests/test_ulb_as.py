"""Offline test of the Assam urban body reader (dforms/ulb_as.py): assamurban.in body sites, office-staff + members pages."""
from esw_common import *  # noqa: F401,F403

M = "ulb_as"


def _seed(key):
    return next(i for i in json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text()) if i["key"] == key)


def test_ulb_as_items_match_seed():
    assert mod(M).items() == json.loads((ROOT / "seeds" / f"dept_{M}.json").read_text())
    assert len(mod(M).items()) == 103


def test_ulb_as_office_staff_and_footer():
    p = _seed("ulb_as-silchar")["payload"]
    get = fake_get({p["url"]: "ulb_as_silchar_office_staff.html", p["members"]: "ulb_as_silchar_members.html"})
    recs, files, why = mod(M).fetch(p, get)
    assert why == "" and len(files) == 2 and files[0][0].startswith(f"depts/{M}/")
    check_records(recs, M, "town_body")
    recs = dict(recs)
    eo = recs["dept:ulb_as:AS-cachar-silchar-executive-officer"]
    assert eo["area"] == "Silchar" and eo["body_type"] == "Municipal Corporation" and eo["list_name"] == "Silchar Municipal Corporation" and eo["district"] == "Cachar" and eo["role"] == "head"
    assert eo["name"] == "SRI NABUTTOM SHARMA , AUS." and eo["phone"] == "8486970495" and eo["section"] == "GENERAL ADMINISTRATION"
    assert eo["office_phone"] == "03842-233830" and eo["office_email"] == "smb1882@gmail.com" and "788001" in eo["address"]
    os_ = recs["dept:ulb_as:AS-cachar-silchar-office-superintendent-i-c-general-administration"]
    assert os_["name"] == "SRI RAJENDRA LAL SINGH." and os_["phone"] == "9435986933"       # "Office Staff": post from the last line
    ha = recs["dept:ulb_as:AS-cachar-silchar-head-assistant"]
    assert ha["ward"] == "07" and ha["section"] == "HEAD ASSISTANT CUM ACCOUNTANTS"
    assert len(recs) == 4                                                              # "No members found."


def test_ulb_as_members_chair_only():
    p = _seed("ulb_as-tihu")["payload"]
    get = fake_get({p["url"]: "ulb_as_silchar_office_staff.html", p["members"]: "ulb_as_tihu_members.html"})
    recs, _, why = mod(M).fetch(p, get)
    check_records(recs, M, "town_body")
    recs = dict(recs)
    ch = recs["dept:ulb_as:AS-nalbari-tihu-chairman"]
    assert ch["role"] == "chair" and ch["name"] == "Smti. Himani Mazumdar" and ch["phone"] == "8474871701" and ch["ward"] == "2"
    assert ch["source"] == "https://tihu.assamurban.in/members"
    assert recs["dept:ulb_as:AS-nalbari-tihu-vice-chairman"]["role"] == "deputy"
    assert not [d for d in recs.values() if "Ward Commissioner" in d["post"]]            # ward councillors are left out


def test_ulb_as_no_answer():
    p = _seed("ulb_as-tihu")["payload"]
    assert mod(M).fetch(p, fake_get({})) == ([], [], "no answer")


def test_ulb_as_split_type():
    st = mod(M).split_type
    assert st("Lakhipur MB(Cachar)") == ("Lakhipur (Cachar)", "MB") and st("Barpeta Rd.MB") == ("Barpeta Rd.", "MB")
    assert st("Sapatgram  MB") == ("Sapatgram", "MB") and st("Silchar Municipal Corporation") == ("Silchar", "Municipal Corporation")
