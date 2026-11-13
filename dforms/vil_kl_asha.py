"""Kerala: the ASHA workers of each ward, with mobile numbers, from the "ASHA Worker Details" page of each local body's own
website on lsgkerala.gov.in (the 2026 Drupal template, the same sites as dforms/civic_anganwadi_kl.py).

Structure (measured 2026-11-13 from Mumbai): the page sits in the body's menu (Administration), but its address differs from
body to body: /en/page/asha-worker-details (Akathethara, 19 ASHAs), /en/page/asha-workers (Adat, 23), /en/page/asha-workers-list
(Adimaly, 42, one table per FHC / PHC with a title row "ASHA DETAILS OF FHC DEVIYAR COLONY"). So the reader opens the body's
home page (/en), follows the menu links whose address or text names ASHA (at most 3), and reads every table of those pages
by its header words (dforms/_vilwork.py): "Ward No | Name | Phone Number", "No | Name | Ward | Mobile Number",
"CHC/PHC | Name of ASHA | Contact NO. | Ward". Bodies without the new template (or without the page) end with "no ASHA page".
Host names of the grama panchayats are derived from their LGD names (<name>panchayat.lsgkerala.gov.in; 12 of the 15 hosts in
archive.s1d.me match the rule), so some seeds name a host that does not exist: such an item ends with "no site".
One queue item = one body: 1 GET of the home page + 1 GET per ASHA page.
Records: dept health, level village, layer village_worker, post ASHA, name, phone, area "Ward <n>", ward_no, centre (FHC / PHC
when given), body, local_body_code (LGD), district, state KL. Ids dept:vil_kl_asha:<host>:<page slug>:t<table>-r<row>:asha.
"""
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw, _vilwork

METHOD = "html table (body menu link to the ASHA page, header words -> columns)"     # source trail (provenance.py)

MODULE = "vil_kl_asha"
LINK = re.compile(r'(?is)<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>')
ASHA = re.compile(r"(?i)\basha\b")


def asha_links(html, url):
    """ASHA page links of a body's site (same host, de-duplicated, menu order)."""
    host = urlparse(url).netloc
    out = []
    for m in LINK.finditer(html or ""):
        href, text = m.group(1).replace("&amp;", "&"), _esw.clean(re.sub(r"<[^>]+>", " ", m.group(2)))
        u = urljoin(url, href)
        if urlparse(u).netloc != host or u.lower().endswith((".pdf", ".jpg", ".png")):
            continue
        if (ASHA.search(text) or re.search(r"(?i)asha", urlparse(u).path)) and u not in out:
            out.append(u)
    return out


def parse(html, url, p):
    tag = _esw.slug(urlparse(url).path.rsplit("/", 1)[-1])[-40:] or "page"
    q = dict(p, post="ASHA", dept="health", state="KL")
    return _vilwork.html_records(MODULE, html, url, q, tag)


def fetch(p, get):
    home = p["url"]
    r = get(home)
    if r is None:
        return [], [], "no site"
    host = urlparse(home).netloc
    files = [_esw.keep(MODULE, f"{host}-home", r.content)]
    links = asha_links(r.text, getattr(r, "url", "") or home)[:3]
    if not links:
        return [], files, "no ASHA page"
    recs = []
    for i, u in enumerate(links, 1):
        a = get(u)
        if a is None:
            continue
        files.append(_esw.keep(MODULE, f"{host}-asha{i}", a.content))
        recs += parse(a.text, u, p)
    return recs, files, "" if recs else "no ASHA table"
