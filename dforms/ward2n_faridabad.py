"""Municipal Corporation Faridabad (mcfaridabad.in): its 8 zones (NIT Zone-I to III, Old Zone-I and II, BLB Zone-I and II,
Chandawali) with the officer and mobile of each zone, and its Joint Commissioners (HQ, NIT, Ballabhgarh, Faridabad), from the page
"Administrative Hierarchy". The site is a single-page app (Vite/React): the text is in the app's script bundle
(/assets/index-<hash>.js, named in the home page) as the English locale object {..., jcHq: {name, designation}, ...,
zones: {zone1: {name, officer, mobile}, ...}}. Live sample 2026-11-11 (answers from Germany; not in archive.s1d.me; the page shows
no date). The old domain mcfbd.org now serves an unrelated gambling site (checked 2026-11-11): do not use it. The page does not
say which wards each zone holds and gives no post for the zone officer ("Officer Name"): post "Zonal Officer". The Hindi locale
object gives name_regional / area_regional.
Two requests per run: the home page, then the bundle. Record ids: dept:ward2n_faridabad:<zone slug | jc key>:<post slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "pdf text (pdftotext -layout, else pypdf layout) + json api + html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2n_faridabad"
BODY, LGD, STATE, DISTRICT = "Municipal Corporation Faridabad", "248585", "HR", "Faridabad"
URL = "https://mcfaridabad.in/"
ZONE = re.compile(r'(zone\d+):\{name:"([^"]+)",officer:"([^"]*)",mobile:"([^"]*)"\}')
JC = re.compile(r'(jc[A-Z][a-z]+):\{name:"([^"]*)",designation:"([^"]*)"\}')
DEV = re.compile(r"[\u0900-\u097F]")
JC_AREA = {"jcNit": "NIT", "jcBlb": "Ballabhgarh", "jcFrb": "Faridabad (Old)"}


def items(get=None):
    return [{"key": f"{MODULE}-administrative-hierarchy", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def bundle_url(html, base=URL):
    m = re.search(r'<script[^>]+src="(/assets/index-[^"]+\.js)"', html)
    return base.rstrip("/") + m.group(1) if m else None


def pairs(rx, js):
    """{key: (English groups, Hindi groups or None)}: the bundle holds an English and a Hindi locale object with the same keys."""
    out = {}
    for m in rx.finditer(js):
        g = m.groups()
        en, hi = out.get(g[0], (None, None))
        if DEV.search("".join(g[1:])):
            hi = hi or g[1:]
        else:
            en = en or g[1:]
        out[g[0]] = (en, hi)
    return out


def parse(js, p, source=None):
    seen, recs = set(), []
    kw = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, source=source or p["url"],
              page="https://mcfaridabad.in/ (Administrative Hierarchy)")
    for key, (en, hi) in pairs(ZONE, js).items():
        if not en:
            continue
        zone, officer, mobile = en
        recs.append(_ward.record(MODULE, f"{_esw.slug(zone)}:zonal-officer", seen, level="zone", area=zone, zone=zone,
                                 area_regional=hi[0] if hi else None, post="Zonal Officer", name=officer.strip(" -"),
                                 name_regional=hi[1] if hi else None, phone=mobile, wing="administration", **kw))
    for key, (en, hi) in pairs(JC, js).items():
        if not en or not en[0].strip(" -"):
            continue
        name, post = en
        area = JC_AREA.get(key)
        recs.append(_ward.record(MODULE, f"{_esw.slug(key)}:{_esw.slug(post)}", seen, level="zone" if area else "body",
                                 area=area or BODY, zone=area, post=post, post_regional=hi[1] if hi else None, name=name,
                                 name_regional=hi[0] if hi else None, wing="administration", **kw))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer (home page)"
    js_url = bundle_url(r.text, p["url"])
    if not js_url:
        return [], [_esw.keep(MODULE, "home", r.content)], "no script bundle in the home page"
    j = get(js_url)
    if j is None:
        return [], [], "no answer (script bundle)"
    recs = parse(j.text, p, source=js_url)
    return recs, [_esw.keep(MODULE, "bundle", j.content, "js")], "" if recs else "no zone objects in the bundle"
