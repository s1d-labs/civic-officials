"""Shared helpers for ASP.NET WebForms pages."""
import ssl

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from certs_trust import trust

UA = "s1d-labs-public-records/1.0 (+https://labs.s1d.me)"


class LegacyTLS(HTTPAdapter):
    """For servers that still need TLS legacy renegotiation (OpenSSL 3 turns it off). Certificate checks stay on."""

    def init_poolmanager(self, *a, **kw):
        ctx = ssl.create_default_context(cafile=trust() if trust() is not True else None)
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        kw["ssl_context"] = ctx
        return super().init_poolmanager(*a, **kw)


def session(legacy_host=None):
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.verify = trust()
    if legacy_host:
        s.mount(f"https://{legacy_host}/", LegacyTLS())
    return s


def hidden(html):
    soup = BeautifulSoup(html, "lxml")
    return {i.get("name"): i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}


def options(html, select_name_end):
    soup = BeautifulSoup(html, "lxml")
    sel = next((s for s in soup.find_all("select") if (s.get("name") or "").endswith(select_name_end)), None)
    return [(o.get("value"), " ".join(o.get_text(" ", strip=True).split())) for o in (sel.find_all("option") if sel else [])
            if o.get("value") not in (None, "", "0", "-1")]
