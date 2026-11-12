"""Archive first: read a page from archive.s1d.me before fetching the live government site (owner, 2026-11-12).

On when the project env has ARCHIVE_FIRST=1 and ARCHIVE_READ_TOKEN (a read-only key: archive /get, /search, /host, never
ingest). For a plain GET (no form data, no extra headers) the pool loop asks the archive for the latest capture of that exact
url with HTTP 2xx, fetched in the last ARCHIVE_MAX_DAYS days (default 30). A hit is returned like a live response (r.url =
the capture's final url); a miss or any archive error falls through to the live site. The records of an item that used a
saved copy carry "archived_at" (the capture time). An item that fails while saved copies were used runs once more fully live
(form postbacks need a live session).
"""
import os

import requests

BASE = "https://archive.s1d.me"


class ArchiveFirst:
    def __init__(self, token, max_days=30, base=BASE):
        self.token, self.max_days, self.base = token, max_days, base.rstrip("/")
        self.s = requests.Session()          # its own session: no cookies of government sites go to the archive, and back
        self.used = []                       # capture times of the hits since the last reset()

    def reset(self):
        self.used = []

    def lookup(self, url):
        """The saved copy of url as a requests.Response, or None (not saved, too old, not 2xx, archive down)."""
        try:
            r = self.s.get(self.base + "/get", params={"url": url, "ok": 1, "max_days": self.max_days},
                           headers={"Authorization": f"Bearer {self.token}"}, timeout=(10, 60))
        except requests.RequestException:
            return None
        if r.status_code != 200 or not r.history:
            return None
        first = r.history[0].headers
        fetched = first.get("X-Archive-Fetched", "")
        r.url = requests.utils.unquote(first.get("X-Archive-Final-Url", "")) or url
        r.from_archive = fetched
        self.used.append(fetched)
        return r


def from_env(env=None):
    env = os.environ if env is None else env
    if env.get("ARCHIVE_FIRST") != "1" or not env.get("ARCHIVE_READ_TOKEN"):
        return None
    try:
        days = int(env.get("ARCHIVE_MAX_DAYS") or 30)
    except ValueError:
        days = 30
    return ArchiveFirst(env["ARCHIVE_READ_TOKEN"], days, env.get("ARCHIVE_BASE") or BASE)


def plain_get(method, data, headers):
    return method.upper() == "GET" and data is None and not headers
