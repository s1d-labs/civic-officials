"""State lists of urban body officials (dforms/ulb_<xx>.py): the checks that hold for every state. Each reader's own offline test
on its saved sample is tests/test_ulb_<xx>.py."""
import json

from esw_common import ROOT, mod
from dforms import _ulb


def test_seed_files():
    """Every seeds/dept_ulb_<xx>.json: unique keys that start with the module, its own reader, a url (or a seed kind) and a state."""
    every = []
    files = sorted((ROOT / "seeds").glob("dept_ulb_*.json"))
    assert files
    for f in files:
        m = f.stem[len("dept_"):]
        items = json.loads(f.read_text())
        keys = [i["key"] for i in items]
        every += keys
        assert items and len(keys) == len(set(keys)), f
        assert all(k.startswith(m) and len(k) <= 200 for k in keys), f
        for i in items:
            p = i["payload"]
            if p.get("kind") == "seed":
                assert p.get("module") == m and hasattr(mod(m), "items"), (f, i)
                continue
            assert p.get("reader") == m and p.get("url") and p.get("state"), (f, i)
            assert isinstance(p.get("india_only", False), bool), (f, i)
        assert hasattr(mod(m), "fetch"), m
    assert len(every) == len(set(every))


def test_role_of():
    cases = {"Executive Officer": "head", "E.O.": "head", "Chief Officer": "head", "C.M.O.": "head", "CEO": "head",
             "Municipal Commissioner": "head", "Secretary": "head", "अधिशासी अधिकारी": "head", "प्र0 अधि0 अधिकारी": "head",
             "नगर आयुक्त": "head", "Chairman": "chair", "Chairperson": "chair", "Mayor": "chair", "अध्यक्ष": "chair",
             "Vice Chairman": "deputy", "Deputy Mayor": "deputy", "उपाध्यक्ष": "deputy", "Deputy Commissioner": "deputy",
             "Addl. Commissioner": "deputy", "प्रभारी सहायक नगर आयुक्त": "deputy", "Ward Commissioner": "member",
             "Councillor": "member", "पार्षद": "member", "Assistant Engineer(Civil)": "staff", "Junior Assistant": "staff",
             "Health Officer": "staff", "Office": "staff"}
    for post, role in cases.items():
        assert _ulb.role_of(post) == role, (post, _ulb.role_of(post))


def test_record_ids_latin():
    """Two Hindi bodies with the same post get different ids when the reader gives a Latin form."""
    seen = set()
    a = _ulb.record("ulb_up", "UP", "आगरा", "नगर आयुक्त", seen, latin="agra", source="https://x")
    b = _ulb.record("ulb_up", "UP", "मथुरा", "नगर आयुक्त", seen, latin="mathura", source="https://x")
    assert a[0] != b[0] and a[1]["office_id"] != b[1]["office_id"]
    assert a[1]["dept"] == "town_body" and a[1]["level"] == "body" and a[1]["area"] == "आगरा" and a[1]["role"] == "head"
