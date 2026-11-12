import requests

import archive_first


class FakeSession:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        if self.exc:
            raise self.exc
        return self.resp


def resp(status, body=b"", history_headers=None):
    r = requests.Response()
    r.status_code, r._content, r.url = status, body, "https://b2.example/x"
    if history_headers is not None:
        h = requests.Response()
        h.status_code, h.headers = 307, requests.structures.CaseInsensitiveDict(history_headers)
        r.history = [h]
    return r


def test_from_env_needs_flag_and_key():
    assert archive_first.from_env({}) is None
    assert archive_first.from_env({"ARCHIVE_FIRST": "1"}) is None
    assert archive_first.from_env({"ARCHIVE_READ_TOKEN": "k"}) is None
    af = archive_first.from_env({"ARCHIVE_FIRST": "1", "ARCHIVE_READ_TOKEN": "k", "ARCHIVE_MAX_DAYS": "x"})
    assert af.max_days == 30 and af.token == "k"


def test_plain_get_only():
    assert archive_first.plain_get("GET", None, None)
    assert not archive_first.plain_get("POST", None, None)
    assert not archive_first.plain_get("GET", {"a": 1}, None)
    assert not archive_first.plain_get("GET", None, {"X-Requested-With": "XMLHttpRequest"})


def test_hit_sets_url_and_time():
    af = archive_first.ArchiveFirst("k")
    af.s = FakeSession(resp(200, b"<html>ok</html>", {"X-Archive-Fetched": "2026-11-12T21:55:14+05:30",
                                                         "X-Archive-Final-Url": "https://a.gov.in/p%20q"}))
    r = af.lookup("https://a.gov.in/p q")
    assert r.text == "<html>ok</html>" and r.url == "https://a.gov.in/p q"
    assert af.used == ["2026-11-12T21:55:14+05:30"]
    url, params, headers = af.s.calls[0]
    assert url.endswith("/get") and params["ok"] == 1 and params["max_days"] == 30 and headers["Authorization"] == "Bearer k"
    af.reset()
    assert af.used == []


def test_miss_and_errors_fall_through():
    af = archive_first.ArchiveFirst("k")
    af.s = FakeSession(resp(404))
    assert af.lookup("https://a.gov.in/") is None
    af.s = FakeSession(resp(200, b"x"))           # 200 without a redirect: not an archive copy
    assert af.lookup("https://a.gov.in/") is None
    af.s = FakeSession(exc=requests.ConnectionError("down"))
    assert af.lookup("https://a.gov.in/") is None
    assert af.used == []
