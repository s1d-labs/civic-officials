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


class AnyTLS(HTTPAdapter):
    """Last resort for a server whose certificate fails the check (expired, missing intermediate, self-signed, old ciphers):
    no certificate or host name check, legacy renegotiation and old ciphers allowed. The owner allowed this on 2026-11-11.
    Use it only with verify=False on the request, and mark what it fetched (tls_unverified)."""

    def init_poolmanager(self, *a, **kw):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        try:
            ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except (ssl.SSLError, ValueError):
            pass
        kw["ssl_context"] = ctx
        return super().init_poolmanager(*a, **kw)


def insecure_retry(s, url, method="GET", **kw):
    """The same request once more without certificate checks (AnyTLS for this host). Records the host in s.unverified_hosts."""
    import urllib3
    from urllib.parse import urlsplit
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    host = urlsplit(url).hostname
    s.mount(f"https://{host}/", AnyTLS())
    if not hasattr(s, "unverified_hosts"):
        s.unverified_hosts = set()
    s.unverified_hosts.add(host)
    return s.request(method, url, verify=False, **kw)


def session(legacy_host=None):
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.verify = trust()
    if legacy_host:
        s.mount(f"https://{legacy_host}/", LegacyTLS())
    return s


def keep_trail(new, old):
    """A reader that starts its own session (one per AC, no caller cookies) keeps the caller session's response hooks, so the
    source trail (provenance.hook, set by blo.run_form) still notes every answer. Returns new."""
    for h in (getattr(old, "hooks", None) or {}).get("response", []):
        if h not in new.hooks["response"]:
            new.hooks["response"].append(h)
    return new


def hidden(html):
    soup = BeautifulSoup(html, "lxml")
    return {i.get("name"): i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}


def options(html, select_name_end):
    soup = BeautifulSoup(html, "lxml")
    sel = next((s for s in soup.find_all("select") if (s.get("name") or "").endswith(select_name_end)), None)
    return [(o.get("value"), " ".join(o.get_text(" ", strip=True).split())) for o in (sel.find_all("option") if sel else [])
            if o.get("value") not in (None, "", "0", "-1")]
