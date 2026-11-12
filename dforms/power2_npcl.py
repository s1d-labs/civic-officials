"""NPCL (Noida Power Company Limited, Greater Noida, Gautam Buddha Nagar, UP): the officer contact tables of
www.noidapower.com/contact-us. India only (the site times out from Germany, 2026-11-11). The server does not send its intermediate
certificate: certs/globalsign_gcc_r46_ov_tls_ca_2025.pem (already in the repo) completes the chain.
The page is a React app: /contact-us is an empty shell whose script /static/js/main.<hash>.js holds the tables as JSX
(td children strings). fetch() GETs the shell, finds the script name, GETs the script (2 requests). Tables after "Contact Over
Phone": Customer Relation (the sub-heading in the outer row, then Name | Designation | Mobile rows), New Connection - Operations, Operations & Maintenance - Zone-1, Zone-2, Commercial Services; each row
Sub-Heading | Name | Designation | Mobile. One person can cover two sub-areas (rowspan="2": the next row has only the sub-heading).
Levels: the O&M sub-areas ("FBU Surajpur-2 (...)", "Urban-1 (...)") = subdivision, "Zone-N Head" = zone; the head-office desks
(customer relation, new connection, commercial) = zone level with area "Greater Noida (NPCL)". No date on the page.
About 20 records. Record id dept:power2_npcl:<heading>:<sub-heading>.
"""
import re

from dforms._power import Out, clean, phone, raw

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MOD = "power2_npcl"
URL = "https://www.noidapower.com/contact-us"
BASE = "https://www.noidapower.com"
TOKEN = re.compile(r'\("(tr|td)",\{((?:className:"[^"]*",)?(?:rowspan:"(\d+)",)?)(?:children:"([^"]*)")?')
COMPANY = "Greater Noida (NPCL)"


def rows(js):
    """[(heading, sub-heading, name, designation, mobile)] from the contact tables in the script."""
    sh = js.find('children:"Sub-Heading"')
    a = js.rfind("Contact Over Phone", 0, sh) if sh > 0 else -1     # the script has other tables before this one
    b = js.find("Calls to NPCL officials", a)
    if a < 0:
        return []
    part = js[a:b if b > 0 else len(js)]
    out, heading, cur, span, sub = [], None, None, None, None

    def flush():
        nonlocal span, sub
        if not cur:
            return
        texts = [t for t in cur if t is not None]
        if len(texts) == 4:
            out.append((heading, *texts))
            span = texts[1:] if cur_span else None
        elif len(texts) == 3:                    # Customer Relation: the sub-heading sits in the outer row
            out.append((heading, sub, *texts))
        elif len(texts) == 1 and span:
            out.append((heading, texts[0], *span))
            span = None
        elif len(texts) == 1:
            sub = texts[0]

    cur_span = False
    for m in TOKEN.finditer(part):
        tag, attrs, rs, text = m.groups()
        text = clean(text) if text is not None else None
        if tag == "tr":
            flush()
            cur, cur_span = [], False
            continue
        if 'className:"col-sm-2"' in attrs:          # the heading cell of an outer row
            if text:
                heading = f"{heading} (overall)" if text.lower() == "overall" and heading else text
            continue
        if cur is None:
            continue
        if text and text.lower() in ("heading", "sub-heading", "name", "designation", "mobile"):
            continue
        if rs:
            cur_span = True
        if text is not None:
            cur.append(text)
    flush()
    return out


def parse(js, url=URL):
    out = Out(MOD, "UP", url, discom="NPCL")
    for heading, sub, name, post, mob in rows(js):
        zone = re.search(r"Zone-\d+", heading or "")
        if zone and re.search(r"(?i)\bhead\b", sub or ""):
            lvl, area, par = "zone", zone.group(0), None
        elif zone:
            lvl, area, par = "subdivision", sub, {"zone": zone.group(0)}
        else:
            lvl, area, par = "zone", COMPANY, None
        out.add(f"{heading}:{sub}", lvl, area, post=post, name=name, phone_=phone(mob), district="Gautam Buddha Nagar",
                parents=par, function=heading if lvl == "zone" and not zone else None, desk=sub)
    return out.recs


def fetch(p, get):
    url = p.get("url") or URL
    r = get(url)
    if r is None:
        return [], [], "no answer"
    m = re.search(r'src="(/static/js/main\.[0-9a-f]+\.js)"', r.text)
    if not m:
        return [], [raw(MOD, "contact-us", r.content, "html")], "no script in the page"
    s = get(BASE + m.group(1))
    if s is None:
        return [], [raw(MOD, "contact-us", r.content, "html")], "no answer for the script"
    recs = parse(s.text, url)
    files = [raw(MOD, "contact-us", r.content, "html"), raw(MOD, m.group(1).rsplit("/", 1)[-1], s.content, "js")]
    return recs, files, "" if recs else "no rows"
