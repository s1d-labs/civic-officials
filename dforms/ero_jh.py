"""Jharkhand: the EROs of all 81 assembly constituencies and their AEROs, from the CEO's pages
ceojh.jharkhand.gov.in/linkinfo/EROOfficecontact.aspx and AEROOfficecontact.aspx. Answers only from India.

Each page is an ASP.NET GridView (District Name, Constituency Name, name, Designation, Mb No): 20 rows per page on the ERO page
(5 pages), 50 on the AERO page (7 pages). GET page 1, then turn the pager as a visitor does: __doPostBack('GridView1', 'Page$N')
with the page's hidden fields, one postback per page. The page gives AC names only: numbers from forms/jh.py AC_NO (the BLO reader's
map), else _esw.ac_no(). The page shows no date and no office per AERO. One queue item = one page.
Record ids: dept:ero_jh:JH-AC-<no>:ero, dept:ero_jh:JH-AC-<no>:aero:<slug of name>.
"""
import re

from dforms import _esw
from forms.aspnet import hidden
from forms.jh import AC_NO, _norm

MODULE = "ero_jh"
BASE = "https://ceojh.jharkhand.gov.in/linkinfo/"
PAGES = {"ero": "EROOfficecontact.aspx", "aero": "AEROOfficecontact.aspx"}
POST = {"ero": "Electoral Registration Officer", "aero": "Assistant Electoral Registration Officer"}
PAGER = re.compile(r"__doPostBack\(&#39;GridView1&#39;,&#39;Page\$(\d+)&#39;\)|__doPostBack\('GridView1','Page\$(\d+)'\)")
MAX_PAGES = 40


def items(get=None):
    return [{"key": f"{MODULE}-{page}", "payload": {"reader": MODULE, "url": BASE + f, "state": "JH", "page": page, "india_only": True}}
            for page, f in PAGES.items()]


def ac_number(name, district=None):
    return AC_NO.get(_norm(name)) or _esw.ac_no("JH", name, district)


def rows(html):
    """Data rows of GridView1 as [district, AC name, name, designation, mobile]; pager and blank rows left out."""
    t = _esw.soup(html).find("table", id="GridView1")
    if t is None:
        return []
    out = []
    for r in _esw.grid(t)[1:]:
        if len(r) >= 5 and r[1] and r[2] and not re.fullmatch(r"[\d\s.]+", r[0]):
            out.append(r[:5])
    return out


def pages(html):
    """Page numbers the pager offers."""
    return sorted({int(a or b) for a, b in PAGER.findall(html)})


def parse(all_rows, page, url):
    recs, seen, miss = [], set(), set()
    for dist, ac, name, desig, mob in all_rows:
        no = ac_number(ac, dist)
        if not no:
            miss.add(ac)
        office = f"JH-AC-{no}" if no else f"JH-AC-{_esw.slug(ac)}"
        key = f"{office}:ero" if page == "ero" else f"{office}:aero:{_esw.slug(name)}"
        k, i = key, 2
        while k in seen:
            k, i = f"{key}:{i}", i + 1
        seen.add(k)
        recs.append(_esw.record(MODULE, k, dept="elections", level="ac", area=f"{no} - {ac}" if no else ac, post=POST[page],
                                designation=desig if desig.upper() not in ("ERO", "AERO") else None, name=name,
                                phone=_esw.phones(mob), state="JH", district=dist, office_id=office if no else None, source=url))
    return recs, sorted(miss)


def fetch(p, get):
    page, url = p["page"], p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{page}-p1", r.content)]
    html, got, done = r.text, rows(r.text), {1}
    while len(done) < MAX_PAGES:
        todo = [n for n in pages(html) if n not in done]
        if not todo:
            break
        n = todo[0]
        d = hidden(html)
        d.update({"__EVENTTARGET": "GridView1", "__EVENTARGUMENT": f"Page${n}"})
        r = get(url, method="POST", data=d)
        done.add(n)
        if r is None:
            continue
        html = r.text
        files.append(_esw.keep(MODULE, f"{page}-p{n}", r.content))
        got += rows(html)
    recs, _ = parse(got, page, url)
    return recs, files, "" if recs else "no rows"
