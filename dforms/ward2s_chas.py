"""Chas Municipal Corporation (chasmunicipalcorporation.com, Bokaro district): the staff directory with each person's allotted work.
One page, /key-contacts ("CMC Directory", heading "चास नगर निगम में कार्यरत कर्मी एवं पदाधिकारी"; answers from Germany; live sample
2026-11-11, not in archive.s1d.me; the page shows no update date). Two tables:
  1. officers: क्र. सं. | तस्वीर | नाम | पद का नाम | मोबाईल नं0 (additional and assistant municipal commissioners, accounts officer);
  2. staff: क्र. सं. | तस्वीर | नाम | आवंटित कार्य (allotted work) | पद का नाम | मोबाईल नं0: city managers, junior engineers, revenue
     staff and revenue inspectors, sanitary supervisor, garden superintendent, PIU (SBM) staff, computer operators ...
The work text names the zone officers: "... एवं जोन 02 के जोनल पदाधिकारी" -> one more record for that person at level "zone"
(post "Zonal Officer", area "Zone 02"). The site does not say which wards a zone holds (Chas has 35 wards): no "wards" key.
Every other row is level "body" (a body-wide list that holds field posts: junior engineers, revenue inspectors, sanitary
supervisor). Posts in Hindi are put in English (POSTS, then _ward.hi_post); the Hindi stays in post_regional. Hindi names go in
both name and name_regional. The allotted work goes in the extra key "duties" as written.
Record ids: dept:ward2s_chas:<body or zone-NN>:<post slug>:<name slug>.
"""
import re

from dforms import _esw, _ward

METHOD = "html table"     # source trail (provenance.py): how this reader reads its sources

MODULE = "ward2s_chas"
BODY, LGD, STATE, DISTRICT = "Chas Municipal Corporation", "248056", "JH", "Bokaro"
URL = "https://chasmunicipalcorporation.com/key-contacts"
POSTS = (
    (r"नोडल\s*पदाधिकारी", "Nodal Officer, City Mission Manager"), (r"नगर\s*मिशन\s*प्रबंधक", "City Mission Manager"),
    (r"नगर\s*प्रबंधक", "City Manager"), (r"राजस्व\s*कर्मी", "Revenue Staff"), (r"कनीय\s*अभियंता\s*\(\s*यांत्रिक\s*\)", "Junior Engineer (Mechanical)"),
    (r"कनीय\s*अभियंता", "Junior Engineer"), (r"लेखा\s*पदाधिकारी", "Accounts Officer"), (r"लेखापाल", "Accountant"),
    (r"कम्प्यूटर\s*ऑपरेटर", "Computer Operator"), (r"शहरी\s*संरचना\s*विशेषज्ञ", "Urban Infrastructure Specialist"),
    (r"निम्न\s*वर्गीय\s*लिपिक", "Lower Division Clerk"), (r"इलेक्ट्रीशियन", "Electrician"),
    (r"सामुदायिक\s*संगठनकर्त्ता", "Community Organiser"), (r"^PIU$", "PIU (Project Implementation Unit) Staff"),
    (r"(?i)suprintendent", "Superintendent"),
)
ZONE = re.compile(r"जोन\s*[-–]?\s*(\d{1,2})\s*(?:के|का|की)\s*जोनल\s*पदाधिकारी")
UPPER = {"CBTC", "MIS", "PIU", "SBM", "IT"}
HONORIFIC = re.compile(r"^(श्री(?:मति|मती)?|सुश्री|Shri|Smt\.?)\s+")


def items(get=None):
    return [{"key": f"{MODULE}-key-contacts", "payload": {"reader": MODULE, "url": URL, "state": STATE}}]


def post_en(p):
    p = _esw.clean(p)
    if not p:
        return ""
    for rx, en in POSTS:
        if re.search(rx, p):
            return re.sub(rx, en, p) if rx.startswith("(?i)") else en
    if re.search("[ऀ-ॿ]", p):
        return _ward.hi_post(p)
    return " ".join(w if w in UPPER else w.title() for w in p.split()) if p.isupper() else p


def parse(html, p):
    soup = _esw.soup(html)
    seen, recs, src = set(), [], p.get("url") or URL
    for t in soup.find_all("table"):
        gp = []
        g = _esw.grid(t, pos=gp)
        if not g or not any("नाम" in c for c in g[0]):
            continue
        head = g[0]
        ix = {k: next((i for i, c in enumerate(head) if w in c), None)
              for k, w in (("name", "नाम"), ("work", "आवंटित"), ("post", "पद"), ("phone", "मोबा"))}
        ix["name"] = next(i for i, c in enumerate(head) if c.strip() == "नाम")
        for r, rp in zip(g[1:], gp[1:]):
            cell = lambda k: _esw.clean(r[ix[k]]) if ix.get(k) is not None and ix[k] < len(r) else ""  # noqa: E731
            name, work, post, phone = cell("name"), cell("work"), cell("post"), cell("phone")
            if not name or name == head[ix["name"]]:
                continue
            phone = "" if re.fullmatch(r"[-–\s]*", phone) else phone
            en = post_en(post) or "Staff"
            bare = HONORIFIC.sub("", name)
            hindi = bool(re.search("[ऀ-ॿ]", name))
            common = dict(body=BODY, lgd=LGD, state=STATE, district=DISTRICT, name=bare, phone=phone, source=src,
                          name_regional=name if hindi else None, post_regional=post if re.search("[ऀ-ॿ]", post) else None,
                          duties=work or None)
            recs.append(_ward.record(MODULE, f"body:{_esw.slug(en)}:{_esw.slug(bare) or phone or 'n'}", seen, level="body",
                                     area=BODY, post=en, **common, src_pos=rp))
            for z in ZONE.findall(work):
                zone = f"Zone {int(z):02d}"
                recs.append(_ward.record(MODULE, f"zone-{int(z):02d}:zonal-officer:{_esw.slug(bare) or phone or 'n'}", seen,
                                         level="zone", area=zone, zone=zone, post="Zonal Officer", wing="administration", **common, src_pos=rp))
    return recs


def fetch(p, get):
    r = get(p["url"])
    if r is None:
        return [], [], "no answer"
    recs = parse(r.text, p)
    return recs, [_esw.keep(MODULE, "key-contacts", r.content)], "" if recs else "no directory tables"
