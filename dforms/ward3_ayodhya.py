"""Ayodhya Nagar Nigam (nagarnigamayodhya.in, a React app): the officers of each department with mobile numbers. The "Contact Us"
page has no API: its tables are written into the app's script bundle (/static/js/main.<hash>.js, named in the home page; live
sample 2026-11-13 from Mumbai, not in archive.s1d.me) as arrays [{id, itemName: designation, itemName1: name, itemName2: mobile}],
each after a heading (children:"Civil Department", "Tax Department", "Water Department", "Health Department", "Light
Department", "Accounts Department"; the first, under "Contact Us", holds the Mayor, the Commissioner and the additional
commissioners). The page names no zones or wards: records are at level "body" (the sanitary inspectors, junior engineers, tax
inspectors of the whole city). The Mayor row is left out (elected: the councillors task has the heads).
Record ids: dept:ward3_ayodhya:<department slug>:<post slug>:<mobile or id>. src_pos = {"section": heading, "id": the row's id}.
"""
import re

from dforms import _esw, _ward

METHOD = "js bundle (React app arrays)"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward3_ayodhya"
BODY, LGD, STATE, DISTRICT = "Ayodhya Nagar Nigam", "249391", "UP", "Ayodhya"
URL = "https://nagarnigamayodhya.in/"
ARRAY = re.compile(r'\[(\{id:\d+,itemName:"[^\]]*?itemName1[^\]]*?)\]\.map')
ROW = re.compile(r'\{id:(\d+),itemName:"((?:[^"\\]|\\.)*)",itemName1:"((?:[^"\\]|\\.)*)",itemName2:"((?:[^"\\]|\\.)*)"')
WINGS = {"Civil Department": "engineering", "Tax Department": "revenue", "Water Department": "water",
         "Health Department": "health", "Light Department": "electrical", "Accounts Department": "other"}


def items(get=None):
    return [{"key": f"{MODULE}-contact", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def js_text(s):
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    return _esw.clean(s.replace("\\t", " ").replace("\\n", " ").replace("​", ""))


def bundle_url(home):
    m = re.search(r'src="(/static/js/main\.[0-9a-f]+\.js)"', home or "")
    return URL.rstrip("/") + m.group(1) if m else None


def parse(js, p, src=None):
    seen, recs = set(), []
    for m in ARRAY.finditer(js):
        heads = re.findall(r'children:"([^"]{2,60})"', js[max(0, m.start() - 900):m.start()])
        heads = [h for h in heads if h not in ("S.No", "Designation", "Name", "Contact")]
        sec = heads[-1] if heads else ""
        if sec in ("", "Subject") or not re.search(r"(?i)department|contact", sec):
            continue
        for rid, post, name, ph in ROW.findall(m.group(1)):
            post, name, ph = js_text(post), js_text(name), js_text(ph)
            if not post or re.fullmatch(r"(?i)mayor", post):
                continue
            dept = sec if sec != "Contact Us" else "Administration"
            recs.append(_ward.record(MODULE, f"{_esw.slug(dept)}:{_esw.slug(post)}:{re.sub(r'[^0-9]', '', ph) or rid}", seen,
                                     body=BODY, lgd=LGD, state=STATE, district=DISTRICT, level="body", area=BODY, post=post,
                                     name=name, phone=ph, department=dept, wing=WINGS.get(sec) or _ward.wing_of(post),
                                     source=URL, src_url=src, src_pos={"section": sec, "id": int(rid)}))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None or r.status_code != 200:
        return [], [], "no answer"
    u = bundle_url(r.text)
    if not u:
        return [], [], "no script bundle named in the home page"
    j = get(u)
    if j is None or j.status_code != 200:
        return [], [], "no answer for the script bundle"
    files = [_esw.keep(MODULE, "main", j.content, "js")]
    recs = parse(j.text, p, u)
    _ward.tag(recs, j, u, METHOD)
    return recs, files, "" if recs else "no contact arrays in the bundle"
