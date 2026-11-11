"""Shared helpers for the ERO / SRO / water reader tests (test_dept_esw_*.py): fake_get, mod, check_records."""
"""Offline tests of the ERO, sub-registrar and water readers (dforms/ero_*, sro_*, water_*) on small saved answers in tests/data/.
fake_get() answers each URL (and POST) from a saved file, so no test touches the network."""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DATA = Path(__file__).parent / "data"


class Answer:
    """The part of a requests.Response the readers use."""

    def __init__(self, content, url=""):
        self.content = content
        self.url = url
        self.status_code = 200
        self.encoding = "utf-8"

    @property
    def text(self):
        return self.content.decode(self.encoding or "utf-8", "replace")

    def json(self):
        return json.loads(self.content)


def fake_get(routes):
    """routes: {url or (method, url) or callable: saved file name}. A callable key gets (url, method, data) and returns True to match.
    Unknown URLs answer None, as get() does on an error."""
    calls = []

    def get(url, method="GET", data=None, headers=None):
        calls.append((method, url, data))
        for k, name in routes.items():
            if (callable(k) and k(url, method, data)) or k == url or k == (method, url):
                return Answer((DATA / name).read_bytes(), url)
        return None
    get.calls = calls
    return get


def mod(name):
    return importlib.import_module("dforms." + name)


def check_records(recs, module, dept):
    """Every record follows depts.py: id prefix, type, dept, a level, a source; ids are unique."""
    ids = [r for r, _ in recs]
    assert len(ids) == len(set(ids)), "duplicate record ids"
    for rid, d in recs:
        assert rid.startswith(f"dept:{module}:"), rid
        assert d["type"] == "dept_office" and d["dept"] == dept and d.get("level") and d.get("source") and d.get("state"), d
        assert d.get("name") or d.get("phone") or d.get("email"), d
