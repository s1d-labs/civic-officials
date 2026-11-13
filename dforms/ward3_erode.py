"""Erode City Municipal Corporation (www.tnurbantree.tn.gov.in/erode/, the Tamil Nadu urban local body WordPress platform): the
staff of its 4 zone offices and main office, from four section pages (live samples from Mumbai, dev-vps-3, 2026-11-13; not in
archive.s1d.me; the pages show no date; the platform answers slowly or not at all from Germany: India only):
  /erode/general-administration/  Commissioner, the Assistant Commissioners of Zone 1-4 ("ASST. COMMISSIONER (ZONE-1)"), the zone
                                  Superintendents, then "GENERAL SECTION – ZONE – n LAND LINE NUMBER – 0424 – ..." blocks
  /erode/engineering/             City Engineer, Executive / Assistant Executive Engineers (main office), then "ZONE – n LANDLINE
                                  NUMBER ..." blocks with the zone's Assistant and Junior Engineers
  /erode/public-health-2/         City Health Officer, Sanitary Officers and Inspectors, Medical Officers (main office), then
                                  "ZONE-n LAND LINE NO. ..." blocks with the zone's Sanitary Inspectors and Sanitary Work Supervisors
  /erode/revenue/                 "REVENUE SECTION – ZONE – n ..." blocks: Revenue Inspectors and Tax Clerks
Each page is one table: SL. NO. | NAME | DESIGNATION (the revenue page has no heading row), with one-cell block rows that name the block and its landline. A person
gets the zone of the block, or of the post ("(ZONE-1)"), and the block's landline as phone (an office line, phone_kind
"office landline"). The pages give no mobile numbers and do not say which wards each zone holds (the zone landlines also
differ between pages: kept as each page writes them). Workers, drivers, nurses and clerical posts (office / junior assistants,
typists, record clerks, watchmen, skilled / technical assistants) are left out.
Records: level "zone" (area "Zone n") for zone staff, level "body" for the main office. One item, four requests. Record ids:
dept:ward3_erode:<zone-n | body>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward
import provenance

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_erode"
BODY, LGD, STATE, DISTRICT = "Erode City Municipal Corporation", "252568", "TN", "Erode"
BASE = "https://www.tnurbantree.tn.gov.in/erode/"
URL = BASE + "general-administration/"
PAGES = ("general-administration", "engineering", "public-health-2", "revenue")
ZONE = re.compile(r"(?i)\bzone\s*[-–]?\s*(\d)\b")
LEFT_OUT = re.compile(r"(?i)\b(worker|driver|nurse|office\s+assistant|junior\s+assistant|typist|record\s+clerk|watchman|"
                      r"skilled\s+assistant|technical\s+assistant|accountant|steno\w*)\b|^assistant$")
PHONE = re.compile(r"(0\d{3})\s*[–-]\s*(\d{6,8})|(?<![\d-])(\d{7})(?!\d)")


def items(get=None):
    return [{"key": f"{MODULE}-zone-staff", "payload": {"reader": MODULE, "url": URL, "state": STATE, "india_only": True,
                                                       "route": "direct", "pages": [BASE + p + "/" for p in PAGES]}}]


def block_phones(text):
    """Landlines of a block row: "0424 – 2251616, 0424 – 2251617" -> "0424-2251616, 0424-2251617"; a bare 7-digit number after
    one with the STD code takes that code."""
    out, std = [], None
    for m in PHONE.finditer(text):
        if m.group(1):
            std = m.group(1)
            n = f"{std}-{m.group(2)}"
        else:
            n = f"{std}-{m.group(3)}" if std else m.group(3)
        if n not in out:
            out.append(n)
    return ", ".join(out)


def post_name(s):
    s = re.sub(r"(?i)\bASST\.?\s*", "Assistant ", _esw.clean(s))
    s = ZONE.sub(" ", s)
    s = re.sub(r"\(\s*\)", " ", s)
    return " ".join(w.capitalize() if w.isupper() else w for w in _esw.clean(s).split()).strip(" ,-–")


def rows(html):
    """[(block, block zone, block phones, name, post, src_pos)] of a section page's table."""
    out = []
    soup = _esw.soup(html)
    for ti, t in enumerate(soup.find_all("table"), 1):
        trs = [tr for tr in t.find_all("tr") if tr.find_parent("table") is t]
        if not trs:
            continue
        block, bzone, bphone = "", None, ""
        for ri, tr in enumerate(trs, 1):
            c = [_esw.clean(x.get_text(" ")) for x in tr.find_all(["td", "th"])]
            vals = [v for v in c if v]
            if any(v.lower() == "designation" for v in vals):     # the heading row
                provenance.skip_row(tr, 'skip: any(v.lower() == "designation" for v in vals)')
                continue
            if len(vals) == 1 and not c[0].isdigit():
                block = vals[0]
                m = ZONE.search(block)
                bzone = int(m.group(1)) if m else None
                bphone = block_phones(block)
                continue
            if len(c) >= 3 and c[0].isdigit() and c[1]:
                out.append((block, bzone, bphone, c[1], c[2], {"table": ti, "row": ri}))
    return out


def parse(pages, p):
    """pages: {page url: html}."""
    seen, recs = set(), []
    for url, html in pages.items():
        for block, bzone, bphone, name, post, pos in rows(html):
            if not post or LEFT_OUT.search(post) or re.match(r"(?i)vacant$", name):
                provenance.skip_row(block, 'skip: not post or LEFT_OUT.search(post) or re.match(r"(?i)vacant$", name)')
                continue
            m = ZONE.search(post)
            z = int(m.group(1)) if m else bzone
            en = post_name(post)
            name = re.sub(r"(?i)^(thiru|tmt)(\.\s*|\s+)|,?\s*i\.a\.s\.?$", "", name).strip(" ,")
            kw = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=url, post=en, post_as_written=post,
                      name=name, phone=bphone, phone_kind="office landline" if bphone else None, block=block or None,
                      src_pos=pos)
            if z:
                area = f"Zone {z}"
                recs.append((url, _ward.record(MODULE, f"zone-{z}:{_esw.slug(en)}:{_esw.slug(name)}", seen, level="zone",
                                               area=area, zone=area, **kw)))
            else:
                recs.append((url, _ward.record(MODULE, f"body:{_esw.slug(en)}:{_esw.slug(name)}", seen, level="body",
                                               area=BODY, **kw)))
    return recs


def fetch(p, get):
    pages, answers, files = {}, {}, []
    for url in p.get("pages") or [p["url"]]:
        r = get(url)
        if r is None:
            continue
        pages[url], answers[url] = r.text, r
        files.append(_esw.keep(MODULE, url.rstrip("/").rsplit("/", 1)[-1], r.content))
    if not pages:
        return [], files, "no answer"
    recs = []
    for url, rec in parse(pages, p):
        recs += _ward.tag([rec], answers[url], url)
    return recs, files, "" if recs else "no staff tables"
