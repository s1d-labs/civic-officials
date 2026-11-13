"""West Bengal Police: the department's contact list, https://wbpolice.gov.in/wbp/Common/WBP_ContactList.aspx (ASP.NET, 129 KB a
page, "Total No. of Record(s) = 1251" on 2026-11-13, 21 rows a page = about 60 pages; fetched once by hand from Mumbai, needs TLS
legacy renegotiation: councillors.get() retries with LegacyTLS). Table "Name of Office/Establishment | Name | Telephone Number":
SPs, Addl. SPs, SDPOs, police stations, control rooms of the districts and commissionerates, GRP and other units (the
"Others" type holds the headquarters posts). The grid's own pager is followed: POST of the page's hidden fields with
__EVENTTARGET = ctl00$ContentPlaceHolder1$grid_contactus and __EVENTARGUMENT = Page$N (the link the page itself shows).
Records: level police_station for "... PS" offices, state for DGP / ADG / IG / headquarters offices, else district (SP, SDPO,
control room), with the district when the office names a West Bengal district. One queue item = the whole list (one GET +
up to 80 POSTs). Ids: dept:st_wb_police:<office slug>[:n]. src_pos {"page": grid page, "table", "row"} and src_sha256 of the
answer (one url gives many answers). Route: India (direct; the archive copy is from the GitHub pool, so abroad may also answer:
unchecked).
"""
import re

from dforms import _esw, _state, _st_ape
from dforms.st_wb_par import district_in
from forms.aspnet import hidden
import provenance

METHOD = "html table (header names), ASP.NET GridView pager postbacks"
MODULE = "st_wb_police"
URL = "https://wbpolice.gov.in/wbp/Common/WBP_ContactList.aspx"
GRID = "ctl00$ContentPlaceHolder1$grid_contactus"
MAX_PAGES = 80
STATE_POST = re.compile(r"(?i)\b(DGP|D\.G\.|director general|ADG|A\.D\.G|IGP?\b|I\.G\.|inspector general|DIG\b|D\.I\.G|"
                        r"headquarter|bhabani bhawan|state|W\.?B\.?P\.?\s*H\.?Q|CID|IB\b|intelligence|STF|EB\b|"
                        r"enforcement branch|range)")


def total(html):
    m = re.search(r"Total No\. of Record\(s\)\s*=\s*(\d+)", html or "")
    return int(m.group(1)) if m else None


def pages_linked(html):
    return sorted({int(n) for n in re.findall(r"Page\$(\d+)", (html or "").replace("&#39;", "'")) if n.isdigit()})


def parse(html, url=URL, page=1, sha=None):
    recs = []
    for t in _st_ape.tables(html):
        for d, pos, cells in _st_ape.header_rows(t):
            office = d.get("department") or d.get("district") or ""
            if not office or re.search(r"(?i)total no\. of record|please note", office):
                continue
            name = d.get("name", "")
            if re.fullmatch(r"[\d\s.]+", office):        # the pager row
                continue
            code, dname = district_in(office)
            if re.search(r"(?i)\bP\.?S\.?\b|police station|thana", office) and not re.search(r"(?i)\bACP\b|\bDCP\b", office):
                level, kind = "police_station", "police_station"
            elif STATE_POST.search(office) and not code:
                level, kind = "state", "police"
            else:
                level, kind = ("district", "police") if code else ("state", "police")
            post = re.split(r"\s*,\s*", office)[0]
            recs.append((_state.rec(
                MODULE, "", state="WB", level="district" if level == "police_station" and code else level, district=dname,
                district_code=code, post=post, post_kind=_st_ape.post_kind(post), name=name, body=office, body_kind=kind,
                department="West Bengal Police", dept="police", phone=_esw.phones(d.get("phone")), office_level=level,
                area_name=office, src_url=url, src_pos={"page": page, **pos}, src_sha256=sha, cells=cells,
                section="Contact list"), office))
    return recs


def keyed(pairs):
    out, seen = [], {}
    for (rid, d), office in pairs:
        k = _esw.slug(office) or "row"
        seen[k] = seen.get(k, 0) + 1
        if seen[k] > 1:
            k = f"{k}:{seen[k]}"
        out.append((f"dept:{MODULE}:{k}", d))
    return out


def items(get=None):
    return [{"key": f"{MODULE}:list", "payload": {"reader": MODULE, "url": URL, "state": "WB", "india_only": True,
                                                  "route": "direct"}}]


def fetch(p, get):
    url = p["url"]
    r = get(url)
    if r is None:
        return [], [], "no answer"
    files, pairs, done = [], [], set()
    page, html = 1, r.text
    while True:
        done.add(page)
        files.append(_esw.keep(MODULE, f"page-{page}", r.content))
        pairs += parse(html, url, page, provenance.at(r, url).get("src_sha256"))
        nxt = [n for n in pages_linked(html) if n > page and n not in done]
        if not nxt or len(done) >= MAX_PAGES:
            break
        page = nxt[0]
        form = hidden(html)
        form.update({"__EVENTTARGET": GRID, "__EVENTARGUMENT": f"Page${page}"})
        r = get(url, method="POST", data=form)
        if r is None:
            break
        html = r.text
    recs = keyed(pairs)
    tot = total(html)
    if tot is not None and len(recs) < tot:
        recs.append((f"dept:{MODULE}:count", {"type": "seed_note", "module": MODULE, "total": tot, "read": len(recs),
                                              "pages": len(done), "src_url": url}))
    return recs, files, "" if pairs else "no rows"
