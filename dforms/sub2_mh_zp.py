"""Maharashtra: Block Development Officers (BDO, "Group Development Officer", गट विकास अधिकारी: head of the panchayat samiti = block)
from the 34 Zilla Parishad websites. All 34 ZP sites run on the same NIC S3WaaS template (Ahilyanagar nagarzp.gov.in, Yavatmal
zpyavatmal.gov.in, Satara zpsatara.gov.in ...); each has a "Directory" page (/en/directory/) with one table per category: Name |
Designation | Email | Landline No, or Name | Designation | Mobile | Address | Email. The Panchayat Samiti category lists the BDOs
("Block Development Officer, Akole"), or one table per panchayat samiti ("Babhulgaon Panchayat Samiti Officer": Group Development
Officer, address "Panchayat Samiti, Babhulgaon"). Some ZPs put the BDOs on a page of their own that the directory links to (Satara:
/en/block-development-officers-contact-list/).

One queue item per ZP (seeds/dept_sub2_mh_zp.json, 34 items): 1 GET of the directory (/directory/ when /en/directory/ fails), its
/page/N/ pages, the S3WaaS `dir_pages` pager calls of the page itself (officials.pager_blocks / ajax_rows, imported), and up to
3 linked pages of the same site whose address names BDOs or panchayat samitis. About 2-6 requests per item. These hosts answered
from Germany on 2026-11-11.
Rows kept: a designation (or name cell) that says Block / Group Development Officer, B.D.O. or गट विकास अधिकारी; not "Assistant" /
"Extension" / "Deputy" posts. Area = the panchayat samiti: from the designation ("Block Development Officer, Akole"), else the
address ("Panchayat Samiti, Babhulgaon"), else the table caption ("Kalamb Panchayat Samiti Officer"), else the email
("bdo.akole-zpnagar@mah.gov.in"). Name = the name cell when it is not the post itself; phone, email as given.
Record ids: dept:sub2_mh_zp:<host>:<slug of area>[:n].
"""
import re
from urllib.parse import urljoin, urlparse

from dforms import _esw

MODULE = "sub2_mh_zp"
# ZP site -> LGD district (code, name). Hosts checked by DNS on 2026-11-11 (NIC S3WaaS addresses 164.100.50.x / 164.100.52.x).
ZP = {
    "nagarzp.gov.in": ("466", "Ahilyanagar"), "akolazp.gov.in": ("467", "Akola"), "zpamravati.gov.in": ("468", "Amravati"),
    "zpbeed.gov.in": ("470", "Beed"), "zpbhandara.maharashtra.gov.in": ("471", "Bhandara"),
    "zpbuldhana.maharashtra.gov.in": ("472", "Buldhana"), "zpchandrapur.maharashtra.gov.in": ("473", "Chandrapur"),
    "aurangabadzp.gov.in": ("469", "Chhatrapati Sambhajinagar"), "zpdharashiv.maharashtra.gov.in": ("488", "Dharashiv"),
    "zpdhule.maharashtra.gov.in": ("474", "Dhule"), "zpgadchiroli.maharashtra.gov.in": ("475", "Gadchiroli"),
    "zpgondia.gov.in": ("476", "Gondia"), "zphingoli.gov.in": ("477", "Hingoli"), "zpjalgaon.gov.in": ("478", "Jalgaon"),
    "zpjalna.maharashtra.gov.in": ("479", "Jalna"), "zpkolhapur.gov.in": ("480", "Kolhapur"), "zplatur.gov.in": ("481", "Latur"),
    "zpnagpur.maharashtra.gov.in": ("484", "Nagpur"), "zpnanded.maharashtra.gov.in": ("485", "Nanded"),
    "zpnandurbar.maharashtra.gov.in": ("486", "Nandurbar"), "zpnashik.maharashtra.gov.in": ("487", "Nashik"),
    "zppalghar.gov.in": ("665", "Palghar"), "zpparbhani.gov.in": ("489", "Parbhani"), "punezp.gov.in": ("490", "Pune"),
    "zpraigad.gov.in": ("491", "Raigad"), "zpratnagiri.gov.in": ("492", "Ratnagiri"), "zpsangli.maharashtra.gov.in": ("493", "Sangli"),
    "www.zpsatara.gov.in": ("494", "Satara"), "zpsindhudurg.maharashtra.gov.in": ("495", "Sindhudurg"),
    "zpsolapur.gov.in": ("496", "Solapur"), "zpthane.maharashtra.gov.in": ("497", "Thane"), "zpwardha.maharashtra.gov.in": ("498", "Wardha"),
    "zpwashim.gov.in": ("499", "Washim"), "zpyavatmal.gov.in": ("500", "Yavatmal"),
}
BDO = re.compile(r"(?i)\b(block|group|gat)\s+development\s+of+i*c+e*r|\bB\.?\s?D\.?\s?O\b|गट\s*विकास\s*अधिकारी")
NOT_BDO = re.compile(r"(?i)assistant|asst|extension|deputy|dy\.|addl|additional|education|engineer|child|project|सहाय्यक|विस्तार|उप\s")
LINK = re.compile(r"(?i)block-development|group-development|bdo|panchayat-samiti|गट-विकास|पंचायत-समिती")
PLACE_TAIL = re.compile(r"(?i)\b(panchayat\s+(samiti|committee)|पंचायत\s+समिती)\b")


def items(get=None):
    return [{"key": f"sub2_mh_zp_{host.removeprefix('www.').split('.')[0]}",
             "payload": {"reader": MODULE, "url": f"https://{host}/en/directory/", "district": name, "district_code": code, "state": "MH",
                         "india_only": False}}
            for host, (code, name) in ZP.items()]


def clean_place(s):
    s = _esw.clean(s)
    s = re.sub(r"(?i)\b(office|officer|of|the|zilla\s+parishad|z\.?\s?p\.?|taluka?|tal\.|block|पंचायत\s+समिती|कार्यालय|गट\s*विकास\s*अधिकारी)\b",
               " ", s)
    s = PLACE_TAIL.sub(" ", s)
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-:;|")
    return s if 1 < len(s) <= 30 and not re.search(r"\d", s) else ""


def area_of(post, address, caption, email, cells=None):
    for h, v in (cells or {}).items():
        if re.search(r"(?i)panchayat\s*samiti|taluka|block|पंचायत\s*समिती|तालुका", h or "") and clean_place(v):
            return clean_place(v)
    m = re.search(r"[,:\-]\s*([^,:]+?)\s*$", re.sub(r"\(.*?\)", "", post or ""))
    if m and BDO.search(post[:m.start()] + " "):
        a = clean_place(m.group(1))
        if a:
            return a
    for s in (address, caption):
        m = re.search(r"(?i)(?:panchayat\s+(?:samiti|committee)|पंचायत\s+समिती|\bP\.?\s?S\.?(?=\s))\s*(?:office)?\s*[,:\-]?\s*"
                      r"([^\s,|][^,|]*)", s or "")
        if m and clean_place(m.group(1)):
            return clean_place(m.group(1))
        m = re.search(r"(?i)([^,|]+?)\s+(?:panchayat\s+(?:samiti|committee)|पंचायत\s+समिती)", s or "")
        if m and clean_place(m.group(1)):
            return clean_place(m.group(1))
    m = re.search(r"(?i)\bbdo[._-]?([a-z]+)", _esw.deob(email or ""))
    if m and m.group(1) not in ("zp", "office", "ps"):
        return m.group(1).title()
    return ""


def rows_of(html, caption_default=""):
    """[(caption, normalised row)] from every table of one page."""
    from officials import normalise, tables
    out = []
    for t in tables(html):
        for cells in t["rows"]:
            out.append((t["caption"] or caption_default, {**normalise(cells), "_cells": cells}))
    return out


def ajax_rows(html, get):
    from officials import ajax_rows as parse, pager_blocks
    out = []
    pg = pager_blocks(html, "dir")
    if not pg:
        return out, []
    files = []
    for b in pg["blocks"]:
        p = 1
        while p < b["pages"] and p <= 10:
            r = get(pg["ajaxurl"], method="POST", data={"action": pg["action"], "paged": p, "tax_slug": b["slug"], "type": "next",
                                                       "profile_image": pg["profile"], "filter": pg["filter"], "security": pg["nonce"]})
            if r is None:
                break
            files.append(_esw.keep(MODULE, f"ajax-{_esw.slug(b['slug'])[:40]}-{p}", r.content, "json"))
            got = parse(r.text)
            if not got:
                break
            from officials import normalise
            out += [(b["name"], {**normalise(c), "_cells": c}) for c in got]
            if '"last":1' in r.text.replace(" ", "") or '"last":"1"' in r.text.replace(" ", ""):
                break
            p += 1
    return out, files


def tabular_rows(html, url, get):
    """Newer S3WaaS directory pages (div.s3waas-tabular-content data-params=<base64 JSON with the page's nonce>): every taxonomy
    section's table is in the page; more pages come from the page's own call `directory_paginate` (termParams, params, pageno), and
    a page that renders no section gives each department from its select box with `directory_tax_filter` (term_id, params)."""
    from bs4 import BeautifulSoup
    import json
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".s3waas-tabular-content[data-params]")
    m = re.search(r'"ajaxUrl"\s*:\s*"([^"]+)"', html)
    if box is None or not m:
        return [], []
    ajax = m.group(1).replace("\\/", "/")
    params = box["data-params"]
    out, files, calls = [], [], 0

    def answer_rows(r, head):
        try:
            content = (json.loads(r.text).get("data") or {}).get("content") or ""
        except (ValueError, AttributeError):
            return []
        if "<table" not in content:
            content = f"<table>{head}{content}</table>"
        return rows_of(content)
    for sec in soup.select(".taxonomy-section[data-params]"):
        cap = sec.find_previous(["h2", "h3", "h4", "caption"])
        thead = sec.find("thead")
        head = str(thead) if thead else ""
        pages = sorted({int(a["data-page-id"]) for a in sec.select("[data-page-id]") if str(a["data-page-id"]).isdigit()} - {1})
        for n in pages[:10]:
            r = get(ajax, method="POST", data={"action": "directory_paginate", "termParams": sec["data-params"], "params": params,
                                               "pageno": n})
            calls += 1
            if r is None:
                break
            files.append(_esw.keep(MODULE, f"tabular-{_esw.slug(sec['data-params'])[:20]}-{n}", r.content, "json"))
            out += [(c or (cap.get_text(" ", strip=True) if cap else ""), row) for c, row in answer_rows(r, head)]
    if not soup.select(".taxonomy-section[data-params]"):
        opts = [(o["value"], o.get_text(" ", strip=True)) for o in box.select("select option[value]") if o["value"] != "-1"]
        for v, label in opts[:6]:
            if len(opts) > 2 and not re.search(r"(?i)bdo|block|group\s+dev|panchayat|samiti|गट|पंचायत|taluka", label):
                continue
            r = get(ajax, method="POST", data={"action": "directory_tax_filter", "term_id": v, "params": params, "pageno": ""})
            if r is None:
                continue
            files.append(_esw.keep(MODULE, f"tabular-term-{v}", r.content, "json"))
            out += [(c or label, row) for c, row in answer_rows(r, "")]
    return out, files


def build(rows, p, source, host, upd=None):
    recs, seen = [], set()
    for caption, r in rows:
        post = r.get("designation", "")
        name = r.get("name", "")
        cand = post if BDO.search(post) else (name if BDO.search(name) else "")
        if not cand or NOT_BDO.search(cand):
            continue
        email = _esw.emails(r.get("email", "")) or _esw.emails(" ".join(r["_cells"].values()))
        area = area_of(cand, r.get("address", ""), caption, email, r["_cells"])
        if not area:
            continue
        if name and (BDO.search(name) or _esw.clean(name).lower() == _esw.clean(post).lower()):
            name = ""
        name = re.sub(r"(?i)\s*\((in-?\s*charge|incharge|अतिरिक्त\s*कार्यभार|प्रभारी)\)", "", name).strip()
        phone = _esw.phones(r.get("phone", ""), *[v for h, v in r["_cells"].items()
                                                   if re.search(r"(?i)land\s*line|phone|mobile|tel|दूरध्वनी|भ्रमणध्वनी", h or "")
                                                   and v != r.get("phone")])
        key0 = f"{host}:{_esw.slug(area)}"
        k = (key0, name.lower(), phone)
        if k in seen:
            continue
        seen.add(k)
        key, i = key0, 2
        while any(rid == f"dept:{MODULE}:{key}" for rid, _ in recs):
            key, i = f"{key0}:{i}", i + 1
        recs.append(_esw.record(MODULE, key, dept="rural_development", level="block", area=area, district=p.get("district", ""),
                                district_code=p.get("district_code", ""), state="MH", name=name,
                                post="Block Development Officer", designation=cand, phone=phone, email=email,
                                address=r.get("address", ""), source=source, last_updated=upd))
    return recs


def fetch(p, get):
    from dforms.police_s3waas import last_updated, next_pages
    url = p["url"]
    host = urlparse(url).netloc
    r = get(url)
    final = urlparse(getattr(r, "url", "") or url) if r is not None else None
    if final is not None and final.netloc and final.netloc != host and "directory" not in final.path:
        # zpbeed.gov.in -> https://www.zpbeed.gov.in (the redirect drops the path): ask the new host for the same page
        host = final.netloc
        url = f"https://{host}{urlparse(url).path}"
        r = get(url)
    if r is None and "/en/" in url:
        url = url.replace("/en/", "/")
        r = get(url)
    if r is None:
        return [], [], "no answer"
    files = [_esw.keep(MODULE, f"{host}-directory-p1", r.content)]
    pages = [(url, r.text)]
    base, more = next_pages(r.text, url)
    done = {1}
    for n in sorted(more - done)[:8]:
        m = get(f"{base}page/{n}/")
        if m is None:
            break
        files.append(_esw.keep(MODULE, f"{host}-directory-p{n}", m.content))
        pages.append((f"{base}page/{n}/", m.text))
    rows = [(u, row) for u, h in pages for row in rows_of(h)]
    extra, f2 = ajax_rows(r.text, get)
    extra3, f3 = tabular_rows(r.text, url, get)
    files += f2 + f3
    rows += [(url, row) for row in extra + extra3]
    # pages of the same site that name BDOs or panchayat samitis (linked from the directory page)
    from bs4 import BeautifulSoup
    links = []
    for a in BeautifulSoup(r.text, "lxml").find_all("a", href=True):
        u = urljoin(url, a["href"]).split("#")[0]
        if urlparse(u).netloc == host and LINK.search(u + " " + a.get_text(" ")) and u not in links and "/page/" not in u \
                and not re.search(r"\.(pdf|jpe?g|png)$", u, re.I) and u.rstrip("/") != url.rstrip("/"):
            links.append(u)
    links.sort(key=lambda u: 0 if re.search(r"(?i)block-development|group-development|bdo|गट-विकास", u) else 1)
    for u in links[:3]:
        m = get(u)
        if m is None:
            continue
        files.append(_esw.keep(MODULE, f"{host}-{_esw.slug(urlparse(u).path)[-50:]}", m.content))
        rows += [(u, row) for row in rows_of(m.text)]
    upd = last_updated(r.text)
    recs, seen = [], set()
    for src in dict.fromkeys(u for u, _ in rows):
        for rid, d in build([row for u, row in rows if u == src], p, src, host, upd):
            if rid in seen:
                continue
            seen.add(rid)
            recs.append((rid, d))
    return recs, files, "" if recs else "no BDO rows"
