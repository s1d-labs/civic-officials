"""Tripura: the EROs of all 60 assembly constituencies and the AEROs of each sub-division, from the CEO's EnCore ERMS pages
erms.tripura.gov.in/encoretripura/outviews/viewERO.aspx and viewEROAERO.aspx. Answers only from India.

viewERO.aspx: one GET; one card per AC (ContentPlaceHolder1_dlviewDEO_*_<i>: lblDistrict_Name = "1   Simna (ST)", lblName, Label1 =
designation, lblMobileNo, Label2 = alternate mobile, lblEmailId, Label3 = alternate email; "N/A" when empty).
viewEROAERO.aspx: 10 cards a page (lblDistrict_Name = "Sabroom Subdivision", lblName, lblCategory = designation, lblMobileNo,
lblEmailId); the pager (rptPager, "First << 1 2 3 4 5 >> Last") is turned by postbacks, the current page is the disabled link.
AEROs are listed by sub-division, not by AC. The pages show no date. One queue item = one page.
Record ids: dept:ero_tr:TR-AC-<no>:ero, dept:ero_tr:TR-SD-<sub-division>:aero:<slug of name>.
"""
import re

from dforms import _esw
from forms.aspnet import hidden

MODULE = "ero_tr"
BASE = "https://erms.tripura.gov.in/encoretripura/outviews/"
PAGES = {"ero": "viewERO.aspx", "aero": "viewEROAERO.aspx"}
P = "ContentPlaceHolder1_dlviewDEO_"
NO = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s*$")
LINK = re.compile(r"__doPostBack\('([^']*rptPager[^']*)'")
MAX_PAGES = 80


def items(get=None):
    return [{"key": f"{MODULE}-{page}", "payload": {"reader": MODULE, "url": BASE + f, "state": "TR", "page": page, "india_only": True}}
            for page, f in PAGES.items()]


def _v(soup, field, i):
    t = soup.find(id=f"{P}{field}_{i}")
    v = _esw.clean(t.get_text(" ")) if t else ""
    return "" if v.upper() in ("N/A", "NA", "-") else v


def cards(html):
    soup = _esw.soup(html)
    out, i = [], 0
    while soup.find(id=f"{P}lblName_{i}"):
        out.append({"area": _v(soup, "lblDistrict_Name", i), "name": _v(soup, "lblName", i),
                    "designation": _v(soup, "Label1", i) or _v(soup, "lblCategory", i),
                    "phone": _esw.phones(_v(soup, "lblMobileNo", i), _v(soup, "Label2", i)),
                    "email": _esw.emails(_v(soup, "lblEmailId", i) + " " + _v(soup, "Label3", i))})
        i += 1
    return out


def pager(html):
    """(current page, {link text: event target}) of the rptPager."""
    soup = _esw.soup(html)
    cur, links = None, {}
    for a in soup.select("a[id*=rptPager_lnkPage]"):
        text = _esw.clean(a.get_text(" "))
        m = LINK.search(a.get("href", ""))
        if "page_disabled" in (a.get("class") or []):
            cur = int(text) if text.isdigit() else cur
        elif m:
            links[text] = m.group(1)
    return cur, links


def parse(all_cards, page, url):
    recs, seen = [], set()
    for c in all_cards:
        if not c["name"]:
            continue
        if page == "ero":
            m = NO.match(c["area"])
            if not m:
                continue
            no, ac = int(m.group(1)), m.group(2)
            office = f"TR-AC-{no}"
            key, f = f"{office}:ero", dict(level="ac", area=f"{no} - {ac}", post="Electoral Registration Officer", office_id=office)
        else:
            sd = re.sub(r"(?i)\s*sub-?\s*division\s*$", "", c["area"]).strip()
            if not sd:
                continue
            office = f"TR-SD-{_esw.slug(sd)}"
            key, f = f"{office}:aero:{_esw.slug(c['name'])}", dict(level="subdivision", area=sd,
                                                                    post="Assistant Electoral Registration Officer", office_id=office)
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", designation=c["designation"], name=c["name"], phone=c["phone"],
                                email=c["email"], state="TR", source=url, **f))
    return recs


def _form(html):
    d = hidden(html)
    for sel in _esw.soup(html).find_all("select"):
        o = sel.find("option", selected=True) or sel.find("option")
        if sel.get("name") and o is not None:
            d[sel["name"]] = o.get("value", "")
    return d


def fetch(p, get):
    page, url = p["page"], p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{page}-p1", r.content)]
    html, got = r.text, cards(r.text)
    if page == "aero":
        done = {1}
        for _ in range(MAX_PAGES):
            cur, links = pager(html)
            if cur is None:
                break
            target = links.get(str(cur + 1)) or links.get(">>")
            if not target:
                break
            d = _form(html)
            d.update({"__EVENTTARGET": target, "__EVENTARGUMENT": ""})
            r = get(url, method="POST", data=d)
            if r is None:
                break
            new, _ = pager(r.text)
            if new is None or new in done:
                break
            done.add(new)
            html = r.text
            files.append(_esw.keep(MODULE, f"{page}-p{new}", r.content))
            got += cards(html)
    recs = parse(got, page, url)
    return recs, files, "" if recs else "no rows"
