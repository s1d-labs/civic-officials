"""cforms/_pri.py: record shape and LGD matching (extracts in cforms/pri_lgd/)."""
from cforms import _pri


def test_record_shape():
    rid, d = _pri.record("KL", "gp", lgd_code="221003", body="Pallippad", district="Alappuzha", post="President", name="A B",
                         head=True, election="Kerala 2025", url="https://x/")
    assert rid == "pri:KL:gp:221003:head" and d["type"] == "pri_member" and d["level"] == "gp"
    rid, d = _pri.record("TN", "gp", body="X", district="Salem", block="Omalur", ward_no=" 3 ", name="C")
    assert rid == "pri:TN:gp:salem~omalur~x:w3" and d["lgd_code"] == "" and d["ward_no"] == "3"


def test_lgd_match_kerala():
    lgd = _pri.Lgd("KL")
    assert lgd.match("zp", "Alappuzha District Panchayat") == "509"
    assert lgd.match("gp", "Pallippad Grama Panchayat", district="Alappuzha") == "221003"
    assert lgd.match("gp", "") == ""


def test_helpers():
    assert _pri.digits("12") == "12" and _pri.digits("12a") == ""
    assert _pri.phone("Mob: 94470 12345 / 0471-2345678") == "9447012345, 04712345678"
    assert _pri.level_of("Mandal Panchayat") == "ps" and _pri.level_of("Commune Panchayat") == "ps"


def test_norm_keeps_indic_letters_and_matches_local_names():
    from cforms import _pri
    assert _pri.norm("Café") == "cafe"
    assert _pri.norm("अंबीटखींड") and _pri.norm("அங்கலக்குறிச்சி")
    assert _pri.norm("अंबीटखींड") != _pri.norm("அங்கலக்குறிச்சி")
