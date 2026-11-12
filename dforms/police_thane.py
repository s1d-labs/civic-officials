"""Thane Police Commissionerate (36 stations), thanepolice.gov.in (Next.js, rebuilt Nov 2026). Works from outside India.
Station list: the site's own public server action getStationsPublic: POST https://thanepolice.gov.in/en with the header
Next-Action: <action id> and the body [] -> React Server Components text; line "1:" is a JSON array
(id, name, nameMr, address, addressMr, latitude, longitude, contactNo, zone). The action id changes with each deploy, so it is
read again from the site's JS chunks (createServerReference("<id>", ..., "getStationsPublic")) of /en/about/jurisdiction-map;
payload "action_id" is the fallback. Officer: GET /en/about/jurisdiction-map/<id> (server rendered): "Shri. NAME - MOBILE",
then the rank. One queue item = the whole list (~60 requests). Record id dept:police_thane:<station uuid>."""
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import provenance
from dforms._police import clean, gz, phones, rec, uniq

METHOD = "json (Next.js server action) + html text (officer line)"     # source trail (provenance.py): how this reader reads its sources

M = "police_thane"
BASE = "https://thanepolice.gov.in"
MAP = BASE + "/en/about/jurisdiction-map"
ACTION_RE = re.compile(r"""["']([0-9a-f]{40,44})["'][^"';]{0,300}?["']getStationsPublic["']""")


def chunks(html):
    """Script urls of a Next.js page, in page order (src attributes and those named in the flight data)."""
    out = []
    for m in re.finditer(r"""(/_next/static/[^"'\\\s]+?\.js)""", html):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def action_id(get, page_html):
    for c in chunks(page_html):
        r = get(urljoin(BASE, c))
        if r is None:
            continue
        m = ACTION_RE.search(r.text)
        if m:
            return m.group(1)
    return None


def stations(rsc):
    """The JSON array on the line that starts '1:' of the server-action answer."""
    for line in rsc.splitlines():
        if line.startswith("1:"):
            try:
                js = json.loads(line[2:])
            except ValueError:
                return []
            return js if isinstance(js, list) else []
    return []


def officer(html):
    """(name, mobile, rank) from a station page: 'Shri. Shabbir Sayyed - 8007965786' then 'Senior Inspector of Police'."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    tok = [clean(s) for s in soup.stripped_strings]
    for i, t in enumerate(tok):
        m = re.match(r"^((?:Shri|Smt|Sau|Kum|Mr|Mrs|Ms)\.?\s.+?)\s*-\s*([\d\s+]{10,})$", t or "")
        if m:
            rank = next((u for u in tok[i + 1:i + 3] if u and re.search(r"(?i)inspector|police|officer", u)), None)
            return m.group(1), phones(m.group(2)), rank
    return None, None, None


def fetch(p, get):
    files, why = [], []
    page = get(p.get("url", MAP))
    aid = action_id(get, page.text) if page is not None else None
    if not aid:
        why.append("action id not found in the JS chunks; used the payload's")
        aid = p.get("action_id")
    if not aid:
        return [], files, "; ".join(why) or "no action id"
    r = get(BASE + "/en", method="POST", data="[]",
            headers={"Next-Action": aid, "Accept": "text/x-component", "Content-Type": "text/plain;charset=UTF-8"})
    if r is None:
        return [], files, "station list did not answer"
    files.append(gz(M, "stations.rsc", r.content))
    rows = stations(r.text)
    recs = []
    for si, s in enumerate(rows):
        url = f"{MAP}/{s['id']}"
        name = mobile = rank = None
        x = get(url)
        if x is not None:
            files.append(gz(M, f"station-{s['id']}.html", x.content))
            name, mobile, rank = officer(x.text)
        try:
            lat, lon = float(s.get("latitude")), float(s.get("longitude"))
        except (TypeError, ValueError):
            lat = lon = None
        recs.append(rec(M, s["id"], area=s.get("name"), area_regional=s.get("nameMr"), post="Senior Police Inspector (in charge)",
                        name=name, rank=rank, phone=phones(mobile, s.get("contactNo")), mobile=mobile,
                        landline=phones(s.get("contactNo")), address=s.get("address"), address_regional=s.get("addressMr"),
                        zone=s.get("zone"), state="MH", district="Thane", office_id=s["id"], lat=lat, lon=lon, source=url,
                        # station fields: the server-action list (line "1:", array index); the officer: the station page text
                        **provenance.at(r, BASE + "/en"), src_pos={"line": "1:", "index": si, "id": s["id"],
                                                                   **({"officer_from": url} if name else {})},
                        method="json (Next.js server action)" + (" + html text (officer line)" if name else "")))
    return uniq(recs), files, "" if recs else ("; ".join(why) or "no stations")
