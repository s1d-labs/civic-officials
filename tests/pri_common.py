"""Shared helpers for the PRI elected-member reader tests (tests/test_pri_*.py): fake_get, mod and check_pri."""
from esw_common import DATA, ROOT, fake_get, mod  # noqa: F401


def check_pri(recs, module, state):
    """Every record follows dforms/_pri.py: id prefix, type, state, level, role, post, a name, a source, a position; ids unique."""
    assert recs, "no records"
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"pri:{module}:"), rid
        assert d["type"] == "pri_member" and d["state"] == state, d
        assert d["level"] in ("zp", "ps", "gp") and d["role"] in ("head", "deputy", "member"), d
        assert d.get("post") and d.get("name") and d.get("source") and d.get("election"), d
        assert d.get("src_pos"), d
        if "votes" in d:
            assert isinstance(d["votes"], int), d
