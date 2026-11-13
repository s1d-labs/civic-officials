"""BSES Rajdhani (BRPL, south and west Delhi) and BSES Yamuna (BYPL, east and central Delhi): office lists on www.bsesdelhi.com
(Liferay). BRPL answers from Germany, slowly (live samples 2026-11-11; not in archive.s1d.me); the BYPL pages timed out from
Germany (0 bytes in 30-60 s) and /web/bypl/operations-maintenance-offices answered 404.
The "Contact Us" menu of each site (/web/<brpl|bypl>/contact-customer-care) links Divisional Offices, Sub Division Offices,
Operations & Maintenance Offices, Digi Seva Kendras, Payment Centers and Contact Points. items() reads that menu on both sites and
queues the three office pages. Each page has one table; the header row names the columns ("Division Name" | "Address"; other pages
may add phone, e-mail or officer columns: they are mapped by their header text). BRPL /divisional-offices: 23 divisions, name and
address only (no officer, no phone). No date on the pages.
Levels: divisional offices = division, sub division offices = subdivision, O&M offices = division (post "O&M Office").
Record id dept:power2_bses:<brpl|bypl>:<page>:<area>.
"""
import re

from bs4 import BeautifulSoup

from dforms._power import tr_pos, Out, cells, clean, email, phone, raw
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power2_bses"
BASE = "https://www.bsesdelhi.com"
SITES = {"brpl": "BSES Rajdhani Power Limited", "bypl": "BSES Yamuna Power Limited"}
PAGES = (("divisional", r"divisional\s*offices", "division", "Division Office"),
         ("subdivision", r"sub\s*-?\s*division\s*offices", "subdivision", "Sub Division Office"),
         ("om", r"operations\s*&?\s*(amp;)?\s*maintenance\s*offices", "division", "O&M Office"))
COLS = (("address", r"address"), ("phone", r"phone|contact|mobile|tel"), ("email", r"e-?mail"),
        ("post", r"designation"), ("name", r"name of (the )?(officer|manager|head)|officer|manager|in-?charge"),
        ("area", r"division|office|name|area|location|zone|circle"))


def items(get):
    out = []
    for site in SITES:
        r = get(f"{BASE}/web/{site}/contact-customer-care")
        if r is None:
            continue
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ", strip=True).split())
            for kind, rx, _, _ in PAGES:
                if re.fullmatch(rx, text, re.I) and f"/web/{site}/" in a["href"]:
                    url = a["href"] if a["href"].startswith("http") else BASE + a["href"]
                    key = f"power2_bses:{site}:{kind}"
                    if all(i["key"] != key for i in out):
                        out.append({"key": key, "payload": {"reader": MOD, "url": url, "state": "DL", "site": site, "page": kind,
                                                            "india_only": False}})
    return out


def _columns(header):
    cols = {}
    for i, h in enumerate(header):
        for field, rx in COLS:
            if field not in cols and re.search(rx, h or "", re.I):
                cols[field] = i
                break
    return cols


def parse(html, site, page, url):
    _, _, lvl, default_post = next(p for p in PAGES if p[0] == page)
    out = Out(MOD, "DL", url, discom=SITES[site])
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        trs = t.find_all("tr")
        if len(trs) < 2:
            continue
        cols = _columns(cells(trs[0]))
        if "area" not in cols:
            continue
        for tr in trs[1:]:
            out.src = {"src_pos": tr_pos(tr)}
            c = cells(tr)
            g = lambda f: clean(c[cols[f]]) if f in cols and cols[f] < len(c) else None   # noqa: E731
            area = g("area")
            if not area:
                provenance.skip_row(tr, 'skip: not area')
                continue
            out.add(f"{site}:{page}:{area}", lvl, area.title() if area.isupper() else area, post=g("post") or default_post,
                    name=g("name"), phone_=phone(g("phone")), email_=email(g("email")), address=g("address"))
    out.src = {}
    return out.recs


def fetch(p, get):
    url, site, page = p["url"], p.get("site", "brpl"), p.get("page", "divisional")
    r = get(url)
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, site, page, url)
    return recs, [raw(MOD, f"{site}-{page}", r.content, "html")], "" if recs else "no rows"
