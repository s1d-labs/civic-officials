"""dforms/_state.py: post ranks, department keys, division -> districts, the record shape. No network."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dforms import _state  # noqa: E402


def test_post_kind():
    pk = _state.post_kind
    assert pk("Chief Secretary") == "chief_secretary"
    assert pk("Additional Chief Secretary, Home") == "acs"
    assert pk("Principal Secretary to Govt.") == "principal_secretary"
    assert pk("Secretary, Finance") == "secretary"
    assert pk("Joint Secretary") == "joint_secretary"
    assert pk("Director General of Police") == "dgp"
    assert pk("ADGP Law & Order") == "adgp"
    assert pk("IGP, Jalandhar Range") == "igp"
    assert pk("DIG Border Range") == "dig"
    assert pk("Commissioner of Police, Ludhiana") == "cp"
    assert pk("Divisional Commissioner, Patiala") == "divisional_commissioner"
    assert pk("State Election Commissioner") == "state_election_commissioner"
    assert pk("State Chief Information Commissioner") == "chief_information_commissioner"
    assert pk("Director, Health Services") == "head_of_department"
    assert pk("Typist") == ""


def test_dept_key():
    assert _state.dept_key("Department of Water Resources") == "water"
    assert _state.dept_key("Home Department") == "administration"
    assert _state.dept_key("Police Headquarters") == "police"
    assert _state.dept_key("State Election Commission") == "elections"
    assert _state.dept_key("") == "other"


def test_rec_shape():
    rid, d = _state.rec("st_xx", "cs", state="PB", level="state", post="Chief Secretary", name="Sh. A B, IAS",
                        body="Punjab Civil Secretariat", body_kind="secretariat", phone="0172-2740156",
                        src_url="https://x/", src_pos={"table": 1, "row": 2})
    assert rid == "dept:st_xx:cs"
    assert d["type"] == "dept_office" and d["level"] == "state" and d["area"] == "Punjab" and d["state_code"] == "3"
    assert d["post_kind"] == "chief_secretary" and d["service"] == "IAS" and d["name"] == "Sh. A B, IAS"
    assert d["src_pos"] == {"table": 1, "row": 2} and d["source"] == "https://x/"
    _, v = _state.rec("st_xx", "v", state="PB", level="state", post="Secretary", name="Vacant")
    assert v.get("vacant") is True and "name" not in v
