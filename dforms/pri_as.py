"""Assam: Panchayat Election 2025 results (Zilla Parishad, Anchalik Panchayat, Gaon Panchayat members and presidents), State
Election Commission Assam, sec.assam.gov.in "Trends & Results Portal" -> "Panchayat Election - 2025" -> /results/pe-result-2025.

Status (2026-11-13): sec.assam.gov.in does not answer dev-vps-3 (connect timeout, 5 tries) and archive.s1d.me has /results (the
portal index, party totals of SMC/BTC/RHAC/NCHAC only) but NOT /results/pe-result-2025; the PE report PDF
(/pdf/reports/pe-election-report-2025.pdf) is cut at 16 KB in the archive. The archive copies were made through the Indian
proxies (vantage IN-proxy), so the host answers Indian proxy IPs. The structure of the result page is not known yet.

This reader is therefore a SAVE step (fetch once into the bucket): it reads the result page, keeps it, follows the links on it
that stay on sec.assam.gov.in and look like results (/results/..., pdf, xls, xlsx, csv; district / constituency pages), up to
MAX_LINKS, keeps each answer, and gives one "source_file" record per kept file. HTML tables on the kept pages whose header names
a candidate / winner are also read as pri_member rows (role member; level from the words zilla / anchalik / gaon in the table or
page title), so a plain table result gives data on the first run. PDFs and scans are not parsed here (bulk parsing and OCR run
later on the runners, from the bucket copies). After the first run, write the real reader from the kept copies.
Route: Indian proxy (project with proxy "IN", e.g. civic-officials-depts-in). One item.
Record ids: pri:pri_as:file:<sha1 of url, 12>; pri:pri_as:<page sha1 8>:<table>-<row>.
"""
import hashlib
import re
from urllib.parse import urljoin, urlparse

import provenance
from dforms import _pri
from dforms._esw import table_no

METHOD = "save step (result page + linked result files kept); html table header words -> columns where a table is plain"
MODULE = "pri_as"
URL = "https://sec.assam.gov.in/results/pe-result-2025"
ELECTION = "Assam Panchayat Election 2025"
MAX_LINKS = 120
LINK = re.compile(r"(?i)/results?/|\.(pdf|xlsx?|csv)(\?|$)|winn|elected|district|constituenc|zilla|anchalik|gaon")
NOT_LINK = re.compile(r"(?i)facebook|twitter|youtube|instagram|mailto:|javascript:|\.(css|js|png|jpe?g|gif|svg|ico)(\?|$)")
NAME_H = re.compile(r"(?i)candidate|winner|name|elected|প্ৰাৰ্থী|নাম")
PARTY_H = re.compile(r"(?i)party|দল")
VOTES_H = re.compile(r"(?i)votes?|ভোট")
CONST_H = re.compile(r"(?i)constituency|ward|seat|সমষ্টি|ৱাৰ্ড")
BODY_H = re.compile(r"(?i)panchayat|parishad|গাওঁ|আঞ্চলিক|জিলা")


def items(get=None):
    return [{"key": "pri_as:pe-result-2025", "payload": {"reader": MODULE, "url": URL, "state": "AS", "route": "proxy",
             "india_only": True, "expected": 0}}]


def level_of(text):
    t = (text or "").lower()
    if re.search(r"zilla|zila|জিলা", t):
        return "zp"
    if re.search(r"anchalik|আঞ্চলিক", t):
        return "ps"
    return "gp"


def table_records(html, url, r, page_key):
    """pri_member rows from plain HTML tables with a candidate / winner column."""
    s = _pri.soup(html)
    title = _pri.clean(s.title.get_text() if s.title else "")
    out = []
    for t in s.find_all("table"):
        grid = _pri.grid(t)
        if not grid:
            continue
        hi = next((i for i, row in enumerate(grid[:3]) if any(NAME_H.search(_pri.clean(c)) for c in row)), None)
        if hi is None:
            continue
        head = [_pri.clean(c) for c in grid[hi]]
        col = {}
        for j, h in enumerate(head):
            for role, rx in (("name", NAME_H), ("party", PARTY_H), ("votes", VOTES_H), ("constituency", CONST_H), ("body", BODY_H)):
                if role not in col and rx.search(h):
                    col[role] = j
                    break
        if "name" not in col:
            continue
        tno = table_no(t)
        cap = _pri.clean(t.find("caption").get_text()) if t.find("caption") else ""
        for ri, row in enumerate(grid[hi + 1:], start=hi + 2):
            cells = [_pri.clean(c) for c in row]
            name = cells[col["name"]] if col["name"] < len(cells) else ""
            if not name or NAME_H.fullmatch(name):
                continue
            g = lambda k: cells[col[k]] if k in col and col[k] < len(cells) else ""   # noqa: E731
            out.append(_pri.record(
                MODULE, f"{page_key}:{tno}-{ri}", state="AS", level=level_of(cap + " " + title + " " + g("body")), role="member",
                post="Member (result list)", name=name, party=g("party"), votes=_pri.int_or_none(g("votes")),
                constituency=g("constituency"), body_name=g("body"), election=ELECTION, election_year=2025, source=url,
                status="in result table (winner flag not read: check the page)", src_pos={"table": tno, "row": ri},
                cells=dict(zip(head, cells)), **provenance.at(r, url)))
    return out


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer from sec.assam.gov.in (India-only host: run through an Indian proxy)"
    files, recs, seen = [], [], {p["url"]}
    queue = [(p["url"], r)]
    while queue:
        url, resp = queue.pop(0)
        body = resp.content or b""
        ctype = (getattr(resp, "headers", {}) or {}).get("Content-Type", "")
        is_html = b"<html" in body[:2000].lower() or "html" in ctype
        h = hashlib.sha1(url.encode()).hexdigest()[:12]
        ext = "html" if is_html else (re.search(r"\.(pdf|xlsx?|csv)", url.lower()) or [None, "bin"])[1]
        files.append(_pri.keep(MODULE, h, body, ext))
        recs.append((f"pri:{MODULE}:file:{h}", {"type": "source_file", "state": "AS", "url": url, "file": files[-1][0],
                                                  "size": len(body), "election": ELECTION, **provenance.at(resp, url)}))
        if not is_html:
            continue
        html = resp.text
        recs += table_records(html, url, resp, h[:8])
        for a in _pri.soup(html).find_all("a", href=True):
            u = urljoin(url, a["href"]).split("#")[0]
            if (urlparse(u).hostname or "") != "sec.assam.gov.in" or u in seen or NOT_LINK.search(u):
                continue
            if not LINK.search(u + " " + a.get_text(" ")) or len(seen) >= MAX_LINKS:
                continue
            if not (u.startswith(URL) or re.search(r"(?i)\.(pdf|xlsx?|csv)(\?|$)", u)) and "pe-" not in u.lower():
                continue          # stay inside the PE 2025 result pages and their files
            seen.add(u)
            ru = get(u)
            if ru is not None:
                queue.append((u, ru))
    return recs, files, ""
